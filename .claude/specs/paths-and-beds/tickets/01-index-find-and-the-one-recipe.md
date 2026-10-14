# 01: Index, find and the one recipe

**What to build:** Every planted vault gets a find tool in `bin/` that builds and queries a committed index in `.paths/` (one line per note in every kind folder and `Categories/`: `Folder/title :: aliases :: categories :: status`, sorted by folder then title, case-insensitive; `Daily/`, `Templates/`, `Attachments/` and root files left out). `find <words>` prints the lines where every word matches, stale excluded unless `--stale`; `--topic <Topic>` lists one topic's notes; `--all` prints the whole index for a chat AI. The index rebuilds itself when missing, older than the newest indexed note, or when the file set differs; lint compares content and rewrites a stale index with a line saying so (no error); ingest and the librarian rebuild it after writing. Every query, with its hit count and matched paths, is appended to a git-ignored find log in `.paths/`. The template's lookup recipe becomes: (1) the find tool, (2) frontmatter grep, (3) full-text grep, the rest of the recipe text kept; every shipped skill that looks things up points at "the one recipe in `CLAUDE.md`" instead of restating it, and `tools/check.py` fails when a shipped skill restates the recipe or lists kind folders to find notes. The chat-AI guide tells a ChatGPT user to add the `--all` output to their project. See the spec, "The index and the one recipe".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Both presets and a custom vault plant with the find tool and an index whose lines match their notes, aliases and categories included, empty fields kept as empty slots
- [ ] `find` with two words returns only lines matching both; a stale note is left out, and shown with `--stale`; `--topic` returns exactly that topic's notes; `--all` prints the index
- [ ] A note added by hand (no script run) is found by the next `find`, because the index rebuilt; lint rewrites an index edited out of shape and says so, exit 0
- [ ] The find log gains one line per query, with the hit count and matched paths; a no-hit query is recorded as a miss; the log and nothing else in `.paths/` except the index is git-ignored
- [ ] `ingest.py add` and the librarian leave the index current
- [ ] The template `CLAUDE.md` recipe names the find tool as step 1; no shipped skill restates the steps or lists kind folders, and `check.py` has a check that fails if one does
- [ ] Vault map, `Readme.md` and the chat-AI prompts guide mention the index and `--all`; starter-vault rebuilt
- [ ] `tools/check.py` green under `python3` and `/usr/bin/python3`; no dashes; nothing personal
