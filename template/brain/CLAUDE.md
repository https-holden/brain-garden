# @@VAULT_NAME@@

An Obsidian vault at @@VAULT_PATH@@: a second brain for @@PROJECT@@. Kepano method: few
folders, a `categories` property with `[[links]]` for topics, one template and one Base per
kind, one page per topic in `Categories/`. Planted @@DATE@@ from
Brain Garden.

Root documents: this file holds the operating rules, `Readme.md` is the human guide,
`Decisions.md` is the dated log of why the rules are what they are, `Home.md` is the hub.
Rules here are decisions, not laws; @@OWNER@@ changes any of them in a sentence, and the
change is recorded in `Decisions.md` in the same session.

## How Claude works here

- The structure is a starting point, not scripture. It grows where real work keeps producing
  a note with no home and prunes what sits unused. Reach for the smallest change that works:
  a topic page first, then a property, then a Base view, and only then a new kind (a folder,
  a template, a Base, and a row in both tables below).
- Approval is by numbered list. @@OWNER@@ skips or edits by number, the rest is applied. Git
  is the undo.
- When you notice drift between this file and the vault, propose the smallest edit to the
  wrong one in the same session. Never silently adapt and leave the doc behind.
- @@MEMORY_RULE@@
@@ME_RULE@@- Load the matching skill before doing the work: `obsidian:obsidian-markdown` before writing
  or restructuring any note, `obsidian:obsidian-bases` before touching a `.base`,
  `obsidian:obsidian-cli` when something must happen in the running app,
  `obsidian:json-canvas` for `.canvas` files, `obsidian:defuddle` to turn a web page into a
  clipping. `kepano-method` (project skill in `.claude/skills/`) is the why behind the
  structure, for audits and "is this the kepano way" questions, not for syntax.

## Looking things up: the one recipe

Every question uses this order, stopping early when the answer is clear:

1. `ls` the kind folders. Filenames are claims, imperatives and names, so the listing is the
   index. Match on words from the ask.
2. Frontmatter grep: `categories` for the topic, then any property the ask names.
3. Full text grep on distinctive strings.

Read matching notes whole; they are small. When two disagree, the later `source` date wins and
the answer says how old the evidence is. Exclude `status: stale` from results; a stale note is
cited only to warn that an answer may have changed. `verified` can be stated, `draft` must be
hedged.

Before creating a note, grep the filenames for the key noun and show near matches. A second
note about the same thing becomes an edit to the first, never a sibling.

## Vault map

Folders say what a note *is*; `categories` says what it is *about*.

| Path | Holds | Not |
|---|---|---|
| `Home.md`, `Readme.md`, `Decisions.md`, `CLAUDE.md` | Hub, human guide, decision log, rules. | Content. |
@@ME_ROW@@@@NOW_ROW@@@@MAP_ROWS@@
| `Categories/` | One page per topic in use: `tags: [categories]`, one paragraph, `![[Topics.base#In this topic]]`. Every link here must resolve. | Topics with no notes yet. |
| `Templates/`, `Templates/Bases/` | One template and one Base per kind, plus the general Bases (`Everything`, `Topics`, `Related`, `Backlinks`, `Attachments`). Core `{{date}}` syntax only. | Templater syntax. |
| `Attachments/` | Every file, flat. | Subfolders. |
| `bin/` | `lint.py` (the drift check) and its `vault.json`@@BIN_EXTRA@@. Re-runnable maintenance scripts. | Secrets, logs in git. |
| `.obsidian/` | Tracked config, the `vault.css` snippet, any home-made plugins. Document a new plugin in `Readme.md`. | Content. |

## Kinds in use

| Kind | Template | Base | Properties | Title is |
|---|---|---|---|---|
@@KIND_ROWS@@

Adding a kind (the loop): check first that it is not just a `type` value or a view on an
existing kind. If it really is new: the folder, `Templates/<Kind> Template.md` carrying every
property its Base will show, `Templates/Bases/<Kind>.base` filtered on `file.inFolder()`, an
entry in `bin/vault.json` so the lint knows it, a row in both tables above, a paragraph in
`Readme.md`, and a line in `Decisions.md`.

@@EXTRA_SECTIONS@@## Keeping the documentation honest

`python3 @@VAULT_PREFIX@@bin/lint.py` is the deterministic drift check; its docstring lists
every check. **The schema comes from the templates, so a template edit is a schema edit.** Run
it before any commit that touches more than one note. Errors block the commit; warnings are
reported.

## Conventions

- No en dashes (U+2013) or em dashes (U+2014) anywhere in vault content, including titles,
  filenames, properties and imported text. Replace on import.
- Every note carries `categories:` as a YAML list of `"[[Topic]]"` links and
  `created: YYYY-MM-DD`. Dates are always `YYYY-MM-DD`, never relative.
- A topic gets a page in `Categories/` when its first note exists, not before.
- `status` where a kind has it: automation creates `draft`. Only @@OWNER@@, or their explicit
  confirmation, moves a note to `verified`. A contradicted note becomes `stale`; rewrite or
  delete it, never quote it.
- `source` answers where and when a claim was read: a link or path plus the date. Provenance
  is never invented; an unknown source is written as "source unknown" and the claim is hedged.
- One idea per note. If a note argues two things, it is two notes.
- Link the first mention of any person, project or topic. Unresolved links are breadcrumbs,
  except in `Categories/`.
- Renames go through `obsidian rename` / `obsidian move` so links update, or the renamer greps
  every inbound `[[link]]` and fixes it in the same commit. Never a bare `mv`.
- `modified` means "last edited by hand". Automation never sets or bumps it.
- Text a script imports sits between `<!-- name:start -->` and `<!-- name:end -->` markers and
  a re-import rewrites only that region; anything written by hand goes outside them.
- Never mix core `{{date}}` and Templater `<% %>` in one template.
- Bases use current syntax (`filters`, `formulas`, `properties`, `views`). Guard a list
  property that may be missing (`note.x.isEmpty() || ...`): a filter on a missing property is
  false and silently drops the note.
- Corrections are appended and dated, never edited over the original.
