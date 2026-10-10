## Bringing things in

The folder is the divider between the owner's writing and everything brought in: whatever
someone else wrote lives in `Clippings/` and nowhere else, and nothing ingested is ever
written into one of the owner's notes.

- `python3 @@VAULT_PREFIX@@bin/ingest.py add <files, folders or URLs>` brings things into
  `Clippings/`; `--mine` brings in the owner's own writing (an old journal, an export from
  another app) to `@@DEFAULT_FOLDER@@/`, and its words are never rewritten. `--links <file>`
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
