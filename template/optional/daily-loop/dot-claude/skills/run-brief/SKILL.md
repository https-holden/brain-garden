---
name: run-brief
description: Carries out the owner's replies on today's brief. Reads the reply card under each item in Daily/<date>.md, does only the items that have a reply (go, a letter, or a short instruction), logs each action under ## Actions, and leaves every item without a reply for tomorrow. Use when the owner says "run my replies", "do the brief", "go through my replies", "run the brief", or invokes /run-brief [YYYY-MM-DD].
---

# Run the brief

The middle of the daily loop. `start-of-day` writes the brief with an empty reply card under
each item; the owner writes a short instruction in the cards they want handled, whenever they
have a minute; this skill does those and nothing else. The owner only decides. `$ARGUMENTS`
may name a date; the default is today.

## 1. Collect the replies

Read `## Brief` in `Daily/<date>.md`, `Now.md` and `Me.md`. For each item, its reply is the
text under its `**Reply:**` line, up to the next item. An item counts only when that text is
not empty and has no `Ran` line after it: a `Ran` line means it was already run, and a new
line written below a `Ran` line is a new reply.

What a reply means:

| Reply | Means |
|---|---|
| `go`, `yes`, `ok` | Do it as the item proposes (a Green item, or a Yellow item's only sensible option) |
| `A`, `B`, ... | Do that option. A letter followed by words is the option, changed as the words say |
| `skip` or `later` | Not today. Nothing happens; it carries over tomorrow |
| `mine` | The owner will do it. Nothing happens |
| `drop` | No longer wanted. Tick it and write `Ran HH:MM: dropped.` |
| a question | Answer it in the `Ran` line and in chat. No action |
| anything else | An instruction. Follow it as written |

Items with an empty card are left exactly as they are. They are not asked about, not nudged
and not done: an unanswered item is for tomorrow.

## 2. Say the plan, once

One numbered list in chat, one line per replied item: what you will do and the choice you
made where there was one. Mark any you will not do and why (below). Ask once; the owner
answers "go", or skips and edits by number. This is the "say how before you do" rule, done
for the whole brief in one go so it costs one answer.

## 3. Do them

In brief order. For each:

- **Inside the vault** (a note to write or fix, clippings to file, a link to bring in):
  do it, following `CLAUDE.md`.
- **Outside the vault**, through a connected tool: a message to another person is drafted and
  shown, and sent only if the reply said to send it. An event, task or reminder for the owner
  alone may be made. Never spend money, never delete anything outside the vault, never sign in
  or accept terms for the owner: those are Red whatever the reply says, so say so in the
  `Ran` line and leave the item to the owner.
- **A Red item with a reply**: follow the steps the reply gives, exactly; anything they leave
  open is a question back, not a guess.
- **Unclear**: if a reply could mean two things, ask in the `Ran` line and in chat instead of
  picking. It stays open.

Afterwards, under the item's reply, one indented line: `Ran HH:MM: what happened, with a
[[link]]`. Tick the item if it is finished; leave it unticked if it is waiting on the owner
(a draft to approve, a question). Then append one line to `## Actions` per thing done, as
`CLAUDE.md` says, with "Asked by" set to the owner's reply on that brief item.

## 4. Report

Three lines at most: what was done, what is waiting on the owner (with the item), and how
many items are left for tomorrow. Do not rewrite `Now.md` or `## Learned`, and do not touch
items without a reply; `end-of-day` reads the `## Actions` log in the evening.
