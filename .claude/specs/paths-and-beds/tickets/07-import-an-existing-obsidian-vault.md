# 07: Import an existing Obsidian vault

**What to build:** An existing Obsidian vault is one more source. `ingest.py add --vault <path>` recognises it and, without a mapping, writes nothing and prints a proposed folder-to-kind mapping as a numbered list with counts. With a mapping it imports as the owner's writing (the `--mine` rules), except folders mapped to `Clippings/`. It keeps `categories` (making missing topic pages in the hub shape), `created` (frontmatter first, else the file's birth time), `aliases`, `tags` and the other properties; finds `![[...]]` embeds anywhere in the source vault and copies them flat into `Attachments/`, renaming clashes and rewriting the embeds; skips and counts `.obsidian/`, `.trash/`, the templates folder, `.base` and `.canvas` files; renames a clashing note and rewrites every link to it in the imported notes, leaving links to notes that did not come along as breadcrumbs; sends date-titled notes to `Daily/` when the mapping says so. `--sample N` and `--dry-run` work as their names say, and `--via` stamps `Sources.md`. The source vault's own rule files are not imported; the summary says they exist and asks the AI to propose rules for `Decisions.md` and `Me.md` as a numbered list. The harvest skill and the bringing-things-in guide gain the case, sample first. See the spec, "Importing an existing Obsidian vault".

**Blocked by:** None (can start immediately; if 03 has landed, new topic pages use the hub shape)

**Status:** done

- [x] A fixture vault built in the check (two content folders, a date-titled note, a `![[x.png]]` embed whose image sits in a subfolder, a name clash with an existing note, a templates folder, a `.base`, a `.canvas`, `.obsidian/`) gets a proposed mapping and nothing written when no mapping is given
- [x] With a mapping: notes land in the mapped kinds, the date note in `Daily/`, categories and created dates kept, topic pages made, the image in `Attachments/` and the embed resolving, the renamed note reachable from every link that pointed at it
- [x] Nothing comes in from the skipped places, and the summary counts them
- [x] `--sample 2` imports two notes and stops; `--dry-run` writes nothing; `--via` stamps the source row
- [x] Lint passes on the vault after the import; the index includes the imported notes
- [x] The harvest skill and the bringing-things-in guide describe importing an old vault; starter-vault rebuilt if the template changed
- [x] `tools/check.py` green under both Pythons; no dashes; nothing personal

**Outcome (2026-10-14):** Merged d8f749c, review fixes c96560a. `--vault`, `--map src=Kind` (`.` root, `dates=Daily`), `--sample`, `imported_from` property for re-runs. Unverified: Windows paths.
