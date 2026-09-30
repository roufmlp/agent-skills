#!/usr/bin/env python3
"""Tests for wakeup_cron.py and the refusal it gave check_finale_stage.py.

Run: python3 test_wakeup_cron.py
"""

import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import check_finale_stage
import wakeup_cron as cron

HERE = pathlib.Path(__file__).resolve().parent

HEADER = """# Run ledger — `batch-abc123`

Owner: session pid 33488 (desktop app), worktree run-issues-batch-abc123
Worktree: /Users/x/code/p/.claude/worktrees/run-issues-batch-abc123
Branch: `claude/run-issues-batch-abc123`

State: 255 implement
| # | status |
"""


def ledger_at(text, age_minutes=0.0):
    """A ledger at `.../runs/batch-abc123/run.md`, last written `age_minutes` ago."""
    folder = pathlib.Path(tempfile.mkdtemp()) / "runs" / "batch-abc123"
    folder.mkdir(parents=True)
    path = folder / "run.md"
    path.write_text(text, encoding="utf-8")
    stamp = time.time() - age_minutes * 60
    os.utime(path, (stamp, stamp))
    return path


def call(*argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, env or {}, clear=False), \
            redirect_stdout(out), redirect_stderr(err):
        code = cron.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TheRuledCadence(unittest.TestCase):
    def test_the_cron_fires_every_thirty_minutes_off_the_hour(self):
        self.assertEqual(cron.CRON, "7,37 * * * *")

    def test_a_run_is_idle_after_twenty_minutes(self):
        self.assertEqual(cron.IDLE_MINUTES, 20)

    def test_args_prints_what_cron_create_takes(self):
        path = ledger_at(HEADER)
        code, out, _ = call("args", "--ledger", str(path))
        self.assertEqual(code, 0)
        made = json.loads(out)
        self.assertEqual(made["cron"], "7,37 * * * *")
        self.assertIs(made["recurring"], True)
        self.assertIn("batch-abc123", made["prompt"])
        self.assertIn(f"check --ledger {path}", made["prompt"])

    def test_the_prompt_names_the_ledger_by_absolute_path(self):
        """A cron fires wherever the session's directory happens to be."""
        path = ledger_at(HEADER)
        before = os.getcwd()
        try:
            os.chdir(path.parent)
            made = cron.cron_args("run.md")
        finally:
            os.chdir(before)
        named = made["prompt"].split("--ledger ", 1)[1].split("`", 1)[0]
        self.assertTrue(os.path.isabs(named), named)
        self.assertTrue(os.path.samefile(named, path), named)

    def test_args_refuses_a_ledger_outside_a_batch_directory(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        (folder / "run.md").write_text(HEADER)
        code, _, err = call("args", "--ledger", str(folder / "run.md"))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)


class TheFiringVerdict(unittest.TestCase):
    def test_a_ledger_written_inside_the_window_is_busy(self):
        line = cron.verdict(str(ledger_at(HEADER, age_minutes=5)))
        self.assertTrue(line.startswith("BUSY"), line)
        self.assertIn("Do nothing", line)

    def test_twenty_minutes_exactly_is_still_busy(self):
        path = ledger_at(HEADER)
        now = os.path.getmtime(path) + 20 * 60
        self.assertTrue(cron.verdict(str(path), now=now).startswith("BUSY"))

    def test_a_ledger_still_for_more_than_twenty_minutes_is_idle(self):
        line = cron.verdict(str(ledger_at(HEADER, age_minutes=21)))
        self.assertTrue(line.startswith("IDLE"), line)
        self.assertIn("/run-issues resume", line)

    def test_idle_hands_the_agent_test_to_the_session(self):
        """No file holds the session's agents, so the line must name that test."""
        line = cron.verdict(str(ledger_at(HEADER, age_minutes=45)))
        self.assertIn("background agent of this run is still running", line)

    def test_awaiting_merge_stops_the_cron_however_old(self):
        text = HEADER.replace("State: 255 implement", "State: awaiting-merge")
        for age in (1, 90):
            line = cron.verdict(str(ledger_at(text, age_minutes=age)))
            self.assertTrue(line.startswith("STOPPED"), line)
            self.assertIn("CronDelete", line)

    def test_the_decorated_state_the_ruling_grep_missed_still_stops_it(self):
        """The ruling's own prompt grepped `^State: awaiting-merge`."""
        text = HEADER.replace(
            "State: 255 implement",
            "Started 2026-08-20 03:03. State: **`awaiting-merge`, reached 15:45.**")
        line = cron.verdict(str(ledger_at(text, age_minutes=1)))
        self.assertTrue(line.startswith("STOPPED"), line)

    def test_a_halted_owner_line_stops_the_cron(self):
        text = HEADER.replace(
            "Owner: session pid 33488 (desktop app), worktree run-issues-batch-abc123",
            "Owner: none — HALTED 2026-09-29 04:10")
        line = cron.verdict(str(ledger_at(text, age_minutes=40)))
        self.assertTrue(line.startswith("STOPPED"), line)

    def test_a_stop_names_the_recorded_job_and_the_clear_step(self):
        text = cron.with_line(HEADER.replace("State: 255 implement",
                                             "State: awaiting-merge"),
                              "Wakeup cron: d1ab29e9 pid 33488")
        line = cron.verdict(str(ledger_at(text)))
        self.assertIn("CronDelete d1ab29e9", line)
        self.assertIn("wakeup_cron.py clear", line)

    def test_a_ledger_that_is_gone_stops_the_cron(self):
        path = ledger_at(HEADER)
        path.unlink()
        self.assertTrue(cron.verdict(str(path)).startswith("STOPPED"))

    def test_check_always_exits_zero_with_one_line(self):
        code, out, _ = call("check", "--ledger", str(ledger_at(HEADER, 30)))
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 1)


class TheLedgerLine(unittest.TestCase):
    def test_record_writes_the_job_and_this_process_under_the_owner_line(self):
        path = ledger_at(HEADER)
        code, out, _ = call("record", "--ledger", str(path), "--id", "d1ab29e9",
                            env={"CLAUDE_PID": "48532"})
        self.assertEqual(code, 0)
        lines = path.read_text().splitlines()
        owner = next(i for i, l in enumerate(lines) if l.startswith("Owner:"))
        self.assertEqual(lines[owner + 1], "Wakeup cron: d1ab29e9 pid 48532")
        self.assertEqual(cron.read_wakeup(path.read_text()),
                         {"raw": "Wakeup cron: d1ab29e9 pid 48532",
                          "job": "d1ab29e9", "pid": 48532})

    def test_record_replaces_an_earlier_line_and_never_adds_a_second(self):
        path = ledger_at(cron.with_line(HEADER, "Wakeup cron: aaaa1111 pid 1"))
        call("record", "--ledger", str(path), "--id", "bbbb2222",
             env={"CLAUDE_PID": "2"})
        text = path.read_text()
        self.assertEqual(text.count("Wakeup cron:"), 1)
        self.assertEqual(cron.read_wakeup(text)["job"], "bbbb2222")

    def test_record_refuses_without_the_process_id(self):
        path = ledger_at(HEADER)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PID", None)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cron.main(["record", "--ledger", str(path), "--id", "d1ab29e9"])
        self.assertEqual(code, 1)
        self.assertIn("CLAUDE_PID", err.getvalue())
        self.assertNotIn("Wakeup cron:", path.read_text())

    def test_record_refuses_an_id_that_is_not_one(self):
        path = ledger_at(HEADER)
        code, _, err = call("record", "--ledger", str(path), "--id", "d1 ab",
                            env={"CLAUDE_PID": "2"})
        self.assertEqual(code, 1)
        self.assertNotIn("Wakeup cron:", path.read_text())

    def test_clear_leaves_a_line_that_names_no_job(self):
        path = ledger_at(cron.with_line(HEADER, "Wakeup cron: d1ab29e9 pid 2"))
        code, out, _ = call("clear", "--ledger", str(path))
        self.assertEqual(code, 0)
        found = cron.read_wakeup(path.read_text())
        self.assertIsNotNone(found)
        self.assertIsNone(found["job"])
        self.assertIn("none — deleted", found["raw"])

    def test_a_line_outside_the_header_is_not_read(self):
        text = HEADER + "x\n" * cron.HEAD_LINES + "Wakeup cron: d1ab29e9 pid 2\n"
        self.assertIsNone(cron.read_wakeup(text))

    def test_a_line_in_another_shape_names_no_job(self):
        for value in ("TODO", "d1ab29e9", "none pid 4", "d1ab29e9 session 7"):
            found = cron.read_wakeup(f"Wakeup cron: {value}\n")
            self.assertIsNone(found["job"], value)

    def test_the_header_width_matches_the_ledger_selector(self):
        import find_live_ledger
        self.assertEqual(cron.HEAD_LINES, find_live_ledger.HEAD_LINES)


class TheFinaleRefusesALiveCron(unittest.TestCase):
    def run_guard(self, text, target):
        path = ledger_at(text)
        return subprocess.run(
            [sys.executable, str(HERE / "check_finale_stage.py"),
             "--ledger", str(path), "--to", target],
            capture_output=True, text=True)

    def test_awaiting_merge_is_refused_while_the_line_names_a_job(self):
        text = cron.with_line(HEADER.replace("State: 255 implement",
                                             "State: finale-board"),
                              "Wakeup cron: d1ab29e9 pid 2")
        done = self.run_guard(text, "awaiting-merge")
        self.assertEqual(done.returncode, 1)
        self.assertIn("cron-still-live", done.stderr)
        self.assertIn("CronDelete d1ab29e9", done.stderr)

    def test_awaiting_merge_passes_once_the_line_is_cleared(self):
        text = cron.with_line(HEADER.replace("State: 255 implement",
                                             "State: finale-board"),
                              "Wakeup cron: none — deleted 2026-09-29 10:00")
        self.assertEqual(self.run_guard(text, "awaiting-merge").returncode, 0)

    def test_a_ledger_from_before_the_ruling_is_not_refused_for_it(self):
        text = HEADER.replace("State: 255 implement", "State: finale-board")
        self.assertEqual(self.run_guard(text, "awaiting-merge").returncode, 0)

    def test_an_earlier_stage_is_not_refused_for_a_live_cron(self):
        """The cron must live through the finale; only its last write ends it."""
        text = cron.with_line(HEADER.replace("State: 255 implement",
                                             "State: finale-promotion"),
                              "Wakeup cron: d1ab29e9 pid 2")
        self.assertEqual(self.run_guard(text, "finale-board").returncode, 0)

    def test_the_order_refusal_still_comes_first(self):
        self.assertIsNone(check_finale_stage.cron_still_live(
            "Wakeup cron: d1ab29e9 pid 2\n", "finale-board"))
        text = cron.with_line(HEADER.replace("State: 255 implement",
                                             "State: finale-promotion"),
                              "Wakeup cron: d1ab29e9 pid 2")
        done = self.run_guard(text, "awaiting-merge")
        self.assertIn("skips-a-step", done.stderr)


if __name__ == "__main__":
    unittest.main()
