#!/usr/bin/env python3
"""Refuse an implementer spawn once an issue has spent its attempts.

The skill promises three attempts per issue and two criteria-fault resets. On
one measured run one issue took seven attempts and fourteen gate runs, because
the cap was prose and prose does not refuse. This exits non-zero instead.

    attempts:  three, then blocked. Refuses the fourth.
    resets:    two, then the criteria are frozen. Refuses the third.

**A criteria reset refunds the attempt it consumed.** The human ruled it on
2026-09-20. The reason is what a reset means: the pass found the CRITERIA at
fault, so the attempt that failed was never a fair test of the implementer.
Charging it makes a run pay for its own bad brief. So the cap reads SPENT
attempts -- `attempts - resets` -- and not the marker number. One reset
therefore buys a fourth attempt and two buy a fifth, though the reset ceiling
above usually bites first. A refund can never exceed the attempts actually
taken, so a reset written before any attempt buys nothing.

One measured run is why this is code. An issue took one reset, hit the old cap
three hours after the ruling, and blocked a second issue behind it, because the
ruling was prose and prose does not refund.

**It counts an explicit `attempt N` marker, and nothing else.** The ledger's
stamps column is prose in at least two formats, and the older `implement …` /
`retry 1 …` vocabulary cannot be counted: `retry 00:18` is a clock and
`retry 10.2` is a duration in minutes. A cap built on that regex misfires, and a
cap that misfires costs a run more than no cap at all. So the runner writes
`attempt <N>` into the issue's row before each implementer spawn, and this reads
it back. A row it cannot find or cannot parse is a refusal, not a pass — the
runner then fixes the row, which is the only way the marker can go missing.

**A `Level: light` issue gets two attempts** (tracker-tooling issue 40, rule 5).
The level is read by `issue_level.py` from the issue file in the run's own tree,
fresh on every call, so a light issue lifted to full mid-run gets its third.
Anything but `Level: light` keeps the three above. The light refusal ledgers the
issue `blocked` with the reason `light: two attempts spent`: no escalated third.

Exit 0 authorises the spawn and prints the attempt number. Exit 1 refuses and
prints the counts it refused on.

Usage:
    check_attempt_cap.py --ledger <run.md> --issue 348
    check_attempt_cap.py --ledger <run.md> --issue 348 --charges

**It also refuses a row that does not say what its gate rounds cost**
(tracker-tooling issue 15): a rejected `gates N:` token with no `charge=`, and a
criteria reset that names no round or a round the row does not hold.
`--charges` runs that refusal alone, at the commit step, where no spawn follows.

The older `implement …` / `retry N` stamps cannot be counted, because
`retry 00:18` is a clock and `retry 10.2` is a duration in minutes, so a row
still carrying them is refused until it is restamped with `attempt N`. Moved
here from SKILL.md by ticket 36 sitting 5 (2026-09-09).
"""

import argparse
import importlib.util
import os
import re
import sys
from dataclasses import dataclass

MAX_ATTEMPTS = 3
MAX_RESETS = 2
MAX_LIGHT_ATTEMPTS = 2

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
    #
    # **The charge, tracker-tooling issue 15 (fix F12, 2026-09-23).** A strike
    # used to be derived: rounds rejected since the last reset. A standards
    # split, a runner-error annulment and the prose-deletion road each cancel
    # one in prose, so `issues.jsonl` and the ledgers disagreed on 13 issues.
    # `charge=<strike|correction|none>` states what the round cost, copied from
    # `charge_round.py`'s output, and `charge_faults` below refuses a rejected
    # round without it.
    #
    # **A light round names the review gate alone** (tracker-tooling issue 40,
    # default `q-h0925-40-2`): `gates 1: review=reject charge=strike`. Rule 5
    # spawns no verify gate, so the `verify` group is None on that token.
    "gate round": re.compile(
        r"\bgates\s+(?P<round>\d+)\s*:\s*"
        r"(?:verify=(?P<verify>pass|reject)\s+)?review=(?P<review>pass|reject)\b"
        r"(?:\s+charge=(?P<charge>strike|correction|none)\b)?",
        re.IGNORECASE),
    # `criteria reset after gates 2`, or `criteria reset 1 of 2 after gates 2`.
    # A reset annuls the strikes charged up to the round it names. Its place in
    # the row cannot say which: issue 169 of run `batch-24d0d1` wrote its reset
    # before every gate token.
    "reset round": re.compile(
        r"\bcriteria[\s-]*(?:fault[\s-]*)?reset\b(?:\s+\d+(?:\s+of\s+\d+)?)?"
        r"\s+after\s+gates\s+(\d+)\b",
        re.IGNORECASE),
    # `criteria reset 2 of 2` with no round after it: a counted stamp, which is
    # a reset and never prose, left unnamed. Once a row names one reset,
    # `count_resets` counts names, so an unnamed stamp would go uncounted and
    # the criteria would never freeze (review of issue 20, 2026-09-23).
    "unnamed reset stamp": re.compile(
        r"\bcriteria[\s-]*(?:fault[\s-]*)?reset\s+\d+\s+of\s+\d+\b"
        r"(?!\s+after\s+gates\s+\d)",
        re.IGNORECASE),
}

# The stamp alone: `attempt 1` is one, while `attempt 1's files` and a quoted
# `` `attempt 1` `` are prose about one (tracker-tooling issue 27).
STAMPED_ATTEMPT = re.compile(
    r"(?<!`)\battempt\s+(\d+)(?![\d:.`])(?!['’]s\b)", re.IGNORECASE)

# The pre-2026-08-17 stamp vocabulary. A row carrying it and no `attempt N`
# holds attempts this cap cannot count, so it refuses instead of reading zero.
LEGACY = re.compile(r"\b(implement|retry)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    attempt: int
    resets: int
    reason: str = ""
    # Attempts charged against the cap: taken, less those a reset refunded.
    spent: int = 0


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


def count_attempts(row):
    """How many attempts the row has stamped: the distinct numbers it stamps.

    Tracker-tooling issue 27. Rows are prose, and on run `batch-46e4de` issue
    33b's row said "attempt 1's files", which a count of mentions read as a
    second attempt. A possessive or backticked mention is not a stamp, and a
    number stamped twice is one attempt, as issue 20 counts a reset.
    """
    return len({int(n) for n in STAMPED_ATTEMPT.findall(row or "")})


def count_resets(row):
    """How many criteria resets the row records.

    Tracker-tooling issue 20. Where the row names any reset by its round, count
    the distinct rounds named: a row that names its reset and then explains it
    mentions it twice, and a count of mentions read that as two resets and froze
    the criteria. A row that names none is counted by mentions, as before, so no
    ledger already written reads differently.
    """
    named = {int(n) for n in MARKER["reset round"].findall(row or "")}
    return len(named) if named else count_markers(row, "criteria reset")


def charge_faults(row):
    """Every way this row fails to say what its gate rounds cost, or `[]`.

    Read only on a row that carries a gate-round token. A row written before
    the token existed states no round to charge, and no ledger already written
    is refused for it.
    """
    rounds = list(MARKER["gate round"].finditer(row or ""))
    if not rounds:
        return []
    faults = []
    for found in rounds:
        rejected = "reject" in ((found.group("verify") or "").lower(),
                                found.group("review").lower())
        charge = (found.group("charge") or "").lower()
        if rejected and not charge:
            faults.append(
                f"`gates {found.group('round')}:` holds a reject and no "
                "charge. Append the `charge=` `charge_round.py` printed for "
                "that round.")
        elif not rejected and charge not in ("", "none"):
            faults.append(
                f"`gates {found.group('round')}:` charges {charge} on a round "
                "both gates passed. Write `charge=none`.")
    held = {int(found.group("round")) for found in rounds}
    named = sorted({int(n) for n in MARKER["reset round"].findall(row)})
    # Any named reset satisfies this, not one name per mention: rows are
    # prose, and a runner that names the reset and then explains it mentions
    # it twice (found by the review of 2026-09-23).
    if count_markers(row, "criteria reset") and not named:
        faults.append(
            "a criteria reset names no round. Write it `criteria reset after "
            "gates <N>`, N the round whose strike-2 re-check reset it.")
    faults.extend(
        f"`criteria reset after gates {number}` names a round this row does "
        "not hold." for number in named if number not in held)
    faults.extend(
        f"`{stamp.group(0)}` names no round. Write it `{stamp.group(0)} after "
        "gates <N>`, so the cap counts it." for stamp in
        MARKER["unnamed reset stamp"].finditer(row))
    return faults


def decide(ledger_text, issue, level="full"):
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

    attempts = count_attempts(row)
    resets = count_resets(row)
    this_attempt = attempts + 1
    # A reset refunds the attempt it consumed, never more than were taken.
    refunded = min(resets, attempts)
    spent = attempts - refunded

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

    faults = charge_faults(row)
    if faults:
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            reason=(
                f"Refused: issue {issue}'s row does not say what its gate "
                "rounds cost, so `run_quality.py` would derive the strikes "
                "from prose.\n  - " + "\n  - ".join(faults) + "\nFix the "
                "row, then re-run."
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

    if level == "light" and spent >= MAX_LIGHT_ATTEMPTS:
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            spent=spent,
            reason=(
                f"Refused: issue {issue} is `Level: light`, and a light issue "
                f"has a cap of two attempts (rule 5). {spent} are spent and "
                f"this would be attempt {this_attempt}. No escalated implementer "
                f"and no criteria reset: ledger it `blocked` with the reason "
                f"`light: two attempts spent`, and name it in the merge "
                f"briefing's `## Skipped or blocked`."
            ),
        )

    if spent >= MAX_ATTEMPTS:
        refund_note = (
            f", of which {refunded} {'was' if refunded == 1 else 'were'} "
            f"refunded by a criteria reset, so {spent} "
            f"{'is' if spent == 1 else 'are'} spent"
        ) if refunded else ""
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            reason=(
                f"Refused: issue {issue} has {attempts} attempts recorded"
                f"{refund_note} and the cap is {MAX_ATTEMPTS}. This would be "
                f"attempt {this_attempt}. Ledger it `blocked` and work out "
                f"what another attempt would need that the earlier ones did "
                f"not have."
            ),
        )

    return Decision(allowed=True, attempt=this_attempt, resets=resets,
                    spent=spent)


def _issue_level():
    """`issue_level.py` beside this file: the one reader of `Level:` in a run."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "issue_level.py")
    spec = importlib.util.spec_from_file_location("cap_issue_level", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="path to run.md")
    parser.add_argument("--issue", required=True, help="issue id, e.g. 348")
    parser.add_argument("--charges", action="store_true",
                        help="check only that the row's gate rounds carry "
                             "their charges; for the commit step, where no "
                             "spawn follows")
    args = parser.parse_args(argv)

    try:
        with open(args.ledger, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        print(f"Refused: cannot read {args.ledger}: {error}", file=sys.stderr)
        return 1

    if args.charges:
        row = find_row(text, args.issue)
        faults = (charge_faults(row) if row is not None
                  else [f"no row for issue {args.issue} in the status table."])
        if faults:
            print(f"Refused: issue {args.issue}:\n  - " + "\n  - ".join(faults),
                  file=sys.stderr)
            return 1
        print(f"issue {args.issue}: every gate round carries its charge")
        return 0

    reading = _issue_level().read_level(args.ledger, args.issue, text)
    if reading.note:
        print(f"check_attempt_cap: {reading.note}.", file=sys.stderr)
    decision = decide(text, args.issue, reading.level)
    cap = MAX_LIGHT_ATTEMPTS if reading.level == "light" else MAX_ATTEMPTS
    if decision.allowed:
        print(
            f"attempt {decision.attempt}, "
            f"{decision.spent} of {cap} spent "
            f"(criteria resets: {decision.resets} of {MAX_RESETS}, "
            f"each refunding one attempt)"
        )
        return 0
    print(decision.reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
