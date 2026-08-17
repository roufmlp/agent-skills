#!/usr/bin/env python3
"""Tests for the shape of run-issues/SKILL.md itself.

Three structural decisions shaped this file, and each one can be undone by an
ordinary edit that looks harmless:

- The finale and the ledger procedure moved off the orchestrator's common load
  path into `finale.md` and `resume.md`. A later edit that pastes either block
  back, or that drops the trigger line pointing at the moved file, breaks the
  split without breaking anything a reader would notice.
- The effort table gained a justification column. A new role row added without
  a justification returns the table to a dial nothing licenses.
- Every citation a skill makes must resolve where the reader is. A
  machine-local absolute path does not resolve on any other machine, and a bare
  filename does not resolve inside a repo tree.

The checks read the live files, not fixtures. That is deliberate: these are
claims about the files as they stand, and a fixture would pass while the real
file drifted.

Run: python3 test_skill_structure.py
"""

import re
import unittest
from pathlib import Path

RUN_ISSUES = Path(__file__).resolve().parent
SKILLS = RUN_ISSUES.parent

SKILL = RUN_ISSUES / "SKILL.md"
FINALE = RUN_ISSUES / "finale.md"
RESUME = RUN_ISSUES / "resume.md"

# Sentences that live inside the finale block and nowhere else. Every one is
# load-bearing prose a reader would miss if the move dropped it.
FINALE_MARKS = [
    "Then a preview deploy, if the project has one.",
    "A published checksum expires the moment the file moves.",
    "Main moved while you worked. Read it before you write a question.",
    "Sweep the register for rows their own issue already fixed.",
    "The thresholds live in the `promotion` agent file and nowhere else.",
    "**Regenerate the action board**",
    "**The post-deploy smoke walk**, owned by `/daily-brief`.",
    "**Recommend follow-ups; start none.**",
]

# The ledger-selection procedure, reduced to one invocation before the move.
RESUME_MARKS = [
    "**Find the right ledger before reading any of it.**",
    "python3 ~/.claude/skills/run-issues/find_live_ledger.py",
    # The refusal semantics. Wrapped over two lines in the source, so the
    # marker stops at the line break.
    "report what it printed in the launch message and spawn nothing",
    "chasing it cost 25 minutes",
    "recreate the cron",
]

EFFORT_ROLES = [
    "run-issues-implementer",
    "run-issues-implementer-escalated",
    "run-issues-verify-gate",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
    "run-issues-finale",
    "promotion",
]


def read(path):
    return path.read_text(encoding="utf-8")


class TestFinaleIsOffTheCommonPath(unittest.TestCase):
    """The finale half of the split."""

    def test_finale_file_exists_beside_the_skill(self):
        self.assertTrue(FINALE.is_file(), f"{FINALE} does not exist")

    def test_every_finale_sentence_survived_the_move(self):
        finale = read(FINALE)
        for mark in FINALE_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(mark, finale)

    def test_the_finale_body_is_no_longer_resident_in_the_skill(self):
        skill = read(SKILL)
        for mark in FINALE_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(mark, skill)

    def test_the_skill_still_carries_the_trigger(self):
        """The instruction to write `finale-mechanical` sits inside the moved
        block, so the trigger has to be on the common path or nothing reads
        the file."""
        skill = read(SKILL)
        self.assertIn("finale-mechanical", skill)
        self.assertIn("finale.md", skill)

    def test_the_trigger_ties_the_ledger_write_to_the_read(self):
        """A pointer that says the file exists is a reminder. The trigger has
        to name both halves in one sentence: the state the runner writes, and
        the file it reads."""
        skill = read(SKILL)
        sentences = re.split(r"(?<=[.:])\s", skill)
        tying = [
            s for s in sentences if "finale-mechanical" in s and "finale.md" in s
        ]
        self.assertTrue(
            tying,
            "no single sentence names both the `finale-mechanical` ledger write "
            "and `finale.md`",
        )


class TestResumeProcedureIsOffTheCommonPath(unittest.TestCase):
    """The ledger half of the split, carrying the script invocation with it."""

    def test_resume_file_exists_beside_the_skill(self):
        self.assertTrue(RESUME.is_file(), f"{RESUME} does not exist")

    def test_every_ledger_sentence_survived_the_move(self):
        resume = read(RESUME)
        for mark in RESUME_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(mark, resume)

    def test_the_ledger_procedure_is_no_longer_resident_in_the_skill(self):
        skill = read(SKILL)
        for mark in RESUME_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(mark, skill)

    def test_the_skill_still_carries_the_resume_trigger(self):
        skill = read(SKILL)
        self.assertIn("resume.md", skill)

    def test_the_script_it_names_is_on_disk(self):
        """The invocation moved citation, not location."""
        self.assertTrue((RUN_ISSUES / "find_live_ledger.py").is_file())


class TestEffortTableCarriesItsEvidence(unittest.TestCase):
    """The justification column."""

    def effort_table(self):
        """The one table whose header names a Stage and an Effort."""
        for block in re.findall(r"(?:^\|.*\n)+", read(SKILL), re.MULTILINE):
            rows = block.strip().splitlines()
            if "Stage" in rows[0] and "Effort" in rows[0]:
                return rows
        self.fail("no effort table found in SKILL.md")

    def cells(self, row):
        return [c.strip() for c in row.strip().strip("|").split("|")]

    def test_the_table_has_a_justification_column(self):
        header = self.cells(self.effort_table()[0])
        self.assertEqual(
            4,
            len(header),
            f"expected Stage, Agent type, Effort and a justification; got {header}",
        )

    def test_every_role_justifies_its_effort(self):
        rows = self.effort_table()[2:]
        seen = {}
        for row in rows:
            cells = self.cells(row)
            for role in EFFORT_ROLES:
                if f"`{role}`" in cells[1]:
                    seen[role] = cells[3] if len(cells) > 3 else ""
        for role in EFFORT_ROLES:
            with self.subTest(role=role):
                self.assertIn(role, seen, f"{role} is not in the effort table")
                self.assertTrue(
                    len(seen[role]) > 10,
                    f"{role}'s justification cell says nothing: {seen[role]!r}",
                )

    def test_downgrade_safety_is_stated_as_recoverability(self):
        """The measured rule: a downgrade is safe where a wrong verdict is
        recoverable, not where the model looks strong enough."""
        skill = read(SKILL).lower()
        self.assertIn("recoverab", skill)


class TestSpawnInstruction(unittest.TestCase):
    """The foreground-spawn rule and the correction that travels with it."""

    def test_the_spawn_instruction_names_run_in_background_false(self):
        """The rule: every run-issues spawn names run_in_background: false,
        because the runner has nothing to do while a worker runs.

        The evidence history matters more than the rule. A 2026-08-17 audit of
        one run blamed eight 17-to-23-minute stalls, 158 minutes, on background
        spawns. The 2026-08-18 re-measure joined each spawn to its subagent
        transcript and refuted that: a task notification woke the runner within
        seconds of every completion, and the gaps were the workers' own
        runtimes. The field stays on the spawn tool's own guidance and saves no
        measured clock; a PreToolUse hook can enforce it mechanically where the
        harness supports one. This test pins the text that tells the runner
        why.
        """
        self.assertIn(
            "run_in_background: false",
            read(SKILL),
            "SKILL.md must name the field so a runner cannot drift back to "
            "the background default unnoticed.",
        )

    def test_the_reason_travels_with_the_instruction(self):
        """A bare field is a value a later edit flips back without noticing.

        Two facts must sit next to the field. The cron is a usage-limit resume,
        not the pacemaker: its one real rescue was a spawn the runner announced
        and never made. And the original 158-minute stall claim was refuted on
        2026-08-18. Both travel with the field so a later editor inherits the
        correction rather than the myth.
        """
        text = read(SKILL)
        start = text.index("run_in_background: false")
        window = text[max(0, start - 1200):start + 1200].lower()
        self.assertIn("cron", window)
        self.assertIn("refuted", window)


class TestCitationsResolveAnywhere(unittest.TestCase):
    """Every path a published skill cites must resolve where the reader is.

    A machine-local absolute path (`/Users/...`, `/home/...`) resolves only on
    the author's machine. The pack allows home-relative `~/.claude/...` paths,
    because that is where it installs, and repo-relative runtime paths like
    `.scratch/<feature>/`.
    """

    def files(self):
        return sorted(SKILLS.glob("*/SKILL.md")) + [FINALE, RESUME]

    def test_no_skill_cites_a_machine_local_absolute_path(self):
        for path in self.files():
            if not path.is_file():
                continue
            text = read(path)
            for prefix in ("/Users/", "/home/"):
                with self.subTest(path=f"{path.parent.name}/{path.name}",
                                  prefix=prefix):
                    self.assertNotIn(
                        prefix,
                        text,
                        "a machine-local absolute path resolves on no other "
                        "machine; cite a home-relative or repo-relative path",
                    )


if __name__ == "__main__":
    unittest.main()
