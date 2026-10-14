# Paths and beds

Status: ready-for-agent
Source: grilling session 2026-10-14, seventeen decisions approved by the maintainer. Ported from
the work vault Brain Garden was distilled from, where the index, the budgets, the shared bed and
the first desire-paths pass all ran for real; this spec keeps what worked there and fixes what
did not.

## Problem Statement

A brain garden is only useful if an AI can find its way to the answer cheaply. Today every
lookup in a vault starts by listing the kind folders, which grows with every note (in the work
vault the listing alone cost 43K chars per lookup). Nothing says which notes an AI actually
walks and which it never touches, so the garden cannot tell a path from grass. The files every
session pays for before doing anything keep growing: a freshly planted vault's `CLAUDE.md` is
already 12.8K chars, and nothing warns when it or `Now.md` or a skill gets fat. Hub pages (Home
and the topic pages) are almost all Base embeds, so an AI reading the raw text sees no signage
at all. Sharing part of a garden is described as "clone a shared repo and keep your personal
layer inside it", which makes the shared copy the master; the owner wants the opposite, a brain
that is the master and sends vines out to the beds other people can see. A vault planted today
never receives a later improvement, because the builder never overwrites. And someone arriving
with an existing Obsidian vault has no good way in: importing it as a folder flattens its
folders, drops its topics and turns its images into notes.

The mental model is a mouse in a labyrinth looking for cheese, where earlier mice left concise
signage at every fork, so the next one pathfinds with the fewest reads.

## Solution

Every vault gets signage and a way to measure where its AI walks:

- An index of every note (title, aliases, topics, status, one line each) and a `find` tool that
  is step 1 of the one lookup recipe, written once in `CLAUDE.md` and referenced everywhere
  else. The tool logs each query, so even a person pasting into a chat AI leaves footsteps,
  and a query that finds nothing is a fork with missing signage.
- `CLAUDE.md` becomes an index; the detail moves to a visible `Rules.md`. Auto-loaded files
  have size budgets that warn, never block, and the warning suggests `tend`.
- Hubs carry a short hand-picked "Start here" list of plain links above their Bases.
- Footsteps come from whatever the machine has: git (writes), the find log (lookups) and Claude
  Code transcripts (reads), into a local ledger and a one-screen report. With no read source
  the report says so and works from writes and links alone.
- One monthly pass, `tend`, replaces `prune`: it proposes one numbered list (Pave, Compact,
  Split, Signpost, Move cold, Prune, Keep) that the owner approves by number. A one-line nudge
  appears only when something is due.
- Beds: the brain is the master. `beds.py` pushes the notes allowed into each bed (a sibling
  git repo that is itself a working vault) and pulls back what collaborators changed. Nothing
  leaves unless a note or its topic says so.
- An existing Obsidian vault is just another source: `ingest.py add --vault` brings it in with
  its folders mapped to kinds, its topics kept and its links working.
- `build_vault.py --upgrade` brings all of this, and every later improvement, into a vault
  planted earlier, without touching a note or overwriting anything the owner edited.

## User Stories

1. As an AI answering a question in a vault, I want one command that prints only the index lines matching words from the ask, so that a lookup costs a few lines instead of a folder listing.
2. As an AI, I want each index line to carry the note's folder, title, aliases, topics and status, so that one match tells me what the note claims, what it is about and whether to trust it.
3. As an AI, I want stale notes left out of lookups unless I ask for them, so that I never quote a contradicted claim by accident.
4. As an AI, I want to list one topic's notes with one command, so that walking into a topic costs one call.
5. As an owner who writes in Obsidian without running any script, I want the index rebuilt automatically the next time any tool runs, so that it can never silently drift.
6. As an owner, I want the index committed, so that its history is a readable diff of what the vault knows.
7. As a ChatGPT user, I want to print the whole index in one command, so that I can paste it or upload it to a project and the chat AI knows what notes exist.
8. As an owner, I want every query and every miss logged on my machine only, so that the garden learns where its signage is missing without sending anything anywhere.
9. As the seed maintainer, I want the lookup recipe written once in `CLAUDE.md`, and the test suite to fail when a shipped skill restates it or lists kind folders, so that the old listing habit cannot creep back.
10. As an AI starting any session, I want `CLAUDE.md` to be an index that points at detail, so that I pay for the rules I need and no more.
11. As an AI about to write a note, I want the vault map, kinds and conventions in one `Rules.md` that `CLAUDE.md` tells me to read first, so that the detail is one read away.
12. As a ChatGPT user, I want `Rules.md` visible in Finder and Explorer, so that I can upload it to my project with `CLAUDE.md` and `Me.md`.
13. As an owner, I want a warning when `CLAUDE.md`, `Rules.md`, `Me.md`, `Now.md` or a skill grows past its budget, so that bloat is caught before every session pays for it.
14. As an owner, I want budget warnings to never block anything, so that a fat `Now.md` never stops a backup or a commit.
15. As an owner, I want the warning to say which file, how big, the budget, and to suggest `tend`, so that I know what to do in one line.
16. As an owner, I want to raise one file's budget in `bin/vault.json` with a decision entry, so that a file loaded only on demand can be bigger without silencing the rest.
17. As a beginner planting a vault, I want zero budget warnings on day one, so that the first lint run is green.
18. As an AI walking a topic, I want its page to start with a short "Start here" list of plain links, so that I can read the signage without a Base renderer.
19. As an AI opening Home, I want plain links to the main topics, so that Home is a crossroads and not a blank page.
20. As an owner, I want a warning when a hub with several notes has no plain links, so that a hub never goes silent to an AI.
21. As an owner, I want my own Obsidian opens left out of footsteps, so that the paths measure where the AI walks.
22. As a Claude Code user, I want transcripts found under every Claude config folder on my machine, so that a second account or a custom config folder is counted without editing a path.
23. As a user of any AI with a shell, I want my find queries to count as footsteps, so that desire paths work without Claude Code.
24. As a chat-AI-only user with no transcripts, I want the report to say reads are not measured and still show writes, links and budgets, so that it degrades instead of breaking.
25. As an owner, I want footsteps collected with no AI judgement and no frontmatter on notes, so that measuring costs no context and makes no churn commits.
26. As an owner with two computers, I want the ledger kept local and out of git, so that two machines never conflict over it.
27. As an owner, I want the report saved with each monthly pass and committed, so that month-over-month change is a diff.
28. As an owner, I want each session typed by its first skill or slash command, so that the morning brief and the evening loop each get their own fixed-load number without a mapping table.
29. As an owner, I want hot and dormant measured on reads only, so that a bulk commit does not make every note hot.
30. As an owner, I want dormant notes shown only as counts per folder, so that nobody is tempted to prune by list.
31. As an owner, I want the refresh incremental and run quietly at the end of every evening loop, so that the ledger is never more than a day behind.
32. As an owner, I want one monthly pass instead of two, so that I approve one numbered list.
33. As an owner, I want `tend` to propose paving the hot drafts, so that the claims I keep relying on get checked, shortened and linked from their topic.
34. As an owner, I want a paved note proposed once and then shown under "Paved, waiting for your verify" as one batch question, so that the same drafts do not come back every month.
35. As an owner, I want compaction to aim at about 75% of the budget, so that the warning does not return a week later.
36. As an owner, I want every pave or compact to list each fact it removed and where that fact went, so that shortening never loses something true.
37. As an owner, I want a fresh reviewer to check that list when the AI can start one, so that the writer does not grade its own cuts.
38. As an owner, I want a skill over budget split into a lean core plus references loaded on demand, so that the first turn is cheap and the behaviour is unchanged.
39. As an owner, I want queries that missed twice or more to come back as Signpost items (an alias, a clearer title, a missing note), so that the next mouse finds the cheese at that fork.
40. As an owner, I want old decisions moved to a yearly archive and old daily notes to a year folder by rule and date, so that the grep surface stays small and nothing is deleted.
41. As an owner, I want the existing prune items (unused clippings, duplicates, thin topics, sources due) in the same list, so that tending is one sitting.
42. As an owner, I want nothing moved, edited or deleted without an approved number, so that git stays the only undo I need.
43. As a Claude Code user, I want one line at session start only when tending is due or a file is over budget, and nothing otherwise, so that the nudge is never the bloat it exists to prevent.
44. As a user of another AI, I want the same line in my morning brief, so that I get the nudge without hooks.
45. As an owner, I want nothing to leave my brain unless the note or its topic names a bed, so that private is the default.
46. As an owner, I want a bed to include whole topics, so that I do not tag 200 recipes one by one.
47. As an owner, I want daily notes, people, `Me.md`, `Now.md`, `Sources.md` and the ledger never to leave, whatever their tags say, so that a mistaken tag cannot leak my life.
48. As an owner, I want private properties stripped from outgoing notes, so that a bed carries the claim and not my bookkeeping.
49. As an owner, I want push refused while an outgoing note contains a word from my local never-share list, so that a client's or a friend's name cannot slip out.
50. As a collaborator, I want the bed to open as a working vault with its own rules, lint and templates, so that I can tend it without having a brain of my own.
51. As a collaborator reading on GitHub, I want links that work and topic pages that list their notes, so that the bed reads well without Obsidian.
52. As an owner, I want collaborators' edits pulled back into my brain and conflicts, deletions and renames reported rather than applied, so that the brain stays the master and nothing is lost silently.
53. As an owner, I want each private bed to be its own repository, so that git access is the wall.
54. As someone with access to several beds, I want one command that clones the ones I can reach next to my vault, so that joining is quick.
55. As a beginner arriving with an old Obsidian vault, I want it brought in like any other source, so that I start a brain garden without special setup.
56. As that beginner, I want a proposed folder-to-kind mapping as a numbered list before anything is written, so that my journal, projects and daily notes land in the right kinds.
57. As that beginner, I want my topics, created dates and aliases kept, so that my old organisation survives.
58. As that beginner, I want images embedded with `![[...]]` brought into Attachments, and templates, Bases, canvases and settings left out, so that nothing turns into a junk note.
59. As that beginner, I want my links to keep working even when a note had to be renamed, so that the import does not break my web of notes.
60. As that beginner, I want to sample ten notes first, so that I see the result before the whole vault comes in.
61. As an owner whose vault was planted months ago, I want one upgrade command that brings in every new tool and skill, so that my garden gets the same improvements as a new one.
62. As that owner, I want the upgrade to replace only the files I never edited and to put the new version beside any I did, so that my changes survive.
63. As that owner, I want the upgrade never to touch a note and to show everything with a dry run first, so that it is safe to run on a living vault.
64. As the seed maintainer, I want every one of these behaviours covered by the existing check suite on Python 3.9, so that the seed stays trustworthy with no network and no AI.

## Implementation Decisions

### Vocabulary

Added to the vault's `Rules.md` conventions and used throughout, as in the work vault:

- **Footstep**: one read, write or lookup hit of a vault file by a session or a find query.
- **Path**: a file's footsteps over a window.
- **Hot**: three or more reads in 30 days. Reads exclude writes.
- **Dormant**: no read in 60 days, or never read. Dormant is fine.
- **Fixed load**: the chars of vault files a session reads before its first useful action.
- **Pave**: check a hot draft against its source, shorten it, link it from its topic's "Start here", and ask the owner whether to mark it `verified`.
- **Signpost**: a query that missed, turned into an alias, a clearer title or a missing note.
- **Hub**: `Home.md` or a page in `Categories/`.
- **Bed**: a sibling git repo holding the part of the brain that others may see.
- **Tend**: the monthly pass.

### The index and the one recipe

- A `find` tool ships in every vault's `bin/` (always, not behind a flag). It owns the index
  builder; lint, ingest and the librarian call it after writing.
- The index is one committed text file in a `.paths/` folder at the vault root (hidden from
  Obsidian, named for no particular AI). One line per note in every kind folder and in
  `Categories/`; `Daily/`, `Templates/`, `Attachments/` and root files are left out. Line shape:
  `Folder/title :: aliases :: categories :: status`, sorted by folder then title,
  case-insensitive. Empty fields stay empty between the separators so the shape is fixed.
- `find <words>`: every word must match somewhere on the line, case-insensitive; stale lines
  are excluded unless `--stale`; prints the matching lines only. `find --topic <Topic>`: the
  lines whose categories include it. `find --all`: the whole index, for pasting into a chat AI
  or uploading to a project.
- The index is rebuilt whenever it is missing, older than the newest note in an indexed folder,
  or its set of files differs. Lint compares content (clones and pulls reset mtimes) and
  rewrites a stale index, printing that it did, instead of erroring.
- Every query is appended to a local find log in `.paths/` (git-ignored): time, words, the
  number of hits, the matched paths. A query with no hits is a miss.
- The recipe in `CLAUDE.md`: (1) the find tool on words from the ask, (2) frontmatter grep
  (`categories`, then any property the ask names), (3) full-text grep on distinctive strings.
  The rest of the current recipe text (read notes whole, newer source wins, stale excluded,
  verified versus draft, grep before creating) stays. Skills say "look it up with the one
  recipe in `CLAUDE.md`" and never restate it.

### Budgets and the CLAUDE.md split

- The template's `CLAUDE.md` becomes an index: what the vault is, how the AI works here, the
  one recipe, and a short list of what to read before what. The vault map, the kinds table,
  adding a kind, the drift check and the conventions move to `Rules.md` at the vault root, and
  the optional sections the builder splices in go there too, each with a one-line pointer left
  in `CLAUDE.md`. `Rules.md` is binding like `CLAUDE.md`.
- Budgets live in `bin/vault.json`: `CLAUDE.md` 9,000 chars, `Rules.md` 20,000, `Me.md` 5,000,
  `Now.md` 12,000, and a skill budget of 12,000 for every `SKILL.md`. A file named in the
  budgets table overrides the skill budget (the work vault's rule for a third-party skill
  loaded only on demand).
- Lint warns, never errors, on a file over budget: the file, its size, its budget, and the
  suggestion to compact it to about 75% (naming `tend` once `tend` exists). A freshly planted
  vault of either preset is under every budget, with each file at or below 75%.
- The template's `Decisions.md` carries the rule "Every auto-loaded file is an index, never
  the detail": a file the AI loads without asking points at detail and holds none; detail is
  pulled one layer at a time; history is a verdict plus a pointer.

### Hub signage

- Every hub carries a `## Start here` section of 3 to 7 plain wikilinks, hand-picked, above
  its Base embeds. A new topic page starts with the heading and no links. Home's list names
  the main topics.
- Lint warns when a hub whose topic has three or more notes has no plain wikilink outside its
  embeds. Home is checked once the vault has three topic pages.
- The full list of a topic's notes stays the Base for people and `find --topic` for AIs; no
  generated list is written into a hub in the brain. Pave adds to "Start here".

### Footsteps, the ledger and the report

- A paths script ships in every vault's `bin/` with modes `refresh` (default), `due` and
  `--pass`, plus `--today` and repeatable `--transcripts` for tests and odd setups.
- Read sources, each optional: Claude Code transcripts, found by the vault's path slug under
  every config folder on the machine (`CLAUDE_CONFIG_DIR`, the default one, and any sibling
  config folder named like it), including the main checkout's slug when the vault is a git
  worktree; the find log (each matched path is a footstep of kind `find`). Write source: the
  git log, when the vault is a repo. The report names the sources it found.
- Footstep rules port from the work vault: a Read, Edit or Write input path; a vault path in a
  Bash command; a grep hit line in a Bash result; a folder listing is one footstep on the
  folder; Bash writes (`sed -i`, redirection, `tee`); subagent transcripts count with their
  parent session; harness-loaded files count once per session; a Skill call is a footstep on
  its `SKILL.md`. Absolute and vault-relative forms are the same file. Only files that exist
  now count.
- Session type is the first skill or slash command anywhere in the session, by name, else
  `misc`. There is no mapping table. The first useful action is the first write to a vault
  file or the first MCP call of any kind; fixed load is the chars of the distinct vault files
  read before it.
- The ledger is local and git-ignored, kept in `.paths/`. Incremental by transcript mtime; the
  git half is rebuilt from the whole log each run. It also records the paved notes and their
  dates (for Pave once) and the last pass date. No frontmatter is ever written.
- The live report (`.paths/`, git-ignored) is one screen: header (refresh date, last pass,
  window, sources found or "reads not measured"), hot files (top 20, reads only), fixed load
  per session type, dormant count per folder (never a list), the size-budget table, drafts
  wanting paving (top 10 and a count), paved and waiting for verify, and signposts (queries
  that missed twice or more in 30 days). Each pass saves a dated copy that is committed.
- With no read source the report says reads are not measured and shows writes, inbound links
  and budgets; hot, dormant and fixed load are left out rather than shown as zero.
- `end-of-day` runs the refresh after lint, quietly.
- The script never moves, edits or deletes a note, and exits silently in a bed checkout.

### Tend and the nudge

- The `prune` skill becomes `tend` and moves to the always-shipped skills; it reads the ingest
  report only when the ingest tools are present. Every mention of prune in the guides, the
  start pages and the vault docs changes with it.
- `tend` refreshes, reads the paths report (and the ingest report), and proposes one numbered
  list in seven groups, numbering continuous, an empty group kept with one line saying why:
  Pave, Compact, Split, Signpost, Move cold, Prune, Keep. Nothing dormant is named.
- Corrections from the first real pass: compaction aims at about 75% of the budget; every
  Pave and Compact lists each removed fact with its destination (a note, linked) or marks it
  dropped on purpose, before the commit, and a fresh reviewer checks that list when the AI
  can start one; a paved note is recorded and shown once under "Paved, waiting for your
  verify" as a single batch question; Signpost turns repeated misses into an alias, a clearer
  title or a missing note.
- Move cold, by rule and date, never by note name: `Decisions.md` sections older than the
  cutoff to `Decisions/Archive YYYY.md` (one per year, newest first, with a pointer left in
  `Decisions.md`); daily notes older than the cutoff to `Daily/YYYY/`; never-walked clippings
  only as a count while the ledger is under 60 days old.
- Applying: approved items only, in list order, one commit each when the vault is a repo;
  links fixed for anything moved; then the paths script with `--pass` (records the date, saves
  the dated report), then lint; a `Decisions.md` entry when a rule changed.
- The budget warning now names `tend`.
- The nudge: the paths script's `due` mode prints one line, or nothing, when the refresh is
  older than 7 days, the last pass is older than 30 days or never ran, or an auto-loaded file
  is over budget. It reads only the ledger and file sizes. A Claude Code SessionStart hook
  (on startup) runs it; `start-of-day` runs it for any AI and puts the line in the brief. It is
  silent in a bed checkout.

### Beds

- A beds script ships in every vault's `bin/`, inert until a bed is configured, with
  `status`, `push`, `pull` and `clone`, and `--dry-run` on the writing ones.
- Beds are configured in `bin/vault.json`: name, path (a sibling folder), optional remote,
  the topics it includes, the properties to strip.
- A note goes to a bed when its `beds` property names the bed or one of its `categories` is a
  topic the bed includes. Never, whatever the tags: `Daily/`, `People/`, `Me.md`, `Now.md`,
  `Sources.md`, `.paths/`. Attachments embedded by an outgoing note go with it.
- Push strips the configured properties, turns wikilinks into relative Markdown links that
  GitHub renders and Obsidian follows, turns a link to anything outside the bed into plain
  text, and gives each topic page in the bed a generated list of its notes between markers.
  It refuses while an outgoing note contains a word from the git-ignored `bin/never-share.txt`
  (case-insensitive, whole word), while lint has errors, and, unless forced, while the bed has
  commits not yet pulled. It commits in the bed, and pushes when the bed has a remote.
- A bed is itself a working vault: push keeps its `CLAUDE.md`, `Rules.md`, templates, Bases,
  lint and find tool current, and a marker file at its root tells every script it is a bed
  (no ledger, no nudge, no tend there). A collaborator clones it and opens it in Obsidian; a
  git-ignored personal layer on their side is what the current sharing guide describes.
- Pull writes bed-side edits back into the brain, re-inserting stripped properties and
  converting links back, and reports deletions, renames, conflicts (both sides changed since
  the last sync) and new files without applying them. Sync state per bed is committed in the
  brain.
- Clone fetches each configured bed with a remote that is not on disk yet, as a sibling. A
  private bed is its own repo; git access is the wall.
- The sharing guide is rewritten around this model; "how it works" says the brain sends vines
  to its beds.

### Importing an existing Obsidian vault

- `ingest.py add --vault <path>` recognises an Obsidian vault. Without a mapping it writes
  nothing and prints a proposed folder-to-kind mapping as a numbered list, with counts. With
  a mapping it imports, as the owner's writing (the `--mine` rules) except folders mapped to
  `Clippings/`.
- Kept: `categories` (missing topic pages are made in the hub shape), `created` (from
  frontmatter, else the file's birth time), `aliases`, `tags` and the other properties.
  Embeds written `![[...]]` are found anywhere in the source vault and copied flat into
  `Attachments/`, clashes renamed and the embeds rewritten. Skipped and counted:
  `.obsidian/`, `.trash/`, the templates folder, `.base` and `.canvas` files.
- A note renamed on a clash has every link to it in the imported notes rewritten; a link to a
  note that did not come along stays a breadcrumb. Date-titled notes go to `Daily/` when the
  mapping sends them there.
- `--sample N` imports the first N and stops; `--dry-run` prints the plan. The source vault's
  own `CLAUDE.md`, `AGENTS.md` or rules are not imported as notes; the summary says they exist
  and that the AI should read them and propose rules for `Decisions.md` and `Me.md` as a
  numbered list. `--via` stamps `Sources.md` as for any source. The harvest skill and the
  bringing-things-in guide gain the case, sample first as always.

### Upgrade

- The builder writes a manifest in the vault's `bin/` at planting: the seed's commit and date,
  and a hash of every seed-owned file (the bin scripts and their docs, the shipped skills and
  their references, the general Bases, the CSS snippet, the bundled plugins).
- `build_vault.py --upgrade --dest <vault>`: replaces a seed-owned file whose hash still
  matches the manifest; writes `<file>.new` beside one the owner edited and lists it; adds any
  missing file or folder; adds new keys to `bin/vault.json` and new lines to `.gitignore`
  without changing existing ones; merges settings (hooks, permissions); writes `Rules.md` when
  missing and a `CLAUDE.md.new` when the template changed, for the AI to merge with the owner
  as a numbered list; never touches a note, a kind template or a root document's content;
  updates the manifest. `--dry-run` prints the plan. A vault with no manifest (planted before
  this ticket) is compared with the current seed: identical files are recorded as seed-owned,
  different ones get `.new`.

## Testing Decisions

- One seam: `tools/check.py`. A good check plants a vault in a temporary folder with the real
  builder, runs the vault's own scripts from its root the way a person or an AI would, and
  asserts on the files written and the lines printed. Never on internal data structures.
- Prior art in the same file: the ingest round trip, the librarian `--paste` / `--apply` round
  trip, the prune round trip, the reply-card and action-log checks, the starter-vault check.
- Fixture transcripts for the paths script are tiny scrubbed JSONL files checked in with the
  tests, covering: a Read, a Bash cat with a relative path, a grep hit, a folder listing, a
  session typed by slash command, one typed by Skill call, a misc session, a write before the
  first MCP call, a subagent transcript, and two config folders. A fixed `--today` makes due
  mode deterministic.
- Fixture vaults for import and beds are built inside the check, never checked in as vaults.
- Any check that runs `git init` or `git commit` strips every `GIT_` environment variable
  first (in the work vault an inherited `GIT_DIR` reinitialised the real repo from a hook).
- Every check runs under the default `python3` and `/usr/bin/python3` (3.9), with no network,
  no AI and no third-party package. The skills have no code tests; their behaviour is the
  scripts they call.

## Out of Scope

- Transcript adapters for Codex, Gemini or any tool other than Claude Code (later; the
  sources are pluggable).
- The owner's own Obsidian opens, and any Obsidian plugin for them.
- Budgets that block a commit, and any pre-commit hook for budgets.
- Any automatic edit, move or delete of a note by a script, outside import, bed pull and the
  owner-approved items of `tend`.
- Any frontmatter field for footsteps or last read.
- Special handling for any particular person's existing vault: an existing vault is a source.
- An `AGENTS.md` in planted vaults for non-Claude agents.
- Porting any of this back to the work vault or to ObsidianVaultSeed.

## Further Notes

- Measured in the work vault before its pass: about 52K chars of root documents per session,
  a 43K-char listing per lookup, and most notes never opened. Its first pass (2026-10-14) ran
  a 43-item list in a day: 36 hot drafts paved, `Now.md` compacted from 20K to 11.9K, three
  skills split into a core plus references, September's decisions archived, and a third-party
  skill given its own budget. Every budget went green, but every file landed within 1% of its
  budget, one compaction and a dozen paves needed follow-up commits to restore dropped facts,
  and the hot-drafts list did not shrink because paving does not mark a note verified. The
  four corrections in `tend` come from those three findings.
- A freshly planted vault today: `CLAUDE.md` 12.8K (personal) and 13.1K (work), skills 2.4K
  to 5.5K, `Now.md` 0.3K.
- Every ticket: changes `template/` and then runs `tools/build_starter.py`; runs
  `tools/check.py` under both Pythons before committing; adds no en or em dash; names no real
  person, client, company, hostname or account; updates the docs it makes true in the same
  commit (README, AGENTS.md, START-HERE.md, the guides, the template's `Readme.md` sections).
- Tickets 01 to 04 all edit the template's `CLAUDE.md` or `Rules.md`: run them one at a time.
- The README hero image and its alt text say desire paths are coming; ticket 06 changes that
  when it lands them.
