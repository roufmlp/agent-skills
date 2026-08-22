#!/usr/bin/env python3
"""Refuse a ledger state that skips the step before it.

The `/run-issues` finale writes its stage into the run ledger BEFORE the step that
stage names begins, so a session killed inside a step resumes at that step instead of
past it (`finale.md`). The order is fixed:

    finale-mechanical -> finale-judgment -> finale-promotion -> finale-board -> awaiting-merge

**The finale agent has jumped straight to `awaiting-merge` in three consecutive runs.**
The third did it with promotion and the board still unrun, and the runner put the state
back by hand. That run's own ledger says what the harm is: "an interrupted finale resumes
at the state the ledger names, and a premature `awaiting-merge` would have resumed past
two steps that had not happened." Promotion is the step that turns register rows into
issue files. A resume that skips it loses them.

Adopted 2026-08-21. It refuses one thing and nothing else: a transition that is not the
next one in the chain.

Four refusals:

    unknown-state    the ledger's State line names something not in the chain
    no-state         no State line, so nothing can be checked and nothing is assumed
    skips-a-step     the target is further along than one step from the current state
    goes-backwards   the target is behind the current state

A repeat of the same state is allowed. The finale re-enters a stage after an
interruption and rewriting the state it is already on is the correct move.

This does NOT check that a step did its work. It checks the order. A step that ran and
produced nothing is a different fault with a different catcher, and building one guard
for two faults would make both harder to read.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

CHAIN = [
    "finale-mechanical",
    "finale-judgment",
    "finale-promotion",
    "finale-board",
    "awaiting-merge",
]

# `State:` is not at the start of its line in every ledger. One run's ledger
# carries it mid-sentence: "Started 2026-08-20 03:03. State: **`awaiting-merge`ledger".
# An anchored match read that file as having no state at all, which the tests caught.
STATE_LINE = re.compile(r"State:\s*(.+)$", re.MULTILINE)


def read_state(text: str) -> str | None:
    """The stage the ledger currently names, or None.

    The State line is written by hand every run and its decoration is not stable:
    real ledgers have carried `State: **awaiting-merge, reached 15:45.**` and plain
    `State: finale-board`. Match the first chain name that appears on the line rather
    than the whole line, so formatting never decides a refusal.
    """
    for found in STATE_LINE.finditer(text):
        line = found.group(1)
        for stage in CHAIN:
            if stage in line:
                return stage
    return None


def judge(current: str | None, target: str) -> tuple[bool, str]:
    if target not in CHAIN:
        return False, f"unknown-state: '{target}' is not a finale stage"
    if current is None:
        return False, (
            "no-state: the ledger carries no State line naming a finale stage. "
            "Nothing is assumed, so the write is refused."
        )
    here, there = CHAIN.index(current), CHAIN.index(target)
    if there == here:
        return True, f"ok: re-entering '{target}', which a resumed finale is meant to do"
    if there < here:
        return False, f"goes-backwards: the ledger is at '{current}' and this writes '{target}'"
    if there > here + 1:
        skipped = ", ".join(CHAIN[here + 1 : there])
        return False, (
            f"skips-a-step: the ledger is at '{current}' and this writes '{target}', "
            f"which passes {skipped} without running {'it' if there == here + 2 else 'them'}"
        )
    return True, f"ok: '{current}' -> '{target}'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refuse a finale ledger state that skips a step.")
    parser.add_argument("--ledger", required=True, help="path to the run ledger")
    parser.add_argument("--to", required=True, help="the stage about to be written")
    args = parser.parse_args()

    path = pathlib.Path(args.ledger)
    try:
        text = path.read_text()
    except OSError as error:
        print(f"REFUSED unreadable-ledger: {error}", file=sys.stderr)
        return 2

    allowed, reason = judge(read_state(text), args.to)
    if allowed:
        print(reason)
        return 0
    print(f"REFUSED {reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
