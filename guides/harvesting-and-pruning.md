# Harvesting and pruning

A second brain fails in one of two ways: nothing goes in, or everything goes in and none of it
is ever used. Harvesting is deciding what comes in and how; pruning is clearing out what did
not earn its place. Both are a conversation between you and your AI, and this is how to have it.

## The short version

1. **Find your sources first.** Where does your thinking already happen? That is worth more
   than anything you could import.
2. **Sample before you bulk-import.** Bring in ten things, look at them filed, adjust, then do
   the rest.
3. **Write down every source** in `Sources.md`, with how often to pull it.
4. **Prune monthly.** Cut what you never touched, merge duplicates, stop collecting from
   sources that never pay off.

With Claude: say **"harvest"** to do steps 1 to 3 together, and **"prune"** once a month.
With ChatGPT: the prompts are at the bottom of this page.

## Harvesting

### The interview

The AI should ask you these, a few at a time. Answer honestly; "I don't know" is fine.

1. **Where does your thinking happen today?** Notes app, voice memos, messages to yourself,
   screenshots, bookmarks, open tabs, email drafts, paper, a journal app, the desktop.
2. **What do you keep losing, or finding again?** Start there. It is the source with the most
   value and the clearest test of whether the vault works.
3. **What do you collect from other people?** Articles, videos, recipes, newsletters, saved
   posts, podcasts, book highlights.
4. **A year from now, what would you want to find here?** If the answer is "nothing from that
   app", that app does not get imported.
5. **What must never come in?** Other people's private messages, work material in a personal
   vault, anything you would not want an AI to read.

### Picking a method for each source

| Source | Method | Usually |
|---|---|---|
| Articles and web pages | The Obsidian Web Clipper button | as it comes |
| Bookmarks, saved links | A text file of links, `ingest.py add --links` | once, then monthly |
| Your old notes app | Obsidian's Importer plugin, then `ingest.py add --mine` | once |
| Documents and PDFs | `ingest.py add` (add `--mine` if you wrote them) | once, then as it comes |
| Voice memos | The transcript as a text file, `ingest.py add --mine` | weekly |
| Emails worth keeping | Drag them out as `.eml` files, `ingest.py add` | as it comes |
| Photos of paper, whiteboards, screenshots | `ingest.py add` the images; the AI reads them | as it comes |
| Book highlights | Your reading app's export | monthly |
| Thoughts | Today's daily note | every day |

The details of each are in [bringing-things-in.md](bringing-things-in.md).

**Name the source every time**: `ingest.py add <files> --via "Voice memos"`. The note
remembers where it came from, and `Sources.md` records when you last pulled it, so the morning
brief can remind you when one is overdue and the monthly report can tell you which sources you
actually use.

### Backfills: sample first

Importing ten years of notes in one go buries the good ones and teaches you nothing. Instead:

1. Take about ten representative items from the source.
2. Import and file them, then open three. Is this what you wanted to keep? Too much, too
   little, badly named?
3. Change what needs changing (a different export, `--mine` or not, a subfolder to skip).
4. Then import the rest, with `--dry-run` first to see the list.

Order: your own writing before other people's, recent before old, and the "keep losing it"
source before everything else.

### What not to bring in

Receipts, duplicates of things that live somewhere better (your calendar, your photo library),
dead links, anything you saved "just in case" and never opened, and anything private that is
not yours. Write each rejected source under "Not brought in, on purpose" in `Sources.md` with
the reason, so you do not reconsider it every month.

## Pruning

### The monthly report

```bash
python3 bin/ingest.py report
```

It lists, from the vault itself rather than anyone's guess:

- **Unused clippings**: filed a month ago, nothing links to them, you wrote nothing on them.
- **Waiting too long**: imported a week ago and never filed.
- **Old drafts** and **stale notes**: claims nobody checked, or that newer evidence contradicted.
- **Thin topics**: a topic page with one note or none.
- **Quiet people**: a person's page that at most one note mentions.
- **Possible duplicates**: the same link or the same name twice.
- **Unused attachments**: files no note shows.
- **Sources due**: past their cadence in `Sources.md`.
- **Where things come from**: for each source, how much was imported and how much of it you
  have since linked to or written on. This is the most useful number in the vault. A source at
  5% is costing you attention.

### The rules

- **Your own writing is never deleted by a tool or an AI.** Only clippings and unused
  attachments can be trashed (`ingest.py trash`), and only when nothing links to them and you
  have not written on them. Even then they go to `.trash/`, not away.
- **Merge rather than delete** when two notes say the same thing: keep the older name so links
  still work.
- **Stop at the source.** Turning off a source that never pays off (`Keep?: no` in
  `Sources.md`) prevents next month's clutter. Do that before trashing anything.
- **Daily notes stay.** They are the record of what happened.

## Prompts

### For you to ask your AI

- "Harvest with me. Interview me about where my notes and ideas live, then fill in
  Sources.md."
- "What am I collecting but never using?"
- "Which source gives me the most notes I actually link to?"
- "Bring in ten of my [voice memos / old notes / bookmarks] as a sample, file them, and show me
  three."
- "Prune: run the report and give me one numbered list."
- "What keeps coming up in my daily notes that has no note of its own?"
- "Which of my topics should be merged?"

### For ChatGPT or another chat AI

Harvesting:

> I'm building a second brain in Obsidian. Interview me, a few questions at a time, about
> where my notes, ideas and saved things live today, what I keep losing, what I collect from
> others, what I'd want to find a year from now, and what must never go in. Then give me a
> table of sources with: what comes from it, how to bring it in (from the methods below), how
> often, and whether to backfill the past or only capture from now. Recommend which ONE to
> start with and why.
>
> (paste the "Picking a method" table from this guide)

Pruning (run `python3 bin/ingest.py report` first and paste its output):

> Here is my vault's pruning report and my Sources.md. Give me one numbered list of actions:
> what to trash, what to merge into what, which drafts to check, and which sources to stop or
> pull less often, each with a one-line reason. Never suggest deleting anything outside
> Clippings/ or any daily note. Lead with the sources.
>
> (paste the report, then Sources.md)
