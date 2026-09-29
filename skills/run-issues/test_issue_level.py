#!/usr/bin/env python3
"""Drill for issue_level.py, tracker-tooling issue 40.

    python3 test_issue_level.py
"""

import os
import subprocess
import sys
import tempfile
import unittest

import issue_level

HERE = os.path.dirname(os.path.abspath(__file__))
RISK = "No risk paths: a fixture.\n"


def ledger_text(tree, rows):
    return ("# Run `batch-abc123`\n\nOwner: run-issues-batch-abc123\n"
            f"Worktree: `{tree}`\n\n## Status\n\n"
            "| Issue | Size | Status | Stamps |\n|---|---|---|---|\n"
            + "".join(f"| {issue} | S | {status} | attempt 1 |\n"
                      for issue, status in rows))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.tree = os.path.realpath(self.scratch.name)
        self.ledger = os.path.join(self.tree, ".scratch", "feat", "runs",
                                   "batch-abc123", "run.md")
        os.makedirs(os.path.dirname(self.ledger))
        self.risk(RISK)

    def tearDown(self):
        self.scratch.cleanup()

    def risk(self, text, tree=None):
        path = os.path.join(tree or self.tree, "docs", "agents", "risk-paths.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if text is None:
            os.remove(path)
            return
        with open(path, "w") as handle:
            handle.write(text)

    def issue(self, level_line, issue="12", tree=None):
        path = os.path.join(tree or self.tree, ".scratch", "feat", "issues",
                            f"{issue}-x.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("Status: ready-for-agent\n"
                         + (level_line + "\n" if level_line else "")
                         + "\n# 12 — x\n")
        return path

    def write_ledger(self, rows=(("12", "in-progress"),), tree=None):
        with open(self.ledger, "w") as handle:
            handle.write(ledger_text(tree or self.tree, rows))


class TheLevelLine(Fixture):
    def test_only_level_light_reads_light(self):
        self.write_ledger()
        for line, level in (("Level: light", "light"), ("Level: full", "full"),
                            (None, "full"), ("Level: medium", "full"),
                            ("Level: Light-ish", "full")):
            with self.subTest(line=line):
                self.issue(line)
                self.assertEqual(issue_level.read_level(self.ledger, "12").level,
                                 level)

    def test_a_missing_file_reads_full_and_names_what_it_looked_for(self):
        self.write_ledger()
        reading = issue_level.read_level(self.ledger, "12")
        self.assertEqual(reading.level, "full")
        self.assertIn("12-*.md", reading.note)

    def test_it_is_read_fresh_on_every_call(self):
        self.write_ledger()
        self.issue("Level: light")
        self.assertEqual(issue_level.read_level(self.ledger, "12").level, "light")
        self.issue("Level: full")
        self.assertEqual(issue_level.read_level(self.ledger, "12").level, "full")

    def test_an_id_is_not_a_prefix_of_another(self):
        self.write_ledger()
        self.issue("Level: light", issue="12b")
        self.assertEqual(issue_level.read_level(self.ledger, "12").level, "full")


class TheRunsOwnTree(Fixture):
    """Seam pass h0925: the tree the `Worktree:` line names, never the copy
    beside the ledger."""

    def test_the_named_trees_copy_is_the_one_read(self):
        with tempfile.TemporaryDirectory() as other:
            other = os.path.realpath(other)
            self.risk(RISK, tree=other)
            self.issue("Level: light")
            self.issue("Level: full", tree=other)
            self.write_ledger(tree=other)
            self.assertEqual(issue_level.read_level(self.ledger, "12").level,
                             "full")
            self.issue("Level: light", tree=other)
            self.assertEqual(issue_level.read_level(self.ledger, "12").level,
                             "light")


class TheRiskFileBacksALightLevel(Fixture):
    """Default seam h0925 Q6."""

    def test_no_risk_file_reads_full_and_names_the_path(self):
        self.write_ledger()
        self.issue("Level: light")
        self.risk(None)
        reading = issue_level.read_level(self.ledger, "12")
        self.assertEqual(reading.level, "full")
        self.assertIn(os.path.join("docs", "agents", "risk-paths.md"), reading.note)

    def test_an_empty_risk_file_reads_full(self):
        self.write_ledger()
        self.issue("Level: light")
        self.risk("# Risk paths\n")
        self.assertEqual(issue_level.read_level(self.ledger, "12").level, "full")


class TheLiveIssue(Fixture):
    def test_the_one_row_in_progress_or_in_correction_is_read(self):
        self.issue("Level: light")
        for status in ("in-progress", "**in-progress**", "correction",
                       "correction round 1"):
            with self.subTest(status=status):
                self.write_ledger(rows=(("11", "done"), ("12", status),
                                        ("13", "queued")))
                reading = issue_level.read_live_level(self.ledger)
                self.assertEqual((reading.issue, reading.level), ("12", "light"))

    def test_the_status_column_is_found_by_its_header(self):
        self.issue("Level: light")
        with open(self.ledger, "w") as handle:
            handle.write(f"Worktree: `{self.tree}`\n\n"
                         "| # | Status | Issue |\n|---|---|---|\n"
                         "| 1 | in-progress | 12 — x |\n")
        self.assertEqual(issue_level.read_live_level(self.ledger).level, "light")

    def test_no_row_or_two_rows_read_full_with_a_note(self):
        self.issue("Level: light")
        for rows in ((("12", "queued"),),
                     (("12", "in-progress"), ("13", "correction"))):
            with self.subTest(rows=rows):
                self.write_ledger(rows=rows)
                reading = issue_level.read_live_level(self.ledger)
                self.assertEqual(reading.level, "full")
                self.assertTrue(reading.note)


class TheCommand(Fixture):
    def test_it_prints_the_level_and_the_note_on_stderr(self):
        self.write_ledger()
        done = subprocess.run(
            [sys.executable, os.path.join(HERE, "issue_level.py"),
             "--ledger", self.ledger, "--issue", "12"],
            capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout), (0, "full\n"))
        self.assertIn("no issue file", done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
