#!/usr/bin/env python3
"""Decide what one gate round charges, from both gates' per-item grades.

    python3 charge_round.py --issue <abs path> --round 3 \\
        --verify "Grades: C1=pass C2=fail M1=pass" \\
        --review "Grades: C1=pass C2=pass" [--driven C2=fail]

Tracker-tooling issue 14, fix F11 of the audit of 2026-09-23
(`.scratch/tracker-tooling/evidence/audit-2026-09-23-run-time-and-strikes/`).

WHY IT EXISTS. `SKILL.md` held two rules for one event: "A severity or standards
split takes the stricter verdict", which charges a strike, and the
standards-shaped split, which is a correction round and no strike. The runner
chose by hand and chose four ways in four runs. Issue 146 round 3 of run
`batch-24d0d1` became a correction although both gates rejected; issue 53 round 2
had the same shape, criteria 2-7 green and only the guard short, and took a
strike "because both gates rejected". The split decides a strike, and a strike
decides whether an issue reaches its cap, so it is not the runner's to judge.

THE GRADES. Each gate ends its verdict and its final message with one line, one
`<name>=<word>` per rubric item. Names are `criteria_ids.py`'s. Four words:

  pass   met, and the gate observed it.
  fail   behaviour the item demands and the gate did not observe.
  owed   behaviour correct, and its written proof short: a missing pin, an unrun
         mutation, a claim wider than the code.
  fault  the item itself is wrong: unbuildable, or contradicting another.

THE RULE, in order:

  1. A name the issue's own text does not hold is refused. A ground outside the
     issue is a register row or a criteria re-check, never a strike (issue 13).
  2. Any `fault` -> the criteria re-check, no strike.
  3. A name one gate grades `fail` and the other `pass` or `owed` is a factual
     split. `SKILL.md` settles it by driving it, never by reading the code, so
     this exits 2 naming it, and the runner re-runs with `--driven <name>=<word>`.
  4. Any `fail` left -> a retry, and a strike.
  5. Any `owed` left -> a correction round, no strike, the owed names its list.
  6. Otherwise both pass.

WHAT IT PRINTS. Line 1 is the ledger token, `gates N: verify=<pass|reject>
review=<pass|reject> charge=<strike|correction|none>`, which the runner writes
into the issue's row and `run_quality.py` reads. The verdict words record what
the gates answered; the charge records what the round cost. Line 2 is the road.

A LIGHT ROUND (tracker-tooling issue 40, default `q-h0925-40-2`). Rule 5 spawns
one review gate and no verify gate, so where the issue file says `Level: light`
(read by `issue_level.level_in`) `--verify` may be left out. The round is then
charged on the review grades alone, and the token names that gate alone:
`gates N: review=<pass|reject> charge=<strike|correction|none>`. Without
`Level: light`, a missing `--verify` is refused. A `fault` there is no re-check:
the issue is `blocked (criteria)` (default `q-h0925-40-4`).

Exit 0 decided. Exit 1 refused, and nothing is charged. Exit 2 a factual split to
drive first. Drill: `test_charge_round.py` beside this file.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retry_brief = _load("retry_brief")
issue_level = _load("issue_level")
criteria_ids = retry_brief.criteria_ids

WORDS = ("pass", "fail", "owed", "fault")
# `C3c` keeps its letter: one tracker's issue 92 grades 3a and 3c apart, and one
# name for both would read as one item graded twice. `held` checks the number.
GRADE = re.compile(r"^(([CIM]\d+)[a-z]?)=(\w+)$")
PREFIX = re.compile(r"^\s*grades\s*:", re.IGNORECASE)
# The briefs print the line in backticks, and a gate copies what it reads.
EMPHASIS = str.maketrans("", "", "`*")

AFK = ("\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR THE HUMAN. Take the road "
       "above now and carry on.")


class Refused(Exception):
    """A grades line or a drive this cannot read. Nothing is charged."""


def read_grades(line: str, who: str) -> dict:
    """`{name: word}` from one gate's grades line."""
    tokens = PREFIX.sub("", (line or "").translate(EMPHASIS)).split()
    if not tokens:
        raise Refused(
            f"REFUSED. The {who} gate gave no grades line.\n"
            f"  Each gate ends its verdict with `Grades: C1=pass C2=fail ...`. "
            "A gate that graded nothing did not report.\n"
            "  Two roads out:\n"
            f"  1. Re-spawn the {who} gate.\n"
            "  2. Ledger the issue `blocked` with this message." + AFK)
    grades = {}
    for token in tokens:
        match = GRADE.match(token.strip(",;"))
        if not match or match.group(3) not in WORDS:
            raise Refused(
                f"REFUSED. The {who} gate's grade `{token}` is unreadable.\n"
                "  A grade is a name, `=`, and one of "
                f"{', '.join(WORDS)}. Copy the line from the gate's final "
                "message again; if the gate wrote another word, re-spawn it."
                + AFK)
        name, word = match.group(1), match.group(3)
        if grades.get(name, word) != word:
            raise Refused(
                f"REFUSED. The {who} gate grades {name} twice, "
                f"{grades[name]} and {word}.\n"
                f"  Re-spawn the {who} gate: one item, one grade." + AFK)
        grades[name] = word
    return grades


def refuse_unheld(names, held, where):
    unheld = sorted(name for name in set(names)
                    if GRADE.match(f"{name}=pass").group(2) not in held)
    if unheld:
        raise Refused(
            f"REFUSED. {where} names {', '.join(unheld)}, which the issue "
            "does not hold.\n"
            f"  The issue holds {', '.join(sorted(held)) or 'no named item'}. "
            "A round is charged only on an item the issue states.\n"
            "  Two roads out, and neither charges a strike:\n"
            "  1. The ground is outside this issue: file it as a register row "
            "and re-run without it.\n"
            "  2. The issue should have stated it: take step 8's criteria "
            "re-check." + AFK)


def one_spelling(grades: dict, own: str, who: str) -> dict:
    """The grades keyed on one spelling per item (`criteria_ids.same_item`),
    so `M10` at one gate and `I10` at the other are compared as one item."""
    found = {}
    for name, word in grades.items():
        key = criteria_ids.same_item(name, own)
        if found.get(key, word) != word:
            raise Refused(
                f"REFUSED. The {who} grades {key} twice under two names, "
                f"{found[key]} and {word}.\n"
                "  Re-run it with one grade for the item." + AFK)
        found[key] = word
    return found


def combine(verify: dict, review: dict, driven: dict) -> tuple:
    """`(outcome, names, splits)`: the round's road, its names, open splits."""
    combined, splits = {}, []
    for name in sorted(set(verify) | set(review)):
        words = {verify.get(name), review.get(name)} - {None}
        if name in driven:
            behaviour_ok = driven[name] == "pass"
            combined[name] = ("owed" if behaviour_ok and "owed" in words
                              else "pass" if behaviour_ok else "fail")
        elif "fault" in words:
            combined[name] = "fault"
        elif "fail" in words and words & {"pass", "owed"}:
            splits.append(name)
        elif "fail" in words:
            combined[name] = "fail"
        else:
            combined[name] = "owed" if "owed" in words else "pass"
    for outcome in ("fault", "fail", "owed"):
        named = [name for name, word in combined.items() if word == outcome]
        if outcome == "fault" and named:
            return outcome, named, []
        if outcome == "fail" and splits:
            return "split", splits, splits
        if named:
            return outcome, named, []
    return "pass", [], []


# outcome -> (the charge the ledger token carries, the road the runner takes)
ROADS = {
    "fault": ("none",
              "The criteria are at fault on {names}. No strike. Take step 8's "
              "criteria re-check before any other spawn."),
    "fail": ("strike",
             "A retry and a strike. Owed: {names}. Compose the brief with "
             "retry_brief.py."),
    "owed": ("correction",
             "A correction round and no strike. Its items: {names}. Compose "
             "the brief with correction_brief.py."),
    "pass": ("none", "Both pass. Commit."),
}


def verdict(grades: dict) -> str:
    return "reject" if set(grades.values()) - {"pass"} else "pass"


def decide(body, round_number, verify_line, review_line, driven_args=()):
    """`(exit code, stdout, stderr)` for one round."""
    try:
        verify = {} if verify_line is None else read_grades(verify_line,
                                                             "verify")
        review = read_grades(review_line, "review")
        driven = {}
        for item in driven_args:
            match = GRADE.match(item.strip())
            if not match or match.group(3) not in ("pass", "fail"):
                raise Refused(
                    f"REFUSED. `--driven {item}` is unreadable. Write the name "
                    "you drove, `=`, and `pass` or `fail` for what you "
                    "observed." + AFK)
            driven[match.group(1)] = match.group(3)
        own = retry_brief.own_text(body)
        held = criteria_ids.known_ids(own)
        refuse_unheld(verify, held, "The verify gate's grades line")
        refuse_unheld(review, held, "The review gate's grades line")
        refuse_unheld(driven, held, "`--driven`")
        verify = one_spelling(verify, own, "verify gate")
        review = one_spelling(review, own, "review gate")
        driven = one_spelling(driven, own, "`--driven` list")
    except Refused as refusal:
        return 1, "", str(refusal)

    outcome, names, splits = combine(verify, review, driven)
    if splits:
        drives = " ".join(f"--driven {name}=<pass|fail>" for name in splits)
        return 2, "", (
            f"NOT DECIDED. The gates split on {', '.join(splits)}: one observed "
            "the behaviour wrong and the other graded it right.\n"
            "  Drive it yourself, never by reading the code: plant the input "
            "the failing gate names and observe the result, cache-cleared. "
            f"Then re-run with {drives}." + AFK)
    charge, road = ROADS[outcome]
    if outcome == "fault" and verify_line is None:
        # Default `q-h0925-40-4`: a light issue takes no criteria re-check.
        road = ("The criteria are at fault on {names}. No strike, and a "
                "`Level: light` issue takes no criteria re-check: ledger it "
                "`blocked (criteria)` and put the fault in the merge briefing.")
    gates = ("" if verify_line is None else f"verify={verdict(verify)} ")
    token = (f"gates {round_number}: {gates}"
             f"review={verdict(review)} charge={charge}")
    return 0, f"{token}\n{road.format(names=', '.join(names))}\n", ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", required=True, help="the issue file")
    parser.add_argument("--round", required=True, type=int,
                        help="the gate round's number, as in `gates N:`")
    parser.add_argument("--verify",
                        help="the verify gate's grades line, verbatim; left "
                             "out only on a `Level: light` issue")
    parser.add_argument("--review", required=True,
                        help="the review gate's grades line, verbatim")
    parser.add_argument("--driven", action="append", default=[],
                        metavar="NAME=pass|fail",
                        help="what the runner observed driving a split item")
    args = parser.parse_args(argv)
    try:
        body = pathlib.Path(args.issue).read_text(encoding="utf-8",
                                                  errors="replace")
    except OSError:
        print(f"REFUSED. Nothing is readable at {args.issue}. Re-run with the "
              "issue path the ledger header names." + AFK, file=sys.stderr)
        return 1
    if args.verify is None and issue_level.level_in(body) != "light":
        print("REFUSED. No `--verify` grades line, and the issue file does not "
              "say `Level: light`. Only a light round has one gate; a full "
              "round is charged on both gates' grades. Re-run with --verify."
              + AFK, file=sys.stderr)
        return 1
    code, out, err = decide(body, args.round, args.verify, args.review,
                            args.driven)
    if out:
        print(out, end="")
    if err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
