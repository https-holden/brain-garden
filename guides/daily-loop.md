# The daily loop

How the vault learns from your days without you filing anything. This is the habit that turns
a folder of notes into a second brain.

## Three kinds of memory

| | Where | What it holds | Who changes it |
|---|---|---|---|
| **Short-term: the log** | `Daily/YYYY-MM-DD.md` | What happened today: the brief, your scribbles, what was learned | You during the day; it is never rewritten after |
| **Mid-term: working memory** | `Now.md` | What is in flight: goals, active things, what you are waiting on, open questions. Every line dated | Rewritten every evening |
| **Long-term: what you know** | the kind folders | What is true, how things are done, who is who | Grows a note at a time, through you or a numbered list you approve |

The idea is the same as your own memory: the day's raw experience, a short list of what is on
your mind, and what you actually know. Facts move from the log into long-term notes; `Now.md`
just keeps the thread.

## Morning: start of day (two minutes)

In the Claude desktop app (Code tab, your vault's folder), say **"start my day"**. Claude
reads `Now.md`, yesterday's note, and, if you have connected them in Claude's settings, your
calendar, email or chat. Then it writes a short checklist under `## Brief` in today's note.
It only ever reads your accounts; it never sends, replies or accepts anything.

## During the day

Open today's note (the calendar icon) and jot things under `## Notes`: what you did, what you
found out, a link, a name. Tick the brief's boxes as you go. Messy is fine.

## Evening: end of day (five minutes)

Say **"end of day"**. Claude rereads the day and proposes, as one numbered list, what the
vault should now know: a new note for an idea, an update to a person, a correction to
something that turned out wrong, a link to bring in. You answer something like "skip 3, change
5 to say ...", and it applies the rest. Then it rewrites `Now.md` and runs the vault's check. Last, it asks how the garden itself did
today (a note with no home, a source bringing in noise, a step that felt slow) and proposes one
small fix. It does this every evening for the first month, while the garden finds its shape,
and after that only when something rubs.

Because everything is a proposal you approve, nothing gets into your vault that you did not
see. And because the vault is a git repository, any change can be undone.

## With ChatGPT instead

ChatGPT cannot open your files, so you carry them over. The prompts are in
[prompts-for-any-ai.md](prompts-for-any-ai.md): paste `Now.md` and today's note in the evening,
and it gives back the notes to create and the new `Now.md`.

## Weekly (optional)

Once a week, ask for a review: "Read the last seven daily notes and Now.md. What keeps coming
up that has no note yet? What in Now.md is stale?" It is the cheapest way to see your own
patterns.
