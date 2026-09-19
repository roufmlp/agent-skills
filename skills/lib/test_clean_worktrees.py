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

    def test_a_locked_tree_is_refused_and_says_who_locked_it(self):
        # `git worktree remove` cannot take a locked tree without `-f -f`, which
        # this script never passes. Listing one as removable is therefore an
        # instruction git will refuse every time. Measured in one repository on
        # 2026-09-19: ten of the eleven trees listed were held by live sessions
        # the human had ruled must stay, and the report proposed deleting all
        # ten while git refused all ten.
        run(self.repo, "git", "worktree", "lock", str(self.wt / "merged"),
            "--reason", "claude agent bridge-cse_01 (pid 873)")
        ok, reason = self.judge_all()["merged"]
        self.assertFalse(ok)
        self.assertIn("git locks this tree", reason)
        self.assertIn("pid 873", reason)

    def test_a_locked_tree_with_no_reason_still_refuses(self):
        run(self.repo, "git", "worktree", "lock", str(self.wt / "merged"))
        ok, reason = self.judge_all()["merged"]
        self.assertFalse(ok)
        self.assertIn("git locks this tree", reason)

    def test_detached_head_is_refused(self):
        run(self.repo, "git", "worktree", "add", "--detach",
            str(self.wt / "detached"), "main")
        ok, reason = self.judge_all()["detached"]
        self.assertFalse(ok)
        self.assertIn("detached", reason)


class Probe(unittest.TestCase):
    """What `held_by_process` must SEE, and what it must keep on not seeing.

    `lsof -c claude` matches a command NAMED claude. A session started from
    `~/.local/share/claude/versions/2.1.270` has the version number as its
    command name, so the named test alone is blind to it. These tests drive
    the two probes with fixed output rather than the machine's real processes.
    """

    def setUp(self):
        self.tree = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, ignore_errors=True)
        self.versions = str(cw.VERSIONS_DIR)
        self.real = cw.subprocess.run
        self.addCleanup(setattr, cw.subprocess, "run", self.real)

    def install(self, ps="", ps_rc=0, named="", by_pid="", fail=None):
        """Answer `ps -A` and the two `lsof` calls with fixed text."""
        seen = []

        def fake(cmd, *a, **k):
            seen.append(cmd)
            if cmd[0] == "ps":
                if fail == "ps":
                    raise FileNotFoundError
                return subprocess.CompletedProcess(cmd, ps_rc, ps, "")
            if cmd[0] == "lsof" and "-c" in cmd:
                if fail == "named":
                    raise subprocess.TimeoutExpired(cmd, 30)
                return subprocess.CompletedProcess(cmd, 0, named, "")
            if cmd[0] == "lsof" and "-p" in cmd:
                if fail == "by-pid":
                    raise subprocess.TimeoutExpired(cmd, 30)
                return subprocess.CompletedProcess(cmd, 0, by_pid, "")
            raise AssertionError(f"unexpected command: {cmd}")

        cw.subprocess.run = fake
        return seen

    def test_versioned_binary_in_the_tree_holds_it(self):
        """The bug of 2026-09-18: command name 2.1.270, invisible to -c claude."""
        self.install(
            ps=f"  4242 {self.versions}/2.1.270\n",
            named="",
            by_pid=f"p4242\nfcwd\nn{self.tree}\n",
        )
        self.assertTrue(cw.held_by_process(self.tree))

    def test_versioned_binary_asks_lsof_for_that_pid(self):
        seen = self.install(
            ps=f"  4242 {self.versions}/2.1.270\n",
            by_pid=f"n{self.tree}\n",
        )
        cw.held_by_process(self.tree)
        self.assertTrue(any("-p" in cmd and "4242" in cmd for cmd in seen))

    def test_a_command_named_claude_is_still_seen(self):
        self.install(ps="", named=f"n{self.tree}\n")
        self.assertTrue(cw.held_by_process(self.tree))

    def test_a_versioned_session_in_another_tree_does_not_hold_this_one(self):
        elsewhere = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, elsewhere, ignore_errors=True)
        self.install(
            ps=f"  4242 {self.versions}/2.1.270\n",
            by_pid=f"n{elsewhere}\n",
        )
        self.assertFalse(cw.held_by_process(self.tree))

    def test_a_subdirectory_of_the_tree_holds_it(self):
        self.install(
            ps=f"  4242 {self.versions}/2.1.270\n",
            by_pid=f"n{os.path.join(self.tree, 'src')}\n",
        )
        self.assertTrue(cw.held_by_process(self.tree))

    def test_an_unrelated_binary_is_not_probed(self):
        """A path that merely CONTAINS the versions dir is not under it."""
        seen = self.install(ps="  4242 /usr/bin/python3\n", named="")
        self.assertFalse(cw.held_by_process(self.tree))
        self.assertFalse(any("-p" in cmd for cmd in seen))

    def test_ps_failure_keeps_the_tree(self):
        self.install(ps_rc=1)
        self.assertTrue(cw.held_by_process(self.tree))

    def test_missing_ps_keeps_the_tree(self):
        self.install(fail="ps")
        self.assertTrue(cw.held_by_process(self.tree))

    def test_the_by_pid_probe_timing_out_keeps_the_tree(self):
        self.install(ps=f"  4242 {self.versions}/2.1.270\n", fail="by-pid")
        self.assertTrue(cw.held_by_process(self.tree))

    def test_the_named_probe_timing_out_keeps_the_tree(self):
        self.install(ps="", fail="named")
        self.assertTrue(cw.held_by_process(self.tree))


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
