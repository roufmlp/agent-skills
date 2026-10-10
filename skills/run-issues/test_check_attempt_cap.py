#!/usr/bin/env python3
"""Tests for check_attempt_cap.

The row fixtures copy two real ledger formats: an older run's
`implement …; retry 1 …` stamps and a newer run's
`queued → in-progress → gates` stamps. Neither numbers its attempts, which is
why the cap counts an explicit `attempt N` marker and refuses when it finds
none it can trust.
"""

import contextlib
import io
import os
import unittest

from check_attempt_cap import (
    MAX_ATTEMPTS,
    MAX_LIGHT_ATTEMPTS,
    MAX_RESETS,
    Decision,
    charge_faults,
    count_markers,
    decide,
    find_row,
    main,
)

LEDGER = """Owner: run-issues-batch-0a1b2c
Worktree: `/tmp/wt`

Scope, as given: **147, 318, 321b**.

## Status

| Issue | Status | Estimate | Stamps |
|---|---|---|---|
| 147 | **done** | medium | attempt 1 02:35→02:50; gates r1 **both reject** (**strike 1**); attempt 2 03:07→03:25; gates r2 **both pass** |
| 318 — the generic-product road | **in-progress** | ~2.5h | attempt 1 02:37 queued → 04:10 in-progress |
| 321b — the staff may pick a version | **in-progress** | ~2h | attempt 1 08:37; **criteria reset**; attempt 2 09:14; **criteria reset**; attempt 3 10:02 |
| 288 | **blocked** | large | attempt 1 01:00; attempt 2 02:00; attempt 3 03:00 |
| 293 | **queued** | small | |
"""


# The same table with no rows, so a test can add exactly the row it is about.
HEADER = """Owner: run-issues-batch-0a1b2c

## Status

| Issue | Status | Stamps |
|---|---|---|
"""

class FindRow(unittest.TestCase):

    def test_finds_a_bare_numeric_issue(self):
        self.assertIn("attempt 1 02:35", find_row(LEDGER, "147"))

    def test_finds_an_issue_whose_cell_carries_a_title(self):
        self.assertIn("02:37 queued", find_row(LEDGER, "318"))

    def test_finds_a_lettered_issue(self):
        self.assertIn("criteria reset", find_row(LEDGER, "321b"))

    def test_does_not_match_a_prefix_of_another_issue(self):
        """`32` must not match the `321b` row."""
        self.assertIsNone(find_row(LEDGER, "32"))

    def test_returns_none_for_an_issue_not_in_the_table(self):
        self.assertIsNone(find_row(LEDGER, "999"))


NUMBERED = """## Status

| # | issue | estimate | status | stamps |
|---|---|---|---|---|
| 1 | 314 — the sign-in refusal names the wrong limit | medium | queued | |
| 2 | 281 — withdrawn purchase order reads as a win | medium | in-progress | attempt 1; attempt 2; attempt 3 |
| 3 | 288 — quote landing in the deal room | medium | queued | |
"""


class NumberedLedgerFormat(unittest.TestCase):
    """The `| # | issue | …` layout puts the id in the second cell.

    Read naively, `--issue 1` matches the row-number column and returns issue
    314's row. That is a cap authorising a spawn off the wrong row.
    """

    def test_finds_the_issue_by_id_not_by_row_number(self):
        self.assertIn("314", find_row(NUMBERED, "314"))

    def test_a_row_number_is_not_an_issue_id(self):
        self.assertIsNone(find_row(NUMBERED, "1"))

    def test_counts_attempts_on_the_right_row(self):
        d = decide(NUMBERED, "281")
        self.assertFalse(d.allowed)
        self.assertIn("3 attempts", d.reason)

    def test_a_queued_row_in_this_format_authorises_attempt_one(self):
        d = decide(NUMBERED, "314")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 1)


class CountMarkers(unittest.TestCase):
    def test_counts_explicit_attempt_markers(self):
        self.assertEqual(count_markers(find_row(LEDGER, "147"), "attempt"), 2)

    def test_counts_a_single_attempt(self):
        self.assertEqual(count_markers(find_row(LEDGER, "318"), "attempt"), 1)

    def test_counts_criteria_resets(self):
        row = find_row(LEDGER, "321b")
        self.assertEqual(count_markers(row, "criteria reset"), 2)

    def test_an_empty_row_counts_zero(self):
        self.assertEqual(count_markers(find_row(LEDGER, "293"), "attempt"), 0)

    def test_a_timestamp_is_never_read_as_an_attempt_number(self):
        """`retry 00:18` and `retry 10.2` are a clock and a duration."""
        row = "| 165 | done | m | implement 00:17, retry 00:18→00:29, retry 10.2 |"
        self.assertEqual(count_markers(row, "attempt"), 0)

    def test_criteria_fault_reset_is_the_same_marker(self):
        row = "| 9 | x | y | attempt 1; **criteria-fault reset**; attempt 2 |"
        self.assertEqual(count_markers(row, "criteria reset"), 1)


class Decide(unittest.TestCase):
    def test_a_queued_issue_authorises_attempt_one(self):
        d = decide(LEDGER, "293")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 1)

    def test_one_attempt_so_far_authorises_attempt_two(self):
        d = decide(LEDGER, "318")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 2)

    def test_two_attempts_so_far_authorises_the_escalated_third(self):
        d = decide(LEDGER, "147")
        self.assertTrue(d.allowed)
        self.assertEqual(d.attempt, 3)

    def test_three_attempts_refuses_the_fourth(self):
        d = decide(LEDGER, "288")
        self.assertFalse(d.allowed)
        self.assertEqual(d.attempt, 4)
        self.assertIn("3 attempts", d.reason)

    def test_a_criteria_reset_refunds_the_attempt_it_consumed(self):
        """The human's ruling of 2026-09-20. Three attempts and one reset
        spends two."""
        row = ("| 501 | in-progress | attempt 1; gates 1: verify=reject review=reject "
               "charge=strike; attempt 2; gates 2: verify=reject review=reject "
               "charge=strike; criteria reset 1 after gates 2; attempt 3; "
               "gates 3: verify=reject review=reject charge=strike |")
        ledger = HEADER + row + "\n"
        d = decide(ledger, "501")
        self.assertTrue(d.allowed, d.reason)
        self.assertEqual(d.attempt, 4)

    def test_a_refunded_row_still_stops_one_attempt_later(self):
        """The refund buys one attempt, not an open cap."""
        row = ("| 502 | in-progress | attempt 1; criteria reset 1; attempt 2; "
               "attempt 3; attempt 4 |")
        ledger = HEADER + row + "\n"
        d = decide(ledger, "502")
        self.assertFalse(d.allowed)
        self.assertEqual(d.attempt, 5)
        self.assertIn("refund", d.reason.lower())

    def test_the_refund_does_not_depend_on_where_the_reset_sits(self):
        """The row is prose. A reset written first refunds the same attempt."""
        row = "| 503 | in-progress | criteria reset 1; attempt 1; attempt 2; attempt 3 |"
        ledger = HEADER + row + "\n"
        d = decide(ledger, "503")
        self.assertTrue(d.allowed, d.reason)

    def test_a_reset_cannot_refund_an_attempt_that_was_never_taken(self):
        """A reset with no attempt behind it must not buy a fourth attempt."""
        row = "| 504 | in-progress | criteria reset 1 |"
        ledger = HEADER + row + "\n"
        d = decide(ledger, "504")
        self.assertTrue(d.allowed, d.reason)
        self.assertEqual(d.attempt, 1)

    def test_three_attempts_and_no_reset_still_refuses_the_fourth(self):
        """The refund changes nothing for a row that never took a reset."""
        d = decide(LEDGER, "288")
        self.assertFalse(d.allowed)

    def test_two_resets_refuses_the_third(self):
        d = decide(LEDGER, "321b")
        self.assertFalse(d.allowed)
        self.assertIn("2 criteria resets", d.reason)

    def test_a_missing_row_refuses_rather_than_assuming_a_fresh_issue(self):
        d = decide(LEDGER, "999")
        self.assertFalse(d.allowed)
        self.assertIn("no row", d.reason.lower())

    def test_the_refusal_prints_the_count_it_refused_on(self):
        self.assertIn("3", decide(LEDGER, "288").reason)

    def test_a_ledger_with_no_status_table_refuses(self):
        d = decide("Owner: x\n\nnothing here\n", "147")
        self.assertFalse(d.allowed)

    def test_a_legacy_row_refuses_rather_than_counting_zero(self):
        """`implement …; retry 1 …` carries attempts this cap cannot count.

        Reading it as a fresh issue would authorise a fourth attempt on a row
        that already spent three, which is the exact failure the cap exists to
        stop. It refuses and asks for the row to be restamped.
        """
        legacy = (
            "| Issue | Status | Estimate | Stamps |\n"
            "|---|---|---|---|\n"
            "| 147 | **done** | medium | implement 02:35→02:50; gates r1 "
            "**both reject** (**strike 1**); retry 1 03:07→03:25 |\n"
        )
        d = decide(legacy, "147")
        self.assertFalse(d.allowed)
        self.assertIn("cannot count", d.reason.lower())

    def test_a_queued_row_with_no_stamps_is_not_mistaken_for_legacy(self):
        d = decide(LEDGER, "293")
        self.assertTrue(d.allowed)

    def test_decision_is_a_plain_value(self):
        self.assertIsInstance(decide(LEDGER, "293"), Decision)



class RoundChargesTest(unittest.TestCase):
    """Tracker-tooling issue 15, fix F12 of the audit of 2026-09-23.

    A rejected gate round carries what it charged, and a reset names the round
    it follows, or the next spawn is refused. `run_quality.py` then reads the
    strike instead of deriving it from prose.
    """

    def ledger(self, stamps, issue="400"):
        return HEADER + f"| {issue} | in-progress | {stamps} |\n"

    def test_a_rejected_round_with_no_charge_is_refused(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=pass review=reject"), "400")
        self.assertFalse(decision.allowed)
        self.assertIn("gates 1", decision.reason)
        self.assertIn("charge_round.py", decision.reason)

    def test_a_charged_rejected_round_is_allowed(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=pass review=reject charge=strike"),
            "400")
        self.assertTrue(decision.allowed, decision.reason)

    def test_a_passing_round_needs_no_charge(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=pass review=pass"), "400")
        self.assertTrue(decision.allowed, decision.reason)

    def test_a_passing_round_charged_a_strike_is_refused(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=pass review=pass charge=strike"), "400")
        self.assertFalse(decision.allowed)

    def test_a_reset_naming_no_round_is_refused(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=pass charge=strike; "
            "criteria reset 1 of 2"), "400")
        self.assertFalse(decision.allowed)
        self.assertIn("after gates", decision.reason)

    def test_a_reset_naming_a_round_the_row_lacks_is_refused(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "criteria reset after gates 2"), "400")
        self.assertFalse(decision.allowed)
        self.assertIn("gates 2", decision.reason)

    def test_a_reset_naming_its_round_is_allowed_and_still_refunds(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=pass charge=strike; "
            "criteria reset 1 of 2 after gates 2"), "400")
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.resets, 1)
        self.assertEqual(decision.spent, 1)

    def test_a_reset_named_once_and_mentioned_again_in_prose_is_allowed(self):
        """Found by the review of 2026-09-23: rows are prose, and a runner that
        names the reset and then explains it must not be refused for it.

        Asked of `charge_faults` alone. The cap itself counts every mention
        of a reset as a reset, which is older than the charge and not this
        case's subject."""
        from check_attempt_cap import charge_faults
        self.assertEqual(charge_faults(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=pass charge=strike; "
            "criteria reset 1 of 2 after gates 2; the criteria reset annulled "
            "both strikes"), [])

    def test_a_reset_mentioned_twice_counts_once(self):
        """Tracker-tooling issue 20. The row names its reset and explains it,
        and the cap read two resets and froze the criteria."""
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=pass charge=strike; "
            "criteria reset 1 of 2 after gates 2; the criteria reset annulled "
            "both strikes"), "400")
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.resets, 1)
        self.assertEqual(decision.spent, 1)

    def test_two_resets_named_at_two_rounds_still_freeze_the_criteria(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "criteria reset after gates 1; attempt 2; gates 2: verify=reject "
            "review=pass charge=strike; criteria reset after gates 2"), "400")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.resets, 2)
        self.assertIn("frozen", decision.reason)
        self.assertIn("CARVE IT", decision.reason)

    def test_a_counted_reset_stamp_that_names_no_round_is_refused(self):
        """Found by the review of issue 20: once one reset is named, a second
        counted stamp with no round would go uncounted and the criteria would
        never freeze."""
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "criteria reset 1 of 2 after gates 1; attempt 2; gates 2: "
            "verify=reject review=pass charge=strike; criteria reset 2 of 2"),
            "400")
        self.assertFalse(decision.allowed)
        self.assertIn("2 of 2", decision.reason)

    def test_a_zero_padded_round_is_the_same_round(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=pass charge=strike; "
            "criteria reset after gates 2; the criteria reset after gates 02 "
            "annulled both"), "400")
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.resets, 1)

    def test_the_charges_alone_can_be_checked_at_the_commit_step(self):
        """No spawn follows a commit, so the cap has nothing to authorise.
        Issue 163 went `done` at attempt 1 with its rejected round uncharged."""
        import contextlib, io, tempfile, pathlib
        from check_attempt_cap import main
        path = pathlib.Path(tempfile.mkdtemp()) / "run.md"
        path.write_text(self.ledger("attempt 1; gates 1: verify=reject "
                                    "review=pass; committed abc1234"))
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            refused = main(["--ledger", str(path), "--issue", "400",
                            "--charges"])
        self.assertEqual(refused, 1)
        path.write_text(self.ledger("attempt 1; attempt 2; attempt 3; "
                                    "gates 3: verify=pass review=pass"))
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            allowed = main(["--ledger", str(path), "--issue", "400",
                            "--charges"])
        self.assertEqual(allowed, 0, "the cap is not asked at the commit step")


class ProseAboutAnAttempt(unittest.TestCase):
    """Tracker-tooling issue 27. On run `batch-46e4de` the cap read issue 33b's
    phrase "attempt 1's files" as a second attempt, and the runner reworded the
    row. The journal answered with a reminder; a reminder is not a fix."""

    def ledger(self, stamps):
        return HEADER + f"| 400 | in-progress | {stamps} |\n"

    def test_a_possessive_mention_is_not_an_attempt(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 1's files preserved under runs/"), "400")
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.attempt, 2)

    def test_a_quoted_or_repeated_stamp_is_one_attempt(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "the brief quotes `attempt 1` again; attempt 1 (re-stamped)"), "400")
        self.assertEqual(decision.attempt, 2)

    def test_three_stamps_still_reach_the_cap(self):
        decision = decide(self.ledger(
            "attempt 1; gates 1: verify=reject review=reject charge=strike; "
            "attempt 2; gates 2: verify=reject review=reject charge=strike; "
            "attempt 3; gates 3: verify=reject review=reject charge=strike; "
            "attempt 3's review named the same fault"), "400")
        self.assertFalse(decision.allowed)


class TheLightCap(unittest.TestCase):
    """Tracker-tooling issue 40, AC3 and AC6: a `Level: light` issue gets two
    attempts, and everything else keeps three. The level is read through
    `issue_level.py` from the issue file in the run's tree, on every call."""

    ROW = "| 12 | in-progress | attempt 1; attempt 2 |\n"

    def setUp(self):
        import tempfile
        self.scratch = tempfile.TemporaryDirectory()
        self.tree = os.path.realpath(self.scratch.name)
        self.ledger = os.path.join(self.tree, ".scratch", "feat", "runs",
                                   "batch-abc123", "run.md")
        os.makedirs(os.path.dirname(self.ledger))
        os.makedirs(os.path.join(self.tree, "docs", "agents"))
        with open(os.path.join(self.tree, "docs", "agents", "risk-paths.md"),
                  "w") as handle:
            handle.write("No risk paths: a fixture.\n")
        self.write_ledger(self.tree)

    def tearDown(self):
        self.scratch.cleanup()

    def write_ledger(self, worktree, row=None):
        with open(self.ledger, "w") as handle:
            handle.write(f"Owner: run-issues-batch-abc123\nWorktree: `{worktree}`"
                         "\n\n## Status\n\n| Issue | Status | Stamps |\n"
                         "|---|---|---|\n" + (row or self.ROW))

    def issue(self, level_line, tree=None):
        path = os.path.join(tree or self.tree, ".scratch", "feat", "issues",
                            "12-x.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write((level_line + "\n" if level_line else "") + "# 12\n")

    def cap(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--ledger", self.ledger, "--issue", "12"])
        return code, out.getvalue(), err.getvalue()

    def test_a_light_issue_is_refused_its_third_attempt(self):
        self.issue("Level: light")
        code, _, err = self.cap()
        self.assertEqual(code, 1, err)
        self.assertIn("Level: light", err)
        self.assertIn("cap of two", err)
        self.assertIn("carve whole after gates", err)

    def test_the_light_refusal_names_the_land_short_road(self):
        """The human, 2026-10-05: a green light issue at its cap
        lands short and its dependents run; only a red tree is carved whole
        (the human, 2026-10-06)."""
        self.issue("Level: light")
        code, _, err = self.cap()
        self.assertEqual(code, 1, err)
        self.assertIn("`done (landed short)`", err)
        self.assertIn("register row", err)
        self.assertIn("dependents", err)
        self.assertIn("red", err)

    def test_a_full_issue_is_allowed_its_third_attempt(self):
        self.issue("Level: full")
        code, out, err = self.cap()
        self.assertEqual(code, 0, err)
        self.assertIn("attempt 3", out)

    def test_a_light_issue_keeps_its_second_attempt(self):
        self.issue("Level: light")
        self.write_ledger(self.tree, "| 12 | in-progress | attempt 1 |\n")
        code, out, err = self.cap()
        self.assertEqual(code, 0, err)
        self.assertIn("attempt 2, 1 of 2 spent", out)

    def test_anything_but_level_light_is_full(self):
        """AC6: no line, another word, and no file at all."""
        for line in (None, "Level: medium"):
            with self.subTest(line=line):
                self.issue(line)
                code, out, err = self.cap()
                self.assertEqual(code, 0, err)
                self.assertIn("attempt 3", out)
        os.remove(os.path.join(self.tree, ".scratch", "feat", "issues", "12-x.md"))
        code, out, err = self.cap()
        self.assertEqual(code, 0, err)
        self.assertIn("attempt 3", out)
        self.assertIn("no issue file", err)

    def test_the_level_is_read_in_the_tree_the_worktree_line_names(self):
        """Seam pass h0925: light beside the ledger, full in the run's tree."""
        import tempfile
        with tempfile.TemporaryDirectory() as other:
            other = os.path.realpath(other)
            self.issue("Level: light")
            self.issue("Level: full", tree=other)
            self.write_ledger(other)
            code, out, err = self.cap()
            self.assertEqual(code, 0, err)
            self.assertIn("attempt 3", out)

    def test_a_lift_to_full_between_two_calls_is_read(self):
        self.issue("Level: light")
        self.assertEqual(self.cap()[0], 1)
        self.issue("Level: full")
        self.assertEqual(self.cap()[0], 0)

    def test_the_full_caps_are_unchanged(self):
        self.assertEqual((MAX_ATTEMPTS, MAX_RESETS, MAX_LIGHT_ATTEMPTS), (3, 2, 2))


class TheOneGateRound(unittest.TestCase):
    """Seam pass h0925, from issue 38: a light round's token names the review
    gate alone, and a rejected one with no charge is flagged."""

    def row(self, stamps):
        return f"| 400 | in-progress | {stamps} |"

    def test_a_one_gate_reject_with_no_charge_is_a_fault(self):
        faults = charge_faults(self.row("attempt 1; gates 1: review=reject"))
        self.assertEqual(len(faults), 1)
        self.assertIn("gates 1", faults[0])

    def test_a_one_gate_reject_with_its_charge_is_clean(self):
        self.assertEqual(charge_faults(self.row(
            "attempt 1; gates 1: review=reject charge=strike")), [])

    def test_a_one_gate_pass_charged_a_strike_is_a_fault(self):
        self.assertEqual(len(charge_faults(self.row(
            "attempt 1; gates 1: review=pass charge=strike"))), 1)

    def test_the_two_gate_token_reads_as_before(self):
        self.assertEqual(len(charge_faults(self.row(
            "attempt 1; gates 1: verify=pass review=reject"))), 1)
        self.assertEqual(charge_faults(self.row(
            "attempt 1; gates 1: verify=reject review=pass charge=strike")), [])


class ScreenGroundsLandShort(unittest.TestCase):
    """The human, 2026-10-05: a screen difference never blocks an issue, light or
    full. A full issue at its cap whose last round failed on screen criteria
    alone (`grounds=screen`, which `charge_round.py` prints) lands short."""

    def ledger(self, last_round):
        return ("| Issue | Status | Stamps |\n|---|---|---|\n"
                "| 366 | in-progress | attempt 1; gates 1: verify=pass "
                "review=reject charge=strike; attempt 2; gates 2: verify=pass "
                "review=reject charge=strike grounds=screen; attempt 3; "
                f"{last_round} |\n")

    def test_a_full_issue_whose_last_round_failed_on_the_screen_alone_lands_short(self):
        decision = decide(self.ledger(
            "gates 3: verify=pass review=reject charge=strike grounds=screen"),
            "366", "full")
        self.assertFalse(decision.allowed)
        self.assertIn("LAND IT SHORT", decision.reason)
        self.assertIn("screen", decision.reason)
        self.assertIn("`done (landed short)`", decision.reason)

    def test_a_last_round_with_any_other_ground_is_carved(self):
        decision = decide(self.ledger(
            "gates 3: verify=reject review=reject charge=strike"), "366", "full")
        self.assertFalse(decision.allowed)
        self.assertNotIn("LAND IT SHORT", decision.reason)
        self.assertIn("carve after gates 3", decision.reason)

    def test_the_token_with_grounds_carries_its_charge(self):
        self.assertEqual(charge_faults(
            "| 366 | x | attempt 1; gates 1: verify=pass review=reject "
            "charge=strike grounds=screen |"), [])


def says_blocked(reason):
    """True when a refusal tells the runner to ledger an issue `blocked`. The
    briefing's section heading, `## Skipped or blocked`, is a place to name an
    issue, not a status, so it is read past."""
    return "`blocked`" in reason.replace("`## Skipped or blocked`", "")


# One real issue's stamps as its run's ledger holds them, the
# prose between them cut. Two criteria resets, four attempts, every round a
# strike: this cap refused attempt 5 and promised an escalated one it would
# also have refused, and 371 to 380 were skipped behind it.
ROW_370 = (
    "| 2 | 370 — credit and cancel ask | in-progress | Gate: "
    "`run-issues-review-gate-critical` (credit approval rule). attempt 1; "
    "gates 1: verify=reject review=reject charge=strike (C2, I1, I4); "
    "attempt 2; gates 2: verify=reject review=reject charge=strike; criteria "
    "reset after gates 2. attempt 3; gates 3: verify=reject review=reject "
    "charge=strike; attempt 4; gates 4: verify=reject review=reject "
    "charge=strike; criteria reset after gates 4. {tail} |\n")
HEADER_370 = "| # | Issue | Status | Row |\n|---|---|---|---|\n"
CRITERIA_370 = {f"C{n}" for n in range(1, 8)}


class ARunNeverBlocksOnOneFeature(unittest.TestCase):
    """The human, 2026-10-06: at the cap,
    or after a second criteria reset, the runner carves the failing part out,
    ships the rest, and the dependents run. No road this cap prints ends in
    `blocked`."""

    def decide_370(self, tail="", names=CRITERIA_370, verdicts=()):
        return decide(HEADER_370 + ROW_370.format(tail=tail), "370", "full",
                      criteria_names=names, verdict_texts=verdicts)

    def test_issue_370_after_its_second_reset_is_carved_not_escalated(self):
        decision = self.decide_370()
        self.assertFalse(decision.allowed)
        self.assertIn("CARVE IT", decision.reason)
        self.assertIn("carve after gates 4", decision.reason)
        self.assertNotIn("escalated attempt", decision.reason)
        self.assertFalse(says_blocked(decision.reason), decision.reason)

    def test_the_carve_round_keeps_the_critical_gate_370_ran_under(self):
        decision = self.decide_370()
        self.assertIn("`run-issues-review-gate-critical`", decision.reason)
        spawn = self.decide_370("carve after gates 4: C2.")
        self.assertIn("`run-issues-review-gate-critical`", spawn.reason)

    def test_a_carve_stamp_authorises_one_carve_spawn(self):
        decision = self.decide_370("carve after gates 4: C2.")
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.kind, "carve")
        self.assertEqual(decision.attempt, 5)
        self.assertIn("`attempt 5 (carve)`", decision.reason)
        self.assertIn("C2", decision.reason)

    def test_a_second_carve_spawn_is_refused(self):
        decision = self.decide_370("carve after gates 4: C2. attempt 5 (carve)")
        self.assertFalse(decision.allowed)
        self.assertIn("one carve spawn", decision.reason)
        self.assertIn("carve whole after gates 4", decision.reason)

    def test_a_carve_round_that_passes_ships_as_done_carved(self):
        decision = self.decide_370(
            "carve after gates 4: C2. attempt 5 (carve); gates 5: "
            "verify=pass review=pass charge=none")
        self.assertFalse(decision.allowed)
        self.assertIn("`done (carved)`", decision.reason)
        self.assertIn("mint_carved.py", decision.reason)
        self.assertIn("dependents", decision.reason)

    def test_a_carve_round_that_fails_carves_the_issue_whole(self):
        """The shipped part does not stand alone: nothing ships, and still
        nothing blocks."""
        decision = self.decide_370(
            "carve after gates 4: C2. attempt 5 (carve); gates 5: "
            "verify=reject review=pass charge=strike")
        self.assertFalse(decision.allowed)
        self.assertIn("carve whole after gates 5", decision.reason)
        self.assertIn("`carved (whole)`", decision.reason)
        self.assertIn("dependents", decision.reason)
        self.assertFalse(says_blocked(decision.reason), decision.reason)

    def test_a_carve_round_that_fails_on_the_screen_alone_lands_short(self):
        decision = self.decide_370(
            "carve after gates 4: C2. attempt 5 (carve); gates 5: verify=pass "
            "review=reject charge=strike grounds=screen")
        self.assertIn("LAND IT SHORT", decision.reason)
        self.assertIn("`done (carved)`", decision.reason)

    def test_a_whole_carve_spawns_nothing_and_runs_the_dependents(self):
        for tail in ("carve whole after gates 4", "carve whole at launch"):
            with self.subTest(tail=tail):
                decision = self.decide_370(tail)
                self.assertFalse(decision.allowed)
                self.assertIn("`carved (whole)`", decision.reason)
                self.assertIn("`needs-harden`", decision.reason)
                self.assertFalse(says_blocked(decision.reason))

    def test_a_carve_naming_every_criterion_must_be_written_whole(self):
        decision = self.decide_370(
            "carve after gates 4: C1, C2, C3, C4, C5, C6, C7")
        self.assertFalse(decision.allowed)
        self.assertIn("names every criterion", decision.reason)
        self.assertIn("carve whole after gates", decision.reason)

    def test_a_launch_carve_and_a_later_carve_add_up_to_every_criterion(self):
        decision = self.decide_370(
            "carve at launch: C1, C3, C4, C5, C6, C7; carve after gates 4: C2")
        self.assertIn("names every criterion", decision.reason)

    def test_a_carve_naming_a_criterion_the_issue_lacks_is_refused(self):
        decision = self.decide_370("carve after gates 4: C9")
        self.assertFalse(decision.allowed)
        self.assertIn("C9", decision.reason)
        self.assertIn("does not hold", decision.reason)

    def test_a_carve_with_no_readable_issue_file_is_refused(self):
        decision = self.decide_370("carve after gates 4: C2", names=None)
        self.assertFalse(decision.allowed)
        self.assertIn("could not be read", decision.reason)

    def test_a_whole_carve_needs_no_readable_criteria(self):
        decision = self.decide_370("carve whole after gates 4", names=None)
        self.assertIn("`carved (whole)`", decision.reason)

    def test_a_carve_naming_a_round_the_row_lacks_is_refused(self):
        decision = self.decide_370("carve after gates 9: C2")
        self.assertIn("does not hold", decision.reason)

    def test_an_issue_takes_one_carve(self):
        decision = self.decide_370(
            "carve after gates 3: C2; carve after gates 4: C3")
        self.assertIn("one carve", decision.reason)

    def test_a_carve_stamp_the_cap_cannot_read_is_refused(self):
        """Read the whole row: a carve spelled any other way is not silence."""
        for tail in ("carve after round 4: C2", "carve at the launch: C2",
                     "carve after gates 4 C2"):
            with self.subTest(tail=tail):
                decision = self.decide_370(tail)
                self.assertFalse(decision.allowed)
                self.assertIn("cannot be read", decision.reason)

    def test_prose_that_says_carved_is_not_a_stamp(self):
        decision = self.decide_370("the carved part waits for the merge")
        self.assertIn("CARVE IT", decision.reason)

    def test_a_launch_carve_spends_no_attempt(self):
        row = "| 379 | in-progress | carve at launch: C3 |\n"
        decision = decide(HEADER + row, "379", "full",
                          criteria_names={"C1", "C2", "C3"})
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.attempt, 1)
        self.assertEqual(decision.kind, "attempt")

    def test_no_refusal_this_cap_prints_ends_in_blocked(self):
        """The control: every road that used to say `blocked`, driven."""
        rows = {
            "spent": "attempt 1; gates 1: verify=reject review=reject "
                     "charge=strike; attempt 2; gates 2: verify=reject "
                     "review=reject charge=strike; attempt 3; gates 3: "
                     "verify=reject review=reject charge=strike",
            "resets": "attempt 1; gates 1: verify=reject review=reject "
                      "charge=strike; criteria reset after gates 1; attempt 2; "
                      "gates 2: verify=reject review=reject charge=strike; "
                      "criteria reset after gates 2",
            "screen": "attempt 1; gates 1: verify=pass review=reject "
                      "charge=strike grounds=screen; attempt 2; gates 2: "
                      "verify=pass review=reject charge=strike grounds=screen; "
                      "attempt 3; gates 3: verify=pass review=reject "
                      "charge=strike grounds=screen",
        }
        for name, stamps in rows.items():
            for level in ("full", "light"):
                with self.subTest(road=name, level=level):
                    decision = decide(HEADER + f"| 9 | x | {stamps} |\n", "9",
                                      level, criteria_names={"C1", "C2"})
                    self.assertFalse(decision.allowed)
                    self.assertFalse(says_blocked(decision.reason),
                                     decision.reason)


class TheCarveRoundKeepsTheCriticalGate(unittest.TestCase):
    """`--charges` at the commit step refuses a carve round whose review
    verdict the critical gate did not write, where the issue ran under it."""

    def setUp(self):
        import tempfile
        self.scratch = tempfile.TemporaryDirectory()
        self.run = os.path.join(self.scratch.name, "runs", "batch-a1b2c3")
        os.makedirs(os.path.join(self.run, "verdicts"))
        self.ledger = os.path.join(self.run, "run.md")

    def tearDown(self):
        self.scratch.cleanup()

    def write(self, row, verdicts):
        with open(self.ledger, "w") as handle:
            handle.write("| Issue | Status | Stamps |\n|---|---|---|\n" + row)
        for attempt, text in verdicts.items():
            with open(os.path.join(self.run, "verdicts",
                                   f"370-attempt-{attempt}-review.md"), "w") as h:
                h.write(text)

    def charges(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--ledger", self.ledger, "--issue", "370", "--charges"])
        return code, err.getvalue()

    ROW = ("| 370 | gates | attempt 1; gates 1: verify=reject review=reject "
           "charge=strike; carve after gates 1: C2; attempt 2 (carve); "
           "gates 2: verify=pass review=pass charge=none |\n")
    CRITICAL = "# Issue 370, attempt {n} — review gate (critical)\n"
    PLAIN = "# Issue 370, attempt {n} — review gate\n"

    def test_a_carve_round_gated_by_the_plain_gate_is_refused(self):
        self.write(self.ROW, {1: self.CRITICAL.format(n=1),
                              2: self.PLAIN.format(n=2)})
        code, err = self.charges()
        self.assertEqual(code, 1)
        self.assertIn("run-issues-review-gate-critical", err)

    def test_a_carve_round_with_no_review_verdict_is_refused(self):
        self.write(self.ROW, {1: self.CRITICAL.format(n=1)})
        code, err = self.charges()
        self.assertEqual(code, 1)
        self.assertIn("no review verdict", err)

    def test_a_carve_round_gated_by_the_critical_gate_commits(self):
        self.write(self.ROW, {1: self.CRITICAL.format(n=1),
                              2: self.CRITICAL.format(n=2)})
        code, err = self.charges()
        self.assertEqual(code, 0, err)

    def test_an_issue_that_never_ran_critical_needs_no_critical_carve(self):
        self.write(self.ROW, {1: self.PLAIN.format(n=1),
                              2: self.PLAIN.format(n=2)})
        code, err = self.charges()
        self.assertEqual(code, 0, err)


class TheCapReadsTheIssueFilesCriteria(unittest.TestCase):
    """`main` reads the criteria from the issue file in the run's tree, so a
    carve is checked against what the issue holds."""

    def setUp(self):
        import tempfile
        self.scratch = tempfile.TemporaryDirectory()
        self.tree = os.path.realpath(self.scratch.name)
        self.ledger = os.path.join(self.tree, ".scratch", "feat", "runs",
                                   "batch-abc123", "run.md")
        os.makedirs(os.path.dirname(self.ledger))
        issues = os.path.join(self.tree, ".scratch", "feat", "issues")
        os.makedirs(issues)
        with open(os.path.join(issues, "12-x.md"), "w") as handle:
            handle.write("Level: full\n# 12\n\n## Acceptance criteria\n\n"
                         "- [ ] One.\n- [ ] Two.\n")

    def tearDown(self):
        self.scratch.cleanup()

    def cap(self, stamps):
        with open(self.ledger, "w") as handle:
            handle.write(f"Worktree: `{self.tree}`\n\n| Issue | Status | Stamps |"
                         f"\n|---|---|---|\n| 12 | in-progress | {stamps} |\n")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--ledger", self.ledger, "--issue", "12"])
        return code, out.getvalue(), err.getvalue()

    STAMPS = ("attempt 1; gates 1: verify=reject review=reject charge=strike; "
              "attempt 2; gates 2: verify=reject review=reject charge=strike; "
              "attempt 3; gates 3: verify=reject review=reject charge=strike; ")

    def test_a_carve_of_one_criterion_of_two_authorises_the_carve_spawn(self):
        code, out, err = self.cap(self.STAMPS + "carve after gates 3: C2")
        self.assertEqual(code, 0, err)
        self.assertIn("attempt 4 (carve)", out)

    def test_a_carve_of_both_criteria_is_refused(self):
        code, _, err = self.cap(self.STAMPS + "carve after gates 3: C1, C2")
        self.assertEqual(code, 1)
        self.assertIn("names every criterion", err)


if __name__ == "__main__":
    unittest.main()
