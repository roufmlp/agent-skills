#!/usr/bin/env python3
"""Refuse a `[[link]]` in an issue file that names no issue.

## The class

An issue file cites its neighbours with `[[nnn]]`. Nothing compared those
citations against the files that exist, so a link to a number nobody minted read
exactly like a link that works: silent.

The fault that paid for this, on 2026-09-09. Issue 536's file is
`536-a-purchase-order-preview-failure-blanks-the-whole-deal-page.md`. The `-a-`
is the article "a" from its title sentence, and 252 of this tracker's issue
files begin `<number>-a-`, `<number>-an-` or `<number>-the-` for the same
reason. A `/harden-issues` pass took the identifier off the file name, split at
the first hyphen, and wrote `536-a` into 96 places across 14 files. One of them
was a `[[536-a]]` link in issue 583, and that link carried the edge saying 583
must be built before 536. The edge pointed at nothing for a week.

The collision is one character wide. A split issue takes a letter suffix with no
hyphen -- `11a`, `13b`, `262a`, `312d`, 82 files of them -- so `536a` is an
identifier and `536-a` is a file name read wrong.

## Why prose did not close it

`docs/agents/issue-tracker.md` already states the suffix rule, and the pass that
made this mistake could have read it. The human's three-class test in
`~/.claude/CLAUDE.md` sorts that outcome into the class that does not work: an
agent was asked to remember, and did not. So the rule refuses here instead.

## The two refusals

    hyphenated    `[[536-a]]`. A hyphen after the number begins the slug, so a
                  token of this shape is never an identifier. Names the two
                  things it could have meant, `536` and `536a`.

    unknown       `[[742]]`, where no file of any shape answers. Either the
                  number was never minted or the file moved out of every root
                  this walk was given.

## And one note, which refuses nothing

    split parent  `[[308]]`, where the parent has no file and `308a` and `308b`
                  do. A reader cannot tell which half carries the edge, so the
                  note names the halves it found.

This is a note and not a refusal because the first real walk found 92 of them
and nothing else, across issues 304, 308, 321, 323, 333, 334, 589 and 590,
measured 2026-09-11. A citation of the parent number is how this tracker has
always written a back-reference to a split, so refusing it would refuse the
convention rather than a fault, and a checker that is wrong 92 times on its
first day gets switched off. The human's three-class test calls this the second
class: a fact nobody wrote down, so it is stated. `--split-parent-refuses`
promotes it to a refusal, and belongs in the invocation on the day he rules that
a parent citation is wrong.

A link whose text is not identifier-shaped is ignored, not refused. Issue files
carry `[[pending-on-abdul]]`, `[[nnn]]` written as a placeholder, and regex
fragments such as `[[:space:]]` inside fenced code. None of them is a citation
and none of them is this script's business.

## Roots

`--issues` is both the directory walked and the first place a citation resolves.
`--archive` adds a resolution root and is walked for nothing: a closed issue
still answers a live link, and issues 221 and 246 are exactly that shape today.
`--scan` adds files whose links are read -- the hardening findings and the seam
files hold citations too, and the 583 link that broke was copied there first.

Exit 0 is a clean walk and prints the count out loud, notes included. Exit 1 is
"a link was read and it names no issue". Exit 2 is "nothing could be read, so
nothing is asserted", which is what an empty walk gets, for the same reason a
checker that parsed zero links may not report a pass.

Usage:

    check_issue_links.py --issues .scratch/example-feature/issues \\
                         --archive .scratch/example-feature/archive \\
                         --scan .scratch/example-feature/harden
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

# `[[536]]`, `[[312d]]`, `[[536-a]]`, `[[pending-on-abdul]]`. Kept loose on
# purpose: what a link MEANS is decided by classify(), not by the scanner, so a
# shape nobody anticipated is read and then ignored rather than skipped unseen.
LINK = re.compile(r"\[\[([^\[\]\n]{1,60})\]\]")

# `536`, `312d`. One optional lowercase letter, which is the whole of the split
# convention.
IDENTIFIER = re.compile(r"^(\d{1,4})([a-z]?)$")

# `536-a`. The shape this script exists for.
HYPHENATED = re.compile(r"^(\d{1,4})-([a-z]{1,2})$")

# `536-a-purchase-order-...md` -> `536`, ``; `312d-the-...md` -> `312`, `d`.
FILENAME = re.compile(r"^(\d{1,4})([a-z]?)-")


REFUSE = "refuse"
NOTE = "note"


@dataclass
class Finding:
    path: str
    line: int
    link: str
    severity: str
    reason: str

    def __str__(self):
        return f"{self.path}:{self.line}: [[{self.link}]] — {self.reason}"


@dataclass
class Walk:
    links_read: int = 0
    files_read: int = 0
    refusals: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def markdown_files(root):
    """Every `.md` file under root, sorted, so two runs report in one order."""
    if os.path.isfile(root):
        return [root] if root.endswith(".md") else []
    found = []
    for base, _dirs, names in os.walk(root):
        found.extend(os.path.join(base, n) for n in sorted(names) if n.endswith(".md"))
    return sorted(found)


def index(roots):
    """Map every issue file under roots to what a citation of it would say.

    Returns (whole, halves). `whole` maps a full identifier -- `536`, `312d` --
    to the file that answers it. `halves` maps a bare number to the lettered
    files carrying it, which is what lets the split-parent refusal name them.
    """
    whole = {}
    halves = defaultdict(list)
    for root in roots:
        for path in markdown_files(root):
            match = FILENAME.match(os.path.basename(path))
            if not match:
                continue
            number, letter = match.group(1), match.group(2)
            whole.setdefault(number + letter, path)
            if letter:
                halves[number].append(number + letter)
    return whole, {n: sorted(set(v)) for n, v in halves.items()}


def links(text):
    """Yield (link text, 1-indexed line) for every `[[...]]` in the text."""
    for match in LINK.finditer(text):
        yield match.group(1), text.count("\n", 0, match.start()) + 1


def classify(link, whole, halves):
    """(severity, reason) for this link, or None when it is not our business."""
    hyphenated = HYPHENATED.match(link)
    if hyphenated:
        number, letter = hyphenated.group(1), hyphenated.group(2)
        return REFUSE, (
            f"a hyphen after the number begins the slug, so `{link}` is never an "
            f"issue id. A split issue carries its letter with no hyphen. Write "
            f"`{number}` for the issue, or `{number}{letter}` for a split half."
        )

    identifier = IDENTIFIER.match(link)
    if not identifier:
        return None

    if link in whole:
        return None

    number = identifier.group(1)
    if not identifier.group(2) and number in halves:
        found = ", ".join(f"`{h}`" for h in halves[number])
        return NOTE, (
            f"issue {number} split and its own file is gone. The halves are "
            f"{found}. Name the half that carries this edge."
        )

    return REFUSE, (
        "no issue file of that number answers, in any root this walk was given. "
        "Either the number was never minted, or the file sits outside --issues "
        "and --archive."
    )


def walk(scan_roots, whole, halves, split_parent_refuses=False):
    result = Walk()
    seen = set()
    for root in scan_roots:
        for path in markdown_files(root):
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError as error:
                result.refusals.append(
                    Finding(path, 0, "", REFUSE,
                            f"cannot read the file: {error}"))
                continue
            result.files_read += 1
            for link, line in links(text):
                result.links_read += 1
                verdict = classify(link, whole, halves)
                if not verdict:
                    continue
                severity, reason = verdict
                if severity == NOTE and split_parent_refuses:
                    severity = REFUSE
                finding = Finding(path, line, link, severity, reason)
                if severity == REFUSE:
                    result.refusals.append(finding)
                else:
                    result.notes.append(finding)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issues", required=True,
                        help="the issue directory: walked, and resolved against")
    parser.add_argument("--archive", action="append", default=[],
                        help="another resolution root; not walked. Repeatable")
    parser.add_argument("--scan", action="append", default=[],
                        help="another file or directory to read links from. "
                             "Repeatable")
    parser.add_argument("--split-parent-refuses", action="store_true",
                        help="promote the split-parent note to a refusal. Add "
                             "this on the day the human rules that a citation of a "
                             "split parent is wrong")
    args = parser.parse_args(argv)

    roots = [args.issues] + args.archive
    missing = [r for r in roots + args.scan if not os.path.exists(r)]
    if missing:
        print(
            f"Refused: {', '.join(missing)} does not exist. A root that is not "
            f"there resolves nothing, so nothing here is asserted.",
            file=sys.stderr,
        )
        return 2

    whole, halves = index(roots)
    if not whole:
        print(
            f"Refused: no issue file was found under {', '.join(roots)}. Every "
            f"link would refuse, which says nothing about the links.",
            file=sys.stderr,
        )
        return 2

    result = walk([args.issues] + args.scan, whole, halves,
                  args.split_parent_refuses)

    if not result.links_read:
        print(
            f"Refused: {result.files_read} file(s) read and not one `[[link]]` "
            f"among them. A walk that parsed zero links may not report a pass.",
            file=sys.stderr,
        )
        return 2

    for note in result.notes:
        print(f"note: {note}")

    if result.refusals:
        for refusal in result.refusals:
            print(refusal, file=sys.stderr)
        print(
            f"\nRefused: {len(result.refusals)} of {result.links_read} link(s) "
            f"name no issue, across {result.files_read} file(s).",
            file=sys.stderr,
        )
        return 1

    # Say the counts out loud, notes included. A walk that read seven thousand
    # links and one that read none must not print the same sentence.
    tail = f", and {len(result.notes)} split-parent note(s)" if result.notes else ""
    print(
        f"{result.links_read} link(s) across {result.files_read} file(s): none "
        f"names a missing issue{tail}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
