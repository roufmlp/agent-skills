#!/usr/bin/env python3
"""The decisions in `seams_from_commits.py`, driven on a built git repository.

The fixture repeats run `batch-b00631`'s shape: one code commit per issue, every
one named by a ledger row, and a bookkeeping commit between them that no row
names. Issue 21c and issue 110 both touch `src/model/confirm.ts`, which is the
seam that run's predicted list missed.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seams_from_commits as tool

LEDGER_HEAD = """
## Status

| Issue | Status | Estimate | Stamps |
|---|---|---|---|
"""


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo, *args],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def write(repo, path, text):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)


class Fixture:
    """A repository shaped like a run branch, with its ledger."""

    def __init__(self, directory):
        self.repo = directory
        git(directory, "init", "-q", "-b", "main")
        git(directory, "config", "user.email", "t@example.com")
        git(directory, "config", "user.name", "t")
        write(directory, "README.md", "base\n")
        git(directory, "add", "-A")
        git(directory, "commit", "-qm", "base")
        self.base = git(directory, "rev-parse", "HEAD")
        self.rows = []

    def issue(self, name, paths, bookkeeping=True):
        for index, path in enumerate(paths):
            write(self.repo, path, f"{name} {index}\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", f"Issue {name}")
        self.rows.append((name, git(self.repo, "rev-parse", "--short", "HEAD")))
        if bookkeeping:
            write(self.repo, ".scratch/runs/b1/run.md", f"marked {name}\n")
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-qm", f"Mark issue {name} done")

    def ledger(self):
        rows = "".join(
            f"| {name} | done | medium | attempt 1 · committed {sha} |\n"
            for name, sha in self.rows
        )
        return LEDGER_HEAD + rows


class SeamsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.fixture = Fixture(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def test_finds_the_seam_a_predicted_list_would_miss(self):
        self.fixture.issue("21c", ["src/model/delivery.ts", "src/model/confirm.ts"])
        self.fixture.issue("110", ["src/model/money.ts", "src/model/confirm.ts"])
        found = tool.seams(self.fixture.repo, self.fixture.rows)
        code, _ = tool.split_records(found)
        self.assertEqual(code, {"src/model/confirm.ts": ["21c", "110"]})

    def test_a_file_one_issue_touched_is_not_a_seam(self):
        self.fixture.issue("34", ["src/controls/date/date-picker.tsx"])
        self.fixture.issue("110", ["src/model/money.ts"])
        code, _ = tool.split_records(tool.seams(self.fixture.repo, self.fixture.rows))
        self.assertEqual(code, {})

    def test_the_run_s_own_records_are_reported_apart_and_not_dropped(self):
        # Every issue writes the ledger. That is true, and it is not a seam.
        self.fixture.issue("34", ["src/a.ts", ".scratch/runs/b1/primer.md"])
        self.fixture.issue("35", ["src/a.ts", ".scratch/runs/b1/primer.md"])
        code, records = tool.split_records(tool.seams(self.fixture.repo, self.fixture.rows))
        self.assertEqual(code, {"src/a.ts": ["34", "35"]})
        self.assertEqual(records, {".scratch/runs/b1/primer.md": ["34", "35"]})

    def test_the_records_prefix_can_be_named(self):
        found = {"docs/notes.md": ["1", "2"], "src/a.ts": ["1", "2"]}
        code, records = tool.split_records(found, ("docs/",))
        self.assertEqual(list(code), ["src/a.ts"])
        self.assertEqual(list(records), ["docs/notes.md"])

    def test_counts_the_commits_no_row_names(self):
        self.fixture.issue("34", ["src/a.ts"])
        self.fixture.issue("35", ["src/b.ts"])
        loose = tool.unattributed(self.fixture.repo, self.fixture.base, "HEAD",
                                  self.fixture.rows)
        # One bookkeeping commit per issue, and neither is named by a ledger row.
        self.assertEqual(len(loose), 2)

    def test_a_commit_that_cannot_be_read_raises_rather_than_reading_as_empty(self):
        # A commit read as touching nothing would quietly shrink every seam,
        # and the report would be wrong in the direction nobody checks.
        with self.assertRaises(RuntimeError):
            tool.seams(self.fixture.repo, [("34", "0000000")])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.fixture = Fixture(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def _run(self, ledger_text, extra=()):
        path = os.path.join(self.directory.name, "run.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(ledger_text)
        out, err = io.StringIO(), io.StringIO()
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = tool.main(["--ledger", path, "--repo", self.fixture.repo, *extra])
        finally:
            sys.stdout, sys.stderr = stdout, stderr
        return code, out.getvalue(), err.getvalue()

    def test_reports_the_seam_and_separates_the_records(self):
        # The ledger rides in each issue's own commit here, which is what the
        # real runner does: the row is written as the issue closes.
        self.fixture.issue("21c", ["src/model/confirm.ts", ".scratch/runs/b1/primer.md"])
        self.fixture.issue("110", ["src/model/confirm.ts", ".scratch/runs/b1/primer.md"])
        code, out, _ = self._run(self.fixture.ledger())
        self.assertEqual(code, 0)
        self.assertIn("src/model/confirm.ts  <- 21c, 110", out)
        self.assertIn("not a seam", out)
        self.assertIn(".scratch/runs/b1/primer.md", out)

    def test_says_so_plainly_when_there_is_no_seam(self):
        self.fixture.issue("34", ["src/a.ts"])
        self.fixture.issue("35", ["src/b.ts"])
        code, out, _ = self._run(self.fixture.ledger())
        self.assertEqual(code, 0)
        self.assertIn("no file outside the run's own records", out)

    def test_refuses_a_ledger_naming_no_commit_rather_than_reporting_no_seams(self):
        # "No seams" and "no input" read the same and mean opposite things.
        ledger = LEDGER_HEAD + "| 34 | done | medium | attempt 1 · in flight |\n"
        code, _, err = self._run(ledger)
        self.assertEqual(code, 1)
        self.assertIn("empty-input", err)

    def test_reports_an_unreadable_ledger(self):
        out, err = io.StringIO(), io.StringIO()
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = tool.main(["--ledger", "/no/such/run.md", "--repo", self.fixture.repo])
        finally:
            sys.stdout, sys.stderr = stdout, stderr
        self.assertEqual(code, 2)
        self.assertIn("unreadable", err.getvalue())

    def test_the_tip_is_nameable_so_a_merge_does_not_move_it(self):
        self.fixture.issue("34", ["src/a.ts"])
        branch_tip = git(self.fixture.repo, "rev-parse", "HEAD")
        self.fixture.issue("35", ["src/b.ts"])
        code, out, _ = self._run(
            self.fixture.ledger(),
            extra=["--base", self.fixture.base, "--tip", branch_tip],
        )
        self.assertEqual(code, 0)
        # Only the bookkeeping commit of issue 34 is in that range.
        self.assertIn("1 commit(s)", out)


if __name__ == "__main__":
    unittest.main()
