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

THE SECOND RULE: THE REGISTER SWEEP. Ticket 36, rulings 6 and 12, ruled by
the human on 2026-09-07.

Ruling 6 puts it in THIS file rather than in a new script, because this one
already walks the register and grades rows, and a second walker would be the
fifth instance of the drift tickets 37 and 39 found four times.

Fault 2 of ticket 36's ten: a register sweep recorded as done while four rows
still read `open`. Promotion reads the status cell, so it would have minted four
issue files for work that had already shipped. It recurs in three runs --
416-419-421, 99b-99e and 375cbf -- and it was the strongest case for a check.

`--sweep <token>` names the rows in scope and grades them for COMPLETENESS: did
somebody decide this row, and did they say why. A row is in scope when the token
names either half of its `origin` cell (`<issue>/<run>`, ticket 37 ruling 7) or
the front of its id. The finale names the RUN, the commit step names the ISSUE.
Nothing else is graded, which is ruling 7's own rule copied -- nothing backfills
-- and it is why this can be turned on over a register holding rounds back to
`b01`.

WHAT THE SWEEP REFUSES: an empty status cell, and an owner-notes that is empty
or repeats the status word and says nothing else.

WHAT IT DOES NOT REFUSE, measured before it was built. Ruling 12 words the
terminal reading "`fixed` or `verified` with a commit". Requiring a commit SHA
refuses FOUR of the five terminal rows in scope on the live register --
`rg571-01` reads `blocks-attempt-1 — <bug file>` and is correct -- so a SHA rule
would stop a finale on real work. And a note that is only a citation passes,
because ruling 13 makes a resolvable citation a legal way to say why: 29 of run
`batch-207704`'s 45 in-scope rows read that way and that run's promotion
resolved all 53. Both are COUNTED and printed, so the rate stays visible without
a refusal. Calibrated against the two examples ruling 12 itself names --
`batch-170a59`'s two rows left `open` with stated reasons pass, and that run's
`vg149g-01` and `vg149g-02`, which read `open` with nothing at all, do not.

Usage:
    python3 check_register_status.py <register.md>
    python3 check_register_status.py <register.md> --quiet   # offences only
    python3 check_register_status.py <register.md> --sweep batch-207704
    python3 check_register_status.py <register.md> --sweep 436 --sweep rg436

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
    # Ticket 36 ruling 12 names `refused` a terminal reading a swept row may
    # take, and `parallel-hunt/SKILL.md` carries it under "Three exits bound
    # the register": "a refusal takes a row out and leaves it". It was missing
    # here, so the shape half of this file would have refused what the sweep
    # half requires -- one file disagreeing with itself, and a false refusal
    # that stops a finale.
    "refused",
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

# `has_origin` is False when the row sits in a table whose header declares no
# `origin` column at all. A caller that asks the writer to repair the cells
# needs to know, because `origin-row-guard.py` refuses every Edit and Write to
# such a table until the column is there -- so "repair those cells" alone is a
# deadlock. Defaulted, so every older caller building a three-field Fault
# still can. Found on `vg149g.md` by the session verifying ticket 36.
Fault = namedtuple("Fault", "row_id reason line has_origin", defaults=(True,))

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


# `origin` is None when the table declares no such column, and "" when the
# column is there and the cell is empty. The two are different repairs: an
# empty cell is filled, a missing column is added to the header first.
Row = namedtuple("Row", "row_id status notes origin line")


def rows(text):
    """Every row this file judges, as `Row`. ONE walk, used by every grader.

    Lifted out of `faults` when the sweep joined it (ticket 36, ruling 6). A
    second walker would be the fifth instance of the drift tickets 37 and 39
    found four times: two readers of one shape disagree eventually, and the
    disagreement is silent. `check_origin.graded` is the same shape and the
    same reason.
    """
    status_at = notes_at = id_at = origin_at = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            status_at = notes_at = id_at = origin_at = None
            continue
        cells = _cells(line)
        lower = [c.lower() for c in cells]
        if "status" in lower:
            status_at = lower.index("status")
            notes_at = lower.index("owner-notes") if "owner-notes" in lower else None
            id_at = lower.index("id") if "id" in lower else 0
            origin_at = lower.index("origin") if "origin" in lower else None
            continue
        if status_at is None or _is_separator(cells):
            continue
        if status_at >= len(cells):
            continue
        yield Row(
            row_id=cells[id_at].strip("` ") if id_at < len(cells) else "(no id)",
            status=normalise(cells[status_at]),
            notes=(cells[notes_at] if notes_at is not None
                   and notes_at < len(cells) else ""),
            origin=(None if origin_at is None
                    else cells[origin_at] if origin_at < len(cells) else ""),
            line=number,
        )


# A terminal reading: the row is out of the loop. Ruling 12's three readings
# are `fixed`/`verified` with a commit, `refused` with a reason, and `open`
# with a reason line; these are the words that mean the first two.
TERMINAL = ("fixed", "verified", "refused", "retracted", "promoted", "closed")

# An inline-code span. A note whose whole body is one of these has cited a bug
# file and nothing else -- legal under ruling 13, and counted rather than
# refused so the rate stays visible.
_CODE = re.compile(r"`[^`]*`")


def said(row):
    """What the writer put in owner-notes beyond the bare status word.

    `"empty"`, `"bare"`, `"citation"` or `"prose"`. The first two are the row
    nobody decided, and they are the only two this refuses.
    """
    raw = _BOLD.sub("", row.notes or "").strip()
    if not raw:
        return "empty"
    body = re.sub(r"^\s*" + re.escape(row.status) + r"\b[\s\u2014:,.;-]*", " ",
                  raw, flags=re.IGNORECASE).strip() if row.status else raw
    if not body:
        return "bare"
    if re.sub(r"[^A-Za-z0-9]+", "", _CODE.sub("", body)):
        return "prose"
    return "citation"


def in_scope(row, tokens):
    """True when one of `tokens` names this row: either half of its `origin`
    cell, or the front of its id.

    Two shapes because two callers. The finale names the RUN and the commit
    step names the ISSUE, and both live in the origin cell ticket 37 ruling 7
    built (`<issue>/<run>`). The id prefix is the fallback for a row filed
    before that column landed.

    The id is matched two ways, because the row-id grammar is
    `<role><issue>-<n>` -- `rg436-01`, `vg577-01`, `im557b-01`, `df-551`. A
    token is either the FRONT of the id, or the issue part inside it. Without
    the second, `--sweep 436` would not reach `rg436-01` at all, and on a shard
    written before the `origin` column landed (ticket 37 ruling 7, 2026-09-05)
    that leaves the sweep with nothing to grade while looking like a pass.

    THE COST, STATED: a token matched as a prefix over-scopes when it is short
    -- `--sweep rg` sweeps every review-gate row ever filed. That can only ADD
    rows to grade, never hide one, and the printed scope count is where a
    caller sees it. Callers pass a whole issue id or a whole run id.

    A row naming no token is OUT of scope and is not graded at all. That is
    ruling 7's own rule copied -- nothing backfills -- and it is why this can
    be turned on over a register holding rounds back to `b01` without reporting
    hundreds of faults nobody can act on.
    """
    origin = _BOLD.sub("", row.origin or "").strip().strip("`").lower()
    halves = [half.strip().strip("`") for half in origin.split("/")] if origin else []
    row_id = row.row_id.lower()
    for token in tokens:
        want = str(token).strip().strip("`").lower()
        if not want:
            continue
        if want in halves or row_id.startswith(want):
            return True
        # `<role><issue>-<n>`: the issue part inside the id. Bounded on both
        # sides, so `436` reaches `rg436-01` and never `rg4361-01`.
        if re.match(r"^[a-z]+-?" + re.escape(want) + r"(?:-|$)", row_id):
            return True
    return False


def sweep_faults(text, tokens):
    """`(offences, swept, told)` — ticket 36 rulings 6 and 12, the register sweep.

    `told` counts how each in-scope row said why, so the caller never has to
    walk the file again to print it. An earlier draft did exactly that and it
    was the drift this file warns about two paragraphs up: two readers of one
    shape, one of them deciding scope a second time.

    WHAT IT CATCHES. A row the sweep never decided: an empty status cell, or an
    owner-notes that is empty or repeats the status word and says nothing else.
    Run `batch-170a59` left `vg149g-01` and `vg149g-02` reading `open` with
    nothing at all in owner-notes; promotion reads the status cell, so each
    would have minted an issue for work nobody had judged.

    WHAT IT DELIBERATELY DOES NOT REFUSE, and this was measured before it was
    built. Ruling 12 words the terminal reading "`fixed` or `verified` with a
    commit". Requiring a commit SHA refuses FOUR of the five terminal rows in
    scope on the live register -- `rg571-01` reads `blocks-attempt-1 — <bug
    file>` and is correct -- so a SHA rule would stop a finale on real work.
    What is required is that the writer said something.

    A note that is only a citation -- `open — `bugs/rg436-01.md`` -- passes and
    is COUNTED. Ruling 13 makes a resolvable citation a legal way to say why,
    and the bug file states the reason in full. Measured: 29 of run
    `batch-207704`'s 45 in-scope rows read that way, and that run's promotion
    resolved all 53. Refusing them would have stopped a clean finale.

    ZERO rows in scope is legal and is not a refusal. An issue whose gates
    filed nothing sweeps nothing, and a check that refused that would stop
    every clean commit. `main`'s empty-input guard still covers the wrong file.
    """
    found = []
    swept = 0
    told = {"prose": 0, "citation": 0, "bare": 0, "empty": 0}
    for row in rows(text):
        if not in_scope(row, tokens):
            continue
        swept += 1
        how = said(row)
        told[how] += 1
        fault = sweep_fault(row, how)
        if fault:
            found.append(fault)
    return found, swept, told


def sweep_fault(row, how):
    """The sweep's offence on one row, or None. `how` is `said(row)`.

    Per row rather than per file, so that `sweep_faults` and `scoped_faults`
    share one grader and can never disagree about what an undecided row is.
    """
    if not row.status:
        return Fault(row.row_id, "the status cell is empty, so the sweep never "
                     "decided this row", row.line, row.origin is not None)
    if how in ("empty", "bare"):
        where = "is empty" if how == "empty" else "repeats the status word"
        return Fault(
            row.row_id,
            f"the status reads {row.status!r} and owner-notes {where}, so "
            f"the row says nothing about why. Ruling 12: a swept row reads "
            f"{'a terminal word with its commit or reason' if row.status in TERMINAL else 'its status with a reason line'}",
            row.line, row.origin is not None)
    return None


def shape_fault(row):
    """The shape check's offence on one row, or None.

    The two rules from the top of this file: the status cell holds a word the
    machine knows, and where owner-notes opens with a status word it agrees
    with the status cell. Per row for the same reason as `sweep_fault`.
    """
    has_origin = row.origin is not None
    if not row.status:
        return Fault(row.row_id, "the status cell is empty", row.line, has_origin)
    if row.status not in LEGAL and row.status not in HISTORY:
        return Fault(
            row.row_id,
            f"the status cell reads {row.status!r}, which the status "
            f"machine does not know", row.line, has_origin)
    noted = normalise(row.notes)
    if noted in LEGAL and row.status in LEGAL and noted != row.status:
        return Fault(
            row.row_id,
            f"the status cell reads {row.status!r} and its own owner-notes "
            f"opens with {noted!r}. One of the two is in the wrong "
            f"cell, which is the transposition of run batch-b5e96d",
            row.line, has_origin)
    return None


def scoped_faults(text, tokens):
    """`(offences, swept, told)` — BOTH graders over the rows `tokens` scope.

    The entry point the sweep gate hook calls. Built on 2026-09-07 when the
    session verifying ticket 36 drove a transposed row -- status `verified`,
    owner-notes `open`, the shape of run `batch-b5e96d`'s ten live rows --
    through the hook and it PASSED, while `--sweep` on the same file refused
    it. The hook called `sweep_faults` alone, and the sweep grades whether a
    writer said why, never whether the cells are in the right order. So a
    runner's commit went through on a row promotion would read wrongly.

    One row yields at most one fault, the shape check's first, which is the
    rule `main` already applies when it merges the two lists: an empty status
    cell offends both graders and printing it twice makes one repair look like
    two. Scope is decided once, here, by `in_scope` -- not a second walker
    (ruling 6).
    """
    found = []
    swept = 0
    told = {"prose": 0, "citation": 0, "bare": 0, "empty": 0}
    for row in rows(text):
        if not in_scope(row, tokens):
            continue
        swept += 1
        how = said(row)
        told[how] += 1
        fault = shape_fault(row) or sweep_fault(row, how)
        if fault:
            found.append(fault)
    return found, swept, told


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
    for row in rows(text):
        graded += 1
        fault = shape_fault(row)
        if fault:
            found.append(fault)
    return found, graded


def main(argv=None):
    # `argv` so the drill can call this in-process, the way every sibling
    # checker in this directory is already written.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("register", help="the register file to grade")
    parser.add_argument("--quiet", action="store_true",
                        help="print the offences and nothing else")
    parser.add_argument("--sweep", action="append", default=[], metavar="TOKEN",
                        help="also grade the sweep over rows this run or issue "
                             "owns; repeatable. A row is in scope when the "
                             "token names either half of its `origin` cell or "
                             "the front of its id")
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
    swept = 0
    told = {"prose": 0, "citation": 0}
    if args.sweep:
        sweep_found, swept, told = sweep_faults(text, args.sweep)
        # A row with an empty status cell offends BOTH graders, and printing it
        # twice makes one repair look like two. The shape check's line is the
        # one kept, because it names the cell rather than the sweep.
        already = {(fault.row_id, fault.line) for fault in found}
        found = found + [fault for fault in sweep_found
                         if (fault.row_id, fault.line) not in already]
    found.sort(key=lambda fault: fault.line)
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
        if args.sweep:
            print(f"{args.register}: sweep over {', '.join(args.sweep)}: "
                  f"{swept} row(s) in scope, every one decided and saying why "
                  f"-- {told['prose']} in prose, "
                  f"{told['citation']} by citation alone.")
            if not swept:
                # A fact, not a refusal: an issue whose gates filed nothing
                # sweeps nothing, and refusing that would stop every clean
                # commit. `empty_input` above still covers the wrong file.
                print(f"{args.register}: no row names "
                      f"{' or '.join(args.sweep)}. Nothing was swept.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
