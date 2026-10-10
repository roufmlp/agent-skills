#!/usr/bin/env python3
"""Cases for run_suite.py, the whole-suite wrapper.

Fix F4 of the 2026-09-23 audit, `the suite runs through one wrapper`. Each case drives the script as a command, in a throwaway
git repository, against a fake suite that prints what vitest prints.

    python3 -m unittest test_run_suite
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import datetime
import textwrap
import time
import unittest
import unittest.mock

SCRIPT = pathlib.Path(__file__).resolve().parent / "run_suite.py"
sys.path.insert(0, str(SCRIPT.parent))
import run_suite  # noqa: E402  (for `LOCK_ENV` and `lock_path` only)

# Holds the lock at argv[1] until killed, and says so once it has it.
HOLDER = textwrap.dedent("""\
    import fcntl, os, sys, time
    fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    os.write(fd, str(os.getpid()).encode())
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
""")

# A stand-in for `npx vitest run`. It prints the lines the wrapper reads, plus a
# marker line the summary must NOT carry, and exits with the code it is given.
# It also counts its own launches, so a refused run can be told from a run.
FAKE_SUITE = textwrap.dedent("""\
    import pathlib, sys
    exit_code, counter = int(sys.argv[1]), pathlib.Path(sys.argv[2])
    counter.write_text(str(int(counter.read_text() or 0) + 1) if counter.exists() else "1")
    print("the whole output, line one, which only the log keeps")
    for name in sys.argv[3:]:
        print(f" \\x1b[31mFAIL\\x1b[39m  {name} > a suite > a case")
        print(f" FAIL  {name} > a suite > another case")
    print(" Test Files  3 passed (3)")
    print("      Tests  12 passed (12)")
    print("   Duration  1.02s")
    sys.exit(exit_code)
""")


# A stand-in for vitest, installed as `bin/vitest` and as `bin/npm`, whose
# `test` script it plays. It appends its argv to `argv.jsonl`, writes a report
# where `--coverage.reportsDirectory=` points when `--coverage.enabled` is
# given, prints vitest's footer and a FAIL line per name in FAKE_FAILING, and
# exits with FAKE_EXIT.
FAKE_VITEST = textwrap.dedent("""\
    import json, os, pathlib, sys
    here = pathlib.Path(__file__).resolve().parent
    with open(here / "argv.jsonl", "a") as handle:
        handle.write(json.dumps([pathlib.Path(sys.argv[0]).name, *sys.argv[1:]]) + "\\n")
    args = sys.argv[1:]
    if "--coverage.enabled" in args:
        where = next((a.split("=", 1)[1] for a in args
                      if a.startswith("--coverage.reportsDirectory=")), "coverage")
        report = pathlib.Path(where)
        report.mkdir(parents=True, exist_ok=True)
        (report / "coverage-final.json").write_text(json.dumps(
            {str(pathlib.Path.cwd() / "a.ts"): {"path": str(pathlib.Path.cwd() / "a.ts")}}))
    if os.environ.get("FAKE_WRITE"):
        with open(os.environ["FAKE_WRITE"], "a") as handle:
            handle.write("// rewritten by the suite\\n")
    for name in filter(None, os.environ.get("FAKE_FAILING", "").split(",")):
        print(f" FAIL  {name} > a suite > a case")
    # FAKE_FLAKY: files that fail in a whole run and pass when named alone.
    flaky = [name for name in os.environ.get("FAKE_FLAKY", "").split(",") if name]
    named = [a for a in args if a.endswith(".ts")]
    if flaky and not named:
        for name in flaky:
            print(f" FAIL  {name} > a suite > a case")
        sys.exit(1)
    print(" Test Files  3 passed (3)")
    print("   Duration  1.02s")
    sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
""")


def spawn_of(stage):
    """Stage `issue` names its spawn. Every case but `TheIssueStage`'s is a
    final spawn, the one that hands its tree to the gates."""
    return ["--spawn", "final"] if stage == "issue" else []


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class Repo(unittest.TestCase):
    """A throwaway repository with one commit, and a fake suite outside it."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.scratch.name)
        self.repo = root / "tree"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / ".gitignore").write_text("ignored/\n")
        (self.repo / "a.ts").write_text("export const a = 1;\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "one")
        self.fake = root / "fake_suite.py"
        self.fake.write_text(FAKE_SUITE)
        self.counter = root / "launches"
        # Every case points the machine lock into its own
        # scratch directory. Without it a case waits on the real lock, which
        # the outer wrapper holds while the whole suite runs this file.
        self.lock = root / "suite.lock"
        self.env = {**os.environ, run_suite.LOCK_ENV: str(self.lock)}

    def tearDown(self):
        self.scratch.cleanup()

    def run_suite(self, *failing, exit_code=0, stage="issue", cwd=None):
        command = [sys.executable, str(self.fake), str(exit_code),
                   str(self.counter), *failing]
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--stage", stage, *spawn_of(stage),
             "--", *command],
            cwd=str(cwd or self.repo), capture_output=True, text=True,
            env=self.env, timeout=60)

    def copy(self):
        """A gate's private copy, as `make_copy.py` makes it: a clone with
        history, its own store, and the real `node_modules` symlinked."""
        (self.repo / "node_modules").mkdir()
        (self.repo / "node_modules" / "dep.js").write_text("module.exports = 1;\n")
        (self.repo / ".gitignore").write_text("ignored/\nnode_modules/\n")
        git(self.repo, "commit", "-qam", "ignore node_modules")
        copy = pathlib.Path(self.scratch.name) / "copy-of-tree"
        subprocess.run([sys.executable, str(SCRIPT.parent / "make_copy.py"),
                        "--tree", str(self.repo), "--dest", str(copy)],
                       check=True, capture_output=True)
        return copy

    def fake_bin(self):
        """`bin/vitest` and `bin/npm`, both the fake above."""
        bin_dir = pathlib.Path(self.scratch.name) / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name in ("vitest", "npm"):
            path = bin_dir / name
            path.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
            path.chmod(0o755)
        return bin_dir

    def run_command(self, *command, stage="issue", cwd=None, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--stage", stage, *spawn_of(stage),
             "--", *command],
            cwd=str(cwd or self.repo), capture_output=True, text=True,
            env={**self.env, **(env or {})}, timeout=60)

    def argvs(self, bin_dir):
        path = bin_dir / "argv.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def launches(self):
        return int(self.counter.read_text()) if self.counter.exists() else 0

    def store(self):
        path = git(self.repo, "rev-parse", "--git-path", "run-suite")
        return (self.repo / path).resolve() if not os.path.isabs(path) else pathlib.Path(path)

    def records(self):
        path = self.store() / "records.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]


class AGreenRun(Repo):
    """Criterion 1."""

    def test_it_keeps_the_whole_output_in_a_log_and_names_the_log(self):
        done = self.run_suite()
        self.assertEqual(done.returncode, 0, done.stderr)
        [record] = self.records()
        log = pathlib.Path(record["log"])
        self.assertIn(str(log), done.stdout)
        self.assertIn("the whole output, line one", log.read_text())

    def test_the_summary_carries_vitests_lines_and_not_the_whole_output(self):
        done = self.run_suite()
        self.assertIn("Test Files  3 passed (3)", done.stdout)
        self.assertIn("Tests  12 passed (12)", done.stdout)
        self.assertNotIn("the whole output, line one", done.stdout)

    def test_the_record_carries_the_tree_the_stage_and_the_exit(self):
        self.run_suite(stage="finale")
        [record] = self.records()
        self.assertEqual(record["stage"], "finale")
        self.assertEqual(record["exit"], 0)
        self.assertRegex(record["tree"], r"^[0-9a-f]{40}$")


class TheTreeHash(Repo):
    """Criterion 4."""

    def tree(self):
        self.run_suite(exit_code=1)
        return self.records()[-1]["tree"]

    def test_a_tracked_change_moves_it(self):
        before = self.tree()
        (self.repo / "a.ts").write_text("export const a = 22;\n")
        self.assertNotEqual(self.tree(), before)

    def test_a_new_untracked_file_moves_it(self):
        """`git stash create` misses this, and an implementer's new test file
        is untracked until the runner commits it."""
        before = self.tree()
        (self.repo / "b.test.ts").write_text("it('b', () => {});\n")
        self.assertNotEqual(self.tree(), before)

    def test_an_ignored_file_does_not_move_it(self):
        before = self.tree()
        (self.repo / "ignored").mkdir()
        (self.repo / "ignored" / "coverage.json").write_text("{}")
        self.assertEqual(self.tree(), before)

    def test_run_state_under_scratch_does_not_move_it(self):
        """The perf audit of 2026-09-28, fix 2. The runner and the gates write
        the ledger, the primer and the verdicts under `.scratch/` after the
        implementer's suite, and no suite reads them. Were they hashed, a
        verify gate's copy would never match the implementer's record."""
        (self.repo / ".scratch" / "feat").mkdir(parents=True)
        (self.repo / ".scratch" / "feat" / "run.md").write_text("one\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "scratch")
        before = run_suite.tree_hash(self.repo)
        (self.repo / ".scratch" / "feat" / "run.md").write_text("two\n")
        (self.repo / ".scratch" / "feat" / "verdicts.md").write_text("new\n")
        self.assertEqual(run_suite.tree_hash(self.repo), before)

    def test_a_same_size_edit_in_the_second_the_index_was_written_moves_it(self):
        """Git's racy-clean rule. An index entry no older than the index file
        itself is re-hashed, because its stat cannot be trusted. A copy of the
        index that takes a NEW mtime makes every entry look trustworthy, and a
        same-size edit made in the second of the last `git add` then reads as
        no change. This red on the first full run of this file.

        `os.utime` cannot set a ctime, so the state is made the way the run
        made it: stage, edit within the same second, hash in a later one."""
        target = self.repo / "a.ts"
        index = pathlib.Path(git(self.repo, "rev-parse", "--git-dir")) / "index"
        index = index if index.is_absolute() else self.repo / index
        for _ in range(20):
            target.write_text("export const a = 3;\n")
            git(self.repo, "add", "a.ts")
            staged = git(self.repo, "write-tree")
            target.write_text("export const a = 9;\n")      # the same size
            if int(target.stat().st_ctime) == int(index.stat().st_mtime):
                break
        else:
            self.skipTest("never edited within the second of the stage")
        time.sleep(1.1 - (time.time() % 1))
        self.assertNotEqual(self.tree(), staged)

    def test_the_real_index_and_status_are_untouched(self):
        (self.repo / "b.test.ts").write_text("it('b', () => {});\n")
        status = git(self.repo, "status", "--porcelain")
        staged = git(self.repo, "diff", "--cached", "--name-only")
        self.tree()
        self.assertEqual(git(self.repo, "status", "--porcelain"), status)
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), staged)


class ARepeat(Repo):
    """Criteria 2 and 3. Sixty-two implementer suites re-read an unchanged tree."""

    def test_a_second_run_on_a_green_tree_does_not_start_the_suite(self):
        first = self.run_suite()
        second = self.run_suite()
        self.assertEqual(second.returncode, 3, second.stdout + second.stderr)
        self.assertEqual(self.launches(), 1)
        [record] = self.records()
        self.assertIn(record["log"], second.stdout + second.stderr)
        self.assertIn("REFUSED", second.stdout + second.stderr)
        self.assertEqual(first.returncode, 0)

    def test_a_second_run_after_a_red_one_runs(self):
        self.run_suite("tests/flaky.test.ts", exit_code=1)
        second = self.run_suite()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(self.launches(), 2)

    def test_a_green_run_at_one_stage_does_not_refuse_another_stage(self):
        """The finale reads the tree the last implementer read, and
        `finale.md` step 1 asks for that reading. The suite-gate hook judges who
        may run which stage; this rule is per stage."""
        self.run_suite(stage="issue")
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 2)

    def test_a_changed_tree_runs_again(self):
        self.run_suite()
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        done = self.run_suite()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 2)


class ARedRun(Repo):
    """Criteria 5 and 6."""

    def test_it_names_each_failing_file_once(self):
        done = self.run_suite("tests/a.test.ts", "tests/b.test.ts", exit_code=1)
        self.assertEqual(done.stdout.count("tests/a.test.ts"), 1, done.stdout)
        self.assertEqual(done.stdout.count("tests/b.test.ts"), 1, done.stdout)
        self.assertEqual(self.records()[-1]["failing"],
                         ["tests/a.test.ts", "tests/b.test.ts"])

    def test_a_fail_line_that_names_no_file_is_not_a_file(self):
        """One project's transcripts hold `FAIL  a later move cannot land before
        today > refuses ...`, printed by a test's own drill, not by vitest.
        vitest names a file with its extension; a sentence is not one."""
        done = self.run_suite("a later move cannot land before today",
                              "tests/(signed-in)/page.test.tsx", exit_code=1)
        self.assertEqual(self.records()[-1]["failing"],
                         ["tests/(signed-in)/page.test.tsx"], done.stdout)

    def test_a_red_run_with_no_fail_line_says_so(self):
        done = self.run_suite(exit_code=1)
        self.assertIn("no FAIL line", done.stdout)

    def test_two_runs_in_one_second_keep_two_logs(self):
        self.run_suite("tests/a.test.ts", exit_code=1)
        self.run_suite("tests/b.test.ts", exit_code=1)
        first, second = self.records()
        self.assertNotEqual(first["log"], second["log"])
        self.assertIn("tests/a.test.ts", pathlib.Path(first["log"]).read_text())

    def test_a_coloured_summary_line_is_still_printed(self):
        """The FAIL reader strips colour; the summary must read the same text."""
        coloured = self.fake.read_text().replace(
            'print(" Test Files  3 passed (3)")',
            'print(" \\x1b[2mTest Files\\x1b[22m  3 passed (3)")')
        self.fake.write_text(coloured)
        done = self.run_suite()
        self.assertIn("Test Files  3 passed (3)", done.stdout)

    def test_the_exit_code_passes_through(self):
        self.assertEqual(self.run_suite(exit_code=7).returncode, 7)


class ACommandThatCannotStart(Repo):

    def test_it_exits_127_says_so_and_records_no_green(self):
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "--stage", "issue", "--spawn", "final",
             "--", "no-such-suite-binary-17"],
            cwd=str(self.repo), capture_output=True, text=True, env=self.env,
            timeout=60)
        self.assertEqual(done.returncode, 127, done.stdout + done.stderr)
        self.assertIn("could not start", done.stdout)
        self.assertNotIn("Traceback", done.stderr)
        self.assertTrue(all(r["exit"] != 0 for r in self.records()))


class TheBaseline(Repo):
    """Criterion 7. A run takes one baseline, whatever the tree."""

    def test_a_second_green_baseline_is_refused_on_a_changed_tree(self):
        self.run_suite(stage="baseline")
        (self.repo / "a.ts").write_text("export const a = 22;\n")
        done = self.run_suite(stage="baseline")
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.launches(), 1)

    def test_a_red_baseline_may_be_taken_again(self):
        self.run_suite(stage="baseline", exit_code=1)
        done = self.run_suite(stage="baseline")
        self.assertEqual(done.returncode, 0, done.stdout)


class TheVerifyStage(Repo):
    """The perf audit of 2026-09-28, fixes 1 and 2. The verify gate's copy is
    made by `make_copy.py`, with git history, and the gate reuses the
    implementer's suite record where the copy hashes to the same tree."""

    def copy_of(self):
        dest = pathlib.Path(self.scratch.name) / "copies" / "verify-01"
        made = subprocess.run([sys.executable, str(SCRIPT.parent / "make_copy.py"),
                               "--tree", str(self.repo), "--dest", str(dest)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        return dest

    def copy_records(self, copy):
        path = pathlib.Path(git(copy, "rev-parse", "--absolute-git-dir")) / "run-suite" / "records.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def test_the_old_rsync_copy_without_git_is_refused(self):
        copy = pathlib.Path(self.scratch.name) / "copy-of-tree"
        subprocess.run(["rsync", "-a", "--exclude", ".git", f"{self.repo}/",
                        f"{copy}/"], check=True)
        done = self.run_suite(cwd=copy, stage="verify")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 0)
        self.assertIn("make_copy.py", done.stdout)

    def test_a_git_tree_that_make_copy_did_not_make_is_refused(self):
        done = self.run_suite(stage="verify")
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.launches(), 0)
        self.assertIn("make_copy.py", done.stdout)

    def test_a_git_fault_that_is_not_a_missing_repository_still_refuses(self):
        broken = pathlib.Path(self.scratch.name) / "broken"
        broken.mkdir()
        (broken / ".git").write_text("gitdir: /nowhere/at/all\n")
        done = self.run_suite(cwd=broken, stage="verify")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 0)

    def test_the_implementers_record_at_the_same_tree_is_reused(self):
        bin_dir = self.fake_bin()
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.run_command(str(bin_dir / "vitest"), "run")
        issue = self.records()[-1]
        copy = self.copy_of()
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify", cwd=copy)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 1)
        self.assertIn("REUSED", done.stdout)
        self.assertIn(f"Coverage report: {issue['coverage']}", done.stdout)
        self.assertIn(f"Report root:     {issue['report_root']}", done.stdout)
        verify = self.copy_records(copy)[-1]
        self.assertEqual((verify["stage"], verify["reused"], verify["exit"]),
                         ("verify", issue["log"], 0))

    def test_a_red_record_is_reused_and_names_its_failing_files(self):
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run",
                         env={"FAKE_EXIT": "1", "FAKE_FAILING": "b.test.ts"})
        before = len(self.argvs(bin_dir))
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify",
                                cwd=self.copy_of())
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertEqual(len(self.argvs(bin_dir)), before)
        self.assertIn("b.test.ts", done.stdout)
        self.assertIn("alone", done.stdout)

    def test_a_tree_the_suite_itself_rewrote_is_matched_too(self):
        """Every whole suite of the audited project rewrites `tsconfig.json`
        (the pair2 audit, section 5). A copy taken after that matches the tree
        the suite left, which the record keeps as `tree_after`."""
        (self.repo / "tsconfig.json").write_text("{}\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "tsconfig")
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run",
                         env={"FAKE_WRITE": "tsconfig.json"})
        record = self.records()[-1]
        self.assertNotEqual(record["tree"], record["tree_after"])
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify",
                                cwd=self.copy_of())
        self.assertIn("REUSED", done.stdout)
        self.assertEqual(len(self.argvs(bin_dir)), 1)

    def test_the_newest_record_at_the_tree_decides(self):
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run", env={"FAKE_EXIT": "1"})
        self.run_command(str(bin_dir / "vitest"), "run")
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify",
                                cwd=self.copy_of())
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.argvs(bin_dir)), 2)

    def test_a_copy_that_differs_from_the_record_runs_its_own_suite(self):
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run")
        copy = self.copy_of()
        (copy / "a.ts").write_text("export const a = 'changed';\n")
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify", cwd=copy)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.argvs(bin_dir)), 2)
        self.assertIn(str(copy), self.copy_records(copy)[-1]["coverage"] or "")

    def test_a_record_with_no_report_is_not_reused(self):
        self.run_suite()
        bin_dir = self.fake_bin()
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify",
                                cwd=self.copy_of())
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.argvs(bin_dir)), 1)

    def test_a_record_at_another_stage_is_not_reused(self):
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run", stage="baseline")
        self.run_command(str(bin_dir / "vitest"), "run", stage="verify",
                         cwd=self.copy_of())
        self.assertEqual(len(self.argvs(bin_dir)), 2)


class TheCorrectionStage(Repo):
    """The perf audit of 2026-09-28, fix 3. A correction that changes tests
    only is graded by the scoped road, as a light issue is: seven runner
    suites of 5 to 7 minutes each went to test-only corrections in two runs."""

    def test_a_correction_that_changes_tests_only_is_refused_and_named_the_scoped_road(self):
        self.run_suite(exit_code=1)
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "helper.ts").write_text("export const h = 1;\n")
        (self.repo / "b.test.ts").write_text("it('pins', () => {});\n")
        done = self.run_suite(stage="correction")
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.launches(), 1)
        self.assertIn("scoped_suite.py", done.stdout)
        self.assertIn("b.test.ts", done.stdout)

    def test_a_correction_that_changes_source_runs_the_whole_suite(self):
        self.run_suite(exit_code=1)
        (self.repo / "b.test.ts").write_text("it('pins', () => {});\n")
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        done = self.run_suite(stage="correction")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.launches(), 2)

    def test_a_correction_with_no_implementer_suite_to_compare_runs(self):
        (self.repo / "b.test.ts").write_text("it('pins', () => {});\n")
        done = self.run_suite(stage="correction")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.launches(), 1)

    def test_a_correction_that_changed_nothing_is_refused(self):
        self.run_suite(exit_code=1)
        done = self.run_suite(stage="correction")
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.launches(), 1)

    def test_what_counts_as_a_test_path(self):
        for path in ("b.test.ts", "src/x.spec.tsx", "tests/helper.ts",
                     "src/__tests__/x.ts", "e2e/login.ts",
                     "test/x.mjs", "tests/build-checks/design-values.ts"):
            self.assertTrue(run_suite.is_test_path(path), path)
        # A fixture a test reads with `fs` is in no import graph, so the
        # scoped road could not find the test that reads it.
        for path in ("src/lib/testing.ts", "a.ts", "src/tests.ts",
                     "scripts/seed.mjs", "package.json", "src/contest/x.ts",
                     "fixtures/a.json", "tests/fixtures/orders.json",
                     "fixtures/build-checks/design-values/bare-px.tsx",
                     "tests/snapshot.md"):
            self.assertFalse(run_suite.is_test_path(path), path)


class TheHarnessSuite(Repo):
    """The perf audit of 2026-09-28, item 5 of the human's brief. A project's
    `.claude/run-isolation.json` may name `harnessSuite`: a command, and the
    paths whose change makes it required. The wrapper runs
    it after the whole suite when the tree's uncommitted diff touches one of
    them, and at the finale every time."""

    def contract(self, *entries, exit_code=0, failing=()):
        self.harness_counter = pathlib.Path(self.scratch.name) / "harness-launches"
        command = " ".join([sys.executable, str(self.fake), str(exit_code),
                            str(self.harness_counter), *failing])
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "run-isolation.json").write_text(json.dumps({
            "mechanism": "database-per-tree",
            "harnessSuite": {"command": command,
                             "requiredWhen": list(entries or
                                                  ["tests/harness/**", "vitest.config.ts"])}}))
        (self.repo / "vitest.config.ts").write_text("export default {};\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "contract")

    def harness_launches(self):
        path = self.harness_counter
        return int(path.read_text()) if path.exists() else 0

    def test_a_diff_touching_a_named_file_runs_the_harness_after_the_suite(self):
        self.contract()
        (self.repo / "vitest.config.ts").write_text("export default { a: 1 };\n")
        done = self.run_suite()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual((self.launches(), self.harness_launches()), (1, 1))
        harness = self.records()[-1]["harness"]
        self.assertEqual((harness["run"], harness["exit"]), (True, 0))
        self.assertTrue(pathlib.Path(harness["log"]).exists())
        self.assertIn("vitest.config.ts", harness["why"])
        self.assertIn("harness suite exit 0", done.stdout)

    def test_a_new_file_under_a_named_directory_counts(self):
        self.contract()
        (self.repo / "tests" / "harness").mkdir(parents=True)
        (self.repo / "tests" / "harness" / "lease.test.ts").write_text("it('x', () => {});\n")
        self.run_suite()
        self.assertEqual(self.harness_launches(), 1)

    def test_a_diff_touching_no_named_path_runs_no_harness(self):
        self.contract()
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "harnessed.ts").write_text("x\n")
        done = self.run_suite()
        self.assertEqual(self.harness_launches(), 0)
        self.assertFalse(self.records()[-1]["harness"]["run"])
        self.assertIn("harness suite not run", done.stdout)

    def test_the_finale_always_runs_it(self):
        self.contract()
        self.run_suite(stage="finale")
        self.assertEqual(self.harness_launches(), 1)

    def test_the_baseline_runs_none(self):
        self.contract()
        (self.repo / "vitest.config.ts").write_text("export default { a: 1 };\n")
        self.run_suite(stage="baseline")
        self.assertEqual(self.harness_launches(), 0)

    def test_a_red_harness_makes_the_call_red_and_names_its_files(self):
        self.contract(exit_code=1, failing=["tests/harness/lease.test.ts"])
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 1, done.stdout)
        record = self.records()[-1]
        self.assertEqual((record["exit"], record["suite_exit"]), (1, 0))
        self.assertIn("tests/harness/lease.test.ts", record["failing"])

    def test_an_entry_it_cannot_place_is_refused_before_anything_runs(self):
        for entry in ("tests/*.test.ts", "/abs/path", "../outside/**", "src/**/x.ts", ""):
            with self.subTest(entry=entry):
                self.contract(entry)
                done = self.run_suite(stage="finale")
                self.assertEqual(done.returncode, 3, done.stdout)
                self.assertEqual((self.launches(), self.harness_launches()), (0, 0))

    def test_a_contract_that_cannot_be_read_is_refused(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "run-isolation.json").write_text("{ not json")
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.launches(), 0)

    def test_a_repo_with_no_contract_runs_no_harness(self):
        self.run_suite(stage="finale")
        self.assertFalse(self.records()[-1]["harness"]["run"])

    def test_the_verify_gate_reuses_the_harness_reading_too(self):
        self.contract()
        (self.repo / "vitest.config.ts").write_text("export default { a: 1 };\n")
        bin_dir = self.fake_bin()
        self.run_command(str(bin_dir / "vitest"), "run")
        copy = pathlib.Path(self.scratch.name) / "copies" / "verify-01"
        subprocess.run([sys.executable, str(SCRIPT.parent / "make_copy.py"),
                        "--tree", str(self.repo), "--dest", str(copy)],
                       check=True, capture_output=True)
        done = self.run_command(str(bin_dir / "vitest"), "run", stage="verify", cwd=copy)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.harness_launches(), 1)
        self.assertIn("harness suite exit 0", done.stdout)


class TheHarnessFlakeRecheck(TheHarnessSuite):
    """The human, 2026-10-11, changing a ruling of 2026-10-05: a red harness
    reading gets the recheck a red whole suite gets. One project's
    `tests/views/home-badge-time.test.ts` reds under two parallel runs (594 ms
    against a 450 ms bound), and each such red re-ran all 453 harness files.
    That project's command is `npm run test:harness`, whose script takes file
    names after `--`."""

    def npm_contract(self, env):
        bin_dir = self.fake_bin()
        self.contract()
        isolation = self.repo / ".claude" / "run-isolation.json"
        block = json.loads(isolation.read_text())
        block["harnessSuite"]["command"] = f"{bin_dir / 'npm'} run test:harness"
        isolation.write_text(json.dumps(block))
        git(self.repo, "commit", "-qam", "npm contract")
        self.env.update(env)
        return bin_dir

    def ledger(self):
        path = self.repo / ".git" / "run-suite-flakes.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_a_harness_file_that_passes_alone_is_a_flake_and_the_call_is_green(self):
        bin_dir = self.npm_contract({"FAKE_FLAKY": "tests/views/home-badge-time.test.ts"})
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        argvs = self.argvs(bin_dir)
        self.assertEqual(len(argvs), 2)
        self.assertEqual(argvs[1], ["npm", "run", "test:harness", "--",
                                    "--no-file-parallelism",
                                    "tests/views/home-badge-time.test.ts"])
        record = self.records()[-1]
        harness = record["harness"]
        self.assertEqual((record["exit"], record["failing"], harness["exit"],
                          harness["suite_exit"], harness["flaky"]),
                         (0, [], 0, 1, ["tests/views/home-badge-time.test.ts"]))
        self.assertTrue(pathlib.Path(harness["recheck"]["log"]).exists())
        self.assertEqual([(e["file"], e["suite"], e["stage"]) for e in self.ledger()],
                         [("tests/views/home-badge-time.test.ts", "harness", "finale")])
        self.assertIn("FLAKY: tests/views/home-badge-time.test.ts", done.stdout)

    def test_a_harness_file_that_fails_alone_too_keeps_the_call_red(self):
        bin_dir = self.npm_contract({"FAKE_FAILING": "tests/harness/lease.test.ts",
                                     "FAKE_EXIT": "1"})
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 2)
        record = self.records()[-1]
        self.assertEqual(record["failing"], ["tests/harness/lease.test.ts"])
        self.assertNotIn("flaky", record["harness"])
        self.assertEqual(self.ledger(), [])

    def test_more_failing_harness_files_than_the_cap_are_not_rechecked(self):
        names = ",".join(f"tests/f{n}.test.ts" for n in range(run_suite.RECHECK_CAP + 1))
        bin_dir = self.npm_contract({"FAKE_FLAKY": names})
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 1)
        self.assertIn("not rechecked", done.stdout)

    def test_a_harness_command_it_cannot_place_is_not_rechecked(self):
        self.contract(exit_code=1, failing=["tests/harness/lease.test.ts"])
        done = self.run_suite(stage="finale")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertEqual(self.harness_launches(), 1)
        self.assertIn("not rechecked", done.stdout)


class TheMachineLock(Repo):
    """Every whole-suite red in six audited runs was two runs
    contending, so a whole suite waits for any other on the machine."""

    def start(self, cwd, stage="issue"):
        return subprocess.Popen(
            [sys.executable, str(SCRIPT), "--stage", stage, *spawn_of(stage),
             "--", "sleep", "2"],
            cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=self.env)

    def hold(self, seconds):
        holder = subprocess.Popen(
            [sys.executable, "-c", HOLDER, str(self.lock), str(seconds)],
            stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (holder.kill(), holder.wait(),
                                 holder.stdout.close()))
        self.assertEqual(holder.stdout.readline().strip(), "held")
        return holder

    def timed(self, **kwargs):
        began = time.monotonic()
        done = self.run_suite(**kwargs)
        return done, time.monotonic() - began

    def test_two_suites_started_together_run_one_after_the_other(self):
        """AC1. One from the git tree, one from a gate's copy: two
        stores, so the lock is not kept per store, and neither call is refused
        as a green repeat of the other."""
        copy = self.copy()
        calls = [self.start(self.repo), self.start(copy, stage="verify")]
        for call in calls:
            output, _ = call.communicate(timeout=60)
            self.assertEqual(call.returncode, 0, output)
        [in_tree] = self.records()
        [in_copy] = [json.loads(line) for line in
                     (pathlib.Path(git(copy, "rev-parse", "--absolute-git-dir")) / "run-suite" / "records.jsonl").read_text().splitlines()]
        earlier, later = sorted(
            [in_tree, in_copy], key=lambda r: datetime.datetime.fromisoformat(r["started"]))
        gap = (datetime.datetime.fromisoformat(later["started"])
               - datetime.datetime.fromisoformat(earlier["started"])).total_seconds()
        self.assertGreaterEqual(gap, earlier["seconds"] - 0.1, (earlier, later))

    def test_with_no_override_the_lock_is_one_path_outside_every_tree(self):
        """AC1's subtest. Two trees name one absolute path, inside neither."""
        copy = self.copy()
        seen = []
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        with unittest.mock.patch.dict(os.environ):
            os.environ.pop(run_suite.LOCK_ENV, None)
            for tree in (self.repo, copy):
                os.chdir(tree)
                seen.append(run_suite.lock_path())
        self.assertEqual(seen[0], seen[1])
        self.assertTrue(seen[0].is_absolute())
        for tree in (self.repo.resolve(), copy.resolve()):
            self.assertFalse(seen[0].resolve().is_relative_to(tree), seen[0])

    def test_a_suite_waits_for_a_held_lock_and_says_so_once(self):
        self.hold(1.5)
        done, took = self.timed()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        waits = [line for line in done.stdout.splitlines() if "waiting" in line]
        self.assertEqual(len(waits), 1, done.stdout)
        self.assertIn(str(self.lock), waits[0])
        self.assertGreaterEqual(took, 1.0)
        self.assertEqual(len(self.records()), 1)

    def test_a_lock_file_naming_a_dead_pid_is_taken_at_once(self):
        """AC2, fixture (a)."""
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.lock.write_text(str(dead.pid))
        done, took = self.timed()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("waiting", done.stdout)
        self.assertLess(took, 10)
        self.assertEqual(len(self.records()), 1)

    def test_a_lock_whose_holder_was_killed_is_taken_at_once(self):
        """AC2, fixture (b): a wrapper killed by its caller's timeout."""
        holder = self.hold(600)
        holder.send_signal(signal.SIGKILL)
        holder.wait()
        self.assertTrue(self.lock.read_text().strip())   # it still names the dead
        done, took = self.timed()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("waiting", done.stdout)
        self.assertLess(took, 10)
        self.assertEqual(len(self.records()), 1)

    def test_a_lock_that_cannot_be_opened_runs_the_suite_without_it(self):
        blocker = pathlib.Path(self.scratch.name) / "a-file"
        blocker.write_text("")
        self.env[run_suite.LOCK_ENV] = str(blocker / "suite.lock")
        done = self.run_suite(exit_code=5)
        self.assertEqual(done.returncode, 5, done.stdout + done.stderr)
        said = [line for line in done.stdout.splitlines() if "without the lock" in line]
        self.assertEqual(len(said), 1, done.stdout)
        self.assertEqual(self.launches(), 1)

    # The perf audit of 2026-09-28: `started` was stamped after the lock was
    # taken, so 28.5 minutes of queue across two runs were in no record, and
    # one run's ledger blamed "the other run's load" on a suite that
    # started 37 minutes after the other run ended. The record now says when the
    # suite asked, how long it waited, and whether another suite held the lock.

    def test_a_free_lock_is_recorded_as_free_with_no_wait(self):
        done = self.run_suite()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        [record] = self.records()
        self.assertEqual(record["lock"], "free")
        self.assertIsNone(record["lock_holder"])
        self.assertLess(record["waited"], 1.0)
        self.assertLessEqual(datetime.datetime.fromisoformat(record["asked"]),
                             datetime.datetime.fromisoformat(record["started"]))
        self.assertIn("no other whole suite held it", done.stdout)

    def test_a_held_lock_records_the_wait_and_the_holder(self):
        holder = self.hold(1.5)
        done = self.run_suite()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        [record] = self.records()
        self.assertEqual(record["lock"], "held")
        self.assertEqual(record["lock_holder"], str(holder.pid))
        self.assertGreaterEqual(record["waited"], 1.0)
        gap = (datetime.datetime.fromisoformat(record["started"])
               - datetime.datetime.fromisoformat(record["asked"])).total_seconds()
        self.assertGreaterEqual(gap, record["waited"] - 0.1)
        said = [line for line in done.stdout.splitlines() if "waited" in line]
        self.assertEqual(len(said), 1, done.stdout)
        self.assertIn(str(holder.pid), said[0])

    def test_a_suite_run_without_the_lock_says_so_in_its_record(self):
        blocker = pathlib.Path(self.scratch.name) / "a-file"
        blocker.write_text("")
        self.env[run_suite.LOCK_ENV] = str(blocker / "suite.lock")
        self.run_suite()
        [record] = self.records()
        self.assertEqual(record["lock"], "none")
        self.assertIsNone(record["lock_holder"])

    def test_a_refusal_still_exits_3_under_the_lock(self):
        self.run_suite()
        done = self.run_suite()
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertIn("already ran green at stage", done.stdout)


class TheIssueStage(Repo):
    """One run on one project (2026-10-06): 12 whole suites, 47.5 minutes,
    on two screen issues. The logic spawn's suites, 23.7 minutes, were read by
    nobody: the screen spawn ran one on the tree the gates read. Four reds, 15.6
    minutes, were reds the scoped road also finds in a minute and a half."""

    def vitest(self):
        """A tree the scoped road can read: `node_modules/.bin/vitest`."""
        bin_dir = self.repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "vitest").write_text("")
        (self.repo / ".gitignore").write_text("ignored/\nnode_modules/\n")
        git(self.repo, "commit", "-qam", "ignore node_modules")

    def scoped(self, exit_code=0, failing=(), tree=None):
        """A record as `scoped_suite.py` writes it, for the tree as it stands."""
        store = self.store()
        store.mkdir(parents=True, exist_ok=True)
        tree_id = tree or run_suite.tree_hash(self.repo)
        with open(store / "records.jsonl", "a") as handle:
            handle.write(json.dumps({
                "tree": tree_id, "tree_after": tree_id, "stage": "scoped",
                "exit": exit_code, "failing": list(failing),
                "started": "2026-10-06T07:00:00+00:00",
                "log": "/the/scoped.log"}) + "\n")

    def call(self, *spawn, stage="issue"):
        command = [sys.executable, str(self.fake), "0", str(self.counter)]
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--stage", stage, *spawn, "--", *command],
            cwd=str(self.repo), capture_output=True, text=True, env=self.env,
            timeout=60)

    def test_an_issue_suite_naming_no_spawn_is_refused_and_told_both(self):
        done = self.call()
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("--spawn logic", done.stdout)
        self.assertIn("--spawn final", done.stdout)
        self.assertEqual(self.launches(), 0)

    def test_the_logic_spawn_is_refused_and_named_the_scoped_road(self):
        self.vitest()
        self.scoped()
        done = self.call("--spawn", "logic")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("scoped_suite.py", done.stdout)
        self.assertEqual(self.launches(), 0)

    def test_a_final_spawn_with_no_scoped_reading_is_refused(self):
        self.vitest()
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("scoped_suite.py", done.stdout)
        self.assertEqual(self.launches(), 0)

    def test_a_final_spawn_on_a_tree_the_scoped_road_passed_runs(self):
        self.vitest()
        self.scoped()
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 1)
        self.assertEqual(self.records()[-1]["spawn"], "final")

    def test_a_red_whole_suite_may_be_run_again_on_the_same_passed_tree(self):
        self.vitest()
        self.scoped()
        command = [sys.executable, str(self.fake), "1", str(self.counter), "x.test.ts"]
        for _ in range(2):
            subprocess.run([sys.executable, str(SCRIPT), "--stage", "issue",
                            "--spawn", "final", "--", *command],
                           cwd=str(self.repo), capture_output=True, text=True,
                           env=self.env, timeout=60)
        self.assertEqual(self.launches(), 2)

    def test_the_newest_scoped_reading_decides_and_a_red_one_is_named(self):
        self.vitest()
        self.scoped()
        self.scoped(exit_code=1, failing=["tests/a.test.ts"])
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("tests/a.test.ts", done.stdout)
        self.assertEqual(self.launches(), 0)

    def test_a_scoped_pass_on_an_older_tree_does_not_count(self):
        self.vitest()
        self.scoped()
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 0)

    def test_a_wide_scoped_reading_lets_the_final_spawn_run(self):
        self.vitest()
        store = self.store()
        store.mkdir(parents=True, exist_ok=True)
        tree_id = run_suite.tree_hash(self.repo)
        with open(store / "records.jsonl", "a") as handle:
            handle.write(json.dumps({"tree": tree_id, "tree_after": tree_id,
                                     "stage": "scoped", "exit": None, "wide": True,
                                     "started": "2026-10-06T11:00:00+00:00"}) + "\n")
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 1)

    def test_the_refusal_names_the_wide_flag(self):
        self.vitest()
        done = self.call("--spawn", "final")
        self.assertIn("--whole-if-wide", done.stdout)

    def test_a_tree_with_no_vitest_has_no_scoped_road_and_runs(self):
        done = self.call("--spawn", "final")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 1)

    def test_a_spawn_at_another_stage_is_an_error(self):
        done = self.call("--spawn", "final", stage="finale")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 0)


class TheFlakeRecheck(Repo):
    """A red whole suite re-runs only its failing files, one after another.
    Files that pass there are flakes: the call is green, and the repository's
    flake ledger counts them. Nine flaky reds cost 34.5 minutes of whole-suite
    re-runs in the three suite stores on disk on 2026-10-06."""

    copy_of = TheVerifyStage.copy_of

    def red(self, env):
        bin_dir = self.fake_bin()
        done = self.run_command(str(bin_dir / "npm"), "test", env=env)
        return bin_dir, done

    def ledger(self):
        path = self.repo / ".git" / "run-suite-flakes.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_a_file_that_passes_alone_is_a_flake_and_the_call_is_green(self):
        bin_dir, done = self.red({"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("FLAKY: tests/a.test.ts", done.stdout)
        argvs = self.argvs(bin_dir)
        self.assertEqual(len(argvs), 2)
        self.assertIn("tests/a.test.ts", argvs[1])
        self.assertIn("--no-file-parallelism", argvs[1])
        self.assertFalse(any(a.startswith("--coverage") for a in argvs[1]))
        record = self.records()[-1]
        self.assertEqual((record["exit"], record["suite_exit"], record["failing"],
                          record["flaky"]), (0, 1, [], ["tests/a.test.ts"]))
        self.assertTrue(pathlib.Path(record["recheck"]["log"]).exists())
        self.assertEqual([e["file"] for e in self.ledger()], ["tests/a.test.ts"])

    def test_a_flake_line_names_the_app_suite(self):
        self.red({"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual([e["suite"] for e in self.ledger()], ["app"])

    def test_a_file_that_fails_alone_too_stays_red_and_is_no_flake(self):
        bin_dir, done = self.red({"FAKE_FAILING": "tests/a.test.ts", "FAKE_EXIT": "1"})
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 2)
        record = self.records()[-1]
        self.assertEqual((record["exit"], record["failing"]), (1, ["tests/a.test.ts"]))
        self.assertNotIn("flaky", record)
        self.assertEqual(self.ledger(), [])

    def test_more_failing_files_than_the_cap_are_not_rechecked(self):
        names = ",".join(f"tests/f{n}.test.ts" for n in range(run_suite.RECHECK_CAP + 1))
        bin_dir, done = self.red({"FAKE_FLAKY": names})
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 1)
        self.assertIn("not rechecked", done.stdout)

    def test_a_red_with_no_fail_line_is_not_rechecked(self):
        bin_dir, done = self.red({"FAKE_EXIT": "1"})
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.argvs(bin_dir)), 1)

    def test_a_command_it_cannot_place_is_not_rechecked(self):
        done = self.run_suite("tests/a.test.ts", exit_code=1)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(self.launches(), 1)

    def test_a_second_flake_of_one_file_is_counted_as_a_repeat(self):
        self.red({"FAKE_FLAKY": "tests/a.test.ts"})
        (self.repo / "a.ts").write_text("export const a = 3;\n")
        _, done = self.red({"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("flaked 2 times", done.stdout)
        self.assertEqual(len(self.ledger()), 2)

    def test_a_gates_copy_writes_the_run_trees_ledger(self):
        bin_dir = self.fake_bin()
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        copy = self.copy_of()
        (copy / "a.ts").write_text("export const a = 4;\n")
        done = self.run_command(str(bin_dir / "npm"), "test", stage="verify",
                                cwd=copy, env={"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([e["stage"] for e in self.ledger()], ["verify"])


class NoShell(Repo):
    """Criterion 9. A character in an argument is never a shell's to read."""

    def test_an_argument_reaches_the_command_as_written(self):
        done = self.run_suite("tests/$(touch pwned).test.ts", exit_code=1)
        self.assertFalse((self.repo / "pwned").exists())
        self.assertIn("tests/$(touch pwned).test.ts", done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
