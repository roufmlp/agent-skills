#!/usr/bin/env python3
"""Refuse an issue file that carries no criteria for a gate to grade.

An implementer is graded against criteria. Where the issue file carries none, the
runner authors them into the spawn prompt, and the run then grades its own
invention. That is not hardening: hardening is an adversarial pass over criteria
before anyone builds, and it happens in a session of its own, off the run's clock.

**Run `bridge-cse`, 2026-08-24, is what this guard exists for.** Its journal, at
`.scratch/<feature>/run-journal.md` on main, records the pre-flight read:
issues 408 and 407 "carry NO acceptance-criteria section at all — they are promoted
register rows with a 'what is wrong' and a remedy direction", so "the runner
therefore authors the graded criteria into the spawn prompts". Two citations in that
authored brief were wrong, they reached a shipped code comment, and repairing them
cost a correction round. The run took 7h49m against an estimate of 3h15m to 4h45m.

**The refusal is cheap, measured before it was built.** Of the 32 issue files reading
`Status: ready-for-agent` on 2026-08-24, exactly ONE carries neither section. This
does not stand between the runner and a hardened backlog. It stands between the
runner and a freshly promoted register row, which is the class that hurt.

Three verdicts:

    graded            a `## Acceptance criteria` section. Passes silently.
    invariants-only   a `## Must still be true` section and no criteria. Passes,
                      and says so. Issue 338 was this shape and still cost two
                      attempts, so it is never silent.
    no-criteria       neither. REFUSED unless the human overrides that issue by id.

Plus `unreadable`, which refuses and which no override can clear: an override is a
statement about an issue's criteria, and nobody can make one about a file that would
not open.

The human approved this on 2026-08-24, with the override per issue and the cost printed.

This does NOT grade the criteria. A section full of nonsense passes here, and
`/harden-issues` is what attacks the contents. One guard, one fault.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

GRADED = "graded"
INVARIANTS_ONLY = "invariants-only"
NO_CRITERIA = "no-criteria"
UNREADABLE = "unreadable"

# Markdown headings only. A file that merely says "this has no acceptance criteria
# yet" in a sentence must not pass on the strength of the phrase appearing.
CRITERIA_HEADING = re.compile(r"^#{2,6}\s+Acceptance criteria\s*$", re.MULTILINE | re.IGNORECASE)
INVARIANT_HEADING = re.compile(r"^#{2,6}\s+Must still be true\s*$", re.MULTILINE | re.IGNORECASE)

# `402b-correct-the-match.md` -> `402b`. Legacy two-digit ids and lettered slices
# are both real in this tracker.
ID_FROM_NAME = re.compile(r"^(\d+[a-z]?)-")

COST = (
    "What an override costs, measured on run `bridge-cse`, 2026-08-24: issues 408 "
    "and 407 carried no criteria section, so the runner authored the graded criteria "
    "into the spawn prompts itself. Two citations in that brief were wrong. They "
    "reached a shipped code comment and cost a correction round to remove."
)


@dataclass(frozen=True)
class Row:
    path: pathlib.Path
    identifier: str
    verdict: str
    detail: str
    overridden: bool = False


def issue_id(name: str) -> str:
    """The tracker id at the front of an issue filename, or the name itself.

    A file nobody can identify is reported under its own name rather than guessed
    at. An override matches on this string, so a wrong guess here would silently
    apply an override to the wrong issue.
    """
    found = ID_FROM_NAME.match(name)
    return found.group(1) if found else name


def grade(text: str) -> tuple[str, str]:
    if CRITERIA_HEADING.search(text):
        return GRADED, "carries a graded acceptance-criteria section"
    if INVARIANT_HEADING.search(text):
        return INVARIANTS_ONLY, (
            "carries invariants (`Must still be true`) but no graded criteria. "
            "A gate grades behaviour against criteria; invariants say what must not "
            "move. Issue 338 was this shape on run `bridge-cse` and took two attempts"
        )
    return NO_CRITERIA, (
        "carries neither `## Acceptance criteria` nor `## Must still be true`, so "
        "nothing in the file tells a gate what passing means"
    )


def judge(paths: list[pathlib.Path], overrides: set[str]) -> tuple[bool, list[Row]]:
    rows: list[Row] = []
    for path in paths:
        identifier = issue_id(path.name)
        try:
            text = path.read_text()
        except OSError as error:
            rows.append(Row(path, identifier, UNREADABLE, str(error)))
            continue
        verdict, detail = grade(text)
        overridden = verdict == NO_CRITERIA and identifier in overrides
        rows.append(Row(path, identifier, verdict, detail, overridden))

    blocked = [row for row in rows if row.verdict in (NO_CRITERIA, UNREADABLE) and not row.overridden]
    return not blocked, rows


def report(rows: list[Row]) -> None:
    for row in rows:
        if row.verdict == GRADED:
            print(f"ok        {row.identifier}: {row.detail}")
        elif row.verdict == INVARIANTS_ONLY:
            print(f"INVARIANTS {row.identifier}: {row.detail}")
        elif row.overridden:
            print(f"OVERRIDE  {row.identifier}: {row.detail}")
        else:
            print(f"REFUSED   {row.identifier}: {row.detail}", file=sys.stderr)

    # The total, so a caller who passed one path out of nine can see that it
    # did. This check grades what it is handed and cannot know the batch, so
    # the number it graded on is the only honest thing it can say about its own
    # coverage. Same rule as `rn414a-01` on run `414a-483-286335`: a pass and a
    # pass over nothing must not read the same.
    graded = sum(1 for row in rows if row.verdict == GRADED)
    print(
        f"read {len(rows)} issue file(s): {graded} carrying acceptance criteria, "
        f"{len(rows) - graded} not"
    )

    if any(row.overridden for row in rows):
        print()
        print(COST)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse an issue file that carries no criteria for a gate to grade.",
    )
    parser.add_argument(
        "--issue",
        required=True,
        action="append",
        dest="issues",
        help="path to an issue file; repeat for each issue in the batch",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        dest="overrides",
        help="issue id to run without criteria anyway, e.g. --override 408. Per issue, never batch-wide",
    )
    args = parser.parse_args()

    paths = [pathlib.Path(one) for one in args.issues]
    allowed, rows = judge(paths, set(args.overrides))
    report(rows)

    if allowed:
        return 0
    print(
        "\nREFUSED: run `/harden-issues` over the issues above, or name each one in "
        "an --override with the human's word.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
