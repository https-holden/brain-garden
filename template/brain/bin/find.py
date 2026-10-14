#!/usr/bin/env python3
"""Find notes through the vault's index. Step 1 of the one recipe in CLAUDE.md. Standard library only.

    python3 bin/find.py <words>             the notes whose index line has every word
    python3 bin/find.py <words> --stale     the same, with stale notes too
    python3 bin/find.py --topic <Topic>     the notes in one topic (add words to narrow it)
    python3 bin/find.py --all               the whole index: paste it into a chat AI, or save
                                            it as a file in a ChatGPT project
    python3 bin/find.py --rebuild           rebuild the index and print nothing else

The index is .paths/index.txt, committed with the notes so its history is a
readable diff of what the vault knows. One line per note in every kind folder of
bin/vault.json and in Categories/ (never Daily/, Templates/, Attachments/, the
root files or a dot folder), sorted by folder then title, ignoring case:

    Folder/title :: aliases :: categories :: status

Lists are joined with ", " and [[link]] brackets are dropped. An empty field
stays an empty slot, so every line has exactly four fields.

The index rebuilds itself before every query when it is missing, older than the
newest note it covers, or lists a different set of notes. lint.py compares its
content instead (a clone or a pull resets file times) and rewrites it when it
differs. ingest.py and librarian.py rebuild it after writing. Never edit it by
hand.

Matching ignores case. Every word must appear somewhere on a note's line, so
words match the folder, the title, an alias, a topic or the status. Notes with
`status: stale` are left out unless --stale. --topic matches a whole topic name.

The find log, .paths/find.log, stays on this machine (git-ignored). Every word
or --topic query appends one line; --all is a dump, not a lookup, and is not
logged. Fields are separated by a tab:

    YYYY-MM-DD HH:MM:SS <TAB> query <TAB> hits <TAB> path <TAB> path ...

The query is the words as given, then `--topic <Topic>` and `--stale` when
used. Hits is the number of notes printed, and each path is one of them,
vault-relative with `.md` (Notes/Sleep.md). A line with 0 hits and no path is a
miss: a fork in the garden where the signage is missing.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import unicodedata

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEVER = {"Daily", "Templates", "Attachments"}
LINK = re.compile(r"\[\[([^\]|#]*)[^\]]*\]\]")


def index_path(vault: str) -> str:
    return os.path.join(vault, ".paths", "index.txt")


def folders(vault: str) -> list[str]:
    """The folders the index covers: every kind in bin/vault.json, and Categories/."""
    with open(os.path.join(vault, "bin", "vault.json"), encoding="utf-8") as fh:
        kinds = list(json.load(fh).get("kinds", {}))
    return [f for f in dict.fromkeys(kinds + ["Categories"]) if f not in NEVER and not f.startswith(".")]


def notes(vault: str) -> dict[str, str]:
    """Index path (vault-relative, no .md) -> the note's file, for every note the index covers."""
    out = {}
    for folder in folders(vault):
        for root, dirs, files in os.walk(os.path.join(vault, folder)):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if fn.endswith(".md") and not fn.startswith("."):
                    path = os.path.join(root, fn)
                    rel = os.path.relpath(path, vault)[:-3].replace(os.sep, "/")
                    out[unicodedata.normalize("NFC", rel)] = path
    return out


def frontmatter(text: str) -> dict[str, str]:
    """Top-level key -> raw value text. Naive YAML, enough for a vault (the same reading as lint.py)."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return {}
    end = text.index("\n---", 3)
    fm, key = {}, None
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.strip():
            fm[key] += "\n" + line
    return fm


def plain(value: str) -> str:
    """One value as the index shows it: unquoted, [[Sleep|sleep]] as Sleep, on one line."""
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    value = LINK.sub(lambda m: m.group(1).strip(), value)
    return " ".join(value.replace("::", ":").split())


def values(raw: str) -> list[str]:
    """A property as a list of plain values: a block list, a [flow, list] or one value."""
    if "\n" in raw:
        return [v for v in (plain(ln.strip()[1:]) for ln in raw.split("\n") if ln.strip().startswith("-")) if v]
    raw = raw.strip()
    if raw in ("", "~", "null", "[]"):
        return []
    if raw.startswith("[") and raw.endswith("]") and not raw.startswith("[["):
        items = next(csv.reader([raw[1:-1]], skipinitialspace=True), [])
    else:
        items = [raw]
    return [v for v in (plain(i) for i in items) if v]


def line(path: str, text: str) -> str:
    fm = frontmatter(text)
    fields = [", ".join(values(fm.get(key, ""))) for key in ("aliases", "categories", "status")]
    return path + "".join(" ::" + (" " + f if f else "") for f in fields)


def build(vault: str = VAULT) -> str:
    """The index as it should be now."""
    lines = []
    for path, src in notes(vault).items():
        with open(src, encoding="utf-8", errors="replace") as fh:
            lines.append(line(path, fh.read()))
    lines.sort(key=lambda ln: (ln.split("/", 1)[0].lower(), ln.split("/", 1)[-1].lower(), ln))
    return "".join(ln + "\n" for ln in lines)


def rebuild(vault: str = VAULT) -> bool:
    """Write the index if its content is not what the notes say. True when it was rewritten."""
    path = index_path(vault)
    text = build(vault)
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as fh:
            if fh.read() == text:
                os.utime(path, None)  # current, so the next query need not rebuild it
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(path + ".tmp", path)
    return True


def current(vault: str = VAULT) -> list[str]:
    """The index lines, rebuilt first if it is missing, older than a note, or lists other notes."""
    path = index_path(vault)
    have = notes(vault)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().split("\n") if ln]
        newest = max((os.path.getmtime(p) for p in have.values()), default=0)
        listed = {ln.split(" ::", 1)[0] for ln in lines}
        if os.path.getmtime(path) >= newest and listed == set(have):
            return lines
    rebuild(vault)
    with open(path, encoding="utf-8") as fh:
        return [ln for ln in fh.read().split("\n") if ln]


def fields(ln: str) -> list[str]:
    return [f.strip() for f in ln.split("::")]


def search(lines: list[str], words: list[str], topic: str, stale: bool) -> list[str]:
    words = [w.lower() for w in words]
    topic = plain(topic).lower()
    out = []
    for ln in lines:
        _, _, cats, status = (fields(ln) + ["", "", ""])[:4]
        if status.lower() == "stale" and not stale:
            continue
        if topic and topic not in [c.strip().lower() for c in cats.split(",")]:
            continue
        if all(w in ln.lower() for w in words):
            out.append(ln)
    return out


def log(vault: str, query: str, hits: list[str]) -> None:
    os.makedirs(os.path.join(vault, ".paths"), exist_ok=True)
    row = [dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), " ".join(query.split()), str(len(hits))]
    row += [fields(ln)[0] + ".md" for ln in hits]
    with open(os.path.join(vault, ".paths", "find.log"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(row) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*", help="words from the question; every one must match")
    ap.add_argument("--stale", action="store_true", help="include notes with status: stale")
    ap.add_argument("--topic", default="", help="only the notes in this topic (its exact name)")
    ap.add_argument("--all", action="store_true", help="print the whole index")
    ap.add_argument("--rebuild", action="store_true", help="rebuild the index, query nothing")
    args = ap.parse_args()

    if args.rebuild:
        rebuild()
        return 0
    lines = current()
    if args.all:
        sys.stdout.write("".join(ln + "\n" for ln in lines))
        return 0
    words = " ".join(args.words).split()
    if not words and not args.topic:
        ap.error("give words to look for, --topic <Topic>, or --all")
    hits = search(lines, words, args.topic, args.stale)
    query = " ".join(words + (["--topic", args.topic] if args.topic else []) + (["--stale"] if args.stale else []))
    log(VAULT, query, hits)
    for ln in hits:
        print(ln)
    if not hits:
        print("find: no note matches %r (logged as a miss). Next: step 2 of the recipe in CLAUDE.md."
              % query, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
