# My Second Brain

The human guide. `CLAUDE.md` is what your AI reads first in every session: how it works here
and how it looks things up. `Rules.md` is the detail it reads before changing anything: where
each kind of note goes, what it carries, the conventions. `Decisions.md` is the dated log of
why the rules are what they are.

## Opening it

Obsidian, "Open folder as vault", this directory. Start at [[Home]].

## How it is organised

- **Folders say what a note is.** There is one folder per kind of note, and the list is short.
- **`categories` says what a note is about.** A YAML list of `[[links]]` to pages in
  `Categories/`. Each topic page lists every note about it.
- **Every note starts from a template** in `Templates/`, so its properties exist from the
  first day. Insert one with the core Templates plugin.
- **Every kind has a Base** in `Templates/Bases/`, a live table over that folder. Home embeds
  the views worth seeing daily.

## Daily use

One folder per kind of note. New notes land in `Notes/`. To make one, create the note in its folder and insert its template (Command palette, "Templates: Insert template").

- **`Notes/`**, from *Note Template*: Anything authored that is not another kind: essays, evergreen ideas, working notes. Its name: for an idea, the idea as a claim; otherwise a plain name.
- **`References/`**, from *Reference Template*: Things that exist outside your head: books, tools, places, organisations. Its name: the thing's own title, exactly.
- **`People/`**, from *Person Template*: One note per person: who they are, their role, one line. Its name: the person's name, never a role (qualify in parentheses when two share one).
- **`Clippings/`**, from *Clipping Template*: Things other people wrote, as clean Markdown (`obsidian:defuddle` or the Web Clipper). Its name: the page's own title.
- **`Daily/`**, from *Daily Note Template*: `YYYY-MM-DD`, the raw log of one day. Never rewritten after the day. Its name: `YYYY-MM-DD`.

## Finding things

`python3 bin/find.py <words>` lists the notes whose title, aliases, topics or
status have every word, one line each. Your AI starts every lookup with it. It reads an index
of your notes, `.paths/index.txt`, which keeps itself current and is committed, so its history
shows what the vault knows. Using ChatGPT? `python3 bin/find.py --all` prints
the whole index: save it as a file in your ChatGPT project, beside `CLAUDE.md`, `Rules.md`
and `Me.md`.

## Every day

- **Morning**: ask Claude "start my day" (the `start-of-day` skill). Today's note in `Daily/`
  gets a short checklist from `Now.md`, yesterday, and your calendar if it is connected. Each
  item says how much Claude can take: **green** (it can just do it), **yellow** (pick an
  option, A, B or C) or **red** (yours: it is new, or cannot be undone).
- **Reply when you have a minute**: under any item, write a short instruction in its
  **Reply** card: `go`, a letter, `skip`, `mine`, or a sentence. Then say "run my replies"
  (the `run-brief` skill). Claude does only those and leaves the rest for tomorrow.
- **During the day**: jot anything under `## Notes` in today's note. Tick what you finish.
  Everything Claude does for you gets one line under `## Actions`: what, why, what it chose,
  and who asked.
- **Evening**: "end of day" (the `end-of-day` skill). Claude proposes the notes worth keeping
  as a numbered list, you skip any by number, and it updates `Now.md`, your working memory.

## Bringing things in

Anything someone else wrote (articles, PDFs, recipes, emails, screenshots) goes in
`Clippings/`, so you can always tell your thinking from what you collected.

- **From the web**: install the Obsidian Web Clipper browser extension and import the
  template from https://github.com/https-holden/brain-garden
  (`guides/web-clipper-template.json`). One click saves a page here.
- **Files and links**: `python3 bin/ingest.py add <file, folder or link>`. Your own old
  writing: add `--mine`. A list of links: `--links links.txt`.
- **An Obsidian vault you already have**: `python3 bin/ingest.py add --vault <its folder>`
  shows which of its folders would go where, and copies nothing until you agree.
- **Filing**: `python3 bin/librarian.py` has Claude file everything new (a summary, a good
  name, topics, links). With ChatGPT instead: `python3 bin/librarian.py --paste`, paste into
  the chat, save its answer to a file, then `python3 bin/librarian.py --apply <file>`.
- Write your own thoughts on a clipping below its `ingest:end` line. Nothing ever touches that.
- **Where it all comes from**: `Sources.md` lists your sources and how often to pull each.
  Ask Claude to "harvest" to set it up together, and to "prune" once a month to clear out
  what you never use (`python3 bin/ingest.py report` shows the list).

## Keeping it honest

`python3 bin/lint.py` checks the vault against its own templates and rules.
Errors block a commit; warnings are worth a look. One warning is about size: the files your AI
reads every session (`CLAUDE.md`, `Me.md`, `Now.md`, each skill) each have a budget in
`bin/vault.json`, and when one grows past it, ask your AI to compact it.
