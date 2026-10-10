# Bringing things in

A second brain is only as good as what goes into it. This is how to get each kind of material
in, and how to get it filed (summarised, named, tagged and linked) without doing it by hand.

There is one rule behind all of it. **Anything someone else wrote goes in `Clippings/`.**
Your own writing goes everywhere else. So you can always tell your thinking from what you
collected, and nothing an import or an AI does ever touches your own words.

## Step 1: get it in

| You have | Do this |
|---|---|
| A web page | The **Obsidian Web Clipper** browser extension (below). One click. |
| A list of links | Put them in a text file, one per line: `python3 bin/ingest.py add --links links.txt` |
| A PDF, Word file, email, spreadsheet, photo | `python3 bin/ingest.py add <the file>` (or a whole folder) |
| Your own old writing (journals, essays, documents) | `python3 bin/ingest.py add --mine <file or folder>` |
| Notes in another app (Apple Notes, Notion, Evernote, Google Keep, OneNote, Bear) | The **Importer** plugin, then `--mine` (below) |
| A voice memo | Transcribe it (Voice Memos on a recent Mac shows a transcript; copy it into a `.txt`), then `ingest.py add` |
| A photo of handwriting or a whiteboard | `ingest.py add photo.jpg`. Claude can read the image when it files it. |
| A thought | Just write it: a new note in `Notes/`, or under `## Notes` in today's daily note |

Run commands from inside your vault's folder (in the Claude desktop app's Code tab you can
simply ask: "ingest this PDF"). On Windows, type `py` instead of `python3`.

What `ingest.py` does: it turns each thing into a note with the right properties, puts the
imported text between `<!-- ingest:start -->` and `<!-- ingest:end -->`, and copies files and
images into `Attachments/`. It never overwrites anything. Anything you later write below the
`ingest:end` line is yours and is never touched again. PDFs get their text pulled out if the
small `pypdf` package is installed (`python3 -m pip install --user pypdf`); otherwise the PDF
is attached and Obsidian shows it inline.

### The Web Clipper

1. Install it for your browser from https://obsidian.md/clipper.
2. Open its settings, go to Templates, choose **Import**, and pick
   `guides/web-clipper-template.json` from this repo.
3. In its settings, choose your vault.
4. On any page, click the extension and **Add to Obsidian**. It lands in `Clippings/`,
   ready for the librarian.

### Moving from another notes app

1. In Obsidian: Settings, Community plugins, turn off Restricted mode, Browse, search for
   **Importer** (made by Obsidian), Install, Enable.
2. Cmd+P, "Importer: Open importer". Pick your old app and its export file, and set the output
   folder to a scratch folder such as `Imported`.
3. Then give those notes this vault's properties: `python3 bin/ingest.py add --mine Imported`
   (or ask your AI to). Check the result, then delete the scratch folder.

## Step 2: get it filed

Every imported note has `ingested:` and no `filed:` until it is filed. To see what is waiting:
`python3 bin/ingest.py waiting`.

Filing means: a one-line summary of what it is, the missing substance found (a "recipe in bio"
video gets the real recipe), a proper name, its topics, and links to the people and notes it
relates to. The instructions are in `bin/librarian.md`, and three things can follow them:

- **Claude, in the background.** `python3 bin/librarian.py`. It runs Claude Code on your
  subscription, files everything waiting, and prints a report. It is boxed in: it can only
  edit the waiting notes and add topic pages, and it never touches your own writing.
- **Claude, while you watch.** In the Claude desktop app (Code tab, your vault's folder), say
  "file my clippings". Same rules; you can steer it.
- **ChatGPT or any chat AI.** `python3 bin/librarian.py --paste` prints the whole job and
  copies it. Paste it into the chat. Save the AI's entire answer into a text file, then
  `python3 bin/librarian.py --apply answer.txt`. The script checks every note before writing
  it: it will not let the chat overwrite your own text or touch notes that were not waiting.

At the end it runs the vault's check (`bin/lint.py`). Read the report: `PROPOSAL` lines are
ideas for new kinds of notes or pages, which the librarian may suggest but never create.

## What to bring in first

Start small. Ten things you actually care about beat a thousand imported notes you will never
open. A good first week: your last few journal entries (`--mine`), five articles you meant to
keep, and one export from the app you used before.

Not sure where to start, or worried about importing too much? See
[harvesting-and-pruning.md](harvesting-and-pruning.md): an interview to find your sources, the
sample-first rule, `Sources.md`, and the monthly prune.
