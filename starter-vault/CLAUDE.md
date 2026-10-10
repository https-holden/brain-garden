# My Second Brain

An Obsidian vault at the top of this folder: a second brain for its owner. Kepano method: few
folders, a `categories` property with `[[links]]` for topics, one template and one Base per
kind, one page per topic in `Categories/`. Planted 2026-10-10 from
Brain Garden.

Root documents: this file holds the operating rules, `Readme.md` is the human guide,
`Decisions.md` is the dated log of why the rules are what they are, `Home.md` is the hub.
Rules here are decisions, not laws; the owner changes any of them in a sentence, and the
change is recorded in `Decisions.md` in the same session.

## How Claude works here

- The structure is a starting point, not scripture. It grows where real work keeps producing
  a note with no home and prunes what sits unused. Reach for the smallest change that works:
  a topic page first, then a property, then a Base view, and only then a new kind (a folder,
  a template, a Base, and a row in both tables below).
- Approval is by numbered list. The owner skips or edits by number, the rest is applied. Git
  is the undo.
- **Say how before you do.** For any non-trivial task (more than one step, more than one note
  touched, anything that leaves the vault, or anything you have not done here before), first
  say in a few lines how you would solve it: the steps, what changes, and the choice you made
  where there was one. Then wait for a go. A lookup, an answer or one obvious edit needs no
  plan.
- **Log every action.** Everything done on the owner's behalf (a note made, edited or moved,
  something brought in, a message drafted or sent, an event or task made in a connected tool)
  gets one line appended to `## Actions` in today's `Daily/YYYY-MM-DD.md`:
  `- YYYY-MM-DD HH:MM What was done, with a [[link]]. Why: the reason. Chose: any choice made. Asked by: who, and where.`
  "Asked by" is the owner in chat, the owner's reply on a brief item, or a scheduled run.
  Reading and answering are not actions, and a skill's own bookkeeping (the brief, `Now.md`,
  `## Learned`) is not logged. The log is append only: a mistake gets a new line, not an edit.
- When you notice drift between this file and the vault, propose the smallest edit to the
  wrong one in the same session. Never silently adapt and leave the doc behind.
- Three memory tiers. Short-term: `Daily/` (when present), the raw log of one day, never rewritten after it. Mid-term: `Now.md`, what is in flight (Goals, Active, Waiting on, Recently done, Open questions), every bullet ending with the date it last moved; a bullet that settles into a fact becomes a note and the bullet links it. Long-term: the kind folders.
- `Me.md` is who the owner is: what the vault is for, what they bring in, which tools and
  connectors they use, what is private. Read it first in every session, and when it is still
  full of `(fill in: ...)` lines, offer to fill it in with them in a few questions.
- Load the matching skill before doing the work: `obsidian:obsidian-markdown` before writing
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
| `Me.md` | Who the owner is, for any AI: purpose, sources, tools, what is private. | Content. |
| `Sources.md` | Where material comes from: how, cadence, last pulled, keep or not. | Notes. |
| `Now.md` | Working memory: what is in flight, every bullet dated. | Facts (they become notes), history. |
| `Notes/` | Anything authored that is not another kind: essays, evergreen ideas, working notes. | Things other people wrote (those are clippings). |
| `References/` | Things that exist outside your head: books, tools, places, organisations. | Dated, authored writing. |
| `People/` | One note per person: who they are, their role, one line. | Private details, anything they would not want written down. |
| `Clippings/` | Things other people wrote, as clean Markdown (`obsidian:defuddle` or the Web Clipper). | Anything authored here. The folder is the divider between your writing and ingested text. |
| `Daily/` | `YYYY-MM-DD`, the raw log of one day. Never rewritten after the day. | Knowledge (copy it out to its own note and link back). |
| `Categories/` | One page per topic in use: `tags: [categories]`, one paragraph, `![[Topics.base#In this topic]]`. Every link here must resolve. | Topics with no notes yet. |
| `Templates/`, `Templates/Bases/` | One template and one Base per kind, plus the general Bases (`Everything`, `Topics`, `Related`, `Backlinks`, `Attachments`). Core `{{date}}` syntax only. | Templater syntax. |
| `Attachments/` | Every file, flat. | Subfolders. |
| `bin/` | `lint.py` (the drift check) and its `vault.json`, `ingest.py` (bring things in), `librarian.py` and `librarian.md` (file them). Re-runnable maintenance scripts. | Secrets, logs in git. |
| `.obsidian/` | Tracked config, the `vault.css` snippet, any home-made plugins. Document a new plugin in `Readme.md`. | Content. |

## Kinds in use

| Kind | Template | Base | Properties | Title is |
|---|---|---|---|---|
| Notes | Note Template | Notes.base | `categories`, `created`, `topics` | for an idea, the idea as a claim; otherwise a plain name |
| References | Reference Template | References.base | `categories`, `created`, `author`, `url`, `rating` | the thing's own title, exactly |
| People | Person Template | People.base | `categories`, `created`, `org`, `role`, `source` | the person's name, never a role (qualify in parentheses when two share one) |
| Clippings | Clipping Template | Clippings.base | `categories`, `author`, `url`, `created`, `published` | the page's own title |
| Daily | Daily Note Template | Daily.base | `tags`, `cssclasses` | `YYYY-MM-DD` |

Adding a kind (the loop): check first that it is not just a `type` value or a view on an
existing kind. If it really is new: the folder, `Templates/<Kind> Template.md` carrying every
property its Base will show, `Templates/Bases/<Kind>.base` filtered on `file.inFolder()`, an
entry in `bin/vault.json` so the lint knows it, a row in both tables above, a paragraph in
`Readme.md`, and a line in `Decisions.md`.

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
