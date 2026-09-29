#!/usr/bin/env python3
"""Drill for run-issues-suite-gate.py.

Issue 18 of the tracker-tooling set, `the runner runs only
its own three suites`, fix F5 of the 2026-09-23 audit. Issue 19, `the
implementer briefs name the wrapper`, adds the cases that read the two briefs.

    python3 test_run_issues_suite_gate.py
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_issues_suite_gate", os.path.join(HERE, "run-issues-suite-gate.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TREE = "/Users/x/code/p/.claude/worktrees/run-issues-batch-abc123"
MAIN = "/Users/x/code/p"
WRAPPER = "python3 ~/.claude/skills/run-issues/run_suite.py"

# (tree a live run owns, the stage its ledger's State line names)
BEFORE_FINALE = ((TREE, None),)
IN_FINALE = ((TREE, "finale-mechanical"),)

# Standard first, escalated second: the cases below index them.
IMPLEMENTERS_BY_NAME = ("run-issues-implementer", "run-issues-implementer-escalated")


def runner(command, cwd=TREE, runs=BEFORE_FINALE):
    """The main session, which inside a live run's tree is the runner."""
    return mod.decide("", command, cwd, runs)


class TheRunnersRawSuite(unittest.TestCase):
    """Criteria 1 and 2."""

    def test_npm_test_in_a_live_runs_tree_is_refused_and_names_the_wrapper(self):
        reason = runner("npm test")
        self.assertIsNotNone(reason)
        self.assertIn("run_suite.py", reason)

    def test_a_cd_into_the_tree_is_followed(self):
        self.assertIsNotNone(runner(f"cd {TREE} && npx vitest run", cwd=MAIN))

    def test_a_cd_out_of_the_tree_is_followed(self):
        self.assertIsNone(runner(f"cd {MAIN} && npm test"))

    def test_every_spelling_of_the_whole_suite_is_refused(self):
        for command in ("npm test", "npm run test", "npm t", "pnpm test",
                        "yarn test", "npx vitest run", "npx vitest", "vitest run",
                        "node_modules/.bin/vitest run",
                        "npx vitest run > /tmp/suite.log 2>&1",
                        "rm -rf .vitest-cache && npm test 2>&1 | tail -20",
                        "FOO=1 npx vitest run --maxWorkers=2",
                        "npx vitest run --coverage --coverage.reporter=json",
                        "python3 ~/.claude/skills/run-issues/run_step.py --batch b "
                        "--kind suite --label s -- npm test"):
            with self.subTest(command=command):
                self.assertIsNotNone(runner(command))


class OnlyALaunchIsJudged(unittest.TestCase):
    """Review findings 1, 2 and 4 of 2026-09-23. A word is judged where a shell
    would RUN it, not wherever it appears."""

    def test_a_command_that_only_names_the_suite_passes(self):
        for command in ("npm ls vitest", "npm install -D vitest",
                        "grep -n vitest package.json",
                        "ls node_modules/.bin/vitest", "echo npm test",
                        "git log -- vitest",
                        "sed -n 1,40p ~/.claude/skills/run-issues/run_suite.py",
                        "git diff -- run-issues/run_suite.py"):
            for agent in ("", "run-issues-implementer"):
                with self.subTest(command=command, agent=agent):
                    self.assertIsNone(mod.decide(agent, command, TREE,
                                                 BEFORE_FINALE))

    def test_every_launcher_in_front_of_the_suite_is_seen_through(self):
        for command in ("timeout 600 npx vitest run", "npx --yes vitest run",
                        "pnpm exec vitest run", "npm exec vitest", "yarn vitest",
                        "node node_modules/.bin/vitest run", "time npm test",
                        "env CI=1 npm test", "nohup npm test",
                        "bash -c 'rm -rf .vitest-cache && npm test'",
                        'sh -c "cd tests && npx vitest run"',
                        "eval npm test"):
            with self.subTest(command=command):
                self.assertIsNotNone(runner(command))

    def test_a_launcher_options_value_is_skipped_with_it(self):
        """Tracker-tooling issue 31. Run `batch-46e4de` issued about 40
        `env -u DATABASE_URL ...` suites, and the gate read `DATABASE_URL` as
        the command."""
        for command in ("env -u DATABASE_URL npm test",
                        "env -u DATABASE_URL -u DIRECT_URL npx vitest run",
                        "env --unset DATABASE_URL CI=1 npm test",
                        "env -i -P /usr/bin npm test",
                        "timeout -s KILL 600 npm test",
                        "timeout --signal KILL -k 10 600 npx vitest run",
                        "nohup env -u DATABASE_URL timeout -s TERM 600 npm test",
                        "env -iu DATABASE_URL npm test",
                        "env -uS npm test",
                        "caffeinate -i -t 3600 npm test",
                        "npx -p typescript vitest run",
                        "node -r ts-node/register node_modules/.bin/vitest run"):
            for agent in ("", "run-issues-implementer"):
                with self.subTest(command=command, agent=agent):
                    self.assertIsNotNone(mod.decide(agent, command, TREE,
                                                    BEFORE_FINALE))

    def test_env_split_string_is_read_as_the_command(self):
        for command in ("env -S 'npm test'", "env -S'npx vitest run'",
                        "env --split-string='npm test'",
                        "env --split-string 'npm test'",
                        "env -iS'npm test'", "env -iS 'npm test'",
                        "env -u DATABASE_URL -S 'npm run test'"):
            with self.subTest(command=command):
                self.assertIsNotNone(runner(command))

    def test_a_launcher_with_a_value_that_runs_no_suite_passes(self):
        for command in ("env -u DATABASE_URL grep -n vitest package.json",
                        "timeout -s KILL 5 npm ls vitest",
                        "env -u DATABASE_URL npx vitest run tests/a.test.ts",
                        "env -S 'echo npm test'",
                        "caffeinate -w 123 grep vitest package.json"):
            for agent in ("", "run-issues-implementer"):
                with self.subTest(command=command, agent=agent):
                    self.assertIsNone(mod.decide(agent, command, TREE,
                                                 BEFORE_FINALE))

    def test_a_shell_keyword_in_front_is_seen_through(self):
        """Run `batch-2957c3`'s runner ran `for n in B C; do npm test ...`."""
        for command in ("for n in B C; do npm test > /tmp/s$n.log 2>&1; done",
                        "if true; then npx vitest run; fi",
                        "while false; do :; done; ! npm test",
                        "{ npm test; }"):
            with self.subTest(command=command):
                self.assertIsNotNone(runner(command))

    def test_an_unclosed_quote_still_splits_on_operators(self):
        """The audit's own rows are cut at 230 characters, mid-quote."""
        self.assertIsNotNone(runner(
            'rm -rf node_modules/.vite; npm test > /tmp/s.log 2>&1; echo "EXIT'))


class SubshellsAndNesting(unittest.TestCase):
    """Review findings 3 and 5 of 2026-09-23."""

    def test_a_cd_inside_a_subshell_ends_with_it(self):
        self.assertIsNotNone(runner("(cd /tmp && ls); npm test"))
        self.assertIsNone(runner(f"(cd {TREE}); npm test", cwd=MAIN))
        self.assertIsNotNone(runner(f"(cd {TREE} && npm test)", cwd=MAIN))

    def test_the_deepest_run_tree_is_the_owner(self):
        runs = ((MAIN, "finale-mechanical"), (TREE, None))
        self.assertIsNone(runner(f"{WRAPPER} --stage baseline -- npm test",
                                 runs=runs))
        self.assertIsNotNone(runner(f"{WRAPPER} --stage finale -- npm test",
                                    runs=runs))


class TheRunnersThreeStages(unittest.TestCase):
    """Criteria 3 and 4. Issue 06's rule names three runner readings: the
    baseline, the re-run after a correction round, and the finale."""

    def wrapped(self, stage, runs=BEFORE_FINALE):
        return runner(f"{WRAPPER} --stage {stage} -- npm test", runs=runs)

    def test_baseline_and_correction_pass_before_the_finale(self):
        self.assertIsNone(self.wrapped("baseline"))
        self.assertIsNone(self.wrapped("correction"))

    def test_the_equals_spelling_is_read_the_same(self):
        self.assertIsNone(runner(f"{WRAPPER} --stage=baseline -- npm test"))

    def test_issue_is_never_the_runners(self):
        reason = self.wrapped("issue")
        self.assertIsNotNone(reason)
        self.assertIn("verify gate", reason)

    def test_a_wrapper_call_with_no_stage_is_refused(self):
        self.assertIsNotNone(runner(f"{WRAPPER} -- npm test"))

    def test_finale_is_refused_until_the_ledger_names_a_finale_stage(self):
        self.assertIsNotNone(self.wrapped("finale"))
        self.assertIsNone(self.wrapped("finale", runs=IN_FINALE))
        self.assertIsNone(self.wrapped("finale",
                                       runs=((TREE, "awaiting-merge"),)))

    def test_baseline_and_correction_are_refused_inside_the_finale(self):
        self.assertIsNotNone(self.wrapped("baseline", runs=IN_FINALE))
        self.assertIsNotNone(self.wrapped("correction", runs=IN_FINALE))

    def test_the_finale_keeps_its_step_clock(self):
        """`finale.md` step 1 runs the suite under `run_step.py`."""
        command = ("python3 ~/.claude/skills/run-issues/run_step.py --batch b "
                   f"--kind suite --label s -- {WRAPPER} --stage finale -- npm test")
        self.assertIsNone(runner(command, runs=IN_FINALE))


class AScopedRun(unittest.TestCase):
    """Criterion 5. A scoped run is the gates' evidence and nobody's waste."""

    def test_a_file_or_directory_argument_narrows_the_run(self):
        for command in ("npx vitest run tests/a.test.ts",
                        "npm test -- tests/alerts/",
                        "npx vitest run src/lib/push/deliver.test.ts --maxWorkers=2",
                        "npx vitest run --reporter dot tests/a.test.ts",
                        "npm run test -- a.test.ts"):
            with self.subTest(command=command):
                self.assertIsNone(runner(command))

    def test_a_name_filter_or_an_option_value_does_not_narrow_it(self):
        for command in ('npx vitest run -t "tests/a.test.ts"',
                        "npx vitest run --config vitest.conformance.config.ts",
                        "npx vitest run --coverage.include src/lib/**",
                        "npx vitest run alerts"):
            with self.subTest(command=command):
                self.assertIsNotNone(runner(command))


class TheImplementers(unittest.TestCase):
    """Criterion 6. F4's "agents run the suite only through it", made a refusal."""

    def test_a_raw_whole_suite_is_refused(self):
        for agent in mod.IMPLEMENTERS:
            with self.subTest(agent=agent):
                reason = mod.decide(agent, "npm test", "/anywhere", ())
                self.assertIsNotNone(reason)
                self.assertIn("--stage issue", reason)

    def test_the_wrapper_at_issue_passes_and_at_any_other_stage_does_not(self):
        agent = "run-issues-implementer"
        self.assertIsNone(mod.decide(
            agent, f"{WRAPPER} --stage issue -- npm test", TREE, ()))
        for stage in ("finale", "baseline", "correction"):
            with self.subTest(stage=stage):
                self.assertIsNotNone(mod.decide(
                    agent, f"{WRAPPER} --stage {stage} -- npm test", TREE, ()))

    def test_a_scoped_run_passes(self):
        self.assertIsNone(mod.decide("run-issues-implementer",
                                     "npx vitest run tests/a.test.ts", TREE, ()))


class EveryoneElse(unittest.TestCase):
    """Criteria 7 and 8."""

    def test_the_review_gates_pass(self):
        for gate in ("run-issues-review-gate", "run-issues-review-gate-critical"):
            with self.subTest(gate=gate):
                self.assertIsNone(mod.decide(gate, "npx vitest run", TREE,
                                             BEFORE_FINALE))


class TheVerifyGate(unittest.TestCase):
    """The perf audit of 2026-09-28, fix 2. The verify gate's suite goes
    through the wrapper at stage `verify`, which reuses the implementer's
    record for the same tree. A bare `npx vitest run --coverage` in its copy
    reads that tree a second time and keeps nothing (221's verify a1)."""

    GATE = "run-issues-verify-gate"

    def test_a_raw_whole_suite_is_refused_and_names_the_verify_stage(self):
        command = ("npx vitest run --coverage.enabled --coverage.provider=v8 "
                   "--coverage.reporter=json --coverage.reportOnFailure=true")
        reason = mod.decide(self.GATE, command, TREE, BEFORE_FINALE)
        self.assertIsNotNone(reason)
        self.assertIn("--stage verify", reason)

    def test_the_wrapper_at_verify_passes_and_at_any_other_stage_does_not(self):
        self.assertIsNone(mod.decide(
            self.GATE, f"{WRAPPER} --stage verify -- npm test", TREE, ()))
        for stage in ("issue", "baseline", "correction", "finale"):
            with self.subTest(stage=stage):
                reason = mod.decide(
                    self.GATE, f"{WRAPPER} --stage {stage} -- npm test", TREE, ())
                self.assertIn("--stage verify", reason)

    def test_a_named_file_passes(self):
        self.assertIsNone(mod.decide(
            self.GATE, "npx vitest run tests/a.test.ts", TREE, ()))

    def test_the_main_session_outside_every_live_run_passes(self):
        self.assertIsNone(runner("npm test", cwd=MAIN))
        self.assertIsNone(runner("npm test", runs=()))

    def test_a_sibling_tree_sharing_a_name_prefix_is_not_the_run(self):
        self.assertIsNone(runner("npm test", cwd=TREE + "-old"))


class TheHookAsRegistered(unittest.TestCase):
    """Criteria 9 and 10, and the live-ledger read, driven through `main()`."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = os.path.realpath(os.path.join(self.scratch.name, "repo"))
        os.makedirs(self.repo)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.ledger = os.path.join(self.repo, ".scratch", "feat", "runs",
                                   "batch-abc123", "run.md")
        os.makedirs(os.path.dirname(self.ledger))
        self.write_ledger("")

    def tearDown(self):
        self.scratch.cleanup()

    def write_ledger(self, state_line):
        with open(self.ledger, "w") as handle:
            handle.write("# Run `batch-abc123`\n\n"
                         "Owner: run-issues-batch-abc123\n"
                         f"Worktree: `{self.repo}`\n{state_line}\n")

    def hook(self, command, cwd=None, agent_type=None, raw=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command},
                   "cwd": cwd or self.repo}
        if agent_type:
            payload["agent_type"] = agent_type
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "run-issues-suite-gate.py")],
            input=raw if raw is not None else json.dumps(payload),
            capture_output=True, text=True)

    def test_the_runners_raw_suite_in_a_live_run_is_refused(self):
        done = self.hook("npm test")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("run_suite.py", done.stderr)

    def test_the_finale_passes_once_the_ledger_names_it(self):
        command = f"{WRAPPER} --stage finale -- npm test"
        self.assertEqual(self.hook(command).returncode, 2)
        self.write_ledger("State: **`finale-mechanical`**, from 14:02")
        done = self.hook(command)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_finished_run_holds_nothing(self):
        with open(self.ledger, "w") as handle:
            handle.write("# Run `batch-abc123`\n\nOwner: none — merged\n"
                         f"Worktree: `{self.repo}`\n")
        self.assertEqual(self.hook("npm test").returncode, 0)

    def test_an_unreadable_payload_passes_and_says_so(self):
        done = self.hook("", raw="{not json")
        self.assertEqual(done.returncode, 0)
        self.assertIn("unchecked", done.stderr)

    def test_a_ledger_read_that_fails_passes_and_says_so(self):
        outside = os.path.join(self.scratch.name, "not-a-repo")
        os.makedirs(outside)
        done = self.hook("npm test", cwd=outside)
        self.assertEqual(done.returncode, 0)
        self.assertIn("unchecked", done.stderr)

    def test_a_command_that_launches_no_suite_reads_no_ledger(self):
        outside = os.path.join(self.scratch.name, "not-a-repo")
        os.makedirs(outside)
        done = self.hook("python3 test_something.py", cwd=outside)
        self.assertEqual((done.returncode, done.stderr), (0, ""))

    def test_it_is_registered_on_bash(self):
        path = os.path.join(HERE, "..", "settings.json")
        if not os.path.isfile(path):
            # Installed, this drill sits in `~/.claude/hooks` and the settings
            # file is its neighbour. In a copy of the pack there is none.
            self.skipTest("no settings.json beside this hooks directory, so "
                          "this copy is not installed")
        with open(path) as handle:
            settings = json.load(handle)
        commands = [hook.get("command", "")
                    for entry in settings["hooks"]["PreToolUse"]
                    if entry.get("matcher") == "Bash"
                    for hook in entry.get("hooks", [])]
        self.assertTrue(any(c.endswith("/hooks/run-issues-suite-gate.py")
                            for c in commands), commands)

    def test_the_finale_stages_are_check_finale_stages_own(self):
        path = os.path.join(HERE, "..", "skills", "run-issues",
                            "check_finale_stage.py")
        stages = importlib.util.spec_from_file_location("check_finale_stage", path)
        chain = importlib.util.module_from_spec(stages)
        stages.loader.exec_module(chain)
        self.assertEqual(tuple(chain.CHAIN), mod.FINALE_STAGES)


# Where the hook under test finds `issue_level.py`. The walker,
# `lib/run_python_suites.py`, names the skills tree it was handed; run alone,
# the `skills/run-issues` directory beside this hooks directory.
SKILL_DIR_ENV = "RUN_ISSUES_SKILL_DIR"


class TheLightLevel(unittest.TestCase):
    """Tracker-tooling issue 40, AC1, AC2 and AC6, driven through `main()` as
    `TheHookAsRegistered` drives it. A `Level: light` issue's implementer runs
    the tests of the files it touched; the finale runs the one whole suite."""

    WRAPPED = f"{WRAPPER} --stage issue -- npm test"
    SCOPED = "npx vitest run src/lib/orders.test.ts"

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = os.path.realpath(os.path.join(self.scratch.name, "repo"))
        os.makedirs(self.repo)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.ledger = os.path.join(self.repo, ".scratch", "feat", "runs",
                                   "batch-abc123", "run.md")
        os.makedirs(os.path.dirname(self.ledger))
        self.risk(self.repo)
        self.write_ledger(self.repo)

    def tearDown(self):
        self.scratch.cleanup()

    def risk(self, tree):
        path = os.path.join(tree, "docs", "agents", "risk-paths.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("No risk paths: a fixture.\n")

    def write_ledger(self, worktree, status="in-progress"):
        with open(self.ledger, "w") as handle:
            handle.write("# Run `batch-abc123`\n\n"
                         "Owner: run-issues-batch-abc123\n"
                         f"Worktree: `{worktree}`\n\n## Status\n\n"
                         "| Issue | Size | Status | Stamps |\n|---|---|---|---|\n"
                         "| 11 | S | done | attempt 1 |\n"
                         f"| 12 | S | {status} | attempt 1 |\n")

    def issue(self, level_line, tree=None):
        path = os.path.join(tree or self.repo, ".scratch", "feat", "issues",
                            "12-x.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write((level_line + "\n" if level_line else "") + "# 12\n")

    def hook(self, command, cwd=None, agent_type="run-issues-implementer"):
        payload = {"tool_name": "Bash", "tool_input": {"command": command},
                   "cwd": cwd or self.repo, "agent_type": agent_type}
        env = dict(os.environ)
        env.setdefault(SKILL_DIR_ENV, os.path.join(HERE, "..", "skills",
                                                   "run-issues"))
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "run-issues-suite-gate.py")],
            input=json.dumps(payload), capture_output=True, text=True, env=env)

    def test_a_light_issues_implementer_is_refused_the_wrapper(self):
        """AC1, for both roles in `IMPLEMENTERS`."""
        self.issue("Level: light")
        for agent in mod.IMPLEMENTERS:
            with self.subTest(agent=agent):
                done = self.hook(self.WRAPPED, agent_type=agent)
                self.assertEqual(done.returncode, 2, done.stderr)
                self.assertIn("Level: light", done.stderr)
                self.assertIn("finale", done.stderr)
                self.assertNotIn("run_suite.py", done.stderr)
                self.assertNotIn("--stage issue", done.stderr)

    def test_a_light_issues_raw_suite_is_refused_without_naming_the_wrapper(self):
        self.issue("Level: light")
        done = self.hook("npm test")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("Level: light", done.stderr)
        self.assertNotIn("run_suite.py", done.stderr)

    def test_a_light_issues_refusal_names_the_scoped_suite(self):
        """The perf audit of 2026-09-28, fix 4."""
        self.issue("Level: light")
        done = self.hook("npm test")
        self.assertIn("scoped_suite.py", done.stderr)

    def test_a_light_issues_scoped_suite_passes(self):
        self.issue("Level: light")
        done = self.hook("python3 ~/.claude/skills/run-issues/scoped_suite.py")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_light_issues_touched_file_run_passes(self):
        """AC1."""
        self.issue("Level: light")
        done = self.hook(self.SCOPED)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_full_issues_implementer_keeps_the_wrapper(self):
        """AC2."""
        self.issue("Level: full")
        done = self.hook(self.WRAPPED)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_anything_but_level_light_is_full(self):
        """AC6: no line, another word, and no file, which says so on stderr."""
        for line in (None, "Level: medium"):
            with self.subTest(line=line):
                self.issue(line)
                done = self.hook(self.WRAPPED)
                self.assertEqual(done.returncode, 0, done.stderr)
        os.remove(os.path.join(self.repo, ".scratch", "feat", "issues", "12-x.md"))
        done = self.hook(self.WRAPPED)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no issue file", done.stderr)
        self.assertIn("12-*.md", done.stderr)

    def test_a_lift_to_full_between_two_calls_is_read(self):
        """Must still be true: the level is never cached."""
        self.issue("Level: light")
        self.assertEqual(self.hook(self.WRAPPED).returncode, 2)
        self.issue("Level: full")
        done = self.hook(self.WRAPPED)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_level_is_read_in_the_tree_the_worktree_line_names(self):
        """Seam pass h0925: never the copy beside the ledger."""
        subprocess.run(["git", "-C", self.repo, "commit", "-q", "--allow-empty",
                        "-m", "root"], check=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME="t",
                                GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                                GIT_COMMITTER_EMAIL="t@t"))
        tree = os.path.realpath(os.path.join(self.scratch.name, "tree"))
        subprocess.run(["git", "-C", self.repo, "worktree", "add", "-q", tree],
                       check=True)
        self.risk(tree)
        self.write_ledger(tree)
        self.issue("Level: light")
        self.issue("Level: full", tree=tree)
        done = self.hook(self.WRAPPED, cwd=tree)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.issue("Level: light", tree=tree)
        self.issue("Level: full")
        self.assertEqual(self.hook(self.WRAPPED, cwd=tree).returncode, 2)

    def test_the_runner_is_not_judged_by_the_level(self):
        self.issue("Level: light")
        done = self.hook(f"{WRAPPER} --stage baseline -- npm test",
                         agent_type=None)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_decide_holds_the_light_refusal_for_both_roles(self):
        for agent in mod.IMPLEMENTERS:
            with self.subTest(agent=agent):
                self.assertIsNotNone(mod.decide(
                    agent, self.WRAPPED, TREE, (), level_of=lambda _: "light"))
                self.assertIsNone(mod.decide(
                    agent, self.SCOPED, TREE, (), level_of=lambda _: "light"))
                self.assertIsNone(mod.decide(agent, self.WRAPPED, TREE, ()))


class TheVerifyGateBrief(unittest.TestCase):
    """The perf audit of 2026-09-28, fixes 1 and 2. The brief names the one
    copy recipe and the wrapper at `verify`, and no command it states is one
    the gate refuses."""

    BRIEF = os.path.join(HERE, "..", "agents", "run-issues-verify-gate.md")

    def test_it_makes_its_copy_with_make_copy_and_runs_the_wrapper_at_verify(self):
        with open(self.BRIEF, encoding="utf-8") as handle:
            text = " ".join(handle.read().split())
        self.assertIn("make_copy.py", text)
        self.assertIn("run_suite.py --stage verify", text)

    def test_no_command_it_states_is_refused(self):
        with open(self.BRIEF, encoding="utf-8") as handle:
            text = handle.read()
        fenced = [line for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
                  for line in block.splitlines()]
        spans = re.findall(r"`([^`]+)`", re.sub(r"```.*?```", "", text, flags=re.S))
        self.assertTrue(fenced, "no fenced command read; the case is empty")
        for span in spans + fenced:
            span = " ".join(span.split())
            with self.subTest(span=span):
                self.assertIsNone(mod.decide(TheVerifyGate.GATE, span, TREE, ()))


class TheImplementerBriefs(unittest.TestCase):
    """Issue 19. The briefs name the road the gate leaves open, so an
    implementer meets the wrapper before it meets the refusal."""

    BRIEFS = [os.path.join(HERE, "..", "agents", name + ".md")
              for name in IMPLEMENTERS_BY_NAME]

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return " ".join(handle.read().split())

    def test_both_briefs_run_the_whole_suite_through_the_wrapper(self):
        for path in self.BRIEFS:
            with self.subTest(brief=os.path.basename(path)):
                self.assertIn("run_suite.py --stage issue", self.read(path))

    def test_neither_brief_orders_a_raw_whole_suite(self):
        """Every suite command a brief states is judged by the gate itself:
        each inline span, and each line of a fenced block (review finding 6)."""
        fenced_seen = 0
        for path in self.BRIEFS:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            fenced = [line for block in re.findall(r"```[^\n]*\n(.*?)```", text,
                                                    re.S)
                      for line in block.splitlines()]
            prose = re.sub(r"```.*?```", "", text, flags=re.S)
            spans = re.findall(r"`([^`]+)`", prose)
            fenced_seen += len(fenced)
            for span in spans + fenced:
                span = " ".join(span.split())
                with self.subTest(brief=os.path.basename(path), span=span):
                    self.assertIsNone(mod.decide(
                        "run-issues-implementer", span, TREE, ()))
        self.assertTrue(fenced_seen, "no fenced command read; the case is empty")

    def test_the_escalated_brief_no_longer_denies_the_suite(self):
        """It said "run typecheck and the issue's own tests, not the full
        suite" while deferring to a brief that orders one at the end."""
        self.assertNotIn("not the full suite",
                         self.read(self.BRIEFS[1]))

    def test_the_correction_line_cites_where_the_runners_re_run_is_ordered(self):
        """The audit read this line as stale because it cited no source."""
        brief = self.read(self.BRIEFS[0])
        at = brief.index("correction round runs no full suite")
        passage = brief[at:at + 900]
        self.assertIn("check_diff_coverage.py", passage)
        self.assertIn("--stage correction", passage)


if __name__ == "__main__":
    unittest.main(verbosity=2)
