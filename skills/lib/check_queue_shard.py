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

Three refusals, and one refusal-to-pass:

    unnamed     a `## ` heading outside a fenced block carries no backticked
                `q-` id
    duplicate   two headings in one shard carry the same id, so one answer
                would retire both, or a typo has named a second item after
                the first
    ruled       the item asks a question the human has already ruled. The
                matching entry is printed, so the writer applies the ruling
                instead of asking for it a second time. See `rulings.py` for
                the file and the matching rule, and for the one line that
                passes an item past a match it has read and does not accept.
    record      the rulings file governing this shard holds an entry
                `rulings.py` could not parse. The shard is graded against the
                entries that DID parse, so a dropped entry is a question this
                guard can no longer refuse -- silently, which is how one
                `Carried by:` line with two backticked paths in it took a
                ruling off the record on 2026-09-17 with nothing said. An
                incomplete record is not a clean walk, whatever the shard's own
                headings say.
    empty       a file that holds no `## ` heading at all, or cannot be read.
                Nothing was asserted, so nothing passes. Exit 2, the code the
                rest of this directory uses for "nothing could be read".

The last two need `rulings.py` beside this script. WHERE THIS PACK SHIPS
WITHOUT IT THE RULINGS GUARD IS OFF and the two id refusals are unchanged; the
`--rulings` flag then refuses rather than pretending to check. The guard is
silent in the same way where the reader is present and the project has no
rulings file: a project that has never recorded a ruling is checked exactly as
it was before this existed.

Exit 0 is a clean walk. Exit 1 is "a shard was read and it is wrong". Every
refusal names the file and the line.

Usage:
    check_queue_shard.py <shard.md> [<shard.md> ...]
    check_queue_shard.py <shard.md> --rulings <rulings.md>
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_shards import ITEM_ID, item_id, split_items  # noqa: E402

try:
    from rulings import (QUESTION_REF, declared, entries_and_skips,  # noqa: E402
                         entries_for, issue_of, matches, nearest, quoted_ids)
    RULINGS_READER = True
except ImportError:  # pragma: no cover - a pack shipped without the reader
    # `rulings.py` is an optional part of this pack, so the import is the
    # conditional rather than a note telling a reader to remember. Without it
    # there are no entries, `ruled_refusal` returns nothing on every item, and
    # the id refusals above stand exactly as they did.
    RULINGS_READER = False
    QUESTION_REF = re.compile(r"(?!)")  # never matches

    def entries_for(_path):
        return [], []

# `[reversible]`, `[irreversible]`: the routing marker, not part of the subject.
# `QUESTION_REF` -- the `05-Q2` that names the issue and question -- is imported
# rather than restated, for the reason `ITEM_ID` is: two copies of a matching
# rule drift, and then the guard and the recorder disagree about the same item.
MARKER = re.compile(r"\[[^\]]*\]")

CLEAN = 0
WRONG = 1
EMPTY = 2


def headings(text):
    """(line number, heading line, id or empty, whole item) for every `## ` section.

    Uses the collector's own splitter, so a `## ` inside a fenced block is an
    example here exactly as it is there. The whole item comes back because the
    rulings guard reads the body: the line that passes a match is written
    there, not on the heading.
    """
    found = []
    offset = 0
    for part in split_items(text):
        head = part.split("\n", 1)[0]
        if head.startswith("## "):
            line = text.count("\n", 0, offset) + 1
            found.append((line, head, item_id(part), part))
        offset += len(part)
    return found


def subject_of(head):
    """What a heading actually asks, with its ids and markers taken off.

    The ids are backticked tokens, the routing marker is bracketed, and the
    question reference is the `05-Q2` that names the issue. None of the three
    is subject matter, and every one of them would share words with an entry
    that carries the same shape.
    """
    text = head[len("## "):]
    text = ITEM_ID.sub(" ", text)
    text = MARKER.sub(" ", text)
    text = QUESTION_REF.sub(" ", text)
    return text.strip(" :-")


def issue_ref(head):
    """The issue number a heading names, or empty where it names none."""
    found = QUESTION_REF.search(head)
    return issue_of(found.group(1)) if found else ""


def ruled_refusal(line, head, item, entries, path):
    """The rulings refusal for one item, or empty where it has none.

    Three ways past a match, and all three are the same line. An item that
    quotes every matching entry has read them: it may say they do not answer
    it, or that it contradicts one, and either way it is a new question. An
    item that quotes none has not read them. An item that quotes some but not
    the one that matches has read around the answer.

    Ruled by the human on 2026-09-13, issue 04, question `ti04-2`. The issue
    asks only for "the two nearest entries quoted", which passes an item that
    quotes two unrelated ones. The stricter reading was taken on the cause: a
    line that passes anything is a formality, not a refusal. It costs a
    careless writer one more round trip.
    """
    if not RULINGS_READER or not entries:
        return ""
    subject = subject_of(head)
    hits = matches(subject, entries, issue=issue_ref(head))
    if not hits:
        return ""
    if not declared(item):
        first = hits[0]
        return (f"{path}:{line}: already ruled. `{first.question}` of "
                f"{first.date} — {first.subject} — ruled: {first.ruling} "
                f"Carried by {first.home}. Apply it, or write "
                f"`Rulings checked: none match` on the item quoting that entry "
                f"and its nearest neighbour, and say what this asks that it "
                f"does not: {head.strip()}")
    quoted = quoted_ids(item, entries)
    if not quoted:
        return (f"{path}:{line}: `Rulings checked:` quotes no entry of the "
                f"rulings file, so nothing was read. Quote the two nearest, "
                f"starting with "
                f"{', '.join('`' + entry.question + '`' for entry in nearest(subject, entries))}"
                f": {head.strip()}")
    missed = [entry for entry in hits if entry.question not in quoted]
    if missed:
        names = ", ".join(f"`{entry.question}`" for entry in missed)
        return (f"{path}:{line}: `Rulings checked:` does not quote {names}, "
                f"which rules this subject. Read it and quote it, or apply "
                f"it: {head.strip()}")
    return ""


def check_text(text, path="<shard>", entries=()):
    """Every refusal in one shard's text, as `path:line: reason` strings.

    An empty list from a file that holds headings is a pass. A file with no
    heading yields one line naming that, and the caller exits 2 on it.

    `entries` are the project's rulings, from `rulings.parse`. Empty is the
    state of a project that has never recorded one, and it is a clean walk:
    this guard never invents a refusal out of an absent file.
    """
    seen = {}
    found = headings(text)
    if not found:
        return [f"{path}: no `## ` heading, so nothing was checked"]
    out = []
    for line, head, ident, item in found:
        if not ident:
            out.append(
                f"{path}:{line}: heading carries no backticked `q-` id; the "
                f"daily brief can never retire it. Append one, e.g. "
                f"`q-<pass-id>-<n>`, to the heading line: {head.strip()}")
            continue
        if ident in seen:
            out.append(
                f"{path}:{line}: `{ident}` already names the heading on line "
                f"{seen[ident]}; one answer would retire both")
            continue
        seen[ident] = line
        refusal = ruled_refusal(line, head, item, entries, path)
        if refusal:
            out.append(refusal)
    return out


def check_file(path, entries=None):
    """(exit code, refusal lines) for one shard on disk.

    `entries` of None means "find the rulings file for this shard yourself",
    which is what the command line does. An explicit list, empty included,
    is used as given, and its caller owns the same duty: an entry the reader
    could not parse is named before the shard is graded against what is left.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        return EMPTY, [f"{path}: cannot be read: {error}"]
    skips = []
    if entries is None:
        entries, skips = entries_for(path)
    refusals = skips + check_text(text, path, entries)
    if not refusals:
        return CLEAN, []
    if not headings(text):
        return EMPTY, refusals
    return WRONG, refusals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("shards", nargs="+", help="queue shard files to check")
    parser.add_argument("--rulings", default=None,
                        help="the project's rulings file; found beside the "
                             "shard's own `.scratch` when not given")
    args = parser.parse_args(argv)
    entries = None
    worst = CLEAN
    if args.rulings:
        if not RULINGS_READER:
            print("REFUSED — --rulings needs `rulings.py` beside this script, "
                  "which this pack does not ship. Drop the flag: the id "
                  "refusals still run.", file=sys.stderr)
            return WRONG
        with open(args.rulings, encoding="utf-8") as handle:
            entries, skips = entries_and_skips(handle.read())
        # The named-file road reads the record itself, so it carries the same
        # refusal as the derived one. The shards are still checked and printed
        # afterwards: the operator gets the whole picture, and the exit code
        # already says nothing here passed.
        for skip in skips:
            print(f"REFUSED — {args.rulings}:{skip}", file=sys.stderr)
            worst = WRONG
    for path in args.shards:
        code, refusals = check_file(path, entries)
        for line in refusals:
            print(f"REFUSED — {line}", file=sys.stderr)
        worst = max(worst, code)
    if worst == CLEAN:
        print(f"{len(args.shards)} shard(s) checked: every heading carries an "
              f"id, and no item asks a question already ruled.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
