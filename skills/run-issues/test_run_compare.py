#!/usr/bin/env python3
"""Cases for run_compare.py — the reader.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 4, deliverable 4 and rulings 8, 12, 13, 14 and 24.

    python3 -m unittest test_run_compare

## The two facts sitting 2 measured, and the rules that replaced them

Sitting 2 measured that **seventeen of the eighteen lines on disk were marked
`borrowed`**, and that **every one of the eighteen read `not measured` for
ruling 6's counts**. This file held both as counts. Both counts are dead;
neither reader fault they guarded is:

  * Ticket 37 sitting 5 replayed six of the seven finale-written lines from
    their own transcripts on 2026-09-06, on the human's ruling of that day, and
    dropped the mark from five of them because their figures had stopped being
    borrowed. `per_issue` alone was stored at 1.34M to 1.87M and measured at
    4.29M to 9.98M. Twelve lines carry the mark today. What survives a replay
    is the RULE and not the count: a line whose batch id is synthetic has no
    run of its own to measure, so its five cells are always another run's.
  * That same replay wrote ruling 6's counts onto the six replayed lines, and
    `batch-207704`'s finale wrote its own on 2026-09-07.

The mark still names WHICH five fields came from another run: `issues`,
`subagents`, `weighted`, `orchestrator` and `per_issue`. A trend that reads one
of those on a marked line reports a fifteen-issue run's numbers as a two-spawn
run's, and `TheWholeRecord` now checks that against every comparison the reader
prints, rather than against the newest line alone.

So the reader's first duty is to say what it could NOT read. A trend over one
comparable line is not a trend, and a reader that prints one without saying so
is the `ok`-on-nothing fault sitting 1 met on the live register.

## Measured against the whole corpus, never one run

Ticket 39 sitting 4 measured a per-issue reader against ONE ledger, and it was
blind to seven dialects in the other fifteen. Ticket 37 sitting 3 shipped two
false-negative readings that were correct on the runs they were built against.
`TheWholeRecord` below reads every real line on disk, nineteen today, and pins
rules rather than counts wherever a count would age out of step with the file.
"""

from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_compare as tool
import run_records


def line(batch, taken, kind="run", **fields):
    """One per-run record, in the shape `run_records.append_run` writes."""
    record = {"batch": batch, "taken": taken, "kind": kind,
              "version": "2.1.261", "note": ""}
    record.update(fields)
    return record


class FinaleOrder(unittest.TestCase):
    """Ruling 12: the previous line of the SAME KIND by finale time.

    Never the row physically above it, which is what `run-costs.md`'s own
    header told a reader to use until today, and what ticket 38's concurrent
    runs break outright.
    """

    def test_lines_are_ordered_by_the_day_they_were_taken(self):
        records = [line("b", "2026-09-05"), line("a", "2026-09-02")]
        self.assertEqual([one["batch"] for _, one in tool.ordered(records)],
                         ["a", "b"])

    def test_two_lines_taken_the_same_day_keep_their_append_order(self):
        """`taken` is a DATE (`run_costs.build_record`), so two runs finishing
        on one day tie. The file is append-only and a finale appends at its
        end, so the append index IS the finale order and is what breaks the
        tie. Two lines of the corpus tie today: the pair dated 2026-08-23.
        """
        records = [line("first", "2026-09-05"), line("second", "2026-09-05")]
        self.assertEqual([one["batch"] for _, one in tool.ordered(records)],
                         ["first", "second"])

    def test_the_predecessor_is_the_previous_line_of_the_same_kind(self):
        records = [line("r1", "2026-09-01"), line("h1", "2026-09-02",
                                                  kind="hunt"),
                   line("r2", "2026-09-03")]
        found = tool.ordered(records)
        self.assertEqual(tool.previous_of_kind(found, 2)["batch"], "r1")

    def test_a_hunt_never_takes_a_run_as_its_predecessor(self):
        """Ruling 11 shares the file; ruling 12 is what keeps the two apart.
        `parallel-hunt`'s old `--no-append` existed because a hunt row among
        run rows reads as a run, and this is the rule that replaced it."""
        records = [line("r1", "2026-09-01"), line("h1", "2026-09-02",
                                                  kind="hunt")]
        found = tool.ordered(records)
        self.assertIsNone(tool.previous_of_kind(found, 1))

    def test_the_first_line_of_a_kind_has_no_predecessor(self):
        found = tool.ordered([line("only", "2026-09-01")])
        self.assertIsNone(tool.previous_of_kind(found, 0))


class TheBorrowedMark(unittest.TestCase):
    """Sitting 2's mark, and what a trend must do with it.

    `borrowed` is a LIST of the record fields that came from another run --
    `issues`, `subagents`, `weighted`, `orchestrator`, `per_issue` -- not a
    boolean. So the skip is per FIGURE, which is the only reading that is both
    honest and useful: `hours` and `idle` were the run's own on every one of
    the eighteen lines, and blanket-skipping would throw away the two figures
    the whole history can actually answer.
    """

    def test_a_figure_whose_source_field_is_marked_is_not_comparable(self):
        marked = line("a", "2026-09-01", issues=15,
                      borrowed=["issues", "subagents", "weighted",
                                "orchestrator", "per_issue"])
        ok, why = tool.comparable(marked, "issues")
        self.assertFalse(ok)
        self.assertIn("borrowed", why)

    def test_hours_stays_comparable_on_a_marked_line(self):
        """Measured by sitting 2: only five fields were ever borrowed, and
        `Hours` and `Idle` were the run's own throughout."""
        marked = line("a", "2026-09-01", hours=8.0,
                      borrowed=["issues", "subagents", "weighted",
                                "orchestrator", "per_issue"])
        self.assertEqual(tool.comparable(marked, "hours"), (True, ""))
        self.assertEqual(tool.comparable(marked, "idle"), (True, ""))

    def test_an_unmarked_line_is_comparable_on_every_figure(self):
        clean = line("a", "2026-09-06", issues=6)
        for name in tool.FIGURES:
            self.assertEqual(tool.comparable(clean, name), (True, ""))

    def test_the_mark_is_read_as_a_list_and_never_as_a_flag(self):
        """A `borrowed` naming one field must not disqualify the other four.
        Reading the mark as a boolean is the cheap error, and it would delete
        `hours` from a history that holds it."""
        partial = line("a", "2026-09-01", borrowed=["issues"])
        self.assertFalse(tool.comparable(partial, "issues")[0])
        self.assertTrue(tool.comparable(partial, "subagents")[0])


class FiguresAcrossModels(unittest.TestCase):
    """Ticket 39 sitting 3: never a single figure spanning two models.

    `weighted`, `per_issue` and `orchestrator` are `{model: value}`. A weighted
    token on one model is not the same quantity as one on another, so adding
    them makes a number with no unit. The reader compares the SAME MODEL across
    two lines, and says which models it could not pair.
    """

    def test_a_per_model_figure_is_compared_model_by_model(self):
        now = line("b", "2026-09-06", weighted={"opus": 100e6, "fable": 2e6})
        before = line("a", "2026-09-05", weighted={"opus": 80e6, "fable": 1e6})
        paired = tool.by_model(now, before, "weighted")
        self.assertEqual(sorted(paired), ["fable", "opus"])
        self.assertEqual(paired["opus"], (100e6, 80e6))

    def test_a_model_only_one_line_used_is_named_and_not_paired(self):
        now = line("b", "2026-09-06", weighted={"opus": 100e6, "fable": 2e6})
        before = line("a", "2026-09-05", weighted={"opus": 80e6})
        paired = tool.by_model(now, before, "weighted")
        self.assertEqual(sorted(paired), ["opus"])

    def test_a_per_model_figure_has_no_single_value(self):
        """The refusal ticket 39 sitting 3 built, held here so that no caller
        can quietly sum two models into one trend."""
        record = line("b", "2026-09-06", weighted={"opus": 100e6, "fable": 2e6})
        self.assertIsNone(tool.value_of(record, "weighted"))

    def test_a_scalar_figure_reads_through_its_path(self):
        record = line("b", "2026-09-06", hours=8.5,
                      faster={"idle_minutes_per_issue": 12.5},
                      quality={"issues_graded": 6, "first_attempt_passes": 5})
        self.assertEqual(tool.value_of(record, "hours"), 8.5)
        self.assertEqual(tool.value_of(record, "idle_min_per_issue"), 12.5)
        self.assertEqual(tool.value_of(record, "first_attempt_passes"), 5)

    def test_a_figure_nothing_measured_reads_none_and_never_zero(self):
        """Every one of the eighteen lines on disk reads null for all five of
        ruling 6's counts. A reader that turned that into 0 would report a run
        with no strikes, which is a different fact."""
        record = line("b", "2026-09-06",
                      quality={name: None
                               for name in run_records.QUALITY_FIELDS})
        self.assertIsNone(tool.value_of(record, "strikes"))
        self.assertIsNone(tool.value_of(record, "wall_min_per_issue"))


class DirectionAndRange(unittest.TestCase):
    """Ruling 14: one threshold only. Everything else is direction and range.

    Ruling 25 fixes what the words may be: figures, directions, and a figure
    named as outside its observed range. No cause, no advice, no alarm. The
    daily brief has carried an "invent no alarm threshold" rule since the
    borrowed rows were found -- consecutive rows swung by as much as 75 per
    cent, so a 25 per cent flag would have fired on seven of twelve
    transitions and taught them to ignore it.
    """

    def test_a_rise_reads_up_and_carries_its_size(self):
        found = tool.movement(12.0, 10.0)
        self.assertEqual(found.direction, "up")
        self.assertEqual(found.change, 2.0)
        self.assertAlmostEqual(found.percent, 20.0)

    def test_a_fall_reads_down(self):
        self.assertEqual(tool.movement(8.0, 10.0).direction, "down")

    def test_an_identical_figure_reads_level(self):
        self.assertEqual(tool.movement(10.0, 10.0).direction, "level")

    def test_a_movement_from_zero_has_no_percentage_and_still_has_a_direction(self):
        found = tool.movement(4.0, 0.0)
        self.assertEqual(found.direction, "up")
        self.assertIsNone(found.percent)

    def test_a_missing_figure_on_either_side_has_no_movement(self):
        self.assertIsNone(tool.movement(None, 10.0))
        self.assertIsNone(tool.movement(10.0, None))

    def test_no_movement_is_ever_an_alarm(self):
        """Ruling 14 allows exactly one threshold and it is not on any of
        these. A 100 per cent swing renders as a direction and a size."""
        self.assertNotIn("!", tool.render_movement("hours", tool.movement(20.0, 10.0)))

    def test_a_range_is_taken_over_comparable_measured_lines_only(self):
        records = [
            line("a", "2026-09-01", hours=10.0),
            line("b", "2026-09-02", hours=20.0),
            line("c", "2026-09-03"),                       # nothing measured
            line("d", "2026-09-04", hours=99.0, borrowed=["hours"]),
        ]
        low, high, count = tool.observed_range(records, "hours")
        self.assertEqual((low, high, count), (10.0, 20.0, 2))

    def test_a_figure_outside_the_observed_range_is_named(self):
        """Ruling 25, and it is the only judgement the reader makes about a
        figure that has no threshold."""
        records = [line(str(n), f"2026-09-0{n}", hours=10.0 + n)
                   for n in range(1, 5)]
        self.assertIn("outside", tool.range_note(records, "hours", 40.0))
        self.assertEqual(tool.range_note(records, "hours", 12.0), "")

    def test_three_readings_are_not_a_range(self):
        """`daily-brief/SKILL.md` in its own words: "two or three readings are
        not a range". The reader must not undo that by naming a figure
        "outside" one, which would be an alarm wearing a range's clothes."""
        records = [line(str(n), f"2026-09-0{n}", hours=10.0 + n)
                   for n in range(1, 4)]
        self.assertEqual(len(records), 3)
        self.assertEqual(tool.range_note(records, "hours", 40.0), "")


class TheOneThreshold(unittest.TestCase):
    """Ruling 14: the cache read-to-write ratio, and nothing else.

    **The floor is measured, not chosen.** `cache_probe.py --days 60` over the
    26 fleet sessions on this machine on 2026-09-06 read 25.9 to 78.8, median
    about 54. The alarm fires below 20 -- 23 per cent under the lowest of 26
    readings -- so it cannot fire on ordinary variance and fires only where
    the fleet has stopped reading a cache it wrote. A high ratio is the cheap
    state: a cache read costs a tenth of a write in this pipeline's weighting.
    """

    def test_a_ratio_inside_the_measured_band_raises_nothing(self):
        for ratio in (25.9, 41.7, 54.0, 78.8):
            self.assertEqual(tool.cache_alarm(ratio), "")

    def test_a_ratio_under_the_floor_raises_the_one_alarm(self):
        found = tool.cache_alarm(9.0)
        self.assertIn("9.0", found)
        self.assertIn(str(tool.CACHE_FLOOR), found)

    def test_an_unmeasured_ratio_is_not_an_alarm(self):
        """None of the eighteen lines on disk carries a cache reading. A
        reader that read that as a breach would fire on the whole history."""
        self.assertEqual(tool.cache_alarm(None), "")

    def test_the_floor_sits_below_every_reading_ever_measured(self):
        """Pins the reason rather than the number: a floor inside the observed
        band is an alarm that fires on ordinary variance, which is the fault
        the brief's 25-per-cent flag would have been."""
        self.assertLess(tool.CACHE_FLOOR, 25.9)

    def test_a_fleet_that_wrote_almost_nothing_raises_no_alarm(self):
        """Measured over all 159 sessions on this machine with a subagent
        directory: every session reading under 3 to 1 wrote under 0.45M, and
        four reading 0.00 wrote 0.07M to 0.14M on two spawns. The ratio is
        unstable at that volume, so a run that spawned almost nothing would
        fire an alarm about its cache and mean nothing by it."""
        self.assertEqual(tool.cache_alarm(0.79, written=200_218), "")
        self.assertIn("too little", tool.cache_note(0.79, written=200_218))

    def test_the_volume_floor_sits_under_every_run_shaped_session(self):
        """The alarm is applied to a RUN's line. The 26 run-shaped sessions
        `cache_probe.py --days 60` selected on 2026-09-06 all wrote well above
        this; the six large sessions reading under 20 were panel-review,
        harden-issues and bridge sessions, none of which is a run and none of
        which is ever written a line."""
        self.assertLess(tool.CACHE_VOLUME_FLOOR, 1_000_000)
        self.assertIn(str(tool.CACHE_FLOOR),
                      tool.cache_alarm(9.0, written=5_000_000))

    def test_no_other_figure_has_a_threshold(self):
        """Ruling 14 in one assertion. A second threshold added later fails
        here, which is where it should be argued."""
        self.assertEqual(tool.THRESHOLDS, {"cache_ratio": tool.CACHE_FLOOR})


class TheFourDirectionLines(unittest.TestCase):
    """Ruling 8: idle minutes per issue, first-attempt pass count, escaped
    faults, estimate ratio. Everything else stays in the view (ruling 13).
    """

    def test_there_are_exactly_four_of_them(self):
        self.assertEqual(tool.DIRECTION_LINES,
                         ("idle_min_per_issue", "first_attempt_passes",
                          "escaped_faults", "estimate_ratio"))

    def test_a_direction_line_says_not_measured_where_nothing_read_it(self):
        """Not "level", and not "0". Every one of the eighteen lines on disk
        reads null for the first-attempt count, and a reader that printed
        "level" would report a pipeline holding steady on a figure nobody has
        ever taken."""
        now = line("b", "2026-09-06",
                   quality={name: None for name in run_records.QUALITY_FIELDS})
        before = line("a", "2026-09-05",
                      quality={name: None
                               for name in run_records.QUALITY_FIELDS})
        found = tool.direction_line([now, before], now, before,
                                    "first_attempt_passes")
        self.assertIn(tool.NOT_MEASURED, found)
        self.assertNotIn("level", found)

    def test_a_direction_line_carries_the_figure_and_the_word(self):
        now = line("b", "2026-09-06", faster={"idle_minutes_per_issue": 8.0})
        before = line("a", "2026-09-05", faster={"idle_minutes_per_issue": 12.0})
        found = tool.direction_line([now, before], now, before,
                                    "idle_min_per_issue")
        self.assertIn("8", found)
        self.assertIn("down", found)

    def test_a_borrowed_figure_is_skipped_and_the_skip_is_stated(self):
        """The instruction sitting 2 left for this sitting, in one test: skip
        marked lines, and SAY you skipped them. A silent skip is the
        `ok`-on-nothing fault sitting 1 met on the live register."""
        now = line("b", "2026-09-06", issues=6)
        before = line("a", "2026-09-05", issues=15,
                      borrowed=["issues", "subagents", "weighted",
                                "orchestrator", "per_issue"])
        found = tool.compare_figure([now, before], now, before, "issues")
        self.assertIn("borrowed", found)
        self.assertNotIn("down", found)


class EscapedFaults(unittest.TestCase):
    """Ruling 8's fourth line, on sitting 1's `Origin:` key.

    The count is register rows whose `origin` cell names a run, over the rows
    a table with an `origin` column carries at all. `check_origin.graded_rows`
    is that reader and is NOT written again here: a second reader of one table
    drifts in silence, which is what `journal_for` taught ticket 39.
    """

    HEADER = ("| id | what | audience | severity | owner-notes | origin |\n"
              "|---|---|---|---|---|---|\n")

    def test_a_register_with_no_origin_column_is_not_measured(self):
        """Measured 2026-09-06: the live register declares no `origin` column
        on any table, so the honest reading today is "nothing graded" and
        never "no faults escaped"."""
        count, graded, why = tool.escaped_faults(
            "| id | what |\n|---|---|\n| rg1 | a fault |\n")
        self.assertIsNone(count)
        self.assertEqual(graded, 0)
        self.assertIn("origin", why)

    def test_rows_naming_a_run_are_counted(self):
        text = self.HEADER + (
            "| rg1 | a | b | high | c | 512/batch-45c8b1 |\n"
            "| rg2 | a | b | low | c | 530/batch-b5e96d |\n")
        count, graded, _ = tool.escaped_faults(text)
        self.assertEqual((count, graded), (2, 2))

    def test_a_row_saying_unknown_is_graded_but_not_counted(self):
        """`unknown` is legal on either half (sitting 1), and it is the
        production watcher's honest answer. It is not an escaped fault: it is
        a fault whose origin nobody could name."""
        text = self.HEADER + (
            "| rg1 | a | b | high | c | 512/batch-45c8b1 |\n"
            "| rg2 | a | b | low | c | unknown |\n"
            "| rg3 | a | b | low | c | unknown/batch-b5e96d |\n")
        count, graded, _ = tool.escaped_faults(text)
        # Only rg1 names BOTH halves. rg3 names a run and no issue, so it
        # cannot be traced to the code that shipped it, which is what ruling 7
        # asks the figure to say. Three graded, one counted.
        self.assertEqual((count, graded), (1, 3))

    def test_an_absent_register_is_not_measured_and_never_zero(self):
        count, graded, why = tool.escaped_faults("")
        self.assertIsNone(count)
        self.assertEqual(graded, 0)
        self.assertTrue(why)

    def test_it_reads_the_live_register_without_claiming_a_clean_run(self):
        """The whole-corpus half of this class. The live register is
        generated from shards and is the file a brief would open."""
        path = pathlib.Path(
            "/home/user/project/.scratch/example-feature"
            "/register.md")
        if not path.exists():
            self.skipTest(f"{path} is not on this machine")
        count, graded, why = tool.escaped_faults(
            path.read_text(encoding="utf-8", errors="replace"))
        if graded == 0:
            self.assertIsNone(count)
            self.assertTrue(why)
        else:
            self.assertIsNotNone(count)


class TheFiveSubcommands(unittest.TestCase):
    """Ruling 24: `last`, `show <batch-id>`, `since <days>`, `compare <a> <b>`,
    `versions`. Fixed subcommands, so the script is the fact and the skill
    above it only reads the output."""

    def setUp(self):
        self.records = [
            line("a", "2026-09-01", hours=10.0, issues=4,
                 faster={"idle_minutes_per_issue": 12.0,
                         "estimate_median_ratio": 1.4},
                 quality={"issues_graded": 4, "first_attempt_passes": 3,
                          "correction_rounds": 1, "strikes": 0,
                          "escalations": 0}),
            line("h", "2026-09-02", kind="hunt", hours=3.0),
            line("b", "2026-09-03", hours=8.0, issues=6,
                 faster={"idle_minutes_per_issue": 9.0,
                         "estimate_median_ratio": 1.1},
                 quality={"issues_graded": 6, "first_attempt_passes": 5,
                          "correction_rounds": 1, "strikes": 1,
                          "escalations": 0}),
        ]

    def test_there_are_exactly_five(self):
        self.assertEqual(sorted(tool.SUBCOMMANDS),
                         ["compare", "last", "show", "since", "versions"])

    def test_last_reports_the_newest_line_of_each_kind(self):
        found = tool.render_last(self.records, register_text="")
        self.assertIn("`b`", found)
        self.assertIn("`h`", found)

    def test_last_compares_the_newest_run_against_the_previous_run(self):
        """Not against the hunt, which is the row physically above it."""
        found = tool.render_last(self.records, register_text="")
        self.assertIn("against `a`", found)
        self.assertNotIn("against `h`", found)

    def test_last_carries_all_four_direction_lines(self):
        found = tool.render_last(self.records, register_text="")
        self.assertIn("idle minutes per issue", found)
        self.assertIn("first-attempt gate passes", found)
        self.assertIn("escaped faults", found)
        self.assertIn("estimate median ratio", found)

    def test_last_names_the_view_as_the_one_look_page(self):
        """Ruling 13. The reader points at the page; it does not reprint it."""
        self.assertIn(run_records.VIEW,
                      tool.render_last(self.records, register_text=""))

    def test_show_names_a_line_that_is_not_there(self):
        found = tool.render_show(self.records, "nope")
        self.assertIn("nope", found)
        self.assertIn("no line", found.lower())

    def test_show_reads_one_line_against_its_own_predecessor(self):
        found = tool.render_show(self.records, "b")
        self.assertIn("against `a`", found)

    def test_since_takes_a_window_in_days_and_says_what_it_covered(self):
        found = tool.render_since(self.records, 3, today="2026-09-03")
        self.assertIn("`b`", found)
        self.assertNotIn("| `a`", found)

    def test_since_with_nothing_in_the_window_says_so(self):
        found = tool.render_since(self.records, 1, today="2026-10-01")
        self.assertIn("no line", found.lower())

    def test_compare_refuses_two_lines_of_different_kinds(self):
        """Ruling 12 is the rule, and naming two lines by hand is the one road
        that could walk around it. A run against a hunt is not a comparison."""
        found = tool.render_compare(self.records, "a", "h")
        self.assertIn("REFUSED", found)
        self.assertIn("kind", found.lower())
        self.assertIn("run", found)
        self.assertIn("hunt", found)

    def test_compare_reads_two_named_lines_of_one_kind(self):
        found = tool.render_compare(self.records, "a", "b")
        self.assertIn("wall clock", found)

    def test_compare_names_a_line_that_is_not_there(self):
        self.assertIn("REFUSED", tool.render_compare(self.records, "a", "nope"))

    def test_versions_groups_lines_that_ran_the_same_pipeline(self):
        marked = [
            line("a", "2026-09-01", fingerprint={
                "skills": {"head": "aaaaaaa", "dirty": False},
                "agents": {"head": "bbbbbbb", "dirty": False},
                "hooks": {"head": "ccccccc", "dirty": False}}),
            line("b", "2026-09-02", fingerprint={
                "skills": {"head": "aaaaaaa", "dirty": False},
                "agents": {"head": "bbbbbbb", "dirty": False},
                "hooks": {"head": "ccccccc", "dirty": False}}),
            line("c", "2026-09-03", fingerprint={
                "skills": {"head": "ddddddd", "dirty": False},
                "agents": {"head": "bbbbbbb", "dirty": False},
                "hooks": {"head": "ccccccc", "dirty": False}}),
        ]
        groups = tool.fingerprint_groups(marked)
        self.assertEqual(len(groups), 2)
        self.assertEqual([one["batch"] for one in groups[0].records], ["a", "b"])

    def test_versions_prints_the_commits_between_two_groups(self):
        """The subjects come from the three repositories, and the log reader
        is injected so this can be measured without them."""
        marked = [
            line("a", "2026-09-01", fingerprint={
                "skills": {"head": "aaaaaaa", "dirty": False}}),
            line("b", "2026-09-02", fingerprint={
                "skills": {"head": "ddddddd", "dirty": False}}),
        ]
        asked = []

        def log(name, first, second):
            asked.append((name, first, second))
            return ["1111111 a skill change"]

        found = tool.render_versions(marked, log=log)
        self.assertIn("a skill change", found)
        self.assertIn(("skills", "aaaaaaa", "ddddddd"), asked)

    def test_versions_says_so_when_no_line_carries_a_fingerprint(self):
        """Measured 2026-09-06: all eighteen lines on disk read `{}`, because
        ruling 23's header landed in sitting 2 and no finale has run since. A
        reader that printed one empty group would be claiming every run was
        the same pipeline."""
        found = tool.render_versions(
            [line("a", "2026-09-01"), line("b", "2026-09-02")], log=None)
        self.assertIn(tool.NOT_MEASURED, found)


class TheCommandLine(unittest.TestCase):
    """`main` never raises and never writes.

    `finale.md` and `daily-brief/SKILL.md` both run this, and a reader that
    threw in the middle of a brief would cost the brief rather than the
    figure.
    """

    def test_no_subcommand_prints_the_five_and_exits_two(self):
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = tool.main([])
        self.assertEqual(code, 2)

    def test_a_missing_records_file_is_a_reading_not_a_crash(self):
        import io, contextlib, tempfile
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as empty:
            with contextlib.redirect_stdout(out):
                code = tool.main(["last", "--repo", empty])
        self.assertEqual(code, 0)
        self.assertIn("No lines", out.getvalue())

    def test_it_writes_nothing(self):
        """The reader reads. `run_costs.py` at a finale is the only writer of
        these files and `run_records.write_view` the only writer of the page."""
        import io, contextlib, tempfile, os
        with tempfile.TemporaryDirectory() as empty:
            audit = pathlib.Path(empty) / run_records.WORKFLOW_AUDIT
            audit.mkdir(parents=True)
            (audit / "runs.jsonl").write_text(
                '{"batch": "a", "kind": "run", "taken": "2026-09-01"}\n')
            before = sorted(os.listdir(audit))
            with contextlib.redirect_stdout(io.StringIO()):
                for argv in (["last"], ["show", "a"], ["since", "7"],
                             ["versions"], ["compare", "a", "a"]):
                    tool.main(argv + ["--repo", empty])
            self.assertEqual(sorted(os.listdir(audit)), before)


RECORDS = pathlib.Path(
    "/home/user/project/.scratch/workflow-audit/runs.jsonl")


class TheWholeRecord(unittest.TestCase):
    """Every line on disk, not the one the reader was built against.

    Ticket 39 sitting 4 measured a per-issue reader against ONE ledger and was
    blind to seven dialects in the other fifteen. Ticket 37 sitting 3 shipped
    two false-negative readings that were right on the runs behind them, and
    only a count across all seventeen ledgers found either. This class is the
    net for this reader.
    """

    def setUp(self):
        if not RECORDS.exists():
            self.skipTest(f"{RECORDS} is not on this machine")
        self.records = run_records.read_lines(RECORDS).records

    def test_the_record_is_big_enough_to_be_a_net(self):
        """Measured 2026-09-07: nineteen lines. Eighteen stood on 2026-09-06,
        nineteen rows carried in with the duplicate `review-375cbf` deleted
        once by hand, and `batch-207704`'s finale wrote the nineteenth."""
        self.assertGreaterEqual(len(self.records), 19)

    def test_the_mark_follows_the_synthetic_id_and_nothing_else(self):
        """The rule that replaced sitting 2's count of seventeen.

        This test read `>= 17 marked` and broke on 2026-09-06, when ticket 37
        sitting 5's replay measured five of those lines from their own
        transcripts and dropped the mark. The record was right and the count
        was stale: `per_issue` on those five was stored at 1.34M to 1.87M and
        measured at 4.29M to 9.98M, so the stored cells really were another
        run's and really did stop being so.

        A count cannot survive a replay. The rule can, because it is derived
        from each line rather than typed: a line carrying `batch_synthetic`
        has no run of its own to measure, so its five cells are always
        borrowed, and a line naming a real batch must never carry the mark.
        That is the whole reason the mark exists, and it fails loudly both
        ways -- a writer that drops the mark from a synthetic line, and one
        that stamps it on a real run.

        Measured 2026-09-07: nineteen lines, twelve synthetic and all twelve
        marked, seven real and none marked.
        """
        marked, plain = [], []
        for one in self.records:
            (marked if one.get("borrowed") else plain).append(one)
            self.assertEqual(
                bool(one.get("batch_synthetic")), bool(one.get("borrowed")),
                f"`{one.get('batch')}` carries batch_synthetic "
                f"{one.get('batch_synthetic')!r} and borrowed "
                f"{one.get('borrowed')!r}. One of the two is wrong.")
        # Neither side may empty out. An all-marked or an all-plain file would
        # satisfy the loop above and prove nothing about the reader.
        self.assertTrue(marked, "no line is marked; the skip is untested")
        self.assertTrue(plain, "every line is marked; no trend is testable")
        for one in marked:
            self.assertEqual(
                sorted(one["borrowed"]), sorted(tool.BORROWABLE),
                f"`{one.get('batch')}` is marked on a subset of the five. "
                "The mark has one historical cause and covers all five cells.")

    def test_ruling_sixs_counts_arrive_with_a_real_run_and_never_otherwise(self):
        """The second fact sitting 2 measured, and the day it changed.

        This test read `graded == []` and its own docstring named itself the
        place to record the day a finale wrote one. That day came twice:
        ticket 37 sitting 5's replay wrote the counts onto the six replayable
        lines on 2026-09-06, and `batch-207704`'s finale wrote its own on
        2026-09-07. The empty assertion is retired.

        The rule that replaces it holds on both sides. A synthetic line has no
        run behind it to grade, so it can never hold one of these counts. A
        line naming a real batch must hold `issues_graded`, and that count is
        the issues SCOPED, so it can never read below the issues shipped --
        `batch-88624c` scoped ten and shipped eight.
        """
        for one in self.records:
            quality = one.get("quality") or {}
            if one.get("batch_synthetic"):
                self.assertEqual(
                    [], [key for key, value in sorted(quality.items())
                         if value is not None],
                    f"`{one.get('batch')}` is synthetic and holds a count "
                    "there is no run to have measured.")
                continue
            graded = quality.get("issues_graded")
            self.assertIsNotNone(
                graded, f"`{one.get('batch')}` names a real batch and states "
                        "no issues_graded.")
            self.assertGreaterEqual(
                graded, one.get("issues") or 0,
                f"`{one.get('batch')}` graded {graded} and shipped "
                f"{one.get('issues')}. Scoped can never be below shipped.")

    def test_every_headline_figure_is_skipped_or_read_on_every_line(self):
        """The property a narrowed reader breaks first: every figure on every
        real line either reads a number, reads None, or is skipped with the
        mark named. Nothing raises and nothing returns a shape a caller cannot
        use."""
        for record in self.records:
            for name in tool.HEADLINE + tool.PER_MODEL:
                ok, why = tool.comparable(record, name)
                if not ok:
                    self.assertIn("borrowed", why)
                    continue
                value = tool.value_of(record, name)
                self.assertTrue(value is None or isinstance(value, (int, float)),
                                f"{record.get('batch')}/{name} read {value!r}")

    def test_hours_is_comparable_on_every_line_that_holds_it(self):
        """The measurement that decided the skip is per FIGURE and not per
        line: `Hours` and `Idle` were the run's own on all eighteen. A
        blanket skip would throw away the only figure this history can
        answer."""
        holding = [one for one in self.records
                   if tool.value_of(one, "hours") is not None]
        self.assertGreaterEqual(len(holding), 6)
        for one in holding:
            self.assertTrue(tool.comparable(one, "hours")[0])

    def test_no_line_is_marked_borrowed_on_hours_or_idle(self):
        for one in self.records:
            for name in ("hours", "idle"):
                self.assertTrue(tool.comparable(one, name)[0],
                                f"{one.get('batch')} marked on {name}")

    def test_the_real_record_renders_every_subcommand_without_raising(self):
        register = pathlib.Path(
            "/home/user/project/.scratch/example-feature"
            "/register.md")
        text = register.read_text(encoding="utf-8", errors="replace") \
            if register.exists() else ""
        for found in (tool.render_last(self.records, text),
                      tool.render_since(self.records, 30,
                                        today="2026-09-06",
                                        register_text=text),
                      tool.render_versions(self.records, log=None)):
            self.assertTrue(found.strip())
        for one in self.records:
            self.assertTrue(
                tool.render_show(self.records, one["batch"], text).strip())

    def test_no_figure_the_reader_prints_is_compared_across_a_marked_line(self):
        """The corpus test that matters, widened from one line to all of them.

        It used to render the newest line alone and check two figures, resting
        on "the newest run has a predecessor marked `borrowed`". Ticket 37
        sitting 5's replay dropped the mark from those predecessors, and the
        newest comparison became legitimate -- so the test failed on a reading
        that was correct. It had been checking one accident of the history
        rather than the property.

        The property is this: wherever the reader prints "against `X`", the
        line X must be comparable on that very figure. This walks every line
        on disk and every headline figure, resolves the predecessor the reader
        named, and asks `comparable` about it. Measured 2026-09-07: 44
        comparisons checked across nineteen lines, where the old shape checked
        two figures on one. A reader that stopped honouring the mark raises 24
        of them, so this is a net and not a formality.
        """
        by_batch = {str(one.get("batch") or ""): one for one in self.records}
        checked = 0
        for one in self.records:
            text = tool.render_show(self.records, one["batch"],
                                    register_text="")
            for name in tool.HEADLINE:
                label = tool.FIGURES[name].label
                for row in text.splitlines():
                    if not row.startswith(f"- {label}:"):
                        continue
                    found = re.search(r"against `([^`]+)`", row)
                    if not found:
                        continue
                    checked += 1
                    before = by_batch.get(found.group(1))
                    self.assertIsNotNone(
                        before, f"`{one['batch']}` was compared against "
                                f"`{found.group(1)}`, which is not on file: "
                                f"{row}")
                    ok, why = tool.comparable(before, name)
                    self.assertTrue(
                        ok, f"{label} was compared across a marked line "
                            f"on `{one['batch']}`: {row} — {why}")
        self.assertGreaterEqual(checked, 40)

    def test_a_marked_line_still_states_its_skip_in_words(self):
        """The other half of the same duty. Honouring the mark silently would
        pass the test above and leave the reader printing a figure with no
        movement and no reason, which is the `ok`-on-nothing fault sitting 1
        met on the live register."""
        marked = [one for one in self.records if one.get("borrowed")]
        self.assertTrue(marked, "no marked line is on file to render")
        for one in marked:
            text = tool.render_show(self.records, one["batch"],
                                    register_text="")
            self.assertIn("borrowed", text,
                          f"`{one['batch']}` is marked and its block never "
                          "says so.")

    def test_the_real_record_raises_no_cache_alarm_it_cannot_support(self):
        """No line carries a cache reading yet, so ruling 14's one threshold
        must stay silent rather than firing on the whole history."""
        for one in self.records:
            self.assertEqual(tool.cache_alarm(tool.value_of(one, "cache_ratio")),
                             "")


class HowAFigureReads(unittest.TestCase):
    """Found by rendering the eighteen real lines, not by a fixture.

    Every one of these printed something a person would have to decode, and
    the generated view already renders the same quantities properly. A reader
    whose units disagree with the page it points at is two readings of one
    figure.
    """

    def test_weighted_tokens_read_in_millions_and_never_in_exponents(self):
        """`51.9M`, not `5.19e+07`. `run_records.render_view` has rendered
        this column in millions since 2026-09-06."""
        record = line("a", "2026-09-06", weighted={"opus": 51_900_000.0})
        found = tool.render_last([record], register_text="")
        self.assertIn("51.9M", found)
        self.assertNotIn("e+07", found)

    def test_a_share_reads_as_a_percentage(self):
        """`23%`, not `0.23 share`. The view's `Idle` and `Orchestrator`
        columns are both percentages."""
        record = line("a", "2026-09-06", idle=0.23,
                      orchestrator={"opus": 0.13})
        found = tool.render_last([record], register_text="")
        self.assertIn("23%", found)
        self.assertIn("13%", found)
        self.assertNotIn("0.23", found)

    def test_a_share_that_moved_reads_in_points_and_not_in_per_cent_of_itself(self):
        """0.10 to 0.23 is thirteen POINTS. Rendering it as "up 130%" invites
        the reader to think idle time more than doubled as a share of the run,
        which is a different and larger-sounding claim."""
        records = [line("a", "2026-09-05", idle=0.10),
                   line("b", "2026-09-06", idle=0.23)]
        found = tool.render_last(records, register_text="")
        self.assertIn("13 points", found)
        self.assertNotIn("130%", found)

    def test_an_unmeasured_figure_does_not_say_it_twice(self):
        records = [line("a", "2026-09-05"), line("b", "2026-09-06")]
        found = tool.render_last(records, register_text="")
        self.assertNotIn(f"{tool.NOT_MEASURED} — {tool.NOT_MEASURED}", found)

    def test_last_says_which_kinds_have_no_line_at_all(self):
        """Measured: the record holds eighteen runs and no hunt. A heading
        reading "the last line of each kind" that silently prints one kind
        says the other has nothing to report, which nobody measured."""
        found = tool.render_last([line("a", "2026-09-06")], register_text="")
        self.assertIn("hunt", found)


class WhatTheReviewFound(unittest.TestCase):
    """Eight faults from the `/code-review` pass of 2026-09-06, each pinned.

    Every one was confirmed by RUNNING it, not by reading the code, and the
    first is this sitting committing the fault the whole ticket exists to end:
    a reader that reports figures which are not the ones it was asked for.
    """

    def repo_with(self, *records):
        import json, tempfile
        room = tempfile.TemporaryDirectory()
        self.addCleanup(room.cleanup)
        audit = pathlib.Path(room.name) / run_records.WORKFLOW_AUDIT
        audit.mkdir(parents=True)
        (audit / "runs.jsonl").write_text(
            "".join(json.dumps(one) + "\n" for one in records))
        return room.name

    def run_main(self, argv):
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(argv)
        return code, out.getvalue()

    def test_repo_is_honoured_before_the_subcommand(self):
        """The worst of the eight. `--repo X last` read the WORKING DIRECTORY,
        because the subparser's own empty default overwrote the top-level
        value -- so the reader silently answered about a different repository,
        which is the borrowed-figure fault it was built to expose."""
        room = self.repo_with(
            {"batch": "zzz", "kind": "run", "taken": "2026-09-01"})
        _, before = self.run_main(["--repo", room, "last"])
        _, after = self.run_main(["last", "--repo", room])
        self.assertIn("zzz", before)
        self.assertIn("zzz", after)

    def test_a_window_too_large_for_a_date_is_a_refusal_not_a_crash(self):
        """`timedelta` raises OverflowError, not ValueError. The brief runs
        this mid-section and a mistyped window must cost the figure, never the
        brief."""
        found = tool.render_since([line("a", "2026-09-01")], 10 ** 12,
                                  today="2026-09-06")
        self.assertTrue(found.strip())
        room = self.repo_with(
            {"batch": "a", "kind": "run", "taken": "2026-09-01"})
        code, _ = self.run_main(["since", str(10 ** 12), "--repo", room])
        self.assertEqual(code, 0)

    def test_a_line_with_an_unreadable_date_is_in_no_window(self):
        """String comparison put `not stated` above every real date, so such a
        line was inside EVERY window however short -- a run from three weeks
        ago reported as yesterday's. It gets no block; it is NAMED instead,
        which the next test pins."""
        records = [line("good", "2026-09-06"), line("bad", "not stated")]
        found = tool.render_since(records, 1, today="2026-09-06")
        self.assertIn("## `good`", found)
        self.assertNotIn("## `bad`", found)

    def test_a_line_with_an_unreadable_date_is_named_rather_than_dropped(self):
        """Dropping it silently would be the same fault the other way round."""
        records = [line("good", "2026-09-06"), line("bad", "not stated")]
        found = tool.render_since(records, 1, today="2026-09-06")
        self.assertIn("bad", found)

    def test_compare_gives_one_answer_whichever_order_is_typed(self):
        """Two lines taken the same day were ordered by which was NAMED
        first, so the pair had two opposite answers and nothing said which was
        backwards. `ordered()` already breaks the tie by append index."""
        records = [line("first", "2026-09-05", hours=10.0),
                   line("second", "2026-09-05", hours=20.0)]
        one = tool.render_compare(records, "first", "second").splitlines()[0]
        two = tool.render_compare(records, "second", "first").splitlines()[0]
        self.assertEqual(one, two)
        self.assertIn("`second` against `first`", one)

    def test_the_window_selects_by_position_and_not_by_content(self):
        """Two lines edited to identical content were indistinguishable, so
        the window took or left both together. `runs.jsonl` is hand-editable
        by `run_records`' own instruction, so identical lines are reachable."""
        same = dict(taken="2026-09-06", kind="run", batch="a")
        records = [dict(same), dict(same)]
        found = tool.render_since(records, 1, today="2026-09-06")
        self.assertEqual(found.count("## `a`"), 2)

    def test_an_unreadable_borrowed_mark_suppresses_every_marked_figure(self):
        """A string mark did SUBSTRING matching, so it was half-honoured in
        silence. An unreadable mark means every markable figure is suspect,
        which is what the bool branch already said."""
        record = line("x", "2026-09-01", borrowed="issues,subagents")
        for name in tool.BORROWABLE:
            self.assertFalse(tool.comparable(record, name)[0], name)
        # And only those. The mark has one historical cause and sitting 2
        # measured which five cells it covers; widening an unreadable mark to
        # `hours` would delete the figure this history can answer.
        for name in ("hours", "idle"):
            self.assertTrue(tool.comparable(record, name)[0], name)

    def test_a_register_that_was_never_opened_says_so(self):
        """`escaped_faults("")` claimed the register's tables declare no
        `origin` column, which is a statement about a file nobody read."""
        count, graded, why = tool.escaped_faults(None)
        self.assertIsNone(count)
        self.assertEqual(graded, 0)
        self.assertIn("no register", why.lower())
        self.assertNotIn("declares an `origin` column", why)

    def test_the_register_is_parsed_once_per_invocation(self):
        """It was walked once per rendered block: eighteen times for `since
        60` over the lines on file. The figure is one reading of one file."""
        seen = []
        real = tool.escaped_faults

        def counting(text):
            seen.append(1)
            return real(text)

        records = [line(str(n), f"2026-09-0{n}") for n in range(1, 6)]
        try:
            tool.escaped_faults = counting
            tool.render_since(records, 30, today="2026-09-06",
                              register_text="| id | origin |\n|---|---|\n")
        finally:
            tool.escaped_faults = real
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
