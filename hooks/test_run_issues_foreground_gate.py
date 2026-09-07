#!/usr/bin/env python3
"""What the foreground gate requires of every run-issues spawn.

**Why this file exists.** The hook shipped with a drill in its docstring and no
behavioural test of any kind, while every hook beside it in the tree it came
from had one.

That gap mattered more than it looks. This hook is what lets the orchestrator
keep the gate spawn rather than hand it to a runner script: it recovered 252.8
minutes on one measured run and 87 on another, read by hand out of each gate's
own subagent transcript. And `run_timings.py` cannot confirm those figures --
it REFUSES a verdict on any gate pair holding a backgrounded step, and this hook
backgrounds every verify gate. So the measurement refuses, and before this file
nothing at all would have caught a regression.

THE RULE, keyed on the agent type:

    run-issues-verify-gate    must carry run_in_background: true
    every other run-issues-*  must carry run_in_background: false
    every other agent type    passes untouched

**The load-bearing risk here is the same as its sibling's: a FALSE refusal**,
which stops a legitimate run mid-flight. So the pass side is driven first and
hardest -- every foreign agent type, whatever it carries.

The second load-bearing property is that the two rules are OPPOSITE. A change
that made them agree would silence the hook without failing anything obvious,
because a run whose spawns all carry `false` looks orderly. `TestTheTwoRulesAre
Opposite` is where that would be noticed.

Run: python3 test_run_issues_foreground_gate.py
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
HOOK = HOOKS / "run-issues-foreground-gate.py"

_spec = importlib.util.spec_from_file_location("foreground_gate", HOOK)
foreground = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(foreground)

# Every run-issues agent type that is NOT the verify gate, read off
# `~/.claude/agents/` on 2026-09-07. The rule is keyed on the `run-issues-`
# prefix, so this list is what the rule actually meets rather than a sample.
OTHERS = (
    "run-issues-implementer",
    "run-issues-implementer-escalated",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
    "run-issues-finale",
)


def payload(agent_type, **fields):
    return {"tool_input": {"subagent_type": agent_type, **fields}}


class TestTheVerifyGateGoesToTheBackground(unittest.TestCase):
    """The exception, and the reason the pair overlaps at all.

    Measured on run `batch-b5e96d`, 2026-09-04: zero of fifteen gate pairs went
    out in one message, costing 97 minutes. The cause was a pair of rules the
    runner was under -- the Agent tool's own text says to pass false only when
    the next action depends on the result, and this hook refused anything but
    false. Two gates in one message was the only concurrent shape those rules
    left, and on CLI 2.1.255 the runner produced it zero times in fifteen tries.
    """

    def test_true_passes(self):
        self.assertEqual(
            foreground.decide(payload(foreground.VERIFY, run_in_background=True))[0], 0)

    def test_false_is_refused(self):
        code, message = foreground.decide(
            payload(foreground.VERIFY, run_in_background=False))
        self.assertEqual(code, 2)
        self.assertIn("run_in_background: true", message)

    def test_an_absent_field_is_refused(self):
        """A spawn that names no value is not a spawn that meant true. The
        field is named on every spawn, which is what `SKILL.md` orders."""
        code, message = foreground.decide(payload(foreground.VERIFY))
        self.assertEqual(code, 2)
        self.assertIn("absent", message)

    def test_the_string_true_is_not_true(self):
        """`"true"` is truthy in Python and is NOT what the tool sends. A hook
        that accepted it would pass a spawn the harness runs in the foreground.
        """
        code, _ = foreground.decide(
            payload(foreground.VERIFY, run_in_background="true"))
        self.assertEqual(code, 2)

    def test_one_is_not_true(self):
        """`1 == True` in Python, so an identity test is the only correct one."""
        code, _ = foreground.decide(payload(foreground.VERIFY, run_in_background=1))
        self.assertEqual(code, 2)

    def test_the_refusal_names_the_review_gate_that_follows(self):
        """A refusal that only says "set it true" buys back the field and not
        the concurrency. The whole point is the NEXT turn."""
        message = foreground.decide(
            payload(foreground.VERIFY, run_in_background=False))[1]
        self.assertIn("NEXT turn", message)
        self.assertIn("Do not wait", message)


class TestEveryOtherRunIssuesSpawnStaysInTheForeground(unittest.TestCase):
    def test_false_passes_for_all_of_them(self):
        for kind in OTHERS:
            self.assertEqual(
                foreground.decide(payload(kind, run_in_background=False))[0], 0, kind)

    def test_true_is_refused_for_all_of_them(self):
        for kind in OTHERS:
            code, message = foreground.decide(payload(kind, run_in_background=True))
            self.assertEqual(code, 2, kind)
            self.assertIn("run_in_background: false", message)

    def test_an_absent_field_is_refused_for_all_of_them(self):
        for kind in OTHERS:
            self.assertEqual(foreground.decide(payload(kind))[0], 2, kind)

    def test_the_zero_that_is_not_false(self):
        """`0 == False`, so the identity test guards this end too."""
        self.assertEqual(
            foreground.decide(
                payload("run-issues-implementer", run_in_background=0))[0], 2)

    def test_an_unknown_run_issues_type_takes_the_foreground_rule(self):
        """The rule keys on the prefix, not on a list, so a type minted later
        is covered the day it is minted. That is deliberate: a list would let
        a new agent escape in silence."""
        self.assertEqual(
            foreground.decide(
                payload("run-issues-something-not-built-yet",
                        run_in_background=False))[0], 0)
        self.assertEqual(
            foreground.decide(
                payload("run-issues-something-not-built-yet",
                        run_in_background=True))[0], 2)


class TestItNeverTouchesAnybodyElse(unittest.TestCase):
    """A false refusal here stops a session that has nothing to do with a run."""

    def test_foreign_types_pass_whatever_they_carry(self):
        for kind in ("general-purpose", "Explore", "Plan", "claude",
                     "parallel-hunt-finder", "parallel-hunt-fix-gate",
                     "harden-issues-attacker", "promotion", "statusline-setup"):
            for field in ({}, {"run_in_background": True},
                          {"run_in_background": False},
                          {"run_in_background": "yes"}):
                self.assertEqual(
                    foreground.decide(payload(kind, **field))[0], 0, (kind, field))

    def test_a_payload_with_no_agent_type_passes(self):
        self.assertEqual(foreground.decide({"tool_input": {}})[0], 0)
        self.assertEqual(foreground.decide({})[0], 0)

    def test_a_null_agent_type_passes(self):
        self.assertEqual(
            foreground.decide({"tool_input": {"subagent_type": None}})[0], 0)

    def test_a_type_merely_containing_the_prefix_is_not_matched(self):
        """`startswith`, not `in`. A third-party agent whose name happens to
        carry the words must not be governed by this run's rule."""
        self.assertEqual(
            foreground.decide(
                payload("vendor-run-issues-helper", run_in_background=True))[0], 0)


class TestTheTwoRulesAreOpposite(unittest.TestCase):
    """The property the whole 252.8 minutes rests on.

    If a future edit ever made both halves want the same value, the pair would
    serialise again and every other test here would still pass. This is where
    that is noticed.
    """

    def test_the_verify_gate_wants_what_the_others_refuse(self):
        self.assertEqual(
            foreground.decide(payload(foreground.VERIFY, run_in_background=True))[0], 0)
        self.assertEqual(
            foreground.decide(
                payload("run-issues-review-gate", run_in_background=True))[0], 2)

    def test_the_others_want_what_the_verify_gate_refuses(self):
        self.assertEqual(
            foreground.decide(
                payload("run-issues-review-gate", run_in_background=False))[0], 0)
        self.assertEqual(
            foreground.decide(
                payload(foreground.VERIFY, run_in_background=False))[0], 2)

    def test_exactly_one_type_is_the_exception(self):
        """Named, so that a second exception cannot be added silently."""
        self.assertEqual(foreground.VERIFY, "run-issues-verify-gate")


class TestEveryRefusalIsRunnableWithoutTheHuman(unittest.TestCase):
    """Nobody is at the keyboard for a run, and a refusal that reads like a
    question ends one. Ruled 2026-08-30 and carried by every run-issues hook."""

    def refusals(self):
        found = [foreground.decide(payload(foreground.VERIFY, run_in_background=False))[1]]
        found += [foreground.decide(payload(kind, run_in_background=True))[1]
                  for kind in OTHERS]
        return found

    def test_none_of_them_waits_for_the_human(self):
        for message in self.refusals():
            self.assertIn("NEVER WAITS FOR THE HUMAN", message)
            self.assertIn("HALT BLOCK", message)
            self.assertIn("do not ask", message)

    def test_each_names_the_file_that_refused(self):
        for message in self.refusals():
            self.assertIn("run-issues-foreground-gate.py", message)

    def test_each_says_reissue_this_exact_call(self):
        for message in self.refusals():
            self.assertIn("Reissue this exact call", message)

    def test_a_pass_says_nothing_at_all(self):
        """A hook that printed on the pass side would put a line into every
        spawn's stderr for the whole run."""
        self.assertEqual(
            foreground.decide(payload("general-purpose", run_in_background=True))[1], "")
        self.assertEqual(
            foreground.decide(payload(foreground.VERIFY, run_in_background=True))[1], "")


class TestItRunsAsAHook(unittest.TestCase):
    """Driven through the real file, the way the harness drives it."""

    def run_hook(self, body):
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(body),
            capture_output=True, text=True)
        return done.returncode, done.stderr

    def test_a_refusal_exits_two_and_writes_to_stderr(self):
        code, err = self.run_hook(payload(foreground.VERIFY, run_in_background=False))
        self.assertEqual(code, 2)
        self.assertIn("run_in_background: true", err)

    def test_a_pass_exits_zero_and_says_nothing(self):
        code, err = self.run_hook(payload("general-purpose"))
        self.assertEqual(code, 0)
        self.assertEqual(err.strip(), "")

    def test_broken_input_exits_zero(self):
        """A guard that cannot read its input must not refuse."""
        done = subprocess.run(
            [sys.executable, str(HOOK)], input="not json",
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)

    def test_empty_input_exits_zero(self):
        done = subprocess.run(
            [sys.executable, str(HOOK)], input="", capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)

    def test_the_drill_passes(self):
        """Every hook here carries a drill. This one must stay green."""
        done = subprocess.run(
            [sys.executable, str(HOOK), "--drill"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
