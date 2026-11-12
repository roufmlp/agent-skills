"""Tests for feature_run.py: the workflow's args and the report's role cells."""

import contextlib
import datetime
import io
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feature_run as mod  # noqa: E402
import test_plan_check as fixture  # noqa: E402

AGENT = textwrap.dedent("""\
    ---
    name: build-feature-{role}
    description: a role
    model: {model}
    effort: {effort}
    autoCompactWindow: 400000
    tools: Read, Bash
    ---

    body
""")

ROLE_MODELS = {"implementer": ("sonnet", "high"), "verifier": ("sonnet", "high"),
               "reviewer": ("opus", "high"), "note-checker": ("opus", "high"),
               "merger": ("sonnet", "medium"), "final-verifier": ("sonnet", "high"),
               "final-reviewer": ("opus", "xhigh")}


class Feature(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.repo = root / "product"
        self.repo.mkdir()
        for path, text in fixture.FILES.items():
            self.write(self.repo, path, text)
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Sam Doe")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "approved plan")
        self.tree = self.repo / ".claude" / "worktrees" / "feature-bubble"
        self.git(self.repo, "worktree", "add", "-q", str(self.tree), "-b", "feature/bubble", "main")
        agents = root / "agents"
        agents.mkdir()
        for role, (model, effort) in ROLE_MODELS.items():
            (agents / f"build-feature-{role}.md").write_text(AGENT.format(role=role, model=model, effort=effort))
        self.agents_dir = mod.AGENTS_DIR
        mod.AGENTS_DIR = str(agents)

    def tearDown(self):
        mod.AGENTS_DIR = self.agents_dir
        self.tmp.cleanup()

    def write(self, tree, path, text):
        full = tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text)

    def git(self, tree, *args):
        return subprocess.run(["git", *args], cwd=tree, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(list(args))
        return code, out.getvalue()

    def args(self, *extra):
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree), "--started", "now", *extra)
        self.assertEqual(code, 0, out)
        return json.loads(out)

    # ── args ──

    def test_args_reads_notes_graph_roles_and_paths(self):
        got = self.args()
        self.assertEqual(got["feature"], "bubble")
        self.assertEqual(got["main"], "main")
        self.assertEqual(pathlib.Path(got["repo"]), self.repo.resolve())
        self.assertEqual(pathlib.Path(got["tree"]), self.tree.resolve())
        self.assertTrue(got["reports"].endswith(".git/build-feature/bubble"), got["reports"])
        self.assertTrue(pathlib.Path(got["reports"]).is_dir())
        self.assertNotIn("changes/", got["reports"])
        self.assertTrue(got["batch"].startswith("batch-"))
        self.assertEqual(got["started"], "now")
        self.assertIsNone(got["staging"])
        self.assertTrue(got["risk"])  # note 02 says row writes
        numbers = [n["number"] for n in got["notes"]]
        self.assertEqual(numbers, ["01", "02"])
        one, two = got["notes"]
        self.assertEqual(one["waits_for"], [])
        self.assertEqual(two["waits_for"], ["01"])
        self.assertEqual(one["screens"], "all signed-in")
        self.assertEqual(two["risk"], "row writes")
        self.assertEqual(one["state"], "not started")
        self.assertEqual(one["branch"], "note/bubble/01")
        self.assertTrue(one["worktree"].endswith(".claude/worktrees/note-bubble-01"))
        self.assertFalse(one["fresh"])
        self.assertEqual(got["roles"]["implementer"], {"model": "sonnet", "effort": "high", "override": False})
        self.assertEqual(got["roles"]["final-reviewer"]["effort"], "xhigh")

    def test_args_started_defaults_to_the_clock(self):
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 0, out)
        started = json.loads(out)["started"]
        self.assertRegex(started, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertEqual(started[:10], datetime.date.today().isoformat())

    def test_args_applies_a_role_override(self):
        got = self.args("--role", "implementer=opus:medium")
        self.assertEqual(got["roles"]["implementer"], {"model": "opus", "effort": "medium", "override": True})
        self.assertFalse(got["roles"]["verifier"]["override"])

    def test_args_refuses_a_bad_override(self):
        for bad, why in (("implementer=opus", "not `<role>=<model>:<effort>`"),
                         ("runner=opus:high", "names `runner`"),
                         ("implementer=gpt:high", "model `gpt`"),
                         ("implementer=opus:top", "effort `top`")):
            code, out = self.run_main("args", "bubble", "--tree", str(self.tree), "--role", bad)
            self.assertEqual(code, 3, out)
            self.assertIn(why, out)

    def test_args_refuses_a_bad_name_and_a_missing_tree(self):
        code, out = self.run_main("args", "Bubble!", "--tree", str(self.tree))
        self.assertEqual(code, 3)
        self.assertIn("REFUSED", out)
        code, out = self.run_main("args", "bubble", "--tree", str(self.repo / "nowhere"))
        self.assertEqual(code, 3)
        self.assertIn("does not exist", out)

    def test_args_reads_the_report_rows(self):
        self.write(self.tree, "changes/bubble/report.md", textwrap.dedent("""\
            # Bubble report

            State: stopped

            ## Notes

            | Note | State | Strikes | Attempts | Last report |
            | --- | --- | --- | --- | --- |
            | 01 | merged abc1234 | 1 | 2 | /x/01-attempt-1-verifier.md |
            | 02 | running | 0 | 1 | |
        """))
        one, two = self.args()["notes"]
        self.assertEqual(one["state"], "merged abc1234")
        self.assertEqual((one["strikes"], one["attempts"]), (1, 2))
        self.assertEqual(one["last_report"], "/x/01-attempt-1-verifier.md")
        self.assertEqual(two["state"], "not started")
        self.assertTrue(two["fresh"])

    def test_args_keeps_a_cut_notes_row_whose_file_moved(self):
        (self.tree / "changes/bubble/cut").mkdir()
        self.git(self.tree, "mv", "changes/bubble/01-header.md", "changes/bubble/cut/01-header.md")
        self.write(self.tree, "changes/bubble/report.md", textwrap.dedent("""\
            # Bubble report

            ## Notes

            | Note | State | Strikes | Attempts | Last report |
            | --- | --- | --- | --- | --- |
            | 01 | cut 2026-11-04 | 3 | 3 | /x/01-attempt-3-reviewer.md |
            | 02 | not started | | | |
        """))
        one, two = self.args()["notes"]
        self.assertEqual(one["number"], "01")
        self.assertEqual(one["state"], "cut 2026-11-04")
        self.assertEqual((one["strikes"], one["attempts"]), (3, 3))
        self.assertEqual(one["waits_for"], [])
        self.assertEqual(two["number"], "02")

    def test_args_reads_the_earlier_runs_report_parts(self):
        self.write(self.tree, "changes/bubble/report.md", textwrap.dedent("""\
            # Bubble report

            State: stopped

            ## Notes

            | Note | State | Strikes | Attempts | Last report |
            | --- | --- | --- | --- | --- |
            | 01 | merged abc1234 | 0 | 1 | |

            ## Roles

            | Role | Model | Effort | Tokens | Cost | Strikes |
            | --- | --- | --- | --- | --- | --- |
            | implementer | sonnet | high | | | 0 |
            | reviewer | opus | high | | | 2 |

            ## Defaults taken

            01: the toast stays 4 s, the note names no time

            ## Done-check edits

            none

            ## Final check

            Door: two-way, revert the merge commit.
            Blast radius: low, one screen.

            Final verifier 1: Verdict: FINDINGS (/x/final-1-verifier.md)
            Final reviewer 1: PASS (/x/final-1-reviewer.md)
            not run: a note failed, stopped or waits

            ## Decide

            none
        """))
        got = self.args()["earlier"]
        self.assertEqual(got["defaults"], ["01: the toast stays 4 s, the note names no time"])
        self.assertEqual(got["edits"], [])
        self.assertEqual(got["final"], ["Final verifier 1: Verdict: FINDINGS (/x/final-1-verifier.md)",
                                        "Final reviewer 1: PASS (/x/final-1-reviewer.md)"])
        self.assertEqual(got["strikes"], {"reviewer": 2})

    def test_args_earlier_is_empty_with_no_report(self):
        self.assertEqual(self.args()["earlier"],
                         {"defaults": [], "edits": [], "final": [], "tooling": [], "decide": [], "strikes": {}})

    def test_starting_state_rules(self):
        self.assertEqual(mod.starting_state("merged abc1234"), ("merged abc1234", False))
        self.assertEqual(mod.starting_state("cut 2026-11-03"), ("cut 2026-11-03", False))
        self.assertEqual(mod.starting_state("running"), ("not started", True))
        self.assertEqual(mod.starting_state("stopped: API errors"), ("not started", True))
        self.assertEqual(mod.starting_state("stopped: verifier returned no result"), ("not started", True))
        self.assertEqual(mod.starting_state("stopped: worktree: Error: `git worktree remove` was denied"),
                         ("not started", True))
        self.assertEqual(mod.starting_state("stopped: done check passes before the work"),
                         ("stopped: done check passes before the work", False))
        self.assertEqual(mod.starting_state(None), ("not started", False))
        self.assertEqual(mod.starting_state("not started"), ("not started", False))
        self.assertEqual(mod.starting_state("stopped: tooling: hook: PreToolUse:Write hook error"),
                         ("not started", True))
        self.assertEqual(mod.starting_state("waiting: failed again after its re-arm"),
                         ("waiting: failed again after its re-arm", False))

    # ── away mode ──

    REPORT = textwrap.dedent("""\
        # Bubble report

        State: {state}

        ## Notes

        | Note | State | Strikes | Attempts | Last report |
        | --- | --- | --- | --- | --- |
        | 01 | {s01} | 0 | 1 | |
        | 02 | {s02} | 0 | 1 | |

        ## Tooling stops

        2026-11-12 02: hook: PreToolUse:Write hook error: an isolated git worktree
    """)

    RULINGS = textwrap.dedent("""\
        ## Rulings

        - [re-arm] 02: note 02 failed three strikes on the label
          Ruled: 2026-11-12, default, "the done check names the label Reports"
          Touches: none
          Undo: one line

    """)

    def rule(self, part=None):
        plan = fixture.PLAN.replace("Approved: 2026-11-03", (part or self.RULINGS) + "Approved: 2026-11-03")
        self.write(self.tree, "changes/bubble/plan.md", plan)

    def commit(self, message):
        self.git(self.tree, "add", "-A")
        self.git(self.tree, "commit", "-qm", message)

    def test_args_carries_the_wait_from_its_one_place(self):
        import rulings
        self.assertEqual(self.args()["ruling_wait_seconds"], rulings.RULING_WAIT_SECONDS)

    def test_args_marks_a_note_that_had_its_re_arm(self):
        self.rule()
        one, two = self.args()["notes"]
        self.assertFalse(one["rearmed"])
        self.assertTrue(two["rearmed"])

    def test_args_lists_the_rulings_that_wait_at_the_gate(self):
        self.assertEqual((self.args()["gate_open"], self.args()["away"]), ([], []))
        self.rule()
        got = self.args()
        self.assertEqual(got["gate_open"], ["02"])
        self.assertEqual(len(got["away"]), 1)
        self.assertIn("02: note 02 failed three strikes on the label", got["away"][0])
        self.rule(self.RULINGS.replace("  Undo:", "  Confirmed: 2026-11-13\n  Undo:"))
        got = self.args()
        self.assertEqual(got["gate_open"], [])
        self.assertEqual(len(got["away"]), 1, "the report keeps the line once it is confirmed")

    def test_args_keeps_the_earlier_tooling_stops(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="not started"))
        self.assertEqual(self.args()["earlier"]["tooling"],
                         ["2026-11-12 02: hook: PreToolUse:Write hook error: an isolated git worktree"])

    def commands(self, out):
        """The commands a refusal prints between backticks, run as written."""
        found = re.findall(r"`(git -C [^`]+)`", out)
        for line in found:
            subprocess.run(shlex.split(line), env=self.env, check=True, capture_output=True)
        return found

    def test_a_note_changed_after_its_worktrees_base_never_starts_on_the_old_tree(self):
        # Old finding 13: the run handed such a note to the merger with "Fresh: yes", and one
        # sentence of that prompt was all that kept the old build out.
        note_tree = self.repo / ".claude" / "worktrees" / "note-bubble-02"
        self.git(self.repo, "worktree", "add", "-q", str(note_tree), "-b", "note/bubble/02", "feature/bubble")
        self.assertFalse(self.args()["notes"][1]["fresh"], "an unchanged note keeps its tree")
        self.write(self.tree, "changes/bubble/02-order.md", fixture.NOTE_02.replace("report count", "count"))
        self.commit("ruling: note 02")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("note 02: `git -C", out)
        self.assertNotIn("note 01:", out)
        ran = self.commands(out)
        self.assertEqual([line.split()[3] for line in ran], ["worktree", "branch", "worktree"], ran)
        self.assertFalse(note_tree.exists())
        self.assertEqual([n["state"] for n in self.args()["notes"]], ["not started", "not started"])

    def test_a_note_whose_test_changed_after_the_base_never_starts_on_the_old_branch(self):
        self.git(self.repo, "branch", "note/bubble/02", "feature/bubble")
        self.write(self.tree, "e2e/order.spec.ts", "// spec, changed by a ruling\n")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, "an uncommitted change counts too")
        self.assertEqual([line.split()[3] for line in self.commands(out)], ["branch", "worktree"])
        self.args()

    def test_a_note_a_killed_run_left_running_never_starts_on_its_old_tree(self):
        note_tree = self.repo / ".claude" / "worktrees" / "note-bubble-02"
        self.git(self.repo, "worktree", "add", "-q", str(note_tree), "-b", "note/bubble/02", "feature/bubble")
        self.write(note_tree, "half.ts", "// half a build\n")
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="running"))
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.commands(out)
        self.assertFalse(note_tree.exists(), "the printed command removes a tree with work in it")
        self.assertTrue(self.args()["notes"][1]["fresh"])

    def test_held_is_true_only_while_nothing_but_the_plan_and_the_report_changed(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="held", s01="merged abc1234", s02="merged def5678"))
        self.commit("report: bubble held")
        self.assertTrue(self.args()["held"])
        self.rule(self.RULINGS.replace("  Undo:", "  Confirmed: 2026-11-13\n  Undo:"))
        self.commit("rulings: answered")
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="held", s01="merged abc1234", s02="merged def5678") + "\nroles\n")
        self.commit("report: bubble roles")
        self.assertTrue(self.args()["held"], "the answers and the roles cells change no code")
        self.write(self.tree, "src/a.ts", "export const a = 2;\n")
        self.commit("fix")
        self.assertFalse(self.args()["held"], "code changed since the final check passed")

    def test_held_is_false_when_a_note_is_to_be_built(self):
        # Review finding 3: a row back at `not started` kept the old final check standing.
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="held", s01="merged abc1234", s02="merged def5678"))
        self.commit("report: bubble held")
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="held", s01="merged abc1234", s02="not started"))
        self.commit("report: note 02 again")
        self.assertFalse(self.args()["held"], "a note to build is new code, and new code takes a final check")

    def test_args_refuses_rulings_that_do_not_hold(self):
        # Review finding 5: the gate was computed with no fault check.
        self.rule(self.RULINGS.replace(", default, ", ", Default, "))
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("`Default` is not `default`, `panel` or `Sam`", out)

    def test_args_refuses_a_product_whose_hooks_miss_the_one_that_holds_a_fast_forward(self):
        hooks = self.repo / ".githooks"
        hooks.mkdir()
        (hooks / "pre-merge-commit").write_text("#!/bin/sh\n")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("has no `reference-transaction` hook", out)
        # Review 2, N9: a file git may not execute, and a hooks path nobody set, both passed.
        (hooks / "reference-transaction").write_text("#!/bin/sh\n")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("is not executable, so git does not run it", out)
        (hooks / "reference-transaction").chmod(0o755)
        self.git(self.repo, "config", "core.hooksPath", "elsewhere")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("`sh .githooks/prepare`", out)
        self.assertIn("core.hooksPath is `elsewhere`", out)
        self.git(self.repo, "config", "core.hooksPath", ".githooks")
        self.assertEqual(self.run_main("args", "bubble", "--tree", str(self.tree))[0], 0)

    def test_args_refuses_a_correction_the_plan_does_not_record(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="held", s01="merged abc1234", s02="merged def5678")
                   + "\n## Decide\n\n01: [correction] Corrected: the rights test\n")
        code, out = self.run_main("args", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 3, out)
        self.assertIn("note 01: the note checker corrected it", out)

    def test_args_keeps_the_decide_lines_and_the_final_row(self):
        # Review finding 11: a waiting note lost its typed line at the next start.
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="waiting: money: may a manager refund")
                   .replace("\n## Tooling stops", "| final | waiting: money: may the fix round the price | | | |\n\n## Tooling stops")
                   + "\n## Decide\n\n02: [money] may a manager refund Default: yes, up to 50\n")
        got = self.args()
        self.assertEqual(got["earlier"]["decide"], ["02: [money] may a manager refund Default: yes, up to 50"])
        self.assertEqual(got["final"], "waiting: money: may the fix round the price")
        self.assertEqual([n["number"] for n in got["notes"]], ["01", "02"])
        self.assertEqual(got["notes"][1]["state"], "waiting: money: may a manager refund")

    def test_a_final_row_that_restarts_by_itself_is_not_passed_on(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="merged def5678")
                   .replace("\n## Tooling stops", "| final | stopped: tooling: hook: REFUSED | | | |\n\n## Tooling stops"))
        self.assertEqual(self.args()["final"], "")

    # ── the bound on automatic restarts ──

    def start(self, clock, state="stopped", **states):
        rows = {number.lstrip("n"): {"State": row} for number, row in states.items()}
        mod.count_start(pathlib.Path(self.tmp.name) / "records", rows, clock, state)

    def test_a_final_check_no_run_finishes_has_three_starts_too(self):
        # Review 2, N8: every note merged and no `final` row: eight starts over eight days passed.
        done = {"n01": "merged abc1234", "n02": "cut 2026-11-12"}
        for day in range(3):
            self.start(day * 86400, **done)
        with self.assertRaises(mod.Refusal) as refused:
            self.start(3 * 86400, **done)
        self.assertIn("the final check, which an earlier run did not finish", str(refused.exception))
        self.assertIn("`--note final`", str(refused.exception))
        with self.assertRaises(mod.Refusal):
            self.start(4 * 86400, state="running", **done)
        # It waits for him, and his ruling starts the count again.
        self.start(5 * 86400, final="waiting: tooling: the final check did not finish", **done)
        for day in range(6, 9):
            self.start(day * 86400, final="ruled 2026-11-12", **done)
        # Review 3, note 7: a `ruled` row was exempt, so six daily starts on it all passed.
        with self.assertRaises(mod.Refusal) as refused:
            self.start(9 * 86400, final="ruled 2026-11-12", **done)
        self.assertIn("the final check, which an earlier run did not finish", str(refused.exception))
        # A new ruling changes the row, and the count starts again: three more, never a fourth.
        for day in range(10, 13):
            self.start(day * 86400, final="ruled 2026-11-20", **done)
        with self.assertRaises(mod.Refusal):
            self.start(13 * 86400, final="ruled 2026-11-20", **done)

    def test_a_held_or_merged_feature_is_no_restart(self):
        for state in ("held", "merged"):
            for _ in range(5):
                self.start(0, state=state, n01="merged abc1234", n02="merged def5678")

    def test_three_automatic_restarts_with_no_new_merge_then_no_more(self):
        # Review finding 12: nothing bounded the restarts after a tool fault.
        self.assertEqual(mod.MAX_STARTS_WITHOUT_MERGE, 3)
        self.start(0, n01="not started", n02="not started")
        for _ in range(3):
            self.start(10, n01="stopped: tooling: hook: REFUSED", n02="not started")
        with self.assertRaises(mod.Refusal) as refused:
            self.start(20, n01="stopped: tooling: hook: REFUSED", n02="not started")
        self.assertIn("3 automatic restarts in a row merged no new note", str(refused.exception))
        with self.assertRaises(mod.Refusal):
            self.start(30, n01="running", n02="not started")
        self.start(40, n01="waiting: tooling: hook: REFUSED", n02="not started")  # it waits for him: the streak ends
        self.start(50, n01="waiting: tooling: hook: REFUSED", n02="stopped: worktree: classifier denied")

    def test_a_newly_merged_note_starts_the_count_again(self):
        for _ in range(3):
            self.start(0, n01="stopped: tooling: hook: REFUSED", n02="not started")
        self.start(0, n01="stopped: tooling: hook: REFUSED", n02="merged abc1234")
        self.start(0, n01="stopped: tooling: hook: REFUSED", n02="merged abc1234")

    def test_an_outage_is_bounded_by_days_not_by_three_starts(self):
        for hour in range(10):
            self.start(hour * 3600, n01="stopped: API errors", n02="not started")
        self.start(mod.MAX_OUTAGE_SECONDS, n01="stopped: implementer returned no result", n02="not started")
        with self.assertRaises(mod.Refusal) as refused:
            self.start(mod.MAX_OUTAGE_SECONDS + 1, n01="stopped: API errors", n02="not started")
        self.assertIn("3 days", str(refused.exception))

    def test_the_args_command_counts_its_starts(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="stopped: tooling: hook: REFUSED"))
        codes = [self.run_main("args", "bubble", "--tree", str(self.tree))[0] for _ in range(4)]
        self.assertEqual(codes, [0, 0, 0, 3])

    def test_the_args_command_counts_the_starts_of_a_final_check_with_no_row(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="merged def5678"))
        codes = [self.run_main("args", "bubble", "--tree", str(self.tree))[0] for _ in range(4)]
        self.assertEqual(codes, [0, 0, 0, 3])

    # ── the typed stops, from the agents' transcripts ──

    def transcript(self, run, name, role, label, answer):
        (run / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": f"workflow:build-feature-{role}",
                                                                 "description": label}))
        call = {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "done"}, {"type": "tool_use", "name": "StructuredOutput", "input": answer}]}}
        (run / f"agent-{name}.jsonl").write_text(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n"
                                                + json.dumps(call) + "\n")

    def test_roles_records_each_typed_stop_with_the_class_the_agent_typed(self):
        # Review finding 4: the class of a stop was the session's to choose.
        run = pathlib.Path(self.tmp.name) / "wf" / "wf_1"
        run.mkdir(parents=True)
        stop = {"kind": "question", "class": "money", "question": "may a manager\nrefund | without the owner", "default": "yes"}
        self.transcript(run, "a1", "implementer", "note 02: implementer 1", {"outcome": "stopped", "stop": stop})
        self.transcript(run, "a2", "implementer", "note 01: implementer 1", {"outcome": "built", "stop": {"kind": "none"}})
        self.transcript(run, "a3", "implementer", "fix round 1: implementer", {"stop": {**stop, "class": ""}})
        self.transcript(run, "a4", "implementer", "note 01: implementer 2", {"stop": {**stop, "class": "payments"}})
        self.transcript(run, "a5", "note-checker", "note 01: note checker", {"outcome": "stopped", "line": "the note is wrong", "stop": {"kind": "none"}})
        self.transcript(run, "a6", "verifier", "note 01: verifier 1", {"verdict": "REJECT", "stop": {"kind": "tooling", "tool": "hook", "question": "REFUSED"}})
        got = {s["agent"]: (s["note"], s["class"], s["question"]) for s in mod.typed_stops(run.parent)}
        self.assertEqual(got, {
            "agent-a1": ("02", "money", "may a manager refund without the owner"),
            "agent-a3": ("final", "unclassified", "may a manager refund without the owner"),
            "agent-a4": ("01", "unclassified", "may a manager refund without the owner"),
            "agent-a5": ("01", "unclassified", "the note is wrong"),
        })
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="stopped: may a manager refund without the owner"))
        report = str(self.tree / "changes" / "bubble" / "report.md")
        code, out = self.run_main("roles", str(run.parent), "--report", report)
        self.assertEqual(code, 0, out)
        self.assertIn("stops: 4 typed stop(s) added to", out)
        self.assertIn("stops: 0 typed stop(s) added to", self.run_main("roles", str(run.parent), "--report", report)[1])
        import rulings
        feature = rulings.Feature(str(self.tree), "bubble")
        self.assertTrue(str(feature.records()).endswith("/product/.git/build-feature/bubble"))
        self.assertEqual(feature.stop_class("02", "may a manager refund  without the owner"), "money")
        self.assertEqual(feature.stop_class("02", "another question"), "unclassified")
        self.assertEqual(feature.stop_class("final", "may a manager refund without the owner"), "unclassified")

    def test_held_is_false_for_any_other_state(self):
        self.write(self.tree, "changes/bubble/report.md",
                   self.REPORT.format(state="stopped", s01="merged abc1234", s02="merged def5678"))
        self.commit("report: bubble stopped")
        self.assertFalse(self.args()["held"])

    def test_args_reads_the_staging_line(self):
        self.write(self.tree, "CLAUDE.md", "# P\n\nStaging: https://staging.example.test\n")
        self.assertEqual(self.args()["staging"], "https://staging.example.test")

    # ── roles ──

    def test_roles_fills_tokens_and_cost_per_role(self):
        transcripts = pathlib.Path(self.tmp.name) / "wf"
        run = transcripts / "wf_1"
        run.mkdir(parents=True)

        def agent(name, role, rows):
            (run / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": role}))
            lines = []
            for mid, model, usage in rows:
                lines.append(json.dumps({"type": "assistant", "uuid": mid + "-u",
                                         "message": {"id": mid, "model": model, "usage": usage}}))
            lines.append(json.dumps({"type": "user", "message": {"content": "x"}}))
            (run / f"agent-{name}.jsonl").write_text("\n".join(lines) + "\n")

        usage = {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0,
                 "output_tokens": 100}
        agent("a1", "build-feature-implementer", [("m1", "claude-sonnet-5-5", usage),
                                                  ("m1", "claude-sonnet-5-5", usage),  # a repeated row
                                                  ("m2", "claude-sonnet-5-5", usage)])
        # The workflow names its agents with the plugin's prefix; older transcripts have none.
        agent("a2", "workflow:build-feature-reviewer", [("m3", "claude-opus-5-5", usage)])
        agent("a3", "Explore", [("m4", "claude-haiku-5-5", usage)])
        agent("a4", "workflow:parallel-hunt-fixer", [("m5", "claude-haiku-5-5", usage)])
        report = pathlib.Path(self.tmp.name) / "report.md"
        report.write_text(textwrap.dedent("""\
            # R

            ## Roles

            | Role | Model | Effort | Tokens | Cost | Strikes |
            | --- | --- | --- | --- | --- | --- |
            | implementer | sonnet | high | | | 0 |
            | reviewer | opus | high | | | 1 |
            | verifier | sonnet | high | | | 0 |

            ## Time

            | Note | State |
            | --- | --- |
            | 01 | merged |
        """))
        code, out = self.run_main("roles", str(transcripts), "--report", str(report))
        self.assertEqual(code, 0, out)
        self.assertIn("roles: 2 row(s) filled", out)
        text = report.read_text()
        self.assertIn("| implementer | sonnet | high | 2,220 | $", text)
        self.assertIn("| reviewer | opus | high | 1,110 | $", text)
        self.assertIn("| verifier | sonnet | high | | | 0 |", text)
        self.assertIn("| 01 | merged |", text)
        totals = mod.role_totals(transcripts)
        self.assertNotIn("Explore", totals)
        self.assertGreater(totals["reviewer"]["cost"], totals["implementer"]["cost"] / 2)
        self.assertFalse(totals["implementer"]["unpriced"])

    def test_roles_refuses_missing_paths(self):
        code, out = self.run_main("roles", str(self.repo / "nowhere"), "--report", str(self.repo / "README.md"))
        self.assertEqual(code, 3)
        self.assertIn("transcript dir", out)


if __name__ == "__main__":
    unittest.main()
