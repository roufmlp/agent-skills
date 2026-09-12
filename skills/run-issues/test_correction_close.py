#!/usr/bin/env python3
"""Drill for correction_close.py.

Two things this file exists to pin. A round may not close over a RED test, and a
round may not close over a citation pass that never reached its terminator. The
second is the rule the human adopted on 2026-09-08: a dead pass is treated the way a
red test is treated.

    python3 test_correction_close.py
"""

from __future__ import annotations

import io
import contextlib
import pathlib
import tempfile
import unittest

import correction_close as close


COMPLETE = "=== CITATION PASS COMPLETE === exit=0 pinned=abc1234\n"
KILLED = "reading 4 files\nscanning one issue\n"


def pass_file(body: str, name: str = "abc1234.txt") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="corrclose-"))
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = close.main(argv)
    return code, out.getvalue()


class Tests(unittest.TestCase):
    def test_a_green_test_and_a_finished_pass_authorise_the_close(self):
        code, text = run_main(["--test", "true",
                               "--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 0)
        self.assertIn("CLOSE AUTHORISED", text)

    def test_a_red_test_refuses(self):
        code, text = run_main(["--test", "false",
                               "--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)
        self.assertIn("false", text)

    def test_every_named_test_runs_even_after_one_reds(self):
        """One report, not a walk. A round that learns of its second red test on
        the next spawn has bought a second wait for nothing."""
        code, text = run_main(["--test", "exit 3", "--test", "exit 4",
                               "--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 1)
        self.assertIn("(exit 3)", text)
        self.assertIn("(exit 4)", text)

    def test_no_named_test_refuses(self):
        """`SKILL.md`: the round closes when the runner verifies each item's
        NAMED evidence. No named test is no evidence."""
        code, text = run_main(["--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)


class CitationPass(unittest.TestCase):
    def test_a_killed_pass_refuses_the_close(self):
        code, text = run_main(["--test", "true",
                               "--pass-file", str(pass_file(KILLED))])
        self.assertEqual(code, 1)
        self.assertIn("unterminated", text)

    def test_a_missing_pass_file_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrclose-"))
        code, text = run_main(["--test", "true",
                               "--pass-file", str(root / "gone.txt")])
        self.assertEqual(code, 1)
        self.assertIn("absent", text)

    def test_no_pass_file_at_all_refuses(self):
        """R1, adopted 2026-08-23: the round re-runs the citation check before it
        may close. Closing on its own say-so is a conclusion where a measurement
        is owed."""
        code, text = run_main(["--test", "true"])
        self.assertEqual(code, 1)
        self.assertIn("citation", text.lower())

    def test_the_summary_line_is_quoted_back(self):
        """`SKILL.md` asks the round to quote the pass's summary line."""
        code, text = run_main(["--test", "true",
                               "--pass-file", str(pass_file(COMPLETE))])
        self.assertIn("abc1234", text)

    def test_a_red_test_and_a_dead_pass_are_both_named_in_one_report(self):
        code, text = run_main(["--test", "false",
                               "--pass-file", str(pass_file(KILLED))])
        self.assertEqual(code, 1)
        self.assertIn("red", text)
        self.assertIn("unterminated", text)


    def test_a_pass_that_ran_and_returned_non_zero_authorises_and_is_named(self):
        """One rule, two readers: `citation_pass.py` names this and does not
        refuse it, and so must this. The pass RAN, so a re-run reproduces the
        number and the runner would have no road out of a refusal. `SKILL.md`
        already routes it to a register row."""
        body = "=== CITATION PASS COMPLETE === exit=5 pinned=abc1234\n"
        code, text = run_main(["--test", "true",
                               "--pass-file", str(pass_file(body))])
        self.assertEqual(code, 0)
        self.assertIn("exit=5", text)
        self.assertIn("register row", text)

    def test_a_red_tests_own_output_is_quoted_back(self):
        """A refusal naming the command alone costs another turn and another
        whole test run to see why, inside the handover this script shortens."""
        code, text = run_main(
            ["--test", "echo 'expected 3 to be 4' >&2; exit 1",
             "--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 1)
        self.assertIn("expected 3 to be 4", text)

    def test_a_green_tests_output_is_not_quoted(self):
        """A passing suite prints hundreds of lines and none of them is news."""
        _, text = run_main(["--test", "echo quiet | tr a-z A-Z",
                            "--pass-file", str(pass_file(COMPLETE))])
        self.assertIn("quiet", text)      # the command is echoed
        self.assertNotIn("QUIET", text)   # its output is not


class OneRuleTwoReaders(unittest.TestCase):
    def test_the_terminator_rule_is_the_shared_modules_own(self):
        """The runner's commit step, the finale's collection and this close all
        read one function. Three tail checks would drift."""
        import citation_pass
        self.assertIs(close.verdict, citation_pass.verdict)


class Refusal(unittest.TestCase):
    def test_it_never_commits(self):
        """A default of this sitting, recorded in the decisions queue. The
        runner commits; `git-shared-state-guard.py` refuses a commit with no
        explicit paths, and a script that guessed them would stage another
        session's work in a shared index."""
        code, text = run_main(["--test", "true",
                               "--pass-file", str(pass_file(COMPLETE))])
        self.assertEqual(code, 0)
        self.assertIn("commit", text.lower())
        self.assertIn("runner", text.lower())

    def test_the_refusal_says_it_never_waits_for_abdul(self):
        _, text = run_main(["--test", "false",
                            "--pass-file", str(pass_file(COMPLETE))])
        self.assertIn("AFK", text)


if __name__ == "__main__":
    unittest.main()
