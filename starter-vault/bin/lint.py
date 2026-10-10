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
  - a Now.md bullet with no date, or one older than now_max_days

The schema is the templates: Templates/<Kind> Template.md says which properties a
kind carries, so a template edit is a schema edit. bin/vault.json maps each kind
folder to its template and, where it has one, its status vocabulary.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(VAULT, "bin", "vault.json"), encoding="utf-8"))
KINDS = CONFIG["kinds"]
SKIP = {".git", ".obsidian", ".trash", ".claude", "bin", "node_modules", "__pycache__"}
LINK = re.compile(r"\[\[([^\]|#]+)")
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DASHES = ("–", "—")

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

    for topic in sorted(topics - used):
        warnings.append("Categories/%s.md: no note uses this topic" % topic)

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

    for w in warnings:
        print("warn   %s" % w)
    for e in errors:
        print("ERROR  %s" % e, file=sys.stderr)
    print("lint: %d notes, %d errors, %d warnings" % (len(notes), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
