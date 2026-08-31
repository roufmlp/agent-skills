#!/usr/bin/env python3
"""Refuse a paste file whose confirmation query is commented out.

A paste file is the road a migration takes to a database no script may write
to. Where a repo guards its production ref in code, the migration is pasted
into the SQL editor by hand instead, and the confirmation query under it is the
only thing that says whether the migration landed.

**One run shipped two such files with that query behind `--`.** Both ended with
an instruction to run the query on its own, and the SQL under it commented out.
Pasted as written, a commented query returns no rows, no error and no output —
which reads exactly like a clean result.

It mattered most on the first of them, whose own reading rule was to COUNT the
rows before reading the words: ten rows was a pass, and nine meant a constraint
drop had committed while its re-add had not, leaving a column with no foreign
key at all. Nothing in that state reads `SET NULL`, so only the count catches
it, and a commented query gives nobody any rows to count.

Nine agents touched those two files, including a correction round on each. The
two paste files immediately before them both shipped a live query, so this was
a regression rather than the house shape.

Two refusals:

    commented-only   every `select` in the file is behind `--`, so the reader
                     pastes it and gets silence
    no-query         the file hands the reader no `select` at all, commented or
                     otherwise, so nothing confirms the migration landed

And one that is a contract, not a fault in the file:

    unreadable       the path names nothing this process can read

`no-query` is separated from `commented-only` on purpose. They want different
repairs: one is a comment marker to delete, the other is a query somebody has
to write and run. Reporting both as one refusal sends a reader looking for a
`--` that was never there.

Usage:

    python3 check_paste_file.py <path>...

Exit 0 when every file hands the reader a runnable query, 1 on any refusal,
2 when a path could not be read.
"""

import re
import sys

# A statement the reader runs to see an answer. `select` is the only verb the
# repo's paste files have ever used for a confirmation, and widening this to
# every SQL verb would match the migration body itself, which is exactly what
# this check must not grade.
SELECT = re.compile(r"^\s*select\b", re.IGNORECASE)
COMMENTED_SELECT = re.compile(r"^\s*--+\s*select\b", re.IGNORECASE)

REMEDY = (
    "Delete the `--` in front of the confirmation query, paste the file into the QA\n"
    "SQL editor, and run the query there before this file reaches anyone. A query\n"
    "nobody has run is a claim, not a check."
)


def judge(text):
    """Grade one paste file. Returns (kind, detail) or None when it may ship."""
    live = []
    commented = []
    for number, line in enumerate(text.splitlines(), start=1):
        # Order matters: a commented select matches SELECT only after its `--`
        # is stripped, so test the commented form first and never both.
        if COMMENTED_SELECT.match(line):
            commented.append(number)
        elif SELECT.match(line):
            live.append(number)

    if live:
        return None
    if commented:
        lines = ", ".join(str(n) for n in commented)
        return "commented-only", (
            f"every `select` in this file is commented out (line(s) {lines}). "
            f"Pasted as written it returns no rows, no error and no output, which "
            f"reads exactly like a clean result."
        )
    return "no-query", (
        "this file carries no `select` at all. Nothing in it tells the reader "
        "whether the migration landed, and the reader cannot write that query "
        "for themselves at the SQL editor."
    )


def main(argv=None):
    paths = list(argv if argv is not None else sys.argv[1:])
    if not paths:
        print("usage: check_paste_file.py <path>...", file=sys.stderr)
        return 2

    refused = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as error:
            print(f"REFUSED unreadable: {path}: {error}", file=sys.stderr)
            return 2

        verdict = judge(text)
        if verdict is None:
            print(f"ok: {path} hands the reader a runnable query")
            continue

        kind, detail = verdict
        print(f"REFUSED {kind}: {path}: {detail}", file=sys.stderr)
        refused += 1

    if refused:
        print(f"\n{REMEDY}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
