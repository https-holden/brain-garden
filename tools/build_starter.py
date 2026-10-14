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
    """The starter, exactly as the builder makes it. Its manifest records the seed as `starter`, not
    a commit, so a new commit never makes it out of date."""
    vault = os.path.join(where, "starter-vault")
    subprocess.run([sys.executable, SEED, "--preset", "personal", "--dest", vault,
                    "--name", "My Second Brain", "--owner", "the owner", "--project", "its owner",
                    "--date", DATE, "--seed-commit", "starter"],
                   check=True, capture_output=True)
    return vault


def local_files():
    """Files git ignores inside starter-vault/ (a find log, a ledger): left by using it, not the seed."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "--others", "--ignored", "--exclude-standard",
                              "--", "starter-vault"], capture_output=True, text=True, env=env).stdout
    except OSError:
        return set()
    return {os.path.normpath(os.path.join(ROOT, p)) for p in out.splitlines() if p}


def differs(a, b, skip=frozenset()):
    cmp = filecmp.dircmp(a, b)
    right_only = [n for n in cmp.right_only if os.path.normpath(os.path.join(b, n)) not in skip]
    if cmp.left_only or right_only or cmp.diff_files or cmp.funny_files:
        return True
    return any(differs(os.path.join(a, d), os.path.join(b, d), skip) for d in cmp.common_dirs)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build(tmp)
        if "--check" in sys.argv:
            if not os.path.isdir(DEST) or differs(fresh, DEST, local_files()):
                sys.exit("starter-vault/ is out of date: run python3 tools/build_starter.py")
            print("starter-vault/ is up to date")
            return
        shutil.rmtree(DEST, ignore_errors=True)
        shutil.copytree(fresh, DEST)
        print("rebuilt %s" % DEST)


if __name__ == "__main__":
    main()
