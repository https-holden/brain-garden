# Rules

The detail behind `CLAUDE.md`, binding like `CLAUDE.md`: where each kind of note goes, what it
carries, and the conventions every note follows. `CLAUDE.md` says when to read it.

## Vault map

Folders say what a note *is*; `categories` says what it is *about*.

| Path | Holds | Not |
|---|---|---|
| `Home.md`, `Readme.md`, `Decisions.md`, `CLAUDE.md`, `Rules.md` | Hub, human guide, decision log, what a session loads first, the detail it reads before writing. | Content. |
@@ME_ROW@@@@NOW_ROW@@@@MAP_ROWS@@
| `Categories/` | One page per topic in use: `tags: [categories]`, a `## Start here` of plain links, `![[Topics.base#In this topic]]`. Every link here must resolve. | Topics with no notes yet. |
| `Templates/`, `Templates/Bases/` | One template and one Base per kind, plus the general Bases (`Everything`, `Topics`, `Related`, `Backlinks`, `Attachments`). Core `{{date}}` syntax only. | Templater syntax. |
| `Attachments/` | Every file, flat. | Subfolders. |
| `bin/` | `lint.py` (the drift check) and its `vault.json` (kinds, budgets), `find.py` (step 1 of the recipe)@@BIN_EXTRA@@. Re-runnable maintenance scripts. | Secrets, logs in git. |
| `.obsidian/` | Tracked config, the `vault.css` snippet, any home-made plugins. Document a new plugin in `Readme.md`. | Content. |
| `.paths/` | `index.txt`: one line per note, kept current by `bin/find.py` and committed; `find.py --all` prints it for a chat AI. `find.log`: every lookup, kept on this machine. | Hand edits. |

## Kinds in use

| Kind | Template | Base | Properties | Title is |
|---|---|---|---|---|
@@KIND_ROWS@@

## Adding a kind

The loop: check first that it is not just a `type` value or a view on an existing kind. If it
really is new: the folder, `Templates/<Kind> Template.md` carrying every property its Base will
show, `Templates/Bases/<Kind>.base` filtered on `file.inFolder()`, an entry in `bin/vault.json`
so the lint knows it, a row in both tables above, a paragraph in `Readme.md`, and a line in
`Decisions.md`.

## Hubs

A hub is `Home.md` or a page in `Categories/`: where a person or an AI lands first. Each reads
as plain text: `## Start here` sits above its Base embeds and holds 3 to 7 plain `[[links]]`,
hand-picked, to the notes worth opening first. A new topic page has the heading and no links;
Home's list names the main topics. The monthly pass, `tend`, adds each note its Pave step
checks and shortens to its topic's "Start here". The full list stays the Base for people and
`find.py --topic` for an AI: no generated list is ever written into a hub. The lint warns on a
topic page three notes use with no link, and on Home with three topic pages and none linked.

@@EXTRA_SECTIONS@@## Keeping the documentation honest

`python3 @@VAULT_PREFIX@@bin/lint.py` is the deterministic drift check; its docstring lists
every check. **The schema comes from the templates, so a template edit is a schema edit.** Run
it before any commit that touches more than one note. Errors block the commit; warnings are
reported.

Every file a session loads without asking (`CLAUDE.md`, `Me.md`, `Now.md`, each skill's
`SKILL.md`), and this one, has a size budget in characters under `budgets` in `bin/vault.json`.
The lint warns when one is over. Compact it then to about 75% of its budget, keeping every
fact: move detail out to a note or a skill's `references/` and leave a pointer. A path such as
`.claude/skills/pdf/SKILL.md` in that table gives one skill its own budget.

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
