#!/usr/bin/env python3
"""Tests for retired-phrases-gate.py.

The hook is the refusal half of a pair. `skills/lib/test_retired_phrases.py`
REPORTS a superseded sentence that already reached a steering file; this hook
REFUSES the write that would put one there. The pair exists because a test
nobody runs is the remember class, and the skills repo has no runner.

What these tests care about most is the second half of the scope: not only that
the hook refuses a retired phrase in a steering file, but that it lets
everything else past. A gate that over-blocks gets removed, and a removed gate
refuses nothing at all.

Run: python3 test_retired_phrases_gate.py
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "retired-phrases-gate.py"
CLAUDE_HOME = Path.home() / ".claude"

RETIRED_PHRASE = "splitting is his call"
STEERING = str(CLAUDE_HOME / "skills" / "to-issues" / "SKILL.md")


def run(payload):
    """Run the hook against a payload. Returns (exit code, stderr)."""
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stderr


def write_payload(path, content, tool="Edit"):
    key = "new_string" if tool == "Edit" else "content"
    return {"tool_name": tool, "tool_input": {"file_path": path, key: content}}


class TestItRefusesARetiredPhrase(unittest.TestCase):
    def test_an_edit_carrying_a_retired_phrase_is_refused(self):
        code, err = run(write_payload(STEERING, f"The rule: {RETIRED_PHRASE}."))
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)

    def test_a_write_carrying_a_retired_phrase_is_refused(self):
        code, _ = run(write_payload(STEERING, RETIRED_PHRASE, tool="Write"))
        self.assertEqual(code, 2)

    def test_the_refusal_names_what_superseded_the_phrase(self):
        """The check_verdict.py lesson: a guard that names only the symptom
        lets the cause repeat. The message must say what to write instead."""
        _, err = run(write_payload(STEERING, RETIRED_PHRASE))
        self.assertIn("cut, harden and stamp itself", err)

    def test_the_refusal_quotes_the_phrase_and_names_the_file(self):
        _, err = run(write_payload(STEERING, RETIRED_PHRASE))
        self.assertIn(RETIRED_PHRASE, err)
        self.assertIn("SKILL.md", err)

    def test_the_refusal_points_history_at_a_decisions_file(self):
        """The commonest legitimate reason to type a dead sentence is to record
        that it died. The message must name where that goes."""
        _, err = run(write_payload(STEERING, RETIRED_PHRASE))
        self.assertIn("decisions.md", err)

    def test_a_hard_wrap_does_not_launder_the_phrase(self):
        wrapped = "The rule: splitting\n   is his call, for now."
        code, _ = run(write_payload(STEERING, wrapped))
        self.assertEqual(code, 2)

    def test_case_does_not_launder_the_phrase(self):
        code, _ = run(write_payload(STEERING, RETIRED_PHRASE.upper()))
        self.assertEqual(code, 2)

    def test_an_agent_brief_is_guarded(self):
        path = str(CLAUDE_HOME / "agents" / "harden-issues-attacker.md")
        code, _ = run(write_payload(path, RETIRED_PHRASE))
        self.assertEqual(code, 2)

    def test_the_two_named_steering_files_are_guarded(self):
        for name in ("CLAUDE.md", "questionrules.md"):
            with self.subTest(name=name):
                code, _ = run(write_payload(str(CLAUDE_HOME / name), RETIRED_PHRASE))
                self.assertEqual(code, 2)


class TestItLetsEverythingElsePast(unittest.TestCase):
    """The half that decides whether the hook survives contact with real work."""

    def test_a_steering_file_without_a_retired_phrase_passes(self):
        code, _ = run(write_payload(STEERING, "An ordinary rule about splits."))
        self.assertEqual(code, 0)

    def test_a_decisions_file_may_carry_a_retired_phrase(self):
        """The exemption that makes the guard usable. A decisions file quotes
        dead wording on purpose, as history and as a supersession note."""
        path = str(CLAUDE_HOME / "skills" / "harden-issues" / "decisions.md")
        code, _ = run(write_payload(path, RETIRED_PHRASE))
        self.assertEqual(code, 0)

    def test_an_ordinary_project_file_may_carry_anything(self):
        code, _ = run(write_payload("/tmp/some-project/notes.md", RETIRED_PHRASE))
        self.assertEqual(code, 0)

    def test_a_project_claude_md_is_not_guarded(self):
        """Scope is the author's own steering directory. A repo's CLAUDE.md is
        somebody else's file and this hook has no opinion about it."""
        code, _ = run(write_payload("/tmp/some-project/CLAUDE.md", RETIRED_PHRASE))
        self.assertEqual(code, 0)

    def test_a_skill_file_two_levels_deep_is_not_guarded(self):
        """`skills/*/SKILL.md` only. A references/ subdirectory is not a skill."""
        path = str(CLAUDE_HOME / "skills" / "panel-review" / "references" / "SKILL.md")
        code, _ = run(write_payload(path, RETIRED_PHRASE))
        self.assertEqual(code, 0)

    def test_the_hook_itself_and_its_test_are_not_guarded(self):
        """Both carry every phrase by definition. A gate that blocks its own
        maintenance is a gate somebody deletes."""
        for path in (HOOK, Path(__file__)):
            with self.subTest(path=path.name):
                code, _ = run(write_payload(str(path), RETIRED_PHRASE))
                self.assertEqual(code, 0)

    def test_a_bash_command_is_not_inspected(self):
        code, _ = run({"tool_name": "Bash",
                       "tool_input": {"command": f"echo '{RETIRED_PHRASE}'"}})
        self.assertEqual(code, 0)


class TestItFailsOpen(unittest.TestCase):
    """H5: a hook that raises takes the caller's tool call with it."""

    def test_a_malformed_payload_passes(self):
        p = subprocess.run([sys.executable, str(HOOK)], input="not json",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)

    def test_an_empty_payload_passes(self):
        code, _ = run({})
        self.assertEqual(code, 0)

    def test_a_payload_with_no_file_path_passes(self):
        code, _ = run({"tool_name": "Edit", "tool_input": {"new_string": RETIRED_PHRASE}})
        self.assertEqual(code, 0)

    def test_a_payload_with_no_content_passes(self):
        code, _ = run({"tool_name": "Edit", "tool_input": {"file_path": STEERING}})
        self.assertEqual(code, 0)

    def test_it_survives_the_denylist_being_unreachable(self):
        """The list lives in the skills repo. If that is gone, the hook must
        wave the write through rather than break every edit in the session."""
        p = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(write_payload(STEERING, RETIRED_PHRASE)),
            capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp/nonexistent-home",
                 "RETIRED_PHRASES_LIB": "/tmp/nonexistent-lib"},
        )
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
