# Brain Garden

This repo sets people up with an Obsidian second brain. Two kinds of session open here:

- **Someone setting up their own vault** (often a beginner sent this link by a friend). Follow
  `AGENTS.md`: one step at a time, plain words, never ask for a password or token. Their vault
  goes in its own folder (by default `~/Documents/Obsidian/<name>-brain`), never inside this
  repo, and `setup/mac.sh --name <Name> --preset personal|work` makes it without prompts.
  Once it exists, that vault's own `CLAUDE.md` is the contract, not this file.
- **Changing the seed itself.** The rules below.

## Changing the seed

- `template/` is what a vault is built from, with `@@TOKENS@@` filled by
  `setup/build_vault.py`. `template/brain/` is always copied; `template/optional/` holds the
  pieces a flag adds and the `sections/` spliced into a vault's `CLAUDE.md` and `Readme.md`;
  `template/plugins/` are the optional home-made Obsidian plugins.
- Everything a vault runs is Python standard library and must work on Python 3.9 (what Apple's
  Command Line Tools ship). `pypdf` is the one optional extra, and only for PDF text.
- `starter-vault/` is generated: never edit it by hand. After changing `template/` or
  `build_vault.py`, run `python3 tools/build_starter.py`.
- Run `python3 tools/check.py` before committing (also with `/usr/bin/python3` when touching
  scripts). It needs no network and no AI.
- The brain template started as the second-brain archetype of the sister repo
  ObsidianVaultSeed (roadmap and lexicon vaults for code projects). The two now evolve
  separately; port a fix across by hand when it applies to both.
- Nothing personal or employer-specific goes in this repo: no real names, clients, companies,
  hostnames or account ids in the template, guides or examples. "Sam" and "Acme" are the
  examples.
- No en or em dashes in any file (the check scans the docs).
- The headless librarian's permission rules: file writes of every kind are matched by
  `Edit(...)` rules (there is no `Write(...)` rule), and `--restricted` is added only when the
  installed `claude` supports it.
