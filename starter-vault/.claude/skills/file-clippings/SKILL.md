---
name: file-clippings
description: Bring things into this vault and file them. Use when the owner drops in files, folders, exports or links ("add these", "import my Notion export", "save this article", "file my clippings", "what's waiting to be filed"), or after anything was added with bin/ingest.py. Runs the ingest script, then files each waiting note by the librarian's rules in bin/librarian.md. Not for writing the owner's own notes from scratch.
---

# Bring things in and file them

Two steps, always in this order. The script does the mechanical part (it never overwrites, it
keeps the owner's text apart, it satisfies the lint); you do the judgement.

## 1. Ingest

Work out what the owner is handing you and whether they wrote it:

- Someone else wrote it (articles, links, PDFs, recipes, emails, screenshots):
  `python3 bin/ingest.py add <paths or URLs>`. It lands in `Clippings/`.
- The owner wrote it (an export of their old notes, journals, documents):
  `python3 bin/ingest.py add --mine <paths>`. It lands with their own notes, and its words
  are never rewritten.
- A pile of links: put them one per line in a text file and pass `--links <file>`.
- A big export from another app (Apple Notes, Evernote, Notion, Google Keep, OneNote, Bear):
  suggest Obsidian's **Importer** community plugin first, imported into a scratch folder, and
  then `bin/ingest.py add --mine <that folder>` to give the notes this vault's properties.
  Delete the scratch folder only after the owner has checked the result.

Use `--dry-run` first when it is more than a handful of files, and show the list.

## 2. File

`python3 bin/ingest.py waiting` lists what is waiting. Then read `bin/librarian.md` and follow
it for each waiting note, in this session: you are the librarian. The rules there are the same
ones the background run follows, so a note filed here and one filed by `bin/librarian.py` look
alike.

When more than about fifteen notes are waiting, offer the background run instead
(`python3 bin/librarian.py`): it files them on the owner's Claude subscription while they do
something else, and appends its report to `bin/librarian.log`.

## 3. Finish

Run `python3 bin/lint.py` and fix every error. Give the owner the librarian's report (FILED,
INCOMPLETE, PROPOSAL, PROBLEM lines), and offer the proposals as a numbered list. Do not
commit unless asked.
