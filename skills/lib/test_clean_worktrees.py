#!/usr/bin/env python3
"""Tests for clean_worktrees.

Every test here is about a REFUSAL except two. The happy path is cheap to get
right; the direction that loses work is deletion, so that is where the checks
are. The fixtures build a real git repo with one merged branch and one
unmerged branch, because the ancestry test is the fence and a fake cannot
prove git agrees with it.
"""

import io
import contextlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import clean_worktrees as cw


def run(cwd, *args):
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"{' '.join(args)}: {proc.stderr}")
    return proc.stdout


class Base(unittest.TestCase):
    """A repo with main, a merged branch+worktree and an unmerged one."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = pathlib.Path(self.tmp) / "main"
        self.repo.mkdir()
        run(self.repo, "git", "init", "-b", "main")
        run(self.repo, "git", "config", "user.email", "t@t")
        run(self.repo, "git", "config", "user.name", "t")
        (self.repo / "a.txt").write_text("one\n")
        run(self.repo, "git", "add", "-A")
        run(self.repo, "git", "commit", "-m", "first")

        self.wt = self.repo / ".claude" / "worktrees"
        self.wt.mkdir(parents=True)

        run(self.repo, "git", "worktree", "add", "-b", "merged-br", str(self.wt / "merged"))
        (self.wt / "merged" / "b.txt").write_text("two\n")
        run(self.wt / "merged", "git", "add", "-A")
        run(self.wt / "merged", "git", "commit", "-m", "second")
        run(self.repo, "git", "merge", "merged-br", "-m", "merge")

        run(self.repo, "git", "worktree", "add", "-b", "unmerged-br", str(self.wt / "unmerged"))
        (self.wt / "unmerged" / "c.txt").write_text("three\n")
        run(self.wt / "unmerged", "git", "add", "-A")
        run(self.wt / "unmerged", "git", "commit", "-m", "third")

        # No live-process check in the unit tests: lsof would answer about the
        # machine this suite runs on, not about the fixture.
        self._held = cw.held_by_process
        cw.held_by_process = lambda path: False
        self.addCleanup(setattr, cw, "held_by_process", self._held)

    def judge_all(self, here="/nowhere"):
        return {
            pathlib.Path(t["path"]).name: cw.judge(str(self.repo), t, "main", here)
            for t in cw.worktrees(str(self.repo))
        }

    def branches(self):
        return run(self.repo, "git", "branch", "--format=%(refname:short)").split()


class Judgement(Base):
    def test_merged_worktree_is_removable(self):
        ok, reason = self.judge_all()["merged"]
        self.assertTrue(ok)
        self.assertIn("is merged into main", reason)

    def test_unmerged_worktree_is_refused(self):
        ok, reason = self.judge_all()["unmerged"]
        self.assertFalse(ok)
        self.assertIn("not merged", reason)

    def test_main_checkout_is_never_removable(self):
        ok, reason = self.judge_all()[self.repo.name]
        self.assertFalse(ok)
        self.assertIn("main checkout", reason)

    def test_dirty_worktree_is_refused(self):
        (self.wt / "merged" / "untracked.txt").write_text("x\n")
        ok, reason = self.judge_all()["merged"]
        self.assertFalse(ok)
        self.assertIn("uncommitted or untracked", reason)

    def test_current_tree_is_refused(self):
        ok, reason = self.judge_all(here=str(self.wt / "merged"))["merged"]
        self.assertFalse(ok)
        self.assertIn("running in", reason)

    def test_live_process_is_refused(self):
        cw.held_by_process = lambda path: True
        ok, reason = self.judge_all()["merged"]
        self.assertFalse(ok)
        self.assertIn("running process", reason)

    def test_detached_head_is_refused(self):
        run(self.repo, "git", "worktree", "add", "--detach",
            str(self.wt / "detached"), "main")
        ok, reason = self.judge_all()["detached"]
        self.assertFalse(ok)
        self.assertIn("detached", reason)


class FailClosed(unittest.TestCase):
    """Anything the script cannot establish must read as 'keep'."""

    def test_missing_lsof_keeps_the_tree(self):
        real = cw.subprocess.run

        def boom(*a, **k):
            raise FileNotFoundError

        cw.subprocess.run = boom
        try:
            self.assertTrue(cw.held_by_process("/tmp"))
        finally:
            cw.subprocess.run = real

    def test_unreadable_tree_is_dirty(self):
        self.assertTrue(cw.is_dirty("/nonexistent-path-for-this-test"))


class Ancestry(Base):
    def test_is_merged_false_on_unknown_ref(self):
        self.assertFalse(cw.is_merged(str(self.repo), "no-such-branch", "main"))

    def test_is_merged_true_for_merged_branch(self):
        self.assertTrue(cw.is_merged(str(self.repo), "merged-br", "main"))

    def test_stale_branches_skips_base_live_and_unmerged(self):
        run(self.repo, "git", "branch", "orphan-merged", "main")
        live = {t["branch"] for t in cw.worktrees(str(self.repo)) if t.get("branch")}
        stale = cw.stale_branches(str(self.repo), "main", live)
        self.assertIn("orphan-merged", stale)
        self.assertNotIn("main", stale)
        self.assertNotIn("merged-br", stale)
        self.assertNotIn("unmerged-br", stale)


class EndToEnd(Base):
    def test_report_mode_deletes_nothing(self):
        before = self.branches()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cw.main(["--repo", str(self.repo)])
        self.assertEqual(code, 0)
        self.assertEqual(self.branches(), before)
        self.assertTrue((self.wt / "merged").exists())
        self.assertIn("report only", out.getvalue())

    def test_apply_removes_merged_and_keeps_unmerged(self):
        with contextlib.redirect_stdout(io.StringIO()):
            cw.main(["--repo", str(self.repo), "--apply"])
        self.assertNotIn("merged-br", self.branches())
        self.assertIn("unmerged-br", self.branches())
        self.assertFalse((self.wt / "merged").exists())
        self.assertTrue((self.wt / "unmerged").exists())

    def test_apply_leaves_unmerged_branch_after_repeat_runs(self):
        """The fence holds on a second pass, when the merged tree is gone."""
        with contextlib.redirect_stdout(io.StringIO()):
            cw.main(["--repo", str(self.repo), "--apply"])
            cw.main(["--repo", str(self.repo), "--apply"])
        self.assertIn("unmerged-br", self.branches())
        self.assertTrue((self.wt / "unmerged").exists())


if __name__ == "__main__":
    unittest.main()
