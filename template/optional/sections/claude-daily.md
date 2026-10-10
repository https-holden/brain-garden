## The daily loop

Three skills keep the three memory tiers moving. The morning and evening ones read connected
tools read only; `run-brief` acts only on what the owner replied:

- `start-of-day` (morning): reads `Now.md`, yesterday's note and today's calendar, email and
  chat if connected, and writes the `## Brief` checklist into `Daily/YYYY-MM-DD.md`. Each item
  is sorted Green (Claude can just do it), Yellow (Claude offers lettered options) or Red
  (new, or not undoable: Claude will not guess), and gets an indented `**Reply:**` card.
- `run-brief` (any time, "run my replies"): does only the items whose card has a reply (`go`,
  a letter, or a short instruction), writes a `Ran HH:MM:` line under each, and logs every
  action under `## Actions`. Items without a reply wait for tomorrow and are never chased.
- `end-of-day` (evening): reads the day's ticks, replies, notes and `## Actions`, proposes new
  or corrected notes as one numbered list, writes `## Learned`, rewrites `Now.md`, runs the
  lint.

A daily note is never rewritten after its day, except its `## Learned` that evening. Reply
cards are the owner's: only `run-brief` writes in them, and only its `Ran` lines.
