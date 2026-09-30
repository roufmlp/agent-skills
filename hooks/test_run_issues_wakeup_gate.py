#!/usr/bin/env python3
"""Drill for run-issues-wakeup-gate.py.

Run: python3 test_run_issues_wakeup_gate.py

A `unittest` file, so `python3 <file>` runs every check with no pytest. The
end-to-end class builds a real repository with a linked worktree and drives
`main()` through the skill's own `find_live_ledger.py` and `wakeup_cron.py`;
set RUN_ISSUES_SKILL_DIR to drill a skill checkout other than the live one.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_issues_wakeup_gate", os.path.join(HERE, "run-issues-wakeup-gate.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.SKILL_DIR = os.environ.get("RUN_ISSUES_SKILL_DIR", mod.SKILL_DIR)
_, wakeup_cron = mod.load_skill()

PATH = "/Users/x/code/p/.scratch/f/runs/batch-abc123/run.md"
HEADER = ("# Run ledger — `batch-abc123`\n\nOwner: session pid 700\n"
          "Worktree: /Users/x/code/p/.claude/worktrees/run-issues-batch-abc123\n")
LIVE = wakeup_cron.with_line(HEADER, "Wakeup cron: d1ab29e9 pid 700")
CLEARED = wakeup_cron.with_line(HEADER, "Wakeup cron: none — deleted 2026-09-29 10:00")


def decide(text=LIVE, agent="run-issues-implementer", pid=700, ledgers=None):
    payload = {"cwd": "/Users/x/code/p/.claude/worktrees/run-issues-batch-abc123",
               "tool_input": {"subagent_type": agent, "prompt": "issue 12"}}
    return mod.decide(payload,
                      ledgers=[(PATH, text)] if ledgers is None else ledgers,
                      pid=pid, read_wakeup=wakeup_cron.read_wakeup)


class TheRefusal(unittest.TestCase):
    def test_a_line_naming_a_job_of_this_process_passes(self):
        self.assertEqual(decide(), (0, ""))

    def test_a_ledger_with_no_line_refuses(self):
        code, message = decide(HEADER)
        self.assertEqual(code, 2)
        self.assertIn("no `Wakeup cron:` line", message)

    def test_a_cleared_line_refuses(self):
        code, message = decide(CLEARED)
        self.assertEqual(code, 2)
        self.assertIn("names no job", message)

    def test_a_line_from_a_dead_process_refuses(self):
        """The resume case: a new process, and the old job died with the old one."""
        code, message = decide(LIVE, pid=701)
        self.assertEqual(code, 2)
        self.assertIn("process 700", message)
        self.assertIn("701", message)

    def test_every_run_issues_role_is_checked(self):
        for agent in ("run-issues-implementer", "run-issues-implementer-escalated",
                      "run-issues-verify-gate", "run-issues-review-gate",
                      "run-issues-review-gate-critical", "run-issues-finale"):
            self.assertEqual(decide(HEADER, agent=agent)[0], 2, agent)

    def test_every_other_spawn_passes(self):
        for agent in ("general-purpose", "promotion", "parallel-hunt-finder",
                      "Explore", ""):
            self.assertEqual(decide(HEADER, agent=agent), (0, ""), agent)

    def test_a_spawn_outside_every_live_run_passes(self):
        self.assertEqual(decide(ledgers=[]), (0, ""))

    def test_one_good_copy_of_the_two_is_enough(self):
        """The runner writes one copy and mirrors it; a spawn between the two
        writes must not be refused for the copy that lags."""
        pair = [(PATH, HEADER), ("/main/copy/run.md", LIVE)]
        self.assertEqual(decide(ledgers=pair), (0, ""))

    def test_without_a_process_id_any_named_job_passes(self):
        self.assertEqual(decide(LIVE, pid=None), (0, ""))
        self.assertEqual(decide(HEADER, pid=None)[0], 2)

    def test_the_refusal_names_the_three_steps_and_the_ledger(self):
        _, message = decide(HEADER)
        self.assertIn("CronList", message)
        self.assertIn(f"wakeup_cron.py args --ledger {PATH}", message)
        self.assertIn(f"wakeup_cron.py record --ledger {PATH}", message)
        self.assertIn("Never make a second one", message)

    def test_the_refusal_records_the_job_in_every_copy(self):
        """A line recorded in one copy only is erased by the runner's next mirror."""
        pair = [(PATH, HEADER), ("/main/copy/run.md", HEADER)]
        _, message = decide(ledgers=pair)
        self.assertIn(f"record --ledger {PATH} --id <job id>", message)
        self.assertIn("record --ledger /main/copy/run.md --id <job id>", message)

    def test_the_copy_inside_the_run_tree_is_named_first(self):
        tree = "/Users/x/code/p/.claude/worktrees/run-issues-batch-abc123"
        inside = tree + "/.scratch/f/runs/batch-abc123/run.md"
        runs = [(tree, "/Users/x/code/p/.scratch/f/runs/batch-abc123/run.md"),
                (tree, inside)]
        self.assertEqual(mod.owned_ledgers(tree, runs)[0], inside)

    def test_the_refusal_never_waits_for_the_human(self):
        _, message = decide(HEADER)
        self.assertIn("NEVER WAITS FOR THE HUMAN", message)
        self.assertIn("not a halt".upper(), message.upper())

    def test_a_payload_it_cannot_read_passes(self):
        for payload in (None, [], {}, {"tool_input": "x"}):
            self.assertEqual(mod.decide(payload, ledgers=[(PATH, HEADER)],
                                        read_wakeup=wakeup_cron.read_wakeup),
                             (0, ""))


class TheTreeThatOwnsTheSpawn(unittest.TestCase):
    MAIN = "/Users/x/code/p"
    LINKED = "/Users/x/code/p/.claude/worktrees/run-issues-batch-abc123"

    def test_the_deepest_named_tree_owns_a_nested_directory(self):
        runs = [(self.MAIN, "/a/run.md"), (self.LINKED, "/b/run.md"),
                (self.LINKED, "/c/run.md")]
        self.assertEqual(mod.owned_ledgers(self.LINKED + "/src", runs),
                         ["/b/run.md", "/c/run.md"])

    def test_a_sibling_prefix_is_not_inside(self):
        runs = [(self.LINKED, "/b/run.md")]
        self.assertEqual(mod.owned_ledgers(self.LINKED + "-other", runs), [])

    def test_a_run_with_no_named_tree_owns_nothing(self):
        self.assertEqual(mod.owned_ledgers(self.MAIN, [("", "/a/run.md")]), [])


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class EndToEnd(unittest.TestCase):
    """A real repository, a real linked worktree, and `main()` reading both."""

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.main = os.path.join(self.root, "p")
        os.makedirs(self.main)
        git("init", "-q", cwd=self.main)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
            "--allow-empty", "-m", "init", cwd=self.main)
        self.tree = os.path.join(self.root, "run-issues-batch-abc123")
        git("worktree", "add", "-q", self.tree, cwd=self.main)
        folder = os.path.join(self.tree, ".scratch", "f", "runs", "batch-abc123")
        os.makedirs(folder)
        self.ledger = os.path.join(folder, "run.md")
        self.write(f"# Run ledger — `batch-abc123`\n\nOwner: session pid 700\n"
                   f"Worktree: {self.tree}\nState: 12 implement\n")

    def write(self, text):
        with open(self.ledger, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_main(self, agent="run-issues-implementer", cwd=None, pid="700"):
        payload = {"cwd": cwd or self.tree,
                   "tool_input": {"subagent_type": agent, "prompt": "issue 12"}}
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.dict(os.environ, {"CLAUDE_PID": pid}), \
                redirect_stderr(err):
            code = mod.main()
        return code, err.getvalue()

    def test_a_run_that_forgot_the_cron_is_refused(self):
        code, message = self.run_main()
        self.assertEqual(code, 2, message)
        self.assertIn(self.ledger, message)

    def test_recording_the_job_lets_the_spawn_through(self):
        done = subprocess.run(
            [sys.executable, os.path.join(mod.SKILL_DIR, "wakeup_cron.py"),
             "record", "--ledger", self.ledger, "--id", "d1ab29e9"],
            env=dict(os.environ, CLAUDE_PID="700"), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.run_main(), (0, ""))
        # The same line, read by a later process, is a dead job.
        self.assertEqual(self.run_main(pid="701")[0], 2)

    def test_both_live_copies_are_read_and_named(self):
        """The mirrored shape: the runner writes the worktree copy and mirrors
        it to the main checkout. `runs()` keeps one copy per batch."""
        folder = os.path.join(self.main, ".scratch", "f", "runs", "batch-abc123")
        os.makedirs(folder)
        mirror = os.path.join(folder, "run.md")
        with open(self.ledger, encoding="utf-8") as handle:
            text = handle.read()
        with open(mirror, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, message = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn(f"record --ledger {self.ledger} --id", message)
        self.assertIn(f"record --ledger {mirror} --id", message)
        # The copy in the run's own tree is the one `args` names.
        self.assertIn(f"args --ledger {self.ledger}`", message)

    def test_a_spawn_from_the_main_checkout_is_not_this_runs(self):
        self.assertEqual(self.run_main(cwd=self.main)[0], 0)

    def test_a_finished_run_is_not_checked(self):
        self.write(f"# Run ledger — `batch-abc123`\n\n"
                   f"Owner: none — awaiting-merge 2026-09-29 11:00\n"
                   f"Worktree: {self.tree}\nState: awaiting-merge\n")
        self.assertEqual(self.run_main()[0], 0)

    def test_a_foreign_spawn_pays_for_nothing(self):
        with mock.patch.object(mod, "load_skill",
                               side_effect=AssertionError("read the skill")):
            self.assertEqual(self.run_main(agent="general-purpose"), (0, ""))

    def test_a_broken_skill_fails_open_and_says_so(self):
        with mock.patch.object(mod, "load_skill", side_effect=ImportError("gone")):
            code, message = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("passed unchecked", message)


class TheRegistration(unittest.TestCase):
    def test_the_hook_is_registered_on_agent_and_task(self):
        settings = os.path.join(HERE, "..", "settings.json")
        if not os.path.isfile(settings):
            # Installed, this drill sits in `~/.claude/hooks` and the settings
            # file is its neighbour. In a copy of the pack there is none.
            self.skipTest("no settings.json beside this hooks directory, so "
                          "this copy is not installed")
        with open(settings, encoding="utf-8") as handle:
            hooks = json.load(handle)["hooks"]["PreToolUse"]
        commands = [hook.get("command", "")
                    for block in hooks if block.get("matcher") == "Agent|Task"
                    for hook in block.get("hooks", [])]
        self.assertTrue(any(c.endswith("/hooks/run-issues-wakeup-gate.py")
                            for c in commands), commands)


if __name__ == "__main__":
    unittest.main()
