#!/usr/bin/env python3
"""Refuse a hardened issue that has not said which of its writes can overlap
another write on the same record, and what rule holds between them.

The human's ruling `q-fin-671b22-04` of 2026-10-06, in the merge walk of run
`batch-671b22`: one general check, not one refusal per fault class found. "Add a
check but it should be general i dont want to add each time i face issue one by
one."

    python3 ~/.claude/skills/harden-issues/check_overlap_rule.py \
        --issue <each file this pass hardened>

**What it was built on.** One tracker's issue 370, a credit Undo, spent four
attempts and two criteria resets in that run. Every rejection fell in one class, two
writes on the same job at the same moment: an Undo against an Accept, a Confirm,
a decline or a second Undo. Both strike-2 re-checks found the criteria short of a
bounded overlap rule, not the code short of a fix. Each gate found one more
writer or one more reader the criterion had never named, and rejected on it
(the run's merge briefing, "370, read against its verdicts").

**The shape.** Every issue this pass hardens carries a `## Overlapping writes`
section, and it holds one of two answers:

    ## Overlapping writes

    - None: <why no write this issue adds can meet another on one record>

or one bullet per criterion that adds such a write, `- Criterion 2, the credit
Undo.` (or `- C2, ...`). Each criterion it names carries four labelled lines:

    Writers: <every other write that can land on the same record meanwhile>
    Readers: <the reads the rule binds>
    Loser sees: <what the write that loses the overlap answers, and what it saved>
    Outside the list: a writer or reader a gate finds that this list does not
    name is a register row, not a rejection.

The last line is the bound, the shape ruling `q-s4-1` gave a guard's `Forms:`
list on 2026-09-23. Without it the list is open and every gate can plant one more
interleaving, which is exactly what 370's four attempts did.

**Why a missing section refuses, whatever the issue says.** A check that looked
for write-shaped words (undo, cancel, approve) would be a list of forbidden
spellings, and an issue worded some other way would pass it green
(`~/.claude/coderules.md`: a guard reads the whole artefact and refuses what it
cannot place). So the section is owed by every hardened issue, and `None:` is the
cheap answer for one that writes nothing another write can meet. It must give a
reason of four words or more, so a bare `None.` cannot wave it through.

**What it does not judge.** Whether a `None:` is true, and whether a `Writers:`
list is complete. Those are the attacker's class 12 and the seam agent's, which
read the code and the sibling issues. This check refuses the issue that has not
answered at all, and the answer that is missing a part.

It reads only the files handed in, so a backlog stamped before 2026-10-06 is not
refused. The hardening pass names each file it is about to stamp.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "run-issues"))

from check_issue_ready import criteria  # noqa: E402  One reader of criteria for both skills.

SECTION = re.compile(r"^#{2,6}[ \t]+Overlapping writes[ \t]*$", re.MULTILINE | re.IGNORECASE)
NEXT_HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)
NONE_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?None\b[:.]?[ \t]*(?P<why>.*)$", re.MULTILINE)
# Four words is the least a reason can be: "it writes no row".
REASON_WORDS = 4
REFERENCE = re.compile(r"(?i:\bcriterion)[ \t]+(\d+[a-z]?)\b|\bC(\d+[a-z]?)\b")

LABELS = ("Writers", "Readers", "Loser sees", "Outside the list")
LABEL = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?(" + "|".join(LABELS) + r"):[ \t]*",
    re.MULTILINE | re.IGNORECASE,
)
# Any of these three marks a criterion as one that carries an overlap rule.
# `Outside the list:` alone does not: a guard's `Forms:` block uses it too.
RULE_LABELS = ("writers", "readers", "loser sees")
NO_WRITER = re.compile(r"^(?:none|nothing|no other writes?|n/?a)\W*$", re.IGNORECASE)

SHAPE = (
    "\nThe shape (SKILL.md, class 12):\n\n"
    "    ## Overlapping writes\n\n"
    "    - None: <why no write this issue adds can meet another on one record>\n\n"
    "  or `- Criterion N, <the write>.` per criterion, and inside that criterion:\n\n"
    "    Writers: <every other write that can land on the same record meanwhile>\n"
    "    Readers: <the reads the rule binds>\n"
    "    Loser sees: <what the losing write answers, and what it saved>\n"
    "    Outside the list: a writer or reader a gate finds that this list does not\n"
    "    name is a register row, not a rejection."
)


def section(text: str) -> str | None:
    """The `## Overlapping writes` section's body, or None where there is none."""
    found = SECTION.search(text)
    if not found:
        return None
    following = NEXT_HEADING.search(text, found.end())
    return text[found.end():following.start() if following else len(text)]


def labels(body: str) -> dict[str, str]:
    """Each label's value, running on until the next label or a blank line."""
    found = list(LABEL.finditer(body))
    values = {}
    for n, label in enumerate(found):
        end = found[n + 1].start() if n + 1 < len(found) else len(body)
        values[label.group(1).lower()] = " ".join(body[label.end():end].split("\n\n")[0].split())
    return values


def rule_faults(number: str, values: dict[str, str]) -> list[str]:
    """What a named criterion's overlap rule is missing."""
    missing = [f"`{label}:`" for label in LABELS[:3] if not values.get(label.lower())]
    faults = []
    if missing:
        faults.append(f"criterion {number} lacks {', '.join(missing)}")
    if values.get("writers") and NO_WRITER.match(values["writers"]):
        faults.append(f"criterion {number}'s `Writers:` names no other write; "
                      "an issue with none answers `None:` in the section")
    if "register row" not in values.get("outside the list", "").lower():
        faults.append(f"criterion {number} lacks `Outside the list:` saying a writer "
                      "or reader a gate finds outside it is a register row")
    return faults


def faults(text: str) -> list[str]:
    """Every reason this issue's overlap answer is refused. Empty is a pass."""
    body = section(text)
    if body is None:
        return ["no `## Overlapping writes` section: name each criterion that adds a write "
                "another write can overlap, or say `None:` and why"]
    held = dict(criteria(text))
    named = list(dict.fromkeys(one or two for one, two in REFERENCE.findall(body)))
    nones = [match.group("why") for match in NONE_LINE.finditer(body)]
    found = []
    if nones and named:
        found.append(f"the section says `None:` and names criterion {', '.join(named)}")
    elif nones:
        if len(re.findall(r"[A-Za-z]+", nones[0])) < REASON_WORDS:
            found.append("`None:` gives no reason: say why no write this issue adds "
                         "can meet another on one record")
    elif not named:
        found.append("the `## Overlapping writes` section names no criterion and says no `None:`")
    for number in named:
        if number not in held:
            found.append(f"the section names criterion {number}, which this issue does not hold")
        else:
            found += rule_faults(number, labels(held[number]))
    for number, criterion in held.items():
        values = labels(criterion)
        if number not in named and any(label in values for label in RULE_LABELS):
            found.append(f"criterion {number} carries `Writers:`, `Readers:` or `Loser sees:` "
                         "and the section does not name it")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a hardened issue whose overlapping writes are not named and bounded.",
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
        print("\nREFUSED: no stamp until each issue above answers its overlapping writes."
              + SHAPE, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
