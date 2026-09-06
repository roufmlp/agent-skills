#!/usr/bin/env python3
"""Cases for migrate_view.py — ticket 37, ruling 3.

"All 18 rows are kept. The backfilled rows are marked, the duplicate
`review-375cbf` row is deleted once by hand with the reason in the header.
Added by the human: no existing history may be lost."

The migration is a one-time script and it is tested because of that sentence.
A parser that silently dropped a row would lose history that nothing else
holds: the eleven backfilled rows were read from transcripts on 2026-08-30 and
`orchestrator_cost.py` reads a WEEK window, so most of them can no longer be
re-derived.

    python3 -m unittest test_migrate_view
"""

from __future__ import annotations

import unittest

import migrate_view as tool

TABLE = """# What each run cost itself

Some prose the parser must not read as a row.

| Taken | Version | Issues | Hours | Weighted | Per issue | Subagents | Orchestrator | Idle | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-08-16 | not stated | 9 | not read | 72.6M | 1.67M | 52 | 21% | not read | backfilled |
| 2026-08-23 | not stated | 5 | not read | 37.6M | 1.22M | 31 | 16% | not read | backfilled |
| 2026-08-23 | not stated | 3 | not read | 52.5M | 2.14M | 28 | 12% | not read | backfilled |
| 2026-08-31 | 2.1.251 (Claude Code) | 8 | 8.48 | 56.9M | 1.69M | 43 | 24% | 17% | run `batch-88624c`. Ten issues scoped. |

**A correction paragraph typed between two rows on 2026-08-31.** This is what
made the table unparseable, and the parser must skip it.

| 2026-09-01 | 2.1.251 | 16 | 16.16 | 118.9M | 1.34M | 77 | 18% | 13% | run `review-375cbf`. Sixteen issues. |
| 2026-09-01 | 2.1.251 | 16 | 16.2 | 119.8M | 1.40M | 77 | 19% | 13% | run `review-375cbf`. Sixteen issues. |
| 2026-09-06 | 2.1.261 | 6 | 8.06 | opus 51.9M | opus 8.66M | 28 | opus 13% | 23% | run `batch-170a59`. Six slices. |
"""


class ItReadsEveryRow(unittest.TestCase):

    def test_prose_between_rows_does_not_stop_the_parse(self):
        """The exact fault that forced this ticket. Seven data rows sit in the
        fixture and three of them are BELOW the correction paragraph; six
        records come back, because the duplicate is dropped."""
        found = tool.parse(TABLE)
        self.assertEqual(6, len(found))
        self.assertIn("batch-170a59", [r["batch"] for r in found])

    def test_a_prose_paragraph_is_not_read_as_a_row(self):
        for record in tool.parse(TABLE):
            self.assertTrue(record["taken"].startswith("2026-"))

    def test_the_header_row_is_not_a_record(self):
        self.assertNotIn("Taken", [r["taken"] for r in tool.parse(TABLE)])


class ItKeepsTheHistory(unittest.TestCase):

    def test_the_batch_id_is_taken_from_the_note(self):
        found = [r["batch"] for r in tool.parse(TABLE)]
        self.assertIn("batch-88624c", found)
        self.assertIn("batch-170a59", found)

    def test_a_backfilled_row_is_marked(self):
        backfilled = [r for r in tool.parse(TABLE) if r.get("backfilled")]
        self.assertEqual(3, len(backfilled))

    def test_a_backfilled_row_gets_a_stable_synthetic_key(self):
        """It carries no batch id: the eleven rows were read from transcripts
        after the fact and the table records only a date. The record is keyed
        by batch id, so a key is synthesised, marked, and kept stable so a
        re-run of the migration produces the same file."""
        first = tool.parse(TABLE)
        second = tool.parse(TABLE)
        self.assertEqual([r["batch"] for r in first], [r["batch"] for r in second])

    def test_two_backfilled_rows_on_one_date_get_different_keys(self):
        """2026-08-23 carries two rows. One key for both would silently drop
        one of them at the duplicate refusal, which is history lost."""
        keys = [r["batch"] for r in tool.parse(TABLE) if r.get("backfilled")]
        self.assertEqual(len(keys), len(set(keys)))

    def test_a_synthetic_key_says_it_is_synthetic(self):
        """Nobody may mistake it for a real batch id and go looking for a
        ledger that never existed."""
        for record in tool.parse(TABLE):
            if record["batch"].startswith("backfilled-"):
                self.assertTrue(record["batch_synthetic"], record["batch"])

    def test_a_row_that_is_not_backfilled_can_still_need_a_synthetic_key(self):
        """The two facts are independent and the live table proves it. The
        2026-08-30 row is a real finale row -- its note reads "first run with
        the two new hooks; both misfired (rn99f-02)" -- but it names no batch
        id, because `run_costs.py` only started writing one into the note
        later. It gets a synthetic key and it is NOT backfilled."""
        text = TABLE.replace(
            "| 2026-08-31 | 2.1.251 (Claude Code) | 8 | 8.48 | 56.9M | 1.69M | 43 | 24% | 17% | run `batch-88624c`. Ten issues scoped. |",
            "| 2026-08-30 | claude-opus-5 | 9 | 15.02 | 88.9M | 1.48M | 52 | 15% | 12% | first run with the two new hooks; both misfired |")
        row = [r for r in tool.parse(text) if r["taken"] == "2026-08-30"][0]
        self.assertTrue(row["batch_synthetic"])
        self.assertFalse(row.get("backfilled"))
        self.assertEqual("first run with the two new hooks; both misfired",
                         row["note"])

    def test_a_real_batch_id_is_not_marked_synthetic(self):
        for record in tool.parse(TABLE):
            if not record.get("backfilled"):
                self.assertFalse(record.get("batch_synthetic"))


class TheDuplicateIsDeletedOnce(unittest.TestCase):
    """Ruling 3 and ruling 4. Ticket 36's fault 9."""

    def test_the_second_line_for_a_batch_is_dropped(self):
        kept = tool.parse(TABLE)
        self.assertEqual(1, [r["batch"] for r in kept].count("review-375cbf"))

    def test_the_first_of_the_two_is_the_one_kept(self):
        """Not "the last wins". The first is what the run's own merge briefing
        quoted, so keeping it is what makes the record agree with the briefing
        already written."""
        kept = [r for r in tool.parse(TABLE) if r["batch"] == "review-375cbf"][0]
        self.assertEqual(16.16, kept["hours"])

    def test_the_drop_is_reported_and_not_silent(self):
        _, dropped = tool.parse_with_report(TABLE)
        self.assertEqual(1, len(dropped))
        self.assertIn("review-375cbf", dropped[0])


class ItReadsTheFigures(unittest.TestCase):

    def test_a_weighted_cell_becomes_a_number_per_model(self):
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-170a59"][0]
        self.assertEqual({"opus": 51900000.0}, row["weighted"])

    def test_an_unmodelled_weighted_cell_is_filed_under_not_stated(self):
        """Every row before 2026-09-06 wrote a bare figure, and ticket 39
        sitting 3 measured that 13 of the top 14 sessions mixed models. So the
        number is real and the model behind it is genuinely unknown -- which is
        a different thing from no figure at all."""
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-88624c"][0]
        self.assertEqual({"not stated": 56900000.0}, row["weighted"])

    def test_not_read_becomes_absent_rather_than_zero(self):
        """The eleven backfilled rows carry no Hours and no Idle. A zero would
        say the run took no time."""
        row = [r for r in tool.parse(TABLE) if r.get("backfilled")][0]
        self.assertIsNone(row.get("hours"))
        self.assertIsNone(row.get("idle"))

    def test_a_percentage_becomes_a_fraction(self):
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-170a59"][0]
        self.assertAlmostEqual(0.23, row["idle"])

    def test_the_version_suffix_is_dropped(self):
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-88624c"][0]
        self.assertEqual("2.1.251", row["version"])

    def test_the_note_is_carried_and_the_batch_prefix_removed(self):
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-170a59"][0]
        self.assertEqual("Six slices.", row["note"])

    def test_a_carried_note_is_never_truncated(self):
        """Ruling 15 caps a note at 160 characters and ruling 3 says no
        existing history may be lost. They collide on six live rows, whose
        notes run to 538 characters, and ruling 3 wins for what already
        exists: truncating them would have dropped 1,293 characters, measured
        on 2026-09-06. The cap binds what a finale writes from now on."""
        long_note = "run `batch-zzz`. " + "w" * 400
        text = TABLE.replace("run `batch-170a59`. Six slices.", long_note)
        row = [r for r in tool.parse(text) if r["batch"] == "batch-zzz"][0]
        self.assertEqual(400, len(row["note"]))

    def test_a_carried_row_is_marked_carried(self):
        """That mark is what lets the writer exempt it from the cap without
        opening a hole a finale could write through."""
        for record in tool.parse(TABLE):
            self.assertTrue(record["carried"])


class TheCountsAreNull(unittest.TestCase):

    def test_no_carried_row_claims_a_quality_figure(self):
        for record in tool.parse(TABLE):
            self.assertTrue(all(v is None for v in record["quality"].values()))


class BorrowedColumnsAreMarked(unittest.TestCase):
    """Found on 2026-09-06 by the daily brief, and landed on main as commits
    `09db35d1` and `c6005ddc` while this sitting was being built.

    Until skills commit `aa94b3b` (2026-09-06, 00:49) `run_costs.py` scraped
    five of its ten columns -- Issues, Subagents, Weighted, Orchestrator and
    Per issue -- out of `orchestrator_cost.py --days 7`'s LAST data row,
    whatever run that row described. Only Hours and Idle were the run's own.

    Ruling 3 keeps every row, so the mark is what makes keeping them safe: a
    machine-readable record with no mark is exactly how sitting 4's
    `run_compare.py` would compute a trend over another run's numbers.

    The test is a MEASUREMENT, not the date. The header states the check:
    divide Weighted by Per issue and see whether it lands on the row's own
    Issues. Measured over the live file on 2026-09-06, 18 of 19 rows do not,
    and the one that does is `batch-170a59`, the first row written after the
    repair."""

    def test_a_row_whose_figures_disagree_is_marked_borrowed(self):
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-88624c"][0]
        self.assertIn("weighted", row["borrowed"])
        self.assertIn("issues", row["borrowed"])

    def test_a_self_consistent_row_is_not_marked(self):
        """`batch-170a59`: 51.9M over 8.66M is 6, and the row says 6 issues."""
        row = [r for r in tool.parse(TABLE) if r["batch"] == "batch-170a59"][0]
        self.assertNotIn("borrowed", row)

    def test_hours_and_idle_are_never_marked_borrowed(self):
        """They were read from the run's own transcript throughout, and
        marking them would throw away the two columns that are sound."""
        for record in tool.parse(TABLE):
            self.assertNotIn("hours", record.get("borrowed", ()))
            self.assertNotIn("idle", record.get("borrowed", ()))

    def test_a_row_with_no_figures_to_check_is_marked_rather_than_cleared(self):
        """Absence of evidence is not evidence the row is sound. Every row
        before the repair was written by the same code."""
        text = TABLE.replace(
            "| 2026-08-16 | not stated | 9 | not read | 72.6M | 1.67M | 52 | 21% | not read | backfilled |",
            "| 2026-08-16 | not stated | 9 | not read | not read | not read | 52 | 21% | not read | backfilled |")
        row = [r for r in tool.parse(text) if r["taken"] == "2026-08-16"][0]
        self.assertIn("weighted", row["borrowed"])

    def test_the_view_shows_the_mark(self):
        """A reader of the page must see it, not only a reader of the JSON."""
        import run_records
        text = run_records.render_view(tool.parse(TABLE))
        self.assertIn("borrowed", text.lower())


if __name__ == "__main__":
    unittest.main()
