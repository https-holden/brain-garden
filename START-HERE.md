# Start here

You are about to plant a **brain garden**: one place for your ideas, what you read, the
people in your life, your projects and your days, organized so an AI can find its way to any
answer about your life or work, and keep the place tidy for you. It is built on Obsidian, a
free notes app, and it is just a folder of text files on your own computer. Nothing is locked
in, and nothing leaves your computer unless you send it.

The whole idea in one line: **harvest it, seed it, live in it.** Gather what you already have,
put it in the garden in a meaningful way (the AI does most of that), then use it every day, and
it gets better at being yours as you go. The longer version, with the three kinds of memory and
what is coming next, is in [guides/how-it-works.md](guides/how-it-works.md).

You do not need to know Obsidian, the terminal, git or GitHub. You do not need a GitHub
account. About 30 minutes, most of it waiting for installs.

## The easy way: let an AI walk you through it

Open your AI and paste this:

> Help me set up a brain garden (a second brain) from this repo, one step at a time:
> https://github.com/https-holden/brain-garden
> Start by reading its AGENTS.md. I'm new to Obsidian and the terminal.

**Best: the Claude desktop app** (https://claude.ai/download). Use its **Code** tab: it can
run the setup on your computer for you and, later, file your notes itself. Choose your home
folder when it asks which folder to work in.

**ChatGPT, Gemini or Claude in a browser** also work. They cannot touch your computer, so
they tell you what to paste and you paste it. Slightly more copy and paste, same result.

## Or do it yourself

### On a Mac

1. Install **Obsidian**: https://obsidian.md/download
2. Open **Terminal** (press Cmd+Space, type Terminal, press Enter) and paste:

   ```bash
   xcode-select -p >/dev/null 2>&1 && echo "already installed" || xcode-select --install
   ```

   If a window pops up, click **Install** (not "Get Xcode") and wait until it finishes. These
   are Apple's small developer tools, which bring git and Python. You do not need the full
   Xcode app.
3. Then paste:

   ```bash
   git clone https://github.com/https-holden/brain-garden.git ~/brain-garden && bash ~/brain-garden/setup/mac.sh
   ```

   It asks your first name and whether this is for your life or your job, then makes your
   vault in `Documents/Obsidian/`.

### On Windows

1. Open **PowerShell** (Start menu, type PowerShell) and paste:

   ```powershell
   winget install --id Git.Git -e; winget install --id Python.Python.3.12 -e; winget install --id Obsidian.Obsidian -e
   ```

2. Close PowerShell, open it again, and paste:

   ```powershell
   git clone https://github.com/https-holden/brain-garden.git $HOME\brain-garden; powershell -ExecutionPolicy Bypass -File $HOME\brain-garden\setup\windows.ps1
   ```

### No terminal at all

On the GitHub page, click the green **Code** button, then **Download ZIP**. Unzip it, copy
the `starter-vault` folder into your Documents, and rename it to something like `sam-brain`.
That is your vault. (The helper scripts inside it need Python, which you can add later.)

## Then

1. **Open it**: Obsidian, **Open folder as vault**, choose your vault folder. Open **Home**.
2. **Learn the basics** (15 minutes): [guides/obsidian-basics.md](guides/obsidian-basics.md).
3. **Fill in `Me.md`** with your AI: who you are and what this is for. Every AI that helps
   you reads it first.
4. **Bring in a few things you care about**: [guides/bringing-things-in.md](guides/bringing-things-in.md).
   Not sure what? Say "harvest" to your AI and it will interview you
   ([guides/harvesting-and-pruning.md](guides/harvesting-and-pruning.md)).
5. **Make it a habit**: [guides/daily-loop.md](guides/daily-loop.md). "Start my day" in the
   morning, "end of day" at night.

Using ChatGPT? The copy-and-paste prompts are in
[guides/prompts-for-any-ai.md](guides/prompts-for-any-ai.md).

## What you get

- Folders for each kind of note: **Notes** (your own writing), **References** (books, places,
  tools), **People**, **Clippings** (anything someone else wrote), **Daily** (one note per day).
  The work version has **Knowledge**, **Playbooks** and **Meetings** instead.
- **Topic pages** that list every note about a subject, filled in automatically.
- **`Now.md`**: what is on your plate, kept current every evening.
- **Tools to bring things in**: web pages, PDFs, Word files, emails, photos, old notes from
  Apple Notes, Notion or Evernote. An AI librarian files them: summary, name, topics, links.
- **A monthly prune** that shows what you collect but never use, so the vault stays useful.
- **Rules your AI follows** (`CLAUDE.md` in the vault), so it keeps things consistent instead
  of making a mess.

Backing it up is optional and covered in
[guides/backup-with-github.md](guides/backup-with-github.md).
