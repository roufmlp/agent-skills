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
RAIL_ONLY = """## The run on the rail

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

# Issue 554's two tables. THREE issues were minted on that run, not two: the
# briefing's `Minted:` line reads `522, 523, 524` and `34-picture-d-gen.py`
# draws 524 in the run's `floor` list. A fixture holding two would pass a board
# that silently dropped one.
MINTED = """### Minted and left open

| Issue | Stage      | Sentence                                  |
|-------|------------|-------------------------------------------|
| 522   | quotation  | A failed price read shows as 'no price'   |
| 523   | quotation  | An unread price pool calls itself whole   |
| 524   | floor      | A gate writes a row nothing later reads   |

"""

# Six forks, one per `### N.` heading under that run's `## Decide — 6 open
# forks` (lines 1839, 1884, 1925, 1967, 1989 and 2020 of the real file). The
# `Question` cell is the finale's own compression, not the heading: five of the
# six headings are 61 to 89 characters against a card that holds 60. Items 4, 5
# and 6 carry `[rule, nothing live]` and are harness questions, so they take
# `floor`.
FORKS = """### Forks waiting on you

| Fork | Stage     | Question                                            |
|------|-----------|-----------------------------------------------------|
| F1   | workspace | Tell an admin the email belongs to another space?   |
| F2   | quotation | Needs a fourth sentence for 'we never looked'?      |
| F3   | quotation | Should the screen say whether the relink ran?       |
| F4   | floor     | Refuse an untracked paste file?                     |
| F5   | floor     | Should 406's ratchet grow past `src/`?              |
| F6   | floor     | Catch an admin-only comparison in the seat guard?   |

"""

MINTED_AND_FORKS = MINTED + FORKS

# The whole rail block for that run as it reads after issue 554: the shipped
# table, then the two tables this slice adds. `RAIL_ONLY` is the shipped half
# alone, for the tests that are about one of the three tables in isolation.
RAIL = RAIL_ONLY + MINTED + FORKS

# Issue 555's tables, on run `batch-45c8b1`. The band is the one
# `34-picture-d-gen.py` draws for that run: seven shipped issues and the dashed
# `509`, which was minted and not shipped, spanning every column. The `Issues`
# cell is bare ids and the chip text lives in its own table, because a chip's
# own words carry numbers — `99 reads fail closed now` is one of the
# generator's — and a reader taking ids out of that cell would find issue 99.
BANDS = """### Bands

| Band | Stages               | Kind  | Issues                           | Caption                                      | Seats                          |
|------|----------------------|-------|----------------------------------|----------------------------------------------|--------------------------------|
| B1   | workspace..catalogue | guard | 486 487 488 489 485 485b 519 509 | Viewer, on every screen, can no longer write | admin ok, member ok, viewer no |

### Band chips

| Band | Issue | Text                        |
|------|-------|-----------------------------|
| B1   | 486   | customers                   |
| B1   | 487   | suppliers and invites       |
| B1   | 488   | deals and money             |
| B1   | 489   | workspace and ops           |
| B1   | 485   | catalogue                   |
| B1   | 485b  | catalogue guards run        |
| B1   | 519   | seat readers agree          |
| B1   | 509   | money road still open       |

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

# The `## Decide` heading every real briefing carries. Measured over the 34
# briefings on disk, 28 carry the `— N open forks` form and all five of the
# runs the picture draws carry TWO `## Decide` headings. This guard reads the
# heading's presence and never its items; see `_check_forks` for the
# measurement that says why.
REST_QUIET = REST
REST = REST_QUIET + """
## Decide — 6 open forks

### 1. Should an admin be told that an email address already belongs to some other workspace?
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
        # The heading, not the one-screen table cell that names it. Only that
        # section is cut: truncating the file here would take `## Decide` with
        # it and refuse for a different reason entirely.
        at = BRIEFING.index("\n## What shipped, per issue")
        after = BRIEFING.index("\n## ", at + 1)
        without = BRIEFING[:at] + BRIEFING[after:]
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
        self.assertEqual(refusals(BANDED), [])

    def test_a_floor_row_for_a_band_member_is_refused(self):
        found = refusals(BANDED.replace("| 486   | quotation |", "| 486   | floor     |"))
        self.assertIn("floor-in-band", reasons(found))
        floor = [r for r in found if r.startswith("floor-in-band")]
        self.assertIn("486", floor[0])

    def test_with_no_bands_table_every_floor_row_passes(self):
        """555 ships after this. A build that needs the table exits 1 on every
        run until it lands."""
        rail = RAIL.replace("| 486   | quotation |", "| 486   | floor     |")
        self.assertEqual(refusals(ONE_SCREEN + rail + REST), [])


class EveryIssueTheRunLeftOpenHasADashedRow(unittest.TestCase):
    """Issue 554, criterion 5. A dashed card is a hole the run leaves behind,
    and the set of holes is the `Minted:` line plus the `Did not ship:` line.

    Both are fields of the one-screen block, which is where this guard already
    reads the shipped list from, and for the same measured reason: `##
    Promotion` and `## Skipped or blocked` are not stable in name or in shape
    across the five drawn runs, and one line of comma-separated ids is what a
    reader can read.

    The comparison runs in BOTH directions. A row for an issue neither line
    names is a hole the finale invented; an id on either line with no row is a
    hole that vanished from the picture.
    """

    def test_the_three_minted_rows_of_that_run_pass(self):
        self.assertEqual(refusals(ONE_SCREEN + RAIL_ONLY + MINTED + FORKS + REST), [])

    def test_a_deleted_minted_row_is_refused(self):
        """The mutation criterion 5 asks to be driven. 524 is the row a
        two-row fixture would have dropped in silence."""
        cut = MINTED.replace(
            "| 524   | floor      | A gate writes a row nothing later reads   |\n", ""
        )
        found = refusals(ONE_SCREEN + RAIL_ONLY + cut + FORKS + REST)
        self.assertEqual(reasons(found), ["no-minted-row"])
        self.assertIn("524", found[0])

    def test_a_row_for_an_issue_no_line_names_is_refused(self):
        extra = MINTED.replace(
            "reads   |\n\n", "reads   |\n| 999   | floor      | Nothing minted this |\n\n")
        found = refusals(ONE_SCREEN + RAIL_ONLY + extra + FORKS + REST)
        self.assertEqual(reasons(found), ["not-minted"])
        self.assertIn("999", found[0])

    def test_an_issue_that_did_not_ship_owes_a_row_too(self):
        """`99b-99e-6e11ba` minted nothing and drew `99f` dashed. A check
        comparing the rows against the `Minted:` line alone refuses that run's
        own correct board."""
        one = ONE_SCREEN.replace(
            "Did not ship: none - every issue in the batch reached `done`",
            "Did not ship: 99f   - nothing reads the code yet, by the human's cut",
        )
        with_row = MINTED.replace(
            "reads   |\n\n",
            "reads   |\n| 99f   | floor      | Nothing reads the code yet |\n\n")
        self.assertEqual(refusals(one + RAIL_ONLY + with_row + FORKS + REST), [])
        found = refusals(one + RAIL_ONLY + MINTED + FORKS + REST)
        self.assertEqual(reasons(found), ["no-minted-row"])
        self.assertIn("99f", found[0])

    def test_a_minted_stage_outside_the_vocabulary_is_refused(self):
        bad = MINTED.replace("| 522   | quotation ", "| 522   | invoicing ")
        found = refusals(ONE_SCREEN + RAIL_ONLY + bad + FORKS + REST)
        self.assertEqual(reasons(found), ["bad-stage"])
        self.assertIn("minted", found[0])

    def test_a_minted_sentence_of_sixty_characters_is_refused(self):
        long = "x" * 60
        bad = MINTED.replace("A failed price read shows as 'no price'   ", long)
        found = refusals(ONE_SCREEN + RAIL_ONLY + bad + FORKS + REST)
        self.assertEqual(reasons(found), ["sentence-too-long"])
        self.assertIn("60 characters", found[0])

    def test_a_minted_row_with_two_cells_is_refused(self):
        bad = MINTED.replace(
            "| 524   | floor      | A gate writes a row nothing later reads   |",
            "| 524   | floor      |",
        )
        found = reasons(refusals(ONE_SCREEN + RAIL_ONLY + bad + FORKS + REST))
        # 524's row is skipped as unreadable, so it is also missing. Both are
        # true and both are printed; the check prints every refusal, not the first.
        self.assertEqual(found, ["bad-minted-row", "no-minted-row"])

    def test_one_issue_takes_one_minted_row(self):
        twice = MINTED.replace(
            "reads   |\n\n", "reads   |\n| 522   | quotation  | Said twice |\n\n")
        found = refusals(ONE_SCREEN + RAIL_ONLY + twice + FORKS + REST)
        self.assertEqual(reasons(found), ["duplicate-minted"])


class EveryForkWaitingOnHimHasAnAmberRow(unittest.TestCase):
    """Issue 554, criteria 2, 3 and 4.

    **Criterion 4's stated check could not be built, and the measurement is in
    this docstring rather than in a note nobody reads.** It asked the guard to
    count the items under every `## Decide` heading in the file and compare the
    total against the fork rows. Measured 2026-09-05 over the five runs
    `34-picture-d-gen.py` draws, every one of which carries TWO `## Decide`
    headings:

    | Run | first section | second section | true total |
    |---|---|---|---|
    | `batch-45c8b1` | 0, pointer prose | 6, as `### N.` | 6 |
    | `batch-375cbf` | 4, as `- **` | 3, as `- **` | 7 |
    | `batch-88624c` | 0, pointer prose | 4, as `### N.` | **6** |
    | `99b-99e-6e11ba` | 1, a gate REJECT report as `- **` | 3, as `### N.` | 3 |
    | `481-482-2d0f77` | 3, as `**N.` | 2, as `**N.` | 5 |

    Two rows refute the count. `batch-88624c`'s own first section says "Six
    open forks, in two places in this file": four sit under the second heading
    and **two more under `### Refused — 37, and two of them are worth your
    veto`**, which is not a `## Decide` heading at all. So the correct total is
    six and every `## Decide` heading together holds four. And
    `99b-99e-6e11ba`'s first section holds one `- **` bullet that is a verify
    gate's REJECT report, not a fork, so a pattern counter reads four where
    three are true.

    A counter over that prose therefore refuses two of five correct briefings,
    which is the exact fault criterion 4 names on `batch-375cbf`. So the guard
    compares the fork rows against the one-screen table's `Forks to decide`
    figure: two numbers the finale wrote, in one file, where a disagreement is
    a fork drawn and not counted or counted and not drawn. The `## Decide`
    prose is read for one thing only — whether it exists at all.
    """

    def test_the_six_forks_of_that_run_pass(self):
        self.assertEqual(refusals(ONE_SCREEN + RAIL_ONLY + MINTED + FORKS + REST), [])

    def test_a_deleted_fork_row_is_refused(self):
        """The mutation criterion 4 asks to be driven: delete one row, watch it
        go red, restore it, watch it go green."""
        cut = FORKS.replace(
            "| F6   | floor     | Catch an admin-only comparison in the seat guard?   |\n", ""
        )
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + cut + REST)
        self.assertEqual(reasons(found), ["fork-count"])
        self.assertIn("5", found[0])
        self.assertIn("6", found[0])
        # Restored, it is green again. The same fixture, one line back.
        self.assertEqual(refusals(ONE_SCREEN + RAIL_ONLY + MINTED + FORKS + REST), [])

    def test_an_extra_fork_row_is_refused_by_the_same_rule(self):
        extra = FORKS.replace(
            "guard?   |\n\n", "guard?   |\n| F7   | floor     | A seventh nobody counted? |\n\n")
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + extra + REST)
        self.assertEqual(reasons(found), ["fork-count"])

    def test_a_question_of_sixty_characters_is_refused(self):
        bad = FORKS.replace(
            "Tell an admin the email belongs to another space?   ", "y" * 60
        )
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + bad + REST)
        self.assertEqual(reasons(found), ["question-too-long"])
        self.assertIn("F1", found[0])

    def test_the_real_decide_headings_are_all_too_long_to_scrape(self):
        """Criterion 3's evidence, kept as a test rather than a claim. These
        are the six headings of `batch-45c8b1` verbatim, and five of the six
        overflow the card. The guard reads the `Question` cell instead, and
        `test_no_decide_heading_is_ever_read` proves it never opens these."""
        headings = [
            "Should an admin be told that an email address already belongs to some other workspace?",
            'Does the quotation builder need a fourth sentence for "we never looked"?',
            "Should anything on screen say whether the price relink ran?",
            "`[rule, nothing live]` Should the paste-file check refuse an untracked file?",
            "`[rule, nothing live]` Should 406's ratchet grow past `src/`?",
            "`[rule, nothing live]` Should the one-seat guard also catch an `\"admin\"`-only comparison?",
        ]
        over = [h for h in headings if len(h) >= guard.SENTENCE_LIMIT]
        self.assertEqual(len(over), 5, [len(h) for h in headings])

    def test_no_decide_heading_is_ever_read(self):
        """The question comes out of the block. A briefing whose `## Decide`
        section holds nothing a machine could parse still passes."""
        decide = "\n## Decide\n\nSix open forks, written out further down.\n"
        self.assertEqual(refusals(ONE_SCREEN + RAIL_ONLY + MINTED + FORKS + decide + REST_QUIET), [])

    def test_forks_counted_and_no_decide_section_at_all_is_refused(self):
        """The one fact the prose is read for. Six forks counted and no section
        holding them is a briefing that lost them between two steps."""
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + FORKS + REST_QUIET)
        self.assertEqual(reasons(found), ["no-decide"])

    def test_a_fork_key_is_unique_across_the_whole_briefing(self):
        """The seam pass's finding. Two rows keyed `F1` collide as two amber
        cards and `check_run_picture.py` cannot tell which row a card is."""
        twice = FORKS.replace(
            "guard?   |\n\n",
            "guard?   |\n| F1   | floor     | Keyed the same as the first? |\n\n")
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + twice + REST)
        self.assertIn("duplicate-fork", reasons(found))
        self.assertIn("F1", " ".join(found))

    def test_a_fork_stage_outside_the_vocabulary_is_refused(self):
        bad = FORKS.replace("| F1   | workspace ", "| F1   | invoicing ")
        found = refusals(ONE_SCREEN + RAIL_ONLY + MINTED + bad + REST)
        self.assertEqual(reasons(found), ["bad-stage"])
        self.assertIn("fork", found[0])

    def test_a_fork_row_with_two_cells_is_refused(self):
        bad = FORKS.replace(
            "| F6   | floor     | Catch an admin-only comparison in the seat guard?   |",
            "| F6   | floor     |",
        )
        found = reasons(refusals(ONE_SCREEN + RAIL_ONLY + MINTED + bad + REST))
        # The unreadable row is still one row, so the count still agrees.
        self.assertEqual(found, ["bad-fork-row"])


class ARunWithNoHolesAndNoForksDrawsNeitherTable(unittest.TestCase):
    """Issue 554, criterion 8. The fixture is SYNTHETIC and the issue says why:
    measured over the 34 briefings on disk, 28 carry a `## Decide — N open
    forks` heading and the lowest count is one, so no real run has none."""

    QUIET = (
        ONE_SCREEN
        .replace("| Forks to decide     |     6 |", "| Forks to decide     |     0 |")
        .replace("| Issues minted       |     3 |", "| Issues minted       |     0 |")
        .replace("Minted:       522, 523, 524", "Minted:       none")
    )

    def test_neither_table_and_no_refusal(self):
        self.assertEqual(refusals(self.QUIET + RAIL_ONLY + REST_QUIET), [])

    def test_an_empty_minted_table_is_not_owed_and_not_refused(self):
        """Nothing forces the headings to be absent rather than empty. Both
        read the same to this guard, which grades rows and not headings."""
        empty = "### Minted and left open\n\n| Issue | Stage | Sentence |\n|---|---|---|\n\n"
        self.assertEqual(refusals(self.QUIET + RAIL_ONLY + empty + REST_QUIET), [])


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


# --------------------------------------------------------------------------
# Issue 555. A band is one subject crossing several stages, drawn as a strip
# over the columns it touches with its issues as chips inside it. Every rule
# below grades the block the finale wrote; nothing here finds a band, and a
# run that states none passes every one of them.
# --------------------------------------------------------------------------

# `batch-45c8b1` with its band. The band's `509` chip is the money road, which
# that run named in its own headline and did not close, so under issue 554's
# rule it earns a `Did not ship:` entry and a dashed row — and criterion 7 then
# accepts it. The real briefing shipped all sixteen and left the money road
# open in prose alone; the rail is where that becomes a row.
BANDED = (
    ONE_SCREEN.replace(
        "Did not ship: none - every issue in the batch reached `done`",
        "Did not ship: 509  - the money road, left open on purpose",
    )
    + RAIL.replace(
        "| 524   | floor      | A gate writes a row nothing later reads   |",
        "| 524   | floor      | A gate writes a row nothing later reads   |\n"
        "| 509   | award      | The money road is still open              |",
    )
    + BANDS
    + REST
)


class TheBandTableOnTheRealRunPasses(unittest.TestCase):
    """`batch-45c8b1`'s own band, as `34-picture-d-gen.py` draws it."""

    def test_no_refusal(self):
        self.assertEqual(refusals(BANDED), [])

    def test_the_rows_are_read_back(self):
        rail = guard.read_rail(BANDED)
        self.assertEqual([row[0] for row in rail.band_rows], ["B1"])
        self.assertEqual(len(rail.chip_rows), 8)


class ABandBelowTheFloorIsRefused(unittest.TestCase):
    """**Two issues across two spanned columns**, which is the smallest floor
    consistent with all five bands the generator draws.

    Measured 2026-09-03 by importing that file: `batch-375cbf`'s
    anonymous-caller band carries TWO issues and `batch-88624c`'s money band
    spans TWO columns, so the three-and-three rule the issue first proposed
    refuses three of the five bands the human read and approved. The two shapes
    below the floor are a card, not a band.
    """

    def test_one_issue_is_refused_and_both_counts_are_printed(self):
        bad = BANDED.replace(
            "| 486 487 488 489 485 485b 519 509 |", "| 486                              |"
        )
        found = [r for r in refusals(bad) if r.startswith("band-too-small")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("B1", found[0])
        self.assertIn("1 issue", found[0])
        self.assertIn("8 column", found[0])

    def test_two_issues_stay_green(self):
        """The edge on the passing side. `batch-375cbf` draws this band."""
        ok = BANDED.replace(
            "| 486 487 488 489 485 485b 519 509 |", "| 486 487                          |"
        )
        self.assertEqual(
            [r for r in refusals(ok) if r.startswith("band-too-small")], []
        )

    def test_one_spanned_column_is_refused(self):
        bad = BANDED.replace("| workspace..catalogue |", "| workspace..workspace |")
        found = [r for r in refusals(bad) if r.startswith("band-too-small")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("1 column", found[0])

    def test_two_spanned_columns_stay_green(self):
        """The other edge. `batch-88624c`'s money band spans `award..quotation`."""
        ok = BANDED.replace("| workspace..catalogue |", "| workspace..tender    |")
        self.assertEqual(
            [r for r in refusals(ok) if r.startswith("band-too-small")], []
        )


class ASpanThatIsNotAContiguousRangeIsRefused(unittest.TestCase):
    """The span is two keys of the stage vocabulary and the columns between
    them, in the order `docs/agents/run-picture-stages.md` sets.

    `floor` is never spannable: `34-picture-d-gen.py` draws the floor row after
    every band, so a band cannot reach it without redrawing the layout.
    """

    def bad_span(self, cell):
        bad = BANDED.replace("| workspace..catalogue |", f"| {cell} |")
        return [r for r in refusals(bad) if r.startswith("bad-band-span")]

    def test_a_key_outside_the_vocabulary_is_named(self):
        found = self.bad_span("workspace..nonsense")
        self.assertEqual(len(found), 1, found)
        self.assertIn("nonsense", found[0])

    def test_a_reversed_span_is_refused(self):
        found = self.bad_span("catalogue..workspace ")
        self.assertEqual(len(found), 1, found)
        self.assertIn("backwards", found[0])

    def test_the_floor_is_never_spannable(self):
        found = self.bad_span("award..floor         ")
        self.assertEqual(len(found), 1, found)
        self.assertIn("floor", found[0])

    def test_a_cell_that_is_not_a_span_at_all_is_refused(self):
        found = self.bad_span("workspace, catalogue ")
        self.assertEqual(len(found), 1, found)
        self.assertIn("first..last", found[0])

    def test_with_no_vocabulary_the_shape_is_still_graded(self):
        """Rule 4 of run-picture-stages.md. The keys go ungraded where the
        repository has no vocabulary; `first..last` is this file's own shape
        and is graded everywhere."""
        bad = BANDED.replace("| workspace..catalogue |", "| workspace, catalogue |")
        found = [r for r in refusals(bad, stages=None) if r.startswith("bad-band-span")]
        self.assertEqual(len(found), 1, found)
        ok = BANDED.replace("| workspace..catalogue |", "| nowhere..nothing     |")
        self.assertEqual(
            [r for r in refusals(ok, stages=None) if r.startswith("bad-band-span")], []
        )


class EveryIssueABandNamesIsNamedElsewhereInTheBlock(unittest.TestCase):
    """Criterion 7, and the rule that actually refuses an invented subject.

    A band carries shipped issues AND issues the run left open: the generator's
    own band on `batch-45c8b1` carries `509` as a dashed chip, and `509` was
    minted rather than shipped. So the two tables a member may have a row in
    are the shipped one and `### Minted and left open`, and a check written
    against the shipped rows alone refuses the only worked band that exists.
    """

    def test_an_issue_with_no_row_anywhere_is_refused(self):
        bad = BANDED.replace(" 485b 519 509 |", " 485b 519 777 |")
        found = [r for r in refusals(bad) if r.startswith("band-not-in-the-block")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("777", found[0])

    def test_a_minted_issue_is_accepted(self):
        """`509` on the real run. Without this the generator's own band is refused."""
        self.assertEqual(
            [r for r in refusals(BANDED) if r.startswith("band-not-in-the-block")], []
        )

    def test_a_fork_key_in_a_band_is_refused(self):
        """A fork is a question waiting on the human, never a subject that changed."""
        bad = BANDED.replace(" 485b 519 509 |", " 485b 519 F1  |")
        found = [r for r in refusals(bad) if r.startswith("band-not-in-the-block")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("F1", found[0])

    def test_one_issue_in_two_bands_is_refused(self):
        second = (
            "| B2   | quote..quotation     | fix   | 486 487                          "
            "| Money, from award to Zoho                    |                                |\n"
        )
        bad = BANDED.replace("\n\n### Band chips", "\n" + second + "\n### Band chips")
        found = [r for r in refusals(bad) if r.startswith("issue-in-two-bands")]
        self.assertEqual(len(found), 2, refusals(bad))
        self.assertIn("486", found[0])
        self.assertIn("B1", found[0])
        self.assertIn("B2", found[0])

    def test_two_bands_with_their_own_issues_pass(self):
        second = (
            "| B2   | quote..quotation     | fix   | 521 520a                         "
            "| Money, from award to Zoho                    |                                |\n"
        )
        chips = "| B2   | 521   | relink runs early           |\n| B2   | 520a  | options become a table      |\n"
        good = BANDED.replace("\n\n### Band chips", "\n" + second + "\n### Band chips")
        good = good.replace("| B1   | 509   | money road still open       |\n",
                            "| B1   | 509   | money road still open       |\n" + chips)
        self.assertEqual(refusals(good), [])


class ABandMemberSitsInsideItsOwnSpan(unittest.TestCase):
    """`finale.md` already states it: a band member takes a stage inside its
    band's span, never `floor`. A member drawn outside its band's columns is a
    chip in one place and a stage in another, and the picture says both."""

    def test_a_member_on_a_stage_outside_the_span_is_refused(self):
        narrow = BANDED.replace("| workspace..catalogue |", "| workspace..quote     |")
        found = [r for r in refusals(narrow) if r.startswith("member-outside-span")]
        # Every member outside the narrowed span earns its own line: the guard
        # prints them all, so a finale repairing one is not sent back for the next.
        self.assertEqual(len(found), 5, refusals(narrow))
        self.assertIn("486", found[0])
        self.assertIn("quotation", found[0])
        self.assertTrue(all("workspace..quote" in r for r in found))

    def test_a_member_inside_the_span_passes(self):
        self.assertEqual(
            [r for r in refusals(BANDED) if r.startswith("member-outside-span")], []
        )


class TheSeatPillsComeFromTheCellAndNeverFromTheCaption(unittest.TestCase):
    """Criterion 10. **"A band about seats" is not a rule any check can grade**,
    so the check grades the cell and whether a band is about seats stays the
    finale's judgement, exactly as the caption is.

    The three marks are `def seat_pills(x, y, states)` in the generator: a fixed
    admin/member/viewer order and the map `{"ok": "✓", "no": "✕", "dash": "–"}`.
    """

    def test_an_empty_cell_is_a_band_with_no_pills(self):
        none = BANDED.replace("| admin ok, member ok, viewer no |", "|                                |")
        self.assertEqual(refusals(none), [])

    def test_a_seat_out_of_order_is_refused(self):
        bad = BANDED.replace(
            "| admin ok, member ok, viewer no |", "| viewer no, admin ok, member ok |"
        )
        found = [r for r in refusals(bad) if r.startswith("bad-seats")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("admin, member, viewer", found[0])

    def test_a_mark_outside_the_three_is_refused(self):
        bad = BANDED.replace(
            "| admin ok, member ok, viewer no |", "| admin ok, member ok, viewer ✕  |"
        )
        found = [r for r in refusals(bad) if r.startswith("bad-seats")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("ok, no, dash", found[0])

    def test_two_seats_are_refused(self):
        bad = BANDED.replace(
            "| admin ok, member ok, viewer no |", "| admin ok, member ok            |"
        )
        found = [r for r in refusals(bad) if r.startswith("bad-seats")]
        self.assertEqual(len(found), 1, refusals(bad))

    def test_a_dash_passes(self):
        ok = BANDED.replace(
            "| admin ok, member ok, viewer no |", "| admin ok, member dash, viewer no |"
        )
        self.assertEqual([r for r in refusals(ok) if r.startswith("bad-seats")], [])


class ABandTakesOneOfTheFourKinds(unittest.TestCase):
    """The band's colour is the same judgement a card's is, stated in the same
    vocabulary. The generator's five bands read `guard` and `fix`."""

    def test_a_kind_outside_the_four_is_refused(self):
        bad = BANDED.replace("| guard | 486 487", "| story | 486 487")
        found = [r for r in refusals(bad) if r.startswith("bad-band-kind")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("story", found[0])


class EveryChipCarriesItsOwnWords(unittest.TestCase):
    """Measured by importing `34-picture-d-gen.py`: every chip the five drawn
    bands hold draws one or two lines of text under it, and the strings are
    fragments — `486` draws `customers`, `485b` draws `catalogue guards now
    truly run`. A band whose chips draw bare is not the picture the human read.

    The text is its own table because a chip's words carry numbers of their own:
    `99 reads fail closed now` is what `149` draws on `batch-375cbf`, and a
    reader taking ids out of a cell holding both would find issue 99.
    """

    def test_a_member_with_no_chip_row_is_refused(self):
        bad = BANDED.replace("| B1   | 487   | suppliers and invites       |\n", "")
        found = [r for r in refusals(bad) if r.startswith("no-chip-text")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("487", found[0])

    def test_a_chip_row_for_an_issue_the_band_does_not_name_is_refused(self):
        bad = BANDED.replace("| B1   | 487   |", "| B1   | 777   |")
        found = [r for r in refusals(bad) if r.startswith("chip-not-in-the-band")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("777", found[0])

    def test_a_chip_row_naming_no_band_is_refused(self):
        bad = BANDED.replace("| B1   | 487   |", "| B9   | 487   |")
        found = [r for r in refusals(bad) if r.startswith("chip-not-in-the-band")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("B9", found[0])

    def test_two_rows_for_one_chip_are_refused(self):
        bad = BANDED.replace(
            "| B1   | 487   | suppliers and invites       |\n",
            "| B1   | 487   | suppliers and invites       |\n"
            "| B1   | 487   | suppliers again             |\n",
        )
        found = [r for r in refusals(bad) if r.startswith("duplicate-chip")]
        self.assertEqual(len(found), 1, refusals(bad))

    def test_an_empty_text_cell_is_refused(self):
        bad = BANDED.replace("| suppliers and invites       |", "|                             |")
        found = [r for r in refusals(bad) if r.startswith("no-chip-text")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("487", found[0])

    def test_a_run_with_no_bands_needs_no_chip_table(self):
        self.assertEqual(refusals(BRIEFING), [])


class ABandKeyIsUniqueAcrossTheBriefing(unittest.TestCase):
    """The same rule a fork key obeys, for the same reason. Both guards key
    bands by the `Band` cell, so two rows sharing one key collapse into one and
    a whole band leaves the picture with nothing saying so."""

    def test_two_rows_with_one_key_are_refused(self):
        second = (
            "| B1   | quote..quotation     | fix   | 521 520a                         "
            "| Money, from award to Zoho                    |                                |\n"
        )
        bad = BANDED.replace("\n\n### Band chips", "\n" + second + "\n### Band chips")
        found = [r for r in refusals(bad) if r.startswith("duplicate-band")]
        self.assertEqual(len(found), 1, refusals(bad))
        self.assertIn("B1", found[0])


class TheStageVocabularyIsAnOrderedSequence(unittest.TestCase):
    """`_span` reads the vocabulary's ORDER, so a caller handing this guard an
    unordered set gets an AttributeError where every other bad input here earns
    a printed refusal. `read_stages` returns the table's order and `check` says
    so in its signature."""

    def test_read_stages_keeps_the_table_order(self):
        self.assertEqual(guard.read_stages(STAGES)[:3], ["workspace", "tender", "quote"])

    def test_a_repeated_key_is_kept_once(self):
        twice = STAGES.replace(
            "| `tender` | Create a tender | MAP journey 1 | Create a tender. |",
            "| `tender` | Create a tender | MAP journey 1 | Create a tender. |\n"
            "| `tender` | Create a tender | MAP journey 1 | Create a tender. |",
        )
        self.assertEqual(guard.read_stages(twice).count("tender"), 1)


class TheFloorMessageDoesNotClaimAColumnCountItNeverRead(unittest.TestCase):
    """Where the repository has no vocabulary the span's keys go ungraded, so
    the guard has no column count. Printing `0 columns` there states a
    measurement it never took, and a reader would go looking for a span fault
    that is not the one refused."""

    def test_with_no_vocabulary_the_columns_are_named_as_ungraded(self):
        bad = BANDED.replace(
            "| 486 487 488 489 485 485b 519 509 |", "| 486                              |"
        )
        found = [r for r in refusals(bad, stages=None) if r.startswith("band-too-small")]
        self.assertEqual(len(found), 1, found)
        self.assertIn("1 issue", found[0])
        self.assertNotIn("0 column", found[0])


if __name__ == "__main__":
    unittest.main()
