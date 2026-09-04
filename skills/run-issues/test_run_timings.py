#!/usr/bin/env python3
"""Cases for run_timings.py's gate pairing.

Written 2026-09-04 with the correction it grades. The old serial_gates() paired
gates by proximity in time alone and reported 39 minutes of loss on run
`batch-44d0a8` that had never happened. Every case below that starts `false_`
replays one of those real readings and asserts it is no longer reported.
"""
import datetime
import io
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import run_timings  # noqa: E402

T0 = datetime.datetime(2026, 9, 3, 12, 0, 0, tzinfo=datetime.timezone.utc)


def at(minutes):
    return T0 + datetime.timedelta(minutes=minutes)


def span(start_min, end_min, text):
    return (at(start_min), at(end_min), text)


def report(rows):
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_timings.serial_gates(rows)
    return buf.getvalue()


class PairKey(unittest.TestCase):
    def test_reads_issue_and_attempt(self):
        self.assertEqual(run_timings.pair_key("Review gate 312b attempt 2"), "312b@2")

    def test_missing_attempt_is_its_own_bucket(self):
        self.assertEqual(run_timings.pair_key("Verify gate issue 250"), "250@?")

    def test_letter_suffix_survives(self):
        self.assertEqual(run_timings.pair_key("Verify gate issue 312d"), "312d@?")

    def test_no_issue_is_unreadable(self):
        self.assertEqual(run_timings.pair_key("Coherence finale"), "")


class Pairing(unittest.TestCase):
    def test_pair_spawned_together_is_parallel(self):
        out = report([span(0, 14, "Verify gate issue 405"),
                      span(0.5, 12, "Review gate issue 405")])
        self.assertIn("1 pair(s) overlapped, 0 ran one after the other", out)
        self.assertNotIn("SERIAL GATES", out)

    def test_same_pair_twenty_minutes_apart_is_serial(self):
        out = report([span(0, 14, "Verify gate issue 405"),
                      span(20, 33, "Review gate issue 405")])
        self.assertIn("0 pair(s) overlapped, 1 ran one after the other", out)
        self.assertIn("SERIAL GATES", out)

    def test_lone_gate_is_not_a_pair(self):
        out = report([span(0, 14, "Verify gate issue 405")])
        self.assertIn("0 pair(s) overlapped, 0 ran one after the other", out)

    def test_unreadable_label_is_counted_not_guessed(self):
        out = report([span(0, 14, "Verify gate issue 405"),
                      span(0.5, 12, "Review gate issue 405"),
                      span(1, 9, "a gate with no issue in its name")])
        self.assertIn("1 gate step(s) named no issue", out)
        self.assertIn("1 pair(s) overlapped", out)

    def test_third_entry_under_one_key_is_not_a_second_pair(self):
        out = report([span(0, 14, "Verify gate issue 405"),
                      span(0.5, 12, "Review gate issue 405"),
                      span(40, 52, "Review gate issue 405")])
        self.assertIn("1 pair(s) overlapped, 0 ran one after the other", out)


class FalseReadingsFromBatch44d0a8(unittest.TestCase):
    """The three the old shape reported. None may be reported again."""

    def test_false_two_different_issues(self):
        out = report([span(0, 15, "Review gate 312b attempt 2"),
                      span(15, 27, "Verify gate issue 312d")])
        self.assertIn("0 ran one after the other", out)
        self.assertNotIn("SERIAL GATES", out)

    def test_false_attempt_two_after_attempt_one_250(self):
        out = report([span(0, 16, "Review gate issue 250"),
                      span(16, 29, "Verify gate 250 attempt 2")])
        self.assertIn("0 ran one after the other", out)

    def test_false_attempt_two_after_attempt_one_392(self):
        out = report([span(0, 18, "Review gate issue 392"),
                      span(18, 33, "Verify gate 392 attempt 2")])
        self.assertIn("0 ran one after the other", out)

    def test_all_three_together_report_nothing(self):
        out = report([span(0, 15, "Review gate 312b attempt 2"),
                      span(15, 27, "Verify gate issue 312d"),
                      span(30, 46, "Review gate issue 250"),
                      span(46, 59, "Verify gate 250 attempt 2"),
                      span(60, 78, "Review gate issue 392"),
                      span(78, 93, "Verify gate 392 attempt 2")])
        self.assertIn("0 ran one after the other", out)
        self.assertNotIn("SERIAL GATES", out)


class HalvesMustDiffer(unittest.TestCase):
    """Found by running the patched tool on the real transcript, 2026-09-04.

    The first version of this fix grouped by `<issue>@<attempt>` alone, and issue
    349's two VERIFY gates — two attempts whose labels carried no marker — were
    compared against each other. It printed "Verify gate issue 349 followed Verify
    gate issue 349". A round is one verify and one review.
    """

    def test_two_verify_gates_are_not_a_pair(self):
        out = report([span(0, 14, "Verify gate issue 349"),
                      span(20, 34, "Verify gate issue 349")])
        self.assertIn("0 pair(s) overlapped, 0 ran one after the other", out)
        self.assertNotIn("SERIAL GATES", out)

    def test_two_review_gates_are_not_a_pair(self):
        out = report([span(0, 14, "Review gate issue 349"),
                      span(20, 34, "Review gate issue 349")])
        self.assertIn("0 ran one after the other", out)

    def test_critical_review_still_counts_as_review(self):
        self.assertEqual(run_timings.gate_half("Critical review gate for 99e"), "review")
        out = report([span(0, 14, "Verify gate issue 99e"),
                      span(0.5, 16, "Critical review gate for 99e")])
        self.assertIn("1 pair(s) overlapped", out)


class StillCatchesTheRealFault(unittest.TestCase):
    """The 2026-08-27 reading that made this report worth having."""

    def test_review_spawned_after_verify_returned(self):
        out = report([span(0, 14, "Verify gate issue 99b"),
                      span(16, 29, "Review gate issue 99b"),
                      span(40, 55, "Verify gate issue 99c"),
                      span(57, 70, "Review gate issue 99c")])
        self.assertIn("0 pair(s) overlapped, 2 ran one after the other", out)
        self.assertIn("SERIAL GATES", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
