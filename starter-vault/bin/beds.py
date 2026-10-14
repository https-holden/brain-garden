#!/usr/bin/env python3
"""Send notes from this brain to its beds, and bring the beds' edits back. Standard library only.

    python3 bin/beds.py status [bed]                    what each bed gets, and what changed there
    python3 bin/beds.py push [bed] [--dry-run] [--force]
    python3 bin/beds.py pull [bed] [--dry-run]
    python3 bin/beds.py clone [bed]                     clone each bed with a remote that is not on disk

A bed is a sibling git repository holding the part of this brain that other people may see,
and itself a working vault. The brain is the master: push sends, pull brings edits back. With
no bed configured every command says so and writes nothing. Beds are listed under `beds` in
bin/vault.json, `path` relative to the vault root: a folder of its own, never the vault, inside
it, or one that holds it (refused, with no --force way round):

    "beds": [{"name": "recipes", "path": "../sam-recipes", "remote": "<git url, optional>",
              "topics": ["Recipes"], "strip": ["source", "rating"]}]

What goes: a note whose `beds` property names the bed or one of whose `categories` is a topic
the bed includes, those topics' own pages in Categories/, and the files a sent note embeds
(![[...]]). Never, whatever the tags: Daily/, People/, Templates/, bin/, any dot folder
(.paths/ among them), any root file (Me.md, Now.md, Sources.md, Home.md and the rest), and
any symlink, which is skipped and named.

push refuses while bin/lint.py has errors; while a file it would send holds a word from
bin/never-share.txt in its path, its properties or its text (one word or phrase per line, `#`
for a comment, case-insensitive, whole word; git-ignored; read through a symlink, and a list
that is there but cannot be read refuses the push); and, unless --force, while the bed
has changes not yet pulled (commits since the last sync, on its remote too, or a sent note
changed or deleted there) or, with no sync state in the brain, has commits or files at all. On
the way out it strips the `strip` properties and `beds`, keeps only the bed's own topics in
`categories`, and leaves out %% comments. In the body and in every other property, a [[link]]
to something in the bed becomes a relative Markdown link ([Title](../Notes/Title.md)) and a
link to anything else, [[link]] or Markdown link, becomes its plain text; links inside code
and Base embeds stay as they are. Each topic page gets a list of its notes between
`<!-- beds:list:start -->` and `<!-- beds:list:end -->`. Push keeps the bed a working vault
(CLAUDE.md, Rules.md, Templates/, bin/lint.py, bin/find.py, bin/vault.json, the .obsidian
basics, .gitignore, and .bed.json, the marker that tells every script this folder is a bed),
builds the bed's index with this vault's own find.py, removes what is no longer sent, commits
in the bed, and pushes when the bed has a remote. When that push fails (offline), the sync
state is still saved and the next push sends it.

pull takes each note changed in the bed back into the brain when the brain's copy has not
changed since the last sync: lines changed in the bed come back with their links as [[links]],
lines not changed keep the brain's text, and the stripped properties, dropped topics and any
property the bed's copy lacks are kept from the brain. It never changes which beds a note goes
to: a `beds` property from the bed, a topic that is not one of this bed's, and a change of
topics that would move the note into or out of any bed are held back and reported. It reports,
and never applies, conflicts (changed on both sides, a changed line that holds a %% comment, or
a folder where a note was), deletions, renames and new files. It never deletes a note in the
brain. Every file it or push writes replaces the old one (a new file, then a rename), so a
hardlink is cut, never written through.

Nothing in a bed is ever run, and no symlink in the bed or the brain is followed: push and
pull refuse while the bed holds one. --dry-run writes nothing anywhere: it does not fetch, and
the lint it runs does not rewrite the index.

The sync state of each bed is .paths/beds/<name>.json: the bed commit last synced, what was
sent and stripped, and a hash of the brain's copy and of the bed's copy of each note then.
Push and pull commit it in the brain when the brain is a git repository. Every git call runs
with -C and with no GIT_ variable inherited.
"""
from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import io
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from urllib.parse import quote, unquote

sys.dont_write_bytecode = True  # importing find and lint leaves no __pycache__ behind
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find  # noqa: E402

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEVER = {"Daily", "People", "Templates", "Attachments", "bin"}  # top folders whose notes never go
NO_KIND = ("Daily", "People")  # kinds a bed does not have
START, END = "<!-- beds:list:start -->", "<!-- beds:list:end -->"
WIKI = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")
MDLINK = re.compile(r'(!?)\[([^\]\n]*)\]\((<[^>\n]+>|[^()\s]+)(?:\s+"[^"\n]*")?\)')
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
TOKENS, CODE = re.compile(r"`+|%%"), re.compile(r"`+")
KEY = re.compile(r"^([A-Za-z_][\w-]*):")
OBSIDIAN = ("app.json", "appearance.json", "core-plugins.json", "templates.json", "types.json",
            "snippets/vault.css")
BED_BIN = ("lint.py", "find.py", "vault.json")
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
  and are replaced by every push. Ask the owner to change a rule. A symlink stops every push
  and pull until it is gone.
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


class Refused(Exception):
    """A write that would follow a symlink or leave the folder it belongs in."""


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


def within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def safe(root, rel):
    """True when root/rel stays inside root and nothing on the way to it is a symlink."""
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    path = root
    for part in parts:
        path = os.path.join(path, part)
        if os.path.islink(path):
            return False
    return within(path, root) and os.path.realpath(path) != os.path.realpath(root)


def in_the_way(root, rel):
    """True when something at root/rel stops a file being written there: a folder where the file
    goes, or a file where one of its folders goes."""
    path = root
    parts = rel.split("/")
    for i, part in enumerate(parts):
        path = os.path.join(path, part)
        last = i == len(parts) - 1
        if os.path.lexists(path) and (os.path.isdir(path) if last else not os.path.isdir(path)):
            return True
    return False


def put(root, rel, data):
    """Write data (text or bytes) at root/rel when it differs: a regular file inside root, never
    through a symlink, and never into an existing file (a new file replaces it, so a hardlink
    there is cut, not written through). True when written."""
    if not safe(root, rel) or in_the_way(root, rel):
        raise Refused("%s is a symlink, a folder, or leaves %s; nothing written there" % (rel, root))
    path = os.path.join(root, *rel.split("/"))
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            if fh.read() == raw:
                return False
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=folder, prefix=".beds-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        os.chmod(temp, 0o755 if rel.endswith(".py") else 0o644)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return True


def links_under(home):
    """Every symlink under the bed, file or folder, outside .git/."""
    found = []
    for root, dirs, files in os.walk(home):
        here = os.path.relpath(root, home).replace(os.sep, "/")
        if here == ".":
            dirs[:] = [d for d in dirs if d != ".git"]
        found += [posixpath.normpath(posixpath.join(here, n)) for n in dirs + files
                  if os.path.islink(os.path.join(root, n))]
    return sorted(found)


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


def walk_body(body, fn, comments=True):
    """One line out per body line: fn applied to the text outside fenced code, inline code and,
    when `comments`, %% comments, which are left out. Also, per line, whether it held a comment."""
    tokens = TOKENS if comments else CODE
    out, held = [], []
    fence, inside = None, False
    for line in body.split("\n"):
        mark = FENCE.match(line)
        if fence:
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence):
                fence = None
            out.append(line)
            held.append(False)
            continue
        if mark and not inside:
            fence = mark.group(1)
            out.append(line)
            held.append(False)
            continue
        parts, pos, had = [], 0, inside
        while True:
            if inside:
                j = line.find("%%", pos)
                if j < 0:
                    break
                pos, inside = j + 2, False
                continue
            t = tokens.search(line, pos)
            if not t:
                parts.append(fn(line[pos:]))
                break
            parts.append(fn(line[pos:t.start()]))
            if t.group(0) == "%%":
                pos, inside, had = t.end(), True, True
            else:
                close = line.find(t.group(0), t.end())
                end = close + len(t.group(0)) if close >= 0 else t.end()
                parts.append(line[t.start():end])
                pos = end
        text = "".join(parts)
        out.append(text.rstrip() if had else text)
        held.append(had)
    return out, held


def never_words():
    """(pattern, words) from bin/never-share.txt, or None when there is no list. It is the owner's own
    file, so a symlink to it is followed; one that is there but cannot be read refuses the push."""
    path = os.path.join(VAULT, "bin", "never-share.txt")
    if not os.path.lexists(path):
        return None
    try:
        text = read(path)
    except OSError as exc:
        raise Refused("bin/never-share.txt is there but cannot be read (%s), so nothing is pushed"
                      % (exc.strerror or exc))
    words = [w.strip() for w in text.split("\n") if w.strip() and not w.lstrip().startswith("#")]
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
    """Every note and file of the vault that a bed could get, and how a [[link]] resolves.
    Symlinks are never followed: they are left out and listed in `links`."""

    def __init__(self):
        self.notes, self.files, self.links = [], [], []
        for root, dirs, names in os.walk(VAULT):
            here = os.path.relpath(root, VAULT).replace(os.sep, "/")
            for n in sorted(dirs + names):
                if not n.startswith(".") and os.path.islink(os.path.join(root, n)):
                    self.links.append(posixpath.normpath(posixpath.join(here, n)))
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (here == "." and d == "bin")
                             and not os.path.islink(os.path.join(root, d)))
            for fn in sorted(names):
                if not fn.startswith(".") and not os.path.islink(os.path.join(root, fn)):
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


def goes(bed, tags, cats, p):
    """Whether the note at p, with these `beds` names and these topics, goes to this bed."""
    topics = {str(t).lower() for t in bed.get("topics") or []}
    page = p.split("/")[0] == "Categories" and posixpath.basename(p)[:-3].lower() in topics
    return bed["name"].lower() in {t.lower() for t in tags} or bool(topics & {c.lower() for c in cats}) or page


def chosen(brain, bed):
    """(notes, topic pages, files) this bed gets."""
    notes = []
    for p in brain.notes:
        if "/" not in p or p.split("/")[0] in NEVER:
            continue
        fm = brain.fm[p]
        if goes(bed, find.values(fm.get("beds", "")), find.values(fm.get("categories", "")), p):
            notes.append(p)
    pages = {posixpath.basename(p)[:-3].lower() for p in notes if p.startswith("Categories/")}
    files = set()
    for p in notes:
        found = []
        walk_body(split(brain.text[p])[1], lambda s: found.extend(WIKI.findall(s)) or s)
        for bang, inner in found:
            target = inner.split("|")[0].split("#")[0]
            path = brain.resolve(target) if bang and target.strip() else None
            if path and not path.endswith((".md", ".base")) and "/" in path and path.split("/")[0] not in (
                    "Daily", "People", "Templates"):
                files.add(path)
    return notes, pages, sorted(files)


def link_target(here, href):
    """The vault path a Markdown link points at, or None for a web link or an anchor."""
    href = href.strip("<>")
    if "://" in href or href.startswith(("#", "mailto:", "tel:")):
        return None
    path = unquote(href.split("#")[0])
    return posixpath.normpath(path.lstrip("/") if path.startswith("/") else posixpath.join(here or ".", path))


def render_text(brain, text, here, inbed):
    """Text as the bed gets it: links into the bed relative Markdown links, every other link its text."""
    def markdown(m):
        target = link_target(here, m.group(3))
        return m.group(0) if target is None or target in inbed else m.group(2)

    def wiki(m):
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
    return WIKI.sub(wiki, MDLINK.sub(markdown, text))


def unrender_text(brain, text, here):
    """Text from the bed, its relative Markdown links back as [[links]]."""
    def swap(m):
        bang, label, href = m.group(1), m.group(2), m.group(3).strip("<>")
        target = link_target(here, href)
        if target is None or target == ".." or target.startswith("../"):
            return m.group(0)
        heading = href.partition("#")[2]
        known = brain.resolve(target)
        name = brain.wikiname(known) if known else posixpath.basename(target)
        name = name[:-3] if name.endswith(".md") else name
        ref = name + ("#" + unquote(heading) if heading else "")
        if bang:
            return "![[%s%s]]" % (ref, "|" + label if label else "")
        return "[[%s]]" % ref if label == posixpath.basename(name) else "[[%s|%s]]" % (ref, label)
    return MDLINK.sub(swap, text)


def chunk_out(brain, chunk, here, inbed):
    return "\n".join(render_text(brain, ln, here, inbed) for ln in chunk.split("\n"))


def chunk_back(brain, chunk, here):
    return "\n".join(unrender_text(brain, ln, here) for ln in chunk.split("\n"))


def render(brain, p, inbed, pages, strip):
    """The note as the bed gets it, without the topic list."""
    here = posixpath.dirname(p)
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
            else:
                chunk = chunk_out(brain, chunk, here, inbed)
            kept.append((key, chunk))
        groups = kept
    lines, _ = walk_body(body, lambda s: render_text(brain, s, here, inbed))
    return join(groups, "\n".join(lines))


def merge_back(brain, p, bed_text, inbed, pages, strip, beds):
    """(the brain's note with the bed's edits in, what was held back). Changed lines come from the
    bed, unchanged ones stay as they were; the text is None when the bed changed a line that holds a
    %% comment in the brain. Pull never changes which beds a note goes to: a `beds` property from
    the bed, a topic that is not one of this bed's, and a change of topics that would move the note
    into or out of any bed are held back."""
    here = posixpath.dirname(p)
    kept_back = []
    tags = find.values(brain.fm[p].get("beds", ""))

    def bound_for(cats):
        return {b["name"] for b in beds if goes(b, tags, cats, p)}

    def topics_back(chunk, came_chunk):
        names = topics_of(chunk) if chunk is not None else []
        sent = [n for n in names if n.lower() in pages]
        came = topics_of(came_chunk)
        kept_back.extend("topic [[%s]] is not one of this bed's; not applied (add it in the brain if it "
                         "belongs)" % n for n in came if n.lower() not in pages)
        came = [n for n in came if n.lower() in pages]
        merged = came + [n for n in names if n.lower() not in pages]
        if [n.lower() for n in came] == [n.lower() for n in sent]:
            return chunk
        if bound_for(merged) != bound_for(names):
            kept_back.append("its topics changed in the bed in a way that would move it into or out of a "
                             "bed; not applied")
            return chunk
        return categories_chunk(merged)

    b_groups, b_body = split(brain.text[p])
    t_groups, t_body = split(drop_list(bed_text))
    mine = b_body.rstrip("\n").split("\n")
    shown, held = walk_body(b_body.rstrip("\n"), lambda s: render_text(brain, s, here, inbed))
    raw = t_body.rstrip("\n").split("\n")
    back, _ = walk_body(t_body.rstrip("\n"), lambda s: unrender_text(brain, s, here), comments=False)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, shown, raw, autojunk=False).get_opcodes():
        if tag == "equal":
            out += mine[i1:i2]
            continue
        if any(held[k] and shown[k].strip() for k in range(i1, i2)):
            return None, kept_back
        out += [mine[k] for k in range(i1, i2) if held[k]] + back[j1:j2]
    body = "\n".join(out) + (b_body[len(b_body.rstrip("\n")):] or "\n")
    if b_groups is None and t_groups is None:
        return body, kept_back
    theirs = {k: c for k, c in t_groups or [] if k is not None}
    if "beds" in theirs:  # push always strips it, so this one was added in the bed
        kept_back.append("a `beds` property came from the bed; dropped")
    groups, seen = [], set()
    for key, chunk in b_groups or []:
        seen.add(key)
        if key is None or key in strip or key not in theirs:
            groups.append((key, chunk))  # stripped on the way out, or simply not in the bed's copy
        elif key == "categories":
            groups.append((key, topics_back(chunk, theirs[key])))
        elif theirs[key] == chunk_out(brain, chunk, here, inbed):
            groups.append((key, chunk))
        else:
            groups.append((key, chunk_back(brain, theirs[key], here)))
    for key, chunk in t_groups or []:
        if key is None or key in seen or key == "beds":
            continue
        chunk = topics_back(None, chunk) if key == "categories" else chunk_back(brain, chunk, here)
        if chunk is not None:
            groups.append((key, chunk))
    return join(groups, body), kept_back


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


def save_state(name, data, old):
    """Write the sync state when more than its date changed, and commit it when the brain is a repo."""
    if {k: v for k, v in data.items() if k != "synced"} == {k: v for k, v in old.items() if k != "synced"}:
        return
    path = state_file(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    rel = ".paths/beds/%s.json" % name
    if not git(VAULT, "rev-parse", "--git-dir")[0]:
        return
    git(VAULT, "add", "--", rel)
    if git(VAULT, "diff", "--cached", "--quiet", "--", rel)[0]:
        return
    ok, _, err = git(VAULT, "commit", "-q", "-m", "beds: %s sync state" % name, "--", rel)
    if not ok:
        say(name, "saved %s, but could not commit it in the brain: %s" % (rel, err.split("\n")[0]))


def has_upstream(home):
    return git(home, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")[0]


def count(home, span):
    ok, out, _ = git(home, "rev-list", "--count", span)
    return int(out.strip()) if ok else None


def catch_up(home):
    """Bring the remote's commits into the bed checkout. '' when done, else why not."""
    if git(home, "merge", "--ff-only", "-q", "@{u}")[0]:
        return ""
    ok, _, err = git(home, "merge", "-q", "--no-edit", "@{u}")
    if ok:
        return ""
    git(home, "merge", "--abort")
    return err.split("\n")[0] or "the bed and its remote have both moved; settle it in the bed with git"


def no_links(bed):
    """Refuse, naming each, while the bed holds a symlink. True when it holds none."""
    links = links_under(where(bed))
    for rel in links:
        say(bed["name"], "REFUSED  %s in the bed is a symlink; push and pull never follow one. Replace it "
                         "there with the real file, or remove it" % rel)
    return not links


def scaffolding(conf, name, strip):
    """The files that keep a bed a working vault, as {bed path: text}. Read from the brain without
    following a symlink."""
    out = {"CLAUDE.md": BED_CLAUDE.format(name=name, start=START, end=END), ".gitignore": BED_IGNORE,
           ".bed.json": json.dumps({"bed": name}) + "\n"}
    for rel in ("Rules.md", "bin/lint.py", "bin/find.py"):
        if safe(VAULT, rel) and os.path.isfile(os.path.join(VAULT, *rel.split("/"))):
            out[rel] = read(os.path.join(VAULT, *rel.split("/")))
    kinds = conf.get("kinds", {})
    bed_conf = {k: v for k, v in conf.items() if k != "beds"}
    bed_conf["kinds"] = {k: v for k, v in kinds.items() if k not in NO_KIND}
    out["bin/vault.json"] = json.dumps(bed_conf, indent=2) + "\n"
    skip = {"Templates/" + kinds[k].get("template", "") for k in NO_KIND if k in kinds}
    skip |= {"Templates/Bases/%s.base" % k for k in NO_KIND}
    base = os.path.join(VAULT, "Templates")
    for root, dirs, files in os.walk(base) if safe(VAULT, "Templates") else []:
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not os.path.islink(os.path.join(root, d)))
        for fn in sorted(files):
            rel = "Templates/" + os.path.relpath(os.path.join(root, fn), base).replace(os.sep, "/")
            if fn.startswith(".") or rel in skip or not safe(VAULT, rel):
                continue
            text = read(os.path.join(root, fn))
            if fn.endswith(".md"):
                groups, body = split(text)
                text = join(None if groups is None else [(k, c) for k, c in groups if k not in strip], body)
            out[rel] = text
    for rel in OBSIDIAN:
        if safe(VAULT, ".obsidian/" + rel) and os.path.isfile(os.path.join(VAULT, ".obsidian", *rel.split("/"))):
            out[".obsidian/" + rel] = read(os.path.join(VAULT, ".obsidian", *rel.split("/")))
    return out


def survey(bed, state, fetch):
    """What changed in the bed since the last sync, fetching first when asked and it has a remote.
    Call it only on a bed with no symlink."""
    home = where(bed)
    s = dict(changed=[], deleted=[], folders=[], renamed=[], new=[], commits=0, ahead=0, fetch="")
    synced = state.get("notes", {})
    for p in sorted(synced):
        path = os.path.join(home, *p.split("/"))
        if not os.path.lexists(path):
            s["deleted"].append(p)
        elif not os.path.isfile(path):
            s["folders"].append(p)
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
        if fetch:
            ok, _, err = git(home, "fetch", "-q")
            s["fetch"] = "" if ok else err.split("\n")[0]
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
    why += ["%s is a folder in the bed, not a note" % p for p in s["folders"]]
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


def differs(home, rel, data):
    path = os.path.join(home, *rel.split("/"))
    if not os.path.isfile(path):
        return True
    with open(path, "rb") as fh:
        return fh.read() != (data if isinstance(data, bytes) else data.encode("utf-8"))


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
    print("  last sync: %s%s" % ("%s, bed commit %s" % (state.get("synced"), state.get("commit", "")[:7])
                                 if state else "never", "; its push to the remote is still pending"
                                 if state.get("remote_pending") else ""))
    if not no_links(bed):
        return True
    gone = [p for p in list(state.get("notes", {})) + list(state.get("files", [])) if p not in out]
    print("  push would write %d and remove %d" % (len([p for p in out if differs(home, p, out[p])]), len(gone)))
    s = survey(bed, state, fetch=True)
    print("  in the bed since then: %d changed, %d deleted, %d renamed, %d new, %s commit(s)%s"
          % (len(s["changed"]), len(s["deleted"]), len(s["renamed"]), len(s["new"]),
             "?" if s["commits"] is None else s["commits"],
             ", %d more on the remote" % s["ahead"] if s["ahead"] else ""))
    return True


def clear(name, home, paths):
    """Refuse, naming each, while something in the bed stands where push must write a file (a
    folder where a note goes, say), even with --force. True when nothing does."""
    stuck = [p for p in paths if in_the_way(home, p)]
    for p in stuck:
        say(name, "REFUSED  %s: a folder stands where this file goes in the bed (or a file where its "
                  "folder goes). Remove it there; push never deletes a folder" % p)
    return not stuck


def never_shared(brain, conf, bed, words):
    """Print one refusal per file this bed would get that holds a never-share word in its path or,
    for a note, its properties or text. True when none does."""
    _, _, _, _, out, scaffold = plan(brain, conf, bed)
    hits = [(p, never_hit(words, p) or (never_hit(words, t) if p.endswith(".md") else None))
            for p, t in sorted(list(out.items()) + list(scaffold.items()))]
    for p, w in hits:
        if w:
            say(bed["name"], "REFUSED  %s holds \"%s\", a word in bin/never-share.txt" % (p, w))
    return not any(w for _, w in hits)


def push(brain, conf, bed, dry, force):
    name, home = bed["name"], where(bed)
    notes, files, _, strip, out, scaffold = plan(brain, conf, bed)
    state = load_state(name)
    if not os.path.isdir(home):
        if dry:
            say(name, "would make the bed at %s%s" % (bed["path"], " from %s" % bed["remote"]
                                                      if bed.get("remote") else ""))
            for p in sorted(out):
                print("  + %s" % p)
            say(name, "dry run: would send %s and %s, and keep the bed a vault; wrote nothing"
                % (plural(len(notes), "note"), plural(len(files), "file")))
            return True
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
    if not os.path.exists(os.path.join(home, ".git")):
        say(name, "REFUSED  %s exists but is not a git repository" % bed["path"])
        return False
    if not no_links(bed):
        return False
    if not state and not force:
        ok, listed, _ = git(home, "ls-files", "-z", "-co", "--exclude-standard")
        other = [p for p in listed.split("\0") if p and p not in ("README.md", "LICENSE", ".gitignore",
                                                                    ".gitattributes")]
        if other or git(home, "rev-parse", "-q", "--verify", "HEAD")[0]:
            say(name, "REFUSED  %s already has commits or files, and this brain has no sync state for it "
                      "(.paths/beds/%s.json), so it cannot tell what was changed there. If the state was "
                      "lost, restore it from the brain's git history; to replace the bed's notes with the "
                      "brain's anyway (its history keeps the rest), push --force" % (bed["path"], name))
            return False
    s = survey(bed, state, fetch=not dry)
    if s["fetch"]:
        say(name, "could not reach the remote: %s" % s["fetch"])
    why = pending(s, notes)
    if why and not force:
        say(name, "REFUSED  the bed has changes not yet pulled: %s. Run `python3 bin/beds.py pull %s` first, "
                  "or push --force to overwrite them" % ("; ".join(why), name))
        return False
    gone = [p for p in list(state.get("notes", {})) + list(state.get("files", [])) if p not in out]
    written = sorted(list(out) + list(scaffold) + [".paths/index.txt"])
    if dry:
        if not clear(name, home, written):
            return False
        for p in sorted(out):
            if differs(home, p, out[p]):
                print("  %s %s" % ("~" if os.path.exists(os.path.join(home, *p.split("/"))) else "+", p))
        for p in sorted(gone):
            print("  - %s" % p)
        say(name, "dry run: would send %s and %s, remove %d, and keep the bed a vault; wrote nothing%s"
            % (plural(len(notes), "note"), plural(len(files), "file"), len(gone),
               " (the remote was not fetched)" if bed.get("remote") else ""))
        return True
    if s["ahead"]:
        why = catch_up(home)
        if why:
            say(name, "could not bring in the remote's commits first: %s" % why)
            return False
        if not no_links(bed):
            return False
    if not clear(name, home, written):
        return False
    try:
        for p, data in sorted(list(out.items()) + list(scaffold.items())):
            put(home, p, data)
        for p in gone:
            path = os.path.join(home, *p.split("/"))
            if safe(home, p) and os.path.isfile(path):
                os.remove(path)
        put(home, ".paths/index.txt", find.build(home))  # this vault's own find.py, pointed at the bed
    except Refused as exc:
        say(name, "REFUSED  %s" % exc)
        return False
    extra = sorted(f for f in os.listdir(os.path.join(home, "bin")) if f not in BED_BIN and f != "__pycache__")
    for f in extra:
        say(name, "bin/%s in the bed did not come from the brain. Nothing in a bed is ever run by this "
                  "script, but the bed's own lint would load it: remove it there" % f)
    git(home, "add", "-A")
    staged = not git(home, "diff", "--cached", "--quiet")[0]
    if staged:
        ok, _, err = git(home, "commit", "-q", "-m", "Push from the brain: %s, %s"
                         % (plural(len(notes), "note"), plural(len(files), "file")))
        if not ok:
            say(name, "could not commit in the bed: %s" % err)
            return False
    sent = True
    if bed.get("remote"):
        if not git(home, "remote", "get-url", "origin")[0]:  # a bed that was made before it had a remote
            git(home, "remote", "add", "origin", bed["remote"])
        sent, _, err = git(home, "push", "-q", "-u", "origin", "HEAD")
    head = git(home, "rev-parse", "HEAD")[1].strip()
    save_state(name, {"bed": name, "commit": head, "synced": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "notes": {p: {"brain": digest(os.path.join(VAULT, *p.split("/"))),
                                    "bed": digest(os.path.join(home, *p.split("/")))} for p in notes},
                      "files": files, "strip": sorted(strip), "remote_pending": not sent}, state)
    if not sent:
        say(name, "committed in the bed, but could not push to its remote (%s). The sync state is saved; "
                  "the next push sends it" % err.split("\n")[0])
        return False
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
    if not no_links(bed):
        return False
    s = survey(bed, state, fetch=not dry)
    if s["fetch"]:
        say(name, "could not reach the remote: %s" % s["fetch"])
    if dry and bed.get("remote"):
        say(name, "dry run: the remote was not fetched; a pull without --dry-run brings its commits in first")
    elif s["ahead"]:
        why = catch_up(home)
        if why:
            say(name, "could not bring in the remote's commits: %s" % why)
            return False
        if not no_links(bed):
            return False
        s = survey(bed, state, fetch=False)
    # Render the brain's side as it was sent at the last sync, so untouched lines match.
    inbed = set(state.get("notes", {})) | set(state.get("files", []))
    pages = {posixpath.basename(p)[:-3].lower() for p in state.get("notes", {}) if p.startswith("Categories/")}
    strip = set(state.get("strip") or [str(k) for k in bed.get("strip") or []]) | {"beds"}
    pulled, conflicts, kept_back = [], 0, 0
    for p in s["folders"]:
        say(name, "CONFLICT  %s is a folder in the bed, not a note; applied to neither. Remove the folder "
                  "there (or move what is in it), then pull again" % p)
        conflicts += 1
    for p in s["changed"]:
        mine = os.path.join(VAULT, *p.split("/"))
        if p not in brain.text or not safe(VAULT, p):
            say(name, "CONFLICT  %s changed in the bed but is gone from the brain (or is a symlink there); "
                      "applied to neither" % p)
            conflicts += 1
            continue
        if digest(mine) != state["notes"][p]["brain"]:
            say(name, "CONFLICT  %s changed in the brain and in the bed since the last sync; applied to "
                      "neither. Merge the bed's version in by hand, then push --force" % p)
            conflicts += 1
            continue
        text, held = merge_back(brain, p, read(os.path.join(home, *p.split("/"))), inbed, pages, strip,
                                conf.get("beds") or [])
        if text is None:
            say(name, "CONFLICT  %s: the bed changed a line that holds a %%%% comment in the brain; applied "
                      "to neither. Merge the bed's version in by hand, then push --force" % p)
            conflicts += 1
            continue
        if not dry:
            put(VAULT, p, text)
            state["notes"][p] = {"brain": sha(text), "bed": digest(os.path.join(home, *p.split("/")))}
        pulled.append(p)
        say(name, "%s  %s%s" % ("WOULD PULL" if dry else "PULLED", p, ", all but what is held back below"
                                if held else ""))
        for h in held:
            say(name, "HELD BACK  %s: %s" % (p, h))
        kept_back += len(held)
    for p in s["deleted"]:
        say(name, "DELETED  %s was deleted in the bed; not applied. Take it out of the bed in the brain "
                  "(its `beds` or its topic), or push --force to put it back" % p)
    for a, b in s["renamed"]:
        say(name, "RENAMED  %s became %s in the bed; not applied. Rename it in the brain the same way, "
                  "then push" % (a, b))
    for p in s["new"]:
        say(name, "NEW  %s is new in the bed; not applied. Copy it into the brain if you want it" % p)
    if not dry:
        old = load_state(name)
        state["commit"] = git(home, "rev-parse", "HEAD")[1].strip() or state.get("commit", "")
        state["synced"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_state(name, state, old)
        if pulled:
            find.rebuild(VAULT)
    say(name, "%s %d; reported, not applied: conflicts %d, held back %d, deleted %d, renamed %d, new %d%s" % (
        "would pull" if dry else "pulled", len(pulled), conflicts, kept_back, len(s["deleted"]),
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


def lint_errors(dry):
    """The brain's lint errors, from its own bin/lint.py run here. A dry run keeps it from rewriting
    the index."""
    import lint  # noqa: E402  (bin/ is on sys.path; reads bin/vault.json when imported)
    rebuild = find.rebuild
    if dry:
        find.rebuild = lambda vault=VAULT: False
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = lint.main()
    finally:
        find.rebuild = rebuild
    return ["ERROR  %s" % e for e in lint.errors] if code else []


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
    tangled = [b["name"] for b in beds if within(where(b), VAULT) or within(VAULT, where(b))]
    if tangled:
        print("beds: REFUSED  a bed's `path` must be a folder of its own next to this vault: not the vault, "
              "not inside it, not one that holds it. Change `path` in bin/vault.json for: %s" % ", ".join(tangled))
        return 1
    if args.bed:
        beds = [b for b in beds if b["name"] == args.bed]
        if not beds:
            print("beds: no bed named %r (configured: %s)" % (args.bed, ", ".join(b["name"] for b in conf["beds"])))
            return 1
    if args.command == "clone":
        return 0 if all([clone(b) for b in beds]) else 1
    brain = Brain()
    for rel in brain.links:
        print("beds: skipped %s in the brain: a symlink, never followed" % rel)
    if args.command == "status":
        for b in beds:
            status(brain, conf, b)
        return 0
    if args.command == "pull":
        return 0 if all([pull(brain, conf, b, args.dry_run) for b in beds]) else 1
    errors = lint_errors(args.dry_run)
    if errors:
        print("beds: REFUSED  lint has errors; fix them first (python3 bin/lint.py):")
        for e in errors:
            print("  %s" % e)
        return 1
    try:
        words = never_words()
    except Refused as exc:
        print("beds: REFUSED  %s" % exc)
        return 1
    if not all([never_shared(brain, conf, b, words) for b in beds]):
        print("beds: REFUSED  nothing was pushed; take the word out of each file named, or keep it home")
        return 1
    return 0 if all([push(brain, conf, b, args.dry_run, args.force) for b in beds]) else 1


if __name__ == "__main__":
    sys.exit(main())
