#!/usr/bin/env python3
"""Drill for suite.py: the block, the hooksPath refusal, the lock, the full,
scoped and named runs, the flake recheck and ledger, the run row, and the red
check on a fake product whose vitest is a Python script.

    python3 test_suite.py
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import suite as mod  # noqa: E402

SCRIPT = os.path.join(HERE, "suite.py")

# A vitest stand-in. It records its argv, prints a FAIL line per FAKE_FAILING
# name and vitest's footer, and exits FAKE_EXIT. FAKE_FLAKY names fail in a run
# that names no file and pass when named alone. With `--reporter=json` it
# writes a report: every title found in the files it was named, with the
# status FAKE_STATUS gives it (`title=status,...`), `failed` by default; a file
# named in FAKE_NO_LOAD is reported failed with no cases; a file named in
# FAKE_NOT_RUN is left out of the report unless `--config` is among the args,
# as a vitest config that excludes the file would leave it. It records the text
# of `src/a.ts` beside it, so a case can see which code it ran on.
FAKE_VITEST = textwrap.dedent("""\
    import json, os, pathlib, re, sys
    args = sys.argv[1:]
    cwd = pathlib.Path.cwd()
    with open(os.environ["FAKE_ARGV"], "a") as handle:
        handle.write(json.dumps({"args": args, "cwd": str(cwd),
                                 "src": (cwd / "src" / "a.ts").read_text() if (cwd / "src" / "a.ts").exists() else None,
                                 "modules": os.path.islink(cwd / "node_modules"),
                                 "migration": (cwd / "supabase/migrations/0002_b.sql").exists(),
                                 "helper": (cwd / "tests/helper.ts").exists()}) + "\\n")
    if os.environ.get("FAKE_HOLD"):
        import time; time.sleep(float(os.environ["FAKE_HOLD"]))
    named = [a for a in args if a.endswith((".ts", ".tsx"))]
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--outputFile=")), None)
    if out:
        statuses = dict(p.split("=") for p in os.environ.get("FAKE_STATUS", "").split(",") if p)
        no_load = os.environ.get("FAKE_NO_LOAD", "").split(",")
        not_run = os.environ.get("FAKE_NOT_RUN", "").split(",") if "--config" not in args else []
        results = []
        for name in named:
            if name in not_run:
                continue
            if name in no_load:
                results.append({"name": str(cwd / name), "status": "failed", "assertionResults": []})
                continue
            text = (cwd / name).read_text()
            titles = re.findall(r"\\bit\\(\\s*\\"([^\\"]*)\\"", text)
            results.append({"name": str(cwd / name), "status": "passed", "assertionResults": [
                {"title": t, "fullName": t, "status": statuses.get(t, "failed")} for t in titles]})
        pathlib.Path(out).write_text(json.dumps({"testResults": results}))
        sys.exit(1)
    for name in filter(None, os.environ.get("FAKE_FAILING", "").split(",")):
        print(f" FAIL  {name} > a suite > a case")
    flaky = [n for n in os.environ.get("FAKE_FLAKY", "").split(",") if n]
    if flaky and not named:
        for name in flaky:
            print(f" FAIL  {name} > a suite > a case")
        print(" Test Files  1 failed | 2 passed (3)")
        sys.exit(1)
    ran = os.environ.get("FAKE_RAN", str(len(named)) if named else "3")
    if ran != "none":
        print(f" Test Files  {ran} passed ({ran})")
    print("   Duration  1.02s")
    sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
""")

BLOCK = textwrap.dedent("""\
    # A product

    Lane: careful.

    Suite: {vitest} run
    Harness suite: {vitest} run --config harness
    Typecheck: {vitest} typecheck
    End-to-end: {vitest} e2e
    Suite budget: 1 minutes
""")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class Product(unittest.TestCase):
    """A git repo with a CLAUDE.md block, a fake vitest and one commit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.tree = root / "product"
        self.tree.mkdir()
        self.vitest = root / "vitest"
        self.vitest.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
        self.vitest.chmod(0o755)
        self.argv = root / "argv.jsonl"
        self.lock = root / "lock"
        self.env = {**os.environ, mod.LOCK_ENV: str(self.lock), "FAKE_ARGV": str(self.argv)}
        for key in ("FAKE_FAILING", "FAKE_FLAKY", "FAKE_EXIT", "FAKE_RAN", "FAKE_STATUS",
                    "FAKE_NO_LOAD", "FAKE_NOT_RUN", "FAKE_HOLD"):
            self.env.pop(key, None)
        (self.tree / "CLAUDE.md").write_text(BLOCK.format(vitest=self.vitest))
        (self.tree / "src").mkdir()
        (self.tree / "src" / "a.ts").write_text("export const a = 1;\n")
        (self.tree / "tests").mkdir()
        (self.tree / "tests" / "a.test.ts").write_text('it("adds", () => {});\n')
        git(self.tree, "init", "-q", "-b", "main")
        git(self.tree, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.tree, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        self.base = git(self.tree, "rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def run_suite(self, *args, env=None):
        return subprocess.run([sys.executable, SCRIPT, *args, "--tree", str(self.tree)],
                              capture_output=True, text=True, env={**self.env, **(env or {})})

    def calls(self):
        return [json.loads(line) for line in self.argv.read_text().splitlines()] \
            if self.argv.exists() else []

    def rows(self):
        path = pathlib.Path(git(self.tree, "rev-parse", "--path-format=absolute",
                                "--git-common-dir")) / "suite" / "runs.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def ledger(self):
        path = pathlib.Path(git(self.tree, "rev-parse", "--path-format=absolute",
                                "--git-common-dir")) / mod.FLAKES
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class TheBlock(Product):
    def test_a_missing_line_is_refused_and_nothing_runs(self):
        (self.tree / "CLAUDE.md").write_text("Suite: x\nTypecheck: y\nSuite budget: 5 minutes\n")
        done = self.run_suite("full")
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("no `End-to-end:` line", done.stdout)
        self.assertEqual(self.calls(), [])

    def test_a_budget_that_is_not_minutes_is_refused(self):
        (self.tree / "CLAUDE.md").write_text(
            BLOCK.format(vitest=self.vitest).replace("1 minutes", "fast"))
        done = self.run_suite("full")
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("not `<n> minutes`", done.stdout)

    def test_the_harness_line_is_optional(self):
        text = "\n".join(l for l in BLOCK.format(vitest=self.vitest).splitlines()
                         if not l.startswith("Harness")) + "\n"
        (self.tree / "CLAUDE.md").write_text(text)
        done = self.run_suite("full")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.calls()), 1)

    def test_a_missing_claude_md_is_refused(self):
        (self.tree / "CLAUDE.md").unlink()
        done = self.run_suite("full")
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("does not exist", done.stdout)


class TheHooksPath(Product):
    def test_unset_with_no_githooks_runs(self):
        self.assertIsNone(mod.hooks_refusal(self.tree))

    def test_set_to_the_trees_own_githooks_runs(self):
        (self.tree / ".githooks").mkdir()
        git(self.tree, "config", "core.hooksPath", ".githooks")
        self.assertIsNone(mod.hooks_refusal(self.tree))
        git(self.tree, "config", "core.hooksPath", str(self.tree / ".githooks"))
        self.assertIsNone(mod.hooks_refusal(self.tree))

    def test_set_elsewhere_is_refused_before_anything_runs(self):
        (self.tree / ".githooks").mkdir()
        git(self.tree, "config", "core.hooksPath", "/dev/null")
        done = self.run_suite("full")
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("core.hooksPath is `/dev/null`", done.stdout)
        self.assertEqual(self.calls(), [])

    def test_set_while_the_tree_has_no_githooks_is_refused(self):
        git(self.tree, "config", "core.hooksPath", ".husky")
        self.assertIn("does not exist", mod.hooks_refusal(self.tree))

    def test_unset_while_the_tree_has_githooks_is_refused(self):
        (self.tree / ".githooks").mkdir()
        self.assertIn("is not set", mod.hooks_refusal(self.tree))


class TheFullRun(Product):
    def test_a_green_run_writes_a_row_with_seconds_and_budget(self):
        done = self.run_suite("full")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual([c["args"] for c in self.calls()], [["run"], ["run", "--config", "harness"]])
        row = self.rows()[-1]
        self.assertEqual(row["kind"], "full")
        self.assertEqual(row["budget_seconds"], 60)
        self.assertFalse(row["over_budget"])
        self.assertGreaterEqual(row["seconds"], 0)
        self.assertEqual(row["lock"], "free")
        self.assertIn("full run:", done.stdout)
        self.assertEqual(mod.last_full_run(self.tree)["kind"], "full")

    def test_a_red_that_passes_alone_is_a_flake_and_the_run_is_green(self):
        done = self.run_suite("full", env={"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("FLAKY: tests/a.test.ts", done.stdout)
        recheck = self.calls()[1]["args"]
        self.assertIn("--no-file-parallelism", recheck)
        self.assertIn("tests/a.test.ts", recheck)
        self.assertEqual([r["file"] for r in self.ledger()], ["tests/a.test.ts"] * 2)
        self.assertEqual([r["suite"] for r in self.ledger()], ["app", "harness"])
        self.assertEqual(self.rows()[-1]["flaky"], ["tests/a.test.ts"])
        self.assertEqual(self.rows()[-1]["exit"], 0)

    def test_a_red_that_fails_alone_too_stays_red(self):
        done = self.run_suite("full", env={"FAKE_FAILING": "tests/a.test.ts", "FAKE_EXIT": "1"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("this red is no flake", done.stdout)
        self.assertEqual(self.ledger(), [])
        self.assertEqual(self.rows()[-1]["failing"], ["tests/a.test.ts"])

    def test_a_recheck_that_ran_other_files_is_no_flake(self):
        done = self.run_suite("full", env={"FAKE_FLAKY": "tests/a.test.ts", "FAKE_RAN": "0"})
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.ledger(), [])

    def test_more_than_five_failing_files_are_not_rechecked(self):
        names = ",".join(f"tests/{i}.test.ts" for i in range(6))
        done = self.run_suite("full", env={"FAKE_FAILING": names, "FAKE_EXIT": "1"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("over the cap of 5", done.stdout)
        self.assertEqual(len(self.calls()), 2)  # the app run and the harness run

    def test_a_run_over_budget_says_so_and_does_not_stop(self):
        (self.tree / "CLAUDE.md").write_text(
            BLOCK.format(vitest=self.vitest).replace("1 minutes", "0 minutes"))
        done = self.run_suite("full")
        self.assertEqual(done.returncode, 0)
        self.assertIn("OVER BUDGET", done.stdout)
        self.assertTrue(self.rows()[-1]["over_budget"])


class TheLock(Product):
    def test_a_second_full_run_waits_for_the_first(self):
        first = subprocess.Popen([sys.executable, SCRIPT, "full", "--tree", str(self.tree)],
                                 env={**self.env, "FAKE_HOLD": "2"},
                                 stdout=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not self.argv.exists():
            time.sleep(0.05)
        began = time.monotonic()
        second = self.run_suite("full")
        first.wait()
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertIn("waiting for it", second.stdout)
        self.assertGreater(time.monotonic() - began, 1.0)
        waited = [r for r in self.rows() if r["lock"] == "held"]
        self.assertEqual(len(waited), 1)
        self.assertGreater(waited[0]["waited"], 0)

    def test_a_scoped_run_skips_the_lock(self):
        fd = os.open(self.lock, os.O_RDWR | os.O_CREAT, 0o600)
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            done = self.run_suite("scoped", "--base", self.base)
        finally:
            os.close(fd)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertNotIn("waiting", done.stdout)


class TheSmallRuns(Product):
    def test_scoped_runs_the_change_since_base_with_four_workers(self):
        done = self.run_suite("scoped", "--base", self.base)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.calls()[0]["args"], ["run", "--maxWorkers=4", f"--changed={self.base}"])
        self.assertEqual(self.rows()[-1]["kind"], "scoped")

    def test_scoped_without_base_is_refused(self):
        done = self.run_suite("scoped")
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("needs --base", done.stdout)

    def test_files_runs_the_named_files_with_four_workers(self):
        done = self.run_suite("files", "tests/a.test.ts")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.calls()[0]["args"], ["run", "--maxWorkers=4", "tests/a.test.ts"])

    def test_a_scoped_flake_is_rechecked_and_recorded(self):
        done = self.run_suite("scoped", "--base", self.base, env={"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.ledger()[-1]["kind"], "scoped")

    def test_typecheck_runs_its_line_and_e2e_takes_the_lock(self):
        done = self.run_suite("typecheck")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.calls()[0]["args"], ["typecheck"])
        done = self.run_suite("e2e")
        self.assertEqual(self.calls()[1]["args"], ["e2e"])
        self.assertIn("e2e:", done.stdout)

    def test_a_package_manager_script_gets_its_double_dash(self):
        self.assertEqual(mod.place_args(["npm", "test"], ["x"]), ["npm", "test", "--", "x"])
        self.assertEqual(mod.place_args(["npm", "run", "test:harness"], ["x"]),
                         ["npm", "run", "test:harness", "--", "x"])
        self.assertEqual(mod.place_args(["npx", "vitest", "run"], ["x"]), ["npx", "vitest", "run", "x"])
        with self.assertRaises(mod.Refusal):
            mod.place_args(["make", "test"], ["x"])


class TheRedCheck(Product):
    """The note changes `src/a.ts`, adds a migration, adds a test file and a
    title to an old one. The fake vitest reports every new title failed
    unless FAKE_STATUS says otherwise."""

    def note(self):
        (self.tree / "src" / "a.ts").write_text("export const a = 2;\n")
        (self.tree / "supabase" / "migrations").mkdir(parents=True)
        (self.tree / "supabase" / "migrations" / "0002_b.sql").write_text("create table b ();\n")
        (self.tree / "tests" / "b.test.ts").write_text(
            'it("reads b", () => {});\nit("writes b", () => {});\nit("keeps: a still adds", () => {});\n')
        (self.tree / "tests" / "a.test.ts").write_text('it("adds", () => {});\nit("adds twice", () => {});\n')
        (self.tree / "tests" / "helper.ts").write_text("export const h = 1;\n")

    def test_every_new_test_failing_on_the_old_code_passes(self):
        self.note()
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("red check passed", done.stdout)
        self.assertIn("keeps: tests/b.test.ts > keeps: a still adds (skipped", done.stdout)
        call = self.calls()[0]
        # It ran on the old code, in a throwaway tree, with the new test files.
        self.assertEqual(call["src"], "export const a = 1;\n")
        self.assertNotEqual(call["cwd"], str(self.tree))
        old = pathlib.Path(call["cwd"])
        self.assertFalse(old.exists(), "the throwaway tree was removed")
        self.assertIn("tests/b.test.ts", call["args"])
        self.assertIn("tests/a.test.ts", call["args"])
        self.assertIn("--reporter=json", call["args"])
        self.assertIn("--maxWorkers=4", call["args"])
        self.assertEqual(git(self.tree, "worktree", "list").count("\n"), 0)
        # The tree itself was not touched.
        self.assertEqual((self.tree / "src" / "a.ts").read_text(), "export const a = 2;\n")

    def test_the_old_tree_has_the_base_migrations_and_the_notes_test_helpers(self):
        self.note()
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, 0, done.stdout)
        call = self.calls()[0]
        self.assertFalse(call["migration"], "the note's migration reverted with the code")
        self.assertTrue(call["helper"], "a helper under tests/ is test-side and stays")

    def test_a_new_test_that_passes_on_the_old_code_is_refused_by_name(self):
        self.note()
        done = self.run_suite("red", "--base", self.base, env={"FAKE_STATUS": "writes b=passed"})
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("tests/b.test.ts > writes b: passed", done.stdout)
        self.assertNotIn("reads b: passed", done.stdout)

    def test_a_skipped_new_test_is_refused(self):
        self.note()
        done = self.run_suite("red", "--base", self.base, env={"FAKE_STATUS": "reads b=skipped"})
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("reads b: skipped", done.stdout)

    def test_a_file_that_cannot_load_counts_as_failed(self):
        self.note()
        done = self.run_suite("red", "--base", self.base, env={"FAKE_NO_LOAD": "tests/b.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("reads b: failed to load", done.stdout)

    def test_a_title_the_report_never_names_is_refused(self):
        self.note()
        (self.tree / "tests" / "b.test.ts").write_text('it(`reads ${what}`, () => {});\n')
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("not seen in the report", done.stdout)
        self.assertIn("plain string title", done.stdout)

    def test_a_note_with_no_new_title_is_refused(self):
        (self.tree / "src" / "a.ts").write_text("export const a = 2;\n")
        (self.tree / "tests" / "a.test.ts").write_text('it("adds", () => { expect(1).toBe(1); });\n')
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("no new test title", done.stdout)
        self.assertEqual(self.calls(), [])

    def test_only_keeps_titles_is_refused_too(self):
        (self.tree / "tests" / "a.test.ts").write_text('it("adds", () => {});\nit("keeps: x", () => {});\n')
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, mod.REFUSED)

    def test_titles_reads_the_three_quote_forms_once_each(self):
        text = 'it("a", f); test(\'b\', f); it.skip(`c`, f); it("a", g); it.each([1])("d %s", f)'
        self.assertEqual(mod.titles(text), ["a", "b", "c"])

    def test_a_committed_note_is_read_the_same_as_an_uncommitted_one(self):
        self.note()
        git(self.tree, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.tree, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "note")
        done = self.run_suite("red", "--base", self.base)
        self.assertEqual(done.returncode, 0, done.stdout)

    # A title that moved with its file, or into a new file, is not new. Measured
    # 2026-11-05 on Orderflow note 13: 63 kept titles in four moved files, each
    # refused as passing on the old code.

    def test_a_title_kept_through_a_git_mv_is_not_new(self):
        (self.tree / "tests" / "moved").mkdir()
        git(self.tree, "mv", "tests/a.test.ts", "tests/moved/a.test.ts")
        (self.tree / "tests" / "moved" / "a.test.ts").write_text(
            'it("adds", () => {});\nit("adds twice", () => {});\n')
        done = self.run_suite("red", "--base", self.base, env={"FAKE_STATUS": "adds=passed"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 new test(s) in 1 file(s)", done.stdout)
        self.assertNotIn("> adds:", done.stdout)

    def test_a_title_moved_from_a_deleted_file_into_a_new_one_is_not_new(self):
        git(self.tree, "rm", "-q", "tests/a.test.ts")
        (self.tree / "tests").mkdir(exist_ok=True)
        (self.tree / "tests" / "c.test.ts").write_text(
            'it("adds", () => {});\nit("adds twice", () => {});\n')
        done = self.run_suite("red", "--base", self.base, env={"FAKE_STATUS": "adds=passed"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 new test(s) in 1 file(s)", done.stdout)
        self.assertNotIn("> adds:", done.stdout)

    # A file the `Suite:` command does not run (Orderflow's `npm test` excludes
    # `tests/harness/**`) runs again under `Harness suite:` when the block names
    # one. Measured 2026-11-05 on tests/scaffold/vitest-config.test.ts.

    def test_a_file_the_suite_does_not_run_runs_under_the_harness_command(self):
        (self.tree / "tests" / "harness").mkdir()
        (self.tree / "tests" / "harness" / "reset.test.ts").write_text('it("resets", () => {});\n')
        done = self.run_suite("red", "--base", self.base,
                              env={"FAKE_NOT_RUN": "tests/harness/reset.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("tests/harness/reset.test.ts > resets: failed", done.stdout)
        first, second = self.calls()
        self.assertNotIn("--config", first["args"])
        self.assertIn("--config", second["args"])
        self.assertIn("tests/harness/reset.test.ts", second["args"])
        self.assertEqual(first["cwd"], second["cwd"], "the same throwaway tree")

    def test_a_file_the_suite_does_not_run_is_refused_without_a_harness_line(self):
        text = (self.tree / "CLAUDE.md").read_text()
        (self.tree / "CLAUDE.md").write_text(
            "\n".join(l for l in text.splitlines() if not l.startswith("Harness suite:")) + "\n")
        (self.tree / "tests" / "harness").mkdir()
        (self.tree / "tests" / "harness" / "reset.test.ts").write_text('it("resets", () => {});\n')
        done = self.run_suite("red", "--base", self.base,
                              env={"FAKE_NOT_RUN": "tests/harness/reset.test.ts"})
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("tests/harness/reset.test.ts > resets: not run", done.stdout)
        self.assertEqual(len(self.calls()), 1)


if __name__ == "__main__":
    unittest.main()
