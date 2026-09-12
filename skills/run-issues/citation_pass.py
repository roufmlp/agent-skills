#!/usr/bin/env python3
"""Say whether a commit's citation pass finished, or was killed part-way.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling Q7, and the rule the human adopted in the daily-brief walk of
2026-09-08: **the runner refuses a dead citation pass.** A missing
`=== CITATION PASS COMPLETE ===` terminator is treated the way a red test is
treated.

THE INCIDENT. Run `batch-207704`'s last citation pass died after 48 lines,
inside its own preamble. The file was on disk and held content, so every reader
of it called the sweep clean. It had swept nothing. This environment's session
host exits at its 24-hour mark and takes every session with it, so a part-written
file is the ordinary failure here rather than a rare one, and the file on disk is
the only record.

ONE CHECK, THREE READERS, which is why it is a module and not a paragraph in
each. `run-issues/SKILL.md` names it at the runner's commit step, inside the
correction round's close (`correction_close.py` imports it), and in the finale's
collection of every per-sha file. Sitting 2 of this ticket found a report
re-implementing the rule it reported on; three copies of a tail check would drift
the same way.

WHAT IT REFUSES, and it is only this:

    absent          a sha was named and the directory holds no file for it
    unterminated    the file's last non-blank line is not the terminator
    nothing at all  no sha was named and the directory holds no file

WHAT IT NAMES BUT DOES NOT REFUSE. A terminator carrying a non-zero `exit=`. Exit
3 is a tree with no `.git` and exit 5 is an issue file the pinned tree does not
hold; both come from a pass that RAN and returned, which is a different fault
from a pass that died. The ruled scope is the missing terminator. Reporting the
number lets the runner file the register row the skill already asks for.

    python3 citation_pass.py --deltas <dir> [--sha <sha> ...]

Exit 0 authorises the next step. Exit 1 refuses and names every sha it refused
on. Drill: `test_citation_pass.py` beside this file.

**Three measurements behind SKILL.md step 4's citation rules, moved here by
ticket 36 sitting 5 (2026-09-09).** Pinning each pass to its commit took R2's
cost to nearly nothing: run `e047ba` paid about 5h50m on an 8h30m estimate for
ten serial passes, and a pinned pass is roughly 40 minutes against an issue of
30 to 90, so the queue mostly keeps up. On run `batch-170a59` four of six
commits had no pass at all and the finale's listing was the only thing that
noticed, which is why the finale reads every file's last line rather than
re-running the pass. The catch-up pass at branch head was removed by the human on
2026-09-06, by the argument that removed the differential on 2026-08-28: at
full scope on that same run it read 268 files, about 17,200 citations, ran 70
minutes at 4 per cent CPU duty and was about three hours from finishing when it
was stopped, and nothing in a run acts on its finding.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from dataclasses import dataclass

# The last line a finished pass prints, set in `run-issues/SKILL.md`:
# `=== CITATION PASS COMPLETE === exit=<n> pinned=<sha>`.
TERMINATOR = "=== CITATION PASS COMPLETE ==="
TAIL = re.compile(re.escape(TERMINATOR) + r"\s+exit=(\d+)\s+pinned=(\S+)")

AFK = (
    "\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR ABDUL. He is AFK for every "
    "run. Take one of the two roads above now and carry on."
)


@dataclass(frozen=True)
class Pass:
    """One commit's pass file, as read."""

    sha: str
    path: pathlib.Path
    state: str
    exit_code: int | None = None
    pinned: str | None = None


def verdict(path) -> Pass:
    """Read one pass file. `complete`, `unterminated` or `absent`.

    The terminator must be the LAST non-blank line. A pass that printed it and
    then went on was killed after it, and reading for the string anywhere in the
    file would call that clean.
    """
    path = pathlib.Path(path)
    sha = path.stem
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return Pass(sha, path, "absent")

    last = ""
    for line in reversed(lines):
        if line.strip():
            last = line.strip()
            break
    if not last.startswith(TERMINATOR):
        return Pass(sha, path, "unterminated")

    found = TAIL.search(last)
    if not found:
        return Pass(sha, path, "complete")
    return Pass(sha, path, "complete", int(found.group(1)), found.group(2))


def survey(deltas, shas) -> list:
    """Every named sha in the order given, or every file in the directory.

    Naming the shas is the correction round's road: it re-runs the pass over the
    files it touched and reads back only those. Naming none is the finale's road,
    which collects the whole directory.
    """
    deltas = pathlib.Path(deltas)
    if shas:
        return [verdict(deltas / f"{sha}.txt") for sha in shas]
    try:
        # `*.txt` and nothing else. `SKILL.md` writes one file per sha and names
        # it `<sha>.txt`; anything else in the directory is not a pass. Reading
        # every file made a macOS `.DS_Store` refuse a clean finale and tell the
        # runner to "re-run the citation pass for .DS_Store".
        found = sorted(p for p in deltas.glob("*.txt") if p.is_file())
    except OSError:
        return []
    return [verdict(p) for p in found]


def report(results, deltas) -> tuple:
    """`(exit code, text)`. Pure: it reads nothing."""
    lines = []
    refused = []
    for one in results:
        if one.state == "complete":
            tail = f" exit={one.exit_code}" if one.exit_code is not None else ""
            flag = "  <- the pass returned this, file a register row" if one.exit_code else ""
            lines.append(f"  {one.sha}  complete{tail}{flag}")
        else:
            lines.append(f"  {one.sha}  {one.state}")
            refused.append(one)

    if not results:
        return 1, (
            f"REFUSED. Re-run the citation pass and write it to {deltas}, then "
            "re-run this check.\n"
            f"  No pass file is there at all. On run `batch-170a59` four of six "
            "commits had no pass, and nothing noticed until the finale.\n"
            "  Two roads out:\n"
            "  1. Re-run the pass for each commit, pinned to that commit, and "
            "re-run this check.\n"
            "  2. If this step genuinely made no commit, there is nothing to "
            "check and this call should not have been made." + AFK)

    body = "\n".join(lines)
    if not refused:
        return 0, f"Citation passes, {len(results)} read:\n{body}"

    names = ", ".join(one.sha for one in refused)
    return 1, (
        f"REFUSED. Re-run the citation pass for {names}, pinned to that commit, "
        "and re-run this check.\n"
        f"Citation passes, {len(results)} read:\n{body}\n"
        "  A file with no terminator is a KILLED pass, not a clean one: run "
        "`batch-207704`'s last pass died after 48 lines inside its preamble and "
        "read clean to everything that looked at it.\n"
        "  Two roads out:\n"
        "  1. Re-run the pass for each sha above and re-run this check.\n"
        "  2. If the pass cannot run here, say so where the verdict is written "
        "and file a register row naming the sha. Never record the sweep as "
        "clean." + AFK)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deltas", required=True,
                        help="the run's citation-deltas directory")
    parser.add_argument("--sha", action="append", default=[],
                        help="a commit to read; repeatable. Omit to read all")
    args = parser.parse_args(argv)

    code, text = report(survey(args.deltas, args.sha), args.deltas)
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
