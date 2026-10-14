## Bringing things in

Anything someone else wrote (articles, PDFs, recipes, emails, screenshots) goes in
`Clippings/`, so you can always tell your thinking from what you collected.

- **From the web**: install the Obsidian Web Clipper browser extension and import the
  template from https://github.com/https-holden/brain-garden
  (`guides/web-clipper-template.json`). One click saves a page here.
- **Files and links**: `python3 bin/ingest.py add <file, folder or link>`. Your own old
  writing: add `--mine`. A list of links: `--links links.txt`.
- **An Obsidian vault you already have**: `python3 bin/ingest.py add --vault <its folder>`
  shows which of its folders would go where, and copies nothing until you agree.
- **Filing**: `python3 bin/librarian.py` has Claude file everything new (a summary, a good
  name, topics, links). With ChatGPT instead: `python3 bin/librarian.py --paste`, paste into
  the chat, save its answer to a file, then `python3 bin/librarian.py --apply <file>`.
- Write your own thoughts on a clipping below its `ingest:end` line. Nothing ever touches that.
- **Where it all comes from**: `Sources.md` lists your sources and how often to pull each.
  Ask Claude to "harvest" to set it up together. The monthly "tend" clears out what you never
  use (`python3 bin/ingest.py report` shows the list).
