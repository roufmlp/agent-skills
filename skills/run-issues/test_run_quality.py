#!/usr/bin/env python3
"""Cases for run_quality.py — the finale's trial block.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 4 (deliverable 4; rulings 13, 15, 21.3 and 22).

Two readings and one verdict. The per-issue quality figures come off the
ledger's status table, which `check_commit_order.py` and `check_attempt_cap.py`
already read for other purposes. The trial verdict comes off the run journal,
where `model-landed-check.py` has written one line per spawn since sitting 2 and
where, until this sitting, nothing read them.

    python3 -m unittest test_run_quality
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import re
import tempfile
import unittest

import run_quality as tool


# Real lines, generated 2026-09-06 by calling `model-landed-check.py`'s own
# `decide` against a full twelve-role map. They are not typed by hand: a fixture
# a human wrote is a fixture that agrees with whatever the reader expects, and
# this reader's whole job is to disagree with the writer when the map fails.
LANDED_OK = (
    "- model landed: run-issues-implementer ag-1 — ran on claude-opus-5 (opus) "
    "at effort high (ledger asked opus).\n")
LANDED_MODEL_FAULT = (
    "- model landed: run-issues-verify-gate ag-2 — ran on claude-sonnet-5 "
    "(sonnet) at effort high (ledger asked opus). **MISMATCH**: the ledger "
    "asked for `verify=opus`. The run carries on and nothing halts (ticket 39, "
    "ruling 22): the work is still good work and only the experiment is void.\n")
# The hook writes a parenthetical saying what it had to compare against. Only
# `(ledger asked <tier>)` is a comparison; the other three say it made none.
LANDED_NO_MAP = (
    "- model landed: run-issues-implementer ag-4 — ran on claude-opus-5 (opus) "
    "at effort high (no map in the ledger).\n")
LANDED_DAMAGED = (
    "- model landed: run-issues-verify-gate ag-5 — ran on claude-opus-5 (opus) "
    "at effort high (the ledger's map line is damaged).\n")
LANDED_UNREAD_TRANSCRIPT = (
    "- model landed: run-issues-review-gate ag-6 — ran on unmeasured at effort "
    "unmeasured (ledger asked opus).\n")
LANDED_EFFORT_FAULT = (
    "- model landed: run-issues-review-gate ag-3 — ran on claude-opus-5 (opus) "
    "at effort medium (ledger asked opus). **MISMATCH**: the agent file states "
    "`effort: high`. The run carries on and nothing halts (ticket 39, ruling "
    "22): the work is still good work and only the experiment is void.\n")


class TrialVerdict(unittest.TestCase):
    """Ruling 22: a mismatch voids the trial and halts nothing."""

    def test_no_landed_lines_is_unmeasured_and_not_void(self):
        """A journal with no landed line proves nothing either way.

        Silence is not a pass. A run from before sitting 2, or one whose hook
        never fired, has an UNMEASURED trial, and calling that `holds` would
        hand ticket 37 a row saying the map landed when nothing looked.
        """
        verdict = tool.trial_verdict("# Journal\n\n- 09:14 issue 533 spawned.\n")
        self.assertEqual(verdict.state, tool.UNMEASURED)
        self.assertFalse(verdict.void)
        self.assertEqual(verdict.spawns, 0)

    def test_every_spawn_clean_is_holds(self):
        """Lines with no `**MISMATCH**` mark leave the trial readable."""
        verdict = tool.trial_verdict("# Journal\n\n" + LANDED_OK * 3)
        self.assertEqual(verdict.state, tool.HOLDS)
        self.assertFalse(verdict.void)
        self.assertEqual(verdict.spawns, 3)
        self.assertEqual(verdict.mismatches, ())

    def test_one_mismatch_among_many_voids_the_trial(self):
        """Ruling 22: one fault is enough, and the other spawns are still counted."""
        verdict = tool.trial_verdict(
            LANDED_OK * 40 + LANDED_MODEL_FAULT + LANDED_OK * 47)
        self.assertEqual(verdict.state, tool.VOID)
        self.assertTrue(verdict.void)
        self.assertEqual(verdict.spawns, 88)
        self.assertEqual(len(verdict.mismatches), 1)
        self.assertIn("run-issues-verify-gate ag-2", verdict.mismatches[0])

    def test_an_effort_fault_voids_the_trial_too(self):
        """Ruling 7 puts effort in the ledger, so a wrong effort spoils the trial.

        The hook marks both kinds with one word, and nothing here re-reads the
        cause: a reader that graded model faults and passed effort faults would
        be a second opinion on a judgement the hook already made.
        """
        verdict = tool.trial_verdict(LANDED_OK + LANDED_EFFORT_FAULT)
        self.assertEqual(verdict.state, tool.VOID)
        self.assertIn("effort: high", verdict.mismatches[0])

    def test_a_line_that_compared_against_nothing_never_reads_holds(self):
        """A damaged or absent map line proves the spawn ran; it proves
        nothing about whether it ran on what was ASKED.

        This module's docstring already forbids the reasoning one level up --
        `unmeasured` is not `holds` -- and the review of 2026-09-06 found the
        rule was not applied per line. Two lines that compared against nothing
        were reported as "All 2 mapped spawn(s) ran on the model and at the
        effort the ledger asked for".
        """
        verdict = tool.trial_verdict(LANDED_NO_MAP + LANDED_DAMAGED)
        self.assertEqual(verdict.state, tool.UNMEASURED)
        self.assertEqual(verdict.spawns, 2)
        self.assertEqual(verdict.proved, 0)

    def test_an_unmeasured_transcript_is_not_evidence_either(self):
        """`ran on unmeasured` means the transcript could not be read."""
        verdict = tool.trial_verdict(LANDED_UNREAD_TRANSCRIPT)
        self.assertEqual(verdict.state, tool.UNMEASURED)
        self.assertEqual(verdict.proved, 0)

    def test_a_model_the_tier_order_does_not_know_is_not_evidence(self):
        """The hook writes `(unknown tier)` and can raise no fault on it.

        Its own comment: "a gap in the reading, not evidence the map failed".
        The parenthetical still reads `(ledger asked ...)`, so the same false
        `holds` came back through a different door.
        """
        line = ("- model landed: run-issues-verify-gate g1 — ran on "
                "future-model-x (unknown tier) at effort high (ledger asked "
                "fable).\n")
        verdict = tool.trial_verdict(line)
        self.assertEqual(verdict.proved, 0)
        self.assertEqual(verdict.state, tool.UNMEASURED)

    def test_an_effort_nothing_read_is_not_evidence(self):
        """Ruling 7 puts effort in the ledger beside the model, so a line
        reading `at effort unmeasured` has proved half of what the `holds`
        sentence claims."""
        line = ("- model landed: run-issues-implementer a1 — ran on "
                "claude-opus-5 (opus) at effort unmeasured (ledger asked "
                "opus).\n")
        self.assertEqual(tool.trial_verdict(line).proved, 0)

    def test_a_mix_reports_both_counts_and_throws_neither_away(self):
        """80 good readings must not be discarded by 2 inconclusive ones, and
        2 inconclusive ones must not be claimed as good."""
        verdict = tool.trial_verdict(LANDED_OK * 80 + LANDED_DAMAGED * 2)
        self.assertEqual(verdict.state, tool.HOLDS)
        self.assertEqual(verdict.proved, 80)
        self.assertEqual(verdict.spawns, 82)
        text = tool.render_verdict(verdict)
        self.assertIn("80 of 82 mapped spawn(s)", text)
        # Not `assertIn("2", ...)`: the `82` above satisfies that, and deleting
        # the whole second-count paragraph then passes.
        self.assertIn("The other 2 compared against nothing", text)

    def test_a_mismatch_still_voids_whatever_else_the_journal_holds(self):
        verdict = tool.trial_verdict(LANDED_DAMAGED + LANDED_MODEL_FAULT)
        self.assertEqual(verdict.state, tool.VOID)

    def test_an_indented_copy_of_a_landed_line_is_not_counted(self):
        """The `^` anchor, which nothing pinned.

        This module's own output quotes each mismatch line indented by two
        spaces, and that block is pasted into the merge briefing. A journal
        that quoted one back would count it twice.
        """
        verdict = tool.trial_verdict(LANDED_OK + "  " + LANDED_MODEL_FAULT)
        self.assertEqual(verdict.spawns, 1)
        self.assertEqual(verdict.state, tool.HOLDS)

    def test_prose_naming_the_mismatch_word_is_not_a_landed_line(self):
        """The finale writes about mismatches; only a landed line is evidence.

        A journal is prose plus records, and this one carries a sentence with
        the marker in it. Counting that as a spawn would void a clean run on a
        note somebody wrote about voiding.
        """
        verdict = tool.trial_verdict(
            "# Journal\n\n- 09:14 the gate reported a **MISMATCH** risk.\n"
            + LANDED_OK)
        self.assertEqual(verdict.state, tool.HOLDS)
        self.assertEqual(verdict.spawns, 1)


# Every row below is TRIMMED FROM RUN `batch-b5e96d`'s real ledger, 2026-09-05,
# the same practice `test_check_commit_order.py` follows. Only prose carrying no
# marker was cut; every sentence that reports an attempt, a verdict, a
# correction round or a strike stands as the runner wrote it. The run's own
# finale note is the independent answer for one of these figures: it reads "15
# status rows read, 3 carrying a correction round".
LEDGER = """
## Status

| Issue | Est | Status | Notes |
|---|---|---|---|
| 533 | 40-60m | done | attempt 1 — verify: pass. review: accept (critical variant — money). Runner error: the two gates were serialised, not spawned together; annulled from any strike and the review was re-issued with `force-serial-gates`. committed `8639049b` |
| 546 | 90-120m | done | attempt 1 — verify pass, review reject (`rg546-01`, `rg546-02`) plus a fault in the criteria. A `harden-issues-attacker` strike-2 pass rewrote C3 and added invariant 12 (criteria reset, first of two; annuls the earlier strike). attempt 2 — verify pass, review reject on C4 (`rg546-06`); one strike. attempt 3 — verify pass, review accept. committed `6ec79d95` |
| 547 | 60-90m | done | attempt 1 — verify pass, review accept (critical variant). correction: open -> closed 12:33. Two items, both gaps on this issue's own criteria. committed `91c0324d` |
| 527 | 60-90m | done | attempt 1 — an RFQ PDF on an enquiry is still not read. What remains is criterion 2  verify pass, review REJECT — the gates SPLIT and the stricter verdict stands. One strike. attempt 2 — running. attempt 2 — verify pass, review accept, BOTH GATES CONCURRENT. committed `b43f7d68` |
| 530 | 40-60m | done | attempt 1 — a problem report Gmail calls spam is lost with no trace. Criteria 3 and 4 grade nothing here  verify pass, review REJECT — but the gates SPLIT on PROSE alone: every criterion and every invariant passed both, and the review gate's own words are that the rejection 'is narrow and touches no behaviour'. No implementer spawned, no correction round, NOT a strike — SKILL.md step 5's four conditions all held. committed `669a3305` |
| 531 | 60-90m | done | attempt 1 — verify pass, review REJECT on criterion 3; the gates split and the stricter verdict stood. attempt 2 — review ACCEPT, verify REJECT; they split the OTHER way and the stricter verdict stood again. TWO STRIKES bought a `harden-issues-attacker` strike-2 pass, which found the real fault. **It also refuted the verify gate's own premise: `nextUrl` has eight uses in `src/proxy.ts`.** Criteria reset, the first of two, so the strikes are annulled and the next round is not one. attempt 3 — running, and the last the cap allows.  Verify pass, review accept. committed `72e68f32` |
| 479 | 40-60m | done | attempt 1 — a WhatsApp send failed on production and two causes fit. **Cause A is a standing condition the human must close in a console, not a diff**  verify pass, review accept, both gates concurrent. committed `98d96a55` |
"""


def quality_for(issue, text=LEDGER):
    """The one row for an issue, so a case reads as one sentence."""
    return {row.issue: row for row in tool.issue_quality(text)}[issue]


class FirstAttempt(unittest.TestCase):
    """Ruling 15's first figure: first-attempt gate passes against rejections."""

    def test_both_gates_passing_on_the_first_attempt_reads_pass(self):
        """533: `verify: pass. review: accept`, one attempt, shipped."""
        self.assertEqual(quality_for("533").first_attempt, tool.PASS)

    def test_a_first_attempt_rejection_reads_reject(self):
        """546: the review gate rejected attempt 1 and the issue took three."""
        self.assertEqual(quality_for("546").first_attempt, tool.REJECT)

    def test_a_later_attempt_never_repairs_the_first(self):
        """527 shipped on attempt 2, and the figure is about attempt ONE."""
        row = quality_for("527")
        self.assertEqual(row.first_attempt, tool.REJECT)
        self.assertEqual(row.attempts, 2)

    def test_a_later_rejection_never_spoils_a_first_attempt_that_passed(self):
        """The other direction, and the one the fixtures did not cover.

        Every rejected fixture rejects on attempt 1, so grading the WHOLE ROW
        instead of attempt 1's span read the same answer and the spans were
        not actually pinned. Here attempt 1 passed and attempt 2 did not.
        """
        text = ("| Issue |\n|---|\n| 613 | attempt 1 — verify pass, review "
                "accept. Reopened. attempt 2 — verify pass, review REJECT. |\n")
        row = quality_for("613", text)
        self.assertEqual(row.first_attempt, tool.PASS)
        self.assertEqual(row.strikes, 1)

    def test_a_rejection_that_bought_no_retry_still_reads_reject(self):
        """530: one attempt, and a review REJECT inside it.

        The prose-deletion road of `SKILL.md` step 5 ends a rejected round with
        no second implementer. Counting attempts alone would report this issue
        as a first-attempt pass, which is the opposite of what happened.
        """
        row = quality_for("530")
        self.assertEqual(row.attempts, 1)
        self.assertEqual(row.first_attempt, tool.REJECT)

    def test_a_row_stating_no_verdict_reads_unread_and_never_pass(self):
        """Silence is a gap in the record, not a passing gate."""
        text = "| Issue |\n|---|\n| 601 | attempt 1 — committed `abc1234` |\n"
        self.assertEqual(quality_for("601", text).first_attempt, tool.UNREAD)


# Real rows from the OTHER ledgers in the same directory. Sitting 4's first
# reading was measured against `batch-b5e96d` alone, and the review of
# 2026-09-06 found seven dialects it could not read across the other fifteen.
# These rows are those dialects.
DIALECTS = """
| Issue | Est | Status | Notes |
|---|---|---|---|
| 520b | 1h | done | attempt 1 · verify: pass · review(critical): **reject** · **strike 1** · attempt 2 · verify: pass · review(critical): pass |
| 381 | 1h | done | verify: **reject** 20:05 · review(critical): pass · **strike 1** · correction 21:36→21:38 |
| 386 | 2h | done | attempt 1: verify **reject** + review **reject** → **strike 1**; attempt 2 deletions only · verify: pass · review: pass |
| 419c | 1h | done | attempt 1. verify: pass. review: accept. correction: open 08:12 → closed before the commit |
| 390b | 1h | done | verify: pass · review: accept · correction 18:48→18:54 |
| 147 | 1h | done | implement 02:35→02:50; gates r1 **both reject** 03:03/03:05 (**strike 1**); retry 1 03:07→03:25; gates r2 **both pass** 04:00/04:01 |
| 400 | 2h | done | attempt 1 07:15→07:34. gates 07:36→08:03, both pass (review standard; routing tested and upheld). |
| 236 | 2h | done | medium by files, **large by risk** — cause unproven |
| 390c | 1.5h | done | a1 17:13→17:31 · v: pass · r: reject · **strike 1** |
| 250 | 60-90m | done | attempt 1 rejected by BOTH gates. attempt 2 split; the runner drove it. verify: pass, review: accept |
| 384 | 2h | done | implement 03:40→04:02 · one correction round · committed `6a74044a` **04:14**. gates **both pass** |
| 249 | 1h | done | gates **both pass** 14:19/14:27, no strike, no correction round |
| 258 | 1h | done | attempt 1. verify: reject. review: reject. Both graded the BEHAVIOUR correct and split on the record, so this was prose deletion by the runner, not a correction round and not a strike. |
| 392 | 2h | done | attempt 1 rejected. So a correction round. correction: open 10:57 → closed 11:07. attempt 2. verify: pass, review: pass. |
| 401a | 1h | done | attempt 1. verify: pass. review: accept. correction open 04:06 → closed 04:20. |
"""


class TheOtherLedgersDialects(unittest.TestCase):
    """The review of 2026-09-06: one ledger measured, thirteen in use.

    Every case here is a row this reader read WRONG and silently, reporting a
    figure the human would have quoted.
    """

    def test_a_bolded_verdict_is_read(self):
        """`review(critical): **reject**`. 17 rows across 7 of the 16 ledgers.

        The plain `verify: pass` beside it was read, so the row came out
        `pass` with 0 strikes on a round that was rejected and charged one.
        """
        row = quality_for("520b", DIALECTS)
        self.assertEqual(row.first_attempt, tool.REJECT)
        self.assertEqual(row.strikes, 1)

    def test_a_bolded_verdict_with_no_attempt_marker_is_read(self):
        row = quality_for("381", DIALECTS)
        self.assertEqual(row.first_attempt, tool.REJECT)

    def test_an_attempt_marker_followed_by_a_colon_is_a_marker(self):
        """`attempt 1:` — the whole of attempt 1 was dropped, with no `unread`.

        `check_attempt_cap.py`'s lookahead forbids a following `:` or `.` so a
        clock cannot be counted as an attempt. Here it silently deleted a
        round: 386 read `attempts=1, first_attempt=pass, strikes=0` when
        attempt 1 was rejected twice.
        """
        row = quality_for("386", DIALECTS)
        self.assertEqual(row.attempts, 2)
        self.assertEqual(row.first_attempt, tool.REJECT)
        self.assertEqual(row.strikes, 1)

    def test_an_attempt_marker_followed_by_a_full_stop_is_a_marker(self):
        """`attempt 1.` — 15 of the rows in one ledger are written this way."""
        self.assertEqual(quality_for("419c", DIALECTS).attempts, 1)

    def test_a_clock_is_still_not_an_attempt(self):
        """The lookahead exists for a reason and the reason still holds."""
        self.assertEqual(tool.attempt_segments("retry 00:18 attempt 1:30 done"),
                         ())

    def test_a_duration_in_minutes_is_still_not_an_attempt(self):
        """`retry 10.2` is 10.2 minutes. `check_attempt_cap.py` names this
        case beside the clock, and only the clock half was covered."""
        self.assertEqual(tool.attempt_segments("attempt 10.2 minutes"), ())

    def test_a_correction_round_written_without_a_colon_is_counted(self):
        """`correction 18:48→18:54`. One ledger records three rounds this
        way and this reader counted one of them."""
        self.assertEqual(quality_for("390b", DIALECTS).corrections, 1)
        self.assertEqual(quality_for("381", DIALECTS).corrections, 1)

    def test_one_verdict_for_the_pair_is_read(self):
        """`gates **both reject**` and `gates 07:36→08:03, both pass`.

        Six of ten rows in `archive-run-f180e3-merged.md` and two of five in
        `399-403` state one verdict for the pair and never name a gate, so
        every one of them read `unread` -- a hole in the briefing on rows that
        say plainly what happened.
        """
        self.assertEqual(quality_for("147", DIALECTS).first_attempt,
                         tool.REJECT)
        self.assertEqual(quality_for("147", DIALECTS).strikes, 1)
        self.assertEqual(quality_for("400", DIALECTS).first_attempt, tool.PASS)

    def test_the_word_gate_between_the_role_and_its_verdict_is_read(self):
        """`the review gate rejected it` — the optional `gate` in `VERDICT`,
        which nothing pinned. Dropping it left the suite green."""
        text = ("| Issue |\n|---|\n| 615 | attempt 1 — the verify gate passed "
                "and the review gate rejected. |\n")
        self.assertEqual(quality_for("615", text).first_attempt, tool.REJECT)

    def test_both_followed_by_something_that_is_not_a_verdict_is_ignored(self):
        """`both gates concurrent`, `Both agree the fact is real`."""
        text = ("| Issue |\n|---|\n| 611 | attempt 1 — both gates concurrent. "
                "Both agree the fact is real. Both halves are wanted. |\n")
        self.assertEqual(quality_for("611", text).first_attempt, tool.UNREAD)

    def test_single_letter_gate_names_are_read(self):
        """`v: pass · r: reject`, the shortest dialect in the corpus."""
        row = quality_for("390c", DIALECTS)
        self.assertEqual(row.first_attempt, tool.REJECT)
        self.assertEqual(row.strikes, 1)

    def test_a_verdict_stated_as_a_verb_before_the_gates_is_read(self):
        """`attempt 1 rejected by BOTH gates`. Two rows of `44d0a8`."""
        self.assertEqual(quality_for("250", DIALECTS).first_attempt,
                         tool.REJECT)

    def test_a_correction_round_written_in_words_is_counted(self):
        """`one correction round`. Seven rows of `fd4fa2`, counted as none."""
        self.assertEqual(quality_for("384", DIALECTS).corrections, 1)

    def test_no_correction_round_is_still_none_in_the_worded_dialect(self):
        """Three rows of the corpus say `no correction round`, measured."""
        self.assertEqual(quality_for("249", DIALECTS).corrections, 0)

    def test_not_a_correction_round_is_a_denial_and_not_a_round(self):
        """`not a correction round` is the shape that reads as its opposite.

        The prose-deletion road of `SKILL.md` step 5 ends a rejected round
        with no correction round and says so in those words. Two rows of
        `archive-run-batch-44d0a8.md` write it.
        """
        self.assertEqual(quality_for("258", DIALECTS).corrections, 0)

    def test_one_round_reasoned_about_and_recorded_is_counted_once(self):
        """`so a correction round … correction: open 10:57 → closed 11:07`.

        Two patterns read the same row, and a row that reasons about a round
        before recording it was counted twice. Measured over the corpus, `a
        correction round` has no true positive at all: three matches, one
        reasoning and two denials.
        """
        self.assertEqual(quality_for("392", DIALECTS).corrections, 1)

    def test_a_round_written_correction_open_is_counted(self):
        """`correction open 04:06 → closed 04:20`, with no colon and no digit
        after the word. Two rows of the corpus, both read as none."""
        self.assertEqual(quality_for("401a", DIALECTS).corrections, 1)

    def test_a_negated_number_of_rounds_is_still_none(self):
        """`not one correction round`. The `a` alternative is gone, so the
        lookbehind now guards the numbered words alone -- and it must, or the
        denial reads as a record."""
        text = ("| Issue |\n|---|\n| 616 | attempt 1. verify: pass. review: "
                "accept. Not one correction round was opened. |\n")
        self.assertEqual(quality_for("616", text).corrections, 0)

    def test_two_correction_rounds_in_words_count_two(self):
        """The pattern names a number, so it must be read and not ignored."""
        text = ("| Issue |\n|---|\n| 612 | attempt 1. verify: pass. review: "
                "accept. two correction rounds, both closed. |\n")
        self.assertEqual(quality_for("612", text).corrections, 2)

    def test_a_row_that_really_states_nothing_is_still_unread(self):
        """236 has no verdict anywhere in its cell, and `unread` is right."""
        self.assertEqual(quality_for("236", DIALECTS).first_attempt,
                         tool.UNREAD)

    def test_the_words_no_correction_round_still_count_none(self):
        """Widening the pattern must not start matching the denial."""
        text = ("| Issue |\n|---|\n| 610 | attempt 1. verify: pass. review: "
                "accept. No implementer spawned, no correction round. |\n")
        self.assertEqual(quality_for("610", text).corrections, 0)


class Attempts(unittest.TestCase):
    def test_a_repeated_marker_is_one_attempt(self):
        """527 names `attempt 2` twice: once as running, once with its verdicts.

        Occurrences are not attempts. `check_attempt_cap.py` counts occurrences
        because it is asking a different question before a spawn; this figure is
        a count of rounds actually run, so it counts DISTINCT numbers.
        """
        self.assertEqual(quality_for("527").attempts, 2)

    def test_an_attempt_named_in_later_prose_is_not_a_second_attempt(self):
        """549's correction text cites `attempt 1's record` after the fact."""
        text = ("| Issue |\n|---|\n| 549 | attempt 1 — verify pass, review "
                "accept. correction: open -> closed 16:19. All three false "
                "claims are GONE from attempt 1's record. |\n")
        row = quality_for("549", text)
        self.assertEqual(row.attempts, 1)
        self.assertEqual(row.first_attempt, tool.PASS)


    def test_markers_out_of_order_never_leave_an_empty_span(self):
        """Cut the spans in the order the TEXT runs, not the order of numbers.

        Slicing from a number's marker to the NEXT NUMBER's marker gives a
        backwards slice on any row that names a later attempt first, and Python
        returns a backwards slice as "". An empty span is silent: it states no
        verdict, so its round is graded `unread` and charges no strike, and the
        run's strike total comes out low with nothing saying why.

        The row below runs 1, 3, 2. Attempt 2's rejection is the one that
        vanished.
        """
        row = ("| 601 | attempt 1 — verify pass, review REJECT. attempt 3 — "
               "verify pass, review accept. Attempt 2 read: attempt 2 — verify "
               "pass, review REJECT. |")
        self.assertTrue(all(span for _, span in tool.attempt_segments(row)))
        quality = quality_for("601", "| Issue |\n|---|\n" + row + "\n")
        self.assertEqual(quality.attempts, 3)
        self.assertEqual(quality.strikes, 2)

    def test_a_row_with_no_attempt_marker_reports_no_count(self):
        """The `attempt N` marker landed 2026-08-17 and older ledgers are read.

        Such a row ran at least one attempt, so printing `0` states a number
        that is false. The verdicts are still graded off the whole row.
        """
        text = ("| Issue |\n|---|\n| 602 | verify pass, review accept. "
                "committed `abc1234` |\n")
        row = quality_for("602", text)
        self.assertEqual(row.attempts, 0)
        self.assertEqual(row.first_attempt, tool.PASS)
        self.assertIn("not recorded", tool.render_quality((row,)))


class CorrectionRounds(unittest.TestCase):
    """Ruling 15's second figure."""

    def test_a_closed_round_is_counted(self):
        self.assertEqual(quality_for("547").corrections, 1)

    def test_the_run_total_matches_what_its_own_finale_counted(self):
        """`batch-b5e96d`'s ledger says 3 of 15 rows carried a round.

        This trimmed table holds one of those three, so the assertion is on the
        rows present. The figure is checked against a number the run recorded
        independently, not against this reader's own arithmetic.
        """
        rows = tool.issue_quality(LEDGER)
        self.assertEqual(sum(r.corrections for r in rows), 1)

    def test_the_words_no_correction_round_count_none(self):
        """530 says it had none, in a sentence holding the words."""
        self.assertEqual(quality_for("530").corrections, 0)

    def test_a_round_closed_in_words_is_not_reported_as_open(self):
        """`closed before the commit` carries no clock and is still closed.

        Ruling 15 asks for a COUNT of correction rounds and nothing about
        whether one is open. An open-round alarm was built here anyway and it
        fired on three rows of one real ledger that had all closed, so it is
        gone: the figure asked for is the figure printed.
        """
        row = quality_for("419c", DIALECTS)
        self.assertEqual(row.corrections, 1)
        self.assertFalse(hasattr(row, "unclosed"))


class Strikes(unittest.TestCase):
    """Ruling 15's third figure, and the one the ledger states in prose."""

    def test_one_rejected_round_is_one_strike(self):
        """527: attempt 1 rejected, attempt 2 accepted. The row says so too."""
        self.assertEqual(quality_for("527").strikes, 1)

    def test_a_criteria_reset_annuls_every_strike_before_it(self):
        """531: two rejected rounds, then a reset, then an accepted round.

        `SKILL.md` step 8: a criteria fault is "not a strike — the earlier
        attempts were graded against a spec that no longer exists". The row
        agrees in its own words: "the strikes are annulled".
        """
        self.assertEqual(quality_for("531").strikes, 0)

    def test_a_strike_after_a_reset_still_counts(self):
        """546: reject, reset, reject, accept. The row states `one strike`."""
        self.assertEqual(quality_for("546").strikes, 1)

    def test_a_passing_round_charges_nothing(self):
        self.assertEqual(quality_for("479").strikes, 0)

    def test_a_row_that_denies_the_strike_this_reader_counted_is_flagged(self):
        """530 is the whole reason this figure is not asserted as measured.

        Its round was rejected and charged no strike, on a road `SKILL.md` step
        5 permits and no marker records. The count derived from structure says
        one; the row says NOT a strike. Neither is silently preferred: the
        number stands and the disagreement is printed.
        """
        row = quality_for("530")
        self.assertEqual(row.strikes, 1)
        self.assertTrue(row.flags)
        self.assertIn("530", row.flags[0])

    def test_a_reset_row_is_not_flagged_for_saying_annulled(self):
        """531 and 546 both use the word, and the reset already explains it."""
        self.assertEqual(quality_for("531").flags, ())
        self.assertEqual(quality_for("546").flags, ())

    def test_each_shape_of_denial_is_recognised(self):
        """`DENIAL` names three shapes and only one was covered.

        Deleting either of the other two left the suite green, so a row using
        them would have had its disagreement swallowed.
        """
        for words in ("NOT a strike",
                      "annulled from any strike",
                      "the strike is annulled",
                      "a standards split charging no strike"):
            text = ("| Issue |\n|---|\n| 614 | attempt 1 — verify pass, "
                    f"review REJECT. {words}. |\n")
            with self.subTest(words=words):
                self.assertTrue(quality_for("614", text).flags, words)

    def test_an_annulment_with_nothing_to_annul_is_not_flagged(self):
        """533's runner error annulled a strike its round never earned."""
        row = quality_for("533")
        self.assertEqual(row.strikes, 0)
        self.assertEqual(row.flags, ())


class RenderVerdict(unittest.TestCase):
    """The sentence the merge briefing carries, ruling 22."""

    def test_a_void_block_says_the_work_is_still_good(self):
        """The whole point of ruling 22, and it must survive into the briefing.

        A reader who meets the word VOID with no explanation reads it as a
        failed run and questions a merge that is fine.
        """
        text = tool.render_verdict(tool.trial_verdict(
            LANDED_OK + LANDED_MODEL_FAULT))
        self.assertIn("VOID", text)
        self.assertIn("still good work", text)
        self.assertIn("run-issues-verify-gate", text)

    def test_a_holding_block_names_how_many_spawns_were_read(self):
        """`holds` on two spawns and on eighty are different evidence."""
        text = tool.render_verdict(tool.trial_verdict(LANDED_OK * 88))
        self.assertIn("88", text)

    def test_an_unmeasured_block_never_reads_as_a_pass(self):
        text = tool.render_verdict(tool.trial_verdict(""))
        self.assertIn("not measured", text.lower())
        self.assertNotIn("VOID", text)


class RenderQuality(unittest.TestCase):
    def test_the_table_carries_one_row_per_issue_and_a_total(self):
        text = tool.render_quality(tool.issue_quality(LEDGER))
        for issue in ("533", "546", "530", "531"):
            self.assertIn(issue, text)
        self.assertIn("7 issue(s)", text)

    def test_a_flag_is_printed_under_the_table_and_never_swallowed(self):
        """530's disagreement is the figure's own limit and must be visible."""
        text = tool.render_quality(tool.issue_quality(LEDGER))
        self.assertIn("denies the strike", text)

    def test_no_rows_says_so_rather_than_printing_an_empty_table(self):
        self.assertIn("no status table", tool.render_quality(()).lower())


class HuntBlock(unittest.TestCase):
    """A hunt takes the same verdict and has no per-issue rounds to grade."""

    def test_a_hunt_says_it_has_no_issues_rather_than_a_missing_reading(self):
        """Ruling 15's three figures are PER ISSUE, and a hunt has none.

        A hunt resolves register rows, not issues, and it never runs an
        attempt, a gate round or a correction round. Printing `no status table`
        there would report a hole where there is nothing to fill.
        """
        text = tool.render_block((), (), tool.trial_verdict(LANDED_OK),
                                 kind="hunt")
        self.assertIn("a hunt has no issues", text.lower())
        # `not a clean run` is the RUN's sentence for an unreadable status
        # table. A hunt reaching it would be told to go and find a table that
        # never existed.
        self.assertNotIn("not a clean run", text)
        self.assertNotIn("per issue", text)

    def test_a_run_with_no_status_table_still_reports_the_hole(self):
        text = tool.render_block((), (), tool.trial_verdict(LANDED_OK))
        self.assertIn("not a clean run", text)
        self.assertIn("per issue", text)


# Every real ledger this machine holds, not one of them. Sitting 4's first
# reading was measured against `batch-b5e96d` alone and the review of
# 2026-09-06 found five dialects it could not read, in twelve other ledgers.
CORPUS = pathlib.Path("/home/user/project/.scratch/example-feature")


class TheWholeCorpus(unittest.TestCase):
    """A regression net over every ledger, not over the one that agreed.

    It is deliberately WEAK on figures: asserting a count per ledger would be
    asserting this reader's own arithmetic back at itself. It asserts the two
    properties a narrowed regex breaks first -- rows are found at all, and a
    row that states a verdict is not silently `unread`.

    Skipped where the corpus is absent, because these files are in another
    repository and this suite must run without it.
    """

    def setUp(self):
        if not CORPUS.is_dir():
            self.skipTest(f"{CORPUS} is not on this machine")
        self.ledgers = sorted(CORPUS.glob("archive-run-*.md")) + [
            CORPUS / "runs" / "batch-b5e96d" / "run.md",
            CORPUS / "runs" / "batch-170a59" / "run.md"]
        self.rows = []
        for path in self.ledgers:
            if path.exists():
                self.rows.extend(
                    tool.issue_quality(path.read_text(
                        encoding="utf-8", errors="replace")))

    def test_the_corpus_is_big_enough_to_be_a_net(self):
        """Measured 2026-09-06: 18 files read, 17 holding a status table --
        `archive-run-journal-batch-45c8b1.md` is a journal -- and 149 rows.

        `batch-170a59` was added by ticket 37 sitting 3, because it is the one
        ledger on this machine that holds a SECOND table whose first cell can
        pass for an issue id, and its absence is why sitting 4 never saw the
        fault ruling 28 sends here.
        """
        self.assertGreaterEqual(len(self.ledgers), 17)
        self.assertGreaterEqual(len(self.rows), 149)

    def test_the_run_with_two_tables_reads_its_own_six_issues(self):
        """Ticket 37, ruling 28's repair half, measured both ways.

        Before the bound this returned TWELVE rows for a six-issue run: the
        six issues, plus six rows of the carry-forward table of test counts at
        `run.md:35-43`, which open `149c (-13, -3)`. The six phantoms read
        `unread` and `not recorded`, so the totals stayed right and every rate
        was computed over a denominator twice the truth.

        The ledger's own status table is the independent source: it holds six
        rows, one per slice, 149c to 149h.
        """
        path = CORPUS / "runs" / "batch-170a59" / "run.md"
        if not path.exists():
            self.skipTest("batch-170a59 is not on this machine")
        rows = tool.issue_quality(path.read_text(encoding="utf-8"))
        self.assertEqual([r.issue for r in rows],
                         ["149c", "149d", "149e", "149f", "149g", "149h"])
        self.assertEqual([r.first_attempt for r in rows].count(tool.UNREAD), 0)

    def test_almost_no_row_reads_unread(self):
        """Measured 2026-09-06: 2 of 143, both genuine.

        `archive-run-f180e3-merged.md` issue 236 has an empty Notes cell, and
        `archive-run-dc132b-merged.md` issue 288 was still in progress. Every
        other row in the corpus states a verdict this reads. A regex narrowed
        by a later edit shows up here first: before the dialect fixes of
        2026-09-06 this figure was 13.
        """
        unread = [r.issue for r in self.rows
                  if r.first_attempt == tool.UNREAD]
        self.assertLessEqual(len(unread), 3, f"unread rows: {unread}")

    def test_every_ledger_that_states_a_strike_derives_one(self):
        """The check that caught the bolded verdicts.

        Two ledgers stated strikes in prose and reported `0 strike(s)` --
        `395-397` and `batch-45c8b1` -- because the only verdict word in those
        rows was bolded and invisible, and five more undercounted. Prose is the
        independent source here: this reader never writes it.
        """
        stated = re.compile(r"\*\*strike \d\*\*|\bone strike\b|\btwo strikes\b",
                            re.IGNORECASE)
        for path in self.ledgers:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            rows = tool.issue_quality(text)
            if not rows or not stated.search(text):
                continue
            with self.subTest(ledger=path.name):
                self.assertGreater(sum(r.strikes for r in rows), 0)

    def test_the_one_run_that_counted_its_own_rounds_agrees(self):
        """`batch-b5e96d`'s finale wrote "15 status rows read, 3 carrying a
        correction round" into its own ledger, by hand, at the time.

        That sentence is the only independent count of this figure anywhere,
        and it is not derived from anything this module does.
        """
        path = CORPUS / "runs" / "batch-b5e96d" / "run.md"
        if not path.exists():
            self.skipTest("batch-b5e96d is not on this machine")
        rows = tool.issue_quality(path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 15)
        self.assertEqual(sum(1 for r in rows if r.corrections), 3)


class Cli(unittest.TestCase):
    """It can never halt a finale (ruling 22, and `run_costs.py`'s rule)."""

    def test_an_unknown_batch_exits_zero_and_says_what_it_looked_for(self):
        """Both roads name the batch: a walk that ran and found nothing, and a
        walk that could not run at all.

        This suite is run from wherever somebody happens to be, and a
        directory outside a git repository takes the second road. It asserted
        only the first until 2026-09-06, so it failed on the correct answer.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--batch", "batch-nothing-names-this"])
        self.assertEqual(code, 0)
        printed = out.getvalue()
        self.assertIn("batch-nothing-names-this", printed)
        self.assertIn("What could not be read", printed)

    def test_a_bad_repo_exits_zero_rather_than_raising(self):
        """`finale.md` says "it can never halt the finale", and a raise would.

        `git -C /nonexistent worktree list` exits 128, and `list_worktrees`
        does not catch it. The review of 2026-09-06 saw exit 1 with nothing
        printed, in the middle of a finale.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--repo", "/nonexistent-repo", "--batch", "b-1"])
        self.assertEqual(code, 0)
        self.assertIn("could not be read", out.getvalue())

    def test_an_unreadable_journal_is_named_and_not_reported_as_silence(self):
        """A journal that could not be OPENED is a missing measurement, and
        saying "holds no `model landed:` line" states a fact about contents
        nobody read."""
        root = pathlib.Path(tempfile.mkdtemp())
        ledger = root / "run.md"
        ledger.write_text(LEDGER, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--ledger", str(ledger),
                              "--journal", str(root / "gone.md")])
        printed = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("gone.md", printed)
        self.assertIn("could not be read", printed)

    def test_no_ledger_found_prints_neither_shape_of_quality_section(self):
        """A hunt whose `round-brief.md` is already deleted took the RUN road
        and was told to go and find a status table it never had."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            tool.main(["--batch", "hunt-nothing-names-this"])
        printed = out.getvalue()
        self.assertNotIn("not a clean run", printed)
        self.assertNotIn("a hunt has no issues", printed)
        self.assertIn("no ledger", printed.lower())

    def test_a_round_brief_passed_by_hand_is_read_as_a_hunt(self):
        """`--ledger` must reach the same answer `--batch` does.

        The basename decides, which is the rule `find_live_ledger.journal_for`
        already uses to pick `round-journal.md` over `run-journal.md`. Without
        it a hunt read by hand is told to go and find a status table that has
        never existed for a hunt.
        """
        root = pathlib.Path(tempfile.mkdtemp())
        brief = root / "round-brief.md"
        brief.write_text("# Round brief\n", encoding="utf-8")
        (root / "round-journal.md").write_text(LANDED_OK, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--ledger", str(brief)])
        printed = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("a hunt has no issues", printed.lower())
        self.assertIn("holds", printed.lower())

    def test_a_ledger_passed_by_hand_is_read_without_a_batch(self):
        """The fixture road, and the road a run whose transcripts are gone takes."""
        root = pathlib.Path(tempfile.mkdtemp())
        ledger = root / "run.md"
        ledger.write_text(LEDGER, encoding="utf-8")
        (root / "run-journal.md").write_text(LANDED_OK * 2, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--ledger", str(ledger)])
        printed = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("533", printed)
        self.assertIn("holds", printed.lower())


class TheRunnerMarker(unittest.TestCase):
    """Ticket 37 ruling 28's second half: a fixed token per gate round.

    Sitting 4 measured the limit and named the fix. Only `attempt N` and
    `criteria reset` are markers; a gate's verdict and a strike are sentences,
    and reading them cost SEVEN dialects across sixteen ledgers, every one of
    them read as silence until a review found it. `check_attempt_cap.py` tells
    the same story about itself: `implement`/`retry` could not be counted, so
    `attempt N` was minted and the runner writes it.

    The token is `gates <n>: verify=<pass|reject> review=<pass|reject>`. One
    spelling, two fixed verdict words, no synonyms -- a minted marker that
    accepted `accept` and `passed` too would be a seventh dialect rather than
    an end to them.

    **The reader PREFERS the token and keeps its prose reader**, because the
    sixteen ledgers already written carry no token and ruling 3 loses no
    history.
    """

    def row(self, notes, issue="700"):
        return f"| Issue | Notes |\n|---|---|\n| {issue} | {notes} |\n"

    def test_the_marker_is_read(self):
        text = self.row("attempt 1; gates 1: verify=pass review=pass; "
                        "committed `abc1234`")
        self.assertEqual(quality_for("700", text).first_attempt, tool.PASS)

    def test_a_rejection_in_the_marker_is_read(self):
        text = self.row("attempt 1; gates 1: verify=pass review=reject")
        self.assertEqual(quality_for("700", text).first_attempt, tool.REJECT)

    def test_the_marker_wins_where_the_prose_disagrees_with_it(self):
        """The whole point of preferring it. A round the gates rejected, in a
        row whose prose also reasons about a pass elsewhere, must read the
        token rather than whichever sentence the regex reached first."""
        text = self.row("attempt 1; gates 1: verify=pass review=reject; "
                        "the review gate would pass this on a rewrite")
        self.assertEqual(quality_for("700", text).first_attempt, tool.REJECT)

    def test_prose_still_reads_where_no_marker_was_written(self):
        """Sixteen ledgers, 143 rows, none of them carrying a token."""
        text = self.row("attempt 1 — verify: pass, review: accept")
        self.assertEqual(quality_for("700", text).first_attempt, tool.PASS)

    def test_a_strike_is_still_derived_from_the_marker(self):
        """Ruling 28: strikes stay derived under either road. The token says
        what the gates answered; it does not say whether a strike was charged,
        because `SKILL.md` step 5's prose-deletion road and a runner-error
        annulment both cancel one in prose."""
        text = self.row("attempt 1; gates 1: verify=pass review=reject; "
                        "attempt 2; gates 2: verify=pass review=pass")
        row = quality_for("700", text)
        self.assertEqual(row.strikes, 1)
        self.assertEqual(row.attempts, 2)

    def test_sitting_fours_star_survives_the_marker(self):
        """Ruling 28 keeps the `*` on a row whose own words disagree with the
        count, and it must fire on a marked row exactly as on a prose one."""
        text = self.row("attempt 1; gates 1: verify=pass review=reject; "
                        "a runner error, so this is not a strike")
        row = quality_for("700", text)
        self.assertEqual(row.strikes, 1)
        self.assertTrue(row.flags)

    def test_the_marker_is_counted_and_reported(self):
        """`marked` is how the rate at which the token is actually written
        becomes visible, rather than being assumed once it is minted."""
        text = self.row("attempt 1; gates 1: verify=pass review=pass")
        self.assertEqual(quality_for("700", text).marked, 1)

    def test_an_unmarked_row_reports_no_marked_rounds(self):
        text = self.row("attempt 1 — verify: pass, review: accept")
        self.assertEqual(quality_for("700", text).marked, 0)


class BothGateVerdicts(unittest.TestCase):
    """Ticket 37 ruling 17 puts BOTH gate verdicts on the per-issue line.

    `first_attempt` collapses them into one word, which is right for ruling
    15's count and wrong for a line meant to answer "which gate rejects more
    often". So the two are carried apart as well, for the FIRST attempt.

    `v` and `r` are the shortest dialect in the corpus and mean the same two
    gates. A verdict stated for the PAIR -- `both reject`, `rejected by BOTH
    gates` -- is one statement about two gates, and it fills both cells,
    because that is what it says. `unread` where a row states nothing.
    """

    def row(self, notes, issue="700"):
        return f"| Issue | Notes |\n|---|---|\n| {issue} | {notes} |\n"

    def test_a_split_verdict_is_carried_apart(self):
        text = self.row("attempt 1; verify: pass; review: reject")
        got = quality_for("700", text)
        self.assertEqual(got.verify, tool.PASS)
        self.assertEqual(got.review, tool.REJECT)

    def test_the_short_dialect_names_the_same_two_gates(self):
        text = self.row("attempt 1 · v: pass · r: reject")
        got = quality_for("700", text)
        self.assertEqual(got.verify, tool.PASS)
        self.assertEqual(got.review, tool.REJECT)

    def test_a_pair_verdict_fills_both(self):
        text = self.row("attempt 1 — gates both reject 03:03/03:05")
        got = quality_for("700", text)
        self.assertEqual(got.verify, tool.REJECT)
        self.assertEqual(got.review, tool.REJECT)

    def test_the_minted_marker_is_preferred_here_too(self):
        text = self.row("attempt 1; gates 1: verify=reject review=pass")
        got = quality_for("700", text)
        self.assertEqual(got.verify, tool.REJECT)
        self.assertEqual(got.review, tool.PASS)

    def test_a_gate_that_stated_nothing_reads_unread_not_pass(self):
        """The rule the whole module carries: a hole is visible, never a
        pass. A row naming one gate says nothing about the other."""
        text = self.row("attempt 1; verify: pass")
        got = quality_for("700", text)
        self.assertEqual(got.verify, tool.PASS)
        self.assertEqual(got.review, tool.UNREAD)

    def test_only_the_first_attempt_is_read(self):
        """Same rule as `first_attempt`: the figure is about attempt ONE, and
        a later attempt neither repairs nor spoils it."""
        text = self.row("attempt 1; verify: pass; review: reject; "
                        "attempt 2; verify: pass; review: pass")
        got = quality_for("700", text)
        self.assertEqual(got.review, tool.REJECT)

    def test_the_real_corpus_splits_the_gates_where_it_states_them(self):
        """`batch-170a59` issue 149e: the review gate rejected attempt 1 and
        the verify gate passed it. The ledger says so in its own words, and
        this is the one figure a collapsed `first_attempt` cannot show."""
        path = CORPUS / "runs" / "batch-170a59" / "run.md"
        if not path.exists():
            self.skipTest("batch-170a59 is not on this machine")
        rows = {r.issue: r for r in
                tool.issue_quality(path.read_text(encoding="utf-8"))}
        self.assertEqual(rows["149e"].verify, tool.PASS)
        self.assertEqual(rows["149e"].review, tool.REJECT)
        self.assertEqual(rows["149c"].review, tool.PASS)


if __name__ == "__main__":
    unittest.main()
