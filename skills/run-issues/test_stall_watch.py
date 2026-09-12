"""What `stall_watch.py` must decide. The four verdicts are the whole file.

The measurement behind it: run `batch-200d42` stalled 208.8 minutes on 2026-09-11
and the in-session cron fired none of its chances, because a cron fires only while
the REPL is idle and a session behind a modal is mid-query. These tests pin the
replacement's decisions, including the one that says DO NOT resume.
"""

import os
import subprocess
import sys
import tempfile
import time
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stall_watch as sw

HERE = os.path.dirname(os.path.abspath(__file__))


def fake_lsof(cwds):
    def runner(cmd, **kw):
        return types.SimpleNamespace(
            stdout="".join(f"p1\nfcwd\nn{c}\n" for c in cwds), returncode=0
        )
    return runner


class StallWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def ledger(self, owner, worktree="/tmp/tree-a", age_minutes=0.0, batch="batch-aaa111"):
        d = os.path.join(self.tmp.name, "runs", batch)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "run.md")
        with open(p, "w") as fh:
            fh.write(f"# Run ledger — `{batch}`\n\nOwner: {owner}\nWorktree: {worktree}\n\nbody\n")
        if age_minutes:
            old = time.time() - age_minutes * 60
            os.utime(p, (old, old))
        return p

    # --- the owner line decides whether there is anything to watch at all ---

    def test_merged_run_is_not_watched(self):
        p = self.ledger("none — MERGED 2026-09-07 18:39", age_minutes=999)
        self.assertEqual(sw.check(p, 60)[0], sw.GONE)

    def test_awaiting_merge_is_not_watched(self):
        p = self.ledger("none — awaiting-merge 2026-09-11 11:25", age_minutes=999)
        self.assertEqual(sw.check(p, 60)[0], sw.GONE)

    def test_a_deliberate_halt_is_not_a_stall(self):
        """A halt wrote a HALT BLOCK and stopped on purpose. Nobody needs waking."""
        p = self.ledger("none — HALTED 2026-09-11 04:00", age_minutes=999)
        self.assertEqual(sw.check(p, 60)[0], sw.GONE)

    def test_missing_ledger_is_not_an_error(self):
        self.assertEqual(sw.check(os.path.join(self.tmp.name, "no", "run.md"), 60)[0], sw.GONE)

    # --- a moving run is left alone ---

    def test_fresh_ledger_is_moving(self):
        p = self.ledger("hopeful-turing-6a51a8 (session 4cef484b)", age_minutes=5)
        self.assertEqual(sw.check(p, 60)[0], sw.MOVING)

    def test_a_long_implement_attempt_is_not_a_stall(self):
        """SKILL.md: an attempt moves no status line for an hour. 59 minutes is work."""
        p = self.ledger("tree (session x)", age_minutes=59)
        self.assertEqual(sw.check(p, 60)[0], sw.MOVING)

    # --- the second test: alive or gone ---

    def test_stale_with_a_live_session_is_stalled(self):
        p = self.ledger("tree (session x)", age_minutes=209)
        verdict, msg = sw.check(p, 60, runner=fake_lsof(["/tmp/tree-a"]))
        self.assertEqual(verdict, sw.STALLED)
        self.assertIn("do not resume", msg.lower())

    def test_stale_with_no_session_is_dead_and_names_the_resume(self):
        p = self.ledger("tree (session x)", age_minutes=209)
        verdict, msg = sw.check(p, 60, runner=fake_lsof(["/somewhere/else"]))
        self.assertEqual(verdict, sw.DEAD)
        self.assertIn("/run-issues resume", msg)
        self.assertIn("/tmp/tree-a", msg)

    def test_a_subdirectory_of_the_worktree_counts_as_alive(self):
        p = self.ledger("tree (session x)", age_minutes=209)
        self.assertEqual(sw.check(p, 60, runner=fake_lsof(["/tmp/tree-a/src/lib"]))[0], sw.STALLED)

    def test_a_sibling_worktree_is_not_this_run(self):
        """`/tmp/tree-a2` starts with `/tmp/tree-a` as a string and is another tree."""
        p = self.ledger("tree (session x)", age_minutes=209)
        self.assertEqual(sw.check(p, 60, runner=fake_lsof(["/tmp/tree-a2"]))[0], sw.DEAD)

    def test_a_broken_liveness_test_withholds_the_resume(self):
        """STALLED withholds a resume. DEAD starts a second runner against a tree
        that may still be owned. Only one of those two mistakes is reversible."""
        def explode(cmd, **kw):
            raise OSError("lsof is not here")
        p = self.ledger("tree (session x)", age_minutes=209)
        self.assertEqual(sw.check(p, 60, runner=explode)[0], sw.STALLED)

    # --- the whole thing runs ---

    def test_once_exits_on_the_verdict(self):
        p = self.ledger("none — MERGED", age_minutes=999)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "stall_watch.py"),
             "--ledger", p, "--once", "--no-notify"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, sw.GONE, r.stderr)
        self.assertIn("done", r.stdout)

    def test_it_reads_only_the_head_of_the_ledger(self):
        """A run ledger grows to thousands of lines. The watch reads 4 KB."""
        p = self.ledger("tree (session x)", age_minutes=5)
        with open(p, "a") as fh:
            fh.write("Owner: LIAR\n" * 20000)
        self.assertTrue(sw.read_header(p)[0].startswith("tree "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
