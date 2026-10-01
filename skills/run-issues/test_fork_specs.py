#!/usr/bin/env python3
"""Cases for fork_specs.py, the launch refusal of an issue whose named e2e spec
is already red at the fork.

Each case drives the script as a command against a throwaway repository and a
fake browser harness that prints what Playwright's list reporter prints.

    python3 -m unittest test_fork_specs
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
SCRIPT = HERE / "fork_specs.py"

CONTRAST = "e2e/contrast-and-targets.spec.ts"
CONFIG = "e2e/config-lists-at-two-widths.spec.ts"

# The four cases the review gate of run `batch-07853b` found red at the fork
# `9587b5a8`, as the spec at that commit titles them.
RED_AT_FORK = [
    f"[phone] › {CONTRAST}:179:5 › criterion 20: every control on five screens is "
    f"at least 24 px tall at 375 › /lines/1",
    f"[phone] › {CONTRAST}:189:3 › criterion 20: every control on five screens is "
    f"at least 24 px tall at 375 › a line page with two stages and a supplier's phone",
    f"[phone] › {CONTRAST}:206:5 › criterion 16: text boxes are 16 px on the phone "
    f"and 14 px on the laptop › at 375",
    f"[phone] › {CONTRAST}:233:3 › criteria 12 and 13: the colours a phone reads › "
    f"criterion 12: each email on /users reads in ink-2",
]

# Issue 313's criteria at run `batch-07853b`, cut to the six bullets.
ISSUE_313 = textwrap.dedent(f"""\
    # 313 — other pickers go compact

    Level: light

    ## Acceptance criteria

    - [ ] Each picker named above renders compact.
    - [ ] The Orders picker still loads its next page from the model.
    - [ ] The bill's saved supplier and orders are what they were before.
    - [ ] Setup still saves a product's stages and suppliers.
    - [ ] A report filter still narrows the report.
    - [ ] `{CONFIG}` and `{CONTRAST}` pass.

    ## Must still be true

    - `e2e/not-a-criterion.spec.ts` is never run by this check.
    """)

LEDGER = textwrap.dedent("""\
    # Run ledger — `batch-test`

    ## Status

    | # | Issue | Status | Row |
    |---|---|---|---|
    | 1 | 312 — job pickers go compact | queued | Level light. |
    | 2 | 313 — other pickers go compact | queued | Level light. |

    ## Carry-forward

    | # | Serves | Entry |
    |---|---|---|
    | 1 | 313 — and 315 | the picker's paging rule |
    """)

# The fake harness. FAKE_SPECS maps a spec to {"exit", "passed", "failed",
# "skipped"}; a spec it does not hold passes one case. Every call is appended
# to calls.jsonl with its working directory.
FAKE_HARNESS = textwrap.dedent("""\
    import json, os, pathlib, sys
    here = pathlib.Path(__file__).resolve().parent
    spec = sys.argv[-1]
    with open(here / "calls.jsonl", "a") as handle:
        handle.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
    plan = json.loads(os.environ.get("FAKE_SPECS", "{}")).get(spec, {"passed": 1})
    print(f"Running {plan.get('passed', 0) + len(plan.get('failed', []))} tests using 1 worker")
    failed = plan.get("failed", [])
    if failed:
        print(f"  {len(failed)} failed")
        for line in failed:
            print(f"    {line} ─────────")
    if plan.get("skipped"):
        print(f"  {plan['skipped']} skipped")
    if plan.get("passed"):
        print(f"  {plan['passed']} passed (35.0s)")
    sys.exit(plan.get("exit", 1 if failed else 0))
""")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class Fork(unittest.TestCase):

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.scratch.name)
        self.repo = root / "tree"
        (self.repo / "e2e").mkdir(parents=True)
        for spec in (CONTRAST, CONFIG):
            (self.repo / spec).write_text("test('x', () => {});\n")
        self.issue = self.repo / ".scratch" / "issues" / "313-other-pickers-go-compact.md"
        self.issue.parent.mkdir(parents=True)
        self.issue.write_text(ISSUE_313)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "fork")
        self.fork = git(self.repo, "rev-parse", "--short=8", "HEAD")
        self.run_dir = self.repo / ".scratch" / "runs" / "batch-test"
        self.run_dir.mkdir(parents=True)
        self.ledger = self.run_dir / "run.md"
        self.ledger.write_text(LEDGER)
        self.briefing = self.run_dir / "merge-briefing.md"
        self.briefing.write_text("# Merge briefing\n")
        self.bin = root / "bin"
        self.bin.mkdir()
        self.harness = self.bin / "harness.py"
        self.harness.write_text(FAKE_HARNESS)

    def tearDown(self):
        self.scratch.cleanup()

    def check(self, *extra, specs=None, issues=None):
        issues = issues or [self.issue]
        argv = [sys.executable, str(SCRIPT), "--tree", str(self.repo),
                "--harness", f"{sys.executable} {self.harness}",
                "--ledger", str(self.ledger), "--briefing", str(self.briefing)]
        for issue in issues:
            argv += ["--issue", str(issue)]
        return subprocess.run(
            [*argv, *extra], capture_output=True, text=True, timeout=60,
            env={**os.environ, "FAKE_SPECS": json.dumps(specs or {})})

    def calls(self):
        path = self.bin / "calls.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    def red_at_fork(self):
        return {CONTRAST: {"exit": 1, "passed": 9, "failed": RED_AT_FORK},
                CONFIG: {"passed": 4}}


class Issue313(Fork):
    """The human's ruling `q-07853b-04`, 2026-10-01. Issue 313's criterion 6 said
    `e2e/contrast-and-targets.spec.ts` passes. It was red at the fork
    `9587b5a8` in four cases no diff could reach, so the gate graded it
    `fault` and 313 stopped, with 315, 316, 317 and 314 behind it."""

    def test_issue_313_is_refused_and_its_red_cases_named(self):
        done = self.check(specs=self.red_at_fork())
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("REFUSED 313", done.stdout)
        self.assertIn(CONTRAST, done.stdout)
        for case in RED_AT_FORK:
            self.assertIn(case.split(" › ", 2)[2], done.stdout)

    def test_the_ledger_marks_313_blocked_and_names_the_cases(self):
        self.check(specs=self.red_at_fork())
        ledger = self.ledger.read_text()
        self.assertIn("| 2 | 313 — other pickers go compact | blocked (fork spec red) |", ledger)
        self.assertIn("| 1 | 312 — job pickers go compact | queued |", ledger)
        self.assertIn("| 1 | 313 — and 315 | the picker's paging rule |", ledger)
        self.assertIn(f"## Refused at the fork {self.fork}", ledger)
        self.assertIn(f"313 C6: `{CONTRAST}`", ledger)
        self.assertIn("each email on /users reads in ink-2", ledger)

    def test_the_merge_briefing_names_the_spec_and_its_cases(self):
        self.check(specs=self.red_at_fork())
        briefing = self.briefing.read_text()
        self.assertIn(f"## Refused at the fork {self.fork}", briefing)
        self.assertIn(f"313 C6: `{CONTRAST}`", briefing)
        self.assertIn("4 red cases", briefing)
        self.assertIn("a line page with two stages and a supplier's phone", briefing)

    def test_each_spec_runs_once_in_the_tree_through_the_harness(self):
        self.check(specs=self.red_at_fork())
        calls = self.calls()
        self.assertEqual(sorted(call["argv"][-1] for call in calls), sorted([CONFIG, CONTRAST]))
        self.assertTrue(all(pathlib.Path(call["cwd"]).resolve() == self.repo.resolve()
                            for call in calls))

    def test_an_invariant_that_names_a_spec_is_not_run(self):
        self.check(specs=self.red_at_fork())
        self.assertNotIn("e2e/not-a-criterion.spec.ts",
                         [call["argv"][-1] for call in self.calls()])

    def test_a_second_reading_writes_no_second_record(self):
        self.check(specs=self.red_at_fork())
        self.check(specs=self.red_at_fork())
        self.assertEqual(self.briefing.read_text().count(f"313 C6: `{CONTRAST}`"), 1)
        self.assertEqual(self.ledger.read_text().count(f"313 C6: `{CONTRAST}`"), 1)


class GreenAndOther(Fork):

    def test_green_specs_pass_and_write_nothing(self):
        done = self.check(specs={CONTRAST: {"passed": 13}, CONFIG: {"passed": 4}})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("Refused at the fork", self.ledger.read_text())
        self.assertNotIn("Refused at the fork", self.briefing.read_text())

    def test_one_spec_named_by_two_issues_runs_once(self):
        other = self.issue.parent / "316-designers-used-before.md"
        other.write_text(f"## Acceptance criteria\n\n1. `{CONTRAST}` passes.\n")
        done = self.check(specs=self.red_at_fork(), issues=[self.issue, other])
        self.assertEqual(done.returncode, 1)
        self.assertEqual([call["argv"][-1] for call in self.calls()].count(CONTRAST), 1)
        self.assertIn("REFUSED 316", done.stdout)

    def test_a_spec_absent_at_the_fork_is_not_run(self):
        """The issue writes it, so it has no reading at the fork."""
        other = self.issue.parent / "320-a-new-spec.md"
        other.write_text("## Acceptance criteria\n\n1. `e2e/new-road.spec.ts` passes.\n")
        done = self.check(issues=[other])
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.calls(), [])
        self.assertIn("e2e/new-road.spec.ts", done.stdout)

    def test_an_issue_naming_no_spec_runs_nothing(self):
        other = self.issue.parent / "321-no-spec.md"
        other.write_text("## Acceptance criteria\n\n1. The unit tests pass.\n")
        done = self.check(issues=[other])
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_a_red_exit_with_no_case_it_can_read_still_refuses(self):
        done = self.check(specs={CONTRAST: {"exit": 1, "passed": 0}, CONFIG: {"passed": 4}})
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED 313", done.stdout)
        self.assertIn("no red case", done.stdout)

    def test_a_spec_whose_every_case_skips_refuses(self):
        """A skip is not a pass: one project's `browserSkipReason()` turns a
        missing road into a green exit."""
        done = self.check(specs={CONTRAST: {"skipped": 13}, CONFIG: {"passed": 4}})
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("no case passed", done.stdout)

    def test_an_override_runs_the_issue_and_says_so(self):
        done = self.check("--override", "313", specs=self.red_at_fork())
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("| 2 | 313 — other pickers go compact | queued |", self.ledger.read_text())
        self.assertIn("override", self.briefing.read_text())
        self.assertIn("each email on /users reads in ink-2", self.briefing.read_text())

    def test_a_tree_that_is_not_the_fork_is_refused(self):
        (self.repo / CONTRAST).write_text("changed\n")
        done = self.check(specs=self.red_at_fork())
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.calls(), [])

    def test_a_harness_that_cannot_start_is_refused(self):
        argv = [sys.executable, str(SCRIPT), "--tree", str(self.repo),
                "--harness", str(self.bin / "no-such-harness"),
                "--ledger", str(self.ledger), "--briefing", str(self.briefing),
                "--issue", str(self.issue)]
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 3, done.stdout)

    def test_an_issue_file_that_will_not_open_is_refused(self):
        done = self.check(issues=[self.issue.parent / "999-gone.md"])
        self.assertEqual(done.returncode, 3, done.stdout)


if __name__ == "__main__":
    unittest.main()
