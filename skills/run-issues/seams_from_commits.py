#!/usr/bin/env python3
"""The files more than one issue of a run touched, taken from the commits.

## Why the predicted list is not enough

A run hands its finale a seam list derived from what the issue files said they
would touch. That list can only name a seam somebody predicted.

Run `batch-b00631` predicted four. One command over the actual commits found a
fifth: `src/model/confirm.ts`, edited by both issue 21c and issue 110. Four files
on the whole branch were touched by more than one issue and the run's list named
three of them.

It cost that run nothing -- the finale read both hunks, they sit in different
regions of the file, share no symbol and have not drifted -- and the finale
derived the fifth itself, unprompted. The human ruled `q-fin-b00631-04` on
2026-09-19 all the same: the check that cannot miss one costs a single command,
and the case it catches is an implementer touching a file its issue never
mentioned, which is exactly the case a predicted list cannot see.

## What it reads

The ledger's `## Status` table names one commit per issue. `check_commit_order.py`
owns that table's parser and the `committed <sha>` pattern, so both are imported
rather than copied.

Measured on `batch-b00631`: seventeen commits on the branch, six of them code,
one per issue, every one named by a ledger row. The rest are bookkeeping -- a
`Mark issue <id> done` commit per issue, two promotion commits and the records.
So the ledger's shas are the code, and a file this reports was genuinely edited
under two issues.

WHAT IT DOES NOT REACH, said plainly. A commit on the branch that no ledger row
names is invisible here. That is why `--base` exists: given the fork point, this
counts those commits and says how many it could not attribute, so a reader knows
whether the answer covers the branch or part of it. It does not guess which
issue they belong to.

## The run's own records are not seams

Every issue's commit writes the ledger, the primer and the merge briefing, so a
plain count reports them as touched by all six issues. That is true and useless.
They are reported in a second list under their own heading rather than dropped,
because a reader who wanted them should not have to run a different command, and
a reader who did not should not have to sort them out of the answer. `--records`
names the prefix; it defaults to `.scratch/`, which is where this pack's own
skills put the tracker, the run state and the register shards. A project that
keeps them somewhere else names its own prefix.

This REPORTS. It is not a gate and it refuses nothing about the seams it finds:
two issues editing one file is ordinary, and whether it matters is the finale's
judgement to make with both hunks in front of it. The one thing it refuses is
answering at all when it read no commits, because "no seams" and "no input" look
identical in a report and mean opposite things.

Usage:

    python3 seams_from_commits.py --ledger <run.md> --repo . \\
        [--base <fork point> --tip <branch>] [--records <prefix>]

Exit 0 when a report was produced, 1 on an empty-input refusal, 2 when git or
the ledger could not be read.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import subprocess
import sys

import check_commit_order
import empty_input


def committed_shas(text):
    """`(issue, sha)` for every status row that names a commit, in ledger order."""
    found = []
    for issue, line in check_commit_order.status_rows(text):
        stamp = check_commit_order.COMMITTED.search(line)
        if stamp:
            found.append((issue, stamp.group("sha")))
    return found


def files_in(repo, sha):
    """Every path the commit touched.

    `--format=` empties the header so only the name list is read, and a merge
    would print nothing here rather than the wrong thing. A failure raises: a
    commit that cannot be read is never treated as a commit that touched
    nothing, which would quietly shrink every seam.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "show", "--name-only", "--format=", sha],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show {sha} failed: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


DEFAULT_RECORDS = (".scratch/",)


def split_records(found, prefixes=DEFAULT_RECORDS):
    """`(code, records)`, the second being paths under one of `prefixes`.

    Nothing is dropped. A run's ledger and briefing genuinely are touched by
    every issue, and a reader who wants that still gets it -- under its own
    heading, where it cannot be mistaken for an implementer straying into a
    file its issue never named.
    """
    code, records = {}, {}
    for path, issues in found.items():
        target = records if any(path.startswith(prefix) for prefix in prefixes) else code
        target[path] = issues
    return code, records


def seams(repo, rows):
    """`path -> [issues]` for every path more than one issue touched.

    Sorted by path so two runs of this over the same branch print the same
    thing, which is what makes it quotable in a briefing.
    """
    touched = collections.defaultdict(list)
    for issue, sha in rows:
        for path in files_in(repo, sha):
            if issue not in touched[path]:
                touched[path].append(issue)
    return {path: issues for path, issues in sorted(touched.items()) if len(issues) > 1}


def unattributed(repo, base, tip, rows):
    """Commits in `base..tip` that no ledger row names.

    Bookkeeping commits live here and are expected. The number is printed so a
    reader can see how much of the branch the report covers, rather than
    assuming it covers all of it.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-list", f"{base}..{tip}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git rev-list {base}..{tip} failed: {result.stderr.strip()}")
    named = {sha for _, sha in rows}
    return [
        sha for sha in (line.strip() for line in result.stdout.splitlines())
        if sha and not any(sha.startswith(short) for short in named)
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="path to the run's run.md")
    parser.add_argument("--repo", default=".", help="the checkout holding the commits")
    parser.add_argument("--base", help="the fork point, to count commits no row names")
    parser.add_argument("--tip", default="HEAD",
                        help="the branch tip `--base` is measured to; HEAD moves after a "
                             "merge, so a run reads its own branch by naming it")
    parser.add_argument("--records", action="append", default=None,
                        help="a path prefix holding the run's own records, reported "
                             "separately (default `.scratch/`)")
    args = parser.parse_args(argv)

    try:
        text = pathlib.Path(args.ledger).read_text(encoding="utf-8")
    except OSError as error:
        print(f"unreadable: {args.ledger}: {error}", file=sys.stderr)
        return 2

    try:
        rows = committed_shas(text)
    except (IndexError, ValueError) as error:
        print(f"unreadable: {args.ledger} holds no status table this can parse: {error}",
              file=sys.stderr)
        return 2

    # "No seams" and "no input" read the same in a report and mean opposite
    # things, so this refuses rather than printing an empty table.
    if empty_input.refuse_empty(
        len(rows),
        source=args.ledger,
        shape="a status row stamped `committed <sha>`",
        read=len(check_commit_order.status_rows(text)),
        remedy="Run this after the issues are committed. Before that there are no "
               "commits to read and the answer would be empty for the wrong reason.",
    ):
        return 1

    try:
        found = seams(args.repo, rows)
        loose = unattributed(args.repo, args.base, args.tip, rows) if args.base else None
    except RuntimeError as error:
        print(f"git-failed: {error}", file=sys.stderr)
        return 2

    print(f"{len(rows)} issue(s) read from the ledger: "
          f"{', '.join(issue for issue, _ in rows)}")
    if loose is not None:
        print(f"{len(loose)} commit(s) in {args.base}..{args.tip} named by no ledger row, "
              "so not attributed to an issue.")

    code, records = split_records(found, tuple(args.records or DEFAULT_RECORDS))

    if not code:
        print("\nno file outside the run's own records was touched by more than one issue.")
    else:
        print(f"\n{len(code)} file(s) touched by more than one issue:")
        for path, issues in code.items():
            print(f"  {path}  <- {', '.join(issues)}")

    if records:
        print(f"\n{len(records)} of the run's own record file(s), written by every issue "
              "by design and not a seam:")
        for path, issues in records.items():
            print(f"  {path}  <- {', '.join(issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
