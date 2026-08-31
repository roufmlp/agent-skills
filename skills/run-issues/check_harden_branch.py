#!/usr/bin/env python3
"""Refuse to start a run while an unmerged hardening branch holds the same issues.

`/harden-issues` writes its work to a branch. Until that branch merges, the issue
files on main are the unhardened ones, and a run reading them cannot see the
criteria a hardening pass already wrote. Both sessions then work the same files at
the same time, and the later merge has to reconcile shipped code against criteria
that were authored without it.

**Run `bridge-cse`, 2026-08-24, is the recorded instance.** It built issues 408,
407, 409 and 338 from unhardened files. A peer `/harden-issues` session had already
hardened all four on `claude/harden-issues-407-408-ce713b`, held off merging while
the run held the files, and messaged the run mid-issue with five findings. The run
re-derived all five from source, and all five held. That branch merged at 23:12,
about ten hours after the run finished the same four files without it.

The measurement matters more than the story: the hardening existed, on disk, before
the run started. Nothing read it, because nothing looked.

Two refusals:

    overlap     an unmerged `claude/harden-issues-*` branch changes a tracker file
                naming an issue in this batch
    git-failed  the branch list or a diff could not be read, so nothing is assumed

The remedy is to merge the hardening branch and re-read the issue files, which costs
a fast-forward: those branches touch `.scratch/` only.

This does NOT check that the hardening is any good, and it says nothing about a
branch that holds different issues. One guard, one fault.

The human approved this on 2026-08-24.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

# The tracker's two issue-bearing directories. A path outside them names no issue:
# `src/lib/tenders/repo.ts` must never be read as an id.
TRACKER_PATH = re.compile(r"(?:^|/)(?:issues|harden)/([^/]+)$")

# Ids inside the filename itself. `seam-407-408-338.md` covers three issues and is a
# real filename on main, so every id in the name counts, not only a leading one.
ID_IN_NAME = re.compile(r"(?<![0-9a-z])(\d+[a-z]?)(?![0-9a-z])")

HARDEN_BRANCH_GLOB = "refs/heads/claude/harden-issues-*"

REMEDY = (
    "Merge the hardening branch into main, re-read the issue files, then launch. "
    "Those branches touch `.scratch/` only, so the merge is a fast-forward and no "
    "source moves. Measured on run `bridge-cse`, 2026-08-24: the run built four "
    "issues from unhardened files while a peer session held hardened copies of all "
    "four, and that branch merged ten hours later."
)


@dataclass(frozen=True)
class Clash:
    branch: str
    issues: set[str]


def ids_touched(paths: list[str]) -> set[str]:
    """Every issue id named by a changed tracker path."""
    found: set[str] = set()
    for path in paths:
        inside = TRACKER_PATH.search(path)
        if not inside:
            continue
        found.update(ID_IN_NAME.findall(inside.group(1)))
    return found


def judge(batch: set[str], branches: list[tuple[str, list[str]]]) -> tuple[bool, list[Clash]]:
    clashes = []
    for name, paths in branches:
        shared = ids_touched(paths) & batch
        if shared:
            clashes.append(Clash(name, shared))
    return not clashes, clashes


def git(repo: pathlib.Path, args: list[str]) -> str:
    """git, run as a list and never through a shell."""
    done = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def unmerged_harden_branches(repo: pathlib.Path, base: str) -> list[tuple[str, list[str]]]:
    """Every `claude/harden-issues-*` branch not yet in `base`, with what it changes.

    A branch already merged holds nothing the base does not, so it cannot collide.
    `merge-base --is-ancestor` is the question "is this branch already in main", and
    it answers with an exit code rather than output.
    """
    listing = git(repo, ["for-each-ref", "--format=%(refname:short)", HARDEN_BRANCH_GLOB])
    branches = []
    for name in listing.split():
        merged = subprocess.run(
            ["git", "merge-base", "--is-ancestor", name, base],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if merged.returncode == 0:
            continue
        changed = git(repo, ["diff", "--name-only", f"{base}...{name}"]).splitlines()
        branches.append((name, changed))
    return branches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a run while an unmerged hardening branch holds the same issues.",
    )
    parser.add_argument(
        "--issue",
        required=True,
        action="append",
        dest="issues",
        help="issue id in this batch, e.g. --issue 408; repeat for each",
    )
    parser.add_argument("--repo", default=".", help="repository to read (default: cwd)")
    parser.add_argument("--base", default="main", help="branch the run forks from (default: main)")
    args = parser.parse_args()

    repo = pathlib.Path(args.repo)
    try:
        branches = unmerged_harden_branches(repo, args.base)
    except (subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, "stderr", "") or error
        print(f"REFUSED git-failed: {detail}", file=sys.stderr)
        return 2

    allowed, clashes = judge(set(args.issues), branches)
    if allowed:
        # Print BOTH counts. The branch count alone is a vacuous green when
        # `TRACKER_PATH` matches nothing — a repo whose issue files sit outside
        # `issues/` or `harden/` reads as "three branches, no clash" when the
        # truth is "three branches, no issue id could be read from any of
        # them". `rn414a-01` on run `414a-483-286335` is the same shape one
        # layer down, so this says the number it actually graded on.
        read = sorted({one for _, paths in branches for one in ids_touched(paths)})
        seen = f"{len(read)} issue id(s) read from their tracker paths"
        if branches and not read:
            seen += (
                " — NONE, so this green rests on no evidence: check that this "
                "repo keeps its issue files under `issues/` or `harden/`"
            )
        print(
            f"ok: {len(branches)} unmerged hardening branch(es), {seen}, "
            "none holding an issue in this batch"
        )
        return 0

    for clash in clashes:
        held = ", ".join(sorted(clash.issues))
        print(f"REFUSED overlap: `{clash.branch}` holds {held}", file=sys.stderr)
    print(f"\n{REMEDY}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
