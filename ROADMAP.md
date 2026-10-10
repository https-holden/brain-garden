# Roadmap

Where Brain Garden is going, newest ideas last. Dated when added; struck through when it lands.

## Next

- **Desire paths (heat map).** Added 2026-10-10. The routes used most get strengthened; the
  ones never used get compacted or pruned. The opposite of atrophy. The idea is in
  [guides/how-it-works.md](guides/how-it-works.md#desire-paths-coming). Open design questions:
  - **Signals.** Already measured: inbound links per note and use per source
    (`bin/ingest.py report`). To add: hand edits (the `modified` property the
    `manual-modified` plugin stamps), links added over time (git history), notes opened in
    Obsidian (a small plugin writing a local, git-ignored log), and which notes an AI reads
    to answer questions (a line in the daily note's `## Learned`).
  - **Strengthen the warm end.** Surface the hottest notes and topics on `Home.md`; suggest
    links along well-worn routes; promote a hot draft to be verified first.
  - **Compact the cold end.** Fold a cluster of cold clippings on one topic into a single
    summary note that links the originals, before anything is trashed. Never compact the
    owner's own writing without asking.
  - **Decay.** A half-life, so a burst of use in one week does not pave a path forever.
  - Start as a `heat` section in `bin/ingest.py report`, before any plugin.

## Later

- A small Obsidian plugin for the open-note log above, kept on the machine.
- A guided "first week" mode for `start-of-day` that teaches one feature a day.
