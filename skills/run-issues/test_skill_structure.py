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
DECISIONS = RUN_ISSUES / "decisions.md"
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

# --- The class-(a) slim -------------------------------------------------------
#
# A review walked SKILL.md for passages that are pure history and mapped them,
# with a warning attached: six other passages read as history and are rules
# wearing narrative clothes, and moving one of those deletes a live rule. Nothing
# refused a move that took the rule away with the story.
#
# These two lists are that refusal.
#
#   SKILL_MARKS      the rule sentence each move must LEAVE BEHIND. Asserted
#                    present in SKILL.md. If a move takes the anchor with the
#                    story, this goes red.
#   DECISIONS_MARKS  the story each move took. Asserted present in decisions.md
#                    AND absent from SKILL.md — the FINALE_MARKS shape above.
#
# **The two lists were written at different times, deliberately.** Every anchor
# went in before one line moved, so the anchor test was already green and already
# watching while the edits happened. A story joined the second list only once it
# had landed in decisions.md. A passage in neither list is one nobody has moved
# yet, not one exempt from the rule.
#
# The target shape for every move is the sentence at "Small-issue coalescing was
# retired": rule loaded, evidence moved, prohibition intact.
SKILL_MARKS = [
    "The launch line is a gate, not an announcement.",
    "Export the live-database variables only when you",
    "A field you cannot fill stops the spawn",
    "**A prohibition in a brief names the SYSTEM, not the verb.**",
    "is what makes that a refusal instead of a silent pass",
    "the repair belongs to the next",
    "a scopeless negative is not",
    "One grep for a distinctive phrase from the deleted sentence.",
    "*Never write that something is the only copy.*",
    "*A recorded cause is tested against a control, never merely observed.*",
    "*Every citation carries its repo-relative path in full, every time.*",
    # No terminal full stop: the move turned this sentence's period into a colon
    # introducing the pointer. The clause is the rule; the punctuation is not.
    "The class survives its own cure",
    "Ledger actuals derive from commit times, full stop.",
    "This paragraph",
    "A ruling that creates work gets its issue number in the same sitting",
    "staleness is the FILE's mtime",
    "Re-derive every fact the run will carry into its spawns, from source",
    "Never pass a",
    "A green produced without dependencies on disk is",
    "It is a floor, not a definition.",
]

DECISIONS_MARKS = [
    "three red suites in one night",
    "picked the blind one and drove a whole acceptance",
    "three files landed at the shared worktree root",
    "175-line verdict",
    "went from 1 broken citation to 251",
    "Two of the first three implementers on",
    "was broken the same night",
    "its twin sat one",
    "asserted an issue file was the only copy",
    "having watched it succeed there",
    "a bare filename used eleven times",
    "transcribed figure off by 960",
    "7 attempts and 14 gate runs where the skill promises three",
    "it was minted then",
    "failed twice in one run, on a runner",
    "the line printed at 22:22",
    "answers null when the count is not one",
    "it moved to `inherit` on 2026-08-02",
    "resolved off a global install",
    "task counter reading 6h 00m 05s",
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


def squash(text):
    """Collapse every run of whitespace to one space.

    The slim's marks are compared against this rather than the raw file. These
    are hard-wrapped markdown documents, so a sentence that fits on one line
    today sits across two the moment anything before it grows by a word — and
    the very edits this test polices are the ones that reflow paragraphs. The
    first move of the slim proved it: the rule sentence survived intact, the line
    break inside it moved, and the raw-substring check called that a deleted
    rule. A guard that goes red on a reflow is a guard somebody switches off.

    FINALE_MARKS and RESUME_MARKS predate this and cope by choosing marks short
    enough to fit one line; they are left alone rather than churned.
    """
    return " ".join(text.split())


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


class TestTheSlimLeftEveryRuleBehind(unittest.TestCase):
    """The class-(a) slim: no relocated rule loses its enforcement point."""

    def test_every_anchor_is_still_in_the_skill(self):
        """The refusal that matters. A move that carried its rule out with the
        story goes red here, and only here — a reader would not notice."""
        skill = squash(read(SKILL))
        for mark in SKILL_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(
                    squash(mark),
                    skill,
                    "a class-(a) move took its rule anchor with it",
                )

    def test_every_moved_story_landed_in_decisions(self):
        decisions = squash(read(DECISIONS))
        for mark in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(squash(mark), decisions)

    def test_no_moved_story_is_still_resident_in_the_skill(self):
        """A move that copies rather than moves saves nothing and doubles the
        maintenance surface."""
        skill = squash(read(SKILL))
        for mark in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(squash(mark), skill)

    def test_the_anchor_list_is_not_empty(self):
        """An empty catalogue is a green that means no work was done."""
        self.assertTrue(SKILL_MARKS)

    def test_no_story_is_listed_as_its_own_anchor(self):
        """The two lists must not intersect: one string cannot be required to be
        present in and absent from the same file."""
        self.assertEqual(set(SKILL_MARKS) & set(DECISIONS_MARKS), set())

    def test_the_model_sentence_is_still_the_model(self):
        """Every move copies this shape, so a later edit that deletes it takes
        the pattern with it."""
        skill = read(SKILL)
        self.assertIn("Small-issue coalescing was retired", skill)
        self.assertIn("`decisions.md` holds the measurement", skill)


class TestTheClassBPassagesWereNotTouched(unittest.TestCase):
    """The six passages marked "moving this deletes a rule".

    They are not anchors of a move — nothing was moved near them. They are listed
    because the slim is the exact edit that would take them, and the next editor
    reading the class-(a) list may not read the warning beside it.
    """

    CLASS_B = [
        # The cron's own justification.
        "cannot prevent a call that was never made",
        # The recoverability test and the standing refusal of the top-tier trials.
        "No value in the effort column was measured against a lower one",
        # The self-commit contingency, stated nowhere else.
        "The runner commits. An implementer never commits its own work",
        "do not revert it — record it and give the gates the range",
        # The orchestrator-cost ruling.
        "Do not go looking for an older number",
        # The halt block as the only resume document.
        "a second copy goes stale",
    ]

    def test_every_class_b_passage_is_still_loaded(self):
        skill = squash(read(SKILL))
        for mark in self.CLASS_B:
            with self.subTest(mark=mark):
                self.assertIn(
                    squash(mark),
                    skill,
                    "this reads as history and is a live rule",
                )


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
