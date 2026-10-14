# The ingest report, for the Prune group

Read when `bin/ingest.py` exists: `python3 bin/ingest.py report` is the evidence for Prune.
`--days 60` widens its window when the vault is young.

## What each section becomes

| Section | Proposal |
|---|---|
| Where things come from | a source whose notes go unused: `Keep?: no` in `Sources.md`. Listed first |
| Sources due | pull now (`harvest` has the method), or change the cadence |
| Unused clippings | while the paths report's ledger is under 60 days old ("Ledger started"), none by name: Move cold gives their count. After that, `trash` (it refuses anything linked or written on), or Keep with a reason |
| Waiting too long | file now (`file-clippings`), or trash if no longer wanted |
| Old drafts | a hot one is already under Pave; otherwise the owner verifies it, you rewrite it, or the owner deletes it |
| Stale notes | rewrite from the newer evidence, or the owner deletes it |
| Thin topics | merge into a broader topic (change `categories` on its notes, then retire the page), or Keep for now |
| Quiet people | merge into the note that mentions them, or Keep |
| Possible duplicates | merge into one note (the oldest name, so links hold), then trash the leftover clipping |
| Unused attachments | `trash` |

## Applying

- **Trash** clippings and attachments only with `python3 bin/ingest.py trash "<name>"`. It
  moves them to `.trash/` and refuses anything still linked or written on.
- **The owner's own notes** (outside `Clippings/`) and **daily notes** stay. For those,
  propose a merge or a link; when the owner wants one gone, they delete it in Obsidian.
- **Merge** by moving the substance into the surviving note, pointing every link at it
  (`grep -rl "\[\[Old name"`), and only then trashing the leftover clipping. A merged note
  keeps both `source` lines.
- **Structure changes** (a topic retired, a kind no longer used, a source stopped) get a
  dated entry in `Decisions.md`, and a stopped source moves to "Not brought in, on purpose"
  in `Sources.md` with the reason.
