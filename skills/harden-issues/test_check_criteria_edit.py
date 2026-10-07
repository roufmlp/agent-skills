#!/usr/bin/env python3
"""Tests for check_criteria_edit.py. Run: python3 test_check_criteria_edit.py

Fix F9 of the audit of 2026-09-23, tracker-tooling issue 23. The cases quote the
two faults the audit names, both on one tracker: issue 139c, where pass `h0919` added a broad
rule beside the narrow one and deleted nothing, and issue 139, where pass
`h0917c` wrote "twenty-two" colour families with no command behind the figure.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_criteria_edit as check  # noqa: E402

NARROW = (
    "1. **The phone header is the primary colour.** The band's class names `bg-primary`\n"
    "   and nothing else. A test reads the header's class list.\n"
)


def issue(criteria: str) -> str:
    return f"# Issue\n\n## Acceptance criteria\n\n{criteria}\n## Must still be true\n\n- A thing.\n"


class ReplaceNotAdd(unittest.TestCase):
    def test_a_reset_criterion_that_only_gained_text_is_refused(self):
        """Issue 139c: "Both implementers built the first. Both gates graded the second." """
        now = NARROW + "   Every class in the band is one the check can place, under `src/`.\n"
        faults = check.added_only(issue(NARROW), issue(now))
        self.assertEqual(len(faults), 1)
        self.assertIn("criterion 1", faults[0])

    def test_a_sentence_struck_in_place_counts_as_replaced(self):
        """The pass strikes a false claim where it stands (SKILL.md class 5), so
        `~~old~~ new` is a replacement even though the old words are still there."""
        now = NARROW.replace(
            "A test reads the header's class list.",
            "~~A test reads the header's class list.~~ A test reads the rendered header.",
        )
        self.assertEqual(check.added_only(issue(NARROW), issue(now)), [])

    def test_a_rewritten_sentence_passes(self):
        now = NARROW.replace("and nothing else.", "and no other colour class.")
        self.assertEqual(check.added_only(issue(NARROW), issue(now)), [])

    def test_an_unchanged_criterion_is_not_an_edit(self):
        self.assertEqual(check.added_only(issue(NARROW), issue(NARROW)), [])

    def test_reflowed_lines_are_not_an_edit(self):
        now = NARROW.replace("`bg-primary`\n   and", "`bg-primary` and")
        self.assertEqual(check.added_only(issue(NARROW), issue(now)), [])

    def test_a_new_criterion_is_not_an_edit(self):
        """Absent at base, so there is nothing it could have replaced."""
        second = "2. **The tab bar stays white.** A test reads its class list.\n"
        self.assertEqual(check.added_only(issue(NARROW), issue(NARROW + second)), [])


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class FindsTheResetOnRecord(unittest.TestCase):
    """Every strike-2 findings file of one tracker on 2026-09-23 read
    `criteria-fault` between lines 3 and 7: ten files under its `runs/*/harden/`."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.feature = self.root / ".scratch" / "example-feature"
        (self.feature / "issues").mkdir(parents=True)
        self.issue = self.feature / "issues" / "139c-the-coloured-band.md"
        self.issue.write_text(issue(NARROW))

    def findings(self, root, name, verdict_line, line=3):
        path = root / ".scratch" / "example-feature" / "runs" / "batch-cab9be" / "harden" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Strike-2 pass\n" + "\n" * (line - 2) + verdict_line + "\n")
        return path

    def test_a_criteria_fault_verdict_is_a_reset(self):
        found = self.findings(self.root, "139c.md", "**VERDICT: `criteria-fault`.**")
        self.assertEqual(check.reset_record(self.issue), [found])

    def test_a_sound_verdict_is_not_a_reset(self):
        self.findings(self.root, "139c.md", "Verdict: `criteria-sound`.")
        self.assertEqual(check.reset_record(self.issue), [])

    def test_another_issue_s_findings_do_not_count(self):
        """139's findings are not 139c's."""
        self.findings(self.root, "139.md", "**VERDICT: `criteria-fault`.**")
        self.assertEqual(check.reset_record(self.issue), [])

    def test_a_verdict_below_the_head_of_the_file_does_not_count(self):
        """A findings file quoting another verdict in its body is not that verdict."""
        self.findings(self.root, "139c.md", "quoting run 139: `criteria-fault`", line=40)
        self.assertEqual(check.reset_record(self.issue), [])

    def test_a_reset_recorded_in_another_worktree_is_found(self):
        """Run state is committed, so a worktree carries a frozen copy of `runs/`.
        On 2026-09-13 pass `h0913` read its own worktree's copy and missed a live
        run. The record may sit in any worktree of the repository."""
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed")
        other = self.root.parent / (self.root.name + "-run")
        git(self.root, "worktree", "add", "-q", str(other), "-b", "run")
        self.addCleanup(subprocess.run, ["rm", "-rf", str(other)])
        found = self.findings(other, "139c.md", "Verdict: **criteria-fault.**")
        self.assertEqual(check.reset_record(self.issue), [found])


class ACountCarriesItsCommand(unittest.TestCase):
    """Issue 139, pass `h0917c`: "twenty-two" colour families. Installed Tailwind
    ships 26, and nothing in the criterion said how the figure was reached."""

    def faults(self, criterion):
        return check.unmeasured_counts(issue(criterion))

    def test_a_count_in_words_with_no_command_is_refused(self):
        faults = self.faults("1. **The check refuses the twenty-two colour families Tailwind ships.**\n")
        self.assertEqual(len(faults), 1)
        self.assertIn("criterion 1", faults[0])
        self.assertIn("twenty-two colour families", faults[0])

    def test_a_count_in_digits_with_no_command_is_refused(self):
        faults = self.faults("1. **Every one of the 13 action modules takes the guard.**\n")
        self.assertIn("13 action modules", faults[0])

    def test_a_count_beside_its_command_passes(self):
        body = (
            "1. **The check refuses the 26 colour families Tailwind ships.** Measured by\n"
            "   `node -p \"Object.keys(require('tailwindcss/colors')).length\"`.\n"
        )
        self.assertEqual(self.faults(body), [])

    def test_a_query_is_a_command(self):
        body = "1. **The 23 rows are imported.** `select count(*) from suppliers` answers 23.\n"
        self.assertEqual(self.faults(body), [])

    def test_a_backticked_word_that_is_no_command_does_not_count(self):
        """The list of commands is closed: an unknown first word is refused."""
        body = "1. **The 13 action modules call `asSignedInUser`.**\n"
        self.assertEqual(len(self.faults(body)), 1)

    def test_a_number_that_names_something_is_not_a_count(self):
        body = (
            "1. **Criterion 9 of issue 139 grades attempt 3.** See criteria 1 and 2,\n"
            "   invariant M9, round 2 and default 1, on 2026-09-23 at 13:40.\n"
        )
        self.assertEqual(self.faults(body), [])

    def test_a_unit_is_not_a_count(self):
        body = "1. **The drill finishes in under 10 s, with a 1000 ms connect timeout.**\n"
        self.assertEqual(self.faults(body), [])

    def test_one_is_not_a_count(self):
        """"One file says so" is a design rule, not a measurement."""
        self.assertEqual(self.faults("1. **Every screen is served one face, and one file says so.**\n"), [])

    def test_a_number_inside_backticks_is_not_a_count(self):
        self.assertEqual(self.faults("1. **The cap reads `4.5 MB` and `22 families`.**\n"), [])

    def test_a_blank_code_span_is_read_without_a_crash(self):
        """Measured: a ready criterion on one tracker quotes a space as `` ` ` ``."""
        self.assertEqual(len(self.faults("1. **The 13 modules split on ` ` only.**\n")), 1)

    def test_a_count_the_pass_did_not_write_is_not_graded(self):
        """Measured 2026-09-23: graded whole, 123 of the 269 ready criteria in
        two trackers were flagged, mostly fixture sizes. The rule is
        on what the pass writes, so an old sentence is not its fault."""
        old = "1. **The fixture holds two rows.** A test reads them.\n"
        now = "1. **The fixture holds two rows.** A test reads them, both ways.\n"
        self.assertEqual(check.unmeasured_counts(issue(now), issue(old)), [])

    def test_a_count_the_pass_wrote_is_graded(self):
        old = "1. **The fixture holds two rows.**\n"
        now = "1. **The fixture holds two rows.** The check reads the 13 action modules.\n"
        faults = check.unmeasured_counts(issue(now), issue(old))
        self.assertEqual(len(faults), 1)
        self.assertIn("13 action modules", faults[0])
        self.assertNotIn("two rows", faults[0])

    def test_a_count_named_as_not_measured_is_cleared(self):
        body = "1. **The fixture holds two rows.**\n   Not measured: 'two rows' is the fixture this criterion builds.\n"
        self.assertEqual(self.faults(body), [])

    def test_not_measured_clears_only_the_counts_it_quotes(self):
        body = (
            "1. **The fixture holds two rows, over the 13 action modules.**\n"
            "   Not measured: 'two rows' is the fixture this criterion builds.\n"
        )
        faults = self.faults(body)
        self.assertEqual(len(faults), 1)
        self.assertIn("13 action modules", faults[0])
        self.assertNotIn("two rows", faults[0])

    def test_a_size_or_a_duration_is_not_a_count(self):
        body = "1. **A 255 bytes name is refused within 2 seconds, at 2200 bps.**\n"
        self.assertEqual(self.faults(body), [])

    def test_nought_and_one_are_not_counts(self):
        self.assertEqual(self.faults("1. **The drill leaves 0 rows and 1 files behind.**\n"), [])

    def test_only_the_criteria_are_read(self):
        text = issue("1. A thing.\n") + "\n## What is wrong\n\nThe tree holds 15 pages.\n"
        self.assertEqual(check.unmeasured_counts(text), [])


# Issue 381's criterion 3 as pass `Harden at launch` (commit 44d683f5) wrote it,
# cut to the clauses both gates measured false on 2026-10-07.
SEARCH_381 = (
    "1. **One search finds a bill.** Check, as an operations reader: `47` returns [A] by the\n"
    "   job number; `INV-8` returns [B]. Default: the job number matches exactly, so `4`\n"
    "   finds no bill through job 47.\n"
)


class AnExampleCarriesItsCommand(unittest.TestCase):
    """Ruling `q-fin-ce5d7b-03`, 2026-10-07, road A2: an example input and outcome
    with no measuring command beside it is refused where the hardening pass writes
    it. Issue 381's criterion 3 quoted searches that both gates measured false,
    which cost a strike-2 attacker and a second attempt."""

    def test_issue_381s_examples_are_refused(self):
        faults = check.unmeasured_examples(issue(SEARCH_381))
        self.assertEqual(len(faults), 1)
        self.assertIn("criterion 1", faults[0])
        for example in ("`47` returns", "`INV-8` returns", "`4` finds"):
            self.assertIn(example, faults[0])

    def test_a_quoted_input_is_an_example(self):
        text = issue('1. **Search.** "oasis" returns [A] only.\n')
        self.assertEqual(len(check.unmeasured_examples(text)), 1)

    def test_an_example_beside_its_command_passes(self):
        text = issue(
            "1. **Search.** `04 39` folds to `971439` "
            "(`node -e \"console.log(normalisePhone('04 39'))\"`).\n"
        )
        self.assertEqual(check.unmeasured_examples(text), [])

    def test_a_command_in_another_clause_is_not_beside_it(self):
        """Beside means the same clause: one command must not clear a criterion."""
        text = issue(
            "1. **Search.** `07` returns [A] (`grep -n PREFIX src/model/phone.ts`);"
            " `4` finds no bill.\n"
        )
        faults = check.unmeasured_examples(text)
        self.assertEqual(len(faults), 1)
        self.assertIn("`4` finds", faults[0])
        self.assertNotIn("`07`", faults[0])

    def test_code_named_in_backticks_is_not_an_example_input(self):
        """Measured 2026-10-07 over the 391 criteria of one project's ready issues:
        23 of 24 hits on any backticked span named a function, file or flag."""
        for span in (
            "`saveLinePrice` returns the row",
            "`src/model/rights.ts` matches",
            "`refusingTheClear()` matches",
            "`--reporter=json` outputs one line",
            "`check_diff_coverage.py` returns 2",
        ):
            with self.subTest(span=span):
                self.assertEqual(check.unmeasured_examples(issue(f"1. {span}.\n")), [])

    def test_an_example_the_pass_did_not_write_is_not_graded(self):
        base = issue(SEARCH_381)
        now = issue(SEARCH_381 + "   The list paints the bill once.\n")
        self.assertEqual(check.unmeasured_examples(now, base), [])

    def test_not_measured_does_not_clear_an_example(self):
        """The ruling: measure it or remove it. No waiver."""
        text = issue("1. **Search.** `4` finds no bill.\n\n   Not measured: `4` finds no bill.\n")
        self.assertEqual(len(check.unmeasured_examples(text)), 1)

    def test_struck_text_is_not_graded(self):
        text = issue("1. **Search.** ~~`4` finds no bill.~~ A test reads the list.\n")
        self.assertEqual(check.unmeasured_examples(text), [])


class TheCommandLine(unittest.TestCase):
    """What the hardening pass runs before it stamps."""

    SCRIPT = pathlib.Path(__file__).with_name("check_criteria_edit.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.issues = self.root / ".scratch" / "example-feature" / "issues"
        self.issues.mkdir(parents=True)
        self.issue = self.issues / "139c-the-coloured-band.md"
        self.issue.write_text(issue(NARROW))
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", ".")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed")

    def reset(self):
        path = self.issues.parent / "runs" / "batch-cab9be" / "harden" / "139c.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Strike-2 pass\n\n**VERDICT: `criteria-fault`.**\n")

    def run_it(self, *paths):
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *sum((["--issue", str(one)] for one in paths or [self.issue]), [])],
            capture_output=True, text=True,
        )

    def test_an_addition_to_a_reset_issue_is_refused(self):
        self.reset()
        self.issue.write_text(issue(NARROW + "   Every class in the band is one the check can place.\n"))
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED   139c", done.stderr)
        self.assertIn("only gained text", done.stderr)
        self.assertIn("batch-cab9be", done.stdout + done.stderr)

    def test_the_same_addition_with_no_reset_passes(self):
        self.issue.write_text(issue(NARROW + "   Every class in the band is one the check can place.\n"))
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ok        139c", done.stdout)

    def test_a_new_file_is_graded_for_its_counts(self):
        """No base: every sentence is the pass's own."""
        fresh = self.issues / "140-a-new-slice.md"
        fresh.write_text(issue("1. **The check reads the 13 action modules.**\n"))
        done = self.run_it(fresh)
        self.assertEqual(done.returncode, 1)
        self.assertIn("13 action modules", done.stderr)

    def test_an_unmeasured_example_is_refused_before_the_stamp(self):
        self.issue.write_text(issue(NARROW + "   Searching `4` finds no bill.\n"))
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("`4` finds", done.stderr)
        self.assertIn("measure it or remove it", done.stderr)

    def test_it_says_how_much_it_read(self):
        """A pass over nothing must not read like a clean pass."""
        done = self.run_it()
        self.assertIn("read 1 issue file(s), 1 criteria", done.stdout)


if __name__ == "__main__":
    unittest.main()
