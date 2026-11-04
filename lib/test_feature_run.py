"""Tests for feature_run.py: the workflow's args and the report's role cells."""

import contextlib
import datetime
import io
import json
import os
import pathlib
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
        self.assertEqual(self.args()["earlier"], {"defaults": [], "edits": [], "final": [], "strikes": {}})

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
        agent("a2", "build-feature-reviewer", [("m3", "claude-opus-5-5", usage)])
        agent("a3", "Explore", [("m4", "claude-haiku-5-5", usage)])
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
