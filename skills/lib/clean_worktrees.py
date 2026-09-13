#!/usr/bin/env python3
"""Remove the worktrees and branches a finished run left behind, and REFUSE
every one that still holds work.

## The class

Sort a proposal three ways: if it can refuse, build it; if it is a fact nobody
wrote down, write it; if it asks an agent to remember, it will not work. This
one lands in the first class. The rule it replaces was written as prose and is
measurably not obeyed.

One project's `CLAUDE.md` had carried this sentence since it was written: "A
worktree dies when its branch merges to main: clean `git status` -> `git
worktree remove` -> `git branch -d`." Measured in that repo on 2026-09-13, with
the rule present the whole time: 10 live worktrees, 53 local branches, and 38 of
them merged into main and never deleted. A second copy of that sentence in
another repo's `CLAUDE.md` would be a second reminder, and a reminder that has
already failed is never answered with another reminder.

So the sentence becomes a command that does the work and stops at anything it
cannot prove is finished.

## What it refuses, and why each one

The dangerous direction here is deletion, so every check below fails CLOSED:
anything this script cannot establish is a reason to keep the tree, never a
reason to remove it.

    main checkout        never a candidate; it is not under the worktrees dir
    the current tree     removing the tree you are standing in loses the shell
    dirty                uncommitted or untracked work; `git status --porcelain`
    detached HEAD        no branch, so "merged" has no meaning to test
    unmerged branch      NOT an ancestor of the base ref. Measured across two
                         repos on 2026-09-13: 9 such branches, one of them a run
                         branch still holding its work. Deleting one loses work
                         that no reflog in a removed worktree can return.
    live session         a process whose cwd is inside the tree still holds it

`git branch -d` is used, never `-d --force` and never `-D`. git's own refusal
is the second fence behind the ancestry test, and the two disagree only if the
base ref is wrong, which is the case worth stopping on.

`git worktree remove` is called without `--force` for the same reason: its own
dirty check is a fence this script does not reach around.

## The shard hazard, and why the ancestry test covers it

Every writing worktree owns a shard under `.scratch/decisions-queue.d/<id>/`,
which `collect_shards.py` concatenates; a removed tree whose shard never
reached main takes the human's queued decisions with it. Where `.scratch/` is
tracked by git, a merged branch has already carried its shard to main and an
unmerged one is refused above. No separate shard check is needed, and one would
go stale against the ignore rules. Untracked shard files show as dirty and are
refused. **Check that your own repo tracks `.scratch/` before trusting this**: a
repo that ignores it loses the shard with the tree.

## Usage

    python3 ~/.claude/skills/lib/clean_worktrees.py --repo <the main checkout>
    python3 ~/.claude/skills/lib/clean_worktrees.py --repo <the main checkout> --apply

Reporting is the default. `--apply` is the only form that deletes anything.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

WORKTREE_DIR = pathlib.Path(".claude") / "worktrees"


class GitError(RuntimeError):
    pass


def git(repo: str, *args: str) -> str:
    """Run one git command in `repo` and return its stdout, stripped."""
    proc = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def worktrees(repo: str) -> list[dict]:
    """Parse `git worktree list --porcelain` into one dict per tree.

    Keys: `path`, and `branch` (short name) or None for a detached HEAD.
    """
    out = git(repo, "worktree", "list", "--porcelain")
    trees, current = [], {}
    for line in out.splitlines():
        if not line.strip():
            if current:
                trees.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value, "branch": None, "detached": False}
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "detached":
            current["detached"] = True
    if current:
        trees.append(current)
    return trees


def is_merged(repo: str, branch: str, base: str) -> bool:
    """True only when `branch` is an ancestor of `base`.

    Anything that is not a clean exit 0 -- an unknown ref, an unborn base --
    is False, because the caller reads False as "keep it".
    """
    proc = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", branch, base],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def is_dirty(path: str) -> bool:
    """True when the tree has uncommitted or untracked files, or cannot be read.

    A tree git refuses to report on is dirty by this definition, so an
    unreadable tree is kept rather than removed.
    """
    proc = subprocess.run(
        ["git", "-C", path, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return True
    return bool(proc.stdout.strip())


def held_by_process(path: str) -> bool:
    """True when a running `claude` process has its cwd at or inside `path`.

    The shape is `session_alive` in `run-issues/stall_watch.py`, reused whole
    rather than in part: `lsof -a -d cwd -c claude -Fn` prints one `n<path>` line
    per claude process, which is a fixed amount of work. The obvious
    alternative, `lsof +D <path>`, walks the entire tree and would recurse
    `node_modules` on every candidate.

    Where `lsof` is missing, fails, or is slow enough to time out this returns
    True and the tree is kept. A tool that did not answer must never read as
    "nothing is running".
    """
    want = os.path.realpath(path)
    try:
        proc = subprocess.run(
            ["lsof", "-a", "-d", "cwd", "-c", "claude", "-Fn"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    for line in proc.stdout.splitlines():
        if not line.startswith("n"):
            continue
        cwd = os.path.realpath(line[1:])
        if cwd == want or cwd.startswith(want + os.sep):
            return True
    return False


def judge(repo: str, tree: dict, base: str, here: str) -> tuple[bool, str]:
    """Decide one worktree. Returns (removable, reason)."""
    path = tree["path"]
    if os.path.realpath(path) == os.path.realpath(repo):
        return False, "the main checkout"
    if os.path.realpath(path) == os.path.realpath(here):
        return False, "the tree this command is running in"
    if tree.get("detached") or not tree.get("branch"):
        return False, "detached HEAD, so there is no branch to test"
    if is_dirty(path):
        return False, "uncommitted or untracked work in the tree"
    if not is_merged(repo, tree["branch"], base):
        return False, f"{tree['branch']} is not merged into {base}"
    if held_by_process(path):
        return False, "a running process still sits in the tree"
    return True, f"{tree['branch']} is merged into {base}"


def stale_branches(repo: str, base: str, live: set[str]) -> list[str]:
    """Branches merged into `base` that no worktree holds.

    `base` itself is never returned.
    """
    out = git(repo, "branch", "--merged", base, "--format=%(refname:short)")
    return [
        b for b in out.splitlines()
        if b and b != base and b not in live
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove merged worktrees and branches; refuse everything else.")
    parser.add_argument("--repo", required=True, help="path to the main checkout")
    parser.add_argument("--base", default="main", help="the ref a branch must be merged into")
    parser.add_argument("--apply", action="store_true",
                        help="delete. Without it nothing is removed.")
    args = parser.parse_args(argv)

    repo = os.path.realpath(args.repo)
    here = os.getcwd()
    try:
        trees = worktrees(repo)
    except GitError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    removable, kept = [], []
    for tree in trees:
        ok, reason = judge(repo, tree, args.base, here)
        (removable if ok else kept).append((tree, reason))

    live = {t["branch"] for t in trees if t.get("branch")}
    try:
        stale = stale_branches(repo, args.base, live)
    except GitError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for tree, reason in kept:
        print(f"KEEP   {tree['path']}  -- {reason}")
    for tree, reason in removable:
        verb = "REMOVE" if args.apply else "would remove"
        print(f"{verb} {tree['path']}  -- {reason}")
    for branch in stale:
        verb = "DELETE" if args.apply else "would delete"
        print(f"{verb} branch {branch}  -- merged into {args.base}, no worktree")

    if not args.apply:
        print(f"\nreport only. {len(removable)} tree(s) and {len(stale)} branch(es) "
              f"would go; {len(kept)} kept. Re-run with --apply to act.")
        return 0

    failed = 0
    for tree, _ in removable:
        try:
            git(repo, "worktree", "remove", tree["path"])
            git(repo, "branch", "-d", tree["branch"])
        except GitError as error:
            print(f"refused: {error}", file=sys.stderr)
            failed += 1
    for branch in stale:
        try:
            git(repo, "branch", "-d", branch)
        except GitError as error:
            print(f"refused: {error}", file=sys.stderr)
            failed += 1
    git(repo, "worktree", "prune")
    print(f"\ndone. {len(kept)} kept, {failed} refused by git.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
