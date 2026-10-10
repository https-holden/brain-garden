const { Plugin } = require("obsidian");
const { ViewPlugin, Decoration } = require("@codemirror/view");
const { RangeSetBuilder } = require("@codemirror/state");

// Sticky scroll for lists (the VS Code / PyCharm effect). The parents of whatever line sits at
// the top of the editor are pinned there, one clipped row each, outermost first. While the
// editor has focus and the cursor is on screen, the cursor's line decides instead: its parents
// that have scrolled off are pinned, so un-indenting (or moving to a shallower bullet) drops the
// deeper rows and the pinned stack always ends at the parent of the line being written.

const LIST_ITEM = /^([ \t]*)([-*+]|\d+[.)])[ \t]+(?:\[(.)\][ \t]+)?(.*)$/;
const MAX_ROWS = 5;

function indentOf(text, tabSize) {
  let cols = 0;
  for (const ch of text) {
    if (ch === "\t") cols += tabSize - (cols % tabSize);
    else if (ch === " ") cols += 1;
    else break;
  }
  return cols;
}

// List items above `lineNumber` that contain it, outermost first. With `above`, only the ones
// on lines before it (the ones scrolled out of sight).
function ancestorsOf(doc, lineNumber, tabSize, all, above) {
  let text = doc.line(lineNumber).text;
  // a blank line belongs to whatever follows it
  for (let n = lineNumber; !text.trim() && n < doc.lines; ) text = doc.line(++n).text;
  if (!text.trim()) return [];

  let limit = indentOf(text, tabSize);
  const found = [];
  for (let n = lineNumber - 1; n >= 1 && limit > 0; n--) {
    const line = doc.line(n);
    if (!line.text.trim()) continue;
    const indent = indentOf(line.text, tabSize);
    if (indent >= limit) continue;
    const item = line.text.match(LIST_ITEM);
    if (!item) {
      if (indent === 0) break; // an unindented paragraph or heading ends the list
      continue; // continuation text of some other item
    }
    found.unshift({ number: n, from: line.from, to: line.to, indent, marker: item[2], task: item[3], text: item[4] });
    limit = indent;
  }
  if (all) return found;
  // an empty bullet has nothing to show, but it still counted as a level above
  return found.filter((row) => row.text.trim() && (!above || row.number < above)).slice(-MAX_ROWS);
}

// Plain one-line rendering of a bullet's markdown: links keep their colour, syntax is dropped
function renderInline(el, text) {
  const LINK = /!?\[\[([^\]|]+)(?:\|([^\]]*))?\]\]|\[([^\]]*)\]\([^)]*\)/g;
  const plain = (s) => s.replace(/(\*\*|__|==|~~|`|%%)/g, "").replace(/(^|\s)[*_](\S)/g, "$1$2").replace(/(\S)[*_](?=\s|$|[.,;:!?])/g, "$1");
  let last = 0;
  let m;
  while ((m = LINK.exec(text))) {
    if (m.index > last) el.appendText(plain(text.slice(last, m.index)));
    const label = m[3] !== undefined ? m[3] : (m[2] || m[1].split("#")[0] || m[1]).trim();
    el.createSpan({ cls: "sticky-bullets-link", text: label });
    last = m.index + m[0].length;
  }
  if (last < text.length) el.appendText(plain(text.slice(last)));
}

function stickyExtension(plugin) {
  return ViewPlugin.fromClass(
    class {
      constructor(view) {
        this.view = view;
        this.key = "";
        this.rowHeight = 0;
        this.parent = this.findParent(view.state);
        this.decorations = this.build();
        this.el = view.dom.createDiv("sticky-bullets");
        this.el.hide();
        this.onScroll = () => this.schedule();
        view.scrollDOM.addEventListener("scroll", this.onScroll, { passive: true });
        this.schedule();
      }

      update(update) {
        if (update.docChanged || update.selectionSet) {
          this.parent = this.findParent(update.state);
          this.decorations = this.build();
        }
        if (update.docChanged || update.viewportChanged || update.geometryChanged || update.selectionSet || update.focusChanged) this.schedule();
      }

      // The bullet the cursor's line hangs off: its direct parent, or nothing at the top level
      findParent(state) {
        if (!plugin.enabled) return null;
        const line = state.doc.lineAt(state.selection.main.head);
        const chain = ancestorsOf(state.doc, line.number, state.tabSize || 4, true);
        return chain.length ? chain[chain.length - 1] : null;
      }

      build() {
        const builder = new RangeSetBuilder();
        if (this.parent) {
          const { from, to, text } = this.parent;
          builder.add(from, from, Decoration.line({ class: "sticky-bullets-parent" }));
          // the wash hugs the words, not the whole indented row
          if (text.length) builder.add(to - text.length, to, Decoration.mark({ class: "sticky-bullets-parent-text" }));
        }
        return builder.finish();
      }

      destroy() {
        this.view.scrollDOM.removeEventListener("scroll", this.onScroll);
        this.el.remove();
      }

      schedule() {
        this.view.requestMeasure({
          key: this,
          read: (view) => this.measure(view),
          write: (measured) => this.render(measured),
        });
      }

      // First line below `offset` px from the top edge of the scroller
      lineAt(view, offset) {
        const top = view.scrollDOM.getBoundingClientRect().top - view.documentTop + offset;
        if (top <= 0) return 0; // title / properties still on screen
        return view.state.doc.lineAt(view.lineBlockAtHeight(top).from).number;
      }

      // Is the cursor's line inside the visible part of the scroller?
      cursorVisible(view, head) {
        const rect = view.scrollDOM.getBoundingClientRect();
        const top = rect.top - view.documentTop;
        const block = view.lineBlockAt(head);
        return block.bottom > top && block.top < top + rect.height;
      }

      measure(view) {
        if (!plugin.enabled) return { rows: [] };
        const doc = view.state.doc;
        const tabSize = view.state.tabSize || 4;
        const rowHeight = this.rowHeight || view.defaultLineHeight + 4;

        // The pinned rows cover the top of the editor, so the line that matters is the first
        // one below them; settle on a row count that agrees with itself.
        const head = view.state.selection.main.head;
        const cursor = doc.lineAt(head).number;
        const follow = view.hasFocus && this.cursorVisible(view, head);
        let rows = [];
        for (let pass = 0; pass < 3; pass++) {
          const number = this.lineAt(view, rows.length * rowHeight + 2);
          let next = [];
          if (number && follow && cursor >= number) next = ancestorsOf(doc, cursor, tabSize, false, number);
          else if (number) next = ancestorsOf(doc, number, tabSize);
          if (next.length === rows.length && next.every((r, i) => r.number === rows[i].number)) break;
          rows = next;
        }
        if (!rows.length) return { rows };

        // Where each nesting level's text starts, read off list lines that are in the DOM
        const origin = view.dom.getBoundingClientRect().left;
        const starts = new Map();
        view.contentDOM.querySelectorAll(".cm-line.HyperMD-list-line").forEach((el) => {
          let pos;
          try { pos = view.posAtDOM(el); } catch (e) { return; }
          const indent = indentOf(doc.lineAt(pos).text, tabSize);
          if (starts.has(indent)) return;
          const style = getComputedStyle(el);
          starts.set(indent, el.getBoundingClientRect().left - origin + (parseFloat(style.paddingInlineStart) || 0));
        });
        const known = Array.from(starts.entries()).sort((a, b) => a[0] - b[0]);
        const startFor = (indent) => {
          if (starts.has(indent)) return starts.get(indent);
          if (known.length >= 2) {
            const [i0, x0] = known[0];
            const [i1, x1] = known[known.length - 1];
            return x0 + ((indent - i0) * (x1 - x0)) / (i1 - i0);
          }
          const base = view.contentDOM.getBoundingClientRect().left - origin;
          if (known.length === 1) return known[0][1] - ((known[0][0] - indent) / tabSize) * 2.2 * view.defaultCharacterWidth * 2;
          return base + (indent / tabSize + 1) * 2 * view.defaultCharacterWidth;
        };
        const right = view.dom.getBoundingClientRect().right - view.contentDOM.getBoundingClientRect().right;
        const parent = this.parent ? this.parent.number : 0;
        return { rows: rows.map((r) => ({ ...r, x: startFor(r.indent), parent: r.number === parent })), right: Math.max(0, right) };
      }

      render({ rows, right }) {
        const key = rows.map((r) => r.number + ":" + Math.round(r.x) + ":" + r.parent + ":" + (r.task || "") + ":" + r.text).join("\n");
        if (key === this.key) return;
        this.key = key;
        this.el.empty();
        if (!rows.length) {
          this.el.hide();
          return;
        }
        for (const row of rows) {
          const done = row.task !== undefined && row.task !== " ";
          const rowEl = this.el.createDiv("sticky-bullets-row" + (row.parent ? " is-parent" : "") + (done ? " is-checked" : ""));
          rowEl.style.paddingLeft = row.x + "px";
          rowEl.style.paddingRight = right + "px";
          const marker = rowEl.createSpan("sticky-bullets-marker");
          marker.style.left = row.x + "px";
          if (row.task !== undefined) {
            // A task keeps its checkbox while pinned, so it can be ticked from wherever the cursor is
            const box = marker.createEl("input", { type: "checkbox", cls: "task-list-item-checkbox sticky-bullets-checkbox" });
            box.checked = done;
            box.addEventListener("mousedown", (e) => { e.stopPropagation(); e.preventDefault(); });
            box.addEventListener("click", (e) => {
              e.stopPropagation();
              e.preventDefault();
              const line = this.view.state.doc.line(row.number);
              const m = /^([ \t]*(?:[-*+]|\d+[.)])[ \t]+\[)(.)(\])/.exec(line.text);
              if (!m) return;
              const at = line.from + m[1].length;
              this.view.dispatch({ changes: { from: at, to: at + 1, insert: m[2] === " " ? "x" : " " } });
            });
          } else if (/\d/.test(row.marker)) marker.setText(row.marker);
          else marker.createSpan("sticky-bullets-dot");
          renderInline(rowEl.createSpan("sticky-bullets-text"), row.text);
          rowEl.addEventListener("mousedown", (e) => e.preventDefault());
          rowEl.addEventListener("click", () => {
            this.view.dispatch({ selection: { anchor: this.view.state.doc.line(row.number).to }, scrollIntoView: true });
            this.view.focus();
          });
        }
        this.el.show();
        const first = this.el.firstElementChild;
        if (first) this.rowHeight = first.getBoundingClientRect().height;
      }
    },
    { decorations: (value) => value.decorations }
  );
}

module.exports = class StickyBullets extends Plugin {
  async onload() {
    const data = (await this.loadData()) || {};
    this.enabled = data.enabled !== false;
    this.registerEditorExtension(stickyExtension(this));
    this.addCommand({
      id: "toggle",
      name: "Toggle sticky bullets",
      callback: async () => {
        this.enabled = !this.enabled;
        await this.saveData({ enabled: this.enabled });
        // nudge every open editor to re-measure
        this.app.workspace.iterateAllLeaves((leaf) => {
          const cm = leaf.view && leaf.view.editor && leaf.view.editor.cm;
          if (cm) cm.scrollDOM.dispatchEvent(new Event("scroll"));
        });
      },
    });
  }
};
