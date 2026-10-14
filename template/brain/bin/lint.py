#!/usr/bin/env python3
"""Deterministic drift check for this vault. Standard library only.

    python3 bin/lint.py

Errors (exit 1):
  - a note in a kind folder is missing a property its template carries
  - a `status` value outside the kind's list in bin/vault.json
  - an en or em dash in any note or filename
  - an unresolved [[link]] on a page in Categories/
  - a `categories` link with no page in Categories/
Warnings (exit 0):
  - a draft older than draft_max_days
  - a Categories/ page that no note uses
  - a hub with no signs: a Categories/ page whose topic three or more notes use
    and that has no plain [[link]] (an embed does not count), or Home.md, once
    there are three topic pages, with no topic page linked under `## Start here`
  - a Now.md bullet with no date, or one older than now_max_days
  - an action log line (a bullet under `## Actions`) that does not start with
    `YYYY-MM-DD HH:MM` or is missing `Why:` or `Asked by:`
  - a file a session loads without asking (CLAUDE.md, Me.md, Now.md, each
    .claude/skills/*/SKILL.md) or Rules.md over its budget, in characters, under
    `budgets` in bin/vault.json. `SKILL.md` there is every skill's budget; a
    vault-relative path such as `.claude/skills/pdf/SKILL.md` overrides it for
    that file only. A file that does not exist is skipped.
Fixed, never an error:
  - .paths/index.txt (the index bin/find.py reads) is rebuilt and rewritten when
    its content is not what the notes say, with one line saying so. Content, not
    file times, because a clone or a pull resets those.

The schema is the templates: Templates/<Kind> Template.md says which properties a
kind carries, so a template edit is a schema edit. bin/vault.json maps each kind
folder to its template and, where it has one, its status vocabulary, and holds
the budgets.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find  # noqa: E402

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(VAULT, "bin", "vault.json"), encoding="utf-8"))
KINDS = CONFIG["kinds"]
SKIP = {".git", ".obsidian", ".trash", ".claude", ".paths", "bin", "node_modules", "__pycache__"}
LINK = re.compile(r"\[\[([^\]|#]+)")
PLAIN = re.compile(r"(?<!!)\[\[([^\]|#]+)")  # a link, not an embed
BUSY = 3  # notes on a topic, or topic pages in the vault, before its hub needs a sign
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ACTION = re.compile(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} \S")
DASHES = ("–", "—")
# The one place the over-budget warning is worded.
OVER_BUDGET = "{file}: {size:,} chars, over its budget of {budget:,}: have the AI compact it to about {target:,} (75%)"

errors, warnings = [], []


def frontmatter(text):
    """(dict of top-level key -> raw value text, body). Naive YAML, enough for a vault."""
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return {}, text
    end = text.index("\n---", 3)
    fm, key = {}, None
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.strip():
            fm[key] += "\n" + line
    return fm, text[end + 4:]


def walk():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for fn in sorted(files):
            if fn.endswith(".md"):
                path = os.path.join(root, fn)
                yield os.path.relpath(path, VAULT), open(path, encoding="utf-8").read()


def exempt(rel):
    return any(rel.startswith(p) for p in CONFIG.get("dash_exempt", []))


def over_budget():
    """One warning per budgeted file that is over its budget in bin/vault.json."""
    table = {}
    for rel, n in (CONFIG.get("budgets") or {}).items():
        try:
            table[os.path.normpath(rel.replace("\\", "/")).replace(os.sep, "/")] = int(n)
        except (TypeError, ValueError):
            pass  # a hand-edited budget that is not a number is ignored, never an error
    limits = {rel: n for rel, n in table.items() if rel != "SKILL.md"}
    skills = os.path.join(VAULT, ".claude", "skills")
    if "SKILL.md" in table and os.path.isdir(skills):
        for name in sorted(os.listdir(skills)):
            limits.setdefault(".claude/skills/%s/SKILL.md" % name, table["SKILL.md"])
    out = []
    for rel, budget in sorted(limits.items()):
        path = os.path.join(VAULT, *rel.split("/"))
        if os.path.isfile(path):
            size = len(open(path, encoding="utf-8", errors="replace").read())
            if size > budget:
                out.append(OVER_BUDGET.format(file=rel, size=size, budget=budget, target=budget * 3 // 4))
    return out


def unsigned_hubs(notes):
    """A busy hub with no plain link: a topic page whose topic BUSY notes use, and
    Home once the vault has BUSY topic pages (its links to root documents do not count)."""
    pages = {os.path.splitext(os.path.basename(r))[0]: r for r in notes if r.startswith("Categories/")}
    count = {}
    for rel, (fm, _, _) in notes.items():
        if not rel.startswith("Templates/"):
            for topic in {t.strip() for t in LINK.findall(fm.get("categories", ""))}:
                count[topic] = count.get(topic, 0) + 1
    out = []
    for topic, rel in sorted(pages.items()):
        if count.get(topic, 0) >= BUSY and not PLAIN.search(notes[rel][1]):
            out.append("%s: %d notes use this topic and its page links none: put the best 3 to 7 under "
                       "## Start here" % (rel, count[topic]))
    if "Home.md" in notes and len(pages) >= BUSY:
        section = ("\n" + notes["Home.md"][1]).split("\n## Start here\n", 1)
        section = re.split(r"\n#{1,2} ", section[1], maxsplit=1)[0] if len(section) > 1 else ""
        names = {p.lower() for p in pages}
        if not any(os.path.basename(t.strip()).lower() in names for t in PLAIN.findall(section)):
            out.append("Home.md: %d topic pages and none linked under ## Start here: add the main ones "
                       "there as plain links" % len(pages))
    return out


def main():
    notes = {rel: frontmatter(text) + (text,) for rel, text in walk()}
    names = {os.path.splitext(os.path.basename(rel))[0].lower() for rel in notes}
    for rel, (fm, _, _) in notes.items():
        for alias in LINK.findall(fm.get("aliases", "")) + re.findall(r"-\s+(.+)", fm.get("aliases", "")):
            names.add(alias.strip().strip('"').lower())
    topics = {os.path.splitext(os.path.basename(r))[0] for r in notes if r.startswith("Categories/")}
    used = set()
    today = date.today()

    schema = {}
    for kind, spec in KINDS.items():
        path = os.path.join(VAULT, "Templates", spec["template"])
        if not os.path.exists(path):
            errors.append("bin/vault.json: %s names a template that does not exist: %s" % (kind, spec["template"]))
            continue
        schema[kind] = set(frontmatter(open(path, encoding="utf-8").read())[0])

    for rel, (fm, body, text) in notes.items():
        if not exempt(rel) and any(d in text or d in rel for d in DASHES):
            errors.append("%s: contains an en or em dash" % rel)
        folder = rel.split("/")[0]
        for topic in LINK.findall(fm.get("categories", "")):
            used.add(topic.strip())
            if topic.strip() not in topics:
                errors.append("%s: category [[%s]] has no page in Categories/" % (rel, topic.strip()))
        if folder == "Categories":
            for target in LINK.findall(body):
                if os.path.basename(target.strip()).lower().replace(".base", "") not in names and not target.strip().endswith(".base"):
                    errors.append("%s: unresolved link [[%s]]" % (rel, target.strip()))
        if folder not in schema or "/" not in rel:
            continue
        for key in sorted(schema[folder] - set(fm)):
            errors.append("%s: missing `%s` (the %s template carries it)" % (rel, key, folder))
        allowed = KINDS[folder].get("status")
        if allowed and "status" in fm and fm["status"] not in allowed:
            errors.append("%s: status %r is not one of %s" % (rel, fm["status"], allowed))
        if fm.get("status") == "draft" and DATE.match(fm.get("created", "")):
            age = (today - datetime.strptime(fm["created"][:10], "%Y-%m-%d").date()).days
            if age > CONFIG.get("draft_max_days", 14):
                warnings.append("%s: draft for %d days" % (rel, age))

    for rel, (_, body, _) in notes.items():
        section = ""
        for line in body.split("\n"):
            if line.startswith("#"):
                section = line.lstrip("#").strip()
            elif section == "Actions" and line.startswith("- "):
                if not ACTION.match(line):
                    warnings.append("%s: action log line does not start with YYYY-MM-DD HH:MM: %s" % (rel, line[2:50]))
                elif "Why:" not in line or "Asked by:" not in line:
                    warnings.append("%s: action log line is missing Why: or Asked by: %s" % (rel, line[2:50]))

    for topic in sorted(topics - used):
        warnings.append("Categories/%s.md: no note uses this topic" % topic)
    warnings.extend(unsigned_hubs(notes))

    if "Now.md" in notes:
        section = ""
        for line in notes["Now.md"][1].split("\n"):
            if line.startswith("## "):
                section = line[3:].strip()
            elif line.startswith("- ") and section in ("Active", "Waiting on", "Recently done"):
                found = DATE.findall(line)
                if not found:
                    warnings.append("Now.md: undated bullet under %s: %s" % (section, line[2:50]))
                elif (today - datetime.strptime(found[-1], "%Y-%m-%d").date()).days > CONFIG.get("now_max_days", 14):
                    warnings.append("Now.md: stale bullet under %s (%s): %s" % (section, found[-1], line[2:50]))

    warnings.extend(over_budget())

    if find.rebuild(VAULT):
        print("index  .paths/index.txt was out of date: rewrote it from the notes (commit it with them)")
    for w in warnings:
        print("warn   %s" % w)
    for e in errors:
        print("ERROR  %s" % e, file=sys.stderr)
    print("lint: %d notes, %d errors, %d warnings" % (len(notes), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
