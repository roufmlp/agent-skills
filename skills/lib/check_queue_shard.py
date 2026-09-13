#!/usr/bin/env python3
"""Refuse a queue shard that carries an item the daily brief cannot name.

`collect_shards.py` retires a queue item only when its id is written into one
of the two retirement shards — the daily brief's `answered.md`, or an attended
session's `ruled.md` for a question the human ruled at the keyboard — and it
reads an id off a `## ` heading by one rule: the last backticked token of the
form `q-...` on that line (`ITEM_ID`).
A heading with no such token is an item with no name. It renders every time
and can never be answered, so the same question reaches the human again after they
have ruled on it.

That fault has now been repaired by hand four times, from two different
skills: three groups from a hardening pass, 29 items across
them, and one group from an issue-drafting pass, where seven items the human ruled
in the daily-brief walk of 2026-09-12 stayed on the board in their BLOCKING
form. The `/to-issues` pass wrote `## to-issues-2026-09-12-61 [irreversible]
14-Q1: ...`, an id that is bare and does not start with `q-`, and nothing
refused it. `~/.claude/CLAUDE.md` sorts this into the first class: it can
refuse, so it is built, and no skill is asked to remember the shape.

The matching rule is NOT restated here. It is imported from `collect_shards`,
so the check and the collector can never disagree about what an id is.
Nothing in `collect_shards.py` changes: an item with no id always shows, which
is the safe direction for the board and the reason the refusal sits at the
writer, before the pass finishes.

Two refusals, and one refusal-to-pass:

    unnamed     a `## ` heading outside a fenced block carries no backticked
                `q-` id
    duplicate   two headings in one shard carry the same id, so one answer
                would retire both, or a typo has named a second item after
                the first
    empty       a file that holds no `## ` heading at all, or cannot be read.
                Nothing was asserted, so nothing passes. Exit 2, the code the
                rest of this directory uses for "nothing could be read".

Exit 0 is a clean walk. Exit 1 is "a shard was read and it is wrong". Every
refusal names the file and the line.

Usage:
    check_queue_shard.py <shard.md> [<shard.md> ...]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_shards import item_id, split_items  # noqa: E402

CLEAN = 0
WRONG = 1
EMPTY = 2


def headings(text):
    """(line number, heading line, id or empty) for every `## ` section.

    Uses the collector's own splitter, so a `## ` inside a fenced block is an
    example here exactly as it is there.
    """
    found = []
    offset = 0
    for part in split_items(text):
        head = part.split("\n", 1)[0]
        if head.startswith("## "):
            line = text.count("\n", 0, offset) + 1
            found.append((line, head, item_id(part)))
        offset += len(part)
    return found


def check_text(text, path="<shard>"):
    """Every refusal in one shard's text, as `path:line: reason` strings.

    An empty list from a file that holds headings is a pass. A file with no
    heading yields one line naming that, and the caller exits 2 on it.
    """
    seen = {}
    found = headings(text)
    if not found:
        return [f"{path}: no `## ` heading, so nothing was checked"]
    out = []
    for line, head, ident in found:
        if not ident:
            out.append(
                f"{path}:{line}: heading carries no backticked `q-` id; the "
                f"daily brief can never retire it. Append one, e.g. "
                f"`q-<pass-id>-<n>`, to the heading line: {head.strip()}")
        elif ident in seen:
            out.append(
                f"{path}:{line}: `{ident}` already names the heading on line "
                f"{seen[ident]}; one answer would retire both")
        else:
            seen[ident] = line
    return out


def check_file(path):
    """(exit code, refusal lines) for one shard on disk."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        return EMPTY, [f"{path}: cannot be read: {error}"]
    refusals = check_text(text, path)
    if not refusals:
        return CLEAN, []
    if not headings(text):
        return EMPTY, refusals
    return WRONG, refusals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("shards", nargs="+", help="queue shard files to check")
    args = parser.parse_args(argv)
    worst = CLEAN
    for path in args.shards:
        code, refusals = check_file(path)
        for line in refusals:
            print(f"REFUSED — {line}", file=sys.stderr)
        worst = max(worst, code)
    if worst == CLEAN:
        print(f"{len(args.shards)} shard(s) checked: every heading carries an id.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
