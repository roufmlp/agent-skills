#!/usr/bin/env python3
"""Refuse a run journal that has fallen behind its own ledger.

## The fault this closes

Run `batch-b00631` committed six issues and journalled two. Issues 35, 27b, 21c
and 110 -- four of six, including both large issues and the run's only migration
-- have no entry at all. Nothing noticed, because a journal that stops looks
exactly like a journal nobody needed.

It cost that run nothing, and that is the point: the run never had to resume.
Had it halted after issue 34, a resuming runner would have opened the journal and
found nothing for the four issues still to come. The journal's own header says
who reads it -- "a resuming runner, and the finale" -- and neither reader exists
until the moment the record is already missing.

## Why a check and not a reminder

The human's rule, `~/.claude/CLAUDE.md`: a proposal that asks an agent to
remember will not work; make it mechanical or let it go. A journal entry is
exactly the kind of step a runner under load drops without noticing, and the
previous control was a sentence in `SKILL.md` telling it not to.

The alternative weighed and not taken was deleting the journal outright, on the
ground that the ledger and the merge briefing carry the same record for a run
that does not halt. The human's ruling of 2026-09-19 went to the refusal, so the
journal stays and this is what holds it up.

## What it reads, and what it refuses

The ledger's `## Status` table is the source of truth for what the run has
committed. A row is graded when its stamps cell names a commit, because that is
the moment the work became part of the branch and the moment a resuming runner
would need to know what happened. `check_commit_order.py` already owns both the
table parser and the `committed <sha>` pattern, so they are imported rather than
copied. One change to the ledger's shape then moves one file.

The journal is read whole. Every `##` heading is scanned for the issues it names,
so a runner that writes one heading covering two issues satisfies both, and a
heading that names no issue -- a launch note, a baseline measurement -- is
neither counted nor refused.

THE GUARD IS A COMPARISON, NOT A LIST OF SPELLINGS. It never enumerates the
headings a journal is allowed to carry. It takes the set of committed issues, the
set of journalled issues, and refuses the difference, whatever either side is
called.

Four refusals:

    journal-behind      an issue is committed in the ledger and named by no
                        journal heading
    no-journal          the ledger names committed work and the journal file is
                        not there at all
    empty-input         zero committed rows were read from a table that must
                        hold some, so this asserts nothing. See
                        `empty_input.py` for why a pass over nothing is a
                        refusal here rather than an `ok`.
    unreadable          the ledger holds no status table this can parse

Usage:

    python3 check_run_journal.py --run .scratch/<feature>/runs/<batch-id>

    python3 check_run_journal.py --ledger <path to run.md> \\
        --journal <path to run-journal.md>

Exit 0 when every committed issue has an entry, 1 on any refusal, 2 when a file
could not be read.

**Where it runs.** The runner's commit step, before it commits the issue. That is
the latest moment the missing entry is still cheap to write and the earliest
moment the ledger knows the issue is done.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

import check_commit_order
import empty_input

# An issue named in a journal heading: the word, then a LIST of ids.
#
# The list is why this is not one id. A runner that closes two issues together
# writes one heading for both -- "issues 35 and 27b, closed together" -- and a
# reader taking only the first id would refuse a journal that is complete. That
# is the wrong direction for a guard standing in front of a commit: a false
# refusal costs a runner an entry it has already written, and teaches it that
# the check is noise.
#
# The trailing guard stops `110` matching inside `1100`, and stops `21` matching
# the `21c` beside it, which would let a journal cover the wrong issue and read
# green.
#
# WHAT IT DOES NOT REACH, said plainly. A heading reading "issue 34, 1 of 2"
# would read `1` as a second id, because a comma followed by a number is exactly
# the shape of a list. Nothing is refused wrongly by that -- a phantom id can
# only ADD to what the journal appears to cover -- but a tracker holding an
# issue literally numbered `1` could see that issue pass unwritten. This
# tracker's ids are `22b`, `34`, `110`; the day one is `1`, tighten the
# separator to `and` alone.
ISSUE_LIST = re.compile(
    r"\bissues?\s+(?P<list>[0-9]+[a-z]?(?:\s*(?:,|and|&|\+)\s*[0-9]+[a-z]?)*)(?![0-9a-z])",
    re.IGNORECASE,
)

ONE_ID = re.compile(r"[0-9]+[a-z]?")

HEADING = re.compile(r"^#{1,6}\s")

REMEDY = (
    "A resuming runner reads the journal and nothing else for the issues it did not\n"
    "see. Write the missing entry before the commit: what was attempted, what the\n"
    "gates answered, and what the correction round changed. One heading may name\n"
    "more than one issue."
)


def journalled(text):
    """Every issue id named by a heading of the journal.

    Only headings are read. An issue mentioned in the body of another issue's
    entry is a cross-reference, not a record of that issue's own round, and
    counting it would let one entry satisfy an issue nobody wrote about.
    """
    found = set()
    for line in text.splitlines():
        if not HEADING.match(line):
            continue
        for match in ISSUE_LIST.finditer(line):
            found.update(ONE_ID.findall(match.group("list")))
    return found


def committed(text):
    """Every issue the ledger's status table records as committed.

    The table parser and the `committed <sha>` pattern belong to
    `check_commit_order.py`. Importing them means a change to the ledger's shape
    moves one file and both checks follow it.
    """
    found = []
    for issue, line in check_commit_order.status_rows(text):
        if check_commit_order.COMMITTED.search(line):
            found.append(issue)
    return found


def gaps(ledger_text, journal_text):
    """Committed issues with no journal heading, in the ledger's own order."""
    entries = journalled(journal_text)
    return [issue for issue in committed(ledger_text) if issue not in entries]


def _read(path, stream):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as error:
        print(f"unreadable: {path}: {error}", file=stream)
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", help="the run directory holding run.md and run-journal.md")
    parser.add_argument("--ledger", help="path to run.md")
    parser.add_argument("--journal", help="path to run-journal.md")
    args = parser.parse_args(argv)

    if args.run:
        directory = pathlib.Path(args.run)
        ledger_path = args.ledger or directory / "run.md"
        journal_path = args.journal or directory / "run-journal.md"
    elif args.ledger and args.journal:
        ledger_path, journal_path = args.ledger, args.journal
    else:
        parser.error("pass --run, or both --ledger and --journal")

    stream = sys.stderr
    ledger_text = _read(ledger_path, stream)
    if ledger_text is None:
        return 2

    try:
        done = committed(ledger_text)
    except (IndexError, ValueError) as error:
        print(f"unreadable: {ledger_path} holds no status table this can parse: {error}",
              file=stream)
        return 2

    # The collector found something. Without this, a ledger whose stamps cell
    # stopped naming commits would print `ok` on nothing at all -- the silence
    # this check exists to prevent, arriving through the check itself.
    # `read` is the denominator: how many status rows were seen at all. Zero
    # commits out of six rows is a pattern fault; zero out of zero rows is the
    # wrong file. `empty_input` says those want different repairs.
    if empty_input.refuse_empty(
        len(done),
        source=str(ledger_path),
        shape="a status row stamped `committed <sha>`",
        read=len(check_commit_order.status_rows(ledger_text)),
        remedy="A run with nothing committed has nothing to journal yet. Run this "
               "at the commit step, after the ledger row is written.",
        stream=stream,
    ):
        return 1

    journal_text = _read(journal_path, stream)
    if journal_text is None:
        print(
            f"no-journal: the ledger records {len(done)} committed issue(s) "
            f"({', '.join(done)}) and there is no journal at {journal_path}.\n\n{REMEDY}",
            file=stream,
        )
        return 1

    missing = gaps(ledger_text, journal_text)
    if missing:
        print(
            f"journal-behind: {len(missing)} of {len(done)} committed issue(s) have no "
            f"journal heading: {', '.join(missing)}.\n\n{REMEDY}",
            file=stream,
        )
        return 1

    print(f"ok: {len(done)} committed issue(s), every one named by a journal heading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
