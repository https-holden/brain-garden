# The method, rule by rule

A digest in our own words of https://stephango.com/vault and the posts it links. His vault
template is https://github.com/kepano/kepano-obsidian. Read the originals for his wording.

## Stance

- Bottom-up: structure emerges from links and properties, it is not designed up front.
- File over app (https://stephango.com/file-over-app): a vault is a folder of plain files you
  control, in formats that will still open in decades. Everything else follows from that.
- Non-dogmatic: take the parts that serve you.

## Folders

Very few, none nested, rarely navigated. Navigation is the quick switcher, backlinks and links
inside notes. Organisation is the `categories` property, and each category has an overview
page built with Bases.

| Folder | Holds |
|---|---|
| root (or `Notes/`) | What you wrote, or what is about you |
| `References/` | Things outside your head: books, films, places, people. Named by the thing's exact title |
| `Clippings/` | What other people wrote |
| `Daily/` | `YYYY-MM-DD` notes that exist to be linked to |
| `Attachments/`, `Templates/` | Admin folders, kept out of navigation |
| `Categories/` | One overview page per category |

## Links

- Link the first mention of a thing, always.
- An unresolved link is a breadcrumb for a future connection. Make the page when it earns one.
- The payoff compounds: you can trace where an idea came from and what it branched into.

## Properties and templates

- Nearly every note starts from a template; it is the lazy way to leave findable information.
- One template per category, properties at the top. Families: dates (`created`, `start`,
  `end`, `published`), people (`author`, `people`), themes (`genre`, `type`, `topics`),
  places, ratings.
- Names and values are reusable across categories, so one Base can cut across kinds.
- Templates compose: two can be applied to one note.
- Short names (`start`, not `start-date`).
- Default to a list if there could ever be more than one value.
- `.obsidian/types.json` records each property's type.

## Ratings

Integers 1 to 7: 7 perfect, 6 excellent, 5 good, 4 passable, 3 bad, 2 atrocious, 1 evil.

## Evergreen notes

(https://stephango.com/evergreen-notes; the term is Andy Matuschak's,
https://notes.andymatuschak.org/Evergreen_notes)

- One idea per note. Complex thinking is built from small composable ideas.
- The title is the idea, stated so you could use it in a sentence. A bare topic word is a
  topic hub, not an evergreen note.
- Short is fine. They stack: one note can be built on another.
- Matuschak's principles: atomic; organised by concept, not by source; densely linked;
  associative rather than hierarchical; written for yourself first.

## Review

- Fragments through the day, compiled every few days, reviewed monthly, then yearly.
- A "random revisit" every few months: random note, shallow local graph, fix links and style.
- He does this maintenance by hand, on purpose (https://stephango.com/understand): doing it is
  how you learn your own patterns. An assistant that tidies a vault should propose, not
  silently rewrite.

## Style

Write your rules down. A consistent style collapses hundreds of future decisions into one:
pluralise every category and you never again wonder how to name the next one.
