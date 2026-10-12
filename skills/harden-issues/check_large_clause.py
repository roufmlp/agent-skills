#!/usr/bin/env python3
"""Refuse a hardened issue whose "no new LARGE line" clause does not name its
exemption: the words "that no written ruling or default keeps".

The human's ruling `q-fin-6f777a-04` of 2026-10-11, in the session walk of that day:
a check in the stamp script, not a sentence in the attacker brief.

    python3 ~/.claude/skills/harden-issues/check_large_clause.py \
        --issue <each file this pass hardened>

**What it was built on.** In one tracker's run `batch-6f777a` a bare "no new LARGE
line" stood against 468 C9, 470 C8 and 474 C7, and struck 470 once. A line that a
written ruling or a recorded default already kept still read as new, so the gate
rejected on it and the runner had to strike the clause by hand
(issue 468, criterion 9).

**The clause.** "no new LARGE line" or "lines", any case, wrapped across lines.
Measured on that tracker 2026-10-11 with

    grep -rhI -i "new LARGE line" --include='*.md' .scratch

which found that spelling and "forbids a new LARGE line" in register prose only,
never in an issue's criteria. A clause spelled outside that list is a finding for
later, not a fault of this check.

**The exemption.** The words must follow the clause inside its own sentence: from
the clause to the next full stop, blank line or list item. Text struck with
`~~...~~` is dropped first, so a struck bare clause beside its rewritten form
passes. Each clause is judged alone; one exempt clause does not carry another.

It reads only the files handed in, so a backlog stamped before 2026-10-11 is not
refused. The hardening pass names each file it is about to stamp.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

EXEMPTION = "that no written ruling or default keeps"
CLAUSE = re.compile(r"\bno\s+new\s+LARGE\s+lines?\b", re.IGNORECASE)
STRUCK = re.compile(r"~~.*?~~", re.DOTALL)
# The clause's sentence ends at a full stop, a blank line or the next list item.
SENTENCE_END = re.compile(r"\.(?=\s|$)|\n[ \t]*\n|\n[ \t]*(?:[-*]|\d+\.)[ \t]")


def faults(text: str) -> list[str]:
    """One fault per clause whose sentence lacks the exemption. Empty is a pass."""
    live = STRUCK.sub("", text)
    found = []
    for clause in CLAUSE.finditer(live):
        end = SENTENCE_END.search(live, clause.end())
        rest = " ".join(live[clause.end():end.start() if end else len(live)].split())
        if EXEMPTION not in rest.lower():
            line = live.count("\n", 0, clause.start()) + 1
            found.append(f"line {line}: \"{' '.join(clause.group(0).split())}\" lacks "
                         f"\"{EXEMPTION}\" in its sentence")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Refuse a hardened issue whose "no new LARGE line" clause names no exemption.',
    )
    parser.add_argument("--issue", required=True, action="append", dest="issues",
                        help="an issue file this pass hardened; repeat for each")
    args = parser.parse_args()

    refused = False
    for one in args.issues:
        path = pathlib.Path(one)
        identifier = re.match(r"^(\d+[a-z]?)-", path.name)
        identifier = identifier.group(1) if identifier else path.name
        try:
            text = path.read_text()
        except OSError as error:
            print(f"REFUSED   {identifier}: unreadable, {error}", file=sys.stderr)
            refused = True
            continue
        found = faults(text)
        if found:
            refused = True
            for fault in found:
                print(f"REFUSED   {identifier}: {fault}", file=sys.stderr)
        else:
            print(f"ok        {identifier}")

    print(f"read {len(args.issues)} issue file(s)")
    if refused:
        print(f"\nREFUSED: no stamp until each clause above reads \"no new LARGE line "
              f"{EXEMPTION}\", each kept line's row citing its id.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
