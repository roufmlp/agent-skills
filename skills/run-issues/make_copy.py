#!/usr/bin/env python3
"""Make a gate's private copy of the run tree: git history, the uncommitted work,
and the run tree's own `node_modules` through a symlink.

    python3 ~/.claude/skills/run-issues/make_copy.py --tree <run worktree> --dest <copy>

The perf audit of 2026-09-28 (one project, `.scratch/workflow-audit/
perf-audit-2026-09-28/`, audit-pair1.md section 2 and audit-pair2.md section 5).

## Why

The old recipe was `rsync --exclude .git`, then a `node_modules` symlink. With no
`.git` in the copy, every test that reads history is red by construction: 11
"not a git repository" errors in each of the 8 recorded verify suites of one
pair of runs, and 4 git-reading files red in every copy suite of the next pair.
Each verify gate then made a SECOND copy with `git clone --shared` and ran again,
70 to 77 seconds plus the diagnosis. This is that second copy, made once.

## Why `git clone --shared` and not `cp -al`

`cp -al` makes hard links, so a write in the copy lands in the run tree, and
every gate drill writes (`SKILL.md` records the one that nearly shipped a
mutant). A linked worktree's `.git` is also a FILE naming the run tree's own git
directory, so git in a `cp -al` copy would move the run tree's index and HEAD.
`git clone --shared` gives the copy its own `.git`, index and HEAD, and borrows
the object store through `objects/info/alternates`, so no object is copied. It
carries committed history only, so the working tree, uncommitted work
included, is laid over it with the rsync the old recipe used, and `git reset`
points the index at HEAD. `git status` in the copy then reads as it does in
the run tree.

## What it guarantees, and checks

1. The copy hashes to the run tree (`run_suite.tree_hash`). The run tree's
   `info/exclude` is copied in, and `/node_modules` is added to it, because git
   reads a symlink as a file and a `node_modules/` pattern does not match one.
   A copy that hashes elsewhere is deleted and refused: `run_suite.py --stage
   verify` reuses the implementer's suite record only at the same hash.
2. `git config run-suite.source` names the run tree. That is how `run_suite.py
   --stage verify` finds the implementer's records, and it refuses a copy that
   lacks it.
3. It refuses a destination that holds anything, and one inside the run tree,
   where the run tree's own suite would read it.

The copy is for tests and drills. `npm run build` still panics on the symlink
under Turbopack, and a build keeps its `cp -al` copy (`SKILL.md` step 4).

Exit codes: 0 the copy is made; 1 it hashed to another tree and was deleted;
3 refused, nothing made.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_suite  # noqa: E402

REFUSED = 3
SOURCE_KEY = "run-suite.source"
# The old recipe's three exclusions, unchanged.
EXCLUDED = ("node_modules", ".next", ".git")


def git(tree, *args):
    return subprocess.run(["git", "-C", str(tree), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def refuse(why: str) -> int:
    print(f"REFUSED: {why}")
    return REFUSED


def make(tree: pathlib.Path, dest: pathlib.Path) -> None:
    git(tree.parent, "clone", "-q", "--shared", "--no-checkout", str(tree), str(dest))
    rsync = ["rsync", "-a"]
    for name in EXCLUDED:
        rsync += ["--exclude", name]
    subprocess.run([*rsync, f"{tree}/", f"{dest}/"], check=True,
                   capture_output=True, text=True)
    git(dest, "reset", "-q")
    exclude = pathlib.Path(git(tree, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = tree / exclude
    lines = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    (dest / ".git" / "info").mkdir(exist_ok=True)
    (dest / ".git" / "info" / "exclude").write_text(lines + "\n/node_modules\n",
                                                   encoding="utf-8")
    if (tree / "node_modules").is_dir():
        (dest / "node_modules").symlink_to(tree / "node_modules")
    git(dest, "config", SOURCE_KEY, str(tree))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tree", required=True, help="The run worktree.")
    parser.add_argument("--dest", required=True,
                        help="Where the copy goes: a path naming the issue and the role.")
    args = parser.parse_args(argv)

    try:
        tree = pathlib.Path(git(args.tree, "rev-parse", "--show-toplevel")).resolve()
    except (subprocess.CalledProcessError, OSError):
        return refuse(f"{args.tree} is not a git work tree, so there is no history "
                      f"to copy.")
    dest = pathlib.Path(args.dest).resolve()
    if dest == tree or tree in dest.parents:
        return refuse(f"{dest} is inside the run tree {tree}, where the run tree's "
                      f"own suite would read it. Put the copy outside it.")
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        return refuse(f"{dest} already holds files. It may be another gate's copy, "
                      f"so it is left alone. Name a new path.")
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        make(tree, dest)
        tree_id, copy_id = run_suite.tree_hash(tree), run_suite.tree_hash(dest)
    except (subprocess.CalledProcessError, OSError) as error:
        shutil.rmtree(dest, ignore_errors=True)
        detail = getattr(error, "stderr", None) or str(error)
        return refuse(f"the copy could not be made ({detail.strip()}). Nothing is "
                      f"left at {dest}.")
    if copy_id != tree_id:
        differ = git(dest, "diff", "--name-only", tree_id, copy_id)
        shutil.rmtree(dest, ignore_errors=True)
        print(f"FAILED: the copy hashed to {copy_id} and the run tree to {tree_id}. "
              f"These paths differ:\n{differ}\nThe copy is deleted.")
        return 1

    print(f"copy {dest}\nof   {tree}\ntree {tree_id} (the same in both)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
