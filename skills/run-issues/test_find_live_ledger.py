#!/usr/bin/env python3
"""Tests for find_live_ledger.

The fixtures below have the shape of the twelve ledger copies present on
2026-08-16, reduced to the two lines the selector reads, with the paths made
neutral. Eleven are snapshots; one names the tree it sits in. That shape is the whole point of the script, so it is the
shape the tests pin.
"""

import sys
import unittest

from find_live_ledger import (
    Candidate,
    collect_candidates,
    is_admissible_owner,
    journal_for,
    live_ledgers,
    overlapping,
    parse_scope_argument,
    parse_scope_ids,
    hunts,
    parse_worktree_value,
    runs,
    select_ledger,
    tree_of,
)

WT = "/home/user/project/.claude/worktrees"
MAIN = "/home/user/project"
# The worktree list as `git worktree list` prints it: main first. Every tree a
# test names below is in it, so ownership can be decided without a filesystem.
TREES = [MAIN] + [f"{WT}/{name}" for name in (
    "run-issues-batch-29bcff", "resumed-session-3c1f0b", "daily-brief-291c77",
    "harden-issues-360-357-346-574d90", "last-run-completion-prod-1e7c27",
    "peaceful-chaum-65ff79", "ticket-10-item-9-d4e78c", "ticket-17-c4f1f0",
    "ticket-31-0a0403", "workflow-audit-build-resume-cde774",
    "workflow-audit-design-pass-c-98a3be", "run-a", "run-b", "run-c", "harden-issues-xyz",
    "run-issues-batch-b3f7a1", "previous-run-7b21ac", "other-run-aaaaaa", "finished",
    "elsewhere",
)]


def cand(tree, worktree_line, owner_line, scope="", batch="batch-000000"):
    """One ledger copy, as the selector sees it."""
    return Candidate(
        path=f"{tree}/.scratch/example-feature/runs/{batch}/run.md",
        tree=tree,
        worktree_line=worktree_line,
        owner_line=owner_line,
        scope_text=scope,
        batch=batch,
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

    def test_the_word_halted_inside_finished_prose_is_not_a_halt(self):
        """Owner lines are prose. Only a line that IS a halt is live."""
        line = ("Owner: none — awaiting-merge 2026-09-01 10:00, after the halted "
                "finale was revived by hand.")
        self.assertFalse(is_admissible_owner(line))

    def test_halted_in_bold_or_backticks_is_still_a_halt(self):
        self.assertTrue(is_admissible_owner("Owner: none — **HALTED** 2026-09-01 10:00"))
        self.assertTrue(is_admissible_owner("Owner: none - `halted` 2026-09-01"))


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
            cand(f"{WT}/resumed-session-3c1f0b", t17, await_),
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
        chosen, reason = select_ledger(
            self.snapshots() + [self.real_tree()],
            cwd=self.real_tree().tree, worktrees=TREES)
        self.assertEqual(chosen, self.real_tree().path)
        self.assertIsNone(reason)

    def test_a_snapshot_is_never_chosen_even_when_it_is_the_only_copy(self):
        chosen, reason = select_ledger([self.snapshots()[0]], cwd=MAIN, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_zero_candidates_reports_rather_than_guessing(self):
        chosen, reason = select_ledger([], cwd=MAIN, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_a_self_naming_copy_whose_run_is_merged_is_not_chosen(self):
        tree = f"{WT}/finished"
        finished = cand(
            tree,
            f"Worktree: `{tree}`",
            "Owner: none — awaiting-merge 2026-08-16 13:45",
        )
        chosen, reason = select_ledger([finished], cwd=tree, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_two_live_runs_and_a_cwd_inside_one_worktree_pick_that_run(self):
        """Ticket 38, ruling 11: resume keys on the current directory."""
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        a = main_cand(f"Worktree: `{a_tree}`", "Owner: sess-a", batch="batch-aaaaaa")
        b = main_cand(f"Worktree: `{b_tree}`", "Owner: sess-b", batch="batch-bbbbbb")
        chosen, reason = select_ledger([a, b], cwd=f"{a_tree}/src/app", worktrees=TREES)
        self.assertEqual(chosen, a.path)
        self.assertIsNone(reason)

    def test_from_the_main_checkout_it_lists_the_live_runs_by_batch_and_stops(self):
        a_tree, b_tree = f"{WT}/run-a", f"{WT}/run-b"
        a = main_cand(f"Worktree: `{a_tree}`", "Owner: sess-a", batch="batch-aaaaaa")
        b = main_cand(f"Worktree: `{b_tree}`", "Owner: sess-b", batch="batch-bbbbbb")
        chosen, reason = select_ledger([a, b], cwd=MAIN, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("batch-aaaaaa", reason)
        self.assertIn("batch-bbbbbb", reason)
        self.assertIn("2 live", reason)

    def test_a_cwd_in_a_tree_no_live_run_owns_refuses_and_lists(self):
        a_tree = f"{WT}/run-a"
        a = main_cand(f"Worktree: `{a_tree}`", "Owner: sess-a", batch="batch-aaaaaa")
        chosen, reason = select_ledger([a], cwd=f"{WT}/harden-issues-xyz", worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("batch-aaaaaa", reason)

    def test_one_live_run_is_still_not_picked_from_the_main_checkout(self):
        """One run is not a special case: the directory decides, never the count."""
        a_tree = f"{WT}/run-a"
        a = main_cand(f"Worktree: `{a_tree}`", "Owner: sess-a", batch="batch-aaaaaa")
        chosen, reason = select_ledger([a], cwd=MAIN, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("batch-aaaaaa", reason)

    def test_a_snapshot_in_the_cwd_tree_is_never_picked(self):
        """A frozen copy that sits in cwd's tree but names another tree stays a snapshot."""
        here = f"{WT}/harden-issues-xyz"
        snap = cand(here, f"Worktree: `{WT}/run-a`", "Owner: sess-a", batch="batch-aaaaaa")
        chosen, reason = select_ledger([snap], cwd=here, worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("no live ledger", reason.lower())

    def test_selection_never_consults_a_timestamp(self):
        """One run lost 25 minutes to a ledger chosen because it was freshest."""
        import inspect

        import find_live_ledger

        source = inspect.getsource(find_live_ledger)
        for forbidden in ("getmtime", "st_mtime"):
            self.assertNotIn(forbidden, source)



# 2026-08-19: the rule and the convention had drifted apart. `SKILL.md` puts
# the ledger in the MAIN checkout, and its `Worktree:` line names the run's own
# tree, so "the copy that names the tree it sits in" matched nothing and a live
# run refused to resume. The `Worktree:` line still says which run owns the
# ledger; it stopped saying where the ledger lives. Both shapes are live now.

def main_cand(worktree_line, owner_line, scope="", batch="batch-000000"):
    """The live copy as runs write it today: in the main checkout."""
    return Candidate(
        path=f"{MAIN}/.scratch/example-feature/runs/{batch}/run.md",
        tree=MAIN,
        worktree_line=worktree_line,
        owner_line=owner_line,
        scope_text=scope,
        is_main=True,
        batch=batch,
    )


MERGED = "Owner: none — MERGED to local main 2026-08-18 by `/daily-brief`."
LIVE = "Owner: run-issues session (0a1b2c)"


class MainCheckoutCopy(unittest.TestCase):
    def test_selects_the_main_checkout_copy_that_names_the_run_worktree(self):
        candidates = [
            main_cand(f"Worktree: `{WT}/run-issues-batch-b3f7a1`", LIVE),
            cand(f"{WT}/run-issues-batch-b3f7a1",
                 f"Worktree: `{WT}/previous-run-7b21ac`", MERGED),
            cand(f"{WT}/daily-brief-b2d0c6",
                 f"Worktree: `{WT}/previous-run-7b21ac`", MERGED),
        ]
        path, reason = select_ledger(
            candidates, cwd=f"{WT}/run-issues-batch-b3f7a1", worktrees=TREES)
        self.assertIsNone(reason)
        self.assertEqual(
            path, f"{MAIN}/.scratch/example-feature/runs/batch-000000/run.md")

    def test_a_merged_main_checkout_copy_is_finished_paperwork(self):
        candidates = [main_cand(f"Worktree: `{WT}/previous-run-7b21ac`", MERGED)]
        path, reason = select_ledger(
            candidates, cwd=f"{WT}/previous-run-7b21ac", worktrees=TREES)
        self.assertIsNone(path)
        self.assertIn("No live ledger", reason)

    def test_a_copy_naming_its_own_tree_is_still_live(self):
        candidates = [
            main_cand(f"Worktree: `{WT}/previous-run-7b21ac`", MERGED),
            cand(f"{WT}/run-issues-batch-b3f7a1",
                 f"Worktree: `{WT}/run-issues-batch-b3f7a1`", LIVE),
        ]
        path, reason = select_ledger(
            candidates, cwd=f"{WT}/run-issues-batch-b3f7a1", worktrees=TREES)
        self.assertIsNone(reason)
        self.assertEqual(
            path,
            f"{WT}/run-issues-batch-b3f7a1/.scratch/example-feature/runs/batch-000000/run.md")

    def test_two_live_copies_from_the_main_checkout_list_both(self):
        candidates = [
            main_cand(f"Worktree: `{WT}/run-issues-batch-b3f7a1`", LIVE,
                      batch="batch-b3f7a1"),
            cand(f"{WT}/other-run-aaaaaa",
                 f"Worktree: `{WT}/other-run-aaaaaa`", LIVE, batch="batch-aaaaaa"),
        ]
        path, reason = select_ledger(candidates, cwd=MAIN, worktrees=TREES)
        self.assertIsNone(path)
        self.assertIn("2 live ledgers", reason)
        self.assertIn("batch-b3f7a1", reason)
        self.assertIn("batch-aaaaaa", reason)


# 2026-09-05, ticket 38 sitting 1. Run state is keyed by batch id under
# `.scratch/<feature>/runs/<batch-id>/`, the script lists live runs instead of
# returning one, resume keys on the current directory, and the pre-flight
# refuses an issue range that overlaps any live ledger (rulings 10, 11, 21).

import os
import subprocess
import tempfile


class LiveLedgers(unittest.TestCase):
    def test_lists_every_live_copy_and_no_snapshot(self):
        a = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a", batch="batch-aaaaaa")
        b = cand(f"{WT}/run-b", f"Worktree: `{WT}/run-b`", "Owner: sess-b",
                 batch="batch-bbbbbb")
        snap = cand(f"{WT}/elsewhere", f"Worktree: `{WT}/run-a`", "Owner: sess-a",
                    batch="batch-aaaaaa")
        done = main_cand(f"Worktree: `{WT}/run-c`", MERGED, batch="batch-cccccc")
        self.assertEqual([c.batch for c in live_ledgers([a, b, snap, done])],
                         ["batch-aaaaaa", "batch-bbbbbb"])

    def test_zero_live_is_an_empty_list_not_an_error(self):
        self.assertEqual(live_ledgers([]), [])


class ParseScopeIds(unittest.TestCase):
    def test_reads_the_ledger_title_as_batch_b5e96d_wrote_it(self):
        title = ("# Run ledger — 533, 546, 545, 547, 548, 549, 557b, 557a, 526, "
                 "527, 529, 528, 530, 531, 479 (run `batch-b5e96d`)")
        self.assertEqual(
            parse_scope_ids(title),
            ["533", "546", "545", "547", "548", "549", "557b", "557a", "526",
             "527", "529", "528", "530", "531", "479"])

    def test_reads_a_scope_line(self):
        self.assertEqual(parse_scope_ids("Scope, as given: **348, 345, 288**."),
                         ["348", "345", "288"])

    def test_the_batch_id_is_not_an_issue(self):
        self.assertNotIn("b5e96d", parse_scope_ids("# Run ledger — 12 (run `batch-b5e96d`)"))

    def test_a_year_or_a_sha_in_the_title_is_not_an_issue(self):
        self.assertEqual(parse_scope_ids("# Run ledger — 12, 13 (run `batch-x`) 2026-09-04"),
                         ["12", "13"])


class Overlapping(unittest.TestCase):
    def test_names_the_run_holding_each_requested_issue(self):
        a = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a",
                      scope="# Run ledger — 533, 546, 557b (run `batch-aaaaaa`)",
                      batch="batch-aaaaaa")
        hits = overlapping([a], ["546", "999"])
        self.assertEqual([(c.batch, ids) for c, ids in hits], [("batch-aaaaaa", ["546"])])

    def test_a_finished_run_holds_nothing(self):
        done = main_cand(f"Worktree: `{WT}/run-c`", MERGED,
                         scope="# Run ledger — 533 (run `batch-cccccc`)", batch="batch-cccccc")
        self.assertEqual(overlapping([done], ["533"]), [])

    def test_matching_is_whole_id_not_substring(self):
        """`34` must not match `345`, and `345` must not match `34`."""
        a = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a",
                      scope="# Run ledger — 345 (run `batch-aaaaaa`)", batch="batch-aaaaaa")
        self.assertEqual(overlapping([a], ["34"]), [])

    def test_a_leading_zero_is_the_same_issue(self):
        a = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a",
                      scope="# Run ledger — 05, 07 (run `batch-aaaaaa`)", batch="batch-aaaaaa")
        self.assertEqual([ids for _, ids in overlapping([a], ["5"])], [["05"]])


class CollectFromARealCheckout(unittest.TestCase):
    """The glob is the layout. Only `runs/<batch-id>/run.md` is a ledger now."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", self.root], check=True)
        feature = os.path.join(self.root, ".scratch", "example-feature")
        os.makedirs(os.path.join(feature, "runs", "batch-aaaaaa"))
        with open(os.path.join(feature, "runs", "batch-aaaaaa", "run.md"), "w") as h:
            h.write("# Run ledger — 12, 13 (run `batch-aaaaaa`)\n\nOwner: sess-a\n"
                    f"Worktree: `{self.root}`\n")
        # The old fixed name, which ticket 38 retired: never a ledger again.
        with open(os.path.join(feature, "run.md"), "w") as h:
            h.write("# Run ledger — 99 (run `old`)\n\nOwner: sess-old\n"
                    f"Worktree: `{self.root}`\n")

    def test_collects_the_run_directory_and_ignores_the_old_fixed_name(self):
        found = collect_candidates(self.root)
        self.assertEqual([c.batch for c in found], ["batch-aaaaaa"])
        self.assertTrue(found[0].is_main)
        self.assertEqual(parse_scope_ids(found[0].scope_text), ["12", "13"])

    def test_the_cli_lists_live_runs_one_per_line(self):
        import find_live_ledger
        done = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--list", "--repo", self.root],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        line = done.stdout.strip().splitlines()
        self.assertEqual(len(line), 1)
        batch, path, tree, kind = line[0].split("\t")
        self.assertEqual(batch, "batch-aaaaaa")
        self.assertEqual(kind, "run")
        self.assertTrue(path.endswith("runs/batch-aaaaaa/run.md"))
        self.assertEqual(os.path.realpath(tree), os.path.realpath(self.root))

    def test_the_cli_refuses_an_overlapping_issue_range(self):
        import find_live_ledger
        done = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--overlap", "13,40",
             "--repo", self.root], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("batch-aaaaaa", done.stderr)
        self.assertIn("13", done.stderr)
        self.assertNotIn("40", done.stderr.split("batch-aaaaaa", 1)[1].split("\n")[0])

    def test_the_cli_lets_a_disjoint_issue_range_through(self):
        import find_live_ledger
        done = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--overlap", "40",
             "--repo", self.root], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_cli_resumes_from_inside_the_run_tree_and_refuses_from_elsewhere(self):
        import find_live_ledger
        inside = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--repo", self.root],
            cwd=self.root, capture_output=True, text=True)
        self.assertEqual(inside.returncode, 0, inside.stderr)
        self.assertTrue(inside.stdout.strip().endswith("runs/batch-aaaaaa/run.md"))
        elsewhere = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--repo", self.root],
            cwd=tempfile.gettempdir(), capture_output=True, text=True)
        self.assertEqual(elsewhere.returncode, 1)
        self.assertIn("batch-aaaaaa", elsewhere.stderr)


class TreeOf(unittest.TestCase):
    def test_the_main_checkout_is_its_own_tree_even_though_worktrees_nest_under_it(self):
        self.assertEqual(tree_of(f"{MAIN}/src/app", TREES), MAIN)

    def test_a_path_inside_a_linked_worktree_belongs_to_that_worktree(self):
        self.assertEqual(tree_of(f"{WT}/run-a/src/app", TREES), f"{WT}/run-a")

    def test_a_path_outside_every_tree_is_nobodys(self):
        self.assertIsNone(tree_of("/tmp/elsewhere", TREES))


class OwnershipIsTheTreeNotAPrefix(unittest.TestCase):
    def test_a_ledger_naming_the_main_checkout_does_not_own_a_linked_worktree(self):
        m = main_cand(f"Worktree: `{MAIN}`", "Owner: sess-m", batch="batch-mmmmmm")
        chosen, reason = select_ledger([m], cwd=f"{WT}/harden-issues-xyz", worktrees=TREES)
        self.assertIsNone(chosen)
        self.assertIn("batch-mmmmmm", reason)

    def test_the_refusal_names_the_tree_cwd_is_actually_in(self):
        a = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a", batch="batch-aaaaaa")
        _, reason = select_ledger([a], cwd=f"{WT}/harden-issues-xyz/src", worktrees=TREES)
        self.assertIn(f"{WT}/harden-issues-xyz is not a tree", reason)
        self.assertNotIn("main checkout is not", reason)

    def test_a_ledger_naming_the_main_checkout_is_resumed_from_the_main_checkout(self):
        m = main_cand(f"Worktree: `{MAIN}`", "Owner: sess-m", batch="batch-mmmmmm")
        chosen, _ = select_ledger([m], cwd=f"{MAIN}/src", worktrees=TREES)
        self.assertEqual(chosen, m.path)


class OneRunIsOneLedger(unittest.TestCase):
    """A run may be live in the main checkout AND in its own tree. That is one run."""

    def two_copies(self):
        in_main = main_cand(f"Worktree: `{WT}/run-a`", "Owner: sess-a", batch="batch-aaaaaa")
        in_tree = cand(f"{WT}/run-a", f"Worktree: `{WT}/run-a`", "Owner: sess-a",
                       batch="batch-aaaaaa")
        return in_main, in_tree

    def test_live_ledgers_dedupes_by_batch_and_keeps_the_main_copy(self):
        in_main, in_tree = self.two_copies()
        live = live_ledgers([in_tree, in_main])
        self.assertEqual([c.path for c in live], [in_main.path])

    def test_resume_from_inside_the_tree_picks_the_one_run(self):
        in_main, in_tree = self.two_copies()
        chosen, reason = select_ledger([in_main, in_tree], cwd=f"{WT}/run-a", worktrees=TREES)
        self.assertEqual(chosen, in_main.path)
        self.assertIsNone(reason)


class ParseScopeIdsReadsTheTable(unittest.TestCase):
    TABLE = (
        "# Run ledger — batch-c0ffee\n\nOwner: sess\n\n"
        "| Issue | Est | Status | Notes |\n|---|---|---|---|\n"
        "| 533 | 40m | done | attempt 1 — verify at 13:45 |\n"
        "| 557b | 90m | queued | |\n"
    )

    def test_the_status_table_is_read_when_the_title_names_nothing(self):
        self.assertEqual(parse_scope_ids(self.TABLE), ["533", "557b"])

    def test_a_range_in_the_title_is_expanded(self):
        self.assertEqual(parse_scope_ids("# Run ledger — 316-318 (run `batch-x`)"),
                         ["316", "317", "318"])

    def test_a_clock_time_is_not_two_issues(self):
        self.assertEqual(parse_scope_ids("# Run ledger — 12 (run `b`) resumed 13:45"), ["12"])

    def test_a_note_cell_number_is_not_an_issue(self):
        self.assertNotIn("45", parse_scope_ids(self.TABLE))


class ParseScopeArgument(unittest.TestCase):
    """One grammar for `/run-issues <scope>`, shared by the hook and the launch."""

    def test_the_documented_forms(self):
        self.assertEqual(parse_scope_argument("05"), (["05"], []))
        self.assertEqual(parse_scope_argument("05-09"), (["05", "06", "07", "08", "09"], []))
        self.assertEqual(parse_scope_argument("13c 20 14 22"), (["13c", "20", "14", "22"], []))
        self.assertEqual(parse_scope_argument("all"), (["all"], []))

    def test_commas_are_separators(self):
        self.assertEqual(parse_scope_argument("533,546"), (["533", "546"], []))
        self.assertEqual(parse_scope_argument("533, 546"), (["533", "546"], []))

    def test_a_token_it_cannot_read_is_reported_not_dropped(self):
        ids, bad = parse_scope_argument("13a-13c 40")
        self.assertEqual(ids, ["40"])
        self.assertEqual(bad, ["13a-13c"])
        self.assertEqual(parse_scope_argument("05–09")[1], ["05–09"])
        self.assertEqual(parse_scope_argument("12-9")[1], ["12-9"])

    def test_override_words_are_not_issues_and_not_bad(self):
        self.assertEqual(parse_scope_argument("40 force-model"), (["40"], []))

    def test_the_models_word_ends_the_scope(self):
        """Ticket 39 ruling 5: the map is typed after the issue list. Every token
        from `models:` on belongs to the map, and none of them is a bad scope
        token -- the pre-flight refuses a launch on any bad token."""
        self.assertEqual(
            parse_scope_argument("512 513 models: implementer=opus gates=fable"),
            (["512", "513"], []))

    def test_a_map_alone_is_an_empty_scope_not_a_bad_one(self):
        self.assertEqual(parse_scope_argument("models: all=opus"), ([], []))

    def test_a_bad_token_before_the_models_word_is_still_reported(self):
        ids, bad = parse_scope_argument("13a-13c 40 models: all=opus")
        self.assertEqual((ids, bad), (["40"], ["13a-13c"]))


class TitleBatchMustMatchTheDirectory(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", self.root], check=True)
        run_dir = os.path.join(self.root, ".scratch", "f", "runs", "batch-new")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "run.md"), "w") as h:
            h.write(f"# Run ledger — 12 (run `batch-old`)\n\nOwner: s\nWorktree: `{self.root}`\n")

    def test_list_refuses_a_ledger_whose_title_names_another_batch(self):
        import find_live_ledger
        done = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--list", "--repo", self.root],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("batch-old", done.stderr)
        self.assertIn("batch-new", done.stderr)


class RoundBriefs(unittest.TestCase):
    """Ticket 38 sitting 4: a hunt is a run for isolation. Its ledger is
    `round-brief.md` in its own worktree, with the same header lines, so it is
    collected, judged live and listed under the one rule runs already use."""

    def trees(self):
        root = tempfile.mkdtemp()
        hunt = os.path.join(root, ".claude", "worktrees", "hunt-abc123")
        os.makedirs(os.path.join(root, ".scratch", "f"))
        os.makedirs(os.path.join(hunt, ".scratch", "f"))
        return root, hunt

    def brief(self, hunt, owner="Owner: session s1 (orchestrator)"):
        path = os.path.join(hunt, ".scratch", "f", "round-brief.md")
        with open(path, "w") as handle:
            handle.write(f"# Round brief — quotes (hunt `hunt-abc123`)\n\n{owner}\n"
                         f"Worktree: `{hunt}`\nBranch: `hunt/hunt-abc123`\n")
        return path

    def test_no_brief_anywhere_is_no_open_hunt(self):
        root, hunt = self.trees()
        self.assertEqual(hunts(collect_candidates(worktrees=[root, hunt])), [])

    def test_a_brief_in_its_own_worktree_is_a_live_hunt_with_its_title_id(self):
        root, hunt = self.trees()
        path = self.brief(hunt)
        live = hunts(collect_candidates(worktrees=[root, hunt]))
        self.assertEqual([(c.path, c.batch, c.kind) for c in live], [(path, "hunt-abc123", "hunt")])
        self.assertEqual(runs(collect_candidates(worktrees=[root, hunt])), [])

    def test_a_brief_with_no_owner_line_is_finished_paperwork(self):
        root, hunt = self.trees()
        self.brief(hunt, owner="")
        self.assertEqual(hunts(collect_candidates(worktrees=[root, hunt])), [])

    def test_a_brief_never_matches_an_issue_range(self):
        """Its prose carries numbers; none of them is an issue the hunt holds."""
        root, hunt = self.trees()
        path = self.brief(hunt)
        with open(path, "a") as handle:
            handle.write("\nSweep group 1: issues 12, 13 and the 20-25 quote screens.\n")
        self.assertEqual(overlapping(collect_candidates(worktrees=[root, hunt]), ["12", "20"]), [])

    def test_list_prints_the_kind_as_a_fourth_column(self):
        root = tempfile.mkdtemp()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(["git", "init", "-q", root], check=True)
        subprocess.run(["git", "-C", root, "commit", "-q", "--allow-empty", "-m", "base"], check=True, env=env)
        hunt = os.path.join(root, ".claude", "worktrees", "hunt-abc123")
        subprocess.run(["git", "-C", root, "worktree", "add", "-q", hunt, "-b", "hunt/hunt-abc123"], check=True)
        os.makedirs(os.path.join(hunt, ".scratch", "f"))
        path = self.brief(hunt)
        import find_live_ledger
        done = subprocess.run(
            [sys.executable, find_live_ledger.__file__, "--list", "--repo", root],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        batch, listed, tree, kind = done.stdout.strip().split("\t")
        self.assertEqual((batch, kind), ("hunt-abc123", "hunt"))
        self.assertEqual(os.path.realpath(listed), os.path.realpath(path))
        self.assertEqual(os.path.realpath(tree), os.path.realpath(hunt))


class NoTimeoutIsASilentFailure(unittest.TestCase):
    def test_every_git_call_carries_a_timeout(self):
        import inspect, find_live_ledger
        source = inspect.getsource(find_live_ledger)
        for call in source.split("subprocess.run(")[1:]:
            self.assertIn("timeout=", call.split(")")[0] + call.split(")")[1] if ")" in call else call)


class TheJournalBesideALedger(unittest.TestCase):
    """Ticket 39 sitting 2. Two hooks append a line per spawn, and each had
    grown its own copy of this until the 2026-09-05 review refused it."""

    def test_a_run_ledger_journals_into_run_journal_md(self):
        self.assertEqual(
            journal_for("/x/.scratch/f/runs/batch-a/run.md"),
            "/x/.scratch/f/runs/batch-a/run-journal.md")

    def test_a_hunt_brief_journals_into_round_journal_md(self):
        self.assertEqual(
            journal_for("/x/.scratch/f/round-brief.md"),
            "/x/.scratch/f/round-journal.md")


if __name__ == "__main__":
    unittest.main()
