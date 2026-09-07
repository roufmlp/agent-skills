#!/usr/bin/env python3
"""Tests for the shape of harden-issues/SKILL.md itself.

This file is the harden-issues half of the refusal `run-issues/test_skill_structure.py`
already carries for its own skill. Same machine, same reason, and the reason is
worth restating because it is the whole point of the two lists below.

A slimming pass moves history out of a SKILL body and into `decisions.md`, so
the provenance stops being billed on every invocation. The failure mode is not
that the pass forgets a story. It is that a passage READS as history and is a
rule wearing narrative clothes, and the move takes the rule away with the story.
Nothing about the resulting file looks wrong. The panel review of 2026-08-22
marked that gap on the run-issues side, and these lists are the answer to it
here.

  SKILL_MARKS      the rule sentence each move must LEAVE BEHIND. Asserted
                   present in SKILL.md. If a move takes the anchor with the
                   story, this goes red.
  DECISIONS_MARKS  the story each move took, paired with its ONE HOME.
                   Asserted present in that home AND absent from SKILL.md.

**The two lists are written at different times, deliberately.** Every anchor
goes in before one line moves, so the anchor test is already green and already
watching while the edits happen. A story joins the second list only once it has
landed in a decisions file. A passage in neither list is one nobody has moved
yet, not one exempt from the rule.

A moved story does not always land in this skill's own `decisions.md`, and the
home is not always a decisions file. Two of the first three moves deleted a
SECOND copy of a story whose home was already elsewhere — the 2026-08-09
prohibition incident in `run-issues/decisions.md`, and the one illustration of
it that `run-issues/SKILL.md` deliberately keeps loaded. That duplication is
the defect this whole exercise exists to remove, so each story is paired with
the file that is its one home, and the test checks that file.

The checks read the live files, not fixtures. That is deliberate: these are
claims about the files as they stand, and a fixture would pass while the real
file drifted.

Run: python3 test_skill_structure.py
"""

import unittest
from pathlib import Path

HARDEN = Path(__file__).resolve().parent
SKILLS = HARDEN.parent

SKILL = HARDEN / "SKILL.md"
DECISIONS = HARDEN / "decisions.md"
RUN_ISSUES_DECISIONS = SKILLS / "run-issues" / "decisions.md"

# The rule each move must leave behind. Written before the first move.
SKILL_MARKS = [
    # Fan-out: the prohibition rule, whose incident lives in run-issues.
    "**A prohibition in a brief names the SYSTEM, not the verb.**",
    # No terminal full stop: the move turned this sentence's period into a
    # semicolon introducing the pointer. The clause is the rule; the
    # punctuation is not. Same correction the run-issues list carries.
    "Adopted by the human, 2026-08-09",
    # The unattacked-issue refusal, whose two dead gates are the story.
    "An issue nobody attacked is never stamped",
    # The model rule. The Fable history is the story; this is the instruction.
    "To harden on Fable, launch the session on Fable.",
    # Class 3, R1.
    "pins the property, not the count of surviving tests",
    # Class 4, the drill rule and the reminder it must not become.
    "A drill must name the red it produces AND a wrong reason it could go red",
    "Do not answer this class by asking an implementer to check their own drill",
    # Class 4, the evidence-home rule. The widening is a RULE, not a story, so
    # it is anchored here: a move that carried it out would narrow the rule
    # back to the issue file alone, which is the 2026-08-16 regression.
    "may never ask for evidence to land somewhere the party it names cannot",
    "any closed home",
    # Class 11.
    "**Joint satisfiability.**",
    "a cut strands criteria written against the whole",
    # The mark rule, and the sentence inside its parenthetical that is a rule
    # rather than an incident.
    "or the mark is refused at authoring time",
    "a question outside those four classes never takes the mark at all",
    # The graded-home refusal, whose 99b measurement is the story.
    "**A default with neither is an unstamped issue**",
    # The minting prohibition.
    "**The pass never mints.**",
    # The quoted-phrase citation rule, whose 228-citation incident is the story.
    "Every citation you WRITE from 2026-08-26 onward quotes text, never a line",
    "is the guard that makes it stick",
    # Ticket 33 ruling 5, 2026-09-07: one never-attack rule for every caller.
    # The rule is the row test; the blanket rule it replaced is the story.
    "skip any issue whose row in any `runs/<batch-id>/run.md`",
    "in any run, whoever is calling",
    "Run A's launch phase runs while run B is live",
    # Ticket 33 ruling 7: where a run's findings land.
    "A run's findings go to `runs/<batch-id>/harden/`",
    # Ticket 33 ruling 2: the two roles are in the model map, so a spawn inside
    # a run carries a model. The old blanket "never pass a model" is reversed
    # for that half only, and the standalone half is unchanged.
    "carry the ledger's value for the role on every spawn",
    # Ticket 33 ruling 16, sitting 2: the third entry point. A run's launch
    # calls this pass, and the standalone pass survives beside it (ruling 6).
    # Without the anchor a slim that thinned the entry-point list back to two
    # would leave the fold with no door named in the skill it walks through.
    "Three entry points, same pass",
    "Inside a run's launch",
]

# The story each move took, and the file it landed in. Filled as each move
# lands, never before.
DECISIONS_MARKS = [
    # M1 and M2 moved nothing: both stories were ALREADY resident in
    # run-issues/decisions.md, and this skill carried a second full copy. The
    # marks below are what those copies said, so a paste-back goes red.
    ("three files landed at the shared worktree root", RUN_ISSUES_DECISIONS),
    # The one illustration run-issues/SKILL.md deliberately keeps loaded. Its
    # home is that skill body, not a decisions file — hence the pairing.
    ("QA is the only WRITABLE", SKILLS / "run-issues" / "SKILL.md"),
    (
        "Two adversarial gates died at the weekly usage limit during the"
        " 2026-08-15 workflow audit and wrote nothing at all",
        RUN_ISSUES_DECISIONS,
    ),
    # M12 — the Fable pin's history, whose home is the 2026-08-02 section.
    ("credit-gated", DECISIONS),
    # M3 — class 3, R1.
    ("all 69 tests passed", DECISIONS),
    ("a permissive-regex swap satisfies", DECISIONS),
    # M4 — class 4, D4. The second mark is the mutation-testing refusal: it is
    # the reason nobody should re-propose it, so it must stay findable.
    ("Ten guards in that batch were green while proving nothing", DECISIONS),
    ("it runs the suite per mutant, and against 6,385 tests", DECISIONS),
    # M5 — class 4, the evidence-home incidents. The WIDENING is a rule and
    # stays in SKILL.md; only the two incidents moved.
    ("filed the contradiction as `rg305-06`", DECISIONS),
    ("One annulled rejection and one wasted gate round, in one batch", DECISIONS),
    # M6 — class 11.
    ("296, 327, 332, 335, 419b", DECISIONS),
    # M7 — the unmeasured mark. The questionrules sentence is a rule and stays.
    ("the pilot holds 151 supplier rows with 151 distinct", DECISIONS),
    # M8 — the 99b measurement.
    ("was 1417 lines, of which 368 were graded", DECISIONS),
    ("Two implementer spawns and four gate spawns", DECISIONS),
    # M10 — the citation repair cost.
    ("broke 228 citations across 49 open issue files", DECISIONS),
    # M9 — the pass that ran ahead of the no-minting rule.
    ("minted two more into it, leaving the queue", DECISIONS),
    # M13 — the blanket never-attack rule ticket 33 ruling 5 replaced, and why
    # it could not survive the fold.
    ("skip EVERYTHING if any ledger's owner line named a live session", DECISIONS),
]


def read(path):
    return path.read_text(encoding="utf-8")


def squash(text):
    """Collapse every run of whitespace to one space.

    Marks are compared against this rather than the raw file. These are
    hard-wrapped markdown documents, so a sentence that fits on one line today
    sits across two the moment anything before it grows by a word — and the
    very edits this test polices are the ones that reflow paragraphs. A guard
    that goes red on a reflow is a guard somebody switches off.
    """
    return " ".join(text.split())


class TestTheSlimLeftEveryRuleBehind(unittest.TestCase):
    """The refusal: a move may not carry its rule out with the story."""

    def test_every_anchor_is_still_in_the_skill(self):
        """A move that carried its rule out with the story goes red here, and
        only here — a reader would not notice."""
        skill = squash(read(SKILL))
        for mark in SKILL_MARKS:
            with self.subTest(mark=mark):
                # assertTrue, not assertIn: assertIn prints the whole haystack,
                # and the haystack here is a 30 KB file. A red that buries its
                # own message under the entire document is a red somebody
                # switches off.
                self.assertTrue(
                    squash(mark) in skill,
                    f"a slim move took its rule anchor with it: {mark!r}",
                )

    def test_every_moved_story_is_present_in_its_one_home(self):
        """A move that deleted the story without it landing anywhere is a lost
        record, not a slim."""
        for mark, target in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertTrue(
                    squash(mark) in squash(read(target)),
                    f"story is not in its declared home {target.name}: {mark!r}",
                )

    def test_no_moved_story_is_still_resident_in_the_skill(self):
        """A move that copies rather than moves saves nothing and doubles the
        maintenance surface — which is the defect this pass exists to close."""
        skill = squash(read(SKILL))
        for mark, _target in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertFalse(
                    squash(mark) in skill,
                    f"story is still resident in SKILL.md: {mark!r}",
                )

    def test_the_anchor_list_is_not_empty(self):
        """An empty catalogue is a green that means no work was done."""
        self.assertTrue(SKILL_MARKS)

    def test_no_story_is_listed_as_its_own_anchor(self):
        """The two lists must not intersect: one string cannot be required to
        be present in and absent from the same file."""
        stories = {mark for mark, _ in DECISIONS_MARKS}
        self.assertEqual(set(SKILL_MARKS) & stories, set())


class TestTheDecisionsFileIsTheDeclaredHome(unittest.TestCase):
    """The skill must keep saying where its provenance went.

    Without this the slim is reversible by an editor who reads the thinned
    SKILL.md, cannot see why it is thin, and starts writing history back into
    it. The pointer is the only thing that tells them.
    """

    def test_the_skill_points_at_its_decisions_file(self):
        skill = squash(read(SKILL))
        self.assertIn("decisions.md", skill)
        self.assertIn("read it when changing this skill, not", skill)

    def test_the_decisions_file_exists_beside_the_skill(self):
        self.assertTrue(DECISIONS.is_file())


class TheThirdEntryPointIsNamed(unittest.TestCase):
    """Ticket 33 of the pilot-delivery map, ruling 16, sitting 2.

    Deliverable 3 gives this pass a third caller: a `/run-issues` launch that
    finds an unstamped issue in its scope. Ruling 6 kept the standalone pass,
    so the fold ADDS a door rather than replacing one, and the count in the
    lead-in sentence is the thing that goes stale silently -- a reader who
    counts two doors concludes a run cannot call this pass at all.
    """

    def setUp(self):
        self.raw = read(SKILL)
        self.skill = squash(self.raw)

    def entry_block(self):
        """The entry-point list, from its lead-in to the next `## ` heading."""
        start = self.raw.index("entry points, same pass:")
        rest = self.raw[start:]
        stop = rest.find("\n## ")
        return rest[:stop] if stop > 0 else rest

    def test_the_lead_in_says_three(self):
        self.assertIn("Three entry points, same pass", self.skill)

    def test_the_count_word_matches_the_bullets_it_counts(self):
        """Mechanical, because the count is prose and the list is data. A
        fourth caller added without touching the word leaves the sentence
        lying, and nothing else in the file would notice."""
        bullets = [line for line in self.entry_block().splitlines()
                   if line.startswith("- **")]
        self.assertEqual(len(bullets), 3,
                         f"the lead-in says three; the list holds {len(bullets)}")

    def test_the_third_door_names_the_file_that_drives_it(self):
        """The phase is specified in `run-issues/launch-harden.md` and nowhere
        else. A door that does not name it sends the reader back to a
        `/run-issues` SKILL.md that deliberately holds only the trigger."""
        block = squash(self.entry_block())
        self.assertIn("Inside a run's launch", block)
        self.assertIn("launch-harden.md", block)

    def test_the_third_door_states_its_own_trigger(self):
        """An unstamped issue in a run's scope. Any other reading turns the
        fold on for every run, including the ones with nothing to harden."""
        block = squash(self.entry_block())
        self.assertIn("Hardened:", block)

    def test_the_standalone_door_survived_the_fold(self):
        """Ruling 6, and it is the half easiest to lose: the fold reads like a
        replacement. The human kept the attended pass for an issue they want to
        rule on before any code is written."""
        self.assertIn("Standalone, pre-batch", self.skill)

    def test_the_phase_file_the_third_door_names_is_on_disk(self):
        """The pointer and the file are in different skills' directories, so
        nothing else joins them."""
        self.assertTrue((SKILLS / "run-issues" / "launch-harden.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
