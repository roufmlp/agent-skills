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
Anything but `Level: light` keeps the three above. No escalated third.

**A light issue at its cap lands short; it does not block** (the human,
2026-10-05). One run blocked a light issue on two
prototype-fidelity strikes, and nine of its twelve issues never started behind
it. A light issue touches none of the five risk classes, so the refusal prints
the land-short road: commit, row every owed ground, ledger `done (landed short)`,
run the dependents. Only a red tree is still ledgered `blocked`.

**A screen difference never blocks an issue, light or full** (the human,
2026-10-05). A full issue at its cap whose LAST gate round carries
`grounds=screen` -- every item it failed is a screen criterion, as
`charge_round.py` decides and prints -- lands short on the same road. One run
measured why: screen issues took 270 to 560 implementer turns,
and 8 of 16 rejects since 4 October were screen differences. Any other ground in
the last round keeps today's `blocked`.

**A run never blocks on one feature: it carves it out** (the human,
2026-10-06). One run shipped 1 of its 12 issues: one issue's Undo criterion
spent four attempts and two criteria resets, this cap refused the fifth, and
the ten issues behind it were skipped. Two of this
file's own messages promised an escalated attempt after the second reset that
the reset check above refused. Now every road that used to end in `blocked`
ends in a carve:

    at the cap, or after the second reset   the runner stamps
        `carve after gates <N>: C2, C5`, the criteria the last round failed,
        and this check authorises ONE carve spawn: an implementer that takes
        those criteria out of the tree and keeps the rest. Its round is gated
        like any other, under the critical gate where the issue ran under it.
    the carve round passes                  commit, ledger `done (carved)`,
                                            run the dependents
    the carve round fails, or the tree      stamp `carve whole after gates
        reads red                           <M>`, keep the code off the run
                                            branch, ledger `carved (whole)`,
                                            run the dependents
    the carve would name every criterion    the same: `carve whole`
    a dependent needs a carved criterion    `carve at launch: C3`, before its
                                            first attempt, or `carve whole at
                                            launch` where it needs all of it

After the merge, `mint_carved.py` mints each carved part as a new issue at
`needs-harden`, carrying its criteria, rows, verdicts and strike history, and a
whole carve sends the issue itself back to `needs-harden`. The cap prints no
road that ends in `blocked`; `test_check_attempt_cap.py` drives every refusal
and refuses one that does.

**The carve round keeps the critical gate.** `--charges`, run at every commit
step, refuses to commit a carve round whose review verdict was not written by
`run-issues-review-gate-critical` when the row or an earlier review verdict of
the issue names that gate. A carve can only take code away, so the class the
issue ran under still holds for what ships.

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
        r"(?:\s+charge=(?P<charge>strike|correction|none)\b)?"
        r"(?:\s+grounds=(?P<grounds>screen)\b)?",
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
    # `carve after gates 4: C2, C5` -- the criteria the runner takes out of the
    # issue after round 4 (the human, 2026-10-06). Criteria only:
    # an invariant is never carved, because the part that ships must still keep
    # it. `mint_carved.py` reads the same marker after the merge.
    "carve": re.compile(
        r"\bcarve\s+after\s+gates\s+(?P<round>\d+)\s*:\s*"
        r"(?P<ids>C\d+(?:\s*,\s*C\d+)*)", re.IGNORECASE),
    # `carve at launch: C3` -- a dependent's criterion that needs a part its
    # blocker carved, taken out before attempt 1 so no attempt is spent on it.
    "carve at launch": re.compile(
        r"\bcarve\s+at\s+launch\s*:\s*(?P<ids>C\d+(?:\s*,\s*C\d+)*)",
        re.IGNORECASE),
    # `carve whole after gates 5`, or `carve whole at launch`: nothing ships.
    "carve whole": re.compile(
        r"\bcarve\s+whole\s+(?:after\s+gates\s+(?P<round>\d+)|at\s+launch)\b",
        re.IGNORECASE),
    # Any other spelling that starts like a carve stamp. A carve the cap cannot
    # read is refused rather than read as no carve at all.
    "carve word": re.compile(r"\bcarve\s+(?:after|at|whole)\b", re.IGNORECASE),
}

CRITICAL_GATE = "run-issues-review-gate-critical"

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
    # `attempt` for an ordinary spawn, `carve` for the one carve spawn.
    kind: str = "attempt"


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


# `attempt 5 (carve)`: the one carve spawn's stamp. It is an `attempt N` stamp
# too, so the gates name their verdicts `<issue>-attempt-5-review.md` as the
# write guard demands, and the cap can tell the carve spawn has been made.
CARVE_ATTEMPT = re.compile(r"\battempt\s+(\d+)\s*\(carve\)", re.IGNORECASE)


@dataclass(frozen=True)
class Carve:
    """What a row says it carved out of its issue."""
    after: object = None       # the round of `carve after gates N`, or None
    ids: tuple = ()            # every criterion carved, at launch and after
    whole: bool = False
    attempt: object = None     # N of `attempt N (carve)`, or None


def _ids(text):
    return {f"C{int(n)}" for n in re.findall(r"C(\d+)", text, re.IGNORECASE)}


def read_carve(row, criteria_names=None):
    """`(Carve, faults)`: what the row carved, and every way it says so badly.

    `criteria_names` is the set of `C<n>` the issue file holds, read by
    `criteria_ids.py`. With it, a carve naming a criterion the issue lacks is a
    fault, and so is a carve naming every criterion, which is a whole carve
    spelled wrong. Without it -- the issue file could not be read -- a carve
    that keeps a part is a fault, because nothing can say what it leaves. A
    whole carve keeps nothing, so it needs no list.
    """
    row = row or ""
    known = [MARKER[kind].finditer(row)
             for kind in ("carve", "carve at launch", "carve whole")]
    starts = {found.start() for matches in known for found in matches}
    faults = [f"`{found.group(0)}…` is not a carve stamp this cap can read. "
              "Write `carve after gates <N>: C<n>, …`, `carve at launch: "
              "C<n>, …` or `carve whole after gates <N>`."
              for found in MARKER["carve word"].finditer(row)
              if found.start() not in starts]
    held = {int(found.group("round"))
            for found in MARKER["gate round"].finditer(row)}
    after = sorted({int(found.group("round"))
                    for found in MARKER["carve"].finditer(row)})
    ids = set()
    for kind in ("carve", "carve at launch"):
        for found in MARKER[kind].finditer(row):
            ids |= _ids(found.group("ids"))
    whole_rounds = [found.group("round")
                    for found in MARKER["carve whole"].finditer(row)]
    if len(after) > 1:
        faults.append(
            f"the row carves after rounds {', '.join(map(str, after))}. An "
            "issue takes one carve; a carve round that fails is a whole carve.")
    faults.extend(
        f"`carve after gates {number}` names a round this row does not hold."
        for number in after if number not in held)
    faults.extend(
        f"`carve whole after gates {number}` names a round this row does not "
        "hold." for number in whole_rounds if number and int(number) not in held)
    if (ids or after) and criteria_names is None:
        faults.append(
            "the row carves, and the issue file's criteria could not be read, "
            "so nothing can say what the carve leaves.")
    elif ids and criteria_names is not None:
        strangers = sorted(ids - set(criteria_names),
                           key=lambda name: int(name[1:]))
        if strangers:
            faults.append(
                f"the carve names {', '.join(strangers)}, which the issue "
                "file does not hold.")
        elif set(criteria_names) and ids >= set(criteria_names) and not whole_rounds:
            faults.append(
                "the carve names every criterion the issue holds, so nothing "
                "would ship. Write it `carve whole after gates <N>` (or `carve "
                "whole at launch`).")
    attempts = {int(n) for n in CARVE_ATTEMPT.findall(row)}
    if len(attempts) > 1:
        faults.append("the row stamps more than one carve attempt; an issue "
                      "takes one carve spawn.")
    if attempts and not after:
        faults.append("the row stamps a carve attempt and no `carve after "
                      "gates <N>: …`.")
    return Carve(after=after[0] if after else None,
                 ids=tuple(sorted(ids, key=lambda name: int(name[1:]))),
                 whole=bool(whole_rounds),
                 attempt=min(attempts) if attempts else None), faults


def runs_critical(row, verdict_texts=()):
    """True when the issue ran under the critical review gate: its row names
    the gate, or one of its review verdicts was written by it."""
    return CRITICAL_GATE in (row or "") or any(
        CRITICAL_GATE in text or "review gate (critical)" in text.lower()
        for text in verdict_texts)


def _carve_road(issue, why, critical, last_round):
    gate = (f"`{CRITICAL_GATE}`, as this issue ran under it" if critical
            else "the gate this issue ran under")
    return (
        f"Refused: {why} A run never blocks on one feature (the human, "
        f"2026-10-06). CARVE IT, without asking: stamp "
        f"`carve after gates {last_round or '<N>'}: C<n>, …`, naming the "
        f"criteria its last round failed, then re-run this check, which "
        f"authorises one carve spawn. The carve implementer takes those "
        f"criteria's code and tests out of the tree and keeps every criterion "
        f"that passed; its round is gated on what remains, the review gate "
        f"{gate}. Where the last round failed every criterion, stamp `carve "
        f"whole after gates {last_round or '<N>'}` instead. Either way the "
        f"dependents run, and the merge briefing names it under "
        f"`## Skipped or blocked`.")


def _whole_road(issue):
    return (
        f"Refused: issue {issue} is carved whole, so nothing of it ships and no "
        f"implementer is spawned. Keep its code off the run branch, on "
        f"`<run branch>-{issue}-carved`, ledger it `carved "
        f"(whole)`, and run its dependents: a dependent criterion that needs "
        f"it is stamped `carve at launch`. After the merge `mint_carved.py` "
        f"sends the issue back to `needs-harden` with its record. Name it in "
        f"the merge briefing's `## Skipped or blocked`.")


def _carve_decision(issue, row, carve, rounds, this_attempt, resets, critical):
    """The answer for a row that carries `carve after gates N`."""
    later = [found for found in rounds if int(found.group("round")) > carve.after]
    if carve.attempt is None:
        gate = f"`{CRITICAL_GATE}`" if critical else "the issue's own gate"
        return Decision(
            allowed=True, attempt=this_attempt, resets=resets, kind="carve",
            reason=(
                f"carve spawn for issue {issue}: stamp `attempt {this_attempt} "
                f"(carve)`. Take {', '.join(carve.ids)} out of the tree, their "
                f"code and their tests, and keep every other criterion as it "
                f"passed. Gate the round on what remains, the review gate "
                f"{gate}. A red tree is the refusal: it means the rest does "
                f"not stand alone, and the issue is carved whole."))
    if not later:
        return Decision(
            allowed=False, attempt=this_attempt, resets=resets, kind="carve",
            reason=(
                f"Refused: issue {issue}'s carve spawn is made (attempt "
                f"{carve.attempt}). Gate its round. An issue takes one carve "
                f"spawn: where its work is unfinished or its tree is red, stamp "
                f"`carve whole after gates {carve.after}`."))
    last = later[-1]
    passed = "reject" not in ((last.group("verify") or "").lower(),
                              last.group("review").lower())
    if passed:
        return Decision(
            allowed=False, attempt=this_attempt, resets=resets, kind="carve",
            reason=(
                f"Refused: issue {issue}'s carve round passed, so no spawn "
                f"follows. Commit it through the usual commit gate, ledger it "
                f"`done (carved)`, and run its dependents. After the merge "
                f"`mint_carved.py` mints {', '.join(carve.ids)} as a new issue."))
    if last.group("grounds"):
        return Decision(
            allowed=False, attempt=this_attempt, resets=resets, kind="carve",
            reason=(
                f"Refused: issue {issue}'s carve round failed on screen "
                f"criteria alone, and a screen difference never blocks an issue "
                f"(the human, 2026-10-05). LAND IT SHORT: commit through the usual "
                f"commit gate, file every owed screen difference as a register "
                f"row, ledger it `done (carved)` with those row ids in its "
                f"stamps, and run its dependents."))
    return Decision(
        allowed=False, attempt=this_attempt, resets=resets, kind="carve",
        reason=(
            f"Refused: issue {issue}'s carve round failed on what was meant to "
            f"ship, so the rest does not stand alone. Stamp `carve whole after "
            f"gates {last.group('round')}`. " + _whole_road(issue)[len("Refused: "):]))


def decide(ledger_text, issue, level="full", criteria_names=None,
           verdict_texts=()):
    """Authorise or refuse the next implementer spawn for this issue.

    `criteria_names` is the `C<n>` set the issue file holds, and
    `verdict_texts` the text of its review verdicts; both are read by `main`.
    """
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

    carve, carve_faults = read_carve(row, criteria_names)
    if carve_faults:
        return Decision(
            allowed=False, attempt=this_attempt, resets=resets,
            reason=(f"Refused: issue {issue}'s carve stamps cannot be read.\n"
                    "  - " + "\n  - ".join(carve_faults) + "\nFix the row, "
                    "then re-run."))
    rounds = list(MARKER["gate round"].finditer(row))
    last_round = rounds[-1].group("round") if rounds else None
    critical = runs_critical(row, verdict_texts)
    if carve.whole:
        return Decision(allowed=False, attempt=this_attempt, resets=resets,
                        kind="carve", reason=_whole_road(issue))
    if carve.after is not None:
        return _carve_decision(issue, row, carve, rounds, this_attempt, resets,
                               critical)

    if resets >= MAX_RESETS:
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            reason=_carve_road(
                issue,
                f"issue {issue} has {resets} criteria resets, the maximum, so "
                f"its criteria are frozen and no implementer, escalated or "
                f"not, is spawned against them.",
                critical, last_round),
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
                f"and no criteria reset. LAND IT SHORT (the human, 2026-10-05): "
                f"commit the last attempt's work through "
                f"the usual commit gate, file every owed ground of its last "
                f"review verdict as a register row, ledger it "
                f"`done (landed short)` with those row ids in its stamps, and "
                f"run its dependents. Only a tree the commit gate reads red "
                f"cannot land: stamp that one `carve whole after gates "
                f"{last_round or '<N>'}` and ledger it `carved (whole)`. Either "
                f"way, name it in the merge briefing's `## Skipped or blocked`."
            ),
        )

    if spent >= MAX_ATTEMPTS and rounds and rounds[-1].group("grounds"):
        return Decision(
            allowed=False,
            attempt=this_attempt,
            resets=resets,
            spent=spent,
            reason=(
                f"Refused: issue {issue} has spent its {MAX_ATTEMPTS} attempts, "
                f"and its last gate round failed on screen criteria alone "
                f"(`grounds=screen`). A screen difference never blocks an "
                f"issue (the human, 2026-10-05). LAND IT SHORT: commit the last "
                f"attempt's work through the usual commit gate, file every "
                f"owed screen difference of its last review verdict as a "
                f"register row, ledger it `done (landed short)` with those row "
                f"ids in its stamps, and run its dependents. Only a tree the "
                f"commit gate reads red cannot land: stamp that one `carve "
                f"whole after gates {last_round}` and ledger it `carved "
                f"(whole)`. Either way, name it in the merge briefing's "
                f"`## Skipped or blocked`."
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
            spent=spent,
            reason=_carve_road(
                issue,
                f"issue {issue} has {attempts} attempts recorded{refund_note} "
                f"and the cap is {MAX_ATTEMPTS}. This would be attempt "
                f"{this_attempt}.",
                critical, last_round),
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


def _criteria_ids():
    """`criteria_ids.py` beside this file: the one reader of an issue's names."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "criteria_ids.py")
    spec = importlib.util.spec_from_file_location("cap_criteria_ids", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def criteria_names_in(issue_path):
    """The `C<n>` set the issue file holds, or None when it cannot be read."""
    if not issue_path:
        return None
    try:
        with open(issue_path, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
    except OSError:
        return None
    return {f"C{number}" for number, _ in _criteria_ids().criteria(body)}


def review_verdicts(ledger_path, issue):
    """`{attempt: text}` of the issue's review verdicts beside the ledger."""
    folder = os.path.join(os.path.dirname(os.path.abspath(ledger_path)),
                          "verdicts")
    found = {}
    try:
        names = os.listdir(folder)
    except OSError:
        return found
    pattern = re.compile(rf"^{re.escape(issue)}-attempt-(\d+)-review\.md$",
                         re.IGNORECASE)
    for name in names:
        match = pattern.match(name)
        if not match:
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8",
                      errors="replace") as handle:
                found[int(match.group(1))] = handle.read()
        except OSError:
            continue
    return found


def carve_gate_faults(row, ledger_path, issue):
    """At the commit step: a carve round that ships must keep the critical
    gate the issue ran under. `[]` when the row carves nothing."""
    carve, _ = read_carve(row, set())
    if carve.attempt is None:
        return []
    verdicts = review_verdicts(ledger_path, issue)
    earlier = [text for number, text in verdicts.items()
               if number != carve.attempt]
    if not runs_critical(row, earlier):
        return []
    path = os.path.join(os.path.dirname(os.path.abspath(ledger_path)),
                        "verdicts", f"{issue}-attempt-{carve.attempt}-review.md")
    text = verdicts.get(carve.attempt)
    if text is None:
        return [f"the carve round ships code from an issue that ran under "
                f"`{CRITICAL_GATE}`, and it has no review verdict at {path}."]
    if not runs_critical("", [text]):
        return [f"the carve round's review verdict, {path}, was not written by "
                f"`{CRITICAL_GATE}`, and this issue ran under it. Re-gate the "
                f"carve round with the critical gate."]
    return []


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
        faults = (charge_faults(row) + carve_gate_faults(row, args.ledger,
                                                         args.issue)
                  if row is not None
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
    decision = decide(text, args.issue, reading.level,
                      criteria_names=criteria_names_in(reading.path),
                      verdict_texts=tuple(
                          review_verdicts(args.ledger, args.issue).values()))
    cap = MAX_LIGHT_ATTEMPTS if reading.level == "light" else MAX_ATTEMPTS
    if decision.allowed and decision.kind == "carve":
        print(decision.reason)
        return 0
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
