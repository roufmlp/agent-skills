#!/usr/bin/env python3
"""Tracker-tooling issue 39: the finale's red file goes to the register.

`finale_reds.py` reads the newest `finale` record `run_suite.py` wrote, maps each
red file to the run's issue whose `Touches:` meets it, and appends one register
row per file to the tree's own shard. Every test builds a temporary git
repository holding one tracker, one run and one suite store.

Run: python3 test_finale_reds.py
"""

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_origin  # noqa: E402
import check_register_status  # noqa: E402
from finale_reds import main  # noqa: E402

BATCH = "batch-abc123"
FEATURE = "t"


def issue(touches):
    return "\n".join([
        "Status: in-progress", "Sentence: something", f"Touches: {touches}",
        "Kind: product", "Level: light", "", "# An issue", "", "## What to build", "",
        "Words.", ""])


def ledger(*issues, commits=None):
    commits = commits or {}
    lines = [f"# Run `{BATCH}`", "", "## Status", "", "| Issue | Size | Status | Stamps |",
             "|---|---|---|---|"]
    for number in issues:
        stamp = f"committed `{commits[number]}`" if number in commits else "attempt 1"
        lines.append(f"| {number} the issue | M | done | {stamp} |")
    return "\n".join(lines) + "\n"


class Run:
    """A git repository with `.scratch/t/issues/`, a run directory and a store."""

    def __init__(self, issues, ledger_text=None):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._dir.name))
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.tracker = self.root / ".scratch" / FEATURE
        (self.tracker / "issues").mkdir(parents=True)
        for name, text in issues.items():
            (self.tracker / "issues" / name).write_text(text, encoding="utf-8")
        self.run_dir = self.tracker / "runs" / BATCH
        self.run_dir.mkdir(parents=True)
        numbers = [name.split("-")[0] for name in issues]
        (self.run_dir / "run.md").write_text(ledger_text or ledger(*numbers), encoding="utf-8")
        self.store = self.root / ".git" / "run-suite"
        self.store.mkdir(parents=True)
        self.shard = self.tracker / "register.d" / "main" / "fs.md"

    def cleanup(self):
        self._dir.cleanup()

    def record(self, exit_code, failing, stage="finale", log=None):
        log = log or str(self.store / "logs" / f"20260927T0000{len(self.records())}-{stage}.log")
        entry = {"tree": "x", "stage": stage, "exit": exit_code, "command": ["t"],
                 "started": "2026-09-27T00:00:00+00:00", "seconds": 1.0, "log": log,
                 "failing": failing}
        with open(self.store / "records.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        return log

    def records(self):
        path = self.store / "records.jsonl"
        return path.read_text().splitlines() if path.exists() else []

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def run(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--run", str(self.run_dir), "--trees", str(self.root), *extra])
        return code, out.getvalue() + err.getvalue()

    def rows(self):
        """Each row as `check_register_status.rows` reads it, with `.line` the row's text."""
        if not self.shard.exists():
            return []
        text = self.shard.read_text(encoding="utf-8").splitlines()
        return [row._replace(line=text[row.line - 1], header=text[row.header.line - 1])
                for row in check_register_status.rows("\n".join(text))]

    def digest(self):
        return hashlib.sha256(self.shard.read_bytes()).hexdigest() if self.shard.exists() else None


class Fixture(unittest.TestCase):
    ISSUES = {"12-orders.md": issue("`src/lib/**`")}

    def setUp(self):
        self.t = Run(self.ISSUES)

    def tearDown(self):
        self.t.cleanup()


class ARedFileNamesItsIssue(Fixture):
    """AC1: the glob case of `Touches:` maps a red file to issue 12."""

    def test_one_row_carries_the_issue_and_the_run(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        code, out = self.t.run()
        self.assertEqual(code, 0, out)
        rows = self.t.rows()
        self.assertEqual(len(rows), 1, out)
        self.assertEqual(rows[0].origin, f"12/{BATCH}")
        self.assertIn("src/lib/orders.test.ts", rows[0].line)
        self.assertEqual(rows[0].status, "open")
        self.assertTrue(rows[0].row_id.startswith("fs12-"), rows[0].row_id)

    def test_the_cells_sit_in_the_registers_own_columns(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.run()
        header = [c.strip() for c in self.t.rows()[0].header.strip().strip("|").split("|")]
        self.assertEqual(header, ["ID", "one-line summary", "audience", "severity", "status",
                                  "origin", "owner-notes"])
        cells = [c.strip() for c in self.t.rows()[0].line.strip().strip("|").split("|")]
        self.assertEqual(cells[2:5], ["tester", "high", "open"])

    def test_the_id_is_printed_for_the_briefing(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        _, out = self.t.run()
        self.assertIn(self.t.rows()[0].row_id, out)


class ARedFileNoIssueTouched(Fixture):
    """AC2: a red file nothing in the run touched is `unknown/<batch-id>`."""

    def test_the_origin_is_the_legal_null(self):
        self.t.record(1, ["src/other/thing.test.ts"])
        self.t.run()
        rows = self.t.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].origin, f"unknown/{BATCH}")
        self.assertIn("src/other/thing.test.ts", rows[0].line)


class AGreenSuiteWritesNothing(Fixture):
    """AC3: the newest `finale` record decides."""

    def test_a_green_record_leaves_the_shard_as_it_was(self):
        self.t.record(0, [])
        before = self.t.digest()
        code, out = self.t.run()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.t.digest(), before)
        self.assertFalse(self.t.shard.exists())

    def test_a_red_record_followed_by_a_green_re_run_writes_nothing(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.record(0, [])
        self.t.run()
        self.assertEqual(self.t.rows(), [])

    def test_a_record_at_another_stage_is_not_read(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.record(0, [], stage="issue")
        self.t.run()
        self.assertEqual(len(self.t.rows()), 1)

    def test_no_finale_record_is_a_refusal_not_a_pass(self):
        self.t.record(1, ["src/lib/orders.test.ts"], stage="issue")
        code, out = self.t.run()
        self.assertEqual(code, 2, out)
        self.assertFalse(self.t.shard.exists())


class TheRowsPassBothRegisterChecks(Fixture):
    """AC5: the finale's own two checks pass on the shard, and one grades a row."""

    def test_check_origin_grades_one_row(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.run()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = check_origin.main(["--register", str(self.t.shard)])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("1 row(s) graded", out.getvalue())

    def test_the_register_sweep_passes(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.run()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = check_register_status.main([str(self.t.shard), "--sweep", BATCH])
        self.assertEqual(code, 0, out.getvalue())


class ARedSuiteNamingNoFile(Fixture):
    """AC6: Python's runners name no file to `run_suite.failing_files`."""

    def test_one_row_carries_the_log(self):
        log = self.t.record(1, [])
        self.t.run()
        rows = self.t.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].origin, f"unknown/{BATCH}")
        self.assertIn(log, rows[0].line)


class TheScriptReEnters(Fixture):
    """AC7: a second pass over the same record writes nothing."""

    def test_the_second_run_leaves_the_shard_byte_identical(self):
        self.t.record(1, ["src/lib/orders.test.ts", "src/other/thing.test.ts"])
        self.t.run()
        before = self.t.digest()
        code, out = self.t.run()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.t.digest(), before)

    def test_a_new_red_record_writes_new_rows_with_new_ids(self):
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.run()
        self.t.record(1, ["src/lib/orders.test.ts"])
        self.t.run()
        ids = [row.row_id for row in self.t.rows()]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2, ids)


class EveryIssueThatMeetsIsNamed(unittest.TestCase):
    """Q1's default: every issue whose `Touches:` meets the file, and every issue
    whose own commit changed it. More than one leaves no single issue."""

    def test_two_issues_meeting_one_file_give_the_run_only(self):
        t = Run({"12-a.md": issue("`src/lib/**`"), "13-b.md": issue("`src/lib/`")})
        self.addCleanup(t.cleanup)
        t.record(1, ["src/lib/orders.test.ts"])
        t.run()
        rows = t.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].origin, f"unknown/{BATCH}")
        self.assertIn("12", rows[0].line)
        self.assertIn("13", rows[0].line)

    def test_an_issue_whose_commit_changed_the_file_is_named(self):
        t = Run({"14-c.md": issue("`docs/only.md`")})
        self.addCleanup(t.cleanup)
        (t.root / "src").mkdir()
        (t.root / "src" / "x.test.ts").write_text("x\n")
        t.git("add", "src/x.test.ts")
        t.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "14")
        sha = t.git("rev-parse", "--short=8", "HEAD")
        (t.run_dir / "run.md").write_text(ledger("14", commits={"14": sha}))
        t.record(1, ["src/x.test.ts"])
        t.run()
        self.assertEqual(t.rows()[0].origin, f"14/{BATCH}")

    def test_an_issue_saying_none_meets_nothing(self):
        t = Run({"15-d.md": issue("none")})
        self.addCleanup(t.cleanup)
        t.record(1, ["src/lib/orders.test.ts"])
        t.run()
        self.assertEqual(t.rows()[0].origin, f"unknown/{BATCH}")


class CoverageRefusalsBecomeRows(Fixture):
    """AC8: a changed line the report shows unexecuted becomes a row, mapped as AC1."""

    def commit(self, path, text):
        full = self.t.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text)
        self.t.git("add", path)
        self.t.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", path)

    def report(self, hits):
        source = str(self.t.root / "src/lib/orders.ts")
        report = self.t.root / "coverage" / "coverage-final.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps({source: {
            "path": source,
            "statementMap": {str(i): {"start": {"line": i + 1}, "end": {"line": i + 1}}
                             for i in range(len(hits))},
            "s": {str(i): hit for i, hit in enumerate(hits)}}}))
        return report

    def test_an_unexecuted_changed_line_names_its_file(self):
        self.commit("README", "base\n")
        base = self.t.git("rev-parse", "HEAD")
        self.commit("src/lib/orders.ts", "const a = 1;\nconst b = 2;\n")
        self.commit("src/lib/orders.test.ts", "test\n")
        report = self.report([1, 0])
        self.t.record(0, [])
        code, out = self.t.run("--coverage", str(report), "--diff-range", f"{base}..HEAD")
        self.assertEqual(code, 0, out)
        rows = self.t.rows()
        self.assertEqual(len(rows), 1, out)
        self.assertIn("src/lib/orders.ts", rows[0].line)
        self.assertEqual(rows[0].origin, f"12/{BATCH}")

    def test_a_covered_diff_writes_nothing(self):
        self.commit("README", "base\n")
        base = self.t.git("rev-parse", "HEAD")
        self.commit("src/lib/orders.ts", "const a = 1;\n")
        self.commit("src/lib/orders.test.ts", "test\n")
        report = self.report([3])
        self.t.record(0, [])
        self.t.run("--coverage", str(report), "--diff-range", f"{base}..HEAD")
        self.assertEqual(self.t.rows(), [])


# Built from two halves so this file never holds the string itself: issue 38's
# silence check, which this pack does not ship, greps `run-issues/` for it at a
# ledger's fingerprint.
SPAWN = "`promotion`" + " agent"


class PromotionLeftTheRun(unittest.TestCase):
    """AC4 and the seam from issue 38: the spawn string names no file under
    `run-issues/`, so issue 38's silence check owes no later run a promotion."""

    def test_no_file_under_run_issues_names_the_spawn(self):
        found = [p.name for p in HERE.iterdir()
                 if p.is_file() and SPAWN in p.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(found, [])

    def test_the_effort_table_has_no_promotion_row(self):
        self.assertNotIn("| `promotion` |", (HERE / "SKILL.md").read_text(encoding="utf-8"))

    def test_the_finale_runs_this_script_after_its_suite(self):
        finale = (HERE / "finale.md").read_text(encoding="utf-8")
        command = "run-issues/finale_reds.py --run"
        self.assertIn(command, finale)
        self.assertLess(finale.index("--stage finale"), finale.index(command))
        self.assertLess(finale.index(command), finale.index("2. **Judgment.**"))

    def test_a_light_run_skips_no_finale_step(self):
        finale = (HERE / "finale.md").read_text(encoding="utf-8")
        for line in finale.splitlines():
            if "Level: light" in line:
                self.assertNotIn("finale-judgment", line)
                self.assertNotIn("finale-board", line)


if __name__ == "__main__":
    unittest.main()
