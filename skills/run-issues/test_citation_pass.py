#!/usr/bin/env python3
"""Drill for citation_pass.py.

The one thing this file exists to pin: a pass file that HOLDS CONTENT and has no
terminator reads as a killed pass, never as a clean one. Run `batch-207704`'s
last citation pass died after 48 lines inside a preamble and read clean, and
that is the fault this check answers.

    python3 test_citation_pass.py
"""

from __future__ import annotations

import io
import contextlib
import pathlib
import tempfile
import unittest

import citation_pass as pass_check


def tree(files: dict) -> pathlib.Path:
    """A throwaway citation-deltas directory holding the named files."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="citpass-"))
    for name, body in files.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


COMPLETE = "reading 4 files\n=== CITATION PASS COMPLETE === exit=0 pinned=abc1234\n"
KILLED = "reading 4 files\nscanning .scratch/example-feature/issues/501.md\n"


class Verdict(unittest.TestCase):
    def test_a_finished_pass_reads_complete(self):
        root = tree({"abc1234.txt": COMPLETE})
        found = pass_check.verdict(root / "abc1234.txt")
        self.assertEqual(found.state, "complete")
        self.assertEqual(found.exit_code, 0)
        self.assertEqual(found.pinned, "abc1234")

    def test_a_killed_pass_holding_content_reads_unterminated(self):
        """The whole reason this exists. 48 lines and no terminator is a killed
        pass, and reading the file for bytes alone calls it clean."""
        root = tree({"abc1234.txt": KILLED})
        self.assertEqual(pass_check.verdict(root / "abc1234.txt").state,
                         "unterminated")

    def test_an_empty_file_reads_unterminated(self):
        root = tree({"abc1234.txt": ""})
        self.assertEqual(pass_check.verdict(root / "abc1234.txt").state,
                         "unterminated")

    def test_a_missing_file_reads_absent(self):
        root = tree({})
        self.assertEqual(pass_check.verdict(root / "abc1234.txt").state,
                         "absent")

    def test_the_terminator_must_be_the_last_line(self):
        """A pass that printed the terminator and then went on was still killed
        later. Only the last line counts."""
        root = tree({"abc1234.txt": COMPLETE + "then more output\n"})
        self.assertEqual(pass_check.verdict(root / "abc1234.txt").state,
                         "unterminated")

    def test_trailing_blank_lines_do_not_hide_a_terminator(self):
        root = tree({"abc1234.txt": COMPLETE + "\n\n  \n"})
        self.assertEqual(pass_check.verdict(root / "abc1234.txt").state,
                         "complete")

    def test_a_non_zero_checker_exit_is_reported_and_not_refused(self):
        """Exit 3 is a tree with no `.git` and exit 5 is a file the pinned tree
        does not hold. Both are real answers from a pass that RAN, so they are
        named rather than refused. Ruled scope: a missing terminator is what is
        treated as a red test."""
        root = tree({"abc1234.txt": "=== CITATION PASS COMPLETE === exit=5 pinned=abc1234\n"})
        found = pass_check.verdict(root / "abc1234.txt")
        self.assertEqual(found.state, "complete")
        self.assertEqual(found.exit_code, 5)

    def test_an_unreadable_terminator_still_reads_complete(self):
        """The terminator is the rule. A malformed tail on it loses the two
        numbers and nothing else."""
        root = tree({"abc1234.txt": "=== CITATION PASS COMPLETE ===\n"})
        found = pass_check.verdict(root / "abc1234.txt")
        self.assertEqual(found.state, "complete")
        self.assertIsNone(found.exit_code)


class Survey(unittest.TestCase):
    def test_named_shas_are_read_in_the_order_given(self):
        root = tree({"aaa.txt": COMPLETE, "bbb.txt": KILLED})
        found = pass_check.survey(root, ["bbb", "aaa"])
        self.assertEqual([f.sha for f in found], ["bbb", "aaa"])

    def test_with_no_shas_named_it_reads_every_file_in_the_directory(self):
        root = tree({"aaa.txt": COMPLETE, "bbb.txt": KILLED})
        self.assertEqual(sorted(f.sha for f in pass_check.survey(root, [])),
                         ["aaa", "bbb"])

    def test_a_file_that_is_not_a_pass_is_not_read(self):
        """`SKILL.md` writes one `<sha>.txt` per commit. Reading every file made
        a macOS `.DS_Store` refuse a clean finale and tell the runner to re-run
        the citation pass for `.DS_Store`."""
        root = tree({"aaa.txt": COMPLETE, ".DS_Store": "junk",
                     "notes.md": "not a pass"})
        self.assertEqual([f.sha for f in pass_check.survey(root, [])], ["aaa"])

    def test_a_stray_file_does_not_refuse_a_clean_directory(self):
        root = tree({"aaa.txt": COMPLETE, ".DS_Store": "junk"})
        self.assertEqual(pass_check.report(pass_check.survey(root, []), root)[0], 0)

    def test_a_missing_directory_with_no_shas_named_surveys_nothing(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="citpass-")) / "gone"
        self.assertEqual(pass_check.survey(root, []), [])


class Refusal(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = pass_check.main(argv)
        return code, out.getvalue()

    def test_every_pass_complete_authorises(self):
        root = tree({"aaa.txt": COMPLETE})
        code, text = self.run_main(["--deltas", str(root)])
        self.assertEqual(code, 0)
        self.assertIn("complete", text)

    def test_one_unterminated_pass_refuses_and_names_the_sha(self):
        root = tree({"aaa.txt": COMPLETE, "bbb.txt": KILLED})
        code, text = self.run_main(["--deltas", str(root)])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)
        self.assertIn("bbb", text)

    def test_a_named_sha_with_no_file_refuses(self):
        root = tree({"aaa.txt": COMPLETE})
        code, text = self.run_main(["--deltas", str(root), "--sha", "zzz"])
        self.assertEqual(code, 1)
        self.assertIn("zzz", text)

    def test_the_refusal_says_it_never_waits_for_abdul(self):
        """Copied from `run-state-path-guard.py`: a refusal inside a run names
        the roads out and says nobody is coming."""
        root = tree({"bbb.txt": KILLED})
        _, text = self.run_main(["--deltas", str(root)])
        self.assertIn("AFK", text)
        self.assertIn("re-run", text.lower())

    def test_no_files_at_all_refuses_rather_than_reporting_clean(self):
        """A commit with no pass on disk is the `batch-170a59` fault: four of six
        commits had no pass at all. Nothing to read is not a clean sweep."""
        root = tree({})
        code, text = self.run_main(["--deltas", str(root)])
        self.assertEqual(code, 1)
        self.assertIn("no pass file", text.lower())

    def test_a_non_zero_checker_exit_is_named_but_authorises(self):
        root = tree({"aaa.txt": "=== CITATION PASS COMPLETE === exit=5 pinned=aaa\n"})
        code, text = self.run_main(["--deltas", str(root)])
        self.assertEqual(code, 0)
        self.assertIn("exit=5", text)


if __name__ == "__main__":
    unittest.main()
