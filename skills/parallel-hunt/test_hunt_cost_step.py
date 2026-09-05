#!/usr/bin/env python3
"""A hunt measures itself, and it must do so before it deletes its ledger.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 3, ruling 12: one set of cost scripts for a run and a hunt. Until it,
`parallel-hunt` had no cost script at all, so a hunt's cost was not measured
whatever model it ran on.

The order is the part worth a test rather than a sentence. Every script finds
the session by reading `round-brief.md`, and round end DELETES that file. A run
cannot lose this way -- `run.md` is committed and readable for ever -- so
nothing else in this pipeline has taught the lesson.

Sitting 4 added a fifth reading, `run_quality.py`, and it loses more than the
other four: it also reads `round-journal.md`, which sits beside the brief, so a
round that deletes first can never say whether its own model trial held.

    python3 -m unittest test_hunt_cost_step
"""

from __future__ import annotations

import pathlib
import re
import unittest

SKILL = pathlib.Path(__file__).resolve().parent / "SKILL.md"

SCRIPTS = ("run_costs.py", "harness_cost.py", "orchestrator_cost.py",
           "run_timings.py", "run_quality.py")


class HuntTakesTheReadings(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_every_script_is_named_with_a_batch_id(self):
        for script in SCRIPTS:
            self.assertIn(f"{script} --batch <hunt-id>", self.text,
                          f"{script} is not wired into the round end")

    def test_run_costs_is_told_not_to_append_a_hunt_row(self):
        """`run-costs.md` is one row per RUN and its columns are a run's. A
        hunt row there is read as a run for as long as the table lives."""
        self.assertIn("run_costs.py --batch <hunt-id> --no-append", self.text)

    def test_the_readings_come_before_the_brief_is_deleted(self):
        """Step 6 states the round-end order in one sentence. The readings sit
        in it, ahead of the deletion, because after the deletion no ledger
        names the hunt and the round can never be measured."""
        step = re.search(r"^6\. Round end, in this order:(.+?)\n\n",
                         self.text, re.M | re.S)
        self.assertIsNotNone(step, "step 6 no longer states an order")
        sentence = step.group(1)
        # The count in that sentence changes as readings are added, so the
        # phrase pinned here is the one that carries the RULE.
        readings = sentence.find("readings")
        deletion = sentence.find("delete `round-brief.md`")
        self.assertNotEqual(readings, -1,
                            "step 6 does not mention the readings")
        # Flattened: a sentence in a markdown file wraps where the column
        # runs out, and a raw substring check would pin the line breaks.
        self.assertIn("before the brief is deleted", " ".join(sentence.split()))
        self.assertNotEqual(deletion, -1)
        self.assertLess(readings, deletion,
                        "the readings must precede the deletion of the ledger "
                        "they read")

    def test_the_stated_count_matches_the_commands_in_the_block(self):
        """The block said "all four" over five commands for one edit.

        A reader told to run four and given five runs four, and the one they
        drop is the last line -- which is `run_quality.py`, the reading whose
        ledger is deleted moments later.
        """
        found = re.search(
            r"Run all (\w+) with this round's hunt id.*?```(.*?)```",
            self.text, re.S)
        self.assertIsNotNone(found, "the readings block no longer says a count")
        stated, block = found.group(1), found.group(2)
        commands = [line for line in block.splitlines() if line.strip()]
        words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                 7: "seven", 8: "eight"}
        self.assertEqual(stated, words.get(len(commands)),
                         f"the block holds {len(commands)} command(s) and the "
                         f"sentence above it says {stated}")

    def test_the_reason_for_the_order_is_stated_and_not_just_the_order(self):
        """An order with no reason is a rule an editor reorders in good faith."""
        self.assertIn("must run while it still exists", self.text)
        self.assertIn("no ledger names this hunt", self.text)


if __name__ == "__main__":
    unittest.main()
