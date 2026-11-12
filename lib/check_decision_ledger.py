#!/usr/bin/env python3
"""Refuse a decision walk that ends without a costed ledger.

The human ruled this on 2026-08-30, extending their rule of 2026-08-08. That earlier
rule asked every walk to end with what was decided and what each decision costs
to reverse. It lived as prose in a memory file, so it depended on an agent
remembering it, and the three-class test in the steering docs says a reminder
does not work.

What 2026-08-30 added: the estimates are wanted after the decision is taken, so
that anything unusual or doubtful can be overruled on the strength of them, and
they are wanted every time. So the ledger
now carries four costs per ruling rather than one, and this script is what
refuses a walk that skips them.

It grades SHAPE, never quality. It can tell that a ruling has no token estimate
beside it. It cannot tell that the estimate is wrong. Say so when reporting a
pass: a green run here means the ledger is complete, not that it is right.

    python3 check_decision_ledger.py <file.md> [--rulings N]

Exit 0 with "ok" when the ledger is present and complete. Exit 1 and print every
reason otherwise. Exit 2 on a usage error, so a broken invocation never reads as
a pass.
"""

from __future__ import annotations

import argparse
import re
import sys

# The heading that opens the ledger. Matched case-insensitively, at any depth,
# so a walk may nest it under its own section without defeating the check.
LEDGER_HEADING = re.compile(r"^#{1,6}\s+.*decision ledger", re.IGNORECASE)

# The six columns, each named by the words it may be headed with. A walk may
# word a header its own way as long as the meaning stays findable.
REQUIRED_COLUMNS = {
    "what": ("what", "decision", "item", "#"),
    "ruling": ("ruling", "your ruling", "answer", "ruled"),
    "reverse": ("reverse", "reversal", "cost to reverse", "undo"),
    "time": ("time", "clock", "hours"),
    "tokens": ("tokens", "token", "spend"),
    "workflow": ("workflow", "effect", "what it buys", "improvement"),
}

# Text that fills a cell without answering it. A ledger row reading "TBD" is the
# failure this script exists to catch, not a partial pass.
PLACEHOLDERS = {
    "", "-", "--", "—", "?", "??", "n/a", "na", "tbd", "todo", "unknown",
    "unclear", "tk", "...", "___", "none yet", "to be measured",
}


def split_row(line: str) -> list[str]:
    """Cells of one markdown table row, outer pipes dropped."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def is_separator(line: str) -> bool:
    """The `|---|---|` line under a markdown table header."""
    cells = split_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def headings_in(lines: list[str]) -> list[str]:
    """Every `decision ledger` heading in the file, in order, without its `#`s.

    Used only to make a `--heading` refusal useful: a caller that names the
    wrong one is told which ones exist rather than left to grep.
    """
    return [line.lstrip("#").strip()
            for line in lines if LEDGER_HEADING.match(line)]


def find_ledger(lines: list[str],
                heading: str | None = None
                ) -> tuple[list[str], list[list[str]]] | None:
    """The table under a `decision ledger` heading, or None.

    With no `heading`, the FIRST such heading in the file, which is what this
    did before and what every existing caller still gets.

    With one, the first heading whose text contains it, case-insensitively.
    A ticket file collects one ledger per sitting, so these files hold several:
    on 2026-09-06 ticket 37 held three and this graded the 8-row grilling table
    at line 253, never seeing sitting 2's at line 432. Asked for 6 rulings it
    refused and named 8. It can fail the other way too, and that way is silent:
    answer `ok` because an OLD table is complete, while the new one is short or
    absent.

    A named heading that matches nothing returns None rather than falling back
    to the first. A fall-back would grade another sitting's table and report it
    as this one's, which is the fault this argument exists to end.

    A heading with no table under it returns None rather than an empty table,
    because "the heading is there" is exactly the near-miss that would otherwise
    read as a pass.
    """
    wanted = heading.lower() if heading else None
    for index, line in enumerate(lines):
        if not LEDGER_HEADING.match(line):
            continue
        if wanted and wanted not in line.lower():
            continue
        for offset in range(index + 1, len(lines)):
            candidate = lines[offset]
            if LEDGER_HEADING.match(candidate):
                break
            if not candidate.lstrip().startswith("|"):
                continue
            if offset + 1 >= len(lines) or not is_separator(lines[offset + 1]):
                continue
            header = split_row(candidate)
            rows = []
            for row_line in lines[offset + 2:]:
                if not row_line.lstrip().startswith("|"):
                    break
                rows.append(split_row(row_line))
            return header, rows
    return None


def match_columns(header: list[str]) -> tuple[dict[str, int], list[str]]:
    """Map each required column to its index. Report the ones not found."""
    lowered = [cell.strip().lower().strip("*` ") for cell in header]
    found: dict[str, int] = {}
    missing: list[str] = []
    for key, names in REQUIRED_COLUMNS.items():
        for position, cell in enumerate(lowered):
            if any(name in cell for name in names):
                found[key] = position
                break
        else:
            missing.append(key)
    return found, missing


def check(text: str, expected_rulings: int | None = None,
          heading: str | None = None) -> list[str]:
    """Every reason to refuse. An empty list means the ledger passes."""
    lines = text.splitlines()
    ledger = find_ledger(lines, heading)
    if ledger is None and heading:
        found = headings_in(lines)
        return [
            f"No decision ledger heading contains {heading!r}, or the one that "
            "does has no table under it. This is NOT a fall-back to the first "
            "ledger: grading another sitting's table and reporting it as this "
            "one's is the fault --heading exists to end. Headings in this "
            f"file: {', '.join(repr(one) for one in found) or 'none'}."
        ]
    if ledger is None:
        return [
            "No decision ledger found. A walk ends with a heading containing "
            "'decision ledger' and a markdown table under it. The human ruled this "
            "on 2026-08-30: the ledger is read AFTER ruling, so a decision "
            "already taken can still be overruled."
        ]

    header, rows = ledger
    problems: list[str] = []

    columns, missing = match_columns(header)
    if missing:
        problems.append(
            "The ledger is missing a column for: "
            + ", ".join(sorted(missing))
            + ". Every ruling carries what it was, the ruling, the cost to "
            "reverse it, and the effect on time, on tokens and on the workflow."
        )

    if not rows:
        problems.append("The ledger has a header and no rows.")

    for number, row in enumerate(rows, start=1):
        for key, position in sorted(columns.items()):
            if position >= len(row):
                problems.append(f"Row {number} has no '{key}' cell.")
                continue
            value = row[position].strip().strip("*` ")
            if value.lower() in PLACEHOLDERS:
                problems.append(
                    f"Row {number} leaves '{key}' unanswered: {row[position]!r}."
                )

    if expected_rulings is not None and len(rows) != expected_rulings:
        problems.append(
            f"The walk took {expected_rulings} ruling(s) and the ledger has "
            f"{len(rows)} row(s). Every ruling gets a row."
        )

    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Grade a decision walk's ledger.")
    parser.add_argument("path", help="markdown file holding the walk's ledger")
    parser.add_argument(
        "--rulings",
        type=int,
        default=None,
        help="how many rulings the walk took; the ledger must have that many rows",
    )
    parser.add_argument(
        "--heading",
        default=None,
        help="grade the ledger whose heading contains this text, e.g. "
             "'sitting 2'. Without it the FIRST 'decision ledger' heading in "
             "the file is graded, which is wrong in a file holding one ledger "
             "per sitting: on 2026-09-06 ticket 37 held three and the first "
             "was the grilling's own costs table.",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        # A file we cannot read is not a pass. Exit 2, so a mistyped path is
        # never mistaken for a clean ledger.
        print(f"check_decision_ledger: cannot read {args.path}: {error}")
        return 2

    problems = check(text, args.rulings, args.heading)
    if problems:
        print("check_decision_ledger: REFUSED")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    # Say the row count. `check()` already refuses a header with no rows, so
    # this cannot be zero — printing it anyway keeps `ok` and `ok over nothing`
    # different sentences everywhere in the pipeline, which is what run
    # `414a-483-286335` cost a hidden fault to learn (`rn414a-01`).
    found = find_ledger(text.splitlines(), args.heading)
    rows = len(found[1]) if found else 0
    # The caveat is not optional: `~/.claude/questionrules.md` says this
    # checker's pass may never be reported as more than "the ledger is
    # complete". Built as one string so that a later edit cannot detach it,
    # which an inline conditional did on 2026-09-06 and dropped it silently
    # from the --heading branch.
    where = f" from {args.heading!r}" if args.heading else ""
    print(
        f"check_decision_ledger: ok, {rows} ruling row(s) read{where}. The "
        "ledger is COMPLETE, which is not the same as correct — this checks "
        "shape, never whether an estimate is right."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
