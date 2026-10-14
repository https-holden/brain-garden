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

## Daily use

@@DAILY_USE@@

## Finding things

`python3 @@VAULT_PREFIX@@bin/find.py <words>` lists the notes whose title, aliases, topics or
status have every word, one line each. Your AI starts every lookup with it. It reads an index
of your notes, `.paths/index.txt`, which keeps itself current and is committed, so its history
shows what the vault knows. Using ChatGPT? `python3 @@VAULT_PREFIX@@bin/find.py --all` prints
the whole index: save it as a file in your ChatGPT project, beside `CLAUDE.md`, `Rules.md`
and `Me.md`.

@@README_SECTIONS@@## Keeping it honest

`python3 @@VAULT_PREFIX@@bin/lint.py` checks the vault against its own templates and rules.
Errors block a commit; warnings are worth a look. One warning is about size: the files your AI
reads every session (`CLAUDE.md`, `Rules.md`, `Me.md`, `Now.md`, each skill) each have a budget in
`bin/vault.json`, and when one grows past it, ask your AI to compact it.
