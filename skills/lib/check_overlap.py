#!/usr/bin/env python3
"""Refuse a drafted issue that does not name each open issue whose paths it meets.

    python3 ~/.claude/skills/lib/check_overlap.py <draft file> --issues <issue directory>

Tracker-tooling issue 35 (issue 32, item 4). The UI audit of 25 September wrote 35
issues in one tracker without reading the 29 open ones, and a fold found 18 duplicate
pairs.
This reads the draft's `Touches:` line against every open issue in the tracker and lists
each one whose paths meet it. `/to-issues` runs it at the end of step 3, on drafts held
in the session's scratch directory, before step 3.5 writes them into the issue directory.

WHAT IT CAN CLAIM. Every open issue that shares a path with the draft is named before
the draft is written. It cannot claim the draft is not a duplicate: the fold of 25
September counted shared behaviour, and one of its pairs is one fault fixed in two
different files. That is the premise note of issue 35, and the narrower claim is the
honest one.

A MEET IS NAMED, and the draft passes, when the issue's number is

  - a bullet under `## Blocked by`, read by `next_batch.blockers_of`, the reader
    `run-issues/check_origin.py` imports rather than copies: two readers of one section
    that disagreed about what a bullet means would be a fault neither would report. A
    number inside a sentence (`- None; 12 is close`) is not a bullet naming it;
  - on a `Folds: 12` line above the title, the fold target (default `q-h0925-35-6`);
  - a file named in backticks under `## Parent` (default `q-h0925-35-3`).

WHAT IS OPEN. An issue whose `Status:` first word does not take it out of the pool, by
`check_issue_ready.leaves_pool`: `done`, `closed`, `wontfix`, `folded`, any
`folded-into-<n>`, `superseded`, `split` and `resolved` are closed (default
`q-h0925-35-2`, the set seam h0925 Q5 has issue 33's module export). Everything else is
open, `parked` and `blocked` included, and so is a file with no `Status:` line.

WHAT IT READS. `Touches:` through `headers()` in `run-issues/check_issue_ready.py`, issue
33's one reader, so a value continued onto the next lines is read to its end. Two paths
meet by `set_level.meet()`, issue 34's one definition, after `set_level.normalise()`:
`~` expanded, a relative path read against the main checkout's root, `*` never crossing
`/`. A meet through a directory ending `/` alone is printed on a line of its own and does
not change the exit code (default `q-h0925-35-1`).

WHAT IT REFUSES TO GUESS. An open issue with no `Touches:` line, or one holding no
backticked token and not `none`, is printed as unplaceable rather than skipped: one
tracker's 281 files carried no `Touches:` line on 2026-09-25, and a silent skip would
pass every draft there. An unplaceable line does not change the exit code (default
`q-h0925-35-4`). A draft with no `Touches:` line, `none`, or no backticked path is an
offence: a draft that states no path meets nothing and would pass every tracker (ruling
Q10 of 2026-09-25). The draft's own file is never read against itself, so a re-check of a
draft already written into the tracker does not meet its own line.

It writes nothing. Exit codes are `check_origin.py`'s: 0 clean, 1 one or more offences,
2 a file could not be read or the tracker is not inside a git repository. A third
meaning is never put on a code a caller reads.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "run-issues"))

# Issue 33's reader of `Touches:` and its closed set, issue 34's meet, and the
# scheduler's reader of `## Blocked by`. Imported, never copied.
from check_issue_ready import NO_LINE, NO_TOKEN, NONE, headers, leaves_pool  # noqa: E402
from next_batch import FILE_RE, blockers_of  # noqa: E402
from set_level import DIRECTORY, NotARepository, meet, normalise, roots  # noqa: E402

STATUS_LINE = re.compile(r"^Status:[ \t]*(.*)$", re.MULTILINE)
FOLDS_LINE = re.compile(r"^Folds:[ \t]*(.*)$", re.MULTILINE)
TITLE = re.compile(r"^#\s", re.MULTILINE)
PARENT = re.compile(r"^## Parent\s*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,2}\s", re.MULTILINE)
TOKEN = re.compile(r"`([^`\n]+)`")
# The fold targets open the line, split on commas: `Folds: 12` or `Folds: 12, `13``.
# Reading stops at the first item that is not a number, so a date or an item number
# in the prose after them names nothing.
FOLD_TARGET = re.compile(r"^\s*`?(\d+[a-z]?)`?\s*(?:,|$)", re.IGNORECASE)


class Unreadable(Exception):
    """A file this check needs could not be read: exit 2."""


@dataclass(frozen=True)
class Meet:
    issue: str
    file: str
    mine: str
    theirs: str
    how: str


def says_none(line: str | None) -> bool:
    return bool(line) and line.split()[0].rstrip(".,;").lower() == "none"


def header_of(text: str) -> str:
    title = TITLE.search(text)
    return text[:title.start()] if title else text


def named(text: str) -> set[str]:
    """Every issue number the draft names: blockers, fold targets and its parent."""
    found = {n.lower() for n in blockers_of(text.splitlines())}
    for line in FOLDS_LINE.finditer(header_of(text)):
        rest = line.group(1)
        while (target := FOLD_TARGET.match(rest)):
            found.add(target.group(1).lower())
            rest = rest[target.end():]
    parent = PARENT.search(text)
    if parent:
        body = text[parent.end():]
        end = NEXT_HEADING.search(body)
        for token in TOKEN.findall(body[:end.start()] if end else body):
            file = FILE_RE.match(os.path.basename(token.strip()))
            if file:
                found.add(file.group(1).lower())
    return found


def read(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable(f"{path}: {exc}") from exc


def check(draft: Path, issues_dir: Path) -> tuple[list[str], bool]:
    """The lines to print, and whether the draft is refused."""
    if not issues_dir.is_dir():
        raise Unreadable(f"{issues_dir} is not a directory")
    text = read(draft)
    tree_root, main_root = roots(issues_dir.resolve())
    mine = headers(text)
    if mine.touches_form in (NO_LINE, NO_TOKEN) or says_none(mine.touches_line):
        what = "no `Touches:` line" if mine.touches_form == NO_LINE \
            else f"`Touches: {mine.touches_line}`, which names no backticked path"
        return [f"REFUSED: the draft carries {what}. A draft that states no path meets "
                "nothing and would pass every tracker."], True

    names = named(text)
    drafted = [(a, normalise(a, main_root, tree_root)) for a in mine.touches]
    draft_path = draft.resolve()
    meets: list[Meet] = []
    unplaceable: list[str] = []
    for path in sorted(issues_dir.iterdir()):
        number = FILE_RE.match(path.name)
        if not number or not path.is_file() or path.resolve() == draft_path:
            continue
        theirs_text = read(path)
        status = STATUS_LINE.search(theirs_text)
        if status and leaves_pool(status.group(1).replace("*", "")):
            continue
        theirs = headers(theirs_text)
        if theirs.touches_form == NONE or says_none(theirs.touches_line):
            continue
        if theirs.touches_form in (NO_LINE, NO_TOKEN):
            unplaceable.append(
                f"UNPLACEABLE {number.group(1)} {path.name}: "
                + ("no `Touches:` line" if theirs.touches_form == NO_LINE
                   else f"`Touches: {theirs.touches_line}` holds no backticked path")
                + "; read it by hand")
            continue
        for b in theirs.touches:
            other = normalise(b, main_root, tree_root)
            for a, spelled in drafted:
                how = meet(spelled, other)
                if how:
                    meets.append(Meet(number.group(1), path.name, a, b, how))

    lines: list[str] = []
    refused = False
    by_file: dict[str, list[Meet]] = {}
    for found in meets:
        by_file.setdefault(found.file, []).append(found)
    for found in by_file.values():
        number = found[0].issue
        detail = "; ".join(f"`{m.mine}` meets `{m.theirs}` ({m.how})" for m in found)
        is_named = number.lower() in names
        if all(m.how == DIRECTORY for m in found):
            lines.append(f"DIRECTORY {number} {found[0].file}: {detail}")
        elif is_named:
            lines.append(f"named {number} {found[0].file}: {detail}")
        else:
            refused = True
            lines.append(f"UNNAMED {number} {found[0].file}: {detail}. Name it under "
                         "`## Blocked by`, or as a fold target on a `Folds:` line.")
    lines += unplaceable
    if not lines:
        lines.append("no open issue meets the draft's paths")
    return lines, refused


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("draft", type=Path, help="the drafted issue file")
    parser.add_argument("--issues", type=Path, required=True, help="the tracker's issue directory")
    args = parser.parse_args(argv)
    try:
        lines, refused = check(args.draft, args.issues)
    except Unreadable as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"UNREADABLE: {exc}; `git` is needed to find the checkout's root.", file=sys.stderr)
        return 2
    except NotARepository as exc:
        print(f"UNREADABLE: {exc} is not inside a git repository, so a relative path has "
              "no root to be read against.", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
