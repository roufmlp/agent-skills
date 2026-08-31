#!/usr/bin/env python3
"""Cases for run_costs.py's transcript selection.

The anchor is run `batch-88624c`, 2026-08-31. The finale ran `run_costs.py`
from the main checkout rather than the run's worktree. The old rule was
"the newest `.jsonl` under this working directory's project slug", and that
directory holds 64 transcripts from months of unrelated sessions. It picked
one, reported a wall clock of 1.01 h for an 8.4 h run with a longest step of
"Gather week git activity" that the run never ran, and appended the figures to
`.scratch/workflow-audit/run-costs.md` as though they were measured.

Every case below is that fault, held from a different side.

    python3 -m unittest test_run_costs
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

import run_costs as tool


def git_repo(branch: str) -> pathlib.Path:
    """A throwaway repository with one commit on `branch`."""
    root = pathlib.Path(tempfile.mkdtemp())
    run = lambda *args: subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True)
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (root / "a.txt").write_text("a")
    run("add", "a.txt")
    run("commit", "-qm", "first")
    run("checkout", "-q", "-b", branch)
    return root


def transcript_file(directory: pathlib.Path, name: str, text: str) -> pathlib.Path:
    path = directory / f"{name}.jsonl"
    path.write_text(json.dumps({"timestamp": "2026-08-31T05:00:00Z", "text": text}) + "\n")
    return path


class RunNameFromTheBranch(unittest.TestCase):
    def test_a_run_branch_gives_the_run(self):
        root = git_repo("claude/run-issues-batch-88624c")
        self.assertEqual(tool.run_name(root), ("batch-88624c", ""))

    def test_the_main_checkout_refuses(self):
        """Where the fault happened. `main` is not a run and must not guess one."""
        root = git_repo("main")
        found, why = tool.run_name(root)
        self.assertIsNone(found)
        self.assertIn("not a run branch", why)

    def test_a_directory_outside_git_refuses(self):
        found, why = tool.run_name(pathlib.Path(tempfile.mkdtemp()))
        self.assertIsNone(found)
        self.assertTrue(why)


class TranscriptSelection(unittest.TestCase):
    def setUp(self):
        self.projects = pathlib.Path(tempfile.mkdtemp())
        self.original, tool.PROJECTS = tool.PROJECTS, self.projects

    def tearDown(self):
        tool.PROJECTS = self.original

    def directory(self, name: str) -> pathlib.Path:
        made = self.projects / name
        made.mkdir()
        return made

    def test_it_reads_the_transcript_that_names_the_run(self):
        folder = self.directory("-repo--claude-worktrees-run-issues-batch-88624c")
        wanted = transcript_file(folder, "session", "Coherence finale for run batch-88624c")
        found, why = tool.transcript("batch-88624c")
        self.assertEqual(found, wanted)
        self.assertEqual(why, "")

    def test_a_foreign_session_in_the_same_directory_is_REFUSED(self):
        """The check the old rule had no way to make.

        A newer session sitting in the run's own directory still never names
        the run. This is the last line of defence and it holds on its own.
        """
        folder = self.directory("-repo--claude-worktrees-run-issues-batch-88624c")
        transcript_file(folder, "session", "Gather week git activity")
        found, why = tool.transcript("batch-88624c")
        self.assertIsNone(found)
        self.assertIn("never names run", why)

    def test_no_directory_for_the_run_is_refused(self):
        found, why = tool.transcript("batch-88624c")
        self.assertIsNone(found)
        self.assertIn("no transcript directory", why)

    def test_two_matching_directories_are_refused_not_guessed(self):
        for suffix in ("", "-resume"):
            folder = self.directory(f"-repo--claude-worktrees-run-issues-batch-88624c{suffix}")
            transcript_file(folder, "s", "run batch-88624c")
        found, why = tool.transcript("batch-88624c")
        self.assertIsNone(found)
        self.assertIn("more than one", why)

    def test_the_newest_last_turn_wins_among_this_run_s_own_sessions(self):
        """A resumed run has two transcripts and both name it. Take the later."""
        folder = self.directory("-repo--claude-worktrees-run-issues-batch-88624c")
        early = folder / "early.jsonl"
        early.write_text(json.dumps(
            {"timestamp": "2026-08-31T01:00:00Z", "text": "run batch-88624c"}) + "\n")
        late = folder / "late.jsonl"
        late.write_text(json.dumps(
            {"timestamp": "2026-08-31T05:00:00Z", "text": "run batch-88624c"}) + "\n")
        self.assertEqual(tool.transcript("batch-88624c")[0], late)


class NamesTheRun(unittest.TestCase):
    def test_a_missing_file_is_not_a_match(self):
        self.assertFalse(tool.names_the_run(pathlib.Path("/nonexistent/x.jsonl"), "batch-1"))


class NoRowFromAnUnidentifiedTranscript(unittest.TestCase):
    """The row is what outlived the mistake, so the refusal has to reach it."""

    def test_a_refusal_prints_that_no_row_was_appended(self):
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = tool.main([
                "--run", "batch-88624c",
                "--transcript", "/nonexistent/foreign.jsonl",
                "--issues", "8",
            ])
        printed = buffer.getvalue()
        self.assertEqual(code, 0, "a measurement never halts a run")
        self.assertIn("NO ROW WAS APPENDED", printed)
        self.assertNotIn("| 2026-", printed)


if __name__ == "__main__":
    unittest.main()
