# Backing up your vault (optional)

Your vault is a folder of files, so any backup works. Pick one.

| Option | Good for | Cost |
|---|---|---|
| **Time Machine** (Mac) or **File History** (Windows) | You already have it on | Free |
| **iCloud Drive / OneDrive / Dropbox**: keep the vault folder inside it | Using the vault on your phone too (with the Obsidian mobile app) | Free tier |
| **Obsidian Sync** | The smoothest phone and computer sync | Paid |
| **A private GitHub repository** | Full history of every change, and sharing with a team later | Free |

The setup already made your vault a git repository, which is a local history of changes (your
undo button). GitHub is where that history can be backed up. You do **not** need a GitHub
account to use anything in this repo; only for this optional backup.

## GitHub, step by step

1. Make an account at https://github.com/signup (free).
2. Install the GitHub command line tool and sign in. In Terminal, on a Mac:

   ```bash
   tag=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p'); a=$([ "$(uname -m)" = arm64 ] && echo arm64 || echo amd64); mkdir -p ~/.local/bin && curl -fsSL "https://github.com/cli/cli/releases/download/v${tag}/gh_${tag}_macOS_${a}.zip" -o /tmp/gh.zip && unzip -qo /tmp/gh.zip -d /tmp/ghcli && cp /tmp/ghcli/gh_*/bin/gh ~/.local/bin/gh && export PATH="$HOME/.local/bin:$PATH" && gh auth login --web --git-protocol https && gh auth setup-git
   ```

   (On Windows: `winget install GitHub.cli`, then `gh auth login --web`.) It opens your
   browser: choose HTTPS, then "Login with a web browser", and paste the code it shows. You
   never type a password into the terminal.
3. Tell git who you are, once:

   ```bash
   git config --global user.name "Your Name" && git config --global user.email "you@example.com"
   ```

4. From inside your vault's folder, make a **private** repository and push to it:

   ```bash
   gh repo create my-brain --private --source . --push
   ```

5. From then on, save with:

   ```bash
   git add -A && git commit -m "notes" && git push
   ```

   or just ask Claude to "save the vault". The Obsidian Git community plugin can also do it on
   a timer if you prefer buttons.

Keep the repository **private**: it holds your journal.
