#!/usr/bin/env python3
"""Drill for check_briefing_blocked.py, tracker-tooling issue 40, AC7.

    python3 test_check_briefing_blocked.py
"""

import contextlib
import io
import os
import tempfile
import unittest

import check_briefing_blocked as check

# The Status-cell forms of `blocked` the ledgers hold, measured by AC7's
# command on 2026-09-25, and the one `SKILL.md` step 9 orders.
FORMS = ("blocked", "blocked (criteria)", "blocked by 176",
         "BLOCKED. attempt 3 refused by the cap", "blocked (depends on 11)",
         "**blocked**", "blocked — light: two attempts spent")


def ledger(rows):
    return ("# Run `batch-abc123`\n\n## Status\n\n"
            "| Issue | Size | Status | Stamps |\n|---|---|---|---|\n"
            + "".join(f"| {issue} | S | {status} | attempt 1 |\n"
                      for issue, status in rows))


def briefing(skipped):
    return ("# Merge briefing\n\n## The run in one screen\n\nShipped: 11\n\n"
            "## Skipped or blocked\n\n" + skipped + "\n## What shipped\n\n"
            "- 12 appears here and must not count.\n")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.scratch.cleanup()

    def run_check(self, ledger_text, briefing_text):
        paths = []
        for name, text in (("run.md", ledger_text),
                           ("merge-briefing.md", briefing_text)):
            path = os.path.join(self.scratch.name, name)
            if text is not None:
                with open(path, "w") as handle:
                    handle.write(text)
            paths.append(path)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check.main(["--ledger", paths[0], "--briefing", paths[1]])
        return code, out.getvalue(), err.getvalue()


class ABlockedIssueIsNamed(Fixture):
    def test_every_form_omitted_is_refused_and_named(self):
        for form in FORMS:
            with self.subTest(form=form):
                code, _, err = self.run_check(
                    ledger((("11", "done"), ("12", form))),
                    briefing("- 13 — an unrelated line.\n"))
                self.assertEqual(code, 1, err)
                self.assertIn("12", err)

    def test_every_form_named_with_its_reason_passes(self):
        for form in FORMS:
            with self.subTest(form=form):
                code, out, err = self.run_check(
                    ledger((("11", "done"), ("12", form))),
                    briefing("- **12** — light: two attempts spent.\n"))
                self.assertEqual(code, 0, err)
                self.assertIn("12", out)

    def test_an_id_is_not_a_prefix_of_another(self):
        code, _, err = self.run_check(ledger((("12", "blocked"),)),
                                      briefing("- 12b — blocked.\n"))
        self.assertEqual(code, 1, err)

    def test_a_briefing_with_no_section_is_refused(self):
        code, _, err = self.run_check(ledger((("12", "blocked"),)),
                                      "# Merge briefing\n\n- 12 blocked\n")
        self.assertEqual(code, 1)
        self.assertIn("## Skipped or blocked", err)

    def test_no_blocked_row_needs_no_section(self):
        code, _, err = self.run_check(ledger((("11", "done"),
                                              ("12", "queued"))),
                                      "# Merge briefing\n")
        self.assertEqual(code, 0, err)

    def test_a_status_word_that_merely_holds_blocked_is_not_blocked(self):
        code, _, err = self.run_check(
            ledger((("12", "done, unblocked by 11"),)), "# Merge briefing\n")
        self.assertEqual(code, 0, err)


class WhatItCannotRead(Fixture):
    def test_a_ledger_with_no_status_table_grades_nothing(self):
        code, _, err = self.run_check("# Run\n\nno table\n", briefing(""))
        self.assertEqual(code, 2)
        self.assertIn("status table", err)

    def test_a_missing_file_grades_nothing(self):
        code, _, err = self.run_check(ledger((("12", "blocked"),)), None)
        self.assertEqual(code, 2)
        self.assertIn("merge-briefing.md", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
