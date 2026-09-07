#!/usr/bin/env python3
"""Cases for run_session.py — batch id to session, and per-model reporting.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 3 (rulings 11, 12, 15).

The fault this closes, measured twice in `.scratch/workflow-audit/run-costs.md`:
the 2026-09-02 and 2026-09-05 rows both carry "the worktree was reused and its
name does not match the branch, so --transcript had to be passed by hand".
`run_costs.py` looked for the run's name in the PROJECT DIRECTORY name, and run
`batch-b5e96d` ran in a worktree called `run-issues-414a-99f-286335`. A batch id
read off the ledger does not care what the worktree is called.

    python3 -m unittest test_run_session
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import run_session as tool


MERGED_RUN = """# Run ledger — 533, 546 (run `batch-b5e96d`)

Owner: none — MERGED to local main 2026-09-05 at `2c12b53a`
Worktree: `{tree}`
Started 2026-09-04. State: **merged**
"""

LIVE_HUNT = """# Round brief — parallel hunt (hunt `hunt-3f21aa`)

Owner: session-7
Worktree: `{tree}`
"""


def tree_with(text: str, relative: str) -> pathlib.Path:
    """A throwaway worktree holding one ledger at `relative`."""
    root = pathlib.Path(tempfile.mkdtemp())
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.format(tree=root), encoding="utf-8")
    return root


class LedgerForBatch(unittest.TestCase):
    """A batch id selects its ledger whatever the run's state.

    `find_live_ledger.py` refuses everything but a LIVE ledger, on purpose: it
    picks a run to resume. A cost script measures a run that has just finished,
    and by then the owner line reads `awaiting-merge` or `merged`. The two
    questions are different and this is the second one.
    """

    def test_finds_a_merged_run_by_its_batch_id(self):
        tree = tree_with(MERGED_RUN, ".scratch/pilot/runs/batch-b5e96d/run.md")
        found = tool.ledger_for_batch("batch-b5e96d", worktrees=[str(tree)])
        self.assertIsNotNone(found)
        self.assertEqual(found.kind, "run")
        self.assertTrue(found.path.endswith("runs/batch-b5e96d/run.md"))

    def test_finds_a_hunt_by_its_batch_id(self):
        tree = tree_with(LIVE_HUNT, ".scratch/pilot/round-brief.md")
        found = tool.ledger_for_batch("hunt-3f21aa", worktrees=[str(tree)])
        self.assertIsNotNone(found)
        self.assertEqual(found.kind, "hunt")

    def test_an_unknown_batch_id_is_None_and_not_a_guess(self):
        tree = tree_with(MERGED_RUN, ".scratch/pilot/runs/batch-b5e96d/run.md")
        self.assertIsNone(tool.ledger_for_batch("batch-nope", worktrees=[str(tree)]))

    def test_one_live_run_is_not_picked_for_a_different_batch_id(self):
        """Nothing is chosen by count. The 155-157 chase cost 25 minutes to
        a script that picked the only candidate it could see."""
        tree = tree_with(LIVE_HUNT, ".scratch/pilot/round-brief.md")
        self.assertIsNone(tool.ledger_for_batch("batch-b5e96d", worktrees=[str(tree)]))


class SlugForWorktree(unittest.TestCase):
    """A worktree path IS its project directory name, once punctuated out.

    Every expected value below was read off `~/.claude/projects` on 2026-09-06,
    against the path the directory was made from. They are measurements, not a
    second copy of the transform.
    """

    def test_a_plain_checkout(self):
        self.assertEqual(
            tool.slug_for("/home/user/notes"),
            "-home-user-notes")

    def test_a_dot_claude_worktree_doubles_the_dash(self):
        self.assertEqual(
            tool.slug_for("/home/user/project/.claude/worktrees/"
                          "run-issues-414a-99f-286335"),
            "-home-user-project--claude-worktrees-"
            "run-issues-414a-99f-286335")

    def test_a_space_becomes_a_dash_like_every_other_punctuation(self):
        self.assertEqual(
            tool.slug_for("/home/user/My Project 01"),
            "-home-user-My-Project-01")

    def test_a_trailing_slash_does_not_add_a_dash(self):
        """`Worktree:` lines are written by hand as often as by a script."""
        self.assertEqual(
            tool.slug_for("/home/user/notes/"),
            tool.slug_for("/home/user/notes"))


def row(stamp: str, **extra) -> str:
    payload = {"timestamp": stamp}
    payload.update(extra)
    return json.dumps(payload) + "\n"


def session(slug_root: pathlib.Path, name: str, stamps, text: str = "") -> pathlib.Path:
    """One session transcript plus its (empty) subagents directory."""
    main = slug_root / f"{name}.jsonl"
    main.write_text("".join(row(s, note=text) for s in stamps), encoding="utf-8")
    (slug_root / name / "subagents").mkdir(parents=True, exist_ok=True)
    return main


class SessionsForBatch(unittest.TestCase):
    """Batch id, ledger, worktree, slug, session. Every step measured.

    The last step is the one that cannot be skipped: the chosen transcript must
    NAME the batch. A foreign session sitting in the same slug cannot pass
    that, and run `batch-88624c` proved on 2026-08-31 what happens when nothing
    checks — 1.01 h reported for an 8.48 h run, appended as though measured.
    """

    def build(self, batch="batch-b5e96d"):
        tree = tree_with(MERGED_RUN, f".scratch/pilot/runs/{batch}/run.md")
        projects = pathlib.Path(tempfile.mkdtemp())
        slug = projects / tool.slug_for(str(tree))
        slug.mkdir(parents=True)
        return tree, projects, slug

    def test_picks_the_session_that_names_the_batch(self):
        tree, projects, slug = self.build()
        session(slug, "aaaa", ["2026-09-04T10:00:00Z"], "unrelated work")
        session(slug, "bbbb", ["2026-09-04T11:00:00Z"], "run batch-b5e96d")
        found, why = tool.sessions_for_batch(
            "batch-b5e96d", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(why, "")
        self.assertEqual([pathlib.Path(p).stem for p in found], ["bbbb"])

    def test_a_resumed_run_returns_both_halves_newest_last(self):
        tree, projects, slug = self.build()
        session(slug, "second", ["2026-09-05T09:00:00Z"], "run batch-b5e96d")
        session(slug, "first", ["2026-09-04T09:00:00Z"], "run batch-b5e96d")
        found, why = tool.sessions_for_batch(
            "batch-b5e96d", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(why, "")
        self.assertEqual([pathlib.Path(p).stem for p in found], ["first", "second"])

    def test_no_session_names_the_batch_and_nothing_is_guessed(self):
        tree, projects, slug = self.build()
        session(slug, "aaaa", ["2026-09-04T10:00:00Z"], "unrelated work")
        found, why = tool.sessions_for_batch(
            "batch-b5e96d", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(found, [])
        self.assertIn("batch-b5e96d", why)
        self.assertIn("names", why)

    def test_an_unknown_batch_id_says_so_and_names_it(self):
        tree, projects, _ = self.build()
        found, why = tool.sessions_for_batch(
            "batch-nope", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(found, [])
        self.assertIn("batch-nope", why)

    def test_a_ledger_with_no_worktree_line_says_which_ledger(self):
        tree = tree_with("# Run ledger (run `batch-x`)\n\nOwner: none — merged\n",
                         ".scratch/pilot/runs/batch-x/run.md")
        projects = pathlib.Path(tempfile.mkdtemp())
        found, why = tool.sessions_for_batch(
            "batch-x", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(found, [])
        self.assertIn("Worktree:", why)

    def test_a_missing_slug_directory_names_the_directory_it_wanted(self):
        tree = tree_with(MERGED_RUN, ".scratch/pilot/runs/batch-b5e96d/run.md")
        projects = pathlib.Path(tempfile.mkdtemp())
        found, why = tool.sessions_for_batch(
            "batch-b5e96d", worktrees=[str(tree)], projects=str(projects))
        self.assertEqual(found, [])
        self.assertIn(tool.slug_for(str(tree)), why)


def assistant(stamp, model, effort, msg_id, **usage):
    """One assistant row, shaped as this machine writes them.

    Field names read off a real `run-issues-implementer` transcript from run
    `batch-b5e96d` on 2026-09-06: `effort` is top level, `message.model` and
    `message.usage` are nested, and `message.id` is the retry key.
    """
    return json.dumps({
        "type": "assistant",
        "timestamp": stamp,
        "effort": effort,
        "message": {"model": model, "id": msg_id, "usage": {
            "input_tokens": usage.get("input", 0),
            "cache_creation_input_tokens": usage.get("cache_creation", 0),
            "cache_read_input_tokens": usage.get("cache_read", 0),
            "output_tokens": usage.get("output", 0),
        }},
    }) + "\n"


class ReadTranscript(unittest.TestCase):
    """The reader `model-landed-check.py` had, moved here so both callers share it.

    Its contract does not change: distinct models and efforts, in the order
    seen, and `<synthetic>` skipped. That last rule is the expensive one —
    measured 2026-09-05 over 20000 assistant rows, `<synthetic>` really does
    appear as `message.model`, and counted as a model it voids a trial row on
    no fault at all.
    """

    def write(self, body):
        path = pathlib.Path(tempfile.mkdtemp()) / "agent.jsonl"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def test_distinct_models_and_efforts_in_the_order_seen(self):
        path = self.write(
            assistant("2026-09-04T10:00:00Z", "claude-opus-5", "high", "a")
            + assistant("2026-09-04T10:01:00Z", "claude-opus-5", "high", "b")
            + assistant("2026-09-04T10:02:00Z", "claude-fable-5", "max", "c"))
        self.assertEqual(tool.read_transcript(path),
                         (("claude-opus-5", "claude-fable-5"), ("high", "max")))

    def test_synthetic_is_not_a_model(self):
        path = self.write(
            assistant("2026-09-04T10:00:00Z", "<synthetic>", "high", "a")
            + assistant("2026-09-04T10:01:00Z", "claude-opus-5", "high", "b"))
        self.assertEqual(tool.read_transcript(path)[0], ("claude-opus-5",))

    def test_a_missing_file_reads_as_nothing_measured(self):
        self.assertEqual(tool.read_transcript("/nowhere/at/all.jsonl"), ((), ()))


class SpawnRows(unittest.TestCase):
    """One row per subagent: role, model, effort, tokens by kind, clock, rows.

    Ruling 15. Tokens stay BY KIND and unmerged, because ruling 11 wants every
    detail the transcripts hold and a merged figure is the one thing that can
    mislead.
    """

    def build(self, spawns):
        root = pathlib.Path(tempfile.mkdtemp())
        main = root / "sess.jsonl"
        main.write_text(row("2026-09-04T09:00:00Z"), encoding="utf-8")
        subs = root / "sess" / "subagents"
        subs.mkdir(parents=True)
        for name, agent_type, description, body in spawns:
            (subs / f"{name}.jsonl").write_text(body, encoding="utf-8")
            (subs / f"{name}.meta.json").write_text(json.dumps({
                "agentType": agent_type, "description": description,
            }), encoding="utf-8")
        return str(main)

    def test_a_row_carries_the_role_the_model_the_effort_and_the_clock(self):
        main = self.build([("agent-a1", "run-issues-implementer",
                            "Implement issue 545 attempt 2",
                            assistant("2026-09-04T10:00:00Z", "claude-opus-5",
                                      "high", "a", input=2, cache_creation=100,
                                      cache_read=4000, output=50)
                            + assistant("2026-09-04T10:30:00Z", "claude-opus-5",
                                        "high", "b", output=10))])
        rows = tool.spawn_rows([main])
        self.assertEqual(len(rows), 1)
        one = rows[0]
        self.assertEqual(one.role, "implementer")
        self.assertEqual(one.agent_type, "run-issues-implementer")
        self.assertEqual(one.description, "Implement issue 545 attempt 2")
        self.assertEqual(one.models, ("claude-opus-5",))
        self.assertEqual(one.efforts, ("high",))
        self.assertEqual(one.input, 2)
        self.assertEqual(one.cache_creation, 100)
        self.assertEqual(one.cache_read, 4000)
        self.assertEqual(one.output, 60)
        self.assertEqual(one.rows, 2)
        self.assertEqual(one.seconds, 1800.0)

    def test_a_retried_turn_is_counted_once(self):
        """The transcript repeats a message when a turn is retried and both
        copies carry the same `message.id`."""
        main = self.build([("agent-a1", "run-issues-verify-gate", "Verify 545",
                            assistant("2026-09-04T10:00:00Z", "claude-opus-5",
                                      "high", "same", output=50)
                            + assistant("2026-09-04T10:00:01Z", "claude-opus-5",
                                        "high", "same", output=50))])
        self.assertEqual(tool.spawn_rows([main])[0].output, 50)

    def test_a_subagent_outside_the_twelve_roles_still_gets_a_row(self):
        """The board render has no agent file and no map row. It still spent
        tokens, and ruling 11 asks for every detail the transcripts hold."""
        main = self.build([("agent-b", "general-purpose", "Render the board",
                            assistant("2026-09-04T10:00:00Z", "claude-fable-5",
                                      "medium", "a", output=5))])
        one = tool.spawn_rows([main])[0]
        self.assertIsNone(one.role)
        self.assertEqual(one.agent_type, "general-purpose")

    def test_a_spawn_with_no_meta_file_is_read_anyway(self):
        root = pathlib.Path(tempfile.mkdtemp())
        main = root / "sess.jsonl"
        main.write_text(row("2026-09-04T09:00:00Z"), encoding="utf-8")
        subs = root / "sess" / "subagents"
        subs.mkdir(parents=True)
        (subs / "agent-c.jsonl").write_text(
            assistant("2026-09-04T10:00:00Z", "claude-opus-5", "high", "a",
                      output=7), encoding="utf-8")
        one = tool.spawn_rows([str(main)])[0]
        self.assertEqual(one.agent_type, "")
        self.assertEqual(one.output, 7)

    def test_both_halves_of_a_resumed_run_contribute_their_spawns(self):
        first = self.build([("agent-a", "run-issues-implementer", "Implement 1",
                             assistant("2026-09-04T10:00:00Z", "claude-opus-5",
                                       "high", "a", output=1))])
        second = self.build([("agent-b", "run-issues-implementer", "Implement 2",
                              assistant("2026-09-05T10:00:00Z", "claude-opus-5",
                                        "high", "b", output=2))])
        self.assertEqual(len(tool.spawn_rows([first, second])), 2)


class PerModelAccounting(unittest.TestCase):
    """the human's ruling of 2026-09-06: record all, display all, never merge.

    His words: "what harm in recording everything? ... i want all which model
    cost how much and time it took so that i can compare with other runs with
    different models as well". None in recording, so everything is recorded.
    The one thing refused is a SINGLE weighted figure spanning two models,
    because that figure needs a cross-model multiplier and a multiplier is a
    price with the currency taken off (ruling 11 refuses a dollar figure, and
    `~/.claude/rulings.md:64-67` struck a price sheet already).

    That merged figure is not hypothetical. On 2026-09-06 two real runs on this
    machine were measured mixing models materially -- `run-issues-resume-6a2355`
    at fable 50.6M against opus-4-8 43.4M, and `mint-settlement-batch-28b482`
    at opus-4-8 85.0M against fable 16.1M -- and `run-costs.md` wrote each as
    one `Weighted` cell.
    """

    def spawn(self, model, role="implementer", **counts):
        one = tool.Spawn(role=role, models=(model,), seconds=counts.pop("seconds", 60.0))
        one.by_model[model] = {k: counts.get(k, 0) for k in tool.KINDS}
        for kind in tool.KINDS:
            setattr(one, kind, counts.get(kind, 0))
        one.rows = 1
        return one

    def test_weigh_is_the_within_model_weighting_and_nothing_else(self):
        """input + cache_creation + cache_read/10 + output*5, as
        `orchestrator_cost.py:19` has weighted since 2026-08-21."""
        self.assertEqual(
            tool.weigh({"input": 100, "cache_creation": 200,
                        "cache_read": 1000, "output": 10}),
            100 + 200 + 100 + 50)

    def test_by_model_keeps_two_models_apart(self):
        rows = [self.spawn("claude-opus-5", output=10),
                self.spawn("claude-fable-5", role="verify", output=4)]
        found = tool.by_model(rows)
        self.assertEqual(sorted(found), ["claude-fable-5", "claude-opus-5"])
        self.assertEqual(found["claude-opus-5"]["output"], 10)
        self.assertEqual(found["claude-fable-5"]["output"], 4)

    def test_by_model_weights_each_model_on_its_own(self):
        rows = [self.spawn("claude-opus-5", output=10),
                self.spawn("claude-fable-5", role="verify", output=4)]
        found = tool.by_model(rows)
        self.assertEqual(found["claude-opus-5"]["weighted"], 50)
        self.assertEqual(found["claude-fable-5"]["weighted"], 20)

    def test_mixed_is_true_only_when_two_models_really_answered(self):
        one = [self.spawn("claude-opus-5", output=1)]
        self.assertFalse(tool.mixed(one))
        two = one + [self.spawn("claude-fable-5", role="verify", output=1)]
        self.assertTrue(tool.mixed(two))

    def test_a_synthetic_row_does_not_make_a_run_look_mixed(self):
        """`<synthetic>` is a row the harness wrote, not a model that
        answered. Counted as one it voids a trial on no fault at all."""
        rows = [self.spawn("claude-opus-5", output=1),
                self.spawn(tool.SYNTHETIC, role="verify", output=1)]
        self.assertFalse(tool.mixed(rows))

    def test_by_role_carries_the_model_column_ruling_15_asks_for(self):
        rows = [self.spawn("claude-opus-5", output=10, seconds=120.0),
                self.spawn("claude-opus-5", output=6, seconds=60.0),
                self.spawn("claude-fable-5", role="verify", output=4)]
        found = tool.by_role(rows)
        self.assertEqual(found["implementer"]["models"], ("claude-opus-5",))
        self.assertEqual(found["implementer"]["spawns"], 2)
        self.assertEqual(found["implementer"]["seconds"], 180.0)
        self.assertEqual(found["verify"]["models"], ("claude-fable-5",))

    def test_a_role_that_ran_on_two_models_names_both(self):
        """A resumed run can change the map. The row says so rather than
        picking one, which is the same rule `read_transcript` follows."""
        rows = [self.spawn("claude-opus-5", output=1),
                self.spawn("claude-fable-5", output=1)]
        self.assertEqual(tool.by_role(rows)["implementer"]["models"],
                         ("claude-opus-5", "claude-fable-5"))

    def test_hours_split_between_the_models_a_role_ran_on(self):
        """Measured on the real run `batch-b5e96d` 2026-09-06: the
        `general-purpose` role ran on two models and BOTH rows read 3.04 h,
        because the clock was the role's total repeated. A number that repeats
        where it should split is read as two facts and is one."""
        rows = [self.spawn("claude-opus-5", output=1, seconds=7200.0),
                self.spawn("claude-fable-5", output=1, seconds=600.0)]
        found = tool.by_role(rows)["implementer"]["by_model"]
        self.assertEqual(found["claude-opus-5"]["seconds"], 7200.0)
        self.assertEqual(found["claude-fable-5"]["seconds"], 600.0)

    def test_effort_splits_between_the_models_a_role_ran_on(self):
        """Same defect the hours column had, and it survived that fix.
        Measured on run `batch-b5e96d` 2026-09-06: the `general-purpose` role
        ran on two models and BOTH rows read effort `high/max`, because the
        effort was the role's whole list repeated."""
        opus = self.spawn("claude-opus-5", output=1)
        opus.efforts = ("high",)
        fable = self.spawn("claude-fable-5", output=1)
        fable.efforts = ("max",)
        found = tool.by_role([opus, fable])["implementer"]["by_model"]
        self.assertEqual(found["claude-opus-5"]["efforts"], ("high",))
        self.assertEqual(found["claude-fable-5"]["efforts"], ("max",))

    def test_by_model_rows_counts_rows_and_not_spawns(self):
        """A field named `rows` that holds a spawn count is read as rows by
        the next caller, and nothing in the output says the two were swapped."""
        one = self.spawn("claude-opus-5", output=1)
        one.rows = 40
        two = self.spawn("claude-opus-5", output=1)
        two.rows = 2
        found = tool.by_model([one, two])["claude-opus-5"]
        self.assertEqual(found["spawns"], 2)
        self.assertEqual(found["rows"], 42)

    def test_a_spawn_outside_the_twelve_roles_is_filed_under_its_agent_type(self):
        one = tool.Spawn(agent_type="general-purpose", role=None,
                         models=("claude-fable-5",))
        one.by_model["claude-fable-5"] = dict.fromkeys(tool.KINDS, 0)
        self.assertIn("general-purpose", tool.by_role([one]))

    def test_the_module_offers_no_cross_model_total(self):
        """The refusal, stated as a test so it cannot be added back quietly.

        Every public name that totals tokens returns a mapping keyed by model.
        A future caller wanting one number has to write the multiplier itself,
        in the open, where a reviewer sees it.
        """
        rows = [self.spawn("claude-opus-5", output=10),
                self.spawn("claude-fable-5", role="verify", output=4)]
        for name in ("by_model", "by_role"):
            self.assertIsInstance(getattr(tool, name)(rows), dict)
        self.assertFalse(
            [n for n in dir(tool)
             if n in ("total_weighted", "weighted_total", "combined_weighted")])


class Rendering(unittest.TestCase):
    """What the human reads. One table per role, one row per subagent, no dollars."""

    def spawn(self, model, role, description, seconds=60.0, **counts):
        one = tool.Spawn(role=role, agent_type=f"run-issues-{role}",
                         agent_id="agent-1", description=description,
                         models=(model,), efforts=("high",), seconds=seconds)
        one.by_model[model] = {k: counts.get(k, 0) for k in tool.KINDS}
        for kind in tool.KINDS:
            setattr(one, kind, counts.get(kind, 0))
        one.rows = 3
        return one

    def test_the_role_table_carries_a_model_column(self):
        text = tool.render_roles([
            self.spawn("claude-opus-5", "implementer", "Implement 545", output=10),
            self.spawn("claude-fable-5", "verify", "Verify 545", output=4)])
        self.assertIn("implementer", text)
        self.assertIn("claude-opus-5", text)
        self.assertIn("verify", text)
        self.assertIn("claude-fable-5", text)

    def test_a_mixed_run_is_told_why_there_is_no_single_figure(self):
        text = tool.render_roles([
            self.spawn("claude-opus-5", "implementer", "Implement 545", output=10),
            self.spawn("claude-fable-5", "verify", "Verify 545", output=4)])
        self.assertIn("mixed models", text)
        self.assertIn("/usage", text)

    def test_a_single_model_run_is_not_lectured_about_mixing(self):
        text = tool.render_roles([
            self.spawn("claude-opus-5", "implementer", "Implement 545", output=10)])
        self.assertNotIn("mixed models", text)

    def test_no_currency_symbol_reaches_any_output(self):
        """Ruling 11: no dollar figure. Dollars come from `/usage` by hand."""
        rows = [self.spawn("claude-opus-5", "implementer", "Implement 545",
                           input=1, cache_creation=2, cache_read=3, output=4)]
        for text in (tool.render_roles(rows), tool.render_spawns(rows)):
            for mark in ("$", "USD", "£", "€", "cent"):
                self.assertNotIn(mark, text)

    def test_one_row_per_subagent_with_all_six_readings(self):
        rows = [self.spawn("claude-opus-5", "implementer", "Implement issue 545",
                           seconds=1800.0, input=2, cache_creation=100,
                           cache_read=4000, output=50)]
        text = tool.render_spawns(rows)
        self.assertIn("implementer", text)
        self.assertIn("claude-opus-5", text)
        self.assertIn("high", text)
        self.assertIn("4,000", text)
        self.assertIn("30.0", text)
        self.assertIn("Implement issue 545", text)

    def test_the_spawn_table_holds_a_row_for_every_spawn(self):
        rows = [self.spawn("claude-opus-5", "implementer", "Implement 545"),
                self.spawn("claude-opus-5", "implementer", "Implement 546"),
                self.spawn("claude-fable-5", "verify", "Verify 545")]
        text = tool.render_spawns(rows)
        self.assertEqual(text.count("Implement 54"), 2)
        self.assertIn("Verify 545", text)

    def test_nothing_at_all_says_so_rather_than_printing_an_empty_table(self):
        self.assertIn("no subagent", tool.render_spawns([]).lower())
        self.assertIn("no subagent", tool.render_roles([]).lower())


if __name__ == "__main__":
    unittest.main()
