#!/usr/bin/env python3
"""The decisions in `check_commit_order.py`, driven with no git.

Every row here is copied from run `batch-34455f`'s ledger, 2026-08-25. Two of
its nine rows carry a commit stamped before the correction round it contains,
and both read as healthy under the rule this check replaces.
"""

import os
import tempfile
import unittest

import check_commit_order as guard

# Trimmed from the real ledger. The full rows carry the gate history as well;
# the parser must reach the two times through all of it.
LEDGER = """
## Status

| Issue | Est | Status | Stamps |
|---|---|---|---|
| 413b — a tender line that names a brand | 30-45 min | **done** | gates open 06:43 → correction: open 07:06 → closed 07:28 (5 items) → committed `e9737396` 07:02 |
| 412 — the registers take one at a time | 2-2.5 h | **done** | correction: open 10:30 → closed 10:32 (4 guard gaps) → committed `bb7ff4f0` 10:34 |
| 419 — an issue with no correction round | 1 h | **done** | verify: pass, review: pass 11:00 → committed `abc1234` 11:05 |
"""


class RowsTest(unittest.TestCase):
    def test_it_reads_both_times_through_the_rest_of_the_row(self):
        rows = guard.rows_from(LEDGER)
        self.assertEqual([r["issue"] for r in rows], ["413b", "412"])
        self.assertEqual(rows[0]["closed"], "07:28")
        self.assertEqual(rows[0]["sha"], "e9737396")
        self.assertEqual(rows[0]["stamped"], "07:02")

    def test_a_row_with_no_correction_round_is_not_graded(self):
        """Nothing to be out of order with, so silence is the right answer."""
        self.assertNotIn("419", [r["issue"] for r in guard.rows_from(LEDGER)])

    def test_prose_outside_the_table_is_ignored(self):
        text = "The run committed `deadbee` 09:00 after the correction closed 08:00.\n"
        self.assertEqual(guard.rows_from(text), [])


class JudgeTest(unittest.TestCase):
    def row(self, closed, sha="e9737396", stamped="07:02", issue="413b"):
        return {"issue": issue, "closed": closed, "sha": sha, "stamped": stamped}

    def test_the_413b_fault_is_refused(self):
        """Correction closed 07:28; git says the commit landed at 07:02."""
        detail = guard.judge(self.row("07:28"), "07:02")
        self.assertIsNotNone(detail)
        self.assertIn("26 minute(s) BEFORE", detail)

    def test_the_413_fault_is_refused(self):
        row = self.row("10:00", sha="da0ce42b", stamped="08:05", issue="413")
        detail = guard.judge(row, "08:05")
        self.assertIn("115 minute(s) BEFORE", detail)

    def test_a_commit_after_its_round_holds(self):
        """412: correction closed 10:32, committed 10:34."""
        row = self.row("10:32", sha="bb7ff4f0", stamped="10:34", issue="412")
        self.assertIsNone(guard.judge(row, "10:34"))

    def test_a_commit_in_the_same_minute_holds(self):
        """The bar is ordering, not a gap. A round closing as the commit lands
        is the tightest legitimate case there is, and refusing it would be the
        misfire `check_attempt_cap.py:13-14` warns about."""
        self.assertIsNone(guard.judge(self.row("10:34"), "10:34"))

    def test_one_minute_early_is_still_early(self):
        """422 on this run: closed 12:32, committed 12:31. The briefing did not
        name it and the check does, which is the point of a check."""
        detail = guard.judge(self.row("12:32", sha="8d484155", issue="422"), "12:31")
        self.assertIn("1 minute(s) BEFORE", detail)

    def test_git_decides_it_and_not_the_ledger_stamp(self):
        """The ledger stamp may agree with the round and git may not.

        This is the whole reason the check moved: rule 9 compared the ledger's
        stamp against git, and the runner writes one from the other.
        """
        row = self.row("07:28", stamped="07:30")
        self.assertIsNotNone(guard.judge(row, "07:02"))


class PlainColumnTest(unittest.TestCase):
    """Register row `rn414a-01`, run `414a-483-286335` of 2026-08-30.

    The reader demanded `| 483 — title |` and matched nothing against a ledger
    writing the id in a column of its own. It then printed `ok`, having read
    zero rows, over a commit stamped before the round it carried.
    """

    PLAIN = """
| Issue | Est | Status | Notes |
| --- | --- | --- | --- |
| 501 | 2h | done | attempt 1 correction: closed 07:28 committed `e9737396` 07:02 |
| 502 | 1h | done | attempt 1, no correction round |
"""

    def test_a_row_with_no_em_dash_is_still_read(self):
        rows = guard.rows_from(self.PLAIN)
        self.assertEqual([row["issue"] for row in rows], ["501"])
        self.assertEqual(rows[0]["closed"], "07:28")
        self.assertEqual(rows[0]["sha"], "e9737396")

    def test_the_denominator_counts_every_row_not_only_the_graded_ones(self):
        self.assertEqual([issue for issue, _ in guard.status_rows(self.PLAIN)], ["501", "502"])

    def test_the_header_row_is_not_counted_as_an_issue(self):
        self.assertNotIn("Issue", [issue for issue, _ in guard.status_rows(self.PLAIN)])

    def test_the_em_dash_shape_still_reads(self):
        self.assertEqual([issue for issue, _ in guard.status_rows(LEDGER)], ["413b", "412", "419"])

    def test_an_id_second_behind_a_row_number_is_read_from_the_header(self):
        numbered = """
| # | Issue | Status |
| --- | --- | --- |
| 1 | 501 | done, correction: closed 07:28 committed `e9737396` 07:02 |
"""
        self.assertEqual([issue for issue, _ in guard.status_rows(numbered)], ["501"])


class MainTest(unittest.TestCase):
    def test_an_unreadable_ledger_exits_two(self):
        self.assertEqual(guard.main(["--ledger", "/nonexistent/run.md"]), 2)

    def test_a_ledger_with_no_status_row_is_refused_not_passed(self):
        """`ok` on zero rows is the fault this check was found by. A table it
        cannot read is a table it cannot grade, so it exits 2."""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write("# Run 999\n\nNo table here at all.\n")
            path = handle.name
        try:
            self.assertEqual(guard.main(["--ledger", path]), 2)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()


class TheCommitClockIsOptional(unittest.TestCase):
    """The human deleted the ledger's per-step clocks on 2026-08-31.

    `rows_from` needs BOTH patterns to match, so while the commit's own `HH:MM`
    was required, the first ledger written without it would have graded zero
    rows and printed `ok`. Git supplies the time this check compares; the
    ledger's commit stamp was only ever quoted back in the refusal.
    """

    ROW = ("| 483 | 1 h | **done** | correction: open → closed 07:28 (2 items) "
           "→ committed `e9737396` |")

    def test_a_row_with_no_commit_clock_is_still_graded(self):
        rows = guard.rows_from(f"| Issue | Est | Status | Stamps |\n|---|---|---|---|\n{self.ROW}\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["closed"], "07:28")
        self.assertEqual(rows[0]["sha"], "e9737396")
        self.assertIsNone(rows[0]["stamped"])

    def test_the_refusal_reads_without_a_ledger_stamp(self):
        row = {"issue": "483", "closed": "07:28", "sha": "e9737396", "stamped": None}
        detail = guard.judge(row, "07:02")
        self.assertIn("26 minute(s) BEFORE", detail)
        self.assertNotIn("None", detail)

    def test_the_ledger_stamp_is_still_quoted_when_it_is_there(self):
        row = {"issue": "483", "closed": "07:28", "sha": "e9737396", "stamped": "07:02"}
        self.assertIn("reads 07:02", guard.judge(row, "07:02"))
