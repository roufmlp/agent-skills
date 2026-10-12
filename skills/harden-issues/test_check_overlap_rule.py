#!/usr/bin/env python3
"""Tests for check_overlap_rule.py. Run: python3 test_check_overlap_rule.py

The human's ruling `q-fin-671b22-04` of 2026-10-06. One tracker's issue 370, a credit
Undo, spent four attempts and two criteria resets in run `batch-671b22`, every rejection
in one class: two writes on the same job at the same moment. Both resets found the
criteria short of a bounded overlap rule, not the code short of a fix. The fixtures
below are cut down from that Undo.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_overlap_rule as check  # noqa: E402

SCRIPT = pathlib.Path(__file__).parent / "check_overlap_rule.py"

PLAIN = "1. **The credit sheet shows the earlier decline.** A test reads the sheet.\n"

UNDO = (
    "2. **Undo after \"Approve credit\" appends and never deletes.** The server refuses\n"
    "   the Undo once a line this approval moved stands anywhere but `Confirmed`.\n"
    "   Writers: an Accept on a line of the job, Confirm the order, a credit decline,\n"
    "   a second Undo of the same approval.\n"
    "   Readers: `creditHeld`, `standingRow` and the Undo window.\n"
    "   Loser sees: \"That did not save. Try again in a moment.\" and nothing saved.\n"
    "   Outside the list: a writer or reader a gate finds that this list does not\n"
    "   name is a register row, not a rejection.\n"
)

SECTION_UNDO = "## Overlapping writes\n\n- Criterion 2, the credit Undo.\n"
SECTION_NONE = (
    "## Overlapping writes\n\n"
    "- None: this issue only renders the credit sheet and writes no row.\n"
)


def issue(criteria: str, section: str = "") -> str:
    return (
        "Status: needs-harden\n\n# Issue\n\n## Acceptance criteria\n\n"
        f"{criteria}\n## Must still be true\n\n- A thing.\n\n{section}"
    )


class TheSectionIsOwed(unittest.TestCase):
    def test_an_issue_with_no_section_is_refused(self):
        """Issue 370 as it was stamped: an Undo, and no overlap rule anywhere."""
        faults = check.faults(issue(PLAIN + UNDO))
        self.assertEqual(len(faults), 1)
        self.assertIn("no `## Overlapping writes` section", faults[0])

    def test_an_issue_with_no_section_is_refused_even_with_no_write_in_sight(self):
        """The check refuses what it cannot place. It never guesses from words."""
        self.assertTrue(check.faults(issue(PLAIN)))

    def test_a_section_naming_nothing_is_refused(self):
        faults = check.faults(issue(PLAIN, "## Overlapping writes\n\nSee below.\n"))
        self.assertEqual(len(faults), 1)
        self.assertIn("names no criterion and says no `None:`", faults[0])


class NoneMustSayWhy(unittest.TestCase):
    def test_none_with_a_reason_passes(self):
        self.assertEqual(check.faults(issue(PLAIN, SECTION_NONE)), [])

    def test_a_bare_none_is_refused(self):
        faults = check.faults(issue(PLAIN, "## Overlapping writes\n\n- None.\n"))
        self.assertEqual(len(faults), 1)
        self.assertIn("`None:` gives no reason", faults[0])

    def test_a_reason_of_two_words_is_refused(self):
        faults = check.faults(issue(PLAIN, "## Overlapping writes\n\n- None: not applicable\n"))
        self.assertIn("`None:` gives no reason", faults[0])

    def test_none_beside_a_criterion_carrying_the_rule_is_refused(self):
        faults = check.faults(issue(PLAIN + UNDO, SECTION_NONE))
        self.assertEqual(len(faults), 1)
        self.assertIn("criterion 2 carries `Writers:`", faults[0])

    def test_none_beside_a_named_criterion_is_refused(self):
        section = SECTION_NONE + "- Criterion 2, the credit Undo.\n"
        faults = check.faults(issue(PLAIN + UNDO, section))
        self.assertIn("says `None:` and names criterion 2", faults[0])


class ANamedCriterionCarriesTheRule(unittest.TestCase):
    def test_the_whole_rule_passes(self):
        self.assertEqual(check.faults(issue(PLAIN + UNDO, SECTION_UNDO)), [])

    def test_the_short_name_passes(self):
        section = "## Overlapping writes\n\n- C2, the credit Undo.\n"
        self.assertEqual(check.faults(issue(PLAIN + UNDO, section)), [])

    def test_each_missing_label_is_named(self):
        for label in ("Writers", "Readers", "Loser sees"):
            with self.subTest(label=label):
                lines = [one for one in UNDO.splitlines(keepends=True)
                         if not one.lstrip().startswith(f"{label}:")]
                if label == "Writers":
                    lines = [one for one in lines if "a second Undo" not in one]
                faults = check.faults(issue(PLAIN + "".join(lines), SECTION_UNDO))
                self.assertEqual(len(faults), 1, faults)
                self.assertIn(f"`{label}:`", faults[0])

    def test_an_empty_label_counts_as_missing(self):
        undo = UNDO.replace("Readers: `creditHeld`, `standingRow` and the Undo window.",
                            "Readers:")
        faults = check.faults(issue(PLAIN + undo, SECTION_UNDO))
        self.assertIn("`Readers:`", faults[0])

    def test_writers_none_is_refused(self):
        """No other writer means no overlap, and that is the `None:` road."""
        undo = UNDO.replace(
            "Writers: an Accept on a line of the job, Confirm the order, a credit decline,\n"
            "   a second Undo of the same approval.",
            "Writers: none.",
        )
        faults = check.faults(issue(PLAIN + undo, SECTION_UNDO))
        self.assertIn("`Writers:` names no other write", faults[0])

    def test_an_unbounded_list_is_refused(self):
        """The bound is what both strike-2 re-checks of 370 found missing."""
        undo = UNDO.replace("is a register row, not a rejection", "is a rejection")
        faults = check.faults(issue(PLAIN + undo, SECTION_UNDO))
        self.assertIn("`Outside the list:`", faults[0])

    def test_a_criterion_the_issue_does_not_hold_is_refused(self):
        section = "## Overlapping writes\n\n- Criterion 7, the credit Undo.\n"
        faults = check.faults(issue(PLAIN + UNDO, section))
        self.assertIn("names criterion 7, which this issue does not hold", faults[0])

    def test_a_criterion_carrying_the_rule_and_not_named_is_refused(self):
        second = UNDO.replace("2. **Undo", "3. **A second Undo")
        faults = check.faults(issue(PLAIN + UNDO + second, SECTION_UNDO))
        self.assertEqual(len(faults), 1, faults)
        self.assertIn("criterion 3 carries `Writers:`", faults[0])

    def test_labels_are_read_in_their_own_criterion_only(self):
        """Criterion 1 holds the rule; the section names criterion 2, which does not."""
        rule = UNDO.split("\n", 2)[2]
        first = "1. **One.** A test reads it.\n" + rule
        second = "2. **Two.** A test reads it.\n"
        faults = check.faults(issue(first + second, SECTION_UNDO))
        self.assertTrue(any("criterion 2 lacks" in one for one in faults), faults)
        self.assertTrue(any("criterion 1 carries `Writers:`" in one for one in faults), faults)


class TheCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def run_on(self, *names_and_texts):
        paths = []
        for name, text in names_and_texts:
            path = self.dir / name
            if text is not None:
                path.write_text(text)
            paths += ["--issue", str(path)]
        return subprocess.run([sys.executable, str(SCRIPT), *paths],
                              capture_output=True, text=True)

    def test_a_clean_set_exits_zero(self):
        done = self.run_on(("409-undo.md", issue(PLAIN + UNDO, SECTION_UNDO)),
                           ("410-sheet.md", issue(PLAIN, SECTION_NONE)))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ok        409", done.stdout)
        self.assertIn("ok        410", done.stdout)

    def test_one_fault_in_the_set_exits_one_and_names_the_issue(self):
        done = self.run_on(("409-undo.md", issue(PLAIN + UNDO)),
                           ("410-sheet.md", issue(PLAIN, SECTION_NONE)))
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED   409", done.stderr)
        self.assertIn("ok        410", done.stdout)

    def test_an_unreadable_file_is_refused(self):
        done = self.run_on(("411-gone.md", None))
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED   411: unreadable", done.stderr)


if __name__ == "__main__":
    unittest.main()
