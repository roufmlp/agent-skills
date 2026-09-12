#!/usr/bin/env python3
"""Name every added comment that claims something about code outside its file.

    python3 report_claim_commands.py --repo . --range <base>..<head> \
        --out <run dir>/claim-commands.md --batch <batch-id>

**IT REFUSES NOTHING AND EXITS 0 WHATEVER IT FINDS.** That is the ruling, not a
stage this grows out of. Do not turn it into a gate without a second
measurement; the first one says a refusal here deletes true sentences.

## Why report-only, in the human's own ruling of 2026-09-12

Run `batch-200d42`'s finale asked for a standing rule: grep the branch diff for
absolute quantifiers in added comments and REFUSE the close on a hit. The finale
named the one fact that would flip its own recommendation, and a measurement
written to the project's own audit directory took it.

Fifty quantified comment and test-name lines were sampled from six merged run
diffs and graded twice: does the line claim anything outside its own file, and
if so is the claim true of the tree at that commit.

    28 of 50   claim nothing outside their own file at all
    16 of 22   of the rest are TRUE
     4 of 22   are false
     2 of 22   cannot be settled by reading the tree

So a refusal on the quantifier alone would have deleted twenty-eight sentences
that were never claims and sixteen that were true and useful. The human rejected the
blanket refusal on those numbers and ruled this report instead.

The false rate is nevertheless real and nobody has been catching it: eighteen per
cent of out-of-file claims false, over 373 quantified lines in five runs, puts
three to eleven false sentences per run in main today, because nothing reads a
source comment for truth.

## The precision figure is 71%, MEASURED, not assumed

The record cross-tabulated a narrow trigger vocabulary against that graded
sample. It catches 12 of the 22 out-of-file claims, wrongly catches 5 lines that
claim nothing outside their file, and misses 10. That is 12/17 precise and 12/22
recall -- 71% and 55% -- and it catches two of the four false claims. Every one
of those figures belongs to the record's vocabulary, and the sample behind them
is fifty lines. Read them as the order of magnitude they are.

**The record does not write its narrow vocabulary down, and `TREE_WIDE` below is
a RECONSTRUCTION of it.** The wide vocabulary is on disk beside that
measurement, and this file's collector reproduces
its per-run totals byte for byte -- 97, 143, 46, 49, 38 and 25 -- so the line
collection is the record's. The narrow half is not: the record reports 10 to 29
hits per run and the tree-wide terms it names give 10, 11, 14, 16, 27 and 50 over
the same six ranges. Nothing reconciles the 50. **So the 71% is inherited, and it
has NOT been re-measured against this exact regex.** Anyone proposing to make
this a refusal owes that measurement first.

## What the report is for

One number: how many lines it fires on in one real run. The human stated the fact
that flips it when they ruled -- **above about thirty lines in a real run, the
trigger is too wide to build a refusal on and the question should be dropped.**
`FLIP` holds that thirty. The report prints the count against it and says which
way it reads, and the verdict is the human's to take, not this script's.

## The reading, taken 2026-09-12 over the six merged runs

Run report-only against the same six ranges the record graded, before it was
wired into any finale. Issues, then lines fired, then the denominator:

    batch-44d0a8   17 issues    27 of 5362
    batch-b5e96d   15 issues    50 of 7126
    batch-170a59    6 issues    11 of 2948
    batch-207704   15 issues    14 of 3367
    batch-e649bb    7 issues    16 of 2990
    batch-200d42    8 issues    10 of 1717

**Five of six sit at or below `FLIP`; `batch-b5e96d` fires 50 and does not.** So
the flipping fact reads BOTH ways depending on the run, and a single run's number
cannot settle it. Anyone bringing this to the human owes them that sentence, not the
flattering run. The 50 is not one runaway file either: its worst file carries 6
of them and the fifty are spread over 35 files.

**A count scales with the diff, not with the fault.** The rate is steady at 0.37
to 0.70 per cent of added prose lines across all six, which is the same flatness
the record found in the wide vocabulary. A per-run count therefore measures how
much was written, and `FLIP` is a budget for how many lines a human will read.

## What it reads, and what it deliberately does not

ADDED lines only, under `src/`, `scripts/` and `tests/`, that are a comment or a
test name. A deleted line is not a claim anybody can act on, and a line the diff
merely moves past is already in main and was never this run's to answer for.

It does not read whether the claim is TRUE. That is the whole point of the shape
the four false claims share: each names something one command settles -- a second
file that reads route wiring, a write that does not upsert, a second raiser of a
kind, an export that is neither handler nor config. The rule that pays is "a
claim about code outside this file carries the command that settles it", and
this report is the first half of it: find the lines, count them, and let the
count decide whether the second half is worth building.

It would have MISSED the one claim `batch-200d42` cared about. That escape was a
false citation of a named neighbour and carries no quantifier at all. A
vocabulary is not a truth check and this docstring will not pretend otherwise.

Drill: `test_report_claim_commands.py` beside this file.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

# The three roots the measurement collected over, and no fourth. A comment in a
# markdown file is prose for a reader, not a claim a later agent builds on.
ROOTS = ("src/", "scripts/", "tests/")

# The tree-wide half of the vocabulary. `the only`, `every caller` and the rest
# of the wide list are deliberately OUT: `the only` alone fires 5 to 47 times a
# run over the six graded ranges and most of those describe the file they sit
# in, which is the twenty-eight the record refused to refuse on.
TREE_WIDE = (
    ("nothing else", r"\bnothing else\b"),
    ("nobody else", r"\b(?:nobody|no one) else\b"),
    ("anywhere else", r"\banywhere else\b"),
    ("elsewhere in the tree",
     r"\belsewhere in (?:this|the) (?:tree|repo|repository|codebase|app|suite)\b"),
    ("in this tree", r"\bin this tree\b"),
    ("across the tree", r"\bacross the tree\b"),
    ("no other", r"\bno other\b"),
)
TRIGGERS = tuple((name, re.compile(pattern, re.I)) for name, pattern in TREE_WIDE)

# `//`, `/*`, a jsdoc continuation `*`, and `#` for the shell and python under
# `scripts/`. Same two expressions the measurement used, so the denominator
# this report prints is the one the record printed.
COMMENT = re.compile(r"^\s*(//|\*|/\*|#)")
TESTNAME = re.compile(r"^\s*(it|test|describe)\s*\(\s*['\"`]")

# `@@ -10,0 +11,3 @@` -- the new file's first line of this hunk.
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

# the human's flipping fact, stated when they ruled on 2026-09-12: above about thirty
# lines in a real run the trigger is too wide to build a refusal on, and the
# question is dropped rather than narrowed again.
FLIP = 30

REPORT = "claim-commands.md"


@dataclass(frozen=True)
class Hit:
    """One added prose line, and which phrases fired on it."""

    path: str
    line: int
    kind: str
    text: str
    triggers: list


def fires(text) -> list:
    """Which trigger phrases this line carries, in vocabulary order."""
    return [name for name, pattern in TRIGGERS if pattern.search(text)]


def added_prose(diff) -> list:
    """Every added comment or test-name line in a unified diff.

    The line number is the NEW file's, counted from each hunk header rather
    than from a running total: a report that names a line the author never
    wrote sends its reader to the wrong sentence, which is the same fault class
    this report exists to find.
    """
    found = []
    path, line = None, 0
    for raw in diff.split("\n"):
        if raw.startswith("+++ b/"):
            path, line = raw[6:], 0
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        header = HUNK.match(raw)
        if header:
            line = int(header.group(1))
            continue
        if raw.startswith("\\"):          # `\ No newline at end of file`
            continue
        if raw.startswith("-"):
            continue
        if raw.startswith("+"):
            text = raw[1:]
            if path and (COMMENT.match(text) or TESTNAME.match(text)):
                kind = "test-name" if TESTNAME.match(text) else "comment"
                stripped = text.strip()
                found.append(Hit(path, line, kind, stripped, fires(stripped)))
            line += 1
            continue
        if raw.startswith(" "):           # context, only above `--unified=0`
            line += 1
    return found


def collect(repo, rng):
    """`(prose lines, error)`. Never raises, never runs a shell.

    The command is an argument LIST. `shell=True` here would make a character
    in a branch name run something else and would buy nothing.
    """
    try:
        done = subprocess.run(
            ["git", "diff", "--unified=0", rng, "--", *ROOTS],
            cwd=str(repo), capture_output=True, text=True, errors="replace",
        )
    except (OSError, ValueError) as error:
        return [], str(error)
    if done.returncode:
        return [], (done.stderr or "git exited "
                    f"{done.returncode} and said nothing").strip()
    return added_prose(done.stdout), ""


def report_beside(ledger_path) -> str:
    """The report for the run whose ledger this is.

    Ticket 38 ruling 10 puts run state in `.scratch/<feature>/runs/<batch-id>/`,
    and `run_step.steps_beside` resolves the steps file by the same rule. This
    is a sibling of both, so the layout has one shape wherever it is read.
    """
    return os.path.join(os.path.dirname(ledger_path), REPORT)


def render(hits, scanned, rng, batch) -> str:
    """The report, as text. Pure: it reads nothing and writes nothing."""
    fired = [one for one in hits if one.triggers]
    count = len(fired)

    if count <= FLIP:
        verdict = (
            f"**{count} is at or below {FLIP}**, so on the human's flipping fact of "
            "2026-09-12 the trigger is narrow enough that a command requirement "
            "built on it is worth costing. That is a reading, not a decision: "
            "the next step is the human's."
        )
    else:
        verdict = (
            f"**{count} is above {FLIP}**, which is the fact the human named when he "
            "ruled on 2026-09-12: the trigger is too wide to build a refusal on, "
            "and the question should be dropped rather than narrowed again. That "
            "is a reading, not a decision: the call is the human's."
        )

    rate = f"{100.0 * count / scanned:.1f}%" if scanned else "no denominator"
    lines = [
        f"# Out-of-file claims, {batch or rng}",
        "",
        "**REPORT ONLY. This check REFUSES NOTHING and exits 0 whatever it "
        "finds.** The human ruled it report-only on 2026-09-12, against a "
        "measurement saying a refusal would delete true and useful sentences.",
        "",
        f"- Range: `{rng}`",
        f"- Scanned: {scanned} added comment and test-name lines under "
        f"{', '.join('`' + root + '`' for root in ROOTS)}",
        f"- Fired: {count} ({rate})",
        "",
        verdict,
        "",
        "The vocabulary is 71% precise and 55% recall, MEASURED against a "
        "fifty-line graded sample on 2026-09-12, not assumed. A line below is "
        "a line worth a second look, never a line known to be wrong: 16 of the "
        "22 out-of-file claims in that sample were TRUE.",
        "",
    ]

    if not fired:
        lines += ["Nothing fired. That is a measurement of this range only, and "
                  "it is not a statement that the range holds no false claim: "
                  "the vocabulary misses about 45% of out-of-file claims, and "
                  "the one escape `batch-200d42` cared about carried no "
                  "quantifier at all.", ""]
        return "\n".join(lines)

    lines.append("## Every line that fired")
    lines.append("")
    for one in sorted(fired, key=lambda hit: (hit.path, hit.line)):
        lines.append(f"- `{one.path}:{one.line}` ({one.kind}, "
                     f"{', '.join(one.triggers)})")
        lines.append(f"  > {one.text}")
    lines.append("")
    lines.append(
        "For each line: does it claim something about code OUTSIDE its own "
        "file? If it does not, it is one of the 28-in-50 the vocabulary catches "
        "by accident and there is nothing to do. If it does, the repair the "
        "measurement recommends is a command beside the sentence that settles "
        "it -- each of the four false claims it found was settled by one grep."
    )
    lines.append("")
    return "\n".join(lines)


def write(path, text):
    """`(ok, message)`. A report that cannot be written never stops a run."""
    try:
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except (OSError, ValueError) as error:
        return False, (f"the report was NOT written to {path}: {error}. The "
                       "finding is above; nothing about the run is refused.")
    return True, f"report written to {path}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="the tree to read")
    parser.add_argument("--range", dest="rng", required=True,
                        help="a git range, `<base>..<head>`")
    parser.add_argument("--out", default="",
                        help="the report path; default beside --ledger")
    parser.add_argument("--ledger", default="",
                        help="this run's run.md, to place the report")
    parser.add_argument("--batch", default="", help="this run's batch id")
    args = parser.parse_args(argv)

    out = args.out or (report_beside(args.ledger) if args.ledger else REPORT)

    prose, error = collect(args.repo, args.rng)
    if error:
        print(f"COULD NOT READ `{args.rng}` in {args.repo}: {error}\n"
              "Nothing is asserted about this run, and nothing is refused. "
              "This report exits 0 by the human's ruling of 2026-09-12.",
              file=sys.stderr)
        return 0

    text = render(prose, len(prose), args.rng, args.batch)
    ok, said = write(out, text)
    fired = sum(1 for one in prose if one.triggers)

    print(f"{fired} lines fire on the tree-wide vocabulary, out of "
          f"{len(prose)} added comment and test-name lines in `{args.rng}`.")
    print(said if ok else f"NOT written: {said}",
          file=sys.stdout if ok else sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
