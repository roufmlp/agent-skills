#!/usr/bin/env python3
"""The decisions in `check_paste_file.py`, driven with no filesystem.

Every case here is taken from a real paste file, named in the test. The two
that fail are the pair one run shipped with the confirmation query commented
out; the two that pass were written before that regression.
"""

import unittest

import check_paste_file as guard


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


class MainTest(unittest.TestCase):
    def test_no_paths_is_a_usage_error_not_a_pass(self):
        self.assertEqual(guard.main([]), 2)

    def test_an_unreadable_path_exits_two(self):
        self.assertEqual(guard.main(["/nonexistent/0099-paste.sql"]), 2)


if __name__ == "__main__":
    unittest.main()
