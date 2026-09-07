#!/usr/bin/env python3
"""Cases for run_records.py — the two append-only record files and the view.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 2. Rulings 2, 3, 4, 6, 9, 10, 11, 15, 17 and 23.

The anchor fault is ticket 36's fault 9. Run `review-375cbf` appended TWO cost
rows for itself on 2026-09-01, and nothing noticed. Both rows are in
`.scratch/workflow-audit/run-costs.md` today, four minutes and 0.9M weighted
tokens apart, and a reader comparing a row against the row above it compares
the run against itself. Ruling 4 puts the refusal here.

The second fault is the shape. The table cannot be parsed as it stands: a
correction paragraph sits between two data rows, so `run-costs.md` is prose
with a table in it, not a table. Ruling 2 makes the record machine-readable and
the markdown a generated view of it.

    python3 -m unittest test_run_records
"""

from __future__ import annotations

import json
import pathlib
import re
import tempfile
import unittest

import run_records as tool


def repo() -> pathlib.Path:
    return pathlib.Path(tempfile.mkdtemp())


def run_record(**over):
    """A minimal legal run record. Every case names only what it varies."""
    record = {
        "batch": "batch-abc123",
        "kind": "run",
        "taken": "2026-09-06",
        "version": "2.1.261",
        "issues": 6,
        "note": "first run under the new records",
    }
    record.update(over)
    return record


class DuplicateBatch(unittest.TestCase):
    """Ruling 4, and ticket 36's fault 9."""

    def test_first_row_for_a_batch_is_appended(self):
        root = repo()
        ok, why = tool.append_run(root, run_record())
        self.assertTrue(ok, why)
        self.assertEqual(1, len(tool.read_runs(root).records))

    def test_second_row_for_the_same_batch_is_refused(self):
        root = repo()
        tool.append_run(root, run_record())
        ok, why = tool.append_run(root, run_record(note="a second reading"))
        self.assertFalse(ok)
        self.assertIn("batch-abc123", why)

    def test_the_refused_row_is_not_written(self):
        """A refusal that still appends is worse than no refusal: the reader
        would see two rows AND a passing exit code."""
        root = repo()
        tool.append_run(root, run_record())
        tool.append_run(root, run_record(note="a second reading"))
        self.assertEqual(1, len(tool.read_runs(root).records))

    def test_a_different_batch_is_appended(self):
        root = repo()
        tool.append_run(root, run_record())
        ok, _ = tool.append_run(root, run_record(batch="batch-def456"))
        self.assertTrue(ok)
        self.assertEqual(2, len(tool.read_runs(root).records))

    def test_the_refusal_names_the_road(self):
        """A refusal that does not say what to do next sends the finale to a
        hand edit of the view, which the hook then refuses too."""
        root = repo()
        tool.append_run(root, run_record())
        _, why = tool.append_run(root, run_record())
        self.assertIn("runs.jsonl", why)


class DamagedLines(unittest.TestCase):
    """A half-written line must not take the whole history down with it."""

    def test_a_damaged_line_is_reported_and_the_rest_still_read(self):
        root = repo()
        tool.append_run(root, run_record())
        tool.append_run(root, run_record(batch="batch-def456"))
        path = root / tool.RUNS
        path.write_text(path.read_text() + '{"batch": "half\n', encoding="utf-8")
        seen = tool.read_runs(root)
        self.assertEqual(2, len(seen.records))
        self.assertEqual(1, len(seen.damaged))

    def test_a_damaged_line_still_blocks_its_own_batch_id(self):
        """Only if the id is readable. A line nobody can parse names no batch,
        so it cannot be the guard for one -- and saying otherwise would refuse
        a legitimate row on evidence nobody has."""
        root = repo()
        path = root / tool.RUNS
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all}\n", encoding="utf-8")
        ok, _ = tool.append_run(root, run_record())
        self.assertTrue(ok)


class NoteLimit(unittest.TestCase):
    """Ruling 15: the note is "what changed since the last line", at most 160
    characters, refused above it. The rest stays in the merge briefing.

    The measured reason: the note cell of the 2026-09-05 row runs to 559
    characters and carries five separate facts, so nothing can be read from it
    and nobody scans a column that wide."""

    def test_a_note_at_the_limit_is_appended(self):
        root = repo()
        ok, why = tool.append_run(root, run_record(note="x" * 160))
        self.assertTrue(ok, why)

    def test_a_note_over_the_limit_is_refused(self):
        root = repo()
        ok, why = tool.append_run(root, run_record(note="x" * 161))
        self.assertFalse(ok)
        self.assertIn("161", why)

    def test_a_carried_row_may_exceed_the_limit(self):
        """Ruling 3 against ruling 15. Six of the 18 rows carried on
        2026-09-06 hold notes over the cap, the longest 538 characters, and
        truncating them would have lost 1,293 characters of history."""
        root = repo()
        ok, why = tool.append_run(root, run_record(note="x" * 400, carried=True))
        self.assertTrue(ok, why)

    def test_a_new_line_may_not_claim_to_be_carried_to_dodge_the_cap(self):
        """The exemption is for the one-time migration. A finale writes no
        `carried` flag, so `run_costs.build_record` cannot reach this road."""
        record = tool.append_run.__doc__ or ""
        import run_costs
        self.assertNotIn("carried", run_costs.build_record(batch="b", kind="run"))

    def test_the_over_long_note_is_not_truncated_and_written(self):
        """Truncation would drop the writer's words silently and leave a
        sentence ending mid-word in the one cell a person reads."""
        root = repo()
        tool.append_run(root, run_record(note="x" * 400))
        self.assertEqual(0, len(tool.read_runs(root).records))


class VersionCell(unittest.TestCase):
    """Ruling 10: the version cell holds the Claude Code version ONLY.

    The live table proves it needs a refusal: three of its rows read `not
    stated`, one reads `claude-opus-5`, two read `2.1.251 (Claude Code)` and
    three read `2.1.251`. The model landed there because `finale.md` asks an
    agent to type `--version <cc-version>` and an agent typed the model."""

    def test_a_bare_version_is_kept(self):
        root = repo()
        tool.append_run(root, run_record(version="2.1.261"))
        self.assertEqual("2.1.261", tool.read_runs(root).records[0]["version"])

    def test_the_claude_code_suffix_is_stripped(self):
        root = repo()
        tool.append_run(root, run_record(version="2.1.261 (Claude Code)"))
        self.assertEqual("2.1.261", tool.read_runs(root).records[0]["version"])

    def test_a_model_name_in_the_version_cell_is_refused(self):
        root = repo()
        ok, why = tool.append_run(root, run_record(version="claude-opus-5"))
        self.assertFalse(ok)
        self.assertIn("claude-opus-5", why)

    def test_not_stated_is_legal_because_the_backfilled_rows_carry_it(self):
        """Ruling 10 says the backfilled rows keep `not stated`, so the value
        has to survive a round trip through the writer."""
        root = repo()
        ok, _ = tool.append_run(root, run_record(version="not stated"))
        self.assertTrue(ok)


class Kind(unittest.TestCase):
    """Ruling 11: hunts share the files, with a `kind` field."""

    def test_a_hunt_is_appended(self):
        root = repo()
        ok, _ = tool.append_run(root, run_record(kind="hunt"))
        self.assertTrue(ok)

    def test_an_unknown_kind_is_refused(self):
        """Ruling 12 compares a line against the previous line OF THE SAME
        KIND, so a third spelling silently removes a line from both trends."""
        root = repo()
        ok, why = tool.append_run(root, run_record(kind="round"))
        self.assertFalse(ok)
        self.assertIn("round", why)

    def test_a_missing_kind_is_refused(self):
        root = repo()
        record = run_record()
        del record["kind"]
        ok, _ = tool.append_run(root, record)
        self.assertFalse(ok)


class InsideRunCounts(unittest.TestCase):
    """Ruling 6's four counts and the denominator beside them.

    **Sitting 2 declared these five fields and refused every figure for them,
    on purpose.** Its reason was ruling 28: `run_quality.issue_quality`
    returned 12 rows for the six-issue run `batch-170a59`, so the totals were
    right, the denominator was wrong, and every rate ruling 6 asks for would
    have been wrong. The human chose branch A -- declare the schema, write explicit
    nulls, and let ONE reader fill all five at one moment.

    **Sitting 3 is that moment.** `check_commit_order.status_rows` is bounded
    to the status table, the corpus reads 149 rows across seventeen ledgers
    instead of 155, and `batch-170a59` reads its own six. So the blanket
    refusal comes out in the same change that makes the figures true.

    What replaces it is narrower and mechanical: a count must be a
    non-negative whole number or null, the five names are the only five, and
    **a count may not be written without its denominator**. That last is
    ruling 6's own wording -- "with the issue count beside them" -- and it
    refuses exactly the shape ruling 28 was raised about: real totals over a
    denominator nobody read.
    """

    def counts(self, **over):
        given = {"issues_graded": 6, "first_attempt_passes": 5,
                 "correction_rounds": 1, "strikes": 1, "escalations": 0}
        given.update(over)
        return given

    def test_the_five_fields_are_present_even_when_nothing_measured_them(self):
        """The key is present and null. An omitted key is indistinguishable
        from a schema written before the field existed, and these files are
        append-only, so that difference would be permanent."""
        root = repo()
        tool.append_run(root, run_record())
        quality = tool.read_runs(root).records[0]["quality"]
        self.assertEqual(sorted(tool.QUALITY_FIELDS), sorted(quality))
        self.assertTrue(all(value is None for value in quality.values()))

    def test_a_measured_figure_is_now_written(self):
        root = repo()
        ok, why = tool.append_run(root, run_record(quality=self.counts()))
        self.assertTrue(ok, why)
        self.assertEqual(tool.read_runs(root).records[0]["quality"]["strikes"], 1)

    def test_a_measured_zero_is_written_and_is_not_a_missing_measurement(self):
        """The other half of sitting 2's rule, now that a reader exists. A run
        with no strikes is a FACT and must be recordable as one; only a run
        whose strikes were never read is null."""
        root = repo()
        ok, why = tool.append_run(root, run_record(quality=self.counts(strikes=0)))
        self.assertTrue(ok, why)
        self.assertEqual(tool.read_runs(root).records[0]["quality"]["strikes"], 0)

    def test_a_count_without_its_denominator_is_refused(self):
        """Ruling 6: the counts go on the line "with the issue count beside
        them", because the view shows a RATE beside each. A rate over a
        denominator nobody read is the fault ruling 28 was raised about."""
        root = repo()
        ok, why = tool.append_run(
            root, run_record(quality=self.counts(issues_graded=None)))
        self.assertFalse(ok)
        self.assertIn("issues_graded", why)

    def test_a_denominator_with_no_counts_is_allowed(self):
        """The other direction is not a fault: a run whose status table was
        read and whose rows stated no verdict is a real thing, and it is what
        `unread` means."""
        root = repo()
        ok, why = tool.append_run(root, run_record(quality={
            "issues_graded": 6, "first_attempt_passes": None,
            "correction_rounds": None, "strikes": None, "escalations": None}))
        self.assertTrue(ok, why)

    def test_an_unknown_count_name_is_refused(self):
        """The five names are the schema. A sixth spelling writes a figure
        into a column no view renders and no reader compares."""
        root = repo()
        ok, why = tool.append_run(
            root, run_record(quality=dict(self.counts(), strikeouts=2)))
        self.assertFalse(ok)
        self.assertIn("strikeouts", why)

    def test_a_count_that_is_not_a_whole_number_is_refused(self):
        root = repo()
        ok, why = tool.append_run(
            root, run_record(quality=self.counts(strikes="three")))
        self.assertFalse(ok)
        self.assertIn("strikes", why)

    def test_a_negative_count_is_refused(self):
        root = repo()
        ok, _ = tool.append_run(root, run_record(quality=self.counts(strikes=-1)))
        self.assertFalse(ok)

    def test_more_passes_than_issues_graded_is_refused(self):
        """A first-attempt pass is one issue's, so the count can never exceed
        the denominator. It is the cheapest possible check that the two came
        from the same reading, and ruling 28's fault would have failed it:
        twelve rows graded against six real issues."""
        root = repo()
        ok, why = tool.append_run(
            root, run_record(quality=self.counts(first_attempt_passes=9)))
        self.assertFalse(ok)
        self.assertIn("first_attempt_passes", why)

    def test_a_refusal_is_returned_and_never_raised(self):
        """Everything on this road answers `(False, reason)`. A measurement
        that could halt a finale would cost a run the thing it measures."""
        root = repo()
        ok, why = tool.append_run(root, run_record(quality=["not", "a", "map"]))
        self.assertFalse(ok)
        self.assertTrue(why)


class PerIssueLines(unittest.TestCase):
    """Ruling 17's second file: one line per issue, keyed by batch id.

    `append_issues` takes the whole run's rows at once, because they are
    written at one moment by one reader and a half-written run is a run whose
    rates are computed over part of itself.
    """

    def rows(self, batch="batch-abc123"):
        return [{"batch": batch, "issue": "149c", "strikes": 0},
                {"batch": batch, "issue": "149e", "strikes": 1}]

    def test_the_rows_are_appended_one_line_each(self):
        root = repo()
        ok, why = tool.append_issues(root, self.rows())
        self.assertTrue(ok, why)
        self.assertEqual([one["issue"] for one in tool.read_issues(root).records],
                         ["149c", "149e"])

    def test_a_second_write_for_the_same_batch_is_refused(self):
        """Ruling 4's reason, on the second file. Run `review-375cbf` wrote
        itself twice into the per-run table and nothing noticed; a run written
        twice here would double every per-issue population a trend reads."""
        root = repo()
        tool.append_issues(root, self.rows())
        ok, why = tool.append_issues(root, self.rows())
        self.assertFalse(ok)
        self.assertIn("batch-abc123", why)

    def test_another_batch_is_not_refused(self):
        root = repo()
        tool.append_issues(root, self.rows())
        ok, why = tool.append_issues(root, self.rows(batch="batch-other"))
        self.assertTrue(ok, why)

    def test_a_row_naming_no_issue_is_refused_before_anything_is_written(self):
        """All or nothing. A partial write would leave a run whose per-issue
        population is smaller than its own `issues_graded`, and nothing would
        say which rows were lost."""
        root = repo()
        ok, why = tool.append_issues(
            root, self.rows() + [{"batch": "batch-abc123", "issue": ""}])
        self.assertFalse(ok)
        self.assertEqual(tool.read_issues(root).records, [])

    def test_rows_from_two_batches_in_one_call_are_refused(self):
        """One call writes one run. Two batches in one list is a caller that
        has lost track of which run it is measuring."""
        root = repo()
        ok, why = tool.append_issues(
            root, self.rows() + self.rows(batch="batch-other"))
        self.assertFalse(ok)

    def test_no_rows_is_not_an_error_and_writes_nothing(self):
        """A hunt has no issues (ruling 11 shares the files; `run_quality`
        already says a hunt has no per-issue figures). Refusing here would
        print a fault at every round end."""
        root = repo()
        ok, why = tool.append_issues(root, [])
        self.assertTrue(ok, why)
        self.assertEqual(tool.read_issues(root).records, [])


class GeneratedView(unittest.TestCase):
    """Ruling 2: `run-costs.md` becomes a view generated from `runs.jsonl`,
    keeping its name so every citation written since 2026-08-18 stays true.
    Ruling 13 makes it the one-look page."""

    def test_the_view_names_itself_generated(self):
        """A reader who edits it loses the edit at the next finale. The hook
        refuses the write; this line says why before they try."""
        text = tool.render_view([run_record()])
        self.assertIn("runs.jsonl", text)
        self.assertIn("generated", text.lower())

    def test_every_record_gets_a_row(self):
        rows = [run_record(batch=f"batch-{n}") for n in range(4)]
        text = tool.render_view(rows)
        for one in rows:
            self.assertIn(one["batch"], text)

    def test_the_note_reaches_the_row(self):
        text = tool.render_view([run_record(note="the hooks changed mid-run")])
        self.assertIn("the hooks changed mid-run", text)

    def test_a_backfilled_row_is_marked(self):
        """Ruling 3. The eleven backfilled rows carry no Hours and no Idle
        figure, and a reader comparing them against a measured row without
        knowing that is comparing two different things."""
        text = tool.render_view([run_record(backfilled=True)])
        self.assertIn("backfilled", text.lower())

    def test_the_header_says_why_one_row_was_deleted(self):
        """Ruling 3 requires the reason in the header, because the deletion is
        the one hand edit this file will ever carry."""
        text = tool.render_view([run_record()])
        self.assertIn("review-375cbf", text)

    def test_the_unmeasured_quality_cells_read_not_measured(self):
        """Branch A of 2026-09-06. Never `0`, and never blank: a blank cell
        reads as nothing to report."""
        text = tool.render_view([run_record()])
        self.assertIn("not measured", text)

    def test_a_hunt_and_a_run_are_both_shown_and_told_apart(self):
        """Ruling 11 shares the file; ruling 12 compares a line against the
        previous line of the same KIND, so the view has to show which."""
        text = tool.render_view([run_record(batch="b1", kind="run"),
                                 run_record(batch="b2", kind="hunt")])
        self.assertIn("hunt", text)
        self.assertIn("run", text)

    def test_the_model_cells_reach_the_view(self):
        """Ruling 9: the orchestrator's model, and the worker map."""
        text = tool.render_view([run_record(
            orchestrator_model="claude-opus-5/high",
            worker_models="implementer=opus/high gates=fable/high")])
        self.assertIn("claude-opus-5/high", text)
        self.assertIn("gates=fable/high", text)

    def test_the_fingerprint_reaches_the_view_with_its_dirty_mark(self):
        """Ruling 23. A dirty row may not be compared cleanly, so the mark has
        to survive to the page a person reads."""
        text = tool.render_view([run_record(fingerprint={
            "skills": {"head": "323099e54653", "dirty": True},
            "agents": {"head": "46fc7372c0bc", "dirty": False}})])
        self.assertIn("323099e", text)
        self.assertIn("dirty", text)


    def test_the_borrowed_mark_does_not_repeat_the_column_names_per_row(self):
        """They are the same five on every marked line -- one historical
        cause -- and repeating them cost 60 characters on 17 of 18 lines in
        the one column a person scans. The header names them once."""
        text = tool.render_view([run_record(borrowed=["issues", "weighted"])])
        row = [l for l in text.splitlines() if l.startswith("| `batch-abc123`")][0]
        self.assertIn("borrowed", row)
        self.assertNotIn("weighted", row)

    def test_a_pipe_in_a_note_cannot_break_the_table(self):
        """The one hostile input this file has. A note is free text written by
        an agent, and one `|` would silently add a column to that row and
        shift every cell after it."""
        def cells(note):
            text = tool.render_view([run_record(note=note)])
            row = [line for line in text.splitlines()
                   if line.startswith("| `batch-abc123`")][0]
            # A escaped pipe is still a pipe character, so counting characters
            # proves nothing. Split on the unescaped ones, which is what a
            # markdown renderer does.
            return len(re.split(r"(?<!\\)\|", row))
        self.assertEqual(cells("a b c"), cells("a | b | c"))

    def test_a_newline_in_a_note_cannot_break_the_table(self):
        """A newline in the note would end the row and leave its tail as a
        line of its own, which renders as a broken table rather than as a
        rendering bug anybody would recognise.

        **This counted the rendered rows until sitting 3, and the count was
        the wrong assertion.** It asserted two -- one cost row, one quality row
        -- so adding the `faster` table ruling 5 asks for failed it on no
        fault at all. What it is really about is that the note stays on ONE
        line and leaves no orphan behind, and that is what it now says.
        """
        text = tool.render_view([run_record(note="one\ntwo")])
        lines = text.splitlines()
        self.assertTrue(any("one two" in line for line in lines))
        self.assertNotIn("two", [line.strip() for line in lines])
        for line in lines:
            if line.startswith("| `batch-abc123`"):
                self.assertTrue(line.rstrip().endswith("|"))


    def test_the_header_counts_are_computed_not_typed(self):
        """The table this replaces said "18 rows" and was wrong within a day:
        a nineteenth row landed on 2026-09-06. A header number that is counted
        cannot go stale."""
        five = tool.render_view([run_record(batch=f"b{n}") for n in range(5)])
        three = tool.render_view([run_record(batch=f"b{n}") for n in range(3)])
        self.assertIn("so 5 lines are here", five)
        self.assertIn("so 3 lines are here", three)

    def test_the_borrowed_count_is_counted(self):
        text = tool.render_view([run_record(batch="b1", borrowed=["weighted"]),
                                 run_record(batch="b2")])
        self.assertIn("1 of the 2", text)

    def test_an_empty_history_still_renders_a_readable_page(self):
        text = tool.render_view([])
        self.assertIn("runs.jsonl", text)


class TheReviewOf2026_09_06(unittest.TestCase):
    """The `/code-review` pass on this sitting's own diff, four findings."""

    def test_a_quality_field_that_is_not_a_mapping_is_refused_not_raised(self):
        """Everything else on this road answers `(False, reason)`, and both
        `append_record` and the human's ruling of 2026-08-30 promise a measurement
        cannot halt a finale. Before the fix this raised `AttributeError`."""
        ok, why = tool.append_run(repo(), run_record(quality="oops"))
        self.assertFalse(ok)
        self.assertIn("mapping", why)

    def test_the_view_is_rendered_from_disk_not_from_a_stale_snapshot(self):
        """Ticket 38 puts two runs and a hunt in flight at once. Two finales
        appending seconds apart would each render its own older snapshot, and
        the last writer would publish a page missing the other run's line."""
        root = repo()
        tool.append_run(root, run_record(batch="run-a"))
        tool.append_run(root, run_record(batch="run-b"))
        tool.write_view(root)
        drawn = (root / tool.VIEW).read_text(encoding="utf-8")
        self.assertIn("run-a", drawn)
        self.assertIn("run-b", drawn)

    def test_the_view_write_leaves_no_temporary_file_behind(self):
        root = repo()
        tool.append_run(root, run_record())
        tool.write_view(root)
        leftovers = [p.name for p in (root / tool.WORKFLOW_AUDIT).iterdir()
                     if p.name.endswith(".tmp")]
        self.assertEqual([], leftovers)


class TheViewShowsWhatSittingThreeMeasured(unittest.TestCase):
    """Ruling 6: "The view shows the rate beside each count." Ruling 13 makes
    the view the one-look page: per-run table, per-issue table, longest steps
    by kind. Ruling 5: all five "faster" figures, so that one look tells the human
    where to optimise with no mental arithmetic.

    Sitting 2's header said "the four inside-run counts read `not measured` on
    every line below" and named ruling 28 as the cause. That sentence is now
    false, and a generated page that states a false fact about its own contents
    is worse than one that omits it -- so the header is counted from the
    records, as every other number in it already is.
    """

    def page(self, *records):
        return tool.render_view(list(records))

    def measured(self, **over):
        given = dict(run_record(), quality={
            "issues_graded": 6, "first_attempt_passes": 5,
            "correction_rounds": 1, "strikes": 1, "escalations": 0})
        given.update(over)
        return given

    def test_a_count_is_printed_with_its_rate(self):
        """5 of 6 is 83%. The rate is what ruling 6 asks the view to show, and
        computing it is exactly the mental arithmetic ruling 5 forbids."""
        page = self.page(self.measured())
        self.assertIn("5 (83%)", page)

    def test_a_zero_count_shows_a_zero_rate_and_not_a_gap(self):
        page = self.page(self.measured())
        self.assertIn("0 (0%)", page)

    def test_an_unmeasured_count_still_reads_not_measured(self):
        page = self.page(run_record())
        self.assertIn(tool.NOT_MEASURED, page)

    def test_the_header_no_longer_claims_every_line_is_unmeasured(self):
        """It said so, with ruling 28 as its reason, and the reason is spent."""
        page = self.page(self.measured())
        self.assertNotIn("read `not measured` on every line", page)

    def test_the_header_counts_the_lines_that_carry_the_figures(self):
        """Counted, never typed. The figure it replaced went stale in a day."""
        page = self.page(self.measured(), run_record(batch="batch-two"))
        self.assertIn("1 of the 2", page)

    def test_the_five_faster_figures_are_columns(self):
        page = self.page(self.measured(faster={
            "wall_minutes_per_issue": 120.0, "idle_minutes_per_issue": 30.0,
            "agent_hours_per_issue": 1.25, "estimate_median_ratio": 1.5,
            "issues_rated": 6}))
        for shown in ("120", "30", "1.25", "1.50x"):
            self.assertIn(shown, page)

    def test_a_missing_faster_figure_reads_not_measured_rather_than_zero(self):
        page = self.page(self.measured(faster={
            "wall_minutes_per_issue": None, "idle_minutes_per_issue": 30.0,
            "agent_hours_per_issue": None, "estimate_median_ratio": None,
            "issues_rated": 0}))
        self.assertIn(tool.NOT_MEASURED, page)

    def test_the_longest_step_per_kind_is_shown(self):
        page = self.page(self.measured(longest_steps={
            "build": {"minutes": 15.0, "label": "cold build",
                      "measured": "stamped"},
            "run-issues-implementer": {"minutes": 60.0, "label": "issue 149e",
                                       "measured": "agent"}}))
        self.assertIn("cold build", page)
        self.assertIn("stamped", page)
        self.assertIn("run-issues-implementer", page)

    def test_the_per_issue_table_is_rendered_from_the_issue_lines(self):
        page = tool.render_view([self.measured()], issues=[
            {"batch": "batch-abc123", "issue": "149e", "stage": "award",
             "estimate_minutes": 75.0, "span_minutes": 120.0,
             "agent_minutes": 200.0, "attempts": 2, "strikes": 1,
             "correction_rounds": 0, "escalated": True, "critical_gate": False,
             "migration": False, "cut_on_a_default": True,
             "verify": "pass", "review": "reject", "marked_rounds": 0,
             "derived_strike_disputed": False}])
        self.assertIn("149e", page)
        self.assertIn("award", page)

    def test_the_size_bucket_is_the_views_own_rule(self):
        """Ruling 18: "the view buckets it (small under 60, medium 60 to 120,
        large over 120). The rule lives in the view." So the RECORD keeps the
        midpoint in minutes and nothing else, and a later change of bucket
        re-reads every line already written."""
        self.assertEqual(tool.size_bucket(45), "small")
        self.assertEqual(tool.size_bucket(75), "medium")
        self.assertEqual(tool.size_bucket(120), "medium")
        self.assertEqual(tool.size_bucket(180), "large")
        self.assertEqual(tool.size_bucket(None), tool.NOT_MEASURED)

    def test_the_bucket_boundaries_are_the_ones_ruling_18_states(self):
        """"small under 60" makes 60 itself medium; "medium 60 to 120" makes
        120 medium and 121 large."""
        self.assertEqual(tool.size_bucket(59.9), "small")
        self.assertEqual(tool.size_bucket(60), "medium")
        self.assertEqual(tool.size_bucket(120.1), "large")

    def test_a_page_with_no_issue_lines_says_so_rather_than_printing_a_gap(self):
        page = self.page(self.measured())
        self.assertIn("No per-issue lines", page)


class TheTrialColumnShowsRuling22sMark(unittest.TestCase):
    """Ticket 39 ruling 22 marks a run's trial row VOID. Its sitting 4 put the
    mark in the merge briefing alone and named ticket 37 as the caller that
    would carry it across runs. Sitting 5 is that caller.

    It sits in the quality table beside the two model cells, because the three
    answer one question: what ran this, and may the answer be trusted."""

    def line(self, trial=None):
        found = {"batch": "batch-x", "kind": "run", "taken": "2026-09-06",
                 "version": "2.1.261"}
        if trial is not None:
            found["trial"] = trial
        return tool.render_view([found])

    def test_a_void_trial_is_named_on_the_page(self):
        drawn = self.line({"state": "void", "spawns": 4, "proved": 3,
                           "mismatches": 1})
        self.assertIn("Trial", drawn)
        self.assertIn("void", drawn)

    def test_a_holding_trial_shows_what_it_proved(self):
        """`holds` on 3 of 88 spawns and `holds` on 88 of 88 are different
        claims. Ticket 39 sitting 4 found five parentheticals that compared
        nothing and were all reported as `holds` until its reviews."""
        drawn = self.line({"state": "holds", "spawns": 88, "proved": 88,
                           "mismatches": 0})
        self.assertIn("holds 88/88", drawn)

    def test_a_line_carrying_no_trial_reads_not_measured(self):
        """Every line written before sitting 5, and ruling 3 keeps them all.
        A blank cell would read as a clean trial."""
        self.assertIn(tool.NOT_MEASURED, self.line())

    def test_an_unmeasured_trial_is_not_drawn_as_a_pass(self):
        """`batch-b5e96d` reads this, measured: it ran before the landed
        check existed."""
        drawn = self.line({"state": "unmeasured", "spawns": 0, "proved": 0,
                           "mismatches": 0})
        self.assertIn(tool.NOT_MEASURED, drawn)
        self.assertNotIn("holds", drawn)


class AValidatorNeverRaises(unittest.TestCase):
    """The `/code-review` pass of 2026-09-06. `validate_issues` calls
    `set.pop()`, which raises `KeyError` on an empty set, and both of today's
    callers happen to guard against an empty row list before calling it. A
    third caller would have crashed rather than been refused, on a road whose
    whole contract is that a measurement never halts a finale."""

    def test_no_rows_is_refused_rather_than_raised(self):
        batch, why = tool.validate_issues([])
        self.assertEqual("", batch)
        self.assertTrue(why)


if __name__ == "__main__":
    unittest.main()
