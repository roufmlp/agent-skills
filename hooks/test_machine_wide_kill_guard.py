"""Drill for machine-wide-kill-guard.py.

The corpus is the shape an agent actually types. The refused case is the one a
verify gate typed on 2026-09-17, walking a run's decisions; the passing cases are
the ones that run's finale typed the same evening.

Run: python3 test_machine_wide_kill_guard.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "machine_wide_kill_guard", os.path.join(HERE, "machine-wide-kill-guard.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def refused(command):
    return mod.verdict(command) is not None


# ── The measured fault ──────────────────────────────────────────────────────

def test_the_call_the_verify_gate_actually_made_is_refused():
    assert refused("pkill -9 -f vitest")


def test_the_refusal_names_the_command_and_offers_the_pid_road():
    reason = mod.verdict("pkill -9 -f vitest")
    assert "pkill" in reason
    assert "kill" in reason and "pid" in reason
    assert "2026-09-17" in reason


# ── Every road to the same thing ────────────────────────────────────────────

def test_killall_is_refused():
    assert refused("killall node")


def test_sudo_does_not_get_round_it():
    assert refused("sudo pkill -f next")


def test_a_pattern_kill_after_a_pipe_is_refused():
    assert refused("ps -ax | pkill -f vitest")


def test_a_pattern_kill_after_a_semicolon_is_refused():
    assert refused("cd /tmp; pkill -f vitest")


def test_a_pattern_kill_after_and_and_is_refused():
    assert refused("npm test && pkill -f vitest")


def test_a_pattern_kill_in_a_subshell_is_refused():
    assert refused("(pkill -f vitest)")


def test_kill_fed_from_a_substitution_is_refused():
    assert refused("kill $(pgrep -f vitest)")


def test_kill_fed_from_backticks_is_refused():
    assert refused("kill -9 `pgrep -f next`")


# ── What must keep working ──────────────────────────────────────────────────

def test_a_literal_pid_is_never_refused():
    # A run's finale stopped its own dev server this way.
    assert not refused("kill 55832")


def test_a_literal_pid_with_a_signal_is_never_refused():
    assert not refused("kill -9 55832")


def test_a_pid_read_from_a_file_this_session_wrote_is_allowed():
    # The shape the refusal text steers toward. It is a substitution, but it
    # reads a pid the caller captured rather than selecting by pattern.
    assert not refused('kill "$(cat /tmp/dev.pid)"')


def test_an_unrelated_command_is_untouched():
    assert not refused("npm test")


def test_a_command_merely_mentioning_the_word_is_untouched():
    assert not refused("grep -rn 'pkill' ~/.claude/hooks")


def test_pgrep_alone_is_a_read_and_is_allowed():
    assert not refused("pgrep -f vitest")


def test_an_empty_command_is_not_a_refusal():
    assert not refused("")


# ── The hook contract ───────────────────────────────────────────────────────

def test_a_malformed_payload_never_breaks_the_session():
    assert mod.verdict(None) is None


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
