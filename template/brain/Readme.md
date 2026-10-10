# @@VAULT_NAME@@

The human guide. `CLAUDE.md` holds the operating rules a model follows, `Decisions.md` is the
dated log of why the rules are what they are.

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

@@README_SECTIONS@@## Keeping it honest

`python3 @@VAULT_PREFIX@@bin/lint.py` checks the vault against its own templates and rules.
Errors block a commit; warnings are worth a look.
