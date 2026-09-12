#!/usr/bin/env python3
"""Drill for correction_brief.py.

The one thing this file exists to pin: the composed prompt earns the cap hook's
correction exemption, judged by the HOOK'S OWN function and never by a second
copy of its rule. A correction brief that puts the marker late is capped like a
first attempt, and its owed list is the varying part that cannot be cut.

    python3 test_correction_brief.py
"""

from __future__ import annotations

import io
import contextlib
import pathlib
import tempfile
import unittest

import correction_brief as brief


GATED = """# 501 something

## Verify gate

verify: pass

## Review gate

review: pass
"""


def issue(body: str = GATED, name: str = "501-a.md") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = brief.main(argv)
    return code, out.getvalue()


class Compose(unittest.TestCase):
    def test_the_marker_lands_inside_the_hooks_opening_window(self):
        """Read by the hook's own `is_correction`, imported, not copied. Ticket
        36 ruling 11 reads `CORRECTION ROUND` in the opening alone."""
        text = brief.compose(issue(), ["a missing pin on the totals test"])
        self.assertTrue(brief.earns_exemption(text))

    def test_every_item_reaches_the_prompt(self):
        text = brief.compose(issue(), ["the first owed thing",
                                       "the second owed thing"])
        self.assertIn("the first owed thing", text)
        self.assertIn("the second owed thing", text)

    def test_the_items_are_numbered(self):
        text = brief.compose(issue(), ["one", "two"])
        self.assertIn("1. one", text)
        self.assertIn("2. two", text)

    def test_the_issue_path_is_carried_in_full(self):
        path = issue()
        self.assertIn(str(path), brief.compose(path, ["x"]))

    def test_it_says_the_runner_commits(self):
        """`SKILL.md`: an implementer never commits its own work. A correction
        implementer is an implementer."""
        self.assertIn("commit", brief.compose(issue(), ["x"]).lower())

    def test_it_carries_no_run_facts(self):
        """The round's whole shape: the items, the marker and nothing else. The
        run's facts are in the ledger header the implementer reads first."""
        text = brief.compose(issue(), ["x"]).lower()
        for leaked in ("register", "dev server", "workspace", "sign-in", "qa"):
            self.assertNotIn(leaked, text)


class Refusal(unittest.TestCase):
    def test_no_owed_items_refuses(self):
        """An empty owed list is not a correction round. `SKILL.md`: both gates
        pass and a verdict enumerates follow-up items. Nothing owed is `done`."""
        code, text = run_main(["--issue", str(issue())])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_a_missing_issue_file_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        code, text = run_main(["--issue", str(root / "nope.md"), "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("nope.md", text)

    def test_an_issue_file_with_no_gate_section_refuses(self):
        """The scope of the round is the verdicts' owed list. No verdict on disk
        means the list was built from something else."""
        code, text = run_main(["--issue", str(issue("# 501\n\nnothing\n")),
                               "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("gate", text.lower())

    def test_an_issue_path_inside_a_worktree_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        deep = root / ".claude" / "worktrees" / "batch-1" / ".scratch"
        deep.mkdir(parents=True)
        path = deep / "501-a.md"
        path.write_text(GATED, encoding="utf-8")
        code, text = run_main(["--issue", str(path), "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("worktree", text.lower())

    def test_a_blank_item_refuses(self):
        code, text = run_main(["--issue", str(issue()), "--item", "   "])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_the_refusal_says_it_never_waits_for_abdul(self):
        _, text = run_main(["--issue", str(issue())])
        self.assertIn("AFK", text)

    def test_a_composed_prompt_that_lost_its_marker_refuses(self):
        """The guard is on the OUTPUT, so a later edit to the preamble that
        pushes the marker past the window is caught here rather than on a run."""
        original = brief.PREAMBLE
        try:
            brief.PREAMBLE = "x" * 500 + "\nCORRECTION ROUND for {issue}.\n"
            code, text = run_main(["--issue", str(issue()), "--item", "x"])
            self.assertEqual(code, 1)
            self.assertIn("exemption", text.lower())
        finally:
            brief.PREAMBLE = original


class ItemsFile(unittest.TestCase):
    def test_items_come_off_a_file_one_per_line(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        listing = root / "owed.txt"
        listing.write_text("first\n\nsecond\n", encoding="utf-8")
        code, text = run_main(["--issue", str(issue()),
                               "--items-file", str(listing)])
        self.assertEqual(code, 0)
        self.assertIn("1. first", text)
        self.assertIn("2. second", text)

    def test_a_missing_items_file_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        code, _ = run_main(["--issue", str(issue()),
                            "--items-file", str(root / "gone.txt")])
        self.assertEqual(code, 1)


class SharedRule(unittest.TestCase):
    def test_the_exemption_is_the_hooks_own_function_when_the_hook_is_there(self):
        """One rule, two readers. Sitting 2 of this ticket found the cap's
        record re-implementing the refusal's exemption tests, and a later change
        to one alone would have the two disagreeing."""
        self.assertTrue(brief.hook_module() is None
                        or hasattr(brief.hook_module(), "is_correction"))

    def test_the_real_hook_lets_the_real_prompt_past(self):
        """End to end, not a stand-in. The hook's own `decide` is handed the
        payload shape a spawn produces, carrying this script's own output."""
        hook = brief.hook_module()
        if hook is None:
            self.skipTest("no cap hook installed on this machine")
        prompt = brief.compose(issue(), ["x " * 500])
        code, _ = hook.decide({
            "tool_input": {"subagent_type": "run-issues-implementer",
                           "prompt": prompt}})
        self.assertEqual(code, 0)

    def test_the_same_prompt_without_the_marker_is_refused_by_the_real_hook(self):
        """The counterpart: proof the exemption is what carried it, not brevity."""
        hook = brief.hook_module()
        if hook is None:
            self.skipTest("no cap hook installed on this machine")
        prompt = brief.compose(issue(), ["x " * 500]).replace(
            "CORRECTION ROUND", "Follow-up work")
        code, _ = hook.decide({
            "tool_input": {"subagent_type": "run-issues-implementer",
                           "prompt": prompt}})
        self.assertEqual(code, 2)

    def test_with_no_hook_installed_the_prompt_is_still_emitted(self):
        """No hook means no cap to fail. Refusing there would stop a run over a
        guard that is not present."""
        original = brief.hook_module
        try:
            brief.hook_module = lambda: None
            code, text = run_main(["--issue", str(issue()), "--item", "x"])
            self.assertEqual(code, 0)
            self.assertIn("CORRECTION ROUND", text)
        finally:
            brief.hook_module = original


if __name__ == "__main__":
    unittest.main()
