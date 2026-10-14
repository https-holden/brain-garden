# 06: Tend and the nudge

**What to build:** The monthly `prune` skill becomes `tend`, shipped with every vault. It refreshes the ledger, reads the paths report (and the ingest report when the ingest tools are present) and proposes one numbered list in seven groups, numbering continuous, empty groups kept with a line saying why: Pave, Compact, Split, Signpost, Move cold, Prune, Keep. It carries the four corrections from the work vault's first pass: compaction aims at about 75% of budget; every Pave and Compact lists each removed fact with its destination or marks it dropped on purpose before the commit, checked by a fresh reviewer when the AI can start one; paved notes are recorded in the ledger and shown once under "Paved, waiting for your verify" as one batch question; Signpost turns repeated misses into an alias, a clearer title or a missing note. Move cold follows rules and dates: old `Decisions.md` sections to `Decisions/Archive YYYY.md` with a pointer, old daily notes to `Daily/YYYY/`, never-walked clippings only as a count while the ledger is under 60 days old. Approved items only, one commit each, then the paths script with `--pass` (records the date, saves a dated, committed copy of the report) and lint. The paths script's `due` mode prints one line, or nothing, when the refresh is over 7 days old, the last pass over 30 days old or missing, or a file is over budget; a Claude Code SessionStart hook runs it on startup and `start-of-day` puts its line in the brief. The budget warning names `tend`. Every mention of prune across the repo and the template changes; the roadmap strikes desire paths, "how it works" and the README describe them as landed, and the hero image and its alt text stop saying "coming". Write the skill with the writing-for-agents skill loaded. See the spec, "Tend and the nudge".

**Blocked by:** 02 (Budgets and the CLAUDE.md split), 03 (Hub signage), 05 (Footsteps ledger and report)

**Status:** done

- [x] A planted vault has `tend` and no `prune`; no file in the repo or a planted vault still sends the reader to prune
- [x] The skill reads only the reports to propose, names nothing dormant, lists the seven groups in order, and states the four corrections as steps it follows
- [x] `--pass` records the date, saves the dated report that git tracks, and a paved note recorded in the ledger is listed under "Paved, waiting for your verify" and not under drafts wanting paving
- [x] Due mode at a fixed today: nothing when fresh, the line at 8 days since refresh, at 31 days since the pass or with no pass, and with a file over budget; nothing in a bed checkout
- [x] Planting merges the SessionStart hook into `.claude/settings.json` without disturbing what is there; `start-of-day` runs due mode
- [x] Lint's budget warning names `tend`; ROADMAP, "how it works", README, START-HERE, AGENTS.md and the hero image say desire paths have landed
- [x] `tools/check.py` green under both Pythons; starter-vault rebuilt; no dashes; nothing personal

**Outcome (2026-10-14):** Merged 531ffb0, parent fixes 35cd14a (hook prints systemMessage JSON via `due --hook`; quoted path), follow-up 7b15000. Decision: with no pass ever, the nudge waits until the ledger's first refresh is 30 days old, so a new vault is not nagged. Move cold cutoff is `cold_days` in bin/vault.json (90).
