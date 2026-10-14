# 03: Hub signage

**What to build:** Hubs speak plain text. `Home.md` and every page in `Categories/` carry a `## Start here` section of 3 to 7 hand-picked plain wikilinks above their Base embeds; a new topic page starts with the heading and no links, and Home's list names the main topics. Lint warns when a hub whose topic has three or more notes has no plain wikilink outside its embeds (Home once the vault has three topic pages). `Rules.md` describes the shape of a hub and that `tend`'s Pave adds to "Start here"; the topic template, the kepano-method skill's references where they describe topic pages, and the librarian's instructions for making a topic page follow the new shape. See the spec, "Hub signage".

**Blocked by:** 02 (Budgets and the CLAUDE.md split), since it writes into `Rules.md`

**Status:** done

- [x] A planted vault's Home and topic template carry `## Start here` above the embeds
- [x] A topic page made by the librarian or by ingest has the heading
- [x] Lint warns on a topic with three notes and no plain link outside embeds, stays silent on one with a link, on one with fewer than three notes, and on Home until three topic pages exist
- [x] `Rules.md` and the template `Readme.md` describe hub signage in a few lines; starter-vault rebuilt
- [x] `tools/check.py` green under both Pythons with the lint cases above; no dashes; nothing personal

**Outcome (2026-10-14):** Merged 7cf7281, review fixes 61db9d5 (Start here matched in any case and heading level). Home's check counts only links to topic pages.
