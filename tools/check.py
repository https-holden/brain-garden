#!/usr/bin/env python3
"""Test the seed end to end. Standard library only, no network, no AI.

    python3 tools/check.py

Builds both presets and a custom vault into a temporary folder, runs each
vault's own check, pushes sample files through bin/ingest.py, round-trips a
fake chat answer through bin/librarian.py --apply, checks the daily loop's
reply cards and action log, checks the CLAUDE.md and Rules.md split and the
size budgets lint warns on, installs every bundled plugin, checks
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
    image in a subfolder, a name that clashes, a templates folder, a Base, a Canvas, rule files."""
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
    put("_templates/Meeting.md", "---\ncreated: {{date}}\n---\n")
    put("Board.base", "views: []\n")
    put("Map.canvas", "{}")
    put("CLAUDE.md", "Answer in one line.\n")
    put("Home.md", "Start at [[Plan]].\n")
    put("Projects/Plan.md", "---\ncategories:\n  - \"[[Gardening]]\"\ncreated: 2021-03-04\naliases:\n  - Garden plan\n"
        "tags:\n  - green\nrating: 4\n---\n# Plan\n\nBack to [[Home]], [[Home|the start]] and [[Home#Top]].\n\n"
        "![[x.png]]\n\n![[Ideas]]\n\nSee [[Old]] too.\n")
    put("Projects/Ideas.md", "Ideas for [[Projects/Plan|the plan]].\n", mtime=1577923200)  # 2020-01-02
    put("Reading/Article.md", "---\ncategories: [\"[[Reading list]]\"]\nurl: https://example.com/a\n"
        "author: \"[[Jane Doe]]\"\n---\nSomeone else's words \u2013 with a dash.\n")
    put("Journal/2024-05-01.md", "Planted beans, see [[Plan]].\n")
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
    ing = [PY, os.path.join(vault, "bin", "ingest.py"), "add"]
    maps = ["--map", ".=Notes", "--map", "Projects=Notes", "--map", "Reading=Clippings", "--map", "dates=Daily"]

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
    code, out = run(ing + ["--vault", src], cwd=vault)
    listed = [ln for ln in out.split("\n") if re.match(r"\s*\d+\. ", ln)]
    want = [r"\(root\).*1 note.*Notes", r"Projects.*2 notes.*Notes", r"Reading.*1 note", r"Archive.*1 note",
            r"dates.*1 note.*Daily"]
    missing = [w for w in want if not any(re.search(w, ln) for ln in listed)]
    check("import: no mapping proposes one, numbered with counts, and writes nothing",
          code == 0 and not missing and not any("_templates" in ln or "Journal" in ln for ln in listed)
          and '--map "Projects=Notes"' in out and '--map "dates=Daily"' in out and tree() == before,
          "missing %s\n%s" % (missing, out))

    code, out = run(ing + ["--vault", src, "--dry-run"] + maps, cwd=vault)
    check("import: --dry-run prints the plan and writes nothing",
          code == 0 and out.count("ADDED") == 5 and tree() == before, out)
    code, sample = run(ing + ["--vault", src, "--sample", "2", "--via", "Old vault"] + maps, cwd=vault)
    check("import: --sample 2 imports two notes and stops",
          code == 0 and sample.count("ADDED") == 2 and read("Notes/Home (2).md") and read("Daily/2024-05-01.md")
          and not read("Notes/Plan.md"), sample)
    check("import: --via stamps Sources.md", "| Old vault |" in read("Sources.md"), read("Sources.md"))
    code, out = run(ing + ["--vault", src, "--via", "Old vault"] + maps, cwd=vault)
    check("import: the full run brings the rest and skips the sample",
          code == 0 and out.count("ADDED") == 3 and "2 notes imported before" in out
          and not os.path.exists(os.path.join(vault, "Notes", "Home (3).md")), out)

    if os.path.exists(os.path.join(vault, "bin", "find.py")):
        index = read(".paths/index.txt")
        check("import: the import leaves the index listing its notes",
              all(n in index for n in ("Notes/Plan", "Notes/Ideas", "Notes/Home (2)", "Clippings/Article")), index)
    else:
        print("skip  import: the import leaves the index listing its notes (no bin/find.py yet)")
    plan, ideas, home = read("Notes/Plan.md"), read("Notes/Ideas.md"), read("Notes/Home (2).md")
    clip = read("Clippings/Article.md")
    check("import: notes land in their mapped kinds, the dated one in Daily/",
          plan and ideas and home and clip and "beans" in read("Daily/2024-05-01.md"), out)
    check("import: categories, created, aliases, tags and other properties kept",
          '- "[[Gardening]]"' in plan and "created: 2021-03-04" in plan and "Garden plan" in plan
          and "- green" in plan and "rating: 4" in plan and "created: 2020-01-02" in ideas
          and "https://example.com/a" in clip and "[[Jane Doe]]" in clip and "via: \"Old vault\"" in plan, plan + ideas + clip)
    check("import: missing topic pages made from the topic template",
          read("Categories/Gardening.md") == read("Templates/Topic Template.md")
          and read("Categories/Reading list.md"), out)
    check("import: the embedded image is copied flat, renamed on a clash, and the embed rewritten",
          "![[x (2).png]]" in plan and os.path.exists(os.path.join(vault, "Attachments", "x (2).png"))
          and read("Attachments/x.png") == "already here", plan)
    check("import: the clashing note is renamed and every link to it rewritten",
          "[[Home (2)]], [[Home (2)|the start]] and [[Home (2)#Top]]" in plan and "RENAMED  Home" in sample
          and "[[Plan|the plan]]" in ideas and "![[Ideas]]" in plan and "[[Old]]" in plan, sample + plan + ideas)
    check("import: dashes replaced in imported text", "\u2013" not in clip and "words - with" in clip, clip)
    names = " ".join(tree()[0])
    check("import: nothing comes in from the skipped places",
          not any(n in names for n in ("Gone", "Meeting", "Board.base", "Map.canvas", "Old.md"))
          and "Answer in one line" not in "".join(read(p) for p in tree()[0] if p.endswith(".md")), names)
    summary = ["SKIPPED  .obsidian/ (2 files)", "SKIPPED  .trash/ (1 file)", "SKIPPED  _templates/",
               "SKIPPED  1 .base file", "SKIPPED  1 .canvas file", "SKIPPED  Archive/ (1 note): not mapped",
               "CLAUDE.md", "Decisions.md", "Me.md"]
    missing = [s for s in summary if s not in out]
    check("import: the summary counts what was skipped and names the old rule files", not missing,
          "missing %s\n%s" % (missing, out))
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


def sends_to_claude_md(text):
    """Sentences that name CLAUDE.md, not Rules.md, for the vault map, the kinds, adding a kind or the conventions."""
    return [s for s in re.split(r"(?<=[.;])\s+", " ".join(text.split()))
            if "CLAUDE.md" in s and "Rules.md" not in s
            and re.search(r"kinds table|vault map|convention|adding a kind|mechanics", s, re.I)]


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
        plugins(tmp)
    recipe_guard()

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
