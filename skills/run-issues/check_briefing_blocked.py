#!/usr/bin/env python3
"""Refuse a merge briefing that leaves out an issue the run blocked.

    python3 ~/.claude/skills/run-issues/check_briefing_blocked.py \\
        --ledger <run.md> --briefing <merge-briefing.md>

Tracker-tooling issue 40, AC7. `SKILL.md` step 9 orders every blocked issue into
the briefing, and a light issue the cap stops after two attempts is ledgered
`blocked` with the reason `light: two attempts spent` and nothing else carries it
to the human. The rule is every blocked issue, light or full.

WHAT IT READS. Every status-table row, read by header through
`issue_level.status_rows`, whose Status cell's first word is `blocked` in either
case, past emphasis and punctuation: `blocked`, `blocked (criteria)`,
`blocked by 176`, `BLOCKED.` opening a longer cell, `blocked (depends on NN)`.
Those are the forms the ledgers held, measured by AC7's command on 2026-09-25.
A Status cell holding `landed short` counts too (the human, 2026-10-05): that
light issue reads `done` so its dependents run, and this check is what still
carries its unmet criteria to the human.
A Status cell holding `carved` counts too (the human, 2026-10-06):
`done (carved)` shipped part of the issue and `carved (whole)` shipped none of it,
and both owe the human the line saying what was taken out.
Each one's id must appear as a whole token under `finale.md`'s own heading,
`## Skipped or blocked`, up to the next `## ` heading.

Exit 0 every blocked issue is named. Exit 1 one or more is not, each named. Exit
2 nothing could be graded: a file is unreadable or the ledger has no status table.
"""

import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SECTION = re.compile(r"^##\s+Skipped or blocked\s*$", re.MULTILINE | re.IGNORECASE)
NEXT = re.compile(r"^##\s", re.MULTILINE)
LANDED_SHORT = re.compile(r"\blanded short\b|\bcarved\b", re.IGNORECASE)


def _issue_level():
    spec = importlib.util.spec_from_file_location(
        "briefing_issue_level", os.path.join(HERE, "issue_level.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def skipped_section(briefing_text):
    """The body of `## Skipped or blocked`, or None when there is none."""
    found = SECTION.search(briefing_text or "")
    if not found:
        return None
    end = NEXT.search(briefing_text, found.end())
    return briefing_text[found.end():end.start() if end else len(briefing_text)]


def unnamed(ledger_text, briefing_text, levels):
    """`(blocked ids, ids the section does not name)`, or None with no table."""
    rows = levels.status_rows(ledger_text)
    if not rows:
        return None
    blocked = [issue for issue, status in rows
               if levels.status_word(status) == "blocked"
               or LANDED_SHORT.search(status)]
    body = skipped_section(briefing_text) or ""
    missing = [issue for issue in blocked
               if not re.search(rf"(?<![\w.]){re.escape(issue)}(?!\w)", body,
                                re.IGNORECASE)]
    return blocked, missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="path to run.md")
    parser.add_argument("--briefing", required=True, help="merge-briefing.md")
    args = parser.parse_args(argv)
    texts = []
    for path in (args.ledger, args.briefing):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                texts.append(handle.read())
        except OSError as error:
            print(f"check_briefing_blocked: cannot read {path} ({error}). "
                  "Nothing is graded.", file=sys.stderr)
            return 2
    result = unnamed(texts[0], texts[1], _issue_level())
    if result is None:
        print(f"check_briefing_blocked: {args.ledger} holds no status table with "
              "an Issue and a Status column. Nothing is graded.", file=sys.stderr)
        return 2
    blocked, missing = result
    if missing:
        where = ("its `## Skipped or blocked` section"
                 if skipped_section(texts[1]) is not None
                 else "it has no `## Skipped or blocked` section")
        print(f"Refused: the ledger blocks issue(s) {', '.join(missing)}, and the "
              f"briefing does not name them: {where}. Add each one there with "
              "the reason its row gives, then re-run.", file=sys.stderr)
        return 1
    print("every blocked issue is named under `## Skipped or blocked`: "
          + (", ".join(blocked) if blocked else "none was blocked"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
