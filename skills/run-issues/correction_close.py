#!/usr/bin/env python3
"""Authorise the correction round's close, or refuse it.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling Q7 of round 2, 2026-09-08: the round's two handovers become one
script each. This is the close. `correction_brief.py` is the other.

THE TWO THINGS IT REFUSES ON.

A RED TEST. `SKILL.md` closes the round when the runner verifies each item's
NAMED evidence -- the test now exists and is green, the mutation now reds -- and
not that files were touched. Naming the tests is the runner's judgement; running
them is not, and a round that closed on files-were-touched is what R1 was
adopted against.

A DEAD CITATION PASS. The human adopted this in the daily-brief walk of 2026-09-08:
a missing `=== CITATION PASS COMPLETE ===` terminator is treated the way a red
test is treated. Run `batch-207704`'s last pass died after 48 lines inside its
preamble and read clean to everything that looked at it. The rule itself lives in
`citation_pass.py`, which the runner's commit step and the finale also read, so
there is one tail check and not three.

IT NEVER COMMITS, and that is a default of this sitting rather than a ruling.
Ruling Q7's wording ends "and commits". `git-shared-state-guard.py` refuses a
commit carrying no explicit paths, one git index serves every session in the main
checkout (ticket 41), and a script that guessed the paths would stage another
session's work. So this authorises and the runner commits, which is also what
`SKILL.md` already says about who commits.

`--test` runs through the shell because the commands are `npx vitest run <path>`
and its cousins, written by the runner for its own use. Nothing untrusted reaches
it: the runner composes every one.

    python3 correction_close.py --test "<cmd>" [--test ...] --pass-file <path> ...

Exit 0 authorises the commit. Exit 1 refuses and names every fault at once.
Drill: `test_correction_close.py` beside this file.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# How much of a failing command's output to quote back.
TAIL_LINES = 12

from citation_pass import verdict

AFK = (
    "\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR ABDUL. He is AFK for every "
    "run. Take one of the two roads above now and carry on."
)


def run_tests(commands) -> list:
    """`(command, exit code)` per named test. Every one runs, red or not.

    One report rather than a walk: a round that learns of its second red test on
    the next spawn has bought a second eleven-to-twenty-two-minute wait for
    nothing, and that wait is what ruling Q7 exists to cut.
    """
    found = []
    for command in commands:
        try:
            done = subprocess.run(command, shell=True, capture_output=True,
                                  text=True)
            found.append((command, done.returncode,
                          tail(done.stdout, done.stderr)))
        except OSError as err:
            found.append((command, f"could not run ({err})", ""))
    return found


def tail(out, err, lines=TAIL_LINES):
    """The last few lines a failing command printed.

    A refusal naming the command and nothing else costs the runner another turn
    and another whole test run to see why, inside the handover this script exists
    to shorten. `stderr` first: a vitest failure ends there.
    """
    text = "\n".join(part for part in (err or "", out or "") if part.strip())
    kept = [line for line in text.splitlines() if line.strip()][-lines:]
    return "\n".join(f"         {line}" for line in kept)


def report(tests, passes) -> tuple:
    """`(exit code, text)`. Pure: everything is already measured."""
    lines = []
    faults = []
    notes = []

    if not tests:
        faults.append(
            "no test was named. The round closes on each item's NAMED "
            "evidence, so a close with nothing to run has measured nothing")
    for command, code, said in tests:
        if code == 0:
            lines.append(f"  green  {command}")
        else:
            lines.append(f"  red    {command}  (exit {code})")
            if said:
                lines.append(said)
            faults.append(f"the test `{command}` is red")

    if not passes:
        faults.append(
            "no citation pass was named. R1, adopted 2026-08-23: the round "
            "re-runs the citation check over the files it touched and quotes "
            "the summary line BEFORE it may close")
    for one in passes:
        if one.state == "complete":
            ran = f" exit={one.exit_code}" if one.exit_code is not None else ""
            lines.append(f"  pass   {one.sha}  complete{ran}")
            if one.exit_code:
                # NAMED, never refused, which is what `citation_pass.py` does
                # with the same condition. That pass ran and returned, so a
                # re-run reproduces the number and the runner would have no road
                # out of the refusal. The remedy is the register row `SKILL.md`
                # already asks for.
                notes.append(
                    f"the citation pass for {one.sha} returned exit "
                    f"{one.exit_code}. That pass RAN, so file a register row "
                    "naming the sha; do not re-run it")
        else:
            lines.append(f"  pass   {one.sha}  {one.state}")
            faults.append(
                f"the citation pass for {one.sha} is {one.state}. A file with "
                "no terminator is a KILLED pass, not a clean one")

    body = "\n".join(lines) if lines else "  nothing was named"
    if notes:
        body += "\nNote:\n" + "\n".join(f"  - {one}" for one in notes)
    if not faults:
        return 0, (
            "CLOSE AUTHORISED.\n" + body + "\n"
            "  The runner commits and marks the row `done`. A correction round "
            "is not a strike.")

    listed = "\n".join(f"  - {one}" for one in faults)
    return 1, (
        "REFUSED. Fix what is named below, then re-run this check before you "
        "commit.\n" + body + "\nWhy:\n" + listed + "\n"
        "  Two roads out:\n"
        "  1. Re-spawn nothing: fix the named faults in place if they are the "
        "round's own work, re-run the tests and the citation pass, and re-run "
        "this check.\n"
        "  2. If a fault is outside the round's owed list, file a register row "
        "naming it and re-run this check without it. One round is the maximum; "
        "anything bigger is a row, never a second round." + AFK)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--test", action="append", default=[],
                        help="a named test command; repeatable")
    parser.add_argument("--pass-file", action="append", default=[],
                        help="a citation pass output file; repeatable")
    args = parser.parse_args(argv)

    code, text = report(run_tests(args.test),
                        [verdict(one) for one in args.pass_file])
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
