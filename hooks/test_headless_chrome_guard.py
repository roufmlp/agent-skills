"""Drill for headless-chrome-guard.py.

The refused corpus is the shapes agents actually typed, taken from the session
records on 2026-09-30. The passing cases are the wrapper and commands that never
name a Chrome binary.
"""

import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "headless_chrome_guard", os.path.join(HERE, "headless-chrome-guard.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SAFE = ("--use-mock-keychain --password-store=basic --mute-audio "
        "--disable-features=HardwareMediaKeyHandling")


def refused(command):
    return mod.verdict(command) is not None


# ── The measured forms ──────────────────────────────────────────────────────

def test_the_literal_path_form_agents_typed_47_times_is_refused():
    assert refused(f'"{APP}" --headless=new --disable-gpu --no-sandbox '
                   '--virtual-time-budget=10000 --dump-dom "file://$PWD/flow.html"')


def test_the_path_held_in_a_variable_is_refused():
    assert refused(f'CH="{APP}"; "$CH" --headless=new --dump-dom file:///tmp/x.html')


def test_the_path_inside_a_python_heredoc_is_refused():
    assert refused("python3 - <<'PY'\nimport subprocess\n"
                   f"subprocess.run(['{APP}', '--headless', '--dump-dom', 'x'])\nPY")


def test_the_refusal_names_the_missing_flags_and_the_wrapper():
    reason = mod.verdict(f'"{APP}" --headless=new --dump-dom x')
    assert "--use-mock-keychain" in reason
    assert mod.WRAPPER in reason
    assert "2026-09-30" in reason


# ── Every spelling of the same binary ───────────────────────────────────────

def test_an_escaped_space_is_refused():
    assert refused(r"/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome "
                   "--headless --screenshot x")


def test_chromium_is_refused():
    assert refused("/Applications/Chromium.app/Contents/MacOS/Chromium --headless x")


def test_canary_is_refused():
    assert refused("'/Applications/Google Chrome Canary.app/Contents/MacOS/"
                   "Google Chrome Canary' --headless x")


def test_chrome_for_testing_is_refused():
    assert refused("~/Library/Caches/ms-playwright/chromium-1200/chrome-mac/"
                   "Google Chrome for Testing.app/Contents/MacOS/"
                   "Google Chrome for Testing --headless x")


def test_a_partial_set_of_flags_is_still_refused():
    reason = mod.verdict(f'"{APP}" --use-mock-keychain --headless x')
    assert reason is not None
    assert "--password-store=basic" in reason
    assert "`--use-mock-keychain`" not in reason


# ── What passes ─────────────────────────────────────────────────────────────

def test_the_wrapper_passes():
    assert not refused('~/.claude/bin/headless-chrome --dump-dom "file://$PWD/x.html"')


def test_the_binary_with_every_flag_passes():
    assert not refused(f'"{APP}" {SAFE} --headless=new --dump-dom x')


def test_a_command_that_never_names_chrome_passes():
    assert not refused("npm test")


def test_checking_the_bundle_directory_passes():
    assert not refused('ls "/Applications/Google Chrome.app"')


def test_opening_a_url_in_the_humans_chrome_passes():
    assert not refused('open -a "Google Chrome" https://example.com')


def test_an_empty_command_passes():
    assert not refused("")


# ── The hook boundary ───────────────────────────────────────────────────────

def run_hook(payload):
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "headless-chrome-guard.py")],
        input=payload, capture_output=True, text=True)


def test_the_hook_exits_2_on_a_refusal():
    result = run_hook(json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": f'"{APP}" --headless x'}}))
    assert result.returncode == 2
    assert "REFUSED" in result.stderr


def test_the_hook_ignores_other_tools():
    result = run_hook(json.dumps(
        {"tool_name": "Write", "tool_input": {"command": f'"{APP}" --headless x'}}))
    assert result.returncode == 0


def test_a_malformed_payload_never_breaks_the_session():
    assert run_hook("not json").returncode == 0


def _load_tests(loader=None, tests=None, pattern=None):
    """Wrap this file's plain `test_` functions as a unittest suite, the shape
    `test_machine_wide_kill_guard.py` uses, so the runner reads `Ran N tests`."""
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
