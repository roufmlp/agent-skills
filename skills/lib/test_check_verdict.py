#!/usr/bin/env python3
"""Tests for check_verdict.

The fixtures copy the three shapes the four orchestrator skills actually
produce: an issue file carrying one heading per `/run-issues` gate, a
`/parallel-hunt` bug file where the finder's evidence is already on disk before
any gate writes, and the `gate.md` skeleton `/panel-review` now opens before it
spawns its gate.

The bug file matters most. Its evidence section means the file is never empty,
so a check that only asks "does the file exist and hold bytes" passes while the
gate has written nothing at all. That is why the section is a first-class
argument rather than an extra.
"""

import os
import tempfile
import unittest

from check_verdict import (
    decide,
    main,
    pending_ids,
    read_section,
)

ISSUE_BOTH_GATES = """# Issue 288 — the withdrawn purchase order

## Acceptance criteria

1. A withdrawn order never counts as a win.

## Verify gate

PASS. Drove: /deals/12, /deals/12/orders.

## Review gate

REJECT. The guard reads the wrong column, `orders.ts:214`.
"""

ISSUE_VERIFY_ONLY = """# Issue 288 — the withdrawn purchase order

## Acceptance criteria

1. A withdrawn order never counts as a win.

## Verify gate

PASS. Drove: /deals/12.

## Review gate

## Notes

The runner committed at 04:12.
"""

BUG_FILE_NO_GATE = """# PH-014 — the quote total drops the freight line

## Evidence

`quote-total.ts:88` sums `lines` and never adds `freight`.

## Reproducer

`npm test -- quote-total` with the freight fixture.

## Claim gate
"""

GATE_SKELETON = """# Gate verdicts — 2026-08-15 workflow audit

| id | verdict | why |
|---|---|---|
| p1-1 | confirmed | the citation says what p1 claims |
| p2-1 | pending | |
| p3-1 | **pending** | |
| inv-1 | HOLDS | `SKILL.md:40` |
"""

GATE_COMPLETE = """# Gate verdicts

| id | verdict | why |
|---|---|---|
| p1-1 | confirmed | the citation holds |
| p2-1 | retracted | an inference dressed as an observation |
| inv-1 | UNTESTABLE BY READING | reading shows presence, never behaviour |
"""


class ReadSection(unittest.TestCase):
    def test_reads_the_named_section(self):
        self.assertIn("REJECT", read_section(ISSUE_BOTH_GATES, "## Review gate"))

    def test_accepts_the_section_name_without_its_hashes(self):
        self.assertIn("REJECT", read_section(ISSUE_BOTH_GATES, "Review gate"))

    def test_matches_the_heading_case_insensitively(self):
        self.assertIn("REJECT", read_section(ISSUE_BOTH_GATES, "## review GATE"))

    def test_stops_at_the_next_heading(self):
        self.assertNotIn("Review gate", read_section(ISSUE_BOTH_GATES, "## Verify gate"))

    def test_returns_none_when_the_heading_is_absent(self):
        self.assertIsNone(read_section(BUG_FILE_NO_GATE, "## Fix gate"))

    def test_returns_an_empty_string_for_a_heading_with_nothing_under_it(self):
        self.assertEqual(read_section(ISSUE_VERIFY_ONLY, "## Review gate").strip(), "")

    def test_does_not_match_a_heading_that_merely_starts_the_same(self):
        text = "## Review gate notes\n\nnot the verdict.\n"
        self.assertIsNone(read_section(text, "## Review gate"))


class QualifiedHeadings(unittest.TestCase):
    """Counted across one project's 200-odd issue files, 2026-08-16.

    78 review-gate headings read `## Review gate` exactly. The rest qualify it:
    16 `— attempt 2`, 10 `— 2026-07-23`, 3 `— critical variant, 2026-08-09`, 2
    with a comma instead of a dash. A rule that demands the bare heading refuses
    every one of those, and a check that misfires costs a run more than no check
    does.
    """

    def test_matches_an_attempt_qualifier(self):
        text = "## Review gate — attempt 2\n\nREJECT.\n"
        self.assertIn("REJECT", read_section(text, "## Review gate"))

    def test_matches_a_date_qualifier(self):
        text = "## Review gate — 2026-07-23\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Review gate"))

    def test_matches_a_comma_qualifier(self):
        text = "## Verify gate, 2026-08-03\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Verify gate"))

    def test_matches_a_variant_qualifier(self):
        text = "## Review gate — critical variant, 2026-08-09\n\nREJECT.\n"
        self.assertIn("REJECT", read_section(text, "## Review gate"))

    def test_matches_a_heading_that_says_verdict_out_loud(self):
        """Four in the corpus read `## Review gate verdict …`, one `re-verdict`."""
        text = "## Review gate verdict — PASS (2026-07-22)\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Review gate"))

    def test_matches_a_re_verdict_heading(self):
        text = "## Review gate re-verdict (fable @ max, 2026-07-19): PASS\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Review gate"))

    def test_matches_a_deeper_heading_level(self):
        """The 2026-07-24 run wrote its gates at `###`, not `##`."""
        text = "### Review gate 2026-07-24 — PASS (Opus @ high)\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Review gate"))

    def test_matches_a_date_with_no_separator_before_it(self):
        text = "## Verify gate 2026-07-24 — PASS\n\nPASS.\n"
        self.assertIn("PASS", read_section(text, "## Verify gate"))

    def test_stops_at_a_sibling_heading_of_the_same_deeper_level(self):
        text = (
            "### Verify gate 2026-07-24 — PASS\n\nverify said this.\n\n"
            "### Review gate 2026-07-24 — PASS\n\nreview said this.\n"
        )
        body = read_section(text, "## Verify gate")
        self.assertIn("verify said this", body)
        self.assertNotIn("review said this", body)

    def test_still_refuses_an_unrelated_continuation(self):
        """The counted words are allowed; anything else is a new section."""
        self.assertIsNone(read_section("## Review gate notes\n\nx.\n", "## Review gate"))


class BugFileHeadings(unittest.TestCase):
    """Counted across one project's 335 `/parallel-hunt` bug files, 2026-08-16.

    138 gate headings: 121 spell the name with a space and 17 with a hyphen
    (`claim-gate` 11, `fix-gate` 6). After the name come `verdict` 99 times,
    nothing 31 times, `batch` 7 times, and `verdict on the rework` once.
    """

    def test_matches_a_hyphenated_section_name(self):
        text = "## Fix-gate verdict (2026-07-24) — VERIFIED\n\nVERIFIED.\n"
        self.assertIn("VERIFIED", read_section(text, "## Fix gate"))

    def test_matches_a_batch_qualifier(self):
        text = "## Fix gate batch 8 — verdict: `verified`\n\nVERIFIED.\n"
        self.assertIn("VERIFIED", read_section(text, "## Fix gate"))

    def test_matches_a_verdict_carrying_a_clause(self):
        text = "## Claim gate verdict on the rework\n\nopen.\n"
        self.assertIn("open", read_section(text, "## Claim gate"))

    def test_refuses_a_heading_that_wrapped_onto_a_second_line(self):
        """`bugs/ph8-03.md`, the one such file in 335, 2026-07-27.

        Its title ran over: `## Fix gate verdict … with one` then
        `## over-claim corrected`. The body sits under the second line, so this
        section reads empty and the check refuses a verdict that is really
        there. Refusing is the correct direction for this check — a false pass
        is what it exists to prevent — so the message names the wrap instead.
        """
        text = (
            "## Fix gate verdict — 2026-07-27: **verified**, with one\n"
            "## over-claim corrected\n\nStatus fix-ready -> verified.\n"
        )
        decision = decide(text, "## Fix gate")
        self.assertFalse(decision.allowed)
        self.assertIn("wrapped", decision.reason)

    def test_matches_a_verdict_naming_the_transition(self):
        text = "## Claim gate verdict, 2026-07-27 — `candidate` -> **`open`**\n\nx.\n"
        self.assertIn("x.", read_section(text, "## Claim gate"))

    def test_reads_the_last_matching_heading(self):
        """Attempt 2's empty section is the answer, not attempt 1's verdict."""
        text = (
            "## Review gate\n\nREJECT on the first attempt.\n\n"
            "## Review gate — attempt 2\n"
        )
        self.assertEqual(read_section(text, "## Review gate").strip(), "")
        self.assertFalse(decide(text, "## Review gate").allowed)


class PendingIds(unittest.TestCase):
    def test_finds_a_pending_row(self):
        self.assertIn("p2-1", pending_ids(GATE_SKELETON))

    def test_finds_a_pending_row_wearing_emphasis(self):
        self.assertIn("p3-1", pending_ids(GATE_SKELETON))

    def test_ignores_rows_already_judged(self):
        self.assertNotIn("p1-1", pending_ids(GATE_SKELETON))
        self.assertNotIn("inv-1", pending_ids(GATE_SKELETON))

    def test_finds_nothing_in_a_complete_table(self):
        self.assertEqual(pending_ids(GATE_COMPLETE), [])

    def test_ignores_the_word_pending_in_prose(self):
        """A verdict may say a question is pending the human's answer."""
        prose = "REJECT. The fix waits on a decision still pending with the human.\n"
        self.assertEqual(pending_ids(prose), [])

    def test_reads_the_id_from_the_first_cell(self):
        self.assertEqual(pending_ids("| p9-4 | pending | |\n"), ["p9-4"])


class DecideOnAWholeFile(unittest.TestCase):
    def test_refuses_an_empty_file(self):
        self.assertFalse(decide("").allowed)

    def test_refuses_a_file_holding_only_whitespace(self):
        self.assertFalse(decide("\n\n   \n").allowed)

    def test_allows_a_complete_gate_table(self):
        self.assertTrue(decide(GATE_COMPLETE).allowed)

    def test_refuses_a_skeleton_nobody_finished(self):
        decision = decide(GATE_SKELETON)
        self.assertFalse(decision.allowed)
        self.assertIn("p2-1", decision.reason)
        self.assertIn("p3-1", decision.reason)

    def test_names_the_judged_rows_it_is_not_throwing_away(self):
        """A partial verdict is deliberately preserved; the refusal must say so."""
        self.assertIn("2 of 4", decide(GATE_SKELETON).reason)


class DecideOnASection(unittest.TestCase):
    def test_allows_a_section_the_gate_wrote(self):
        self.assertTrue(decide(ISSUE_BOTH_GATES, "## Review gate").allowed)

    def test_refuses_a_heading_with_nothing_under_it(self):
        decision = decide(ISSUE_VERIFY_ONLY, "## Review gate")
        self.assertFalse(decision.allowed)
        self.assertIn("Review gate", decision.reason)

    def test_refuses_when_the_heading_is_absent_altogether(self):
        decision = decide(BUG_FILE_NO_GATE, "## Fix gate")
        self.assertFalse(decision.allowed)
        self.assertIn("Fix gate", decision.reason)

    def test_refuses_a_bug_file_whose_evidence_is_the_only_content(self):
        """The trap: the finder's evidence makes the file non-empty on its own."""
        self.assertFalse(decide(BUG_FILE_NO_GATE, "## Claim gate").allowed)
        self.assertTrue(decide(BUG_FILE_NO_GATE).allowed)

    def test_ignores_a_pending_row_outside_the_named_section(self):
        text = ISSUE_BOTH_GATES + "\n## Follow-ups\n\n| f-1 | pending | |\n"
        self.assertTrue(decide(text, "## Review gate").allowed)

    def test_refuses_a_pending_row_inside_the_named_section(self):
        text = "## Review gate\n\n| r-1 | pending | |\n"
        self.assertFalse(decide(text, "## Review gate").allowed)


class Main(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, name, text):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_refuses_a_file_that_does_not_exist(self):
        missing = os.path.join(self.dir.name, "gate.md")
        self.assertEqual(main(["--file", missing]), 1)

    def test_refuses_a_directory_given_where_a_file_was_meant(self):
        self.assertEqual(main(["--file", self.dir.name]), 1)

    def test_authorises_a_finished_verdict(self):
        path = self.write("gate.md", GATE_COMPLETE)
        self.assertEqual(main(["--file", path]), 0)

    def test_refuses_an_unfinished_verdict(self):
        path = self.write("gate.md", GATE_SKELETON)
        self.assertEqual(main(["--file", path]), 1)

    def test_authorises_a_section_the_gate_wrote(self):
        path = self.write("288.md", ISSUE_BOTH_GATES)
        self.assertEqual(main(["--file", path, "--section", "## Review gate"]), 0)

    def test_refuses_a_section_the_gate_did_not_write(self):
        path = self.write("288.md", ISSUE_VERIFY_ONLY)
        self.assertEqual(main(["--file", path, "--section", "## Review gate"]), 1)


# A gate section can also be STALE rather than absent: the file carries last
# attempt's verdict under the same heading, and this attempt's gate died before
# writing. Measured over one project's issue files on 2026-08-20: 194 files
# carry gate sections and no attempt record at all, 4 carry both with the gates
# last, and 1 — whose two attempt-2 gates died with their session — carries
# the record last. The order is the discriminator, so the order is what is read.

ISSUE_ATTEMPT_TWO_UNGRADED = """# Issue 390a — the item reader

## Implementation record, attempt 1, 2026-08-19

Built the reader.

## Review gate

| id | verdict |
|---|---|
| rev-01 | reject |

## Verify gate

| id | verdict |
|---|---|
| ver-01 | reject |

## Implementation record, attempt 2, 2026-08-19

Rebuilt on both gates' ground. No gate has read this diff.
"""

ISSUE_ATTEMPT_TWO_GRADED = ISSUE_ATTEMPT_TWO_UNGRADED + """
## Review gate — attempt 2

| id | verdict |
|---|---|
| rev-01 | pass |

## Verify gate — attempt 2

| id | verdict |
|---|---|
| ver-01 | pass |
"""


class StaleSection(unittest.TestCase):
    def test_refuses_a_gate_section_older_than_the_newest_attempt_record(self):
        for section in ("## Verify gate", "## Review gate"):
            with self.subTest(section=section):
                decision = decide(ISSUE_ATTEMPT_TWO_UNGRADED, section)
                self.assertFalse(decision.allowed)
                self.assertIn("attempt 2", decision.reason)

    def test_allows_a_gate_section_written_after_the_newest_record(self):
        for section in ("## Verify gate", "## Review gate"):
            with self.subTest(section=section):
                self.assertTrue(decide(ISSUE_ATTEMPT_TWO_GRADED, section).allowed)

    def test_a_file_with_no_attempt_record_is_unaffected(self):
        self.assertTrue(decide(ISSUE_BOTH_GATES, "## Verify gate").allowed)


if __name__ == "__main__":
    unittest.main()
