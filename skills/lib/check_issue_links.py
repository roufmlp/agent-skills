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
carry `[[pending-actions]]`, `[[nnn]]` written as a placeholder, and regex
fragments such as `[[:space:]]` inside fenced code. None of them is a citation
and none of them is this script's business.

## The edges, and two more refusals

An issue also cites its neighbours by NOT citing them. `## Blocked by` is the
section a scheduler reads to decide what may be built today, and until
2026-09-13 nothing compared it against what the file says in prose. Measured
that day in one project: not one of the 22 needs-harden issues was named as a
blocker by any other issue, and issue 64, the tab bar, was needed by every
screen in prose only.

Promotion cannot close that, because it reads a register row and never the
code. The harden pass reads the code, so it is the one place the edge can be
written, and these two refusals are what make it write both directions. They
grade the files under `--issues` only: a hardening findings file carries
citations and is not an issue.

    unstamped edge   a file carrying `Hardened:` or `Hardened (provisional):`
                     and no `## Blocked by` section. The stamp says a pass read
                     the code behind this issue; the section is what it read the
                     code for. `- None` satisfies it — the section is required,
                     a blocker is not.

    prose edge       a sentence saying this issue needs, reads, calls, assumes,
                     builds on or comes after another OPEN issue, where
                     `## Blocked by` does not name that issue. The refusal
                     quotes the sentence, so the reader can see the dependency
                     rather than only the number. A `done` or `closed` issue
                     blocks nothing and is never one of these.

`--grade <file>` narrows the edge refusals to the files named, and repeats. The
links are still all read. A harden pass stamps the issues it hardened and cannot
repair a tracker's backlog to do it: 128 of a second tracker's 641 files carry
a stamp and no section, measured 2026-09-13, every one minted before the rule
existed, and a tracker-wide grade would block every stamp on that repository
forever. Same reason `run-issues/check_origin.py` is run on one file and never
over the directory. Without the flag every file under `--issues` is graded,
which is the sweep a human runs over a tracker.

Ruled 2026-09-13, issue 02 of the set that added them. The width of "the same
sentence" was ruled the same day, on the three counts `WINDOW` below carries.

## Roots

`--issues` is both the directory walked and the first place a citation resolves.
`--archive` adds a resolution root and is walked for nothing: a closed issue
still answers a live link, and issues 221 and 246 are exactly that shape today.
`--scan` adds files whose links are read -- the hardening findings and the seam
files hold citations too, and the 583 link that broke was copied there first.

Exit 0 is a clean walk and prints the count out loud, notes included. Exit 1 is
"a link was read and it names no issue", or "an issue does not carry the edges
it should". Exit 2 is "nothing could be read, so nothing is asserted", which is
what an empty walk gets, for the same reason a checker that parsed zero links
may not report a pass. A refusal is printed before that guard and beats it: an
edge refusal needs no link to be true, so a tracker whose files carry no
citation at all can still be wrong about its edges.

Usage:

    check_issue_links.py --issues .scratch/example-feature/issues \\
                         --archive .scratch/example-feature/archive \\
                         --scan .scratch/example-feature/harden
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# `[[536]]`, `[[312d]]`, `[[536-a]]`, `[[pending-actions]]`. Kept loose on
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

# `Hardened: 2026-09-13 — ...` and `Hardened (provisional): ...`. Either line is
# the harden pass saying it read the code behind this issue, which is the read
# the edges come out of.
STAMP = re.compile(r"^Hardened(?: \(provisional\))?:", re.M)

# `## Blocked by`, and `## Blocked by, and the order` with it: `next_batch.py`
# reads the same heading the same loose way, and two readers of one section that
# disagree about which heading opens it is the fault neither would report.
SECTION = re.compile(r"^## Blocked by\b.*$", re.M)


# `Status: done`, `Status: ready-for-agent — merged ...`. The first token after
# the colon, which is the read `next_batch.py` already does.
STATUS = re.compile(r"^Status:\s*(\S+)", re.M)
CLOSED = ("done", "closed")

# The title line, and everything from it down is prose. The header block above it
# carries `Status:`, `Origin: 149e/batch-170a59` and `Siblings: 44 — ...`, every
# one of which names another issue and depends on none of them.
TITLE = re.compile(r"^# ", re.M)

# A fenced block. A regex fragment or a shell line inside one is not a sentence.
FENCE = re.compile(r"^```.*?^```", re.M | re.S)

# `issue 64`, `issues 64 and 65`, and the `[[64]]` citation beside them. Both are
# how this tracker names a neighbour in prose.
NAMED = re.compile(r"\bissues?\s+(\d{1,4}[a-z]?)\b|\[\[(\d{1,4}[a-z]?)\]\]",
                   re.I)

# The six words the human ruled on, 2026-09-13. A dependency is a claim about
# another issue's code, and these are the verbs this tracker writes it with.
# `builds on` carries its preposition: "builds the tab bar" is what an issue says
# about ITSELF, and without the `on` every such sentence would refuse.
DEPENDS = re.compile(
    r"\b(needs|reads|calls|assumes|builds\s+on|after)\b", re.I)

# One sentence ends and the next begins. Kept crude on purpose: a split that is
# one sentence wide either way changes which words sit beside a number, and the
# refusal quotes what it read, so a reader sees the split it judged on.
SENTENCE = re.compile(r"(?<=[.!?])\s+")

# How close the verb must sit to the number it governs, and what may not stand
# between them. The rule as ruled was "in the same sentence", and the same
# sentence is too wide to ship: measured 2026-09-13 over the 112 files of one
# project, the sentence-wide read refused 93 times, and the first two refusals
# it printed were both wrong in the same way -- a verb whose subject was some
# other clause entirely ("Nothing under `src/` CALLS the composer yet -- no
# screen uploads a file until issues 08 and 09"). A checker wrong that often on
# its first day is a checker somebody switches off, which is the standing
# judgement this file's split-parent note was written on.
#
# Four words and no clause break between the verb and the number takes that
# project to 9 and a second tracker's 641 files to 9, and both lists read as
# real dependencies -- `02` needs the Supabase project `33` creates, `24` calls
# the booking gate of `21`. Eight words finds one more true edge on the first
# project and two wrong ones (a negation, "needs neither issue 22", and a verb
# governing another word, "after acceptance ... issue 21"); the whole sentence
# finds 16, of which the majority past word eight are wrong.
#
# Ruled 2026-09-13, at the keyboard, on those three counts. Widening it back is
# these two constants and the tests that pin them.
WINDOW = 4
CLAUSE_BREAK = re.compile(r"[,;:)—]")

REFUSE = "refuse"
NOTE = "note"

# What a finding is ABOUT, which is what the count line groups by. A file nobody
# could open is its own kind: it says nothing about the links in it and nothing
# about its edges, and counting it as either sends the reader to repair a file
# they cannot read.
LINK_KIND = "link"
EDGE_KIND = "edge"
UNREADABLE = "unreadable"


@dataclass
class Finding:
    path: str
    line: int
    link: str
    severity: str
    reason: str
    kind: str = LINK_KIND

    def __str__(self):
        # An edge finding carries no link, and `[[]]` in front of its message
        # would read as a citation of nothing -- which is the very fault the
        # link half of this script reports.
        cited = f" [[{self.link}]]" if self.link else ""
        return f"{self.path}:{self.line}:{cited} — {self.reason}"


@dataclass
class Walk:
    links_read: int = 0
    files_read: int = 0
    issues_read: int = 0
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


def issue_id(path):
    """`536` for `536-a-purchase-order-...md`, or None for a file that is not an
    issue. The same read `index()` does, named so the edge checks can use it."""
    match = FILENAME.match(os.path.basename(path))
    return match.group(1) + match.group(2) if match else None


def status_of(text):
    """The first token of the `Status:` line, lowercased, or "" where a file
    carries none."""
    found = STATUS.search(text)
    return found.group(1).lower() if found else ""


def open_issues(paths):
    """The ids under these paths whose `Status:` is neither `done` nor `closed`.

    A file with no `Status:` line at all is NOT open here. The tracker's own
    notes and READMEs sit in the issues directory beside the issues, and a
    dependency on something that is not an issue is not an edge anybody can
    write down.
    """
    found = set()
    for path in paths:
        this_id = issue_id(path)
        if not this_id:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                status = status_of(handle.read())
        except OSError:
            continue
        if status and status not in CLOSED:
            found.add(this_id)
    return found


def named_in_section(text):
    """Every issue id the `## Blocked by` section mentions, anywhere in it.

    Wider than the blocker `next_batch.py` counts, and deliberately so. This set
    answers "did the writer consider this edge", not "does this edge hold up the
    batch", and the whole section is where they answered. Two shapes forced the
    width, both measured on a second tracker 2026-09-13. 122 of that tracker's
    bullets open with a link rather than a number -- `- [[240]] — the reason`
    -- so a reader of bare numbers alone would refuse the files that answer
    properly. And issue 418's section names `[[421]]` to say the two do NOT
    block each other, while its body says this issue runs after it; a refusal
    there tells a writer who read the edge and wrote the reason to go and read
    it again. Silence is what the refusal is for.
    """
    section = SECTION.search(text)
    if not section:
        return set()
    rest = text[section.end():]
    end = re.search(r"^## ", rest, re.M)
    if end:
        rest = rest[: end.start()]
    found = {m.group(1) or m.group(2) for m in NAMED.finditer(rest)}
    for line in rest.splitlines():
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if not bullet:
            continue
        bare = re.match(r"^(?:\*\*)?`?(\d{1,4}[a-z]?)(?:[-`\s]|$)",
                        bullet.group(1))
        if bare:
            found.add(bare.group(1))
    return found


def prose(text):
    """The sentences of an issue file that could carry a dependency.

    Three things are cut out before the split, each because it names another
    issue while depending on nothing: the header block above the title, a fenced
    block, and the `## Blocked by` section itself -- which is the answer, not the
    question.
    """
    title = TITLE.search(text)
    body = text[title.start():] if title else text
    body = FENCE.sub(" ", body)
    section = SECTION.search(body)
    if section:
        rest = body[section.end():]
        end = re.search(r"^## ", rest, re.M)
        body = body[: section.start()] + (rest[end.start():] if end else "")
    return SENTENCE.split(" ".join(body.split()))


def governs(before):
    """True where the text in front of a number carries a dependency verb close
    enough to be about that number: inside the last `WINDOW` words, with no
    clause break after it. See the constants for what the two readings cost."""
    tail = " ".join(before.split()[-WINDOW:])
    verbs = list(DEPENDS.finditer(tail))
    if not verbs:
        return False
    return not CLAUSE_BREAK.search(tail[verbs[-1].end():])


def missing_edges(path, text, this_id, open_ids):
    """A refusal per sentence that depends on an open issue the section omits.

    Both directions of the edge are the harden pass's job, and this is the half a
    reader can check: the issue says in prose that it needs another issue's work,
    and its own `## Blocked by` does not say so. Measured in one project
    2026-09-13: issue 64, the tab bar, was needed by every screen in prose and
    named as a blocker by none of them.
    """
    declared = named_in_section(text)
    found = []
    for sentence in prose(text):
        if not DEPENDS.search(sentence):
            continue
        for match in NAMED.finditer(sentence):
            named = match.group(1) or match.group(2)
            if named == this_id or named in declared or named not in open_ids:
                continue
            if not governs(sentence[: match.start()]):
                continue
            declared.add(named)  # one refusal per missing edge, not per mention
            found.append(Finding(
                path, 1, "", REFUSE,
                f"issue {this_id} depends on open issue {named} in prose and "
                f"its `## Blocked by` does not name it: \"{sentence}\" Add "
                f"`- {named}` there, and add `- {this_id}` to issue {named} "
                f"where {named} depends on this one.",
                EDGE_KIND,
            ))
    return found


def edge_findings(path, text, this_id, open_ids=frozenset()):
    """Findings about the EDGES this issue file declares, not its links.

    Two refusals. A stamped issue with no `## Blocked by` section: the stamp says
    a harden pass read the code behind this issue, and the section is what it
    read the code for, so a stamp without one is a pass that skipped the step
    (`- None` satisfies it; the section is required, not a blocker). And a
    dependency this file states in prose while its own section omits it, which
    `missing_edges()` above reads.
    """
    found = missing_edges(path, text, this_id, open_ids)
    if STAMP.search(text) and not SECTION.search(text):
        found.append(Finding(
            path, 1, "", REFUSE,
            f"issue {this_id} is stamped and carries no `## Blocked by` "
            f"section. The stamp says a harden pass read the code behind this "
            f"issue; the section is what it read the code for. Write the "
            f"section, `- None` where nothing blocks it.",
            EDGE_KIND,
        ))
    return found


def walk(scan_roots, whole, halves, split_parent_refuses=False, issue_files=(),
         open_ids=frozenset()):
    """Read every file under scan_roots for links, and every file in
    `issue_files` for its edges as well. A hardening findings file carries
    citations and is not an issue, so only the tracker's own files are graded
    on the section they declare."""
    issue_files = {os.path.abspath(path) for path in issue_files}
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
                            f"cannot read the file: {error}", UNREADABLE))
                continue
            result.files_read += 1
            this_id = issue_id(path)
            if os.path.abspath(path) in issue_files and this_id:
                result.issues_read += 1
                result.refusals.extend(
                    edge_findings(path, text, this_id, open_ids))
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
    parser.add_argument("--grade", action="append", default=[],
                        help="an issue file whose EDGES are graded; repeatable. "
                             "Every link in the walk is still read. Without it "
                             "every file under --issues is graded, which is "
                             "right for a tracker sweep and wrong for a stamp: "
                             "a pass stamps the issues it hardened and cannot "
                             "repair a backlog minted before the rule")
    parser.add_argument("--split-parent-refuses", action="store_true",
                        help="promote the split-parent note to a refusal. Add "
                             "this on the day the human rules that a citation of "
                             "a split parent is wrong")
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

    tracker = markdown_files(args.issues)
    graded = tracker
    if args.grade:
        graded = [os.path.abspath(path) for path in args.grade]
        walked = {os.path.abspath(path) for path in tracker}
        stray = [path for path in graded if path not in walked]
        if stray:
            print(
                f"Refused: {', '.join(stray)} is not a file this walk reads, so "
                f"grading it would assert a pass over a file nobody opened. "
                f"Name a file under {args.issues}.",
                file=sys.stderr,
            )
            return 2

    result = walk([args.issues] + args.scan, whole, halves,
                  args.split_parent_refuses,
                  issue_files=graded, open_ids=open_issues(tracker))

    # The refusals are printed BEFORE the zero-links guard, and that order is
    # the rule: an edge refusal needs no link to be true, so a tracker whose
    # files carry no citation at all can still be wrong about its edges. The
    # guard below is about what a walk may call a PASS, never about what it may
    # report.
    for note in result.notes:
        print(f"note: {note}")

    if result.refusals:
        for refusal in result.refusals:
            print(refusal, file=sys.stderr)
        tally = Counter(r.kind for r in result.refusals)
        counts = []
        if tally[LINK_KIND]:
            counts.append(f"{tally[LINK_KIND]} of {result.links_read} link(s) "
                          f"name no issue")
        if tally[EDGE_KIND]:
            counts.append(f"{tally[EDGE_KIND]} of {result.issues_read} issue(s) "
                          f"do not carry the edges they should")
        if tally[UNREADABLE]:
            counts.append(f"{tally[UNREADABLE]} file(s) could not be read")
        print(
            f"\nRefused: {' and '.join(counts)}, across {result.files_read} "
            f"file(s).",
            file=sys.stderr,
        )
        return 1

    if not result.links_read:
        print(
            f"Refused: {result.files_read} file(s) read and not one `[[link]]` "
            f"among them. A walk that parsed zero links may not report a pass.",
            file=sys.stderr,
        )
        return 2

    # Say the counts out loud, notes included. A walk that read seven thousand
    # links and one that read none must not print the same sentence.
    tail = f", and {len(result.notes)} split-parent note(s)" if result.notes else ""
    print(
        f"{result.links_read} link(s) across {result.files_read} file(s): none "
        f"names a missing issue{tail}. {result.issues_read} issue(s) carry the "
        f"edges they declare."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
