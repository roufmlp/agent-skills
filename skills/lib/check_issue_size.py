#!/usr/bin/env python3
"""Refuse an issue file carrying more acceptance criteria than one implementer takes.

## The class

Class 9 of `/harden-issues` asks an attacker whether an issue fits "one
implementer". Until 2026-09-14 the whole of the rule was a sentence -- "A clean
issue runs ~30-90 min" -- and no script computed anything. Each attacker listed
what the file held, found some past durations, and reasoned by analogy. One
attacker in the pass of 2026-09-14 wrote in its own findings file, unprompted:
"the estimate above is mine and is a judgement, not a measurement."

The three-class test in `~/.claude/CLAUDE.md` sorts that outcome into the
class that does not work. So the rule counts and refuses here instead.

## The fault that paid for this

The analogy step had nothing under it. The pass of 2026-09-14 reported
that issue `05b` "ran 150 minutes", `05f` "measured 45 minutes", `02e` was
"marked a WHALE" and issue `06` "ran 120 minutes", every one quoted from an
attacker's findings file as a MEASURED duration.

Not one of them was measured. `batch-be624c`'s ledger heads that column
**Estimate**; `batch-d67136`'s carries the runner's own launch sizes and says so
in its carry-forward -- "Sizes above are the runner's estimates from criteria
counts and file length, made at launch"; and `02e`'s WHALE stamp quotes the
ISSUE FILE's own `## Size` section, which is a previous attacker's judgement.
Every comparable the harden passes had ever used was another estimate. The
pipeline was calibrating estimates against estimates.

The real spans, read from the three run transcripts on 2026-09-14 (every
per-issue spawn attributed, retries and correction rounds included, and
cross-checked against the measured commit stamps):

    05b   estimated 150 min, took  68.6
    06    estimated 120 min, took  40.5
    05d   estimated 120 min, took  28.0
    02e   judged at or past the 90-minute bound, took 77.6
    05f   estimated  45 min, took  36.2

Median over all 25 issues that have run: **36.2 minutes**. p75 51, p90 72. One
issue of 25 crossed 90 minutes, and that was issue 01, the Next.js scaffold on
an empty repository, at 104.2 over three attempts. The "~30-90 min" bound was
not near the truth: it named as a ceiling a figure only 4% of issues ever
reached.

## Why the unit is the acceptance criterion

Every candidate predictor was tested against those 25 measured spans, reading
each issue file AS IT WAS at its run's fork point, so the file graded is the one
the implementer was handed:

    criteria         pearson +0.44   spearman +0.62     <- this one
    fixtures         pearson +0.32   spearman +0.34
    crit_words       pearson +0.33   spearman +0.31
    migration        pearson +0.31   spearman +0.25
    distinct files   pearson +0.28   spearman +0.21
    browser          pearson +0.22   spearman +0.13
    invariants       pearson +0.03   spearman +0.05
    blockers         pearson +0.00   spearman +0.03

Rank correlations use AVERAGED ranks for ties, which is what
`run_compare._spearman` computes, so the two readers of this quantity agree.
A column of equal counts must not invent an order.

Criteria count wins, and nothing else comes close. **A candidate that does not
predict is as useful a finding as one that does**, so the four that attackers
have reached for -- invariants, blockers, a migration, a browser -- are named
here as measured non-predictors. An attacker citing "this one ships a migration"
as a size signal is citing a correlation of +0.31 over a field that 19 of the 25
run issues carried; it barely discriminates. Invariants and blockers predict
nothing at all.

Dropping issue 01, the repo scaffold, which is a once-per-repository event:
criteria rises to pearson +0.62, spearman +0.67.

## What this check CANNOT see, said plainly

The strongest correlate of duration is not in the file. It is **attempts**:

    1 attempt    n=16   median 31.4 min
    2+ attempts  n= 9   median 52.5 min      pearson +0.90

A strike is an outcome, not a property of a file, so no counter can read it at
harden time. The fit on what a counter CAN read is weak and its own error bar
says so:

    span = 25.2 + 2.6 * criteria      R^2 0.19, residual sd 17.5 min

So this script counts. **It does not estimate minutes**, and a caller must not
convert its count into one. The analogy step is where the judgement hid, and a
predicted-minutes field would put it straight back.

It also would not have caught the only issue that ever broke 90 minutes: issue
01 carried six criteria. What it catches is the other tail -- the files at the
top of a tracker that are larger than anything that has ever successfully run.

## The limit is 14, and it is a ruling

The human ruled it on 2026-09-14, from the distribution above. The rule chosen:
**no issue may be bigger than the biggest one this pipeline has finished.**
That is issue 06, at 14 criteria and 40.5 minutes.

It refuses 3 of one tracker's 116 files -- `02b` at 23, `07` and `12` at 17 --
and it agrees with all four NO CUT rulings made by hand the same day. The
alternatives offered were 12, which would also have refused issue 06 itself, a
size the record shows is safe; and 17, which would have refused only `02b` and
left the passes judging size by hand, which is the state this change ends.

`--limit` is still a flag, because another tracker is another distribution.
Moving it on a tracker that has readings of its own is the human's.

## The refusals

    oversize      more criteria than `--limit`. Names the count, the limit, and
                  every criterion it counted, each by its line and its opening
                  words, so the reader cuts the file rather than re-reading it.

    ungraded      a file named to `--grade` carrying NO criteria. A count of
                  zero is not a pass: it means the pass that stamped this file
                  wrote no criteria, so class 9 was never judged on it. Outside
                  `--grade` this is a note, because 27 of that tracker's 116
                  files are un-hardened, and refusing them would refuse the
                  backlog.

## Two counting facts, because the tracker is not consistent

A criterion is written two ways in these trackers and both are counted: the
checkbox form `- [ ]` / `- [x]`, and the numbered form `1.` that one file in
the measured tracker used, which a checkbox-only reader counted at zero. A
TICKED box still counts -- issue 01 ran with four of its six already green and
still took the longest span in the record, so a ticked criterion is work the
file carries, not work removed.

A criterion's WIDTH is not refused, only reported. Issue `05b`'s first criterion
runs 45 lines and carries a whole nested argument; `05g` holds one criterion and
1,817 words of it. Width correlates at +0.33 and a second limit would double the
questions a pass has to ask, so the note states the widest criterion and refuses
nothing. The human rules a width limit on the day the data supports one.

## `--grade`, and why a tracker sweep is not a stamp

A tracker carries issues minted before this rule. `--grade <file>` narrows
refusal to the files named, and repeats; every file under `--issues` is still
read and counted. Without it every file is graded, which is the sweep a human
runs over a tracker and the wrong thing for a pass to do to a backlog. Copied
from `check_issue_links.py`, which solved exactly this on 2026-09-13.

Exit 0 is a clean walk and prints the counts out loud. Exit 1 is a refusal.
Exit 2 is "nothing could be read, so nothing is asserted".

Usage:

    check_issue_size.py --issues .scratch/example-feature/issues --limit 14
    check_issue_size.py --issues .scratch/example-feature/issues --limit 14 \\
                        --grade .scratch/example-feature/issues/08-a-request.md
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

# `## Acceptance criteria`, and `## Acceptance criteria, rewritten 2026-09-13`
# with it: the harden passes date the heading when they rewrite the section, and
# a reader that demanded the bare heading would count zero on exactly the files a
# pass had just worked hardest on.
SECTION = re.compile(r"^## Acceptance criteria\b.*$", re.M)

# Any `## ` heading, which is what closes the section above.
NEXT_HEADING = re.compile(r"^## ", re.M)

# The two forms this tracker writes a criterion in. `- [ ]` and `- [x]` are the
# common one; `1.` is the form one file in the measured tracker used, and a
# reader that knew only the checkbox counted that file at zero.
CRITERION = re.compile(r"^(?:- \[[ xX]\]|\d{1,2}\.\s)", re.M)

# A fenced block. A shell line or a numbered list inside one is not a criterion.
FENCE = re.compile(r"^```.*?^```", re.M | re.S)

OVERSIZE = "oversize"
UNGRADED = "ungraded"


@dataclass
class Criterion:
    line: int
    opening: str


@dataclass
class Finding:
    path: str
    kind: str
    reason: str

    def __str__(self):
        return f"{self.path}: {self.reason}"


@dataclass
class Walk:
    files_read: int = 0
    graded: int = 0
    criteria_read: int = 0
    refusals: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    passed: list = field(default_factory=list)
    uncounted: list = field(default_factory=list)


def markdown_files(root):
    """Every `.md` under root, sorted, so two runs report in one order."""
    if os.path.isfile(root):
        return [os.path.abspath(root)]
    out = []
    for base, _dirs, names in os.walk(root):
        for name in sorted(names):
            if name.endswith(".md"):
                out.append(os.path.abspath(os.path.join(base, name)))
    return sorted(out)


def blank_fences(text):
    """Replace every fenced block with blank lines of the same count.

    Blanking rather than deleting keeps every later line number equal to the
    line number in the file, which is the whole point of quoting one.
    """
    def blanks(match):
        return "\n" * match.group(0).count("\n")
    return FENCE.sub(blanks, text)


def criteria_section(text):
    """The acceptance-criteria section, and the line it starts on.

    Returns `(body, first_line)`, or `(None, 0)` when the file has no such
    section at all -- which is a different thing from a section holding nothing,
    and the caller tells them apart.
    """
    match = SECTION.search(text)
    if not match:
        return None, 0
    start = match.end()
    rest = text[start:]
    close = NEXT_HEADING.search(rest)
    body = rest[:close.start()] if close else rest
    first_line = text[:start].count("\n") + 1
    return body, first_line


def read_criteria(text):
    """Every criterion in the file, by line and opening words."""
    body, first_line = criteria_section(blank_fences(text))
    if body is None:
        return None
    found = []
    for match in CRITERION.finditer(body):
        line = first_line + body[:match.start()].count("\n")
        # The criterion's own first line, stripped of its marker and of the bold
        # the tracker opens most criteria with. Forty characters is enough to
        # recognise a criterion and short enough that a refusal listing fourteen
        # of them still fits a terminal.
        opening = body[match.end():].split("\n", 1)[0].strip()
        opening = opening.lstrip("*").strip()
        if len(opening) > 70:
            opening = opening[:67].rstrip() + "..."
        found.append(Criterion(line=line, opening=opening))
    return found


def width(text):
    """The widest criterion, in words, and the line it opens on.

    Reported, never refused -- see the module docstring.
    """
    body, first_line = criteria_section(blank_fences(text))
    if not body:
        return None
    marks = list(CRITERION.finditer(body))
    if not marks:
        return None
    widest = None
    for index, match in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(body)
        words = len(body[match.start():end].split())
        line = first_line + body[:match.start()].count("\n")
        if widest is None or words > widest[0]:
            widest = (words, line)
    return widest


def walk(paths, limit, graded_paths):
    result = Walk()
    graded_set = {os.path.abspath(p) for p in graded_paths} if graded_paths else None
    for path in paths:
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as error:
            result.refusals.append(Finding(path, UNGRADED,
                f"could not be read ({error}), so nothing about its size is "
                f"asserted"))
            continue
        result.files_read += 1
        found = read_criteria(text)
        is_graded = graded_set is None or os.path.abspath(path) in graded_set
        if is_graded:
            result.graded += 1

        if found is None or not found:
            what = ("carries no `## Acceptance criteria` section"
                    if found is None else
                    "carries a `## Acceptance criteria` section holding no "
                    "criterion")
            if is_graded and graded_set is not None:
                result.refusals.append(Finding(path, UNGRADED,
                    f"{what}. A count of zero is not a pass: class 9 was never "
                    f"judged on this file. Write the criteria, then grade it."))
            else:
                result.uncounted.append(path)
            continue

        result.criteria_read += len(found)
        if is_graded and len(found) > limit:
            listing = "\n".join(
                f"    {path}:{c.line}: {c.opening}" for c in found)
            result.refusals.append(Finding(path, OVERSIZE,
                f"{len(found)} acceptance criteria, and the limit is {limit}. "
                f"Cut this issue. The {len(found)} counted:\n{listing}"))
        elif is_graded:
            result.passed.append((path, len(found), width(text)))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issues", required=True,
                        help="the issue directory walked, or one issue file")
    parser.add_argument("--limit", type=int, default=14,
                        help="the most acceptance criteria one issue may carry. "
                             "14 is THE HUMAN'S RULING of 2026-09-14, "
                             "not a "
                             "default: it is the largest count that has ever "
                             "run (issue 06, which took 40.5 min), so the rule "
                             "is 'no issue bigger than the biggest one we have "
                             "finished'. It agrees with all four NO CUT "
                             "rulings made by hand the same day. Changing it "
                             "is the human's")
    parser.add_argument("--grade", action="append", default=[],
                        help="an issue file whose count is GRADED; repeatable. "
                             "Every file under --issues is still read and "
                             "counted. Without it every file is graded, which "
                             "is right for a tracker sweep and wrong for a "
                             "stamp: a pass cannot repair a backlog minted "
                             "before the rule")
    args = parser.parse_args(argv)

    if args.limit < 1:
        print(f"Refused: --limit {args.limit} is not a count of criteria. A "
              f"limit below one would refuse every issue ever written.",
              file=sys.stderr)
        return 2

    if not os.path.exists(args.issues):
        print(f"Refused: {args.issues} does not exist. Nothing was read, so "
              f"nothing here is asserted.", file=sys.stderr)
        return 2

    paths = markdown_files(args.issues)
    if not paths:
        print(f"Refused: no markdown file was found under {args.issues}. A "
              f"walk over nothing may not report a pass.", file=sys.stderr)
        return 2

    if args.grade:
        graded = [os.path.abspath(p) for p in args.grade]
        walked = set(paths)
        stray = [p for p in graded if p not in walked]
        if stray:
            print(f"Refused: {', '.join(stray)} is not a file this walk reads, "
                  f"so grading it would assert a pass over a file nobody "
                  f"opened. Name a file under {args.issues}.", file=sys.stderr)
            return 2
    else:
        graded = []

    result = walk(paths, args.limit, graded)

    # A pass is reported one file at a time when a caller NAMED its files, and
    # as a distribution when it did not. A tracker sweep that printed a line per
    # file printed 116 of them on one tracker, and a report nobody reads is the
    # same as no report.
    if graded:
        for path, count, widest in result.passed:
            tail = (f"; widest criterion {widest[0]} words at line {widest[1]}"
                    if widest else "")
            print(f"note: {path}: {count} criteria, within the limit of "
                  f"{args.limit}{tail}")
    elif result.passed:
        counts = sorted(c for _p, c, _w in result.passed)
        print(f"note: {len(counts)} graded file(s) under the limit: "
              f"median {counts[len(counts) // 2]} criteria, "
              f"most {counts[-1]}, fewest {counts[0]}")
    if result.uncounted:
        # Never itemised. Under --grade these are by definition files the caller
        # did NOT name, and a graded file holding no criterion is a refusal
        # above rather than a note here.
        print(f"note: {len(result.uncounted)} file(s) carry no criterion and "
              f"were counted, not graded — a tracker's un-hardened backlog")
    for note in result.notes:
        print(f"note: {note}")

    if result.refusals:
        for refusal in result.refusals:
            print(refusal, file=sys.stderr)
        oversize = sum(1 for r in result.refusals if r.kind == OVERSIZE)
        ungraded = sum(1 for r in result.refusals if r.kind == UNGRADED)
        counts = []
        if oversize:
            counts.append(f"{oversize} of {result.graded} graded issue(s) "
                          f"carry more than {args.limit} criteria")
        if ungraded:
            counts.append(f"{ungraded} graded issue(s) carry no criterion to "
                          f"count")
        print(f"Refused: {'; '.join(counts)}.", file=sys.stderr)
        return 1

    print(f"{result.criteria_read} criteria read across {result.files_read} "
          f"file(s); {result.graded} graded at a limit of {args.limit}; none "
          f"over.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
