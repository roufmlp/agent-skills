#!/usr/bin/env python3
"""The next-batch scheduler, asked for on 2026-09-13.

the human scheduled runs by hand: read the issue files, work out what blocks what,
notice which were never hardened, order them. On 2026-09-13 he nearly scheduled
issue 05 ahead of issue 37, which builds the connection every one of 05's
criteria needs, because 05's `## Blocked by` named only a merged issue and the
real dependency sat in prose. `next_batch.py` reads every issue file, orders a
batch so every blocker is satisfied before the issue that needs it, and REFUSES
rather than print an order it cannot honour.

Run: python3 test_next_batch.py
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "next_batch.py"
sys.path.insert(0, str(HERE))

import next_batch  # noqa: E402


def write_issue(root: Path, name: str, status: str, blocked_by=None, extra_header=""):
    """Write one issue file in the tracker's shape. `blocked_by` is a list of
    bullet bodies; None means no `## Blocked by` section at all."""
    lines = [f"Status: {status}", extra_header, "Sentence: something", "",
             "## What to build", "", "Words.", ""]
    if blocked_by is not None:
        lines += ["## Blocked by", ""]
        lines += [f"- {entry}" for entry in blocked_by]
        lines += ["", "## Must still be true", "", "- A thing."]
    (root / f"{name}.md").write_text("\n".join(lines) + "\n")


def write_ledger(feature: Path, batch_id: str, rows, state="in-flight"):
    """Write one run ledger at <feature>/runs/<batch_id>/run.md in the shape
    `/run-issues` writes: a `State:` line and the issue table. `rows` is a list
    of (issue id, row status) pairs."""
    run_dir = feature / "runs" / batch_id
    run_dir.mkdir(parents=True)
    lines = [f"# Run {batch_id}", "", f"State: {state}", "",
             "| Check | Command | Result |", "|---|---|---|",
             "| Types | `npm run typecheck` | EXIT=0 |", "",
             "| Issue | Sentence | Status | Size | Stamps |",
             "|---|---|---|---|---|"]
    for issue_id, status in rows:
        lines.append(f"| {issue_id} | A sentence; with `code` | {status} | medium | attempt 1 |")
    (run_dir / "run.md").write_text("\n".join(lines) + "\n")


def run(root: Path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), *args],
        capture_output=True, text=True,
    )


class Parsing(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_blocked_by_bare_slug_form(self):
        write_issue(self.root, "02-sign-in", "done — merged", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent",
                    blocked_by=["02-sign-in-users-sessions — merged, satisfied."])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["05"].blockers, ["02"])

    def test_blocked_by_backtick_number_form(self):
        write_issue(self.root, "02c-limiter", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "02d-link", "ready-for-agent",
                    blocked_by=["`02c` — the sign-in rate limiter and the shipped `pg` seam."])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["02d"].blockers, ["02c"])

    def test_blocked_by_bold_backtick_slug_form(self):
        write_issue(self.root, "47a-store", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "47b-thumb", "ready-for-agent",
                    blocked_by=["**`47a-the-object-store-and-the-round-trip`** — the adapter."])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["47b"].blockers, ["47a"])

    def test_negation_and_none_bullets_are_not_blockers(self):
        write_issue(self.root, "02f-removal", "ready-for-agent", blocked_by=[
            "None - can start immediately",
            "**Not blocked by `02e-claim-the-link`, and `02e` is not blocked by this.**",
            "Nothing here waits on the human.",
            "**Criterion 4 is not blocked by 47a.**",
        ])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["02f"].blockers, [])

    def test_missing_blocked_by_section_means_unblocked(self):
        write_issue(self.root, "46-decode", "ready-for-agent", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["46"].blockers, [])

    def test_prose_in_the_section_is_ignored(self):
        write_issue(self.root, "02c-limiter", "ready-for-agent", blocked_by=[])
        path = self.root / "02c-limiter.md"
        path.write_text(path.read_text().replace(
            "## Blocked by\n",
            "## Blocked by\n\n**Nothing in code.** The parent's section named "
            "`02-sign-in-users-sessions`, which is merged.\n"))
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["02c"].blockers, [])

    def test_heading_with_a_suffix_still_opens_the_section(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "42-rls", "ready-for-agent", blocked_by=["`37-db-type`"])
        path = self.root / "42-rls.md"
        path.write_text(path.read_text().replace("## Blocked by\n", "## Blocked by, and the order\n"))
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["42"].blockers, ["37"])

    def test_status_takes_only_the_first_token(self):
        write_issue(self.root, "01-foundation", "done — merged to main 2026-09-13 in 3fce28e")
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["01"].status, "done")

    def test_missing_status_refuses(self):
        (self.root / "09-assign.md").write_text("Sentence: no status here\n")
        with self.assertRaises(next_batch.Refusal) as ctx:
            next_batch.load_issues(self.root)
        self.assertIn("09-assign.md", str(ctx.exception))
        self.assertIn("no Status: line", str(ctx.exception))

    def test_unrecognised_status_refuses(self):
        write_issue(self.root, "09-assign", "in-progress")
        with self.assertRaises(next_batch.Refusal) as ctx:
            next_batch.load_issues(self.root)
        self.assertIn("in-progress", str(ctx.exception))

    def test_blocker_naming_an_unknown_issue_refuses(self):
        write_issue(self.root, "09-assign", "ready-for-agent", blocked_by=["99-ghost"])
        with self.assertRaises(next_batch.Refusal) as ctx:
            next_batch.load_issues(self.root)
        self.assertIn("99", str(ctx.exception))


class Ordering(unittest.TestCase):
    def test_sort_key_orders_number_then_letter_suffix(self):
        ids = ["10", "05c", "05", "09", "05b", "47a", "01b", "01", "47"]
        self.assertEqual(
            sorted(ids, key=next_batch.sort_key),
            ["01", "01b", "05", "05b", "05c", "09", "10", "47", "47a"],
        )


class Scheduling(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_done_and_closed_satisfy_a_blocker(self):
        write_issue(self.root, "01-foundation", "done — merged")
        write_issue(self.root, "02-signin", "closed — absorbed")
        write_issue(self.root, "03-controls", "ready-for-agent", blocked_by=["01-foundation", "`02`"])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 03", out.stdout)
        self.assertNotIn("/harden-issues", out.stdout)

    def test_order_puts_the_blocker_first_whatever_the_number(self):
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 37 05", out.stdout)

    def test_needs_harden_members_go_to_the_harden_command(self):
        write_issue(self.root, "34-picker", "needs-harden", blocked_by=None)
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 34\n", out.stdout)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_a_ready_issue_behind_an_unhardened_blocker_is_not_reachable(self):
        write_issue(self.root, "34-picker", "needs-harden", blocked_by=None)
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=["34-picker"])
        out = run(self.root, "--count", "2")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("1 reachable", out.stderr)
        self.assertIn("35", out.stderr)
        self.assertIn("34", out.stderr)

    def test_count_larger_than_reachable_refuses_and_names_the_count(self):
        write_issue(self.root, "01-foundation", "done — merged")
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "41-timeout", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "5")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("2 reachable", out.stderr)
        self.assertNotIn("/run-issues", out.stdout)

    def test_cycle_refuses_and_prints_it(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent", blocked_by=["08-request"])
        write_issue(self.root, "08-request", "ready-for-agent", blocked_by=["09-assign"])
        write_issue(self.root, "09-assign", "ready-for-agent", blocked_by=["07-catalogue"])
        out = run(self.root, "--count", "1")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("cycle", out.stderr.lower())
        self.assertIn("07 -> 08 -> 09 -> 07", out.stderr)

    def test_table_shows_status_and_what_each_issue_waited_on(self):
        write_issue(self.root, "02-signin", "done — merged")
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["02-signin", "`37-db-type`"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        rows = [line for line in out.stdout.splitlines() if line.startswith("05 ")]
        self.assertEqual(len(rows), 1)
        self.assertIn("ready-for-agent", rows[0])
        self.assertIn("02 (done)", rows[0])
        self.assertIn("37", rows[0])

    def test_verify_order_rejects_a_stranded_issue(self):
        issues = {
            "37": next_batch.Issue("37", "37-db.md", "ready-for-agent", []),
            "05": next_batch.Issue("05", "05-records.md", "ready-for-agent", ["37"]),
        }
        with self.assertRaises(next_batch.Refusal):
            next_batch.verify_order(["05"], issues)
        next_batch.verify_order(["37", "05"], issues)

    def test_theme_filter_refuses_when_no_file_carries_themes(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "1", "--theme", "security")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Themes:", out.stderr)

    def test_theme_filter_keeps_only_the_theme_but_orders_its_blockers_first(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None,
                    extra_header="Themes: plumbing")
        write_issue(self.root, "38-signed-url", "ready-for-agent", blocked_by=["`37-db-type`"],
                    extra_header="Themes: security, files")
        out = run(self.root, "--count", "1", "--theme", "security")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 37 38", out.stdout)


class Ledgers(unittest.TestCase):
    """`Status:` in an issue file does not change until a run MERGES, so the run
    ledgers (`<feature>/runs/<batch>/run.md`) are the only record of what is
    built or being built. Measured 2026-09-13: one run had all eight
    issues at `done` and the tool still offered five of them as a fresh batch,
    and missed that issue 05 had just become unblocked by two of them."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_done_row_hides_the_issue_and_satisfies_a_dependent(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_ledger(self.feature, "batch-<id>", [("37", "done")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05\n", out.stdout)
        table = out.stdout.split("Held by a run")[0]
        self.assertFalse([line for line in table.splitlines() if line.startswith("37 ")])
        rows = [line for line in out.stdout.splitlines() if line.startswith("05 ")]
        self.assertEqual(len(rows), 1)
        self.assertIn("37 (done in batch-<id>)", rows[0])

    def test_the_table_says_which_run_holds_an_excluded_issue(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id>", [("37", "done")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        held = out.stdout.split("Held by a run")[1]
        self.assertIn("37", held)
        self.assertIn("batch-<id>", held)
        self.assertIn("done", held)

    def test_a_blocked_criteria_row_leaves_the_issue_available_and_not_satisfied(self):
        write_issue(self.root, "02b-limiter", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`02b-limiter`"])
        write_ledger(self.feature, "batch-abc123", [("02b", "blocked (criteria)")])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 02b 05\n", out.stdout)
        self.assertNotIn("Held by a run", out.stdout)

    def test_an_in_progress_row_hides_the_issue_and_satisfies_nothing(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id>", [("37", "in-progress")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)
        out = run(self.root, "--count", "2")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("05 waits on 37", out.stderr)
        self.assertIn("batch-<id>", out.stderr)

    def test_a_queued_row_leaves_the_issue_available(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id>", [("40", "queued")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_an_unknown_row_status_refuses_naming_run_status_and_issue(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-abc123", [("40", "escalated")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 1)
        self.assertIn("batch-abc123", out.stderr)
        self.assertIn("escalated", out.stderr)
        self.assertIn("40", out.stderr)
        self.assertEqual(out.stdout, "")

    def test_an_issue_row_naming_no_issue_file_refuses(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-abc123", [("99", "done")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 1)
        self.assertIn("99", out.stderr)
        self.assertIn("batch-abc123", out.stderr)

    def test_a_missing_runs_directory_is_harmless(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        self.assertFalse((self.feature / "runs").exists())
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_the_issue_file_status_still_satisfies_without_a_ledger(self):
        write_issue(self.root, "02-signin", "done — merged")
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["02-signin"])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05\n", out.stdout)


class ReachableCount(unittest.TestCase):
    """Asked for 10 on 2026-09-13 the tool printed 10 and said nothing about the
    rest. It must say how many were reachable and how many it did not show."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_says_how_many_were_reachable_and_how_many_not_shown(self):
        for name in ("40-ci", "41-timeout", "44-zero", "46-decode"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=None)
        write_issue(self.root, "34-picker", "needs-harden", blocked_by=None)
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=["34-picker"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("2 of 5 reachable, 3 not shown\n", out.stdout)
        self.assertIn("/harden-issues 34\n", out.stdout)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_says_so_when_everything_reachable_is_shown(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "41-timeout", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("2 of 2 reachable, 0 not shown\n", out.stdout)


class FanOut(unittest.TestCase):
    """What an issue unblocks, ruled by the human 2026-09-13. Measured the same day on
    one tracker: issue 37 sat upstream of 56 open issues and the script still listed
    it by number."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_diamond_counts_the_far_issue_once(self):
        write_issue(self.root, "01-schema", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "02-left", "ready-for-agent", blocked_by=["01-schema"])
        write_issue(self.root, "03-right", "ready-for-agent", blocked_by=["01-schema"])
        write_issue(self.root, "04-screen", "ready-for-agent", blocked_by=["02-left", "03-right"])
        issues = next_batch.load_issues(self.root)
        counts = next_batch.fan_out(issues)
        self.assertEqual(counts["01"], 3)
        self.assertEqual(counts["02"], 1)
        self.assertEqual(counts["04"], 0)

    def test_a_finished_or_run_held_issue_downstream_is_not_counted(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["37-db-type"])
        write_issue(self.root, "06-screen", "ready-for-agent", blocked_by=["37-db-type"])
        write_issue(self.root, "09-report", "done — merged", blocked_by=["37-db-type"])
        issues = next_batch.load_issues(self.root)
        rows = [next_batch.LedgerRow("06", "batch-<id>", "in-progress")]
        self.assertEqual(next_batch.fan_out(issues)["37"], 2)
        self.assertEqual(next_batch.fan_out(issues, rows)["37"], 1)

    def test_a_free_candidate_with_fan_out_goes_before_a_lower_number(self):
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "09-assign", "ready-for-agent", blocked_by=None)
        for name in ("10-ci", "11-timeout", "12-decode"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=["09-assign"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 09 05\n", out.stdout)

    def test_by_number_restores_the_old_order(self):
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "09-assign", "ready-for-agent", blocked_by=None)
        for name in ("10-ci", "11-timeout", "12-decode"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=["09-assign"])
        out = run(self.root, "--count", "2", "--by", "number")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05 09\n", out.stdout)

    def test_the_table_carries_the_fan_out_column(self):
        write_issue(self.root, "01-schema", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "02-left", "ready-for-agent", blocked_by=["01-schema"])
        write_issue(self.root, "03-right", "ready-for-agent", blocked_by=["01-schema"])
        write_issue(self.root, "04-screen", "ready-for-agent",
                    blocked_by=["02-left", "03-right"])
        out = run(self.root, "--count", "4")
        self.assertEqual(out.returncode, 0, out.stderr)
        header = out.stdout.splitlines()[0]
        self.assertIn("Fan-out", header)
        at = header.index("Fan-out")
        rows = {line[:2]: line[at:at + len("Fan-out")].strip()
                for line in out.stdout.splitlines() if line[:2] in ("01", "02", "04")}
        self.assertEqual(rows["01"], "3")
        self.assertEqual(rows["02"], "1")
        self.assertEqual(rows["04"], "0")


class HardenLine(unittest.TestCase):
    """The third command line, ruled by the human 2026-09-13. A needs-harden issue never
    appeared in the `/harden-issues` line unless the count exhausted every ready
    issue, because its number is higher, so no agent ever told him to harden an
    upstream issue before a run."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_needs_harden_blocker_is_named_and_the_blocked_issue_says_why(self):
        write_issue(self.root, "34-picker", "needs-harden", blocked_by=None)
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=["34-picker"])
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "41-timeout", "ready-for-agent", blocked_by=["40-ci"])
        write_issue(self.root, "42-decode", "ready-for-agent", blocked_by=["40-ci"])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 34\n", out.stdout)
        self.assertIn("/run-issues 40\n", out.stdout)
        self.assertIn("35", out.stdout)
        self.assertIn("waits on harden of 34", out.stdout)
        self.assertLess(out.stdout.index("not shown"),
                        out.stdout.index("waits on harden of 34"))
        self.assertLess(out.stdout.index("/harden-issues 34"),
                        out.stdout.index("/run-issues 40"))

    def test_a_minted_issue_ranks_by_its_origins_fan_out_then_by_severity(self):
        write_issue(self.root, "05-rights", "done — merged", blocked_by=None)
        for name in ("06-screen", "07-export", "08-audit", "09-report"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=["05-rights"])
        write_issue(self.root, "20-copy", "done — merged", blocked_by=None)
        write_issue(self.root, "66-rounding", "needs-harden", blocked_by=None,
                    extra_header="Origin: 05/batch-x\nRows: r1 operator/medium")
        write_issue(self.root, "67-expiry", "needs-harden", blocked_by=None,
                    extra_header="Origin: 05/batch-x\nRows: r2 operator/high")
        write_issue(self.root, "68-label", "needs-harden", blocked_by=None,
                    extra_header="Origin: 20/batch-x\nRows: r3 operator/high")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 67 66\n", out.stdout)
        self.assertNotIn("68", out.stdout.split("/harden-issues")[1])

    def test_a_member_is_named_once_and_by_the_members_line(self):
        """Both harden lines are commands a reader pastes. A number on the first
        that the second carries too teaches the reader to skip one of them."""
        write_issue(self.root, "34-picker", "needs-harden", blocked_by=None)
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=["34-picker"])
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(
            [line for line in out.stdout.splitlines()
             if line.startswith("/harden-issues")],
            ["/harden-issues 34"])
        self.assertIn("waits on harden of 34", out.stdout)

    def test_a_run_held_minted_issue_is_never_offered(self):
        write_issue(self.root, "05-rights", "done — merged", blocked_by=None)
        for name in ("06-screen", "07-export"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=["05-rights"])
        write_issue(self.root, "66-rounding", "needs-harden", blocked_by=None,
                    extra_header="Origin: 05/batch-x\nRows: r1 operator/high")
        write_ledger(self.feature, "batch-<id>", [("66", "in-progress")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("/harden-issues", out.stdout)

    def test_an_unknown_origin_ranks_nothing(self):
        write_issue(self.root, "05-rights", "done — merged", blocked_by=None)
        write_issue(self.root, "06-screen", "ready-for-agent", blocked_by=["05-rights"])
        write_issue(self.root, "66-rounding", "needs-harden", blocked_by=None,
                    extra_header="Origin: unknown\nRows: r1 operator/high")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("/harden-issues", out.stdout)


class WideIssueNumbers(unittest.TestCase):
    """An issue number was capped at two digits until 2026-09-13, so every issue
    from 100 up was invisible: `FILE_RE` did not match the file, `load_issues`
    did not hold it, and the tool neither offered it nor named it in the count
    line. Measured the same day: one tracker in use carries 641 issues. The cap also rejected a bullet opening with a date by
    accident, and these tests pin that rejection now that it is deliberate."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_three_digit_issue_file_is_loaded_and_offered(self):
        write_issue(self.root, "07-early", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "641-late", "ready-for-agent", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertEqual(sorted(issues, key=next_batch.sort_key), ["07", "641"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("2 of 2 reachable, 0 not shown\n", out.stdout)
        self.assertIn("/run-issues 07 641\n", out.stdout)

    def test_a_bullet_opening_with_a_date_is_not_a_blocker(self):
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=[
            "2026-09-13 ruling: the human moved the dependency into prose.",
            "`2026-08-09` - the push ruling, which is not an issue.",
        ])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["05"].blockers, [])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05\n", out.stdout)

    def test_a_dated_note_beside_the_issues_is_not_an_issue_file(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        (self.root / "2026-09-13-decisions.md").write_text("A note, not an issue.\n")
        issues = next_batch.load_issues(self.root)
        self.assertEqual(sorted(issues, key=next_batch.sort_key), ["40"])

    def test_a_three_digit_origin_issue_is_an_identifier_this_tool_reads(self):
        """`Origin: 149e/batch-<id>` names issue 149e, and
        `run-issues/check_origin.py` reads the same identifier. What is pinned here
        is the identifier: 149e loads, blocks, and sorts. The harden line then
        ranks by it."""
        write_issue(self.root, "149e-rights-rows", "ready-for-agent", blocked_by=None,
                    extra_header="Origin: 149e/batch-<id>")
        write_issue(self.root, "09-assign", "ready-for-agent",
                    blocked_by=["`149e-rights-rows` - the rows minted from it."])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["09"].blockers, ["149e"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 149e 09\n", out.stdout)

    def test_a_three_digit_origin_ranks_the_harden_line(self):
        """The seam between the two changes of 2026-09-13. The wide identifier
        reaches `Origin:`, so a minted issue from issue 149e inherits 149e's
        fan-out. Under the two-digit cap the origin parsed to nothing and the
        issue was silently left out of the line."""
        write_issue(self.root, "149e-rights", "done — merged", blocked_by=None)
        for name in ("150-screen", "151-export", "641-audit"):
            write_issue(self.root, name, "ready-for-agent", blocked_by=["149e-rights"])
        write_issue(self.root, "700-rounding", "needs-harden", blocked_by=None,
                    extra_header="Origin: 149e/batch-<id>\nRows: r1 operator/high")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 700\n", out.stdout)


if __name__ == "__main__":
    unittest.main()
