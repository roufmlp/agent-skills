#!/usr/bin/env python3
"""One refusal, shared: a checker that parsed nothing may not report a pass.

## The class, measured three times

A checker reads a file, its pattern matches zero rows, it finds no fault in
those zero rows and it prints `ok`. Nothing is wrong with the code and nothing
is wrong with the file. The instrument simply never looked at anything, and its
silence is byte-for-byte the silence of a clean result.

    batch-170a59    `check_commit_order.py` ran at six commit steps and the
                    finale and reported `ok` six times over nothing. The run
                    journal counts six. Its `COMMITTED` pattern
                    demanded the sha in BACKTICKS and every ledger row that run
                    wrote it bare — as `SKILL.md` itself instructs, `committed
                    <sha>`. The check never saw a single commit stamp. The
                    runner found it at the finale, by hand, while wondering why
                    a row that plainly recorded both a round and a commit was
                    reported as recording neither.

    414a-483-286335 the same script, one fault earlier: its id pattern demanded
                    `| 483 — title |` and the ledger wrote `| 483 | 2h | … |`.
                    Zero rows, `ok`. Register row `rn414a-01`.

    399-403         `--touches` on `check-issue-citations.mjs`, twice in one
                    run.

## Why prose did not close it

`run-issues/SKILL.md` has carried the rule in words since 2026-08-29: report a
zero as "this file carries no parsed citations at this moment" and never as a
property of the instrument. The fault recurred anyway, on a different script,
five days later. The human ruled on 2026-09-06 that the rule becomes a refusal,
because an agent cannot be asked to remember one.

## What a caller gets, and what it still owes

This builds the sentence and prints it. It cannot know whether zero is a fault,
so the caller decides where to put the guard — and that decision is the whole
skill in using this. Two rules learned from the survey that came with the
ruling:

  * Guard the shape whose ABSENCE is impossible, not merely unusual.
    `check_commit_order.py` guards "no row carries a commit stamp", because the
    skill runs it right after writing one. It does NOT guard "no row carries a
    correction round", because a run where every issue passed its gates first
    time legitimately has none.

  * Where zero is legitimate and the reader already says so, leave it.
    `check_origin.py` yields nothing for a table declaring no `origin` column,
    and that is ticket 37 ruling 7 working as built — history is never graded
    and nothing backfills. Its pass line prints the count and names the reason.
    A refusal there would refuse correct files.

`EXIT_EMPTY` is 2, not 1, and the difference carries meaning everywhere in this
directory: 1 is "the input was read and it is wrong", 2 is "the input could not
be read, so nothing is asserted about it". A vacuous pass is the second.
"""

import sys

EXIT_EMPTY = 2


def empty_refusal(source, shape, read=None, remedy=None):
    """The sentence a checker prints when it parsed zero rows of `shape`.

    `shape` NAMES what could not be parsed, in the checker's own words, and is
    the reason this is a refusal rather than a silence. "no row" tells the
    reader nothing; "no row recording a commit stamp" tells them where to look.

    `read` is the denominator when the checker has one — how many lines or rows
    it did see. Zero matches out of 40 rows read is a pattern fault; zero out of
    zero is the wrong file. Those want different repairs, so the message
    separates them.
    """
    lines = [f"REFUSED empty-input: {source} yields no {shape} this reader "
             f"could parse."]
    if read is not None:
        lines.append(
            f"  It read {read} candidate row(s) and matched none of them, so "
            f"the file is not empty — this reader's shape and the file's shape "
            f"disagree." if read
            else "  It read 0 candidate rows, so this is very likely the wrong "
                 "file rather than a pattern fault.")
    lines.append(
        "  This is NOT a pass. A check that matched nothing is indistinguishable "
        "from a check that passed, and reporting the second when the first "
        "happened has now cost three runs (`batch-170a59`, `414a-483-286335`, "
        "and the 399-403 run twice).")
    if remedy:
        lines.append(f"  {remedy}")
    return "\n".join(lines)


def refuse_empty(count, source, shape, read=None, remedy=None, stream=None):
    """Print the refusal and return True when `count` is zero. Else False.

    The call site is one line, which is the point: a clause copied into each
    checker drifts, and this class is already three incidents of one clause
    being absent rather than wrong.
    """
    if count:
        return False
    print(empty_refusal(source, shape, read=read, remedy=remedy),
          file=sys.stderr if stream is None else stream)
    return True
