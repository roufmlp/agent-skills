#!/usr/bin/env python3
"""Refuses superseded wording in the steering files.

Built 2026-09-01.

**The defect this closes.** The 2026-08-29 sweep found eighteen instances of one
shape: a rule ruled in one file while another file kept the old wording, and the
old wording won locally, because the agent reading it had no way to know a newer
ruling existed. Every one of those was repaired by hand. Nothing refused the
next one.

The structure that prevents the drift already existed — a SKILL.md holds rules,
its `decisions.md` holds incidents, `~/.claude/questionrules.md` holds question
rules, CLAUDE.md holds pointers. What was missing was the refusal. This is it.

**The whole maintenance contract is one sentence: when a ruling retires wording,
its phrase joins RETIRED below.** Nothing else is asked of anybody. That is
deliberate — by the human's own three-class test a proposal must refuse something or
state a fact nobody wrote down, and "remember to sweep the citing files" is the
class that has already failed repeatedly in this system.

**Why each entry carries its replacement.** A guard is graded by whether its
message names the act that would prevent a repeat, not by whether it refuses.
`check_verdict.py` refused a lone gate spawn and named the missing VERDICT,
which is the symptom, and the same slip happened again on the next attempt
because nothing named the missing SPAWN. So a red here does not merely say "this
sentence is retired" — it says what superseded it, on what date, and where the
ruling is recorded.

**`decisions.md` files are exempt, and that is load-bearing.** They quote
retired wording on purpose: as history, and as the supersession notes that stop
somebody re-deriving a dead rule from an old entry. Two entries in
`run-issues/decisions.md` do exactly that. Scanning them would make the guard
unusable within a week, and a guard somebody switches off is worse than none.
The scan set below is rules-only for that reason.

Run: python3 test_retired_phrases.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retired_phrases import (  # the one home; see that module's docstring
    CLAUDE_HOME,
    RETIRED,
    contains as hits_in,
    scan_set,
    squash,
)


class TestNoRetiredPhraseSurvives(unittest.TestCase):
    """The refusal itself."""

    def test_the_scan_set_is_readable_and_not_empty(self):
        """Fail closed. A moved directory or a renamed file must go red here
        rather than quietly shrinking what the guard covers to nothing."""
        files, problems = scan_set()
        self.assertEqual(problems, [], "the guard could not read what it polices")
        self.assertGreater(len(files), 20, "the scan set collapsed")

    def test_no_steering_file_carries_a_retired_phrase(self):
        files, problems = scan_set()
        self.assertEqual(problems, [])
        texts = {f: f.read_text(encoding="utf-8") for f in files}
        for phrase, superseded_by in RETIRED:
            for path, text in texts.items():
                with self.subTest(phrase=phrase, file=path.name):
                    self.assertFalse(
                        hits_in(text, phrase),
                        f"\n  {path} carries retired wording: {phrase!r}"
                        f"\n  What replaced it: {superseded_by}"
                        f"\n  Repair the file. If the phrase is being quoted as"
                        f" history, it belongs in a decisions.md, which this"
                        f" guard does not read.",
                    )

    def test_every_retired_phrase_names_what_superseded_it(self):
        """An entry with no replacement turns a red into a puzzle, which is the
        `check_verdict.py` failure: a guard that names the symptom and not the
        act that would prevent a repeat."""
        for phrase, superseded_by in RETIRED:
            with self.subTest(phrase=phrase):
                self.assertTrue(superseded_by.strip())
                self.assertGreater(
                    len(superseded_by), 40, "too short to tell anyone what to write"
                )

    def test_the_list_is_not_empty(self):
        """An empty denylist is a green that polices nothing."""
        self.assertTrue(RETIRED)

    def test_no_phrase_is_listed_twice(self):
        phrases = [p.lower() for p, _ in RETIRED]
        self.assertEqual(len(phrases), len(set(phrases)))


class TestTheDetectorActuallyDetects(unittest.TestCase):
    """The mutation, driven rather than described.

    `test_no_steering_file_carries_a_retired_phrase` is green today because the
    tree is clean. A green that would also be green with a broken matcher
    proves nothing, so these drive a phrase back in and require the red.
    """

    def test_a_reintroduced_phrase_is_caught(self):
        for phrase, _ in RETIRED:
            with self.subTest(phrase=phrase):
                self.assertTrue(hits_in(f"prefix {phrase} suffix", phrase))

    def test_a_reintroduced_phrase_is_caught_across_a_line_break(self):
        """The reflow case. A hard wrap must not launder a retired sentence."""
        for phrase, _ in RETIRED:
            words = phrase.split()
            if len(words) < 2:
                continue
            wrapped = " ".join(words[:2]) + "\n    " + " ".join(words[2:])
            with self.subTest(phrase=phrase):
                self.assertTrue(hits_in(wrapped, phrase))

    def test_a_reintroduced_phrase_is_caught_in_a_different_case(self):
        for phrase, _ in RETIRED:
            with self.subTest(phrase=phrase):
                self.assertTrue(hits_in(phrase.upper(), phrase))

    def test_unrelated_prose_is_not_caught(self):
        """A guard that fires on ordinary text gets switched off."""
        innocent = (
            "The session settles a split it can cut, harden and stamp itself, "
            "and routes anything wider by the table in questionrules.md."
        )
        for phrase, _ in RETIRED:
            with self.subTest(phrase=phrase):
                self.assertFalse(hits_in(innocent, phrase))


class TestDecisionsFilesAreExempt(unittest.TestCase):
    """The exemption, asserted rather than assumed.

    A later editor tidying `scan_set` into "every markdown file under
    ~/.claude" would break the supersession notes that stop somebody
    re-deriving a dead rule. This is what stops that edit.
    """

    def test_no_decisions_file_is_in_the_scan_set(self):
        files, _ = scan_set()
        for path in files:
            with self.subTest(file=str(path)):
                self.assertNotEqual(path.name, "decisions.md")

    def test_decisions_files_exist_and_are_therefore_deliberately_skipped(self):
        """If none existed, the exemption above would be vacuous."""
        found = sorted((CLAUDE_HOME / "skills").glob("*/decisions.md"))
        self.assertTrue(found, "no decisions.md files — the exemption proves nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
