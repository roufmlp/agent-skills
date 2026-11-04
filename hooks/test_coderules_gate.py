#!/usr/bin/env python3
"""Tests for coderules-gate: the first code edit of a context is blocked once and sent to the
`coderules` skill; prose, scratch files and a second edit pass.

Run: python3 test_coderules_gate.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
GATE = HOOKS / "coderules-gate.py"


def run(payload, state):
    env = {**os.environ, "CODERULES_GATE_STATE": state}
    proc = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return proc.returncode, proc.stderr


def edit(path, session=None, agent=None, agent_type=None):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": path}, "session_id": session or uuid.uuid4().hex}
    if agent:
        payload["agent_id"] = agent
        payload["agent_type"] = agent_type or agent
    return payload


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_first_code_edit_is_blocked_and_names_the_skill_not_a_rules_file(self):
        code, err = run(edit("/repo/src/app.ts"), self.state)
        self.assertEqual(code, 2)
        self.assertIn("`coderules` skill", err)
        self.assertIn("Skill tool", err)
        self.assertNotIn("coderules.md", err)

    def test_the_message_says_where_the_skill_is_or_that_it_is_missing(self):
        _, err = run(edit("/repo/src/app.ts"), self.state)
        self.assertTrue("installed at" in err or "not installed" in err, err)

    def test_the_second_edit_in_the_same_context_passes(self):
        session = uuid.uuid4().hex
        self.assertEqual(run(edit("/repo/a.py", session), self.state)[0], 2)
        self.assertEqual(run(edit("/repo/b.py", session), self.state)[0], 0)

    def test_a_subagent_of_the_same_session_is_its_own_context(self):
        session = uuid.uuid4().hex
        self.assertEqual(run(edit("/repo/a.py", session), self.state)[0], 2)
        code, err = run(edit("/repo/b.py", session, agent="a1", agent_type="run-issues-implementer"), self.state)
        self.assertEqual(code, 2)
        self.assertIn("run-issues-implementer", err)

    def test_prose_and_scratch_files_pass_without_a_marker(self):
        for path in ["/repo/README.md", "/repo/.scratch/notes.json", "/repo/node_modules/x/index.js", ""]:
            self.assertEqual(run(edit(path), self.state)[0], 0, path)
        self.assertEqual(os.listdir(self.state) if os.path.isdir(self.state) else [], [])

    def test_a_malformed_payload_never_breaks_the_call(self):
        proc = subprocess.run([sys.executable, str(GATE)], input="not json", capture_output=True, text=True,
                              env={**os.environ, "CODERULES_GATE_STATE": self.state})
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
