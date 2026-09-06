#!/usr/bin/env python3
"""Refuse a ledger row whose commit predates the correction round it contains.

## The check this replaces could not fail

`SKILL.md` rule 9 tells the finale to read each issue's commit time with
`git log -1 --format=%ad` and compare it against the stamp the ledger carries.
That catches a runner that wrote a wrong time, and nothing else — the runner
writes one from the other, so the two agree by construction whenever the runner
is working normally.

What it cannot see is the fault that matters: a commit stamped BEFORE the
correction round whose items it is supposed to contain. Run `batch-34455f`,
2026-08-25, carries two of them.

    413b   correction closed 07:28, committed e9737396 at 07:02
    413    correction closed 10:00, committed da0ce42b at 08:05

Both rows read as healthy under rule 9, because the ledger's own stamp and the
git author date agree in each case. They agree on a time that is too early.

## Why the two sources cannot drift into agreement

The correction-round close comes from the ledger, written when the round ended.
The commit time comes from git. Neither is derived from the other, so a match
here is evidence rather than bookkeeping — which is the whole reason rule 9's
comparison was worth replacing rather than repairing in place.

## What a refusal means, and what it does not

It means the commit does not contain the round's work, or the round's items
went in under a later commit nobody recorded, or one of the two times is wrong.
All three want a human. It does NOT mean the code is bad: the correction round
may have landed in a later commit on the same branch, which is a paperwork
fault in the ledger and still worth catching, because every per-issue duration
in a run's records comes from these stamps and `orchestrator_cost.py` inherits
them.

Three refusals:

    commit-precedes-round   the commit is earlier than the correction round it
                            is recorded as carrying
    git-failed              a commit could not be read, so nothing is assumed
    empty-input             this read zero rows of a shape it must find, so it
                            asserts nothing. Two shapes are guarded: the status
                            table itself, and the `committed <sha>` stamp. See
                            `empty_input.py` for why a pass over nothing is a
                            refusal here rather than an `ok`.

Usage:

    python3 check_commit_order.py --ledger .scratch/<feature>/runs/<batch-id>/run.md --repo .

Exit 0 when every row holds, 1 on any refusal, 2 when git or the ledger could
not be read.
"""

import argparse
import re
import subprocess
import sys

import empty_input

# A row of the ledger's status table. Both times are `HH:MM` on the run's own
# day; a run that crosses midnight is out of scope and says so below.
#
# **The id is read by COLUMN, not by an em-dash.** This used to be
# `^\|\s*([0-9]+[a-z]?)\s*—`, which demanded the `| 483 — title |` shape and
# matched nothing against a ledger writing `| 483 | 2h | done | … |`. On run
# `414a-483-286335` it read ZERO rows and printed `ok`: register row
# `rn414a-01`. `check_attempt_cap.py` had already solved the same problem by
# splitting cells and taking the first token, so this does the same rather than
# keeping a second dialect of the same table.
ID_IN_CELL = re.compile(r"^(?P<issue>[0-9]+[a-z]?)(?![0-9a-z])")
SEPARATOR = re.compile(r"^\|[\s|:-]+\|?\s*$")
CLOSED = re.compile(r"correction:.*?closed\s+(?P<time>[0-2]?[0-9]:[0-5][0-9])", re.IGNORECASE)

# **The commit's own `HH:MM` is OPTIONAL, and that is deliberate.** It used to be
# required, and `rows_from` needs both patterns, so a ledger that stopped writing
# it would have made this print `ok` on zero graded rows — the exact silence the
# empty-table refusal below exists to prevent. The human ruled on 2026-08-31 that the
# ledger's per-step clocks go and only the correction-round close stamp stays, so
# a row reading `committed \`e9737396\`` with no time is now the normal shape.
# Nothing is lost: git supplies the time this check actually compares. The ledger
# stamp, when present, is only quoted back in the refusal.
#
# **The BACKTICKS are optional, and that is the whole of ruling 6(a).** This
# pattern demanded them. `SKILL.md:284` tells the runner to write `committed
# <sha>` — bare — so the script and the skill that drives it disagreed about the
# shape of the one stamp this check exists to read. On run `batch-170a59` every
# ledger row obeyed the skill, the pattern matched zero of them, and six `ok`
# results were vacuous. Both forms are now read, so neither the skill nor any
# ledger already written in either dialect has to move.
# The backtick is captured and matched again by backreference, so an opening one
# demands a closing one and a bare sha demands neither. `(?![0-9a-z])` stops a
# 45-character hex token being read as its own first 40 characters.
COMMITTED = re.compile(
    r"committed\s+(?P<tick>`?)(?P<sha>[0-9a-f]{7,40})(?P=tick)(?![0-9a-z])"
    r"(?:\s+(?P<time>[0-2]?[0-9]:[0-5][0-9]))?")

REMEDY = (
    "A commit cannot carry a correction round that closed after it. Either the round's\n"
    "items went in under a later commit, or one of the two times is wrong. Find which,\n"
    "and correct the ledger row before the briefing quotes a duration from it."
)


def minutes(stamp):
    """`HH:MM` as minutes past midnight."""
    hours, mins = stamp.split(":")
    return int(hours) * 60 + int(mins)


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def tables(text):
    """Every markdown table on the page, as a list of its stripped lines.

    A table is a CONTIGUOUS run of lines beginning with a pipe. A blank line, a
    heading or a paragraph ends one, which is what markdown itself requires to
    render two tables rather than one.
    """
    found, current = [], []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            current.append(stripped)
        elif current:
            found.append(current)
            current = []
    if current:
        found.append(current)
    return found


def status_table(text):
    """`(lines, column)` for the status table, or `([], 0)` when there is none.

    **The status table is the one whose HEADER declares `issue`, and the bound
    is the whole of ticket 37 ruling 28's repair half.** Until 2026-09-06 this
    reader walked every pipe line on the page, so any other table whose first
    cell could pass for an issue id was counted as issues. Run `batch-170a59`
    reported 12 issues for six, because its carry-forward table of test counts
    at `run.md:35-43` writes rows opening `149c (-13, -3)`. The totals were
    right and the DENOMINATOR was wrong, so every rate ruling 6 asks for was
    wrong -- and the number had already reached a merge briefing.

    Two header shapes are in use: `| Issue | Status | …` puts the id first, and
    `| # | issue | …` puts it second behind a row number. Measured 2026-09-06
    over the sixteen ledgers on this machine that hold a status table, every
    one of them declares `issue` in that header.

    **A page with no such header returns nothing rather than guessing**, and
    that is deliberate. The header is the only thing that tells a status table
    from a carry-forward table, so a reader without one cannot tell them apart;
    guessing is what produced the phantom rows. `empty_input.py` already turns
    a zero read into a refusal here, and `run_quality.render_quality` prints
    "no status table was read ... a missing measurement, not a clean run". Both
    say a hole rather than inventing a figure.
    """
    for lines in tables(text):
        # Every line of the block, not only the first. A ledger writing any
        # pipe line directly above its header -- `| Run | batch-x |` -- puts
        # both in one contiguous block, and testing `lines[0]` alone lost the
        # whole table. Found by the review of 2026-09-06; no ledger on this
        # machine does it, so the loss was latent rather than live.
        #
        # A data row cannot be mistaken for the header: the test is a cell
        # reading exactly `issue`, and a data row's cell reads `149c`.
        for index, line in enumerate(lines):
            lowered = [cell.lower() for cell in cells(line)]
            if "issue" in lowered:
                return lines[index + 1:], lowered.index("issue")
    return [], 0


def issue_column(text):
    """Which column of the status table holds the issue id.

    Kept because `check_attempt_cap.py` and `estimate_accuracy.py` read the
    same header, and because a caller wanting only the column should not have
    to take the rows as well.
    """
    return status_table(text)[1]


def status_rows(text):
    """Every data row of the status table, whatever its column shape.

    This is the denominator. `rows_from` grades a subset of these, and the
    caller prints both numbers, so `ok` on a table this could not read is a
    different sentence from `ok` on a table with nothing to grade.
    """
    lines, column = status_table(text)
    found = []
    for stripped in lines:
        if SEPARATOR.match(stripped):
            continue
        parts = cells(stripped)
        if len(parts) <= column:
            continue
        token = ID_IN_CELL.match(parts[column])
        if not token:
            continue  # A wrapped header, and any row that names no issue.
        found.append((token.group("issue"), stripped))
    return found


def rows_from(text):
    """Every status row that records BOTH a correction round and a commit.

    A row with no correction round is not graded: plenty of issues pass their
    gates and go straight to a commit, and there is nothing to be out of order
    with. Silence on those is correct, not a gap.
    """
    found = []
    for issue, line in status_rows(text):
        closed = CLOSED.search(line)
        committed = COMMITTED.search(line)
        if not closed or not committed:
            continue
        found.append(
            {
                "issue": issue,
                "closed": closed.group("time"),
                "sha": committed.group("sha"),
                "stamped": committed.group("time"),   # None once the clocks go
            }
        )
    return found


def judge(row, author_time):
    """Grade one row against git's own answer. Returns a detail string or None.

    `author_time` is `HH:MM` from `git log`. A run that crosses midnight would
    read a small number as early when it is late; this refuses to guess and the
    caller reports it, because a run of that shape has never happened here and
    inventing a date rule for it would be untested code on a live path.
    """
    gap = minutes(row["closed"]) - minutes(author_time)
    if gap <= 0:
        return None
    detail = (
        f"issue {row['issue']}: commit `{row['sha']}` is stamped {author_time} by git, "
        f"{gap} minute(s) BEFORE the correction round this row says it carries "
        f"(closed {row['closed']})."
    )
    if row["stamped"]:
        detail += f" The ledger's own commit stamp reads {row['stamped']}."
    return detail


def author_time_of(repo, sha):
    result = subprocess.run(
        ["git", "-C", repo, "log", "-1", "--format=%ad", "--date=format:%H:%M", sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git could not read {sha}")
    return result.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)

    try:
        with open(args.ledger, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print(f"REFUSED unreadable: {args.ledger}: {error}", file=sys.stderr)
        return 2

    # Two guards, and they name DIFFERENT absences. This one is the table: a
    # ledger always carries one row per issue, so zero is the wrong file or a
    # column shape this reader does not know (`rn414a-01`, run
    # `414a-483-286335`).
    seen = status_rows(text)
    if empty_input.refuse_empty(
        len(seen),
        args.ledger,
        "status row",
        read=len([1 for line in text.splitlines()
                  if line.strip().startswith("|")]),
        remedy="A ledger carries one status row per issue. Check this is the "
               "run's own `run.md`, and that its table's issue column is where "
               "`issue_column` looks for it.",
    ):
        return empty_input.EXIT_EMPTY

    # This one is the STAMP, and it is the `batch-170a59` silence. `SKILL.md`
    # runs this check right after writing a `committed <sha>` stamp, so by the
    # time it runs at least one row carries one and zero means the pattern and
    # the ledger disagree. It is deliberately NOT a guard on correction rounds:
    # a run where every issue passed its gates first time carries none, and
    # refusing that would refuse a healthy run.
    stamped = [line for _, line in seen if COMMITTED.search(line)]
    if empty_input.refuse_empty(
        len(stamped),
        args.ledger,
        "row recording a `committed <sha>` stamp",
        read=len(seen),
        remedy="This check runs after a commit stamp is written, so one always "
               "exists by then. Read a status row and compare it against "
               "`COMMITTED` in this file. Run `batch-170a59` reached the finale "
               "with six vacuous `ok` results on exactly this absence.",
    ):
        return empty_input.EXIT_EMPTY

    rows = rows_from(text)
    if not rows:
        print(
            f"ok: {len(seen)} status row(s) read, {len(stamped)} carrying a "
            "commit stamp, none of them also recording a correction round"
        )
        return 0

    faults = []
    for row in rows:
        try:
            author_time = author_time_of(args.repo, row["sha"])
        except RuntimeError as error:
            print(f"REFUSED git-failed: {error}", file=sys.stderr)
            return 2
        detail = judge(row, author_time)
        if detail:
            faults.append(detail)

    if not faults:
        print(
            f"ok: {len(seen)} status row(s) read, {len(stamped)} carrying a commit "
            f"stamp, {len(rows)} carrying a correction round, every one of those "
            "committed after its round"
        )
        return 0

    for detail in faults:
        print(f"REFUSED commit-precedes-round: {detail}", file=sys.stderr)
    print(f"\n{REMEDY}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
