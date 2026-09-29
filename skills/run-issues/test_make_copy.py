#!/usr/bin/env python3
"""Cases for make_copy.py, the one recipe for a gate's private copy.

Each case builds a throwaway repository with a linked worktree, which is the
shape of a run tree, puts uncommitted work in it, and drives the script as a
command.

    python3 -m unittest test_make_copy
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "make_copy.py"
sys.path.insert(0, str(HERE))
import run_suite  # noqa: E402  (for `tree_hash` only)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def status(repo):
    """`git status --porcelain`, one entry per line, leading blanks kept."""
    return sorted(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                 check=True, capture_output=True,
                                 text=True).stdout.splitlines())


class RunTree(unittest.TestCase):
    """A main checkout, a linked worktree on its own branch, and in the
    worktree the three kinds of uncommitted work an implementer leaves: an
    edit, a new file and a deletion."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.scratch.name)
        main = root / "main"
        main.mkdir()
        git(main, "init", "-q", "-b", "main")
        git(main, "config", "user.email", "t@example.com")
        git(main, "config", "user.name", "t")
        (main / ".gitignore").write_text("node_modules/\n.env.run.local\n")
        (main / "a.ts").write_text("export const a = 1;\n")
        (main / "gone.ts").write_text("export const gone = 1;\n")
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "one")
        self.tree = root / "run-tree"
        git(main, "worktree", "add", "-q", "-b", "claude/run-issues-batch-abc123",
            str(self.tree))
        (self.tree / "b.ts").write_text("export const b = 2;\n")
        git(self.tree, "add", "b.ts")
        git(self.tree, "commit", "-q", "-m", "Issue 01: two")
        (self.tree / "a.ts").write_text("export const a = 3;\n")
        (self.tree / "new.test.ts").write_text("it('reads', () => {});\n")
        (self.tree / "gone.ts").unlink()
        (self.tree / ".env.run.local").write_text("DATABASE_URL=run\n")
        (self.tree / "node_modules").mkdir()
        (self.tree / "node_modules" / "dep.js").write_text("module.exports = 1;\n")
        self.dest = root / "copies" / "verify-01"

    def tearDown(self):
        self.scratch.cleanup()

    def make(self, dest=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--tree", str(self.tree),
             "--dest", str(dest or self.dest)],
            capture_output=True, text=True, timeout=60)


class ACopy(RunTree):

    def test_it_carries_the_history_of_the_run_branch(self):
        made = self.make()
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        self.assertEqual(git(self.dest, "log", "--format=%s"), "Issue 01: two\none")
        self.assertEqual(git(self.dest, "rev-parse", "HEAD"),
                         git(self.tree, "rev-parse", "HEAD"))

    def test_it_carries_the_uncommitted_work_as_uncommitted_work(self):
        self.make()
        self.assertEqual((self.dest / "a.ts").read_text(), "export const a = 3;\n")
        self.assertTrue((self.dest / "new.test.ts").exists())
        self.assertFalse((self.dest / "gone.ts").exists())
        self.assertEqual(status(self.dest),
                         [" D gone.ts", " M a.ts", "?? new.test.ts"])

    def test_it_hashes_to_the_tree_it_was_copied_from(self):
        self.make()
        self.assertEqual(run_suite.tree_hash(self.dest), run_suite.tree_hash(self.tree))

    def test_node_modules_is_the_run_trees_own_through_a_symlink(self):
        self.make()
        self.assertTrue((self.dest / "node_modules").is_symlink())
        self.assertEqual((self.dest / "node_modules").resolve(),
                         (self.tree / "node_modules").resolve())

    def test_a_write_in_the_copy_never_reaches_the_run_tree(self):
        self.make()
        self.assertNotEqual(os.stat(self.dest / "a.ts").st_ino,
                            os.stat(self.tree / "a.ts").st_ino)
        (self.dest / "a.ts").write_text("export const a = 'mutant';\n")
        git(self.dest, "add", "-A")
        self.assertEqual((self.tree / "a.ts").read_text(), "export const a = 3;\n")
        self.assertEqual(status(self.tree),
                         [" D gone.ts", " M a.ts", "?? new.test.ts"])

    def test_it_names_the_run_tree_it_came_from(self):
        self.make()
        self.assertEqual(git(self.dest, "config", "--get", "run-suite.source"),
                         str(self.tree.resolve()))

    def test_it_prints_the_copy_and_the_hash_they_share(self):
        made = self.make()
        self.assertIn(str(self.dest), made.stdout)
        self.assertIn(run_suite.tree_hash(self.tree), made.stdout)


class ARefusal(RunTree):

    def test_a_destination_that_holds_files_is_refused_and_left_alone(self):
        self.dest.mkdir(parents=True)
        (self.dest / "keep.txt").write_text("another gate's work\n")
        made = self.make()
        self.assertEqual(made.returncode, 3)
        self.assertIn("REFUSED", made.stdout)
        self.assertEqual((self.dest / "keep.txt").read_text(), "another gate's work\n")

    def test_a_destination_inside_the_run_tree_is_refused(self):
        made = self.make(self.tree / "verify-01")
        self.assertEqual(made.returncode, 3)
        self.assertFalse((self.tree / "verify-01").exists())

    def test_a_tree_that_is_not_a_git_work_tree_is_refused(self):
        plain = pathlib.Path(self.scratch.name) / "plain"
        plain.mkdir()
        made = subprocess.run([sys.executable, str(SCRIPT), "--tree", str(plain),
                               "--dest", str(self.dest)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(made.returncode, 3)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
