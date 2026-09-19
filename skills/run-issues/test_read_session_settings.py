"""Drill for read_session_settings.py.

The case that matters is the one run `batch-26c495` got wrong on 2026-09-17: a
session whose model is a command-line flag and whose effort is only ever a
settings key.
"""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "read_session_settings", os.path.join(HERE, "read_session_settings.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


ONLY_PROJECT = (
    (".claude/settings.local.json", "project-local settings"),
    (".claude/settings.json", "project settings"),
)


def _repo(**files):
    """A throwaway repo carrying the named settings files."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    for name, payload in files.items():
        with open(os.path.join(root, ".claude", name), "w",
                  encoding="utf-8") as handle:
            json.dump(payload, handle)
    return root


# ── The measured fault ──────────────────────────────────────────────────────

def test_effort_is_found_in_settings_when_no_flag_carries_it():
    root = _repo(**{"settings.json": {"effortLevel": "high"}})
    value, source = mod.read(pid="", repo=root, files=ONLY_PROJECT)["effort"]
    assert value == "high"
    assert "project settings" in source


def test_the_source_is_named_so_a_reader_can_check_it():
    root = _repo(**{"settings.json": {"effortLevel": "high"}})
    value, source = mod.read(pid="", repo=root, files=ONLY_PROJECT)["effort"]
    assert root in source


def test_a_value_found_nowhere_still_reads_unmeasured():
    # The old behaviour must survive: a guess is worse than a gap.
    value, source = mod.read(pid="", repo=_repo(), files=ONLY_PROJECT)["effort"]
    assert value == "unmeasured"
    assert "no settings file" in source


# ── Precedence ──────────────────────────────────────────────────────────────

def test_project_local_beats_project():
    root = _repo(**{"settings.local.json": {"effortLevel": "max"},
                    "settings.json": {"effortLevel": "high"}})
    assert mod.read(pid="", repo=root, files=ONLY_PROJECT)["effort"][0] == "max"


def test_a_command_line_flag_beats_every_settings_file(monkeypatched=None):
    root = _repo(**{"settings.json": {"effortLevel": "high"}})
    original = mod.from_command_line
    mod.from_command_line = lambda pid: {"effort": "medium"}
    try:
        value, source = mod.read(pid="1", repo=root, files=ONLY_PROJECT)["effort"]
        assert value == "medium"
        assert "command line" in source
    finally:
        mod.from_command_line = original


# ── The model road, which was never broken and must stay working ────────────

def test_the_model_still_comes_off_the_command_line():
    original = mod.from_command_line
    mod.from_command_line = lambda pid: {"model": "claude-opus-5"}
    try:
        value, source = mod.read(pid="1", repo=_repo(), files=ONLY_PROJECT)["model"]
        assert value == "claude-opus-5"
        assert "command line" in source
    finally:
        mod.from_command_line = original


def test_the_model_is_never_taken_from_a_settings_file():
    # `model` in settings names a default for NEW sessions, not what this
    # process is running, so reading it would be a guess wearing a source.
    root = _repo(**{"settings.json": {"model": "claude-fable-5-1"}})
    assert mod.read(pid="", repo=root, files=ONLY_PROJECT)["model"][0] == "unmeasured"


# ── Flag spellings ──────────────────────────────────────────────────────────

def test_both_flag_spellings_are_read():
    class _Done:
        stdout = "claude --model claude-opus-5 --effort=max --print"

    original = mod.subprocess.run
    mod.subprocess.run = lambda *a, **k: _Done()
    try:
        found = mod.from_command_line("1")
        assert found["model"] == "claude-opus-5"
        assert found["effort"] == "max"
    finally:
        mod.subprocess.run = original


def test_no_pid_reads_no_command_line_and_does_not_raise():
    assert mod.from_command_line("") == {}


# ── It can never halt a launch ──────────────────────────────────────────────

def test_an_unreadable_settings_file_is_skipped_rather_than_raised():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    with open(os.path.join(root, ".claude", "settings.json"), "w",
              encoding="utf-8") as handle:
        handle.write("{ this is not json")
    assert mod.read(pid="", repo=root, files=ONLY_PROJECT)["effort"][0] == "unmeasured"


def test_main_exits_zero_whatever_it_finds():
    assert mod.main(["--pid", "", "--repo", _repo()]) == 0


def test_the_output_carries_both_ledger_header_lines():
    text = "\n".join(mod.lines(mod.read(pid="", repo=_repo(), files=ONLY_PROJECT)))
    assert "Session model at launch:" in text
    assert "Session effort at launch:" in text


def _load_tests(loader=None, tests=None, pattern=None):
    """Wrap this file's plain `test_` functions as a unittest suite, so the
    repo's suite runner can read an executed-count off a `Ran N tests` line."""
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
