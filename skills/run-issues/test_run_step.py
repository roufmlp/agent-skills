#!/usr/bin/env python3
"""Cases for run_step.py — the finale's step wrapper.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 3, deliverable 3 and ruling 19.

    python3 -m unittest test_run_step
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_step as tool


class Kinds(unittest.TestCase):
    """Ruling 19 names five, and a sixth spelling would leave a step out of
    ruling 21's longest-step-per-kind reading without saying so."""

    def test_the_five_kinds_are_the_ones_ruling_19_names(self):
        self.assertEqual(set(tool.KINDS),
                         {"citation", "suite", "build", "board", "cost"})

    def test_an_unknown_kind_is_refused_before_the_command_runs(self):
        """A step stamped under a kind nothing reads is a step nobody can
        find, and the wrapper cannot un-run the command afterwards."""
        ok, why = tool.check_kind("typecheck")
        self.assertFalse(ok)
        self.assertIn("typecheck", why)
        for name in tool.KINDS:
            self.assertIn(name, why)


class Stamping(unittest.TestCase):
    """Start, end and exit code, measured by the wrapper (ruling 19).

    **Never a stamp by the runner** (ticket 36, ruling 3). The runner writing a
    clock is the thing this replaces: it writes one time from another, so the
    two agree by construction and the figure measures nothing.
    """

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.steps = pathlib.Path(self.dir.name) / "steps.jsonl"

    def lines(self):
        return [json.loads(one) for one in
                self.steps.read_text().splitlines() if one.strip()]

    def wrap(self, argv):
        """NOT called `run`: that name is `TestCase.run` itself, and
        overriding it makes every case in the class fail before `setUp`."""
        # `--steps` goes BEFORE the `--`. Everything after it is the command,
        # which is what `argparse.REMAINDER` is for and what the wrapper
        # promises, so a flag appended at the end is passed to the command.
        at = argv.index("--")
        argv = argv[:at] + ["--steps", str(self.steps)] + argv[at:]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = tool.main(argv)
        return code, out.getvalue()

    def test_a_command_that_succeeds_is_stamped_with_exit_zero(self):
        code, _ = self.wrap(["--batch", "batch-test", "--kind", "suite",
                            "--", sys.executable, "-c", "pass"])
        self.assertEqual(code, 0)
        line, = self.lines()
        self.assertEqual(line["batch"], "batch-test")
        self.assertEqual(line["kind"], "suite")
        self.assertEqual(line["exit"], 0)

    def test_a_command_that_fails_keeps_its_own_exit_code(self):
        """`finale.md` step 1 says a refusal from either guard STOPS the
        finale. A wrapper that swallowed the code would turn every refusal in
        the pipeline into a pass, which is a far worse fault than a lost
        measurement."""
        code, _ = self.wrap(["--batch", "batch-test", "--kind", "build",
                            "--", sys.executable, "-c", "raise SystemExit(3)"])
        self.assertEqual(code, 3)
        self.assertEqual(self.lines()[0]["exit"], 3)

    def test_the_span_is_measured_and_not_typed(self):
        code, _ = self.wrap(["--batch", "batch-test", "--kind", "cost", "--",
                            sys.executable, "-c",
                            "import time; time.sleep(0.05)"])
        self.assertEqual(code, 0)
        line, = self.lines()
        self.assertGreaterEqual(line["seconds"], 0.05)
        self.assertLess(line["started"], line["ended"])

    def test_the_command_is_recorded_so_a_step_can_be_identified(self):
        """Five kinds cover more than five commands: the board step runs three
        scripts and the cost step six, so the kind alone cannot say which step
        was the longest one."""
        self.wrap(["--batch", "batch-test", "--kind", "board", "--",
                  sys.executable, "-c", "pass"])
        self.assertIn("-c", self.lines()[0]["command"])

    def test_a_label_names_the_step_where_the_command_is_noise(self):
        self.wrap(["--batch", "batch-test", "--kind", "board",
                  "--label", "draw the rail", "--",
                  sys.executable, "-c", "pass"])
        self.assertEqual(self.lines()[0]["label"], "draw the rail")

    def test_two_steps_append_two_lines(self):
        for kind in ("suite", "build"):
            self.wrap(["--batch", "batch-test", "--kind", kind, "--",
                      sys.executable, "-c", "pass"])
        self.assertEqual([one["kind"] for one in self.lines()],
                         ["suite", "build"])


class ItCannotBeTheReasonAStepFails(unittest.TestCase):
    """The rule every measurement in this pipeline carries, and the one that
    matters most here: this wrapper sits IN FRONT of the finale's real work.

    `run_costs.py` states it -- a measurement that could break a finale would
    be worse than no measurement -- and here the stakes are higher, because a
    wrapper that raised would stop the suite, the build and the board from
    running at all rather than losing a figure.
    """

    def test_an_unwritable_steps_file_still_runs_the_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = tool.main(["--batch", "batch-test", "--kind", "suite",
                              "--steps", "/nonexistent/deep/steps.jsonl",
                              "--", sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(code, 7)
        self.assertIn("NOT stamped", out.getvalue())

    def test_a_command_that_cannot_be_run_is_stamped_and_reported(self):
        """A missing binary is a fact about the step, not an exception. It is
        also the one road where there is no exit code to pass on, so the
        wrapper must choose one and say which it chose."""
        with tempfile.TemporaryDirectory() as where:
            steps = pathlib.Path(where) / "steps.jsonl"
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = tool.main(["--batch", "b", "--kind", "suite",
                                  "--steps", str(steps),
                                  "--", "no-such-binary-anywhere"])
            self.assertNotEqual(code, 0)
            line, = [json.loads(x) for x in
                     steps.read_text().splitlines() if x.strip()]
            self.assertIsNone(line["exit"])
            self.assertTrue(line["failed_to_start"])

    def test_no_shell_is_used(self):
        """The wrapper takes an argument LIST and never a string. A shell here
        would make every finale command a place where a semicolon in a file
        name runs something else, for no gain at all: the finale's commands are
        fixed and known."""
        with tempfile.TemporaryDirectory() as where:
            steps = pathlib.Path(where) / "steps.jsonl"
            marker = pathlib.Path(where) / "ran"
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                tool.main(["--batch", "b", "--kind", "suite",
                           "--steps", str(steps), "--",
                           "true", ";", "touch", str(marker)])
            self.assertFalse(marker.exists())


class WhereTheStepsFileLives(unittest.TestCase):
    """Ticket 38 ruling 10: run state lives in `.scratch/<feature>/runs/<batch
    id>/`. The steps file sits beside the ledger, which is where `journal_for`
    already puts the journal -- one layout, one owner."""

    def test_it_sits_beside_the_ledger(self):
        self.assertEqual(
            tool.steps_beside("/x/.scratch/f/runs/batch-1/run.md"),
            "/x/.scratch/f/runs/batch-1/steps.jsonl")

    def test_a_hunt_gets_one_too(self):
        self.assertEqual(
            tool.steps_beside("/x/.scratch/f/rounds/r1/round-brief.md"),
            "/x/.scratch/f/rounds/r1/steps.jsonl")


class Reading(unittest.TestCase):
    """Ruling 21's half of this file: the longest STAMPED step per kind. The
    agent half comes from the transcript, and `run_measures.py` joins them."""

    def test_the_longest_step_of_each_kind_is_found(self):
        lines = [
            {"kind": "suite", "seconds": 30.0, "label": "short suite"},
            {"kind": "suite", "seconds": 90.0, "label": "long suite"},
            {"kind": "build", "seconds": 60.0, "label": "cold build"},
        ]
        found = tool.longest_per_kind(lines)
        self.assertEqual(found["suite"]["label"], "long suite")
        self.assertEqual(found["build"]["seconds"], 60.0)

    def test_a_kind_nothing_stamped_is_absent_rather_than_zero(self):
        """A `0` would say the citation pass took no time; absence says
        nothing stamped it. Ticket 37 sitting 2's rule, in the human's words: a run
        with no strikes is a fact, and a run whose strikes were never read is
        not."""
        found = tool.longest_per_kind([{"kind": "suite", "seconds": 1.0}])
        self.assertNotIn("citation", found)

    def test_a_line_with_no_duration_is_skipped_rather_than_read_as_zero(self):
        found = tool.longest_per_kind([{"kind": "suite", "seconds": None},
                                       {"kind": "suite", "seconds": 5.0}])
        self.assertEqual(found["suite"]["seconds"], 5.0)


if __name__ == "__main__":
    unittest.main()
