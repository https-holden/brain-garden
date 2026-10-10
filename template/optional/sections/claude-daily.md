## The daily loop

Two skills keep the three memory tiers moving, and both read connected tools read only:

- `start-of-day` (morning): reads `Now.md`, yesterday's note and today's calendar, email and
  chat if connected, and writes the `## Brief` checklist into `Daily/YYYY-MM-DD.md`.
- `end-of-day` (evening): reads the day's ticks and notes and what moved, proposes new or
  corrected notes as one numbered list, writes `## Learned`, rewrites `Now.md`, runs the lint.

A daily note is never rewritten after its day, except its `## Learned` that evening.
