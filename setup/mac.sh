#!/bin/bash
# Set up a Mac for a second brain: git and Python, Obsidian, and your vault.
# Safe to run as many times as you like: it skips whatever is already done.
#
#   bash setup/mac.sh                         asks a few questions
#   bash setup/mac.sh --name Sam --preset personal [--dest ~/Documents/Obsidian/sam-brain] [--pdf]
#   bash setup/mac.sh --check                 only report what is installed
#
# Needs no password, no Homebrew and no full Xcode. Apple's small "Command Line
# Tools" are enough: they bring git and python3. Full Xcode is a 10+ GB app for
# building iPhone apps, and nothing here needs it.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
seed="$here/setup/build_vault.py"
name="" preset="" dest="" pdf="" check=""
while [ $# -gt 0 ]; do
  case "$1" in
    --name) name="$2"; shift 2 ;;
    --preset) preset="$2"; shift 2 ;;
    --dest) dest="$2"; shift 2 ;;
    --pdf) pdf=yes; shift ;;
    --check) check=yes; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (try --help)"; exit 2 ;;
  esac
done
B=$'\033[1m'; G=$'\033[1;32m'; Y=$'\033[1;33m'; N=$'\033[0m'
say() { printf '\n%s==> %s%s\n' "$B" "$*" "$N"; }

say "1. Developer tools (git and python3)"
if xcode-select -p >/dev/null 2>&1 && git --version >/dev/null 2>&1; then
  echo "installed: $(git --version), $(python3 --version 2>&1)"
elif [ -n "$check" ]; then
  echo "missing. Run: xcode-select --install"
else
  xcode-select --install 2>/dev/null || true
  cat <<MSG
${Y}A macOS window has opened asking to install the "command line developer tools".
Click Install (not "Get Xcode"). It takes 5 to 15 minutes and its time
estimate is not to be trusted. When it says it is done, run this again:${N}

    bash "$0"
MSG
  exit 1
fi

say "2. Obsidian (the app you read and write notes in)"
if [ -d /Applications/Obsidian.app ] || [ -d "$HOME/Applications/Obsidian.app" ]; then
  echo "installed"
else
  echo "not installed yet. Download it from https://obsidian.md/download, open the .dmg"
  echo "and drag Obsidian into Applications. The rest of this script does not need it."
  [ -z "$check" ] && open "https://obsidian.md/download" || true
fi

say "3. An AI that can work on your files (optional, recommended)"
if [ -d /Applications/Claude.app ] || command -v claude >/dev/null 2>&1; then
  echo "Claude found. In the Claude desktop app, use the Code tab and open your vault's folder."
else
  echo "None found. The Claude desktop app (https://claude.ai/download, its Code tab) can read and"
  echo "file your notes for you. ChatGPT or any chat AI also works, by copy and paste."
fi

[ -n "$check" ] && exit 0

say "4. Your vault"
if [ -z "$name" ]; then
  read -r -p "Your first name (it goes in the vault's name): " name || true
fi
name="${name:-My}"
if [ -z "$preset" ]; then
  echo "What is this second brain mostly for?"
  echo "  1) My life: ideas, journal, things I read, people, projects (personal)"
  echo "  2) My job: how things work, how to do things, colleagues, meetings (work)"
  read -r -p "Pick 1 or 2 [1]: " pick || true
  [ "${pick:-1}" = "2" ] && preset=work || preset=personal
fi
slug="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')"
[ "$preset" = work ] && suffix="work-brain" || suffix="brain"
dest="${dest:-$HOME/Documents/Obsidian/${slug:-my}-$suffix}"
title="$name's Brain"; [ "$preset" = work ] && title="$name's Work Brain"
if [ -f "$dest/CLAUDE.md" ]; then
  echo "A vault already exists at $dest; leaving it as it is."
else
  mkdir -p "$(dirname "$dest")"
  python3 "$seed" --preset "$preset" --dest "$dest" --name "$title" --owner "$name" | tail -3
  if [ ! -d "$dest/.git" ]; then
    git -C "$dest" init -q
    if git config user.name >/dev/null && git config user.email >/dev/null; then
      git -C "$dest" add -A && git -C "$dest" commit -qm "Seed $title" && echo "Saved a first snapshot with git (your undo button)."
    fi
  fi
fi

say "5. Reading PDFs (optional)"
if python3 -c "import pypdf" 2>/dev/null; then
  echo "installed"
else
  if [ -z "$pdf" ] && [ -t 0 ]; then
    read -r -p "Install the small PDF reader so imported PDFs get their text pulled out? [y/N]: " ans || true
    case "$ans" in y|Y|yes) pdf=yes ;; esac
  fi
  if [ -n "$pdf" ]; then
    python3 -m pip install --user --quiet pypdf && echo "installed" || echo "could not install; PDFs will still be attached, just without their text"
  else
    echo "skipped. PDFs will be attached without their text; run this again with --pdf to add it."
  fi
fi

cat <<MSG

${G}############################################################${N}
${G}  Done. Your vault is at:${N}
${B}  $dest${N}

${Y}  Next:${N}
  1. Open Obsidian. Click "Open folder as vault" and choose that folder.
  2. Read Home and Readme inside it (they are short).
  3. With Claude: desktop app, Code tab, open that same folder,
     and say: "Read CLAUDE.md and Me.md, then help me fill in Me.md."
     With ChatGPT: see guides/prompts-for-any-ai.md in this repo.
${G}############################################################${N}
MSG
[ -d /Applications/Obsidian.app ] && open -a Obsidian || true
