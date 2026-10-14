# @@VAULT_NAME@@

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
- **Home and every topic page open with "Start here"**: 3 to 7 links you pick, to the notes
  worth reading first. The table below lists everything. A new topic page starts with the
  heading and no links, and the monthly tend adds a note there once it is checked and short.

## Daily use

@@DAILY_USE@@

## Finding things

`python3 @@VAULT_PREFIX@@bin/find.py <words>` lists the notes whose title, aliases, topics or
status have every word, one line each. Your AI starts every lookup with it. It reads an index
of your notes, `.paths/index.txt`, which keeps itself current and is committed, so its history
shows what the vault knows. Using ChatGPT? `python3 @@VAULT_PREFIX@@bin/find.py --all` prints
the whole index: save it as a file in your ChatGPT project, beside `CLAUDE.md`, `Rules.md`
and `Me.md`.

Every lookup leaves a footstep. `python3 @@VAULT_PREFIX@@bin/paths.py` gathers them, with
Claude Code's own session logs and the git history when there are any, into
`.paths/report.md`: the notes your AI reads most, what each kind of session reads before it
starts work, the files near their size budget, and the lookups that keep finding nothing. It
never changes a note, and the report stays on this computer.

Once a month, say "tend". Your AI reads that report and proposes one numbered list: check and
shorten the drafts it keeps reading, compact the files that grew, add the aliases your lookups
missed, move what has gone cold. It changes only the numbers you approve. When tending is due,
one line says so as Claude Code starts, and at the top of the morning brief if you use one.

@@README_SECTIONS@@## Keeping it honest

`python3 @@VAULT_PREFIX@@bin/lint.py` checks the vault against its own templates and rules.
Errors block a commit; warnings are worth a look. One warning is about size: the files your AI
reads every session (`CLAUDE.md`, `Rules.md`, `Me.md`, `Now.md`, each skill) each have a budget in
`bin/vault.json`, and when one grows past it, say "tend" and your AI compacts it to about three
quarters of its budget.
