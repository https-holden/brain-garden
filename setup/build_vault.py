#!/usr/bin/env python3
"""Build a second-brain Obsidian vault from template/. Standard library only.

    build_vault.py --preset personal --dest ~/Documents/Obsidian/sam-brain --name "Sam's Brain" --owner Sam
    build_vault.py --preset work     --dest ~/Documents/Obsidian/sam-work-brain --name "Sam's Work Brain" --owner Sam
    build_vault.py --kinds Notes,People,Clippings,Daily --working-memory --me --dest ... --name ...
    build_vault.py --self-update     pull this repo

Presets: `personal` (a life: your notes, references, people, clippings, days) and
`work` (a job: claims, procedures, people, meetings, clippings, days). Both get
Now.md, Me.md, Sources.md, the ingest tools and the daily loop. With neither
--preset nor --kinds, the personal preset is used. setup/mac.sh and
setup/windows.ps1 call this for you.

Rules it keeps:

- It never overwrites. A file that already exists is left alone and reported
  as "kept", so it is safe to rerun and to point at a half-built vault.
- It writes structure, never content. No note a person would have authored
  comes out of this script.
- --dry-run prints exactly what a real run would write and touches nothing.
- The vault's folder carries a name. Obsidian lists a vault by its folder name
  and nothing else, so a folder called `vault` or `brain` is refused.
"""
from __future__ import annotations

import argparse
import colorsys
import datetime
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # the repo
ASSETS = os.path.join(SKILL_DIR, "template")
TEXT_EXT = {".md", ".base", ".json", ".css", ".py", ".js", ".txt", ".canvas", ""}
KNOWN_PLUGINS = ["auto-alias", "home-button", "manual-modified", "response-cards", "resting-view",
                 "sticky-bullets"]

# Obsidian names a vault by the last segment of its path, and nothing else.
# A folder called `vault` is "vault" in the vault switcher, beside any other.
GENERIC_DIRS = {
    "vault", "brain", "notes", "obsidian", "second-brain", "knowledge", "kb", "wiki",
}


def slug(text):
    """"Sam's Brain" -> 'sam-s-brain': safe in a path and a shell command."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

# ------------------------------------------------------------ brain kinds
#
# One entry per kind of note the builder knows how to shape. A kind is
# a folder (what a note IS), a template (its schema) and a Base (its table).
# A name that is not here still works: it gets the generic shape.

DRAFTS = ["draft", "verified", "stale"]

KINDS = {
    "Knowledge": dict(
        singular="Knowledge note", template="Knowledge",
        holds="One claim per note, third person. The title is the claim. Default landing folder.",
        nots="Procedures, wishes, raw logs.",
        title="a claim you could say in a sentence, one idea per note",
        props=[("categories", "[]"), ("created", "{{date}}"), ("status", "draft"), ("source", "")],
        status=DRAFTS, views=[("Recent", None, 15), ("Drafts", "draft", None), ("Stale", "stale", None)],
        home="Recent", body="\n"),
    "Playbooks": dict(
        singular="Playbook", template="Playbook",
        holds="Procedures actually run: when to use, inputs, steps, outputs, the last run.",
        nots="Theory, one-off logs.",
        title="an imperative (\"Rotate the signing key\")",
        props=[("categories", "[]"), ("created", "{{date}}"), ("status", "draft"), ("source", "")],
        status=DRAFTS, views=[("Drafts", "draft", None)], home="All playbooks",
        body="## When to use\n\n## Inputs\n\n## Steps\n\n1. \n\n## Outputs\n\n## Gotchas\n\n## Last run\n\n"),
    "People": dict(
        singular="Person", template="Person",
        holds="One note per person: who they are, their role, one line.",
        nots="Private details, anything they would not want written down.",
        title="the person's name, never a role (qualify in parentheses when two share one)",
        props=[("categories", "[]"), ("created", "{{date}}"), ("org", "[]"), ("role", ""), ("source", "")],
        body="\n"),
    "Projects": dict(
        singular="Project", template="Project",
        holds="One hub note per project: what it is for, its state, links to everything about it.",
        nots="The project's own notes (they link here through `project` or `categories`).",
        title="the project's name",
        props=[("categories", "[]"), ("created", "{{date}}"), ("status", "active"), ("start", ""), ("end", "")],
        status=["active", "paused", "done"], views=[("Active", "active", None)], home="Active",
        body="\n"),
    "Meetings": dict(
        singular="Meeting", template="Meeting",
        holds="One note per meeting or call, written on the day.",
        nots="Facts that outlive the meeting (copy them out to a claim note and link back).",
        title="`YYYY-MM-DD Title`",
        props=[("categories", "[]"), ("created", "{{date}}"), ("date", "{{date}}"), ("people", "[]"), ("topics", "[]")],
        body="## Notes\n\n## Decisions\n\n## Follow-ups\n\n"),
    "References": dict(
        singular="Reference", template="Reference",
        holds="Things that exist outside your head: books, tools, places, organisations.",
        nots="Dated, authored writing.",
        title="the thing's own title, exactly",
        props=[("categories", "[]"), ("created", "{{date}}"), ("author", "[]"), ("url", ""), ("rating", "")],
        body="\n"),
    "Notes": dict(
        singular="Note", template="Note",
        holds="Anything authored that is not another kind: essays, evergreen ideas, working notes.",
        nots="Things other people wrote (those are clippings).",
        title="for an idea, the idea as a claim; otherwise a plain name",
        props=[("categories", "[]"), ("created", "{{date}}"), ("topics", "[]")],
        body="\n"),
    "Clippings": dict(
        singular="Clipping", template="Clipping",
        holds="Things other people wrote, as clean Markdown (`obsidian:defuddle` or the Web Clipper).",
        nots="Anything authored here. The folder is the divider between your writing and ingested text.",
        title="the page's own title",
        props=[("categories", "[]"), ("author", "[]"), ("url", ""), ("created", "{{date}}"), ("published", "")],
        body="\n"),
    "Daily": dict(
        singular="Daily note", template="Daily Note",
        holds="`YYYY-MM-DD`, the raw log of one day. Never rewritten after the day.",
        nots="Knowledge (copy it out to its own note and link back).",
        title="`YYYY-MM-DD`",
        props=[("tags", "\n  - daily"), ("cssclasses", "\n  - workbook")],
        views=[("Recent days", None, 14)], home="Recent days",
        sort="file.name", body="## Brief\n\n## Notes\n\n## Actions\n\n## Learned\n\n"),
}

# The two second brains the seed was distilled from, as a set of flags. A preset
# only fills in what was not given, so `--preset work --kinds ...` still works.
PRESETS = {
    "personal": dict(kinds="Notes,References,People,Clippings,Daily"),
    "work": dict(kinds="Knowledge,Playbooks,People,Meetings,Clippings,Daily"),
}

PROP_TYPES = {
    "aliases": "aliases", "cssclasses": "multitext", "tags": "tags", "categories": "multitext",
    "created": "date", "modified": "date", "status": "text", "source": "text", "org": "multitext",
    "role": "text", "start": "date", "end": "date", "date": "date", "people": "multitext",
    "topics": "multitext", "author": "multitext", "url": "text", "rating": "number",
    "published": "date", "type": "text", "key": "text", "short": "text", "keywords": "multitext",
    "kind": "text", "area": "text", "order": "number", "ideas": "multitext",
}


def kind_spec(name):
    if name in KINDS:
        return KINDS[name]
    singular = name[:-1] if name.endswith("s") and len(name) > 3 else name
    return dict(
        singular=singular, template=singular,
        holds="(fill in: what a %s note holds)" % singular.lower(),
        nots="(fill in: what does not belong)", title="(fill in: how these are named)",
        props=[("categories", "[]"), ("created", "{{date}}")], body="\n")


def kind_template(spec):
    lines = ["---"]
    for key, val in spec["props"]:
        lines.append("%s:%s%s" % (key, "" if val.startswith("\n") else " ", val) if val else "%s: " % key)
    lines.append("---")
    return "\n".join(lines) + "\n" + spec.get("body", "\n")


def kind_base(folder, spec):
    cols = [k for k, _ in spec["props"] if k not in ("tags", "cssclasses")]
    sort = spec.get("sort", "created")

    def view(name, status=None, limit=None):
        out = ["  - type: table", "    name: %s" % name]
        if status:
            out += ["    filters:", "      and:", '        - status == "%s"' % status]
        out += ["    order:", "      - file.name"] + ["      - %s" % c for c in cols]
        out += ["    sort:", "      - property: %s" % sort, "        direction: DESC"]
        if limit:
            out.append("    limit: %d" % limit)
        return out

    lines = ["filters:", "  and:", '    - file.inFolder("%s")' % folder,
             "properties:", "  file.name:", "    displayName: %s" % spec["singular"], "views:"]
    lines += view("All %s" % folder.lower())
    for name, status, limit in spec.get("views", []):
        lines += view(name, status, limit)
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------ plumbing


class Seeder:
    def __init__(self, dry):
        self.dry, self.made, self.kept = dry, [], []

    def write(self, path, data, binary=False):
        if os.path.exists(path):
            self.kept.append(path)
            return False
        self.made.append(path)
        if self.dry:
            return True
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as fh:
            fh.write(data)
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        return True

    def copy_tree(self, src, dest, tokens):
        for root, dirs, files in os.walk(src):
            dirs.sort()
            for fn in sorted(files):
                if fn == ".DS_Store":
                    continue
                rel = os.path.relpath(os.path.join(root, fn), src)
                parts = ["." + p[4:] if p.startswith("dot-") else p for p in rel.split(os.sep)]
                if parts[-1] == "gitignore":
                    parts[-1] = ".gitignore"
                target = os.path.join(dest, *[sub(p, tokens) for p in parts])
                ext = os.path.splitext(fn)[1]
                if ext in TEXT_EXT:
                    with open(os.path.join(root, fn), encoding="utf-8") as fh:
                        self.write(target, sub(fh.read(), tokens))
                else:
                    with open(os.path.join(root, fn), "rb") as fh:
                        self.write(target, fh.read(), binary=True)


def sub(text, tokens):
    for key, val in tokens.items():
        text = text.replace("@@%s@@" % key, val)
    return text


def git_root(path):
    probe = path
    while not os.path.isdir(probe):
        probe = os.path.dirname(probe) or "."
    try:
        out = subprocess.run(["git", "-C", probe, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def self_update():
    root = git_root(SKILL_DIR)
    if not root:
        print("build: not installed from a git checkout; using the bundled assets as they are")
        return 0
    try:
        out = subprocess.run(["git", "-C", root, "pull", "--ff-only", "--quiet"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print("build: could not reach the repo (%s); using what is on disk" % exc)
        return 0
    if out.returncode:
        print("build: pull failed, using what is on disk:\n%s" % out.stderr.strip())
    else:
        head = subprocess.run(["git", "-C", root, "log", "-1", "--format=%h %s"],
                              capture_output=True, text=True).stdout.strip()
        print("build: up to date at %s (%s)" % (head, root))
    return 0


def merge_settings(seeder, repo_root, stop_cmd=None, allow=(), start_cmd=None):
    """Add a Stop hook, a SessionStart hook and/or permission rules to .claude/settings.json without
    disturbing the rest. Each is added once: a rebuild finds it there and leaves it."""
    path = os.path.join(repo_root, ".claude", "settings.json")
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except ValueError:
            print("build: %s is not valid JSON; leaving it alone. Add this by hand:" % path)
            if stop_cmd:
                print("      Stop hook: %s" % stop_cmd)
            if start_cmd:
                print("      SessionStart hook (matcher startup): %s" % start_cmd)
            return
    before = json.dumps(data, sort_keys=True)
    if stop_cmd:
        stops = data.setdefault("hooks", {}).setdefault("Stop", [])
        if "session_check.py" not in json.dumps(stops):
            stops.append({"hooks": [{"type": "command", "command": stop_cmd, "timeout": 30,
                                     "statusMessage": "Checking the vault write-back"}]})
    if start_cmd:
        starts = data.setdefault("hooks", {}).setdefault("SessionStart", [])
        if not any(h.get("command") == start_cmd for e in starts if isinstance(e, dict)
                   for h in e.get("hooks", []) if isinstance(h, dict)):
            starts.append({"matcher": "startup", "hooks": [{"type": "command", "command": start_cmd}]})
    if allow:
        rules = data.setdefault("permissions", {}).setdefault("allow", [])
        for rule in allow:
            if rule not in rules:
                rules.append(rule)
    if json.dumps(data, sort_keys=True) == before:
        return
    print("build: %s .claude/settings.json" % ("would update" if seeder.dry else "updated"))
    if not seeder.dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")


def accent_css(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return ("\n/* The vault's accent, so it is told apart from every other vault at a glance. */\n"
            "body {\n  --accent-h: %d;\n  --accent-s: %d%%;\n  --accent-l: %d%%;\n}\n"
            % (round(hue * 360), round(sat * 100), round(light * 100)))


# ------------------------------------------------------------ archetypes


def brain_tokens(kinds, working_memory):
    map_rows, kind_rows, home, schema, types = [], [], [], {}, {}
    for folder in kinds:
        spec = kind_spec(folder)
        map_rows.append("| `%s/` | %s | %s |" % (folder, spec["holds"], spec["nots"]))
        keys = ", ".join("`%s`" % k for k, _ in spec["props"])
        kind_rows.append("| %s | %s Template | %s.base | %s | %s |"
                         % (folder, spec["template"], folder, keys, spec["title"]))
        view = spec.get("home", "All %s" % folder.lower())
        home.append("## %s\n\n![[%s.base#%s]]\n" % (folder, folder, view))
        schema[folder] = {"template": "%s Template.md" % spec["template"]}
        if spec.get("status"):
            schema[folder]["status"] = spec["status"]
        for key, _ in spec["props"]:
            types[key] = PROP_TYPES.get(key, "text")
    daily_use = ["One folder per kind of note. New notes land in `%s/`. To make one, create the "
                 "note in its folder and insert its template (Command palette, \"Templates: Insert "
                 "template\")." % kinds[0], ""]
    for folder in kinds:
        spec = kind_spec(folder)
        daily_use.append("- **`%s/`**, from *%s Template*: %s Its name: %s." % (
            folder, spec["template"], spec["holds"], spec["title"]))
    drafts = [k for k in kinds if kind_spec(k).get("status") == DRAFTS]
    if drafts:
        home.append("## Needs attention\n\nDrafts are unchecked. Stale notes were contradicted "
                    "by something newer and need a rewrite or a delete.\n")
        for k in drafts:
            home.append("![[%s.base#Drafts]]\n" % k)
    memory = ("Three memory tiers. Short-term: `Daily/` (when present), the raw log of one day, "
              "never rewritten after it. Mid-term: `Now.md`, what is in flight (Goals, Active, "
              "Waiting on, Recently done, Open questions), every bullet ending with the date it "
              "last moved; a bullet that settles into a fact becomes a note and the bullet links "
              "it. Long-term: the kind folders." if working_memory else
              "There is no working-memory page yet. If the same in-flight items keep being "
              "re-explained to sessions, add a `Now.md` (dated bullets under Goals, Active, "
              "Waiting on, Recently done, Open questions) and record the decision.")
    return dict(
        MAP_ROWS="\n".join(map_rows), KIND_ROWS="\n".join(kind_rows),
        HOME_SECTIONS="\n".join(home), MEMORY_RULE=memory, DAILY_USE="\n".join(daily_use),
        DEFAULT_FOLDER=kinds[0], KIND_LIST=" ".join("%s/" % k for k in kinds),
        NOW_ROW=("| `Now.md` | Working memory: what is in flight, every bullet dated. | Facts "
                 "(they become notes), history. |\n" if working_memory else ""),
    ), schema, types


def index_text(dest):
    """What bin/find.py keeps in .paths/index.txt, for the notes already in dest (none in a new vault)."""
    if not os.path.exists(os.path.join(dest, "bin", "vault.json")):
        return ""
    spec = importlib.util.spec_from_file_location("vault_find", os.path.join(ASSETS, "brain", "bin", "find.py"))
    finder = importlib.util.module_from_spec(spec)
    before, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in template/
    try:
        spec.loader.exec_module(finder)
    finally:
        sys.dont_write_bytecode = before
    return finder.build(dest)


def section(name, tokens):
    with open(os.path.join(ASSETS, "optional", "sections", name + ".md"), encoding="utf-8") as fh:
        return sub(fh.read(), tokens)


# The sections spliced into Rules.md, and when CLAUDE.md's one-line pointer sends a session to each.
RULES_SECTIONS = {
    "claude-ingest": "Before bringing anything in, filing it or removing a clipping",
    "claude-daily": "Before touching a daily note, its brief or a reply card",
}

# Size budgets, in characters, for the files a session loads without asking (and Rules.md).
# `SKILL.md` is every .claude/skills/*/SKILL.md; a vault-relative path overrides it for one skill.
BUDGETS = {"CLAUDE.md": 9000, "Rules.md": 20000, "Me.md": 5000, "Now.md": 12000, "SKILL.md": 12000}


def pointer(name, tokens):
    """CLAUDE.md's line for a section that lives in Rules.md, named by the section's own heading."""
    heading = section(name, tokens).split("\n", 1)[0].lstrip("#").strip()
    return '- %s: "%s" in `Rules.md`.\n' % (RULES_SECTIONS[name], heading)


def seed_brain(seeder, dest, tokens, kinds, working_memory, me=False):
    extra, schema, types = brain_tokens(kinds, working_memory)
    tokens = dict(tokens, **extra)
    ingest = "Clippings" in kinds
    daily = working_memory and "Daily" in kinds
    # The action log: one line per thing done on the owner's behalf, in a plain file in the
    # vault (a person working alone has no team channel to post it in).
    log_in_daily = "Daily" in kinds
    spliced = [n for n, on in (("claude-ingest", ingest), ("claude-daily", daily)) if on]
    tokens.update(
        ACTION_LOG=("`## Actions` in today's `Daily/YYYY-MM-DD.md`" if log_in_daily
                    else "`Actions.md`"),
        ME_RULE=section("claude-me", tokens) if me else "",
        ME_ROW=("| `Me.md` | Who the owner is, for any AI: purpose, sources, tools, what is "
                "private. | Content. |\n" if me else "") + (
                "| `Sources.md` | Where material comes from: how, cadence, last pulled, keep or not. | "
                "Notes. |\n" if ingest else "") + (
                "" if log_in_daily else "| `Actions.md` | The action log: one dated line per thing "
                "done on the owner's behalf. | Plans, notes. |\n"),
        BIN_EXTRA=(", `ingest.py` (bring things in), `librarian.py` and `librarian.md` (file them)"
                   if ingest else ""),
        EXTRA_SECTIONS="".join(section(n, tokens) + "\n" for n in spliced),  # into Rules.md
        SECTION_POINTERS="".join(pointer(n, tokens) for n in spliced),  # into CLAUDE.md
        README_SECTIONS="".join(section(n, tokens) + "\n" for n, on in
                                (("readme-daily", daily), ("readme-ingest", ingest)) if on),
    )
    seeder.copy_tree(os.path.join(ASSETS, "brain"), dest, tokens)
    if ingest:
        seeder.copy_tree(os.path.join(ASSETS, "optional", "ingest"), dest, tokens)
    if daily:
        seeder.copy_tree(os.path.join(ASSETS, "optional", "daily-loop"), dest, tokens)
    if me:
        with open(os.path.join(ASSETS, "optional", "Me.md"), encoding="utf-8") as fh:
            seeder.write(os.path.join(dest, "Me.md"), sub(fh.read(), tokens))
    if not log_in_daily:
        with open(os.path.join(ASSETS, "optional", "Actions.md"), encoding="utf-8") as fh:
            seeder.write(os.path.join(dest, "Actions.md"), sub(fh.read(), tokens))
    for folder in kinds:
        spec = kind_spec(folder)
        seeder.write(os.path.join(dest, folder, ".gitkeep"), "")
        seeder.write(os.path.join(dest, "Templates", "%s Template.md" % spec["template"]),
                     kind_template(spec))
        seeder.write(os.path.join(dest, "Templates", "Bases", "%s.base" % folder),
                     kind_base(folder, spec))
    for folder in ("Categories", "Attachments"):
        seeder.write(os.path.join(dest, folder, ".gitkeep"), "")
    seeder.write(os.path.join(dest, "bin", "vault.json"), json.dumps(
        {"kinds": schema, "draft_max_days": 14, "now_max_days": 14,
         "dash_exempt": [".obsidian/", ".git/", ".claude/", "bin/"], "budgets": BUDGETS}, indent=2) + "\n")
    types.update({k: PROP_TYPES[k] for k in ("aliases", "cssclasses", "tags", "modified")})
    seeder.write(os.path.join(dest, ".obsidian", "types.json"),
                 json.dumps({"types": types}, indent=2) + "\n")
    if "Daily" in kinds:
        seeder.write(os.path.join(dest, ".obsidian", "daily-notes.json"), json.dumps(
            {"folder": "Daily", "format": "YYYY-MM-DD",
             "template": "Templates/Daily Note Template"}, indent=2) + "\n")
    if working_memory:
        with open(os.path.join(ASSETS, "optional", "Now.md"), encoding="utf-8") as fh:
            seeder.write(os.path.join(dest, "Now.md"), sub(fh.read(), tokens))
    seeder.write(os.path.join(dest, ".paths", "index.txt"), index_text(dest))
    return tokens


def add_plugins(seeder, dest, plugins, tokens):
    for pid in plugins:
        src = os.path.join(ASSETS, "plugins", pid)
        if not os.path.isdir(src):
            print("build: no bundled plugin %r (have: %s)" % (pid, ", ".join(KNOWN_PLUGINS)))
            continue
        seeder.copy_tree(src, os.path.join(dest, ".obsidian", "plugins", pid), tokens)
    path = os.path.join(dest, ".obsidian", "community-plugins.json")
    have = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            have = json.load(fh)
    want = have + [p for p in plugins if p not in have]
    if want != have and not seeder.dry:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(want, fh, indent=2)
            fh.write("\n")
    # A vault that ships its own plugins has to track them.
    ignore = os.path.join(dest, ".gitignore")
    if os.path.exists(ignore) and not seeder.dry:
        with open(ignore, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        kept = [ln for ln in lines if ln.strip() != ".obsidian/plugins/"]
        if kept != lines:
            with open(ignore, "w", encoding="utf-8") as fh:
                fh.write("\n".join(kept))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=sorted(PRESETS),
                    help="personal or work (sets --kinds, --working-memory and --me)")
    ap.add_argument("--dest", help="vault directory, created if missing. Obsidian shows the vault under "
                                   "this folder's name (default: --name as a slug, e.g. sams-brain)")
    ap.add_argument("--name", help="the vault's name as its notes and CLAUDE.md say it, e.g. \"Sam's Brain\"")
    ap.add_argument("--generic-dir-ok", action="store_true",
                    help="allow a folder name like vault/ that does not say whose it is")
    ap.add_argument("--project", help="who or what the brain serves (default: the owner)")
    ap.add_argument("--owner", help="whose vault it is (default: git user.name's first word)")
    ap.add_argument("--kinds", default="", help="kind folders, comma separated (instead of a preset)")
    ap.add_argument("--plugins", default="", help="bundled home-made plugins to install: " + ", ".join(KNOWN_PLUGINS))
    ap.add_argument("--accent", help="accent colour as #rrggbb")
    ap.add_argument("--working-memory", action="store_true",
                    help="add Now.md (and, with a Daily kind, the start-of-day, run-brief and "
                         "end-of-day skills)")
    ap.add_argument("--me", action="store_true", help="add Me.md, who the owner is, for any AI")
    ap.add_argument("--date", help="the date written into the vault (default: today)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-update", action="store_true")
    args = ap.parse_args()

    if args.self_update:
        return self_update()
    if not args.name:
        ap.error("--name is required")
    if not args.preset and not args.kinds:
        args.preset = "personal"
    if args.preset:
        args.kinds = args.kinds or PRESETS[args.preset]["kinds"]
        args.working_memory = args.me = True
    owner = args.owner
    if not owner:
        try:
            owner = subprocess.run(["git", "config", "user.name"], capture_output=True,
                                   text=True).stdout.split()[0]
        except (OSError, IndexError):
            owner = "the owner"
    args.project = args.project or owner

    dest = os.path.abspath(os.path.expanduser(args.dest or slug(args.name) or "my-brain"))
    vault_folder = os.path.basename(dest)
    if vault_folder.lower() in GENERIC_DIRS and not args.generic_dir_ok:
        ap.error("the vault folder would be %r. Obsidian lists a vault by its folder name, so give it "
                 "one that says whose it is, e.g. --dest %s (or pass --generic-dir-ok)."
                 % (vault_folder, os.path.join(os.path.dirname(dest), "%s-brain" % slug(owner))))
    repo_root = git_root(dest) or dest
    vault_path = os.path.relpath(dest, repo_root)
    prefix = "" if vault_path == "." else vault_path.replace(os.sep, "/") + "/"
    tokens = dict(
        VAULT_NAME=args.name, PROJECT=args.project,
        VAULT_PATH=("`%s`" % prefix if prefix else "the repo root" if git_root(dest)
                    else "the top of this folder"), VAULT_PREFIX=prefix,
        DATE=args.date or datetime.date.today().isoformat(), OWNER=owner, HOME_NOTE="Home",
    )
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    plugins = [p.strip() for p in args.plugins.split(",") if p.strip()]
    seeder = Seeder(args.dry_run)

    seed_brain(seeder, dest, tokens, kinds, args.working_memory, args.me)
    allow = ["Bash(python3 %sbin/lint.py:*)" % prefix, "Bash(python3 %sbin/find.py:*)" % prefix,
             "Bash(python3 %sbin/paths.py:*)" % prefix]
    if "Clippings" in kinds:
        allow += ["Bash(python3 %sbin/ingest.py:*)" % prefix]
    # The nudge: on startup Claude Code runs due mode, which prints one line only when tend is due.
    merge_settings(seeder, repo_root, allow=allow, start_cmd="python3 %s due --hook" % shlex.quote(prefix + "bin/paths.py"))
    if plugins:
        add_plugins(seeder, dest, plugins, tokens)
    if args.accent:
        css = os.path.join(dest, ".obsidian", "snippets", "vault.css")
        if not seeder.dry and os.path.exists(css):
            with open(css, "a", encoding="utf-8") as fh:
                fh.write(accent_css(args.accent))

    verb = "would create" if args.dry_run else "created"
    for path in seeder.made:
        print("  + %s" % os.path.relpath(path, repo_root))
    for path in seeder.kept:
        print("  = %s (exists, kept)" % os.path.relpath(path, repo_root))
    print("build: %s %d files, kept %d, vault at %s" % (verb, len(seeder.made), len(seeder.kept), dest))
    print("build: Obsidian will list this vault as \"%s\" (its folder name)" % vault_folder)
    if not args.dry_run:
        print("build: check it with: python3 %sbin/lint.py" % prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
