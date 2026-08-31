#!/usr/bin/env python3
"""Tests for check_harden_branch.py. Run: python3 test_check_harden_branch.py

The overlap this guard refuses happened on 2026-08-24 and is recorded in run
`bridge-cse`'s journal on main. The branch name and the issue numbers below are
that incident, not invented ones.
"""

import unittest

import check_harden_branch as guard

# The real branch, and the four issues it held while the run built the same files.
BRIDGE_CSE = "claude/harden-issues-407-408-ce713b"
TOUCHED = [
    ".scratch/example-feature/harden/407.md",
    ".scratch/example-feature/harden/408.md",
    ".scratch/example-feature/harden/409.md",
    ".scratch/example-feature/harden/338.md",
    ".scratch/example-feature/issues/408-the-create-form-tells-the-operator.md",
]


class ReadsIssueIdsOffPaths(unittest.TestCase):
    def test_an_issue_file(self):
        found = guard.ids_touched([".scratch/example-feature/issues/408-a-thing.md"])
        self.assertEqual(found, {"408"})

    def test_a_harden_note(self):
        found = guard.ids_touched([".scratch/example-feature/harden/338.md"])
        self.assertEqual(found, {"338"})

    def test_a_lettered_slice(self):
        found = guard.ids_touched([".scratch/example-feature/issues/402b-a-thing.md"])
        self.assertEqual(found, {"402b"})

    def test_a_suffixed_harden_note(self):
        """`harden/409-harden-issues-pass.md` is on main today."""
        found = guard.ids_touched([".scratch/example-feature/harden/409-harden-issues-pass.md"])
        self.assertEqual(found, {"409"})

    def test_a_seam_note_names_every_issue_it_spans(self):
        """`harden/seam-407-408-338.md` is a real filename on main. A seam note
        that covers three issues is evidence about all three."""
        found = guard.ids_touched([".scratch/example-feature/harden/seam-407-408-338.md"])
        self.assertEqual(found, {"407", "408", "338"})

    def test_source_files_carry_no_issue_id(self):
        """Only the tracker directories name issues. `src/lib/tenders/repo.ts`
        must never be read as issue 0."""
        self.assertEqual(guard.ids_touched(["src/lib/tenders/repo.ts", "eslint.config.js"]), set())

    def test_the_register_is_not_an_issue(self):
        self.assertEqual(guard.ids_touched([".scratch/example-feature/register.md"]), set())


class JudgesTheBatch(unittest.TestCase):
    def test_the_recorded_overlap_is_refused(self):
        """Run `bridge-cse` built 408, 407, 409 and 338 while this branch held
        hardened copies of all four. The branch merged ten hours after the run."""
        allowed, clashes = guard.judge({"408", "407", "409", "338"}, [(BRIDGE_CSE, TOUCHED)])
        self.assertFalse(allowed)
        self.assertEqual(clashes[0].branch, BRIDGE_CSE)
        self.assertEqual(clashes[0].issues, {"338", "407", "408", "409"})

    def test_a_branch_holding_other_issues_does_not_block(self):
        allowed, clashes = guard.judge({"224"}, [(BRIDGE_CSE, TOUCHED)])
        self.assertTrue(allowed)
        self.assertEqual(clashes, [])

    def test_one_shared_issue_is_enough_to_refuse(self):
        allowed, clashes = guard.judge({"224", "409"}, [(BRIDGE_CSE, TOUCHED)])
        self.assertFalse(allowed)
        self.assertEqual(clashes[0].issues, {"409"})

    def test_no_branches_at_all_passes(self):
        allowed, clashes = guard.judge({"408"}, [])
        self.assertTrue(allowed)
        self.assertEqual(clashes, [])

    def test_a_branch_that_touched_no_tracker_file_passes(self):
        allowed, _ = guard.judge({"408"}, [("claude/harden-issues-empty", ["README.md"])])
        self.assertTrue(allowed)

    def test_every_clashing_branch_is_reported_not_just_the_first(self):
        """A run that fixes one collision and meets a second on the next attempt
        pays the pre-flight twice."""
        second = ("claude/harden-issues-338-abc", [".scratch/example-feature/harden/338.md"])
        allowed, clashes = guard.judge({"408", "338"}, [(BRIDGE_CSE, TOUCHED), second])
        self.assertFalse(allowed)
        self.assertEqual(len(clashes), 2)


class TheRemedyIsNamed(unittest.TestCase):
    def test_the_remedy_says_merge_the_branch(self):
        """A refusal with no road out gets worked around. Merging the hardening
        branch first is the road, and it is cheap: the branch is scratch-only."""
        self.assertIn("merge", guard.REMEDY.lower())

    def test_the_cost_names_the_run_that_earned_it(self):
        self.assertIn("bridge-cse", guard.REMEDY)
        self.assertIn("2026-08-24", guard.REMEDY)


if __name__ == "__main__":
    unittest.main()
