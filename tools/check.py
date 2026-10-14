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
    check("CLAUDE.md: the vault map has .paths/ and find.py --all",
          "| `.paths/` |" in rules and "find.py --all" in rules, rules)
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
