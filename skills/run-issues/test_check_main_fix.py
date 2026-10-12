#!/usr/bin/env python3
"""Tests for check_main_fix.py. Run: python3 test_check_main_fix.py

The human's ruling `q-fin4a2388-06` of 2026-10-11. On Sunday 11 October a test outside
run `batch-4a2388` redded on the calendar alone. The runner fixed it in its own gated
commit (`80bb4c7a`) while main fixed the same case a second way (`df-sn1011`). Each
case below builds a small repository with a run branch and a main.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_main_fix as check  # noqa: E402

SCRIPT = pathlib.Path(__file__).parent / "check_main_fix.py"
TEST = "tests/jobs/out-for-delivery-screen.test.tsx"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def commit(repo, path, body, message):
    file = pathlib.Path(repo) / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(body)
    git(repo, "add", path)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class Repo(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.folder.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        commit(self.repo, TEST, "reads the real clock\n", "the arrival sheet test")
        commit(self.repo, "app/sheet.ts", "sheet\n", "the arrival sheet")
        git(self.repo, "checkout", "-q", "-b", "run")

    def tearDown(self):
        self.folder.cleanup()

    def on_main(self, path, body, message):
        git(self.repo, "checkout", "-q", "main")
        sha = commit(self.repo, path, body, message)
        git(self.repo, "checkout", "-q", "run")
        return sha

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              capture_output=True, text=True)


class MainsLog(Repo):
    def test_main_holds_no_fix(self):
        result = self.run_script("--test", TEST)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no fix on main", result.stdout)

    def test_main_changed_the_test_after_the_fork(self):
        """The df-sn1011 shape: main fixed the same test the same morning."""
        sha = self.on_main(TEST, "freezes Date to a Saturday\n", "Sunday arrival-sheet test")
        result = self.run_script("--test", TEST)
        self.assertEqual(result.returncode, check.MAIN_HOLDS_FIX)
        self.assertIn(sha[:12], result.stdout)
        self.assertIn(f"git cherry-pick -x {sha[:12]}", result.stdout)

    def test_a_main_commit_naming_the_file_counts(self):
        """A fix in the code under test names the red file in its message."""
        sha = self.on_main("app/sheet.ts", "sheet, Sunday note\n",
                           "out-for-delivery-screen.test.tsx reds on Sunday: fix the note")
        self.assertEqual(check.fixes(self.repo, TEST, "main"), [(sha, check.subject(self.repo, sha))])

    def test_main_work_on_other_files_is_not_a_fix(self):
        self.on_main("app/other.ts", "other\n", "issue 504: the other screen")
        self.assertEqual(self.run_script("--test", TEST).returncode, 0)

    def test_a_fix_the_run_branch_already_holds_is_not_owed(self):
        sha = self.on_main(TEST, "freezes Date\n", "Sunday arrival-sheet test")
        git(self.repo, "cherry-pick", sha)
        self.assertEqual(self.run_script("--test", TEST).returncode, 0)

    def test_fixes_are_listed_oldest_first(self):
        first = self.on_main(TEST, "one\n", "first fix")
        second = self.on_main(TEST, "two\n", "second fix")
        result = self.run_script("--test", TEST)
        self.assertIn(f"git cherry-pick -x {first[:12]} {second[:12]}", result.stdout)


class NothingAsserted(Repo):
    def test_a_test_path_the_tree_does_not_hold_is_refused(self):
        """A typo must never read as "no fix on main"."""
        result = self.run_script("--test", "tests/jobs/no-such.test.tsx")
        self.assertEqual(result.returncode, check.NOTHING_ASSERTED)
        self.assertIn("not in HEAD", result.stderr)

    def test_a_missing_base_is_refused(self):
        result = self.run_script("--test", TEST, "--base", "trunk")
        self.assertEqual(result.returncode, check.NOTHING_ASSERTED)

    def test_a_folder_that_is_no_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run([sys.executable, str(SCRIPT), "--repo", empty, "--test", TEST],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, check.NOTHING_ASSERTED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
