#!/usr/bin/env python3
"""Cases for estimate_accuracy.py.

The anchor is run `414a-483-286335`, whose ledger estimated 26.5 hours of issue
time and whose issues occupied 13.8. The regression case is the fault the first
version shipped with: the finale and promotion prompts open by naming the RUN,
`**414a-483-286335**`, and a reader that takes the first `**…**` token reads
that as issue `414a`.

    python3 -m unittest test_estimate_accuracy
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

import estimate_accuracy as tool


LEDGER = """
## Status

| Issue | Est | Status | Stamps |
|---|---|---|---|
| 414a — resolve a reply matching several open invitations | 3.5h | done | … |
| 99f — a supplier's reply proves itself | 4h | done | … |
| 414d — the WhatsApp front door | 2.5h, expect long | done | … |
| 413b — a tender line that names a brand | 30-45 min | done | … |
| 412 — the registers take one at a time | 2-2.5 h | done | … |
"""


def transcript(rows) -> pathlib.Path:
    """A throwaway .jsonl. Each row is (call_time, result_time, type, prompt)."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for index, (started, ended, kind, prompt) in enumerate(rows):
        call = {
            "timestamp": started,
            "message": {"content": [{
                "type": "tool_use", "id": f"t{index}", "name": "Task",
                "input": {"subagent_type": kind, "prompt": prompt},
            }]},
        }
        result = {
            "timestamp": ended,
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": f"t{index}", "content": "done",
            }]},
        }
        handle.write(json.dumps(call) + "\n")
        handle.write(json.dumps(result) + "\n")
    handle.close()
    return pathlib.Path(handle.name)


class Durations(unittest.TestCase):
    def test_plain_hours(self):
        self.assertEqual(tool.minutes_from("3.5h"), 210)
        self.assertEqual(tool.minutes_from("4h"), 240)
        self.assertEqual(tool.minutes_from("1 hour"), 60)

    def test_minutes(self):
        self.assertEqual(tool.minutes_from("45 min"), 45)
        self.assertEqual(tool.minutes_from("90 minutes"), 90)

    def test_a_range_becomes_its_midpoint(self):
        """Taking either end would flatter or damn the estimate by construction."""
        self.assertEqual(tool.minutes_from("30-45 min"), 37.5)
        self.assertEqual(tool.minutes_from("2-2.5 h"), 135)

    def test_trailing_prose_is_ignored(self):
        self.assertEqual(tool.minutes_from("2.5h, expect long"), 150)

    def test_a_cell_with_no_duration_reads_none(self):
        for cell in ("", "—", "not sized", "TBD"):
            with self.subTest(cell=cell):
                self.assertIsNone(tool.minutes_from(cell))


class Estimates(unittest.TestCase):
    def test_every_row_with_a_duration_is_read(self):
        got = tool.estimates(LEDGER)
        self.assertEqual(
            got, {"414a": 210, "99f": 240, "414d": 150, "413b": 37.5, "412": 135}
        )

    def test_a_plain_column_ledger_reads_too(self):
        plain = "| Issue | Est | Status |\n|---|---|---|\n| 501 | 2h | done |\n"
        self.assertEqual(tool.estimates(plain), {"501": 120})

    def test_a_ledger_with_no_est_column_reads_nothing(self):
        none = "| Issue | Status |\n|---|---|\n| 501 | done |\n"
        self.assertEqual(tool.estimates(none), {})

    def test_the_header_row_is_not_an_issue(self):
        self.assertNotIn("Issue", tool.estimates(LEDGER))


class IssueOfPrompt(unittest.TestCase):
    def test_a_gate_prompt(self):
        self.assertEqual(tool.issue_of("Verify gate for issue **99f**, attempt 1."), "99f")

    def test_an_implementer_prompt(self):
        self.assertEqual(tool.issue_of("Implement issue **414a**, attempt 1, on the"), "414a")

    def test_a_correction_round(self):
        self.assertEqual(tool.issue_of("**CORRECTION ROUND for issue 483. Not a retry"), "483")

    def test_the_first_match_wins(self):
        """An attempt-2 prompt discusses attempt 1 and may name other issues."""
        self.assertEqual(
            tool.issue_of("Verify gate for issue **417**, **attempt 2**. issue 99f rejected"),
            "417",
        )

    def test_the_bold_span_may_carry_the_title_as_well_as_the_id(self):
        """Run `batch-88624c`, 2026-08-31: the shape 18 of 30 spawns were lost to.

        Every brief in that run wrote `issue **NNN — title**`. The bold span is
        not `**NNN**`, and `issue\s+` cannot cross the two asterisks, so the old
        reader fell through to a number in the body: 201's implementer read 207,
        224's two gates read 156, and 339's review gate read 224.
        """
        for prompt, want in (
            ("Implement issue **201 — pin the remaining workspace-crossing FKs, "
             "census-first**. This is attempt 1.", "201"),
            ("Verify gate for issue **224b — the database accepts a quotation whose "
             "lines do not sum**, attempt 1.", "224b"),
            ("Review gate (critical variant) for issue **339 — a purchase-order line "
             "pins its technical profile**, attempt 1.", "339"),
            ("**CORRECTION ROUND — issue 269.** Not a retry, not a strike.", "269"),
        ):
            with self.subTest(want=want):
                self.assertEqual(tool.issue_of(prompt), want)

    def test_only_the_heading_line_is_read(self):
        """A body that names other issues must not rescue a heading that names none.

        Falling through to the body always finds A number and reports it with
        the confidence of a right one. Unattributed is the honest answer.
        """
        prompt = (
            "Implement the pending work on the branch.\n\n"
            "Context: issue 207 landed earlier tonight and issue 156 is queued.\n"
        )
        self.assertIsNone(tool.issue_of(prompt))

    def test_a_leading_blank_line_does_not_hide_the_heading(self):
        self.assertEqual(tool.issue_of("\n\nVerify gate for issue **225**, attempt 1."), "225")


class RunWideRolesAreExcluded(unittest.TestCase):
    """The fault the first version shipped with, and how it showed.

    The finale, the promotion phase and the board rebuild all open by naming the
    RUN — `**414a-483-286335**` — whose first token is `414a`. Issue 414a then
    absorbed every step to the end of the run, read 908 minutes against its
    210-minute estimate (4.32x), and the spans totalled 29.7 hours inside a 15.5
    hour run. An impossible total is what caught it.
    """

    ROWS = [
        ("2026-08-30T00:15:50Z", "2026-08-30T00:56:00Z",
         "run-issues-implementer", "Implement issue **414a**, attempt 1, on the run's branch."),
        ("2026-08-30T00:57:35Z", "2026-08-30T01:17:00Z",
         "run-issues-verify-gate", "Verify gate for issue **414a**, attempt 1."),
        # Six hours later, a run-wide role that names the run in its first line.
        ("2026-08-30T14:51:17Z", "2026-08-30T15:23:00Z",
         "run-issues-finale", "Coherence finale for run **`414a-483-286335`**, nine issues"),
        ("2026-08-30T15:24:38Z", "2026-08-30T15:31:00Z",
         "promotion", "Promotion phase for `/run-issues` run **`414a-483-286335`** — nine"),
    ]

    def test_the_run_wide_roles_do_not_stretch_the_span(self):
        path = transcript(self.ROWS)
        try:
            got, orphans = tool.actuals(path)
        finally:
            os.remove(path)
        self.assertEqual(set(got), {"414a"})
        self.assertEqual(got["414a"]["steps"], 2)
        span = (got["414a"]["last"] - got["414a"]["first"]).total_seconds() / 60
        self.assertLess(span, 90, "the finale and promotion must not be inside 414a's span")

    def test_a_finale_alone_yields_no_issue_at_all(self):
        path = transcript(self.ROWS[2:])
        try:
            self.assertEqual(tool.actuals(path), ({}, []))
        finally:
            os.remove(path)


class Actuals(unittest.TestCase):
    def test_span_and_agent_time_are_both_reported(self):
        rows = [
            ("2026-08-30T10:00:00Z", "2026-08-30T10:30:00Z",
             "run-issues-implementer", "Implement issue **483**, attempt 1"),
            # Two gates spawned together and overlapping, as they should.
            ("2026-08-30T10:40:00Z", "2026-08-30T11:00:00Z",
             "run-issues-verify-gate", "Verify gate for issue **483**, attempt 1"),
            ("2026-08-30T10:40:30Z", "2026-08-30T11:02:00Z",
             "run-issues-review-gate", "Review gate for issue **483**, attempt 1"),
        ]
        path = transcript(rows)
        try:
            got = tool.actuals(path)[0]["483"]
        finally:
            os.remove(path)
        span = (got["last"] - got["first"]).total_seconds() / 60
        self.assertEqual(span, 62.0)                 # 10:00 to 11:02
        self.assertAlmostEqual(got["agent"], 30 + 20 + 21.5)   # the two gates overlap
        self.assertGreater(got["agent"], span - 62)
        self.assertEqual(got["steps"], 3)


class UnattributedStepsRefuse(unittest.TestCase):
    """A table built from part of a run must not exit 0.

    Run `batch-88624c` graded seven issues from twelve steps out of thirty and
    printed no warning at all. The finale pasted it, hedged it in prose, and
    carried on. A count the machine writes cannot be forgotten the way that
    hedge could.
    """

    ROWS = [
        ("2026-08-30T10:00:00Z", "2026-08-30T10:30:00Z",
         "run-issues-implementer", "Implement issue **483**, attempt 1"),
        ("2026-08-30T10:40:00Z", "2026-08-30T11:00:00Z",
         "run-issues-verify-gate", "Verify gate for issue **483**, attempt 1"),
        ("2026-08-30T10:40:30Z", "2026-08-30T11:02:00Z",
         "run-issues-review-gate", "Pick up where the last gate stopped."),
    ]

    def test_the_orphan_is_named_not_dropped(self):
        path = transcript(self.ROWS)
        try:
            spans, orphans = tool.actuals(path)
        finally:
            os.remove(path)
        self.assertEqual(spans["483"]["steps"], 2)
        self.assertEqual(orphans, ["Pick up where the last gate stopped."])

    def test_main_exits_two_when_a_spawn_is_unattributed(self):
        handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        handle.write("| Issue | Est |\n|---|---|\n| 483 — a thing | 1h |\n")
        handle.close()
        path = transcript(self.ROWS)
        try:
            self.assertEqual(
                tool.main(["--ledger", handle.name, "--transcript", str(path)]), 2
            )
        finally:
            os.remove(path)
            os.remove(handle.name)


class Main(unittest.TestCase):
    def ledger_file(self, text=LEDGER):
        handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        handle.write(text)
        handle.close()
        return handle.name

    def test_a_missing_ledger_exits_two(self):
        path = transcript([])
        try:
            self.assertEqual(
                tool.main(["--ledger", "/nonexistent/run.md", "--transcript", str(path)]), 2
            )
        finally:
            os.remove(path)

    def test_a_missing_transcript_exits_two(self):
        ledger = self.ledger_file()
        try:
            self.assertEqual(
                tool.main(["--ledger", ledger, "--transcript", "/nonexistent/x.jsonl"]), 2
            )
        finally:
            os.remove(ledger)

    def test_a_ledger_with_no_estimates_is_refused_not_passed(self):
        ledger = self.ledger_file("| Issue | Status |\n|---|---|\n| 501 | done |\n")
        path = transcript([])
        try:
            self.assertEqual(tool.main(["--ledger", ledger, "--transcript", str(path)]), 2)
        finally:
            os.remove(ledger)
            os.remove(path)

    def test_a_ledger_and_transcript_from_different_runs_are_refused(self):
        """Both sides read fine and nothing joins. That is not a pass."""
        ledger = self.ledger_file()
        path = transcript([
            ("2026-08-30T10:00:00Z", "2026-08-30T10:30:00Z",
             "run-issues-implementer", "Implement issue **777**, attempt 1"),
        ])
        try:
            self.assertEqual(tool.main(["--ledger", ledger, "--transcript", str(path)]), 2)
        finally:
            os.remove(ledger)
            os.remove(path)

    def test_a_clean_join_exits_zero(self):
        ledger = self.ledger_file()
        path = transcript([
            ("2026-08-30T10:00:00Z", "2026-08-30T10:30:00Z",
             "run-issues-implementer", "Implement issue **414a**, attempt 1"),
        ])
        try:
            self.assertEqual(tool.main(["--ledger", ledger, "--transcript", str(path)]), 0)
        finally:
            os.remove(ledger)
            os.remove(path)


class RolesPerIssue(unittest.TestCase):
    """Ticket 37 ruling 6's fourth count, and ruling 20's third kind fact.

    Escalations and the critical review variant are both readable straight off
    the transcripts BY ROLE NAME, and neither was read anywhere until sitting
    3. The walk that attributes a spawn to an issue already exists here, so it
    records the role rather than growing a second walk beside it -- the drift
    `journal_for` taught ticket 39 in sitting 2 and `read_transcript` in
    sitting 3.

    Reading it from the transcript rather than from the ledger is ticket 39
    ruling 21.3's proof rule: the ledger records what was asked for.
    """

    ROWS = [
        ("2026-08-30T10:00:00Z", "2026-08-30T10:30:00Z",
         "run-issues-implementer", "Implement issue **483**, attempt 1"),
        ("2026-08-30T10:40:00Z", "2026-08-30T11:00:00Z",
         "run-issues-review-gate-critical",
         "Review gate for issue **483**, attempt 1"),
        ("2026-08-30T11:10:00Z", "2026-08-30T12:00:00Z",
         "run-issues-implementer-escalated",
         "Implement issue **483**, attempt 3"),
        ("2026-08-30T12:10:00Z", "2026-08-30T12:30:00Z",
         "run-issues-implementer", "Implement issue **484**, attempt 1"),
    ]

    def spans(self):
        path = transcript(self.ROWS)
        try:
            return tool.actuals(path)[0]
        finally:
            os.remove(path)

    def test_an_escalated_spawn_is_recorded_against_its_issue(self):
        self.assertIn("run-issues-implementer-escalated",
                      self.spans()["483"]["roles"])

    def test_an_issue_that_never_escalated_says_so(self):
        self.assertNotIn("run-issues-implementer-escalated",
                         self.spans()["484"]["roles"])

    def test_the_critical_review_variant_is_recorded_against_its_issue(self):
        self.assertIn("run-issues-review-gate-critical",
                      self.spans()["483"]["roles"])

    def test_an_issue_whose_review_was_not_critical_says_so(self):
        self.assertNotIn("run-issues-review-gate-critical",
                         self.spans()["484"]["roles"])

    def test_the_roles_do_not_disturb_the_figures_already_read(self):
        """`actuals` has three callers' worth of named keys. Adding a fourth
        is additive only if the other three still read what they read."""
        got = self.spans()["484"]
        self.assertEqual(got["steps"], 1)
        self.assertAlmostEqual(got["agent"], 20.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
