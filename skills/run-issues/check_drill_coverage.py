#!/usr/bin/env python3
"""Refuse a gate verdict that grades a DRILL-CARRYING criterion in silence.

    python3 check_drill_coverage.py --issue <file> --section "## Review gate"

Ruled by the human on 2026-09-17, walking the decisions of run `batch-26c495`.
It is the third of three gate rules taken that evening, and the only one of them
that cost a gate round.

WHAT HAPPENED. Issue 114's criterion 7 names its own drill in the issue text:
"**Drive it:** run the two loudest of the nine ... concurrently on two workers
ten times, with MinIO up, and get ten identical results." The critical review
gate graded it **PASS** and its whole evidence was a count -- "Sixteen files
rather than the nine the issue predicted, held on one advisory lock and one
database, with the rule in `reset-road.ts` rather than a list." It never ran the
drill. The verify gate did, and found the pair red. The runner then drove it
too: red 4 of 4 at two workers, green 2 of 2 at one worker. A rule matching more
files is not evidence that a hole is closed.

WHAT THIS REFUSES, AND IT IS ONE THING. Where the issue names a drill for a
criterion, and the verdict's evidence for that criterion is the IMPLEMENTATION
RECORD's rather than the gate's own, the verdict must say so. Leaning on the
record is legal and often sensible. Leaning in silence is not, because the
runner then reads the round as two independent measurements when it holds one.

THE WIDER RULE DID NOT MECHANISE, AND THAT IS RECORDED HERE RATHER THAN HIDDEN.
The human's rule as agreed was "a gate may not grade a behaviour criterion by
reading code". Two attempts to enforce that directly both failed:

  * Reading a criterion's entry for ANY evidence passed issue 114's criterion 7
    outright, because the entry cites `reset-road.ts` and a backticked file name
    looked like a result.
  * Tightening the evidence test to results only then refused FOUR of eleven
    criteria in the round-2 verdict that had driven seven of them, because the
    prose a gate uses for a drive -- "runs green in this gate's copy" -- carries
    no number at all.

A check that cries wolf gets switched off, so the second half was demoted to a
report and is printed under `NOT GRADED`. What survives is the narrow rule that
caught the real fault with no false alarm on either round-2 verdict. Per
`~/.claude/CLAUDE.md`: make it mechanical or let it go, and never answer a
failed reminder with a second reminder. Half of this was let go.

WHAT IT IS NOT

- Not a pass/fail on the criterion. The gate's own verdict word is untouched.
- Not run on an issue whose criteria name no drill. Those exit 0 saying so.
- Never a halt. Exit 1 names the criteria, and the repair is one sentence in the
  verdict rather than a re-spawn.

EXIT CODES

  0  no drill-carrying criterion leans on the record in silence
  1  one or more do
  2  could not grade -- no such file, or the section is absent or empty
"""

import argparse
import re
import sys

# The phrases an issue uses to name a drill. Measured across one project's
# tracker on 2026-09-17: `**Drive it:**`, `**Drive both:**`, `**Drive the
# mutation once, in this order:**`, `**Drive the mutation, in this order:**`.
# The common stem is a bolded imperative "Drive", so that is what is matched
# rather than the four full phrases, which would go stale at the next author.
_DRILL = re.compile(r"\*\*\s*drive\b", re.IGNORECASE)

# A numbered criterion opens a block. Real issues write `- [ ] **1. ...` and
# gates write `1. **...`, `**1.** ...` and `| 1 | ...`. All four forms put the
# number early on the line, so the number is read from the first 12 characters.
_NUMBER = re.compile(r"^[\s\-\[\]x*|>]*\*{0,2}(\d{1,2})[.)\s*|]")

# The gate drove something and is quoting a RESULT.
#
# A backticked symbol was in this list in the first draft and had to come out.
# It made the check pass issue 114's criterion 7 -- the very fault this exists
# for -- because that entry cites `reset-road.ts`. A file name is not a result.
# A drill produces counts, exit codes, timings or a colour; nothing else counts.
_EVIDENCE = re.compile(
    r"\b\d+\s*(?:of|/)\s*\d+\b"      # "10 of 10", "4/4"
    r"|\bexit\s*(?:code\s*)?\d+\b"   # "exit 0"
    r"|\b(?:red|green|passed|failed|skipped)\b\s*\d"   # "red 4"
    r"|\b\d+\s*(?:ms|s|seconds)\b",  # a timing
    re.IGNORECASE)

# The gate is quoting the IMPLEMENTATION RECORD's evidence rather than its own.
#
# This is the shape that actually shipped the fault. Issue 114's criterion 7
# read "The record drives unheld (9, 5 and 9 files red in three runs) against
# held (17 of 17 twice)" -- real numbers, none of them this gate's. A gate is
# free to lean on the record; what it may not do is lean without saying so,
# because the runner then reads the round as two independent measurements when
# it holds one.
# ONLY the verb forms, and the bare mention was removed after it cried wolf.
# An early draft also matched a plain "the implementation record", which fired
# twice on the round-2 verify verdict: once where the gate was CRITICISING the
# record ("the implementation record's criterion 9 drill names the wrong kind of
# file") and once where it was explaining scope ("the implementation record
# explains why for seven of them"). Neither sources a result from the record.
# What the fault actually looks like is a verb of reporting: issue 114's
# criterion 7 read "The record drives unheld ... against held (17 of 17 twice)".
#
# EVERY GAP IS `\s+`, NEVER A LITERAL SPACE. A gate wraps its verdict at about
# 95 characters, so any phrase of three words straddles a newline sooner or
# later. The first draft used single spaces and missed "This gate did\n   not
# re-drive it" -- a disclosure, read as a silent lean, which would have refused
# the honest case. That is the false alarm that gets a check switched off.
_LEANED = re.compile(
    r"\bthe\s+(?:implementation\s+)?record\s+"
    r"(?:drives|drove|shows|showed|says|said|reports|reported|holds|measured|"
    r"records|recorded)\b",
    re.IGNORECASE)

# The gate said it did NOT drive, which is the other legal answer.
_DISCLOSED = re.compile(
    r"did\s+not\s+(?:re-)?drive"
    r"|did\s+not\s+re-?run"
    r"|not\s+driven"
    r"|drove\s+none"
    r"|graded\s+by\s+reading"
    r"|read\s+rather\s+than\s+driven",
    re.IGNORECASE)

# The entry points somewhere else in the same verdict for its evidence. Issue
# 114's criterion 9 was rejected in round 1 with a whole section of drives under
# its own heading, and its rubric line reads "See below." Treating that as
# silence is a false refusal, and a check that cries wolf gets switched off.
_POINTER = re.compile(
    r"\bsee\s+(?:below|above|the\s|§)"
    r"|\bbelow\b.{0,20}\brejection\b",
    re.IGNORECASE | re.DOTALL)


def criteria_with_drills(text):
    """`{number: True}` for every acceptance criterion naming a drill.

    Reads the `## Acceptance criteria` section alone. A drill named anywhere
    else in the issue is prose about the work, not a criterion's own bar.
    """
    section = _named_section(text, "## Acceptance criteria")
    if section is None:
        return {}
    found, current = {}, None
    for line in section.splitlines():
        match = _NUMBER.match(line[:12])
        if match:
            current = int(match.group(1))
            found.setdefault(current, False)
        if current is not None and _DRILL.search(line):
            found[current] = True
    return {number: True for number, has in found.items() if has}


def _named_section(text, heading):
    """The body under `heading`, to the next heading of the same depth or less."""
    depth = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    wanted = heading.strip().lower()
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower().startswith(wanted):
            start = index + 1
            break
    if start is None:
        return None
    body = []
    for line in lines[start:]:
        stripped = line.lstrip("#")
        this_depth = len(line) - len(stripped)
        if line.startswith("#") and 0 < this_depth <= depth:
            break
        body.append(line)
    return "\n".join(body)


def answered(section_text):
    """`{number: state}` per numbered entry.

    States, in the order they are tested: `disclosed` (the gate said it did not
    drive), `pointer` (it points elsewhere in its own verdict), `leaned` (it is
    quoting the implementation record's evidence and has NOT disclosed),
    `evidence` (a result of its own), `silent`.

    `disclosed` is tested first on purpose: an entry that both leans and
    discloses is the honest case, and issue 114's criterion 6 is exactly that.
    """
    blobs = {}
    current, buffer = None, []

    def flush():
        if current is None:
            return
        # ACCUMULATE, never overwrite. A verdict numbers things more than once:
        # the rubric runs 1..11 and the findings table that follows it starts
        # again at 1. An overwriting bind let the table's row 7 replace the
        # rubric's criterion 7, which is how the first working draft of this
        # check reported nine criteria "silent" in a verdict that discussed
        # every one of them. Evidence anywhere about criterion N is evidence
        # about criterion N.
        blobs.setdefault(current, []).append("\n".join(buffer))

    for line in section_text.splitlines():
        match = _NUMBER.match(line[:12])
        if match:
            flush()
            current, buffer = int(match.group(1)), [line]
        elif current is not None:
            buffer.append(line)
    flush()

    verdict = {}
    for number, parts in blobs.items():
        blob = "\n".join(parts)
        if _DISCLOSED.search(blob):
            verdict[number] = "disclosed"
        elif _POINTER.search(blob):
            verdict[number] = "pointer"
        elif _LEANED.search(blob):
            verdict[number] = "leaned"
        elif _EVIDENCE.search(blob):
            verdict[number] = "evidence"
        else:
            verdict[number] = "silent"
    return verdict


def grade(issue_text, section_heading):
    """`(exit_code, lines)`."""
    drills = criteria_with_drills(issue_text)
    if not drills:
        return 0, ["ok: the issue's acceptance criteria name no drill, so "
                   "there is nothing for this to grade."]

    section = _named_section(issue_text, section_heading)
    if section is None or not section.strip():
        return 2, [f"REFUSED: {section_heading!r} is absent or empty, so "
                   "nothing was graded. That is not a pass."]

    graded = answered(section)
    def those(state):
        return sorted(n for n in drills if graded.get(n, "silent") == state)

    silent, leaned = those("silent"), those("leaned")
    drove, told, pointed = those("evidence"), those("disclosed"), those("pointer")

    lines = []
    if leaned:
        lines.append(
            "REFUSED leaned-undisclosed: "
            + ", ".join(f"criterion {n}" for n in leaned)
            + " name a drill, and the verdict's evidence for them is the "
              "IMPLEMENTATION RECORD's rather than this gate's, without "
              "saying so. The runner then reads the round as two independent "
              "measurements when it holds one.")
        lines.append(
            "  This is issue 114's criterion 7, 2026-09-17: graded PASS on a "
            "file count and the record's own numbers, while the drill it "
            "skipped was red 4 of 4 the first time anybody ran it.")
        lines.append(
            "  The repair is one sentence, not a re-drive: say that this gate "
            "leaned on the record. Leaning is legal; leaning in silence is not.")
    else:
        lines.append(
            f"ok: {len(drills)} drill-carrying criterion(s) in the issue, and "
            "none is graded on the implementation record's evidence in silence.")

    lines.append(
        f"  drove: {drove or 'none'} · disclosed a non-drive: {told or 'none'}"
        f" · pointed elsewhere: {pointed or 'none'} · leaned undisclosed: "
        f"{leaned or 'none'}")

    # REPORTED, NEVER REFUSED. See the module docstring: the prose a gate uses
    # to describe a drive is too various to recognise, and a refusal here fired
    # on four of eleven criteria in a round-2 verdict that had driven seven of
    # them. A check that cries wolf gets switched off, so this half states what
    # it saw and grades nothing.
    if silent:
        lines.append(
            f"  NOT GRADED, reported only: criteria {silent} name a drill and "
            "this could not recognise a result, a disclosure or a pointer in "
            "their entries. That is as likely to be this reader's blindness as "
            "the gate's silence. Read them before you quote this line.")

    lines.append(
        "  This grades DISCLOSURE and never the drill. Whether a drill was the "
        "right one, or its result read correctly, passed here unread.")
    return (1 if leaned else 0), lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Refuse a gate verdict silent on a criterion's own drill.")
    parser.add_argument("--issue", required=True)
    parser.add_argument("--section", required=True,
                        help='e.g. "## Review gate, round 2"')
    args = parser.parse_args(argv)
    try:
        with open(args.issue, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print(f"REFUSED: cannot read {args.issue}: {error}", file=sys.stderr)
        return 2
    code, lines = grade(text, args.section)
    stream = sys.stderr if code else sys.stdout
    for line in lines:
        print(line, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
