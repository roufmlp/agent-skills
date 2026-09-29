#!/usr/bin/env python3
"""The names of an issue's criteria and invariants, and the names a text cites.

Tracker-tooling issue 13, fix F10 of the audit of 2026-09-23
(`.scratch/tracker-tooling/evidence/audit-2026-09-23-run-time-and-strikes/`).
A strike is bought only on a criterion or an invariant the issue holds, so two
scripts need to read the same names: `retry_brief.py`, which refuses an owed
item that names none, and `charge_round.py`, which refuses a gate grade on a
name the issue does not hold. This file is the one reader both use.

THREE KINDS OF NAME, normalised to one spelling each:

  C3   criterion 3: the third numbered item under `## Acceptance criteria`.
       Written `criterion 3` or `C3`.
  I4   invariant 4: the fourth numbered item under `## Must still be true`.
       Written `invariant 4` or `I4`.
  M9   the issue's own label on a `## Must still be true` item, as some
       trackers write them: `- **M9 — ...`. Written `M9` or `invariant M9`.
       Where the issue writes no such label, `M9` is a second name for I9.

An invariant section that numbers nothing and labels nothing is counted by its
unindented bullets: the third bullet is I3, and M3 too. That is the name a gate
gives it, and without it an issue written in bullets holds no invariant name.

WHAT IS NOT A NAME. `I-1` is the label the verify gate of run `batch-d67136`
wrote for an item it implied, and the issue held no such line. It has a hyphen,
so nothing here reads it, and that is on purpose. A nested numbered line is a
step inside a criterion, not a criterion, so only an unindented `3.` counts.

THE FORMS A CRITERION TAKES. Tracker-tooling issue 26, ruling `q-fin-46e4de-06`
of 2026-09-24: one reader, for `check_issue_ready.py` as well as the two above.
`/to-issues` writes criteria as `- [ ]` bullets and hardening keeps them, so 8
of run `batch-46e4de`'s 12 issues launched with criteria this file read as no
names. Five forms were in use that day:

  1. **One.**                        numbered: C1, from its number
  - [ ] **1. One.**                  a box with a number in bold: C1
  - [ ] **Criterion 1, ground (a).** a box naming its number: C1. The box is
  - **Criterion 1.**                 optional here, as `check_issue_ready` had it
  - [ ] **One.**                     a box and no number: its position, C1
  **1. One.**                        a bold paragraph on its number, read only
                                     where no list form is (a second
                                     tracker's issue 285)

Where any unindented numbered line exists, only numbered lines count, so an
issue that read one way before reads the same way now. Where any box names its
number, only boxes that name one count. A bare `- **Criterion N**` bullet
counts only where the section holds no box: that tracker's 421b keeps a note,
`- **Criterion 4** went to 421e`, above its four unnumbered boxes, which are
C1-C4. The heading may be `##` to `######`; its issue 161 files its
criteria under `### Acceptance criteria`. A plain `- ` bullet is a note, and an
indented box is a step inside a criterion; neither is a criterion. Positional
numbers move when a bullet moves. So do the numbered form's, when an author
renumbers, so the risk is not new.
"""

from __future__ import annotations

import re

# One alternation, so `invariant M9` is read once, as M9, and never also as a
# bare M9. A letter suffix (`criterion 3c`) names a part of criterion 3 and
# reads as C3. The plural names its first number: `criteria 1 and 2` is C1.
CITED = re.compile(
    r"\b(?:(?i:criteri(?:on|a))\s+(?P<c1>\d+)[a-z]?"
    r"|C(?P<c2>\d+)[a-z]?"
    r"|(?i:invariant)\s+M(?P<m1>\d+)"
    r"|(?i:invariant)\s+(?P<i1>\d+)"
    r"|I(?P<i2>\d+)"
    r"|M(?P<m2>\d+))\b")

SECTION = re.compile(r"^(?P<level>#{2,6})\s+(?P<title>[^\n]*)$", re.MULTILINE)
NUMBERED = re.compile(r"^(\d+)\.\s", re.MULTILINE)
# An unindented box, or a bare bullet that names `Criterion N`. The number, where
# the item carries one, is `**1.` or `Criterion 1` straight after the box.
CHECKLIST = re.compile(
    r"^[-*][ \t]+(?:(?P<box>\[[ xX]\])[ \t]+\**(?:Criterion[ \t]+(?P<n>\d+)\b"
    r"|(?P<m>\d+)\.\s)?|\**Criterion[ \t]+(?P<k>\d+)\b)", re.MULTILINE)
# The last form read, where no list form is: a paragraph opening in bold on its
# number, `**1. The bell's number moves ...**` (the second tracker's 285).
BOLD_NUMBERED = re.compile(r"^\*\*(?:Criterion[ \t]+(\d+)\b|(\d+)\.\s)", re.MULTILINE)
# The label opens a list item, after the bullet and any emphasis. A label met
# in running prose -- "issue 94's invariant M8" -- belongs to another issue.
LABEL = re.compile(r"^\s*(?:[-*]|\d+\.)?\s*\**M(\d+)\b", re.MULTILINE)
# An unindented bullet. A nested one is a line inside the item above it.
BULLET = re.compile(r"^[-*][ \t]", re.MULTILINE)


def section(body: str, title: str) -> str:
    """The text under the `## <title>` heading, of any level from two to six,
    up to the next heading of its own level or higher. A deeper heading
    (`### The case table`) is inside the section."""
    headings = list(SECTION.finditer(body or ""))
    matches = [index for index, heading in enumerate(headings)
               if heading.group("title").strip().lower().startswith(title)]
    if not matches:
        return ""
    # The shallowest match wins, so a `### Acceptance criteria, what changed`
    # inside a corrections section never shadows the real `## ` one.
    index = min(matches, key=lambda i: len(headings[i].group("level")))
    level = len(headings[index].group("level"))
    later = [one for one in headings[index + 1:] if len(one.group("level")) <= level]
    return body[headings[index].end():later[0].start() if later else len(body)]


def criteria(body: str) -> list:
    """Each criterion under `## Acceptance criteria`, as (number, its text),
    in any of the forms the docstring lists. Empty where none is readable."""
    text = section(body, "acceptance criteria")
    starts = list(NUMBERED.finditer(text))
    if starts:
        numbers = [start.group(1) for start in starts]
    else:
        starts = list(CHECKLIST.finditer(text))
        if any(start.group("box") for start in starts):
            starts = [start for start in starts if start.group("box")]
        named = [start.group("n") or start.group("m") or start.group("k")
                 for start in starts]
        if any(named):
            starts = [start for start, number in zip(starts, named) if number]
            numbers = [number for number in named if number]
        else:
            numbers = [str(position) for position in range(1, len(starts) + 1)]
        if not starts:
            starts = list(BOLD_NUMBERED.finditer(text))
            numbers = [start.group(1) or start.group(2) for start in starts]
    return [(number, text[start.start():
                          starts[n + 1].start() if n + 1 < len(starts) else len(text)])
            for n, (number, start) in enumerate(zip(numbers, starts))]


def invariant_places(invariants: str) -> list:
    """The invariants' numbers: each numbered item's own number, or, where the
    section numbers none and labels none, each unindented bullet's place,
    counted from 1.

    Issue 232 of run `batch-04dff9` is why a bullet is counted. Its invariants
    are unlabelled bullets, as in 154 of the 255 issues of one tracker measured
    on 2026-09-28, so the issue held no invariant name at all. Both gates named
    them by place, every name was refused, and the review gate's `M8=fail`
    was never charged. A labelled section is not counted: its labels are its
    names, and a place name beside them would be a second name for one item.
    """
    numbered = NUMBERED.findall(invariants)
    if numbered or LABEL.search(invariants):
        return numbered
    return [str(n) for n in range(1, len(BULLET.findall(invariants)) + 1)]


def known_ids(body: str) -> set:
    """Every name the issue holds, read from its two sections alone.

    Where the issue writes no `M` label of its own, `M<n>` is a second name
    for invariant n: see `same_item`.
    """
    invariants = section(body, "must still be true")
    places = invariant_places(invariants)
    labels = LABEL.findall(invariants)
    return ({f"C{number}" for number, _ in criteria(body)}
            | {f"I{n}" for n in places}
            | {f"M{n}" for n in (labels or places)})


def same_item(name: str, body: str) -> str:
    """The one spelling of a held name: `M<n>` is `I<n>` where the issue
    writes no `M` label.

    The gate briefs print `M9` as their example name, and a gate copies it:
    issue 227d of run `batch-e35a25` graded invariant 10 as `M10` at one gate
    and `I10` at the other. One item under two names must be one item, or a
    fail at one gate and a pass at the other is never seen as a split.
    """
    if name[:1] == "M" and not LABEL.search(section(body, "must still be true")):
        return "I" + name[1:]
    return name


def named_ids(text: str) -> list:
    """Every name the text cites, normalised, in the order it cites them."""
    found = []
    for match in CITED.finditer(text or ""):
        kind = next(name for name, value in match.groupdict().items() if value)
        found.append(kind[0].upper() + match.group(kind))
    return found
