#!/usr/bin/env python3
"""Refuse a register row, or a minted issue, that does not name where it came from.

Ticket 37 of the pilot-delivery map, ruling 7, ruled by the human on 2026-09-05.

WHY IT EXISTS. "Escaped faults" -- a fault found later that traces back to the
run that shipped it -- is the only measure of what the pipeline lets through,
and it was not measurable at all. Measured 2026-09-05: no register row, issue
file or commit message carries a field naming the run or the issue that shipped
the code. The finder's row shape carries no origin field, and promotion writes
the fact as a blockquote that nothing reads.

THE FACT ALREADY EXISTS, IN PROSE. Shard `rv149e.md` of run `batch-170a59`
opens its owner-notes with "From issue 149e's review gate, run `batch-170a59`".
So the writer knows it and writes it; it is uncountable because it is a
sentence. This gives it a cell.

NOTHING BACKFILLS, and that is held mechanically rather than by a date. Ruling 7
starts the count the day the key lands. A table whose header does not declare an
`origin` column is history and is skipped whole -- not graded and not reported.
The register holds rounds going back to `b01` under a dozen header shapes, and a
check that refused them would report hundreds of faults nobody can act on, which
is a check people learn to ignore.

That leaves one hole this file cannot close: a NEW table typed without the
column escapes, because a missing column and a historical table look alike here.
`origin-row-guard.py` in the hooks closes it at the moment of writing, which is
the only place the difference is visible.

THE GRAMMAR. Two parts, an issue and a run, written `<issue>/<run>`:

    149e/batch-170a59     both known
    unknown/batch-170a59  the run is known and no single issue is
    149e/unknown          the issue is known and the run is not
    unknown               neither is known

`unknown` is the explicit null, and it is legal on purpose. It copies `Owed:
unsorted`, ruled by the human on 2026-08-13: a null that is present cannot be told
from a field somebody forgot, and a writer with no legal way to say "I do not
know" invents one. The production watcher files rows from Sentry groups and
genuinely does not know either half. The count of `unknown` is printed, so the
rate stays visible without a refusal.

WHAT IT DOES NOT DO. It never judges whether an origin is TRUE. A row naming the
wrong run passes here, because nothing in the file can tell. It grades the shape
a writer filed.

It prints EVERY offence, not the first, so one pass repairs a whole file. That
copies `check_register_status.py` beside it, which is correct for the same
reason: both grade a file a person is about to repair by hand, and stopping at
the first turns one repair into many passes.

Usage:
    python3 check_origin.py --register <register.md>
    python3 check_origin.py --issue <issue file>

Exit 0 clean, 1 one or more offences, 2 the file could not be read. A third
meaning is never put on a code a caller reads.
"""

import argparse
import os
import re
import sys
from collections import namedtuple

Fault = namedtuple("Fault", "row_id reason line")

# The tracker's issue id: `512`, `149e`, `402b`. Same shape as
# `check_issue_ready.ID_FROM_NAME`, which reads it off a file name.
ISSUE = re.compile(r"^\d+[a-z]?$", re.IGNORECASE)

# A run or round id is one bare token. Deliberately not pinned harder: the
# record holds `batch-170a59`, `review-375cbf`, `bridge-cse` and `round-10`,
# and a pattern narrow enough to exclude a typo would exclude four of those.
RUN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

UNKNOWN = "unknown"

_BOLD = re.compile(r"\*+")

# A literal pipe inside a cell is written `\|`. Splitting on every pipe shifts
# every column after it and reports a clean row as a fault: the lesson
# `check_register_status.py` records from 2026-09-06.
_SPLIT = re.compile(r"(?<!\\)\|")


def cells(line):
    text = line.strip()
    text = text[1:] if text.startswith("|") else text
    text = text[:-1] if text.endswith("|") and not text.endswith("\\|") else text
    return [c.strip() for c in _SPLIT.split(text)]


def _is_separator(row):
    return all(set(c) <= set("-: ") for c in row if c != "")


def parse_origin(value):
    """The two halves of a legal origin, or None.

    Returns `(issue, run)`, either of which may be the word `unknown`.
    """
    text = _BOLD.sub("", value or "").strip().strip("`").strip().lower()
    if not text:
        return None
    if text == UNKNOWN:
        return (UNKNOWN, UNKNOWN)
    parts = text.split("/")
    if len(parts) != 2:
        return None
    issue, run = (p.strip().strip("`").strip() for p in parts)
    if not (issue == UNKNOWN or ISSUE.match(issue)):
        return None
    if not (run == UNKNOWN or RUN.match(run)):
        return None
    return (issue, run)


def graded(text):
    """Every row this file judges: `(row_id, origin cell, line number)`.

    ONE walk, used by both readers. `check_origin` grew a second copy of this
    loop for the `unknown` count, which is the drift `journal_for` taught in
    ticket 39 sitting 2: two readers of one shape disagree eventually, and the
    disagreement is silent.

    A table whose header declares no `origin` column yields nothing. That is
    where "nothing backfills" lives, and it is one line so it cannot be
    half-applied by one caller and not the other.
    """
    origin_at = id_at = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            origin_at = id_at = None
            continue
        row = cells(line)
        lower = [c.lower() for c in row]
        if "origin" in lower:
            origin_at = lower.index("origin")
            id_at = lower.index("id") if "id" in lower else 0
            continue
        if origin_at is None or _is_separator(row) or origin_at >= len(row):
            continue
        row_id = row[id_at].strip("` ") if id_at < len(row) else "(no id)"
        yield (row_id, row[origin_at], number)


def register_faults(text):
    """Every offence in one register or shard, in the order they appear."""
    found = []
    for row_id, cell, number in graded(text):
        if not _BOLD.sub("", cell).strip():
            found.append(Fault(row_id, "the origin cell is empty", number))
            continue
        if parse_origin(cell) is None:
            found.append(Fault(
                row_id,
                f"the origin cell reads {cell!r}, which is not "
                f"`<issue>/<run>` and is not `unknown`", number))
    return found


# The header field, on its own line, beside `Owed:` and `Stage:`. Anchored at
# the start of the line so a sentence opening with the word cannot pass for one.
ORIGIN_LINE = re.compile(r"^Origin:\s*(.*)$", re.MULTILINE | re.IGNORECASE)

# The issue's own title. Everything above it is the header; a field below it is
# body prose, whatever it is called.
TITLE = re.compile(r"^#\s+", re.MULTILINE)


def issue_faults(text):
    """Every offence in one minted issue file.

    A list, not a single fault, so one caller shape serves both halves of this
    check and a future second rule on the same file has somewhere to land.
    """
    title = TITLE.search(text)
    header = text[:title.start()] if title else text
    match = ORIGIN_LINE.search(header)
    if not match:
        return [Fault("(the issue file)",
                      "it carries no `Origin:` line in its header, above the "
                      "title, so nothing can say which run shipped the code "
                      "this fault is in", 0)]
    line = header[:match.start()].count("\n") + 1
    value = match.group(1)
    if not _BOLD.sub("", value).strip():
        return [Fault("(the issue file)", "its `Origin:` line is empty", line)]
    if parse_origin(value) is None:
        return [Fault(
            "(the issue file)",
            f"its `Origin:` line reads {value.strip()!r}, which is not "
            f"`<issue>/<run>` and is not `unknown`", line)]
    return []


def graded_rows(text):
    """`(graded, unknown)` — how many rows were judged, and how many took `unknown`.

    The pass line prints both. Ruling 7 skips a table declaring no `origin`
    column, so a file can be clean because nothing in it was graded, and a pass
    that does not say so is the `ok` on a table nobody could read that
    `check_commit_order.status_rows` exists to prevent.

    `unknown` is legal and refused by nothing, so the only way its rate stays
    honest is for the pass to say how many took it.
    """
    rows = list(graded(text))
    blank = sum(1 for _, cell, _ in rows if parse_origin(cell) == (UNKNOWN, UNKNOWN))
    return (len(rows), blank)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--register", help="a register or shard file to grade")
    what.add_argument("--issue", help="a minted issue file to grade")
    parser.add_argument("--quiet", action="store_true",
                        help="print the offences and nothing else")
    args = parser.parse_args(argv)

    path = args.register or args.issue
    if not os.path.exists(path):
        print(f"check_origin: no such file: {path}", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as err:
        print(f"check_origin: cannot read {path}: {err}", file=sys.stderr)
        return 2

    found = (register_faults(text) if args.register else issue_faults(text))
    for fault in found:
        where = f"{path}:{fault.line}" if fault.line else path
        print(f"{where}: {fault.row_id}: {fault.reason}")
    if found:
        if args.register:
            print(f"{len(found)} row(s) refused. Add the origin and run this "
                  f"again.")
        else:
            print(
                f"{len(found)} issue file refused. Add the origin and run this "
                f"again.\n"
                f"This mode grades a file promotion has JUST minted. Every issue "
                f"written before ticket 37 landed carries no `Origin:` line by "
                f"design — ruling 7 starts the count the day the key lands and "
                f"backfills nothing — so do not run it over the issue "
                f"directory.")
        return 1
    if not args.quiet:
        if args.register:
            graded, blank = graded_rows(text)
            print(f"{path}: {graded} row(s) graded, all naming an origin; "
                  f"{blank} took `unknown`. A table declaring no `origin` "
                  f"column is history and is not graded.")
        else:
            print(f"{path}: the `Origin:` line is present and reads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
