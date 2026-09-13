#!/usr/bin/env python3
"""The next-batch scheduler, asked for on 2026-09-13.

The human scheduled runs by hand: read the issue files, work out what blocks what,
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


if __name__ == "__main__":
    unittest.main()
