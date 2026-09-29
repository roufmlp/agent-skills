#!/usr/bin/env python3
"""Refuse an issue file that carries no criteria for a gate to grade.

An implementer is graded against criteria. Where the issue file carries none, the
runner authors them into the spawn prompt, and the run then grades its own
invention. That is not hardening: hardening is an adversarial pass over criteria
before anyone builds, and it happens in a session of its own, off the run's clock.

**Run `bridge-cse`, 2026-08-24, is what this guard exists for.** Its journal, at
`.scratch/<feature>/run-journal.md` on main, records the pre-flight read:
issues 408 and 407 "carry NO acceptance-criteria section at all — they are promoted
register rows with a 'what is wrong' and a remedy direction", so "the runner
therefore authors the graded criteria into the spawn prompts". Two citations in that
authored brief were wrong, they reached a shipped code comment, and repairing them
cost a correction round. The run took 7h49m against an estimate of 3h15m to 4h45m.

**The refusal is cheap, measured before it was built.** Of the 32 issue files reading
`Status: ready-for-agent` on 2026-08-24, exactly ONE carries neither section. This
does not stand between the runner and a hardened backlog. It stands between the
runner and a freshly promoted register row, which is the class that hurt.

Four verdicts:

    graded            a `## Acceptance criteria` section. Passes silently.
    invariants-only   a `## Must still be true` section and no criteria. Passes,
                      and says so. Issue 338 was this shape and still cost two
                      attempts, so it is never silent.
    no-criteria       neither. REFUSED unless the human overrides that issue by id.
    unnamed-criteria  a criteria section in which `criteria_ids.py`, the reader
                      `charge_round.py` also uses, finds no criterion. REFUSED,
                      and the same override clears it. Tracker-tooling issue 26,
                      ruling `q-fin-46e4de-06` of 2026-09-24.

Plus `unreadable`, which refuses and which no override can clear: an override is a
statement about an issue's criteria, and nobody can make one about a file that would
not open.

The human approved this on 2026-08-24, with the override per issue and the cost printed.

This does NOT grade the criteria. A section full of nonsense passes here, and
`/harden-issues` is what attacks the contents. One guard, one fault.

**One more fault, and it is the one shape of criterion this does read: a guard
with no population.** Fix F7 of the audit of 2026-09-23, tracker-tooling issue 22,
under ruling `q-s4-1`. A guard criterion told to read "the whole artefact" names
nothing a build can meet, so every adversarial gate plants one more spelling and
rejects on it. Issue 53 of one project passed every other criterion in all seven
attempts that way; the audit puts 1,665 of 2,687 rejected agent-minutes on 12
guard issues. So a guard criterion carries three lines:

    Forms: `.ts`, `.tsx` under `src/app/`
    Measured by: `<the command that listed them>`
    Outside the list: a form a gate plants that this list does not hold is a
    register row, not a rejection.

    open-guard        a criterion reads like a guard over files, or carries a
                      `Forms:` line, and lacks one of the three. REFUSED, and an
                      override clears it the same way as no-criteria.

**How a guard is recognised, measured, and what it misses.** A path scope and a
refusal word in the same numbered criterion (`GUARD_SCOPE`, `GUARD_WORD`). Over
the 55 `ready-for-agent` files of two projects on 2026-09-23, 269
criteria, it flagged 31, about half of them real guards, and it flagged
guard criteria in each of issues 53, 139, 139c, 151, 152, 45, 146, 92 and 166. A wrong flag
costs one line, `Not a guard: <why>`. A guard worded some other way passes here,
and the hardening attacker's class 4 is the net for it.

**It binds an issue stamped on or after `GUARD_RULE_FROM`.** An older stamp, or no
stamp, prints `GUARD?` and passes: issues 53 and 166 were re-hardened to closed
forms on 2026-09-23 in their own words, before this shape existed, and a run is
already planned for them. `--all-guards` binds every file handed in, and the
hardening pass runs it on the files it is about to stamp.

**Every issue says what it touches.** Tracker-tooling issue 33, rulings Q10 and Q4
of 2026-09-25. Three lines sit under `Sentence:`, and `headers()` is the one
reader of them that every later script imports:

    Touches: `run-issues/`, `lib/*.py`     backticked paths, directories or globs
    Kind: product | machinery. <how it helps every repo>
    Level: light | full

A file lacking one, or carrying a value outside the form, is a header fault. It is
reported beside the criteria verdict, never in place of it, so a file refused for
both prints both. It binds a stamp on or after `HEADER_RULE_FROM`, any file that
carries `Kind:` or `Level:` (a light issue is never hardened, so it never carries a
stamp), and every file under `--all-guards`. An older file carrying none of the
three prints `HEADER?` and passes: one project held 281 issue files on 2026-09-25 and
not one carried the lines. The shape is the open guard's, a refusal from a rule
date and a warning before it, as `q-s4-2` ruled.

**A full issue with a pending default stays out.** Tracker-tooling issue 43b, rule
7 of issue 32 (ruling Q19 of 2026-09-25). A provisional stamp may enter a run,
except a `Level: full` issue whose pending default changes a criterion. The one
mark is ``Default (`q-<pass>-<issue>-<n>`)``, written inside the criterion it
changes (default `q-h0925b-43-1`), and it is read only in the criteria `criteria()`
returns, never in the section's opening paragraph. A mark whose id has an entry in
the project's rulings file, read through `lib/rulings.py`, is ruled and does not
refuse (default `q-h0925b-43-3`). It binds a stamp on or after `PENDING_RULE_FROM`
and warns with `DEFAULT?` before it; `--all-guards` does not reach it, so the
hardening pass can still stamp a full issue provisional (default `q-h0925b-43-4`).
`lib/next_batch.py` reads it through `pending_defaults()` too, so its `/run-issues`
line never names an issue this refuses.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import criteria_ids  # noqa: E402  The one reader of criterion names.

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import rulings  # noqa: E402  The one reader of the project's rulings file.

GRADED = "graded"
INVARIANTS_ONLY = "invariants-only"
NO_CRITERIA = "no-criteria"
# A criteria section `criteria_ids.py` reads no criterion in. Issue 26.
UNNAMED = "unnamed-criteria"
UNREADABLE = "unreadable"
OPEN_GUARD = "open-guard"
# An open guard on a file stamped before the rule. Passes, never silently.
OPEN_GUARD_BEFORE_RULE = "open-guard-before-rule"

# The first stamp date this refusal binds. Ruled `q-s4-1`, 2026-09-23.
GUARD_RULE_FROM = "2026-09-24"
# The first stamp date the header refusal binds: the day issue 33 merged to local
# master, never earlier than 2026-09-26. Ruled `q-h0925-33-4`, 2026-09-25.
HEADER_RULE_FROM = "2026-09-26"
# The first provisional stamp date rule 7 binds: the day issue 43b merged to local
# master. Older stamps warn, as `q-s4-2` and `q-h0925-33-4` ruled.
PENDING_RULE_FROM = "2026-09-27"

# Markdown headings only. A file that merely says "this has no acceptance criteria
# yet" in a sentence must not pass on the strength of the phrase appearing.
CRITERIA_HEADING = re.compile(r"^#{2,6}\s+Acceptance criteria\s*$", re.MULTILINE | re.IGNORECASE)
INVARIANT_HEADING = re.compile(r"^#{2,6}\s+Must still be true\s*$", re.MULTILINE | re.IGNORECASE)

# `402b-correct-the-match.md` -> `402b`. Legacy two-digit ids and lettered slices
# are both real in this tracker.
ID_FROM_NAME = re.compile(r"^(\d+[a-z]?)-")

STAMP = re.compile(r"^Hardened(?: \(provisional\))?:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
# The one pending-default mark, inside the criterion it changes. Issue 43b.
DEFAULT_MARK = re.compile(r"Default \(`(q-[A-Za-z0-9._-]+)`\)")
SECTION = re.compile(r"^(#{2,6})\s+(.*?)\s*$", re.MULTILINE)
# What a guard over files says, measured over 251 criteria on 2026-09-23 (the
# docstring). Both halves must appear in one criterion.
GUARD_SCOPE = re.compile(
    r"\b(?:under|across|anywhere in|every file in|no file in)\s+`[^`\n]*/`"
    r"|\b(?:the|its) (?:source |whole |finished |real )?tree\b"
    r"|\bevery (?:\w+ )?file (?:under|in)\b|\bno (?:other )?file (?:under|in)\b"
    r"|\bbuild[- ]check|\bstatic test|\bwhole artefact",
    re.IGNORECASE,
)
GUARD_WORD = re.compile(r"refus|\breds?\b|\bguard|forbid|allowlist|denylist", re.IGNORECASE)

LABEL = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?(Forms|Measured by|Outside the list|Not a guard):[ \t]*",
    re.MULTILINE | re.IGNORECASE,
)
BACKTICKED = re.compile(r"`[^`\n]+`")

# The three header lines, each read from the first line that opens with its label,
# the way `STAMP` reads `Hardened:`. Issue 32 writes `Touches:` below its title.
TOUCHES_LINE = re.compile(r"^Touches:[ \t]*(.*)$", re.MULTILINE)
KIND_LINE = re.compile(r"^Kind:[ \t]*(.*)$", re.MULTILINE)
LEVEL_LINE = re.compile(r"^Level:[ \t]*(.*)$", re.MULTILINE)
TOKEN = re.compile(r"`([^`\n]+)`")
STRICT_TOUCHES = re.compile(r"^`[^`\s]+`(?:,[ \t]*`[^`\s]+`)*[ \t]*$")
# What ends a wrapped `Touches:` line: a blank line, another header line, a heading.
ENDS_TOUCHES = re.compile(r"^\s*$|^[A-Z][A-Za-z ()-]*:(?:\s|$)|^#")
KIND_FORM = re.compile(r"^(?:product(?![\w-])|machinery(?![\w-]).*[A-Za-z])")
LEVEL_FORM = re.compile(r"^(?:light|full)\s*$")

# The forms a `Touches:` line takes. This check passes `strict` alone; issues 34,
# 35 and 41 read the same answer and apply rules of their own to the others.
STRICT = "strict"
PROSE = "prose"
WRAPPED = "wrapped"
NONE = "none"
NO_TOKEN = "no-token"
NO_LINE = "no-line"

# The `Status:` first words that take an issue out of the open pool, measured by
# issue 35's AC2, plus any `folded-into-<n>`. Issue 35 reads it for open and issue
# 37 for closed. `SATISFIED` in `lib/next_batch.py` stays narrower on purpose: a
# blocker that ended `wontfix` or `split` never delivered its work.
OUT_OF_POOL = frozenset(
    {"done", "closed", "wontfix", "folded", "superseded", "split", "resolved"})
FOLDED_INTO = re.compile(r"^folded-into-\S+$")

COST = (
    "What an override costs, measured on run `bridge-cse`, 2026-08-24: issues 408 "
    "and 407 carried no criteria section, so the runner authored the graded criteria "
    "into the spawn prompts itself. Two citations in that brief were wrong. They "
    "reached a shipped code comment and cost a correction round to remove."
)


@dataclass(frozen=True)
class Row:
    path: pathlib.Path
    identifier: str
    verdict: str
    detail: str
    overridden: bool = False
    # Issue 33's header faults, beside the verdict and never in place of it.
    header_faults: tuple[str, ...] = ()
    header_binds: bool = False
    # Issue 43b's pending defaults, beside the verdict like the header faults.
    pending: tuple[str, ...] = ()
    pending_binds: bool = False

    @property
    def header_refused(self) -> bool:
        return bool(self.header_faults) and self.header_binds

    @property
    def pending_refused(self) -> bool:
        return bool(self.pending) and self.pending_binds


@dataclass(frozen=True)
class Headers:
    """The three header lines of an issue file, as `headers()` reads them.

    `touches` holds the backticked tokens of the `Touches:` line and of each line
    that continues it, in order. `touches_form` names the shape found: `strict`,
    `prose`, `wrapped`, `none`, `no-token` or `no-line`. `kind` and `level` hold
    the text after the label, or None where the file has no such line."""
    touches: tuple[str, ...]
    touches_form: str
    touches_line: str | None
    kind: str | None
    level: str | None


HEADER_SHAPE = (
    "Every issue carries three lines under `Sentence:`, each on one line:\n"
    "    Touches: `run-issues/check_issue_ready.py`, `lib/`, `src/**/*.ts`\n"
    "    Kind: product   or   Kind: machinery. <how the change helps every repo>\n"
    "    Level: light   or   Level: full\n"
    "`Touches:` holds backticked paths, directories ending in `/` or globs, comma "
    "separated, and nothing else. `Level:` is set by hand from the direct road's "
    "classes (money, sign-in, secrets, migrations, row writes) until issue 34's "
    "script sets it."
)

GUARD_SHAPE = (
    "A guard criterion names the population it reads, measured, as three lines inside it:\n"
    "    Forms: `.ts`, `.tsx` under `src/app/`\n"
    "    Measured by: `<the command that listed them>`\n"
    "    Outside the list: a form a gate plants that this list does not hold is a register row, not a rejection.\n"
    "A criterion that is not a guard over files says so: `Not a guard: <why>`."
)


def issue_id(name: str) -> str:
    """The tracker id at the front of an issue filename, or the name itself.

    A file nobody can identify is reported under its own name rather than guessed
    at. An override matches on this string, so a wrong guess here would silently
    apply an override to the wrong issue.
    """
    found = ID_FROM_NAME.match(name)
    return found.group(1) if found else name


def grade(text: str) -> tuple[str, str]:
    if CRITERIA_HEADING.search(text):
        if not criteria(text):
            return UNNAMED, (
                "carries `## Acceptance criteria` but no criterion the charging tool "
                "can name. Write each one as `1.`, `- [ ]`, `- [ ] **1. ...**`, "
                "`- [ ] **Criterion 1 ...**` or a paragraph opening `**1. ...**`. On run `batch-46e4de` eight issues "
                "launched unnamed, and 33b spent an implementation fail as a "
                "criteria reset"
            )
        return GRADED, "carries a graded acceptance-criteria section"
    if INVARIANT_HEADING.search(text):
        return INVARIANTS_ONLY, (
            "carries invariants (`Must still be true`) but no graded criteria. "
            "A gate grades behaviour against criteria; invariants say what must not "
            "move. Issue 338 was this shape on run `bridge-cse` and took two attempts"
        )
    return NO_CRITERIA, (
        "carries neither `## Acceptance criteria` nor `## Must still be true`, so "
        "nothing in the file tells a gate what passing means"
    )


GUARD_COST = (
    "What an override of an open guard costs, measured by the audit of 2026-09-23: "
    "one project's issue 53 was rejected seven times, each time on a spelling a gate planted "
    "outside any population its criterion named, and 12 such issues cost 1,665 of 2,687 "
    "rejected agent-minutes."
)


UNNAMED_COST = (
    "What an override of unnamed criteria costs, measured on run `batch-46e4de`, "
    "2026-09-23: `charge_round.py` refused every grade on such an issue, so every "
    "rejected round took the criteria re-check, and issue 33b spent an implementation "
    "fail as a criteria reset and was blocked one attempt early."
)


HEADER_COST = (
    "What an override of a header fault costs is not measured: no run has met the "
    "rule yet. Issue 33, 2026-09-26. The issue passes with no path a script can "
    "place it by, so issue 41's overlap check cannot see what it touches."
)

HEADER = "header"

PENDING_COST = (
    "What an override of a pending default costs is not measured: no run has met "
    "rule 7 yet. Issue 43b, 2026-09-27. The run builds a full issue's criterion on "
    "a recommendation the human has not ruled."
)

PENDING = "pending"


def cost_of(rows: list[Row]) -> str:
    """The cost line for each kind of override the batch used, and nothing else."""
    kinds = {row.verdict for row in rows if row.overridden}
    if any(row.overridden and row.header_refused for row in rows):
        kinds.add(HEADER)
    if any(row.overridden and row.pending_refused for row in rows):
        kinds.add(PENDING)
    return "\n".join(line for kind, line in (
        (NO_CRITERIA, COST), (UNNAMED, UNNAMED_COST), (OPEN_GUARD, GUARD_COST),
        (HEADER, HEADER_COST), (PENDING, PENDING_COST))
        if kind in kinds)


def criteria(text: str) -> list[tuple[str, str]]:
    """Each criterion under `## Acceptance criteria`, as (number, text).

    `criteria_ids.py` reads them, in every form in use. Tracker-tooling issue 26,
    ruling `q-fin-46e4de-06`: this check had a pattern of its own and the
    charging tool another, so an issue could pass launch while
    `charge_round.py` read its criteria as no names."""
    return criteria_ids.criteria(text)


def labels(body: str) -> dict[str, str]:
    """Each label line's value, running on until the next label or a blank line."""
    found = list(LABEL.finditer(body))
    values = {}
    for n, label in enumerate(found):
        end = found[n + 1].start() if n + 1 < len(found) else len(body)
        values[label.group(1).lower()] = body[label.end():end].split("\n\n")[0]
    return values


def guard_faults(text: str) -> list[str]:
    """One sentence per guard criterion that names no measured population."""
    faults = []
    for number, body in criteria(text):
        values = labels(body)
        if "forms" not in values:
            if "not a guard" in values and values["not a guard"].strip():
                continue
            scope = GUARD_SCOPE.search(body)
            if not (scope and GUARD_WORD.search(body)):
                continue
            faults.append(
                f"criterion {number} reads like a guard over files "
                f"(\"{' '.join(scope.group(0).split())}\") and carries no `Forms:` list"
            )
            continue
        missing = []
        if not BACKTICKED.search(values["forms"]):
            missing.append("a backticked form after `Forms:`")
        if not BACKTICKED.search(values.get("measured by", "")):
            missing.append("`Measured by:` and the command, backticked")
        if "register row" not in " ".join(values.get("outside the list", "").split()).lower():
            missing.append("`Outside the list:` saying a planted form is a register row")
        if missing:
            faults.append(f"criterion {number} carries `Forms:` but lacks " + ", ".join(missing))
    return faults


def headers(text: str) -> Headers:
    """The one reader of `Touches:`, `Kind:` and `Level:`. Issue 33, default
    h0925 Q6: issue 26 was two readers of one section disagreeing."""
    kind = KIND_LINE.search(text)
    level = LEVEL_LINE.search(text)
    found = TOUCHES_LINE.search(text)
    if not found:
        form, tokens, line = NO_LINE, (), None
    else:
        line = found.group(1).strip()
        wrapped = []
        for more in text[found.end():].split("\n")[1:]:
            if ENDS_TOUCHES.match(more):
                break
            wrapped.append(more)
        tokens = tuple(TOKEN.findall(" ".join([line, *wrapped])))
        if line == "none" and not wrapped:
            form = NONE
        elif wrapped:
            form = WRAPPED
        elif not tokens:
            form = NO_TOKEN
        else:
            form = STRICT if STRICT_TOUCHES.match(line) else PROSE
    return Headers(
        touches=tokens,
        touches_form=form,
        touches_line=line,
        kind=kind.group(1).strip() if kind else None,
        level=level.group(1).strip() if level else None,
    )


def header_faults(found: Headers) -> list[str]:
    """One sentence per header line that is missing or outside its form."""
    missing = [label for label, value in (
        ("Touches:", found.touches_line), ("Kind:", found.kind), ("Level:", found.level))
        if value is None]
    faults = ["lacks " + ", ".join(f"`{label}`" for label in missing)] if missing else []
    if found.touches_line is not None and found.touches_form != STRICT:
        faults.append(
            f"`Touches: {found.touches_line}` is {found.touches_form}, not one line of "
            "backticked paths, directories or globs, comma separated")
    if found.kind is not None and not KIND_FORM.match(found.kind):
        if found.kind.startswith("machinery"):
            faults.append(
                f"`Kind: {found.kind}` needs a sentence after `machinery` on how the "
                "change helps every repo")
        else:
            faults.append(f"`Kind: {found.kind}` is neither `product` nor `machinery`")
    if found.level is not None and not LEVEL_FORM.match(found.level):
        faults.append(f"`Level: {found.level}` is neither `light` nor `full`")
    return faults


def header_binds(text: str, found: Headers, all_guards: bool) -> bool:
    """A header fault refuses on `--all-guards`, on a stamp from the rule date, and
    on any file that carries `Kind:` or `Level:`, stamped or not (default h0925
    Q2): issue 40 runs a light issue unhardened, so it never carries a stamp."""
    if all_guards or found.kind is not None or found.level is not None:
        return True
    stamp = STAMP.search(text)
    return bool(stamp) and stamp.group(1) >= HEADER_RULE_FROM


def pending_defaults(path: pathlib.Path, text: str) -> tuple[list[str], bool]:
    """Rule 7's faults for one file, and whether they bind. Issue 43b.

    A fault is a criterion carrying an unruled ``Default (`q-...`)`` mark on a
    `Level: full` issue whose first stamp is `Hardened (provisional)`. They bind
    on a stamp from `PENDING_RULE_FROM`. `lib/next_batch.py` calls this too."""
    stamp = STAMP.search(text)
    if not stamp or not stamp.group(0).startswith("Hardened (provisional)"):
        return [], False
    if headers(text).level != "full":
        return [], False
    marked = [(number, DEFAULT_MARK.findall(body)) for number, body in criteria(text)]
    if not any(ids for _, ids in marked):
        return [], False
    ruled = {entry.question.strip().casefold() for entry in rulings.entries_for(str(path))[0]}
    faults = []
    for number, ids in marked:
        pending = [one for one in ids if one.casefold() not in ruled]
        if pending:
            faults.append(
                f"criterion {number} carries pending default "
                + ", ".join(f"`{one}`" for one in pending)
                + " on a `Level: full` issue stamped `Hardened (provisional)`; rule 7 "
                "holds it out until the human rules")
    return faults, bool(faults) and stamp.group(1) >= PENDING_RULE_FROM


def leaves_pool(status: str) -> bool:
    """Whether a `Status:` value's first word takes the issue out of the open pool."""
    words = status.split()
    word = words[0].lower() if words else ""
    return word in OUT_OF_POOL or bool(FOLDED_INTO.match(word))


def guard_binds(text: str, all_guards: bool) -> bool:
    if all_guards:
        return True
    stamp = STAMP.search(text)
    return bool(stamp) and stamp.group(1) >= GUARD_RULE_FROM


def judge(
    paths: list[pathlib.Path], overrides: set[str], all_guards: bool = False
) -> tuple[bool, list[Row]]:
    rows: list[Row] = []
    for path in paths:
        identifier = issue_id(path.name)
        try:
            text = path.read_text()
        except OSError as error:
            rows.append(Row(path, identifier, UNREADABLE, str(error)))
            continue
        verdict, detail = grade(text)
        if verdict == GRADED:
            faults = guard_faults(text)
            if faults:
                verdict = OPEN_GUARD if guard_binds(text, all_guards) else OPEN_GUARD_BEFORE_RULE
                detail = "; ".join(faults)
        found = headers(text)
        faults = tuple(header_faults(found))
        binds = bool(faults) and header_binds(text, found, all_guards)
        pending, pending_binds = pending_defaults(path, text)
        overridden = identifier in overrides and (
            verdict in (NO_CRITERIA, UNNAMED, OPEN_GUARD) or binds or pending_binds)
        rows.append(Row(path, identifier, verdict, detail, overridden, faults, binds,
                        tuple(pending), pending_binds))

    blocked = [
        row for row in rows
        if (row.verdict in (NO_CRITERIA, UNNAMED, UNREADABLE, OPEN_GUARD)
            or row.header_refused or row.pending_refused)
        and not row.overridden
    ]
    return not blocked, rows


def report(rows: list[Row]) -> None:
    for row in rows:
        if row.verdict == GRADED:
            print(f"ok        {row.identifier}: {row.detail}")
        elif row.verdict == INVARIANTS_ONLY:
            print(f"INVARIANTS {row.identifier}: {row.detail}")
        elif row.verdict == OPEN_GUARD_BEFORE_RULE:
            print(f"GUARD?    {row.identifier}: stamped before {GUARD_RULE_FROM}, so this passes: {row.detail}")
        elif row.overridden:
            print(f"OVERRIDE  {row.identifier}: {row.detail}")
        else:
            print(f"REFUSED   {row.identifier}: {row.detail}", file=sys.stderr)
        if row.header_faults:
            detail = "header " + "; ".join(row.header_faults)
            if not row.header_binds:
                print(f"HEADER?   {row.identifier}: stamped before {HEADER_RULE_FROM}, so this passes: {detail}")
            elif row.overridden:
                print(f"OVERRIDE  {row.identifier}: {detail}")
            else:
                print(f"REFUSED   {row.identifier}: {detail}", file=sys.stderr)
        for fault in row.pending:
            if not row.pending_binds:
                print(f"DEFAULT?  {row.identifier}: stamped before {PENDING_RULE_FROM}, so this passes: {fault}")
            elif row.overridden:
                print(f"OVERRIDE  {row.identifier}: {fault}")
            else:
                print(f"REFUSED   {row.identifier}: {fault}", file=sys.stderr)

    # The total, so a caller who passed one path out of nine can see that it
    # did. This check grades what it is handed and cannot know the batch, so
    # the number it graded on is the only honest thing it can say about its own
    # coverage. Same rule as `rn414a-01` on run `414a-483-286335`: a pass and a
    # pass over nothing must not read the same.
    if any(row.verdict == OPEN_GUARD and not row.overridden for row in rows):
        print(GUARD_SHAPE, file=sys.stderr)
    if any(row.header_refused and not row.overridden for row in rows):
        print(HEADER_SHAPE, file=sys.stderr)

    graded = sum(1 for row in rows if row.verdict in (GRADED, OPEN_GUARD_BEFORE_RULE, OPEN_GUARD))
    print(
        f"read {len(rows)} issue file(s): {graded} carrying acceptance criteria, "
        f"{len(rows) - graded} not"
    )

    if any(row.overridden for row in rows):
        print()
        print(cost_of(rows))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse an issue file that carries no criteria for a gate to grade.",
    )
    parser.add_argument(
        "--issue",
        required=True,
        action="append",
        dest="issues",
        help="path to an issue file; repeat for each issue in the batch",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        dest="overrides",
        help="issue id to run without criteria anyway, e.g. --override 408. Per issue, never batch-wide",
    )
    parser.add_argument(
        "--all-guards",
        action="store_true",
        help=f"refuse an open guard or a header fault whatever the stamp says. Without it "
        f"the refusals bind a stamp on or after {GUARD_RULE_FROM} and {HEADER_RULE_FROM}. "
        f"The hardening pass passes it",
    )
    args = parser.parse_args()

    paths = [pathlib.Path(one) for one in args.issues]
    allowed, rows = judge(paths, set(args.overrides), all_guards=args.all_guards)
    report(rows)

    if allowed:
        return 0
    print(
        "\nREFUSED: run `/harden-issues` over the issues above, or name each one in "
        "an --override with the human's word.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
