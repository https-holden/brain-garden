---
name: prune
description: Monthly tidy of this vault. Runs bin/ingest.py report, then proposes one numbered list of what to trash, merge, verify, rewrite or stop collecting, and applies what the owner keeps. Use when the owner says "prune", "tidy up", "clean up the vault", "monthly review", "what am I collecting but never using", or when start-of-day says a prune is due. Never deletes the owner's own writing.
---

# Prune: keep what earns its place

A vault that only grows gets slower to search and harder to trust. Once a month, cut what is
not used, merge what is duplicated, and stop collecting from sources that do not pay off.
Everything is proposed first, and nothing the owner wrote is ever deleted by you.

## 1. Read the report

```bash
python3 bin/ingest.py report
```

Its sections, and what each one can become:

| Section | Proposal |
|---|---|
| Unused clippings | `trash` (it refuses anything linked or written on), or keep with a reason |
| Waiting too long | file now (`file-clippings`), or trash if no longer wanted |
| Old drafts | the owner verifies (`status: verified`), you rewrite, or it is deleted |
| Stale notes | rewrite from the newer evidence, or delete |
| Thin topics | merge into a broader topic (change `categories` on its note, then delete the page), or keep for now |
| Quiet people | merge into the note that mentions them, or keep |
| Possible duplicates | merge into one note (keep the oldest name, so links hold), then trash the rest |
| Unused attachments | `trash` |
| Sources due | pull now (`harvest` has the method), or change the cadence |
| Where things come from | a source whose notes go unused: propose `Keep?: no` in `Sources.md` |

`--days 60` widens the window when the vault is young.

## 2. Propose one numbered list

One line each: the note, the action, and the reason from the report. Group by action. Lead
with the sources table, because stopping a bad source prevents next month's clutter. Ask once
for skips and edits by number.

## 3. Apply, with these limits

- **Trash** clippings and attachments only with `python3 bin/ingest.py trash "<name>"`. It moves
  them to `.trash/` and refuses anything still linked or written on. Never `rm`.
- **The owner's own notes** (outside `Clippings/`) and **daily notes** are never trashed or
  deleted by you. For those, propose merging or linking, and if the owner wants one gone, they
  delete it in Obsidian.
- **Merge** by moving the substance into the surviving note, pointing every link at it
  (`grep -rl "\[\[Old name"`), and only then trashing the leftover clipping. A merged note keeps
  both `source` lines.
- Changes to the structure (a topic retired, a kind no longer used, a source stopped) get a
  dated line in `Decisions.md`, and stopped sources move to "Not brought in, on purpose" in
  `Sources.md` with the reason.

## 4. Finish

Run `python3 bin/lint.py` and fix every error. Report in three lines: what was cut, what was
merged, and which source to watch next month. Then one line on the process: what the report
keeps flagging month after month, and the smallest change that would stop it at the source
(a cadence, a `Keep?: no`, a filing rule in `bin/librarian.md`). Offer to commit if the vault is a git repo.
