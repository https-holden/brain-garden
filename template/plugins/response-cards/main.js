const { Plugin, MarkdownView, editorInfoField, setIcon } = require("obsidian");
const { ViewPlugin, Decoration, WidgetType, keymap } = require("@codemirror/view");
const { EditorState, RangeSetBuilder, Prec } = require("@codemirror/state");

// Response cards for question-and-answer notes: a daily brief with a reply under each item, a
// workbook or course with an answer under each question. A note opts in with
// `cssclasses: [workbook]` (Brain Garden's daily notes carry it). Inside it, every item is a task
// item shaped like:
//
//   - [ ] **Question 01.** ...
//
//       **Response:**
//       the answer, any Markdown: paragraphs, bullets, [[links]]
//
// `**Reply:**` works the same as `**Response:**`. That line is the card's caption and every
// indented line after it (up to the next item) is the card's body. The answer stays ordinary
// Markdown rather than a code fence, so links keep working.
//
// Inside the card the editor behaves like a task description box, as if the card's left edge
// were the start of the line:
// - The caption line cannot be edited; the cursor never lands on it (a click on it goes to the
//   body, arrowing up past it goes to the line above the card), and the body always has a line.
// - The indent that keeps the body inside its question is out of reach: the cursor never sits in
//   it, Backspace at the start of a line joins it to the line above (never eating the indent),
//   and no deletion removes it.
// - Enter starts a new line in the card (twice for a paragraph: the blank line keeps the indent),
//   Enter on an empty bullet ends the list inside the card, Tab/Shift-Tab indent bullets inside
//   the card but Shift-Tab never takes a line out of it, Cmd+A selects the card (again for the
//   whole note), and a multi-line paste is re-indented into the card.
//
// Each question also gets one continuous thread line from under its checkbox to the end of its
// answer (Obsidian's own indent guide breaks at every blank line), with the card's accent edge on
// top of it. Ticked questions are collapsed by default: every time the note is opened (or switched
// into the editor) each ticked question is folded, and ticking one folds it. One unfolded by hand
// stays open while the note is open. Reading view has no fold for a list item without a nested
// list, so there each question gets its own toggle, collapsed when ticked.

const CSSCLASSES = ["workbook"];
const LABEL = /^([ \t]+)\*\*(?:Response|Reply):\*\*/;
const TASK = /^- \[( |x|X)\] (.*)$/;
const BULLET = /^[ \t]*([-*+]|\d+[.)])( \[.\])?[ \t]+/;

const leading = (t) => /^[ \t]*/.exec(t)[0].length;

// Drawn in place of the indent on a body line that holds nothing else. Obsidian renders the
// indent's spaces at their natural width there (there is no text after them to push the cursor
// to the text column), so the cursor sat next to the card's edge; this is one list indent wide.
class IndentWidget extends WidgetType {
  eq() { return true; }
  toDOM() { return createSpan({ cls: "response-card-indent" }); }
  ignoreEvent() { return false; }
}
const indentWidget = Decoration.replace({ widget: new IndentWidget() });

// Cards in a document: [{ start, end, indent }], 0-based line numbers; `start` is the caption line.
// An empty line only belongs to the card when more card follows it; a line holding just the
// card's indent always does (that is the paragraph break Enter makes inside a card).
function findCards(getLine, count) {
  const cards = [];
  for (let i = 0; i < count; i++) {
    const m = LABEL.exec(getLine(i));
    if (!m) continue;
    const indent = m[1];
    let last = i;
    for (let j = i + 1; j < count; j++) {
      const t = getLine(j);
      if (t === "") continue;
      if (leading(t) < indent.length || LABEL.test(t)) break;
      last = j;
    }
    cards.push({ start: i, end: last, indent });
    i = last;
  }
  return cards;
}

// Question items: [{ head, end }], the task line and the last indented line of its body.
function findItems(getLine, count) {
  const items = [];
  for (let i = 0; i < count; i++) {
    if (!TASK.test(getLine(i))) continue;
    let last = i;
    for (let j = i + 1; j < count; j++) {
      const t = getLine(j);
      if (t === "") continue;
      if (leading(t) === 0) break;
      last = j;
    }
    if (last > i) items.push({ head: i, end: last });
    i = last;
  }
  return items;
}

const cardCache = new WeakMap(); // Text -> cards
function cardsOf(doc) {
  let cards = cardCache.get(doc);
  if (!cards) {
    cards = findCards((i) => doc.line(i + 1).text, doc.lines);
    cardCache.set(doc, cards);
  }
  return cards;
}

// The card containing 0-based line `n`, or null.
function cardAt(doc, n) {
  return cardsOf(doc).find((c) => n >= c.start && n <= c.end) || null;
}

// Where the text of a body line starts: after the card's indent (or after less, if the line has less).
function bodyStart(line, card) {
  return line.from + Math.min(card.indent.length, leading(line.text));
}

module.exports = class ResponseCards extends Plugin {
  onload() {
    const plugin = this;
    const scopedState = (state) => {
      const info = state.field(editorInfoField, false);
      return plugin.scoped(info && info.file);
    };

    // Editor: line classes for the thread and the card; the stylesheet draws both from those.
    let lang = null;
    try { lang = require("@codemirror/language"); } catch (e) { /* no folding info: thread head always drawn */ }
    const folds = (state) => (lang ? lang.foldedRanges(state) : null);
    const cardLines = ViewPlugin.fromClass(class {
      constructor(view) { this.decorations = this.build(view); }
      update(u) {
        if (u.docChanged || u.viewportChanged || folds(u.state) !== folds(u.startState)) this.decorations = this.build(u.view);
      }
      build(view) {
        if (!scopedState(view.state)) return Decoration.none;
        const doc = view.state.doc;
        const text = (i) => doc.line(i + 1).text;
        const classes = new Map(); // 0-based line -> class names
        const add = (i, c) => { if (!classes.has(i)) classes.set(i, []); classes.get(i).push(c); };
        const folded = folds(view.state);
        for (const it of findItems(text, doc.lines)) {
          let open = true;
          if (folded) folded.between(doc.line(it.head + 1).to, doc.line(it.head + 1).to + 1, () => { open = false; });
          if (open) add(it.head, "response-thread-head");
          for (let i = it.head + 1; i <= it.end; i++) add(i, "response-thread");
        }
        for (const c of cardsOf(doc)) {
          for (let i = c.start; i <= c.end; i++) {
            add(i, "response-card");
            if (i === c.start) add(i, "response-card-first");
            if (i === c.end) add(i, "response-card-last");
          }
        }
        const builder = new RangeSetBuilder();
        for (const i of [...classes.keys()].sort((a, b) => a - b)) {
          const from = doc.line(i + 1).from;
          builder.add(from, from, Decoration.line({ class: classes.get(i).join(" ") }));
        }
        return builder.finish();
      }
    }, { decorations: (v) => v.decorations });

    // Editor: indent-only body lines draw their indent at full width (see IndentWidget).
    const emptyLines = ViewPlugin.fromClass(class {
      constructor(view) { this.decorations = this.build(view); }
      update(u) { if (u.docChanged || u.viewportChanged) this.decorations = this.build(u.view); }
      build(view) {
        if (!scopedState(view.state)) return Decoration.none;
        const doc = view.state.doc;
        const builder = new RangeSetBuilder();
        for (const c of cardsOf(doc)) {
          for (let i = c.start + 1; i <= c.end; i++) {
            const line = doc.line(i + 1);
            if (line.text.length >= c.indent.length && line.text.trim() === "") {
              builder.add(line.from, line.from + c.indent.length, indentWidget);
            }
          }
        }
        return builder.finish();
      }
    }, { decorations: (v) => v.decorations });

    // Where the cursor may rest, and what may be deleted, inside a card.
    const guard = EditorState.transactionFilter.of((tr) => {
      if (!scopedState(tr.startState)) return tr;
      if (tr.docChanged && tr.isUserEvent("delete")) return plugin.guardDelete(tr) || tr;
      if (!tr.selection) return tr;
      const fix = plugin.placeCursor(tr);
      return fix ? [tr, { ...fix, sequential: true }] : tr;
    });

    this.registerEditorExtension([
      cardLines,
      emptyLines,
      guard,
      Prec.highest(keymap.of([
        { key: "Enter", run: (cm) => this.enter(cm) },
        { key: "Backspace", run: (cm) => this.backspace(cm) },
        { key: "Delete", run: (cm) => this.del(cm) },
        { key: "Mod-a", run: (cm) => this.selectCard(cm) },
        { key: "Tab", run: (cm) => this.indent(cm, 1) },
        { key: "Shift-Tab", run: (cm) => this.indent(cm, -1) },
      ])),
    ]);

    this.registerEvent(this.app.workspace.on("editor-paste", (evt, editor, info) => this.onPaste(evt, editor, info)));

    // Folding ticked questions: all of them when the note opens, then each one as it is ticked.
    this.foldedOnce = new Map(); // file path -> Set of question texts already auto-folded
    this.unfolded = new Map(); // file path -> Set of question texts opened by hand in reading view
    this.modes = new WeakMap(); // leaf -> last view mode, to catch a switch into the editor
    const reopen = () => {
      const view = this.app.workspace.getActiveViewOfType(MarkdownView);
      if (!view || !view.file) return;
      this.modes.set(view.leaf, view.getMode());
      this.foldedOnce.delete(view.file.path);
      this.queueFold(view.editor, view);
    };
    this.registerEvent(this.app.workspace.on("editor-change", (editor, info) => this.queueFold(editor, info)));
    this.registerEvent(this.app.workspace.on("file-open", (file) => {
      if (file) this.unfolded.delete(file.path);
      reopen();
    }));
    this.registerEvent(this.app.workspace.on("layout-change", () => {
      const view = this.app.workspace.getActiveViewOfType(MarkdownView);
      if (view && view.getMode() !== this.modes.get(view.leaf)) reopen();
    }));

    // Reading view: wrap the Response (or Reply) paragraph and what follows it in the list item in a div.
    this.registerMarkdownPostProcessor((el, ctx) => {
      if (!this.hasClass(ctx.frontmatter)) return;
      for (const p of el.querySelectorAll("li > p")) {
        const strong = p.querySelector(":scope > strong");
        const label = strong && strong.textContent.trim();
        if ((label !== "Response:" && label !== "Reply:") || p.textContent.trim().indexOf(label) !== 0) continue;
        const card = createDiv({ cls: "response-card-block" });
        p.before(card);
        let node = p;
        while (node) {
          const next = node.nextSibling;
          card.appendChild(node);
          node = next;
        }
      }
      for (const li of el.querySelectorAll("li.task-list-item")) this.addToggle(li, ctx.sourcePath);
    });
  }

  hasClass(fm) {
    const v = fm && fm.cssclasses;
    return [].concat(v || []).some((c) => String(c).split(/\s+/).some((x) => CSSCLASSES.includes(x)));
  }

  scoped(file) {
    return !!(file && this.hasClass(this.app.metadataCache.getFileCache(file)?.frontmatter));
  }

  // A cursor that would land on the caption line, inside the indent, or on an empty body line is
  // moved (and the body line created, or indented, when needed). Returns a follow-up spec or null.
  placeCursor(tr) {
    const sel = tr.newSelection;
    if (sel.ranges.length > 1 || !sel.main.empty) return null;
    const doc = tr.newDoc;
    const head = sel.main.head;
    const line = doc.lineAt(head);
    const n = line.number - 1;
    const card = cardAt(doc, n);
    if (!card) return null;
    const ind = card.indent;
    const before = tr.changes.mapPos(tr.startState.selection.main.head);
    const fromBelow = !tr.isUserEvent("select.pointer") && before > line.to;

    if (n === card.start) {
      if (fromBelow) return { selection: { anchor: n > 0 ? doc.line(n).to : 0 } }; // line above the card
      if (card.end > card.start) {
        const body = doc.line(n + 2);
        if (body.text === "") return { changes: { from: body.from, insert: ind }, selection: { anchor: body.from + ind.length } };
        return { selection: { anchor: bodyStart(body, card) } };
      }
      return { changes: { from: line.to, insert: "\n" + ind }, selection: { anchor: line.to + 1 + ind.length } };
    }
    if (line.text === "") return { changes: { from: line.from, insert: ind }, selection: { anchor: line.from + ind.length } };
    const start = bodyStart(line, card);
    if (head >= start) return null;
    // Moving left from the start of a body line goes to the end of the line above, if that is body.
    if (before === start && n - 1 > card.start && !tr.isUserEvent("select.pointer")) return { selection: { anchor: doc.line(n).to } };
    return { selection: { anchor: start } };
  }

  // A deletion that would eat a body line's indent or touch the caption line is narrowed to the
  // text, or dropped. Returns a replacement spec, [] to cancel, or null to let it through.
  guardDelete(tr) {
    const doc = tr.startState.doc;
    let spec = null;
    let count = 0;
    tr.changes.iterChanges((fromA, toA, _fromB, _toB, inserted) => { count++; spec = { from: fromA, to: toA, insert: inserted.toString() }; });
    if (count !== 1 || spec.insert) return null;
    const a = doc.lineAt(spec.from);
    const b = doc.lineAt(spec.to);
    const cardA = cardAt(doc, a.number - 1);
    const cardB = cardAt(doc, b.number - 1);
    if (!cardA && !cardB) return null;
    const card = cardB || cardA;
    // Whole card or more selected and deleted: fine.
    if (spec.from <= doc.line(card.start + 1).from && spec.to >= doc.line(card.end + 1).to) return null;
    const caption = doc.line(card.start + 1);
    if (spec.from <= caption.to && spec.to >= caption.from) return []; // the caption stays as it is
    if (a.number !== b.number) return null; // joins are handled by the keys, anything else passes
    const start = bodyStart(a, card);
    if (spec.to <= start) return [];
    if (spec.from >= start) return null;
    return { changes: { from: start, to: spec.to }, selection: { anchor: start }, userEvent: "delete" };
  }

  // { card, line, sel, doc } when the cursor is on a body line of a card in a scoped note.
  context(cm) {
    const state = cm.state;
    const info = state.field(editorInfoField, false);
    if (!this.scoped(info && info.file)) return null;
    const sel = state.selection.main;
    const line = state.doc.lineAt(sel.head);
    const card = cardAt(state.doc, line.number - 1);
    if (!card || line.number - 1 === card.start) return null;
    return { card, line, sel, doc: state.doc };
  }

  enter(cm) {
    const ctx = this.context(cm);
    if (!ctx) return false;
    const { card, line, sel } = ctx;
    const bullet = BULLET.exec(line.text);
    if (bullet && leading(line.text) >= card.indent.length) {
      if (line.text.slice(bullet[0].length).trim() !== "" || !sel.empty) return false; // Obsidian continues the list
      // An empty bullet: a nested one outdents a level, a first-level one ends the list but stays
      // in the card (Obsidian would turn it into a new question). The blank line keeps the next
      // paragraph from being read as part of the last bullet.
      if (leading(line.text) > card.indent.length) return this.indent(cm, -1);
      const insert = card.indent + "\n" + card.indent;
      cm.dispatch({ changes: { from: line.from, to: line.to, insert }, selection: { anchor: line.from + insert.length }, scrollIntoView: true, userEvent: "input" });
      return true;
    }
    const insert = "\n" + card.indent;
    cm.dispatch({ changes: { from: sel.from, to: sel.to, insert }, selection: { anchor: sel.from + insert.length }, scrollIntoView: true, userEvent: "input" });
    return true;
  }

  // Backspace at the start of a body line joins it to the line above; on the first body line it
  // does nothing (the caption is not editable).
  backspace(cm) {
    const ctx = this.context(cm);
    if (!ctx) return false;
    const { card, line, sel, doc } = ctx;
    if (!sel.empty || sel.head !== bodyStart(line, card)) return false;
    if (line.number - 2 === card.start) return true;
    const prev = doc.line(line.number - 1);
    cm.dispatch({ changes: { from: prev.to, to: sel.head }, selection: { anchor: prev.to }, scrollIntoView: true, userEvent: "delete.backward" });
    return true;
  }

  // Delete at the end of a body line pulls the next body line up without its indent; at the end
  // of the card it does nothing.
  del(cm) {
    const ctx = this.context(cm);
    if (!ctx) return false;
    const { card, line, sel, doc } = ctx;
    if (!sel.empty || sel.head !== line.to) return false;
    if (line.number - 1 >= card.end) return true;
    const next = doc.line(line.number + 1);
    cm.dispatch({ changes: { from: line.to, to: bodyStart(next, card) }, scrollIntoView: true, userEvent: "delete.forward" });
    return true;
  }

  // Cmd+A selects the card's body; pressed again, the whole note.
  selectCard(cm) {
    const ctx = this.context(cm);
    if (!ctx) return false;
    const { card, sel, doc } = ctx;
    const from = bodyStart(doc.line(card.start + 2), card);
    const to = doc.line(card.end + 1).to;
    if (sel.from === from && sel.to === to) return false;
    cm.dispatch({ selection: { anchor: from, head: to }, scrollIntoView: true });
    return true;
  }

  // Tab / Shift-Tab on bullet lines add or remove one level of indentation right after the card's
  // own indent, so nesting works inside the card and nothing is ever outdented out of it.
  // (Obsidian's own Tab puts the new indent at the very start of the line, in front of the card's.)
  // On other lines Tab does nothing: an indented paragraph would turn into a code block.
  indent(cm, dir) {
    const ctx = this.context(cm);
    if (!ctx) return false;
    const { card, doc } = ctx;
    const sel = cm.state.selection.main;
    const unit = this.app.vault.getConfig("useTab") === false ? " ".repeat(this.app.vault.getConfig("tabSize") || 4) : "\t";
    const changes = [];
    for (let n = doc.lineAt(sel.from).number; n <= doc.lineAt(sel.to).number; n++) {
      const line = doc.line(n);
      if (n - 1 < card.start + 1 || n - 1 > card.end || !BULLET.test(line.text)) continue;
      const at = bodyStart(line, card);
      if (dir > 0) { changes.push({ from: at, insert: unit }); continue; }
      const extra = /^[ \t]*/.exec(line.text.slice(at - line.from))[0];
      const drop = extra.startsWith("\t") ? 1 : Math.min(extra.length, (this.app.vault.getConfig("tabSize") || 4));
      if (drop) changes.push({ from: at, to: at + drop });
    }
    if (!changes.length) return true;
    const set = cm.state.changes(changes);
    cm.dispatch({ changes: set, selection: cm.state.selection.map(set, 1), scrollIntoView: true, userEvent: dir > 0 ? "input.indent" : "delete.dedent" });
    return true;
  }

  onPaste(evt, editor, info) {
    if (evt.defaultPrevented || !this.scoped(info && info.file)) return;
    const from = editor.getCursor("from");
    const card = cardAt(editor.cm.state.doc, from.line);
    if (!card || from.line === card.start) return;
    const raw = evt.clipboardData && evt.clipboardData.getData("text/plain");
    if (!raw || !raw.includes("\n")) return;
    evt.preventDefault();
    const lines = raw.replace(/\r\n?/g, "\n").replace(/\n+$/, "").split("\n");
    const nonEmpty = lines.filter((l) => l.trim());
    const common = nonEmpty.length ? Math.min(...nonEmpty.map((l) => leading(l))) : 0;
    const body = lines.map((l) => (l.trim() ? l.slice(common) : ""));
    const rest = body.slice(1).map((l) => card.indent + l);
    editor.replaceRange([body[0], ...rest].join("\n"), from, editor.getCursor("to"));
  }

  // Reading view: a fold toggle on a question that has a body, collapsed while it is ticked unless
  // opened by hand since the note was opened. Obsidian's own toggle only appears on list items
  // with a nested list (and would fold only that list), so it is replaced.
  addToggle(li, path) {
    const content = [...li.children].filter((c) => !c.matches(".list-bullet, .list-collapse-indicator"));
    if (content.length < 2) return;
    li.querySelectorAll(":scope > .list-collapse-indicator").forEach((c) => c.remove());
    for (const c of content.slice(1)) c.addClass("response-fold-body");
    const key = content[0].textContent.trim();
    const open = this.unfolded.get(path);
    const toggle = createSpan({ cls: "collapse-icon response-fold-toggle" });
    setIcon(toggle, "right-triangle");
    li.prepend(toggle);
    const set = (folded) => {
      li.toggleClass("response-folded", folded);
      toggle.toggleClass("is-collapsed", folded);
    };
    set(li.hasClass("is-checked") && !(open && open.has(key)));
    toggle.addEventListener("click", (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      const folded = !li.hasClass("response-folded");
      set(folded);
      if (!this.unfolded.has(path)) this.unfolded.set(path, new Set());
      if (folded) this.unfolded.get(path).delete(key);
      else this.unfolded.get(path).add(key);
    });
  }

  queueFold(editor, info) {
    if (!this.scoped(info && info.file)) return;
    const path = info.file.path; // read now: by the time the timer fires the view may show no file
    clearTimeout(this.foldTimer);
    this.foldTimer = setTimeout(() => this.foldTicked(editor, path), 250);
  }

  foldTicked(editor, path) {
    let lang;
    try { lang = require("@codemirror/language"); } catch (e) { return; }
    const view = editor.cm;
    if (!view || !lang.foldEffect) return;
    let seen = this.foldedOnce.get(path);
    if (!seen) { seen = new Set(); this.foldedOnce.set(path, seen); }
    const n = editor.lineCount();
    const folded = lang.foldedRanges(view.state);
    const indented = (i) => i < n && /^[ \t]/.test(editor.getLine(i));
    const effects = [];
    let selection = null;
    for (let i = 0; i < n; i++) {
      const m = TASK.exec(editor.getLine(i));
      if (!m) continue;
      const key = m[2].trim();
      if (m[1] === " ") { seen.delete(key); continue; }
      if (seen.has(key)) continue;
      seen.add(key);
      let j = i + 1;
      while (indented(j) || (j < n && editor.getLine(j).trim() === "" && indented(j + 1))) j++;
      if (j === i + 1) continue;
      const from = view.state.doc.line(i + 1).to;
      const to = view.state.doc.line(j).to;
      let already = false;
      folded.between(from, to, () => { already = true; });
      if (already) continue;
      effects.push(lang.foldEffect.of({ from, to }));
      const head = view.state.selection.main.head;
      if (head > from && head <= to) selection = { anchor: from };
    }
    if (effects.length) view.dispatch(selection ? { effects, selection } : { effects });
  }
};
