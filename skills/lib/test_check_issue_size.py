#!/usr/bin/env python3
"""The one-implementer counter, ruled by the human on 2026-09-14.

Class 9 of `/harden-issues` used to ask an attacker to judge "one implementer"
against a sentence, and `check_issue_size.py` counts instead. These tests pin
what it counts, what it refuses, and the two things it deliberately does not
refuse: a criterion's width, and a backlog file nobody named.

Run: python3 test_check_issue_size.py
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_issue_size.py"
sys.path.insert(0, str(HERE))

import check_issue_size  # noqa: E402


def issue(root: Path, name: str, criteria=(), form="checkbox", extra=""):
    """One issue file in the tracker's shape.

    `criteria` are the criterion bodies; `form` picks which of the two shapes
    the tracker actually writes them in.
    """
    lines = ["# " + name, "", "## What to build", "", "Something.", "",
             "## Acceptance criteria", ""]
    for index, body in enumerate(criteria, start=1):
        if form == "checkbox":
            lines.append(f"- [ ] {body}")
        elif form == "ticked":
            lines.append(f"- [x] {body}")
        else:
            lines.append(f"{index}. {body}")
    lines += ["", "## Must still be true", "", "- Something else.", ""]
    if extra:
        lines.append(extra)
    path = root / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


class Counting(unittest.TestCase):
    def test_checkbox_criteria_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["one", "two", "three"])
            self.assertEqual(
                len(check_issue_size.read_criteria((root / "01-a.md").read_text())),
                3)

    def test_numbered_criteria_are_counted(self):
        """One file in the measured tracker writes them this way, and a reader
        that knew only the checkbox counted that file at zero."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "42-a.md", ["one", "two", "three", "four", "five"],
                  form="numbered")
            self.assertEqual(
                len(check_issue_size.read_criteria((root / "42-a.md").read_text())),
                5)

    def test_a_ticked_criterion_still_counts(self):
        """Issue 01 ran with four of its six already green and still took the
        longest span in the record. A ticked criterion is work the file
        carries, not work removed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["one", "two"], form="ticked")
            self.assertEqual(
                len(check_issue_size.read_criteria((root / "01-a.md").read_text())),
                2)

    def test_a_dated_heading_still_opens_the_section(self):
        """Harden passes date the heading when they rewrite the section."""
        text = ("# t\n\n## Acceptance criteria, rewritten 2026-09-13\n\n"
                "- [ ] one\n- [ ] two\n\n## Must still be true\n\n- x\n")
        self.assertEqual(len(check_issue_size.read_criteria(text)), 2)

    def test_a_numbered_line_inside_a_fence_is_not_a_criterion(self):
        text = ("# t\n\n## Acceptance criteria\n\n- [ ] one\n\n"
                "```\n1. not a criterion\n2. nor this\n```\n\n"
                "## Must still be true\n\n- x\n")
        self.assertEqual(len(check_issue_size.read_criteria(text)), 1)

    def test_the_section_stops_at_the_next_heading(self):
        text = ("# t\n\n## Acceptance criteria\n\n- [ ] one\n\n"
                "## Must still be true\n\n- [ ] not a criterion\n")
        self.assertEqual(len(check_issue_size.read_criteria(text)), 1)

    def test_no_section_reads_as_None_not_as_zero(self):
        """A file with no section and a file with an empty one are different
        things, and the caller tells them apart."""
        self.assertIsNone(check_issue_size.read_criteria("# t\n\nnothing\n"))
        self.assertEqual(
            check_issue_size.read_criteria(
                "# t\n\n## Acceptance criteria\n\n## Must still be true\n"),
            [])

    def test_a_criterion_carries_its_line_and_its_opening_words(self):
        """The refusal quotes what it counted, the way check_issue_links.py
        quotes the sentence it refuses on."""
        text = ("# t\n\n## Acceptance criteria\n\n"
                "- [ ] The limiter refuses the sixth request\n"
                "- [ ] And a second thing\n\n## Must still be true\n\n- x\n")
        found = check_issue_size.read_criteria(text)
        self.assertEqual(found[0].line, 5)
        self.assertEqual(found[0].opening, "The limiter refuses the sixth request")
        self.assertEqual(found[1].line, 6)

    def test_a_line_number_survives_a_fence_above_it(self):
        """Fences are blanked, not deleted, so a quoted line number is the line
        number in the file."""
        text = ("# t\n\n## Acceptance criteria\n\n"
                "```\nsome\ncode\n```\n"
                "- [ ] the only criterion\n\n## Must still be true\n\n- x\n")
        found = check_issue_size.read_criteria(text)
        self.assertEqual(found[0].line, 9)


class Refusing(unittest.TestCase):
    def test_over_the_limit_refuses_and_names_the_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", [f"criterion {n}" for n in range(1, 8)])
            code, _out, err = run("--issues", tmp, "--limit", "5")
            self.assertEqual(code, 1)
            self.assertIn("7 acceptance criteria, and the limit is 5", err)

    def test_the_refusal_lists_every_criterion_it_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["alpha one", "beta two", "gamma three"])
            code, _out, err = run("--issues", tmp, "--limit", "2")
            self.assertEqual(code, 1)
            for word in ("alpha one", "beta two", "gamma three"):
                self.assertIn(word, err)

    def test_at_the_limit_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["one", "two", "three"])
            code, out, _err = run("--issues", tmp, "--limit", "3")
            self.assertEqual(code, 0)
            self.assertIn("none over", out)

    def test_it_never_prints_a_predicted_duration(self):
        """The point of the ruling: the analogy step is where the judgement
        hid, so a minutes field would put it straight back."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", [f"criterion {n}" for n in range(1, 20)])
            _code, out, err = run("--issues", tmp, "--limit", "5")
            for word in ("minute", "min ", "hour", "estimate"):
                self.assertNotIn(word, (out + err).lower())


class Grading(unittest.TestCase):
    def test_grade_narrows_refusal_to_the_files_named(self):
        """A tracker carries issues minted before the rule, and a pass cannot
        repair a backlog to stamp one file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = issue(root, "01-old.md", [f"c{n}" for n in range(1, 10)])
            issue(root, "02-new.md", ["one", "two"])
            code, _out, _err = run("--issues", tmp, "--limit", "3",
                                   "--grade", str(root / "02-new.md"))
            self.assertEqual(code, 0)
            code, _out, err = run("--issues", tmp, "--limit", "3",
                                  "--grade", str(old))
            self.assertEqual(code, 1)

    def test_every_file_is_still_read_under_grade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-old.md", [f"c{n}" for n in range(1, 10)])
            issue(root, "02-new.md", ["one", "two"])
            _code, out, _err = run("--issues", tmp, "--limit", "3",
                                   "--grade", str(root / "02-new.md"))
            self.assertIn("across 2 file(s)", out)
            self.assertIn("11 criteria read", out)

    def test_a_graded_file_with_no_criteria_refuses(self):
        """A count of zero is not a pass: class 9 was never judged on it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare = root / "03-bare.md"
            bare.write_text("# t\n\nNo criteria here.\n", encoding="utf-8")
            issue(root, "02-new.md", ["one"])
            code, _out, err = run("--issues", tmp, "--limit", "3",
                                  "--grade", str(bare))
            self.assertEqual(code, 1)
            self.assertIn("count of zero is not a pass", err)

    def test_an_ungraded_file_with_no_criteria_is_a_note_not_a_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "03-bare.md").write_text("# t\n\nNothing.\n",
                                             encoding="utf-8")
            issue(root, "02-new.md", ["one"])
            code, out, _err = run("--issues", tmp, "--limit", "3",
                                  "--grade", str(root / "02-new.md"))
            self.assertEqual(code, 0)
            self.assertIn("counted, not graded", out)

    def test_grading_a_file_outside_the_walk_refuses_with_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["one"])
            code, _out, err = run("--issues", tmp, "--limit", "3",
                                  "--grade", str(root / "99-absent.md"))
            self.assertEqual(code, 2)
            self.assertIn("not a file this walk reads", err)


class Width(unittest.TestCase):
    def test_width_is_reported_and_never_refused(self):
        """Issue 05g holds one criterion and 1,817 words of it. Width
        correlates at +0.33, so it is stated and not refused."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["word " * 400])
            code, out, _err = run("--issues", tmp, "--limit", "3",
                                  "--grade", str(root / "01-a.md"))
            self.assertEqual(code, 0)
            self.assertIn("widest criterion", out)

    def test_width_names_the_widest_and_its_line(self):
        text = ("# t\n\n## Acceptance criteria\n\n"
                "- [ ] short\n"
                "- [ ] " + "word " * 50 + "\n\n## Must still be true\n\n- x\n")
        words, line = check_issue_size.width(text)
        self.assertGreater(words, 40)
        self.assertEqual(line, 6)


class Refusals(unittest.TestCase):
    def test_a_missing_directory_asserts_nothing(self):
        code, _out, err = run("--issues", "/nowhere/at/all", "--limit", "3")
        self.assertEqual(code, 2)
        self.assertIn("nothing here is asserted", err)

    def test_an_empty_walk_may_not_report_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, err = run("--issues", tmp, "--limit", "3")
            self.assertEqual(code, 2)
            self.assertIn("may not report a pass", err)

    def test_a_limit_below_one_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue(root, "01-a.md", ["one"])
            code, _out, err = run("--issues", tmp, "--limit", "0")
            self.assertEqual(code, 2)
            self.assertIn("would refuse every issue", err)


# THE CALIBRATION CLASS DOES NOT TRAVEL, AND THE FACT IT CARRIED DOES.
# Live, two cases read a real tracker at an absolute path under one author's home
# and pinned the counter against four issues ruled NO CUT by hand on 2026-09-14:
# `08` at 11 criteria, `21` at 9, `27` at 4, `27c` at 6. All four pass at the
# default limit of 14. A test that reads a checkout nobody else has grades a
# machine rather than the counter, so the reading is written down here and the
# pinning stays behind. Run the counter over your own tracker to calibrate a
# limit for it; `--limit` is a flag for exactly that reason.


if __name__ == "__main__":
    unittest.main(verbosity=2)
