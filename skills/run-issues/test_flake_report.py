#!/usr/bin/env python3
"""Cases for flake_report.py, the reader of run_suite.py's flake ledger.

    python3 -m unittest test_flake_report
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent / "flake_report.py"


class TheReport(unittest.TestCase):

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.scratch.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def tearDown(self):
        self.scratch.cleanup()

    def write(self, *entries):
        with open(self.repo / ".git" / "run-suite-flakes.jsonl", "a") as handle:
            for file, started in entries:
                handle.write(json.dumps({"file": file, "started": started,
                                         "stage": "issue"}) + "\n")

    def report(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo)],
                              capture_output=True, text=True, timeout=30)

    def test_no_ledger_says_so(self):
        done = self.report()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no flake recorded", done.stdout)

    def test_files_are_listed_most_flakes_first_and_a_repeat_is_marked(self):
        self.write(("tests/a.test.ts", "2026-10-05T10:00:00+00:00"),
                   ("tests/b.test.ts", "2026-10-06T09:00:00+00:00"),
                   ("tests/b.test.ts", "2026-10-06T11:00:00+00:00"))
        lines = self.report().stdout.splitlines()
        rows = [line for line in lines if "tests/" in line]
        self.assertIn("tests/b.test.ts", rows[0])
        self.assertIn("2", rows[0])
        self.assertIn("repeat", rows[0])
        self.assertIn("2026-10-06", rows[0])
        self.assertNotIn("repeat", rows[1])

    def test_a_torn_line_is_skipped(self):
        self.write(("tests/a.test.ts", "2026-10-05T10:00:00+00:00"))
        with open(self.repo / ".git" / "run-suite-flakes.jsonl", "a") as handle:
            handle.write('{"file": "tests/c.te')
        done = self.report()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("tests/a.test.ts", done.stdout)


if __name__ == "__main__":
    unittest.main()
