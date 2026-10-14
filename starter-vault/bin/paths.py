#!/usr/bin/env python3
"""Footsteps: where the AI walks in this vault, as a ledger and a one-screen report. Standard library only.

    python3 bin/paths.py                     refresh the ledger and the report (mode `refresh`)
    python3 bin/paths.py --today YYYY-MM-DD  as if today were that date
    python3 bin/paths.py --transcripts DIR   also read the Claude Code transcripts in DIR (repeatable)

It writes two files and nothing else, both kept on this machine (git-ignored):
.paths/ledger.json, every footstep so far, and .paths/report.md, the report.
It never creates, edits or moves a note and writes no frontmatter. In a bed
checkout (.bed.json at the vault root) it prints nothing and exits.

A footstep is one read, write or lookup hit of a vault file. The sources, each
optional, are named at the top of the report:

- Claude Code transcripts (reads and writes): every .jsonl file under
  <config folder>/projects/<slug>/, where the slug is the vault's path with
  each character that is not a letter or a digit turned into "-" (and the main
  checkout's path too when the vault is a git worktree). The config folders
  are $CLAUDE_CONFIG_DIR, ~/.claude and every ~/.claude-* that has a
  projects/ folder. Subagent transcripts count with their parent session.
- The find log, .paths/find.log: each path a query matched is a footstep of
  kind `find`; a query with no hits is a miss.
- The git log, when the vault is a repo: each file a commit touched is a
  footstep of kind `git`.

What counts in a transcript: the path given to Read, Edit or Write; a vault
path in a Bash command (a folder is one footstep on the folder; the target of
sed -i, >, >> or tee is a write); each file named on a line of grep output
(Bash or Grep); the folder a Glob lists; the SKILL.md of a skill called by the
Skill tool or by a slash command; and CLAUDE.md, which Claude Code loads at the
start of every session. Absolute and vault-relative paths are the same file,
only files that exist now count, and a session counts each file once per kind.

A session's type is its first skill or slash command, by name, else `misc`.
Its first useful action is its first write to a vault file or its first MCP
call. Its fixed load is the chars of the distinct vault files it read whole
before that (Read, cat and the like, skills, CLAUDE.md; not grep hits or
folder listings).

Hot: three or more reads (sessions and find hits) in 30 days. Dormant: no read
in 60 days, or never read. Writes (transcripts and git) never make a file hot.
A transcript is read again only when its time or size changed; the find log
and the git log are read whole on every refresh.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find  # noqa: E402

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(".paths", "ledger.json")
REPORT = os.path.join(".paths", "report.md")
HOT_DAYS, HOT_READS, DORMANT_DAYS, TOP_HOT, TOP_LIST = 30, 3, 60, 20, 10
READS = ("read", "find")  # the kinds that make a file hot; write and git never do
# Claude Code's own commands are not a session's type; any other slash command is, by name.
BUILT_IN = {"add-dir", "agents", "clear", "compact", "config", "context", "cost", "doctor", "effort", "exit",
            "export", "fast", "help", "hooks", "ide", "init", "login", "logout", "mcp", "memory", "model",
            "permissions", "plugin", "resume", "rewind", "status", "usage"}
WRITERS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READERS = {"cat", "head", "tail", "less", "more", "bat"}  # Bash commands that read a file whole
GREPS = {"grep", "egrep", "fgrep", "rg", "ag"}
CONTROL = {"|", "||", "&&", ";", ";;", "&", "|&", "(", ")"}
REDIRECT = {">", ">>", ">|", "&>", "&>>"}
COMMAND = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
NOT_NOTES = {"bin", "Templates"}


def slug(path):
    """The folder name Claude Code gives a project: every character but a letter or a digit is "-"."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def git(vault, *args):
    """git's output, or None when it fails. Never inherits GIT_* (a hook's GIT_DIR points elsewhere)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        res = subprocess.run(["git", "-C", vault, "-c", "core.quotepath=off"] + list(args), capture_output=True,
                             env=env, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.decode("utf-8", "replace") if res.returncode == 0 else None


def checkouts(vault):
    """The vault's path, and the same folder in the main checkout when the vault is a git worktree."""
    out = [vault]
    lines = (git(vault, "rev-parse", "--show-toplevel", "--git-common-dir") or "").split("\n")
    if len(lines) >= 2 and lines[0] and lines[1]:
        top = os.path.realpath(lines[0])
        common = os.path.realpath(os.path.join(vault, lines[1]))
        main = os.path.dirname(common)
        if os.path.basename(common) == ".git" and main != top:
            out.append(os.path.normpath(os.path.join(main, os.path.relpath(os.path.realpath(vault), top))))
    return out


class Vault:
    """Turns any path a session wrote into a vault-relative one, whichever checkout or symlink it went through."""

    def __init__(self, root):
        self.root = root
        self.roots = []
        for r in checkouts(root):
            for form in (os.path.abspath(r), os.path.realpath(r)):
                if form not in self.roots:
                    self.roots.append(form)

    def rel(self, path, cwd=None):
        """'Notes/X.md' for a path inside the vault ('' for the root), None for one outside it."""
        if not isinstance(path, str) or not path or "\0" in path:
            return None
        full = os.path.normpath(os.path.join(cwd or self.root, os.path.expanduser(path)))
        for cand in (full, os.path.realpath(full)):
            for r in self.roots:
                if cand == r:
                    return ""
                if cand.startswith(r + os.sep):
                    return unicodedata.normalize("NFC", cand[len(r) + 1:].replace(os.sep, "/"))
        return None

    def kind(self, rel):
        """'file', 'dir' or None (missing, the root, or inside .git)."""
        if not rel or rel == ".git" or rel.startswith(".git/"):
            return None
        path = os.path.join(self.root, *rel.rstrip("/").split("/"))
        return "dir" if os.path.isdir(path) else "file" if os.path.isfile(path) else None

    def size(self, rel):
        with open(os.path.join(self.root, *rel.split("/")), encoding="utf-8", errors="replace") as fh:
            return len(fh.read())


# ------------------------------------------------------------ transcripts


def config_dirs():
    home = os.path.expanduser("~")
    dirs = [os.path.expanduser(os.environ["CLAUDE_CONFIG_DIR"])] if os.environ.get("CLAUDE_CONFIG_DIR") else []
    dirs.append(os.path.join(home, ".claude"))
    try:
        names = sorted(os.listdir(home))
    except OSError:
        names = []
    dirs += [os.path.join(home, n) for n in names
             if n.startswith(".claude-") and os.path.isdir(os.path.join(home, n, "projects"))]
    seen, out = set(), []
    for d in dirs:
        if os.path.realpath(d) not in seen:
            seen.add(os.path.realpath(d))
            out.append(d)
    return out


def shown(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


def transcript_files(vault, extra):
    """(the folders transcripts were found in, as shown in the report; every transcript file)."""
    slugs = []
    for r in vault.roots:
        if slug(r) not in slugs:
            slugs.append(slug(r))
    found, files = [], []
    places = [(d, [os.path.join(d, "projects", s) for s in slugs]) for d in config_dirs()]
    places += [(d, [d]) for d in extra]
    for label, dirs in places:
        hit = False
        for d in dirs:
            if os.path.isdir(d):
                hit = True
                for root, subdirs, names in os.walk(d):
                    subdirs.sort()
                    files += [os.path.join(root, n) for n in sorted(names) if n.endswith(".jsonl")]
        if hit:
            found.append(shown(label))
    return found, sorted(set(files))


def records(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def session_of(recs, path):
    for rec in recs:
        if isinstance(rec.get("sessionId"), str) and rec["sessionId"]:
            return rec["sessionId"]
    return os.path.splitext(os.path.basename(path))[0]


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def bash_paths(command):
    """(read paths, whole-file read paths, written paths, is a grep) named in one Bash command."""
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        tokens = command.split()
    reads, whole, writes, grep, words = [], [], [], False, []
    for tok in tokens + [";"]:
        if tok not in CONTROL:
            words.append(tok)
            continue
        plain, i = [], 0
        while i < len(words):
            w = words[i]
            if w in REDIRECT and i + 1 < len(words):
                writes.append(words[i + 1])
                i += 2
            elif w in (">&", "<<", "<<<"):
                i += 2
            else:
                plain.append(w)
                i += 1
        k = 0
        while k < len(plain) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", plain[k]):
            k += 1
        cmd, args = (os.path.basename(plain[k]), plain[k + 1:]) if k < len(plain) else ("", [])
        grep = grep or cmd in GREPS or (cmd == "git" and args[:1] == ["grep"])
        if cmd == "tee":
            writes += [a for a in args if not a.startswith("-")]
        elif cmd == "sed" and any(a.startswith("-i") or a.startswith("--in-place") for a in args):
            writes += [a for a in args if not a.startswith("-")]
        else:
            reads += plain[k:]
            whole += args if cmd in READERS else []
        words = []
    return reads, whole, writes, grep


def session(recs, vault):
    """One session's footsteps, type and fixed load, from its records in time order. None if it has no turns."""
    out = {"date": "", "type": "misc", "fixed_load": None, "read": {}, "write": {}}
    state = {"typed": False, "useful": False, "harness": False, "turns": 0}
    loaded, greps = set(), {}

    def step(kind, rel, day, whole=False):
        what = vault.kind(rel)
        if what is None or (what == "dir" and kind != "read"):
            return
        key = rel.rstrip("/") + ("/" if what == "dir" else "")
        out[kind].setdefault(key, day)
        if whole and what == "file" and not state["useful"]:
            loaded.add(key)

    def write(rel, day):
        if rel:  # a write into the vault, even to a file gone since, is the first useful action
            state["useful"] = True
            step("write", rel, day)

    def skill(name, day, slash):
        name = name.strip().lstrip("/")
        if not name or (slash and name in BUILT_IN):
            return
        if not state["typed"]:
            state["typed"], out["type"] = True, name
        if re.match(r"^[\w.-]+$", name):
            step("read", ".claude/skills/%s/SKILL.md" % name, day, whole=True)

    for rec in recs:
        kind = rec.get("type")
        if kind not in ("user", "assistant"):
            continue
        state["turns"] += 1
        day = str(rec.get("timestamp") or "")[:10]
        out["date"] = out["date"] or day
        cwd = rec.get("cwd") if isinstance(rec.get("cwd"), str) else None
        if cwd and not state["harness"] and vault.rel(cwd) is not None:
            state["harness"] = True
            step("read", "CLAUDE.md", day, whole=True)
        message = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        content = message.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content or []
        for b in blocks if isinstance(blocks, list) else []:
            if not isinstance(b, dict):
                continue
            if kind == "user" and b.get("type") == "text":
                m = COMMAND.search(str(b.get("text") or ""))
                if m:
                    skill(m.group(1), day, slash=True)
            elif kind == "user" and b.get("type") == "tool_result" and b.get("tool_use_id") in greps:
                base = greps[b.get("tool_use_id")]
                for line in text_of(b.get("content")).split("\n"):
                    step("read", grep_hit(vault, line, base), day)
            elif kind == "assistant" and b.get("type") == "tool_use":
                name, args = str(b.get("name") or ""), b.get("input") if isinstance(b.get("input"), dict) else {}
                if name.startswith("mcp__"):
                    state["useful"] = True
                elif name == "Skill":
                    skill(str(args.get("skill") or args.get("command") or ""), day, slash=False)
                elif name == "Read":
                    step("read", vault.rel(args.get("file_path"), cwd), day, whole=True)
                elif name in WRITERS:
                    write(vault.rel(args.get("file_path") or args.get("notebook_path"), cwd), day)
                elif name == "Bash" and isinstance(args.get("command"), str):
                    reads, whole, writes, grep = bash_paths(args["command"])
                    for tok in reads:
                        step("read", vault.rel(tok, cwd), day, whole=tok in whole)
                    for tok in writes:
                        write(vault.rel(tok, cwd), day)
                    if grep:
                        greps[b.get("id")] = cwd
                elif name == "Grep":
                    greps[b.get("id")] = cwd
                elif name in ("Glob", "LS"):
                    literal = []
                    for part in str(args.get("pattern") or "").split("/") if name == "Glob" else []:
                        if any(c in part for c in "*?[{"):
                            break
                        literal.append(part)
                    folder = os.path.join(str(args.get("path") or cwd or vault.root), *literal)
                    if vault.kind(vault.rel(folder, cwd)) == "dir":
                        step("read", vault.rel(folder, cwd), day)
    if not state["turns"]:
        return None
    if state["useful"]:
        out["fixed_load"] = sum(vault.size(rel) for rel in loaded if vault.kind(rel) == "file")
    return out


def grep_hit(vault, line, cwd):
    """The vault file a line of grep output names (path, path:line:text or path:text), or None."""
    line = line.strip()
    if not line or len(line) > 4096:
        return None
    for cand in [line] + [line[:i] for i, ch in enumerate(line) if ch == ":"][:3]:
        rel = vault.rel(cand, cwd)
        if vault.kind(rel) == "file":
            return rel
    return None


# ------------------------------------------------------------ the other sources


def find_log(root):
    """[(date, query, matched paths)] from .paths/find.log, or None when there is no log."""
    path = os.path.join(root, ".paths", "find.log")
    if not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 3 and re.match(r"^\d{4}-\d{2}-\d{2}", fields[0]):
                out.append((fields[0][:10], " ".join(fields[1].lower().split()),
                            [unicodedata.normalize("NFC", p) for p in fields[3:] if p]))
    return out


def git_log(root):
    """[(date, paths touched)], one per commit, or None when the vault is not a repo with commits."""
    text = git(root, "log", "--no-renames", "--relative", "--name-only", "--date=short", "--format=%x01%cd")
    if text is None:
        return None
    commits = []
    for line in text.split("\n"):
        if line.startswith("\x01"):
            commits.append((line[1:].strip(), []))
        elif line.strip() and commits:
            commits[-1][1].append(unicodedata.normalize("NFC", line.strip()))
    return commits


# ------------------------------------------------------------ refresh


def within(day, today, days):
    try:
        return (today - dt.date.fromisoformat(day)).days < days
    except (TypeError, ValueError):
        return False


def load(root):
    try:
        with open(os.path.join(root, LEDGER), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def refresh(root, today, extra):
    """Bring the ledger up to date and write it. (the ledger, transcripts read, transcripts unchanged)."""
    vault = Vault(root)
    old = load(root)
    known = old.get("transcripts") if isinstance(old.get("transcripts"), dict) else {}
    sessions = old.get("sessions") if isinstance(old.get("sessions"), dict) else {}
    found, files = transcript_files(vault, extra)
    fresh, touched = {}, set()
    for path in files:
        try:
            st = os.stat(path)
        except OSError:
            continue
        stamp = [st.st_mtime_ns, st.st_size]
        if (known.get(path) or {}).get("stamp") != stamp:
            fresh[path] = records(path)
            known[path] = {"stamp": stamp, "session": session_of(fresh[path], path)}
            touched.add(known[path]["session"])
    opened = len(fresh)
    for sid in sorted(touched):
        mine, timeline = sorted(p for p, v in known.items() if v.get("session") == sid and os.path.exists(p)), []
        for i, path in enumerate(mine):
            if path not in fresh:
                fresh[path] = records(path)
                opened += 1
            timeline += [(str(r.get("timestamp") or ""), i, n, r) for n, r in enumerate(fresh[path])]
        timeline.sort(key=lambda t: t[:3])
        s = session([t[3] for t in timeline], vault)
        if s is None:
            sessions.pop(sid, None)
        else:
            sessions[sid] = s

    steps = {}

    def add(rel, kind, day):
        if vault.kind(rel) == ("dir" if rel.endswith("/") else "file"):
            days = steps.setdefault(rel, {}).setdefault(kind, {})
            days[day] = days.get(day, 0) + 1

    for s in sessions.values():
        for kind in ("read", "write"):
            for rel, day in s[kind].items():
                add(rel, kind, day)
    lookups, commits = find_log(root), git_log(root)
    for day, _, matched in lookups or []:
        for rel in matched:
            add(rel, "find", day)
    for day, touched_paths in commits or []:
        for rel in touched_paths:
            add(rel, "git", day)

    types = {}
    for s in sessions.values():
        if within(s["date"], today, HOT_DAYS):
            t = types.setdefault(s["type"], {"sessions": 0, "loads": []})
            t["sessions"] += 1
            if s["fixed_load"] is not None:
                t["loads"].append(s["fixed_load"])
    types = {k: {"sessions": t["sessions"],
                 "fixed_load": round(sum(t["loads"]) / len(t["loads"])) if t["loads"] else None}
             for k, t in types.items()}
    misses = {}
    for day, query, matched in lookups or []:
        if not matched and query and within(day, today, HOT_DAYS):
            m = misses.setdefault(query, {"misses": 0, "last": ""})
            m["misses"] += 1
            m["last"] = max(m["last"], day)

    ledger = {
        "version": 1, "refreshed": today.isoformat(), "last_pass": old.get("last_pass"),
        "paved": old.get("paved") if isinstance(old.get("paved"), dict) else {},
        "sources": {"transcripts": found, "sessions": len(sessions),
                    "find_log": None if lookups is None else len(lookups),
                    "git": None if commits is None else len(commits)},
        "transcripts": known, "sessions": sessions, "paths": steps, "types": types,
        "signposts": {q: m for q, m in misses.items() if m["misses"] >= 2},
    }
    os.makedirs(os.path.join(root, ".paths"), exist_ok=True)
    with open(os.path.join(root, LEDGER + ".tmp"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(os.path.join(root, LEDGER + ".tmp"), os.path.join(root, LEDGER))
    return ledger, opened, len(files) - len([p for p in files if p in fresh])


# ------------------------------------------------------------ report


def notes(root):
    """Every note: a .md file outside the dot folders, bin/ and Templates/."""
    out = []
    for dirpath, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (dirpath == root and d in NOT_NOTES))
        out += [unicodedata.normalize("NFC", os.path.relpath(os.path.join(dirpath, n), root).replace(os.sep, "/"))
                for n in sorted(names) if n.endswith(".md")]
    return out


def budget_rows(root):
    """(label, chars, budget) for each file the `budgets` in bin/vault.json name, every skill as one row."""
    try:
        with open(os.path.join(root, "bin", "vault.json"), encoding="utf-8") as fh:
            raw = json.load(fh).get("budgets") or {}
    except (OSError, ValueError, AttributeError):
        raw = {}
    table = {}
    for rel, n in raw.items() if isinstance(raw, dict) else []:
        try:
            table[os.path.normpath(rel.replace("\\", "/")).replace(os.sep, "/")] = int(n)
        except (TypeError, ValueError):
            pass  # a hand-edited budget that is not a number is ignored, as lint does

    def size(rel):
        path = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return len(fh.read())

    rows = [(rel, size(rel), n) for rel, n in sorted(table.items()) if rel != "SKILL.md" and size(rel) is not None]
    skills = os.path.join(root, ".claude", "skills")
    if "SKILL.md" in table and os.path.isdir(skills):
        each = [(size(".claude/skills/%s/SKILL.md" % s), s) for s in sorted(os.listdir(skills))
                if ".claude/skills/%s/SKILL.md" % s not in table]
        each = [(n, s) for n, s in each if n is not None]
        if each:
            n, s = max(each)
            rows.append(("each SKILL.md (%d), largest %s" % (len(each), s), n, table["SKILL.md"]))
    return rows


def report(root, ledger, today):
    paths, src = ledger["paths"], ledger["sources"]
    has_reads = bool(ledger["sessions"]) or bool(src.get("find_log"))
    named = []
    if ledger["sessions"]:
        named.append("Claude Code transcripts in %s (%d sessions)" % (", ".join(src["transcripts"]) or "the ledger",
                                                                      src["sessions"]))
    if src.get("find_log"):
        named.append("find log (%d queries)" % src["find_log"])
    if src.get("git") is not None:
        named.append("git log (%d commits)" % src["git"])
    lines = ["# Paths report", "",
             "Refreshed %s. Last pass: %s. Window: %d days (dormant: %d)."
             % (ledger["refreshed"], ledger.get("last_pass") or "never", HOT_DAYS, DORMANT_DAYS),
             "Sources: %s." % ("; ".join(named) or "none")]
    if not has_reads:
        lines.append("Reads not measured: no Claude Code transcripts and no find log on this machine.")

    def recent(rel, kinds, days=HOT_DAYS):
        return sum(n for k in kinds for d, n in paths.get(rel, {}).get(k, {}).items() if within(d, today, days))

    def last(rel, kinds):
        return max([d for k in kinds for d in paths.get(rel, {}).get(k, {})] or [""])

    hot = sorted(rel for rel in paths if recent(rel, READS) >= HOT_READS)
    hot.sort(key=lambda r: (recent(r, READS), last(r, READS)), reverse=True)  # most walked, then latest
    drafts = []
    for rel in hot:
        if rel.endswith(".md") and rel not in ledger["paved"]:
            with open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace") as fh:
                if find.plain(find.frontmatter(fh.read()).get("status", "")) == "draft":
                    drafts.append(rel)

    def steps_line(rel, kinds, noun):
        n, by_find = recent(rel, kinds), recent(rel, ("find",))
        extra = " (%d by find)" % by_find if by_find and noun == "reads" else ""
        return "- %s: %d %s%s, last %s" % (rel, n, noun, extra, last(rel, kinds))

    if has_reads:
        lines += ["", "## Hot: %d or more reads in %d days" % (HOT_READS, HOT_DAYS)]
        lines += [steps_line(rel, READS, "reads") for rel in hot[:TOP_HOT]] or ["None yet."]
        if len(hot) > TOP_HOT:
            lines.append("And %d more." % (len(hot) - TOP_HOT))
        lines += ["", "## Fixed load per session type, %d days" % HOT_DAYS]
        types = sorted(ledger["types"].items(), key=lambda kv: (-kv[1]["sessions"], kv[0]))
        if types:
            lines += ["| Type | Sessions | Average fixed load |", "|---|---|---|"]
            lines += ["| %s | %d | %s |" % (t, v["sessions"], "{:,} chars".format(v["fixed_load"])
                                            if v["fixed_load"] is not None else "no useful action") for t, v in types]
        else:
            lines.append("No Claude Code session in %d days." % HOT_DAYS)
        folders = {}
        for rel in notes(root):
            folder = rel.split("/")[0] if "/" in rel else "(root)"
            total, cold = folders.get(folder, (0, 0))
            folders[folder] = (total + 1, cold + (not recent(rel, READS, DORMANT_DAYS)))
        order = sorted(folders, key=lambda f: (f == "(root)", f))
        lines += ["", "## Dormant: no read in %d days, counts only" % DORMANT_DAYS,
                  ", ".join("%s %d of %d" % (f, folders[f][1], folders[f][0]) for f in order)]
    else:
        written = sorted((rel for rel in paths if recent(rel, ("write", "git"))),
                         key=lambda r: (-recent(r, ("write", "git")), r))
        lines += ["", "## Writes in %d days" % HOT_DAYS]
        if src.get("git") is None:
            lines.append("Not measured: the vault is not a git repo with commits.")
        else:
            lines += [steps_line(rel, ("write", "git"), "writes") for rel in written[:TOP_LIST]] or ["None."]
        inbound, names = {}, {}
        for rel in notes(root):
            names.setdefault(os.path.basename(rel)[:-3].lower(), rel)
        for rel in notes(root):
            with open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace") as fh:
                for target in find.LINK.findall(fh.read()):
                    hit = names.get(os.path.basename(target.strip()).lower())
                    if hit and hit != rel:
                        inbound[hit] = inbound.get(hit, 0) + 1
        lines += ["", "## Inbound links"]
        lines += ["- %s: %d link%s" % (rel, n, "" if n == 1 else "s") for rel, n in
                  sorted(inbound.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_LIST]] or ["None yet."]

    lines += ["", "## Size budgets", "| File | Chars | Budget | Used |", "|---|---|---|---|"]
    lines += ["| {} | {:,} | {:,} | {}%{} |".format(label, n, b, n * 100 // b if b else 0, " over" if n > b else "")
              for label, n, b in budget_rows(root)]
    if has_reads:
        lines += ["", "## Drafts wanting paving: hot, `status: draft`",
                  "%d hot draft%s." % (len(drafts), "" if len(drafts) == 1 else "s")]
        lines += ["- %s: %d reads" % (rel, recent(rel, READS)) for rel in drafts[:TOP_LIST]]
    lines += ["", "## Paved, waiting for your verify"]
    lines += ["- %s (paved %s)" % (rel, day) for rel, day in sorted(ledger["paved"].items())] or ["None yet."]
    if has_reads:
        lines += ["", "## Signposts: missed twice or more in %d days" % HOT_DAYS]
        signs = sorted(ledger["signposts"].items(), key=lambda kv: (-kv[1]["misses"], kv[0]))
        lines += ['- "%s": %d misses, last %s' % (q, m["misses"], m["last"])
                  for q, m in signs[:TOP_LIST]] or ["None."]
    return "\n".join(lines) + "\n"


def main():
    if os.path.exists(os.path.join(VAULT, ".bed.json")):
        return 0  # a bed keeps no ledger: its footsteps are walked in the brain
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="refresh", choices=["refresh"],
                    help="refresh (the default): update .paths/ledger.json and .paths/report.md")
    ap.add_argument("--today", help="YYYY-MM-DD to count from instead of today (for tests)")
    ap.add_argument("--transcripts", action="append", default=[], metavar="DIR",
                    help="a folder of Claude Code transcripts (.jsonl) of this vault to read as well")
    args = ap.parse_args()
    try:
        today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    except ValueError:
        ap.error("--today takes YYYY-MM-DD")
    ledger, opened, unchanged = refresh(VAULT, today, [os.path.abspath(d) for d in args.transcripts])
    with open(os.path.join(VAULT, REPORT), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report(VAULT, ledger, today))
    print("paths: %d transcripts read, %d unchanged; the report is .paths/report.md" % (opened, unchanged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
