#!/usr/bin/env python3
"""Test the seed end to end. Standard library only, no network, no AI.

    python3 tools/check.py

Builds both presets and a custom vault into a temporary folder, runs each
vault's own check, pushes sample files through bin/ingest.py, round-trips a
fake chat answer through bin/librarian.py --apply, checks the daily loop's
reply cards and action log, installs every bundled plugin, checks
starter-vault/ is what the seed makes today, scans this repo's own docs
for en and em dashes, and fails when a tracked file names a term from the
git-ignored tools/never-share.txt. Prints one line per check and exits 1 if
any failed. The pre-commit hook in .githooks/ and the CI job run it.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "setup", "build_vault.py")
PY = sys.executable
failed = []


def check(label, ok, detail=""):
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, ("\n      " + detail.strip().replace("\n", "\n      ")) if not ok and detail else ""))
    if not ok:
        failed.append(label)


def run(args, cwd=None):
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def seed(tmp, *args):
    return run([PY, SEED, *args], cwd=tmp)


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
    code, out = run(ing + ["add", "--mine", os.path.join(fx, "essay.docx")], cwd=vault)
    check("ingest: --mine", code == 0 and "ADDED" in out, out)
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
    check("librarian: --paste prints the job", code == 0 and "=== FILE: Clippings/A book.md" in out, out[-500:])
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
        vault_import(tmp)
        plugins(tmp)

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
