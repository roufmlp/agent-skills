#!/usr/bin/env python3
"""Report what the implementer brief cap did during a run.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling 16, 2026-09-08. `~/.claude/hooks/run-issues-brief-cap.py` refuses
a first-attempt implementer brief over its cap, and until this pair shipped it
recorded nothing. A run therefore left no evidence of how often the runner was
refused or what it then cut the brief to, so any later move of the number would
have been an opinion. The hook now appends one JSON line per implementer spawn
it judges; this reads those lines at the finale.

**A MISSING RECORD IS "NO DATA", NEVER "NO REFUSALS".** The record lives in the
machine's temporary directory, because scrub rule H6 of
`~/code/agent-skills/MANIFEST.md` says a published hook writes nothing outside
one. A temporary file can be swept between a refusal and the finale, so its
absence says nothing about what happened. A reader that printed "zero refusals"
there would hand the next reader of ticket 40 a measurement nobody took. A
filter that matches nothing says the same thing for the same reason.

**IT NEVER REFUSES ANYTHING.** It exits 0 on every input, including a record it
cannot parse. It runs at the finale, where a non-zero exit reads as a fault in
the run, and ticket 38 rules that a run never halts.

WHAT IT REPORTS. A count per outcome; the length of every refusal; and the
length of the spawn recorded NEXT after each one -- which is what the runner cut
the brief to, because a re-issued brief is another first attempt. It is the next
spawn recorded and not a proven re-issue: nothing in the record ties two spawns
to the same issue.

    python3 report_brief_cap.py [--tree <path>] [--since <epoch>]

Drill: `test_report_brief_cap.py` beside this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

RECORD_NAME = "run-issues-brief-cap.jsonl"

NO_DATA = (
    "NO DATA. Nothing was read, and that is not the same as no refusals.\n"
    "  The cap's record lives in the machine's temporary directory, so it can "
    "be swept away between a refusal and this report, and a filter can match "
    "nothing that is there.\n"
    "  What this says: nobody took the measurement. It does not say the cap "
    "never fired."
)


def default_record() -> str:
    """The path the hook writes. The two must not drift, so both name it once."""
    return os.path.join(tempfile.gettempdir(), RECORD_NAME)


def read_record(path: str) -> tuple[list[dict], int]:
    """Every readable line, and how many were not. A missing file reads empty."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            raw = handle.read().splitlines()
    except OSError:
        return [], 0
    lines: list[dict] = []
    unreadable = 0
    for line in raw:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            unreadable += 1
            continue
        if isinstance(entry, dict):
            lines.append(entry)
        else:
            unreadable += 1
    return lines, unreadable


def _inside(path: str, root: str) -> bool:
    """True when `path` is `root` or sits under it. A run's worktree counts."""
    if not path:
        return False
    path = os.path.normpath(path)
    root = os.path.normpath(root)
    return path == root or path.startswith(root + os.sep)


def select(lines, tree=None, since=None) -> list[dict]:
    """The lines this report is about, in the order they were written."""
    kept = []
    for entry in lines:
        if tree and not _inside(str(entry.get("cwd") or ""), tree):
            continue
        if since is not None:
            try:
                if float(entry.get("at") or 0) < float(since):
                    continue
            except (TypeError, ValueError):
                continue
        kept.append(entry)
    return kept


def _words(entry) -> int:
    try:
        return int(entry.get("words") or 0)
    except (TypeError, ValueError):
        return 0


def answers(lines) -> list[tuple[int, int | None]]:
    """Each refusal's length, and the length of the spawn recorded next.

    The brief the runner re-issues after a refusal is another first attempt, so
    the NEXT judged spawn is what the refusal became. Reading further than one
    step gets this wrong when the runner is refused twice: pairing the first
    refusal with the eventual pass reports the second as though nothing followed
    it, when in fact the pass did.

    It is the next spawn recorded, not a proven re-issue. Nothing in the record
    ties two spawns to the same issue, and the header says so.
    """
    out: list[tuple[int, int | None]] = []
    for index, entry in enumerate(lines):
        if str(entry.get("outcome") or "") != "refused":
            continue
        following = lines[index + 1] if index + 1 < len(lines) else None
        out.append((_words(entry),
                    _words(following) if following is not None else None))
    return out


def render(lines, unreadable: int) -> str:
    """The report itself. `lines` is already filtered."""
    counts: dict[str, int] = {}
    for entry in lines:
        name = str(entry.get("outcome") or "unnamed")
        counts[name] = counts.get(name, 0) + 1

    caps = sorted({str(entry.get("cap")) for entry in lines
                   if entry.get("cap") is not None},
                  key=lambda text: (len(text), text))
    out = [
        "THE IMPLEMENTER BRIEF CAP, from its own record.",
        f"  spawns judged: {len(lines)}",
        "  " + ", ".join(f"{count} {name}" for name, count in
                         sorted(counts.items(), key=lambda p: (-p[1], p[0]))),
        f"  cap in force: {' and '.join(caps) if caps else 'not recorded'} words",
    ]
    if unreadable:
        out.append(f"  {unreadable} unreadable line(s), skipped")

    pairs = answers(lines)
    if pairs:
        out.append("  what each refusal became (the next spawn recorded):")
        for refused, cut in pairs:
            out.append(f"    {refused} -> {cut}" if cut is not None
                       else f"    {refused} -> nothing followed it in this record")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Report what the implementer brief cap did during a run."
    )
    parser.add_argument("--record", default=None,
                        help="The cap's record. Defaults to the hook's own path.")
    parser.add_argument("--tree", default=None,
                        help="Keep only spawns from this tree or a worktree under it.")
    parser.add_argument("--since", type=float, default=None,
                        help="Keep only spawns at or after this epoch second.")
    args = parser.parse_args(argv)

    lines, unreadable = read_record(args.record or default_record())
    kept = select(lines, tree=args.tree, since=args.since)
    print(render(kept, unreadable) if kept else NO_DATA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
