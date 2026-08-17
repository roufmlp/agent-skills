#!/usr/bin/env python3
"""Print the one live /run-issues ledger, or exit non-zero saying what it found.

`resume` with no issue range is ambiguous: every worktree carries its own
`.scratch/<feature>/run.md`. On 2026-08-16 that was twelve copies of which one
was live. Run state is committed, so every worktree branched from that commit
carries a copy frozen at whatever the ledger said when it branched.

Two lines decide it, and neither is a timestamp:

  Worktree:  the only real copy is the one whose `Worktree:` line names the tree
             it is sitting in. Every other copy is a snapshot — never resume
             from one, never write to one.
  Owner:     a named session is live, and `none — HALTED` is live too, because a
             halt is exactly what `resume` resumes. `none — awaiting-merge`,
             `none — merged` and a missing line are finished paperwork.

Never pick by timestamp. On one measured chase the freshest ledger belonged to
an already-merged run and chasing it cost 25 minutes.

Exit 0 prints exactly one path on stdout. Exit 1 prints what it found on stderr
and chooses nothing — a launch-time stop, before anything is spawned, is not a
mid-run stall.

Usage:
    find_live_ledger.py [--issues 348,345] [--repo /path/to/checkout]
"""

import argparse
import glob
import os
import subprocess
import sys
from dataclasses import dataclass

HEAD_LINES = 60


@dataclass(frozen=True)
class Candidate:
    """One `run.md` copy, reduced to the lines the selector reads."""

    path: str
    tree: str
    worktree_line: str | None
    owner_line: str | None
    scope_text: str = ""


def parse_worktree_value(line):
    """The path a `Worktree:` line names, or None. The ledger writes backticks."""
    if not line:
        return None
    value = line.split(":", 1)[1] if ":" in line else ""
    value = value.strip().strip("`").strip()
    value = value.rstrip("/")
    return value or None


def is_admissible_owner(line):
    """True when the owner line describes a run that still has somewhere to go."""
    if not line:
        return False
    value = line.split(":", 1)[1] if ":" in line else ""
    value = value.strip()
    if not value:
        return False
    if not value.lower().lstrip("*`_ ").startswith("none"):
        return True
    return "halted" in value.lower()


def names_own_tree(candidate):
    """True when this copy's `Worktree:` line names the tree it sits in."""
    named = parse_worktree_value(candidate.worktree_line)
    if not named:
        return False
    return os.path.realpath(named) == os.path.realpath(candidate.tree)


def _describe(candidates):
    lines = []
    for c in candidates:
        named = parse_worktree_value(c.worktree_line) or "no Worktree: line"
        owner = (c.owner_line or "NO OWNER LINE").strip()
        lines.append(f"  {c.path}\n    {owner}\n    Worktree: {named}")
    return "\n".join(lines)


def select_ledger(candidates, issues=None):
    """Return (path, None) for exactly one live ledger, else (None, reason)."""
    live = [
        c for c in candidates
        if names_own_tree(c) and is_admissible_owner(c.owner_line)
    ]

    if len(live) == 1:
        return live[0].path, None

    if not live:
        return None, (
            "No live ledger found. Every copy examined is a snapshot (its "
            "Worktree: line names another tree) or finished paperwork (no "
            "owner line, or awaiting-merge/merged).\n"
            f"Examined {len(candidates)} copies:\n{_describe(candidates)}"
        )

    if issues:
        matched = [
            c for c in live
            if all(issue in c.scope_text for issue in issues)
        ]
        if len(matched) == 1:
            return matched[0].path, None

    hint = (
        " The issue range matched none of them, or more than one."
        if issues else
        " Re-run with --issues to split them by scope."
    )
    return None, (
        f"{len(live)} live ledgers. Choosing between them needs a human.{hint}\n"
        f"{_describe(live)}"
    )


def collect_candidates(repo=None):
    """Every `.scratch/*/run.md` under every worktree of this repository."""
    cmd = ["git"]
    if repo:
        cmd += ["-C", repo]
    cmd += ["worktree", "list", "--porcelain"]
    listing = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    ).stdout

    candidates = []
    for line in listing.splitlines():
        if not line.startswith("worktree "):
            continue
        tree = line[len("worktree "):].strip()
        for path in glob.glob(os.path.join(tree, ".scratch", "*", "run.md")):
            candidates.append(_read(path, tree))
    return candidates


def _read(path, tree):
    owner = worktree = None
    scope = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for index, line in enumerate(handle):
                if index >= HEAD_LINES:
                    break
                if owner is None and line.startswith("Owner:"):
                    owner = line.rstrip("\n")
                elif worktree is None and line.startswith("Worktree:"):
                    worktree = line.rstrip("\n")
                elif line.startswith("Scope"):
                    scope.append(line.rstrip("\n"))
    except OSError as error:
        print(f"warning: cannot read {path}: {error}", file=sys.stderr)
    return Candidate(path, tree, worktree, owner, "\n".join(scope))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--issues",
        help="comma-separated issue ids, used only to split two live ledgers",
    )
    parser.add_argument("--repo", help="checkout to enumerate; defaults to cwd")
    args = parser.parse_args(argv)

    issues = None
    if args.issues:
        issues = [part.strip() for part in args.issues.split(",") if part.strip()]

    try:
        candidates = collect_candidates(args.repo)
    except subprocess.CalledProcessError as error:
        print(
            f"Cannot enumerate worktrees: {error.stderr or error}".strip(),
            file=sys.stderr,
        )
        return 1

    path, reason = select_ledger(candidates, issues)
    if path:
        print(path)
        return 0
    print(reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
