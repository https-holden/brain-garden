# Sharing part of a vault (beds)

A brain garden is private: it lives on your computer and nothing leaves it unless you send it.
When you want to grow part of it with other people (a family's recipes, a team's know-how),
your brain sends vines to its beds. Skip this until you actually need it.

## The idea

- **Your brain is the master.** It holds everything. A bed holds only the part you chose to
  share, and is rebuilt from your brain on every push.
- **A bed is a vault of its own.** It is a separate folder next to your vault, in its own git
  repository, with its own `CLAUDE.md`, `Rules.md`, templates, lint and find tool. The people
  you share it with open it in Obsidian like any vault, and never see your brain.
- **Nothing leaves unless a note or its topic says so.** A bed includes whole topics (every
  note in "Recipes"), and a single note can join with a `beds` property.
- **Edits come back.** `bin/beds.py pull` brings what the others changed into your brain. What
  it cannot settle on its own, it shows you instead of applying.
- **Walls are repositories, not folders.** Git cannot hide one folder from some people. A
  private bed is its own repository, and who can open that repository is the wall. Family
  recipes go in one bed, the team's procedures in another.

## What goes, and what never does

| Goes | Never goes, whatever its tags say |
|---|---|
| Every note whose `categories` hold a topic the bed includes | `Daily/` (your days) |
| Every note whose `beds` property names the bed (`beds: [recipes]`) | `People/` (your contacts) |
| The pages of the topics the bed includes | `Me.md`, `Now.md`, `Sources.md`, `Home.md` and every other root file |
| The images and files those notes embed | `.paths/` (the index, the find log, the sync state) |

On the way out, a push also:

- strips the properties you list for that bed (a `source` that names a private conversation,
  a personal `rating`), and the `beds` property itself;
- keeps only the bed's own topics in `categories`;
- rewrites links so they work on GitHub as well as in Obsidian: a link to a note in the bed
  becomes a relative link, and a link to a note that stays home becomes plain text;
- writes on each topic page a list of its notes, between `<!-- beds:list:start -->` and
  `<!-- beds:list:end -->`, so the bed reads well without Obsidian.

## Making a bed

Ask your AI ("set up a bed for my recipes, shared with my sister"), or do it by hand:

1. **Make an empty repository** for it, private, on GitHub or any git host. A bed only you use
   on this computer needs none.
2. **List the bed** in your vault's `bin/vault.json`, beside `kinds`:

   ```json
   "beds": [
     {"name": "recipes", "path": "../sam-recipes", "remote": "<the repository's URL>",
      "topics": ["Recipes"], "strip": ["source", "rating"]}
   ]
   ```

   `path` is where the bed lives, next to your vault. `remote` is optional.
3. **Choose what goes**: topics in `topics`, single notes with `beds: [recipes]`.
4. **Write your never-share list**: `bin/never-share.txt`, one word or phrase per line (a
   client, a friend's surname, a project's code name). A push stops while any note it would
   send contains one, and names the note and the word. The list is git-ignored, so it never
   leaves either.
5. **Look first, then send**: `python3 bin/beds.py push --dry-run` lists every note that would
   go. Then `python3 bin/beds.py push` makes the bed, commits there and pushes to the
   repository. Commit your brain too: `.paths/beds/recipes.json` records what was synced.
6. **Invite people** to the repository.

## Keeping it in step

| Command | What it does |
|---|---|
| `python3 bin/beds.py status` | Per bed: what it gets, when it last synced, what changed there since |
| `python3 bin/beds.py pull` | Brings the others' edits into your brain (`--dry-run` to look first) |
| `python3 bin/beds.py push` | Sends your brain's current version (`--dry-run` to look first) |
| `python3 bin/beds.py clone` | Fetches each bed with a `remote` that is not on this computer yet, next to your vault |

Add a bed's name to act on that one only (`push recipes`).

**Pull** takes an edit made in the bed back into your note, with your stripped properties and
your links put back. It reports, and never applies:

- a **conflict**: the note changed in your brain and in the bed since the last sync. Merge the
  bed's version in by hand, then `push --force`.
- a **deletion**: take the note out of the bed (drop its `beds` or its topic), or `push
  --force` to put it back.
- a **rename**: rename the note in your brain the same way, then push.
- a **new note**: copy it into your brain if you want it.

Pull never deletes a note in your brain.

**Push refuses** while your vault's lint has errors, while a note it would send holds a
never-share word, and while the bed has changes you have not pulled yet. `--force` overrides
only the last one, and the others' versions stay in the bed's git history.

## The other side: tending a bed

For the people you share with:

1. Clone the bed's repository (GitHub Desktop does it with no terminal) and open the folder in
   Obsidian, "Open folder as vault". It is a working vault: templates, topic pages, a
   `CLAUDE.md` for their AI, `bin/lint.py` and `bin/find.py`.
2. Write, edit and link notes as in any vault, run `python3 bin/lint.py`, then commit and push.
   An edit to a note goes back to the owner's brain on their next pull. A new note, a deletion
   or a rename is shown to the owner, who decides.
3. Keep a personal layer if they like: `Me.md`, `Now.md`, `Daily/` and `People/` are
   git-ignored in a bed, so notes there stay on their machine. For anything else private, list
   it in `.git/info/exclude`.

`CLAUDE.md`, `Rules.md`, `Templates/` and `bin/` in a bed come from the owner's brain and are
replaced on every push: rule changes go through the owner. So does the generated list on each
topic page.

## Rules that make a shared bed trustworthy

- **`status` on every claim**: `draft` (someone said it, nobody checked), `verified` (checked
  against the real thing), `stale` (contradicted by something newer). An AI writes drafts; a
  person promotes them.
- **`source` on every claim**: where and when it was learned, with a link and a date. When two
  notes disagree, the newer source wins. Strip it on the way out if it names something private.
- **No private names in a bed.** Write "a customer", "a client". The name goes in your own
  notes, and in `bin/never-share.txt`.
- **Connected accounts are read only.** Skills read Slack, email or calendars to brief and to
  learn, and never post, reply or change anything. Drafts are handed to the person.

## People who will not use Claude Code

- **On GitHub**, a bed reads well in the browser: the links work and every topic page lists its
  notes. Small edits can be made right there with the pencil button, and come back on the
  owner's next pull like any other.
- **In Obsidian alone**, a bed is a normal vault; clone it with GitHub Desktop.
- **With a chat AI**, make a Claude or ChatGPT project whose files are the bed's `CLAUDE.md` and
  `Rules.md`, the whole index (`python3 bin/find.py --all` in the bed), and the notes. Tell it to
  answer from the notes, prefer `verified`, hedge `draft`, ignore `stale`, and say how old the
  evidence is.
