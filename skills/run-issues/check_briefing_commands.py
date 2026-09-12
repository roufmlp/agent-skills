#!/usr/bin/env python3
"""Refuse a merge briefing that hands a human a command marked neither RAN nor UNRUN.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, and the human's ruling in the daily-brief walk of 2026-09-08. Eight commands
in run `batch-207704`'s merge briefing do not do what their text says, and every
one was written by a gate that never ran it: `tsc --noEmit` written bare where
neither `tsc` nor `eslint` is on the path, `npx eslint` given no target and
exiting 0 while linting nothing, `git show HEAD:` naming no file, three seeders
handed over as bare paths with no execute bit. A reader pasting those gets a
false pass, and a check that errors in a human's hands reads as diligence.

WHY IT IS A REFUSAL AND NOT A REMINDER. The finale proposed "a gate runs any
command it writes". The human's own three-class test says a reminder will not work,
they were told so before they ruled, and they ruled adopt on the mechanical form. **A
gate may always mark UNRUN and pay nothing**, so the worst case here is honest
rather than expensive. The four gate briefs in `~/.claude/agents/` already carry
the UNRUN half; sitting 4 of this ticket added the RAN half, which is what makes
the rule readable by a machine. Before it, a command that WAS run carried no mark
at all, so nothing could tell "ran, unmarked" from "never considered".

WHAT COUNTS AS A HANDED-OVER COMMAND, and the definition is the whole difficulty.
Run `batch-207704`'s briefing holds 1,332 inline code spans and 24 distinct
commands. A check firing on every span would refuse it for naming `storableRow`;
one firing on every fenced block would refuse it for quoting a cost table. So a
command is a code span, or a line inside a fence, that

    - starts with a runner from RUNNERS below AND carries an argument, so the
      bare noun `tsc` in "`tsc` and `lint` clean" does not fire; or
    - starts with an executable script path, which must either sit under a
      script root (`scripts/`, `./`, `~/`, `/`) or carry an argument, so the 60
      source-file citations the briefing makes do not fire.

Leading `VAR=value` assignments are stripped before the runner is read.

WHAT IT CANNOT SEE. The eighth fault the finale found by hand is twelve
whole-suite figures quoted with NO command beside them. No check reading what is
written can see an absence, and this one does not pretend to.

    python3 check_briefing_commands.py <merge-briefing.md> [--list]

Exit 0 authorises the merge briefing. Exit 1 refuses and names every unmarked
command with its line. `--list` names every command it finds, marked or not, and
always exits 0: a gate reads what the check reads before it marks anything, and
reading may not refuse. Drill: `test_check_briefing_commands.py` beside this file.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

# The runners this pipeline actually hands over, read off run `batch-207704`'s
# briefing and its three siblings. Kept tight on purpose: every name added here
# is a class of prose that starts refusing.
RUNNERS = frozenset({
    "git", "npm", "npx", "node", "python3", "psql", "bash", "sh", "tsc",
    "eslint", "vitest", "pytest", "uv", "make", "docker", "curl", "gh",
    "supabase", "vercel",
})

# A script this machine can execute, as opposed to a source file the briefing
# cites. `.ts` and `.tsx` are deliberately absent: they are the citation shape.
EXECUTABLE = re.compile(r"\.(?:mjs|js|sh|py)$")
SCRIPT_ROOT = re.compile(r"^(?:\./|~/|/|scripts/|\.claude/)")
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# The two marks, as tokens. Uppercase and whole-word, because "I ran it" is the
# sentence every gate already writes and a check reading that prose word would
# authorise every briefing ever written.
MARK = re.compile(r"\b(UNRUN|RAN)\b")

SPAN = re.compile(r"`([^`\n]+)`")
# A trailing shell comment on a fenced line is beside the command, not part of
# it, and it is a real place to write the mark. `#` must follow whitespace, so a
# `%h#%d` format string is not cut.
TRAILING_COMMENT = re.compile(r"\s+#.*$")
FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")

AFK = (
    "\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR ABDUL. He is AFK for every "
    "run. Take one of the two roads above now and carry on."
)


@dataclass(frozen=True)
class Command:
    """One handed-over command, and the mark standing beside it."""

    text: str
    line: int
    block: int
    marked: str | None = None


def is_command(candidate: str) -> bool:
    """True when this code span hands a human something to run."""
    tokens = candidate.strip().split()
    while tokens and ENV_ASSIGNMENT.match(tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return False
    head, arguments = tokens[0], tokens[1:]
    if EXECUTABLE.search(head):
        return bool(arguments) or bool(SCRIPT_ROOT.match(head))
    return head in RUNNERS and bool(arguments)


def blocks(text: str) -> list:
    """One block id per line, 0-based, `None` for a boundary line.

    A block is what "mark it UNRUN beside the command" means: a list item or a
    paragraph, however many lines it takes, plus any fenced block hanging under
    it. A heading closes a block and belongs to none, so a mark under one
    heading cannot reach a command under the next.
    """
    ids: list = []
    current = None
    counter = 0
    in_fence = False
    last_closed = None
    for line in text.splitlines():
        if FENCE.match(line):
            if not in_fence and current is None:
                # A fence opening after a blank line rejoins the paragraph that
                # introduced it, which is where its mark is written.
                current = last_closed if last_closed is not None else counter
                if current == counter:
                    counter += 1
            in_fence = not in_fence
            ids.append(current)
            if not in_fence:
                # A closing fence leaves NOTHING for the next fence to rejoin. A
                # mark written for one fenced block may not authorise the block
                # below it, which is a different command the writer never ran.
                last_closed, current = None, None
            continue
        if in_fence:
            ids.append(current)
            continue
        if HEADING.match(line):
            last_closed, current = None, None
            ids.append(None)
            continue
        if not line.strip():
            if current is not None:
                last_closed, current = current, None
            ids.append(None)
            continue
        if current is None:
            current, counter = counter, counter + 1
        ids.append(current)
    return ids


def commands(text: str) -> list:
    """Every handed-over command in the briefing, in the order it is written."""
    ids = blocks(text)
    lines = text.splitlines()
    found = []
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        block = ids[index]
        if in_fence:
            # Inside a fence the whole line is the candidate: backticks are not
            # spans there. Only two of run `batch-207704`'s sixteen fenced
            # blocks hold a command, and the rest are rails and cost tables.
            spelling = TRAILING_COMMENT.sub("", line).strip()
            if is_command(spelling):
                found.append(Command(spelling, index + 1, block))
            continue
        for span in SPAN.findall(line):
            if is_command(span):
                found.append(Command(span.strip(), index + 1, block))
    return found


def audit(text: str) -> list:
    """Every command, each carrying the mark standing in its own block.

    **A command may not mark itself.** The mark is read from what is LEFT of the
    line once every command on it is removed, so a command carrying the token —
    an env var named `RAN=1`, a quoted diff line — authorises nothing. A comment
    beside a fenced command survives that removal and still marks it.
    """
    ids = blocks(text)
    lines = text.splitlines()
    found = commands(text)

    written: dict = {}
    for one in found:
        written.setdefault(one.line, []).append(one.text)

    marks: dict = {}
    for index, line in enumerate(lines):
        block = ids[index]
        if block is None or block in marks:
            continue
        residue = line
        for spelling in written.get(index + 1, []):
            residue = residue.replace(spelling, " ")
        seen = MARK.search(residue)
        if seen:
            marks[block] = seen.group(1)
    return [Command(one.text, one.line, one.block, marks.get(one.block))
            for one in found]


def report(results: list, path) -> tuple:
    """`(exit code, text)`. Pure: it reads nothing."""
    unmarked = [one for one in results if one.marked is None]
    if not results:
        return 0, f"{path}: no handed-over command. Nothing to mark."
    if not unmarked:
        marked = ", ".join(sorted({one.marked for one in results}))
        return 0, (f"{path}: {len(results)} handed-over commands, every one "
                   f"marked ({marked}).")

    named = "\n".join(f"  {path}:{one.line}  {one.text}" for one in unmarked)
    return 1, (
        f"REFUSED. Mark each command below `RAN` or `UNRUN` in its own block, "
        "then re-run this check.\n"
        f"  {len(unmarked)} of {len(results)} handed-over commands carry "
        "neither mark:\n"
        f"{named}\n"
        "  Eight commands in run `batch-207704`'s merge briefing did not do "
        "what their text said, and every one was written by a gate that never "
        "ran it. A check that errors in a human's hands reads as diligence.\n"
        "  Two roads out:\n"
        "  1. Run it once yourself, read-only, against the state it will "
        "actually meet, then write `RAN` beside it.\n"
        "  2. Write `UNRUN` beside it. That is free and it is always allowed. "
        "An unrun check may not be presented as a safety step, and saying so "
        "costs nothing." + AFK)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("briefing", help="the run's merge-briefing.md")
    parser.add_argument("--list", action="store_true",
                        help="name every command found, marked or not; exits 0")
    args = parser.parse_args(argv)

    path = pathlib.Path(args.briefing)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as reason:
        print(f"REFUSED. Read the briefing and re-run this check: {path}\n"
              f"  {reason}\n"
              "  Two roads out:\n"
              "  1. Give the path to this run's own `merge-briefing.md`, under "
              "`.scratch/<feature>/runs/<batch-id>/`.\n"
              "  2. If no briefing exists yet, this call is too early: write it "
              "first." + AFK, file=sys.stderr)
        return 1

    results = audit(text)
    if args.list:
        for one in results:
            print(f"{path}:{one.line}  {one.marked or '--'}  {one.text}")
        print(f"{len(results)} handed-over commands, "
              f"{sum(1 for one in results if one.marked is None)} unmarked.")
        return 0

    code, text = report(results, str(path))
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
