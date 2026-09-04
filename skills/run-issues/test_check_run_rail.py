#!/usr/bin/env python3
"""Tests for check_run_rail.py. Run: python3 test_check_run_rail.py

Issue 552. Picture D draws a run as a rail of stages with one card per shipped
issue, and deciding where a card lands, what kind it is and what it says is
judgement. `finale.md` step 5 forbids the renderer any: "The panel transcribes.
It never counts." So the judgement moves upstream into `## The run on the rail`
in the merge briefing, written by the finale, and this guard refuses a block the
renderer could not transcribe.

Every fixture is an inline string. This file lives in the skills repository and
cannot read a briefing in a project repository; the named-run fixtures
say which real briefing they are cut from so a reader can go and check.
`STAGES` is the vocabulary table as `docs/agents/run-picture-stages.md` holds
it on 2026-09-04.

It grades keys, counts and lengths. It catches nothing about whether a sentence
is true or a stage is the right one. That is the stated limit, not an oversight.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

import check_run_picture
import check_run_rail as guard

# The table from `docs/agents/run-picture-stages.md` in the project it was
# written for, as it stood when this guard was written. Header, keys and sources
# are verbatim; five `Sentence` cells are shortened, and the guard reads keys only.
STAGES = """# Run picture stages

| Key | Column | Source | Sentence |
|---|---|---|---|
| `workspace` | Workspace | invented here | The walk starts with a workspace. |
| `tender` | Create a tender | MAP journey 1 | Create a tender. |
| `quote` | Invite and quote | MAP journey 2 | Invite suppliers, and receive a quote. |
| `award` | Compare and award | MAP journey 3 | Compare quotes and award one. |
| `quotation` | Customer quotation | MAP journey 4 | Build and send the customer quotation. |
| `needs-you` | Needs-you queue | MAP journey 5 | Work the "Needs you" queue on `/app`. |
| `zoho` | Zoho push and read | MAP journey 6 | Push the result to Zoho Books. |
| `catalogue` | Catalogue | MAP journey 7 | The catalogue. |
| `floor` | Under the floor | invented here | Anything no user sees. |

## The four rules
"""

# The head of run `batch-45c8b1`'s archived merge briefing,
# verbatim, up to the point where the rail goes. The real file follows the
# one-screen block with prose and then a SECOND `## The run in one screen`, the
# unfilled template stub, which is why every reader anchors on the first.
ONE_SCREEN = """# Merge briefing — batch-45c8b1

## The run in one screen

Run `batch-45c8b1`, 16 issues, 17.79 h. ~~Nothing is merged and nothing is deployed.~~
**Merged and pushed on 2026-09-02. The stamp is directly below.**

Branch `claude/run-issues-batch-45c8b1`, head **`7604316d`**, 19 commits, cut from main at
`9ca53765`. **The working tree is clean.**

| What                | Count | Detail lives at             |
|---------------------|-------|-----------------------------|
| Shipped, unmerged   |    16 | ## What shipped, per issue  |
| Did NOT ship        |     0 | ## Skipped, blocked, or shipped unstamped |
| Migrations minted   |     7 | ## Migrations, and the order they are pasted |
| Issues minted       |     3 | ## Promotion                |
| Register rows left  |     0 | ## Promotion                |
| Waiting on you      |    10 | ## What waits on the human  |
| Forks to decide     |     6 | ## Decide                   |
| Wall clock, hours   | 17.79 | ## What this run cost       |
| Idle, per cent      |    15 | ## What this run cost       |

Shipped:      485b, 486, 487, 488, 489, 485, 519, 518, 516, 517a, 517, 521, 520a, 520b, 503, 406
Did not ship: none - every issue in the batch reached `done`
Minted:       522, 523, 524
Register:     64 row lines resolved - 3 promoted, 13 fixed, 42 refused, 6 dropped. None left.
Waiting:      7 migration pastes (0110-0116, BEFORE the push, in numeric order), 1 button press
              on /app/zoho AFTER the deploy, 2 skill edits under ~/.claude/skills/

**The one sentence that must not be softened.** The database now refuses a viewer's DIRECT
write across every table this batch touched. **The `security definer` money road is still open**
— a viewer calling `issue_purchase_order` or `generate_quotation` still succeeds, driven on QA.
You ruled on 2026-09-01 that issue **509** closes it after you walk this batch.

"""

# The rail this issue would have written for that run. Stages and kinds are
# read off the drawing script's `r45c8b1` spec; the
# seven band chips take a stage inside their band's span, never `floor`, and
# `Lit:` does not name `catalogue` because 485 is a chip and not a card.
RAIL = """## The run on the rail

Headline: The database now refuses a viewer's direct write on every table this batch
touched. The money road is still open.
Lit: workspace, quotation, needs-you, zoho

| Issue | Stage     | Kind    | Sentence                                             |
|-------|-----------|---------|------------------------------------------------------|
| 485b  | catalogue | harness | Catalogue guards now truly run                       |
| 486   | quotation | guard   | Customer tables refuse a viewer's write              |
| 487   | quote     | guard   | Supplier and invite tables refuse a viewer's write   |
| 488   | award     | guard   | Deal and money tables refuse a viewer's direct write |
| 489   | workspace | guard   | Workspace and ops tables refuse a viewer's write     |
| 485   | catalogue | guard   | Catalogue tables refuse a viewer's write             |
| 519   | workspace | fix     | The four seat readers agree, and so does the type    |
| 518   | zoho      | guard   | Import asks the seat before it touches Zoho          |
| 516   | needs-you | new     | Admin is told a customer waits to be verified        |
| 517a  | workspace | guard   | Database keeps the last admin in place               |
| 517   | workspace | new     | Admin adds a person and changes a seat               |
| 521   | quotation | fix     | Price relink runs on the way out, not only at the end |
| 520a  | quotation | new     | Options become a table                               |
| 520b  | quotation | new     | Member sees the supplier's past price                |
| 503   | floor     | fix     | Citation checker refuses without a clean bill        |
| 406   | floor     | guard   | A new bare line-number citation is refused           |

"""

# Issue 554's two tables, quoted from that issue file. 522 and 523 did not ship.
MINTED_AND_FORKS = """### Minted and left open

| Issue | Stage      | Sentence                                  |
|-------|------------|-------------------------------------------|
| 522   | quotation  | A failed price read shows as 'no price'   |
| 523   | quotation  | An unread price pool calls itself whole   |

### Forks waiting on you

| Fork | Stage      | Question                                          |
|------|------------|---------------------------------------------------|
| F1   | workspace  | Tell the admin an email belongs to another space?  |
| F4   | floor      | Refuse an untracked paste file?                    |

"""

# Issue 555's table, quoted from that issue file.
BANDS = """### Bands

| Band | Stages                    | Issues                          | Caption                                |
|------|---------------------------|---------------------------------|----------------------------------------|
| B1   | workspace..catalogue      | 486 487 488 489 485 485b 519    | Viewer, on every screen, can no longer write |

"""

# The rest of the real briefing, from the template stub onward.
REST = """
Branch `claude/run-issues-batch-45c8b1`, cut from `main` at `9ca53765`.
Session model: **claude-opus-5**. Session effort: **high**.

## The run in one screen
*(written at the finale)*

## What shipped, per issue
**All sixteen shipped. One section each, below, in the order they were built:** 485b, 486, 487,
488, 489, 485 (the five-slice migrate family plus its test half), 519, 518, 516, 517a, 517, 521,
520a, 520b, 503, 406.
"""

BRIEFING = ONE_SCREEN + RAIL + REST


def refusals(briefing, stages=STAGES):
    vocabulary = guard.read_stages(stages) if stages is not None else None
    return guard.check(briefing, vocabulary).refusals


def reasons(found):
    return [r.split(":")[0] for r in found]


class TheRealShapePasses(unittest.TestCase):
    """Run `batch-45c8b1`'s own briefing with the rail this issue would have
    written for it."""

    def test_no_refusal(self):
        self.assertEqual(refusals(BRIEFING), [])

    def test_the_vocabulary_reads_nine_keys(self):
        keys = guard.read_stages(STAGES)
        self.assertEqual(len(keys), 9)
        self.assertIn("needs-you", keys)
        self.assertIn("floor", keys)

    def test_a_vocabulary_with_no_table_reads_as_none(self):
        self.assertIsNone(guard.read_stages("# nothing here\n\nprose only\n"))


class AStageOutsideTheVocabularyIsRefused(unittest.TestCase):
    """The fault the check exists for: a stage word that drifted. `warehouse`
    is not one of the nine."""

    def test_the_bad_key_is_named(self):
        bad = BRIEFING.replace("| 516   | needs-you |", "| 516   | warehouse |")
        found = refusals(bad)
        self.assertEqual(reasons(found), ["bad-stage"])
        self.assertIn("warehouse", found[0])
        self.assertIn("516", found[0])

    def test_a_missing_vocabulary_skips_the_stage_rule_and_carries_on(self):
        """Rule 4 of run-picture-stages.md. `/run-issues` runs on repositories
        with no such file, and a guard that exits 1 there stops every finale."""
        bad = BRIEFING.replace("| 516   | needs-you |", "| 516   | warehouse |")
        self.assertEqual(refusals(bad, stages=None), [])
        # Everything else is still graded without the vocabulary.
        worse = bad.replace("| new     | Admin is told", "| invisible | Admin is told")
        self.assertEqual(reasons(refusals(worse, stages=None)), ["bad-kind"])


class AKindOutsideTheFourIsRefused(unittest.TestCase):
    """`invisible` is the word ticket 34's second sitting used before Picture D
    settled on `harness`."""

    def test_the_bad_kind_is_named(self):
        bad = BRIEFING.replace("| 406   | floor     | guard   |", "| 406   | floor     | invisible |")
        found = refusals(bad)
        self.assertEqual(reasons(found), ["bad-kind"])
        self.assertIn("invisible", found[0])
        self.assertIn("406", found[0])

    def test_the_two_columns_are_never_derived_from_each_other(self):
        """`harness` is a kind and `floor` is a stage. A `harness` row on the
        rail and a `fix` row under the floor are both legal, and the real
        fixture carries both: 485b is `catalogue | harness`, 503 is `floor | fix`."""
        self.assertEqual(refusals(BRIEFING), [])


class ASentenceOfSixtyOrMoreIsRefused(unittest.TestCase):
    """The bound is `59 characters or fewer`. Issue 551's field carries the
    same words, so the two cannot disagree at 60."""

    # Each ends in a letter, because the check measures the cell stripped and a
    # slice ending in a space would measure one short.
    BASE = "A sentence that runs on past the bound of any rail card and keeps going well past it"
    LONG = BASE[:71] + "x"
    SHORT = BASE[:58] + "x"

    def test_a_72_character_sentence_is_refused_and_the_length_printed(self):
        self.assertEqual(len(self.LONG), 72)
        bad = BRIEFING.replace(
            "Admin adds a person and changes a seat               ", self.LONG
        )
        found = refusals(bad)
        self.assertEqual(reasons(found), ["sentence-too-long"])
        self.assertIn("72", found[0])
        self.assertIn("517", found[0])

    def test_a_59_character_sentence_passes(self):
        self.assertEqual(len(self.SHORT), 59)
        ok = BRIEFING.replace(
            "Admin adds a person and changes a seat               ", self.SHORT
        )
        self.assertEqual(refusals(ok), [])

    def test_exactly_60_is_refused(self):
        sixty = self.BASE[:59] + "x"
        self.assertEqual(len(sixty), 60)
        bad = BRIEFING.replace("Admin adds a person and changes a seat               ", sixty)
        self.assertEqual(reasons(refusals(bad)), ["sentence-too-long"])


class EveryShippedIssueHasExactlyOneRow(unittest.TestCase):
    """The shipped list is the one-screen block's `Shipped:` line, compared
    against the shipped table's `Issue` column in both directions."""

    def test_a_shipped_issue_with_no_row_is_named(self):
        bad = BRIEFING.replace(
            "| 503   | floor     | fix     | Citation checker refuses without a clean bill        |\n",
            "",
        )
        found = refusals(bad)
        self.assertEqual(reasons(found), ["no-row"])
        self.assertIn("503", found[0])

    def test_a_row_for_an_issue_that_did_not_ship_is_named(self):
        bad = BRIEFING.replace(
            "| 406   | floor     | guard   |",
            "| 406   | floor     | guard   | A new bare line-number citation is refused |\n"
            "| 999   | floor     | guard   |",
        )
        found = refusals(bad)
        self.assertEqual(reasons(found), ["not-shipped"])
        self.assertIn("999", found[0])

    def test_an_issue_with_two_rows_is_refused(self):
        row = "| 516   | needs-you | new     | Admin is told a customer waits to be verified        |\n"
        bad = BRIEFING.replace(row, row + row)
        found = refusals(bad)
        self.assertEqual(reasons(found), ["duplicate-row"])
        self.assertIn("516", found[0])

    def test_the_list_is_not_read_from_what_shipped(self):
        """`## What shipped, per issue` names the same sixteen in prose. Delete
        it and nothing changes, because the `Shipped:` line is the source."""
        # The heading, not the one-screen table cell that names it.
        without = BRIEFING[: BRIEFING.index("\n## What shipped, per issue")]
        self.assertEqual(refusals(without), [])

    def test_a_missing_shipped_line_is_an_exit_two_refusal(self):
        bad = BRIEFING.replace("Shipped:      485b", "Delivered:    485b")
        found = refusals(bad)
        self.assertEqual(reasons(found), ["no-shipped-line"])

    def test_a_run_that_shipped_nothing_writes_an_honest_rail(self):
        """No rows, a headline saying so, `Lit: none`. Never a missing block."""
        empty = (
            "## The run in one screen\n\n| What | Count | Detail lives at |\n|---|---|---|\n"
            "| Shipped, unmerged | 0 | ## What shipped |\n\nShipped:      none\n\n"
            "## The run on the rail\n\nHeadline: Nothing shipped; both issues wait on 161.\n"
            "Lit: none\n\n| Issue | Stage | Kind | Sentence |\n|---|---|---|---|\n\n"
            "## What shipped\n\nnothing.\n"
        )
        self.assertEqual(refusals(empty), [])


class TheHeadlineIsARequiredField(unittest.TestCase):
    """Run `batch-88624c`'s briefing carried no one-screen block and no headline
    sentence, so this case is real rather than hypothetical."""

    def test_a_missing_headline_is_refused(self):
        bad = BRIEFING.replace("Headline: ", "Story: ")
        self.assertEqual(reasons(refusals(bad)), ["no-headline"])

    def test_an_empty_headline_is_refused(self):
        bad = BRIEFING.replace(
            "Headline: The database now refuses a viewer's direct write on every table this batch\n"
            "touched. The money road is still open.\n",
            "Headline:\n",
        )
        self.assertEqual(reasons(refusals(bad)), ["no-headline"])


class TheLitLineIsStatedAndGraded(unittest.TestCase):
    """The finale states the lit stages; the renderer never works them out. On
    run `batch-45c8b1` the line names four and must NOT name `catalogue`, and
    nothing here can check that second half: it is judgement."""

    def test_a_missing_lit_line_is_refused(self):
        bad = BRIEFING.replace("Lit: workspace, quotation, needs-you, zoho\n", "")
        self.assertEqual(reasons(refusals(bad)), ["no-lit"])

    def test_a_lit_key_outside_the_vocabulary_is_named(self):
        bad = BRIEFING.replace("Lit: workspace, quotation", "Lit: workspace, warehouse")
        found = refusals(bad)
        self.assertEqual(reasons(found), ["bad-lit-stage"])
        self.assertIn("warehouse", found[0])

    def test_a_headline_ending_in_a_stage_word_is_not_read_as_a_lit_key(self):
        """The wrong reason the check could go red: a parser reading the
        `Headline:` line's trailing text as keys. Ending the headline in
        `workspace` and dropping the real `Lit:` line must red on `no-lit`
        alone, and with the `Lit:` line present must pass."""
        ends_in_stage = BRIEFING.replace(
            "touched. The money road is still open.\n", "touched, on every workspace\n"
        )
        self.assertEqual(refusals(ends_in_stage), [])
        without_lit = ends_in_stage.replace("Lit: workspace, quotation, needs-you, zoho\n", "")
        self.assertEqual(reasons(refusals(without_lit)), ["no-lit"])


class TheRailSitsBelowTheWholeOneScreenBlock(unittest.TestCase):
    """Below the block's CONTENT, never between the heading and its table, and
    above every other `## ` heading. `check_run_picture.py` ends the one-screen
    block at the next `## `, so a rail heading above the table leaves it with
    zero figures and it exits 2 on `no-block-figures`."""

    def test_the_rail_above_the_one_screen_heading_is_refused(self):
        bad = RAIL + ONE_SCREEN + REST
        self.assertEqual(reasons(refusals(bad)), ["rail-above-block"])

    def test_the_rail_between_the_heading_and_its_table_is_refused(self):
        head, table = ONE_SCREEN.split("| What ", 1)
        bad = head + RAIL + "| What " + table + REST
        found = refusals(bad)
        self.assertIn("rail-splits-block", reasons(found))

    def test_another_heading_between_them_is_named(self):
        bad = ONE_SCREEN + "## Migrations\n\nSeven.\n\n" + RAIL + REST
        found = refusals(bad)
        self.assertEqual(reasons(found), ["heading-between"])
        self.assertIn("## Migrations", found[0])

    def test_it_anchors_on_the_first_one_screen_heading(self):
        """The real briefing carries the heading twice. Anchoring on the last
        would put the rail ABOVE the block and refuse a correct file."""
        self.assertEqual(BRIEFING.count("## The run in one screen"), 2)
        self.assertEqual(refusals(BRIEFING), [])


class CheckRunPictureStillReadsTheOneScreenFigures(unittest.TestCase):
    """The neighbour guard must keep exiting 0 on a briefing carrying both
    blocks, and the mutation is DRIVEN here rather than described."""

    def test_the_figures_are_read_with_the_rail_present(self):
        figures = check_run_picture.read_block_figures(BRIEFING)
        self.assertEqual(figures["shipped-unmerged"], 16.0)
        self.assertEqual(figures["wall-clock-hours"], 17.79)
        self.assertEqual(len(figures), 9)

    def test_the_rail_heading_above_the_table_costs_it_every_figure(self):
        head, table = ONE_SCREEN.split("| What ", 1)
        bad = head + RAIL + "| What " + table + REST
        ok, reason = check_run_picture.compare(
            check_run_picture.read_block_figures(bad), {"shipped-unmerged": 16.0}
        )
        self.assertFalse(ok)
        self.assertIn("no-block-figures", reason)
        # And this guard names the same fault in its own words.
        self.assertIn("rail-splits-block", reasons(refusals(bad)))


class OnlyTheShippedTableIsCompared(unittest.TestCase):
    """Issues 554 and 555 add three tables beneath the shipped one. The check
    keys on the shipped table's own header row, so 522 and 523 under `### Minted
    and left open` are never refused as issues that did not ship."""

    def test_the_minted_and_fork_tables_are_ignored(self):
        self.assertEqual(refusals(ONE_SCREEN + RAIL + MINTED_AND_FORKS + REST), [])

    def test_a_bands_table_is_not_read_as_shipped_rows(self):
        self.assertEqual(refusals(ONE_SCREEN + RAIL + MINTED_AND_FORKS + BANDS + REST), [])

    def test_a_floor_row_for_a_band_member_is_refused(self):
        rail = RAIL.replace("| 486   | quotation |", "| 486   | floor     |")
        found = refusals(ONE_SCREEN + rail + BANDS + REST)
        self.assertEqual(reasons(found), ["floor-in-band"])
        self.assertIn("486", found[0])
        # 555 owns the span rule. This message must not claim more than is checked.
        self.assertNotIn("span", found[0])

    def test_with_no_bands_table_every_floor_row_passes(self):
        """555 ships after this. A build that needs the table exits 1 on every
        run until it lands."""
        rail = RAIL.replace("| 486   | quotation |", "| 486   | floor     |")
        self.assertEqual(refusals(ONE_SCREEN + rail + REST), [])


class TheReviewsFaultsStayFixed(unittest.TestCase):
    """Eight faults the code review of 2026-09-04 drove against the first
    build, each pinned here so it cannot come back."""

    def test_a_table_cell_naming_the_rail_heading_is_not_the_heading(self):
        """The one-screen table's third column names headings by design."""
        cell = "| Rail rows           |    16 | ## The run on the rail      |\n"
        with_cell = BRIEFING.replace(
            "| Idle, per cent      |    15 | ## What this run cost       |\n",
            "| Idle, per cent      |    15 | ## What this run cost       |\n" + cell,
        )
        self.assertEqual(refusals(with_cell), [])

    def test_a_prose_mention_of_either_heading_above_the_block_is_not_the_heading(self):
        prose = "This file opens with ## The run in one screen and then ## The run on the rail.\n\n"
        self.assertEqual(refusals(prose + BRIEFING), [])

    def test_a_wrapped_shipped_line_keeps_its_continuation_ids(self):
        wrapped = BRIEFING.replace(
            "Shipped:      485b, 486, 487, 488, 489, 485, 519, 518, 516, 517a, 517, 521, 520a, 520b, 503, 406",
            "Shipped:      485b, 486, 487, 488, 489, 485, 519, 518, 516, 517a, 517, 521,\n"
            "              520a, 520b, 503, 406",
        )
        self.assertEqual(refusals(wrapped), [])

    def test_the_continuation_stops_at_the_next_label(self):
        """`Did not ship: none - every issue...` follows `Shipped:` directly and
        must not be read as part of it."""
        self.assertEqual(refusals(BRIEFING), [])
        one_line = BRIEFING.replace("Did not ship: none - every issue in the batch reached `done`\n", "")
        self.assertEqual(refusals(one_line), [])

    def test_a_rail_between_the_table_and_the_shipped_line_is_a_split_not_a_missing_line(self):
        head, rest = ONE_SCREEN.split("\nShipped:", 1)
        bad = head + "\n" + RAIL + "Shipped:" + rest + REST
        found = refusals(bad)
        self.assertIn("rail-splits-block", reasons(found))
        self.assertNotIn("no-shipped-line", reasons(found))
        self.assertIn("`Shipped:`", found[0])

    def test_a_rail_after_the_table_that_swallows_the_other_field_lines_is_refused(self):
        """`Shipped:` moved above the table, rail placed after the table's last
        row: the `Did not ship:`, `Minted:`, `Register:` and `Waiting:` lines
        land inside the rail body, and /daily-brief reads them from the block."""
        shipped = "Shipped:      485b, 486, 487, 488, 489, 485, 519, 518, 516, 517a, 517, 521, 520a, 520b, 503, 406\n"
        moved = ONE_SCREEN.replace(shipped, "")
        head, tail = moved.split("| What ", 1)
        table_end = tail.index("\n\n") + 2
        bad = head + shipped + "\n| What " + tail[:table_end] + RAIL + tail[table_end:] + REST
        found = refusals(bad)
        self.assertIn("rail-splits-block", reasons(found))
        self.assertIn("`Did not ship:`", found[0])

    def test_shipped_none_with_a_trailing_note_reads_as_empty(self):
        empty = (
            "## The run in one screen\n\n| What | Count | Detail lives at |\n|---|---|---|\n"
            "| Shipped, unmerged | 0 | ## What shipped |\n\n"
            "Shipped:      none - both wait on 161, which is unbuilt\n\n"
            "## The run on the rail\n\nHeadline: Nothing shipped; both issues wait on 161.\n"
            "Lit: none\n\n| Issue | Stage | Kind | Sentence |\n|---|---|---|---|\n\n"
            "## What shipped\n\nnothing.\n"
        )
        self.assertEqual(refusals(empty), [])

    def test_a_headline_that_starts_on_the_next_line_is_present(self):
        bad = BRIEFING.replace(
            "Headline: The database now refuses",
            "Headline:\nThe database now refuses",
        )
        self.assertEqual(refusals(bad), [])

    def test_an_escaped_pipe_stays_inside_the_sentence_it_measures(self):
        sentence = "Admin adds a person \\| changes a seat, then holds the last one xx"
        self.assertEqual(len(sentence.replace("\\|", "|")), 64)
        bad = BRIEFING.replace("Admin adds a person and changes a seat               ", sentence)
        found = refusals(bad)
        self.assertEqual(reasons(found), ["sentence-too-long"])
        self.assertIn("64", found[0])

    def test_a_row_with_too_few_cells_is_refused_as_bad_row(self):
        bad = BRIEFING.replace(
            "| 406   | floor     | guard   | A new bare line-number citation is refused           |",
            "| 406   | floor     | guard |",
        )
        found = refusals(bad)
        self.assertEqual(sorted(set(reasons(found))), ["bad-row", "no-row"])


class TheCommandTheFinaleRuns(unittest.TestCase):
    """Driven as a subprocess, because that is how the finale meets it.

    Three exit codes. 0 passes and says what it compared. 1 is a refusal the
    finale stops for. 2 is "I could grade nothing", never reported as a pass.
    """

    SCRIPT = str(pathlib.Path(__file__).resolve().parent / "check_run_rail.py")

    def run_it(self, briefing, stages=STAGES, stages_arg=True):
        with tempfile.TemporaryDirectory() as room:
            briefing_path = pathlib.Path(room) / "merge-briefing.md"
            stages_path = pathlib.Path(room) / "run-picture-stages.md"
            briefing_path.write_text(briefing)
            if stages is not None:
                stages_path.write_text(stages)
            command = [sys.executable, self.SCRIPT, "--briefing", str(briefing_path)]
            if stages_arg:
                command += ["--stages", str(stages_path)]
            return subprocess.run(command, capture_output=True, text=True)

    def test_the_real_shape_exits_zero_and_says_what_it_compared(self):
        done = self.run_it(BRIEFING)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("16 shipped, 16 rail rows", done.stdout)
        self.assertIn("4 stages lit", done.stdout)
        self.assertIn("graded", done.stdout)

    def test_a_bad_stage_exits_one_and_names_it(self):
        bad = BRIEFING.replace("| 516   | needs-you |", "| 516   | warehouse |")
        done = self.run_it(bad)
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED bad-stage", done.stderr)
        self.assertIn("warehouse", done.stderr)

    def test_every_refusal_is_printed_not_just_the_first(self):
        bad = BRIEFING.replace("| 516   | needs-you |", "| 516   | warehouse |").replace(
            "| 406   | floor     | guard   |", "| 406   | floor     | invisible |"
        )
        done = self.run_it(bad)
        self.assertEqual(done.returncode, 1)
        self.assertIn("bad-stage", done.stderr)
        self.assertIn("bad-kind", done.stderr)

    def test_a_missing_stages_argument_exits_two(self):
        done = self.run_it(BRIEFING, stages_arg=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("--stages", done.stderr)

    def test_a_missing_stages_file_says_so_and_carries_on(self):
        done = self.run_it(BRIEFING, stages=None)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no stage vocabulary", done.stdout)
        self.assertIn("NOT graded", done.stdout)

    def test_a_stages_file_with_no_readable_table_exits_two(self):
        """A present file whose header drifted is not a repo with no file, and
        rule 4's skip must not swallow it."""
        done = self.run_it(BRIEFING, stages=STAGES.replace("| Key |", "| **Key** |"))
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-stages-table", done.stderr)

    def test_a_relative_stages_path_is_found_from_the_git_top_level(self):
        """The finale may run the command from `.scratch/<feature>/`. The
        vocabulary lives at the repo root, so the path is tried there too, and
        a bad stage is still refused from the subdirectory."""
        with tempfile.TemporaryDirectory() as room:
            top = pathlib.Path(room)
            subprocess.run(["git", "init", "-q", str(top)], check=True)
            (top / "docs" / "agents").mkdir(parents=True)
            (top / "docs" / "agents" / "run-picture-stages.md").write_text(STAGES)
            sub = top / ".scratch" / "feature"
            sub.mkdir(parents=True)
            bad = BRIEFING.replace("| 516   | needs-you |", "| 516   | warehouse |")
            (sub / "merge-briefing.md").write_text(bad)
            done = subprocess.run(
                [sys.executable, self.SCRIPT, "--briefing", "merge-briefing.md",
                 "--stages", "docs/agents/run-picture-stages.md"],
                capture_output=True, text=True, cwd=sub,
            )
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("bad-stage", done.stderr)

    def test_a_briefing_with_no_one_screen_block_exits_two(self):
        done = self.run_it(RAIL + "## What shipped\n\nnothing\n")
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-block", done.stderr)

    def test_a_briefing_with_no_rail_exits_two(self):
        done = self.run_it(ONE_SCREEN + REST)
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-rail", done.stderr)

    def test_a_missing_briefing_exits_two(self):
        done = subprocess.run(
            [sys.executable, self.SCRIPT, "--briefing", "/nowhere/briefing.md",
             "--stages", "/nowhere/stages.md"],
            capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 2)


if __name__ == "__main__":
    unittest.main()
