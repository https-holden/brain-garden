#!/usr/bin/env python3
"""Send notes from this brain to its beds, and bring the beds' edits back. Standard library only.

    python3 bin/beds.py status [bed]                    what each bed gets, and what changed there
    python3 bin/beds.py push [bed] [--dry-run] [--force]
    python3 bin/beds.py pull [bed] [--dry-run]
    python3 bin/beds.py clone [bed]                     clone each bed with a remote that is not on disk

A bed is a sibling git repository holding the part of this brain that other people may see,
and itself a working vault. The brain is the master: push sends, pull brings edits back. With
no bed configured every command says so and writes nothing. Beds are listed under `beds` in
bin/vault.json, `path` relative to the vault root:

    "beds": [{"name": "recipes", "path": "../sam-recipes", "remote": "<git url, optional>",
              "topics": ["Recipes"], "strip": ["source", "rating"]}]

What goes: a note whose `beds` property names the bed or one of whose `categories` is a topic
the bed includes, those topics' own pages in Categories/, and the files a sent note embeds
(![[...]]). Never, whatever the tags: Daily/, People/, Templates/, bin/, any dot folder
(.paths/ among them) and any root file (Me.md, Now.md, Sources.md, Home.md and the rest).

push refuses while bin/lint.py has errors, while a file it would send contains a word from
bin/never-share.txt (one word or phrase per line, `#` for a comment, case-insensitive, whole
word; git-ignored), and, unless --force, while the bed has changes not yet pulled: commits
since the last sync (on its remote too), or a sent note changed or deleted there. It strips
the `strip` properties and `beds`, keeps only the bed's own topics in `categories`, turns each
[[link]] in a note's body into a relative Markdown link ([Title](../Notes/Title.md)) when the
target is in the bed and into its alias or title when it is not (Base embeds stay as they
are), and writes on each topic page a list of its notes between `<!-- beds:list:start -->` and
`<!-- beds:list:end -->`. It keeps the bed a working vault (CLAUDE.md, Rules.md, Templates/,
bin/lint.py, bin/find.py and bin/vault.json, the .obsidian basics, .gitignore, and .bed.json,
the marker that tells every script this folder is a bed), removes what is no longer sent,
commits in the bed, and pushes when the bed has a remote.

pull takes each note changed in the bed back into the brain when the brain's copy has not
changed since the last sync: lines changed in the bed come back with their links as [[links]],
lines not changed keep the brain's text, and stripped properties and dropped topics are put
back. It reports, and never applies, conflicts (changed on both sides), deletions, renames and
new files. It never deletes a note in the brain.

The sync state of each bed is .paths/beds/<name>.json, committed with the brain: the bed
commit last synced, and a hash of the brain's copy and of the bed's copy of each note then.
Every git call runs with -C and with no GIT_ variable inherited.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
from datetime import datetime
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find  # noqa: E402

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEVER = {"Daily", "People", "Templates", "Attachments", "bin"}  # top folders whose notes never go
NO_KIND = ("Daily", "People")  # kinds a bed does not have
START, END = "<!-- beds:list:start -->", "<!-- beds:list:end -->"
WIKI = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")
MDLINK = re.compile(r"(!?)\[([^\]\n]*)\]\(([^()\s]+)\)")
KEY = re.compile(r"^([A-Za-z_][\w-]*):")
OBSIDIAN = ("app.json", "appearance.json", "core-plugins.json", "templates.json", "types.json",
            "snippets/vault.css")
NOT_NOTES = ("CLAUDE.md", "Rules.md", "README.md", "LICENSE", ".gitignore", ".bed.json")
NOT_NOTE_DIRS = ("bin/", "Templates/", ".obsidian/", ".paths/", ".claude/", ".trash/")
NONE = ("beds: no bed is configured. To add one, list it under `beds` in bin/vault.json "
        "(\"Beds\" in Rules.md shows how).")

BED_CLAUDE = """# The {name} bed

A bed: the part of someone's brain garden they share, as a working Obsidian vault of its own.
Their brain is the master. It sends the notes here with `bin/beds.py push`, and brings the
edits made here back with `bin/beds.py pull`.

- Edit, add and link notes as in any vault, run `python3 bin/lint.py`, then commit (and push,
  when the bed has a remote). An edit to a note goes back to the brain. A new note, a deletion
  or a rename is reported to the owner, who decides; nothing here deletes a note in the brain.
- On a topic page, the list between `{start}` and `{end}` is rewritten by every push: edits
  inside it are lost.
- This file, `Rules.md`, `Templates/`, `bin/`, `.gitignore` and `.bed.json` come from the brain
  and are replaced by every push. Ask the owner to change a rule.
- `Rules.md` is binding here: the kinds, the properties, the conventions. What it says about
  daily notes, `Now.md`, `Me.md`, people and bringing things in is the owner's own.
- `Me.md`, `Now.md`, `Daily/` and `People/` are git-ignored here: a personal layer of your own
  stays on your machine.

## Looking things up

1. `python3 bin/find.py <words from the ask>`: one line per note that has every word
   (`Folder/title :: aliases :: categories :: status`); `--topic <Topic>` lists one topic.
2. Frontmatter grep: `categories` for the topic, then any property the ask names.
3. Full text grep on distinctive strings.

Read matching notes whole. `verified` can be stated, `draft` must be hedged, `stale` is never
quoted.
"""

BED_IGNORE = """# Written by the brain's bin/beds.py on every push.
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/workspace/
.obsidian/cache/
.trash/
.DS_Store
.claude/settings.local.json
__pycache__/
.paths/find.log

# A personal layer of your own stays on your machine
Me.md
Now.md
Daily/
People/
"""


# ------------------------------------------------------------ small helpers


def git(where, *args):
    """Run git in `where` (always -C) with no GIT_ variable inherited. (ok, stdout, stderr)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        res = subprocess.run(["git", "-C", where] + list(args), capture_output=True, text=True, env=env)
    except OSError as exc:
        return False, "", str(exc)
    return res.returncode == 0, res.stdout, res.stderr.strip()


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def put(root, rel, data):
    """Write data (text or bytes) at root/rel when it differs. True when written."""
    path = os.path.join(root, *rel.split("/"))
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    if os.path.exists(path):
        with open(path, "rb") as fh:
            if fh.read() == raw:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(raw)
    if rel.endswith(".py"):
        os.chmod(path, 0o755)
    return True


def split(text):
    """(frontmatter as [(key, lines)], body), the same reading as find.py; (None, text) without one."""
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return None, text
    end = text.index("\n---", 3)
    groups = []
    for line in text[4:end].split("\n") if end > 3 else []:
        m = KEY.match(line)
        if m or not groups:
            groups.append([m.group(1) if m else None, line])
        else:
            groups[-1][1] += "\n" + line
    return [tuple(g) for g in groups], text[end + 4:]


def join(groups, body):
    if groups is None:
        return body
    return "---\n" + "".join(chunk + "\n" for _, chunk in groups) + "---" + body


def topics_of(chunk):
    """The topic names in a `categories` frontmatter chunk."""
    return find.values(find.frontmatter("---\n%s\n---\n" % chunk).get("categories", ""))


def categories_chunk(names):
    return "categories:" + ("".join('\n  - "[[%s]]"' % n for n in names) if names else " []")


def with_list(text, items):
    block = "%s\n## Notes\n\n%s%s\n" % (START, "".join("- %s\n" % i for i in items), END)
    return text.rstrip("\n") + "\n\n" + block


def drop_list(text):
    a = text.find(START)
    b = text.find(END, a + 1)
    if a < 0 or b < 0:
        return text
    return text[:a].rstrip("\n") + "\n" + text[b + len(END):].lstrip("\n")


def never_words():
    path = os.path.join(VAULT, "bin", "never-share.txt")
    if not os.path.exists(path):
        return None
    words = [w.strip() for w in read(path).split("\n") if w.strip() and not w.lstrip().startswith("#")]
    if not words:
        return None
    return re.compile(r"(?<!\w)(%s)(?!\w)" % "|".join(re.escape(w) for w in words), re.I), words


def never_hit(pattern, text):
    """The never-share word (as listed) that text contains, or None."""
    if not pattern:
        return None
    m = pattern[0].search(text)
    if not m:
        return None
    return next((w for w in pattern[1] if w.lower() == m.group(1).lower()), m.group(1))


# ------------------------------------------------------------ the brain


class Brain:
    """Every note and file of the vault that a bed could get, and how a [[link]] resolves."""

    def __init__(self):
        self.notes, self.files = [], []
        for root, dirs, names in os.walk(VAULT):
            here = os.path.relpath(root, VAULT).replace(os.sep, "/")
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (here == "." and d == "bin"))
            for fn in sorted(names):
                if not fn.startswith("."):
                    rel = posixpath.normpath(posixpath.join(here, fn))
                    (self.notes if fn.endswith(".md") else self.files).append(rel)
        self.text = {p: read(os.path.join(VAULT, *p.split("/"))) for p in self.notes}
        self.fm = {p: find.frontmatter(t) for p, t in self.text.items()}
        self.names, self.count, self.paths = {}, {}, {}
        for p in self.notes:
            title = posixpath.basename(p)[:-3].lower()
            self.paths[p[:-3].lower()] = p
            self.names.setdefault(title, p)
            self.count[title] = self.count.get(title, 0) + 1
        for p in self.notes:
            for alias in find.values(self.fm[p].get("aliases", "")):
                self.names.setdefault(alias.lower(), p)
        for f in self.files:
            self.paths.setdefault(f.lower(), f)
            self.names.setdefault(posixpath.basename(f).lower(), f)

    def resolve(self, target):
        t = target.strip().lstrip("/").lower()
        t = t[:-3] if t.endswith(".md") else t
        return self.paths.get(t) or self.names.get(t) or self.names.get(posixpath.basename(t))

    def wikiname(self, path):
        """What a [[link]] to this path says: its title, or its path when two notes share the title."""
        if not path.endswith(".md"):
            return posixpath.basename(path)
        title = posixpath.basename(path)[:-3]
        return path[:-3] if self.count.get(title.lower(), 0) > 1 else title


def chosen(brain, bed):
    """(notes, topic pages, files) this bed gets."""
    name = bed["name"].lower()
    topics = {str(t).lower() for t in bed.get("topics") or []}
    notes = []
    for p in brain.notes:
        top = p.split("/")[0]
        if "/" not in p or top in NEVER:
            continue
        fm = brain.fm[p]
        tagged = name in [v.lower() for v in find.values(fm.get("beds", ""))]
        cats = {c.lower() for c in find.values(fm.get("categories", ""))}
        page = top == "Categories" and posixpath.basename(p)[:-3].lower() in topics
        if tagged or page or topics & cats:
            notes.append(p)
    pages = {posixpath.basename(p)[:-3].lower() for p in notes if p.startswith("Categories/")}
    files = set()
    for p in notes:
        for bang, inner in WIKI.findall(brain.text[p]):
            target = inner.split("|")[0].split("#")[0]
            path = brain.resolve(target) if bang and target.strip() else None
            if path and not path.endswith((".md", ".base")) and "/" in path and path.split("/")[0] not in (
                    "Daily", "People", "Templates"):
                files.add(path)
    return notes, pages, sorted(files)


def render_line(brain, line, here, inbed):
    """One body line as the bed gets it: [[links]] to the bed relative, the rest plain text."""
    def swap(m):
        bang, inner = m.group(1), m.group(2)
        target, _, alias = inner.partition("|")
        target, _, heading = target.partition("#")
        target, alias, heading = target.strip(), alias.strip(), heading.strip()
        if not target or target.lower().endswith(".base"):
            return m.group(0)
        path = brain.resolve(target)
        title = posixpath.basename(target)
        if path in inbed:
            href = quote(posixpath.relpath(path, here or "."), safe="/")
            href += "#" + quote(heading, safe="") if heading else ""
            return "%s[%s](%s)" % (bang, alias if bang else (alias or title), href)
        return (alias if not bang else "") or title
    return WIKI.sub(swap, line)


def unrender_line(brain, line, here):
    """One body line from the bed, its relative Markdown links back as [[links]]."""
    def swap(m):
        bang, text, href = m.groups()
        if "://" in href or href.startswith(("#", "mailto:")):
            return m.group(0)
        path, _, heading = href.partition("#")
        target = posixpath.normpath(posixpath.join(here or ".", unquote(path)))
        if target == ".." or target.startswith("../"):
            return m.group(0)
        known = brain.resolve(target)
        name = brain.wikiname(known) if known else posixpath.basename(target)
        name = name[:-3] if name.endswith(".md") else name
        ref = name + ("#" + unquote(heading) if heading else "")
        if bang:
            return "![[%s%s]]" % (ref, "|" + text if text else "")
        return "[[%s]]" % ref if text == posixpath.basename(name) else "[[%s|%s]]" % (ref, text)
    return MDLINK.sub(swap, line)


def render(brain, p, inbed, pages, strip):
    """The note as the bed gets it, without the topic list."""
    groups, body = split(brain.text[p])
    if groups is not None:
        kept = []
        for key, chunk in groups:
            if key in strip:
                continue
            if key == "categories":
                names = topics_of(chunk)
                keep = [n for n in names if n.lower() in pages]
                chunk = chunk if keep == names else categories_chunk(keep)
            kept.append((key, chunk))
        groups = kept
    here = posixpath.dirname(p)
    return join(groups, "\n".join(render_line(brain, ln, here, inbed) for ln in body.split("\n")))


def merge_back(brain, p, bed_text, inbed, pages, strip):
    """The brain's note with the bed's edits in: changed lines from the bed, unchanged ones as they were."""
    b_groups, b_body = split(brain.text[p])
    t_groups, t_body = split(drop_list(bed_text))
    here = posixpath.dirname(p)
    mine = b_body.rstrip("\n").split("\n")
    theirs = t_body.rstrip("\n").split("\n")
    shown = [render_line(brain, ln, here, inbed) for ln in mine]
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, shown, theirs, autojunk=False).get_opcodes():
        out += mine[i1:i2] if tag == "equal" else [unrender_line(brain, ln, here) for ln in theirs[j1:j2]]
    body = "\n".join(out) + (b_body[len(b_body.rstrip("\n")):] or "\n")
    if b_groups is None and t_groups is None:
        return body
    theirs_fm = {k: c for k, c in t_groups or [] if k is not None}
    groups, seen = [], set()
    for key, chunk in b_groups or []:
        seen.add(key)
        if key is None or key in strip:
            groups.append((key, chunk))
        elif key == "categories":
            names = topics_of(chunk)
            sent = [n for n in names if n.lower() in pages]
            back = topics_of(theirs_fm["categories"]) if "categories" in theirs_fm else []
            if [n.lower() for n in back] == [n.lower() for n in sent]:
                groups.append((key, chunk))
            else:
                lower = {n.lower() for n in back}
                groups.append((key, categories_chunk(back + [n for n in names
                                                           if n.lower() not in pages and n.lower() not in lower])))
        elif key in theirs_fm:
            groups.append((key, theirs_fm[key]))
    groups += [(k, c) for k, c in t_groups or [] if k is not None and k not in seen]
    return join(groups, body)


# ------------------------------------------------------------ the bed


def where(bed):
    return os.path.normpath(os.path.join(VAULT, bed["path"]))


def state_file(name):
    return os.path.join(VAULT, ".paths", "beds", "%s.json" % name)


def load_state(name):
    path = state_file(name)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(name, data):
    path = state_file(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def has_upstream(home):
    return git(home, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")[0]


def count(home, span):
    ok, out, _ = git(home, "rev-list", "--count", span)
    return int(out.strip()) if ok else None


def scaffolding(conf, name, strip):
    """The files that keep a bed a working vault, as {bed path: text or bytes}."""
    out = {"CLAUDE.md": BED_CLAUDE.format(name=name, start=START, end=END), ".gitignore": BED_IGNORE,
           ".bed.json": json.dumps({"bed": name}) + "\n"}
    for rel in ("Rules.md", "bin/lint.py", "bin/find.py"):
        path = os.path.join(VAULT, *rel.split("/"))
        if os.path.exists(path):
            out[rel] = read(path)
    kinds = conf.get("kinds", {})
    bed_conf = {k: v for k, v in conf.items() if k != "beds"}
    bed_conf["kinds"] = {k: v for k, v in kinds.items() if k not in NO_KIND}
    out["bin/vault.json"] = json.dumps(bed_conf, indent=2) + "\n"
    skip = {"Templates/" + kinds[k].get("template", "") for k in NO_KIND if k in kinds}
    skip |= {"Templates/Bases/%s.base" % k for k in NO_KIND}
    base = os.path.join(VAULT, "Templates")
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for fn in sorted(files):
            rel = "Templates/" + os.path.relpath(os.path.join(root, fn), base).replace(os.sep, "/")
            if fn.startswith(".") or rel in skip:
                continue
            text = read(os.path.join(root, fn))
            if fn.endswith(".md"):
                groups, body = split(text)
                text = join(None if groups is None else [(k, c) for k, c in groups if k not in strip], body)
            out[rel] = text
    for rel in OBSIDIAN:
        path = os.path.join(VAULT, ".obsidian", *rel.split("/"))
        if os.path.exists(path):
            out[".obsidian/" + rel] = read(path)
    return out


def survey(bed, state, notes):
    """What changed in the bed since the last sync. Fetches first when the bed has a remote."""
    home = where(bed)
    s = dict(changed=[], deleted=[], renamed=[], new=[], commits=0, ahead=0, fetch="")
    synced = state.get("notes", {})
    for p in sorted(synced):
        path = os.path.join(home, *p.split("/"))
        if not os.path.exists(path):
            s["deleted"].append(p)
        elif digest(path) != synced[p]["bed"]:
            s["changed"].append(p)
    ok, listed, _ = git(home, "ls-files", "-z", "-co", "--exclude-standard")
    known = set(synced) | set(state.get("files", []))
    s["new"] = sorted(p for p in (listed.split("\0") if ok else []) if p and p not in known
                      and p not in NOT_NOTES and not p.startswith(NOT_NOTE_DIRS))
    for old in list(s["deleted"]):
        ok, before, _ = git(home, "show", "%s:%s" % (state.get("commit", ""), old))
        for new in [n for n in s["new"] if n.endswith(".md")] if ok else []:
            text = read(os.path.join(home, *new.split("/")))
            if alike(before, text) and alike(split(before)[1], split(text)[1]):
                s["renamed"].append((old, new))
                s["deleted"].remove(old)
                s["new"].remove(new)
                break
    if state.get("commit"):
        s["commits"] = count(home, "%s..HEAD" % state["commit"])
    if bed.get("remote") and has_upstream(home):
        ok, _, err = git(home, "fetch", "-q")
        s["fetch"] = "" if ok else err.split("\n")[-1]
        s["ahead"] = count(home, "HEAD..@{u}") or 0
    return s


def alike(a, b):
    """Close enough that a deleted note and a new one are one note renamed."""
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.8


def pending(s, notes):
    """Why a push would overwrite something not yet pulled (empty when nothing)."""
    why = []
    if s["commits"] is None:
        why.append("the bed's history does not have the commit last synced")
    elif s["commits"]:
        why.append("%d commit(s) in the bed since the last sync" % s["commits"])
    if s["ahead"]:
        why.append("%d commit(s) on its remote not in the bed yet" % s["ahead"])
    why += ["%s changed in the bed" % p for p in s["changed"]]
    why += ["%s deleted in the bed" % p for p in s["deleted"] if p in notes]
    why += ["%s renamed in the bed" % a for a, _ in s["renamed"] if a in notes]
    return why


def plan(brain, conf, bed):
    """Everything a push would write into the bed: {bed path: text or bytes}, and what goes."""
    notes, pages, files = chosen(brain, bed)
    strip = {str(k) for k in bed.get("strip") or []} | {"beds"}
    inbed = set(notes) | set(files)
    texts = {p: render(brain, p, inbed, pages, strip) for p in notes}
    for p in notes:
        if p.startswith("Categories/"):
            topic = posixpath.basename(p)[:-3].lower()
            members = sorted((q for q in notes if q != p and topic in {
                c.lower() for c in find.values(find.frontmatter(texts[q]).get("categories", ""))}),
                key=lambda q: (q.split("/")[0].lower(), posixpath.basename(q).lower()))
            items = ["[%s](%s)" % (posixpath.basename(q)[:-3], quote(posixpath.relpath(q, posixpath.dirname(p)),
                                                                      safe="/")) for q in members]
            texts[p] = with_list(texts[p], items)
    out = dict(texts)
    for f in files:
        with open(os.path.join(VAULT, *f.split("/")), "rb") as fh:
            out[f] = fh.read()
    return notes, files, pages, strip, out, scaffolding(conf, bed["name"], strip)


# ------------------------------------------------------------ commands


def say(name, text):
    print("beds: %s: %s" % (name, text))


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def status(brain, conf, bed):
    name, home = bed["name"], where(bed)
    notes, files, _, _, out, _ = plan(brain, conf, bed)
    state = load_state(name)
    print("beds: %s -> %s (%s)" % (name, bed["path"], "remote: %s" % bed["remote"] if bed.get("remote")
                                   else "no remote"))
    print("  sends %s and %s" % (plural(len(notes), "note"), plural(len(files), "file")))
    if not os.path.isdir(home):
        print("  not on disk yet: push makes it%s" % (", clone fetches it" if bed.get("remote") else ""))
        return True
    print("  last sync: %s" % ("%s, bed commit %s" % (state.get("synced"), state.get("commit", "")[:7])
                               if state else "never"))
    gone = [p for p in state.get("notes", {}) if p not in out] + [p for p in state.get("files", []) if p not in out]
    stale = [p for p, data in out.items() if not os.path.exists(os.path.join(home, *p.split("/")))
             or put_differs(home, p, data)]
    print("  push would write %d and remove %d" % (len(stale), len(gone)))
    s = survey(bed, state, notes)
    print("  in the bed since then: %d changed, %d deleted, %d renamed, %d new, %s commit(s)%s"
          % (len(s["changed"]), len(s["deleted"]), len(s["renamed"]), len(s["new"]),
             "?" if s["commits"] is None else s["commits"],
             ", %d more on the remote" % s["ahead"] if s["ahead"] else ""))
    return True


def put_differs(home, rel, data):
    with open(os.path.join(home, *rel.split("/")), "rb") as fh:
        return fh.read() != (data if isinstance(data, bytes) else data.encode("utf-8"))


def never_shared(brain, conf, bed, words):
    """Print one refusal per file this bed would get that holds a never-share word. True when none."""
    _, _, _, _, out, scaffold = plan(brain, conf, bed)
    hits = [(p, never_hit(words, t)) for p, t in sorted(list(out.items()) + list(scaffold.items()))
            if p.endswith(".md")]
    for p, w in hits:
        if w:
            say(bed["name"], "REFUSED  %s contains \"%s\", a word in bin/never-share.txt" % (p, w))
    return not any(w for _, w in hits)


def push(brain, conf, bed, dry, force):
    name, home = bed["name"], where(bed)
    notes, files, _, _, out, scaffold = plan(brain, conf, bed)
    state = load_state(name)
    exists = os.path.isdir(home)
    if exists and not os.path.exists(os.path.join(home, ".git")):
        say(name, "REFUSED  %s exists but is not a git repository" % bed["path"])
        return False
    if exists and not state and not os.path.exists(os.path.join(home, ".bed.json")):
        ok, listed, _ = git(home, "ls-files", "-z", "-co", "--exclude-standard")
        other = [p for p in listed.split("\0") if p and p.split("/")[0] not in (
            "README.md", "LICENSE", ".gitignore", ".gitattributes")]
        if other:
            say(name, "REFUSED  %s holds other files and is not a bed (no .bed.json): point `path` at an "
                      "empty folder or repository" % bed["path"])
            return False
    s = survey(bed, state, notes) if exists else None
    why = pending(s, notes) if s else []
    if s and s["fetch"]:
        say(name, "could not reach the remote: %s" % s["fetch"])
    if why and not force:
        say(name, "REFUSED  the bed has changes not yet pulled: %s. Run `python3 bin/beds.py pull %s` first, "
                  "or push --force to overwrite them" % ("; ".join(why), name))
        return False
    sent = set(out)
    gone = [p for p in list(state.get("notes", {})) + list(state.get("files", [])) if p not in sent]
    if dry:
        if not exists:
            say(name, "would make the bed at %s%s" % (bed["path"], " from %s" % bed["remote"] if bed.get("remote")
                                                      else ""))
        for p in sorted(out):
            path = os.path.join(home, *p.split("/"))
            if not os.path.exists(path) or put_differs(home, p, out[p]):
                print("  %s %s" % ("~" if os.path.exists(path) else "+", p))
        for p in sorted(gone):
            print("  - %s" % p)
        say(name, "dry run: would send %s and %s, remove %d, and keep the bed a vault; wrote nothing"
            % (plural(len(notes), "note"), plural(len(files), "file"), len(gone)))
        return True
    if not exists:
        parent = os.path.dirname(home)
        os.makedirs(parent, exist_ok=True)
        if bed.get("remote"):
            ok, _, err = git(parent, "clone", "-q", bed["remote"], os.path.basename(home))
        else:
            os.makedirs(home)
            ok, _, err = git(home, "init", "-q")
        if not ok:
            say(name, "could not make the bed: %s" % err)
            return False
    if s and s["ahead"]:
        ok, _, err = git(home, "merge", "--ff-only", "-q", "@{u}")
        if not ok:
            say(name, "could not bring in the remote's commits first: %s" % err)
            return False
    for p, data in sorted(list(out.items()) + list(scaffold.items())):
        put(home, p, data)
    for p in gone:
        path = os.path.join(home, *p.split("/"))
        if os.path.exists(path):
            os.remove(path)
    subprocess.run([sys.executable, os.path.join(home, "bin", "find.py"), "--rebuild"], cwd=home)
    git(home, "add", "-A")
    staged = not git(home, "diff", "--cached", "--quiet")[0]
    if staged:
        ok, _, err = git(home, "commit", "-q", "-m", "Push from the brain: %d notes, %d files"
                         % (len(notes), len(files)))
        if not ok:
            say(name, "could not commit in the bed: %s" % err)
            return False
    if bed.get("remote"):
        if not git(home, "remote", "get-url", "origin")[0]:  # a bed that was made before it had a remote
            git(home, "remote", "add", "origin", bed["remote"])
        ok, _, err = git(home, "push", "-q", "-u", "origin", "HEAD")
        if not ok:
            say(name, "committed in the bed, but could not push to its remote: %s" % err)
            return False
    head = git(home, "rev-parse", "HEAD")[1].strip()
    save_state(name, {"bed": name, "commit": head, "synced": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "notes": {p: {"brain": digest(os.path.join(VAULT, *p.split("/"))),
                                    "bed": digest(os.path.join(home, *p.split("/")))} for p in notes},
                      "files": files})
    say(name, "%s %s (%s, %s)%s%s" % (
        "sent to" if staged else "nothing new for", bed["path"], plural(len(notes), "note"),
        plural(len(files), "file"), ", removed %d" % len(gone) if gone else "",
        ", pushed to its remote" if bed.get("remote") else ""))
    return True


def pull(brain, conf, bed, dry):
    name, home = bed["name"], where(bed)
    state = load_state(name)
    if not os.path.isdir(home):
        say(name, "not on disk at %s: run `python3 bin/beds.py clone`, or push to make it" % bed["path"])
        return False
    if not state:
        say(name, "never pushed from this brain, so nothing to pull yet")
        return True
    notes, pages, files = chosen(brain, bed)
    strip = {str(k) for k in bed.get("strip") or []} | {"beds"}
    inbed = set(notes) | set(files)
    s = survey(bed, state, notes)
    if s["fetch"]:
        say(name, "could not reach the remote: %s" % s["fetch"])
    if s["ahead"]:
        if dry:
            say(name, "%d commit(s) on the remote are not in the bed yet; a pull without --dry-run brings "
                      "them in first" % s["ahead"])
        else:
            ok, _, err = git(home, "merge", "--ff-only", "-q", "@{u}")
            if not ok:
                say(name, "could not bring in the remote's commits: %s" % err)
                return False
            s = survey(bed, state, notes)
    pulled = []
    for p in s["changed"]:
        mine = os.path.join(VAULT, *p.split("/"))
        if not os.path.exists(mine):
            say(name, "CONFLICT  %s changed in the bed but is gone from the brain; applied to neither" % p)
            continue
        if digest(mine) != state["notes"][p]["brain"]:
            say(name, "CONFLICT  %s changed in the brain and in the bed since the last sync; applied to "
                      "neither. Merge the bed's version in by hand, then push --force" % p)
            continue
        text = merge_back(brain, p, read(os.path.join(home, *p.split("/"))), inbed, pages, strip)
        if not dry:
            put(VAULT, p, text)
            state["notes"][p] = {"brain": sha(text), "bed": digest(os.path.join(home, *p.split("/")))}
        pulled.append(p)
        say(name, "%s  %s" % ("WOULD PULL" if dry else "PULLED", p))
    for p in s["deleted"]:
        say(name, "DELETED  %s was deleted in the bed; not applied. Take it out of the bed in the brain "
                  "(its `beds` or its topic), or push --force to put it back" % p)
    for a, b in s["renamed"]:
        say(name, "RENAMED  %s became %s in the bed; not applied. Rename it in the brain the same way, "
                  "then push" % (a, b))
    for p in s["new"]:
        say(name, "NEW  %s is new in the bed; not applied. Copy it into the brain if you want it" % p)
    if not dry:
        state["commit"] = git(home, "rev-parse", "HEAD")[1].strip() or state.get("commit", "")
        state["synced"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_state(name, state)
        if pulled:
            find.rebuild(VAULT)
    say(name, "%s %d; reported, not applied: conflicts %d, deleted %d, renamed %d, new %d%s" % (
        "would pull" if dry else "pulled", len(pulled), len(s["changed"]) - len(pulled), len(s["deleted"]),
        len(s["renamed"]), len(s["new"]), " (dry run, wrote nothing)" if dry else ""))
    return True


def clone(bed):
    name, home = bed["name"], where(bed)
    if not bed.get("remote"):
        say(name, "no remote configured, nothing to clone")
        return True
    if os.path.exists(home):
        say(name, "already on disk at %s" % bed["path"])
        return True
    parent = os.path.dirname(home)
    os.makedirs(parent, exist_ok=True)
    ok, _, err = git(parent, "clone", "-q", bed["remote"], os.path.basename(home))
    say(name, "cloned %s into %s" % (bed["remote"], bed["path"]) if ok else "could not clone: %s" % err)
    return ok


def lint_errors():
    res = subprocess.run([sys.executable, os.path.join(VAULT, "bin", "lint.py")], cwd=VAULT,
                         capture_output=True, text=True)
    if res.returncode == 0:
        return []
    return [ln for ln in (res.stderr + res.stdout).split("\n") if ln.startswith("ERROR")] or [res.stderr.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "push", "pull", "clone"])
    ap.add_argument("bed", nargs="?", help="act on this bed only")
    ap.add_argument("--dry-run", action="store_true", help="push or pull: print what would change, write nothing")
    ap.add_argument("--force", action="store_true", help="push over changes in the bed not yet pulled")
    args = ap.parse_args()

    with open(os.path.join(VAULT, "bin", "vault.json"), encoding="utf-8") as fh:
        conf = json.load(fh)
    beds = conf.get("beds") or []
    if not beds:
        print(NONE)
        return 0
    if not isinstance(beds, list) or not all(isinstance(b, dict) and b.get("name") and b.get("path") for b in beds):
        print("beds: `beds` in bin/vault.json must be a list of {\"name\": ..., \"path\": ...}")
        return 1
    if args.bed:
        beds = [b for b in beds if b["name"] == args.bed]
        if not beds:
            print("beds: no bed named %r (configured: %s)" % (args.bed, ", ".join(b["name"] for b in conf["beds"])))
            return 1
    if args.command == "clone":
        return 0 if all([clone(b) for b in beds]) else 1
    brain = Brain()
    if args.command == "status":
        for b in beds:
            status(brain, conf, b)
        return 0
    if args.command == "pull":
        return 0 if all([pull(brain, conf, b, args.dry_run) for b in beds]) else 1
    errors = lint_errors()
    if errors:
        print("beds: REFUSED  lint has errors; fix them first (python3 bin/lint.py):")
        for e in errors:
            print("  %s" % e)
        return 1
    words = never_words()
    if not all([never_shared(brain, conf, b, words) for b in beds]):
        print("beds: REFUSED  nothing was pushed; take the word out of each note named, or keep the note home")
        return 1
    return 0 if all([push(brain, conf, b, args.dry_run, args.force) for b in beds]) else 1


if __name__ == "__main__":
    sys.exit(main())
