#!/usr/bin/env python3
"""The next-batch scheduler, asked for on 2026-09-13.

The human scheduled runs by hand: read the issue files, work out what blocks what,
notice which were never hardened, order them. On 2026-09-13 they nearly scheduled
issue 05 ahead of issue 37, which builds the connection every one of 05's
criteria needs, because 05's `## Blocked by` named only a merged issue and the
real dependency sat in prose. `next_batch.py` reads every issue file, orders a
batch so every blocker is satisfied before the issue that needs it, and REFUSES
rather than print an order it cannot honour.

Run: python3 test_next_batch.py
"""

import ast
import inspect
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "next_batch.py"
sys.path.insert(0, str(HERE))

import next_batch  # noqa: E402

sys.path.insert(0, str(HERE.parent / "run-issues"))
from check_issue_ready import HEADER_RULE_FROM, PENDING_RULE_FROM  # noqa: E402

# Issue 43's `Light:` line, dated from the rule-date constant, never a typed
# literal (`q-h0925-33-4`).
LIGHT_LINE = f"Light: {HEADER_RULE_FROM} — not hardened, rule 5 of issue 32."


# `blocked_by=NO_SECTION` writes a file with NO `## Blocked by` heading at all.
# `blocked_by=None`, which nearly every test below uses, writes the section with
# `- None` in it. The two parse identically -- `blockers_of` returns [] for both
# -- and they differ for `harden_marks`, which names a file that has no section
# as one nobody has hardened. Separated on 2026-09-14, when the tool started
# grading the issues it OFFERS.
NO_SECTION = object()


def write_issue(root: Path, name: str, status: str, blocked_by=None,
                extra_header="", hardened=True, criteria=1):
    """Write one issue file in the tracker's shape.

    The default is a file that a run could be handed: a `Hardened:` stamp, a
    `## Blocked by` section and one acceptance criterion. `hardened=False` and
    `criteria=0` write the un-hardened shapes, which is what the marks and the
    size check are there to name.
    """
    lines = [f"Status: {status}"]
    if hardened:
        lines.append("Hardened: 2026-09-14 — fixture")
    lines += [extra_header, "Sentence: something", "",
              "## What to build", "", "Words.", ""]
    if criteria:
        lines += ["## Acceptance criteria", ""]
        lines += [f"- [ ] Criterion {n + 1}." for n in range(criteria)]
        lines.append("")
    if blocked_by is not NO_SECTION:
        lines += ["## Blocked by", ""]
        lines += [f"- {entry}" for entry in (blocked_by or ["None"])]
        lines += ["", "## Must still be true", "", "- A thing."]
    (root / f"{name}.md").write_text("\n".join(lines) + "\n")


def write_ledger(feature: Path, batch_id: str, rows, state="in-flight"):
    """Write one run ledger at <feature>/runs/<batch_id>/run.md in the shape
    `/run-issues` writes: a `State:` line and the issue table. `rows` is a list
    of (issue id, row status) pairs.

    `state` decides everything the fix of 2026-09-14 turns on. `in-flight`, the
    default, is a run whose branch main does NOT carry; `merged` is one it does.
    The default is deliberate: a ledger that is not saying `merged` must never be
    read as merged."""
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

    def test_the_minted_bullet_is_not_a_blocker(self):
        """Promotion writes `- Unknown until hardened` on every issue it mints,
        so a reader can tell a minted issue from a hardened one that genuinely
        has no blockers. It is a statement that nobody has looked yet, not an
        edge, and this tool must place the issue exactly as it places one whose
        section reads `- None`. Issue 02 of the set that added it, ruled by
        the human on 2026-09-13."""
        write_issue(self.root, "70-minted", "needs-harden",
                    blocked_by=["Unknown until hardened"])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["70"].blockers, [])

    def test_a_minted_issue_is_offered_like_any_other(self):
        """The parse and the placement are two things, and the bullet has to
        survive both: an issue read as unblocked and then held out of the batch
        would be dropped work, which this tool promises never to do."""
        write_issue(self.root, "70-minted", "ready-for-agent",
                    blocked_by=["Unknown until hardened"])
        result = run(self.root, "--count", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("70", result.stdout)

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

    def test_blocked_is_a_status_this_tool_knows(self):
        """The human's ruling of 2026-09-18. A run writes `blocked` when it spends
        a strike cap; it did so on issue 08d on 17 September and on issue 139
        on 18 September, and four instruments then refused two whole
        trackers."""
        write_issue(self.root, "09-assign", "blocked")
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["09"].status, "blocked")
        self.assertEqual(issues["09"].unreadable, "")

    def test_a_blocked_issue_is_never_offered(self):
        write_issue(self.root, "09-assign", "blocked", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertNotIn(issues["09"].status, next_batch.CANDIDATES)
        self.assertEqual(next_batch.schedule(issues, 1, refuse_short=False).order, [])

    def test_a_blocked_issue_is_still_open_work(self):
        """It is not parked and it is not done: something stopped, and what
        waits on it still waits."""
        write_issue(self.root, "09-assign", "blocked", blocked_by=None)
        self.assertIn("09", next_batch.open_ids(next_batch.load_issues(self.root)))

    def test_missing_status_names_the_file_and_loads_the_rest(self):
        """Second half of the same ruling: an unreadable file is named, and
        the tracker is still read."""
        (self.root / "09-assign.md").write_text("Sentence: no status here\n")
        write_issue(self.root, "10-totals", "ready-for-agent", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertEqual(issues["09"].unreadable, "no Status: line in the header")
        self.assertIn("10", issues)

    def test_unrecognised_status_names_the_file_and_loads_the_rest(self):
        write_issue(self.root, "09-assign", "in-progress")
        write_issue(self.root, "10-totals", "ready-for-agent", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertIn("in-progress", issues["09"].unreadable)
        self.assertEqual(issues["09"].status, "in-progress")
        self.assertIn("10", issues)

    def test_an_unreadable_issue_is_never_offered(self):
        """It cannot be shown to be ready, so it is not work a run may take."""
        write_issue(self.root, "09-assign", "in-progress", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertEqual(next_batch.schedule(issues, 1, refuse_short=False).order, [])

    def test_an_unreadable_issue_still_blocks_what_names_it(self):
        """Nothing may be offered on the strength of a file nobody could read."""
        write_issue(self.root, "09-assign", "in-progress", blocked_by=None)
        write_issue(self.root, "10-totals", "ready-for-agent", blocked_by=["`09-assign`"])
        issues = next_batch.load_issues(self.root)
        self.assertEqual(next_batch.schedule(issues, 1, refuse_short=False).order, [])

    def test_the_unreadable_files_are_listed_for_the_caller_to_name(self):
        (self.root / "09-assign.md").write_text("Sentence: no status here\n")
        write_issue(self.root, "10-totals", "ready-for-agent", blocked_by=None)
        issues = next_batch.load_issues(self.root)
        self.assertEqual([f for f, _ in next_batch.unreadable(issues)],
                         ["09-assign.md"])

    def test_the_command_names_an_unreadable_file_and_still_prints(self):
        (self.root / "09-assign.md").write_text("Sentence: no status here\n")
        write_issue(self.root, "10-totals", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("09-assign.md", out.stdout + out.stderr)
        self.assertIn("10", out.stdout)

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
    built or being built. Measured 2026-09-13: run batch-<id2> had all eight
    issues at `done` and the tool still offered five of them as a fresh batch,
    and missed that issue 05 had just become unblocked by two of them."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_done_row_on_a_MERGED_run_hides_the_issue_and_satisfies_a_dependent(self):
        """The 2026-09-13 case, now written with the merge it always assumed.

        A merged run's work IS in main, so its `done` row stands as a satisfied
        blocker even where the merge never rewrote the issue file. Measured on
        one tracker on 2026-09-14: issue 37 is `done` in a run that merged on
        2026-09-13, and its file still reads `ready-for-agent`."""
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_ledger(self.feature, "batch-<id2>", [("37", "done")], state="merged")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05\n", out.stdout)
        table = out.stdout.split("Held by a run")[0]
        self.assertFalse([line for line in table.splitlines() if line.startswith("37 ")])
        rows = [line for line in out.stdout.splitlines() if line.startswith("05 ")]
        self.assertEqual(len(rows), 1)
        self.assertIn("37 (done, batch-<id2>)", rows[0])

    def test_the_table_says_which_run_holds_an_excluded_issue(self):
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id2>", [("37", "done")], state="merged")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        held = out.stdout.split("Held by a run")[1]
        self.assertIn("37", held)
        self.assertIn("batch-<id2>", held)
        self.assertIn("done", held)

    def test_a_blocked_criteria_row_leaves_the_issue_available_and_not_satisfied(self):
        write_issue(self.root, "02b-limiter", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`02b-limiter`"])
        write_ledger(self.feature, "batch-<id6>", [("02b", "blocked (criteria)")])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 02b 05\n", out.stdout)
        self.assertNotIn("Held by a run", out.stdout)

    def test_a_plain_blocked_row_leaves_the_issue_available_and_not_satisfied(self):
        """The spent attempt cap. Run `batch-<id3>` wrote `blocked` for issue 08d
        on 2026-09-17 after three attempts and three rejections, and this tool
        refused the whole tracker over that one cell. It built nothing into main,
        so the issue is offered again and it satisfies nothing behind it."""
        write_issue(self.root, "02b-limiter", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`02b-limiter`"])
        write_ledger(self.feature, "batch-<id6>", [("02b", "blocked")])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 02b 05\n", out.stdout)
        self.assertNotIn("Held by a run", out.stdout)

    def test_a_plain_blocked_row_never_refuses_the_tracker(self):
        """The refusal this entry closes, driven end to end: one `blocked` cell
        used to cost every other issue its batch."""
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "08d-draft-store", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id3>", [("08d", "blocked")], state="merged")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("REFUSED", out.stdout)
        self.assertNotIn("does not know", out.stdout)

    def test_a_plain_blocked_row_on_a_merged_run_still_satisfies_nothing(self):
        """A merged run that gave up is still a run that built nothing, so the
        issue is offered rather than stood behind."""
        write_issue(self.root, "08d-draft-store", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "11b-brief", "ready-for-agent", blocked_by=["`08d-draft-store`"])
        write_ledger(self.feature, "batch-<id3>", [("08d", "blocked")], state="merged")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 08d 11b\n", out.stdout)

    def test_a_bold_blocked_row_is_read_as_blocked(self):
        """Emphasis is markdown, not vocabulary. Run `batch-<id7>` wrote
        `**blocked**` for issues 151, 152 and 53, and on 2026-09-23 this tool
        refused the whole tracker over the asterisks. A released row offers the
        issue again, so 151 lands in the batch."""
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "151-guard", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id7>", [("151", "**blocked**")], state="merged")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("does not know", out.stdout + out.stderr)
        batch = [l for l in out.stdout.splitlines() if l.startswith("/run-issues ")]
        self.assertEqual(len(batch), 1, out.stdout)
        self.assertIn("151", batch[0].split())

    def test_a_backticked_in_progress_row_still_holds(self):
        """The strip reaches the holding statuses too, so a formatted cell can
        never turn an issue a run is building into one a new batch offers."""
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id2>", [("37", "`in-progress`")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)
        held = out.stdout.split("Held by a run")[1]
        self.assertIn("37", held)

    def test_a_bold_unknown_status_still_refuses(self):
        """Only the emphasis goes. The word under it is still tested by exact
        membership, so a status this tool does not know refuses as before."""
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id6>", [("40", "**blocked-on-the-human**")])
        out = run(self.root, "--count", "1")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("blocked-on-the-human", out.stdout + out.stderr)
        self.assertIn("does not know", out.stdout + out.stderr)

    def test_blocked_and_blocked_criteria_stay_two_statuses(self):
        """Exact membership, not a prefix. A status this tool does not know must
        still refuse, and `blocked-on-the-human` is the nearest wrong
        neighbour."""
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id6>",
                     [("40", "blocked-on-the-human")])
        out = run(self.root, "--count", "1")
        self.assertIn("blocked-on-the-human", out.stdout + out.stderr)
        self.assertIn("does not know", out.stdout + out.stderr)

    def test_an_in_progress_row_hides_the_issue_and_satisfies_nothing(self):
        """An issue a run is building now cannot stand as a blocker, and the
        candidate behind it is named under the run rather than in a refusal:
        the run IS live, so the count could not have been honoured anyway."""
        write_issue(self.root, "37-db-type", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id2>", [("37", "in-progress")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("SOME CAN START IN PARALLEL", out.stdout)
        self.assertIn("Waiting on run batch-<id2> to merge", out.stdout)
        self.assertIn("05", out.stdout.split("Waiting on run batch-<id2>")[1])
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_a_queued_row_leaves_the_issue_available(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_ledger(self.feature, "batch-<id2>", [("40", "queued")])
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


class Parked(unittest.TestCase):
    """The fifth status, issue 03 of the set that added it, ruled by the human
    on 2026-09-13 on a measurement of one tracker: 641 issues and 149 of them
    needs-harden, none named as a blocker by any other issue. A needs-harden
    issue with fan-out zero sits last for ever under the fan-out order, so the
    backlog grows and nothing leaves it. A parked issue is never offered here;
    `sweep_parked.py` is the one door back."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_parked_issue_is_counted_under_the_table_and_never_offered(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        for name in ("70-rounding", "71-colour", "72-import"):
            write_issue(self.root, name, "parked", blocked_by=["Unknown until hardened"])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("1 of 1 reachable, 0 not shown\n", out.stdout)
        self.assertIn("3 parked, not offered\n", out.stdout)
        for number in ("70", "71", "72"):
            self.assertNotIn(number, out.stdout)

    def test_the_count_line_is_absent_where_no_issue_is_parked(self):
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("parked", out.stdout)

    def test_a_parked_issue_is_never_pulled_in_as_a_blocker(self):
        """A parked ancestor is not a member and nothing is placed behind it.
        The refusal names the status, so the reader learns why."""
        write_issue(self.root, "70-rounding", "parked", blocked_by=None)
        write_issue(self.root, "71-screen", "ready-for-agent", blocked_by=["70-rounding"])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 1)
        self.assertIn("71 waits on 70 (parked)", out.stderr)

    def test_a_parked_issue_downstream_adds_no_fan_out(self):
        """Fan-out is the leverage an issue carries, and a parked issue is work
        this tool will not offer until a sweep brings it back."""
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "41-timeout", "ready-for-agent", blocked_by=None)
        write_issue(self.root, "70-rounding", "parked", blocked_by=["40-ci"])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40 41\n", out.stdout)
        rows = [line for line in out.stdout.splitlines() if line.startswith("40 ")]
        self.assertEqual(len(rows), 1)
        self.assertIn(" 0 ", rows[0])

    def test_a_parked_issue_is_a_status_this_tool_knows(self):
        """It refuses an unknown status, and a tracker carrying the fifth one
        must still print an order."""
        write_issue(self.root, "70-rounding", "parked", blocked_by=None)
        write_issue(self.root, "40-ci", "ready-for-agent", blocked_by=None)
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)


class FanOut(unittest.TestCase):
    """What an issue unblocks, ruled by the human 2026-09-13. Measured the same day
    on one tracker: issue 37 sat upstream of 56 open issues and the script still
    listed it by number."""

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
        rows = [next_batch.LedgerRow("06", "batch-<id2>", "in-progress")]
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
    """The third command line, ruled by the human 2026-09-13. A needs-harden issue
    never appeared in the `/harden-issues` line unless the count exhausted every
    ready issue, because its number is higher, so no agent ever told the human to
    harden an upstream issue before a run."""

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
        write_ledger(self.feature, "batch-<id2>", [("66", "in-progress")])
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
    line. Measured the same day, issue 03 of that same set: one tracker in use
    carries 641 issues. The cap also rejected a bullet opening with a date by
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
        """`Origin: 149e/batch-<id1>` names issue 149e, and
        `run-issues/check_origin.py` reads the same identifier. What is pinned here
        is the identifier: 149e loads, blocks, and sorts. Issue 01 of that
        same set then ranks the harden line by it."""
        write_issue(self.root, "149e-rights-rows", "ready-for-agent", blocked_by=None,
                    extra_header="Origin: 149e/batch-<id1>")
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
                    extra_header="Origin: 149e/batch-<id1>\nRows: r1 operator/high")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 700\n", out.stdout)



class TheLedgerCellCarriesATitle(unittest.TestCase):
    """A run ledger writes `| 70 — permit write narrowing is private |`.

    The read was `re.fullmatch(ISSUE_ID, cell)` until 2026-09-14, so a ledger of
    that shape yielded NO rows and the run holding those issues held nothing.
    Measured that day on one tracker: one run was live with 25 issues and 13
    committed, and this tool offered fifteen of them as the next batch.
    Two of that tracker's four ledgers write the title in the cell.
    """

    def rows(self, table):
        return list(next_batch.ledger_rows(table))

    def test_a_bare_id_still_parses(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n| 42 | done |\n"),
            [("42", "done")])

    def test_an_id_with_an_em_dash_title_parses(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n"
                      "| 70 — permit write narrowing is private | done |\n"),
            [("70", "done")])

    def test_an_id_with_a_hyphen_title_parses(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n"
                      "| 40 - CI runs no next build | done |\n"),
            [("40", "done")])

    def test_a_letter_suffix_survives_a_title(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n"
                      "| 08c — the draft store | in-progress |\n"),
            [("08c", "in-progress")])

    def test_a_leading_row_number_column_is_not_the_issue(self):
        """`| # | Issue | Size | Status | Stamps |` is the live ledger's shape."""
        self.assertEqual(
            self.rows("| # | Issue | Size | Status | Stamps |\n|---|---|---|---|---|\n"
                      "| 1 | 70 — a thing | small | done | x |\n"),
            [("70", "done")])

    def test_an_iso_date_is_not_an_issue(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n"
                      "| 2026-09-13 a note about the run | done |\n"),
            [])

    def test_a_cell_opening_with_prose_yields_nothing(self):
        self.assertEqual(
            self.rows("| Issue | Status |\n|---|---|\n"
                      "| none of them | done |\n"),
            [])


class TheMergedState(unittest.TestCase):
    """`run_is_merged` reads the ledger's `State:` line, and the state is the
    FIRST word on it. Measured on one tracker on 2026-09-14: three of four ledgers
    say merged in three different shapes, and the live one carries no `State:`
    line at all."""

    def test_a_plain_merged_line(self):
        self.assertTrue(next_batch.run_is_merged("State: merged\n"))

    def test_the_two_timestamp_shape(self):
        self.assertTrue(next_batch.run_is_merged(
            "State: merged — reached awaiting-merge 2026-09-13 12:40, merged to "
            "main 2026-09-13 12:49 at commit c237457\n"))

    def test_the_fork_point_shape(self):
        self.assertTrue(next_batch.run_is_merged(
            "State: merged 2026-09-13 21:59, into main at the run's fork point "
            "`5e22834`\n"))

    def test_awaiting_merge_is_not_merged(self):
        """The word `merged` is inside `awaiting-merge`, and a run at
        awaiting-merge has not merged. Anchoring on the first word is the
        difference between the two."""
        self.assertFalse(next_batch.run_is_merged(
            "State: **awaiting-merge, reached 15:45.**\n"))

    def test_a_mid_sentence_state_line_still_reads(self):
        self.assertFalse(next_batch.run_is_merged(
            "Started 2026-08-20 03:03. State: `finale-board`\n"))

    def test_no_state_line_is_not_merged(self):
        """The live ledger measured on 2026-09-14 carried no `State:` line. A tool that read that as merged would hand out exactly the
        batch main could not build."""
        self.assertFalse(next_batch.run_is_merged(
            "# Run ledger — `batch-<id5>`\n\nOwner: run-issues session\n"))


class AnUnmergedBranchSatisfiesNothing(unittest.TestCase):
    """THE FIX OF 2026-09-14.

    `LEDGER_SATISFIES = ("done",)` treated an issue finished on an UNMERGED run
    branch as a satisfied blocker. It is not one: a new run branches from main,
    and work that exists only on another run's branch is not in main.

    Measured on one tracker that day with one run live — 25 issues, 13
    committed, 1 in gates, 11 queued — the tool offered five issues as free
    (27, 07b, 30, 30b, 32) and every one of them was blocked by work that
    existed only on that branch.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_output_1_nothing_can_start_names_the_run_and_prints_no_run_command(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_issue(self.root, "30-report", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 1)
        self.assertIn("NOTHING CAN START", out.stdout)
        self.assertIn("batch-<id5>", out.stdout)
        self.assertFalse([line for line in out.stdout.splitlines()
                          if line.startswith("/run-issues")], out.stdout)
        self.assertIn("No /run-issues command is printed", out.stdout)
        self.assertIn("nothing can start today", out.stderr)
        self.assertIn("batch-<id5>", out.stderr)

    def test_output_1_prints_the_batch_the_merge_would_release(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_issue(self.root, "30-report", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "2")
        self.assertIn("Available the moment batch-<id5> merges", out.stdout)
        table = out.stdout.split("Available the moment")[1]
        self.assertIn("07b", table)
        self.assertIn("30", table)

    def test_output_2_offers_only_what_main_can_build(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("SOME CAN START IN PARALLEL", out.stdout)
        self.assertIn("/run-issues 41\n", out.stdout)
        self.assertNotIn("/run-issues 41 07b", out.stdout)

    def test_output_2_files_the_rest_under_the_run_they_wait_on(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "1")
        self.assertIn("Waiting on run batch-<id5> to merge", out.stdout)
        block = out.stdout.split("Waiting on run batch-<id5> to merge")[1]
        self.assertIn("07b", block)
        self.assertIn("not in main", block)

    def test_output_2_says_how_many_more_the_merge_releases(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "1")
        self.assertIn("more become reachable when batch-<id5> merges", out.stdout)

    def test_output_3_is_todays_shape_when_no_run_is_live(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_ledger(self.feature, "batch-<id5>", [("07", "done")], state="merged")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("NOTHING CAN START", out.stdout)
        self.assertNotIn("SOME CAN START", out.stdout)
        self.assertIn("/run-issues 07b\n", out.stdout)

    def test_a_merged_ledger_satisfies_where_the_file_still_lags(self):
        """Issue 37 on one tracker: `done` in a run that merged on 2026-09-13,
        and the file still read `ready-for-agent` on 2026-09-14. The merge did
        not rewrite it."""
        write_issue(self.root, "37-db-type", "ready-for-agent")
        write_issue(self.root, "05-records", "ready-for-agent", blocked_by=["`37-db-type`"])
        write_ledger(self.feature, "batch-<id2>", [("37", "done")], state="merged")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 05\n", out.stdout)

    def test_two_live_runs_are_both_named(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "15-receipt", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent",
                    blocked_by=["`07-catalogue`", "`15-receipt`"])
        write_ledger(self.feature, "batch-aaa111", [("07", "done")])
        write_ledger(self.feature, "batch-bbb222", [("15", "done")])
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 1)
        self.assertIn("batch-aaa111", out.stdout)
        self.assertIn("batch-bbb222", out.stdout)
        self.assertIn("runs batch-aaa111, batch-bbb222", out.stdout)

    def test_the_table_says_a_blocker_sits_on_an_unmerged_branch(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "07b-setup", "ready-for-agent", blocked_by=["`07-catalogue`"])
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "1")
        self.assertIn("07 (on branch batch-<id5>)", out.stdout)

    def test_the_held_block_says_whether_the_run_merged(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>", [("07", "done")])
        out = run(self.root, "--count", "1")
        self.assertIn("batch-<id5>  NOT merged  done: 07", out.stdout)


class TheQueuedFlag(unittest.TestCase):
    """`LEDGER_RELEASES` offers a live run's own queued issues to a new batch.
    On 2026-09-14 that meant eight of thirteen offered issues belonged to the
    live run's scope; against that, an abandoned run must not lock its queue
    for ever. WHICH IS RIGHT IS THE HUMAN'S, queued as `q-nb01-1`. The flag
    exists so they can drive all three and the default is today's behaviour."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()
        write_issue(self.root, "40-ci", "ready-for-agent")
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>", [("40", "queued"), ("41", "done")])

    def tearDown(self):
        self._tmp.cleanup()

    def test_released_is_the_default_and_offers_the_queued_issue(self):
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)
        self.assertIn("/run-issues 40\n", run(self.root, "--count", "1",
                                              "--queued", "released").stdout)

    def test_held_keeps_the_queued_issue_for_its_run(self):
        out = run(self.root, "--count", "1", "--queued", "held")
        self.assertEqual(out.returncode, 1)
        self.assertIn("NOTHING CAN START", out.stdout)
        self.assertIn("batch-<id5>  NOT merged  queued: 40", out.stdout)

    def test_fresh_holds_a_young_ledger(self):
        out = run(self.root, "--count", "1", "--queued", "fresh")
        self.assertEqual(out.returncode, 1)
        self.assertIn("NOTHING CAN START", out.stdout)

    def test_fresh_releases_a_stale_ledger(self):
        ledger = self.feature / "runs" / "batch-<id5>" / "run.md"
        old = time.time() - 30 * 86400
        os.utime(ledger, (old, old))
        out = run(self.root, "--count", "1", "--queued", "fresh")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_a_merged_runs_queued_row_always_releases(self):
        """A merged run will never build what it left queued, whatever the
        policy says, so holding it would strand the issue for ever."""
        write_ledger(self.feature, "batch-<id4>", [("40", "queued")],
                     state="merged")
        for mode in ("released", "held", "fresh"):
            with self.subTest(mode=mode):
                out = run(self.root, "--count", "1", "--queued", mode)
                self.assertNotIn("queued in run batch-<id4>", out.stdout)

    def test_a_fresh_window_of_zero_days_is_bad_usage(self):
        out = run(self.root, "--count", "1", "--queued", "fresh",
                  "--queued-fresh-days", "0")
        self.assertEqual(out.returncode, 2)


class HardenTheBatchBeforeTheRun(unittest.TestCase):
    """The harden guidance serves the BATCH, not the tracker. A sweep over one
    tracker's 116 files names 28 unstamped ones and refuses 3 on size, and a
    reader looking for today's batch would never find it in that."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_an_oversize_offered_issue_carries_the_scripts_refusal(self):
        """The limit is `check_issue_size.py`'s and the human's ruling of
        2026-09-14. This file never restates the number, so the refusal is
        quoted rather than recomputed."""
        write_issue(self.root, "40-ci", "ready-for-agent", criteria=40)
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("BEFORE the run, harden these offered issues", out.stdout)
        self.assertIn("check_issue_size.py refuses 1 of the 1 offered", out.stdout)
        self.assertIn("40 — 40 acceptance criteria, and the limit is 14",
                      out.stdout)
        self.assertIn("run check_issue_size.py --grade", out.stdout)
        self.assertIn("/harden-issues 40\n", out.stdout)
        self.assertFalse([line for line in out.stdout.splitlines()
                          if line.startswith("/run-issues")], out.stdout)

    def test_a_size_refusal_names_only_the_file_it_refused(self):
        write_issue(self.root, "40-ci", "ready-for-agent", criteria=40)
        write_issue(self.root, "41-timeout", "ready-for-agent")
        out = run(self.root, "--count", "2")
        self.assertIn("/harden-issues 40\n", out.stdout)
        self.assertIn("/run-issues 41\n", out.stdout)

    def test_a_shorter_file_name_is_not_read_inside_a_longer_one(self):
        """`23-home.md` is a substring of `123-home.md`. Matching the bare name
        would refuse issue 23 on a refusal that named only 123. One tracker in
        use carries 641 issues, so the case is live."""
        write_issue(self.root, "23-home", "ready-for-agent")
        write_issue(self.root, "123-home", "ready-for-agent", criteria=40)
        out = run(self.root, "--count", "2")
        self.assertIn("/harden-issues 123\n", out.stdout)
        self.assertIn("/run-issues 23\n", out.stdout)

    def test_an_unstamped_offered_issue_is_named_and_moved_off_the_run_line(self):
        write_issue(self.root, "40-ci", "ready-for-agent", hardened=False)
        write_issue(self.root, "41-timeout", "ready-for-agent")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("40", out.stdout)
        self.assertIn("no Hardened: stamp", out.stdout)
        self.assertIn("/harden-issues 40\n", out.stdout)
        self.assertIn("/run-issues 41\n", out.stdout)

    def test_a_light_line_stamps_a_light_issue_and_nothing_else(self):
        """Issue 43, AC3: rule 5 of issue 32 lets a `Level: light` issue skip
        hardening, and its `Light:` line stands in for the stamp. A
        `Level: full` issue with no stamp stays on the harden line as today.
        Measured on 2026-09-25: this pair printed `/harden-issues 01 02`."""
        write_issue(self.root, "01-light", "ready-for-agent", hardened=False,
                    extra_header=f"{LIGHT_LINE}\nLevel: light")
        write_issue(self.root, "02-full", "ready-for-agent", hardened=False,
                    extra_header="Level: full")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 01\n", out.stdout)
        self.assertIn("/harden-issues 02\n", out.stdout)
        self.assertIn("  no Hardened: stamp: 02\n", out.stdout)

    def test_a_light_line_on_a_full_issue_is_named_and_not_refused(self):
        """Issue 43, AC2, default `q-h0925b-43-2`: issue 42's lift rewrites a
        light issue to `Level: full` and leaves its `Light:` line. That pair
        is read as unstamped, and the mark says why."""
        write_issue(self.root, "01-lifted", "ready-for-agent", hardened=False,
                    extra_header=f"{LIGHT_LINE}\nLevel: full")
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/harden-issues 01\n", out.stdout)
        mark = [line for line in out.stdout.splitlines() if "Light:" in line]
        self.assertEqual(len(mark), 1, out.stdout)
        self.assertIn("Level: full", mark[0])

    def test_a_full_issue_with_a_pending_default_leaves_the_run_line(self):
        """Issue 43b, default `q-h0925b-seam-3`: the criteria gate refuses a
        `Level: full` issue stamped provisional whose criterion carries a
        pending default, so a `/run-issues` line naming it is a launch refused
        whole. The mark comes from `check_issue_ready.pending_defaults`."""
        path = self.root / "01-full.md"
        write_issue(self.root, "01-full", "ready-for-agent", hardened=False,
                    extra_header=f"Hardened (provisional): {PENDING_RULE_FROM} — "
                                 "1 default pending.\nLevel: full")
        path.write_text(path.read_text().replace(
            "- [ ] Criterion 1.", "- [ ] Criterion 1. Default (`q-h9-43b-1`): plain."))
        write_issue(self.root, "02-clean", "ready-for-agent")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("/run-issues 02\n", out.stdout)
        mark = [line for line in out.stdout.splitlines() if "rule 7" in line]
        self.assertEqual(len(mark), 1, out.stdout)
        self.assertIn("criterion 1", mark[0])

    def test_a_light_issue_keeps_its_other_marks(self):
        """Issue 43, must still be true: an open questions section still moves
        a light issue to the harden line."""
        write_issue(self.root, "01-light", "ready-for-agent", hardened=False,
                    extra_header=f"{LIGHT_LINE}\nLevel: light")
        path = self.root / "01-light.md"
        path.write_text(path.read_text()
                        + "\n## Questions open on this file\n\nOne must be "
                          "ruled before this issue runs.\n")
        out = run(self.root, "--count", "1")
        self.assertIn("/harden-issues 01\n", out.stdout)
        self.assertNotIn("no Hardened: stamp", out.stdout)

    def test_an_open_questions_section_is_named(self):
        write_issue(self.root, "40-ci", "ready-for-agent")
        path = self.root / "40-ci.md"
        path.write_text(path.read_text()
                        + "\n## Questions open on this file\n\nTwo, and both "
                          "must be ruled before this issue is stamped.\n")
        out = run(self.root, "--count", "1")
        self.assertIn("an open ## Questions open on this file", out.stdout)
        self.assertIn("/harden-issues 40\n", out.stdout)

    def test_a_defaulted_questions_section_is_not_named(self):
        """`## Questions, defaulted so the run never waits` is issue 42's
        heading on one tracker. Those questions do not stop a run."""
        write_issue(self.root, "40-ci", "ready-for-agent")
        path = self.root / "40-ci.md"
        path.write_text(path.read_text()
                        + "\n## Questions, defaulted so the run never waits\n\n"
                          "Both are written into the file as defaults.\n")
        out = run(self.root, "--count", "1")
        self.assertNotIn("BEFORE the run", out.stdout)
        self.assertIn("/run-issues 40\n", out.stdout)

    def test_a_missing_blocked_by_section_is_a_note_and_keeps_its_place(self):
        """This file reads a missing section as no blockers, measured on
        2026-09-13: nine files on one tracker had none and all nine genuinely had
        none. So it is worth saying, and not worth pulling a stamped, sized,
        ready issue out of a batch for."""
        write_issue(self.root, "40-ci", "ready-for-agent",
                    blocked_by=NO_SECTION)
        out = run(self.root, "--count", "1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("no ## Blocked by section", out.stdout)
        self.assertIn("/run-issues 40\n", out.stdout)
        self.assertNotIn("/harden-issues 40", out.stdout)

    def test_no_number_sits_on_two_pasteable_lines(self):
        write_issue(self.root, "34-picker", "needs-harden")
        write_issue(self.root, "35-note", "ready-for-agent", blocked_by=["34-picker"])
        write_issue(self.root, "40-ci", "ready-for-agent", hardened=False)
        write_issue(self.root, "41-timeout", "ready-for-agent")
        out = run(self.root, "--count", "2")
        self.assertEqual(out.returncode, 0, out.stderr)
        seen = []
        for line in out.stdout.splitlines():
            if line.startswith(("/harden-issues ", "/run-issues ")):
                seen += line.split()[1:]
        self.assertEqual(sorted(seen), sorted(set(seen)), out.stdout)

    def test_a_clean_batch_prints_no_harden_block_at_all(self):
        write_issue(self.root, "40-ci", "ready-for-agent")
        write_issue(self.root, "41-timeout", "ready-for-agent")
        out = run(self.root, "--count", "2")
        self.assertNotIn("BEFORE the run", out.stdout)
        self.assertIn("/run-issues 40 41\n", out.stdout)

    def test_a_missing_size_script_is_a_note_and_never_a_pass(self):
        """The ordinary road where this pack ships without the size script.

        Three values come back, the shape `harden_the_batch` unpacks. It used
        to be two here and three everywhere else, so the one case that matters
        — the script absent — raised `ValueError` in the caller instead of
        printing the note. The arity is asserted here so it cannot drift again.
        """
        write_issue(self.root, "40-ci", "ready-for-agent")
        issues = next_batch.load_issues(self.root)
        ok, refusals, notes = next_batch.size_check(
            self.root, [self.root / "40-ci.md"],
            script=self.root / "no-such-script.py")
        self.assertTrue(ok)
        self.assertEqual(refusals, [])
        self.assertIn("was not found", "\n".join(notes))
        self.assertIn("Nothing here says the batch is the right size",
                      "\n".join(notes))
        self.assertEqual(issues["40"].marks, [])

    def test_an_empty_batch_returns_the_same_three_values(self):
        """Nothing to grade is the commonest road of all, and it returned two."""
        ok, refusals, notes = next_batch.size_check(self.root, [])
        self.assertTrue(ok)
        self.assertEqual(refusals, [])
        self.assertEqual(notes, [])

    def test_every_road_out_of_size_check_returns_three_values(self):
        """Read the whole function, not the roads somebody remembered.

        Two of the six returns were two-tuples and four were three-tuples, and
        the two drills here covered neither of the two. Listing the roads to
        check is how that happens again, so this reads them all out of the
        source and refuses any that does not hand back three.
        """
        source = textwrap.dedent(inspect.getsource(next_batch.size_check))
        tree = ast.parse(source)
        returns = [node for node in ast.walk(tree)
                   if isinstance(node, ast.Return) and node.value is not None]
        self.assertGreaterEqual(len(returns), 6, "the function lost its roads")
        wrong = [ast.unparse(node) for node in returns
                 if not (isinstance(node.value, ast.Tuple)
                         and len(node.value.elts) == 3)]
        self.assertEqual([], wrong, "these return something other than three "
                                    "values: " + "; ".join(wrong))


class LessText(unittest.TestCase):
    """The human read the output at `--count 20` on 2026-09-15 and asked for less
    of it. Three blocks repeated one phrase on every line, and a fourth named
    files by absolute path where a number would do."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        self.root = self.feature / "issues"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_held_block_prints_one_line_per_run_and_status(self):
        """Fifteen held issues printed fifteen copies of
        `done in run batch-<id5> (NOT merged)`."""
        for name in ("07-catalogue", "08-request", "09-assign", "41-timeout"):
            write_issue(self.root, name, "ready-for-agent")
        write_issue(self.root, "10-revision", "ready-for-agent")
        write_ledger(self.feature, "batch-<id5>",
                     [("07", "done"), ("08", "done"), ("09", "done"),
                      ("10", "in-progress")])
        out = run(self.root, "--count", "1")
        held = [line for line in out.stdout.splitlines()
                if line.startswith("  batch-")]
        self.assertEqual(held, ["  batch-<id5>  NOT merged  done: 07 08 09",
                                "  batch-<id5>  NOT merged  in-progress: 10"])

    def test_the_waiting_block_names_numbers_and_puts_the_legend_in_the_heading(self):
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "08-request", "ready-for-agent")
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_issue(self.root, "30b-report", "ready-for-agent",
                    blocked_by=["`07-catalogue`", "`08-request`"])
        write_ledger(self.feature, "batch-<id5>",
                     [("07", "done"), ("08", "done")])
        out = run(self.root, "--count", "1")
        block = out.stdout.split("Waiting on run batch-<id5> to merge")[1]
        self.assertIn("Each number below is done on that branch", block)
        row = [line for line in block.splitlines() if line.startswith("  30b")]
        self.assertEqual(row, ["  30b    07 08"])
        self.assertNotIn("not in main,", "\n".join(row))

    def test_a_blocker_the_run_has_not_finished_keeps_its_bracket(self):
        """A merge does not release a blocker the run is still building, so
        that one is not covered by the heading's promise."""
        write_issue(self.root, "07-catalogue", "ready-for-agent")
        write_issue(self.root, "17-stages", "ready-for-agent")
        write_issue(self.root, "41-timeout", "ready-for-agent")
        write_issue(self.root, "27-bills", "ready-for-agent",
                    blocked_by=["`07-catalogue`", "`17-stages`"])
        write_ledger(self.feature, "batch-<id5>",
                     [("07", "done"), ("17", "gates")])
        out = run(self.root, "--count", "1")
        row = [line for line in out.stdout.splitlines()
               if line.startswith("  27 ")]
        self.assertEqual(row, ["  27     07 17 (gates)"])

    def test_the_size_refusal_names_issue_numbers_once_per_reason(self):
        """Fourteen files sharing one sentence printed it fourteen times, each
        behind an absolute path."""
        for name in ("34-picker", "35-note", "36-region"):
            write_issue(self.root, name, "ready-for-agent", criteria=0)
        out = run(self.root, "--count", "3")
        block = out.stdout.split("BEFORE the run")[1]
        reasons = [line for line in block.splitlines()
                   if line.startswith("    34")]
        self.assertEqual(len(reasons), 1)
        self.assertIn("34 35 36 — carries no", reasons[0])
        self.assertNotIn(str(self.root), block)

    def test_the_marks_print_one_line_per_mark(self):
        write_issue(self.root, "34-picker", "ready-for-agent", hardened=False)
        write_issue(self.root, "35-note", "ready-for-agent", hardened=False)
        write_issue(self.root, "41-timeout", "ready-for-agent")
        out = run(self.root, "--count", "3")
        stamp = [line for line in out.stdout.splitlines()
                 if line.strip().startswith("no Hardened: stamp")]
        self.assertEqual(stamp, ["  no Hardened: stamp: 34 35"])

    def test_an_unparsed_size_line_is_still_printed(self):
        """Nothing the script says is dropped silently, whatever this reader
        fails to recognise in it."""
        refusals, rest = next_batch.split_size_refusal(
            ["/tmp/40-ci.md: 20 acceptance criteria, and the limit is 14. "
             "Cut this issue. The 20 counted:",
             "      /tmp/40-ci.md:12: 1. A criterion.",
             "Refused: 1 of 1 graded issue(s) carry more than 14 criteria.",
             "something this reader has never seen"],
            "/tmp", ["/tmp/40-ci.md"])
        self.assertEqual(
            refusals,
            [("/tmp/40-ci.md",
              "20 acceptance criteria, and the limit is 14. Cut this issue.")])
        self.assertEqual(rest, ["something this reader has never seen"])


if __name__ == "__main__":    unittest.main()
