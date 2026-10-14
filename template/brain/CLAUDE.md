# @@VAULT_NAME@@

An Obsidian vault at @@VAULT_PATH@@: a second brain for @@PROJECT@@. Kepano method: few
folders, a `categories` property with `[[links]]` for topics, one template and one Base per
kind, one page per topic in `Categories/`. Planted @@DATE@@ from
Brain Garden.

Root documents: this file is the index a session loads first (how Claude works here, how to
look things up, what to read before what); `Rules.md` holds the detail and is binding like this
file; `Readme.md` is the human guide, `Decisions.md` the dated log of why the rules are what
they are, `Home.md` the hub. Rules are decisions, not laws; @@OWNER@@ changes any of them in a
sentence, and the change is recorded in `Decisions.md` in the same session.

## Read before

- **`Rules.md` before you write or restructure a note, touch a template, a Base or a skill,
  and before a first commit.** It has the vault map, the kinds and their properties, adding a
  kind, the drift check and the conventions.
@@SECTION_POINTERS@@
## How Claude works here

- The structure is a starting point, not scripture. It grows where real work keeps producing
  a note with no home and prunes what sits unused. Reach for the smallest change that works:
  a topic page first, then a property, then a Base view, and only then a new kind ("Adding a
  kind" in `Rules.md`).
- Approval is by numbered list. @@OWNER@@ skips or edits by number, the rest is applied. Git
  is the undo.
- **Say how before you do.** For any non-trivial task (more than one step, more than one note
  touched, anything that leaves the vault, or anything you have not done here before), first
  say in a few lines how you would solve it: the steps, what changes, and the choice you made
  where there was one. Then wait for a go. A lookup, an answer or one obvious edit needs no
  plan.
- **Log every action.** Everything done on @@OWNER@@'s behalf (a note made, edited or moved,
  something brought in, a message drafted or sent, an event or task made in a connected tool)
  gets one line appended to @@ACTION_LOG@@:
  `- YYYY-MM-DD HH:MM What was done, with a [[link]]. Why: the reason. Chose: any choice made. Asked by: who, and where.`
  "Asked by" is @@OWNER@@ in chat, @@OWNER@@'s reply on a brief item, or a scheduled run.
  Reading and answering are not actions, and a skill's own bookkeeping (the brief, `Now.md`,
  `## Learned`) is not logged. The log is append only: a mistake gets a new line, not an edit.
- When you notice drift between this file or `Rules.md` and the vault, propose the smallest
  edit to the wrong one in the same session. Never silently adapt and leave the doc behind.
- @@MEMORY_RULE@@
@@ME_RULE@@- Load the matching skill before doing the work: `obsidian:obsidian-markdown` before writing
  or restructuring any note, `obsidian:obsidian-bases` before touching a `.base`,
  `obsidian:obsidian-cli` when something must happen in the running app,
  `obsidian:json-canvas` for `.canvas` files, `obsidian:defuddle` to turn a web page into a
  clipping. `kepano-method` (project skill in `.claude/skills/`) is the why behind the
  structure, for audits and "is this the kepano way" questions, not for syntax.

## Looking things up: the one recipe

Every question uses this order, stopping early when the answer is clear:

1. `python3 @@VAULT_PREFIX@@bin/find.py <words from the ask>`. It prints one line per note
   that has every word: `Folder/title :: aliases :: categories :: status`. Titles are claims,
   imperatives and names, so the line often answers on its own. Stale notes are left out unless
   you add `--stale`; `--topic <Topic>` lists one topic's notes. Never list the kind folders
   instead: `.paths/index.txt` is the listing, and each query is logged, so a miss shows where a note
   or an alias is missing.
2. Frontmatter grep: `categories` for the topic, then any property the ask names.
3. Full text grep on distinctive strings.

Read matching notes whole; they are small. When two disagree, the later `source` date wins and
the answer says how old the evidence is. Exclude `status: stale` from results; a stale note is
cited only to warn that an answer may have changed. `verified` can be stated, `draft` must be
hedged.

Before creating a note, run the find tool on its key noun, grep the filenames for it too, and
show near matches. A second note about the same thing becomes an edit to the first, never a
sibling.
