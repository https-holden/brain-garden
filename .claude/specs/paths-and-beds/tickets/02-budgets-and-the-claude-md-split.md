# 02: Budgets and the CLAUDE.md split

**What to build:** The template's `CLAUDE.md` becomes an index (what the vault is, how the AI works here, the one recipe from 01, and what to read before what) and the detail moves to a visible `Rules.md` at the vault root: the vault map, the kinds table, adding a kind, the drift check, the conventions, and the optional sections the builder splices in, each with a one-line pointer left in `CLAUDE.md`. Budgets go in `bin/vault.json` (`CLAUDE.md` 9,000 chars, `Rules.md` 20,000, `Me.md` 5,000, `Now.md` 12,000, every `SKILL.md` 12,000, a file named in the table overriding the skill budget). Lint warns, never errors, on a file over budget, naming the file, its size and budget, and suggesting the AI compact it to about 75%. The template's `Decisions.md` gains "Every auto-loaded file is an index, never the detail". A fresh vault of either preset is under every budget with each file at or below 75%. See the spec, "Budgets and the CLAUDE.md split".

**Blocked by:** 01 (Index, find and the one recipe)

**Status:** ready-for-agent

- [ ] Both presets plant with `CLAUDE.md` at or below 6,750 chars and `Rules.md` at or below 15,000, and every token the builder fills lands in the right file
- [ ] `CLAUDE.md` tells the AI to read `Rules.md` before writing or restructuring a note, touching a template, a Base or a skill, and before a first commit; nothing in `Rules.md` is duplicated in `CLAUDE.md`
- [ ] Lint on a fresh vault prints no budget warning; with `Now.md` pushed past 12,000 chars it prints one warning with the size, the budget and the compact suggestion, and exits 0
- [ ] A budget set for one skill in `bin/vault.json` wins over the skill budget for that skill only
- [ ] The decision entry is in the template's `Decisions.md`, dated with the planting date
- [ ] The repo's AGENTS.md, the chat-AI prompts guide (project files: `CLAUDE.md`, `Rules.md`, `Me.md`) and the template `Readme.md` name `Rules.md`; every skill that said "read CLAUDE.md" for detail now says `Rules.md` where that is what it means; starter-vault rebuilt
- [ ] `tools/check.py` green under both Pythons, with checks for the fresh-vault budgets and the warning; no dashes; nothing personal
