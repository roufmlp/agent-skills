#!/usr/bin/env python3
"""Tests for check_finale_stage.py. Run: python3 test_check_finale_stage.py

This file held nine bare `test_` functions, no runner and no `unittest.main()`
until 2026-08-23. Run the way every sibling test file here is run, it exited 0
having executed none of them, and `pytest` — the runner its docstring named — is
not installed on this machine and is required by no file in the tree. A test file
that reports a pass without running is worse than no test file, so it is a
`unittest.TestCase` now, like its siblings.
"""

import unittest

import check_finale_stage as guard


class CheckFinaleStage(unittest.TestCase):
    def test_reads_a_plain_state_line(self):
        self.assertEqual(guard.read_state("State: finale-board\n"), "finale-board")

    def test_reads_a_decorated_state_line(self):
        """The shape the pilot's own ledger carries, decoration and trailing prose included."""
        text = (
            "Started 2026-08-20 03:03. State: **`awaiting-merge`, reached 15:45.** "
            "All five done.\n"
        )
        self.assertEqual(guard.read_state(text), "awaiting-merge")

    def test_no_state_line_is_not_a_pass(self):
        self.assertIsNone(guard.read_state("Owner: none\n"))
        allowed, reason = guard.judge(None, "awaiting-merge")
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("no-state"))

    def test_the_recorded_fault_is_refused(self):
        """One measured run: promotion still current, awaiting-merge written."""
        allowed, reason = guard.judge("finale-promotion", "awaiting-merge")
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("skips-a-step"))
        self.assertIn("finale-board", reason)

    def test_one_step_forward_passes(self):
        allowed, _ = guard.judge("finale-board", "awaiting-merge")
        self.assertTrue(allowed)

    def test_re_entering_the_same_stage_passes(self):
        """A finale killed inside a stage rewrites that stage on resume."""
        allowed, reason = guard.judge("finale-board", "finale-board")
        self.assertTrue(allowed)
        self.assertIn("re-entering", reason)

    def test_going_backwards_is_refused(self):
        allowed, reason = guard.judge("finale-board", "finale-judgment")
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("goes-backwards"))

    def test_an_unknown_target_is_refused(self):
        allowed, reason = guard.judge("finale-board", "merged")
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("unknown-state"))

    def test_every_adjacent_pair_in_the_chain_passes(self):
        for here, there in zip(guard.CHAIN, guard.CHAIN[1:]):
            allowed, _ = guard.judge(here, there)
            self.assertTrue(allowed, f"{here} -> {there} should pass")


if __name__ == "__main__":
    unittest.main()
