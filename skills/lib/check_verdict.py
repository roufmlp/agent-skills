#!/usr/bin/env python3
"""Refuse to proceed past a gate that produced no verdict.

Four skills spawn an adversarial agent whose entire output is a file:
`/run-issues` (verify and review), `/parallel-hunt` (claim and fix),
`/harden-issues` (attacker and seam) and `/panel-review` (the refutation gate).
In every one of them the orchestrator's next step assumes a verdict is on disk.
Nothing checked that it was.

Two gates died at the weekly usage limit during one workflow audit
and wrote nothing at all. Both times a person recovered the work by reading a
transcript by hand, and nothing mechanical noticed the gates had returned empty.
This notices.

It also survives the Claude Code upgrade. From 2.1.232 subagents run in the
background by default, so an orchestrator that no longer blocks could mark an
issue resolved before its gate has judged and read green. A step that refuses to
move without a verdict is correct under both behaviours.

Three refusals, and that is the whole of it:

    absent   the file is not there, or the named heading is not in it
    empty    the file, or the section under that heading, holds nothing
    pending  a row still reads `pending`, so the gate never judged it

**Name the section wherever the file has one.** A `/parallel-hunt` bug file
already carries the finder's evidence before any gate writes, and a
`/run-issues` issue file carries the criteria, so "the file exists and holds
bytes" passes on both while the gate has written nothing. The heading is what
makes the refusal real. Without `--section` this checks the whole file, which is
right for a `gate.md` the orchestrator opened and nothing else.

Reading the path in the run's own worktree is deliberate: a gate that drilled on
a private whole-tree copy can write its verdict beside the copy, and a verdict in
the wrong checkout reads as absent here. That is the intended answer, not a false
alarm — one gate's 175-line verdict was left in the wrong tree on one run.

Exit 0 authorises the next step. Exit 1 refuses and prints what it refused on.

Usage:
    check_verdict.py --file <path> [--section "## Review gate"]
"""

import argparse
import re
import sys
from dataclasses import dataclass, field

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
SEPARATOR = re.compile(r"^\|[\s|:-]+\|?\s*$")
# `pending`, `**pending**`, `_pending_`, `` `pending` `` — the skeleton's own
# cell in any emphasis a writer might reach for. Nothing else counts, so a
# verdict saying a decision is "pending with the human" is prose, not a gap.
DECORATION = "*_`~ "
# The words a real heading uses after its section name. Counted, not guessed:
# see `_matches`. Written flattened, the way `_flatten` leaves them.
SPELLED_OUT = ("re verdict", "verdict", "batch")


def _flatten(text):
    """Lowercase, with hyphens and runs of space reduced to one space."""
    return re.sub(r"[-\s]+", " ", text).strip().lower()


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""
    pending: list = field(default_factory=list)
    judged: int = 0
    total: int = 0


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _headings(text):
    """Every heading line, as (index, level, title), ignoring fenced code."""
    fenced = False
    for index, line in enumerate(text.splitlines()):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING.match(line)
        if match:
            yield index, len(match.group(1)), match.group(2).strip()


def _matches(title, wanted):
    """Is this heading the wanted section, qualifier and all?

    Counted over one project's issue files on 2026-08-16: 78 headings read
    `## Review gate` exactly, and the rest carry a qualifier — `— attempt 2`,
    `— 2026-07-23`, `— critical variant, 2026-08-09`, `, 2026-08-03`. All of
    those are the gate's verdict and must match, or the check refuses a healthy
    run, which costs more than no check at all.

    The qualifier begins with anything that is not a letter — a dash, a comma, a
    bracket, or a date straight after a space, all of which the corpus holds.
    Three words are allowed on top, each counted rather than guessed:
    `verdict` (99 bug files and 4 issue files), `re-verdict` (1) and `batch`
    (7, as in `## Fix gate batch 8 — verdict: verified`). Past one of those the
    rest of the heading is free text.

    Any other word continuing the title makes it a different section, so
    `## Review gate notes` misses and a note cannot stand in for a verdict.

    Hyphens read as spaces, because 17 of the 138 bug-file headings write
    `claim-gate` or `fix-gate`. Heading depth is ignored: the 2026-07-24 run
    wrote its gates at `###` and every run since at `##`.
    """
    lowered = _flatten(title)
    if lowered == wanted:
        return True
    if not lowered.startswith(wanted):
        return False
    rest = lowered[len(wanted):].lstrip()
    for word in SPELLED_OUT:
        if rest.startswith(word):
            return True
    return not rest or not rest[0].isalpha()


def read_section(text, section):
    """The body under this heading, or None when the heading is absent.

    Where the heading repeats — one section per gate attempt — the LAST one
    wins. It belongs to the attempt just spawned, and reading attempt 1's
    verdict for attempt 2 would pass a gate that has not reported.

    Case is ignored; leading hashes in the argument are optional, so both
    `## Review gate` and `Review gate` work. The body runs to the next heading
    at the same level or higher, so a gate that writes `### Rubric` under its
    own heading keeps it.
    """
    wanted = _flatten(section.lstrip("#"))
    lines = text.splitlines()
    headings = list(_headings(text))

    start = level = None
    for index, depth, title in headings:
        if _matches(title, wanted):
            start, level = index, depth
    if start is None:
        return None

    for index, depth, _title in headings:
        if index > start and depth <= level:
            return "\n".join(lines[start + 1:index])
    return "\n".join(lines[start + 1:])


def _rows(text):
    """The data rows of every markdown table here, header rows excluded."""
    lines = text.splitlines()
    out = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or SEPARATOR.match(stripped):
            continue
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if SEPARATOR.match(following):
            continue  # this is a header row
        out.append(stripped)
    return out


def _bare(cell):
    return cell.strip().strip(DECORATION).strip().lower()


def verdict_rows(text):
    """Every table row that carries a verdict cell, judged or not."""
    return [row for row in _rows(text) if len(_cells(row)) >= 2]


def pending_ids(text):
    """The id of every row whose verdict cell still reads `pending`."""
    out = []
    for row in verdict_rows(text):
        cells = _cells(row)
        if any(_bare(cell) == "pending" for cell in cells[1:]):
            out.append(_bare(cells[0]))
    return out


def decide(text, section=None):
    """Authorise or refuse the step after a gate spawn."""
    scope = text
    where = "the file"

    if section is not None:
        name = section.lstrip("#").strip()
        where = f"`{name}`"
        scope = read_section(text, section)
        if scope is None:
            return Decision(
                allowed=False,
                reason=(
                    f"Refused: no `{name}` heading in this file. The gate wrote "
                    f"its verdict somewhere else, or it died before writing "
                    f"anything. Check the path is the one in this run's own "
                    f"worktree — a gate that drilled on a private copy can "
                    f"leave its verdict beside the copy — then re-spawn it."
                ),
            )

    if not scope.strip():
        wrapped = (
            " Read the lines just under the heading before re-spawning: a title "
            "that wrapped onto a second `##` line leaves the body under the "
            "wrap, and this section then reads empty when a verdict is really "
            "there. Join the heading back into one line if that is what "
            "happened." if section is not None else ""
        )
        return Decision(
            allowed=False,
            reason=(
                f"Refused: {where} is empty. The gate produced no verdict, so "
                f"there is nothing to read and nothing to act on. Re-spawn it, "
                f"or record it as failed — never proceed as though it passed."
                f"{wrapped}"
            ),
        )

    total = len(verdict_rows(scope))
    pending = pending_ids(scope)
    if pending:
        judged = total - len(pending)
        return Decision(
            allowed=False,
            reason=(
                f"Refused: {len(pending)} row(s) in {where} still read "
                f"`pending` — {', '.join(pending)}. The gate judged {judged} of "
                f"{total} and stopped. Those {judged} stand; re-spawn a gate for "
                f"the rest, or record why they go unjudged."
            ),
            pending=pending,
            judged=judged,
            total=total,
        )

    return Decision(allowed=True, judged=total, total=total)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", required=True,
                        help="the verdict file, in this run's own worktree")
    parser.add_argument("--section", default=None,
                        help='the gate\'s heading, e.g. "## Review gate"')
    args = parser.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        print(
            f"Refused: cannot read {args.file}: {error}. A verdict that is not "
            f"there is not a pass.",
            file=sys.stderr,
        )
        return 1

    decision = decide(text, args.section)
    if decision.allowed:
        where = f"`{args.section.lstrip('#').strip()}`" if args.section else args.file
        if decision.total:
            print(f"verdict present in {where}: {decision.total} row(s), none pending")
        else:
            print(f"verdict present in {where}")
        return 0
    print(decision.reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
