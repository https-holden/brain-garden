# Decisions

The dated log of why the vault's rules are what they are. Newest first. A rule changed in
`CLAUDE.md` or `Rules.md` gets its entry here in the same session. Corrections are appended,
never edited over: the wrong claim and the date it was believed are both evidence.

## 2026-10-10 Every auto-loaded file is an index, never the detail

- A file the AI loads without asking (`CLAUDE.md`, `Me.md`, `Now.md`, each skill's
  `SKILL.md`) points at detail and holds none. `CLAUDE.md` is how to work and how to look
  things up; where things go and the conventions are in `Rules.md`, read before writing.
- Detail is pulled one layer at a time: an index, then the page it names, then that page's
  sources. History is a verdict plus a pointer, never the whole story retold.
- Each has a budget in characters in `bin/vault.json`, and the lint warns when one is over.
  The fix is to compact it to about 75% of its budget, keeping every fact.

## 2026-10-10 Planted from Brain Garden

- Second-brain archetype: folder per kind, `categories` links for topics, one template and one
  Base per kind, a deterministic lint whose schema is the templates.
- Kinds at the start: Notes/ References/ People/ Clippings/ Daily/
- (fill in: what the interview decided. Who reads the vault, what is private, what is
  shareable, which plugins and why.)
