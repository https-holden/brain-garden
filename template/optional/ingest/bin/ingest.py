#!/usr/bin/env python3
"""Bring things into the vault: files, folders, web pages, emails. Standard library only.

    python3 bin/ingest.py add <file|folder|url> [...]     into Clippings/ (someone else wrote it)
    python3 bin/ingest.py add --mine <file|folder> [...]  into your own notes (you wrote it)
    python3 bin/ingest.py add --links links.txt           every URL in a text file, one per line
    python3 bin/ingest.py add --vault <folder>            an existing Obsidian vault: proposes which
                                                          of its folders go where, and writes nothing
    python3 bin/ingest.py add --vault <folder> --map "Projects=Notes" --map "dates=Daily" [--sample 10]
                                                          imports it as your own writing (a folder
                                                          mapped to Clippings is other people's)
    python3 bin/ingest.py waiting                         what the librarian has not filed yet
    python3 bin/ingest.py rename "Old name" "New name"    rename a note that is still waiting
    python3 bin/ingest.py report [--days 30] [--due]      what to prune, which sources are due
                                                          and which ones earn their place
    python3 bin/ingest.py trash "Note name"               move an unused clipping (or an unused
                                                          attachment) to Obsidian's .trash/

Name where things came from with --via "<Source>" (say --via "Voice memos"). It is
written into each note as `via:`, stamps "Last pulled" on that row of Sources.md
(adding the row if there is none), and lets `report` say which sources are worth it.
A URL's via defaults to its website.

What it does with each thing:

    .md .markdown .txt   the text; a Notion export's long id is dropped from the name,
                         and images it links to are copied into Attachments/
    .html .htm, URLs     the page as Markdown, with its title, author and date
    .docx                the text, with headings, lists and tables
    .eml                 the email: subject, sender, date and body
    .pdf                 attached and embedded; its text too if `pypdf` is installed
                         (python3 -m pip install --user pypdf)
    .csv                 a Markdown table
    anything else        copied to Attachments/ and embedded (photos, audio, video)

Rules it keeps, like every script in this vault:

- It never overwrites. A name already in the vault gets " (2)", " (3)".
- The imported text sits between <!-- ingest:start --> and <!-- ingest:end -->.
  Whatever you write below the end marker is yours and is never touched again.
- En and em dashes become hyphens, because the lint refuses them.
- A note gets every property its folder's template has, so the lint passes, plus
  `ingested: <today>`. It has no `filed:` until the librarian files it, and that
  missing line is what `waiting` looks for.
- It never sets `modified`, which means "last edited by hand".
- After it writes, it rebuilds the index of notes (.paths/index.txt, see
  bin/find.py), so the next lookup finds what came in.

An existing Obsidian vault (`add --vault`) is one more source. Without --map it
writes nothing and proposes which folder goes to which kind folder here, with
counts and the command to run. With --map it brings the notes in as your own
writing (a folder mapped to Clippings is other people's), keeping their
properties: `categories` (missing topic pages are made from the topic template),
`created` (else the file's birth time), aliases, tags and the rest. The files
their notes embed are copied flat into Attachments/. A note whose name is taken
here is renamed, and every link to it in the imported notes is rewritten; links
to notes left behind stay as they are. Its settings, .trash/, templates folder,
.base and .canvas files are skipped and counted, and its CLAUDE.md or AGENTS.md
is named, not imported. --sample N brings the first N notes; a later run skips
whatever an earlier one brought, which it knows by `imported_from:` (the old
vault and the path there). Names are decided for the whole old vault on every
run, so a sample and the full run agree.

Add --dry-run to `add` to see what would be made without writing anything.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import email
import email.policy
import email.utils
import filecmp
import html
import io
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

sys.dont_write_bytecode = True  # no __pycache__ in the vault's bin/
sys.path.insert(0, str(Path(__file__).resolve().parent))
import find  # noqa: E402

VAULT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((VAULT / "bin" / "vault.json").read_text(encoding="utf-8"))
ATTACH = VAULT / "Attachments"
START, END = "<!-- ingest:start -->", "<!-- ingest:end -->"
DASHES = str.maketrans({"\u2013": "-", "\u2014": "-"})
SKIP_DIRS = {".git", ".obsidian", ".trash", ".claude", ".paths", "bin", "node_modules", "__pycache__"}
NOTION_ID = re.compile(r"\s+[0-9a-f]{32}$")
URL = re.compile(r"^https?://\S+$")
TODAY = dt.date.today().isoformat()
VIA = ""  # set by `add --via`
CADENCE = {"daily": 1, "weekly": 7, "monthly": 31}
DOC_EXT = {".md", ".markdown", ".txt", ".html", ".htm", ".docx", ".eml", ".csv", ".pdf", ".json"}


# ------------------------------------------------------------ the vault


def kind_folder(mine: bool) -> str:
    """Clippings/ for other people's writing; the vault's first authored kind for yours."""
    kinds = list(CONFIG["kinds"])
    if not mine:
        if "Clippings" not in kinds:
            sys.exit("This vault has no Clippings/ kind. Add it (see Rules.md, adding a kind) or use --mine.")
        return "Clippings"
    for k in ("Notes", "Knowledge"):
        if k in kinds:
            return k
    authored = [k for k in kinds if k not in ("Clippings", "Daily")]
    if not authored:
        sys.exit("This vault has no folder for your own notes.")
    return authored[0]


def template_keys(folder: str) -> list[tuple[str, str]]:
    """(key, raw default) for every top-level property in the folder's template, in order."""
    name = CONFIG["kinds"][folder]["template"]
    text = (VAULT / "Templates" / name).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    block = text[4:text.index("\n---", 3)]
    out: list[tuple[str, str]] = []
    for line in block.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            out.append((m.group(1), m.group(2)))
        elif out and line.strip():
            out[-1] = (out[-1][0], out[-1][1] + "\n" + line)
    return out


def note_names(but: str = "") -> set[str]:
    """Every note name in the vault, lower case (leaving out the top folder `but`, if given).
    Obsidian links by name, so names are global."""
    names = set()
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (d == but and Path(root) == VAULT)]
        for fn in files:
            if fn.endswith(".md"):
                names.add(unicodedata.normalize("NFC", fn[:-3]).lower())
    return names


def safe_name(title: str) -> str:
    title = unicodedata.normalize("NFC", title).translate(DASHES)
    title = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return title[:100].rstrip(" .") or "Untitled"


def unique_note(title: str, taken: set[str]) -> str:
    base = safe_name(title)
    name, n = base, 2
    while name.lower() in taken:
        name, n = "%s (%d)" % (base, n), n + 1
    taken.add(name.lower())
    return name


def attach(src: Path | None, data: bytes | None, filename: str, dry: bool) -> str:
    """Copy a file into Attachments/ under a free name; return that name for ![[...]]."""
    stem, ext = os.path.splitext(safe_name(filename))
    name, n = stem + ext, 2
    while (ATTACH / name).exists():
        name, n = "%s (%d)%s" % (stem, n, ext), n + 1
    if not dry:
        ATTACH.mkdir(exist_ok=True)
        if src is not None:
            shutil.copy2(src, ATTACH / name)
        else:
            (ATTACH / name).write_bytes(data or b"")
    return name


def yaml_value(value) -> str:
    if isinstance(value, list):
        return " []" if not value else "".join("\n  - " + json.dumps(v, ensure_ascii=False) for v in value)
    if value in ("", None):
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
        return " " + str(value)
    return " " + json.dumps(str(value), ensure_ascii=False)


def blocks(lines: list[str]) -> dict[str, list[str]]:
    """Frontmatter lines grouped by top-level key, in order. A key is any unindented `name:` line."""
    out: dict[str, list[str]] = {}
    key = None
    for line in lines:
        if line[:1].strip() and not line.startswith(("-", "#")) and ":" in line:
            key = line.split(":", 1)[0].strip()
            out[key] = [line]
        elif key is not None:
            out[key].append(line)
    return out


def frontmatter(folder: str, fields: dict, carry: list[str]) -> str:
    """The template's properties in order (from fields, else the old note's own value, else the
    default), then what ingest adds, then every other property the old note had."""
    kept = blocks(carry)
    lines = ["---"]
    keys = template_keys(folder)
    have = {k for k, _ in keys}
    for key, raw in keys:
        if key in fields and fields[key] not in ("", None, []):
            lines.append(key + ":" + yaml_value(fields[key]))
        elif key in kept:
            lines.extend(kept[key])
        else:
            default = raw.replace("{{date}}", TODAY).replace("{{title}}", "")
            lines.append(key + ":" + ((" " if default and not default.startswith("\n") else "") + default))
    for key in ("categories", "url", "author", "published"):
        if key not in have and fields.get(key):
            lines.append(key + ":" + yaml_value(fields[key]))
            have.add(key)
    via = VIA or (urllib.parse.urlparse(fields["url"]).netloc.replace("www.", "") if fields.get("url") else "")
    if via and "via" not in have:
        lines.append("via:" + yaml_value(via))
        have.add("via")
    lines.append("ingested: " + TODAY)
    have.update(("ingested", "filed"))
    for key, block in kept.items():
        if key not in have:
            lines.extend(block)
    lines.append("---")
    return "\n".join(lines)


def write_note(folder: str, title: str, body: str, fields: dict, origin: str,
               taken: set[str], dry: bool, carry: list[str] | None = None) -> Path:
    name = unique_note(title, taken)
    path = VAULT / folder / (name + ".md")
    body = body.translate(DASHES).strip()
    text = "%s\n%s\n*Imported from %s on %s.*\n\n%s\n%s\n\n## Notes\n\n- \n" % (
        frontmatter(folder, fields, carry or []), START, origin.translate(DASHES), TODAY, body, END)
    if not dry:
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("ADDED  %s/%s.md  (from %s)" % (folder, name, origin))
    return path


# ------------------------------------------------------------ HTML to Markdown


class Markdown(HTMLParser):
    """Small HTML to Markdown converter: enough for articles, not for web apps."""

    DROP = {"script", "style", "noscript", "svg", "nav", "footer", "form", "aside", "iframe",
            "button", "template", "head"}
    BLOCK = {"p", "div", "section", "article", "main", "header", "figure", "figcaption",
             "table", "dl", "dt", "dd", "hr", "body"}

    def __init__(self, base: str = "", only: str | None = None):
        super().__init__(convert_charrefs=True)
        self.base, self.only = base, only
        self.out: list[str] = []
        self.drop = 0
        self.inside = 0 if only else 1
        self.lists: list[list] = []
        self.pre = 0
        self.href: list[str | None] = []
        self.quote_at: list[int] = []
        self.meta: dict[str, str] = {}
        self.title = ""
        self.in_title = False
        self.cells = 0  # cells in the current table row
        self.head = False  # the current row is a header row
        self.ruled = False  # the current table has its header rule

    def emit(self, text: str) -> None:
        if self.inside and not self.drop:
            self.out.append(text)

    def block(self) -> None:
        self.emit("\n\n")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"])
            return
        if tag == "title":
            self.in_title = True
        if self.only and tag == self.only:
            self.inside += 1
        if tag in self.DROP:
            self.drop += 1
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.block()
            self.emit("#" * int(tag[1]) + " ")
        elif tag in ("ul", "ol"):
            if not self.lists:
                self.block()
            self.lists.append([tag, 0])
        elif tag == "li":
            depth = max(len(self.lists) - 1, 0)
            if self.lists and self.lists[-1][0] == "ol":
                self.lists[-1][1] += 1
                mark = "%d. " % self.lists[-1][1]
            else:
                mark = "- "
            self.emit("\n" + "    " * depth + mark)
        elif tag == "br":
            self.emit("  \n")
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "code" and not self.pre:
            self.emit("`")
        elif tag == "pre":
            self.pre += 1
            self.emit("\n\n```\n")
        elif tag == "blockquote":
            self.block()
            self.quote_at.append(len(self.out))
        elif tag == "a":
            href = a.get("href")
            self.href.append(urllib.parse.urljoin(self.base, href) if href and not href.startswith("#") else None)
            if self.href[-1]:
                self.emit("[")
        elif tag == "img":
            src = a.get("src") or a.get("data-src")
            if src and not src.startswith("data:"):
                self.emit("![%s](%s)" % ((a.get("alt") or "").replace("]", ""), urllib.parse.urljoin(self.base, src)))
        elif tag == "table":
            self.block()
            self.ruled = False
        elif tag == "tr":
            self.cells, self.head = 0, False
            self.emit("\n|")
        elif tag in ("td", "th"):
            self.cells += 1
            self.head = self.head or tag == "th"
            self.emit(" ")
        elif tag in self.BLOCK:
            self.block()

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in self.DROP:
            self.drop = max(self.drop - 1, 0)
            return
        if re.fullmatch(r"h[1-6]", tag) or tag in self.BLOCK:
            self.block()
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            if not self.lists:
                self.block()
        elif tag in ("td", "th"):
            self.emit(" |")
        elif tag == "tr":
            if not self.ruled and self.cells:
                self.emit("\n|" + " --- |" * self.cells)
                self.ruled = True
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "code" and not self.pre:
            self.emit("`")
        elif tag == "pre":
            self.pre = max(self.pre - 1, 0)
            self.emit("\n```\n\n")
        elif tag == "blockquote" and self.quote_at:
            at = self.quote_at.pop()
            inner = "".join(self.out[at:]).strip()
            del self.out[at:]
            self.emit("\n\n" + "\n".join("> " + ln if ln.strip() else ">" for ln in inner.split("\n")) + "\n\n")
        elif tag == "a" and self.href:
            href = self.href.pop()
            if href:
                self.emit("](%s)" % href)
        if self.only and tag == self.only:
            self.inside = max(self.inside - 1, 0)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.pre:
            self.emit(data)
        else:
            self.emit(re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+(?=[^\s-])", "\n", text)
        text = re.sub(r"\[\s*\]\([^)]*\)", "", text)
        text = re.sub(r"(?m)^(\s*(?:-|\d+\.)) {2,}", r"\1 ", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def html_to_note(raw: str, base: str = "") -> tuple[str, str, dict]:
    """(title, markdown body, fields) from an HTML page."""
    lower = raw.lower()
    only = "article" if "<article" in lower else ("main" if "<main" in lower else None)
    parser = Markdown(base, only)
    parser.feed(raw)
    body = parser.markdown()
    if only and len(body) < 200:  # the article tag held a teaser, not the article
        parser = Markdown(base, None)
        parser.feed(raw)
        body = parser.markdown()
    m = parser.meta
    title = html.unescape(m.get("og:title") or parser.title or "").strip()
    author = m.get("author") or m.get("article:author") or m.get("twitter:creator") or ""
    published = (m.get("article:published_time") or m.get("datepublished") or m.get("date") or "")[:10]
    fields = {"author": ["[[%s]]" % safe_name(author)] if author and not author.startswith("http") else [],
              "published": published if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published) else ""}
    return title, body, fields


# ------------------------------------------------------------ one reader per kind of file


def read_markdown(path: Path, dry: bool, used: set[Path]) -> tuple[str, list[str]]:
    """Body of a Markdown or text file, its old frontmatter kept, local images attached."""
    text = path.read_text(encoding="utf-8", errors="replace")
    carry: list[str] = []
    if text.startswith("---\n") and "\n---" in text[3:]:
        end = text.index("\n---", 3)
        own = {"categories", "created", "ingested", "filed", "modified", "url", "author", "published"}
        block_key = None
        for line in text[4:end].split("\n"):
            m = re.match(r"^([A-Za-z_][\w-]*):", line)
            if m:
                block_key = m.group(1)
            if block_key and block_key not in own:
                carry.append(line.translate(DASHES))
        text = text[end + 4:].lstrip("\n")

    def local_image(m: re.Match) -> str:
        target = urllib.parse.unquote(m.group(2).split(" ")[0])
        src = (path.parent / target).resolve()
        if re.match(r"^[a-z]+:", target) or not src.is_file():
            return m.group(0)
        used.add(src)
        return "![[%s]]" % attach(src, None, src.name, dry)

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", local_image, text)
    return text, carry


def read_docx(path: Path) -> str:
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))

    def para(p) -> str:
        parts = []
        for node in p.iter():
            if node.tag == w + "t":
                parts.append(node.text or "")
            elif node.tag == w + "tab":
                parts.append("\t")
            elif node.tag in (w + "br", w + "cr"):
                parts.append("\n")
        text = "".join(parts).strip()
        style = p.find("%spPr/%spStyle" % (w, w))
        style = (style.get(w + "val") if style is not None else "") or ""
        m = re.match(r"(?i)heading\s*(\d)", style)
        if text and m:
            return "#" * min(int(m.group(1)), 6) + " " + text
        if text and style.lower() == "title":
            return "# " + text
        if text and p.find("%spPr/%snumPr" % (w, w)) is not None:
            return "- " + text
        return text

    out = []
    body = root.find(w + "body")
    for child in list(body) if body is not None else []:
        if child.tag == w + "p":
            out.append(para(child))
        elif child.tag == w + "tbl":
            rows = [[" ".join(para(p) for p in cell.iter(w + "p")).strip().replace("|", "\\|")
                     for cell in row.iter(w + "tc")] for row in child.iter(w + "tr")]
            if rows:
                out.append(md_table(rows))
    return "\n\n".join(x for x in out if x)


def read_pdf(path: Path) -> str:
    try:
        import pypdf  # optional: python3 -m pip install --user pypdf
    except ImportError:
        return ("> [!note] Text not extracted\n> The PDF is attached above. To have its text "
                "pulled out too, run `python3 -m pip install --user pypdf` and ingest it again.")
    try:
        reader = pypdf.PdfReader(str(path))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:  # a damaged or encrypted PDF should not stop a folder import
        return "> [!warning] Could not read the PDF's text (%s). It is attached above." % exc
    text = "\n\n".join(p for p in pages if p)
    return text or "> [!note] This PDF has no text layer (it may be a scan). It is attached above."


def md_table(rows: list[list[str]], limit: int = 1000) -> str:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:limit + 1]]
    if len(rows) > limit + 1:
        lines.append("\n*%d more rows not shown; the full file is attached.*" % (len(rows) - limit - 1))
    return "\n".join(lines)


def read_csv(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows = [[c.replace("|", "\\|").replace("\n", " ") for c in r] for r in csv.reader(io.StringIO(text)) if r]
    return md_table(rows) if rows else "(empty file)"


def read_email(path: Path) -> tuple[str, str, dict]:
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    part = msg.get_body(preferencelist=("plain", "html"))
    body = part.get_content() if part else ""
    if part is not None and part.get_content_type() == "text/html":
        body = html_to_note(body)[1]
    sender = email.utils.parseaddr(msg.get("from", ""))[0] or msg.get("from", "")
    try:
        sent = email.utils.parsedate_to_datetime(msg["date"]).date().isoformat() if msg["date"] else ""
    except (TypeError, ValueError):
        sent = ""
    fields = {"author": ["[[%s]]" % safe_name(sender)] if sender else [], "published": sent}
    return msg.get("subject", "") or path.stem, body, fields


def fetch(url: str) -> tuple[str, bytes]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh) vault-ingest/1.0", "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.headers.get("Content-Type", ""), res.read()


# ------------------------------------------------------------ the commands


def add_url(url: str, folder: str, taken: set[str], dry: bool) -> None:
    fields = {"url": url}
    try:
        ctype, data = fetch(url)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        host = urllib.parse.urlparse(url).netloc
        body = ("> [!warning] Not fetched yet\n> The page could not be read (%s). The librarian "
                "will try to find what it is.\n\n<%s>" % (exc, url))
        write_note(folder, host or url, body, fields, url, taken, dry)
        return
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        name = os.path.basename(urllib.parse.urlparse(url).path) or "download.pdf"
        stored = attach(None, data, name, dry)
        tmp = ATTACH / stored
        body = "![[%s]]\n\n%s" % (stored, read_pdf(tmp) if not dry else "")
        write_note(folder, os.path.splitext(name)[0], body, fields, url, taken, dry)
        return
    charset = re.search(r"charset=([\w-]+)", ctype)
    raw = data.decode(charset.group(1) if charset else "utf-8", errors="replace")
    title, body, more = html_to_note(raw, url)
    fields.update(more)
    write_note(folder, title or urllib.parse.urlparse(url).netloc, body, fields, url, taken, dry)


def born(path: Path) -> str:
    """The day a file was made: its birth time where the system keeps one, else its last change."""
    st = path.stat()
    return dt.date.fromtimestamp(getattr(st, "st_birthtime", st.st_mtime)).isoformat()


def add_file(path: Path, folder: str, mine: bool, taken: set[str], dry: bool, used: set[Path]) -> None:
    ext = path.suffix.lower()
    title = NOTION_ID.sub("", path.stem)
    origin = "`%s`" % path.name
    fields: dict = {}
    carry: list[str] = []
    if mine:
        fields["created"] = born(path)
    if ext in (".md", ".markdown", ".txt"):
        body, carry = read_markdown(path, dry, used)
        first = re.match(r"#\s+(.+)", body)
        if first and title.lower().startswith("untitled"):
            title = first.group(1)
    elif ext in (".html", ".htm"):
        t, body, more = html_to_note(path.read_text(encoding="utf-8", errors="replace"))
        title = t or title
        fields.update(more)
    elif ext == ".docx":
        body = read_docx(path)
    elif ext == ".eml":
        title, body, more = read_email(path)
        fields.update(more)
    elif ext == ".csv":
        body = read_csv(path)
        body = "![[%s]]\n\n%s" % (attach(path, None, path.name, dry), body)
    elif ext == ".json":
        body = "```json\n%s\n```" % path.read_text(encoding="utf-8", errors="replace").strip()
    elif ext == ".pdf":
        body = "![[%s]]\n\n%s" % (attach(path, None, path.name, dry), read_pdf(path))
    else:
        body = "![[%s]]" % attach(path, None, path.name, dry)
    if mine:
        fields["created"] = fields.get("created") or TODAY
    else:
        fields.setdefault("created", TODAY)
    write_note(folder, title, body, fields, origin, taken, dry, carry)


def add_folder(root: Path, folder: str, mine: bool, taken: set[str], dry: bool, used: set[Path]) -> None:
    docs, rest = [], []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            p = Path(base) / fn
            (docs if p.suffix.lower() in DOC_EXT else rest).append(p)
    for p in docs:  # documents first, so the images they link are attached with them
        add_file(p, folder, mine, taken, dry, used)
    for p in rest:
        if p.resolve() not in used:
            add_file(p, folder, mine, taken, dry, used)


# ------------------------------------------------------------ an existing Obsidian vault


RULE_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")  # only at the old vault's top level or in its .claude/
DATED = re.compile(r"\d{4}-\d{2}-\d{2}")
WIKI = re.compile(r"(!?)\[\[([^\[\]|#^]+)([#^][^\[\]|]*)?(\|[^\[\]]*)?\]\]")
MD_LINK = re.compile(r'(!?)\[([^\]]*)\]\((<[^>]*>|[^)\s]+)(?:\s+"[^"]*")?\)')
CODE = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]+`)", re.S)
CATEGORY = re.compile(r"\[\[([^\]|#]*)[^\]]*\]\]|([^,\n\[\]\"]+)")


def plural(n: int, word: str) -> str:
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


class OldVault:
    """What is in an Obsidian vault: its notes, its other files, and what an import leaves out."""

    def __init__(self, root: Path):
        self.root, self.name = root, root.name
        self.notes: list[str] = []  # vault-relative paths of the notes, sorted
        self.files: dict[str, Path] = {}  # lower-case relative path of every other file
        self.by_name: dict[str, list[str]] = {}  # lower-case file name -> those paths
        self.rules: list[str] = []  # CLAUDE.md, AGENTS.md: the old vault's rules for an AI
        self.skipped: list[str] = []  # one summary line per place left out
        self.templates = self.templates_folder()
        counts = {".base": 0, ".canvas": 0}
        for base, dirs, names in os.walk(root):
            here = Path(base).relative_to(root).as_posix()
            here = "" if here == "." else here + "/"
            for d in sorted(dirs):
                rel = here + d
                if d.startswith(".") or rel == self.templates:
                    inside = [f for _, _, fs in os.walk(Path(base) / d) for f in fs]
                    what = plural(len(inside), "file") if d.startswith(".") else (
                        plural(sum(f.endswith(".md") for f in inside), "note") + ", the templates folder")
                    self.skipped.append("%s/ (%s)" % (rel, what))
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and here + d != self.templates)
            for fn in sorted(names):
                rel, ext = here + fn, os.path.splitext(fn)[1].lower()
                if fn.startswith("."):
                    continue
                if not here and fn in RULE_FILES:
                    self.rules.append(rel)
                elif ext in counts:
                    counts[ext] += 1
                elif ext == ".md":
                    self.notes.append(rel)
                else:
                    self.files[rel.lower()] = Path(base) / fn
                    self.by_name.setdefault(fn.lower(), []).append(rel.lower())
        self.rules += [".claude/" + fn for fn in RULE_FILES if (root / ".claude" / fn).is_file()]
        self.notes.sort()
        self.skipped += ["%s %s file%s" % (n, ext, "" if n == 1 else "s") for ext, n in counts.items() if n]

    def templates_folder(self) -> str:
        """The folder Obsidian's Templates plugin reads, from the vault's settings, else Templates/."""
        try:
            folder = json.loads((self.root / ".obsidian" / "templates.json").read_text(encoding="utf-8")).get("folder")
        except (OSError, ValueError, AttributeError):
            folder = ""
        folder = (folder or "").strip().strip("/")
        return folder or ("Templates" if (self.root / "Templates").is_dir() else "")

    def find(self, target: str, folder: str) -> str | None:
        """The file an embed points at: a path from the note's folder or the vault root, else by name."""
        t = target.strip().lstrip("/").lower()
        for cand in (os.path.normpath(os.path.join(folder.lower(), t)), os.path.normpath(t)):
            if cand.replace(os.sep, "/") in self.files:
                return cand.replace(os.sep, "/")
        hits = self.by_name.get(t.split("/")[-1])
        return hits[0] if hits else None


def is_dated(rel: str) -> bool:
    return DATED.fullmatch(Path(rel).stem) is not None


def top_folder(rel: str) -> str:
    return rel.split("/")[0] if "/" in rel else "."


def kind_for(rel: str, mapping: dict[str, str]) -> str | None:
    """The kind folder a note goes to: `dates` first, then its folder or the nearest parent mapped."""
    if "dates" in mapping and is_dated(rel):
        return mapping["dates"]
    folder = os.path.dirname(rel).lower()
    if not folder:
        return mapping.get(".")
    while folder:
        if folder in mapping:
            return mapping[folder]
        folder = os.path.dirname(folder)
    return None


def read_maps(maps: list[str], old: OldVault) -> dict[str, str]:
    """--map "Folder=Kind" flags as {lower-case folder: kind}, refusing names that do not exist."""
    kinds = {k.lower(): k for k in CONFIG["kinds"]}
    out = {}
    for m in maps:
        folder, _, kind = m.rpartition("=")
        folder, kind = folder.strip().strip("/") or ".", kind.strip().strip("/")
        if kind.lower() not in kinds:
            sys.exit("--map %r: %r is not a kind folder here. Kinds: %s." % (m, kind, ", ".join(CONFIG["kinds"])))
        if folder not in (".", "dates") and not (old.root / folder).is_dir():
            sys.exit("--map %r: the vault has no folder %r." % (m, folder))
        out[folder.lower()] = kinds[kind.lower()]
    return out


def propose(old: OldVault) -> None:
    """Print a mapping to agree with the owner, and the command that runs it. Writes nothing."""
    kinds = list(CONFIG["kinds"])
    dated = [n for n in old.notes if is_dated(n)] if "Daily" in kinds else []
    counts: dict[str, int] = {}
    for n in old.notes:
        if n not in dated:
            counts[top_folder(n)] = counts.get(top_folder(n), 0) + 1
    rows = []
    for top in sorted(counts, key=lambda t: (t != ".", t.lower())):
        kind = next((k for k in kinds if k.lower() in (top.lower(), top.lower() + "s", top.lower().rstrip("s"))), None)
        if kind is None and top.lower() == "categories":
            rows.append((top, counts[top], None, "skip: topic pages are made from `categories`"))
        else:
            rows.append((top, counts[top], kind or kind_folder(True), ""))
    if dated:
        rows.append(("dates", len(dated), "Daily", "notes titled YYYY-MM-DD, wherever they are"))
    print("VAULT  %s is an Obsidian vault with %s. Nothing was written. Proposed mapping:\n" % (
        old.name, plural(len(old.notes), "note")))
    for i, (top, n, kind, why) in enumerate(rows, 1):
        print("  %d. %s  (%s)  ->  %s" % (i, "(root)" if top == "." else top, plural(n, "note"),
                                          kind + ("  (%s)" % why if why else "") if kind else why))
    report_skipped(old, [])
    flags = "".join(' --map "%s=%s"' % (top, kind) for top, _, kind, _ in rows if kind)
    print("\nShow the owner this list and change it by number. Then sample first (add --sample 10), "
          "and run:\n  python3 bin/ingest.py add --vault \"%s\"%s --via \"%s\"" % (old.root, flags, VIA or old.name))


def report_skipped(old: OldVault, more: list[str]) -> None:
    for line in old.skipped + more:
        print("SKIPPED  %s" % line)
    if old.rules:
        print("RULES    %s: the old vault's rules for an AI, not imported. Read them and propose, as one "
              "numbered list, the rules worth keeping here: decisions for Decisions.md, facts about the "
              "owner for Me.md." % ", ".join(old.rules))


def imported_before() -> dict[str, str]:
    """{imported_from value: note name} for every note an import brought in. The property names the
    old vault and the path there, and the librarian keeps it, so a filed or renamed note still counts."""
    out = {}
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".md"):
                fm, _ = head_and_body((Path(root) / fn).read_text(encoding="utf-8", errors="replace"))
                value = fm.get("imported_from", "").strip()
                try:
                    value = json.loads(value) if value.startswith('"') else value
                except ValueError:
                    pass
                if value:
                    out[value] = fn[:-3]
    return out


def attached_before(src: Path) -> str | None:
    """The name of a file already in Attachments/ with the same bytes, among the names attach() tries."""
    stem, ext = os.path.splitext(safe_name(src.name))
    name, n = stem + ext, 2
    while (ATTACH / name).exists():
        if filecmp.cmp(str(src), str(ATTACH / name), shallow=False):
            return name
        name, n = "%s (%d)%s" % (stem, n, ext), n + 1
    return None


def category_values(lines: list[str]) -> list[str]:
    """Every value of a `categories` property: a link by its target, a plain word as written."""
    out = []
    for m in CATEGORY.finditer("\n".join(lines).split(":", 1)[-1]):
        value = m.group(1).split("/")[-1] if m.group(1) is not None else m.group(2).strip().lstrip("-")
        value = value.strip().strip("'\"")
        value = value[:-3] if value.lower().endswith(".md") else value
        if value:
            out.append(safe_name(value))
    return out


def topic_page(topic: str, dry: bool, why: str = "") -> None:
    """A new page in Categories/, made from the topic template like any other."""
    tpl = VAULT / "Templates" / "Topic Template.md"
    text = tpl.read_text(encoding="utf-8") if tpl.exists() else "---\ntags:\n  - categories\n---\n"
    if not dry:
        (VAULT / "Categories").mkdir(exist_ok=True)
        (VAULT / "Categories" / (topic + ".md")).write_text(
            text.replace("{{title}}", topic).replace("{{date}}", TODAY), encoding="utf-8")
    print("TOPIC  Categories/%s.md  (a new topic page%s)" % (topic, why))


def import_vault(root: Path, maps: list[str], sample: int | None, dry: bool) -> bool:
    """Bring an Obsidian vault in. Without --map, propose a mapping and return False."""
    if not (root / ".obsidian").is_dir():
        sys.exit("%s is not an Obsidian vault (it has no .obsidian/ folder). Use `add` without --vault." % root)
    src, here = root.resolve(), VAULT.resolve()
    if src == here or src in here.parents:
        sys.exit("Refused: %s is this vault, or a folder that holds it. Give the old vault's own folder." % root)
    old = OldVault(src)
    if not maps:
        propose(old)
        return False
    mapping = read_maps(maps, old)
    key = lambda rel: ("%s/%s" % (old.name, rel)).translate(DASHES)  # noqa: E731  its imported_from: value
    origin_of = lambda rel: ("`%s` in the vault `%s`" % (rel, old.name)).translate(DASHES)  # noqa: E731
    picked, unmapped = [], {}
    for rel in old.notes:
        kind = kind_for(rel, mapping)
        if kind:
            picked.append((rel, kind))
        else:
            unmapped[top_folder(rel)] = unmapped.get(top_folder(rel), 0) + 1
    before = imported_before()
    done = [rel for rel, _ in picked if key(rel) in before]
    todo = [(rel, kind) for rel, kind in picked if key(rel) not in before]
    if sample:
        todo = todo[:sample]
    coming = {rel for rel, _ in todo}
    # A name for every mapped note on every run, in sorted order, whether it comes now, came before
    # (it keeps the name it has) or comes later: a sample and the full run agree, and every link
    # points at the name its note has, or will have, here.
    taken = note_names()
    name_of, by_path, by_name = {}, {}, {}
    for rel, kind in picked:
        stem = Path(rel).stem
        name = before.get(key(rel)) or unique_note(stem, taken)
        name_of[rel] = name
        by_path[rel[:-3].lower()] = name
        by_name.setdefault(stem.lower(), name)
        if name != stem and rel in coming:
            print("RENAMED  %s  ->  %s  (%s; links to it are rewritten)" % (
                stem, name, "a note here has that name" if safe_name(stem) == stem else "a character a name cannot have here"))

    copied: dict[str, str] = {}
    fresh: list[str] = []
    topics = {p.stem.lower(): p.stem for p in (VAULT / "Categories").glob("*.md")}
    others = note_names(but="Categories") | {n.lower() for n in name_of.values()}
    made: list[tuple[str, str]] = []

    def topic_for(value: str) -> str:
        """An existing topic page, else a new one on the first free name that is no note's name."""
        n = 1
        while True:
            name = value if n == 1 else "%s (%d)" % (value, n)
            if name.lower() in topics:
                return topics[name.lower()]
            if name.lower() not in others:
                topics[name.lower()] = name
                made.append((name, "" if n == 1 else "; %s is a note's name here" % value))
                return name
            n += 1

    def attachment(found: str) -> str:
        if found not in copied:
            path = old.files[found]
            same = attached_before(path)  # brought by an earlier run: not copied twice
            copied[found] = same or attach(path, None, path.name, dry)
            if not same:
                fresh.append(copied[found])
        return copied[found]

    def note_named(target: str, folder: str) -> str | None:
        t = target.strip().lower()
        t = t[:-3] if t.endswith(".md") else t
        if "/" not in t:
            return by_name.get(t)
        t = os.path.normpath(os.path.join(folder.lower(), t)).replace(os.sep, "/") if t.startswith(".") else t
        return by_path.get(t) or next((v for p, v in by_path.items() if p.endswith("/" + t)), None)

    def relink(text: str, folder: str) -> str:
        """Embedded files copied and their embeds renamed, links to renamed notes rewritten, code untouched."""
        def wiki(m: re.Match) -> str:
            bang, target, anchor, alias = m.group(1), m.group(2), m.group(3) or "", m.group(4) or ""
            found = old.find(target, folder) if bang else None
            if found:
                return "![[%s%s%s]]" % (attachment(found), anchor, alias)
            name = note_named(target, folder)
            if name is None or name == target.strip():
                return m.group(0)  # a note that did not come along stays a breadcrumb
            return "%s[[%s%s%s]]" % (bang, name, anchor, alias)

        def md(m: re.Match) -> str:
            bang, label, target = m.group(1), m.group(2), m.group(3).strip("<>")
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                return m.group(0)  # a web address
            path, _, anchor = urllib.parse.unquote(target).partition("#")
            if bang:
                found = old.find(path, folder)
                return "![[%s]]" % attachment(found) if found else m.group(0)
            name = note_named(path, folder) if path.lower().endswith(".md") else None
            if name is None or name == path[:-3]:
                return m.group(0)
            return "[[%s%s%s]]" % (name, "#" + anchor if anchor else "", "|" + label if label and label != name else "")

        parts = CODE.split(text)
        return "".join(p if i % 2 else MD_LINK.sub(md, WIKI.sub(wiki, p)) for i, p in enumerate(parts))

    added: dict[str, int] = {}
    for rel, kind in todo:
        path, folder = old.root / rel, os.path.dirname(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        lines: list[str] = []
        if text.startswith("---\n") and "\n---" in text[3:]:
            end = text.index("\n---", 3)
            lines, text = text[4:end].split("\n"), text[end + 4:].lstrip("\n")
        props = blocks([ln.translate(DASHES) for ln in lines])
        fields: dict = {}
        for value in category_values(props.pop("categories", [])):  # as written: topics, not the notes renamed
            link = "[[%s]]" % topic_for(value)
            if link not in fields.setdefault("categories", []):
                fields["categories"].append(link)
        if "created" in {k for k, _ in template_keys(kind)}:
            given = " ".join(props.get("created", [])).split(":", 1)[-1].strip()
            day = DATED.search(given)
            if day or not given.strip("\"' "):
                props.pop("created", None)
                fields["created"] = day.group(0) if day else born(path)
            # else a date in some other form ("March 4, 2021") is kept as the owner wrote it
        carry = [relink(ln, folder) for block in props.values() for ln in block]  # frontmatter() drops an old ingested: or filed:
        carry.append("imported_from:" + yaml_value(key(rel)))
        write_note(kind, name_of[rel], relink(text, folder), fields, origin_of(rel), set(), dry, carry)
        added[kind] = added.get(kind, 0) + 1
    for name, why in made:
        topic_page(name, dry, why)

    print("VAULT  %s from %s: %s. %s copied into Attachments/, %s made." % (
        plural(sum(added.values()), "note"), old.name,
        ", ".join("%s %d" % kv for kv in added.items()) or "nothing new",
        plural(len(fresh), "attachment"), plural(len(made), "topic page")))
    if done:
        print("ALREADY  %s imported before, left as they are" % plural(len(done), "note"))
    report_skipped(old, ["%s (%s): not mapped" % ("notes at the top level" if f == "." else f + "/", plural(n, "note"))
                         for f, n in sorted(unmapped.items())])
    left = len(picked) - len(todo) - len(done)
    if sample and left > 0:
        print("SAMPLE   stopped after %s; %s left. File and check these with the owner, then run the same "
              "command without --sample for the rest." % (plural(len(todo), "note"), left))
    return True


def source_names() -> list[str]:
    """The Source column of Sources.md, as spelled there."""
    path = VAULT / "Sources.md"
    if not path.exists():
        return []
    out, rows = [], False
    for ln in path.read_text(encoding="utf-8").split("\n"):
        if ln.startswith("| Source"):
            rows = True
        elif rows and ln.startswith("|") and not ln.startswith("|---"):
            out.append(ln.strip().strip("|").split("|")[0].strip().strip("[]"))
        elif rows and not ln.startswith("|"):
            break
    return out


def stamp_source(via: str) -> None:
    """Set Last pulled on the Sources.md row named `via`, adding the row if it is missing."""
    path = VAULT / "Sources.md"
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").split("\n")
    head = next((i for i, ln in enumerate(lines) if ln.startswith("| Source")), None)
    if head is None:
        return
    cols = [c.strip().lower() for c in lines[head].strip("|").split("|")]
    at = cols.index("last pulled") if "last pulled" in cols else None
    end = head + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    for i in range(head + 2, end):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if cells and cells[0].strip("[]").lower() == via.lower():
            if at is not None and at < len(cells):
                cells[at] = TODAY
                lines[i] = "| " + " | ".join(cells) + " |"
            break
    else:
        row = [""] * len(cols)
        row[0] = via
        for name, value in (("how", "`ingest.py add --via`"), ("last pulled", TODAY), ("keep?", "trial")):
            if name in cols:
                row[cols.index(name)] = value
        lines.insert(end, "| " + " | ".join(row) + " |")
        print("SOURCE   added %r to Sources.md (fill in its cadence)" % via)
    path.write_text("\n".join(lines), encoding="utf-8")


def add_items(args) -> None:
    """Files, folders and URLs, each into Clippings/ (or, with --mine, the owner's notes)."""
    items = list(args.items)
    if args.links:
        for line in Path(args.links).read_text(encoding="utf-8").splitlines():
            if URL.match(line.strip()):
                items.append(line.strip())
    if not items:
        sys.exit("Nothing to add. Give a file, a folder, a URL, --links FILE, or --vault FOLDER.")
    for item in items:
        p = Path(item).expanduser()
        if not URL.match(item) and (p / ".obsidian").is_dir():
            sys.exit("%s is an Obsidian vault: bring it in with `add --vault \"%s\"`, which proposes "
                     "a mapping first. Nothing was written." % (item, item))
    folder = kind_folder(args.mine)
    taken = note_names()
    used: set[Path] = set()
    for item in items:
        if URL.match(item):
            add_url(item, folder, taken, args.dry_run)
            continue
        p = Path(item).expanduser()
        if p.is_dir():
            add_folder(p, folder, args.mine, taken, args.dry_run, used)
        elif p.is_file():
            add_file(p, folder, args.mine, taken, args.dry_run, used)
        else:
            print("SKIPPED  %s  (no such file, folder or URL)" % item)


def cmd_add(args) -> None:
    global VIA
    VIA = (args.via or "").translate(DASHES).strip()
    VIA = next((s for s in source_names() if s.lower() == VIA.lower()), VIA)  # Sources.md's spelling
    if args.vault:
        if args.items or args.links or args.mine:
            sys.exit("--vault goes on its own: no files, --links or --mine with it.")
        if args.sample is not None and args.sample < 1:
            sys.exit("--sample takes a number of notes, 1 or more.")
        if not import_vault(Path(args.vault).expanduser(), args.map or [], args.sample, args.dry_run):
            return  # no mapping yet: the proposal is printed and nothing was written
    else:
        if args.map or args.sample is not None:
            sys.exit("--map and --sample go with --vault <an Obsidian vault>.")
        add_items(args)
    if args.dry_run:
        print("(dry run: nothing was written)")
    else:
        if VIA:
            stamp_source(VIA)
        find.rebuild(str(VAULT))
        print("Next: file them with `python3 bin/librarian.py`, or ask your AI to follow bin/librarian.md.")


def waiting_notes(filed_today: bool = False) -> list[Path]:
    """Notes with `ingested:` and no `filed:` (or, with filed_today, filed today)."""
    out = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and d != "Templates")
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            p = Path(root) / fn
            text = p.read_text(encoding="utf-8", errors="replace")
            head = text[:text.find("\n---", 3)] if text.startswith("---\n") else ""
            filed = re.search(r"^filed:\s*(\S*)", head, re.M)
            if re.search(r"^ingested:", head, re.M) and (
                    not filed or (filed_today and filed.group(1) == TODAY)):
                out.append(p)
    return out


def cmd_waiting(_args) -> None:
    notes = waiting_notes()
    if not notes:
        print("Nothing waiting to be filed.")
    for p in notes:
        print("WAITING  %s" % p.relative_to(VAULT))


def rename(old: str, new: str) -> Path:
    """Rename an imported note that is waiting or was filed today. Exits with the reason if not."""
    def stem(s: str) -> str:
        s = unicodedata.normalize("NFC", s.strip())
        return s[:-3] if s.endswith(".md") else s

    old, new = stem(old), stem(new)
    match = [p for p in waiting_notes(filed_today=True) if unicodedata.normalize("NFC", p.stem) == old]
    if not match:
        sys.exit("No note named %r waiting to be filed (or filed today). Only those can be renamed here." % old)
    if not new or any(c in new for c in "/\\:") or new.startswith("."):
        sys.exit("Not a plain note name: %r" % new)
    if new != new.translate(DASHES):
        sys.exit("The new name has an en or em dash. Use a hyphen, comma or parentheses.")
    if new.lower() in note_names() and new.lower() != old.lower():
        sys.exit("A note named %r already exists. Pick another name." % new)
    src = match[0]
    dest = src.with_name(new + ".md")
    src.rename(dest)
    print("RENAMED  %s  ->  %s" % (src.relative_to(VAULT), dest.relative_to(VAULT)))
    return dest


def cmd_rename(args) -> None:
    rename(args.old, args.new)
    find.rebuild(str(VAULT))


# ------------------------------------------------------------ pruning


LINK_TO = re.compile(r"\[\[([^\]|#^]+)")


def head_and_body(text: str) -> tuple[dict, str]:
    """Top-level frontmatter keys as raw text, and the body."""
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return {}, text
    end = text.index("\n---", 3)
    fm: dict = {}
    key = None
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.strip():
            fm[key] += "\n" + line
    return fm, text[end + 4:]


def day(value: str) -> dt.date | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", value or "")
    try:
        return dt.date.fromisoformat(m.group(0)) if m else None
    except ValueError:
        return None


def own_text(body: str) -> bool:
    """Has the owner written anything below the ingest:end marker?"""
    tail = body.split(END, 1)[1] if END in body else ""
    left = [ln for ln in tail.split("\n") if ln.strip() not in ("", "-", "- ", "## Notes")]
    return bool(left)


def scan() -> tuple[dict, dict, set]:
    """(notes by rel path, inbound link count by lower-case name, every link target)."""
    notes, inbound, targets = {}, {}, set()
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and d != "Templates")
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            p = Path(root) / fn
            text = p.read_text(encoding="utf-8", errors="replace")
            fm, body = head_and_body(text)
            rel = p.relative_to(VAULT).as_posix()
            notes[rel] = dict(path=p, name=unicodedata.normalize("NFC", p.stem), fm=fm, body=body)
            seen = set()
            for m in LINK_TO.finditer(text):
                target = unicodedata.normalize("NFC", m.group(1).strip()).split("/")[-1]
                target = target[:-3] if target.endswith(".md") else target
                targets.add(target.lower())
                if target.lower() != p.stem.lower() and target.lower() not in seen:
                    seen.add(target.lower())
                    inbound[target.lower()] = inbound.get(target.lower(), 0) + 1
    return notes, inbound, targets


def sources_due() -> list[str]:
    path = VAULT / "Sources.md"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    head = next((i for i, ln in enumerate(lines) if ln.startswith("| Source")), None)
    if head is None:
        return []
    cols = [c.strip().lower() for c in lines[head].strip("|").split("|")]
    out = []
    for ln in lines[head + 2:]:
        if not ln.startswith("|"):
            break
        cells = dict(zip(cols, [c.strip() for c in ln.strip().strip("|").split("|")]))
        every = CADENCE.get(cells.get("cadence", "").lower())
        if not every or cells.get("keep?", "").lower() == "no":
            continue
        last = day(cells.get("last pulled", ""))
        if last is None or (dt.date.today() - last).days >= every:
            out.append("%s  (%s; last pulled %s)" % (cells.get("source", "?"), cells["cadence"],
                                                     last.isoformat() if last else "never"))
    return out


def cmd_report(args) -> None:
    today = dt.date.today()
    old = lambda d: d is not None and (today - d).days >= args.days  # noqa: E731
    due = sources_due()
    if args.due:
        print("\n".join("DUE  " + s for s in due) or "No source is due.")
        return
    notes, inbound, targets = scan()
    used = lambda n: inbound.get(n["name"].lower(), 0) > 0 or own_text(n["body"])  # noqa: E731
    sections = []

    def section(title, why, items):
        if items:
            sections.append("## %s (%d)\n%s\n%s" % (title, len(items), why, "\n".join("  - " + i for i in items)))

    clips = {r: n for r, n in notes.items() if r.startswith("Clippings/")}
    section("Unused clippings", "Filed %d+ days ago, nothing links to them, nothing written below the marker. "
            "Candidates for `trash`." % args.days,
            [r for r, n in clips.items() if old(day(n["fm"].get("filed", ""))) and not used(n)])
    section("Waiting too long", "Imported 7+ days ago and never filed. Run the librarian.",
            [r for r, n in notes.items() if "ingested" in n["fm"] and "filed" not in n["fm"]
             and (today - (day(n["fm"]["ingested"]) or today)).days >= 7])
    section("Old drafts", "status: draft for %d+ days. Verify, rewrite or delete." % args.days,
            [r for r, n in notes.items() if n["fm"].get("status") == "draft" and old(day(n["fm"].get("created", "")))])
    section("Stale notes", "Contradicted by something newer. Rewrite or delete.",
            [r for r, n in notes.items() if n["fm"].get("status") == "stale"])
    topic_use: dict = {}
    for r, n in notes.items():
        if not r.startswith("Categories/"):
            for t in LINK_TO.findall(n["fm"].get("categories", "")):
                topic_use[t.strip().lower()] = topic_use.get(t.strip().lower(), 0) + 1
    section("Thin topics", "A topic page with one note or none. Merge into a broader topic, or wait.",
            ["%s (%d)" % (r, topic_use.get(n["name"].lower(), 0)) for r, n in notes.items()
             if r.startswith("Categories/") and topic_use.get(n["name"].lower(), 0) <= 1])
    section("Quiet people", "A person page made %d+ days ago that at most one note mentions." % args.days,
            [r for r, n in notes.items() if r.startswith("People/") and old(day(n["fm"].get("created", "")))
             and inbound.get(n["name"].lower(), 0) <= 1])
    by_url: dict = {}
    by_title: dict = {}
    for r, n in notes.items():
        url = n["fm"].get("url", "").strip('"')
        if url:
            by_url.setdefault(url.rstrip("/"), []).append(r)
        by_title.setdefault(re.sub(r" \(\d+\)$", "", n["name"]).lower(), []).append(r)
    dupes = [" = ".join(v) for v in list(by_url.values()) + list(by_title.values()) if len(v) > 1]
    section("Possible duplicates", "Same link or same name. Merge into one note, then trash the rest.",
            sorted(set(dupes)))
    orphans = []
    if ATTACH.is_dir():
        orphans = sorted("Attachments/" + f.name for f in ATTACH.iterdir()
                         if f.is_file() and not f.name.startswith(".") and f.name.lower() not in targets
                         and f.stem.lower() not in targets)
    section("Unused attachments", "No note embeds or links them.", orphans)
    section("Sources due", "Past their cadence in Sources.md. Pull them, or change the cadence.", due)

    stats: dict = {}
    for r, n in notes.items():
        if "ingested" in n["fm"]:
            via = n["fm"].get("via", "").strip('"') or "(no via)"
            via = next((k for k in stats if k.lower() == via.lower()), via)
            s = stats.setdefault(via, [0, 0])
            s[0] += 1
            s[1] += 1 if used(n) else 0
    if stats:
        rows = sorted(stats.items(), key=lambda kv: (-kv[1][1], -kv[1][0]))
        sections.append("## Where things come from\nImported, and how many you have linked to or written "
                        "on. A source whose notes go unused is a candidate for `Keep?: no` in Sources.md.\n"
                        + "\n".join("  - %s: %d imported, %d used (%d%%)" % (v, a, b, round(100 * b / a))
                                     for v, (a, b) in rows))
    print("\n\n".join(sections) if sections else "Nothing to prune. The vault is in good shape.")


def cmd_trash(args) -> None:
    """Move one unused clipping or attachment to .trash/, which Obsidian and git both ignore."""
    name = unicodedata.normalize("NFC", args.name.strip())
    trash = VAULT / ".trash"
    notes, inbound, targets = scan()
    att = ATTACH / name
    if att.is_file():
        if name.lower() in targets or att.stem.lower() in targets:
            sys.exit("Refused: a note still embeds or links %s." % name)
        trash.mkdir(exist_ok=True)
        shutil.move(str(att), str(trash / name))
        print("TRASHED  Attachments/%s" % name)
        return
    stem = name[:-3] if name.endswith(".md") else name
    match = [n for r, n in notes.items() if r.startswith("Clippings/") and n["name"] == stem]
    if not match:
        sys.exit("Refused: no clipping named %r. Only clippings and attachments can be trashed here; "
                 "your own notes are only ever deleted by you, in Obsidian." % stem)
    n = match[0]
    if inbound.get(stem.lower(), 0):
        sys.exit("Refused: %d note(s) link to %r. Remove those links first, or keep it." % (inbound[stem.lower()], stem))
    if own_text(n["body"]):
        sys.exit("Refused: you wrote something below the ingest:end marker in %r." % stem)
    trash.mkdir(exist_ok=True)
    shutil.move(str(n["path"]), str(trash / n["path"].name))
    find.rebuild(str(VAULT))
    print("TRASHED  Clippings/%s.md  (restore it from .trash/ or Obsidian's file recovery)" % stem)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="bring in files, folders or URLs")
    a.add_argument("items", nargs="*")
    a.add_argument("--mine", action="store_true", help="you wrote these: file them with your own notes")
    a.add_argument("--links", help="a text file with one URL per line")
    a.add_argument("--via", help="where these came from, as named in Sources.md (\"Voice memos\")")
    a.add_argument("--vault", help="an existing Obsidian vault: proposes a mapping, or imports with --map")
    a.add_argument("--map", action="append", metavar="FOLDER=KIND",
                   help="with --vault: send a folder of it (. for its top level, dates for notes titled "
                        "YYYY-MM-DD) to a kind folder here; repeat for each folder")
    a.add_argument("--sample", type=int, metavar="N", help="with --vault: import the first N notes and stop")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=cmd_add)
    w = sub.add_parser("waiting", help="list notes not yet filed")
    w.set_defaults(func=cmd_waiting)
    r = sub.add_parser("rename", help="rename a waiting note")
    r.add_argument("old")
    r.add_argument("new")
    r.set_defaults(func=cmd_rename)
    rp = sub.add_parser("report", help="what to prune, which sources are due, which earn their place")
    rp.add_argument("--days", type=int, default=30, help="how old before something counts as unused (30)")
    rp.add_argument("--due", action="store_true", help="only the sources that are due a pull")
    rp.set_defaults(func=cmd_report)
    tr = sub.add_parser("trash", help="move an unused clipping or attachment to .trash/")
    tr.add_argument("name")
    tr.set_defaults(func=cmd_trash)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
