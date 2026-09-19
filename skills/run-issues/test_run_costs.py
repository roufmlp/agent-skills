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
import run_records


def git_repo(branch: str) -> pathlib.Path:
    """A throwaway repository with one commit on `branch`, and no other branch.

    `git init -b` names the branch before the first commit, so the fixture holds
    whatever `init.defaultBranch` this machine sets. Checking out a new branch
    after the commit did not: on a machine that defaults to `main`, asking for
    `main` asked git to create a branch it had already made, and git exited 128.
    """
    root = pathlib.Path(tempfile.mkdtemp())
    run = lambda *args: subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True)
    run("init", "-q", "-b", branch)
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (root / "a.txt").write_text("a")
    run("add", "a.txt")
    run("commit", "-qm", "first")
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


class ItWritesARecordNotAMarkdownRow(unittest.TestCase):
    """Ticket 37, sitting 2. `run_costs.py` stops appending a markdown row and
    appends one JSON line to `runs.jsonl`, then regenerates the view.

    The fault this closes is the shape. The old `append_row` wrote a line of
    pipes into a file that also carries prose, so a correction paragraph typed
    on 2026-08-31 sits BETWEEN two data rows and the table cannot be parsed at
    all. Every quality fact lived in the free-text Note cell, so no figure could
    be read down a column."""

    def test_the_record_carries_the_batch_and_the_kind(self):
        record = tool.build_record(batch="batch-abc123", kind="run")
        self.assertEqual("batch-abc123", record["batch"])
        self.assertEqual("run", record["kind"])

    def test_the_four_quality_counts_are_present_and_null(self):
        """Branch A, ruled by the human 2026-09-06. Sitting 3 fills them, after it
        repairs `run_quality.issue_quality`, which returns 12 rows for the
        six-issue run `batch-170a59`."""
        quality = tool.build_record(batch="b", kind="run")["quality"]
        self.assertTrue(all(value is None for value in quality.values()))
        self.assertIn("strikes", quality)
        self.assertIn("escalations", quality)

    def test_the_version_is_measured_not_typed(self):
        """Ruling 10. `finale.md` asks an agent to type `--version
        <cc-version>` and on 2026-08-30 an agent typed `claude-opus-5`, which
        is in the live table today."""
        record = tool.build_record(batch="b", kind="run",
                                   version_reader=lambda: "2.1.261 (Claude Code)")
        self.assertEqual("2.1.261 (Claude Code)", record["version"])

    def test_a_typed_version_still_wins_for_a_hand_reading(self):
        record = tool.build_record(batch="b", kind="run", version="2.1.251",
                                   version_reader=lambda: "2.1.261")
        self.assertEqual("2.1.251", record["version"])

    def test_an_unreadable_version_is_not_stated_rather_than_a_guess(self):
        record = tool.build_record(batch="b", kind="run",
                                   version_reader=lambda: "")
        self.assertEqual("not stated", record["version"])

    def test_the_fingerprint_is_copied_off_the_ledger_not_re_measured(self):
        """Ruling 23. The finale runs days after the launch and in another
        tree, so measuring HEAD again here would record what the pipeline is
        NOW, not what ran. That is the whole value of the field."""
        ledger = ("Pipeline fingerprint at launch:\n"
                  "  - skills: `aaaaaaaaaaaa` dirty\n"
                  "  - agents: `bbbbbbbbbbbb`\n")
        record = tool.build_record(batch="b", kind="run", ledger_text=ledger)
        self.assertEqual("aaaaaaaaaaaa", record["fingerprint"]["skills"]["head"])
        self.assertTrue(record["fingerprint"]["skills"]["dirty"])

    def test_a_ledger_with_no_fingerprint_leaves_the_field_empty(self):
        """Every run before this sitting."""
        record = tool.build_record(batch="b", kind="run", ledger_text="State: merged")
        self.assertEqual({}, record["fingerprint"])

    def test_the_two_model_cells_come_off_the_ledger_map(self):
        """Ruling 9."""
        ledger = ("Session model at launch: claude-opus-5\n"
                  "Session effort at launch: high\n"
                  # The ledger writes TIER names, not full model ids --
                  # `implementer=opus`, as `batch-170a59`'s ledger does.
                  "Model map at launch: `" + " ".join(
                      f"{role}=opus" for role in tool.model_map.ROLES)
                  + "`\n")
        record = tool.build_record(batch="b", kind="run", ledger_text=ledger)
        self.assertEqual("claude-opus-5/high", record["orchestrator_model"])
        self.assertTrue(record["worker_models"].startswith("all=opus"))

    def test_a_ledger_written_before_a_role_joined_still_names_its_workers(self):
        """Ticket 33 ruling 2 widened the map from twelve roles to fourteen, so
        every ledger already on disk names twelve. Read through the strict
        `ledger_map` those read `{}` and this cell falls to `not stated`, which
        would overwrite run `batch-170a59`'s and run `batch-207704`'s existing
        `runs.jsonl` rows with a worse answer the next time either reading is
        re-taken. The cost cell reports history, so it reads the partial map.
        """
        twelve = [r for r in tool.model_map.ROLES if r not in ("attacker", "seam")]
        ledger = ("Session model at launch: claude-opus-5\n"
                  "Model map at launch: `" + " ".join(
                      f"{role}=opus" for role in twelve) + "`\n")
        cell = tool.build_record(batch="b", kind="run",
                                 ledger_text=ledger)["worker_models"]
        self.assertNotEqual(tool.model_map.NOT_STATED, cell)
        self.assertIn("workers=opus", cell)
        self.assertNotIn("attacker", cell)

    def test_a_hunt_record_carries_kind_hunt(self):
        """Ruling 11: hunts share the files."""
        self.assertEqual("hunt", tool.build_record(batch="b", kind="hunt")["kind"])


class TheCacheReading(unittest.TestCase):
    """Ticket 37, ruling 14: the one threshold, and the field it needs.

    **The figure was printed and never stored.** The ticket's own facts of
    2026-09-05 list `cache_probe.py:113`'s read-to-write ratio under "Printed
    and not stored -- none reaches a row", and `finale.md` step has run
    `cache_probe.py --days 2` since. Sitting 4 builds ruling 14's threshold,
    and a threshold over a field nothing writes is an alarm that can never
    fire -- which is the "figure nobody acts on" this ticket's own grilling
    section was raised to prevent.

    The arithmetic is `cache_probe.report`'s own: the fleet's reads over the
    fleet's writes, counting only subagents that hold usage rows.
    """

    def test_the_ratio_is_the_fleets_reads_over_its_writes(self):
        found = tool.cache_reading({
            "session": "s",
            "main": {"written": 1, "read": 9, "rows": 2},
            "agents": [{"written": 100, "read": 5000, "rows": 3},
                       {"written": 100, "read": 1000, "rows": 4}]})
        self.assertEqual(found["written"], 200)
        self.assertEqual(found["read"], 6000)
        self.assertEqual(found["ratio"], 30.0)

    def test_a_subagent_with_no_usage_rows_is_left_out(self):
        """`cache_probe.report` filters on `rows` and this must agree with it,
        or the same transcript answers two ratios."""
        found = tool.cache_reading({
            "session": "s", "main": {"written": 0, "read": 0, "rows": 0},
            "agents": [{"written": 100, "read": 5000, "rows": 3},
                       {"written": 0, "read": 0, "rows": 0}]})
        self.assertEqual(found["ratio"], 50.0)

    def test_nothing_written_yields_no_ratio_and_never_a_division(self):
        found = tool.cache_reading({
            "session": "s", "main": {"written": 0, "read": 0, "rows": 0},
            "agents": [{"written": 0, "read": 10, "rows": 1}]})
        self.assertIsNone(found["ratio"])

    def test_a_run_with_no_subagent_rows_reads_none(self):
        """Null, never zero. A ratio of zero would fire ruling 14's floor on a
        run nobody measured."""
        self.assertIsNone(tool.cache_reading(
            {"session": "s", "main": {"written": 0, "read": 0, "rows": 0},
             "agents": []}))

    def test_the_record_carries_it_where_it_was_read(self):
        record = tool.build_record("b", "run", version="2.1.261",
                                   version_reader=lambda: "2.1.261",
                                   cache={"read": 6000, "written": 200,
                                          "ratio": 30.0})
        self.assertEqual(record["cache"]["ratio"], 30.0)

    def test_the_record_omits_nothing_when_the_reading_failed(self):
        """A finale whose transcript could not be probed writes the line
        anyway. A measurement never costs a run its record."""
        record = tool.build_record("b", "run", version="2.1.261",
                                   version_reader=lambda: "2.1.261")
        self.assertIsNone(record.get("cache"))


class TheInsideRunCountsAreNowMeasured(unittest.TestCase):
    """Ticket 37 sitting 3: ruling 6's four counts and their denominator.

    Sitting 2 wrote five explicit nulls and said why. The reader is repaired,
    so `build_record` fills them from it -- from `run_quality.issue_quality`
    for three, and from the transcript's role names for escalations, which was
    "not read anywhere at all" until now.
    """

    LEDGER = """
| issue | status | estimate | stamps |
|---|---|---|---|
| 149c | done | 60-90 min | attempt 1; verify: pass; review: pass |
| 149e | done | 60-90 min | attempt 1; verify: pass; review: reject; attempt 2; verify: pass; review: pass |

| after | total | files |
|---|---|---|
| 149c (-13, -3) | 51 | 29 |
"""

    def record(self, **over):
        given = dict(batch="b", kind="run", ledger_text=self.LEDGER,
                     spans={"149e": {"roles": {"run-issues-implementer-escalated"}}})
        given.update(over)
        return tool.build_record(**given)

    def test_the_denominator_is_the_repaired_readers_count(self):
        """TWO issues, not three. The carry-forward row in the ledger above is
        the exact shape that made `batch-170a59` grade 12 rows for six."""
        self.assertEqual(self.record()["quality"]["issues_graded"], 2)

    def test_the_first_attempt_passes_are_counted(self):
        self.assertEqual(self.record()["quality"]["first_attempt_passes"], 1)

    def test_the_strikes_are_counted(self):
        self.assertEqual(self.record()["quality"]["strikes"], 1)

    def test_escalations_are_counted_off_the_transcript_role_names(self):
        self.assertEqual(self.record()["quality"]["escalations"], 1)

    def test_a_run_with_no_escalation_records_a_measured_zero(self):
        """A zero here is a FACT and is not the same as a null. Sitting 2 could
        write neither; this sitting must be able to write both."""
        got = self.record(spans={"149e": {"roles": {"run-issues-implementer"}}})
        self.assertEqual(got["quality"]["escalations"], 0)

    def test_no_transcript_leaves_escalations_null_and_the_others_measured(self):
        """The ledger and the transcript are two sources. Losing one must cost
        the figures that came from it and no others."""
        got = self.record(spans=None)
        self.assertIsNone(got["quality"]["escalations"])
        self.assertEqual(got["quality"]["strikes"], 1)

    def test_a_ledger_that_could_not_be_read_leaves_every_count_null(self):
        """Not zero. `run_records.append_run` would take a zero now, so the
        discipline has to hold HERE: a run whose ledger is gone did not have
        no strikes, it had none read."""
        quality = tool.build_record(batch="b", kind="run")["quality"]
        self.assertTrue(all(value is None for value in quality.values()))

    def test_what_it_writes_is_accepted_by_the_writer(self):
        """The two halves have to agree, and they are in different files.
        `normalise_quality` refuses a count without its denominator and a
        count larger than it, so this is the join under test."""
        ok, why = run_records.append_run(
            pathlib.Path(tempfile.mkdtemp()), self.record())
        self.assertTrue(ok, why)


class TheFasterFiguresAndTheSteps(unittest.TestCase):
    """Rulings 5, 19 and 21, on the record `run_costs.py` builds."""

    def test_the_five_faster_figures_ride_on_the_record(self):
        got = tool.build_record(
            batch="b", kind="run", ledger_text=TheInsideRunCountsAreNowMeasured.LEDGER,
            hours=4.0, idle_hours=1.0, agent_hours=2.0)
        faster = got["faster"]
        self.assertEqual(faster["wall_minutes_per_issue"], 120.0)
        self.assertEqual(faster["idle_minutes_per_issue"], 30.0)
        self.assertEqual(faster["agent_hours_per_issue"], 1.0)

    def test_a_missing_clock_nulls_one_figure_and_not_the_others(self):
        got = tool.build_record(
            batch="b", kind="run", ledger_text=TheInsideRunCountsAreNowMeasured.LEDGER,
            hours=4.0)
        self.assertIsNone(got["faster"]["idle_minutes_per_issue"])
        self.assertEqual(got["faster"]["wall_minutes_per_issue"], 120.0)

    def test_the_longest_step_per_kind_joins_both_instruments(self):
        got = tool.build_record(
            batch="b", kind="run",
            stamped=[{"kind": "build", "seconds": 900.0, "label": "cold build"}],
            agent_steps=[{"kind": "run-issues-implementer", "seconds": 3600.0,
                          "label": "issue 149e"}])
        self.assertEqual(got["longest_steps"]["build"]["measured"], "stamped")
        self.assertEqual(
            got["longest_steps"]["run-issues-implementer"]["minutes"], 60.0)

    def test_a_run_that_stamped_nothing_carries_no_step_reading(self):
        """Absent, never a zero. Every run before this sitting stamped nothing
        at all, and ruling 3 keeps all of them."""
        got = tool.build_record(batch="b", kind="run")
        self.assertEqual(got.get("longest_steps"), {})


class TheOrphanCensusIsNotDiscarded(unittest.TestCase):
    """The `/code-review` pass of 2026-09-06, and the worst finding in it.

    `estimate_accuracy.actuals` returns `(spans, orphans)`, and the second
    value exists precisely so a silent loss is impossible: 30 per-issue spawns
    went into run `batch-88624c` and 18 came out booked to the wrong issue,
    with issue 224c named by no prompt at all.

    `quality_counts` read the first value alone and took an EMPTY `spans` as
    "the transcript named no issue", so a transcript whose spawns were all
    unattributed recorded `escalations: 0`. That is a measured zero for a
    figure nothing read -- the exact fault this whole sitting exists to end,
    committed by the code that ends it.
    """

    LEDGER = TheInsideRunCountsAreNowMeasured.LEDGER

    def test_a_transcript_that_attributed_nothing_leaves_escalations_null(self):
        got = tool.quality_counts(self.LEDGER, spans={}, orphans=["a heading"])
        self.assertIsNone(got["escalations"])

    def test_a_transcript_that_attributed_everything_and_found_none_is_zero(self):
        """The other direction must still be a FACT. A run where every spawn
        was attributed and none was an escalation genuinely had none."""
        got = tool.quality_counts(
            self.LEDGER, spans={"149c": {"roles": {"run-issues-implementer"}}},
            orphans=[])
        self.assertEqual(got["escalations"], 0)

    def test_an_orphan_beside_attributed_spawns_still_refuses_the_figure(self):
        """A partial attribution cannot be counted either: the escalation may
        be the spawn that was lost."""
        got = tool.quality_counts(
            self.LEDGER, spans={"149c": {"roles": {"run-issues-implementer"}}},
            orphans=["Pick up where the last gate stopped."])
        self.assertIsNone(got["escalations"])

    def test_the_ledgers_own_counts_survive_an_orphaned_transcript(self):
        """Losing one source costs the figures that came from it and no
        others."""
        got = tool.quality_counts(self.LEDGER, spans={}, orphans=["x"])
        self.assertEqual(got["issues_graded"], 2)
        self.assertEqual(got["strikes"], 1)


# One real `model landed:` line, from the shape `model-landed-check.py` writes.
LANDED_OK = ("- model landed: run-issues-implementer ran on claude-opus-5 "
             "(opus) at effort high (ledger asked opus).\n")
LANDED_FAULT = ("- model landed: run-issues-implementer ran on "
                "claude-fable-5 (fable) at effort high (ledger asked opus). "
                "**MISMATCH**: the ledger asked opus.\n")


class TheTrialVerdictRidesOnTheLine(unittest.TestCase):
    """Ticket 39 sitting 4 handed this ticket one line and nothing carried it.

    Its own decision ledger reads: "The merge briefing alone, with the answer
    behind one function `trial_verdict`. ... Ticket 37 calls the same
    function." Sittings 2, 3 and 4 of ticket 37 all passed it, so the mark
    ruling 22 raises has lived only in a briefing nothing reads across runs.

    The answer is READ, never re-derived: `run_quality.trial_verdict` is the
    one reader, so the briefing and this line cannot disagree. That is the
    same discipline `journal_for` and `read_transcript` were consolidated
    under in ticket 39.
    """

    def test_a_journal_proving_the_map_records_holds(self):
        record = tool.build_record(batch="b", kind="run",
                                   journal_text=LANDED_OK * 3)
        self.assertEqual("holds", record["trial"]["state"])
        self.assertEqual(3, record["trial"]["spawns"])
        self.assertEqual(3, record["trial"]["proved"])

    def test_one_mismatch_voids_the_line(self):
        """Ruling 22: a run whose workers did not land on the map cannot be
        read as a trial of that map, whatever else it measured."""
        record = tool.build_record(batch="b", kind="run",
                                   journal_text=LANDED_OK + LANDED_FAULT)
        self.assertEqual("void", record["trial"]["state"])
        self.assertEqual(1, record["trial"]["mismatches"])

    def test_no_journal_is_not_measured_and_never_a_pass(self):
        """Every run before ticket 39 sitting 2's hook landed on 2026-09-05.
        `batch-b5e96d` is one, measured, and it must not read as a pass."""
        record = tool.build_record(batch="b", kind="run")
        self.assertEqual("unmeasured", record["trial"]["state"])
        self.assertEqual(0, record["trial"]["spawns"])

    def test_the_mismatch_count_is_a_number_the_record_can_hold(self):
        """`Verdict.mismatches` is a tuple of whole journal lines. Storing it
        would put a sentence naming a role and a model into a field a reader
        counts, and JSON would carry it into every future reading of the
        file."""
        record = tool.build_record(batch="b", kind="run",
                                   journal_text=LANDED_FAULT * 2)
        self.assertEqual(2, record["trial"]["mismatches"])
        json.dumps(record)



class TheForkPointCriteria(unittest.TestCase):
    """`_criteria` reads each issue file AS IT WAS at the run's fork point.

    Not at HEAD: the run itself appends implementation records and two gate
    verdicts to the very file it is grading, so a count taken afterwards would
    grade a file the implementer never saw. Ruled by the human, 2026-09-14.
    """

    def git(self, repo, *args):
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                       capture_output=True, text=True)

    def build(self, tmp):
        repo = pathlib.Path(tmp)
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "t@example.com")
        self.git(repo, "config", "user.name", "t")
        issues = repo / ".scratch" / "f" / "issues"
        issues.mkdir(parents=True)
        (issues / "05b-a-thing.md").write_text(
            "# t\n\n## Acceptance criteria\n\n"
            + "".join(f"- [ ] criterion {n}\n" for n in range(1, 4))
            + "\n## Must still be true\n\n- x\n", encoding="utf-8")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-qm", "fork point")
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        # The run then APPENDS to the same file, as every run does.
        with open(issues / "05b-a-thing.md", "a", encoding="utf-8") as handle:
            handle.write("\n## Acceptance criteria\n\n"
                         + "".join(f"- [ ] later {n}\n" for n in range(1, 9)))
        runs = repo / ".scratch" / "f" / "runs" / "batch-aaaaaa"
        runs.mkdir(parents=True)
        ledger = runs / "run.md"
        ledger.write_text(f"Fork point: `{sha}` (main's head at launch)\n",
                          encoding="utf-8")
        return repo, ledger

    def test_it_counts_the_file_the_implementer_was_handed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ledger = self.build(tmp)
            found = tool._criteria(str(repo), str(ledger),
                                   ledger.read_text(encoding="utf-8"))
            self.assertEqual(found.get("05b"), 3)

    def test_a_ledger_with_no_fork_point_reads_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ledger = self.build(tmp)
            self.assertEqual(tool._criteria(str(repo), str(ledger),
                                            "no fork point here\n"), {})

    def test_a_repository_git_cannot_read_returns_an_empty_map(self):
        """Empty, which `run_measures` turns into nulls. A repository nobody
        could read has not told us how many criteria an issue had."""
        with tempfile.TemporaryDirectory() as tmp:
            _repo, ledger = self.build(tmp)
            self.assertEqual(
                tool._criteria("/nowhere/at/all", str(ledger),
                               ledger.read_text(encoding="utf-8")), {})



class TheDeclaredClass(unittest.TestCase):
    """What the issue file says about ITSELF, read at the fork point.

    `migration` and `critical_gate` are outcomes, read after the run. Class 9
    acts before either exists, so these two are what a harden pass can read.
    Ruled by the human, 2026-09-14.
    """

    def git(self, repo, *args):
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                       capture_output=True, text=True)

    def build(self, tmp, body):
        repo = pathlib.Path(tmp)
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "t@example.com")
        self.git(repo, "config", "user.name", "t")
        issues = repo / ".scratch" / "f" / "issues"
        issues.mkdir(parents=True)
        (issues / "05b-a-thing.md").write_text(body, encoding="utf-8")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-qm", "fork point")
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        runs = repo / ".scratch" / "f" / "runs" / "batch-aaaaaa"
        runs.mkdir(parents=True)
        ledger = runs / "run.md"
        ledger.write_text(f"Fork point: `{sha}` (main's head at launch)\n",
                          encoding="utf-8")
        return repo, ledger

    def read(self, tmp, body):
        repo, ledger = self.build(tmp, body)
        return tool._declared(str(repo), str(ledger),
                              ledger.read_text(encoding="utf-8")).get("05b")

    def test_writes_rows_yes_is_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.read(tmp, "# t\n\n## Target database\n\n"
                                 "Writes rows: yes\n")
            self.assertIs(got["declared_writes_rows"], True)

    def test_writes_rows_no_is_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.read(tmp, "# t\n\n## Target database\n\n"
                                 "Writes rows: no. The change is in ci.yml\n")
            self.assertIs(got["declared_writes_rows"], False)

    def test_a_file_with_no_such_line_is_null_and_never_false(self):
        """A file that has not answered has not answered no. Three of the 25
        issues measured on 2026-09-14 read this way."""
        with tempfile.TemporaryDirectory() as tmp:
            got = self.read(tmp, "# t\n\nNo target database section.\n")
            self.assertIsNone(got["declared_writes_rows"])

    def test_a_named_migration_file_is_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.read(tmp, "# t\n\nApplies "
                                 "`supabase/migrations/0004_x.sql`.\n")
            self.assertIs(got["declared_migration"], True)

    def test_the_word_migration_alone_is_not_a_named_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.read(tmp, "# t\n\nThis issue needs a migration one "
                                 "day.\n")
            self.assertIs(got["declared_migration"], False)

    def test_it_reads_the_fork_point_not_head(self):
        """The run appends to the file it is grading, so a later edit that adds
        `Writes rows: yes` must not change what the fork point declared."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, ledger = self.build(
                tmp, "# t\n\n## Target database\n\nWrites rows: no\n")
            later = repo / ".scratch" / "f" / "issues" / "05b-a-thing.md"
            with open(later, "a", encoding="utf-8") as handle:
                handle.write("\nWrites rows: yes\n")
            got = tool._declared(str(repo), str(ledger),
                                 ledger.read_text(encoding="utf-8"))["05b"]
            self.assertIs(got["declared_writes_rows"], False)

    def test_a_repository_git_cannot_read_returns_an_empty_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            _repo, ledger = self.build(tmp, "# t\n\nWrites rows: yes\n")
            self.assertEqual(
                tool._declared("/nowhere", str(ledger),
                               ledger.read_text(encoding="utf-8")), {})


# --------------------------------------------------------------------------
# Issue 06, `three suites per issue`. The figure counts WHOLE-SUITE launches,
# runner and subagents alike, because the ruling it answers counts them alike:
# "one issue runs the full suite five to nine times".
#
# The human ruled the reading on 2026-09-17 against three rivals. Measured on
# the `7f5b53` transcript the four candidates gave 0.07, 1.43, 5.50 and 77.86 per
# issue; 5.50 is the one that reproduces the ruling's own "five to nine"
# independently, and it is the only one of the four that counts what the cut
# removes.


def transcript_line(command, sidechain=False, call_id=None):
    block = {"type": "tool_use", "name": "Bash", "input": {"command": command}}
    if call_id is not None:
        block["id"] = call_id
    return json.dumps({"isSidechain": sidechain,
                       "message": {"content": [block]}})


def fixture_run(commands):
    """One run directory of transcripts. `commands` is (command, sidechain)
    or (command, sidechain, tool_use id)."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="suites-"))
    (root / "session.jsonl").write_text(
        "\n".join(transcript_line(*one) for one in commands), encoding="utf-8")
    return root


class WholeSuiteReadings(unittest.TestCase):
    def count(self, commands):
        return tool.whole_suite_readings(fixture_run(commands))

    def test_a_bare_suite_run_counts(self):
        self.assertEqual(self.count([("npm test", False)]), (1, 0))

    def test_a_redirect_is_not_a_positional_path(self):
        """`npm test > log 2>&1` is a whole suite. Reading the words after the
        redirect as arguments to the suite is what made an early draft of this
        rule score the real transcript at zero."""
        self.assertEqual(
            self.count([("npm test > /tmp/baseline.log 2>&1", False)]), (1, 0))

    def test_a_scoped_run_does_not_count(self):
        """A run over named directories reads part of the tree, so it is not a
        whole-tree reading however much coverage it asks for."""
        self.assertEqual(self.count([
            ("npx vitest run --coverage.enabled tests/jobs/ tests/storage/", False),
        ]), (0, 0))

    def test_an_exclusion_repair_still_counts_as_whole(self):
        """`--exclude <pattern>` is a flag and its value is not a positional
        path. The `Regenerate coverage without the contended file` repair is
        the shape this issue exists to remove, so it must be counted."""
        self.assertEqual(self.count([
            ('npx vitest run --coverage --exclude "tests/a.test.ts"', False),
        ]), (1, 0))

    def test_a_heredoc_that_quotes_a_command_is_prose(self):
        """A journal entry quoting a vitest line is not a launch. `segments`
        strips heredocs, which is why it is borrowed rather than re-written."""
        self.assertEqual(self.count([
            ("cat >> run-journal.md <<'J'\nran npx vitest run --coverage\nJ", False),
        ]), (0, 0))

    def test_the_runner_and_its_subagents_are_counted_apart(self):
        self.assertEqual(self.count([
            ("npm test", False), ("npm test", True), ("npx vitest run", True),
        ]), (1, 2))

    def test_one_call_counts_once_however_many_segments_it_carries(self):
        """The rule the transcript reading already took: a figure one compound
        one-liner can move is not a figure."""
        self.assertEqual(self.count([
            ("npm test && npx vitest run --coverage && npm test", False),
        ]), (1, 0))

    def test_two_separate_calls_of_the_same_command_count_twice(self):
        """Identity is the tool_use id, not the command text: two gates that
        each ran `rm -rf .vitest-cache && npm test` ran the suite twice.

        Measured on `7f5b53`, 2026-09-17: 84 whole-suite calls, 84 distinct
        ids, 78 distinct command texts. Keying on text dropped six real runs,
        five of them that one cache-clearing line from five gate sessions.
        """
        self.assertEqual(self.count([("npm test", False, "a"),
                                     ("npm test", False, "b")]), (2, 0))

    def test_one_call_written_to_the_transcript_twice_counts_once(self):
        """The other direction. A resumed or compacted session can write an
        entry again, and the id is what refuses it."""
        self.assertEqual(self.count([("npm test", False, "same"),
                                     ("npm test", False, "same")]), (1, 0))

    def test_a_call_carrying_no_id_is_counted_rather_than_dropped(self):
        """A reading that happened is a reading. Dropping it would shrink the
        figure quietly on a transcript shape we have not seen."""
        self.assertEqual(self.count([("npm test", False), ("npm test", False)]),
                         (2, 0))

    def test_a_malformed_line_does_not_end_the_reading(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="suites-bad-"))
        (root / "s.jsonl").write_text(
            "{ not json\n" + transcript_line("npm test"), encoding="utf-8")
        self.assertEqual(tool.whole_suite_readings(root), (1, 0))

    def test_a_directory_with_no_transcripts_reads_zero(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="suites-empty-"))
        self.assertEqual(tool.whole_suite_readings(root), (0, 0))


class SuitesPerIssue(unittest.TestCase):
    def test_the_figure_divides_by_issues_closed(self):
        self.assertEqual(tool.suites_figure(1, 76, 14),
                         {"whole": 77, "runner": 1, "subagents": 76,
                          "per_issue": 5.5})

    def test_no_issue_count_means_no_rate_rather_than_a_crash(self):
        figure = tool.suites_figure(1, 2, 0)
        self.assertIsNone(figure["per_issue"])
        self.assertEqual(figure["whole"], 3)



if __name__ == "__main__":
    unittest.main()
