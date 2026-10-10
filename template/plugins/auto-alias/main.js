const { Plugin, PluginSettingTab, Setting, TFile, normalizePath, editorInfoField, moment } = require("obsidian");
const { EditorState, ChangeSet } = require("@codemirror/state");
const { EditorView } = require("@codemirror/view");

// `[[Sam (neighbour)|Sam]]` written once should make `[[Sam]]` resolve forever after. Obsidian keeps
// the pipe text local to that one link, so this plugin copies it into the target note's `aliases`
// property. The pipe is taken as a signal that the target matters: if the note does not exist yet it
// is created (where Obsidian's "default location for new notes" says) with that alias. In a Brain
// Garden vault the new note starts from its folder's template (bin/vault.json names it), so it
// carries every property the vault's lint expects.
//
// It listens to the metadata cache (not keystrokes), so it works for typing, paste, and scripts alike,
// and it touches only the *target* note, never the note being written.
//
// Each (source, target, alias) triple is handled once and remembered in data.json. Deleting an alias
// or a created page by hand therefore sticks: the plugin will not redo it on the next edit of the source.
//
// Shorthand for the same thing while typing: `[[Sam {neighbour}]]` is rewritten to
// `[[Sam (neighbour)|Sam]]` as soon as the cursor leaves the braces (typing `}` is enough). The
// rewritten link then goes through the alias step above, so a few lines later `[[Sa` offers "Sam"
// and inserts the piped link. This part is an editor extension: it only rewrites links the user is
// typing or pasting, never whole files, and it is part of the same undo step as the keystroke that
// triggered it.
//
// A link is only handled once it is finished. The metadata cache updates while you type, so without
// this `[[Acme Ltd|Acme]]` left `A` and `Acm` behind as aliases. A link is skipped while a cursor is
// inside it, or when the cache is behind the editor and the link is no longer in the text; the note
// is rescanned once the cursor moves off or the note is closed.
//
// Clippings/ is excluded by default: links in text other people wrote should not make notes.

const DEFAULTS = {
  excludeFolders: ["Templates", "Clippings"],
  done: [],                    // "source|target|alias" triples already handled
};
const DONE_CAP = 5000;

module.exports = class AutoAlias extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
    this.done = new Set(this.settings.done);
    this.pending = new Set(); // paths with a link skipped because it was still being typed
    this.registerEvent(this.app.metadataCache.on("changed", (file, data, cache) => this.scan(file, cache)));
    this.registerEditorExtension(EditorState.transactionFilter.of((tr) => this.expandBraces(tr)));
    this.registerEditorExtension(EditorView.updateListener.of((u) => {
      if (this.pending.size && (u.selectionSet || u.docChanged)) this.scheduleFlush();
    }));
    this.registerEvent(this.app.workspace.on("file-open", () => this.scheduleFlush()));
    this.registerEvent(this.app.workspace.on("layout-change", () => this.scheduleFlush()));
    this.addSettingTab(new AutoAliasSettings(this.app, this));
  }

  onunload() {
    window.clearTimeout(this.flushTimer);
  }

  scheduleFlush() {
    if (!this.pending.size) return;
    window.clearTimeout(this.flushTimer);
    this.flushTimer = window.setTimeout(() => this.flush(), 400);
  }

  flush() {
    const paths = [...this.pending];
    this.pending.clear();
    for (const path of paths) {
      const file = this.app.vault.getAbstractFileByPath(path);
      if (file instanceof TFile) this.scan(file, this.app.metadataCache.getFileCache(file));
    }
  }

  // Live text and cursor positions of every editor showing this file (none if it is not open).
  editorsOf(file) {
    const out = [];
    for (const leaf of this.app.workspace.getLeavesOfType("markdown")) {
      const view = leaf.view;
      if (!view || !view.file || view.file.path !== file.path) continue;
      if (typeof view.getMode === "function" && view.getMode() !== "source") continue;
      const cm = view.editor && view.editor.cm;
      if (!cm) continue;
      out.push({ text: cm.state.doc.toString(), heads: cm.state.selection.ranges.map((r) => r.head) });
    }
    return out;
  }

  // Finished: present in every open editor's text at least once with no cursor strictly inside it
  // (a cursor right after the closing `]]` counts as finished).
  settled(original, editors) {
    return editors.every(({ text, heads }) => {
      for (let i = text.indexOf(original); i !== -1; i = text.indexOf(original, i + 1)) {
        const end = i + original.length;
        if (!heads.some((h) => h > i && h < end)) return true;
      }
      return false;
    });
  }

  // `[[Name {context}]]` -> `[[Name (context)|Name]]`, on the lines this transaction touched or moved
  // the cursor off. Waits while any cursor is still inside the braces, so the context can be typed.
  expandBraces(tr) {
    if (!tr.docChanged && !tr.selection) return tr;
    if (!["input", "delete", "select", "move"].some((e) => tr.isUserEvent(e))) return tr;
    const info = tr.startState.field(editorInfoField, false);
    if (info && info.file && this.excluded(info.file)) return tr;

    const state = tr.state;
    const doc = state.doc;
    const lines = new Set();
    for (const r of state.selection.ranges) lines.add(doc.lineAt(r.head).number);
    for (const r of tr.startState.selection.ranges) lines.add(doc.lineAt(tr.changes.mapPos(r.head)).number);
    tr.changes.iterChangedRanges((fa, ta, from, to) => {
      const first = doc.lineAt(from).number, last = doc.lineAt(to).number;
      for (let n = first; n <= last && n - first < 200; n++) lines.add(n);
    });

    const heads = state.selection.ranges.map((r) => r.head);
    const changes = [];
    for (const n of lines) {
      const line = doc.line(n);
      if (!line.text.includes("{")) continue;
      for (const m of line.text.matchAll(BRACE_LINK)) {
        const from = line.from + m.index;
        const open = from + m[0].indexOf("{");
        const close = from + m[0].lastIndexOf("}");
        if (heads.some((h) => h > open && h <= close)) continue; // still typing the context
        if (inCode(state, from)) continue;
        const name = m[1].trim();
        const context = m[2].trim();
        const display = name.slice(name.lastIndexOf("/") + 1);
        changes.push({ from, to: from + m[0].length, insert: `[[${name} (${context})|${display}]]` });
      }
    }
    if (!changes.length) return tr;
    const set = ChangeSet.of(changes, doc.length);
    return [tr, { changes: set, selection: state.selection.map(set, 1), sequential: true, userEvent: "input.auto-alias" }];
  }

  excluded(file) {
    return this.settings.excludeFolders.some((folder) => {
      const clean = folder.trim().replace(/^\/+|\/+$/g, "");
      return clean && (file.path === clean || file.path.startsWith(clean + "/"));
    });
  }

  async scan(file, cache) {
    if (!(file instanceof TFile) || file.extension !== "md" || this.excluded(file)) return;
    const links = (cache && cache.links) || [];
    const editors = this.editorsOf(file);
    let dirty = false;
    for (const l of links) {
      const parsed = parse(l.original);
      if (!parsed) continue;
      const key = `${file.path}|${parsed.path.toLowerCase()}|${parsed.display.toLowerCase()}`;
      if (this.done.has(key)) continue;
      if (!this.settled(l.original, editors)) {
        this.pending.add(file.path);
        continue;
      }
      this.done.add(key);
      dirty = true;
      try {
        const dest = this.resolve(parsed.path, file) || (await this.create(parsed.path, file, parsed.display));
        if (!dest || dest.path === file.path || this.excluded(dest)) continue;
        await this.addAlias(dest, parsed.display);
      } catch (e) {
        console.warn("auto-alias: could not handle", l.original, "in", file.path, e);
      }
    }
    if (dirty) await this.persist();
  }

  resolve(linkpath, source) {
    const dest = this.app.metadataCache.getFirstLinkpathDest(linkpath, source.path);
    return dest instanceof TFile && dest.extension === "md" ? dest : null;
  }

  // A link with a folder in it ([[Folder/Note|x]]) is created at that path; a bare name goes where
  // Obsidian's "Default location for new notes" setting points, same as clicking the unresolved link.
  async create(linkpath, source, alias) {
    let path;
    if (linkpath.includes("/")) {
      path = normalizePath(linkpath + ".md");
    } else {
      const parent = this.app.fileManager.getNewFileParent(source.path);
      path = normalizePath((parent && parent.path && parent.path !== "/" ? parent.path + "/" : "") + linkpath + ".md");
    }
    const existing = this.app.vault.getAbstractFileByPath(path);
    if (existing instanceof TFile) return existing; // created moments ago, cache not caught up yet
    if (existing) return null;                       // a folder of that name
    const folder = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
    if (folder && !this.app.vault.getAbstractFileByPath(folder)) await this.app.vault.createFolder(folder);
    const body = (await this.templateFor(path)) || `---\naliases:\n  - ${yamlString(alias)}\n---\n`;
    return await this.app.vault.create(path, body); // scan() adds the alias next
  }

  // The text of the template for a note at `path`: bin/vault.json maps a top-level folder to its
  // template in Templates/, with core {{date}}, {{time}} and {{title}} filled in. Null when the vault
  // has no such map (not a Brain Garden vault) or the folder has no template.
  async templateFor(path) {
    const folder = path.includes("/") ? path.slice(0, path.indexOf("/")) : "";
    try {
      const config = JSON.parse(await this.app.vault.adapter.read("bin/vault.json"));
      const kind = config.kinds && config.kinds[folder];
      if (!kind || !kind.template) return null;
      const text = await this.app.vault.adapter.read(normalizePath("Templates/" + kind.template));
      const title = path.slice(path.lastIndexOf("/") + 1).replace(/\.md$/, "");
      return text
        .replace(/\{\{date\}\}/g, moment().format("YYYY-MM-DD"))
        .replace(/\{\{time\}\}/g, moment().format("HH:mm"))
        .replace(/\{\{title\}\}/g, title);
    } catch (e) {
      return null;
    }
  }

  async addAlias(dest, alias) {
    const fm = this.app.metadataCache.getFileCache(dest)?.frontmatter || {};
    const existing = toList(fm.aliases);
    const known = new Set([dest.basename.toLowerCase(), ...existing.map((a) => String(a).toLowerCase())]);
    if (known.has(alias.toLowerCase())) return;
    await this.app.fileManager.processFrontMatter(dest, (front) => {
      const list = toList(front.aliases);
      if (!list.some((a) => String(a).toLowerCase() === alias.toLowerCase())) list.push(alias);
      front.aliases = list;
    });
  }

  async persist() {
    let done = [...this.done];
    if (done.length > DONE_CAP) { done = done.slice(done.length - DONE_CAP); this.done = new Set(done); }
    this.settings.done = done;
    await this.saveData(this.settings);
  }
};

// "[[Note|Text]]" or "![[Note|Text]]" -> { path: "Note", display: "Text" }; anything else -> null.
// Heading and block links ([[Note#H|x]]) are skipped: their display text describes a section, not the note.
// So are dates and times as display text ([[2026-10-10 Weekly review|2026-10-10]]): that is
// formatting, not a name for the note.
function parse(original) {
  const m = /^!?\[\[([^\]|#^]+)\|([^\]]+)\]\]$/.exec(original || "");
  if (!m) return null;
  const path = m[1].trim();
  const display = m[2].trim();
  if (!path || !display || display.includes("|")) return null;
  if (/^[\d\s\-/.:h]+$/.test(display)) return null;
  return { path, display };
}

// `[[Name {context}]]`: a name, then one {context} at the very end. No pipe, heading or nested brackets.
const BRACE_LINK = /\[\[([^\[\]{}|#^]*[^\[\]{}|#^\s][^\[\]{}|#^]*?)\s*\{([^\[\]{}|]*[^\[\]{}|\s][^\[\]{}|]*)\}\s*\]\]/g;

// Inside inline code or a code block, `{` means code, not context.
let language = null;
try { language = require("@codemirror/language"); } catch (e) { /* no syntax tree: always expand */ }
function inCode(state, pos) {
  if (!language) return false;
  for (let node = language.syntaxTree(state).resolveInner(pos, 1); node; node = node.parent) {
    if (/code/i.test(node.name)) return true;
  }
  return false;
}

function toList(v) {
  if (v == null || v === "") return [];
  return Array.isArray(v) ? v.filter((x) => x != null && x !== "") : [v];
}

function yamlString(s) {
  return /^[\w][\w .'()-]*$/.test(s) && !/^(true|false|null|yes|no|~)$/i.test(s) && !/^\d/.test(s)
    ? s
    : JSON.stringify(s);
}

class AutoAliasSettings extends PluginSettingTab {
  constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName("Excluded folders")
      .setDesc("One per line. Links written in these notes, and notes inside them, are ignored.")
      .addTextArea((t) => t.setValue(this.plugin.settings.excludeFolders.join("\n")).onChange(async (v) => {
        this.plugin.settings.excludeFolders = v.split("\n").map((s) => s.trim()).filter(Boolean);
        await this.plugin.saveData(this.plugin.settings);
      }));
    new Setting(containerEl)
      .setName("Forget handled links")
      .setDesc("Clears the memory of which links were already processed, so removed aliases or deleted pages may be recreated on the next edit.")
      .addButton((b) => b.setButtonText("Clear").onClick(async () => { this.plugin.done = new Set(); await this.plugin.persist(); }));
  }
}
