# Obsidian in fifteen minutes

Everything you need to use your vault, and nothing you don't. Mac keys are shown; on Windows
use Ctrl where it says Cmd.

## The big idea

Obsidian is an app for reading and writing notes, and your notes are just text files in a
folder on your computer. That folder is called a **vault**. Nothing is locked inside an app or
a company's servers: if Obsidian disappeared tomorrow you would still have every word, and any
AI can read the files too. That is why this works so well with Claude or ChatGPT.

## Opening your vault

1. Open Obsidian.
2. Click **Open folder as vault** and choose the folder the setup made (for example
   `Documents/Obsidian/sam-brain`).
3. If it asks whether you trust the author, say yes: it is your own folder.
4. Open **Home** from the file list on the left. That is your starting page.

## The six things to know

**1. Links: `[[double square brackets]]`.** Type `[[` and start typing a note's name, then
press Enter. That makes a link, and clicking it opens the note. You can link to a note that
does not exist yet: the link shows faded, and clicking it creates the note. This is the whole
trick of a second brain: link generously, and the connections build themselves.

**2. Backlinks.** Every note knows what links *to* it. Open the right sidebar (the icon at the
top right, or Cmd+P and type "backlinks") to see them. Write `[[Maria]]` in ten different
notes and Maria's page lists all ten without you doing anything.

**3. Properties.** The grey box at the top of a note holds its properties: little labelled
fields like `created`, `author` or `categories`. They are how the vault sorts and finds notes.
Click a value to edit it. (In the file itself they are the lines between two `---` lines at
the top; that is called frontmatter.)

**4. Categories, not folders.** Each kind of note has one folder (Notes, People, Clippings and
so on), and that is all the folders you need. What a note is *about* goes in its `categories`
property as links, like `[[Health]]` or `[[Cooking]]`. Each topic has a page in `Categories/`
that lists every note about it, automatically. Resist making new folders.

**5. Templates.** Each kind of note has a template that fills in the right properties. Make a
new note in the right folder, then Cmd+P, type "insert template", and pick the one for that
kind. Daily notes use theirs by themselves.

**6. Bases (the tables).** A file ending in `.base` is a live table of notes, like a
spreadsheet that fills itself in. Your Home page and every topic page embed them. You never
have to update them: add a note with the right property and it appears.

## Everyday keys

| Keys | Does |
|---|---|
| Cmd+O | Jump to any note by typing part of its name |
| Cmd+P | The command palette: every action, searchable |
| Cmd+N | New note |
| Cmd+Shift+F | Search inside every note |
| Cmd+E | Switch between editing and reading view |
| Cmd+click a link | Open it in a new tab |

The calendar icon on the left opens today's daily note.

## A few more bits of Markdown

Notes are written in Markdown, which is plain text with a few symbols:

```
# Big heading           ## Smaller heading
**bold**   *italic*     - a bullet      - [ ] a checkbox
![[photo.jpg]]          shows an image (or any file) inside the note
![[Other note]]         shows another note inside this one
> [!note] A callout     a highlighted box
```

You do not need to memorise any of it: Obsidian shows it formatted as you type.

## The graph

Cmd+P, "open graph view": every note as a dot and every link as a line. Pretty, occasionally
useful for spotting clusters. The backlinks pane is where the real value is.

## Rules of thumb

- Write first, organise later. A messy note with links beats a perfect empty structure.
- One idea per note, titled as the idea ("Walking helps me think", not "Walking").
- Link the first mention of any person, place, book or project, even before its page exists.
- Dates are always written `2026-10-10` (year, month, day). It sorts correctly.
- Your AI keeps the vault tidy for you. Its rules are in the vault's `CLAUDE.md`, and it
  checks itself with `python3 bin/lint.py`.

## Where to learn more

- Obsidian's own help: https://help.obsidian.md
- The method this vault follows, by Obsidian's CEO: https://stephango.com/vault
