#!/usr/bin/env python3
"""Rebuild starter-vault/ from the seed: the personal preset with a placeholder owner.

    python3 tools/build_starter.py           rebuild it
    python3 tools/build_starter.py --check   exit 1 if it is out of date (tools/check.py runs this)

starter-vault/ is for people who download the ZIP and never open a terminal, so it
must be exactly what `setup/build_vault.py --preset personal` makes, never hand-edited. It is
seeded outside any git repo, so its .claude/settings.json lands inside it.
"""
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "setup", "build_vault.py")
DEST = os.path.join(ROOT, "starter-vault")
DATE = "2026-10-10"  # fixed, so a rebuild is not a diff; bump it when the starter changes


def build(where):
    vault = os.path.join(where, "starter-vault")
    subprocess.run([sys.executable, SEED, "--preset", "personal", "--dest", vault,
                    "--name", "My Second Brain", "--owner", "the owner", "--project", "its owner",
                    "--date", DATE],
                   check=True, capture_output=True)
    for root, _, files in os.walk(vault):
        for fn in files:
            if fn.endswith(".md"):
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                fixed = text.replace(". the owner", ". The owner")
                if fixed != text:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(fixed)
    return vault


def differs(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return True
    return any(differs(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build(tmp)
        if "--check" in sys.argv:
            if not os.path.isdir(DEST) or differs(fresh, DEST):
                sys.exit("starter-vault/ is out of date: run python3 tools/build_starter.py")
            print("starter-vault/ is up to date")
            return
        shutil.rmtree(DEST, ignore_errors=True)
        shutil.copytree(fresh, DEST)
        print("rebuilt %s" % DEST)


if __name__ == "__main__":
    main()
