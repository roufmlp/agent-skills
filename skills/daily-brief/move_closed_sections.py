#!/usr/bin/env python3
"""Move the pending-actions file's closed sections into an archive beside it.

`/daily-brief` reads the whole pending-actions file every day, in a fresh session
with no cross-day cache, and much of what it reads is sections that closed days
ago. This moves them out. It is invoked from the apply step of the daily-brief
skill, with the live file's path as the argument.

WHAT IT MATCHES. Only a `#` or `##` heading whose own text carries an uppercase
`DONE`, `STRUCK`, `CLOSED` or `SUPERSEDED` **and** a date. A marker in body text
is not a section. A marker at `###` or deeper is not matched, which is a decision
and not an oversight: widening the matcher is a decision, not a reflex.

WHAT IT REFUSES, and this is the whole point of the script.

  Open work inside the marked heading. `ticket 27 is MERGED ... Actions 1 and 2
  are DONE. Steps 5, 7 and 8 remain.` reads as closed to any matcher that stops
  at the marker, and archiving it would file live work where nobody looks.

  A mixed block. A marked section whose own subheadings hold open work goes
  nowhere, whole. And a `DONE` subheading inside a parent that is itself refused
  is never lifted out on its own, because the record of what is finished is what
  makes the parent's remaining steps legible.

  A marker with no date. `ACTION 1 — DONE. Merged, pushed, deployed.` is almost
  certainly closed and this refuses it anyway, because "almost certainly" is the
  judgement call this script exists to delete.

  A negation is read, not ignored. `Nothing on it waits on you` closes a section;
  `Three actions remain` does not. The test is the clause, so a heading that
  closes one thing and leaves another open is refused on the open clause.

  The refusal is by heading, not by body prose. A section whose heading is
  cleanly closed but whose body still holds an ask will be archived. That limit
  is deliberate — the body of these sections is full of the ordinary words open
  work is written in, and a matcher that read them would refuse everything. The
  archive is the mitigation: nothing is deleted, so a wrong move is one grep and
  one paste from being undone.

NOTHING IS DELETED. The matched sections are appended to the archive first and
removed from the live file second, and the live rewrite is a temp file and a
rename. If the live file changes between the read and the rewrite — several
sessions may write it — the append is rolled back and nothing moves.

NEVER CITE THE PENDING FILE BY LINE NUMBER. It is newest-first and grows daily.
One counterexample sat at three different lines inside one working day while
three readers checked it, with identical text every time. Everything here
matches and reports heading text.

Usage:
    move_closed_sections.py [--dry-run] [--archive PATH] FILE
"""

import argparse
import hashlib
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

MAX_LEVEL = 2

MARKERS = ("DONE", "STRUCK", "CLOSED", "SUPERSEDED")

# Whole words only. `blockers` in "both run blockers are closed" is not `block`,
# and a matcher that cannot tell them apart refuses the clean headings too.
OPEN_WORK = (
    "remain", "remains", "remaining",
    "left", "outstanding", "pending",
    "wait", "waits", "waiting",
    "need", "needs", "needed",
    "block", "blocks", "blocked", "blocking",
    "still", "unresolved", "todo",
)

# A pending file writes an ask as a heading shape as often as it writes one as a
# sentence, and no word list reaches those. Real blocks read closed at the top
# and hold one of these below: `## 5. OPEN — walk the new grain`, `## Your next
# step on this`, `### On you`, `### On the human, in order`.
ASK_SHAPES = (
    (re.compile(r"\bOPEN\b"), "OPEN"),
    (re.compile(r"\bon (you|the human)\b", re.IGNORECASE), "on you"),
    (re.compile(r"\bnext step", re.IGNORECASE), "next step"),
    (re.compile(r"\bstill open\b", re.IGNORECASE), "still open"),
)

# A negation anywhere in the same clause turns the open-work word into a closure
# statement: "Nothing on it waits on you" is the end of a block, not an ask.
NEGATIONS = ("nothing", "none", "never", "no ", "not ")

CLAUSE_BREAK = re.compile(r"[.;—:]")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6}) +(.*)$")
WORD = re.compile(r"[a-z']+")
MONTHS = (
    "january|february|march|april|may|june|july"
    "|august|september|october|november|december"
)
DATE = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    rf"|\b\d{{1,2}}\s+({MONTHS})\b"
    rf"|\b({MONTHS})\s+\d{{1,2}}\b",
    re.IGNORECASE,
)

ARCHIVE_HEADER = """# The pending-actions file — the closed sections

Sections moved out of the live pending-actions file by `move_closed_sections.py`,
oldest run first. Nothing here was edited on the way in; every section is the
text that stood in the live file, verbatim. Nothing is deleted.
"""


class LiveFileMoved(Exception):
    """The live file changed between the read and the rewrite."""


@dataclass(frozen=True)
class Section:
    """One heading and everything under it, as it stands in the live file."""

    level: int
    heading: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Refusal:
    heading: str
    reason: str


@dataclass
class Result:
    archived: list = field(default_factory=list)
    refused: list = field(default_factory=list)


def marker_in(heading):
    """The closure marker a heading carries, or None. Uppercase only.

    `the auth work was already done` is prose. `Action 1 is DONE` is a marker.
    Case is the only thing that separates them in this file.
    """
    for marker in MARKERS:
        if re.search(rf"\b{marker}\b", heading):
            return marker
    return None


def open_work_in(heading):
    """The open-work signals a heading carries un-negated, in order.

    Read by clause, because one heading routinely closes one thing and leaves
    another open: `ticket 27 is MERGED ... Actions 1 and 2 are DONE. Steps 5, 7
    and 8 remain.` The clause is also what keeps `nothing here waits on you`
    from reading as an ask.
    """
    found = []
    for clause in CLAUSE_BREAK.split(heading):
        lowered = clause.lower()
        if any(negation in lowered for negation in NEGATIONS):
            continue
        words = set(WORD.findall(lowered))
        for signal in OPEN_WORK:
            if signal in words and signal not in found:
                found.append(signal)
        for pattern, name in ASK_SHAPES:
            if pattern.search(clause) and name not in found:
                found.append(name)
    return found


def has_date(heading):
    return bool(DATE.search(heading))


def headings(lines):
    """Every real heading as (index, level, text). Fenced lines are not code."""
    fenced = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING.match(line)
        if match:
            yield index, len(match.group(1)), line.rstrip("\n")


def build_sections(lines):
    """Every heading as a Section spanning to the next heading of its level or
    above. Returned in file order, parents before their children."""
    marks = list(headings(lines))
    sections = []
    for position, (index, level, heading) in enumerate(marks):
        end = len(lines)
        for later_index, later_level, _ in marks[position + 1:]:
            if later_level <= level:
                end = later_index
                break
        sections.append(
            Section(level, heading, "".join(lines[index:end]), index, end)
        )
    return sections


def judge(section, sections):
    """(archivable, reason). The reason is the refusal text when it is not."""
    marker = marker_in(section.heading)
    if not marker:
        return False, ""
    if section.level > MAX_LEVEL:
        return False, ""
    if not has_date(section.heading):
        return False, (
            f"carries {marker} but no date, so what it closed cannot be read "
            "off the heading"
        )
    own = open_work_in(section.heading)
    if own:
        return False, (
            f"carries {marker} and open work in the same heading "
            f"({', '.join(own)})"
        )
    for other in sections:
        if other is section or not (section.start < other.start < section.end):
            continue
        below = open_work_in(other.heading)
        if below:
            return False, (
                f"mixed block: a heading below it still holds open work "
                f"({', '.join(below)}) — {other.heading.strip()}"
            )
    return True, ""


def plan(text):
    """What would move and what is refused, deciding nothing else."""
    lines = text.splitlines(keepends=True)
    sections = build_sections(lines)
    result = Result()
    settled = []

    for section in sections:
        # A section inside one already settled travels with it. Archived spans
        # move whole; refused spans stay whole, which is what stops a `DONE`
        # subheading being lifted out of a parent that still holds open work.
        if any(start <= section.start < end for start, end in settled):
            continue
        archivable, reason = judge(section, sections)
        if archivable:
            result.archived.append(section)
            settled.append((section.start, section.end))
        elif reason:
            result.refused.append(Refusal(section.heading, reason))
            settled.append((section.start, section.end))
    return result


def remaining_text(text, archived):
    """The live file with the archived spans removed, and nothing else changed."""
    lines = text.splitlines(keepends=True)
    dropped = set()
    for section in archived:
        dropped.update(range(section.start, section.end))
    return "".join(line for index, line in enumerate(lines) if index not in dropped)


def _append_archive(archive, sections):
    """Append the sections verbatim. Returns the byte length before the append,
    so a later refusal can put the file back exactly as it was."""
    before = archive.stat().st_size if archive.exists() else 0
    body = "" if before else ARCHIVE_HEADER
    body += "\n" + "".join(section.text for section in sections)
    with open(archive, "a", encoding="utf-8") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    return before


def _write_atomically(path, text):
    handle, temp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def apply_move(live, archive, dry_run=False, _after_archive=None):
    """Archive first, remove second, roll the archive back if the file moved.

    `_after_archive` is a test seam: it runs between the append and the rewrite,
    which is the window a parallel session writes into.
    """
    live, archive = Path(live), Path(archive)
    text = live.read_text(encoding="utf-8")
    result = plan(text)
    if dry_run or not result.archived:
        return result

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    before = _append_archive(archive, result.archived)

    if _after_archive is not None:
        _after_archive()

    now = live.read_text(encoding="utf-8")
    if hashlib.sha256(now.encode("utf-8")).hexdigest() != digest:
        with open(archive, "r+b") as handle:
            handle.truncate(before)
        raise LiveFileMoved(
            f"{live} changed while the move was running, so nothing was moved. "
            "The archive append has been rolled back. Run it again."
        )

    _write_atomically(live, remaining_text(text, result.archived))
    return result


def report(result, live, archive, dry_run):
    lines = []
    verb = "would move" if dry_run else "moved"
    lines.append(f"{verb} {len(result.archived)} section(s) to {archive}")
    for section in result.archived:
        lines.append(f"  + {section.heading.strip()}")
    if result.refused:
        lines.append("")
        lines.append(f"refused {len(result.refused)}, left in {live.name}:")
        for refusal in result.refused:
            lines.append(f"  - {refusal.heading.strip()}")
            lines.append(f"      {refusal.reason}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", help="the live pending-actions file")
    parser.add_argument("--archive", default=None, help="the archive file")
    parser.add_argument(
        "--dry-run", action="store_true", help="report the plan and write nothing"
    )
    args = parser.parse_args(argv)

    live = Path(args.file)
    archive = (
        Path(args.archive)
        if args.archive
        else live.with_name(live.stem + "-closed.md")
    )

    if not live.exists():
        print(f"No live file at {live}", file=sys.stderr)
        return 1
    if live.resolve() == archive.resolve():
        print(
            f"The live file and the archive are the same file: {live}",
            file=sys.stderr,
        )
        return 1

    try:
        result = apply_move(live, archive, dry_run=args.dry_run)
    except LiveFileMoved as moved:
        print(str(moved), file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Cannot move: {error}", file=sys.stderr)
        return 1

    print(report(result, live, archive, args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
