#!/usr/bin/env python3
"""Tests for find_live_ledger.

The fixtures below have the shape of the twelve ledger copies present on
2026-08-16, reduced to the two lines the selector reads, with the paths made
neutral. Eleven are snapshots; one names the tree it sits in. That shape is the
whole point of the script, so it is the shape the tests pin.
"""

import unittest

from find_live_ledger import (
    Candidate,
    is_admissible_owner,
    parse_worktree_value,
    select_ledger,
)

WT = "/home/user/project/.claude/worktrees"
MAIN = "/home/user/project"


def cand(tree, worktree_line, owner_line, scope=""):
    """One ledger copy, as the selector sees it."""
    return Candidate(
        path=f"{tree}/.scratch/example-feature/run.md",
        tree=tree,
        worktree_line=worktree_line,
        owner_line=owner_line,
        scope_text=scope,
    )


class ParseWorktreeValue(unittest.TestCase):
    def test_strips_the_backticks_the_ledger_writes(self):
        self.assertEqual(parse_worktree_value("Worktree: `/a/b/c`"), "/a/b/c")

    def test_accepts_a_bare_path(self):
        self.assertEqual(parse_worktree_value("Worktree: /a/b/c"), "/a/b/c")

    def test_strips_a_trailing_slash(self):
        self.assertEqual(parse_worktree_value("Worktree: `/a/b/c/`"), "/a/b/c")

    def test_returns_none_when_there_is_no_line(self):
        self.assertIsNone(parse_worktree_value(None))

    def test_returns_none_when_the_value_is_empty(self):
        self.assertIsNone(parse_worktree_value("Worktree: ``"))


class IsAdmissibleOwner(unittest.TestCase):
    def test_a_named_session_is_admissible(self):
        self.assertTrue(is_admissible_owner("Owner: run-issues-batch-0a1b2c"))

    def test_halted_is_admissible_because_a_halt_is_what_resume_resumes(self):
        line = ("Owner: none — HALTED 2026-08-14 02:49. The human stopped the "
                "run and will resume it later.")
        self.assertTrue(is_admissible_owner(line))

    def test_awaiting_merge_is_finished_paperwork(self):
        self.assertFalse(
            is_admissible_owner("Owner: none — awaiting-merge 2026-08-16 13:45")
        )

    def test_merged_is_finished_paperwork(self):
        line = ("Owner: none — **`merged` 2026-08-16 14:00**. The run no longer "
                "owns this tree.")
        self.assertFalse(is_admissible_owner(line))

    def test_a_missing_owner_line_is_not_admissible(self):
        self.assertFalse(is_admissible_owner(None))

    def test_a_bare_none_is_not_admissible(self):
        self.assertFalse(is_admissible_owner("Owner: none"))


class SelectLedger(unittest.TestCase):
    def real_tree(self):
        """The one 2026-08-16 copy whose Worktree: line names its own tree."""
        tree = f"{WT}/run-issues-batch-29bcff"
        return cand(
            tree,
            f"Worktree: `{tree}`",
            "Owner: none — HALTED 2026-08-14 02:49. The human stopped the run.",
        )

    def snapshots(self):
        """Eleven copies naming a tree other than the one they sit in."""
        dc = f"Worktree: `{WT}/run-issues-batch-0a1b2c`"
        t17 = f"Worktree: `{WT}/ticket-17-drafting-c04848`"
        merged = "Owner: none — **`merged` 2026-08-16 14:00**."
        await_ = "Owner: none — awaiting-merge 2026-08-16 13:45."
        return [
            cand(MAIN, dc, merged),
            cand(f"{WT}/bridge-cse_01HR34FKMcAhVdKHerCGmRmd", t17, await_),
            cand(f"{WT}/daily-brief-291c77", dc, await_),
            cand(f"{WT}/harden-issues-360-357-346-574d90", dc, await_),
            cand(f"{WT}/last-run-completion-prod-1e7c27", t17, await_),
            cand(f"{WT}/peaceful-chaum-65ff79", t17, await_),
            cand(f"{WT}/ticket-10-item-9-d4e78c", t17, await_),
            cand(f"{WT}/ticket-17-c4f1f0", t17, await_),
            cand(f"{WT}/ticket-31-0a0403", dc, await_),
            cand(f"{WT}/workflow-audit-build-resume-cde774", dc, await_),
            cand(f"{WT}/workflow-audit-design-pass-c-98a3be", t17, await_),
        ]

    def test_the_real_2026_08_16_tree_yields_exactly_one_path(self):
        chosen, reason = select_ledger(self.snapshots() + [self.real_tree()])
        self.assertEqual(chosen, self.real_tree().path)
        self.assertIsNone(reason)

    def test_a_snapshot_is_never_chosen_even_when_it_is_the_only_copy(self):
        chosen, reason = select_ledger([self.snapshots()[0]])
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_zero_candidates_reports_rather_than_guessing(self):
        chosen, reason = select_ledger([])
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_a_self_naming_copy_whose_run_is_merged_is_not_chosen(self):
        tree = f"{WT}/finished"
        finished = cand(
            tree,
            f"Worktree: `{tree}`",
            "Owner: none — awaiting-merge 2026-08-16 13:45",
        )
        chosen, reason = select_ledger([finished])
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_two_live_candidates_are_split_by_the_issue_range(self):
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        a = cand(a_tree, f"Worktree: `{a_tree}`", "Owner: sess-a",
                 "Scope, as given: **348, 345, 288**.")
        b = cand(b_tree, f"Worktree: `{b_tree}`", "Owner: sess-b",
                 "Scope, as given: **262a, 262b, 266**.")
        chosen, reason = select_ledger([a, b], issues=["348", "345"])
        self.assertEqual(chosen, a.path)
        self.assertIsNone(reason)

    def test_two_live_candidates_with_no_issue_range_refuse_and_report_both(self):
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        a = cand(a_tree, f"Worktree: `{a_tree}`", "Owner: sess-a")
        b = cand(b_tree, f"Worktree: `{b_tree}`", "Owner: sess-b")
        chosen, reason = select_ledger([a, b])
        self.assertIsNone(chosen)
        self.assertIn("run-a", reason)
        self.assertIn("run-b", reason)

    def test_an_issue_range_matching_both_still_refuses(self):
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        scope = "Scope, as given: **348, 345**."
        a = cand(a_tree, f"Worktree: `{a_tree}`", "Owner: sess-a", scope)
        b = cand(b_tree, f"Worktree: `{b_tree}`", "Owner: sess-b", scope)
        chosen, reason = select_ledger([a, b], issues=["348"])
        self.assertIsNone(chosen)
        self.assertIn("run-a", reason)

    def test_an_issue_range_matching_neither_refuses_rather_than_falling_back(self):
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        a = cand(a_tree, f"Worktree: `{a_tree}`", "Owner: sess-a",
                 "Scope, as given: **111**.")
        b = cand(b_tree, f"Worktree: `{b_tree}`", "Owner: sess-b",
                 "Scope, as given: **222**.")
        chosen, reason = select_ledger([a, b], issues=["999"])
        self.assertIsNone(chosen)

    def test_selection_never_consults_a_timestamp(self):
        """One run lost 25 minutes to a ledger chosen because it was freshest."""
        import inspect

        import find_live_ledger

        source = inspect.getsource(find_live_ledger)
        for forbidden in ("getmtime", "st_mtime"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
