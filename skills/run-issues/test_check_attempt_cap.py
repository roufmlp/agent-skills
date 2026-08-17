#!/usr/bin/env python3
"""Tests for check_attempt_cap.

The row fixtures copy two real ledger formats: an older run's
`implement …; retry 1 …` stamps and a newer run's
`queued → in-progress → gates` stamps. Neither numbers its attempts, which is
why the cap counts an explicit `attempt N` marker and refuses when it finds
none it can trust.
"""

import unittest

from check_attempt_cap import (
    Decision,
    count_markers,
    decide,
    find_row,
)

LEDGER = """Owner: run-issues-batch-0a1b2c
Worktree: `/tmp/wt`

Scope, as given: **147, 318, 321b**.

## Status

| Issue | Status | Estimate | Stamps |
|---|---|---|---|
| 147 | **done** | medium | attempt 1 02:35→02:50; gates r1 **both reject** (**strike 1**); attempt 2 03:07→03:25; gates r2 **both pass** |
| 318 — the generic-product road | **in-progress** | ~2.5h | attempt 1 02:37 queued → 04:10 in-progress |
| 321b — the staff may pick a version | **in-progress** | ~2h | attempt 1 08:37; **criteria reset**; attempt 2 09:14; **criteria reset**; attempt 3 10:02 |
| 288 | **blocked** | large | attempt 1 01:00; attempt 2 02:00; attempt 3 03:00 |
| 293 | **queued** | small | |
"""


class FindRow(unittest.TestCase):
    def test_finds_a_bare_numeric_issue(self):
        self.assertIn("attempt 1 02:35", find_row(LEDGER, "147"))

    def test_finds_an_issue_whose_cell_carries_a_title(self):
        self.assertIn("02:37 queued", find_row(LEDGER, "318"))

    def test_finds_a_lettered_issue(self):
        self.assertIn("criteria reset", find_row(LEDGER, "321b"))

    def test_does_not_match_a_prefix_of_another_issue(self):
        """`32` must not match the `321b` row."""
        self.assertIsNone(find_row(LEDGER, "32"))

    def test_returns_none_for_an_issue_not_in_the_table(self):
        self.assertIsNone(find_row(LEDGER, "999"))


NUMBERED = """## Status

| # | issue | estimate | status | stamps |
|---|---|---|---|---|
| 1 | 314 — the sign-in refusal names the wrong limit | medium | queued | |
| 2 | 281 — withdrawn purchase order reads as a win | medium | in-progress | attempt 1; attempt 2; attempt 3 |
| 3 | 288 — quote landing in the deal room | medium | queued | |
"""


class NumberedLedgerFormat(unittest.TestCase):
    """The `| # | issue | …` layout puts the id in the second cell.

    Read naively, `--issue 1` matches the row-number column and returns issue
    314's row. That is a cap authorising a spawn off the wrong row.
    """

    def test_finds_the_issue_by_id_not_by_row_number(self):
        self.assertIn("314", find_row(NUMBERED, "314"))

    def test_a_row_number_is_not_an_issue_id(self):
        self.assertIsNone(find_row(NUMBERED, "1"))

    def test_counts_attempts_on_the_right_row(self):
        d = decide(NUMBERED, "281")
        self.assertFalse(d.allowed)
        self.assertIn("3 attempts", d.reason)

    def test_a_queued_row_in_this_format_authorises_attempt_one(self):
        d = decide(NUMBERED, "314")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 1)


class CountMarkers(unittest.TestCase):
    def test_counts_explicit_attempt_markers(self):
        self.assertEqual(count_markers(find_row(LEDGER, "147"), "attempt"), 2)

    def test_counts_a_single_attempt(self):
        self.assertEqual(count_markers(find_row(LEDGER, "318"), "attempt"), 1)

    def test_counts_criteria_resets(self):
        row = find_row(LEDGER, "321b")
        self.assertEqual(count_markers(row, "criteria reset"), 2)

    def test_an_empty_row_counts_zero(self):
        self.assertEqual(count_markers(find_row(LEDGER, "293"), "attempt"), 0)

    def test_a_timestamp_is_never_read_as_an_attempt_number(self):
        """`retry 00:18` and `retry 10.2` are a clock and a duration."""
        row = "| 165 | done | m | implement 00:17, retry 00:18→00:29, retry 10.2 |"
        self.assertEqual(count_markers(row, "attempt"), 0)

    def test_criteria_fault_reset_is_the_same_marker(self):
        row = "| 9 | x | y | attempt 1; **criteria-fault reset**; attempt 2 |"
        self.assertEqual(count_markers(row, "criteria reset"), 1)


class Decide(unittest.TestCase):
    def test_a_queued_issue_authorises_attempt_one(self):
        d = decide(LEDGER, "293")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 1)

    def test_one_attempt_so_far_authorises_attempt_two(self):
        d = decide(LEDGER, "318")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 2)

    def test_two_attempts_so_far_authorises_the_escalated_third(self):
        d = decide(LEDGER, "147")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 3)

    def test_three_attempts_refuses_the_fourth(self):
        d = decide(LEDGER, "288")
        self.assertFalse(d.allowed)
        self.assertEqual(d.attempt, 4)
        self.assertIn("3 attempts", d.reason)

    def test_two_resets_refuses_the_third(self):
        d = decide(LEDGER, "321b")
        self.assertFalse(d.allowed)
        self.assertIn("2 criteria resets", d.reason)

    def test_a_missing_row_refuses_rather_than_assuming_a_fresh_issue(self):
        d = decide(LEDGER, "999")
        self.assertFalse(d.allowed)
        self.assertIn("no row", d.reason.lower())

    def test_the_refusal_prints_the_count_it_refused_on(self):
        self.assertIn("3", decide(LEDGER, "288").reason)

    def test_a_ledger_with_no_status_table_refuses(self):
        d = decide("Owner: x\n\nnothing here\n", "147")
        self.assertFalse(d.allowed)

    def test_a_legacy_row_refuses_rather_than_counting_zero(self):
        """`implement …; retry 1 …` carries attempts this cap cannot count.

        Reading it as a fresh issue would authorise a fourth attempt on a row
        that already spent three, which is the exact failure the cap exists to
        stop. It refuses and asks for the row to be restamped.
        """
        legacy = (
            "| Issue | Status | Estimate | Stamps |\n"
            "|---|---|---|---|\n"
            "| 147 | **done** | medium | implement 02:35→02:50; gates r1 "
            "**both reject** (**strike 1**); retry 1 03:07→03:25 |\n"
        )
        d = decide(legacy, "147")
        self.assertFalse(d.allowed)
        self.assertIn("cannot count", d.reason.lower())

    def test_a_queued_row_with_no_stamps_is_not_mistaken_for_legacy(self):
        d = decide(LEDGER, "293")
        self.assertTrue(d.allowed)

    def test_decision_is_a_plain_value(self):
        self.assertIsInstance(decide(LEDGER, "293"), Decision)


if __name__ == "__main__":
    unittest.main()
