#!/usr/bin/env python3
"""Test the seed end to end. Standard library only, no network, no AI.

    python3 tools/check.py

Builds both presets and a custom vault into a temporary folder, runs each
vault's own check, pushes sample files through bin/ingest.py, round-trips a
fake chat answer through bin/librarian.py --apply, checks the daily loop's
reply cards and action log, checks the CLAUDE.md and Rules.md split and the
size budgets lint warns on, checks every hub opens with `## Start here` and
lint warns on a busy hub with no plain link, runs bin/paths.py over the fixture
transcripts in tools/fixtures/paths/, sends notes to two beds through
bin/beds.py and pulls edits back (git in temporary folders, a local bare repo
for the remote), checks the tend skill, the dated report a pass saves, due mode
and its SessionStart hook, and that nothing sends the reader to the skill tend
replaced, installs every bundled plugin, upgrades a vault planted earlier
(build_vault.py --upgrade: the manifest, .new files, a dry run, a second run
that changes nothing), checks starter-vault/ is what the seed makes today,
scans this repo's own docs for en and em dashes, and fails when a tracked
file names a term from the git-ignored tools/never-share.txt. Prints one line per check and exits 1 if
any failed. The pre-commit hook in .githooks/ and the CI job run it.
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import unquote

# CI has no PYTHONDONTWRITEBYTECODE; run every check the way CI and vault owners do.
os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "setup", "build_vault.py")
PY = sys.executable
failed = []


def check(label, ok, detail=""):
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, ("\n      " + detail.strip().replace("\n", "\n      ")) if not ok and detail else ""))
    if not ok:
        failed.append(label)


def run(args, cwd=None, env=None):
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    return res.returncode, res.stdout + res.stderr


def seed(tmp, *args):
    return run([PY, SEED, *args], cwd=tmp)


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def no_git_env():
    """The environment without GIT_* variables, so an inherited GIT_DIR never points git at a real repo."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def fixtures(d):
    os.makedirs(os.path.join(d, "export", "img"))
    with open(os.path.join(d, "export", "Trip ideas 0123456789abcdef0123456789abcdef.md"), "w") as fh:
        fh.write("---\naliases: [Trip]\n---\n# Trip ideas\n\nLisbon — in May.\n\n![x](img/a.png)\n")
    with open(os.path.join(d, "export", "img", "a.png"), "wb") as fh:
        fh.write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))
    with open(os.path.join(d, "page.html"), "w") as fh:
        fh.write("<html><head><title>Sleep</title><meta name='author' content='Jane Doe'></head><body>"
                 "<nav>menu</nav><article><h1>Sleep</h1><p>It <b>matters</b>.</p><ul><li>a<ul><li>b</li>"
                 "</ul></li></ul><table><tr><th>x</th><th>y</th></tr><tr><td>1</td><td>2</td></tr></table>"
                 "<p>" + "Filler text for length. " * 12 + "</p></article></body></html>")
    with zipfile.ZipFile(os.path.join(d, "essay.docx"), "w") as z:
        z.writestr("word/document.xml",
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                   '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Intro</w:t></w:r></w:p>'
                   '<w:p><w:r><w:t>Body – text.</w:t></w:r></w:p></w:body></w:document>')
    with open(os.path.join(d, "mail.eml"), "w") as fh:
        fh.write("From: Bob Smith <bob@example.com>\nSubject: A book\nDate: Tue, 07 Oct 2026 09:00:00 +0000\n\nRead it.\n")
    with open(os.path.join(d, "data.csv"), "w") as fh:
        fh.write("a,b\n1,2\n")


def ingest_round_trip(vault, fx):
    ing = [PY, os.path.join(vault, "bin", "ingest.py")]
    code, out = run(ing + ["add", os.path.join(fx, "export"), os.path.join(fx, "page.html"),
                           os.path.join(fx, "mail.eml"), os.path.join(fx, "data.csv")], cwd=vault)
    check("ingest: files and a folder", code == 0 and out.count("ADDED") == 4, out)
    added = re.findall(r"ADDED  (\S.*?)\.md  ", out)
    code, out = run(ing + ["add", "--mine", os.path.join(fx, "essay.docx")], cwd=vault)
    check("ingest: --mine", code == 0 and "ADDED" in out, out)
    added += re.findall(r"ADDED  (\S.*?)\.md  ", out)
    index = read(os.path.join(vault, ".paths", "index.txt"))
    check("ingest: add leaves the index current", len(added) == 5 and all(
        "\n%s ::" % a in "\n" + index for a in added) and "Clippings/Trip ideas :: Trip :: ::" in index,
        "added %s\nindex:\n%s" % (added, index))
    clip = open(os.path.join(vault, "Clippings", "Trip ideas.md"), encoding="utf-8").read()
    check("ingest: Notion id dropped, dash replaced, image attached",
          "—" not in clip and "![[a.png]]" in clip and "aliases: [Trip]" in clip, clip)
    page = open(os.path.join(vault, "Clippings", "Sleep.md"), encoding="utf-8").read()
    check("ingest: HTML lists, tables, author", "- a\n    - b" in page and "| --- | --- |" in page
          and "[[Jane Doe]]" in page and "menu" not in page, page)
    code, out = run(ing + ["waiting"], cwd=vault)
    check("ingest: waiting lists all five", out.count("WAITING") == 5, out)
    code, out = run([PY, os.path.join(vault, "bin", "lint.py")], cwd=vault)
    check("lint passes after ingest", code == 0, out)

    with open(os.path.join(vault, "Clippings", "A book.md"), "a", encoding="utf-8") as fh:
        fh.write("- the owner's own line\n")
    code, out = run([PY, os.path.join(vault, "bin", "librarian.py"), "--paste"], cwd=vault)
    check("librarian: --paste prints the job, with CLAUDE.md and Rules.md", code == 0
          and "=== FILE: Clippings/A book.md" in out and "## The vault's rules (Rules.md)\n\n# Rules" in out
          and "## The vault's rules (CLAUDE.md)" in out, out[-500:])
    answer = os.path.join(fx, "answer.txt")
    mine = [p for p in os.listdir(os.path.join(vault, "Notes")) if p.endswith(".md")][0]
    with open(answer, "w", encoding="utf-8") as fh:
        fh.write("=== FILE: Clippings/A book.md\n=== NAME: Book from Bob\n---\ncategories: []\nauthor: []\n"
                 "url:\ncreated: 2026-10-10\npublished:\ningested: 2026-10-10\n---\n<!-- ingest:start -->\n"
                 "Rewritten — summary.\n<!-- ingest:end -->\n\n- the AI's line\n=== END\n\n"
                 "=== FILE: Notes/%s\n---\ncategories: []\ncreated: 2026-10-10\ntopics: []\ningested: 2026-10-10\n"
                 "---\n<!-- ingest:start -->\nAI REWRITE\n<!-- ingest:end -->\n\n## Related\n\n- [[Book from Bob]]\n"
                 "=== END\n\n=== FILE: Home.md\nnope\n=== END\n\nFILED  Book from Bob  |  test\n" % mine)
    code, out = run([PY, os.path.join(vault, "bin", "librarian.py"), "--apply", answer], cwd=vault)
    book = os.path.join(vault, "Clippings", "Book from Bob.md")
    text = open(book, encoding="utf-8").read() if os.path.exists(book) else ""
    check("librarian: --apply renames, keeps the owner's text, drops the AI's",
          "filed:" in text and "the owner's own line" in text and "the AI's line" not in text
          and "—" not in text, out + text)
    essay = open(os.path.join(vault, "Notes", mine), encoding="utf-8").read()
    check("librarian: --apply never rewrites --mine text", "AI REWRITE" not in essay and "[[Book from Bob]]" in essay, essay)
    check("librarian: --apply refuses other notes", "REFUSED  Home.md" in out, out)
    index = read(os.path.join(vault, ".paths", "index.txt"))
    check("librarian: --apply leaves the index current",
          "\nClippings/Book from Bob ::" in "\n" + index and "\nClippings/A book ::" not in "\n" + index, index)


def prune_round_trip(vault, fx):
    ing = [PY, os.path.join(vault, "bin", "ingest.py")]

    def note(rel, fm, body="<!-- ingest:start -->\nx\n<!-- ingest:end -->\n\n## Notes\n\n- \n"):
        path = os.path.join(vault, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\n%s\n---\n%s" % (fm, body))

    clip = ("categories: []\nauthor: []\nurl: \"https://ex.com/a\"\ncreated: 2026-01-01\npublished:\n"
            "via: \"Feeds\"\ningested: 2026-01-01\nfiled: 2026-01-01")
    note("Clippings/Unused one.md", clip)
    note("Clippings/Unused one (2).md", clip)
    note("Clippings/Linked one.md", clip.replace("/a", "/b"))
    note("Clippings/Written on.md", clip.replace("/a", "/c"),
         "<!-- ingest:start -->\nx\n<!-- ingest:end -->\n\n## Notes\n\n- my thought\n")
    note("Clippings/Never filed.md", clip.replace("/a", "/d").replace("\nfiled: 2026-01-01", ""))
    note("Notes/Old idea.md", "categories:\n  - \"[[Lonely]]\"\ncreated: 2026-01-01\ntopics: []",
         "See [[Linked one]].\n")
    note("Categories/Lonely.md", "tags:\n  - categories", "\n![[Topics.base#In this topic]]\n")
    with open(os.path.join(vault, "Attachments", "orphan.png"), "wb") as fh:
        fh.write(b"x")
    src = os.path.join(vault, "Sources.md")
    text = open(src, encoding="utf-8").read().replace(
        "|---|---|---|---|---|---|\n",
        "|---|---|---|---|---|---|\n| Feeds | articles | clipper | weekly | 2026-01-01 | trial |\n"
        "| Old app | notes | importer | once | 2026-01-01 | yes |\n", 1)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(text)

    code, out = run(ing + ["report"], cwd=vault)
    want = ["Unused clippings", "Clippings/Unused one.md", "Waiting too long", "Clippings/Never filed.md",
            "Thin topics", "Categories/Lonely.md", "Possible duplicates", "Unused attachments",
            "Attachments/orphan.png", "Sources due", "Feeds  (weekly", "Where things come from", "Feeds:"]
    missing = [w for w in want if w not in out]
    unused = out.split("## Unused clippings", 1)[-1].split("##", 1)[0]
    check("report: finds what to prune", code == 0 and not missing, "missing %s\n%s" % (missing, out))
    check("report: a linked or written-on clipping is not 'unused'",
          "Linked one" not in unused and "Written on" not in unused, unused)
    check("report: a one-off source is never due", "Old app" not in out.split("## Sources due", 1)[-1].split("##")[0], out)
    code, out = run(ing + ["report", "--due"], cwd=vault)
    check("report --due lists only due sources", "DUE  Feeds" in out and "Old app" not in out, out)

    code, out = run(ing + ["trash", "Unused one"], cwd=vault)
    check("trash: moves an unused clipping to .trash/", code == 0 and
          os.path.exists(os.path.join(vault, ".trash", "Unused one.md")), out)
    code, out = run(ing + ["trash", "Linked one"], cwd=vault)
    check("trash: refuses a linked clipping", code != 0 and os.path.exists(os.path.join(vault, "Clippings", "Linked one.md")), out)
    code, out = run(ing + ["trash", "Written on"], cwd=vault)
    check("trash: refuses a clipping the owner wrote on", code != 0, out)
    code, out = run(ing + ["trash", "Old idea"], cwd=vault)
    check("trash: refuses the owner's own notes", code != 0 and os.path.exists(os.path.join(vault, "Notes", "Old idea.md")), out)
    code, out = run(ing + ["trash", "orphan.png"], cwd=vault)
    check("trash: moves an unused attachment", code == 0 and os.path.exists(os.path.join(vault, ".trash", "orphan.png")), out)

    run(ing + ["add", os.path.join(fx, "data.csv"), "--via", "Feeds"], cwd=vault)
    run(ing + ["add", os.path.join(fx, "data.csv"), "--via", "New place"], cwd=vault)
    code, out = run(ing + ["add", os.path.join(fx, "mail.eml"), "--via", "FEEDS"], cwd=vault)
    made = re.search(r"ADDED  (\S.*?\.md)", out)
    text = open(os.path.join(vault, made.group(1)), encoding="utf-8").read() if made else ""
    check("add --via takes the spelling already in Sources.md", 'via: "Feeds"' in text, out + text)
    text = open(src, encoding="utf-8").read()
    check("add --via stamps Last pulled and adds new sources",
          "| Feeds | articles | clipper | weekly | 2026-01-01 |" not in text and "| Feeds |" in text
          and "| New place |" in text, text)


def old_vault(d):
    """An existing Obsidian vault, as someone might bring it: two content folders, a dated note, an
    image in a subfolder, names that clash, a templates folder, a Base, a Canvas, rule files."""
    def put(rel, text, mtime=None):
        path = os.path.join(d, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
            fh.write(text)
        if mtime:
            os.utime(path, (mtime, mtime))

    put(".obsidian/app.json", "{}")
    put(".obsidian/templates.json", '{"folder": "_templates"}')
    put(".trash/Gone.md", "deleted\n")
    put(".claude/CLAUDE.md", "Be brief.\n")
    put("_templates/Meeting.md", "---\ncreated: {{date}}\n---\n")
    put("Board.base", "views: []\n")
    put("Map.canvas", "{}")
    put("CLAUDE.md", "Answer in one line.\n")
    # Sorted, the first two mapped notes are Clips/Article.md and Home.md: the sample.
    put("Clips/Article.md", "---\ncategories: [\"[[Reading list]]\"]\nurl: https://example.com/a\n"
        "author: \"[[Jane Doe]]\"\n---\nSomeone else's words \u2013 with a dash.\n")
    put("Home.md", "Start at [[Plan]] and [[Garden ideas]].\n\n![[x.png]]\n")
    put("Journal/2024-05-01.md", "Planted beans, see [[Plan]].\n")
    put("Projects/Plan.md", "---\ncategories:\n  - \"[[Gardening]]\"\n  - Films\n  - Home\ncreated: 2021-03-04\n"
        "aliases:\n  - Garden plan\ntags:\n  - green\nrating: 4\n---\n# Plan\n\n"
        "Back to [[Home]], [[Home|the start]] and [[Home#Top]], or [back](../Home.md).\n\n![[x.png]]\n\n"
        "![[Garden ideas]] and [ideas](Garden%20ideas.md)\n\nSee [[Old]] too.\n\n"
        "In code: `[[Home]]` and\n\n```\n![[x.png]] [[Home]]\n```\n")
    put("Projects/Garden ideas.md", "Ideas for [[Projects/Plan|the plan]].\n", mtime=1577923200)  # 2020-01-02
    put("Projects/Tools/AGENTS.md", "---\ncreated: March 4, 2021\n---\nNotes on agents, not rules.\n")
    put("Archive/Old.md", "old\n")
    put("Attachments/img/x.png", base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))


def vault_import(tmp):
    """ingest.py add --vault: a proposal first, then a sample, then the rest, as the harvest skill runs it."""
    code, out = seed(tmp, "--preset", "personal", "--dest", "import-brain", "--name", "Import Brain", "--owner", "Sam")
    vault = os.path.join(tmp, "import-brain")
    src = os.path.join(tmp, "old-vault")
    old_vault(src)
    with open(os.path.join(vault, "Attachments", "x.png"), "wb") as fh:
        fh.write(b"already here")
    mine = "---\ncategories: []\ncreated: 2026-01-01\ntopics: []\n---\nThe brain's own garden ideas.\n"
    with open(os.path.join(vault, "Notes", "Garden ideas.md"), "w", encoding="utf-8") as fh:
        fh.write(mine)
    ing = [PY, os.path.join(vault, "bin", "ingest.py"), "add"]
    maps = ["--map", ".=Notes", "--map", "Projects=Notes", "--map", "Clips=Clippings", "--map", "dates=Daily"]

    def tree():
        out = []
        for root, dirs, files in os.walk(vault):
            dirs[:] = [x for x in dirs if x != ".git"]
            out += [os.path.relpath(os.path.join(root, f), vault) for f in files]
        return sorted(out), open(os.path.join(vault, "Sources.md"), encoding="utf-8").read()

    def read(rel):
        path = os.path.join(vault, rel)
        return open(path, encoding="utf-8").read() if os.path.exists(path) else ""

    before = tree()
    code, out = run(ing + [src], cwd=vault)
    check("import: a plain add of a vault points at --vault and writes nothing",
          "--vault" in out and "ADDED" not in out and tree() == before, out)
    code, out = run(ing + ["--vault", vault, "--map", ".=Notes"], cwd=vault)
    check("import: refuses to import the vault into itself", code != 0 and "ADDED" not in out and tree() == before, out)
    code, out = run(ing + ["--vault", src], cwd=vault)
    listed = [ln for ln in out.split("\n") if re.match(r"\s*\d+\. ", ln)]
    want = [r"\(root\).*1 note.*Notes", r"Projects.*3 notes.*Notes", r"Clips.*1 note", r"Archive.*1 note",
            r"dates.*1 note.*Daily"]
    missing = [w for w in want if not any(re.search(w, ln) for ln in listed)]
    check("import: no mapping proposes one, numbered with counts, and writes nothing",
          code == 0 and not missing and not any("_templates" in ln or "Journal" in ln for ln in listed)
          and '--map "Projects=Notes"' in out and '--map "dates=Daily"' in out and tree() == before,
          "missing %s\n%s" % (missing, out))

    code, out = run(ing + ["--vault", src, "--dry-run"] + maps, cwd=vault)
    check("import: --dry-run prints the plan and writes nothing",
          code == 0 and out.count("ADDED") == 6 and tree() == before, out)
    code, sample = run(ing + ["--vault", src, "--sample", "2", "--via", "Old vault"] + maps, cwd=vault)
    home, article = read("Notes/Home (2).md"), read("Clippings/Article.md")
    check("import: --sample 2 imports two notes and stops",
          code == 0 and sample.count("ADDED") == 2 and home and article and not read("Notes/Plan.md"), sample)
    check("import: a sampled note links a clashing note that sorts after the sample by its final name",
          "[[Garden ideas (2)]]" in home and "![[x (2).png]]" in home, home)
    check("import: dashes replaced in imported text", "\u2013" not in article and "words - with" in article, article)
    check("import: --via stamps Sources.md", "| Old vault |" in read("Sources.md"), read("Sources.md"))

    # The librarian files the sampled clipping: rewrites its region and renames it.
    clip = re.sub(r"<!-- ingest:start -->.*<!-- ingest:end -->", "<!-- ingest:start -->\nA summary.\n<!-- ingest:end -->",
                  article, flags=re.S).replace("\n---\n", "\nfiled: 2026-10-14\n---\n", 1)
    with open(os.path.join(vault, "Clippings", "Good read.md"), "w", encoding="utf-8") as fh:
        fh.write(clip)
    os.remove(os.path.join(vault, "Clippings", "Article.md"))

    code, out = run(ing + ["--vault", src, "--via", "Old vault"] + maps, cwd=vault)
    check("import: the full run brings the rest and nothing twice, even a filed and renamed clipping",
          code == 0 and out.count("ADDED") == 4 and "2 notes imported before" in out
          and not read("Clippings/Article.md") and not read("Notes/Home (3).md"), out)
    if os.path.exists(os.path.join(vault, "bin", "find.py")):
        index = read(".paths/index.txt")
        check("import: the import leaves the index listing its notes",
              all(n in index for n in ("Notes/Plan", "Notes/Garden ideas (2)", "Notes/Home (2)", "Clippings/Good read")),
              index)
    else:
        print("skip  import: the import leaves the index listing its notes (no bin/find.py yet)")

    plan, ideas, agents = read("Notes/Plan.md"), read("Notes/Garden ideas (2).md"), read("Notes/AGENTS.md")
    check("import: notes land in their mapped kinds, the dated one in Daily/",
          plan and ideas and agents and "beans" in read("Daily/2024-05-01.md")
          and read("Notes/Garden ideas.md") == mine, out)
    check("import: categories, created, aliases, tags and other properties kept",
          '- "[[Gardening]]"\n  - "[[Films]]"\n  - "[[Home (3)]]"' in plan and "created: 2021-03-04" in plan
          and "Garden plan" in plan and "- green" in plan and "rating: 4" in plan and "created: 2020-01-02" in ideas
          and "created: March 4, 2021" in agents and "https://example.com/a" in clip and "[[Jane Doe]]" in clip
          and 'via: "Old vault"' in plan, plan + ideas + agents)
    check("import: missing topic pages made from the topic template, never on a note's name",
          read("Categories/Gardening.md") == read("Templates/Topic Template.md") and read("Categories/Films.md")
          and read("Categories/Home (3).md") and not read("Categories/Home.md") and read("Categories/Reading list.md"),
          out)
    check("import: the embedded image is copied flat once, renamed on a clash, and the embed rewritten",
          "![[x (2).png]]" in plan and os.path.exists(os.path.join(vault, "Attachments", "x (2).png"))
          and not os.path.exists(os.path.join(vault, "Attachments", "x (3).png"))
          and read("Attachments/x.png") == "already here", plan)
    check("import: clashing notes are renamed and every link to them rewritten, Markdown links too",
          "[[Home (2)]], [[Home (2)|the start]] and [[Home (2)#Top]], or [[Home (2)|back]]" in plan
          and "![[Garden ideas (2)]] and [[Garden ideas (2)|ideas]]" in plan and "RENAMED  Home" in sample
          and "[[Plan|the plan]]" in ideas and "[[Old]]" in plan, sample + plan + ideas)
    check("import: links and embeds inside code are left alone",
          "`[[Home]]`" in plan and "```\n![[x.png]] [[Home]]\n```" in plan, plan)
    names = " ".join(tree()[0])
    check("import: nothing comes in from the skipped places",
          not any(n in names for n in ("Gone", "Meeting", "Board.base", "Map.canvas", "Old.md"))
          and not any(t in read(p) for p in tree()[0] if p.endswith(".md") for t in ("Answer in one line", "Be brief")),
          names)
    summary = ["SKIPPED  .claude/ (1 file)", "SKIPPED  .obsidian/ (2 files)", "SKIPPED  .trash/ (1 file)",
               "SKIPPED  _templates/", "SKIPPED  1 .base file", "SKIPPED  1 .canvas file",
               "SKIPPED  Archive/ (1 note): not mapped", "RULES    CLAUDE.md, .claude/CLAUDE.md:", "Decisions.md", "Me.md"]
    missing = [s for s in summary if s not in out]
    check("import: the summary counts what was skipped and names only the root's rule files",
          not missing and "Tools/AGENTS.md" not in out.split("RULES", 1)[-1], "missing %s\n%s" % (missing, out))
    code, out = run([PY, os.path.join(vault, "bin", "lint.py")], cwd=vault)
    check("import: lint passes after the import", code == 0, out)


def daily_loop(tmp):
    """The brief's reply cards, the action log, the standing rules, and every skill's header."""
    vault = os.path.join(tmp, "sam-brain")
    daily_tpl = open(os.path.join(vault, "Templates", "Daily Note Template.md"), encoding="utf-8").read()
    check("daily template has ## Actions and opts in to reply cards",
          "## Actions" in daily_tpl and "  - workbook" in daily_tpl, daily_tpl)
    rules = open(os.path.join(vault, "CLAUDE.md"), encoding="utf-8").read()
    check("CLAUDE.md: say how before you do, and log every action to the daily note",
          "Say how before you do" in rules and "`## Actions` in today's `Daily/" in rules, rules[:1500])
    other = os.path.join(tmp, "kinds-brain")
    rules = open(os.path.join(other, "CLAUDE.md"), encoding="utf-8").read()
    check("a vault without Daily/ logs actions to Actions.md",
          os.path.exists(os.path.join(other, "Actions.md")) and "appended to `Actions.md`" in rules, rules[:1500])

    skills = os.path.join(vault, ".claude", "skills")
    for name in sorted(os.listdir(skills)):
        text = open(os.path.join(skills, name, "SKILL.md"), encoding="utf-8").read()
        head = text.split("\n---", 1)[0]
        check("skill %s: frontmatter names it and describes it" % name,
              re.search(r"^name: %s$" % re.escape(name), head, re.M) is not None
              and re.search(r"^description: \S", head, re.M) is not None, head)
    check("run-brief ships with the daily loop", os.path.isdir(os.path.join(skills, "run-brief")))

    # The brief's example must be what the response-cards plugin draws as a card.
    js = open(os.path.join(ROOT, "template", "plugins", "response-cards", "main.js"), encoding="utf-8").read()
    label = re.compile(re.search(r"const LABEL = /(.+)/;", js).group(1))
    brief = open(os.path.join(skills, "start-of-day", "SKILL.md"), encoding="utf-8").read()
    example = "\n".join(re.findall(r"```markdown\n(.*?)```", brief, re.S))
    cards = [ln for ln in example.split("\n") if "**Reply:**" in ln]
    check("start-of-day's reply cards match the response-cards plugin",
          cards and all(label.match(ln) for ln in cards), "\n".join(cards))

    today = os.path.join(vault, "Daily", "2026-10-10.md")
    with open(today, "w", encoding="utf-8") as fh:
        fh.write(daily_tpl.replace("## Actions\n", "## Actions\n\n"
                 "- 2026-10-10 09:40 Filed 6 clippings. Why: brief item 2. Chose: two topics. Asked by: Sam's reply on brief item 2.\n"
                 "- 09:41 Drafted a reply to Bob. Why: asked. Asked by: Sam in chat.\n"
                 "- 2026-10-10 09:42 Moved a note. Asked by: Sam in chat.\n"))
    code, out = run([PY, os.path.join(vault, "bin", "lint.py")], cwd=vault)
    check("lint: warns on action log lines with no time or no Why:",
          code == 0 and out.count("action log line") == 2 and "Filed 6" not in out, out)
    with open(os.path.join(other, "Actions.md"), "a", encoding="utf-8") as fh:
        fh.write("- 2026-10-10 09:40 Made [[Sam]]. Why: a new person. Asked by: Sam in chat.\n")
    code, out = run([PY, os.path.join(other, "bin", "lint.py")], cwd=other)
    check("lint: a good Actions.md passes", code == 0 and "action log line" not in out, out)


def find_tool(tmp):
    """bin/find.py: the index it builds, its queries, the find log, and what keeps the index current."""
    code, out = seed(tmp, "--preset", "work", "--dest", "find-brain", "--name", "Find Brain", "--owner", "Sam")
    check("build a vault for the find checks", code == 0, out)
    vault = os.path.join(tmp, "find-brain")
    index = os.path.join(vault, ".paths", "index.txt")
    flog = os.path.join(vault, ".paths", "find.log")

    def note(rel, fm, body="\n"):
        path = os.path.join(vault, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\n%s\n---\n%s" % (fm, body))
        return path

    def find(*args):
        code, out = run([PY, os.path.join("bin", "find.py"), *args], cwd=vault)
        return code, [ln for ln in out.split("\n") if " ::" in ln], out

    claim = "created: 2026-10-01\nsource: \"\"\n"
    note("Knowledge/Sleep comes before focus.md", claim + 'categories:\n  - "[[Sleep]]"\n  - "[[Health]]"\n'
         "status: draft\naliases: [Rest first]")
    note("Knowledge/Coffee after noon hurts sleep.md", claim + 'categories: ["[[Sleep]]"]\nstatus: stale')
    note("Knowledge/Blue light delays sleep.md", claim + 'categories:\n  - "[[Sleep hygiene]]"\n'
         "status: verified\naliases:\n  - Screens at night")
    note("Knowledge/alpha waves rise at rest.md", claim + "categories: []\nstatus: draft")
    note("Knowledge/.drafts/Secret sleep plan.md", claim + "categories: []\nstatus: draft")
    note("Playbooks/Wind down at night.md", claim + 'categories:\n  - "[[Sleep|sleep]]"\nstatus: draft')
    bob = note("People/Bob Smith.md", claim + "categories: []\norg: []\nrole: ")
    for topic in ("Sleep", "Health", "Sleep hygiene"):
        note("Categories/%s.md" % topic, "tags:\n  - categories", "\n![[Topics.base#In this topic]]\n")
    note("Daily/2026-10-10.md", "tags:\n  - daily\ncssclasses:\n  - workbook", "Slept badly, no focus.\n")
    note("Sleep diary.md", 'categories:\n  - "[[Sleep]]"')
    want = ["Categories/Health :: :: ::", "Categories/Sleep :: :: ::", "Categories/Sleep hygiene :: :: ::",
            "Knowledge/alpha waves rise at rest :: :: :: draft",
            "Knowledge/Blue light delays sleep :: Screens at night :: Sleep hygiene :: verified",
            "Knowledge/Coffee after noon hurts sleep :: :: Sleep :: stale",
            "Knowledge/Sleep comes before focus :: Rest first :: Sleep, Health :: draft",
            "People/Bob Smith :: :: ::", "Playbooks/Wind down at night :: :: Sleep :: draft"]

    code, lines, out = find("--all")
    check("find --all prints the index: one line per note in a kind folder or Categories/, sorted, "
          "lists joined, empty slots kept, never Daily/, root files or dot folders",
          code == 0 and lines == want and read(index) == "\n".join(want) + "\n", out)
    code, lines, out = find("sleep", "focus")
    check("find: every word must match", code == 0 and lines == [want[6]], out)
    code, lines, out = find("rest first")
    check("find: words match aliases", lines == [want[6]], out)
    code, lines, out = find("coffee")
    check("find: a stale note is left out", code == 0 and lines == [], out)
    code, lines, out = find("coffee", "--stale")
    check("find --stale shows it", lines == [want[5]], out)
    code, lines, out = find("--topic", "Sleep")
    check("find --topic: exactly that topic's notes", code == 0 and lines == [want[6], want[8]], out)
    code, lines, out = find("--topic", "sleep hygiene")
    check("find --topic ignores case", lines == [want[4]], out)
    code, lines, out = find("marmalade")
    check("find: a miss prints no note", code == 0 and lines == [], out)

    entries = [ln.split("\t") for ln in read(flog).split("\n") if ln]
    check("find log: one tab-separated line per word or --topic query, none for --all",
          len(entries) == 7 and all(re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", e[0]) for e in entries),
          read(flog))
    check("find log: the query, the hit count and the matched paths",
          entries and entries[0][1:] == ["sleep focus", "1", "Knowledge/Sleep comes before focus.md"]
          and entries[4][1:] == ["--topic Sleep", "2", "Knowledge/Sleep comes before focus.md",
                                 "Playbooks/Wind down at night.md"], read(flog))
    check("find log: a miss is recorded with 0 hits", entries and entries[-1][1:] == ["marmalade", "0"], read(flog))

    old = note("Knowledge/Magnesium helps sleep.md", claim + "categories: []\nstatus: draft")
    os.utime(old, (978307200, 978307200))  # a pull or a copy can leave a new note looking old
    code, lines, out = find("magnesium")
    check("find: a note added by hand is found by the next query",
          lines == ["Knowledge/Magnesium helps sleep :: :: :: draft"]
          and "Knowledge/Magnesium helps sleep ::" in read(index), out)
    note("People/Bob Smith.md", claim + "categories: []\norg: []\nrole: \naliases: [Bobby]")
    later = (os.path.getmtime(index) if os.path.exists(index) else 0) + 10
    os.utime(bob, (later, later))
    code, lines, out = find("bobby")
    check("find: a note edited by hand is found by the next query", lines == ["People/Bob Smith :: Bobby :: ::"], out)

    good = read(index)
    with open(index, "w", encoding="utf-8") as fh:
        fh.write(good.replace("before focus :: Rest first :: Sleep, Health :: draft", "before focus :: draft"))
    soon = os.path.getmtime(index) + 100
    os.utime(index, (soon, soon))  # newer than every note, as after a clone
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    check("lint rewrites an index out of shape, says so, and exits 0",
          code == 0 and ".paths/index.txt" in out and read(index) == good, out)
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    check("lint says nothing about an index that is current", code == 0 and ".paths/index.txt" not in out, out)

    git = shutil.which("git")
    if git:
        env = no_git_env()
        run([git, "init", "-q"], cwd=vault, env=env)
        ignored = {p: run([git, "check-ignore", "-q", p], cwd=vault, env=env)[0] == 0
                   for p in (".paths/find.log", ".paths/index.txt", ".paths/reports/2026-10-14.md")}
        check("the find log is git-ignored, the index and the rest of .paths/ are not",
              ignored == {".paths/find.log": True, ".paths/index.txt": False,
                          ".paths/reports/2026-10-14.md": False}, str(ignored))
    else:
        print("skip  the find log is git-ignored (no git on this machine)")

    rules = read(os.path.join(vault, "CLAUDE.md"))
    check("CLAUDE.md: the one recipe starts with the find tool",
          re.search(r"## Looking things up: the one recipe\n.*?\n1\. `python3 bin/find\.py ", rules, re.S)
          is not None, rules[:4000])
    detail = read(os.path.join(vault, "Rules.md"))
    check("Rules.md: the vault map has .paths/ and find.py --all",
          "| `.paths/` |" in detail and "find.py --all" in detail, detail)
    check("Readme.md: mentions the index and find.py --all",
          "find.py --all" in read(os.path.join(vault, "Readme.md")))
    check("the chat-AI guide puts find.py --all in a ChatGPT project",
          "find.py --all" in read(os.path.join(ROOT, "guides", "prompts-for-any-ai.md")))


def restates_recipe(text, kinds):
    """Lines that restate the lookup recipe or list kind folders to find notes. A heuristic."""
    alt = "|".join(re.escape(k) for k in kinds)
    rules = [
        ("lists the kind folders", re.compile(r"\b(?:ls|list|listing)\b[^.\n]{0,40}\bkind folders?\b", re.I)),
        ("runs ls on a kind folder", re.compile(r"\bls\b(?:\s+-\w+)*\s+[`'\"]?(?:%s)/" % alt)),
        ("restates a grep step of the recipe", re.compile(
            r"frontmatter grep|\bgrep\w*\s+(?:the\s+)?(?:frontmatter|file\s?names)|full[- ]text grep", re.I)),
    ]
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        why = [w for w, rx in rules if rx.search(line)]
        if len(set(re.findall(r"\b(%s)/" % alt, line))) >= 3:
            why.append("names three or more kind folders")
        if why:
            hits.append((n, "%s: %s" % (", ".join(why), line.strip())))
    return hits


def recipe_guard():
    """The lookup recipe lives once, in CLAUDE.md. Shipped skills and sections point at it."""
    sys.path.insert(0, os.path.join(ROOT, "setup"))
    import build_vault
    kinds = sorted(build_vault.KINDS)
    bad = ("1. `ls` the kind folders and match on words from the ask.\n"
           "Run `ls Clippings/` to see what came in.\n"
           "2. Frontmatter grep: `categories` for the topic, then full text grep.\n"
           "Look in `Notes/`, `References/` and `People/` for a match.\n"
           "Look it up with the one recipe in `CLAUDE.md`.\n")
    caught = [n for n, _ in restates_recipe(bad, kinds)]
    check("the recipe guard catches a skill that restates the recipe or lists kind folders",
          caught == [1, 2, 3, 4], str(restates_recipe(bad, kinds)))
    shipped = []
    for root, _, files in os.walk(os.path.join(ROOT, "template")):
        for fn in sorted(files):
            path = os.path.join(root, fn)
            if fn == "SKILL.md" or (fn.endswith(".md") and (
                    os.sep + "references" in root or root.endswith(os.path.join("optional", "sections")))):
                shipped.append(path)
    shipped.append(os.path.join(ROOT, "template", "optional", "ingest", "bin", "librarian.md"))
    found = ["%s:%d %s" % (os.path.relpath(p, ROOT), n, why) for p in shipped
             for n, why in restates_recipe(read(p), kinds)]
    check("no shipped skill or section restates the recipe or lists kind folders (%d files)" % len(shipped),
          len(shipped) > 10 and not found, "\n".join(found))
    pointers = [os.path.join("daily-loop", "dot-claude", "skills", s, "SKILL.md")
                for s in ("start-of-day", "run-brief", "end-of-day")]
    pointers.append(os.path.join("ingest", "bin", "librarian.md"))
    missing = [p for p in pointers if "the one recipe in `CLAUDE.md`"
               not in read(os.path.join(ROOT, "template", "optional", p))]
    check("skills that look notes up point at the one recipe in CLAUDE.md", not missing, ", ".join(missing))


def budgets(tmp):
    """CLAUDE.md is the index and Rules.md the detail; every file the AI loads without asking has a
    budget in bin/vault.json, a fresh vault is well under each, and lint warns (never errors) when one is over."""
    want = {"CLAUDE.md": 9000, "Rules.md": 20000, "Me.md": 5000, "Now.md": 12000, "SKILL.md": 12000}
    detail = ["## Vault map", "## Kinds in use", "## Adding a kind", "## Keeping the documentation honest",
              "## Conventions", "## Bringing things in", "## The daily loop", "| `Me.md` |", "| `Now.md` |",
              "| `People/` |", "| People | Person Template |", "`ingest.py` (bring things in)"]
    index = ["## Looking things up: the one recipe", "`Me.md` is who the owner is", "Three memory tiers",
             "`## Actions` in today's `Daily/"]
    for preset in ("personal", "work"):
        name = "budget-%s" % preset
        code, out = seed(tmp, "--preset", preset, "--dest", name, "--name", "Budget Brain", "--owner", "Sam",
                         "--date", "2026-10-14")
        check("build %s" % name, code == 0, out)
        vault = os.path.join(tmp, name)
        claude, rules = read(os.path.join(vault, "CLAUDE.md")), read(os.path.join(vault, "Rules.md"))
        check("%s: CLAUDE.md at or below 6,750 chars (%d), Rules.md at or below 15,000 (%d)"
              % (preset, len(claude), len(rules)), rules != "" and len(claude) <= 6750 and len(rules) <= 15000)
        table = json.load(open(os.path.join(vault, "bin", "vault.json"), encoding="utf-8")).get("budgets")
        sizes = {rel: len(read(os.path.join(vault, rel))) for rel in want if rel != "SKILL.md"}
        skills = os.path.join(vault, ".claude", "skills")
        sizes.update({".claude/skills/%s/SKILL.md" % s: len(read(os.path.join(skills, s, "SKILL.md")))
                      for s in os.listdir(skills)})
        over = ["%s %d of %d" % (rel, n, (table or want).get(rel, want["SKILL.md"])) for rel, n in sorted(sizes.items())
                if n > 0.75 * (table or want).get(rel, want["SKILL.md"])]
        check("%s: bin/vault.json has the budgets, every budgeted file at or below 75%% of its budget" % preset,
              table == want and len(sizes) > 8 and not over, "%s\n%s" % (table, "\n".join(over)))
        misplaced = ([d for d in detail if d not in rules or d in claude]
                     + [i for i in index if i not in claude or i in rules])
        check("%s: each filled token lands in the file its text lives in" % preset, not misplaced, str(misplaced))
        flat = " ".join(claude.split())
        check("%s: CLAUDE.md says read Rules.md before writing a note, touching a template, a Base or a skill, "
              "and before a first commit, and points at each section spliced into it" % preset,
              "`Rules.md` before you write or restructure a note, touch a template, a Base or a skill, and "
              "before a first commit" in flat and '"Bringing things in" in `Rules.md`' in flat
              and '"The daily loop" in `Rules.md`' in flat, claude[:2500])
        twice = sorted({ln.strip() for ln in claude.split("\n") if len(ln.strip()) >= 30}
                       & {ln.strip() for ln in rules.split("\n")})
        check("%s: nothing in Rules.md is repeated in CLAUDE.md" % preset, not twice, "\n".join(twice))
        check("%s: Rules.md says it is binding like CLAUDE.md" % preset, "binding like `CLAUDE.md`" in rules, rules[:600])
        code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
        check("%s: lint on a fresh vault prints no budget warning" % preset, code == 0 and "budget" not in out, out)

    vault = os.path.join(tmp, "budget-personal")
    check("Decisions.md: every auto-loaded file is an index, dated with the planting date",
          "## 2026-10-14 Every auto-loaded file is an index, never the detail" in read(os.path.join(vault, "Decisions.md")))
    now_path = os.path.join(vault, "Now.md")
    fresh = read(now_path)
    with open(now_path, "a", encoding="utf-8") as fh:
        fh.write("- Should the garden grow a page for every question I keep asking myself?\n" * 170)
    size = len(read(now_path))
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    warned = [ln for ln in out.split("\n") if ln.startswith("warn")]
    check("lint: Now.md over 12,000 chars gives one warning with its size, its budget and the compact "
          "suggestion, and exits 0",
          size > 12000 and code == 0 and len(warned) == 1 and "Now.md" in warned[0]
          and "{:,}".format(size) in warned[0] and "12,000" in warned[0] and "compact" in warned[0]
          and "9,000" in warned[0], out)
    with open(now_path, "w", encoding="utf-8") as fh:
        fh.write(fresh)

    config_path = os.path.join(vault, "bin", "vault.json")
    config = json.load(open(config_path, encoding="utf-8"))
    config.setdefault("budgets", {}).update({".claude/skills/start-of-day/SKILL.md": 30000,
                              ".claude/skills/run-brief/SKILL.md": 1000, ".claude/skills/gone/SKILL.md": 10})
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    for skill in ("start-of-day", "end-of-day"):
        with open(os.path.join(vault, ".claude", "skills", skill, "SKILL.md"), "a", encoding="utf-8") as fh:
            fh.write("\nA long aside that makes this skill too big to load every time it is used.\n" * 160)
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    named = sorted(re.findall(r"^warn\s+(\S+): .*budget", out, re.M))
    check("lint: a budget set for one skill in bin/vault.json wins for that skill only; a missing file is skipped",
          code == 0 and named == [".claude/skills/end-of-day/SKILL.md", ".claude/skills/run-brief/SKILL.md"], out)
    config["budgets"] = {"SKILL.md": "12000", "Now.md": "lots", "Me.md": None,
                         "./.claude/skills/end-of-day/SKILL.md": 30000}
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    check("lint: a hand-edited budgets table (a number as text, a word, null, a ./ path) never errors",
          code == 0 and "Traceback" not in out and "end-of-day/SKILL.md" not in out
          and "start-of-day/SKILL.md" in out, out)

    docs = {"AGENTS.md": "`Rules.md`", os.path.join("guides", "prompts-for-any-ai.md"): "`CLAUDE.md`, `Rules.md` and `Me.md`"}
    missing = [p for p, s in docs.items() if s not in " ".join(read(os.path.join(ROOT, p)).split())]
    missing += ["Readme.md (planted)"] if "`Rules.md`" not in read(os.path.join(vault, "Readme.md")) else []
    check("AGENTS.md, the chat-AI guide and the vault's Readme.md name Rules.md", not missing, ", ".join(missing))
    stale = []
    for root, _, files in os.walk(os.path.join(ROOT, "template")):
        for fn in sorted(files):
            if fn.endswith((".md", ".py")) and fn != "Rules.md":
                stale += ["%s: %s" % (os.path.relpath(os.path.join(root, fn), ROOT), s)
                          for s in sends_to_claude_md(read(os.path.join(root, fn)))]
    check("no template file sends the AI to CLAUDE.md for the detail that moved to Rules.md", not stale, "\n".join(stale))


def paths_ledger(tmp):
    """bin/paths.py: footsteps from the fixture transcripts (two config folders), the find log and git, into
    a git-ignored ledger and a one-screen report; a second run reads nothing; no read source degrades; a bed is silent."""
    tmp = os.path.realpath(tmp)  # Claude Code names a project folder after the physical path
    code, out = seed(tmp, "--preset", "work", "--dest", "paths-brain", "--name", "Paths Brain", "--owner", "Sam",
                     "--date", "2026-10-01")
    check("build a vault for the paths checks", code == 0, out)
    vault = os.path.join(tmp, "paths-brain")
    sleep, coffee = "Knowledge/Sleep comes before focus.md", "Knowledge/Coffee after noon hurts sleep.md"
    claim = 'created: 2026-10-01\nsource: ""\ncategories:\n  - "[[Sleep]]"\n'
    for rel, text in ((sleep, claim + "status: draft"), (coffee, claim + "status: verified"),
                      ("Playbooks/Wind down at night.md", claim + "status: draft"),
                      ("People/Sam.md", "categories: []\ncreated: 2026-10-01\norg: []\nrole: \nsource: "),
                      ("Categories/Sleep.md", "tags:\n  - categories"),
                      ("Daily/2026-10-10.md", "tags:\n  - daily")):
        os.makedirs(os.path.dirname(os.path.join(vault, rel)), exist_ok=True)
        with open(os.path.join(vault, rel), "w", encoding="utf-8") as fh:
            fh.write("---\n%s\n---\n\nA line of text.\n" % text)
    with open(os.path.join(vault, "Daily", "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("Daily notes are never rewritten after their day.\n")  # loaded by Claude Code on demand
    fx = os.path.join(ROOT, "tools", "fixtures", "paths")
    shutil.copy(os.path.join(fx, "find.log"), os.path.join(vault, ".paths", "find.log"))
    home = os.path.join(tmp, "paths-home")
    slug = re.sub(r"[^A-Za-z0-9]", "-", vault)
    for src, config in (("claude", ".claude"), ("claude-work", ".claude-work")):
        for root, _, files in os.walk(os.path.join(fx, src)):
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), os.path.join(fx, src))
                dest = os.path.join(home, config, "projects", slug, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(read(os.path.join(root, fn)).replace("__VAULT__", json.dumps(vault)[1:-1]))
    # Two hours east of UTC: a transcript time of 23:30 UTC falls on the next local day.
    env = dict(no_git_env(), HOME=home, TZ="XYZ-2")
    env.pop("CLAUDE_CONFIG_DIR", None)
    git = shutil.which("git")
    if git:
        def commit(message, day):
            when = "%sT12:00:00+00:00" % day
            run([git, "add", "-A"], cwd=vault, env=env)
            run([git, "-c", "user.name=Sam", "-c", "user.email=sam@example.com", "-c", "commit.gpgsign=false",
                 "commit", "-q", "--no-verify", "-m", message], cwd=vault,
                env=dict(env, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))
        run([git, "init", "-q"], cwd=vault, env=env)
        commit("Plant", "2026-10-01")
        with open(os.path.join(vault, sleep), "a", encoding="utf-8") as fh:
            fh.write("Another line.\n")
        commit("Edit a claim", "2026-10-11")

    def files():
        out = {}
        for root, dirs, names in os.walk(vault):
            dirs[:] = [d for d in dirs if d != ".git"]
            for fn in names:
                with open(os.path.join(root, fn), "rb") as fh:
                    out[os.path.relpath(os.path.join(root, fn), vault)] = fh.read()
        return out

    before = files()
    paths = [PY, os.path.join("bin", "paths.py"), "--today", "2026-10-14"]
    code, out = run(paths, cwd=vault, env=env)
    ledger_path, report_path = os.path.join(vault, ".paths", "ledger.json"), os.path.join(vault, ".paths", "report.md")
    check("paths: a refresh reads the five fixture transcripts and exits 0",
          code == 0 and "5 transcripts read" in out and os.path.exists(ledger_path), out)
    try:
        ledger = json.loads(read(ledger_path))
    except ValueError:
        ledger = {}
    steps = ledger.get("paths", {})

    def count(rel, kind):
        return sum(steps.get(rel, {}).get(kind, {}).values())

    def last(rel, kind):
        return max(steps.get(rel, {}).get(kind, {}) or [""])

    want = {"CLAUDE.md": (4, "2026-10-13"), sleep: (4, "2026-10-13"), coffee: (2, "2026-10-11"),
            "Now.md": (2, "2026-10-13"), "People/Sam.md": (2, "2026-10-12"),
            "Playbooks/Wind down at night.md": (1, "2026-10-12"), "Knowledge/": (2, "2026-10-12"),
            ".claude/skills/start-of-day/SKILL.md": (2, "2026-10-13"),
            ".claude/skills/end-of-day/SKILL.md": (1, "2026-10-11"), "Me.md": (1, "2026-10-11"),
            "Daily/CLAUDE.md": (1, "2026-10-10"), "Daily/2026-10-10.md": (1, "2026-10-13"),
            "People/": (1, "2026-10-13"), "Playbooks/": (1, "2026-10-13"), "bin/find.py": (0, "")}
    got = {rel: (count(rel, "read"), last(rel, "read")) for rel in want}
    check("paths: reads per file and their last dates match the fixtures (Read, Bash cat, grep hits and context "
          "lines, a grep too big to show whole, folder listings and Globs, a Skill call, a slash command, CLAUDE.md "
          "once per session, a nested CLAUDE.md, an @-mentioned file, a subagent with its parent; local dates; "
          "running a vault script is not reading it)",
          got == want, "\n".join("%s: got %s, want %s" % (k, got[k], want[k]) for k in want if got[k] != want[k]))
    check("paths: writes from Edit, Write and a Bash redirect; a file that does not exist now is left out",
          count("Now.md", "write") == 2 and last("Now.md", "write") == "2026-10-12"
          and count("Daily/2026-10-10.md", "write") == 1 and "Daily/2026-10-13.md" not in steps, str(steps.get("Now.md")))
    check("paths: find-log hits are footsteps of kind find",
          steps.get(sleep, {}).get("find") == {"2026-10-09": 1} and steps.get(coffee, {}).get("find") == {"2026-10-12": 1},
          "%s\n%s" % (steps.get(sleep), steps.get(coffee)))
    if git:
        check("paths: git commits are footsteps of their own kind",
              steps.get(sleep, {}).get("git") == {"2026-10-01": 1, "2026-10-11": 1}
              and count("People/Sam.md", "git") == 1, str(steps.get(sleep)))
    size = {rel: len(read(os.path.join(vault, rel))) for rel in
            ("CLAUDE.md", "Now.md", sleep, "Playbooks/Wind down at night.md", "Me.md", "Daily/CLAUDE.md",
             ".claude/skills/start-of-day/SKILL.md", ".claude/skills/end-of-day/SKILL.md")}
    start = [size["CLAUDE.md"] + size[".claude/skills/start-of-day/SKILL.md"] + size["Now.md"] + n
             for n in (size[sleep] + size["Daily/CLAUDE.md"], 0)]  # the second read the note after its write
    types = ledger.get("types", {})
    want_types = {"start-of-day": {"sessions": 2, "fixed_load": round(sum(start) / 2)},
                  "end-of-day": {"sessions": 1, "fixed_load": size["CLAUDE.md"] + size["Me.md"]
                                 + size[".claude/skills/end-of-day/SKILL.md"] + size[sleep]},
                  "misc": {"sessions": 1, "fixed_load": size["CLAUDE.md"] + size["Playbooks/Wind down at night.md"]
                           + size[sleep]}}
    check("paths: sessions typed by their first skill or slash command, else misc, with the average fixed load "
          "(files read whole before the first write or MCP call)", types == want_types,
          "got  %s\nwant %s" % (types, want_types))

    report = read(report_path)
    lines = report.split("\n")
    sections = {s.split("\n", 1)[0]: s for s in report.split("\n## ")}
    dormant = next((s for h, s in sections.items() if h.startswith("Dormant")), "")
    signs = next((s for h, s in sections.items() if h.startswith("Signposts")), "")
    drafts = next((s for h, s in sections.items() if h.startswith("Drafts wanting paving")), "")
    head = " ".join(lines[:6])
    check("paths: the report fits one screen and names its sources",
          len(lines) <= 50 and "Refreshed 2026-10-14" in head and "Last pass: never" in head
          and "~/.claude," in head and "~/.claude-work" in head and "find log" in head
          and ("git log" in head or not git), report)
    check("paths: hot files, fixed load per type, budgets and paved sections are there",
          re.search(r"^- Knowledge/Sleep comes before focus\.md: 5 reads", report, re.M) is not None
          and "| start-of-day | 2 |" in report and "| CLAUDE.md |" in report and "9,000" in report
          and "\n## Paved, waiting for your verify" in report, report)
    check("paths: dormant notes only as counts per folder, never a name",
          dormant != "" and ".md" not in dormant and re.search(r"Knowledge \d+ of \d+", dormant) is not None, dormant)
    check("paths: signposts are the queries that missed twice or more in 30 days",
          "marmalade" in signs and "jam" not in signs and "tea" not in signs, signs)
    check("paths: drafts wanting paving are the hot drafts", sleep in drafts and "Wind down" not in drafts, drafts)

    first = read(ledger_path)
    for root, _, names in os.walk(os.path.join(home)):
        for fn in names:  # same size and time, junk inside: a run that opened one would change the ledger
            path = os.path.join(root, fn)
            st = os.stat(path)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("x" * st.st_size)
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    code, out = run(paths, cwd=vault, env=env)
    check("paths: a second run with nothing new reads no transcript and leaves the ledger byte for byte",
          code == 0 and "0 transcripts read" in out and read(ledger_path) == first, out)
    after = files()
    added = sorted(set(after) - set(before))
    changed = sorted(p for p in before if after.get(p) != before[p])
    check("paths: writes only .paths/ledger.json and .paths/report.md; no note made, edited or moved",
          added == [os.path.join(".paths", "ledger.json"), os.path.join(".paths", "report.md")] and not changed,
          "added %s, changed %s" % (added, changed))
    if git:
        ignored = {p: run([git, "check-ignore", "-q", p], cwd=vault, env=env)[0] == 0
                   for p in (".paths/ledger.json", ".paths/report.md", ".paths/index.txt")}
        check("paths: the ledger and the live report are git-ignored, the index is not",
              ignored == {".paths/ledger.json": True, ".paths/report.md": True, ".paths/index.txt": False}, str(ignored))
    else:
        print("skip  paths: git checks (no git on this machine)")

    eod = read(os.path.join(vault, ".claude", "skills", "end-of-day", "SKILL.md"))
    rules = read(os.path.join(vault, "Rules.md")).split("## Conventions", 1)[-1]
    settings = read(os.path.join(vault, ".claude", "settings.json"))
    missing = [w for w in ("**Footstep**", "**Path**", "**Hot**", "**Dormant**", "**Fixed load**") if w not in rules]
    check("paths: end-of-day refreshes after lint, Rules.md conventions carry the vocabulary, settings allow it",
          "python3 bin/paths.py" in eod.split("bin/lint.py", 1)[-1] and not missing
          and "Bash(python3 bin/paths.py:*)" in settings, "missing %s" % missing)

    if git:  # a vault in a folder of a bigger repo: Claude Code runs at the repo's top, where the settings are
        nest, nest_home = os.path.join(tmp, "nest-repo"), os.path.join(tmp, "nest-home")
        os.makedirs(nest)
        run([git, "init", "-q"], cwd=nest, env=env)
        with open(os.path.join(nest, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# Acme tools\n")
        code, out = seed(tmp, "--preset", "personal", "--dest", os.path.join(nest, "acme-brain"), "--name", "Nest Brain",
                         "--owner", "Sam")
        check("build a vault in a folder of a repo", code == 0, out)
        when = "2026-10-01T12:00:00+00:00"
        run([git, "add", "-A"], cwd=nest, env=env)
        run([git, "-c", "user.name=Sam", "-c", "user.email=sam@example.com", "-c", "commit.gpgsign=false", "commit",
             "-q", "--no-verify", "-m", "Plant"], cwd=nest, env=dict(env, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))
        projects = os.path.join(nest_home, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", nest))
        os.makedirs(projects)
        for fn in sorted(os.listdir(os.path.join(fx, "nested"))):
            with open(os.path.join(projects, fn), "w", encoding="utf-8") as fh:
                fh.write(read(os.path.join(fx, "nested", fn)).replace("__REPO__", json.dumps(nest)[1:-1]))
        code, out = run(paths, cwd=os.path.join(nest, "acme-brain"), env=dict(env, HOME=nest_home))
        nested = read(os.path.join(nest, "acme-brain", ".paths", "ledger.json"))
        try:
            nested = json.loads(nested)
        except ValueError:
            nested = {}
        got = {rel: {k: v for k, v in kinds.items() if k != "git" or rel == "Now.md"}
               for rel, kinds in nested.get("paths", {}).items() if rel in ("CLAUDE.md", "Now.md") or "README" in rel}
        check("paths: a vault in a folder of a repo is measured from sessions at the repo's top: only footsteps "
              "inside the vault, its CLAUDE.md loaded, a session that never enters the vault left out",
              code == 0 and "2 transcripts read" in out and got == {
                  "CLAUDE.md": {"read": {"2026-10-13": 1}},
                  "Now.md": {"read": {"2026-10-13": 1}, "git": {"2026-10-01": 1}}}
              and nested.get("types") == {"misc": {"sessions": 1, "fixed_load": None}}
              and "(1 session)" in read(os.path.join(nest, "acme-brain", ".paths", "report.md")), "%s\n%s" % (out, got))

    code, out = seed(tmp, "--preset", "personal", "--dest", "bare-brain", "--name", "Bare Brain", "--owner", "Sam")
    bare = os.path.join(tmp, "bare-brain")
    empty = os.path.join(tmp, "empty-home")
    os.makedirs(empty)
    bare_env = dict(no_git_env(), HOME=empty, TZ="XYZ-2")
    bare_env.pop("CLAUDE_CONFIG_DIR", None)
    code, out = run([PY, os.path.join("bin", "paths.py")], cwd=bare, env=bare_env)
    report = read(os.path.join(bare, ".paths", "report.md"))
    check("paths: with no transcripts, no find log and no git the report says reads are not measured, still shows "
          "budgets, and leaves hot, dormant and fixed load out",
          code == 0 and "Traceback" not in out and "Reads not measured" in report and "## Size budgets" in report
          and "| CLAUDE.md |" in report and "## Inbound links" in report and "## Writes" in report
          and "## Hot" not in report and "## Dormant" not in report and "## Fixed load" not in report, out + report)
    os.makedirs(os.path.join(empty, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(bare))))
    open(os.path.join(bare, ".paths", "find.log"), "w").close()
    if git:
        when = "2026-10-01T12:00:00+00:00"
        run([git, "init", "-q"], cwd=bare, env=bare_env)
        run([git, "add", "-A"], cwd=bare, env=bare_env)
        run([git, "-c", "user.name=Sam", "-c", "user.email=sam@example.com", "-c", "commit.gpgsign=false", "commit",
             "-q", "--no-verify", "-m", "Plant"], cwd=bare, env=dict(bare_env, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))
    code, out = run([PY, os.path.join("bin", "paths.py"), "--today", "2026-10-14"], cwd=bare, env=bare_env)
    report = read(os.path.join(bare, ".paths", "report.md"))
    head = " ".join(report.split("\n")[:6])
    check("paths: a transcripts folder with no session and an empty find log are named as found but empty, "
          "and reads are still not measured; counts are singular when they are one",
          code == 0 and "~/.claude (found, no sessions yet)" in head and "find log (found, empty)" in head
          and "Reads not measured" in head and (not git or ("git log (1 commit)" in head
                                                            and re.search(r"^- \S.*: 1 write, last 2026-10-01$", report, re.M))),
          out + report)
    for fn in ("ledger.json", "report.md"):
        os.remove(os.path.join(bare, ".paths", fn))
    with open(os.path.join(bare, ".bed.json"), "w", encoding="utf-8") as fh:
        fh.write("{}\n")
    code, out = run([PY, os.path.join("bin", "paths.py")], cwd=bare, env=bare_env)
    check("paths: silent in a bed checkout", code == 0 and out == ""
          and not os.path.exists(os.path.join(bare, ".paths", "ledger.json")), out)


# What sends a reader to the old monthly skill, or to a monthly pass of that name, now that `tend` does
# it. The group name Prune in tend's list and the verb in plain prose ("what to prune") pass.
SENDS_TO_PRUNE = [
    re.compile(r"`pr[u]ne`"),  # the skill's name in code
    re.compile(r"skills/pr[u]ne\b"),  # its folder
    re.compile(r"[\"“]pr[u]ne[\"”]", re.I),  # say "prune"
    re.compile(r"\bpr[u]ne (skill|pass)", re.I),
    re.compile(r"\b(monthly|a|the|next) pr[u]ne\b"),  # a pass, lower case: "the Prune group" is tend's
    re.compile(r"\bpr[u]ne (is |was )?(due|monthly|once a month|every month)", re.I),
    re.compile(r"harvesting-and-pr[u]ning"),  # the guide's old name
]


def sends_to_prune(root, skip=()):
    """'path:line: match' for every text file under root that sends the reader to the old skill."""
    hits = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git" and os.path.join(dirpath, d) not in skip)
        for fn in sorted(files):
            path = os.path.join(dirpath, fn)
            if path in skip or fn.endswith((".png", ".jpg", ".pdf", ".zip")):
                continue
            try:
                lines = read(path).split("\n")
            except UnicodeDecodeError:
                continue
            hits += ["%s:%d: %s" % (os.path.relpath(path, root), n, m.group(0))
                     for n, line in enumerate(lines, 1) for p in SENDS_TO_PRUNE for m in p.finditer(line)]
    return hits


def tend_and_nudge(tmp):
    """tend ships in every vault in place of the old skill; bin/paths.py --pass saves a dated report git
    tracks, a paved note is asked about in one pass only, due mode prints one line or nothing, planting
    merges the SessionStart hook that runs it, and start-of-day and lint point at tend."""
    tmp = os.path.realpath(tmp)
    for name in ("acme-brain", "kinds-brain", "sam-work-brain", "sam-brain"):
        vault = os.path.join(tmp, name)
        skills = sorted(os.listdir(os.path.join(vault, ".claude", "skills")))
        check("%s: tend ships, the old monthly skill does not, nothing sends the reader to it" % name,
              "tend" in skills and not [s for s in skills if s.startswith("pru")] and not sends_to_prune(vault),
              "%s\n%s" % (skills, "\n".join(sends_to_prune(vault))))

    tend = read(os.path.join(tmp, "sam-brain", ".claude", "skills", "tend", "SKILL.md"))
    flat = " ".join(tend.split())
    groups = re.findall(r"^### (.+)$", tend, re.M)
    check("tend: under 9,000 chars, the seven groups in order", len(tend) < 9000 and groups == [
        "Pave", "Compact", "Split", "Signpost", "Move cold", "Prune", "Keep"], "%d chars, %s" % (len(tend), groups))
    missing = [s for s in ("bin/paths.py", ".paths/report.md", "only when `bin/ingest.py` exists",
                           "Nothing dormant is named", "about 75%", "fresh reviewer", "dropped on purpose",
                           "bin/paths.py --paved", "Paved, waiting for your verify", "one batch question",
                           "an alias, a clearer title or a missing note", "Decisions/Archive YYYY.md",
                           "Daily/YYYY/", "60 days", "one commit each", "bin/paths.py --pass", "bin/lint.py")
               if s not in flat]
    check("tend: reads only the reports, names nothing dormant, and follows the four corrections", not missing,
          "missing %s" % missing)
    sod = read(os.path.join(tmp, "sam-brain", ".claude", "skills", "start-of-day", "SKILL.md"))
    check("start-of-day runs due mode and puts its line at the top of the brief",
          "python3 bin/paths.py due" in sod and "top of the brief" in " ".join(sod.split()), sod[:2500])
    settings = json.loads(read(os.path.join(tmp, "sam-brain", ".claude", "settings.json")) or "{}")
    starts = (settings.get("hooks") or {}).get("SessionStart") or []
    check("planting adds the SessionStart hook that runs due mode on startup", starts == [
        {"matcher": "startup", "hooks": [{"type": "command", "command": "python3 bin/paths.py due --hook"}]}], str(starts))

    home = os.path.join(tmp, "tend-home")
    os.makedirs(home)
    env = dict(no_git_env(), HOME=home)
    env.pop("CLAUDE_CONFIG_DIR", None)
    code, out = seed(tmp, "--preset", "work", "--dest", "tend-brain", "--name", "Tend Brain", "--owner", "Sam",
                     "--date", "2026-09-01")
    check("build a vault for the tend checks", code == 0, out)
    vault = os.path.join(tmp, "tend-brain")
    sleep, rest = "Knowledge/Sleep comes before focus.md", "Knowledge/Rest beats caffeine.md"
    draft = '---\ncategories: []\ncreated: 2026-09-01\nsource: ""\nstatus: draft\n---\n\nA line of text.\n'
    extra = ["Knowledge/Paved %02d.md" % n for n in range(1, 13)]
    for rel in [sleep, rest] + extra:
        with open(os.path.join(vault, rel), "w", encoding="utf-8") as fh:
            fh.write(draft)
    with open(os.path.join(vault, ".paths", "find.log"), "w", encoding="utf-8") as fh:
        for day in ("2026-10-09", "2026-10-10", "2026-10-11"):
            fh.write("%s 10:00:00\tsleep\t2\t%s\t%s\n" % (day, sleep, rest))
    paths = [PY, os.path.join("bin", "paths.py")]

    def report(*args):
        code, out = run(paths + list(args), cwd=vault, env=env)
        text = read(os.path.join(vault, ".paths", "report.md"))
        parts = {s.split("\n", 1)[0].split(":")[0]: s for s in text.split("\n## ")}
        return code, out, parts.get("Drafts wanting paving", ""), parts.get("Paved, waiting for your verify", "")

    code, out, drafts, paved = report("--paved", sleep, "--today", "2026-10-14")
    ledger = json.loads(read(os.path.join(vault, ".paths", "ledger.json")) or "{}")
    check("paths --paved: recorded in the ledger with the day; off the drafts wanting paving at once",
          code == 0 and sleep in json.dumps(ledger.get("paved")) and "2026-10-14" in json.dumps(ledger.get("paved"))
          and sleep not in drafts and rest in drafts and sleep not in paved, out + drafts + paved)
    git = shutil.which("git")
    if git:
        run([git, "init", "-q"], cwd=vault, env=env)
    code, out, drafts, paved = report("--pass", "--today", "2026-10-14")
    saved = os.path.join(vault, ".paths", "reports", "2026-10-14.md")
    ledger = json.loads(read(os.path.join(vault, ".paths", "ledger.json")) or "{}")
    check("paths --pass: records the day and saves the report as .paths/reports/YYYY-MM-DD.md, whose header "
          "says when the ledger started (tend's 60-day rule)",
          code == 0 and ledger.get("last_pass") == "2026-10-14" and read(saved) != ""
          and read(saved) == read(os.path.join(vault, ".paths", "report.md")) and "Last pass: 2026-10-14" in read(saved)
          and "Ledger started 2026-10-14" in read(saved) and sleep not in paved, out + read(saved))
    if git:
        ignored = run([git, "check-ignore", "-q", ".paths/reports/2026-10-14.md"], cwd=vault, env=env)[0] == 0
        check("paths --pass: the dated report is not git-ignored", not ignored)
    code, out, drafts, paved = report("--today", "2026-10-20")
    check("paths: a paved note waits for the verify on a later day, never back among the drafts",
          sleep in paved and sleep not in drafts and rest in drafts, drafts + paved)
    code, out, drafts, paved = report("--pass", "--today", "2026-10-20")
    asked = read(os.path.join(vault, ".paths", "reports", "2026-10-20.md"))
    code, out, drafts, paved = report("--today", "2026-10-21")
    check("paths: the first pass after the pave asks once, then the note is not listed again",
          sleep in asked.split("## Paved, waiting for your verify", 1)[-1] and sleep not in paved
          and sleep not in drafts, asked + paved)
    args = []
    for rel in extra:
        args += ["--paved", rel]
    report(*(args + ["--today", "2026-10-21"]))
    tdir = os.path.join(tmp, "tend-transcripts")
    os.makedirs(tdir)
    for n in range(1, 11):
        with open(os.path.join(tdir, "s%02d.jsonl" % n), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "user", "sessionId": "s%02d" % n, "cwd": vault,
                                 "timestamp": "2026-10-21T09:00:00.000Z", "message": {
                                     "role": "user", "content": "<command-name>/kind-%02d</command-name>" % n}}) + "\n")
    code, out, drafts, paved = report("--transcripts", tdir, "--today", "2026-10-22")
    text = read(os.path.join(vault, ".paths", "report.md"))
    fixed = text.split("## Fixed load", 1)[-1].split("\n## ", 1)[0]
    check("paths: the report caps the session types at 8 and the paved list at 10, each with a count",
          len(re.findall(r"^\| kind-\d\d \|", fixed, re.M)) == 8 and "And 2 more" in fixed
          and paved.count("\n- ") == 10 and "And 2 more" in paved, fixed + paved)

    code, out = seed(tmp, "--preset", "personal", "--dest", "due-brain", "--name", "Due Brain", "--owner", "Sam")
    vault = os.path.join(tmp, "due-brain")
    ledger_path = os.path.join(vault, ".paths", "ledger.json")

    def due(today):
        return run(paths + ["due", "--today", today], cwd=vault, env=env)

    def refresh(today, *more):
        return run(paths + list(more) + ["--today", today], cwd=vault, env=env)

    def files():
        out = {}
        for root, _, names in os.walk(vault):
            for fn in names:
                with open(os.path.join(root, fn), "rb") as fh:
                    out[os.path.join(root, fn)] = fh.read()
        return out

    got = {}
    got["no ledger, nothing over budget"] = due("2026-10-01")
    refresh("2026-10-01")
    got["fresh"] = due("2026-10-01")
    got["7 days since the refresh"] = due("2026-10-08")
    before = files()
    got["8 days since the refresh"] = due("2026-10-09")
    unchanged = files() == before
    refresh("2026-10-31")
    got["no pass, first refresh 30 days back"] = due("2026-10-31")
    refresh("2026-11-01")
    got["no pass, first refresh 31 days back"] = due("2026-11-01")
    refresh("2026-11-01", "--pass")
    got["a pass today"] = due("2026-11-01")
    refresh("2026-12-01")
    got["30 days since the pass"] = due("2026-12-01")
    refresh("2026-12-02")
    got["31 days since the pass"] = due("2026-12-02")
    want = {"no ledger, nothing over budget": [], "fresh": [], "7 days since the refresh": [],
            "8 days since the refresh": ["8 days"], "no pass, first refresh 30 days back": [],
            "no pass, first refresh 31 days back": ["no pass", "31 days"], "a pass today": [],
            "30 days since the pass": [], "31 days since the pass": ["last pass", "31 days"]}
    bad = ["%s: %r" % (k, got[k][1]) for k, words in want.items() if got[k][0] != 0 or (
        got[k][1] != "" if not words else not (got[k][1].count("\n") == 1 and "tend" in got[k][1]
                                               and all(w in got[k][1] for w in words)))]
    check("paths due: nothing when fresh; one line naming tend at 8 days since the refresh, at 31 days since "
          "the pass, and with no pass 31 days after the first refresh", not bad, "\n".join(bad))
    check("paths due: reads only, writes nothing", unchanged)

    now_path = os.path.join(vault, "Now.md")
    with open(now_path, "a", encoding="utf-8") as fh:
        fh.write("- Should the garden grow a page for every question I keep asking myself?\n" * 170)
    code, out = due("2026-12-02")
    check("paths due: a file over budget is named in the same one line as the other reasons",
          code == 0 and out.count("\n") == 1 and "Now.md" in out and "last pass" in out and "tend" in out, out)
    code, lint_out = run([PY, os.path.join("bin", "lint.py")], cwd=vault, env=env)
    warned = [ln for ln in lint_out.split("\n") if "budget" in ln]
    check("lint: the budget warning names tend", code == 0 and len(warned) == 1 and "tend" in warned[0], lint_out)
    os.remove(ledger_path)
    code, out = due("2026-12-02")
    check("paths due: with no ledger, only the budget reason",
          code == 0 and out.count("\n") == 1 and "Now.md" in out and "pass" not in out and "refresh" not in out, out)
    with open(os.path.join(vault, ".bed.json"), "w", encoding="utf-8") as fh:
        fh.write("{}\n")
    code, out = due("2026-12-02")
    code2, out2 = refresh("2026-12-02")
    check("paths: due and refresh are silent in a bed checkout",
          code == 0 and out == "" and code2 == 0 and out2 == "" and not os.path.exists(ledger_path), out + out2)

    host = os.path.join(tmp, "hook-brain")
    os.makedirs(os.path.join(host, ".claude"))
    theirs = {"permissions": {"allow": ["Bash(ls:*)"]},
              "hooks": {"SessionStart": [{"matcher": "resume", "hooks": [{"type": "command", "command": "echo hi"}]}],
                        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo pre"}]}]}}
    with open(os.path.join(host, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
        json.dump(theirs, fh)
    for _ in range(2):
        code, out = seed(tmp, "--dest", "hook-brain", "--name", "Hook Brain", "--owner", "Sam")
    data = json.loads(read(os.path.join(host, ".claude", "settings.json")) or "{}")
    starts = (data.get("hooks") or {}).get("SessionStart") or []
    ours = [s for s in starts if "paths.py due" in json.dumps(s)]
    check("planting twice into a settings file with another hook and a permission merges the hook once",
          code == 0 and theirs["hooks"]["SessionStart"][0] in starts and len(ours) == 1 and len(starts) == 2
          and ours[0]["matcher"] == "startup" and data["hooks"]["PreToolUse"] == theirs["hooks"]["PreToolUse"]
          and "Bash(ls:*)" in data["permissions"]["allow"]
          and "Bash(python3 bin/paths.py:*)" in data["permissions"]["allow"], json.dumps(data, indent=1))
    with open(os.path.join(host, "CLAUDE.md"), "a", encoding="utf-8") as fh:
        fh.write("A line that makes the index too long to load every session.\n" * 200)
    code, out = run([PY, os.path.join("bin", "paths.py"), "due", "--hook"], cwd=host)
    try:
        shown = json.loads(out)
    except ValueError:
        shown = {}
    check("paths due --hook prints hook JSON whose systemMessage shows the line to the owner",
          code == 0 and "tend" in shown.get("systemMessage", "")
          and shown.get("hookSpecificOutput", {}).get("hookEventName") == "SessionStart", out)

    repo = os.path.join(tmp, "hook-repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], env=no_git_env(), capture_output=True)
    for _ in range(2):
        code, out = seed(tmp, "--dest", os.path.join("hook-repo", "café brain"), "--name", "Cafe Brain",
                         "--owner", "Sam")
    data = json.loads(read(os.path.join(repo, ".claude", "settings.json")) or "{}")
    cmds = [h.get("command", "") for s in (data.get("hooks") or {}).get("SessionStart") or [] for h in s.get("hooks", [])]
    cmds = [c for c in cmds if "paths.py" in c]
    res = subprocess.run(cmds[0] if cmds else "false", shell=True, cwd=repo, capture_output=True, text=True)
    check("a vault in a repo folder with a space and an accent gets one quoted hook that runs from the repo root",
          code == 0 and len(cmds) == 1 and res.returncode == 0, "%s\n%s%s" % (cmds, res.stdout, res.stderr))


def tend_docs():
    """The repo says desire paths have landed and names tend, and nothing in it sends the reader to the old skill."""
    hits = sends_to_prune(ROOT, skip={os.path.join(ROOT, d) for d in (".claude", "starter-vault")}
                          | {os.path.abspath(__file__)})
    check("no file in the repo sends the reader to the old monthly skill", not hits, "\n".join(hits[:40]))
    guides = os.path.join(ROOT, "guides")
    check("the harvesting guide is harvesting-and-tending.md",
          os.path.exists(os.path.join(guides, "harvesting-and-tending.md"))
          and not [g for g in os.listdir(guides) if g.startswith("harvesting-and-pr")])
    roadmap, how = read(os.path.join(ROOT, "ROADMAP.md")), read(os.path.join(ROOT, "guides", "how-it-works.md"))
    readme = read(os.path.join(ROOT, "README.md"))
    alt = re.search(r'alt="([^"]*)"', readme)
    missing = [p for p, ok in (
        ("ROADMAP.md strikes desire paths", re.search(r"~~[^~]*Desire paths[^~]*~~", roadmap)),
        ("how-it-works.md: desire paths, landed", "## Desire paths\n" in how and "`tend`" in how),
        ("README.md names tend", "`tend`" in readme),
        ("README.md alt text", alt and "coming" not in alt.group(1).lower() and "desire paths" in alt.group(1)),
        ("START-HERE.md names tend", re.search(r"\btend\b", read(os.path.join(ROOT, "START-HERE.md")))),
        ("AGENTS.md names tend", "`tend`" in read(os.path.join(ROOT, "AGENTS.md"))),
    ) if not ok]
    for svg in ("brain-garden-loop-light.svg", "brain-garden-loop-dark.svg"):
        if "coming" in read(os.path.join(ROOT, "assets", svg)).lower():
            missing.append("assets/%s says coming" % svg)
    check("the docs and the hero image say desire paths have landed and name tend", not missing, ", ".join(missing))


def sends_to_claude_md(text):
    """Sentences that name CLAUDE.md, not Rules.md, for the vault map, the kinds, adding a kind or the conventions."""
    return [s for s in re.split(r"(?<=[.;])\s+", " ".join(text.split()))
            if "CLAUDE.md" in s and "Rules.md" not in s
            and re.search(r"kinds table|vault map|convention|adding a kind|mechanics", s, re.I)]


def hubs(tmp):
    """Hub signage: Home and every topic page open with `## Start here` above their Base embeds, the topic
    pages ingest and the librarian make get it too, and lint warns (never errors) on a busy hub with no plain link."""
    code, out = seed(tmp, "--preset", "personal", "--dest", "hub-brain", "--name", "Hub Brain", "--owner", "Sam")
    check("build hub-brain", code == 0, out)
    vault = os.path.join(tmp, "hub-brain")
    plain = r"(?<!!)\[\[([^\]|#]+)"

    def put(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def notes(topic, *names):
        for n in names:
            put(os.path.join(vault, "Notes", n + ".md"),
                '---\ncategories:\n  - "[[%s]]"\ncreated: 2026-10-14\ntopics: []\n---\n%s.\n' % (topic, n))

    def hub_warnings():
        code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
        return code, [ln for ln in out.split("\n") if ln.startswith("warn") and "Start here" in ln], out

    home = read(os.path.join(vault, "Home.md"))
    start, embed = home.find("## Start here\n"), home.find("![[")
    links = re.findall(plain, home)
    check("Home: ## Start here above every embed, with Readme, CLAUDE, Rules and Decisions once each, "
          "and a line saying the main topics go there",
          0 < start < embed and sorted(links) == ["CLAUDE", "Decisions", "Readme", "Rules"]
          and all(start < home.find("[[%s]]" % ln) < embed for ln in links)
          and "main topics" in home[start:embed], home)
    tpl = read(os.path.join(vault, "Templates", "Topic Template.md"))
    check("topic template: ## Start here with no links, above the Base embed",
          0 < tpl.find("## Start here\n") < tpl.find("![[Topics.base#In this topic]]") and not re.search(plain, tpl), tpl)

    code, warned, out = hub_warnings()
    check("lint: a fresh vault has no hub warning", code == 0 and not warned, out)
    notes("Sleep", "Sleep one", "Sleep two", "Sleep three")
    put(os.path.join(vault, "Categories", "Sleep.md"), tpl)
    notes("Garden", "Garden one", "Garden two")
    put(os.path.join(vault, "Categories", "Garden.md"), tpl)
    code, warned, out = hub_warnings()
    check("lint: warns on a topic used by three notes whose page has no plain link, never on one with two, "
          "never on Home with two topic pages",
          code == 0 and len(warned) == 1 and "Categories/Sleep.md" in warned[0] and "3 notes" in warned[0], out)
    notes("Health", "Health one", "Health two", "Health three")
    put(os.path.join(vault, "Categories", "Health.md"),
        tpl.replace("## Start here\n", "## Start here\n\n- [[Health two]]\n"))
    code, warned, out = hub_warnings()
    check("lint: silent on a busy topic with a plain link; warns on Home at three topic pages when its "
          "## Start here links only root documents",
          code == 0 and len(warned) == 2 and "Categories/Sleep.md" in warned[0] and "Home.md" in warned[1], out)
    put(os.path.join(vault, "Home.md"), home.replace("## Start here\n", "## Start here\n\n- [[Health]]\n"))
    code, warned, out = hub_warnings()
    check("lint: silent on Home once its ## Start here links a topic page",
          code == 0 and len(warned) == 1 and "Categories/Sleep.md" in warned[0], out)

    src = os.path.join(tmp, "hub-old-vault")
    os.makedirs(os.path.join(src, ".obsidian"))
    put(os.path.join(src, "Plan.md"), '---\ncategories:\n  - "[[Gardening]]"\n---\nBeans.\n')
    code, out = run([PY, os.path.join("bin", "ingest.py"), "add", "--vault", src, "--map", ".=Notes"], cwd=vault)
    page = read(os.path.join(vault, "Categories", "Gardening.md"))
    check("ingest: a topic page made by a vault import has ## Start here above its embed",
          code == 0 and 0 < page.find("## Start here\n") < page.find("![[Topics.base"), out + page)

    answer = os.path.join(tmp, "hub-answer.txt")
    fm = "---\ntags:\n  - categories\n---\n"
    put(answer, "=== FILE: Categories/Rest.md\n%sWhat rest is.\n\n![[Topics.base#In this topic]]\n=== END\n\n"
        "=== FILE: Categories/Food.md\n%sWhat we eat.\n\n## Start here\n\n![[Topics.base#In this topic]]\n=== END\n\n"
        "=== FILE: Categories/Walks.md\n%sWalks.\n=== END\n\nPROPOSAL  none\n" % (fm, fm, fm))
    code, out = run([PY, os.path.join("bin", "librarian.py"), "--apply", answer], cwd=vault)
    rest, food, walks = (read(os.path.join(vault, "Categories", t + ".md")) for t in ("Rest", "Food", "Walks"))
    check("librarian: --apply gives a new topic page ## Start here above its embed, once, keeping the AI's text",
          0 < rest.find("What rest is.") < rest.find("## Start here\n") < rest.find("![[Topics.base")
          and food.count("## Start here") == 1 and walks.rstrip().endswith("## Start here")
          and "Walks." in walks, out + rest + food + walks)

    rules, readme = read(os.path.join(vault, "Rules.md")), read(os.path.join(vault, "Readme.md"))
    hubs_at = rules.find("## Hubs\n")
    section = rules[hubs_at:rules.find("\n## ", hubs_at + 1)]
    check("Rules.md: ## Hubs, right before ## Bringing things in, names the shape, 3 to 7 links, Pave and find --topic",
          0 < hubs_at and rules.find("\n## ", hubs_at + 1) == rules.find("\n## Bringing things in")
          and all(s in section for s in ("## Start here", "3 to 7", "tend", "Pave", "find.py --topic")), section)
    check("Readme.md tells people about ## Start here", "Start here" in readme, readme)
    librarian = read(os.path.join(vault, "bin", "librarian.md"))
    check("the librarian makes a topic page with an empty ## Start here, never by copying another",
          "## Start here" in librarian and "copy one" not in librarian, librarian)
    kepano = read(os.path.join(vault, ".claude", "skills", "kepano-method", "references", "divergences.md"))
    check("kepano-method lists Start here on hubs as a deliberate divergence", "## Start here" in kepano, kepano)


def upgrade(tmp):
    """build_vault.py --upgrade. Planting writes bin/seed-manifest.json, and a rerun leaves it alone. An old
    vault (planted today, then stripped of what tickets 01 to 07 added, its manifest gone and the old monthly
    skill back) gets every new file, key, line and hook, with nothing it already had changed; a seed file the
    owner edited gets a .new beside it and an unedited one is replaced; --dry-run writes nothing; a second
    upgrade is a no-op; lint passes after."""
    tmp = os.path.realpath(tmp)
    template = os.path.join(ROOT, "template", "brain")

    def sha(data):
        return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()

    def raw(path):
        with open(path, "rb") as fh:
            return fh.read()

    def put(vault, rel, data):
        path = os.path.join(vault, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data.encode("utf-8") if isinstance(data, str) else data)

    def up(vault, *more):
        return seed(tmp, "--upgrade", "--dest", vault, *more)

    code, out = run(["git", "-C", ROOT, "rev-parse", "HEAD"], env=no_git_env())
    head = out.strip() if code == 0 else "unknown"
    plant = ["--preset", "personal", "--name", "Sam's Brain", "--owner", "Sam", "--plugins", "home-button",
             "--accent", "#3a7d44", "--date", "2026-09-01", "--dest"]
    code, out = seed(tmp, *(plant + ["manifest-brain"]))
    vault = os.path.join(tmp, "manifest-brain")
    mpath = os.path.join(vault, "bin", "seed-manifest.json")
    manifest = json.loads(read(mpath) or "{}")
    files, options = manifest.get("files") or {}, manifest.get("options") or {}
    owned = ["bin/find.py", "bin/lint.py", "bin/paths.py", "bin/beds.py", "bin/ingest.py", "bin/librarian.md",
             ".claude/skills/tend/SKILL.md", ".claude/skills/tend/references/ingest-report.md",
             ".claude/skills/start-of-day/SKILL.md", "Templates/Bases/Everything.base",
             ".obsidian/snippets/vault.css", ".obsidian/plugins/home-button/main.js"]
    mine = ["CLAUDE.md", "Rules.md", "Home.md", "Now.md", "Me.md", "bin/vault.json", "Templates/Note Template.md",
            "Templates/Topic Template.md", "Templates/Bases/Notes.base", ".paths/index.txt", ".claude/settings.json"]
    wrong = ([rel for rel in owned if files.get(rel) != sha(raw(os.path.join(vault, rel)))]
             + [rel for rel in mine if rel in files])
    check("planting writes bin/seed-manifest.json: the seed's commit, the date, the options, and a sha256 for "
          "each seed-owned file, none for a root document, a template, bin/vault.json or settings",
          code == 0 and manifest.get("seed") == head and manifest.get("planted") == "2026-09-01"
          and options.get("name") == "Sam's Brain" and options.get("plugins") == ["home-button"]
          and options.get("accent") == "#3a7d44" and not wrong, "%s\n%s" % (wrong, read(mpath)[:1500]))
    before, css = read(mpath), read(os.path.join(vault, ".obsidian", "snippets", "vault.css"))
    seed(tmp, *(plant + ["manifest-brain"]))
    seed(tmp, *(plant + ["manifest-brain-2"]))
    check("a rerun of the builder leaves the manifest (and the accent) as they were, and the same options plant "
          "the same manifest byte for byte",
          before != "" and read(mpath) == before and css == read(os.path.join(vault, ".obsidian", "snippets", "vault.css"))
          and read(os.path.join(tmp, "manifest-brain-2", "bin", "seed-manifest.json")) == before)
    starter = json.loads(read(os.path.join(ROOT, "starter-vault", "bin", "seed-manifest.json")) or "{}")
    check("starter-vault/ carries its manifest, with the seed recorded as starter (no commit, so a commit never "
          "makes it stale)", starter.get("seed") == "starter" and "bin/find.py" in (starter.get("files") or {}))

    # An old vault: planted before tickets 01 to 08, simulated by stripping a fresh one (CI clones shallow).
    code, out = seed(tmp, "--preset", "personal", "--dest", "old-brain", "--name", "Old Brain", "--owner", "Sam",
                     "--date", "2026-09-01")
    vault = os.path.join(tmp, "old-brain")
    note = read(os.path.join(vault, "Templates", "Note Template.md")).replace("{{date}}", "2026-09-02")
    put(vault, "Notes/Sleep comes before focus.md", note + "Sleep first, then the hard work.\n")
    put(vault, "Daily/2026-09-02.md", read(os.path.join(vault, "Templates", "Daily Note Template.md"))
        + "- Slept nine hours.\n")
    put(vault, "Now.md", read(os.path.join(vault, "Now.md")) + "\n- Plant the beans. 2026-09-02\n")
    for rel in ("bin/seed-manifest.json", "bin/find.py", "bin/paths.py", "bin/beds.py", "Rules.md"):
        os.remove(os.path.join(vault, rel))
    shutil.rmtree(os.path.join(vault, ".paths"))
    shutil.rmtree(os.path.join(vault, ".claude", "skills", "tend"))
    put(vault, ".claude/skills/prune/SKILL.md", "---\nname: prune\n---\nThe old monthly pass.\n")
    put(vault, "bin/lint.py", raw(os.path.join(vault, "bin", "lint.py")) + b"\n# Sam: my own tweak\n")
    claude = read(os.path.join(vault, "CLAUDE.md"))
    put(vault, "CLAUDE.md", claude.replace("## Looking things up: the one recipe", "## Looking things up"))
    config = json.loads(read(os.path.join(vault, "bin", "vault.json")))
    budgets = config.pop("budgets")
    config["draft_max_days"] = 30
    put(vault, "bin/vault.json", json.dumps(config, indent=2) + "\n")
    new_lines = [".paths/find.log", ".paths/ledger.json", ".paths/report.md", "bin/never-share.txt"]
    ignore = read(os.path.join(vault, ".gitignore"))
    old_ignore = ignore.split("\n\n# The find log", 1)[0] + "\n\nsecret/\n"
    put(vault, ".gitignore", old_ignore)
    settings = json.loads(read(os.path.join(vault, ".claude", "settings.json")))
    hook = settings["hooks"].pop("SessionStart")
    settings["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "echo done"}]}]
    new_rules = [r for r in settings["permissions"]["allow"] if "find.py" in r or "paths.py" in r]
    old_rules = [r for r in settings["permissions"]["allow"] if r not in new_rules] + ["Bash(ls:*)"]
    settings["permissions"]["allow"] = old_rules
    put(vault, ".claude/settings.json", json.dumps(settings, indent=2) + "\n")
    tree = files_in(vault)

    code, out = up(vault, "--dry-run")
    check("upgrade --dry-run prints the plan and changes nothing (every file hashed before and after)",
          code == 0 and files_in(vault) == tree and "bin/find.py" in out and "Rules.md" in out
          and "nothing written" in out, out)
    code, out = up(vault)
    after = files_in(vault)
    gone = [rel for rel in ("bin/find.py", ".paths/index.txt", "bin/paths.py", "bin/beds.py", "Rules.md",
                            ".claude/skills/tend/SKILL.md", ".claude/skills/tend/references/ingest-report.md",
                            "bin/seed-manifest.json") if rel not in after]
    check("upgrade on an old vault says what it inferred, then adds the find tool, the index, the paths and beds "
          "scripts, tend, Rules.md and the manifest",
          code == 0 and not gone and "inferred" in out and "Old Brain" in out, "%s\n%s" % (gone, out))
    upgraded = json.loads(after.get("bin/vault.json", b"{}").decode("utf-8"))
    check("upgrade adds the budgets to bin/vault.json and changes no value already there",
          upgraded.get("budgets") == budgets and upgraded.get("draft_max_days") == 30
          and upgraded.get("kinds") == config["kinds"], json.dumps(upgraded))
    text = after.get(".gitignore", b"").decode("utf-8")
    check("upgrade appends the new .gitignore lines once each and keeps every line there",
          text.startswith(old_ignore) and all(text.split("\n").count(ln) == 1 for ln in new_lines), text)
    merged = json.loads(after.get(".claude/settings.json", b"{}").decode("utf-8"))
    check("upgrade merges the SessionStart hook and the new allow rules, removing and duplicating nothing",
          merged.get("hooks", {}).get("SessionStart") == hook and merged["hooks"].get("Stop") == settings["hooks"]["Stop"]
          and merged.get("permissions", {}).get("allow") == old_rules + new_rules, json.dumps(merged))
    check("upgrade keeps the old monthly skill and lists it as retired, with tend in its place",
          after.get(".claude/skills/prune/SKILL.md") == tree[".claude/skills/prune/SKILL.md"]
          and re.search(r"retired.*prune.*tend", out), out)
    check("a seed file the owner edited is left alone, the seed's version beside it as .new, and listed",
          after["bin/lint.py"] == tree["bin/lint.py"] and "bin/lint.py.new" in out
          and after.get("bin/lint.py.new") == raw(os.path.join(template, "bin", "lint.py")), out)
    check("CLAUDE.md is left alone; CLAUDE.md.new holds the seed's, and the AI is told to merge it with the owner "
          "as a numbered list",
          after["CLAUDE.md"] == tree["CLAUDE.md"] and after.get("CLAUDE.md.new") == claude.encode("utf-8")
          and "numbered list" in out, out)
    changed = [rel for rel in tree if after.get(rel) != tree[rel]
               and rel not in (".gitignore", "bin/vault.json", ".claude/settings.json")]
    check("upgrade changes no note, root document, template or other file the vault had, byte for byte",
          not changed, ", ".join(changed))
    code, lint = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    found = run([PY, os.path.join("bin", "find.py"), "sleep"], cwd=vault)[1]
    check("lint passes on the upgraded vault, and the index has its notes",
          code == 0 and "Notes/Sleep comes before focus" in found, lint + found)
    tree = files_in(vault)
    code, out = up(vault)
    check("a second upgrade is a no-op and says so", code == 0 and files_in(vault) == tree
          and "nothing to upgrade" in out, out)

    # A vault with a manifest: an unedited seed file is replaced, an edited one gets a .new.
    code, out = seed(tmp, "--preset", "work", "--dest", "kept-brain", "--name", "Kept Brain", "--owner", "Sam")
    vault = os.path.join(tmp, "kept-brain")
    manifest = json.loads(read(os.path.join(vault, "bin", "seed-manifest.json")) or "{}")
    kepano, older = ".claude/skills/kepano-method/SKILL.md", b"The kepano skill as an older seed shipped it.\n"
    put(vault, kepano, older)
    manifest["files"][kepano] = sha(older)
    find_edit = raw(os.path.join(vault, "bin", "find.py")) + b"# Sam: my own line\n"
    put(vault, "bin/find.py", find_edit)
    manifest["files"]["bin/find.py"] = sha(b"find.py as an older seed shipped it\n")
    beds_edit = raw(os.path.join(vault, "bin", "beds.py")) + b"# Sam: mine, and the seed has not changed it\n"
    put(vault, "bin/beds.py", beds_edit)
    put(vault, ".claude/skills/prune/SKILL.md", "The old monthly pass.\n")
    manifest["files"][".claude/skills/prune/SKILL.md"] = sha(b"The old monthly pass.\n")
    put(vault, "bin/seed-manifest.json", json.dumps(manifest, indent=2) + "\n")
    put(vault, "CLAUDE.md", read(os.path.join(vault, "CLAUDE.md")) + "\n## Sam's own rule\n\nShort answers.\n")
    put(vault, "Knowledge/Rest beats caffeine.md", "---\ncategories: []\ncreated: 2026-10-01\nstatus: draft\n"
        "source: \"\"\n---\nRest first.\n")
    shutil.rmtree(os.path.join(vault, "Categories"))
    os.remove(os.path.join(vault, ".paths", "index.txt"))
    tree = files_in(vault)
    code, out = up(vault)
    after = files_in(vault)
    check("an unedited seed file is replaced with the seed's current one",
          after.get(kepano) == raw(os.path.join(template, "dot-claude", "skills", "kepano-method", "SKILL.md"))
          and kepano in out, out)
    check("an edited seed file keeps the owner's bytes and gets a .new, listed; one the seed has not changed since "
          "planting gets nothing",
          after["bin/find.py"] == find_edit and after.get("bin/find.py.new") == raw(os.path.join(template, "bin", "find.py"))
          and "bin/find.py.new" in out and after["bin/beds.py"] == beds_edit and "bin/beds.py.new" not in after, out)
    check("missing folders and files come back (Categories/, .paths/index.txt); an edited CLAUDE.md gets no .new "
          "while the seed's is unchanged",
          "Categories/.gitkeep" in after and ".paths/index.txt" in after and "CLAUDE.md.new" not in after, out)
    check("a retired file the manifest lists is kept and listed",
          ".claude/skills/prune/SKILL.md" in after and re.search(r"retired.*prune", out), out)
    changed = [rel for rel in tree if after.get(rel) != tree[rel] and rel not in (kepano, "bin/seed-manifest.json")]
    recorded = json.loads(after["bin/seed-manifest.json"].decode("utf-8")).get("files", {})
    check("nothing else changed, and the manifest now records the seed's current files",
          not changed and recorded.get(kepano) == sha(after[kepano])
          and recorded.get("bin/find.py") == sha(after["bin/find.py.new"])
          and ".claude/skills/prune/SKILL.md" not in recorded, ", ".join(changed))
    tree = files_in(vault)
    code, out = up(vault)
    check("a second upgrade of that vault is a no-op too", code == 0 and files_in(vault) == tree
          and "nothing to upgrade" in out, out)

    missing = [doc for doc in ("README.md", "AGENTS.md")
               if not all(s in read(os.path.join(ROOT, doc)) for s in ("--upgrade", "--dry-run", ".new"))]
    check("README.md and AGENTS.md say how to update a vault: --upgrade, a dry run first, then the .new files",
          not missing, ", ".join(missing))


def plugins(tmp):
    """Every bundled plugin is known to the builder, documented, installs, and parses."""
    sys.path.insert(0, os.path.join(ROOT, "setup"))
    import build_vault
    have = sorted(os.listdir(os.path.join(ROOT, "template", "plugins")))
    check("KNOWN_PLUGINS is every folder in template/plugins/", sorted(build_vault.KNOWN_PLUGINS) == have,
          "%s vs %s" % (sorted(build_vault.KNOWN_PLUGINS), have))
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    missing = [p for p in have if "| `%s` |" % p not in readme]
    check("README.md documents every plugin", not missing, ", ".join(missing))
    for pid in have:
        manifest = json.load(open(os.path.join(ROOT, "template", "plugins", pid, "manifest.json"), encoding="utf-8"))
        check("plugin %s: manifest id matches its folder" % pid, manifest.get("id") == pid, str(manifest))
    code, out = seed(tmp, "--dest", "plugin-brain", "--name", "Plugin Brain", "--owner", "Sam",
                     "--plugins", ",".join(have))
    vault = os.path.join(tmp, "plugin-brain")
    listed = json.load(open(os.path.join(vault, ".obsidian", "community-plugins.json"), encoding="utf-8")) if code == 0 else []
    check("--plugins installs and enables every bundled plugin", code == 0 and listed == have and all(
        os.path.exists(os.path.join(vault, ".obsidian", "plugins", p, "main.js")) for p in have), out)
    node = shutil.which("node")
    if node:
        bad = []
        for pid in have:
            code, out = run([node, "--check", os.path.join(ROOT, "template", "plugins", pid, "main.js")])
            if code:
                bad.append("%s: %s" % (pid, out))
        check("plugins parse as JavaScript (node --check)", not bad, "\n".join(bad))
    else:
        print("skip  plugins parse as JavaScript (no node on this machine)")


def never_share():
    """No tracked file names a term from tools/never-share.txt: one term per line, `#` for comments,
    matched case-insensitively as a whole word. The list is git-ignored, so it never ships; without it
    (a fresh clone, CI) the check is skipped."""
    path = os.path.join(ROOT, "tools", "never-share.txt")
    if not os.path.exists(path):
        print("skip  never-share terms (no tools/never-share.txt on this machine)")
        return
    try:
        ignored = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", path]).returncode == 0
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True).stdout
    except OSError as exc:
        check("never-share terms", False, "git is needed to list the tracked files: %s" % exc)
        return
    check("tools/never-share.txt is git-ignored", ignored, "add it to .gitignore before anything else")
    with open(path, encoding="utf-8") as fh:
        terms = [t.strip() for t in fh if t.strip() and not t.lstrip().startswith("#")]
    if not terms:
        return
    pattern = re.compile(r"(?<!\w)(%s)(?!\w)" % "|".join(re.escape(t) for t in terms), re.I)
    hits = []
    for rel in tracked.decode("utf-8").split("\0"):
        full = os.path.join(ROOT, rel)
        if not rel or not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8") as fh:
                lines = fh.read().split("\n")
        except UnicodeDecodeError:
            continue
        hits += ["%s:%d: %s" % (rel, n, m.group(1)) for n, line in enumerate(lines, 1) for m in pattern.finditer(line)]
    check("no tracked file names a never-share term (%d terms)" % len(terms), not hits, "\n".join(hits[:40]))


def git_env(tmp):
    """No GIT_* variables, and a HOME holding only a git identity, so commits work on any machine (CI
    has no identity) and the user's own git config (signing, hooks) stays out of the checks. Bytecode
    is allowed, so a script that writes __pycache__ where it must not is caught."""
    home = os.path.join(tmp, "git-home")
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as fh:
        fh.write("[user]\n\tname = Sam\n\temail = sam@example.com\n[init]\n\tdefaultBranch = main\n"
                 "[commit]\n\tgpgsign = false\n")
    env = no_git_env()
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.update(HOME=home, XDG_CONFIG_HOME=os.path.join(home, ".config"))
    return env


def files_in(root):
    """{relative path: bytes} of every file under root, leaving out .git/ and __pycache__/."""
    out = {}
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in files:
            path = os.path.join(here, fn)
            with open(path, "rb") as fh:
                out[os.path.relpath(path, root).replace(os.sep, "/")] = fh.read()
    return out


def snapshot(root):
    """{relative path: (bytes, mtime)} of every file under root, .git/ and __pycache__/ included."""
    out = {}
    for here, _, files in os.walk(root):
        for fn in files:
            path = os.path.join(here, fn)
            with open(path, "rb") as fh:
                out[os.path.relpath(path, root)] = (fh.read(), os.stat(path).st_mtime_ns)
    return out


def beds(tmp):
    """bin/beds.py: inert with no bed; two beds get exactly their notes, stripped, with working links and
    no private comments; a bed is a vault; never-share and lint stop a push; pull brings edits back and
    reports the rest; nothing in a bed is run and no symlink is followed; clone."""
    code, out = seed(tmp, "--preset", "personal", "--dest", "beds-brain", "--name", "Beds Brain", "--owner", "Sam")
    check("build a vault for the beds checks", code == 0, out)
    vault = os.path.join(tmp, "beds-brain")
    recipes, garden = os.path.join(tmp, "beds-recipes"), os.path.join(tmp, "beds-garden")
    env = git_env(tmp)

    def beds_py(*args):
        return run([PY, os.path.join("bin", "beds.py"), *args], cwd=vault, env=env)

    def note(rel, text, root=vault):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def head(repo):
        return run([git, "-C", repo, "rev-parse", "HEAD"], env=env)[1].strip()

    docs = {"guides/sharing-a-vault.md": "bin/beds.py push", "guides/how-it-works.md": "sends vines to its beds",
            "README.md": "`beds.py`", "AGENTS.md": "beds"}
    missing = [p for p, s in docs.items() if s not in " ".join(read(os.path.join(ROOT, p)).split())]
    rules = read(os.path.join(vault, "Rules.md"))
    missing += [] if "\n## Beds\n" in rules and "bin/beds.py status" in rules and "never-share.txt" in rules else ["Rules.md"]
    missing += [] if "bin/beds.py" in read(os.path.join(vault, "Readme.md")) else ["Readme.md (planted)"]
    check("beds: the sharing guide, how it works, README, AGENTS.md and the planted Rules.md and Readme.md "
          "describe beds", not missing, ", ".join(missing))
    before = files_in(vault)
    outs = [beds_py(*a) for a in (["status"], ["push"], ["push", "--dry-run"], ["pull"], ["clone"])]
    check("beds: with no bed configured every command says so in one line and writes nothing",
          all(c == 0 and len(o.strip().split("\n")) == 1 and "no bed is configured" in o for c, o in outs)
          and files_in(vault) == before and not os.path.exists(recipes), "\n".join(o for _, o in outs))
    git = shutil.which("git")
    if not git:
        print("skip  beds: push, pull and clone (no git on this machine)")
        return
    run([git, "-C", vault, "init", "-q"], env=env)

    topic = read(os.path.join(vault, "Templates", "Topic Template.md"))
    for name in ("Recipes", "Garden", "Health"):
        note("Categories/%s.md" % name, topic)
    note("Notes/Pancakes.md", '---\ncategories:\n  - "[[Recipes]]"\n  - "[[Health]]"\ncreated: 2026-10-01\n'
         'topics: ["[[Bob Smith]]", "[[Waffles]]"]\nsource: "Acme Corp card"\n---\n\n'
         "Mix [[Flour]] with [[Eggs|two eggs]] and milk.\n\n%% Mum's card from Acme Corp, keep it home %%\n\n"
         "Serve like [[Waffles#Batter|the waffle batter]], never like [[Secret plan]]. Ask [[Bob Smith]].\n\n"
         "![[pancakes.png]]\n")
    note("Notes/Waffles.md", '---\ncategories: ["[[Recipes]]"]\ncreated: 2026-10-01\ntopics: []\n---\n\n'
         "## Batter\n\nLike [[Pancakes]].\n")
    flour = ('---\ncategories:\n  - "[[Recipes]]"\ncreated: 2026-10-01\nauthor: ["[[Jane Doe]]"]\nurl: \n'
             "rating: 5\n---\n\nPlain flour.\n")
    note("References/Flour.md", flour)
    secret_plan = ('---\ncategories:\n  - "[[Health]]"\ncreated: 2026-10-01\ntopics: []\n---\n\n'
                   "For Acme Corp only.\n\n![[private.png]]\n")
    note("Notes/Secret plan.md", secret_plan)
    note("Notes/Tomatoes.md", '---\ncategories:\n  - "[[Garden]]"\ncreated: 2026-10-01\ntopics: []\n---\n\n'
         "Stake them.\n\nWater at dawn. %%the neighbour's hose%%\n\n%%\nGrown for the Smiths.\n%%\n\n"
         "See [the log](../Daily/2026-10-10.md) and [Compost](Compost.md).\n\nWrite `[[Not a link]]` in code.\n\n"
         "```\n[[Also not a link]] %% not a comment %%\n```\n")
    compost = "---\ncategories: []\ncreated: 2026-10-01\ntopics: []\nbeds: [garden]\n---\n\nTurn it weekly.\n"
    note("Notes/Compost.md", compost)
    note("People/Bob Smith.md", '---\ncategories:\n  - "[[Recipes]]"\ncreated: 2026-10-01\norg: []\nrole: \n'
         "source: \nbeds: [recipes]\n---\n")
    note("Daily/2026-10-10.md", '---\ntags:\n  - daily\ncssclasses:\n  - workbook\ncategories:\n  - "[[Recipes]]"\n'
         "beds: [recipes]\n---\n\nMade pancakes.\n")
    note("Recipe ideas.md", '---\ncategories:\n  - "[[Recipes]]"\nbeds: [recipes, garden]\n---\n\nTry crepes.\n')
    note("Me.md", read(os.path.join(vault, "Me.md")).replace("---\n", '---\nbeds: [recipes]\ncategories:\n'
                                                                    '  - "[[Recipes]]"\n', 1))
    for img in ("pancakes.png", "private.png"):
        with open(os.path.join(vault, "Attachments", img), "wb") as fh:
            fh.write(img.encode())
    note("bin/never-share.txt", "# words that never leave this brain\nAcme Corp\nPan\n")
    bare = os.path.join(tmp, "recipes.git")
    run([git, "-C", tmp, "init", "-q", "--bare", "recipes.git"], env=env)
    config_path = os.path.join(vault, "bin", "vault.json")
    config = json.load(open(config_path, encoding="utf-8"))

    def configure(extra=(), strip=("source", "rating")):
        config["beds"] = [{"name": "recipes", "path": "../beds-recipes", "remote": bare, "topics": ["Recipes"],
                           "strip": list(strip)},
                          {"name": "garden", "path": "../beds-garden", "topics": ["Garden"], "strip": []}] + list(extra)
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2)

    configure()
    code, out = run([PY, os.path.join("bin", "lint.py")], cwd=vault)
    check("beds: the fixture brain passes its lint", code == 0, out)

    configure([{"name": "inside", "path": "Shared", "topics": ["Garden"]}])
    code, out = beds_py("push")
    check("beds: a bed whose path is inside the vault is refused, and nothing is pushed",
          code != 0 and "inside" in out and not os.path.exists(os.path.join(vault, "Shared"))
          and not os.path.exists(recipes), out)
    configure()

    before = snapshot(vault)
    code, out = beds_py("push", "--dry-run")
    check("beds: push --dry-run lists what would go and writes nothing",
          code == 0 and "+ Notes/Pancakes.md" in out and "+ Notes/Compost.md" in out and snapshot(vault) == before
          and not os.path.exists(recipes) and not os.path.exists(garden), out)
    waffles = read(os.path.join(vault, "Notes", "Waffles.md"))
    note("Notes/Waffles.md", waffles.replace("Like [[Pancakes]].", "Like [[Pancakes]], a tip from acme corp."))
    code, out = beds_py("push")
    check("beds: a never-share word in a sent note stops the push, naming the note and the word; one in a "
          "stripped property, a %% comment, a note that stays home or inside a longer word does not",
          code != 0 and "Notes/Waffles.md" in out and "Acme Corp" in out and "Pancakes" not in out
          and "Secret plan" not in out and not os.path.exists(recipes) and not os.path.exists(garden), out)
    note("Notes/Waffles.md", waffles)
    note("Notes/Acme Corp fritters.md", '---\ncategories:\n  - "[[Recipes]]"\ncreated: 2026-10-01\ntopics: []\n---\n')
    with open(os.path.join(vault, "Attachments", "acme corp logo.png"), "wb") as fh:
        fh.write(b"logo")
    note("References/Flour.md", flour.replace("Plain flour.", "Plain flour.\n\n![[acme corp logo.png]]"))
    note("Notes/Compost.md", compost.replace("topics: []", 'topics: ["[[Acme Corp]]"]'))
    code, out = beds_py("push")
    refused = sorted(re.findall(r"REFUSED  (.+?) holds", out))
    check("beds: never-share also stops a word in a note's title (and the topic page listing it), an "
          "attachment's name or a property",
          code != 0 and refused == ["Attachments/acme corp logo.png", "Categories/Recipes.md",
                                    "Notes/Acme Corp fritters.md", "Notes/Compost.md"]
          and not os.path.exists(recipes) and not os.path.exists(garden), out)
    os.remove(os.path.join(vault, "Notes", "Acme Corp fritters.md"))
    os.remove(os.path.join(vault, "Attachments", "acme corp logo.png"))
    note("References/Flour.md", flour)
    note("Notes/Compost.md", compost)
    note("Notes/Broken.md", '---\ncategories:\n  - "[[Nowhere]]"\ncreated: 2026-10-01\ntopics: []\n---\n')
    code, out = beds_py("push")
    check("beds: push refuses while the brain's lint has errors", code != 0 and "lint" in out and "Nowhere" in out
          and not os.path.exists(recipes), out)
    os.remove(os.path.join(vault, "Notes", "Broken.md"))

    code, out = beds_py("push")
    check("beds: push sends to both beds", code == 0, out)
    shared = ("bin/", "Templates/", ".obsidian/", ".paths/")
    sent = {b: sorted(p for p in files_in(b) if not p.startswith(shared)
                      and p not in ("CLAUDE.md", "Rules.md", ".gitignore", ".bed.json")) for b in (recipes, garden)}
    check("beds: each bed gets exactly the notes tagged for it or in its topics and their attachments, never a "
          "daily note, a person or a root document",
          sent[recipes] == ["Attachments/pancakes.png", "Categories/Recipes.md", "Notes/Pancakes.md",
                            "Notes/Waffles.md", "References/Flour.md"]
          and sent[garden] == ["Categories/Garden.md", "Notes/Compost.md", "Notes/Tomatoes.md"], str(sent))
    pan = read(os.path.join(recipes, "Notes", "Pancakes.md"))
    check("beds: a sent note loses the stripped properties, `beds` and the topics its bed does not have",
          "source:" not in pan and "Health" not in pan and '  - "[[Recipes]]"' in pan
          and "rating" not in read(os.path.join(recipes, "References", "Flour.md"))
          and "rating" not in read(os.path.join(recipes, "Templates", "Reference Template.md"))
          and "beds:" not in read(os.path.join(garden, "Notes", "Compost.md")), pan)
    check("beds: links into the bed become relative Markdown links, links out of it plain text",
          "Mix [Flour](../References/Flour.md) with two eggs and milk." in pan
          and "Serve like [the waffle batter](Waffles.md#Batter), never like Secret plan. Ask Bob Smith." in pan
          and "![](../Attachments/pancakes.png)" in pan and "[[" not in pan.split("\n---", 1)[1], pan)
    bed_flour = read(os.path.join(recipes, "References", "Flour.md"))
    check("beds: links in every other property go the same way (in the bed relative, out of it plain text)",
          'topics: ["Bob Smith", "[Waffles](Waffles.md)"]' in pan and 'author: ["Jane Doe"]' in bed_flour
          and "[[Bob" not in pan and "[[Jane" not in bed_flour, pan + bed_flour)
    tomatoes = read(os.path.join(garden, "Notes", "Tomatoes.md"))
    check("beds: %% comments stay home, Markdown links out of the bed become plain text, code is left alone",
          "Mum's card" not in pan and "neighbour" not in tomatoes and "Smiths" not in tomatoes
          and "\nWater at dawn.\n" in tomatoes and "\nSee the log and [Compost](Compost.md).\n" in tomatoes
          and "Write `[[Not a link]]` in code." in tomatoes
          and "```\n[[Also not a link]] %% not a comment %%\n```" in tomatoes, tomatoes)
    broken = []
    for bed in (recipes, garden):
        for rel, data in files_in(bed).items():
            if rel.endswith(".md") and not rel.startswith(shared):
                for href in re.findall(r"\]\(([^)\s]+)\)", data.decode("utf-8")):
                    target = os.path.join(bed, os.path.dirname(rel), unquote(href.split("#")[0]))
                    if not os.path.exists(target):
                        broken.append("%s: %s" % (rel, href))
    check("beds: every link in a bed resolves to a file in the bed", not broken, "\n".join(broken))
    page = read(os.path.join(recipes, "Categories", "Recipes.md"))
    listed = page.split("<!-- beds:list:start -->")[-1].split("<!-- beds:list:end -->")[0]
    check("beds: each topic page in a bed lists its notes between markers",
          "<!-- beds:list:end -->" in page and all(item in listed for item in (
              "- [Flour](../References/Flour.md)", "- [Pancakes](../Notes/Pancakes.md)",
              "- [Waffles](../Notes/Waffles.md)")) and "Bob" not in listed
          and "- [Tomatoes](../Notes/Tomatoes.md)" in read(os.path.join(garden, "Categories", "Garden.md")), page)
    results = [run([PY, os.path.join(bed, "bin", "lint.py")], cwd=bed) if os.path.isdir(bed) else (1, "no bed")
               for bed in (recipes, garden)]
    code, found = run([PY, os.path.join(recipes, "bin", "find.py"), "--topic", "Recipes"],
                      cwd=recipes) if os.path.isdir(recipes) else (1, "no bed")
    marker = json.loads(read(os.path.join(recipes, ".bed.json")) or "{}")
    check("beds: a bed opens as a vault (CLAUDE.md, Rules.md, templates, .bed.json): its lint passes and its "
          "find tool works",
          all(c == 0 and " 0 errors" in o for c, o in results) and marker == {"bed": "recipes"}
          and "edits made here back" in read(os.path.join(recipes, "CLAUDE.md"))
          and read(os.path.join(recipes, "Rules.md")) == read(os.path.join(vault, "Rules.md"))
          and found.split("\n")[:3] == ["Notes/Pancakes :: :: Recipes ::", "Notes/Waffles :: :: Recipes ::",
                                        "References/Flour :: :: Recipes ::"],
          "\n".join(o for _, o in results) + found)
    code, logged = run([git, "-C", vault, "log", "--format=%s", "--", ".paths/beds/recipes.json"], env=env)
    code2, dirty = run([git, "-C", vault, "status", "--porcelain", "--", ".paths/beds"], env=env)
    check("beds: push commits the sync state in the brain when the brain is a git repository",
          code == 0 and "beds: recipes sync state" in logged and code2 == 0 and dirty.strip() == "", logged + dirty)
    first = head(recipes)
    code, out = beds_py("push")
    check("beds: push commits in the bed and pushes to its remote; a second push with nothing new commits nothing",
          code == 0 and first and head(bare) == first and head(recipes) == first, out)

    note("Notes/Crepes.md", '---\ncategories:\n  - "[[Recipes]]"\ncreated: 2026-10-01\ntopics: []\n---\n')
    brain_before, bed_before = snapshot(vault), snapshot(recipes)
    code, out = beds_py("push", "recipes", "--dry-run")
    check("beds: --dry-run writes nothing anywhere: not the brain's stale index, not a fetch in the bed",
          code == 0 and "+ Notes/Crepes.md" in out and snapshot(vault) == brain_before
          and snapshot(recipes) == bed_before, out)
    os.remove(os.path.join(vault, "Notes", "Crepes.md"))

    os.rename(bare, bare + "-away")
    note("References/Flour.md", flour.replace("Plain flour.", "Plain flour, sifted."))
    code, out = beds_py("push", "recipes")
    state = json.loads(read(os.path.join(vault, ".paths", "beds", "recipes.json")) or "{}")
    offline_ok = code != 0 and "next push" in out and state.get("commit") == head(recipes) != first
    os.rename(bare + "-away", bare)
    code, out2 = beds_py("push", "recipes")
    check("beds: a push that cannot reach the remote still saves the sync state, and the next push sends it",
          offline_ok and code == 0 and head(bare) == head(recipes), out + out2)
    code, out = beds_py("status")
    check("beds: status names each bed", code == 0 and "beds: recipes" in out and "beds: garden" in out, out)

    collab = os.path.join(tmp, "collab-recipes")
    ran = os.path.join(tmp, "bed-code-ran")
    run([git, "-C", tmp, "clone", "-q", bare, "collab-recipes"], env=env)
    pan = read(os.path.join(collab, "Notes", "Pancakes.md"))
    note("Notes/Pancakes.md", pan.replace("two eggs and milk.", "two eggs and oat milk.").replace(
        "![](../Attachments", "Rest the batter for [Waffles](Waffles.md) ten minutes.\n\n![](../Attachments"), collab)
    note("Notes/Waffles.md", read(os.path.join(collab, "Notes", "Waffles.md")).replace(
        "Like [Pancakes](Pancakes.md).", "Like [Pancakes](Pancakes.md), but crisper."), collab)
    os.remove(os.path.join(collab, "References", "Flour.md"))
    note("Notes/Syrup.md", '---\ncategories:\n  - "[[Recipes]]"\ncreated: 2026-10-12\ntopics: []\n---\n\nMaple.\n',
         collab)
    note("bin/csv.py", "open(%r, 'w').write('ran')\n" % ran, collab)
    for args in (["add", "-A"], ["commit", "-q", "-m", "Edits from a friend"], ["push", "-q"]):
        run([git, "-C", collab] + args, env=env)
    note("Notes/Waffles.md", waffles.replace("Like [[Pancakes]].", "Like [[Pancakes]], only thinner."))
    before = files_in(recipes)
    code, out = beds_py("push", "recipes")
    check("beds: push refuses while the bed has commits not yet pulled",
          code != 0 and "not yet pulled" in out and files_in(recipes) == before, out)
    note("Notes/Secret plan.md", secret_plan.replace("topics: []", "topics: []\nbeds: [recipes]"))
    configure(strip=["rating"])
    code, out = beds_py("pull", "recipes")
    brain_pan, brain_waffles = read(os.path.join(vault, "Notes", "Pancakes.md")), read(os.path.join(vault, "Notes", "Waffles.md"))
    check("beds: pull brings a bed edit back, dropped topics put back, links as [[links]]",
          code == 0 and "Mix [[Flour]] with two eggs and oat milk." in brain_pan
          and "Rest the batter for [[Waffles]] ten minutes." in brain_pan and "![[pancakes.png]]" in brain_pan
          and '  - "[[Health]]"' in brain_pan and "](" not in brain_pan, out + brain_pan)
    check("beds: pull renders the brain's side as sent at the last sync, so an untouched line keeps its "
          "[[links]] after the bed's set of notes changed",
          "Serve like [[Waffles#Batter|the waffle batter]], never like [[Secret plan]]. Ask [[Bob Smith]]." in brain_pan,
          brain_pan)
    check("beds: pull keeps a property stripped at the last sync after `strip` changed, and never deletes "
          "one the bed's copy lacks", 'source: "Acme Corp card"' in brain_pan, brain_pan)
    check("beds: pull puts property links back as [[links]] and keeps the brain's %% comments",
          'topics: ["[[Bob Smith]]", "[[Waffles]]"]' in brain_pan
          and "%% Mum's card from Acme Corp, keep it home %%" in brain_pan, brain_pan)
    note("Notes/Secret plan.md", secret_plan)
    configure()
    check("beds: an edit on both sides is reported as a conflict and applied to neither",
          re.search(r"CONFLICT\s+Notes/Waffles\.md", out) is not None and "only thinner" in brain_waffles
          and "crisper" not in brain_waffles and "crisper" in read(os.path.join(recipes, "Notes", "Waffles.md")), out)
    check("beds: a deletion and a new note in the bed are reported, not applied",
          re.search(r"DELETED\s+References/Flour\.md", out) is not None
          and re.search(r"NEW\s+Notes/Syrup\.md", out) is not None
          and os.path.exists(os.path.join(vault, "References", "Flour.md"))
          and not os.path.exists(os.path.join(vault, "Notes", "Syrup.md")), out)
    code, out = beds_py("push", "recipes")
    code2, out2 = beds_py("push", "recipes", "--force")
    check("beds: push refuses over the reported conflict and deletion until forced, and --force sends the brain's",
          code != 0 and "Notes/Waffles.md" in out and "References/Flour.md" in out and code2 == 0
          and "only thinner" in read(os.path.join(recipes, "Notes", "Waffles.md"))
          and os.path.exists(os.path.join(recipes, "References", "Flour.md")) and head(bare) == head(recipes),
          out + out2)
    check("beds: push never runs code from the bed, and names a file in its bin/ that did not come from the brain",
          not os.path.exists(ran) and "bin/csv.py" in out2, out2)

    secret = os.path.join(tmp, "secret.txt")
    with open(secret, "w", encoding="utf-8") as fh:
        fh.write("the owner's private file\n")
    run([git, "-C", collab, "pull", "-q"], env=env)
    os.remove(os.path.join(collab, "Notes", "Waffles.md"))
    try:
        os.symlink(secret, os.path.join(collab, "Notes", "Waffles.md"))
        with open(os.path.join(tmp, "outside.md"), "w", encoding="utf-8") as fh:
            fh.write('---\ncategories:\n  - "[[Garden]]"\ncreated: 2026-10-01\ntopics: []\n---\n\nOutside.\n')
        os.symlink(os.path.join(tmp, "outside.md"), os.path.join(vault, "Notes", "Outside.md"))
    except (OSError, NotImplementedError):
        print("skip  beds: symlinks are never followed (no symlinks on this machine)")
    else:
        for args in (["add", "-A"], ["commit", "-q", "-m", "A link"], ["push", "-q"]):
            run([git, "-C", collab] + args, env=env)
        brain_waffles = read(os.path.join(vault, "Notes", "Waffles.md"))
        code, out = beds_py("pull", "recipes")
        code2, out2 = beds_py("push", "recipes", "--force")
        code3, out3 = beds_py("push", "garden", "--dry-run")
        check("beds: a symlink in the bed stops pull and push, which neither read nor write through it; one in "
              "the brain is skipped and named",
              code != 0 and "symlink" in out and "Notes/Waffles.md" in out and code2 != 0 and "symlink" in out2
              and read(os.path.join(vault, "Notes", "Waffles.md")) == brain_waffles
              and read(secret) == "the owner's private file\n"
              and "skipped Notes/Outside.md" in out3 and "+ Notes/Outside.md" not in out3,
              out + out2 + out3)
        os.remove(os.path.join(vault, "Notes", "Outside.md"))

    note("Notes/Compost.md", read(os.path.join(garden, "Notes", "Compost.md")).replace(
        "Turn it weekly.", "Turn it weekly, and water it."), garden)
    run([git, "-C", garden, "commit", "-q", "-am", "Water it"], env=env)
    code, out = beds_py("push", "garden")
    before = files_in(vault)
    code2, out2 = beds_py("pull", "garden", "--dry-run")
    check("beds: a commit in a bed with no remote stops the push; pull --dry-run reports it and writes nothing",
          code != 0 and "not yet pulled" in out and code2 == 0 and "Notes/Compost.md" in out2
          and files_in(vault) == before, out + out2)
    code, out = beds_py("pull", "garden")
    pulled = read(os.path.join(vault, "Notes", "Compost.md"))
    code2, out2 = beds_py("push", "garden")
    check("beds: pull applies it, `beds` put back, and the next push goes through",
          code == 0 and "water it" in pulled and "beds: [garden]" in pulled and code2 == 0, out + pulled + out2)
    os.remove(os.path.join(vault, ".paths", "beds", "garden.json"))
    code, out = beds_py("push", "garden")
    code2, out2 = beds_py("push", "garden", "--force")
    check("beds: with no sync state, push refuses a bed that has commits unless forced",
          code != 0 and "no sync state" in out and code2 == 0
          and os.path.exists(os.path.join(vault, ".paths", "beds", "garden.json")), out + out2)

    shutil.move(recipes, recipes + "-old")
    code, out = beds_py("clone")
    check("beds: clone fetches a configured bed from its remote (a local bare repo) as a sibling",
          code == 0 and read(os.path.join(recipes, ".bed.json")) and os.path.exists(os.path.join(recipes, "Notes", "Pancakes.md"))
          and "garden: no remote" in out, out)
    ignored = {p: run([git, "-C", vault, "check-ignore", "-q", p], env=env)[0] == 0
               for p in ("bin/never-share.txt", ".paths/beds/recipes.json")}
    check("beds: bin/never-share.txt is git-ignored, the sync state in .paths/beds/ is not",
          ignored == {"bin/never-share.txt": True, ".paths/beds/recipes.json": False}, str(ignored))


def main():
    for root, _, files in os.walk(ROOT):
        if "/.git" in root:
            continue
        for fn in files:
            if fn.endswith(".py"):
                try:
                    with open(os.path.join(root, fn), encoding="utf-8") as fh:
                        compile(fh.read(), fn, "exec")
                except SyntaxError as exc:
                    check("compiles: %s" % os.path.relpath(os.path.join(root, fn), ROOT), False, str(exc))
    with tempfile.TemporaryDirectory() as tmp:
        cases = [
            ("default (personal)", ["--dest", "acme-brain", "--name", "Acme Brain", "--owner", "Sam"],
             [PY, "bin/lint.py"]),
            ("custom kinds", ["--kinds", "Notes,People", "--dest", "kinds-brain", "--name", "Kinds Brain",
                              "--owner", "Sam"], [PY, "bin/lint.py"]),
            ("preset work", ["--preset", "work", "--dest", "sam-work-brain", "--name", "Sam's Work Brain", "--owner", "Sam"],
             [PY, "bin/lint.py"]),
            ("preset personal", ["--preset", "personal", "--dest", "sam-brain", "--name", "Sam's Brain", "--owner", "Sam"],
             [PY, "bin/lint.py"]),
        ]
        for label, args, cmd in cases:
            code, out = seed(tmp, *args)
            vault = os.path.join(tmp, args[args.index("--dest") + 1])
            check("build %s" % label, code == 0, out)
            planted = os.path.exists(os.path.join(vault, ".paths", "index.txt"))
            code, out = run([PY, os.path.join("bin", "find.py"), "--all"], cwd=vault)
            check("%s plants bin/find.py and its index" % label, planted and code == 0
                  and out == read(os.path.join(vault, ".paths", "index.txt")), out)
            code, out = run(cmd, cwd=vault)
            check("%s passes its own check" % label, code == 0, out)
            leftover = []
            for root, _, files in os.walk(vault):
                for fn in files:
                    with open(os.path.join(root, fn), encoding="utf-8", errors="ignore") as fh:
                        if re.search(r"@@[A-Z_]+@@", fh.read()):
                            leftover.append(fn)
            check("%s has no unfilled @@TOKENS@@" % label, not leftover, ", ".join(leftover))
        fx = os.path.join(tmp, "fx")
        fixtures(fx)
        ingest_round_trip(os.path.join(tmp, "sam-brain"), fx)
        prune_round_trip(os.path.join(tmp, "sam-work-brain"), fx)
        daily_loop(tmp)
        find_tool(tmp)
        vault_import(tmp)
        budgets(tmp)
        hubs(tmp)
        paths_ledger(tmp)
        beds(tmp)
        tend_and_nudge(tmp)
        plugins(tmp)
        upgrade(tmp)
    recipe_guard()
    tend_docs()

    code, out = run([PY, os.path.join(ROOT, "tools", "build_starter.py"), "--check"])
    check("starter-vault/ matches the seed", code == 0, out)
    dashes = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "starter-vault", "references")]
        for fn in files:
            if fn.endswith((".md", ".sh", ".ps1", ".json")):
                path = os.path.join(root, fn)
                if re.search("[–—]", open(path, encoding="utf-8").read()):
                    dashes.append(os.path.relpath(path, ROOT))
    check("no en or em dashes in the repo's own docs", not dashes, ", ".join(dashes))
    never_share()
    print("\n%s" % ("all checks passed" if not failed else "%d failed: %s" % (len(failed), "; ".join(failed))))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
