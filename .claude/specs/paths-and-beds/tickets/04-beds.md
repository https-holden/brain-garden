# 04: Beds

**What to build:** The brain is the master and sends vines to its beds. A beds script in every vault's `bin/`, inert until a bed is configured in `bin/vault.json` (name, sibling path, optional remote, included topics, properties to strip), with `status`, `push`, `pull` and `clone`, and `--dry-run` on the writing ones. A note goes to a bed when its `beds` property names it or one of its `categories` is an included topic; `Daily/`, `People/`, `Me.md`, `Now.md`, `Sources.md` and `.paths/` never go; embedded attachments go with their notes. Push strips the configured properties, turns wikilinks into relative Markdown links (links leaving the bed become plain text), writes a generated list of notes on each topic page in the bed between markers, keeps the bed a working vault (its own `CLAUDE.md`, `Rules.md`, templates, Bases, lint and find tool, and a bed marker at its root), commits in the bed and pushes when it has a remote. Push refuses while an outgoing note contains a word from the git-ignored `bin/never-share.txt`, while lint has errors, or (unless forced) while the bed has commits not yet pulled. Pull brings bed-side edits back (stripped properties re-inserted, links converted back) and reports deletions, renames, conflicts and new files without applying them; sync state per bed is committed in the brain. Clone fetches configured beds with a remote that are not on disk, as siblings. The sharing guide is rewritten around this model (private beds as their own repos, the collaborator's side, people without Claude Code), and "how it works" says the brain sends vines to its beds. Port the mechanisms of the work vault's two-way sync generically. See the spec, "Beds".

**Blocked by:** 02 (Budgets and the CLAUDE.md split)

**Status:** done

- [x] With no bed configured every command says so and writes nothing
- [x] Two beds configured in a planted vault: push sends exactly the notes tagged for each bed or in an included topic, plus their attachments, and never a daily note, a person or a root document, whatever its tags
- [x] An outgoing note has the configured properties stripped, links converted (in-bed links resolve as relative paths, out-of-bed links are plain text), and each bed topic page lists its notes between markers
- [x] The bed opens as a vault: its lint passes and its find tool works; the paths script and the nudge are silent there
- [x] A word from `never-share.txt` in an outgoing note stops the push and names the note; `--dry-run` writes nothing
- [x] An edit made in the bed comes back with pull, properties re-inserted and links converted back; an edit on both sides is reported as a conflict and applied to neither; a deletion is reported, not applied; push refuses over unpulled bed commits unless forced
- [x] `clone` fetches a configured bed from a local bare repo standing in for a remote
- [x] The sharing guide, "how it works", README and the template `Rules.md` describe beds; starter-vault rebuilt
- [x] `tools/check.py` green under both Pythons; every git call in the checks strips `GIT_` variables; no dashes; nothing personal

**Outcome (2026-10-14):** Merged 059f4ff, hardening 9908525. Two review rounds: symlinks never followed, nothing from the bed is executed, frontmatter links and file names checked for leaks, bed path must be outside the brain, pull never changes bed membership. Deviation accepted: `categories` stays as `[[Topic]]` in the bed (only the bed's own topics). Unverified: real GitHub remotes, Windows.
