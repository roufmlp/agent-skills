#!/usr/bin/env python3
"""The parked sweep, ruled by the human on 2026-09-13.

Promotion parks a medium or low row that names no blocker, and nothing offers a
parked issue again: not `/run-issues all`, not `next_batch.py`, not
`/harden-issues`. A status with no door back is a deletion with a nicer name, so
this is the door. It lists the parked issues past thirty days and the parked
issues some open issue now names, and prints the `/harden-issues` line for the
second kind. It changes no file.

Run: python3 test_sweep_parked.py
"""

import datetime
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "sweep_parked.py"
sys.path.insert(0, str(HERE))

import sweep_parked  # noqa: E402

TODAY = datetime.date.today()


def days_ago(days: int) -> str:
    return (TODAY - datetime.timedelta(days=days)).isoformat()


def write_issue(root: Path, name: str, status, parked=None, stage=None,
                rows=None, blocked_by=None):
    """One issue file in the tracker's shape. `parked`, `stage` and `rows` are
    the header lines promotion writes; `blocked_by` is a list of bullet bodies,
    None meaning no `## Blocked by` section at all."""
    lines = [f"Status: {status}"]
    if parked is not None:
        lines.append(f"Parked: {parked}")
    if stage is not None:
        lines.append(f"Stage: {stage}")
    if rows is not None:
        lines.append(f"Rows: {rows}")
    lines += ["Sentence: something", "", "# A title", "", "## What to build", "",
              "Words.", ""]
    if blocked_by is not None:
        lines += ["## Blocked by", ""]
        lines += [f"- {entry}" for entry in blocked_by]
        lines += [""]
    (root / f"{name}.md").write_text("\n".join(lines) + "\n")


def write_parked(root: Path, name: str, age_days, **kwargs):
    kwargs.setdefault("stage", "checkout")
    kwargs.setdefault("rows", "rv01-6 operator/medium")
    kwargs.setdefault("blocked_by", ["Unknown until hardened"])
    write_issue(root, name, "parked", parked=days_ago(age_days), **kwargs)


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), str(root), *args],
                          capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TheInterval(Base):
    """Thirty days, the human's ruling of 2026-09-13."""

    def test_only_the_issue_past_the_interval_is_listed(self):
        write_parked(self.root, "70-rounding", 31)
        write_parked(self.root, "71-colour", 2)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70", out.stdout)
        self.assertNotIn("71", out.stdout)

    def test_the_day_of_the_interval_itself_is_not_yet_due(self):
        write_parked(self.root, "70-rounding", 30)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("No parked issue is due", out.stdout)

    def test_the_row_carries_the_severity_the_stage_and_the_age(self):
        write_parked(self.root, "70-rounding", 45, stage="checkout",
                     rows="rv01-6 operator/medium")
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        row = [ln for ln in out.stdout.splitlines() if ln.startswith("70")]
        self.assertEqual(len(row), 1, out.stdout)
        self.assertIn("medium", row[0])
        self.assertIn("checkout", row[0])
        self.assertIn("45 days", row[0])

    def test_a_parked_file_with_no_date_is_listed_and_says_so(self):
        """A file that cannot be shown to be young is shown. The sweep errs
        towards the reader seeing work, never towards hiding it."""
        write_issue(self.root, "70-rounding", "parked", stage="floor",
                    rows="rv01-6 operator/medium",
                    blocked_by=["Unknown until hardened"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70", out.stdout)
        self.assertIn("no Parked: date", out.stdout)

    def test_a_date_that_does_not_parse_is_the_same_as_none(self):
        write_issue(self.root, "70-rounding", "parked", parked="soon",
                    rows="rv01-6 operator/medium",
                    blocked_by=["Unknown until hardened"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("no Parked: date", out.stdout)

    def test_a_missing_severity_or_stage_reads_as_a_dash_not_a_guess(self):
        write_issue(self.root, "70-rounding", "parked", parked=days_ago(40),
                    blocked_by=["Unknown until hardened"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        row = [ln for ln in out.stdout.splitlines() if ln.startswith("70")][0]
        self.assertIn("-", row)
        self.assertNotIn("medium", row)


class WhatNamesIt(Base):
    """Criterion 4. A parked issue another issue waits on is not backlog: it is
    a blocker, and the age has nothing to do with it."""

    def test_a_named_parked_issue_is_listed_and_hardened_whatever_its_age(self):
        write_parked(self.root, "70-rounding", 2)
        write_issue(self.root, "35-note", "ready-for-agent",
                    blocked_by=["70-rounding"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70", out.stdout)
        self.assertIn("/harden-issues 70\n", out.stdout)

    def test_the_row_names_the_issues_that_wait_on_it(self):
        write_parked(self.root, "70-rounding", 2)
        write_issue(self.root, "35-note", "ready-for-agent",
                    blocked_by=["70-rounding"])
        write_issue(self.root, "41-export", "needs-harden",
                    blocked_by=["70-rounding"])
        out = run(self.root)
        row = [ln for ln in out.stdout.splitlines() if ln.startswith("70")][0]
        self.assertIn("35, 41", row)

    def test_a_closed_issue_naming_it_does_not_bring_it_back(self):
        """`done` and `closed` are built. Nothing waits on this one."""
        write_parked(self.root, "70-rounding", 2)
        write_issue(self.root, "35-note", "done", blocked_by=["70-rounding"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("No parked issue is due", out.stdout)

    def test_another_parked_issue_naming_it_does_not_bring_it_back(self):
        """A parked namer is not open work either; two parked issues would
        otherwise hold each other on the list for ever."""
        write_parked(self.root, "70-rounding", 2)
        write_parked(self.root, "71-colour", 2, blocked_by=["70-rounding"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("No parked issue is due", out.stdout)

    def test_an_aged_issue_nobody_names_is_listed_and_not_in_the_harden_line(self):
        write_parked(self.root, "70-rounding", 40)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70", out.stdout)
        self.assertNotIn("/harden-issues", out.stdout)

    def test_the_harden_line_lists_every_named_issue_in_tracker_order(self):
        write_parked(self.root, "71-colour", 2)
        write_parked(self.root, "70-rounding", 2)
        write_issue(self.root, "35-note", "ready-for-agent",
                    blocked_by=["70-rounding", "71-colour"])
        out = run(self.root)
        self.assertIn("/harden-issues 70 71\n", out.stdout)


class WhatItNeverDoes(Base):
    def test_it_writes_no_file(self):
        write_parked(self.root, "70-rounding", 40)
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=None)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        run(self.root)
        after = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_an_issue_that_is_not_parked_is_never_listed(self):
        for status in ("ready-for-agent", "needs-harden", "done", "closed"):
            write_issue(self.root, f"{40 + len(status)}-thing", status,
                        blocked_by=None)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("No parked issue is due", out.stdout)

    def test_a_file_it_cannot_read_is_NAMED_and_the_sweep_carries_on(self):
        """The human's ruling of 2026-09-18. The reading is `next_batch.py`'s,
        imported and not restated, so the scheduler and the sweep can never
        disagree about what a parked issue is.

        On 2026-09-18 one unknown word refused this sweep in both
        repositories and 42 parked issues went unchecked. One file nobody can
        read must cost that file, not the tracker."""
        write_issue(self.root, "70-rounding", "on-hold", blocked_by=None)
        write_parked(self.root, "71-colour", 40)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70-rounding.md", out.stderr)
        self.assertIn("71", out.stdout)

    def test_a_blocked_issue_naming_a_parked_one_puts_it_on_the_list(self):
        """`blocked` is open work: a run stopped on it and it will come back,
        so what it waits on is a blocker and not backlog."""
        write_parked(self.root, "70-rounding", 2)
        write_issue(self.root, "71-colour", "blocked", blocked_by=["`70-rounding`"])
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("70", out.stdout)
        self.assertIn("/harden-issues 70", out.stdout)

    def test_a_directory_that_is_not_there_is_bad_usage(self):
        out = run(self.root / "nowhere")
        self.assertEqual(out.returncode, 2)


class TheCountLine(Base):
    def test_it_says_how_many_are_parked_and_how_many_it_listed(self):
        write_parked(self.root, "70-rounding", 40)
        write_parked(self.root, "71-colour", 2)
        write_parked(self.root, "72-import", 2)
        out = run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("1 of 3 parked issues listed", out.stdout)

    def test_the_empty_sweep_says_how_many_are_parked_and_waiting(self):
        write_parked(self.root, "70-rounding", 2)
        out = run(self.root)
        self.assertIn("No parked issue is due", out.stdout)
        self.assertIn("1 parked", out.stdout)


class TheInterface(unittest.TestCase):
    def test_the_interval_is_thirty_days(self):
        self.assertEqual(sweep_parked.INTERVAL_DAYS, 30)


if __name__ == "__main__":
    unittest.main()
