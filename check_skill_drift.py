#!/usr/bin/env python3
"""Refuse two skill files that have stopped agreeing.

`run-issues/SKILL.md` and `parallel-hunt/SKILL.md` are both hand-edited, both
loaded for the length of a run, and both restate the same rules. That is where
drift lives. A rule restated across AGENT BRIEFS is duplicated on purpose --
each brief loads alone into a fresh context, so a shared file would cost a
second read per spawn, and `run-issues/SKILL.md` says so. A rule restated
across the two SKILL.md files has no such excuse.

**The skills audit of 2026-08-22 found eight conflicts, six of them one
shape**: a rule ruled into one skill and never carried to the other. Every one
of them was found by a human reading both files side by side for an afternoon.
Nothing mechanical was watching, and nothing mechanical would have noticed.

So this refuses instead. Two refusals:

    lost        a file no longer holds a rule the catalogue says it must
    stale       a file still holds a claim the catalogue says is false

**It is keyed on TEXT, never on line numbers.** The audit that produced this
catalogue cited lines measured on 2026-08-22, when `run-issues/SKILL.md` held
852 lines. Six standing rules landed the next day and it holds 902, moving
every citation below them by about 34 lines. A line-keyed check would have been
wrong within a day of being written. Each entry below carries the line observed
when it was added, as a reading aid only; nothing here asserts against it.

The needles are deliberately short and deliberately operative. A needle should
be the clause that carries the rule, so that rewording the surrounding prose
does not trip it but deleting the rule does.

An entry blocked on a decision nobody has taken carries `ruling=`. It still
refuses. A guard that stays quiet about a real disagreement because the fix
needs a human is a reminder, and reminders are what this repo replaces.

Exit 0 means the two files still agree. Exit 1 prints every disagreement.

    python3 check_skill_drift.py
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass

RUN_ISSUES = "skills/run-issues/SKILL.md"
PARALLEL_HUNT = "skills/parallel-hunt/SKILL.md"


@dataclass(frozen=True)
class Predicate:
    """One assertion about one file.

    `invariant` is the catalogue id from the skills audit, so a failure leads
    back to the evidence rather than to this file. `note` says what breaks if
    the assertion fails, in the words a session reading the refusal needs.
    `line` is where the needle sat when the entry was written, for reading
    only. `ruling` names the decision an entry waits on, when it waits on one.
    """

    invariant: str
    kind: str  # "present" or "absent"
    path: str
    needle: str
    note: str
    line: int | None = None
    ruling: str | None = None


@dataclass(frozen=True)
class Contradiction:
    """Two files answering the same question with opposite words.

    This is NOT drift. Neither side is measurably false, so a script cannot
    know which one to delete, and encoding a guess as an `absent` predicate
    would quietly take a decision that belongs to a human. What a script CAN
    do is notice that both sides are still standing, and say so with the
    ruling it waits on. It fires while every needle is present, and goes
    quiet when a human deletes one of them.
    """

    invariant: str
    sides: tuple[tuple[str, str], ...]  # (path, needle) per side
    note: str
    ruling: str


# The catalogue. One entry per assertion, grouped by the invariant it grades.
# Sources: `.scratch/skills-audit/2026-08-22-invariants-and-shared-protocol.md`
# in the procurement repo, sections 1 (conflicts C1-C8) and 2 (INV-01..INV-29).
#
# READ THIS BEFORE ADDING AN ENTRY. Six of that audit's eight conflicts were
# already repaired by hand on 2026-08-23, hours after it was written. So most
# of what follows is a REGRESSION GUARD: it does not find a fault today, it
# stops a closed conflict re-opening the next time either file is hand-edited.
# That is the failure mode the audit named -- every rule that went stale in
# this pack went stale in a SKILL.md, never in an agent brief.
CATALOGUE: list[Predicate] = [
    # --- C1. The permission allowlist. Repaired; guarded both ways. The two
    # files word it differently ("THIS round" against "this run"), so they
    # cannot share a needle.
    Predicate(
        "C1", "present", PARALLEL_HUNT,
        "Verify the allowlist, never assert it",
        "parallel-hunt asserted allowlist coverage that run-issues had measured false.",
        line=320,
    ),
    Predicate(
        "C1", "present", PARALLEL_HUNT,
        "Derive the list from the roles THIS round spawns, not from this bullet",
        "The derive-from-roles rule is what stops the bullet going stale.",
        line=331,
    ),
    Predicate(
        "C1", "present", RUN_ISSUES,
        "Verify the allowlist, never assert it",
        "The home of the rule. Two measured stalls are behind it.",
        line=831,
    ),
    Predicate(
        "C1", "present", RUN_ISSUES,
        "Derive the list from the roles this run will spawn, not from this bullet",
        "The derive-from-roles rule, run-issues wording.",
        line=840,
    ),
    # --- C2. Gate isolation. Repaired in two briefs of three. The third entry
    # below FAILS TODAY and is meant to: parallel-hunt-fix-gate.md carries the
    # private-copy sentence but neither the copy-naming clause nor the
    # git-checkout prohibition. Its two siblings carry both.
    Predicate(
        "C2", "present", "agents/parallel-hunt-claim-gate.md",
        "`git checkout -- <path>` to undo a drill",
        "Round 9: a gate wiped four source files while a fixer was mid-edit.",
        line=32,
    ),
    Predicate(
        "C2", "present", "agents/parallel-hunt-fix-gate-critical.md",
        "`git checkout -- <path>` to undo a drill",
        "Same ruling, critical variant.",
        line=33,
    ),
    Predicate(
        "C2", "present", "agents/parallel-hunt-fix-gate.md",
        "`git checkout -- <path>` to undo a drill",
        "FAILS TODAY. The round-9 ruling reached two of the three gate briefs. "
        "This one has the private-copy sentence and neither of the other two "
        "halves. Ruled at parallel-hunt/decisions.md:87-89; never applied here.",
        line=None,
    ),
    Predicate(
        "C2", "present", "agents/parallel-hunt-fix-gate.md",
        "the copy's path names",
        "FAILS TODAY. Same gap: the copy must name the issue and the role, so "
        "two gates cannot collide on one path.",
        line=None,
    ),
    # --- C3. "Every agent file opens with its own idempotency check" was false
    # for three parallel-hunt gates. Repaired. The SKILL.md sentence is only
    # true while all five briefs below hold their check, so they are graded
    # together: the claim and the tree it describes.
    Predicate(
        "C3", "present", PARALLEL_HUNT,
        "Every agent file opens with its own idempotency check",
        "A claim about the tree. The five briefs below are the tree.",
        line=304,
    ),
    Predicate(
        "C3", "present", RUN_ISSUES,
        "Every agent file opens with its own idempotency check",
        "The same claim, run-issues side.",
        line=887,
    ),
    *[
        Predicate(
            "C3", "present", f"agents/parallel-hunt-{role}.md",
            "Read the register first",
            f"Without this, the {role} brief makes the C3 claim false again.",
        )
        for role in (
            "claim-gate", "fix-gate", "fix-gate-critical", "finder", "fixer",
        )
    ],
    # --- C4. The delete-the-claim rule, ruled into parallel-hunt and never
    # applied. Repaired. run-issues words it without "by", so the needle there
    # is the shorter one.
    Predicate(
        "C4", "present", PARALLEL_HUNT,
        "fixed by deleting the claim, never by",
        "Four fix rejections in round 9 were all prose, none a wrong diff.",
        line=99,
    ),
    Predicate(
        "C4", "present", "agents/parallel-hunt-fixer.md",
        "fixed by deleting the claim, never by",
        "The role that applies it.",
        line=39,
    ),
    Predicate(
        "C4", "present", RUN_ISSUES,
        "fixed by deleting the claim, never",
        "The home of the rule.",
        line=479,
    ),
    # --- C5. Both skills said check_verdict.py has three refusals. It has
    # four. Repaired in both, with identical wording.
    Predicate(
        "C5", "present", PARALLEL_HUNT,
        "It has four refusals, not three.",
        "Two gates died at a usage limit and wrote nothing; the fourth refusal "
        "is what notices.",
        line=254,
    ),
    Predicate(
        "C5", "present", RUN_ISSUES,
        "It has four refusals, not three.",
        "Same correction, run-issues side.",
        line=353,
    ),
    # --- C6. parallel-hunt's cron tested "no worker progress", which
    # run-issues had refuted twice in one run. Repaired.
    Predicate(
        "C6", "present", PARALLEL_HUNT,
        "Staleness is a FILE's mtime, never worker progress",
        "The handwritten trigger failed twice in one run, on a runner who had "
        "already diagnosed the failure.",
        line=287,
    ),
    Predicate(
        "C6", "present", RUN_ISSUES,
        "staleness is the FILE's mtime, never a",
        "The home of the refutation.",
        line=705,
    ),
    # --- C7. WAS a genuine contradiction, closed by Abdul's ruling of
    # 2026-08-22: the prohibition is scoped to roles that HAVE an agent file,
    # and each side points at the other. Guard the two SCOPING sentences, not
    # the "never" sentence. Delete either one and the contradiction returns.
    Predicate(
        "C7", "present", RUN_ISSUES,
        'The scope of that prohibition is exactly "roles that HAVE an agent file"',
        "The scoping half. Without it, finale.md's board spawn reads as a breach.",
        line=774,
    ),
    Predicate(
        "C7", "present", "skills/run-issues/finale.md",
        "is the one spawn",
        "The other half of the same ruling: the one spawn with no agent file.",
        line=161,
    ),
    # --- Two line-range citations that the 2026-08-23 edits broke. Both point
    # at a range that now holds an unrelated rule. This is the third recurrence
    # of this class in two days; the audit's own line numbers were the first.
    Predicate(
        "cite-1", "absent", PARALLEL_HUNT,
        "run-issues/SKILL.md:460-468",
        "FAILS TODAY. Cites the delete-the-claim rule, which moved to :479-487. "
        "That range now holds the R1 citation-check paragraph, a different rule.",
        line=107,
    ),
    Predicate(
        "cite-2", "absent", PARALLEL_HUNT,
        "run-issues/SKILL.md:676-682",
        "FAILS TODAY. Cites the mtime refutation, which moved to :705-711. That "
        "range now holds the branch-and-human-gate paragraph.",
        line=292,
    ),
    # --- Section 2 invariants marked Copy with an occurrence in BOTH SKILL.md
    # files. Rows whose second occurrence is an agent brief, a decisions.md or
    # finale.md are excluded: those are duplicated on purpose, because each
    # brief loads alone into a fresh context.
    Predicate(
        "INV-06", "present", PARALLEL_HUNT,
        "A prohibition in a brief names the SYSTEM, not the verb",
        "Three faults in the 2026-08-09 run, quoted in full in both files.",
        line=227,
    ),
    Predicate(
        "INV-06", "present", RUN_ISSUES,
        "A prohibition in a brief names the SYSTEM, not the verb",
        "The home of the incident.",
        line=268,
    ),
    Predicate(
        "INV-07", "present", PARALLEL_HUNT,
        "Creating a worktree includes installing dependencies",
        "A fresh worktree typechecked green with node_modules absent.",
        line=357,
    ),
    Predicate(
        "INV-07", "present", RUN_ISSUES,
        "Creating the worktree includes installing dependencies",
        "The only copy carrying the measurement.",
        line=819,
    ),
    Predicate(
        "INV-08", "present", PARALLEL_HUNT,
        "symlink** to the canonical env file (path in",
        "A copy drifts from the canonical env file within a week.",
        line=363,
    ),
    Predicate(
        "INV-08", "present", RUN_ISSUES,
        "symlink** to the canonical env file (path in",
        "Same rule, run-issues side.",
        line=879,
    ),
    Predicate(
        "INV-09", "present", PARALLEL_HUNT,
        "write *through* the symlink",
        "vercel link and vercel pull write through it and corrupt the original.",
        line=366,
    ),
    Predicate(
        "INV-09", "present", RUN_ISSUES,
        "write *through* the symlink",
        "Same trap, run-issues side.",
        line=882,
    ),
    Predicate(
        "INV-09", "present", RUN_ISSUES,
        "Never edit the canonical file to clean",
        "The extra clause run-issues carries and parallel-hunt does not.",
        line=884,
    ),
    Predicate(
        "INV-14", "present", PARALLEL_HUNT,
        "Spawn prompts carry **only** what varies",
        "Stable instructions live in the agent file, where they cache.",
        line=34,
    ),
    Predicate(
        "INV-14", "present", RUN_ISSUES,
        "Spawn prompts carry **only** what varies",
        "Same rule, run-issues side.",
        line=95,
    ),
    Predicate(
        "INV-27", "present", PARALLEL_HUNT,
        "In **the main checkout**, not any worktree",
        "A brief naming no register path sent two gates to the worktree copy.",
        line=39,
    ),
    # --- C8. Was a contradiction; ruled by Abdul on 2026-08-23. The pinned
    # model name is gone and both files carry the same rule. NOTE: the string
    # "The session model is Opus 5" is still in parallel-hunt/SKILL.md, quoted
    # inside the replacement as the text it retired, so it can never be used as
    # an `absent` needle. Guard the new rule instead.
    Predicate(
        "C8", "present", PARALLEL_HUNT,
        "not evidence of absence, and may not be reported as one",
        "The generalised rule. A weak finder and a clean codebase produce the "
        "same empty register, and nothing downstream catches the difference.",
        line=322,
    ),
    Predicate(
        "C8", "present", RUN_ISSUES,
        "A run on any other tier is still a valid run",
        "The run-issues half of the same rule, which the ruling adopted as the "
        "general one.",
        line=786,
    ),
]

# Opposite answers to one question, both still standing. See Contradiction.
#
# EMPTY, and that is a result. C8 was the one entry here: parallel-hunt pinned
# "The session model is Opus 5" while run-issues permitted any recorded tier.
# Abdul generalised it on 2026-08-23 -- the pin is gone, and both files now
# carry the same rule. The two guards for it sit in CATALOGUE above.
CONTRADICTIONS: list[Contradiction] = []


def read(root: pathlib.Path, relative: str) -> str | None:
    try:
        return (root / relative).read_text()
    except OSError:
        return None


def audit(root, catalogue=None, contradictions=None) -> list[tuple[str, object]]:
    """Every disagreement, in catalogue order.

    A file the catalogue names and disk does not hold is `missing-file`, not a
    silent pass. That case is why this returns the entry rather than a string:
    the caller needs the invariant id to explain itself.
    """
    root = pathlib.Path(root)
    catalogue = CATALOGUE if catalogue is None else catalogue
    contradictions = CONTRADICTIONS if contradictions is None else contradictions
    problems: list[tuple[str, object]] = []
    bodies: dict[str, str | None] = {}

    def body_of(path: str) -> str | None:
        if path not in bodies:
            bodies[path] = read(root, path)
        return bodies[path]

    for predicate in catalogue:
        body = body_of(predicate.path)
        if body is None:
            problems.append(("missing-file", predicate))
            continue
        found = predicate.needle in body
        if predicate.kind == "present" and not found:
            problems.append(("lost", predicate))
        elif predicate.kind == "absent" and found:
            problems.append(("stale", predicate))

    for clash in contradictions:
        standing = all(needle in (body_of(path) or "") for path, needle in clash.sides)
        if standing:
            problems.append(("contradiction", clash))
    return problems


HEADLINE = {
    "lost": "A rule the catalogue says must be here is not here.",
    "stale": "A claim the catalogue says is false is still here.",
    "missing-file": "The catalogue names a file that is not on disk.",
    "contradiction": "Two files answer one question with opposite words.",
}

REMEDY = {
    "lost": (
        "Restore the rule, or amend the catalogue and say in the commit why the "
        "rule stopped applying. Deleting a rule is allowed; deleting it silently "
        "is what this refuses."
    ),
    "stale": (
        "Correct the claim in the file. If the claim is the one that is right and "
        "the catalogue is wrong, amend the catalogue and cite the measurement."
    ),
    "missing-file": "The file moved or went. Fix the catalogue entry or drop it.",
    "contradiction": (
        "Neither side is false, so nothing here may be deleted by a session. "
        "Take the ruling, apply it to both files, then delete the losing needle "
        "from this catalogue. Until then this refusal is the accurate report."
    ),
}


def render(problems) -> str:
    if not problems:
        return "The two skill files still agree."
    lines = [f"REFUSED: {len(problems)} disagreement(s) between the skill files.", ""]
    for kind in ("lost", "stale", "missing-file", "contradiction"):
        hits = [entry for found, entry in problems if found == kind]
        if not hits:
            continue
        lines.append(f"{kind} ({len(hits)}): {HEADLINE[kind]}")
        for entry in hits:
            if kind == "contradiction":
                lines.append(f"    {entry.invariant}")
                for path, needle in entry.sides:
                    lines.append(f"        {path}: {needle!r}")
                lines.append(f"        {entry.note}")
                lines.append(f"        WAITS ON A RULING: {entry.ruling}")
                continue
            where = f" (was line {entry.line})" if entry.line else ""
            lines.append(f"    {entry.invariant}  {entry.path}{where}")
            lines.append(f"        needle: {entry.needle!r}")
            lines.append(f"        {entry.note}")
            if entry.ruling:
                lines.append(f"        WAITS ON A RULING: {entry.ruling}")
        lines.append(f"  {REMEDY[kind]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refuse two drifted skill files.")
    parser.add_argument(
        "--root",
        default=str(pathlib.Path.home() / ".claude"),
        help="Directory holding skills/. Defaults to the live tree, ~/.claude.",
    )
    args = parser.parse_args(argv)

    if not CATALOGUE and not CONTRADICTIONS:
        print(
            "REFUSED empty-catalogue: this guard asserts nothing, so it grades "
            "nothing. An empty catalogue is a green that means no work was done.",
            file=sys.stderr,
        )
        return 2

    problems = audit(args.root)
    if problems:
        print(render(problems), file=sys.stderr)
        return 1
    print(render(problems))
    return 0


if __name__ == "__main__":
    sys.exit(main())
