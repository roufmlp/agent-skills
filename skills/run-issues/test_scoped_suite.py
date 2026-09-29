#!/usr/bin/env python3
"""Cases for scoped_suite.py, the light road's one suite.

Each case drives the script as a command in a throwaway repository, against a
fake vitest that answers `list` from FAKE_LIST and records every `run`.

    python3 -m unittest test_scoped_suite
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "scoped_suite.py"
sys.path.insert(0, str(HERE))
import run_suite  # noqa: E402  (for `LOCK_ENV` only)

# `list --filesOnly --changed=<since> --json=<path>` writes FAKE_LIST, a comma
# list of repo-relative files, as vitest's JSON, and exits FAKE_LIST_EXIT.
# `run` appends its argv to `argv.jsonl`, writes a report where
# `--coverage.reportsDirectory=` points, prints a FAIL line per FAKE_FAILING
# and exits FAKE_EXIT.
FAKE_VITEST = textwrap.dedent("""\
    import json, os, pathlib, sys
    here = pathlib.Path(__file__).resolve().parent
    args = sys.argv[1:]
    with open(here / "argv.jsonl", "a") as handle:
        handle.write(json.dumps(args) + "\\n")
    if args[0] == "list":
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--json="))
        files = [f for f in os.environ.get("FAKE_LIST", "").split(",") if f]
        pathlib.Path(out).write_text(json.dumps(
            [{"file": str(pathlib.Path.cwd() / f)} for f in files]))
        sys.exit(int(os.environ.get("FAKE_LIST_EXIT", "0")))
    where = next(a.split("=", 1)[1] for a in args
                 if a.startswith("--coverage.reportsDirectory="))
    pathlib.Path(where).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(where) / "coverage-final.json").write_text("{}")
    for name in filter(None, os.environ.get("FAKE_FAILING", "").split(",")):
        print(f" FAIL  {name} > a suite > a case")
    print(" Test Files  2 passed (2)")
    sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
""")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class Repo(unittest.TestCase):

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.scratch.name)
        self.repo = root / "tree"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.ts").write_text("export const a = 1;\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "one")
        self.bin = root / "bin"
        self.bin.mkdir()
        self.vitest = self.bin / "vitest"
        self.vitest.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
        self.vitest.chmod(0o755)
        self.env = {**os.environ, run_suite.LOCK_ENV: str(root / "suite.lock")}

    def tearDown(self):
        self.scratch.cleanup()

    def scoped(self, *extra, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--vitest", str(self.vitest), *extra],
            cwd=str(self.repo), capture_output=True, text=True,
            env={**self.env, **(env or {})}, timeout=60)

    def argvs(self):
        path = self.bin / "argv.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def runs(self):
        return [argv for argv in self.argvs() if argv[0] == "run"]

    def records(self):
        path = pathlib.Path(git(self.repo, "rev-parse", "--absolute-git-dir")) \
            / "run-suite" / "records.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]


class TheSet(Repo):
    """The perf audit of 2026-09-28, fix 4. Three light-issue reds escaped
    because the scoped run read only the touched files: 181's brief-route,
    which imports a file 181 changed, and 254's design-values and 234c's
    standing-rules, repo-wide checks that import nothing it changed."""

    def test_vitest_names_the_tests_whose_imports_reach_a_change(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.scoped(env={"FAKE_LIST": "tests/documents/brief-route.test.ts"})
        listed = self.argvs()[0]
        self.assertEqual(listed[:2], ["list", "--filesOnly"])
        self.assertIn("--changed=HEAD", listed)
        [run] = self.runs()
        self.assertIn(str(self.repo.resolve() / "tests/documents/brief-route.test.ts"), run)

    def test_the_repo_wide_checks_run_whatever_the_change(self):
        self.scoped()
        [run] = self.runs()
        self.assertIn("tests/build-checks/", run)
        self.assertIn("standing-rules.test.", run)
        self.assertIn("--passWithNoTests", run)

    def test_the_repo_declares_its_own_checks(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "run-isolation.json").write_text(json.dumps(
            {"sweepTests": ["tests/sweeps/", "rules.test."]}))
        self.scoped()
        [run] = self.runs()
        self.assertIn("tests/sweeps/", run)
        self.assertNotIn("tests/build-checks/", run)

    def test_a_declaration_it_cannot_read_is_refused(self):
        (self.repo / ".claude").mkdir()
        for bad in ([], ["tests/", 3], "tests/", [""]):
            with self.subTest(bad=bad):
                (self.repo / ".claude" / "run-isolation.json").write_text(
                    json.dumps({"sweepTests": bad}))
                done = self.scoped()
                self.assertEqual(done.returncode, 3, done.stdout)
                self.assertEqual(self.runs(), [])

    def test_since_widens_the_diff(self):
        self.scoped("--since", "main")
        self.assertIn("--changed=main", self.argvs()[0])

    def test_a_list_that_fails_is_refused_and_nothing_runs(self):
        done = self.scoped(env={"FAKE_LIST_EXIT": "1"})
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.runs(), [])


class TheReading(Repo):

    def test_it_runs_with_coverage_and_records_a_scoped_reading(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        done = self.scoped(env={"FAKE_LIST": "a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        [run] = self.runs()
        self.assertIn("--coverage.enabled", run)
        record = self.records()[-1]
        self.assertEqual(record["stage"], "scoped")
        self.assertEqual(record["files"], ["a.test.ts"])
        self.assertTrue(pathlib.Path(record["coverage"]).exists())
        self.assertEqual(record["tree"], run_suite.tree_hash(self.repo))
        self.assertIn(f"Coverage report: {record['coverage']}", done.stdout)

    def test_a_red_run_passes_its_exit_and_names_its_files(self):
        done = self.scoped(env={"FAKE_EXIT": "1",
                                "FAKE_FAILING": "tests/build-checks/design-values.test.ts"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("tests/build-checks/design-values.test.ts", done.stdout)
        self.assertEqual(self.records()[-1]["failing"],
                         ["tests/build-checks/design-values.test.ts"])

    def test_a_second_run_on_a_green_tree_is_refused(self):
        self.scoped()
        done = self.scoped()
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(len(self.runs()), 1)

    def test_a_second_run_after_a_red_one_runs(self):
        self.scoped(env={"FAKE_EXIT": "1"})
        self.scoped()
        self.assertEqual(len(self.runs()), 2)

    def test_the_harness_runs_when_the_diff_touches_its_paths(self):
        counter = pathlib.Path(self.scratch.name) / "harness"
        harness = pathlib.Path(self.scratch.name) / "harness.py"
        harness.write_text("import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('ran')\n")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "run-isolation.json").write_text(json.dumps(
            {"harnessSuite": {"command": f"{sys.executable} {harness} {counter}",
                              "requiredWhen": ["scripts/**"]}}))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "contract")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "seed.mjs").write_text("x\n")
        done = self.scoped()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertTrue(counter.exists())
        self.assertTrue(self.records()[-1]["harness"]["run"])


class TheLightCommit(Repo):
    """The perf audit of 2026-09-28, fix 4. The runner's commit of a light
    issue waits for a green scoped reading of the tree it commits. A commit
    hook, where the reader has one, calls this at every issue's commit; this
    pack does not ship that hook."""

    def setUp(self):
        super().setUp()
        bin_dir = self.repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "vitest").write_text("")
        (self.repo / ".gitignore").write_text("node_modules/\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "ignore node_modules")

    def refusal(self, level="light"):
        import scoped_suite
        return scoped_suite.light_commit_refusal(self.repo, level)

    def test_a_tree_with_no_vitest_is_not_judged(self):
        """The skills repository runs light issues on Python suites. The
        scoped road is vitest's, so a tree without it keeps its old road."""
        (self.repo / "node_modules" / ".bin" / "vitest").unlink()
        self.assertIsNone(self.refusal())

    def test_with_no_scoped_reading_it_refuses_and_names_the_road(self):
        why = self.refusal()
        self.assertIn("scoped_suite.py", why)

    def test_a_green_reading_of_this_tree_passes(self):
        self.scoped()
        self.assertIsNone(self.refusal())

    def test_a_red_reading_refuses_and_names_its_files(self):
        self.scoped(env={"FAKE_EXIT": "1", "FAKE_FAILING": "tests/x.test.ts"})
        self.assertIn("tests/x.test.ts", self.refusal())

    def test_a_reading_of_an_older_tree_refuses(self):
        self.scoped()
        (self.repo / "a.ts").write_text("export const a = 9;\n")
        self.assertIn("scoped_suite.py", self.refusal())

    def test_run_state_written_after_the_reading_does_not_matter(self):
        self.scoped()
        (self.repo / ".scratch" / "feat").mkdir(parents=True)
        (self.repo / ".scratch" / "feat" / "run.md").write_text("committed\n")
        self.assertIsNone(self.refusal())

    def test_a_full_issue_is_not_judged_here(self):
        self.assertIsNone(self.refusal("full"))


if __name__ == "__main__":
    unittest.main()
