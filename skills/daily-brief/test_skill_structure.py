#!/usr/bin/env python3
"""Marks on `daily-brief/SKILL.md` that a later edit must not undo.

    python3 -m unittest test_skill_structure

Ticket 37 of the pilot-delivery map, sitting 4, ruling 27: **one reader.** The
cost block and the estimate reading become a call to `run_compare.py last`,
and the "row above" prose is deleted with its cause.

Held by a test rather than by a note, because CLAUDE.md's own three-class rule
says so: a change that can refuse gets built, and a change that asks an agent
to remember does not work. The prose this file refuses was correct when it was
written and stayed in place for five days after the table's own rule stopped
being true.
"""

from __future__ import annotations

import pathlib
import unittest

SKILL = pathlib.Path(__file__).resolve().parent / "SKILL.md"


class TheCostBlockCallsTheReader(unittest.TestCase):

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_it_runs_run_compare_last(self):
        """Ruling 27. One reader of `runs.jsonl`, not two."""
        self.assertIn("run_compare.py last", self.text)

    def test_the_row_above_rule_is_gone(self):
        """Ruling 12 replaced it: a line compares against the previous line of
        the SAME KIND by finale time. Ticket 38 puts two runs and a hunt in
        flight at once, so the row above is not the run before, and
        `run-costs.md` is now generated from `runs.jsonl` in an order no
        reader should be reading positionally.
        """
        for phrase in ("the row above it", "the row above",
                       "compare a row against the row"):
            self.assertNotIn(phrase, self.text,
                             f"`{phrase}` is ruling 12's own cause and is "
                             "deleted (ruling 27)")

    def test_the_brief_no_longer_opens_the_generated_view_itself(self):
        """`run-costs.md` is GENERATED from `runs.jsonl` (ruling 2) and the
        brief reads the reader's output, not the page. It may still NAME the
        page, which ruling 13 makes the one-look page."""
        self.assertNotIn("Read\n`.scratch/workflow-audit/run-costs.md`",
                         self.text)

    def test_the_invent_no_alarm_rule_survives_with_its_one_exception(self):
        """Ruling 14 allows exactly one threshold, on the cache read-to-write
        ratio. The brief's older rule was absolute, and the exception has to
        be written down or the next reader restores the absolute form."""
        self.assertIn("Invent no alarm threshold", self.text)
        self.assertIn("cache read-to-write", self.text)

    def test_the_borrowed_rows_keep_their_explanation(self):
        """Ruling 3 keeps every row and sitting 2's mark is what makes keeping
        them safe. The reader prints the count; the brief still has to say
        what the mark means."""
        self.assertIn("borrowed", self.text)
        self.assertIn("aa94b3b", self.text)


class TheRankerStandsInForTheUnsortedList(unittest.TestCase):
    """Ticket 33 ruling 19, 2026-09-07: the brief prints the ranked fifteen in
    place of the unsorted list. The ranker itself belongs to the reader's own repo; this is the one line
    the skill owed it."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_the_brief_runs_the_ranker(self):
        self.assertIn("node scripts/what-is-owed.mjs --next 15", self.text)

    def test_the_ranked_block_has_its_heading(self):
        self.assertIn('headed "Next fifteen"', self.text)

    def test_the_unsorted_list_is_no_longer_a_section(self):
        self.assertNotIn("an `unsorted` list that has grown since yesterday", self.text)
        self.assertIn("The `unsorted` list is never printed", self.text)


if __name__ == "__main__":
    unittest.main()
