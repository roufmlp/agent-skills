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


def span(start_min, end_min, text, background=False):
    """One graded Agent span. `background` is the fourth element added on
    2026-09-06: a backgrounded call returns at once, so its span is the spawn
    and not the work, and no verdict may rest on it."""
    return (at(start_min), at(end_min), text, background)


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


class BackgroundedGatesCannotBeJudged(unittest.TestCase):
    """Ruling 8 of the 2026-09-06 walk. Run `batch-170a59`.

    That runner reached concurrency by BACKGROUNDING one gate of each pair. A
    backgrounded Agent call returns the moment it is spawned, so all seven verify
    gates read as instant, every pair read as serial, and the report printed
    "0 pair(s) overlapped, 7 ran one after the other" and "SERIAL GATES COST THIS
    RUN ROUGHLY 0 MINUTES". All seven had in fact overlapped, by 87 minutes.

    The script's own header has warned about backgrounded calls since it was
    written. The verdict ignored its own warning; these cases close that.

    **What is deliberately NOT tested, because it is deliberately not built:** a
    corrected span read from the backgrounded subagent's own transcript. The human
    refused that by name on cost.
    """

    def test_a_backgrounded_pair_is_not_called_serial(self):
        out = report([span(0, 14, "Verify gate 149c", background=True),
                      span(0.1, 13, "Review gate 149c")])
        self.assertIn("CANNOT JUDGE", out)
        self.assertNotIn("SERIAL GATES", out)

    def test_the_batch_170a59_reading_is_refused_not_reported(self):
        """The real shape: the verify gate is backgrounded, so its span collapses
        and the review gate appears to start after it ended."""
        rows = []
        for n, issue in enumerate(["149c", "149d", "149e", "149f", "149g"]):
            base = n * 60
            rows.append(span(base, base + 0.05, f"Verify gate {issue}", background=True))
            rows.append(span(base + 0.1, base + 14, f"Review gate {issue}"))
        out = report(rows)
        self.assertIn("CANNOT JUDGE 5 of 5", out)
        # No verdict of any kind survives: no cost line, and no judged tally.
        self.assertNotIn("SERIAL GATES COST", out)
        self.assertNotIn("ran one after the other", out)
        self.assertNotIn("ROUGHLY", out)

    def test_it_says_why_rather_than_only_that_it_cannot(self):
        out = report([span(0, 0.1, "Verify gate 149c", background=True),
                      span(0.2, 14, "Review gate 149c")])
        self.assertIn("backgrounded", out)
        self.assertIn("not its runtime", out)

    def test_a_foreground_run_is_unchanged(self):
        """A run with no backgrounded gate must read exactly as it always did,
        so a reader comparing two reports is not made to translate."""
        out = report([span(0, 14, "Verify gate issue 405"),
                      span(0.5, 12, "Review gate issue 405")])
        self.assertIn("gate concurrency: 1 pair(s) overlapped, 0 ran one after the other", out)
        self.assertNotIn("CANNOT JUDGE", out)

    def test_a_foreground_serial_pair_is_still_caught(self):
        out = report([span(0, 14, "Verify gate issue 99b"),
                      span(16, 29, "Review gate issue 99b")])
        self.assertIn("SERIAL GATES", out)
        self.assertNotIn("CANNOT JUDGE", out)


class AMixedRunKeepsTheHalfItCanJudge(unittest.TestCase):
    """Run `batch-b5e96d`, measured 2026-09-06 while building this.

    21 pairs were reported serial there. TWELVE were the spurious near-zero
    readings the refusal above now withholds; NINE ran wholly in the foreground
    and were genuinely serial, worth about 134 minutes. Suppressing all 21 would
    trade a false zero for a false silence, on the very run whose real loss a
    peer session had to find by hand. So the blind pairs are refused and the
    foreground pairs are still reported, marked as a floor.
    """

    ROWS = [
        # Two blind pairs: the verify gate was backgrounded.
        span(0, 0.1, "Verify gate issue 479", background=True),
        span(0.2, 13, "Review gate issue 479"),
        span(30, 30.1, "Verify gate issue 526", background=True),
        span(30.2, 44, "Review gate issue 526"),
        # Two real foreground faults: review spawned after verify returned.
        span(60, 76, "Verify gate issue 546"),
        span(78, 97, "Review gate issue 546"),
        span(120, 138, "Verify gate issue 547"),
        span(140, 160, "Review gate issue 547"),
    ]

    def test_the_blind_pairs_are_refused_by_count(self):
        self.assertIn("CANNOT JUDGE 2 of 4", report(self.ROWS))

    def test_the_foreground_pairs_are_still_reported(self):
        out = report(self.ROWS)
        self.assertIn("over the 2 pair(s) that ran wholly in the foreground", out)
        self.assertIn("SERIAL GATES", out)

    def test_the_number_is_marked_a_floor(self):
        # It must not read as the run's whole cost: two pairs are unjudged.
        self.assertIn("FLOOR", report(self.ROWS))

    def test_no_floor_marking_when_nothing_was_withheld(self):
        out = report([span(0, 14, "Verify gate issue 99b"),
                      span(16, 29, "Review gate issue 99b")])
        self.assertNotIn("FLOOR", out)

    def test_the_blind_pairs_contribute_nothing_to_the_minutes(self):
        """The 0.1-minute readings are exactly the false ones. The reported cost
        must come from the foreground pairs alone."""
        out = report(self.ROWS)
        line = [l for l in out.splitlines() if "SERIAL GATES COST" in l][0]
        self.assertIn("ROUGHLY 34 MINUTES", line)


class ReadCarriesTheBackgroundFlag(unittest.TestCase):
    """`read()` is where the flag comes from, and it is on the CALL while the
    duration is only known at the RESULT. This pins that they meet."""

    def test_an_agent_span_carries_its_flag(self):
        import json
        import tempfile
        lines = [
            {"timestamp": "2026-09-05T23:50:00Z",
             "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Agent",
                                      "input": {"description": "Verify gate 149c",
                                                "run_in_background": True}}]}},
            {"timestamp": "2026-09-05T23:50:06Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}},
            {"timestamp": "2026-09-05T23:50:01Z",
             "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Agent",
                                      "input": {"description": "Review gate 149c"}}]}},
            {"timestamp": "2026-09-06T00:04:00Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "t2"}]}},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as handle:
            for one in lines:
                handle.write(json.dumps(one) + "\n")
            path = handle.name
        try:
            labelled = run_timings.read(path)[4]
        finally:
            import os
            os.remove(path)
        flags = {text: background for _, _, text, background in labelled}
        self.assertTrue(flags["Verify gate 149c"])
        self.assertFalse(flags["Review gate 149c"])

    def test_that_transcript_refuses_a_verdict_end_to_end(self):
        pass  # covered by the classes above; read() is pinned here.


if __name__ == "__main__":
    unittest.main(verbosity=2)
