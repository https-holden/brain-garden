const { Plugin, PluginSettingTab, Setting, TFile } = require("obsidian");

// `modified: YYYY-MM-DD` = the last day this note was edited by hand.
//
// File mtime can't answer that: a link rename rewrites hundreds of notes, scripts re-sync
// frontmatter, and a fresh git clone stamps everything with today. So the date lives in the note
// and is only written when an editor change follows real input (typing, paste, cut, drop) inside
// that editor. Everything else reaches the file without passing through here.

const PROPERTY = "modified";
const INPUT_WINDOW = 2000; // ms between your input and the editor change it caused
const IDLE = 4000; // ms of quiet before the property is written, so it never fights your typing
const DEFAULTS = { excludeFolders: ["Templates"] };

module.exports = class ManualModified extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
    this.lastInput = 0;
    this.timers = new Map();

    this.watchInput(document);
    this.registerEvent(this.app.workspace.on("window-open", (win) => this.watchInput(win.doc)));

    this.registerEvent(this.app.workspace.on("editor-change", (editor, info) => {
      const file = info && info.file;
      if (!(file instanceof TFile) || file.extension !== "md" || this.excluded(file)) return;
      if (Date.now() - this.lastInput > INPUT_WINDOW) return; // not caused by you
      if (editor.hasFocus && !editor.hasFocus()) return;
      this.schedule(file);
    }));

    this.addSettingTab(new ManualModifiedSettings(this.app, this));
  }

  onunload() {
    this.timers.forEach((timer) => window.clearTimeout(timer));
  }

  // Only input that lands in a note's text counts: not the inline title, rename boxes,
  // the properties panel or a modal.
  watchInput(doc) {
    const mark = (e) => {
      const target = e.target;
      if (target && target.closest && target.closest(".cm-content")) this.lastInput = Date.now();
    };
    for (const type of ["keydown", "beforeinput", "paste", "cut", "drop", "compositionend"]) {
      this.registerDomEvent(doc, type, mark, { capture: true });
    }
  }

  excluded(file) {
    return this.settings.excludeFolders.some((folder) => {
      const clean = folder.trim().replace(/^\/+|\/+$/g, "");
      return clean && (file.path === clean || file.path.startsWith(clean + "/"));
    });
  }

  schedule(file) {
    window.clearTimeout(this.timers.get(file.path));
    this.timers.set(file.path, window.setTimeout(() => {
      this.timers.delete(file.path);
      this.stamp(file);
    }, IDLE));
  }

  // At most one write per note per day
  async stamp(file) {
    if (!this.app.vault.getAbstractFileByPath(file.path)) return; // renamed or deleted meanwhile
    const today = window.moment().format("YYYY-MM-DD");
    const cache = this.app.metadataCache.getFileCache(file);
    const current = cache && cache.frontmatter && cache.frontmatter[PROPERTY];
    if (String(current || "").slice(0, 10) === today) return;
    try {
      await this.app.fileManager.processFrontMatter(file, (fm) => { fm[PROPERTY] = today; });
    } catch (e) {
      console.warn("manual-modified: could not update", file.path, e); // e.g. malformed frontmatter
    }
  }
};

class ManualModifiedSettings extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    this.containerEl.empty();
    new Setting(this.containerEl)
      .setName("Excluded folders")
      .setDesc("Notes in these folders never get a modified date. One vault-relative folder per line.")
      .addTextArea((text) => text
        .setValue(this.plugin.settings.excludeFolders.join("\n"))
        .onChange(async (value) => {
          this.plugin.settings.excludeFolders = value.split("\n").map((s) => s.trim()).filter(Boolean);
          await this.plugin.saveData(this.plugin.settings);
        }));
  }
}
