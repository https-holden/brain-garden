#!/usr/bin/env python3
"""File the notes `bin/ingest.py` brought in. Standard library only.

A note is waiting while its frontmatter has `ingested:` and no `filed:`. The
librarian's instructions are `bin/librarian.md`; this script hands them, with
the list of waiting notes, to whichever AI you use.

    python3 bin/librarian.py              Claude Code, in the background (needs the `claude` command)
    python3 bin/librarian.py --list       only show what is waiting
    python3 bin/librarian.py --paste      for ChatGPT, Gemini or Claude in a browser: prints the
                                          instructions and the notes (and copies them), you paste
                                          that into the chat, and save its whole answer to a file
    python3 bin/librarian.py --apply answer.txt
                                          writes that answer back into the vault, checking every
                                          note first

The Claude Code run is boxed in: it may read the vault and the web, edit only
the waiting notes, add topic pages in Categories/, and run only the rename
helper. Every other action is refused without asking. Nothing is committed.
Set CLAUDE_BIN to use a differently named `claude` command, MODEL to change
the model (default sonnet).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import DASHES, END, START, VAULT, rename, waiting_notes  # noqa: E402

PROMPT = Path(__file__).with_name("librarian.md")
LOG = Path(__file__).with_name("librarian.log")
MODEL = os.environ.get("MODEL", "sonnet")
TIMEOUT = 20 * 60
REPLY_FORMAT = """
## How to answer (you cannot edit files, so write them out)

For every note, give back the whole note, frontmatter included, in exactly this form:

=== FILE: <the note's path as listed above>
=== NAME: <its new name, without .md>
<the complete note>
=== END

For a new topic page, the same with `=== FILE: Categories/<Subject>.md` and no NAME line.
Then the report. Nothing else: no commentary between the blocks.
"""


def rel(p: Path) -> str:
    return p.relative_to(VAULT).as_posix()


def build_prompt(notes: list[Path], paste: bool) -> str:
    today = dt.date.today().isoformat()
    text = PROMPT.read_text(encoding="utf-8").format(
        today=today, notes="\n".join("- `%s`" % rel(p) for p in notes))
    if not paste:
        return text
    rules = (VAULT / "CLAUDE.md").read_text(encoding="utf-8")
    topics = sorted(p.stem for p in (VAULT / "Categories").glob("*.md"))
    parts = [text, REPLY_FORMAT,
             "## The vault's rules (CLAUDE.md)\n\n" + rules,
             "## Topic pages that exist\n\n" + (", ".join(topics) or "none yet"),
             "## The notes"]
    for p in notes:
        parts.append("=== FILE: %s\n%s\n=== END" % (rel(p), p.read_text(encoding="utf-8")))
    return "\n\n".join(parts)


def copy_to_clipboard(text: str) -> bool:
    for cmd in (["pbcopy"], ["clip"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text, text=True)
            return True
    return False


def find_claude() -> str | None:
    env = os.environ.get("CLAUDE_BIN")
    for c in (env and (shutil.which(env) or env), shutil.which("claude"),
              str(Path.home() / ".local/bin/claude"), str(Path.home() / ".claude/local/claude")):
        if c and Path(c).is_file():
            return c
    return None


def run_claude(notes: list[Path]) -> None:
    claude = find_claude()
    if not claude:
        sys.exit("No `claude` command found. Install Claude Code, or use --paste with any chat AI.")
    allowed = ["Read", "Glob", "Grep", "WebSearch", "WebFetch",
               "Edit(./Clippings/**)", "Edit(./Categories/**)",  # Edit rules cover Write too
               "Bash(python3 bin/ingest.py rename *)", "Bash(python3 bin/ingest.py waiting)"]
    allowed += ["Edit(./%s)" % rel(p) for p in notes if not rel(p).startswith("Clippings/")]
    now = dt.datetime.now()
    cmd = [claude, "-p", build_prompt(notes, paste=False), "--model", MODEL,
           "--permission-mode", "dontAsk", "--output-format", "json", "--strict-mcp-config",
           "--allowedTools", *allowed]
    help_text = subprocess.run([claude, "--help"], capture_output=True, text=True).stdout
    if "--tools" in help_text:
        cmd += ["--tools", "Read,Glob,Grep,Edit,Write,Bash,WebSearch,WebFetch"]
    if "--restricted" in help_text:
        cmd.append("--restricted")
    print("The librarian is filing %d note(s). This can take a few minutes." % len(notes))
    try:
        res = subprocess.run(cmd, cwd=VAULT, text=True, capture_output=True,
                             timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        sys.exit("The librarian took longer than %d minutes and was stopped." % (TIMEOUT // 60))
    try:
        out = json.loads(res.stdout)
    except json.JSONDecodeError:
        sys.exit("The librarian did not answer:\n%s" % (res.stderr or res.stdout).strip()[:2000])
    report = (out.get("result") or "").strip()
    if out.get("is_error") or res.returncode:
        sys.exit("The librarian stopped with an error:\n%s" % (report or res.stderr.strip()))
    finish(report, now, out.get("session_id", "?"))


def finish(report: str, when: dt.datetime, session: str) -> None:
    lines = [ln.strip() for ln in report.splitlines()
             if re.match(r"(FILED|INCOMPLETE|PROPOSAL|PROBLEM)\s", ln.strip())]
    body = "\n".join(lines) or report
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("## %s  %s\n%s\n\n" % (when.strftime("%Y-%m-%d %H:%M"), session, body))
    print(body)
    left = waiting_notes()
    if left:
        print("\n".join("UNFILED  %s" % rel(p) for p in left))
    print("\nThe vault's check:", flush=True)
    subprocess.run([sys.executable, str(VAULT / "bin" / "lint.py")], cwd=VAULT)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return "", text
    end = text.index("\n---", 3) + 4
    return text[:end], text[end:]


def apply_answer(path: Path) -> None:
    """Write a chat AI's answer back, refusing anything outside the rules."""
    answer = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    blocks = re.findall(r"^=== FILE: (.+?)\n(?:=== NAME: (.*?)\n)?(.*?)\n=== END", answer, re.M | re.S)
    if not blocks:
        sys.exit("No `=== FILE:` blocks found in %s. Save the AI's whole answer to the file." % path)
    waiting = {rel(p): p for p in waiting_notes()}
    for target, name, text in blocks:
        target = target.strip().strip("`")
        text = text.strip("\n").translate(DASHES) + "\n"
        if target.startswith("Categories/") and target.count("/") == 1 and target.endswith(".md"):
            dest = VAULT / target
            if dest.exists():
                print("KEPT     %s  (exists; topic pages are never overwritten)" % target)
            else:
                dest.write_text(text, encoding="utf-8")
                print("TOPIC    %s" % target)
            continue
        if target not in waiting:
            print("REFUSED  %s  (not a waiting note)" % target)
            continue
        current = waiting[target].read_text(encoding="utf-8")
        new_fm, new_body = split_frontmatter(text)
        if not new_fm:
            print("REFUSED  %s  (the answer has no frontmatter)" % target)
            continue
        if not re.search(r"^filed:", new_fm, re.M):
            new_fm = new_fm[:-4] + "\nfiled: %s\n---" % dt.date.today().isoformat()
        tail = current.split(END, 1)[1] if END in current else ""
        if target.startswith("Clippings/"):
            if START not in new_body or END not in new_body:
                print("REFUSED  %s  (the ingest markers are missing)" % target)
                continue
            body = new_body.split(END, 1)[0] + END + tail  # below the marker stays the owner's
        else:
            body = split_frontmatter(current)[1]  # the owner's own words are never changed
            related = re.search(r"\n## Related\n.*", new_body, re.S)
            if related and "## Related" not in body:
                body = body.rstrip("\n") + "\n\n" + related.group(0).strip("\n") + "\n"
        dest = waiting[target]
        if name and name.strip() and name.strip() != dest.stem:
            try:
                dest = rename(dest.stem, name.strip().translate(DASHES))
            except SystemExit as why:  # a refused name keeps the old one; the note is still filed
                print("KEPT NAME %s  (%s)" % (target, why))
        dest.write_text(new_fm + body, encoding="utf-8")
        print("FILED    %s" % rel(dest))
    report = answer.split("=== END")[-1]
    finish(report, dt.datetime.now(), "pasted answer")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show waiting notes, file nothing")
    ap.add_argument("--paste", action="store_true", help="print the job for a chat AI and copy it")
    ap.add_argument("--apply", metavar="FILE", help="write a chat AI's saved answer back into the vault")
    args = ap.parse_args()

    if args.apply:
        return apply_answer(Path(args.apply).expanduser())
    notes = waiting_notes()
    if not notes:
        print("Nothing waiting to be filed.")
        return
    if args.list:
        print("\n".join("WAITING  %s" % rel(p) for p in notes))
        return
    if args.paste:
        text = build_prompt(notes, paste=True)
        print(text)
        if copy_to_clipboard(text):
            print("\n(Copied to the clipboard. Paste it into your AI chat. Save its whole answer to a "
                  "text file, then run: python3 bin/librarian.py --apply <that file>)", file=sys.stderr)
        return
    run_claude(notes)


if __name__ == "__main__":
    main()
