"""Drill for gate-commit-guard.py.

The refused cases are the two commits a run's critical review gate actually made
on 2026-09-17, including the `-c core.hooksPath=/dev/null` form it used on the
first and volunteered afterwards.

Run: python3 test_gate_commit_guard.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(stem, name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, stem))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load("gate-commit-guard.py", "gate_commit_guard")

GATE = "run-issues-review-gate-critical"


def refused(agent_type, command):
    return mod.verdict(agent_type, command) is not None


# ── The measured fault ──────────────────────────────────────────────────────

def test_the_plain_commit_the_gate_made_is_refused():
    assert refused(GATE, 'git commit -q -m "Record the gate rows"')


def test_the_hooks_path_spelling_is_refused_too():
    # The form the gate used on the first of the two, which turns the other
    # hooks off.
    assert refused(
        GATE,
        "git -c core.hooksPath=/dev/null commit -m 'rows'")


def test_the_refusal_names_the_role_and_the_road_out():
    reason = mod.verdict(GATE, "git commit -m x")
    assert GATE in reason
    assert "UNCOMMITTED" in reason
    assert "runner" in reason


def test_the_refusal_says_it_is_not_a_halt():
    reason = mod.verdict(GATE, "git commit -m x")
    assert "NOT A HALT" in reason
    assert "NEVER WAITS FOR THE HUMAN" in reason


def test_the_refusal_names_no_person_and_no_run():
    """H2: the message a stranger reads carries no name and no run id."""
    reason = mod.verdict(GATE, "git commit -m x")
    assert "batch-" not in reason


# ── Every gate role, and only them ──────────────────────────────────────────

def test_every_gate_role_is_refused():
    for role in mod.GATES:
        assert refused(role, "git commit -m x"), role


def test_the_runner_may_commit():
    # The main session carries no agent_type, and the runner is what commits.
    assert not refused("", "git commit -m x")


def test_an_implementer_is_not_this_hook_s_business():
    assert not refused("run-issues-implementer", "git commit -m x")


def test_the_finale_may_commit():
    assert not refused("run-issues-finale", "git commit -m x")


def test_promotion_may_commit():
    assert not refused("promotion", "git commit -m x")


# ── Command positions ───────────────────────────────────────────────────────

def test_a_commit_after_and_and_is_refused():
    assert refused(GATE, "git add . && git commit -m x")


def test_a_commit_after_a_semicolon_is_refused():
    assert refused(GATE, "cd /tmp; git commit -m x")


def test_a_commit_in_a_subshell_is_refused():
    assert refused(GATE, "(git commit -m x)")


# ── What a gate keeps ───────────────────────────────────────────────────────

def test_a_gate_may_still_stage():
    assert not refused(GATE, "git add .scratch/register.d/x.md")


def test_a_gate_may_still_read_history():
    assert not refused(GATE, "git log --oneline -5")
    assert not refused(GATE, "git diff HEAD~1")
    assert not refused(GATE, "git status --short")


def test_a_gate_may_run_a_suite():
    assert not refused(GATE, "npx vitest run tests/example.test.ts")


def test_a_word_merely_containing_commit_is_untouched():
    assert not refused(GATE, "grep -rn 'git commit' ~/.claude/skills")


def test_an_empty_command_is_not_a_refusal():
    assert not refused(GATE, "")


# ── The role list must not drift from the pack ──────────────────────────────

def test_every_guarded_role_has_a_definition_in_the_pack():
    """A name in `GATES` that no `agents/` file defines is a typo, and a typo
    here is a role that quietly stops being guarded."""
    agents = os.path.join(HERE, "..", "agents")
    if not os.path.isdir(agents):
        return  # The hook was copied out of the pack on its own. Nothing to pin.
    for role in mod.GATES:
        assert os.path.isfile(os.path.join(agents, role + ".md")), role


# ── The hook contract ───────────────────────────────────────────────────────

def test_a_malformed_command_never_breaks_the_session():
    assert mod.verdict(GATE, None) is None


def test_only_bash_is_guarded():
    assert mod.GUARDED_TOOLS == ("Bash",)


def _load_tests(loader=None, tests=None, pattern=None):
    """Wrap this file's plain `test_` functions as a unittest suite.

    The suite runner reads an executed-count from a unittest or pytest summary
    line, and refuses a file that prints neither -- an unread instrument and a
    clean instrument look alike. These checks are plain functions rather than
    `TestCase` methods, so this is what gives them a `Ran N tests` line to be
    counted by.
    """
    import unittest
    suite = unittest.TestSuite()
    for name in sorted(n for n, v in list(globals().items())
                       if n.startswith("test_") and callable(v)):
        suite.addTest(unittest.FunctionTestCase(globals()[name], description=name))
    return suite


load_tests = _load_tests


if __name__ == "__main__":
    import unittest
    unittest.main(argv=["-"], exit=True)
