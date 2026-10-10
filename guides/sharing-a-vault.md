# Sharing a vault with a team (the garden pattern)

A personal second brain is for one person. This is how the same structure scales to a team
without anyone's private notes leaking, learned from a work vault that was opened up to a
company. Skip this until you actually need it.

## Two layers, one folder

| | Shared layer (the garden) | Personal layer (your brain) |
|---|---|---|
| Holds | What is true for everyone: how things work, procedures, references, shared clippings, topic pages, templates, skills | Who you are (`Me.md`), working memory (`Now.md`), your days (`Daily/`), your contacts, anything naming a customer or a private person |
| Lives in | A git repository everyone can pull from and push to | The same folder on your machine, listed in `.gitignore` so git never sends it |
| Written | Third person, one claim per note, with a `source` and a `status` | However you like |

Each person clones the shared repo and adds their own personal layer next to it. The result
is their own brain: the team's knowledge plus their private context, in one vault. A
`.gitignore` like this keeps the personal part home:

```
Me.md
Now.md
Daily/
People/
```

## Rules that make it trustworthy

- **`status` on every claim**: `draft` (someone said it, nobody checked), `verified` (checked
  against the real thing), `stale` (contradicted by something newer). An AI writes drafts; a
  person promotes them.
- **`source` on every claim**: where and when it was learned, with a link and a date. When two
  notes disagree, the newer source wins.
- **No private names in the shared layer.** Write "a customer", "a client". The name goes in
  your personal notes.
- **A check before every push.** The vault's `bin/lint.py` runs before committing; add checks
  for whatever must never be shared (a list of client names, internal hostnames).
- **Walls are repositories, not folders.** Git cannot hide one folder from some people. A team
  that needs private notes gets its own repo, cloned next to the shared one.
- **Connected accounts are read only.** Skills read Slack, email or calendars to brief and to
  learn, and never post, reply or change anything. Drafts are handed to the person.

## Onboarding someone

An init skill (a `SKILL.md` in `.claude/skills/`) does it in ten minutes: clone the repo, ask
four questions (where they will ask questions, whether they use Obsidian, what topics come to
them, what they can access), write their `Me.md` and `Now.md` from templates, and confirm with
`git check-ignore` that the personal files will never be committed. The daily loop
(`start-of-day`, `end-of-day`) then works the same for everyone, and `end-of-day` ends by
offering to push the shareable notes it drafted. That is how the shared garden grows: each
person's day feeds it.

Every shared skill opens with a `## Who should run this` section saying who it is for and what
access it needs, and a `Skills.md` page lists them all.

## People who will not use Claude Code

Give them a Claude project (or a ChatGPT project) whose knowledge is the shared repo, and a
short instruction: answer from the notes, prefer `verified`, hedge `draft`, ignore `stale`,
say how old the evidence is, and never name a customer. They get the answers; the daily loop
needs Claude Code.
