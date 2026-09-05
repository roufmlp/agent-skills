#!/usr/bin/env python3
"""The four cost scripts take a batch id and find the session themselves.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 3, ruling 12.

Before this each script had its own way in and none of them was a batch id:
`run_costs.py` took `--run` and looked for that name inside the PROJECT
DIRECTORY name, `harness_cost.py` took `--run` as a fragment of a worktree name
against one hard-coded project prefix, `orchestrator_cost.py` took `--days`
and measured whatever week it found, and `run_timings.py` took a bare path and
had no argparse at all.

The fault is written twice in `.scratch/workflow-audit/run-costs.md`: the
2026-09-02 and 2026-09-05 rows each say "the worktree was reused and its name
does not match the branch, so --transcript had to be passed by hand". A batch
id read off a ledger does not care what a worktree is called.

    python3 -m unittest test_cost_scripts_batch
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

import run_session
import run_timings
import harness_cost
import orchestrator_cost
import run_costs


LEDGER = """# Run ledger — 533, 546 (run `{batch}`)

Owner: none — MERGED to local main 2026-09-05 at `2c12b53a`
Model map at launch: `implementer=opus verify=opus`
Worktree: `{tree}`
Started 2026-09-04. State: **merged**
"""


def assistant(stamp, model, effort, msg_id, batch, **usage):
    return json.dumps({
        "type": "assistant", "timestamp": stamp, "effort": effort,
        "note": f"working on run {batch}",
        "message": {"model": model, "id": msg_id, "usage": {
            "input_tokens": usage.get("input", 0),
            "cache_creation_input_tokens": usage.get("cache_creation", 0),
            "cache_read_input_tokens": usage.get("cache_read", 0),
            "output_tokens": usage.get("output", 0),
        }},
    }) + "\n"


def agent_call(stamp, use_id, description):
    return json.dumps({
        "type": "assistant", "timestamp": stamp,
        "message": {"model": "claude-opus-5", "id": f"call-{use_id}", "content": [
            {"type": "tool_use", "id": use_id, "name": "Agent",
             "input": {"description": description}}]},
    }) + "\n"


def agent_result(stamp, use_id):
    return json.dumps({
        "type": "user", "timestamp": stamp,
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": use_id, "content": "done"}]},
    }) + "\n"


class Fixture:
    """A git repo holding one merged ledger, and the transcripts to match."""

    def __init__(self, batch="batch-b5e96d", spawns=None):
        self.batch = batch
        self.tree = pathlib.Path(tempfile.mkdtemp())
        run = lambda *a: subprocess.run(["git", "-C", str(self.tree), *a],
                                        capture_output=True, check=True)
        run("init", "-q")
        run("config", "user.email", "t@example.com")
        run("config", "user.name", "t")
        ledger = self.tree / ".scratch" / "pilot" / "runs" / batch / "run.md"
        ledger.parent.mkdir(parents=True)
        ledger.write_text(LEDGER.format(batch=batch, tree=self.tree),
                          encoding="utf-8")
        self.ledger = ledger

        self.projects = pathlib.Path(tempfile.mkdtemp())
        slug = self.projects / run_session.slug_for(str(self.tree))
        slug.mkdir(parents=True)
        self.main = slug / "sess.jsonl"
        # An `Agent` call and its result, so the main transcript reads the way
        # a real run's does: `run_timings.py` measures a step as the wall clock
        # from a `tool_use` block to its `tool_result`.
        self.main.write_text(
            assistant("2026-09-04T09:00:00Z", "claude-opus-5", "high",
                      "m1", batch, output=100)
            + agent_call("2026-09-04T10:00:00Z", "t1", "Implement issue 545")
            + agent_result("2026-09-04T10:30:00Z", "t1")
            + agent_call("2026-09-04T11:00:00Z", "t2", "Verify gate for issue 545")
            + agent_result("2026-09-04T11:10:00Z", "t2"), encoding="utf-8")
        subs = slug / "sess" / "subagents"
        subs.mkdir(parents=True)
        for name, agent_type, description, model, stamps in (spawns or ()):
            (subs / f"{name}.jsonl").write_text("".join(
                assistant(s, model, "high", f"{name}-{i}", batch,
                          input=2, cache_creation=100, cache_read=4000,
                          output=50)
                for i, s in enumerate(stamps)), encoding="utf-8")
            (subs / f"{name}.meta.json").write_text(json.dumps(
                {"agentType": agent_type, "description": description}),
                encoding="utf-8")

        # A foreign session in the same slug: the trap that cost run
        # `batch-88624c` its 2026-08-31 row.
        (slug / "foreign.jsonl").write_text(
            assistant("2026-09-06T09:00:00Z", "claude-sonnet-5", "low",
                      "f1", "some other work"), encoding="utf-8")


TWO_SPAWNS = (
    ("agent-a", "run-issues-implementer", "Implement issue 545",
     "claude-opus-5", ["2026-09-04T10:00:00Z", "2026-09-04T10:30:00Z"]),
    ("agent-b", "run-issues-verify-gate", "Verify gate for issue 545",
     "claude-fable-5", ["2026-09-04T11:00:00Z", "2026-09-04T11:10:00Z"]),
)


class Batched(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture(spawns=TWO_SPAWNS)
        self.original = run_session.PROJECTS
        run_session.PROJECTS = str(self.fx.projects)

    def tearDown(self):
        run_session.PROJECTS = self.original


class RunTimings(Batched):
    """`run_timings.py` grows an argparse and a `--batch`, keeping its path."""

    def test_batch_finds_the_transcript_without_being_told_the_path(self):
        code = run_timings.main(["--batch", self.fx.batch,
                                 "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)

    def test_a_bare_path_still_works_because_the_finale_passes_one(self):
        self.assertEqual(run_timings.main([str(self.fx.main)]), 0)

    def test_an_unknown_batch_refuses_and_names_it(self):
        with self.assertRaises(SystemExit) as caught:
            run_timings.main(["--batch", "batch-nope",
                              "--repo", str(self.fx.tree)])
        self.assertIn("batch-nope", str(caught.exception))


class OrchestratorCost(Batched):
    """`--batch` measures ONE run. `--days` keeps the weekly table it had.

    The share it prints is main-thread tokens over main plus fleet. That is a
    RATIO ACROSS MODELS the moment a run is mixed, so on a mixed run it is
    printed per model and never merged.
    """

    def read(self, argv):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = orchestrator_cost.main(argv)
        return code, out.getvalue()

    def test_batch_measures_that_run_and_names_every_model(self):
        code, text = self.read(["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("claude-opus-5", text)
        self.assertIn("claude-fable-5", text)

    def test_a_mixed_run_gets_no_single_share_and_is_told_why(self):
        code, text = self.read(["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree)])
        self.assertIn("mixed models", text)
        self.assertIn("/usage", text)

    def test_batch_prints_the_per_role_table_and_the_per_spawn_rows(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree)])
        self.assertIn("implementer", text)
        self.assertIn("verify", text)
        self.assertIn("Implement issue 545", text)

    def test_an_unknown_batch_says_so_and_exits_zero(self):
        """A measurement never refuses a finale. It says what it could not
        read and returns 0, the rule `run_costs.py` has carried since
        2026-08-30."""
        code, text = self.read(["--batch", "batch-nope",
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("batch-nope", text)

    def test_no_currency_symbol_reaches_the_output(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree)])
        for mark in ("$", "USD", "£", "€"):
            self.assertNotIn(mark, text)


class WeeklyTableCarriesTheModel(unittest.TestCase):
    """`--days` compares runs. The human asked on 2026-09-06 to compare runs "with
    different models as well", so the column that says which model has to be in
    the row they compare along."""

    def setUp(self):
        import datetime as dt
        self.projects = pathlib.Path(tempfile.mkdtemp())
        slug = self.projects / "-a-run"
        subs = slug / "sess" / "subagents"
        subs.mkdir(parents=True)
        today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (slug / "sess.jsonl").write_text(
            assistant(today, "claude-opus-5", "high", "m1", "x", output=10),
            encoding="utf-8")
        # `MIN_SUBAGENTS` is 25; a hardening pass runs 12 to 14 and a run has
        # not gone below 35, so the floor is what keeps foreign fleets out.
        for n in range(orchestrator_cost.MIN_SUBAGENTS + 1):
            model = "claude-fable-5" if n % 2 else "claude-opus-5"
            # `count_issues` reads the FIRST LINE only and matches
            # `"content":"Implement issue N`, with no space after the colon.
            # It matches loosely on purpose: the prompt format is not stable,
            # and a matcher written against one shape silently returned zero on
            # the other when run `cab74e` and run `fd4fa2` opened their gates
            # differently.
            (subs / f"agent-{n}.jsonl").write_text(
                json.dumps({"type": "user", "message": {
                    "content": f"Implement issue {300 + n} in the pilot"}},
                    separators=(",", ":")) + "\n"
                + assistant(today, model, "high", f"s{n}", "x", output=1),
                encoding="utf-8")
            (subs / f"agent-{n}.meta.json").write_text(json.dumps({
                "agentType": "run-issues-implementer",
                "description": f"Implement issue {300 + n}"}), encoding="utf-8")
        self.original = orchestrator_cost.PROJECTS
        orchestrator_cost.PROJECTS = self.projects

    def tearDown(self):
        orchestrator_cost.PROJECTS = self.original

    def test_the_weekly_row_names_the_models_that_ran(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            orchestrator_cost.main(["--days", "7"])
        text = out.getvalue()
        self.assertIn("models", text)
        self.assertIn("fable", text)
        self.assertIn("opus", text)


class HarnessCost(Batched):
    """`--batch` replaces a worktree-name fragment matched against a hard-coded
    one project's prefix. That prefix meant this script could only ever measure
    one repository, and the fragment meant it could not find run `batch-b5e96d`
    at all -- that run's worktree is called `run-issues-414a-99f-286335`."""

    def read(self, argv):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = harness_cost.main(argv)
        return code, out.getvalue()

    def test_batch_finds_the_run_whatever_the_worktree_is_called(self):
        code, text = self.read(["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("PROMPTS", text)
        self.assertIn("POLLING", text)
        self.assertIn("DENIALS", text)

    def test_the_batch_report_names_the_batch(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree)])
        self.assertIn(self.fx.batch, text)

    def test_an_unknown_batch_says_so_and_exits_zero(self):
        code, text = self.read(["--batch", "batch-nope",
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("batch-nope", text)


class RunCosts(Batched):
    """The finale's script. `--batch` replaces `--run`, and the token cells
    carry their model so the number cannot be read without it."""

    def read(self, argv):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_costs.main(argv)
        return code, out.getvalue()

    def test_batch_takes_the_reading_without_a_run_name_or_a_path(self):
        code, text = self.read(["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree), "--no-append"])
        self.assertEqual(code, 0)
        self.assertIn(self.fx.batch, text)

    def test_the_weighted_cell_carries_its_model(self):
        """A bare `96.6M` on a mixed run is opus and fable added together, and
        `run-costs.md` holds two such cells already. The model travels with the
        number so nobody can read one without the other."""
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        row = [line for line in text.splitlines()
               if line.startswith("|") and self.fx.batch in line][-1]
        self.assertIn("opus", row)
        self.assertIn("fable", row)

    def test_the_row_is_still_ten_cells_so_the_old_table_still_reads(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        row = [line for line in text.splitlines()
               if line.startswith("|") and self.fx.batch in line][-1]
        self.assertEqual(len(row.strip().strip("|").split("|")), 10)

    def test_the_orchestrator_reading_is_this_batch_not_the_week_window(self):
        """The window states what OTHER runs cost, at launch. Read here it made
        the appended row borrow another run's issues, agents and share."""
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        self.assertNotIn("runs of the last", text)
        self.assertIn("orchestrator against fleet, PER MODEL", text)

    def test_the_issue_count_comes_from_this_batch_own_spawns(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        row = [line for line in text.splitlines()
               if line.startswith("|") and self.fx.batch in line][-1]
        self.assertEqual(row.strip().strip("|").split("|")[2].strip(), "1")

    def test_the_per_role_and_per_spawn_tables_are_printed(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        self.assertIn("per role and per model", text)
        self.assertIn("One row per subagent", text)
        self.assertIn("Implement issue 545", text)

    def test_nothing_is_appended_when_the_batch_cannot_be_found(self):
        code, text = self.read(["--batch", "batch-nope",
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("NO ROW WAS APPENDED", text)

    def test_no_currency_symbol_reaches_the_output(self):
        _, text = self.read(["--batch", self.fx.batch,
                             "--repo", str(self.fx.tree), "--no-append"])
        for mark in ("$", "USD", "£", "€"):
            self.assertNotIn(mark, text)


HUNT_BRIEF = """# Round brief — inquiry-core (hunt `{batch}`)

Owner: session-7 (orchestrator)
Worktree: `{tree}`
Branch: `hunt/{batch}`
Model map at launch: `finder=opus claim-gate=opus`
"""


class HuntFixture(Fixture):
    """A hunt's ledger is `round-brief.md`, not `runs/<id>/run.md`.

    Ticket 38 ruling 22 made a hunt a run with a batch id; ticket 39 ruling 8
    gave it the same header, and sitting 1 put those lines in the round brief
    rather than minting a second state file. Ruling 12 then asks these scripts
    for one set serving both, so the hunt road needs proving on its own -- it
    shares no directory shape with the run road at all.
    """

    def __init__(self, batch="hunt-3f21aa", spawns=None):
        super().__init__(batch=batch, spawns=spawns)
        (self.tree / ".scratch" / "pilot" / "runs" / batch / "run.md").unlink()
        brief = self.tree / ".scratch" / "pilot" / "round-brief.md"
        brief.write_text(HUNT_BRIEF.format(batch=batch, tree=self.tree),
                         encoding="utf-8")
        self.ledger = brief


HUNT_SPAWNS = (
    ("agent-f", "parallel-hunt-finder", "Finder sweep, inquiry-core",
     "claude-opus-5", ["2026-09-04T10:00:00Z", "2026-09-04T10:40:00Z"]),
    ("agent-g", "parallel-hunt-claim-gate", "Claim gate for bug ic-01",
     "claude-opus-5", ["2026-09-04T11:00:00Z", "2026-09-04T11:05:00Z"]),
)


class TheHuntRoad(unittest.TestCase):
    """One set of scripts for a run and a hunt (ruling 12)."""

    def setUp(self):
        self.fx = HuntFixture(spawns=HUNT_SPAWNS)
        self.original = run_session.PROJECTS
        run_session.PROJECTS = str(self.fx.projects)

    def tearDown(self):
        run_session.PROJECTS = self.original

    def read(self, module, argv):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(argv)
        return code, out.getvalue()

    def test_the_hunt_ledger_is_found_by_its_hunt_id(self):
        found = run_session.ledger_for_batch(
            self.fx.batch, worktrees=[str(self.fx.tree)])
        self.assertIsNotNone(found)
        self.assertEqual(found.kind, "hunt")

    def test_orchestrator_cost_measures_a_hunt(self):
        code, text = self.read(orchestrator_cost,
                               ["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn("finder", text)
        self.assertIn("claim-gate", text)

    def test_run_costs_measures_a_hunt_without_appending(self):
        code, text = self.read(run_costs,
                               ["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree), "--no-append"])
        self.assertEqual(code, 0)
        self.assertIn("Finder sweep", text)

    def test_harness_cost_measures_a_hunt(self):
        code, text = self.read(harness_cost,
                               ["--batch", self.fx.batch,
                                "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
        self.assertIn(self.fx.batch, text)

    def test_run_timings_measures_a_hunt(self):
        code = run_timings.main(["--batch", self.fx.batch,
                                 "--repo", str(self.fx.tree)])
        self.assertEqual(code, 0)
