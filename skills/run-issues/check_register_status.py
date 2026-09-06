#!/usr/bin/env python3
"""Refuse a register row whose status cell cannot be read as a status.

Rule candidate R1, from the coherence finale of run `batch-b5e96d`, ruled by
The human on 2026-09-06.

WHAT IT CATCHES, and why the obvious rule is not enough. The finale found three
rows -- `im557b-01`, `im557b-02` and `im557b-03` -- carrying `verified` in the
status cell and the bare word `open` in the owner-notes cell. Promotion reads
the status cell, so all three would have taken its `fixed` exit on defects that
still reproduce. The finale corrected them by hand.

`verified` IS a legal word, so a check that only tested the status cell against
a vocabulary would have passed all three. The fault was a TRANSPOSITION, and
what makes it visible is that the register's own contract puts a status word in
the notes cell too: `parallel-hunt/SKILL.md`, under "`owner-notes` holds a
status word and a link to `bugs/<ID>.md`. Nothing else, and 200 characters
hard." So two rules, and the
second is the one that earns the build:

  1. The status cell holds a word the status machine knows.
  2. Where owner-notes opens with a status word, it agrees with the status cell.

The vocabulary is the status machine of `parallel-hunt/SKILL.md`, under
"Status machine, single writer per transition":
`candidate`, `open`, `in-fix`, `fix-ready`, `verified`, `retracted`, `deferred`,
plus `fixed`, the exit rule F6 writes. `promoted` and `closed` are accepted
because rows in the register's own history sections carry them; they are exits
that took the row out, and refusing them would report a hundred faults nobody
can act on.

WHAT IT DOES NOT DO. It never judges whether a status is TRUE. A row saying
`verified` on an unfixed defect passes here, because nothing in the file can
tell. It grades the shape a writer filed, which is the class of fault measured.

It prints EVERY offence, not the first, so one pass repairs a whole file. That
copies `check_run_rail.py` beside it, on the ruling of 2026-09-04 recorded in
the decisions queue as `q-h-130` item 2, and it differs from
`check_run_picture.py`, which stops at the first on purpose.

Usage:
    python3 check_register_status.py <register.md>
    python3 check_register_status.py <register.md> --quiet   # offences only

Exit 0 clean, 1 one or more offences, 2 the file could not be read. A third
meaning is never put on a code a caller reads.
"""

import argparse
import os
import re
import sys
from collections import namedtuple

import empty_input

# The status machine, `parallel-hunt/SKILL.md` under "Status machine, single
# writer per transition", plus the three exit words the register's history
# sections carry.
LEGAL = (
    "candidate",
    "open",
    "in-fix",
    "fix-ready",
    "verified",
    "retracted",
    "deferred",
    "fixed",
    "promoted",
    "closed",
)

# Words the status machine does not mint, measured in the register's own
# history sections on 2026-09-06: `issue` (w0808-01, w0808-02), `promotion`
# (seam-390-389-381-05), `done` (hd-401-split), `resolved` (pw-01) and
# `withdrawn` (h0903-22). All six rows are exits taken before the machine was
# written down. They are accepted so that a clean file exits 0 -- a check that
# reports six faults nobody can act on is a check people learn to ignore.
#
# THE COST, STATED: a NEW row typed with one of these words passes too, and
# this file cannot tell a new row from an old one. What still bites is the
# class the finale actually met -- an audience or severity word in the status
# cell, and a status cell that disagrees with its own owner-notes.
HISTORY = (
    "issue",
    "promotion",
    "done",
    "resolved",
    "withdrawn",
)

Fault = namedtuple("Fault", "row_id reason line")

_BOLD = re.compile(r"\*+")
_TRAILING = re.compile(r"^([a-z-]+)\b.*$")


def normalise(cell):
    """The bare status word inside a cell, or "" when there is none.

    Writers decorate: `**fixed 2026-08-23**`, `**promoted -> 421e**`. All three
    forms were measured in the live register on 2026-09-06. The word is always
    first, so take the first token and drop what follows it.
    """
    text = _BOLD.sub("", cell or "").strip().lower()
    if not text:
        return ""
    match = _TRAILING.match(text)
    return match.group(1) if match else ""


# A literal pipe inside a cell is written `\|`, and the register uses it inside
# inline code -- `document_counters` row `h0903-03` carries `2026 \| 4`. Splitting
# on every pipe shifts every column after it and reports a clean row as a fault:
# measured on 2026-09-06, three of ten first refusals were this and nothing else.
_SPLIT = re.compile(r"(?<!\\)\|")


def _cells(line):
    text = line.strip()
    text = text[1:] if text.startswith("|") else text
    text = text[:-1] if text.endswith("|") and not text.endswith("\\|") else text
    return [c.strip() for c in _SPLIT.split(text)]


def _is_separator(cells):
    return all(set(c) <= set("-: ") for c in cells if c != "")


def faults(text):
    """`(offences, graded)` — every offence in one file, and how many rows it read.

    **The count is returned, not discarded, and that is ruling 6 of 2026-09-06.**
    This used to return the list alone, so a file whose every table declares no
    `status` column produced an empty list and the caller printed "every status
    cell reads a legal word" over zero cells. That sentence and a real pass are
    the same bytes. `check_commit_order.py` reported six of them on run
    `batch-170a59`.
    """
    found = []
    graded = 0
    status_at = notes_at = id_at = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            status_at = notes_at = id_at = None
            continue
        cells = _cells(line)
        lower = [c.lower() for c in cells]
        if "status" in lower:
            status_at = lower.index("status")
            notes_at = lower.index("owner-notes") if "owner-notes" in lower else None
            id_at = lower.index("id") if "id" in lower else 0
            continue
        if status_at is None or _is_separator(cells):
            continue
        if status_at >= len(cells):
            continue
        graded += 1
        row_id = cells[id_at].strip("` ") if id_at < len(cells) else "(no id)"
        status = normalise(cells[status_at])
        if not status:
            found.append(Fault(row_id, "the status cell is empty", number))
            continue
        if status not in LEGAL and status not in HISTORY:
            found.append(Fault(
                row_id,
                f"the status cell reads {status!r}, which the status machine "
                f"does not know", number))
            continue
        if notes_at is not None and notes_at < len(cells):
            noted = normalise(cells[notes_at])
            if noted in LEGAL and status in LEGAL and noted != status:
                found.append(Fault(
                    row_id,
                    f"the status cell reads {status!r} and its own owner-notes "
                    f"opens with {noted!r}. One of the two is in the wrong "
                    f"cell, which is the transposition of run batch-b5e96d",
                    number))
    return found, graded


def main(argv=None):
    # `argv` so the drill can call this in-process, the way every sibling
    # checker in this directory is already written.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("register", help="the register file to grade")
    parser.add_argument("--quiet", action="store_true",
                        help="print the offences and nothing else")
    args = parser.parse_args(argv)

    if not os.path.exists(args.register):
        print(f"check_register_status: no such file: {args.register}",
              file=sys.stderr)
        return 2
    try:
        with open(args.register, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as err:
        print(f"check_register_status: cannot read {args.register}: {err}",
              file=sys.stderr)
        return 2

    found, graded = faults(text)
    for fault in found:
        print(f"{args.register}:{fault.line}: {fault.row_id}: {fault.reason}")
    if found:
        print(f"{len(found)} row(s) refused. Repair the cells and run this again.")
        return 1

    # The guard goes AFTER the offences, so a file that produced faults is never
    # also called unreadable, and BEFORE the pass line, which is the sentence
    # this refusal exists to stop being printed over nothing. Unlike
    # `check_origin.py`, this reader has no legitimate zero: every register and
    # every shard declares a `status` column, so zero graded rows means the
    # wrong file or a table shape this reader does not know.
    if empty_input.refuse_empty(
        graded,
        args.register,
        "row under a `status` column",
        read=len([1 for line in text.splitlines()
                  if line.lstrip().startswith("|")]),
        remedy="Promotion calls this before it resolves a row, so a vacuous "
               "pass here clears every row in the file. Check the path names "
               "the register or a shard, and that a header row declares "
               "`status`.",
    ):
        return empty_input.EXIT_EMPTY

    if not args.quiet:
        print(f"{args.register}: {graded} row(s) graded, every status cell "
              f"reading a legal word and agreeing with its own owner-notes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
