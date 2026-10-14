---
name: tend
description: The monthly pass over this vault. Refreshes the footsteps, reads the paths report (and the ingest report when the vault has one), proposes one numbered list in seven groups (Pave, Compact, Split, Signpost, Move cold, Prune, Keep) and applies only the numbers the owner approves, one commit each. Use when the owner says "tend", "monthly review", "tidy up the vault", "what am I collecting but never using", asks to prune or compact, when lint says a file is over its budget, or when the nudge says tend is due.
---

# Tend: pave the paths, keep the rest light

Once a month the garden gets one sitting. The routes the AI walks get paved, the files every
session pays for get lighter, lookups that missed get signs, and what is cold is moved by rule.
Everything is one numbered list the owner approves by number; git is the undo.

## 1. Read the reports

```bash
python3 bin/paths.py
```

Then read `.paths/report.md`, and run `python3 bin/ingest.py report` too, only when
`bin/ingest.py` exists; `references/ingest-report.md` says what each of its sections becomes.
Read the `## Kept` section of the newest file in `.paths/reports/`: what was kept there is
decided and stays off the list unless its reason changed.

The reports are the evidence: propose from them, and open a note only to check an item that is
already on the list. Nothing dormant is named: the paths report gives dormant notes as counts
per folder, and dormant is fine. When the report says reads are not measured, the list works
from writes, links and budgets, and says so in its first line.

Done when every section of each report has been read.

## 2. Propose one numbered list

Seven groups, always all seven, in this order. Numbering runs on across groups (Pave 1 to 4,
Compact 5, and so on). A group with nothing in it keeps its heading and one line saying why
("Compact: every file is under 75% of its budget"). Each item is one line: the file, the
action, and the reason from the report.

### Pave

Each note under "Drafts wanting paving" (hot and still `status: draft`). Paving a note: check
it against its `source`, shorten it to what is true, and link it from its topic's
`## Start here` (3 to 7 links, so another may come off).

### Compact

Each file over its budget in "Size budgets". The target is about 75% of the budget, so the
warning does not come back a week later. Detail moves to a note (or a skill's `references/`)
with a pointer left behind; every fact survives somewhere.

### Split

A skill over its budget becomes a lean core `SKILL.md` plus `references/` files it loads on
demand, its behaviour unchanged. A session type whose fixed load stays high points at what it
reads first: name that file here or under Compact.

### Signpost

Each query under "Signposts" (missed twice or more). Find what it was looking for with the one
recipe in `CLAUDE.md`, then propose the fix: an alias, a clearer title or a missing note.

### Move cold

By rule and date, never by note name. The reports do not list these; find them as below. The
cutoff is `cold_days` in `bin/vault.json` (90 when it is missing).

- `Decisions.md`: its `## YYYY-MM-DD` headings date each section. Sections older than the
  cutoff move to `Decisions/Archive YYYY.md`, one file per year, newest first, with one
  pointer line left in `Decisions.md`. A section that sets a rule tend follows (a budget, a
  kept item, a stopped source) stays in `Decisions.md` whatever its age.
- `Daily/`: the file names are the dates. `Daily/YYYY-MM-DD.md` notes older than the cutoff
  move to `Daily/YYYY/`.
- Clippings no session has read: the Clippings figure in the report's Dormant line. While the
  ledger is under 60 days old (the report's "Ledger started" date), one line with that count
  and nothing more. After that, the unused ones come up under Prune, from the ingest report.

### Prune

From the ingest report only (no ingest tools: one line saying so). Sources first, because
stopping a source prevents next month's clutter; then what to trash, merge, rewrite or ask
about, as `references/ingest-report.md` maps it.

### Keep

What a report flags that should stay as it is, with the reason, so it is decided and not
re-proposed. Every Keep item is recorded under `## Kept` at the end of the dated pass report
(step 4), which the next pass reads. A file that earns a bigger budget is also given its own
budget in `bin/vault.json`, with a `Decisions.md` entry saying why.

After Keep, when the report lists notes under "Paved, waiting for your verify", show them
once, numbered on, as one batch question: "These were paved last time. Mark them all
`verified`? Skip any by number." Only the owner's answer moves a note to `verified`, and the
next pass does not ask again.

Ask once for skips and edits by number. Done when every report section is an item or a
group's one-line reason.

## 3. Apply what was approved

Approved numbers only, in list order, one commit each when the vault is a git repo
(`tend N: what was done`).

1. **Removed facts, before the commit.** Every Pave and Compact lists each fact it took out
   with its destination (the note it now lives in, linked) or marks it dropped on purpose.
   When you can start a fresh reviewer (a subagent that did not write the change), give it
   the before, the after and that list, and have it name any fact that is in none of them.
   Restore what it finds, then commit.
2. **Record each pave.** `python3 bin/paths.py --paved "<path from the vault root>"`. The note
   leaves "Drafts wanting paving" for good and comes back once, next pass, under "Paved,
   waiting for your verify".
3. **Moves keep their links.** Move with `obsidian move`, or grep every inbound `[[link]]`
   and fix it in the same commit. A file is moved, never deleted, except a clipping or an
   attachment through `bin/ingest.py trash`.
4. **Rules changed get an entry.** A budget raised, `cold_days` changed, a source stopped or
   a topic retired: a dated entry in `Decisions.md`.

## 4. Finish

Run `python3 bin/paths.py --pass`: it records today as the last pass and saves the report as
`.paths/reports/YYYY-MM-DD.md`. Append `## Kept` to that file: one line per Keep item, with
its reason. Then `python3 bin/lint.py`, fixing every error, and commit the dated report (with
any lint fix) as the pass's last commit. Report in three lines: what was paved and compacted, what was moved or cut, and what
the next pass should watch. Then one line on the process: what the reports keep flagging,
and the smallest change that would stop it at its source.
