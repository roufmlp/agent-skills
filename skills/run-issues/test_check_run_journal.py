#!/usr/bin/env python3
"""The decisions in `check_run_journal.py`, driven on real shapes.

The ledger below is run `batch-b00631`'s own status table, trimmed to the
columns the check reads. The journal fixtures are that run's real headings: one
set as the runner left them, stopping after issue 34, and one set as the finale
left them, after it reconstructed the four missing entries.

The first is the state the check exists to refuse, and it is what a resuming
runner would have opened had the run halted in issues 35, 27b, 21c or 110.
"""

import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_run_journal as guard

LEDGER = """
# Run ledger — `batch-b00631`

## Status

State: merged

| Issue | Status | Estimate | Stamps |
|---|---|---|---|
| 22b | done | small — 2 criteria | attempt 1 · correction: open -> closed 01:31 · committed fc423c2 |
| 34  | done | medium — 6 criteria | attempt 1 · no correction round · committed 4716787 |
| 35  | done | medium — 8 criteria | attempt 1 · correction: open -> closed 02:31 · committed f84a968 |
| 27b | done | medium — two read surfaces | attempt 1 · correction: open -> closed 03:16 · committed 2fe0c26 |
| 21c | done | large — largest criteria section | attempt 1 · no correction round · committed e2863a2 |
| 110 | done | large — one migration (0043) | attempt 1 · correction: open -> closed 04:23 · committed 5c7ee0a |

## Carry-forward
"""

# As the runner left it. Two issues journalled, six committed.
JOURNAL_BEHIND = """
# Run journal — `batch-b00631`

## 2026-09-19 — launch
## 2026-09-19 — baseline measured
## 2026-09-19 — issue 22b, round 1
## 2026-09-19 — issue 34, prep, read-only, while the gates ran
## 2026-09-19 — issue 22b, correction round and close
## 2026-09-19 — issue 34, round 1, BOTH GATES PASSED
"""

# As the finale left it, with the four reconstructed entries.
JOURNAL_WHOLE = JOURNAL_BEHIND + """
## 2026-09-19 — WRITTEN LATE, AT THE FINALE, AND THE LATENESS IS THE POINT
## 2026-09-19 — issue 35, round 1 plus a correction round
## 2026-09-19 — issue 27b, round 1 plus a correction round
## 2026-09-19 — issue 21c, round 1, BOTH GATES PASSED
## 2026-09-19 — issue 110, round 1 plus a runner-opened correction round
"""


class CommittedTest(unittest.TestCase):
    def test_reads_every_committed_issue_in_the_ledger_order(self):
        self.assertEqual(guard.committed(LEDGER), ["22b", "34", "35", "27b", "21c", "110"])

    def test_a_row_with_no_commit_is_not_committed(self):
        ledger = LEDGER.replace("· committed 5c7ee0a", "· gates open, no commit yet")
        self.assertNotIn("110", guard.committed(ledger))


class JournalledTest(unittest.TestCase):
    def test_reads_the_issues_its_headings_name(self):
        self.assertEqual(guard.journalled(JOURNAL_BEHIND), {"22b", "34"})

    def test_one_heading_may_name_two_issues(self):
        self.assertEqual(
            guard.journalled("## 2026-09-19 — issues 35 and 27b, closed together"),
            {"35", "27b"},
        )

    def test_a_heading_naming_no_issue_is_neither_counted_nor_refused(self):
        self.assertEqual(guard.journalled("## 2026-09-19 — launch\n## baseline measured"), set())

    def test_a_mention_in_the_body_does_not_count_as_an_entry(self):
        # A cross-reference inside another issue's entry is not a record of
        # that issue's own round. Counting it would let one entry satisfy an
        # issue nobody wrote about.
        body = "## 2026-09-19 — issue 34, round 1\n\nIt retires a test issue 35 writes.\n"
        self.assertEqual(guard.journalled(body), {"34"})

    def test_an_id_is_not_matched_inside_a_longer_one(self):
        self.assertEqual(guard.journalled("## issue 1100, round 1"), {"1100"})
        self.assertEqual(guard.journalled("## issue 21c, round 1"), {"21c"})

    def test_reads_the_separators_a_runner_actually_writes(self):
        for heading in ("## issues 35, 27b", "## issues 35 & 27b", "## issues 35 + 27b"):
            self.assertEqual(guard.journalled(heading), {"35", "27b"}, heading)

    def test_ordinary_prose_after_an_id_ends_the_list(self):
        self.assertEqual(guard.journalled("## issue 34, prep, read-only"), {"34"})
        self.assertEqual(
            guard.journalled("## issue 110, round 1 plus a runner-opened correction"),
            {"110"},
        )

    def test_the_documented_limit_is_real_and_only_adds(self):
        # The docstring says a heading like this reads `1` as a second id. It is
        # driven here rather than only claimed, so the day somebody tightens the
        # separator this test says what changed.
        self.assertEqual(guard.journalled("## issue 34, 1 of 2"), {"34", "1"})


class GapsTest(unittest.TestCase):
    def test_names_the_four_the_runner_stopped_writing(self):
        self.assertEqual(guard.gaps(LEDGER, JOURNAL_BEHIND), ["35", "27b", "21c", "110"])

    def test_the_finale_s_reconstruction_closes_every_gap(self):
        self.assertEqual(guard.gaps(LEDGER, JOURNAL_WHOLE), [])

    def test_an_uncommitted_issue_is_not_owed_an_entry(self):
        # Plenty of issues are mid-flight when the check runs. Only what is
        # committed has a record a resuming runner would go looking for.
        ledger = LEDGER.replace("· committed 5c7ee0a", "· attempt 1 in flight")
        self.assertEqual(guard.gaps(ledger, JOURNAL_BEHIND), ["35", "27b", "21c"])


class MainTest(unittest.TestCase):
    def _run(self, ledger, journal, write_journal=True):
        errors = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = os.path.join(directory, "run.md")
            journal_path = os.path.join(directory, "run-journal.md")
            with open(ledger_path, "w", encoding="utf-8") as handle:
                handle.write(ledger)
            if write_journal:
                with open(journal_path, "w", encoding="utf-8") as handle:
                    handle.write(journal)
            stderr, sys.stderr = sys.stderr, errors
            try:
                code = guard.main(["--run", directory])
            finally:
                sys.stderr = stderr
        return code, errors.getvalue()

    def test_refuses_the_run_as_the_runner_left_it(self):
        code, errors = self._run(LEDGER, JOURNAL_BEHIND)
        self.assertEqual(code, 1)
        self.assertIn("journal-behind", errors)
        for issue in ("35", "27b", "21c", "110"):
            self.assertIn(issue, errors)

    def test_passes_the_run_as_the_finale_left_it(self):
        self.assertEqual(self._run(LEDGER, JOURNAL_WHOLE)[0], 0)

    def test_refuses_a_missing_journal_rather_than_passing_over_it(self):
        code, errors = self._run(LEDGER, "", write_journal=False)
        self.assertEqual(code, 1)
        self.assertIn("no-journal", errors)

    def test_refuses_a_ledger_that_records_no_commit_at_all(self):
        # The silence this check exists to prevent, arriving through the check
        # itself: a stamps column that stopped naming commits would otherwise
        # print `ok` on nothing.
        ledger = LEDGER.replace("committed", "landed")
        code, errors = self._run(ledger, JOURNAL_WHOLE)
        self.assertEqual(code, 1)
        self.assertIn("empty-input", errors)
        self.assertIn("6 candidate row(s)", errors)

    def test_reports_the_unreadable_file_rather_than_guessing(self):
        errors = io.StringIO()
        stderr, sys.stderr = sys.stderr, errors
        try:
            code = guard.main(["--run", "/no/such/run/directory"])
        finally:
            sys.stderr = stderr
        self.assertEqual(code, 2)
        self.assertIn("unreadable", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
