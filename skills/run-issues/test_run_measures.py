#!/usr/bin/env python3
"""Cases for run_measures.py — the per-issue line and the five "faster" figures.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 3, deliverable 3 and rulings 5, 17, 18, 20 and 21.

    python3 -m unittest test_run_measures
"""

from __future__ import annotations

import datetime
import os
import pathlib
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_measures as tool

CORPUS = pathlib.Path("/home/user/project/.scratch/example-feature")

LEDGER = """
## Status

| issue | status | estimate | stamps |
|---|---|---|---|
| 149c | done | 60-90 min | attempt 1; verify: pass; review: pass; committed `75e23f45` |
| 149e | done | 60-90 min | attempt 1; verify: pass; review: reject; attempt 2; verify: pass; review: pass; committed `91f2af9f` |

## Carry-forward

| after | total | files |
|---|---|---|
| 149c (-13, -3) | 51 | 29 |
"""

BRIEFING = """
## The run on the rail

| Issue | Stage     | Kind    | Sentence |
|-------|-----------|---------|----------|
| 149c  | quotation | guard   | Accept and re-issue refuse a failed read |
| 149e  | award     | guard   | A failed order read is not 'gone' |

## Ruled — 2, overturn any of these

1. **149e's coverage refusal was accepted without a correction round**, because
   the one line is unreachable through a fake that predates the slice.
2. **No band is drawn on the rail**, because the two slices that reached zero
   sit on `floor`.
"""


def when(text):
    return datetime.datetime.fromisoformat(text)


SPANS = {
    "149c": {"first": when("2026-09-06T10:00:00+00:00"),
             "last": when("2026-09-06T11:00:00+00:00"),
             "agent": 90.0, "steps": 3,
             "roles": {"run-issues-implementer", "run-issues-verify-gate",
                       "run-issues-review-gate-critical"}},
    "149e": {"first": when("2026-09-06T11:00:00+00:00"),
             "last": when("2026-09-06T13:00:00+00:00"),
             "agent": 200.0, "steps": 6,
             "roles": {"run-issues-implementer",
                       "run-issues-implementer-escalated",
                       "run-issues-verify-gate", "run-issues-review-gate"}},
}


def records(**over):
    given = dict(batch="batch-test", ledger_text=LEDGER, briefing_text=BRIEFING,
                 spans=SPANS, touched=lambda sha: [])
    given.update(over)
    return {one["issue"]: one for one in tool.issue_records(**given)}


class OneLinePerIssue(unittest.TestCase):
    """Ruling 17. The denominator is the repaired `status_rows`, so the
    carry-forward table in the fixture must contribute nothing."""

    def test_one_line_per_status_row_and_no_more(self):
        self.assertEqual(sorted(records()), ["149c", "149e"])

    def test_every_line_names_its_batch(self):
        """The batch id is the key of both files (ruling 17), and a per-issue
        line that does not carry it cannot be joined to its run."""
        for one in records().values():
            self.assertEqual(one["batch"], "batch-test")


class RulingSeventeensFigures(unittest.TestCase):
    """estimate, span, agent minutes, attempt, correction rounds, strikes,
    escalation, both gate verdicts."""

    def test_the_span_comes_from_the_transcript(self):
        self.assertEqual(records()["149c"]["span_minutes"], 60.0)

    def test_agent_minutes_come_from_the_transcript(self):
        self.assertEqual(records()["149e"]["agent_minutes"], 200.0)

    def test_the_attempt_count_comes_from_the_ledger(self):
        self.assertEqual(records()["149e"]["attempts"], 2)

    def test_both_gate_verdicts_are_carried_apart(self):
        """149e: the review gate rejected attempt 1 and verify passed it."""
        one = records()["149e"]
        self.assertEqual(one["verify"], "pass")
        self.assertEqual(one["review"], "reject")

    def test_a_strike_is_carried(self):
        self.assertEqual(records()["149e"]["strikes"], 1)
        self.assertEqual(records()["149c"]["strikes"], 0)

    def test_an_escalation_is_read_by_role_name(self):
        self.assertTrue(records()["149e"]["escalated"])
        self.assertFalse(records()["149c"]["escalated"])


class TheFiveKindFacts(unittest.TestCase):
    """Ruling 20: rail stage key, estimate midpoint, critical gate variant
    ran, carried a migration, cut on a default."""

    def test_the_rail_stage_key_comes_from_the_briefing(self):
        self.assertEqual(records()["149c"]["stage"], "quotation")
        self.assertEqual(records()["149e"]["stage"], "award")

    def test_the_estimate_is_the_midpoint_in_minutes(self):
        """`60-90 min` is 75, not 60 and not 90 (ruling 18). Taking either end
        would flatter or damn the estimate by construction, which is the rule
        `estimate_accuracy.minutes_from` already carries."""
        self.assertEqual(records()["149c"]["estimate_minutes"], 75.0)

    def test_the_critical_variant_is_read_by_role_name(self):
        self.assertTrue(records()["149c"]["critical_gate"])
        self.assertFalse(records()["149e"]["critical_gate"])

    def test_a_migration_is_read_from_what_the_commit_touched(self):
        """The ledger row names the commit; git says what it held. Neither is
        derived from the other, which is the evidence rule
        `check_commit_order.py` was built on."""
        one = records(touched=lambda sha: ["supabase/migrations/0122_x.sql"]
                      if sha == "91f2af9f" else ["src/app/page.tsx"])
        self.assertTrue(one["149e"]["migration"])
        self.assertFalse(one["149c"]["migration"])

    def test_a_default_cut_is_read_from_the_briefings_ruled_section(self):
        """`## Ruled — N, overturn any of these` IS the record of a default:
        CLAUDE.md's rule is that every skill records each default as a default
        rather than a decision. An item naming the issue is that issue's."""
        self.assertTrue(records()["149e"]["cut_on_a_default"])
        self.assertFalse(records()["149c"]["cut_on_a_default"])

    def test_a_register_prefix_holding_the_id_is_not_the_issue(self):
        """`rg149c-02` carries `149c` and names a REGISTER ROW, not the issue.
        A word boundary is what tells them apart, and without it every run
        naming one of its own register rows would mark that issue defaulted."""
        briefing = BRIEFING.replace(
            "**149e's coverage refusal", "**`rg149c-02` is discharged")
        one = records(briefing_text=briefing)
        self.assertFalse(one["149c"]["cut_on_a_default"])


class WhatIsNotMeasuredIsNull(unittest.TestCase):
    """Sitting 2's rule, in the human's words: a run with no strikes is a fact, and
    a run whose strikes were never read is not. Every road here answers null
    rather than a zero or a false."""

    def test_an_issue_the_transcript_never_named_has_null_times(self):
        one = records(spans={})["149c"]
        self.assertIsNone(one["span_minutes"])
        self.assertIsNone(one["agent_minutes"])

    def test_an_issue_the_transcript_never_named_has_null_roles_not_false(self):
        """`escalated: false` would say it did not escalate. Null says nothing
        looked, and the two are a different fact about the pipeline."""
        one = records(spans={})["149c"]
        self.assertIsNone(one["escalated"])
        self.assertIsNone(one["critical_gate"])

    def test_a_briefing_with_no_rail_leaves_the_stage_null(self):
        self.assertIsNone(records(briefing_text="")["149c"]["stage"])

    def test_a_row_with_no_readable_estimate_is_null_not_zero(self):
        ledger = LEDGER.replace("| 60-90 min |", "|  |")
        self.assertIsNone(records(ledger_text=ledger)["149c"]["estimate_minutes"])

    def test_git_that_cannot_answer_leaves_the_migration_null(self):
        """A `false` here would say the commit held no migration. Null says
        nothing read it, which is what a missing repository means."""
        def refuses(sha):
            raise OSError("not a git working tree")
        self.assertIsNone(records(touched=refuses)["149c"]["migration"])

    def test_a_row_naming_no_commit_leaves_the_migration_null(self):
        ledger = LEDGER.replace("; committed `75e23f45`", "")
        self.assertIsNone(records(ledger_text=ledger)["149c"]["migration"])


class TheFiveFasterFigures(unittest.TestCase):
    """Ruling 5. The human's aim, stated: one look tells them where to optimise,
    with no mental arithmetic. So every one of the five is RECORDED, and none
    of them is left for a reader to divide."""

    ISSUES = [
        {"issue": "a", "estimate_minutes": 60.0, "span_minutes": 120.0,
         "agent_minutes": 90.0},
        {"issue": "b", "estimate_minutes": 100.0, "span_minutes": 100.0,
         "agent_minutes": 60.0},
    ]

    def figures(self, **over):
        given = dict(issues=self.ISSUES, wall_hours=4.0, idle_hours=1.0,
                     agent_hours=2.5)
        given.update(over)
        return tool.faster(**given)

    def test_wall_clock_per_issue(self):
        self.assertEqual(self.figures()["wall_minutes_per_issue"], 120.0)

    def test_idle_minutes_per_issue(self):
        """`run_timings.py:324` prints this and says "Compare THIS across
        runs, not the share", and until now it reached no row."""
        self.assertEqual(self.figures()["idle_minutes_per_issue"], 30.0)

    def test_agent_hours_per_issue(self):
        self.assertEqual(self.figures()["agent_hours_per_issue"], 1.25)

    def test_the_estimate_ratio_is_the_median_of_the_per_issue_ratios(self):
        """Two issues at 2.00x and 1.00x: the median is 1.50x. The median and
        not the mean, which is what `estimate_accuracy.py:284` already prints
        and what one runaway issue would otherwise decide on its own."""
        self.assertEqual(self.figures()["estimate_median_ratio"], 1.5)

    def test_an_issue_with_no_estimate_is_left_out_of_the_ratio(self):
        issues = self.ISSUES + [{"issue": "c", "estimate_minutes": None,
                                 "span_minutes": 50.0}]
        self.assertEqual(self.figures(issues=issues)["estimate_median_ratio"],
                         1.5)

    def test_no_issues_gives_nulls_and_never_a_division(self):
        got = self.figures(issues=[])
        self.assertIsNone(got["wall_minutes_per_issue"])
        self.assertIsNone(got["estimate_median_ratio"])

    def test_a_missing_clock_gives_a_null_for_that_figure_alone(self):
        got = self.figures(idle_hours=None)
        self.assertIsNone(got["idle_minutes_per_issue"])
        self.assertEqual(got["wall_minutes_per_issue"], 120.0)


class LongestStepPerKind(unittest.TestCase):
    """Ruling 21, across AGENT and STAMPED steps (ruling 19).

    A finale's mechanical half leaves no duration in a transcript at all
    (`run_timings.py:40-46`), so neither half alone can answer "where did the
    clock go". They are joined here and nowhere else.
    """

    STAMPED = [
        {"kind": "suite", "seconds": 600.0, "label": "full suite"},
        {"kind": "build", "seconds": 900.0, "label": "cold build"},
    ]
    AGENTS = [
        {"kind": "run-issues-implementer", "seconds": 3600.0,
         "label": "issue 149e"},
        {"kind": "run-issues-verify-gate", "seconds": 1200.0,
         "label": "issue 149c"},
    ]

    def test_both_halves_appear(self):
        found = tool.longest_steps(self.STAMPED, self.AGENTS)
        self.assertEqual(found["build"]["minutes"], 15.0)
        self.assertEqual(found["run-issues-implementer"]["minutes"], 60.0)

    def test_each_half_says_where_it_was_measured(self):
        """A stamped step and an agent step are measured by different
        instruments, and a reader comparing two numbers must be able to see
        that. The wrapper holds a wall clock; the transcript holds a tool
        call's own span."""
        found = tool.longest_steps(self.STAMPED, self.AGENTS)
        self.assertEqual(found["build"]["measured"], "stamped")
        self.assertEqual(found["run-issues-implementer"]["measured"], "agent")

    def test_a_kind_nothing_measured_is_absent_rather_than_zero(self):
        found = tool.longest_steps([], self.AGENTS)
        self.assertNotIn("suite", found)


class AgainstTheRealRun(unittest.TestCase):
    """`batch-170a59` on disk, not a fixture. Sitting 4's whole finding was
    that its first reading was measured against ONE ledger and seven dialects
    in the others were read as silence."""

    def setUp(self):
        self.ledger = CORPUS / "runs" / "batch-170a59" / "run.md"
        self.briefing = CORPUS / "runs" / "batch-170a59" / "merge-briefing.md"
        if not self.ledger.exists():
            self.skipTest("batch-170a59 is not on this machine")

    def rows(self):
        return {one["issue"]: one for one in tool.issue_records(
            batch="batch-170a59",
            ledger_text=self.ledger.read_text(encoding="utf-8"),
            briefing_text=self.briefing.read_text(encoding="utf-8")
            if self.briefing.exists() else "",
            spans={}, touched=lambda sha: [])}

    def test_it_reads_six_issues_and_not_twelve(self):
        """The whole of ruling 28's repair half, on the real file."""
        self.assertEqual(sorted(self.rows()),
                         ["149c", "149d", "149e", "149f", "149g", "149h"])

    def test_the_stages_are_the_ones_the_briefing_names(self):
        """Read off `merge-briefing.md` by hand, 2026-09-06."""
        rows = self.rows()
        self.assertEqual(rows["149c"]["stage"], "quotation")
        self.assertEqual(rows["149g"]["stage"], "floor")

    def test_the_estimates_are_the_midpoints_of_what_the_ledger_states(self):
        """The ledger states `60-90 min` for 149c and `30-45 min` for 149h."""
        rows = self.rows()
        self.assertEqual(rows["149c"]["estimate_minutes"], 75.0)
        self.assertEqual(rows["149h"]["estimate_minutes"], 37.5)


class TwoRuledHeadings(unittest.TestCase):
    """Found by measuring the corpus at the close of sitting 3, not by review.

    A merge briefing is written in passes, so several carry an EMPTY `## Ruled`
    placeholder early on and the real `## Ruled — N, overturn any of these`
    later. `archive-merge-briefing-batch-375cbf.md` holds one at line 529
    reading "Nothing yet." and the real one at line 1785;
    `archive-merge-briefing-batch-45c8b1.md` holds the same pair at 156 and
    2044.

    `ruled_section` took the FIRST match, so on those briefings it read the
    placeholder, found nothing, and every issue in the run read
    `cut_on_a_default: false`. **That is a false `false`** -- the same shape as
    the `status_rows` fault ruling 28 sent this sitting to repair: take the
    first thing that matches rather than the right thing, and report the answer
    with no sign that nothing was read.

    Every such section is now read, so a placeholder contributes nothing and
    the real one contributes its items, whichever order they sit in.
    """

    BRIEFING = """
## Ruled

Nothing yet.

## Finale

Some prose that names 149c and 149e in passing.

## Ruled — 2, overturn any of these

1. **149f's coverage refusal was accepted**, because the line is unreachable.
2. **No band is drawn on the rail.**
"""

    def test_the_later_section_is_read_and_not_only_the_placeholder(self):
        rows = {one["issue"]: one for one in tool.issue_records(
            batch="b", ledger_text=LEDGER, briefing_text=self.BRIEFING,
            spans={}, touched=lambda sha: [])}
        self.assertFalse(rows["149c"]["cut_on_a_default"])

    def test_an_issue_named_only_in_the_real_section_is_found(self):
        ruled = tool.ruled_section(self.BRIEFING)
        self.assertTrue(tool.cut_on_a_default("149f", ruled))

    def test_prose_between_the_two_sections_is_not_swept_in(self):
        """The bound still stops at the next heading. `## Finale` names 149c
        and 149e, and reading to the end of the file would mark both."""
        ruled = tool.ruled_section(self.BRIEFING)
        self.assertFalse(tool.cut_on_a_default("149e", ruled))

    def test_the_real_corpus_briefings_with_two_headings_read_their_items(self):
        """`batch-45c8b1` holds the placeholder at line 156 and the real
        section at 2044. Its real section states seven rulings."""
        path = CORPUS / "archive-merge-briefing-batch-45c8b1.md"
        if not path.exists():
            self.skipTest("the corpus is not on this machine")
        ruled = tool.ruled_section(path.read_text(encoding="utf-8",
                                                  errors="replace"))
        self.assertNotIn("Nothing yet", ruled)
        self.assertTrue(ruled.strip())


if __name__ == "__main__":
    unittest.main()
