#!/usr/bin/env python3
"""Tests for mint_carved, and for the refusal in `next_batch.py` that makes it
impossible to forget. The fixture is one real carved issue, cut down:
its Undo criterion carved, the rest shipped."""

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mint_carved

next_batch = mint_carved.next_batch

ISSUE = """Status: ready-for-agent
Sentence: Admin decides credit on the record, and a cancel ask lands

Touches: `src/model/credit.ts`
Kind: product
Level: full
Run: operations 3
Claims: OPS-S13

# Admin decides credit on the record

## Acceptance criteria

- [ ] The credit sheet shows the record.
      Fixture: job 50.
- [ ] Undo after "Approve credit" appends and never deletes.
      Fixture: job 50; a second job refuses the Undo.
- [ ] The cancel ask lands with its reason.

A note under the criteria, which is not a criterion.

## Must still be true

- **M1 — history is append-only.**

## Blocked by

- 369-second-round-note
"""

ROW = ("| 370 — credit and cancel ask | {status} | Gate: "
       "`run-issues-review-gate-critical`. attempt 1; gates 1: verify=reject "
       "review=reject charge=strike (rows rn-a1b2c3-370r-01 to -04); "
       "carve after gates 1: C2; attempt 2 (carve); gates 2: verify=pass "
       "review=pass charge=none; row rn-a1b2c3-370r-05 |")


def ledger_text(status="done (carved)", state="awaiting-merge",
                row=ROW):
    return (
        "# Run ledger — `batch-a1b2c3`\n\n"
        "Branch: `claude/run-issues-369-380-a1b2c3`. Register prefix: "
        "`rn-a1b2c3-NN`.\n\n"
        "| Issue | Status | Row |\n|---|---|---|\n"
        "| 369 — second round note | done | attempt 1 |\n"
        + row.format(status=status) + "\n\n"
        f"State: {state}\n")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = Path(os.path.realpath(self.scratch.name)) / "repo"
        self.feature = self.repo / ".scratch" / "feat"
        self.issues = self.feature / "issues"
        self.run = self.feature / "runs" / "batch-a1b2c3"
        (self.run / "verdicts").mkdir(parents=True)
        self.issues.mkdir(parents=True)
        (self.issues / "369-second-round-note.md").write_text(
            "Status: done\n\n# 369\n")
        (self.issues / "370-credit-and-cancel-ask.md").write_text(ISSUE)
        for name in ("370-attempt-1-review.md", "370-attempt-1-verify.md",
                     "370-attempt-2-review.md", "369-attempt-1-review.md"):
            (self.run / "verdicts" / name).write_text("# verdict\n")
        self.git("init", "-q", "-b", "main")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                 "--allow-empty", "-m", "root")
        store = Path(self.scratch.name) / "claims"
        patcher = mock.patch.dict(os.environ, {"CLAIM_STORE": str(store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.scratch.cleanup)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True,
                       capture_output=True)

    def write_ledger(self, **kwargs):
        (self.run / "run.md").write_text(ledger_text(**kwargs))

    def mint(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mint_carved.main(["--ledger", str(self.run / "run.md"),
                                     "--issues", str(self.issues)])
        return code, out.getvalue(), err.getvalue()

    def minted(self):
        return [path for path in self.issues.glob("*.md")
                if path.name.endswith("-carved.md")]


class AfterTheMerge(Fixture):
    def test_an_unmerged_run_is_refused(self):
        self.write_ledger()
        code, _, err = self.mint()
        self.assertEqual(code, 1)
        self.assertIn("has not merged", err)
        self.assertEqual(self.minted(), [])

    def test_a_run_whose_branch_is_in_main_counts_as_merged(self):
        """One run merged and its ledger still read
        `State: awaiting-merge`, so the branch is the second proof."""
        self.git("branch", "claude/run-issues-369-380-a1b2c3")
        self.write_ledger()
        code, out, err = self.mint()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.minted()), 1, out)

    def test_a_run_whose_branch_is_not_in_main_is_refused(self):
        self.git("checkout", "-q", "-b", "claude/run-issues-369-380-a1b2c3")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                 "--allow-empty", "-m", "run work")
        self.git("checkout", "-q", "main")
        self.write_ledger()
        code, _, err = self.mint()
        self.assertEqual(code, 1)
        self.assertIn("has not merged", err)


class APartCarve(Fixture):
    def setUp(self):
        super().setUp()
        self.write_ledger(state="merged 2026-10-06")

    def test_the_carved_criterion_is_minted_as_a_needs_harden_issue(self):
        code, out, err = self.mint()
        self.assertEqual(code, 0, err)
        [path] = self.minted()
        text = path.read_text()
        self.assertTrue(text.startswith("Status: needs-harden\n"))
        self.assertIn("Origin: 370/batch-a1b2c3", text)
        self.assertIn("Carved from: issue 370 in run batch-a1b2c3, criteria C2, "
                      "after gates 1", text)
        self.assertIn('Undo after "Approve credit" appends', text)
        self.assertIn("a second job refuses the Undo", text)
        self.assertNotIn("The credit sheet shows the record", text)
        self.assertNotIn("A note under the criteria", text)
        self.assertIn("M1 — history is append-only", text)
        self.assertIn("`rn-a1b2c3-370r-01`", text)
        self.assertIn("`rn-a1b2c3-370r-05`", text)
        self.assertIn("370-attempt-1-verify.md", text)
        self.assertNotIn("369-attempt-1-review.md", text)
        self.assertIn("charge=strike", text)
        self.assertIn("- 370-credit-and-cancel-ask", text)

    def test_the_minted_issue_claims_no_prototype_row(self):
        # A carved issue claims nothing until hardening says otherwise, and claiming
        # nothing is the absence of the line: one project's prototype-pairs build
        # check reads `Claims: none` as a row ID called "none" and refuses it
        # (red on 2026-10-09).
        self.mint()
        [path] = self.minted()
        self.assertNotRegex(path.read_text(), r"(?m)^Claims:")

    def test_the_minted_issue_is_one_the_tracker_reads(self):
        self.mint()
        issues = next_batch.load_issues(self.issues)
        [path] = self.minted()
        number = path.name.split("-")[0]
        self.assertEqual(issues[number].status, "needs-harden")
        self.assertEqual(issues[number].unreadable, "")

    def test_the_source_keeps_a_moved_box_in_the_carved_place(self):
        self.mint()
        [path] = self.minted()
        body = (self.issues / "370-credit-and-cancel-ask.md").read_text()
        self.assertIn(f"- [ ] MOVED to issue {path.name.split('-')[0]}", body)
        self.assertNotIn("Undo after", body)
        self.assertIn("The credit sheet shows the record", body)
        self.assertIn("The cancel ask lands", body)
        self.assertIn("A note under the criteria", body)
        names = [n for n, _ in mint_carved.ids.criteria(body)]
        self.assertEqual(len(names), 3, "the place numbers must not move")

    def test_a_second_run_mints_nothing_new(self):
        self.mint()
        code, out, err = self.mint()
        self.assertEqual(code, 0, err)
        self.assertIn("already minted", out)
        self.assertEqual(len(self.minted()), 1)

    def test_a_carve_stamp_it_cannot_read_is_refused(self):
        self.write_ledger(state="merged", row=ROW.replace(
            "carve after gates 1: C2", "carve after gates 1: C9"))
        code, _, err = self.mint()
        self.assertEqual(code, 1)
        self.assertIn("C9", err)
        self.assertEqual(self.minted(), [])


class AWholeCarve(Fixture):
    WHOLE = ("| 370 — credit and cancel ask | {status} | attempt 1; gates 1: "
             "verify=reject review=reject charge=strike; carve after gates 1: "
             "C2; attempt 2 (carve); gates 2: verify=reject review=reject "
             "charge=strike; carve whole after gates 2 |")

    def setUp(self):
        super().setUp()
        self.write_ledger(status="carved (whole)", state="merged", row=self.WHOLE)

    def test_nothing_is_minted_and_the_issue_goes_back_to_hardening(self):
        code, out, err = self.mint()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.minted(), [])
        body = (self.issues / "370-credit-and-cancel-ask.md").read_text()
        self.assertTrue(body.startswith("Status: needs-harden"))
        self.assertIn("## Carved whole by run batch-a1b2c3", body)
        self.assertIn("carve whole after gates 2", body)
        issues = next_batch.load_issues(self.issues)
        self.assertEqual(issues["370"].status, "needs-harden")

    def test_a_second_run_sends_nothing_back_twice(self):
        self.mint()
        code, out, _ = self.mint()
        self.assertIn("already sent back", out)
        body = (self.issues / "370-credit-and-cancel-ask.md").read_text()
        self.assertEqual(body.count("## Carved whole by run"), 1)


class TheNextBatchRefusesAnUnmintedCarve(Fixture):
    def runs(self):
        return next_batch.unminted_carves(self.feature / "runs", self.issues)

    def test_a_merged_part_carve_with_no_minted_issue_is_listed(self):
        self.write_ledger(state="merged")
        self.assertEqual(self.runs(), [("batch-a1b2c3", "370", "done (carved)")])
        self.mint()
        self.assertEqual(self.runs(), [])

    def test_a_merged_whole_carve_is_listed_until_it_is_sent_back(self):
        self.write_ledger(status="carved (whole)", state="merged",
                          row=AWholeCarve.WHOLE)
        self.assertEqual(self.runs(), [("batch-a1b2c3", "370", "carved (whole)")])
        self.mint()
        self.assertEqual(self.runs(), [])

    def test_an_unmerged_carve_waits_for_its_merge(self):
        self.write_ledger()
        self.assertEqual(self.runs(), [])

    def test_the_next_batch_command_refuses_and_names_the_mint(self):
        self.write_ledger(state="merged")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = next_batch.main([str(self.issues), "--count", "1"])
        self.assertNotEqual(code, 0)
        self.assertIn("mint_carved.py", err.getvalue())

    def test_a_carved_row_reads_as_done_and_a_whole_one_releases(self):
        self.write_ledger(state="merged")
        rows = next_batch.load_ledgers(self.feature / "runs",
                                       next_batch.load_issues(self.issues))
        self.assertIn(("370", "done"), {(r.issue, r.status) for r in rows})
        self.write_ledger(status="carved (whole)", state="merged",
                          row=AWholeCarve.WHOLE)
        rows = next_batch.load_ledgers(self.feature / "runs",
                                       next_batch.load_issues(self.issues))
        self.assertIn(("370", "blocked"), {(r.issue, r.status) for r in rows})


if __name__ == "__main__":
    unittest.main()
