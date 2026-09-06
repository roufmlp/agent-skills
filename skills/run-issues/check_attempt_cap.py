#!/usr/bin/env python3
"""Refuse an implementer spawn once an issue has spent its attempts.

The skill promises three attempts per issue and two criteria-fault resets. On
one measured run one issue took seven attempts and fourteen gate runs, because
the cap was prose and prose does not refuse. This exits non-zero instead.

    attempts:  three, then blocked. Refuses the fourth.
    resets:    two, then the criteria are frozen. Refuses the third.

**It counts an explicit `attempt N` marker, and nothing else.** The ledger's
stamps column is prose in at least two formats, and the older `implement …` /
`retry 1 …` vocabulary cannot be counted: `retry 00:18` is a clock and
`retry 10.2` is a duration in minutes. A cap built on that regex misfires, and a
cap that misfires costs a run more than no cap at all. So the runner writes
`attempt <N>` into the issue's row before each implementer spawn, and this reads
it back. A row it cannot find or cannot parse is a refusal, not a pass — the
runner then fixes the row, which is the only way the marker can go missing.

Exit 0 authorises the spawn and prints the attempt number. Exit 1 refuses and
prints the counts it refused on.

Usage:
    check_attempt_cap.py --ledger <run.md> --issue 348
"""

import argparse
import re
import sys
from dataclasses import dataclass

MAX_ATTEMPTS = 3
MAX_RESETS = 2

# `attempt 1`, `attempt 2` — a marker the runner writes, never a clock.
# The digits must not run into `:` or `.`, which is what makes `retry 00:18`
# and `retry 10.2` uncountable and this marker countable.
MARKER = {
    "attempt": re.compile(r"\battempt\s+(\d+)(?![\d:.])", re.IGNORECASE),
    "criteria reset": re.compile(r"\bcriteria[\s-]*(?:fault[\s-]*)?reset\b",
                                 re.IGNORECASE),
    # `gates 1: verify=pass review=reject` — one gate ROUND, minted by ticket
    # 37 ruling 28 on 2026-09-06 and read by `run_quality.py`. It lives here
    # because this dict is the one home for markers the RUNNER writes, and a
    # second home is the drift `journal_for` and `read_transcript` taught
    # ticket 39 in its sittings 2 and 3.
    #
    # **It exists for the same reason `attempt N` does.** Sitting 4 of ticket
    # 39 measured what a verdict costs when it is prose: seven dialects across
    # sixteen ledgers, every one of them read as silence until two review
    # passes found them, and two ledgers reporting `0 strike(s)` on runs that
    # charged them.
    #
    # **Two fixed verdict words and no synonyms.** `pass` and `reject` only. A
    # minted marker that also took `accept`, `passed` and `rejects` would be an
    # eighth dialect rather than an end to the seven.
    "gate round": re.compile(
        r"\bgates\s+(?P<round>\d+)\s*:\s*"
        r"verify=(?P<verify>pass|reject)\s+review=(?P<review>pass|reject)\b",
        re.IGNORECASE),
}

# The pre-2026-08-17 stamp vocabulary. A row carrying it and no `attempt N`
# holds attempts this cap cannot count, so it refuses instead of reading zero.
LEGACY = re.compile(r"\b(implement|retry)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    attempt: int
    resets: int
    reason: str = ""


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def issue_column(ledger_text):
    """Which column holds the issue id.

    Two header shapes are in use: `| Issue | Status | …` puts it first, and
    `| # | issue | …` puts it second behind a row number. Reading the row
    number as an issue id matches the wrong row entirely, so the header
    decides. Without a header, the first column.
    """
    for line in ledger_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        lowered = [c.lower() for c in _cells(line)]
        if "issue" in lowered:
            return lowered.index("issue")
    return 0


def find_row(ledger_text, issue, column=None):
    """The status-table row for this issue, or None."""
    wanted = issue.strip().lower()
    if column is None:
        column = issue_column(ledger_text)
    for line in ledger_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if len(cells) <= column:
            continue
        # The cell is `147` or `318 — the generic-product road`.
        token = re.split(r"[\s—–-]", cells[column], maxsplit=1)[0].strip().lower()
        if token == wanted:
            return stripped
    return None


def count_markers(row, kind):
    """How many times this marker appears in the row. None counts as zero."""
    if not row:
        return 0
    return len(MARKER[kind].findall(row))


def decide(ledger_text, issue):
    """Authorise or refuse the next implementer spawn for this issue."""
    row = find_row(ledger_text, issue)
    if row is None:
        return Decision(
            allowed=False,
            attempt=0,
            resets=0,
            reason=(
                f"Refused: no row for issue {issue} in the ledger's status "
                "table. Every issue carries a row from launch, so a missing "
                "row means the wrong ledger or an unrecorded issue. Fix the "
                "row, then re-run."
            ),
        )

    attempts = count_markers(row, "attempt")
    resets = count_markers(row, "criteria reset")
    this_attempt = attempts + 1

    if attempts == 0 and LEGACY.search(row):
        return Decision(
            allowed=False,
            attempt=0,
            resets=resets,
            reason=(
                f"Refused: issue {issue}'s row carries the old "
                f"`implement`/`retry` stamps, which this cap cannot count — "
                f"`retry 00:18` is a clock and `retry 10.2` is a duration. "
                f"Reading it as a fresh issue would authorise a fourth "
                f"attempt on a row that may have spent three. Restamp the row "
                f"as `attempt 1`, `attempt 2`, … then re-run."
            ),
        )

    if resets >= MAX_RESETS:
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            reason=(
                f"Refused: issue {issue} has {resets} criteria resets, the "
                f"maximum. The criteria are frozen for this run — the next "
                f"strike-2 buys one escalated attempt, then `blocked`."
            ),
        )

    if attempts >= MAX_ATTEMPTS:
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            reason=(
                f"Refused: issue {issue} has {attempts} attempts recorded and "
                f"the cap is {MAX_ATTEMPTS}. This would be attempt "
                f"{this_attempt}. Ledger it `blocked` and work out what a "
                f"fourth attempt would need that the first three did not have."
            ),
        )

    return Decision(allowed=True, attempt=this_attempt, resets=resets)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="path to run.md")
    parser.add_argument("--issue", required=True, help="issue id, e.g. 348")
    args = parser.parse_args(argv)

    try:
        with open(args.ledger, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        print(f"Refused: cannot read {args.ledger}: {error}", file=sys.stderr)
        return 1

    decision = decide(text, args.issue)
    if decision.allowed:
        print(
            f"attempt {decision.attempt} of {MAX_ATTEMPTS} "
            f"(criteria resets: {decision.resets} of {MAX_RESETS})"
        )
        return 0
    print(decision.reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
