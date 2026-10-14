# 05: Footsteps ledger and report

**What to build:** A paths script in every vault's `bin/` turns footsteps into a local, git-ignored ledger and a one-screen live report in `.paths/`. Read sources, each optional: Claude Code transcripts, found by the vault's path slug under every Claude config folder on the machine (the configured one, the default one and any sibling config folder named like it, plus the main checkout's slug for a worktree), and the find log from 01. The write source is the git log when the vault is a repo. Footstep rules, session typing (first skill or slash command by name, else misc, no mapping table), first useful action (first write to a vault file or first MCP call of any kind) and fixed load port from the work vault's paths script, generically. Incremental by transcript mtime; hot and dormant on reads only; nothing ever written to a note. The report: header with refresh date, last pass, window and the sources found, hot files, fixed load per session type, dormant counts per folder, the size-budget table from 02, drafts wanting paving, paved and waiting for verify (empty until 06), and signposts (queries that missed twice or more in 30 days). With no read source it says reads are not measured and shows writes, inbound links and budgets only. `end-of-day` runs the refresh after lint, quietly. Silent in a bed checkout. See the spec, "Footsteps, the ledger and the report".

**Blocked by:** 01 (Index, find and the one recipe)

**Status:** ready-for-agent

- [ ] Tiny scrubbed fixture transcripts are checked in with the tests and cover: a Read, a Bash cat with a relative path, a grep hit, a folder listing, a slash-command session, a Skill session, a misc session, a write before the first MCP call, a subagent transcript, and transcripts in two config folders
- [ ] The ledger's counts, last dates, per-type counts and average fixed load match the fixtures; git writes appear with their own kind; find-log hits appear as `find` footsteps
- [ ] A second run with nothing new reads no transcript and leaves the ledger unchanged
- [ ] The report fits one screen, names its sources, lists dormant only as counts, and shows signposts from repeated misses in the find log
- [ ] With no transcripts, no find log and no git, the report says reads are not measured and still shows budgets; nothing errors
- [ ] The ledger and the live report are git-ignored; no note is created, edited or moved by the script
- [ ] `end-of-day` runs the refresh; the vocabulary (footstep, path, hot, dormant, fixed load) is in `Rules.md` conventions
- [ ] `tools/check.py` green under both Pythons; no dashes; nothing personal, including in the fixtures
