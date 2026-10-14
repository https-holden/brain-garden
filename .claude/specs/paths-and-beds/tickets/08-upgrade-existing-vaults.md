# 08: Upgrade existing vaults

**What to build:** A vault planted earlier receives every improvement. Planting writes a manifest in the vault's `bin/` (the seed's commit and date, and a hash of every seed-owned file: the bin scripts and their docs, the shipped skills and their references, the general Bases, the CSS snippet, the bundled plugins). `build_vault.py --upgrade --dest <vault>` replaces a seed-owned file whose hash still matches the manifest, writes `<file>.new` beside one the owner edited and lists it, adds missing files and folders, adds new keys to `bin/vault.json` and new lines to `.gitignore` without changing existing ones, merges settings (hooks, permissions), writes `Rules.md` when missing and `CLAUDE.md.new` when the template changed (for the AI to merge with the owner as a numbered list), and updates the manifest. It never touches a note, a kind template or a root document's content. `--dry-run` prints the plan. A vault with no manifest is compared with the current seed: identical files are recorded as seed-owned, different ones get `.new`. The README and AGENTS.md say how to update a vault. See the spec, "Upgrade".

**Blocked by:** 01 to 07 (it must know every file they add)

**Status:** ready-for-agent

- [ ] Planting writes the manifest; a rerun of the builder on the same vault leaves it unchanged
- [ ] On a vault planted from the seed as it was before ticket 01 (built in the check from an older commit, or simulated by removing the new files and the manifest): upgrade adds the find tool, index, paths and beds scripts, `tend`, `Rules.md`, the budgets keys, the `.gitignore` lines and the SessionStart hook
- [ ] A seed-owned file the owner edited is left alone with a `.new` beside it, listed in the output; an unedited one is replaced
- [ ] Every note's bytes are identical before and after; `--dry-run` changes nothing; a second upgrade is a no-op
- [ ] Lint passes on the upgraded vault (budget warnings allowed)
- [ ] README and AGENTS.md describe updating a vault
- [ ] `tools/check.py` green under both Pythons; no dashes; nothing personal
