#!/usr/bin/env python3
"""Marks on `run-compare/SKILL.md` that a later edit must not undo.

    python3 -m unittest test_skill_structure

Ticket 37 of the pilot-delivery map, sitting 5, rulings 22, 25 and 26. Held by
a test rather than by a note, because CLAUDE.md's own three-class rule says so:
a change that can refuse gets built, and a change that asks an agent to
remember does not work.

Ruling 22 splits the work in two: `run_compare.py` holds fixed subcommands and
IS the fact; the skill answers a question in words over its output. The three
rules below are what keeps that split from closing.
"""

from __future__ import annotations

import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE / "SKILL.md"
READER = (HERE.parent / "run-issues" / "run_compare.py")


class TheSkillIsThin(unittest.TestCase):
    """Ruling 22: it runs the script and answers over its output. It never
    writes and never measures."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        # Phrase checks read the FLATTENED text. Where a phrase falls across a
        # line break is not a fact worth pinning, and a test that broke on
        # rewrapping would be a test people rewrap the prose to satisfy.
        self.flat = " ".join(self.text.split())

    def test_it_names_the_script_it_reads(self):
        self.assertIn("run_compare.py", self.text)

    def test_it_names_every_one_of_the_five_subcommands(self):
        """Ruling 24 fixes them, so a skill that offered a sixth would be
        inventing a reading nothing measured."""
        for word in ("last", "show", "since", "compare", "versions"):
            self.assertRegex(self.flat, rf"`run_compare\.py {word}\b")

    def test_it_forbids_itself_every_writing_road(self):
        """A reader that wrote would make asking a question change the answer.
        `run_costs.py` at a finale is the only writer of both records, and
        `run_records.write_view` the only writer of the page."""
        self.assertRegex(self.flat, r"never writes?\b")
        self.assertIn("run_costs.py", self.text)

    def test_it_forbids_measuring_of_its_own(self):
        """The figures are the record's. A skill that opened a transcript
        would be a second reader of a quantity `run_costs.py` already
        measures, and two readers of one quantity drift."""
        self.assertRegex(self.flat, r"never measures?\b")


class TheWordsItMayUse(unittest.TestCase):
    """Ruling 25: figures, directions, and a figure named as outside its
    observed range. No cause and no advice."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        # Phrase checks read the FLATTENED text. Where a phrase falls across a
        # line break is not a fact worth pinning, and a test that broke on
        # rewrapping would be a test people rewrap the prose to satisfy.
        self.flat = " ".join(self.text.split())

    def test_it_says_no_cause_and_no_advice(self):
        self.assertIn("no cause", self.flat.lower())
        self.assertIn("no advice", self.flat.lower())

    def test_it_says_a_figure_outside_its_range_is_named(self):
        self.assertIn("observed range", self.flat)

    def test_the_one_threshold_is_named_as_the_only_one(self):
        """Ruling 14: one threshold, on the cache read-to-write ratio.
        Everything else is direction and range, never an alarm."""
        self.assertIn("cache", self.flat.lower())
        self.assertRegex(self.flat.lower(), r"(one|only) threshold")


class TheModelAndTheSpawns(unittest.TestCase):
    """Ruling 26: on the session model, spawning nothing."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        # Phrase checks read the FLATTENED text. Where a phrase falls across a
        # line break is not a fact worth pinning, and a test that broke on
        # rewrapping would be a test people rewrap the prose to satisfy.
        self.flat = " ".join(self.text.split())

    def test_it_says_it_spawns_nothing(self):
        self.assertRegex(self.flat, r"spawn(s|ing)? nothing")

    def test_it_names_no_agent_to_spawn(self):
        """A skill naming a subagent type is one an agent will spawn. This one
        answers in the session it was typed in."""
        self.assertNotIn("subagent_type", self.text)
        self.assertNotIn("Agent tool", self.text)

    def test_it_states_no_model_of_its_own(self):
        """Ruling 26 puts it on the SESSION model. A `model:` key in the
        frontmatter would be a second answer to a question ticket 39 settled
        for the whole loop."""
        head = self.text.split("---")[1]
        self.assertNotRegex(head, r"^model:", )


class TheFrontmatter(unittest.TestCase):

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        # Phrase checks read the FLATTENED text. Where a phrase falls across a
        # line break is not a fact worth pinning, and a test that broke on
        # rewrapping would be a test people rewrap the prose to satisfy.
        self.flat = " ".join(self.text.split())

    def test_it_opens_with_frontmatter_naming_the_skill(self):
        self.assertTrue(self.text.startswith("---\n"))
        head = self.text.split("---")[1]
        self.assertIn("name: run-compare", head)
        self.assertIn("description:", head)

    def test_the_description_says_when_to_use_it(self):
        head = self.text.split("---")[1]
        found = re.search(r"description:\s*(.+)", head)
        self.assertTrue(found)
        self.assertGreater(len(found.group(1)), 60)


class TheReaderItPointsAt(unittest.TestCase):

    def test_the_script_is_where_the_skill_says_it_is(self):
        """Ruling 26 puts this skill beside `run-issues` in the same
        repository, and the script it reads stays in `run-issues` because a
        finale is what writes the records it reads."""
        self.assertTrue(READER.is_file(), f"{READER} is gone")


if __name__ == "__main__":
    unittest.main()
