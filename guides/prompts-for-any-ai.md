# Prompts for ChatGPT (or any chat AI)

Claude in the desktop app's Code tab can open your vault's files itself, so with Claude you
just ask. A chat AI in a browser (ChatGPT, Gemini, claude.ai) cannot see your files, so you
paste them in and paste its answer back. These prompts make that quick. Copy everything inside
a box.

Tip: in ChatGPT, make a **Project** called "Second brain" and put your vault's `CLAUDE.md`,
`Rules.md` and `Me.md` in its files. Add the index of your notes too, so the chat knows what notes exist: run
`python3 bin/find.py --all > ~/Desktop/index.txt` in your vault and upload `index.txt` (do it
again now and then, as the vault grows). Then you can skip pasting them every time.

## Getting set up

> I'm setting up a brain garden (a second brain) in Obsidian using this repo:
> https://github.com/https-holden/brain-garden
> Read its AGENTS.md and walk me through it one step at a time. I'm new to Obsidian and to
> the terminal, so tell me exactly what to click or paste, wait for me to say it worked, and
> explain things in plain words.

## Filling in Me.md

> Here is the Me.md from my vault. Interview me, a few questions at a time, to fill in every
> "(fill in: ...)" line. Then give me the complete file to paste back over the old one.
>
> (paste Me.md)

## Turning something into notes

> Here are my vault's rules (CLAUDE.md and Rules.md), then something I want to keep. Turn it into notes
> that follow the rules exactly: the right folder, the frontmatter its kind's template has,
> `categories` as links to topics, a title that says the idea, `[[links]]` to people and
> things, no en or em dashes. Give each note as its file path and its full content.
>
> (paste CLAUDE.md and Rules.md, then the text)

## Finding your sources, and pruning

The harvesting interview and the monthly pruning prompt are in
[harvesting-and-pruning.md](harvesting-and-pruning.md#prompts).

## Filing imported notes

Run `python3 bin/librarian.py --paste` in your vault. It copies the whole job, rules and
notes included. Paste it into the chat. Save the chat's entire answer to a text file (say
`answer.txt` on your Desktop), then run
`python3 bin/librarian.py --apply ~/Desktop/answer.txt`. The script checks each note before
writing it.

## End of the day

> Here are my vault's Now.md and today's daily note. Work out what I learned or decided today
> and what is still in flight. Give me (1) a numbered list of notes to create or update, each
> with its folder, title and one-line content, and (2) a rewritten Now.md where every bullet
> ends with today's date in (YYYY-MM-DD) form. Don't invent anything that isn't in what I gave
> you.
>
> (paste Now.md, then today's note)

## Weekly review

> Here are my last seven daily notes and Now.md. What keeps coming up that has no note of its
> own yet? What in Now.md is stale or done? What should I let go of? Short answers.
>
> (paste them)

## Asking your vault a question

> Here are some notes from my vault. Answer my question from them only, name the note each
> part of the answer came from, and say plainly if the notes don't cover it.
>
> Question: ...
>
> (paste the notes; for a big vault, run `python3 bin/find.py <a few words>` in your vault, or
> search in Obsidian with Cmd+Shift+F, and paste the notes it finds)
