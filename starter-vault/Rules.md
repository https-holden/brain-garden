# Rules

The detail behind `CLAUDE.md`, binding like `CLAUDE.md`: where each kind of note goes, what it
carries, and the conventions every note follows. `CLAUDE.md` says when to read it.

## Vault map

Folders say what a note *is*; `categories` says what it is *about*.

| Path | Holds | Not |
|---|---|---|
| `Home.md`, `Readme.md`, `Decisions.md`, `CLAUDE.md`, `Rules.md` | Hub, human guide, decision log, what a session loads first, the detail it reads before writing. | Content. |
| `Me.md` | Who the owner is, for any AI: purpose, sources, tools, what is private. | Content. |
| `Sources.md` | Where material comes from: how, cadence, last pulled, keep or not. | Notes. |
| `Now.md` | Working memory: what is in flight, every bullet dated. | Facts (they become notes), history. |
| `Notes/` | Anything authored that is not another kind: essays, evergreen ideas, working notes. | Things other people wrote (those are clippings). |
| `References/` | Things that exist outside your head: books, tools, places, organisations. | Dated, authored writing. |
| `People/` | One note per person: who they are, their role, one line. | Private details, anything they would not want written down. |
| `Clippings/` | Things other people wrote, as clean Markdown (`obsidian:defuddle` or the Web Clipper). | Anything authored here. The folder is the divider between your writing and ingested text. |
| `Daily/` | `YYYY-MM-DD`, the raw log of one day. Never rewritten after the day. | Knowledge (copy it out to its own note and link back). |
| `Categories/` | One page per topic in use: `tags: [categories]`, a `## Start here` of plain links, `![[Topics.base#In this topic]]`. Every link here must resolve. | Topics with no notes yet. |
| `Templates/`, `Templates/Bases/` | One template and one Base per kind, plus the general Bases (`Everything`, `Topics`, `Related`, `Backlinks`, `Attachments`). Core `{{date}}` syntax only. | Templater syntax. |
| `Attachments/` | Every file, flat. | Subfolders. |
| `bin/` | `lint.py` (the drift check) and its `vault.json` (kinds, budgets, beds), `find.py` (step 1 of the recipe), `beds.py` (sends notes to beds), `ingest.py` (bring things in), `librarian.py` and `librarian.md` (file them). Re-runnable maintenance scripts. | Secrets, logs in git. |
| `.obsidian/` | Tracked config, the `vault.css` snippet, any home-made plugins. Document a new plugin in `Readme.md`. | Content. |
| `.paths/` | `index.txt`: one line per note, kept current by `bin/find.py` and committed; `find.py --all` prints it for a chat AI. `find.log`: every lookup, kept on this machine. | Hand edits. |

## Kinds in use

| Kind | Template | Base | Properties | Title is |
|---|---|---|---|---|
| Notes | Note Template | Notes.base | `categories`, `created`, `topics` | for an idea, the idea as a claim; otherwise a plain name |
| References | Reference Template | References.base | `categories`, `created`, `author`, `url`, `rating` | the thing's own title, exactly |
| People | Person Template | People.base | `categories`, `created`, `org`, `role`, `source` | the person's name, never a role (qualify in parentheses when two share one) |
| Clippings | Clipping Template | Clippings.base | `categories`, `author`, `url`, `created`, `published` | the page's own title |
| Daily | Daily Note Template | Daily.base | `tags`, `cssclasses` | `YYYY-MM-DD` |

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

## Bringing things in

The folder is the divider between the owner's writing and everything brought in: whatever
someone else wrote lives in `Clippings/` and nowhere else, and nothing ingested is ever
written into one of the owner's notes.

- `python3 bin/ingest.py add <files, folders or URLs>` brings things into
  `Clippings/`; `--mine` brings in the owner's own writing (an old journal, an export from
  another app) to `Notes/`, and its words are never rewritten. `--links <file>`
  takes one URL per line. The script's docstring lists what it reads.
- Imported text sits between `<!-- ingest:start -->` and `<!-- ingest:end -->`. Anything
  below the end marker is the owner's, and nothing rewrites it.
- An imported note has `ingested: YYYY-MM-DD` and no `filed:` until it is filed.
  `bin/ingest.py waiting` lists those.
- Filing follows `bin/librarian.md`, whoever does it: this session (the `file-clippings`
  skill), the background run (`bin/librarian.py`, Claude Code on the owner's subscription,
  boxed in to the waiting notes), or a chat AI (`bin/librarian.py --paste`, then `--apply`).
- Big exports from another app go through Obsidian's Importer plugin into a scratch folder,
  then `ingest.py add --mine` on that folder.
- An existing Obsidian vault is one more source: `ingest.py add --vault <folder>` writes
  nothing and proposes a numbered folder-to-kind mapping; agree it with the owner, then run it
  with `--map "Folder=Kind"` flags, `--sample 10` first. Its own `CLAUDE.md` or `AGENTS.md` is
  never imported: propose its rules for `Decisions.md` and `Me.md` as a numbered list.
- `Sources.md` is the inventory of where material comes from: how, cadence, last pulled, and
  whether it is worth keeping. Pass `--via "<Source>"` on every `add`, so the note records
  where it came from and the row's Last pulled is stamped. The `harvest` skill builds the
  inventory with the owner (interview, then a sample of about ten, then the backfill); never
  bulk-import before a sample has been filed and looked at.
- `ingest.py report` is the pruning list: unused clippings, notes waiting too long, old
  drafts, stale notes, thin topics, quiet people, duplicates, unused attachments, sources due,
  and how much of each source gets used. The `prune` skill turns it into one numbered list,
  monthly. `ingest.py trash` is the only way anything is removed, it only moves clippings and
  attachments that nothing links, to `.trash/`, and the owner's own notes are never removed
  by a session.

## The daily loop

Three skills keep the three memory tiers moving. The morning and evening ones read connected
tools read only; `run-brief` acts only on what the owner replied:

- `start-of-day` (morning): reads `Now.md`, yesterday's note and today's calendar, email and
  chat if connected, and writes the `## Brief` checklist into `Daily/YYYY-MM-DD.md`. Each item
  is sorted Green (Claude can just do it), Yellow (Claude offers lettered options) or Red
  (new, or not undoable: Claude will not guess), and gets an indented `**Reply:**` card.
- `run-brief` (any time, "run my replies"): does only the items whose card has a reply (`go`,
  a letter, or a short instruction), writes a `Ran HH:MM:` line under each, and logs every
  action under `## Actions`. Items without a reply wait for tomorrow and are never chased.
- `end-of-day` (evening): reads the day's ticks, replies, notes and `## Actions`, proposes new
  or corrected notes as one numbered list, writes `## Learned`, rewrites `Now.md`, runs the
  lint.

A daily note is never rewritten after its day, except its `## Learned` that evening. Reply
cards are the owner's: only `run-brief` writes in them, and only its `Ran` lines.

## Keeping the documentation honest

`python3 bin/lint.py` is the deterministic drift check; its docstring lists
every check. **The schema comes from the templates, so a template edit is a schema edit.** Run
it before any commit that touches more than one note. Errors block the commit; warnings are
reported.

Every file a session loads without asking (`CLAUDE.md`, `Me.md`, `Now.md`, each skill's
`SKILL.md`), and this one, has a size budget in characters under `budgets` in `bin/vault.json`.
The lint warns when one is over. Compact it then to about 75% of its budget, keeping every
fact: move detail out to a note or a skill's `references/` and leave a pointer. A path such as
`.claude/skills/pdf/SKILL.md` in that table gives one skill its own budget.

## Beds

A bed is a sibling git repository holding the part of this brain that others may see, itself a
working vault. The brain is the master and sends vines to it. Each bed is an entry under `beds`
in `bin/vault.json`: `{"name": "recipes", "path": "../sam-recipes", "remote": "<git URL, optional>", "topics": ["Recipes"], "strip": ["source"]}`.

- What goes: notes whose `beds` property names the bed or whose `categories` hold one of its
  `topics`, those topics' pages, and the files they embed. Never, whatever the tags: `Daily/`,
  `People/`, `.paths/` or a root file (`Me.md`, `Now.md`, `Sources.md` and the rest).
- `python3 bin/beds.py status`, `push` (`--dry-run` first), `pull`, and `clone`
  for beds with a remote. Push strips the `strip` properties and refuses while lint has errors,
  while a sent note holds a word from `bin/never-share.txt` (one per line, git-ignored), or
  while the bed has changes not yet pulled (`--force` overrides only that).
- Pull brings the bed's edits back. Conflicts, deletions, renames and new notes are reported,
  never applied: the owner settles each. Commit `.paths/beds/`, the sync state, with the notes.

## Conventions

- No en dashes (U+2013) or em dashes (U+2014) anywhere in vault content, including titles,
  filenames, properties and imported text. Replace on import.
- Every note carries `categories:` as a YAML list of `"[[Topic]]"` links and
  `created: YYYY-MM-DD`. Dates are always `YYYY-MM-DD`, never relative.
- A topic gets a page in `Categories/` when its first note exists, not before.
- `status` where a kind has it: automation creates `draft`. Only the owner, or their explicit
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
