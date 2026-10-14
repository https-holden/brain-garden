# For the AI helping someone set this up

> **Is it about one codebase, or about everything you know?** One codebase:
> [ObsidianVaultSeed](https://github.com/https-holden/ObsidianVaultSeed). Everything you
> know, plus the tasks you run on it: Brain Garden.

You are probably here because a person pointed you at this repository and said something like
"help me get this set up". This file tells you how. It works for Claude (desktop app, Code tab,
or Claude Code), ChatGPT, Codex, Gemini or any other assistant.

## Who you are helping

Assume a beginner until they show otherwise: they may never have used Obsidian, a terminal,
git or GitHub, and may not know what a wiki link is. So:

- **One step at a time.** Say exactly what to click or paste, then wait for them to say it
  worked (or to paste what they see) before the next step. Never hand over ten steps at once.
- **Plain words.** "A folder of notes" before "a vault"; "the box of properties at the top of
  a note" before "frontmatter". Introduce a term once, when it is needed.
- **Every command in its own copyable block**, and say where to run it (Terminal on a Mac,
  PowerShell on Windows, and from which folder).
- **Never ask for a password, token or code**, and never ask them to paste one into the chat.
  Sign-ins happen in their browser. They do not need a GitHub account for any of this.
- **Celebrate small wins**, and if something fails, read the error with them before guessing.

## First, explain the idea (two minutes)

Before any install, tell them what they are building and why, in your own words, short. The
full version is [guides/how-it-works.md](guides/how-it-works.md); the gist:

- A brain garden is your material (notes, ideas, what you read, people, projects, your days)
  organized as linked plain-text notes, so an AI can find the path to an answer fast instead of
  knowing nothing about your life. It thrives on data: the more goes in, and the better it is
  linked, the more useful it gets.
- **Harvest it, seed it, live in it.** Harvest: gather what you have from wherever it lives.
  Seed: put it into the vault in a meaningful way, filed, named and linked (the AI does most of
  this). Live in it: use it daily, and it learns from that use, getting better at its own
  process, especially in the first month.
- It remembers on three timescales: today (the daily note), what is in flight (`Now.md`), and
  what you know (everything else).
- It is a garden: organized and pleasant to walk around in, all private on their computer
  unless they choose to share part of it.

Then ask whether that sounds like what they want, and answer questions before moving on.

## Then find out four things

1. **What they are looking to build**: a brain for their life (journal, ideas, reading,
   people, projects) or for their job (how things work, procedures, colleagues, meetings),
   and in a sentence what they most want it to help with. Life or job picks the preset:
   `personal` or `work`. The sentence goes in `Me.md` later.
2. **Where most of their material already lives**: the one or two places that hold the bulk
   of it (Apple Notes, Notion, Google Docs, voice memos, email, paper). Do not import anything
   yet; this tells you what to harvest first in step 5, and whether they need the Importer
   plugin or PDF support during setup.
3. **Their computer**: Mac or Windows. (Linux works like the Mac path.)
4. **What you can do**: if you can run commands on their machine (Claude Code, the Claude
   desktop app's Code tab, Codex), you do the commands and they watch. If you are a chat in a
   browser (ChatGPT, claude.ai, Gemini), they run the commands and you guide.

Ask their first name for the vault's name.

## The setup, in order

### 1. Get Obsidian

Download from https://obsidian.md/download and install it like any app. No account needed.

### 2. Get this repository onto their computer

**Mac.** In Terminal (Cmd+Space, type Terminal, Enter), first the developer tools, which bring
git and Python:

```bash
xcode-select -p >/dev/null 2>&1 && echo "already installed" || xcode-select --install
```

A window appears: they click **Install**, not "Get Xcode". Full Xcode is a huge app they do
not need. It takes 5 to 15 minutes. Then:

```bash
git clone https://github.com/https-holden/brain-garden.git ~/brain-garden && bash ~/brain-garden/setup/mac.sh
```

**Windows.** In PowerShell:

```powershell
winget install --id Git.Git -e; winget install --id Python.Python.3.12 -e
```

Close and reopen PowerShell, then:

```powershell
git clone https://github.com/https-holden/brain-garden.git $HOME\brain-garden; powershell -ExecutionPolicy Bypass -File $HOME\brain-garden\setup\windows.ps1
```

**No terminal at all** (if they really do not want one): on the GitHub page, the green
**Code** button, **Download ZIP**, unzip it, and copy the `starter-vault` folder into
`Documents`. Rename the folder to their name (say `sam-brain`). That is a ready vault. The
scripts inside it need Python later, but Obsidian works right away.

The setup script asks their name and personal or work, and makes the vault at
`~/Documents/Obsidian/<name>-brain`. If you are running it for them, pass the answers so it
does not wait for typing:

```bash
bash ~/brain-garden/setup/mac.sh --name Sam --preset personal
```

### 3. Open the vault in Obsidian

Obsidian, **Open folder as vault**, choose that folder, trust it. Open **Home**. Then give them
the ten-minute tour from [guides/obsidian-basics.md](guides/obsidian-basics.md): links with
`[[`, backlinks, properties, categories instead of folders, templates, the tables. Have them
make one note and one link while you explain, so it sticks.

### 4. Fill in Me.md together

`Me.md` in the vault says who they are, what the vault is for, what they will bring in and
what is private. Interview them, a few questions at a time, and write it (or give them the
text to paste). Every AI that helps them later reads it first.

### 5. Harvest: find their sources, then bring in a sample

Do not start with "what do you want to import?". Most people answer "everything" or "nothing".
Interview them instead, a few questions at a time (the vault's `harvest` skill has the full
procedure, and [guides/harvesting-and-pruning.md](guides/harvesting-and-pruning.md) has the
reasoning and the prompts):

1. Where does your thinking happen today? (Notes app, voice memos, messages to yourself,
   screenshots, bookmarks, email drafts, paper, a journal app.) Start from what they told you
   at the beginning about where most of their material lives.
2. What do you keep losing, or finding again? **Start with that source.**
3. What do you collect from other people? (Articles, videos, recipes, newsletters, highlights.)
4. A year from now, what would you want to find here?
5. What must never come in?

Then propose one numbered list: each source, what it brings, how (the table in
[guides/bringing-things-in.md](guides/bringing-things-in.md)), how often, and whether to
backfill or only capture from now. Write the agreed ones into the vault's `Sources.md`, and the
rejected ones under "Not brought in, on purpose".

**Sample before any bulk import.** Bring in about ten items from the first source with
`--via "<Source>"` (so `Sources.md` is stamped), file them (with Claude, `python3 bin/librarian.py`
or "file my clippings"; with a chat AI, the `--paste` and `--apply` round trip), then open two
or three in Obsidian together. Is this what they wanted to keep? Adjust, and only then bring in
the rest, with `--dry-run` first. Their own writing before other people's, recent before old.
Show them the topic pages filling themselves in.

### 6. Show them the daily loop

[guides/daily-loop.md](guides/daily-loop.md): "start my day" in the morning, jot under
`## Notes` in the daily note, "end of day" in the evening. That habit is what makes it a
second brain. Tell them about the monthly **prune** too: `python3 bin/ingest.py report` lists
unused clippings, duplicates, thin topics, overdue sources and how much of each source they
actually use, and the `prune` skill turns it into one numbered list. Nothing they wrote is
ever deleted by it. With a chat AI, the prompts are in
[guides/prompts-for-any-ai.md](guides/prompts-for-any-ai.md).

### 7. Optional, later

- A backup: [guides/backup-with-github.md](guides/backup-with-github.md). Only now does a
  GitHub account matter, and only if they choose GitHub.
- Kepano's Obsidian skills for Claude Code, which teach Claude the exact note and table syntax:
  in a Claude Code session, `/plugin marketplace add kepano/obsidian-skills`, then
  `/plugin install obsidian@obsidian-skills`.
- Sharing with a team: [guides/sharing-a-vault.md](guides/sharing-a-vault.md).

## Once the vault exists

Work from the vault's own `CLAUDE.md` (inside their vault folder, not this repo's). It is the
contract: where each kind of note goes, the properties, the rules, the check to run
(`python3 bin/lint.py`). Follow it exactly, even if you are not Claude. Never invent notes or
facts for them: the vault holds their material, not yours.

## What is in this repository

| Path | What it is |
|---|---|
| `START-HERE.md` | The same journey, written for the person instead of for you |
| `guides/how-it-works.md` | The idea: harvest, seed, live in it; the three memory tiers; private and shared beds; desire paths |
| `ROADMAP.md` | What is coming next (desire paths) |
| `setup/` | `mac.sh` and `windows.ps1`: install what is missing and make the vault |
| `starter-vault/` | A ready-made personal vault for people who skip the terminal |
| `guides/` | Obsidian basics, bringing things in, the daily loop, backup, sharing, chat prompts |
| `setup/build_vault.py` | The vault builder the setup scripts call (`--help` for its flags) |
| `template/` | What a vault is built from |

For a planning (roadmap) or content (lexicon) vault for a code project instead, see the sister
repo https://github.com/https-holden/ObsidianVaultSeed.
