# How it works

The version for over coffee: **harvest it, seed it, and then live in it.**

## Why a brain garden

An AI is only as useful as what it can find. Ask it about your own life or work and it knows
nothing, unless your notes, ideas, people and history are somewhere it can read, in a shape it
can move through quickly. A brain garden is that shape: plain text files, one idea per note,
every note linked to the people, topics and projects it touches. When you ask a question, the
AI does not search a pile, it walks the paths: from a topic page to the notes about it, from a
person to every meeting they were in, from a claim to its source. The more you put in, and the
better it is connected, the faster it finds the answer.

So it thrives on data. A thin garden is a pleasant notebook; a full one starts to think with
you.

The name is two ideas put together. The **brain** is the second brain: copious amounts of your
material, organized so an AI can pathfind through it. The **garden** is the part you walk
around in: tended, organized and good to look at, with paths you know, private corners that
are only yours, and, if you choose, shared beds that friends or a team tend with you.

## The loop

| | What happens | How |
|---|---|---|
| **Harvest** | Gather as much as you can from where your material already lives: notes apps, voice memos, articles, PDFs, email, old journals, photos of paper | The `harvest` interview finds your sources; `bin/ingest.py` brings them in; `Sources.md` keeps the list |
| **Seed** | Put it back into the vault in a meaningful way: filed, summarized, well named, linked to topics, people and your own notes | The librarian (`bin/librarian.py`, or "file my clippings") |
| **Live in it** | Use it every day: ask it questions, write in it, plan from it | "Start my day", your daily note, asking your AI anything |
| **Learn** | It improves its own process as you use it: what to harvest, how to file, which kinds of note it needs, what to pave and what to cut | "End of day" and the monthly "tend" |

Then round again. Every turn of the loop makes the next one cheaper: a better-filed garden is
easier to search, which makes it more useful, which makes you put more in.

### Learning from itself

The garden is meant to get better at being your garden. Every evening, `end-of-day` looks not
only at what you learned but at how the system did: a kind of note with no home, a topic that
should be split, a source that is not worth its time, a rule in `CLAUDE.md` or `Rules.md` that
keeps being broken. It proposes the smallest change, you approve it, and the reason goes in
`Decisions.md`.

This matters most in the **early days**. For the first month the evening loop asks one
question about the process every night, because that is when the structure is still finding
its shape. Once it is stable, it only speaks up when something rubs. Most gardens settle in a
few weeks.

## Three kinds of memory

Like your own memory, the garden keeps three timescales:

| | Where | Holds |
|---|---|---|
| **Short-term** | Today's note in `Daily/` | What is happening right now: the morning brief, your scribbles, what you learned today |
| **Mid-term** | `Now.md` | What is in flight: goals, active things, what you are waiting on, open questions. Rewritten every evening, every line dated |
| **Long-term** | The kinds of note (Notes, References, People, Clippings; Knowledge, Playbooks for work) | What is true, how things are done, who is who |

Things move down the tiers. A scribble in today's note becomes a line in `Now.md` if it will
take more than a day, and a note of its own once it settles into something you know. The
evening loop does the moving.

## Private and shared beds

All of a brain garden is private by default: it lives on your computer, and nothing leaves it
unless you send it. If you later want to grow part of it with other people (a family's recipes,
a team's know-how), the brain sends vines to its beds. A bed is a separate vault in its own git
repository, holding only the notes you chose for it, by topic or one by one. `bin/beds.py push`
sends them, with your private properties stripped and a check that no name on your
never-share list goes along; `bin/beds.py pull` brings back what the others changed. Your brain
stays the master: what a pull cannot settle on its own, it shows you instead of applying.
[sharing-a-vault.md](sharing-a-vault.md) shows how.

## Desire paths

In a park, the paths people actually walk wear into the grass, and good gardeners pave them.
The paths nobody takes grow over. A brain garden works the same way, the opposite of atrophy:
the routes your AI uses most get stronger, and the files it reads every time stay lean.

It starts by measuring, with no AI and nothing sent anywhere. Every lookup with `bin/find.py`
leaves a footstep, and `bin/paths.py` adds what Claude Code's own session logs and the git
history show, into a report that stays on your computer: the notes your AI reads most, what
each kind of session reads before it starts work, the files over their size budget, and the
lookups that keep finding nothing. Notes nobody reads are only counted, never listed: quiet is
fine.

Once a month, `tend` turns that report (and, with the ingest tools, `bin/ingest.py report`)
into one numbered list in seven groups. **Pave** the drafts your AI keeps reading: check each
against its source, shorten it, link it from its topic's "Start here". **Compact** a file every
session loads that grew past its budget, to about three quarters of it. **Split** a skill too
big to load every time. **Signpost** a lookup that missed, with an alias, a clearer title or a
missing note. **Move cold** old decisions and old daily notes into yearly folders, by date.
**Prune** what you collect but never use. **Keep** the rest, on purpose. You approve by
number, and every removed fact is accounted for. One line at the start of a session, and in
the morning brief, says when tending is due; otherwise there is no line at all.

## Where to go next

- Set one up: [START-HERE.md](../START-HERE.md)
- Find your sources: [harvesting-and-tending.md](harvesting-and-tending.md)
- The daily habit: [daily-loop.md](daily-loop.md)
