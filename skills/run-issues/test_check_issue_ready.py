#!/usr/bin/env python3
"""Tests for check_issue_ready.py. Run: python3 test_check_issue_ready.py

The run this guard exists for is `bridge-cse`, 2026-08-24. Its ledger and journal
are on main. The cases below quote it rather than inventing shapes.
"""

import pathlib
import tempfile
import unittest

import check_issue_ready as guard


def write(directory: pathlib.Path, name: str, body: str) -> pathlib.Path:
    path = directory / name
    path.write_text(body)
    return path


class ReadsTheIssueId(unittest.TestCase):
    def test_a_plain_number(self):
        self.assertEqual(guard.issue_id("408-the-create-form-tells-the-operator.md"), "408")

    def test_a_lettered_slice(self):
        """A live tracker mints these constantly: 402b, 146b, 224c."""
        self.assertEqual(guard.issue_id("402b-correct-the-match.md"), "402b")

    def test_a_two_digit_legacy_id(self):
        self.assertEqual(guard.issue_id("07-email-oauth-channel.md"), "07")

    def test_a_name_with_no_leading_id_is_its_own_id(self):
        """Never guess. A file nobody can identify is reported under its own name."""
        self.assertEqual(guard.issue_id("primer.md"), "primer.md")


class GradesTheCriteriaSection(unittest.TestCase):
    def test_graded_criteria_pass(self):
        """Issue 409's shape: a `## Acceptance criteria` section."""
        verdict, _ = guard.grade("# Issue\n\n## Acceptance criteria\n\n1. A thing.\n")
        self.assertEqual(verdict, guard.GRADED)

    def test_invariants_alone_are_allowed_and_named(self):
        """Issue 338's shape. The journal calls it the closest thing to criteria
        in that batch, and it still cost two attempts. Allowed, never silent."""
        verdict, _ = guard.grade("# Issue\n\n## Must still be true\n\n- A thing.\n")
        self.assertEqual(verdict, guard.INVARIANTS_ONLY)

    def test_neither_section_is_refused(self):
        """Issues 408 and 407: promoted register rows with a fault and a remedy
        direction, and no criteria at all."""
        verdict, _ = guard.grade("# Issue\n\n## What is wrong\n\n## Remedy direction\n")
        self.assertEqual(verdict, guard.NO_CRITERIA)

    def test_the_heading_must_be_a_heading(self):
        """A sentence mentioning acceptance criteria is not a section of them."""
        verdict, _ = guard.grade("# Issue\n\nThis file has no acceptance criteria yet.\n")
        self.assertEqual(verdict, guard.NO_CRITERIA)

    def test_a_deeper_heading_still_counts(self):
        """`### Acceptance criteria` under a parent section is the same section."""
        verdict, _ = guard.grade("# Issue\n\n### Acceptance criteria\n\n1. A thing.\n")
        self.assertEqual(verdict, guard.GRADED)


class JudgesABatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_ready_batch_passes(self):
        write(self.dir, "409-a.md", "## Acceptance criteria\n1. A thing.\n")
        write(self.dir, "338-b.md", "## Must still be true\n- A thing.\n")
        allowed, rows = guard.judge([self.dir / "409-a.md", self.dir / "338-b.md"], set())
        self.assertTrue(allowed)
        self.assertEqual([row.verdict for row in rows], [guard.GRADED, guard.INVARIANTS_ONLY])

    def test_one_bad_file_refuses_the_batch(self):
        write(self.dir, "409-a.md", "## Acceptance criteria\n1. A thing.\n")
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, rows = guard.judge([self.dir / "409-a.md", self.dir / "408-b.md"], set())
        self.assertFalse(allowed)
        self.assertEqual(rows[1].verdict, guard.NO_CRITERIA)

    def test_an_override_lets_one_issue_through_and_stays_named(self):
        """The human's rule: the override is per issue and it prints what it costs.
        A batch-wide `--override` with no id would defeat the whole guard."""
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, rows = guard.judge([self.dir / "408-b.md"], {"408"})
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.NO_CRITERIA)
        self.assertTrue(rows[0].overridden)

    def test_an_override_for_an_issue_not_in_the_batch_does_not_pass_it(self):
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, _ = guard.judge([self.dir / "408-b.md"], {"407"})
        self.assertFalse(allowed)

    def test_an_unreadable_file_is_refused_not_assumed(self):
        allowed, rows = guard.judge([self.dir / "no-such-issue.md"], set())
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.UNREADABLE)

    def test_an_unreadable_file_cannot_be_overridden(self):
        """An override says "I know this issue has no criteria". It cannot say
        anything about a file nobody could read."""
        allowed, rows = guard.judge([self.dir / "412-gone.md"], {"412"})
        self.assertFalse(allowed)
        self.assertFalse(rows[0].overridden)


class TheCostLineIsMeasured(unittest.TestCase):
    def test_the_cost_names_the_run_that_earned_it(self):
        """A rule outlives its incident, and a later editor who meets the rule
        with no measurement deletes it as ceremony."""
        self.assertIn("bridge-cse", guard.COST)
        self.assertIn("2026-08-24", guard.COST)

    def test_the_cost_names_the_damage_rather_than_a_feeling(self):
        self.assertIn("correction round", guard.COST)


if __name__ == "__main__":
    unittest.main()
