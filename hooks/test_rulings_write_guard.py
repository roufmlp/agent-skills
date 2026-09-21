#!/usr/bin/env python3
"""Cases for `rulings-write-guard.py`.

Run: python3 test_rulings_write_guard.py

Every case drives the hook as the harness drives it -- a JSON payload on
stdin, an exit code out -- rather than calling its internals. A test that
asserted on `is_rulings` alone would pass while the wiring was wrong, which is
the class of green guard `~/.claude/coderules.md` refuses.

`unittest` and a real `__main__` block, not bare functions: run_python_suites.py
refuses a file that defines checks and executes none, because that is
indistinguishable from a pass. It refused the first draft of this file on
2026-09-20, which is the guard working.

The malformed entry in `BAD_ENTRY` is the real one: a `Carried by:` line naming
two backticked paths and a commit, which is what dropped nine of one
project's 106 entries on 2026-09-20.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

# The hook BESIDE this drill, so the copy under test is the copy that ships.
HOOK = str(pathlib.Path(__file__).resolve().parent / "rulings-write-guard.py")

GOOD = """# rulings

## 2026-09-01 `q-1` - the first question
Ruled: the first answer.
Carried by: `docs/one.md`

## 2026-09-02 `q-2` - the second question
Ruled: the second answer.
Carried by: `docs/two.md`
"""

BAD_ENTRY = """
## 2026-09-03 `q-3` - the third question
Ruled: the third answer.
Carried by: `docs/three.md`, `docs/four.md`, commit `abc1234`
"""

REPAIRED = """
## 2026-09-03 `q-3` - the third question
Ruled: the third answer.
Carried by: `docs/three.md`
Also carried by: `docs/four.md`, commit `abc1234`
"""

NO_RULED_LINE = """
## 2026-09-04 `q-4` - an entry with no ruling line
Carried by: `docs/x.md`
"""


def run(payload: dict) -> int:
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    return proc.returncode


def write_payload(path: str, content: str) -> dict:
    return {"tool_name": "Write",
            "tool_input": {"file_path": path, "content": content}}


def edit_payload(path: str, old: str, new: str) -> dict:
    return {"tool_name": "Edit",
            "tool_input": {"file_path": path, "old_string": old,
                           "new_string": new}}


class HookCase(unittest.TestCase):
    """A temporary `.scratch/rulings.md`, torn down after each case."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def rulings(self, text: str = GOOD, name: str = "rulings.md",
                folder: str = ".scratch") -> str:
        d = os.path.join(self.root, folder)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p


class WhatMustBeRefused(HookCase):

    def test_write_adding_a_multi_path_carried_by(self):
        """The exact shape that dropped nine entries on 2026-09-20."""
        p = self.rulings()
        self.assertEqual(run(write_payload(p, GOOD + BAD_ENTRY)), 2)

    def test_edit_adding_a_multi_path_carried_by(self):
        p = self.rulings()
        tail = "Carried by: `docs/two.md`\n"
        self.assertEqual(run(edit_payload(p, tail, tail + BAD_ENTRY)), 2)

    def test_emptying_a_rulings_file_that_holds_entries(self):
        """A truncating write would otherwise pass with a clean zero."""
        p = self.rulings()
        self.assertEqual(run(write_payload(p, "# rulings\n\nnothing.\n")), 2)

    def test_an_entry_missing_its_ruled_line(self):
        p = self.rulings()
        self.assertEqual(run(write_payload(p, GOOD + NO_RULED_LINE)), 2)


class WhatMustBeLetPast(HookCase):

    def test_a_well_formed_new_entry(self):
        p = self.rulings()
        self.assertEqual(run(write_payload(p, GOOD + REPAIRED)), 0)

    def test_repairing_an_inherited_bad_entry(self):
        """A partial repair must land, or the file is harder to fix than break."""
        p = self.rulings(GOOD + BAD_ENTRY)
        self.assertEqual(run(write_payload(p, GOOD + REPAIRED)), 0)

    def test_leaving_an_inherited_bad_entry_untouched(self):
        """This hook judges the delta, not the file it inherited."""
        p = self.rulings(GOOD + BAD_ENTRY)
        after = GOOD + BAD_ENTRY + "\nA trailing note.\n"
        self.assertEqual(run(write_payload(p, after)), 0)

    def test_a_rulings_md_outside_a_scratch_tree(self):
        p = self.rulings(folder="docs")
        self.assertEqual(run(write_payload(p, GOOD + BAD_ENTRY)), 0)

    def test_another_file_inside_a_scratch_tree(self):
        p = self.rulings(name="notes.md")
        self.assertEqual(run(write_payload(p, GOOD + BAD_ENTRY)), 0)

    def test_a_bash_call_is_not_judged(self):
        p = self.rulings()
        payload = {"tool_name": "Bash",
                   "tool_input": {"command": f"echo x >> {p}"}}
        self.assertEqual(run(payload), 0)

    def test_an_edit_whose_old_string_is_absent(self):
        """That fails on the Edit tool's own terms; not this hook's call."""
        p = self.rulings()
        self.assertEqual(run(edit_payload(p, "absent text", BAD_ENTRY)), 0)

    def test_creating_a_new_rulings_file(self):
        d = os.path.join(self.root, ".scratch")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "rulings.md")
        self.assertEqual(run(write_payload(p, GOOD)), 0)


class TheHookNeverBreaksASession(unittest.TestCase):

    def test_a_malformed_payload_exits_zero(self):
        proc = subprocess.run([sys.executable, HOOK], input="not json",
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)

    def test_an_empty_payload_exits_zero(self):
        self.assertEqual(run({}), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
