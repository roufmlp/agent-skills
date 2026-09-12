#!/usr/bin/env python3
"""Tests for check_queue_shard.

The fixtures copy the two shapes that actually reached a board unnamed: an
issue-drafting heading with a bare id and no `q-`, and a hardening
heading with a `q-` id that was never backticked. Both rendered forever, and
both are refused here.
"""

import contextlib
import io
import os
import tempfile
import unittest

from check_queue_shard import CLEAN, EMPTY, WRONG, check_file, check_text, main

NAMED = (
    "# a shard\n\n"
    "## 01-Q1: Which local Postgres `q-h0912-1`\n\nbody\n\n"
    "## 01-Q2: Where does the radius come from `q-h0912-2`\n\nbody\n"
)
BARE = "## to-issues-2026-09-12-61 [irreversible] 14-Q1: declined credit\n\nbody\n"
UNTICKED = "## q-h0908-3 [reversible] the storage meter\n\nbody\n"


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class Text(unittest.TestCase):
    def test_a_shard_whose_headings_all_carry_ids_passes(self):
        self.assertEqual(check_text(NAMED), [])

    def test_the_orderflow_shape_is_refused_and_names_the_line(self):
        refusals = check_text("# shard\n\n" + BARE, "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertTrue(refusals[0].startswith("s.md:3:"), refusals[0])
        self.assertIn("no backticked `q-` id", refusals[0])

    def test_the_unticked_shape_without_backticks_is_refused(self):
        refusals = check_text(UNTICKED)
        self.assertEqual(len(refusals), 1)
        self.assertIn("no backticked", refusals[0])

    def test_the_id_may_sit_anywhere_on_the_line(self):
        self.assertEqual(check_text("## `q-x-1` [reversible] leading id\n\nbody\n"), [])

    def test_a_heading_inside_a_fence_is_an_example_not_an_item(self):
        text = NAMED + "\n```\n## not a heading\n```\n"
        self.assertEqual(check_text(text), [])

    def test_two_headings_sharing_an_id_are_refused(self):
        text = NAMED + "## a third `q-h0912-2`\n\nbody\n"
        refusals = check_text(text, "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertIn("already names the heading on line 7", refusals[0])

    def test_a_file_with_no_heading_asserts_nothing(self):
        refusals = check_text("# only a title\n\nprose\n", "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertIn("nothing was checked", refusals[0])

    def test_every_unnamed_heading_is_reported_not_only_the_first(self):
        text = "# s\n\n" + BARE + "\n" + UNTICKED
        self.assertEqual(len(check_text(text)), 2)


class File(unittest.TestCase):
    def test_exit_codes_follow_the_directory_convention(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_file(write(tmp, "a.md", NAMED))[0], CLEAN)
            self.assertEqual(check_file(write(tmp, "b.md", "# t\n" + BARE))[0], WRONG)
            self.assertEqual(check_file(write(tmp, "c.md", "# t\n"))[0], EMPTY)
            self.assertEqual(check_file(os.path.join(tmp, "missing.md"))[0], EMPTY)


class Main(unittest.TestCase):
    def run_main(self, *paths):
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = main(list(paths))
        return code, out.getvalue(), err.getvalue()

    def test_a_clean_shard_exits_zero_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.run_main(write(tmp, "a.md", NAMED))
        self.assertEqual(code, CLEAN)
        self.assertIn("every heading carries an id", out)
        self.assertEqual(err, "")

    def test_one_bad_shard_among_good_ones_fails_the_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = write(tmp, "a.md", NAMED)
            bad = write(tmp, "b.md", "# t\n\n" + BARE)
            code, out, err = self.run_main(good, bad)
        self.assertEqual(code, WRONG)
        self.assertIn("REFUSED", err)
        self.assertIn("b.md:3:", err)
        self.assertEqual(out, "")

    def test_an_empty_shard_beside_a_wrong_one_reports_the_worse_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = write(tmp, "a.md", "# t\n")
            bad = write(tmp, "b.md", "# t\n\n" + BARE)
            code, _, _ = self.run_main(empty, bad)
        self.assertEqual(code, EMPTY)


if __name__ == "__main__":
    unittest.main()
