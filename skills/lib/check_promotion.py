#!/usr/bin/env python3
"""Refuse a promotion past half the week's closed issues. Issue 37 of the
tracker-tooling set, rules 2 and 3 of issue 32.

The human runs this at the moment they turn a register row into an issue file.
It reads the git history of the repository that holds the tracker and counts, over
the seven days before it runs, the issues the tracker closed and the issues it
gained. It refuses the candidate when gained plus one would pass half of closed,
unless given `--over-cap "<one line of reason>"`, which it writes into the
candidate as an `Over-cap: <date> <reason>` header line. It also refuses a
`Kind: machinery` candidate in a tracker whose `README.md` lacks the line
`Tracker: machinery`, and a candidate with no `Kind:` line at all.

The dates come from git, by author date (defaults of hardening pass h0925):

- promoted: the first commit that adds a `.md` file directly inside
  `<tracker>/issues/`. A rename keeps the date of the first add under the old
  name. A file whose first commit already carries a closed `Status:` counts in
  neither total, and a deleted file counts in neither.
- closed: the first commit that sets the first word of `Status:` to a word that
  takes an issue out of the pool, as `check_issue_ready.leaves_pool` reads it.
- the candidate itself is never counted against itself, committed or not.

It creates no file, commits nothing and stages nothing. Its only write is the
`Over-cap:` line, and only into the candidate. The refusal style is
`run-issues/check_issue_ready.py`'s: `REFUSED` lines on stderr and exit 1.

Usage:
    check_promotion.py --tracker <dir> --issue <candidate.md> [--over-cap "<reason>"]
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "run-issues"))

from check_issue_ready import headers, leaves_pool  # noqa: E402

WINDOW_DAYS = 7
MACHINERY_LINE = "Tracker: machinery"
STATUS_LINE = re.compile(r"^Status:[ \t]*(.*)$", re.MULTILINE)
MACHINERY = re.compile(r"^machinery(?![\w-])")
COMMIT_MARK = "@@commit "


@dataclass
class Issue:
    added_at: int
    born_closed: bool
    closed_at: int | None = None


@dataclass
class Counts:
    closed: int
    promoted: int
    since: int
    unread: list[str] = field(default_factory=list)

    @property
    def cap(self) -> int:
        return self.closed // 2

    def allows_one_more(self) -> bool:
        # Five of ten passes and six of ten is refused: more than half refuses.
        return 2 * (self.promoted + 1) <= self.closed


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(root), *args],
        check=True, capture_output=True, text=True).stdout


def status_closed(root: Path, sha: str, path: str) -> bool:
    text = git(root, "show", f"{sha}:{path}")
    found = STATUS_LINE.search(text)
    return bool(found) and leaves_pool(found.group(1))


def history(root: Path, issues_rel: str) -> dict[str, Issue]:
    """Every issue file alive at HEAD, keyed by its path from the repo root."""
    log = git(root, "log", "--reverse", "--topo-order", "-M", "--name-status",
              f"--format={COMMIT_MARK}%H %at", "--", issues_rel)
    alive: dict[str, Issue] = {}
    sha, at = "", 0

    def is_issue(path: str) -> bool:
        pure = PurePosixPath(path)
        return str(pure.parent) == issues_rel and pure.suffix == ".md"

    for line in log.splitlines():
        if line.startswith(COMMIT_MARK):
            sha, stamp = line[len(COMMIT_MARK):].split()
            at = int(stamp)
            continue
        if not line.strip():
            continue
        parts = line.split("\t")
        change = parts[0][0]
        if change == "R":
            old, new = parts[1], parts[2]
            record = alive.pop(old, None) if is_issue(old) else None
            if not is_issue(new):
                continue
            if record is None:
                record = Issue(at, status_closed(root, sha, new))
            alive[new] = record
            path = new
        elif change == "D":
            alive.pop(parts[1], None)
            continue
        else:
            path = parts[-1]
            if not is_issue(path):
                continue
            if change == "A" or path not in alive:
                alive[path] = Issue(at, status_closed(root, sha, path))
                continue
        record = alive[path]
        if not record.born_closed and record.closed_at is None and status_closed(root, sha, path):
            record.closed_at = at
    return alive


def count(root: Path, issues_rel: str, candidate_rel: str | None, now: float) -> Counts:
    since = int(now - WINDOW_DAYS * 86400)
    closed = promoted = 0
    for path, issue in history(root, issues_rel).items():
        if issue.born_closed:
            continue
        if issue.closed_at is not None and issue.closed_at >= since:
            closed += 1
        if path != candidate_rel and issue.added_at >= since:
            promoted += 1
    return Counts(closed, promoted, since)


def kind_fault(tracker: Path, candidate_text: str) -> str | None:
    kind = headers(candidate_text).kind
    if kind is None:
        return "the candidate has no `Kind:` line, so the machinery rule cannot be applied"
    if not MACHINERY.match(kind):
        return None
    readme = tracker / "README.md"
    lines = readme.read_text().splitlines() if readme.is_file() else []
    if MACHINERY_LINE in (line.strip() for line in lines):
        return None
    return (f"`Kind: {kind}` in a product tracker: `{readme}` does not carry the line "
            f"`{MACHINERY_LINE}`")


def write_over_cap(candidate: Path, reason: str, today: str) -> None:
    """Insert the `Over-cap:` line at the end of the header block, the lines
    above the first blank one."""
    lines = candidate.read_text().split("\n")
    at = next((n for n, line in enumerate(lines) if not line.strip()), len(lines))
    lines.insert(at, f"Over-cap: {today} {reason}")
    candidate.write_text("\n".join(lines))


def refuse(message: str) -> int:
    print(f"REFUSED   {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a promotion past half the issues the tracker closed this week.")
    parser.add_argument("--tracker", required=True, help="the tracker directory, holding issues/")
    parser.add_argument("--issue", required=True, help="the candidate issue file")
    parser.add_argument("--over-cap", dest="over_cap", default=None,
                        help="one line of reason to promote past the cap; written into the candidate")
    args = parser.parse_args(argv)

    tracker = Path(args.tracker).resolve()
    candidate = Path(args.issue).resolve()
    issues = tracker / "issues"
    if args.over_cap is not None and (
            not args.over_cap.strip() or "\n" in args.over_cap or "\r" in args.over_cap):
        return refuse("--over-cap takes one line of reason, not empty and with no line break")
    if not issues.is_dir():
        return refuse(f"`{issues}` is not a directory, so this is not a tracker")
    if not candidate.is_file():
        return refuse(f"the candidate `{candidate}` is not a file")
    try:
        root = Path(git(tracker, "rev-parse", "--show-toplevel").strip()).resolve()
    except subprocess.CalledProcessError:
        return refuse(f"`{tracker}` is not inside a git repository, so nothing dates its issues")

    issues_rel = issues.relative_to(root).as_posix()
    try:
        candidate_rel = candidate.relative_to(root).as_posix()
    except ValueError:
        candidate_rel = None
    try:
        counts = count(root, issues_rel, candidate_rel, time.time())
    except subprocess.CalledProcessError as error:
        return refuse(f"git could not read the history of `{root}`: {error.stderr.strip()}")
    since = datetime.datetime.fromtimestamp(counts.since).isoformat(timespec="minutes")
    summary = (f"closed {counts.closed}, promoted {counts.promoted} since {since}; "
               f"cap {counts.cap}, half of closed")
    print(summary)

    failed = False
    fault = kind_fault(tracker, candidate.read_text())
    if fault:
        refuse(fault)
        failed = True
    over = not counts.allows_one_more()
    if over and args.over_cap is None:
        refuse(f"one more promotion passes the cap: {summary}. Close issues first, or pass "
               '--over-cap "<one line of reason>"')
        failed = True
    if failed:
        return 1
    if over:
        write_over_cap(candidate, args.over_cap.strip(), datetime.date.today().isoformat())
        print(f"over cap, reason written to {candidate}")
    elif args.over_cap is not None:
        print("within the cap, so the --over-cap reason was not written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
