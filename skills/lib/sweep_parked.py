#!/usr/bin/env python3
"""List the parked issues that want a human's eye again. It changes no file.

    python3 ~/.claude/skills/lib/sweep_parked.py <issues dir>

WHY IT EXISTS. Ruled by the human on 2026-09-13, on one project's measurement:
641 issues, 149 of them `needs-harden`, and not one of those 149 named as a
blocker by any other issue. A needs-harden issue with fan-out
zero sits last for ever under `next_batch.py`'s order, so the backlog grows and
nothing ever leaves it. Promotion now mints a medium or low row that names no
blocker as `Status: parked`, and nothing offers a parked issue: not `/run-issues
all`, not `next_batch.py`, not `/harden-issues`. **A status with no door back is a
deletion with a nicer name.** This is the door.

WHAT IT LISTS. Two kinds, and the second is the one that matters.

    AGED    parked more than thirty days, by its own `Parked:` line. The interval
            is the human's ruling of 2026-09-13.
    NAMED   some OPEN issue's `## Blocked by` names it, at any age. Open is
            `next_batch.py`'s own reading: neither `done` nor `closed`, and not
            parked itself, so two parked issues cannot hold each other on the
            list for ever. A parked issue something waits on is not backlog, it
            is a blocker, and the age has nothing to do with it.

Each row carries the issue's severity (off its `Rows:` line), its stage (off its
`Stage:` line) and its age, then the open issues that name it. A field the file
does not carry reads `-`, never a guess.

THE HARDEN LINE names the NAMED kind only, in tracker order. Hardening a parked
issue is what takes it out of parked: `/harden-issues` stamps `ready-for-agent`,
and the next `next_batch.py` places it. An aged issue nobody waits on is listed
and not offered — the human decides whether it comes back, and the list is where
they see it.

A PARKED FILE WITH NO READABLE `Parked:` DATE IS ALWAYS LISTED. It cannot be shown
to be young, and this sweep errs towards the reader seeing work rather than
towards hiding it. The row says `no Parked: date` where the age would stand.

WHAT IT READS. `next_batch.py`, imported rather than restated: which files are
issue files, what a `Status:` is, what a `## Blocked by` bullet has to look like
to be a blocker, and which severity a `Rows:` line carries. Two readers of one
tracker that disagree about what a parked issue is would be a fault neither would
report. Only `Parked:` and `Stage:`, the two fields no other tool here ranks by,
are read in this file, and they use that module's own header grammar.

ONE UNREADABLE FILE COSTS THAT FILE AND NOT THE SWEEP. A `Status:` no tool here
knows is named on stderr as `UNREADABLE <file>: <reason>`, and the sweep runs on
the rest. The human ruled it on 2026-09-18, after one unknown word in each of two
projects refused both sweeps on one day and 42 parked issues went unchecked.

Exit codes: 0 the sweep ran (whether or not it listed anything, and whether or
not a file was unreadable); 1 the tracker could not be read at all, reason on
stderr; 2 bad usage.
"""

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import next_batch  # noqa: E402

# The human's ruling of 2026-09-13. Strictly more than this many days parked is due:
# an issue parked thirty days ago is not yet.
INTERVAL_DAYS = 30

MISSING = "-"
NO_DATE = "no Parked: date"


def header_field(text: str, key: str) -> str:
    """The value of one header field above the title, or "" where there is none.

    Above the title only, and the first one wins: the same read `parse_issue`
    does for `Origin:` and `Rows:`, so a sentence in the body that happens to
    open with the word cannot pass for a field.
    """
    for line in text.splitlines():
        if next_batch.TITLE_RE.match(line):
            break
        found = next_batch.HEADER_RE.match(line)
        if found and found.group(1) == key:
            return found.group(2).strip()
    return ""


def parked_days(value: str):
    """Days since the `Parked:` date, or None where the line is absent or is not
    a date this tool can read."""
    try:
        parked = datetime.date.fromisoformat(value.split()[0])
    except (ValueError, IndexError):
        return None
    return (datetime.date.today() - parked).days


def namers(issues: dict) -> dict:
    """parked issue id -> the OPEN issues that name it under `## Blocked by`."""
    open_issues = next_batch.open_ids(issues)
    waiting = {i.id: [] for i in issues.values() if i.status == next_batch.PARKED}
    for issue in sorted(issues.values(), key=lambda i: next_batch.sort_key(i.id)):
        if issue.id not in open_issues:
            continue
        for blocker in issue.blockers:
            if blocker in waiting:
                waiting[blocker].append(issue.id)
    return waiting


def sweep(issues_dir: Path):
    """`(rows, parked total, unreadable)`, rows in tracker order. A row is
    `(id, severity, stage, age in days or None, the issues naming it)`, and
    `unreadable` is `(file, reason)` for every file no tool here can place.

    ONE FILE'S FAULT COSTS THAT FILE, NOT THE SWEEP. The human's ruling of
    2026-09-18: `Status: blocked` on one issue in one project and `Status: DONE`
    on one issue in another refused this sweep in both repositories on one day,
    and 42 parked issues went unchecked behind them. The caller names every
    unreadable file, and lists the parked issues it could read.
    """
    issues = next_batch.load_issues(issues_dir)
    waiting = namers(issues)
    rows = []
    for issue_id in sorted(waiting, key=next_batch.sort_key):
        issue = issues[issue_id]
        text = (issues_dir / issue.file).read_text(encoding="utf-8")
        age = parked_days(header_field(text, "Parked"))
        named_by = waiting[issue_id]
        if not named_by and age is not None and age <= INTERVAL_DAYS:
            continue
        rows.append((issue_id, issue.severity or MISSING,
                     header_field(text, "Stage") or MISSING, age, named_by))
    return rows, len(waiting), next_batch.unreadable(issues)


def render(rows, parked_total: int) -> str:
    if not rows:
        return (f"No parked issue is due. {parked_total} parked, none past "
                f"{INTERVAL_DAYS} days and none named by open work.\n")
    cells = [(r[0], r[1], r[2],
              f"{r[3]} days" if r[3] is not None else NO_DATE,
              ", ".join(r[4]) or MISSING) for r in rows]
    heads = ("Issue", "Severity", "Stage", "Parked", "Named by")
    widths = [max(len(head), *(len(c[n]) for c in cells))
              for n, head in enumerate(heads)]
    out = ["  ".join(head.ljust(widths[n]) for n, head in enumerate(heads)).rstrip()]
    out += ["  ".join(cell.ljust(widths[n]) for n, cell in enumerate(row)).rstrip()
            for row in cells]
    out.append("")
    out.append(f"{len(rows)} of {parked_total} parked issues listed: past "
               f"{INTERVAL_DAYS} days, or named by an open issue")
    named = [r[0] for r in rows if r[4]]
    if named:
        out.append("")
        out.append("/harden-issues " + " ".join(named))
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues_dir", type=Path)
    args = parser.parse_args(argv)
    if not args.issues_dir.is_dir():
        parser.error(f"{args.issues_dir} is not a directory")
    try:
        rows, parked_total, unreadable = sweep(args.issues_dir)
    except next_batch.Refusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1
    sys.stdout.write(render(rows, parked_total))
    # Named on stderr, so the list on stdout stays the list a reader pipes.
    for file, reason in unreadable:
        print(f"UNREADABLE {file}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
