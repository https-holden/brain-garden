const { Plugin, MarkdownView } = require("obsidian");

// Live preview only shows a block's source (a dataviewjs snippet, a callout, a table...) while the
// cursor is inside it, and Obsidian opens every note with the cursor parked at the top. "Rest" is
// simply: cursor parked on a blank line where it reveals nothing, and the editor not focused.
// The note stays in live preview the whole time, so clicking text to edit is just a normal click.

const INTERACTIVE = "input[type=checkbox], button, a, .clickable-icon, .internal-link, .external-link, select, summary";
const NOT_MARGIN = ".cm-content, .metadata-container, .inline-title, .embedded-backlinks, .sticky-bullets, .cm-panels, .document-search-container";

// Nearest position to `head` that sits on a blank line outside frontmatter, code, math and comments
function restingPos(state, head) {
  const doc = state.doc;
  const safe = [];
  let fence = null;
  let block = null; // "$$" or "%%"
  let frontmatter = doc.lines > 0 && doc.line(1).text.trim() === "---";
  for (let n = 1; n <= doc.lines; n++) {
    const line = doc.line(n);
    const text = line.text.trim();
    if (frontmatter) {
      if (n > 1 && text === "---") frontmatter = false;
      continue;
    }
    if (fence) {
      if (text.startsWith(fence) && !text.slice(fence.length).trim().replace(/[`~]/g, "")) fence = null;
      continue;
    }
    const open = text.match(/^(```+|~~~+)/);
    if (open) { fence = open[1]; continue; }
    if (block) {
      if (text.endsWith(block)) block = null;
      continue;
    }
    if ((text.startsWith("$$") || text.startsWith("%%")) && !(text.length > 2 && text.endsWith(text.slice(0, 2)))) {
      block = text.slice(0, 2);
      continue;
    }
    if (!text) safe.push(line.from);
  }
  if (!safe.length) return fence || block ? null : doc.length;
  return safe.reduce((best, pos) => (Math.abs(pos - head) < Math.abs(best - head) ? pos : best));
}

module.exports = class RestingView extends Plugin {
  async onload() {
    const data = (await this.loadData()) || {};
    this.enabled = data.enabled !== false;
    this.lastInput = 0;
    this.opened = new WeakMap(); // leaf -> path it was last put to rest for

    this.watch(document);
    this.registerEvent(this.app.workspace.on("window-open", (win) => this.watch(win.doc)));

    // A note loading into a tab comes to rest; merely switching back to a tab does not
    const onOpen = () => this.noteOpened(this.app.workspace.getActiveViewOfType(MarkdownView));
    this.registerEvent(this.app.workspace.on("file-open", onOpen));
    this.registerEvent(this.app.workspace.on("active-leaf-change", onOpen));
    this.app.workspace.onLayoutReady(() => {
      this.app.workspace.getLeavesOfType("markdown").forEach((leaf) => this.noteOpened(leaf.view));
    });

    this.addCommand({
      id: "rest",
      name: "Let go of the cursor (rest)",
      callback: () => this.rest(this.app.workspace.getActiveViewOfType(MarkdownView)),
    });
    this.addCommand({
      id: "toggle",
      name: "Toggle resting view",
      callback: async () => {
        this.enabled = !this.enabled;
        await this.saveData({ enabled: this.enabled });
      },
    });
  }

  viewFor(el) {
    return this.app.workspace.getLeavesOfType("markdown")
      .map((leaf) => leaf.view)
      .find((view) => view instanceof MarkdownView && view.containerEl.contains(el));
  }

  editing(view) {
    const cm = view && view.editor && view.editor.cm;
    return !!cm && cm.hasFocus;
  }

  noteOpened(view) {
    if (!this.enabled || !(view instanceof MarkdownView) || !view.file || view.getMode() !== "source") return;
    if (this.opened.get(view.leaf) === view.file.path) return;
    this.opened.set(view.leaf, view.file.path);

    // A note that was only just created (Cmd+N, the morning pages hotkey) is there to be typed in
    if (Date.now() - view.file.stat.ctime < 15000 || !view.editor.getValue().trim()) return;

    // Obsidian restores its cursor and focus a beat after the file loads; rest after that, but
    // never once you have touched anything.
    const since = Date.now();
    for (const delay of [80, 350]) {
      window.setTimeout(() => {
        if (this.lastInput > since || !view.file || this.opened.get(view.leaf) !== view.file.path) return;
        this.rest(view);
      }, delay);
    }
  }

  rest(view) {
    const cm = view && view.editor && view.editor.cm;
    if (!cm) return;
    const selection = cm.state.selection.main;
    const pos = restingPos(cm.state, selection.head);
    if (pos !== null && (!selection.empty || pos !== selection.head)) {
      cm.dispatch({ selection: { anchor: pos }, scrollIntoView: false });
    }
    if (cm.hasFocus) cm.contentDOM.blur();
  }

  watch(doc) {
    const stamp = () => { this.lastInput = Date.now(); };
    this.registerDomEvent(doc, "keydown", stamp, { capture: true });
    this.registerDomEvent(doc, "mousedown", stamp, { capture: true });

    // Clicking the empty margins beside the text lets go of the note
    this.registerDomEvent(doc, "mousedown", (e) => {
      if (!this.enabled || e.button !== 0) return;
      const target = e.target;
      if (!target.closest || !target.closest(".markdown-source-view") || target.closest(NOT_MARGIN)) return;
      const view = this.viewFor(target);
      const cm = view && view.editor && view.editor.cm;
      if (!cm) return;
      if (target === cm.scrollDOM && e.offsetX > cm.scrollDOM.clientWidth) return; // the scrollbar
      const text = cm.contentDOM.getBoundingClientRect();
      if (e.clientX >= text.left && e.clientX <= text.right) return; // above/below the text: Obsidian's own behaviour
      e.preventDefault();
      e.stopPropagation();
      this.rest(view);
    }, { capture: true });

    // Interacting is not editing: a checkbox, button or link used while at rest leaves you at rest
    this.registerDomEvent(doc, "mousedown", (e) => {
      this.wasResting = null;
      if (!this.enabled || !e.target.closest || !e.target.closest(INTERACTIVE)) return;
      const view = this.viewFor(e.target);
      if (view && view.getMode() === "source" && !this.editing(view)) this.wasResting = view;
    }, { capture: true });
    this.registerDomEvent(doc, "click", () => {
      const view = this.wasResting;
      this.wasResting = null;
      if (view) window.setTimeout(() => { if (view.file) this.rest(view); }, 0);
    }, { capture: true });

    // Esc lets go too, unless it is busy closing a suggestion list or leaving zen fullscreen
    this.registerDomEvent(doc, "keydown", (e) => {
      if (!this.enabled || e.key !== "Escape" || doc.fullscreenElement) return;
      if (doc.querySelector(".suggestion-container, .modal-container, .menu")) return;
      if (!e.target.closest || !e.target.closest(".cm-content")) return;
      const view = this.viewFor(e.target);
      if (view && this.editing(view)) this.rest(view);
    });
  }
};
