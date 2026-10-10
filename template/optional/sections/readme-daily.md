## Every day

- **Morning**: ask Claude "start my day" (the `start-of-day` skill). Today's note in `Daily/`
  gets a short checklist from `Now.md`, yesterday, and your calendar if it is connected. Each
  item says how much Claude can take: **green** (it can just do it), **yellow** (pick an
  option, A, B or C) or **red** (yours: it is new, or cannot be undone).
- **Reply when you have a minute**: under any item, write a short instruction in its
  **Reply** card: `go`, a letter, `skip`, `mine`, or a sentence. Then say "run my replies"
  (the `run-brief` skill). Claude does only those and leaves the rest for tomorrow.
- **During the day**: jot anything under `## Notes` in today's note. Tick what you finish.
  Everything Claude does for you gets one line under `## Actions`: what, why, what it chose,
  and who asked.
- **Evening**: "end of day" (the `end-of-day` skill). Claude proposes the notes worth keeping
  as a numbered list, you skip any by number, and it updates `Now.md`, your working memory.
