#!/usr/bin/env python3
"""Drill for report_brief_cap.py.

The one thing this file exists to pin: a MISSING record reads as "no data" and
never as "no refusals". The record lives in a temporary directory, by scrub rule
H6 of `~/code/agent-skills/MANIFEST.md`, so it can be swept away between a
refusal and the finale. A reader that answered "zero refusals" there would hand
the next reader of ticket 40 a measurement nobody took.

    python3 test_report_brief_cap.py
"""

from __future__ import annotations

import io
import contextlib
import json
import pathlib
import tempfile
import unittest

import report_brief_cap as reader


def record(lines) -> pathlib.Path:
    """Write a throwaway record and return its path."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="briefcap-"))
    path = root / "run-issues-brief-cap.jsonl"
    path.write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8"
    )
    return path


def entry(outcome, words, at=1000.0, cwd="/tmp/tree"):
    return {"at": at, "outcome": outcome, "words": words, "cap": 400,
            "attempt": 1, "cwd": cwd}


def report(path, **kwargs) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = reader.main(["--record", str(path)] + [
            item for key, value in kwargs.items()
            for item in (f"--{key.replace('_', '-')}", str(value))
        ])
    return code, out.getvalue() + err.getvalue()


class AMissingRecord(unittest.TestCase):
    def test_reads_as_no_data(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="briefcap-"))
        code, text = report(root / "nothing.jsonl")
        self.assertEqual(code, 0)
        self.assertIn("NO DATA", text)

    def test_says_in_words_that_it_is_not_zero_refusals(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="briefcap-"))
        _, text = report(root / "nothing.jsonl")
        self.assertIn("not the same as no refusals", text)

    def test_an_empty_record_reads_as_no_data_too(self):
        self.assertIn("NO DATA", report(record([]))[1])


class Counting(unittest.TestCase):
    def test_it_reports_how_often_the_cap_refused(self):
        path = record([entry("refused", 900), entry("passed", 310),
                       entry("refused", 620)])
        _, text = report(path)
        self.assertIn("2 refused", text)

    def test_it_reports_every_outcome_by_name(self):
        path = record([entry("refused", 900), entry("passed", 310),
                       entry("exempt-retry", 1500),
                       entry("exempt-correction", 1200)])
        _, text = report(path)
        for word in ("refused", "passed", "exempt-retry", "exempt-correction"):
            self.assertIn(word, text)

    def test_it_names_the_length_of_every_refusal(self):
        _, text = report(record([entry("refused", 913)]))
        self.assertIn("913", text)

    def test_it_reports_what_the_runner_then_cut_to(self):
        """Ruling 16's second half. The brief re-issued after a refusal is
        another first attempt, so the pass that follows a refusal is the cut."""
        path = record([entry("refused", 900, at=10.0),
                       entry("passed", 340, at=20.0)])
        _, text = report(path)
        self.assertIn("900 -> 340", text)

    def test_two_refusals_in_a_row_each_name_what_actually_followed_them(self):
        """The runner cuts, is refused again, and cuts once more. Pairing the
        first refusal with the eventual pass would report the second as though
        nothing had followed it, which is the opposite of what happened."""
        path = record([entry("refused", 1500, at=10.0),
                       entry("refused", 900, at=20.0),
                       entry("passed", 350, at=30.0)])
        _, text = report(path)
        self.assertIn("1500 -> 900", text)
        self.assertIn("900 -> 350", text)
        self.assertNotIn("1500 -> 350", text)
        self.assertNotIn("nothing followed", text)

    def test_the_outcome_counts_are_ordered_the_same_way_every_time(self):
        """A tie must not order itself off dict insertion order, or the same
        record reads differently on two runs."""
        first = record([entry("refused", 900), entry("passed", 310)])
        second = record([entry("passed", 310), entry("refused", 900)])
        counts = lambda text: [l for l in text.splitlines() if "refused" in l][0]
        self.assertEqual(counts(report(first)[1]), counts(report(second)[1]))

    def test_a_refusal_nothing_followed_is_reported_as_unanswered(self):
        _, text = report(record([entry("refused", 900, at=10.0)]))
        self.assertIn("nothing followed", text)

    def test_a_pass_before_a_refusal_is_not_read_as_its_answer(self):
        path = record([entry("passed", 340, at=10.0),
                       entry("refused", 900, at=20.0)])
        _, text = report(path)
        self.assertIn("nothing followed", text)

    def test_the_cap_in_force_is_reported_from_the_record(self):
        _, text = report(record([entry("refused", 900)]))
        self.assertIn("400", text)

    def test_two_caps_in_one_record_are_both_named(self):
        """The number moved once already. A record spanning the move must not
        report one of them as though it were the whole run's cap."""
        path = record([entry("refused", 900), dict(entry("passed", 310), cap=300)])
        _, text = report(path)
        self.assertIn("300", text)
        self.assertIn("400", text)


class Filtering(unittest.TestCase):
    def test_a_tree_filter_keeps_only_that_trees_spawns(self):
        path = record([entry("refused", 900, cwd="/tmp/a"),
                       entry("refused", 800, cwd="/tmp/b")])
        _, text = report(path, tree="/tmp/a")
        self.assertIn("1 refused", text)
        self.assertNotIn("800", text)

    def test_a_tree_filter_matches_a_worktree_under_it(self):
        path = record([entry("refused", 900, cwd="/tmp/a/.claude/worktrees/x")])
        _, text = report(path, tree="/tmp/a")
        self.assertIn("1 refused", text)

    def test_a_since_filter_drops_older_lines(self):
        path = record([entry("refused", 900, at=10.0),
                       entry("refused", 800, at=100.0)])
        _, text = report(path, since=50)
        self.assertIn("1 refused", text)
        self.assertNotIn("900", text)

    def test_a_filter_that_matches_nothing_reads_as_no_data(self):
        """Not "no refusals". The same trap as a missing file."""
        _, text = report(record([entry("refused", 900, cwd="/tmp/a")]),
                         tree="/tmp/elsewhere")
        self.assertIn("NO DATA", text)


class Robustness(unittest.TestCase):
    def test_an_unreadable_line_is_skipped_and_counted(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="briefcap-"))
        path = root / "r.jsonl"
        path.write_text(
            json.dumps(entry("refused", 900)) + "\nnot json at all\n",
            encoding="utf-8",
        )
        code, text = report(path)
        self.assertEqual(code, 0)
        self.assertIn("1 refused", text)
        self.assertIn("1 unreadable", text)

    def test_a_line_missing_its_fields_never_raises(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="briefcap-"))
        path = root / "r.jsonl"
        path.write_text(json.dumps({"outcome": "refused"}) + "\n",
                        encoding="utf-8")
        self.assertEqual(report(path)[0], 0)

    def test_it_never_refuses_anything(self):
        """A report is not a gate. Ticket 38 rules that a run never halts, and
        this runs at the finale, where a non-zero exit would read as a fault."""
        self.assertEqual(report(record([entry("refused", 900)]))[0], 0)

    def test_the_default_record_is_the_hooks_own_path(self):
        self.assertTrue(reader.default_record().startswith(tempfile.gettempdir()))
        self.assertTrue(
            reader.default_record().endswith("run-issues-brief-cap.jsonl")
        )


if __name__ == "__main__":
    unittest.main()
