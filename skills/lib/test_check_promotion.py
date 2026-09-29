#!/usr/bin/env python3
"""The promote script holds the cap, issue 37 of the tracker-tooling set.

The human promotes by hand, and this is the refusal they run at that moment.
It counts, over the seven days before it runs, the issues a tracker closed and the
issues it gained, and refuses a promotion that would make gained more than half
of closed unless it is given one line of reason. It also refuses a
`Kind: machinery` issue in a tracker whose README does not say
`Tracker: machinery`.

Every fixture is a temporary git repo whose commits carry the same author and
committer instant, so the window is driven by the dates the test sets.

Run: python3 test_check_promotion.py
"""

import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_promotion.py"
DAY = 86400


class Tracker:
    """A git repo at `root` holding a tracker at `root/track`."""

    def __init__(self, base: Path, readme=None):
        self.root = base / "repo"
        self.dir = self.root / "track"
        self.issues = self.dir / "issues"
        self.issues.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")
        if readme is not None:
            (self.dir / "README.md").write_text(readme)
        (self.root / "seed").write_text("seed\n")
        self.commit(30)

    def git(self, *args, env=None):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            capture_output=True, text=True, env=env).stdout

    def commit(self, days_ago: float):
        instant = f"@{int(time.time() - days_ago * DAY)} +0000"
        env = dict(os.environ, GIT_AUTHOR_DATE=instant, GIT_COMMITTER_DATE=instant)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", f"at {days_ago}", env=env)

    def write(self, name: str, status: str, kind="product"):
        lines = [f"Status: {status}", "Sentence: something"]
        if kind is not None:
            lines.append(f"Kind: {kind}")
        lines += ["Level: light", "", f"# {name}", "", "Words.", ""]
        path = self.issues / f"{name}.md"
        path.write_text("\n".join(lines))
        return path

    def closed_in_window(self, count: int, prefix="c", days_ago=3):
        """`count` issues added open 20 days ago and closed `days_ago` days ago."""
        for n in range(count):
            self.write(f"{prefix}{n}", "ready-for-agent")
        self.commit(20)
        for n in range(count):
            self.write(f"{prefix}{n}", "done — merged")
        self.commit(days_ago)

    def promoted_in_window(self, count: int, prefix="p", days_ago=2):
        for n in range(count):
            self.write(f"{prefix}{n}", "ready-for-agent")
        self.commit(days_ago)

    def candidate(self, kind="product", name="cand"):
        return self.write(name, "ready-for-agent", kind=kind)


def run(tracker: Tracker, issue: Path, *extra, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--tracker", str(tracker.dir),
         "--issue", str(issue), *extra],
        capture_output=True, text=True, cwd=cwd)


class TestCap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ac1_one_past_half_of_closed_is_refused(self):
        t = Tracker(self.base)
        t.closed_in_window(10)
        t.promoted_in_window(5)
        result = run(t, t.candidate())
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("closed 10", result.stderr)
        self.assertIn("promoted 5", result.stderr)
        self.assertIn("cap 5", result.stderr)

    def test_ac2_exactly_half_passes(self):
        t = Tracker(self.base)
        t.closed_in_window(10)
        t.promoted_in_window(4)
        result = run(t, t.candidate())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac3_over_cap_passes_and_writes_one_header_line(self):
        t = Tracker(self.base)
        t.closed_in_window(10)
        t.promoted_in_window(5)
        candidate = t.candidate()
        result = run(t, candidate, "--over-cap", "launch bug")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith(str(candidate.resolve())), result.stdout)
        lines = candidate.read_text().split("\n")
        written = [line for line in lines if line.startswith("Over-cap: ")]
        self.assertEqual(len(written), 1)
        self.assertRegex(written[0], r"^Over-cap: \d{4}-\d{2}-\d{2} launch bug$")
        # A header line: above the first blank line.
        self.assertLess(lines.index(written[0]), lines.index(""))

    def test_ac4_nothing_closed_refuses_any_promotion(self):
        t = Tracker(self.base)
        result = run(t, t.candidate())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("closed 0", result.stderr)

    def test_ac11_a_committed_candidate_is_not_counted_against_itself(self):
        t = Tracker(self.base)
        t.closed_in_window(10)
        t.promoted_in_window(4)
        candidate = t.candidate()
        t.commit(0.1)
        result = run(t, candidate)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("promoted 4", result.stdout)

    def test_ac12_an_empty_or_multi_line_reason_is_refused(self):
        t = Tracker(self.base)
        t.closed_in_window(10)
        t.promoted_in_window(5)
        candidate = t.candidate()
        before = candidate.read_text()
        for reason in ("", "   ", "a\nb", "a\rb"):
            with self.subTest(reason=reason):
                result = run(t, candidate, "--over-cap", reason)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(candidate.read_text(), before)


class TestKind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def tracker(self, name, readme):
        (self.base / name).mkdir()
        t = Tracker(self.base / name, readme=readme)
        t.closed_in_window(10)
        return t

    def test_ac5_machinery_passes_only_in_a_machinery_tracker(self):
        kind = "machinery. Every repo gets X"
        product = self.tracker("product", "# A tracker\n\nWords.\n")
        machinery = self.tracker("machinery", "# A tracker\n\nTracker: machinery\n")
        refused = run(product, product.candidate(kind=kind))
        passed = run(machinery, machinery.candidate(kind=kind))
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("Kind:", refused.stderr)
        self.assertNotIn("cap:", refused.stderr)
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_ac5_a_tracker_with_no_readme_is_a_product_tracker(self):
        t = self.tracker("bare", None)
        result = run(t, t.candidate(kind="machinery. Every repo gets X"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Kind:", result.stderr)

    def test_ac5_a_candidate_with_no_kind_line_is_refused(self):
        t = self.tracker("machinery", "Tracker: machinery\n")
        result = run(t, t.candidate(kind=None))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Kind:", result.stderr)

    def test_a_product_candidate_passes_a_product_tracker(self):
        t = self.tracker("product", None)
        result = run(t, t.candidate(kind="product"))
        self.assertEqual(result.returncode, 0, result.stderr)


class TestCounting(unittest.TestCase):
    """AC6 to AC10: what the history counts, read from the printed counts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.t = Tracker(self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def counts(self, cwd=None):
        result = run(self.t, self.t.candidate(), cwd=cwd)
        found = re.search(r"closed (\d+), promoted (\d+)", result.stdout)
        self.assertIsNotNone(found, result.stdout + result.stderr)
        return int(found.group(1)), int(found.group(2))

    def test_ac6_the_window_is_seven_days(self):
        self.t.closed_in_window(1, prefix="old", days_ago=8)
        self.t.closed_in_window(1, prefix="new", days_ago=6)
        self.t.promoted_in_window(1, prefix="p8", days_ago=8)
        self.t.promoted_in_window(1, prefix="p6", days_ago=6)
        self.assertEqual(self.counts(), (1, 1))

    def test_ac7_parked_is_not_closed_and_the_first_word_decides(self):
        self.t.write("a", "ready-for-agent")
        self.t.write("b", "ready-for-agent")
        self.t.write("c", "ready-for-agent")
        self.t.commit(20)
        self.t.write("a", "parked")
        self.t.write("b", "closed — merged to local main at abc")
        self.t.write("c", "wontfix")
        self.t.commit(2)
        self.assertEqual(self.counts(), (2, 0))

    def test_ac7_closed_is_dated_by_the_first_commit_that_set_it(self):
        self.t.write("a", "ready-for-agent")
        self.t.commit(20)
        self.t.write("a", "done")
        self.t.commit(10)
        self.t.write("a", "done — and a later note")
        self.t.commit(1)
        self.assertEqual(self.counts(), (0, 0))

    def test_ac8_a_file_added_already_closed_counts_in_neither(self):
        self.t.write("born", "done — master 2026-09-21")
        self.t.commit(2)
        self.assertEqual(self.counts(), (0, 0))

    def test_ac9_a_rename_keeps_its_first_add_date(self):
        self.t.write("old-name", "ready-for-agent")
        self.t.commit(9)
        self.t.git("mv", "track/issues/old-name.md", "track/issues/new-name.md")
        self.t.commit(1)
        self.assertEqual(self.counts(), (0, 0))

    def test_ac9_a_deleted_file_counts_in_neither(self):
        self.t.write("gone", "ready-for-agent")
        self.t.commit(20)
        self.t.write("gone", "done")
        self.t.commit(3)
        (self.t.issues / "gone.md").unlink()
        self.t.commit(2)
        self.assertEqual(self.counts(), (0, 0))

    def test_only_md_files_directly_inside_issues_count(self):
        (self.t.issues / "sub").mkdir()
        (self.t.issues / "sub" / "x.md").write_text("Status: ready-for-agent\n")
        (self.t.issues / "notes.txt").write_text("Status: ready-for-agent\n")
        (self.t.dir / "README.md").write_text("Status: ready-for-agent\n")
        self.t.commit(1)
        self.assertEqual(self.counts(), (0, 0))

    def test_ac10_history_is_the_trackers_repo_not_the_working_directory(self):
        self.t.closed_in_window(3)
        self.t.promoted_in_window(1)
        outside = self.base / "elsewhere"
        outside.mkdir()
        self.assertEqual(self.counts(cwd=outside), self.counts(cwd=self.t.root))
        self.assertEqual(self.counts(cwd=outside), (3, 1))


class TestNoHistory(unittest.TestCase):
    def test_a_repo_with_no_commits_is_refused_with_a_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            (root / "t" / "issues").mkdir(parents=True)
            candidate = root / "t" / "issues" / "c.md"
            candidate.write_text("Status: ready-for-agent\nKind: product\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--tracker", str(root / "t"),
                 "--issue", str(candidate)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("REFUSED", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


class TestLeavesTheRepoAlone(unittest.TestCase):
    """Must still be true: no issue file created, nothing committed or staged,
    and the only write is AC3's line into the candidate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Tracker(Path(self.tmp.name))
        self.t.closed_in_window(10)
        self.t.promoted_in_window(5)

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        return (sorted(p.name for p in self.t.issues.iterdir()),
                self.t.git("status", "--porcelain"),
                self.t.git("rev-parse", "HEAD"))

    def test_a_refusal_changes_nothing(self):
        candidate = self.t.candidate()
        before = self.snapshot()
        self.assertNotEqual(run(self.t, candidate).returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_an_over_cap_pass_changes_only_the_candidate(self):
        candidate = self.t.candidate()
        self.t.commit(0.1)
        names, _, head = self.snapshot()
        self.assertEqual(run(self.t, candidate, "--over-cap", "launch bug").returncode, 0)
        after_names, status, after_head = self.snapshot()
        self.assertEqual((after_names, after_head), (names, head))
        self.assertEqual(status.strip(), "M track/issues/cand.md")


if __name__ == "__main__":
    unittest.main()
