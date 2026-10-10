---
name: harvest
description: Work out with the owner where their material lives and how to bring it into this vault, then record it in Sources.md and run a small first pull. Use when the vault is new, when the owner asks "what should I put in here", "how do I get my notes / voice memos / bookmarks / emails in", "set up my sources", "import everything", or when Sources.md is still empty. Interview first, sample before any bulk import. Not for filing notes already imported (that is file-clippings).
---

# Harvest: find the sources, then bring in a sample

A second brain fails in one of two ways: nothing goes in, or everything goes in and none of it
is ever used. This skill steers between them. The full reasoning, for the owner, is in
`guides/harvesting-and-pruning.md` of https://github.com/https-holden/brain-garden; this is the procedure.

Read `Me.md` and `Sources.md` first. If `Me.md` still says what the vault is for only as
`(fill in: ...)`, ask that first, in one question: every later choice depends on it.

## 1. Interview (a few questions at a time, never a form)

Ask in plain words, and listen for places the owner did not think of as "notes":

1. **Where does your thinking happen today?** A notes app, voice memos, messages to yourself,
   screenshots, browser bookmarks or open tabs, email drafts, paper notebooks, a journal app,
   documents on the desktop.
2. **What do you keep losing, or re-finding?** That is the highest-value source.
3. **What do you collect from others?** Articles, videos, recipes, newsletters, saved posts,
   podcasts, books and highlights.
4. **A year from now, what would you want to search for and find here?** This decides what is
   worth importing at all.
5. **What should never come in?** Other people's private messages, work material on a personal
   vault, anything they would not want an AI to read.

## 2. Map each source to a method and a cadence

Propose one numbered list, one line per source: what it brings, how (from the table below),
cadence, and whether to backfill the past or only capture from now on. The owner skips or
edits by number.

| Source | How |
|---|---|
| Web pages, articles | Obsidian Web Clipper (`guides/web-clipper-template.json`), as it comes |
| Saved links, bookmarks | Export or paste into a text file, `ingest.py add --links file --via "Bookmarks"` |
| Another notes app | Obsidian's Importer plugin into a scratch folder, then `ingest.py add --mine <folder> --via "<App>"`, once |
| Documents, PDFs | `ingest.py add <file or folder> --via "<Name>"` (`--mine` if they wrote it) |
| Voice memos | Copy the transcript to a `.txt` (or ask Claude to transcribe), `ingest.py add --mine`, weekly |
| Email | Drag messages to a folder as `.eml`, `ingest.py add <folder> --via "Email"`; only the ones worth keeping |
| Photos of paper, whiteboards, screenshots | `ingest.py add <images>`; the librarian reads the image when filing |
| Highlights from books | The reading app's export (Kindle, Readwise, Apple Books) into `References/` notes, monthly |
| Things said in meetings or calls | The meeting-notes tool's summary, `--via "Meetings"`, as it comes |
| Thoughts | Not a harvest: today's daily note, `## Notes` |

Add every agreed source as a row in `Sources.md`, and every rejected one as a line under
"Not brought in, on purpose" with the reason.

## 3. Sample, then backfill

Never bulk-import first. For each backfill source:

1. Pick about ten representative items and run `ingest.py add ... --via "<Source>" --dry-run`,
   then for real.
2. File them (`file-clippings`), then open two or three with the owner. Ask: is this what you
   wanted to keep? Too much? Too little? Named well?
3. Adjust (which subfolder of the export, `--mine` or not, what to skip), and only then run the
   rest, again with `--dry-run` first. For more than about a hundred items, file them in the
   background with `python3 bin/librarian.py`.

Order: the owner's own writing before other people's, recent before old, and the source from
question 2 before everything else.

## 4. Hand over

Show the filled `Sources.md`, run `python3 bin/lint.py`, and tell the owner the one habit that
matters for each continuing source ("clip articles with the browser button", "on Sundays, drop
the week's voice memo transcripts in"). `start-of-day` will mention a source when it is due.
