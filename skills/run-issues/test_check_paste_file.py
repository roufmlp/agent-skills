#!/usr/bin/env python3
"""The decisions in `check_paste_file.py`, driven with no filesystem.

Every case here is taken from a real paste file, named in the test. The two
that fail are the pair one run shipped with the confirmation query commented
out; the two that pass were written before that regression.
"""

import os
import tempfile
import unittest

import check_paste_file as guard


def fake_git(**answers):
    """A stand-in for git that answers a fixed status per subcommand.

    Keyed by the subcommand, so a test says what git found and never what git
    was asked. `None` is git itself missing from the machine.
    """

    def git(args, cwd):
        del cwd
        return answers[args[0]]

    return git


class JudgeTest(unittest.TestCase):
    def test_a_live_query_ships(self):
        """`0093` and `0094`'s shape: the query is there and it runs."""
        text = (
            "alter table public.quotes add column if not exists line_notes jsonb;\n"
            "\n"
            "-- Run this on its own after the statement above.\n"
            "select column_name, data_type from information_schema.columns\n"
            "where table_name = 'quotes';\n"
        )
        self.assertIsNone(guard.judge(text))

    def test_a_commented_query_is_refused(self):
        """`0096`'s shape, 2026-08-25: pasted as written it answers nothing."""
        text = (
            "alter table public.quotes add column if not exists line_notes jsonb;\n"
            "\n"
            "-- Run this on its own after the statement above.\n"
            "-- select column_name, data_type, is_nullable\n"
            "-- from information_schema.columns\n"
            "-- where table_name = 'quotes' and column_name = 'line_notes';\n"
        )
        verdict = guard.judge(text)
        self.assertIsNotNone(verdict)
        kind, detail = verdict
        self.assertEqual(kind, "commented-only")
        self.assertIn("4", detail)

    def test_a_file_with_no_query_at_all_is_a_different_refusal(self):
        """The repairs differ: a marker to delete, against a query to write."""
        text = "alter table public.brands add column if not exists origin text;\n"
        kind, _ = guard.judge(text)
        self.assertEqual(kind, "no-query")

    def test_one_live_query_beside_a_commented_one_ships(self):
        """A file may show the recovery statement commented and still be fine.

        `0095` carries exactly this shape in its reading rule: the repair for
        the nine-row outcome is printed as prose the reader does not paste. It
        is the CONFIRMATION being commented that makes the file useless, and a
        check that refused every commented line would refuse a correct file.
        """
        text = (
            "-- select 1;  -- an example the reader does not run\n"
            "select conname from pg_constraint where contype = 'f';\n"
        )
        self.assertIsNone(guard.judge(text))

    def test_the_marker_is_read_past_any_number_of_dashes_and_spaces(self):
        text = "---   SELECT count(*) from public.brands;\n"
        kind, _ = guard.judge(text)
        self.assertEqual(kind, "commented-only")

    def test_case_does_not_decide_it(self):
        text = "SELECT count(*) FROM public.brands;\n"
        self.assertIsNone(guard.judge(text))

    def test_a_select_inside_a_line_is_not_a_statement(self):
        """`select` in prose is not a query the reader can run.

        Without this the instruction sentence above a commented query — "run
        the select below" — would count as the live query and the file would
        ship refuted by its own comment.
        """
        text = "-- Now run the select below to confirm it landed.\n-- select 1;\n"
        kind, _ = guard.judge(text)
        self.assertEqual(kind, "commented-only")

    def test_an_empty_file_is_refused_rather_than_passed(self):
        kind, _ = guard.judge("")
        self.assertEqual(kind, "no-query")


class TrackStateTest(unittest.TestCase):
    """Run `batch-45c8b1` wrote seven paste files and committed none of them.

    Each one graded `ok` on its content and none of them existed for anybody but
    the agent that wrote it. The finale caught all seven by hand as F1.
    """

    def test_a_file_the_index_holds_is_tracked(self):
        state = guard.track_state(
            "/repo/.scratch/0110-paste.sql",
            git=fake_git(**{"rev-parse": 0, "ls-files": 0}),
        )
        self.assertEqual(state, "tracked")

    def test_a_file_the_index_does_not_hold_is_untracked(self):
        """`ls-files --error-unmatch` exits non-zero on a path git never saw."""
        state = guard.track_state(
            "/repo/.scratch/0110-paste.sql",
            git=fake_git(**{"rev-parse": 0, "ls-files": 1}),
        )
        self.assertEqual(state, "untracked")

    def test_a_tree_with_no_repository_cannot_be_graded(self):
        """Not a refusal about the file. The check cannot see its input."""
        state = guard.track_state(
            "/tmp/loose/0110-paste.sql",
            git=fake_git(**{"rev-parse": 128}),
        )
        self.assertEqual(state, "no-repository")

    def test_git_missing_from_the_machine_cannot_be_graded_either(self):
        state = guard.track_state(
            "/repo/0110-paste.sql",
            git=fake_git(**{"rev-parse": None}),
        )
        self.assertEqual(state, "no-git")


class TrackedGateTest(unittest.TestCase):
    """`main` refuses an untracked file, on its own exit code.

    Exit 3 and not 1: the two want different repairs, exactly as `no-query` is
    separated from `commented-only`. A content refusal is a `--` to delete; this
    one is a `git add` and a commit, and the content of a file nobody can pull
    does not matter yet.
    """

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, "0110-paste.sql")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("select count(*) from public.brands;\n")
        self.addCleanup(self.directory.cleanup)

    def test_an_untracked_file_is_refused_with_exit_three(self):
        self.assertEqual(guard.main([self.path], track=lambda path: "untracked"), 3)

    def test_the_same_file_tracked_passes(self):
        self.assertEqual(guard.main([self.path], track=lambda path: "tracked"), 0)

    def test_a_tree_with_no_repository_exits_two_rather_than_refusing_the_file(self):
        self.assertEqual(guard.main([self.path], track=lambda path: "no-repository"), 2)
        self.assertEqual(guard.main([self.path], track=lambda path: "no-git"), 2)

    def test_untracked_outranks_a_content_refusal(self):
        """Both faults are printed, and the tracking code is the one returned.

        Repairing the comment marker in a file nobody will ever pull repairs
        nothing, so the exit the reader acts on is the tracking one.
        """
        commented = os.path.join(self.directory.name, "0111-paste.sql")
        with open(commented, "w", encoding="utf-8") as handle:
            handle.write("-- select count(*) from public.brands;\n")
        self.assertEqual(guard.main([commented], track=lambda path: "untracked"), 3)

    def test_a_tracked_file_with_a_commented_query_still_exits_one(self):
        commented = os.path.join(self.directory.name, "0111-paste.sql")
        with open(commented, "w", encoding="utf-8") as handle:
            handle.write("-- select count(*) from public.brands;\n")
        self.assertEqual(guard.main([commented], track=lambda path: "tracked"), 1)


class MainTest(unittest.TestCase):
    def test_no_paths_is_a_usage_error_not_a_pass(self):
        self.assertEqual(guard.main([]), 2)

    def test_an_unreadable_path_exits_two(self):
        self.assertEqual(guard.main(["/nonexistent/0099-paste.sql"]), 2)


if __name__ == "__main__":
    unittest.main()
