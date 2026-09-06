#!/usr/bin/env python3
"""Tests for origin-row-guard.

Ticket 37 of the pilot-delivery map, ruling 7. Every register row names the
issue and the run that shipped the code it is a fault in.

`check_origin.py` in the run-issues skill grades a file that already exists,
and it deliberately skips a table whose header declares no `origin` column,
because the register holds a dozen historical header shapes and ruling 7 starts
the count the day the key lands. That leaves one hole: a NEW table typed
without the column looks exactly like a historical one.

This hook closes it. A hook sees only writes happening NOW, so it can demand
the column without ever meeting history.

Run: python3 test_origin_row_guard.py
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
GUARD = HOOKS / "origin-row-guard.py"

# The Bash road resolves a redirect target with `generated-file-guard.py`'s
# parser, and this pack does not ship that file. Where it is absent the guard
# passes every Bash write by design, so the two Bash classes below are skipped
# rather than failed: the rule they grade is real, the road is simply not there.
BASH_PARSER = HOOKS / "generated-file-guard.py"
NEEDS_PARSER = unittest.skipUnless(
    BASH_PARSER.is_file(), f"{BASH_PARSER.name} is not beside the guard")

SHARD = "/repo/.scratch/example-feature/register.d/run-a/rg454.md"
NOT_A_SHARD = "/repo/docs/notes.md"

GOOD = (
    "## Rows from run `batch-170a59`\n\n"
    "| id | what | audience | severity | status | origin | owner-notes |\n"
    "|---|---|---|---|---|---|---|\n"
    "| rg454-01 | a thing is wrong | operator | medium | candidate "
    "| 149e/batch-170a59 | candidate; bugs/rg454-01.md |\n"
)

NO_COLUMN = (
    "| id | what | audience | severity | status | owner-notes |\n"
    "|---|---|---|---|---|---|\n"
    "| rg454-01 | a thing is wrong | operator | medium | candidate "
    "| candidate; bugs/rg454-01.md |\n"
)

EMPTY_CELL = GOOD.replace("| 149e/batch-170a59 |", "|  |")


def run_hook(payload: dict) -> tuple:
    done = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload), capture_output=True, text=True)
    return done.returncode, done.stderr


def write_call(path: str, content: str) -> dict:
    return {"tool_name": "Write",
            "tool_input": {"file_path": path, "content": content}}


class TestItDemandsTheColumnOnAShard(unittest.TestCase):
    def test_a_row_naming_its_origin_passes(self):
        self.assertEqual(run_hook(write_call(SHARD, GOOD))[0], 0)

    def test_a_register_table_with_no_origin_column_is_refused(self):
        code, err = run_hook(write_call(SHARD, NO_COLUMN))
        self.assertEqual(code, 2)
        self.assertIn("origin", err.lower())

    def test_an_empty_origin_cell_is_refused_and_the_row_is_named(self):
        code, err = run_hook(write_call(SHARD, EMPTY_CELL))
        self.assertEqual(code, 2)
        self.assertIn("rg454-01", err)

    def test_an_edit_is_judged_the_same_way_as_a_write(self):
        code, _ = run_hook({"tool_name": "Edit",
                            "tool_input": {"file_path": SHARD,
                                           "new_string": NO_COLUMN}})
        self.assertEqual(code, 2)


class TestItStaysOffEverythingElse(unittest.TestCase):
    def test_a_file_outside_a_register_shard_directory_is_not_judged(self):
        self.assertEqual(run_hook(write_call(NOT_A_SHARD, NO_COLUMN))[0], 0)

    def test_a_table_that_is_not_a_register_row_table_is_not_judged(self):
        """A shard holds prose tables too. `audience` and `severity` together
        are what every brief's row shape carries, and nothing else does."""
        prose = ("| after | total | files |\n|---|---|---|\n"
                 "| start | 64 | 32 |\n")
        self.assertEqual(run_hook(write_call(SHARD, prose))[0], 0)

    def test_a_shard_holding_no_table_at_all_passes(self):
        self.assertEqual(run_hook(write_call(SHARD, "just prose\n"))[0], 0)


@NEEDS_PARSER
class TestBash(unittest.TestCase):
    def test_a_heredoc_appending_a_bad_table_to_a_shard_is_refused(self):
        command = f"cat >> {SHARD} <<'EOF'\n{NO_COLUMN}EOF\n"
        code, _ = run_hook({"tool_name": "Bash",
                            "tool_input": {"command": command}})
        self.assertEqual(code, 2)

    def test_a_heredoc_appending_a_good_table_passes(self):
        command = f"cat >> {SHARD} <<'EOF'\n{GOOD}EOF\n"
        code, _ = run_hook({"tool_name": "Bash",
                            "tool_input": {"command": command}})
        self.assertEqual(code, 0)

    def test_reading_a_shard_is_never_a_write(self):
        code, _ = run_hook({"tool_name": "Bash",
                            "tool_input": {"command": f"cat {SHARD}"}})
        self.assertEqual(code, 0)




class TestTheEditHole(unittest.TestCase):
    """An Edit's `new_string` is usually the ROW alone.

    A row with no header above it has no `origin` column to be missing, so the
    guard would pass every bad row appended by Edit — which is how a gate
    appends to a shard it has already opened. The file on disk carries the
    header, so the judgement needs both.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "register.d" / "run-a" / "rg454.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(GOOD)

    def test_an_edit_adding_a_bad_row_to_an_existing_table_is_refused(self):
        bad = ("| rg454-02 | another thing | operator | low | candidate "
               "|  | candidate; bugs/rg454-02.md |\n")
        code, err = run_hook({"tool_name": "Edit",
                              "tool_input": {"file_path": str(self.path),
                                             "new_string": bad}})
        self.assertEqual(code, 2)
        self.assertIn("rg454-02", err)

    def test_an_edit_adding_a_good_row_to_an_existing_table_passes(self):
        good = ("| rg454-02 | another thing | operator | low | candidate "
                "| 149f/batch-170a59 | candidate; bugs/rg454-02.md |\n")
        code, _ = run_hook({"tool_name": "Edit",
                            "tool_input": {"file_path": str(self.path),
                                           "new_string": good}})
        self.assertEqual(code, 0)


class TestItNeverHalts(unittest.TestCase):
    def test_a_missing_check_script_passes_rather_than_throwing(self):
        """`hooks` and `skills` are separate repositories. One can sit at a
        commit where the other's file does not exist yet, and a guard that
        throws there stops every write to a shard."""
        import os
        done = subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps(write_call(SHARD, GOOD)),
            capture_output=True, text=True,
            env={**os.environ, "ORIGIN_CHECK": "/nowhere/check_origin.py"})
        self.assertEqual(done.returncode, 0)

@NEEDS_PARSER
class TestTheHeredocHasTheSameHole(unittest.TestCase):
    """`cat >> shard.md <<'EOF'` with the row alone is the likeliest real
    shape a gate uses, and a row with no header above it has no column to be
    missing. The header is on disk, exactly as for an Edit."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "register.d" / "run-a" / "rg454.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(GOOD)

    def _run(self, body):
        command = f"cat >> {self.path} <<'EOF'\n{body}EOF\n"
        return run_hook({"tool_name": "Bash",
                         "tool_input": {"command": command}})

    def test_a_heredoc_appending_a_bad_row_alone_is_refused(self):
        bad = ("| rg454-02 | another thing | operator | low | candidate "
               "|  | candidate; bugs/rg454-02.md |\n")
        code, err = self._run(bad)
        self.assertEqual(code, 2)
        self.assertIn("rg454-02", err)

    def test_a_heredoc_appending_a_good_row_alone_passes(self):
        good = ("| rg454-02 | another thing | operator | low | candidate "
                "| 149f/batch-170a59 | candidate; bugs/rg454-02.md |\n")
        self.assertEqual(self._run(good)[0], 0)


if __name__ == "__main__":
    unittest.main()
