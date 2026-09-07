#!/usr/bin/env python3
"""Tests for check_run_picture.py. Run: python3 test_check_run_picture.py

Issue 506 item 6b. The board render used to work its own figures out: it read the
whole briefing, counted the bold issue headings under `## What shipped`, noticed
which of them also sat under `## Skipped or blocked`, and subtracted. Item 6a takes
that arithmetic away and leaves the renderer copying `## The run in one screen`.
This guard is what makes the copy checkable, and it is the only part of item 6 that
catches a false number at any model.

It catches NUMBERS and nothing else. A wrong sentence in a `why` line is not a
figure and passes here. That is the stated limit, not an oversight.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

import check_run_picture as guard
import draw_run_rail


class BoardDisagreesWithTheBlock(unittest.TestCase):
    """The fault this guard exists for."""

    BLOCK = """## The run in one screen

| What              | Count | Detail lives at       |
|-------------------|-------|-----------------------|
| Shipped, unmerged |     8 | ## What shipped       |
| Did NOT ship      |     2 | ## Skipped or blocked |
"""

    def test_a_board_that_counted_seven_is_refused(self):
        board = '<div class="n" data-figure="shipped-unmerged">7</div>'
        ok, reason = guard.compare(
            guard.read_block_figures(self.BLOCK), guard.read_board_figures(board)
        )
        self.assertFalse(ok)
        self.assertIn("shipped-unmerged", reason)
        self.assertIn("disagrees", reason)

    def test_a_figure_the_block_does_not_hold_is_refused(self):
        """The 6a violation: the renderer worked a number out for itself.

        Every figure on the board has to be a copy of one in the block. A key
        with no counterpart means the render derived something, which is the
        habit item 6a exists to stop.
        """
        board = '<div class="n" data-figure="gates-passed">14</div>'
        ok, reason = guard.compare(
            guard.read_block_figures(self.BLOCK), guard.read_board_figures(board)
        )
        self.assertFalse(ok)
        self.assertIn("gates-passed", reason)
        self.assertIn("not-in-the-block", reason)


class TheRealShapesAgree(unittest.TestCase):
    """Run `batch-88624c`'s own numbers, in the shapes both files actually carry."""

    BLOCK = """## The run in one screen

Run `batch-88624c`, 10 issues, 8.48 h. Nothing is merged and nothing is deployed.

| What                | Count | Detail lives at             |
|---------------------|-------|-----------------------------|
| Shipped, unmerged   |     8 | ## What shipped             |
| Did NOT ship        |     2 | ## Skipped or blocked       |
| Migrations minted   |     5 | ## Migrations minted        |
| Issues minted       |     3 | ## Promotion                |
| Register rows left  |     0 | ## Promotion                |
| Waiting on you      |     6 | ## Actions waiting on the human |
| Forks to decide     |     4 | ## Decide                   |
| Wall clock, hours   |  8.48 | ## What this run cost       |
| Idle, per cent      |    17 | ## What this run cost       |

Shipped:      201, 224, 224b, 224c, 339, 153, 225, 269

## What shipped

Something else entirely, with a stray 99 in it.
"""

    BOARD = """<div class="strip">
      <div class="stat good"><div class="n" data-figure="shipped-unmerged">8</div>
        <div class="l">Shipped</div></div>
      <div class="stat warn"><div class="n" data-figure="did-not-ship">2</div>
        <div class="l">Did not ship</div></div>
      <div class="stat"><div class="n" data-figure="migrations-minted">5</div>
        <div class="l">Migrations</div></div>
    </div>
    <table><tbody>
      <tr><td>Wall clock, hours</td>
          <td class="num" data-figure="wall-clock-hours"><strong>8.48</strong></td></tr>
    </tbody></table>"""

    def test_the_block_table_reads_as_slugged_figures(self):
        figures = guard.read_block_figures(self.BLOCK)
        self.assertEqual(figures["shipped-unmerged"], 8.0)
        self.assertEqual(figures["did-not-ship"], 2.0)
        self.assertEqual(figures["wall-clock-hours"], 8.48)
        self.assertEqual(figures["idle-per-cent"], 17.0)

    def test_it_stops_at_the_next_heading(self):
        """`## What shipped` follows the block and holds a number of its own."""
        self.assertNotIn(99.0, guard.read_block_figures(self.BLOCK).values())

    def test_a_figure_wrapped_in_another_tag_still_reads(self):
        """The renderer is free to bold or colour the number it prints."""
        self.assertEqual(guard.read_board_figures(self.BOARD)["wall-clock-hours"], 8.48)

    def test_the_agreeing_pair_passes(self):
        ok, reason = guard.compare(
            guard.read_block_figures(self.BLOCK), guard.read_board_figures(self.BOARD)
        )
        self.assertTrue(ok, reason)

    def test_the_count_compared_is_reported_and_is_not_the_count_read(self):
        """A pass on four figures and a pass on nothing must not read alike.

        The board carries four of the block's nine. That is allowed — the panel
        is a summary — so the sentence has to say four and nine, not just `ok`.
        """
        _, reason = guard.compare(
            guard.read_block_figures(self.BLOCK), guard.read_board_figures(self.BOARD)
        )
        self.assertIn("4 of the block's 9", reason)


class MalformedMarkupNeverPassesQuietly(unittest.TestCase):
    """Three ways the reader could lose a figure and report a pass on the rest.

    Losing a figure is worse than refusing, because board-carries-fewer-than-block
    is a legal shape: a dropped figure looks exactly like a figure the panel chose
    not to show, and the number stays wrong on screen with nothing saying so.
    """

    def test_a_void_tag_inside_a_figure_does_not_swallow_the_next_one(self):
        """`<br>` never sends an end tag, so a naive depth counter never returns
        to zero and every later figure is read as part of this one."""
        board = (
            '<div class="n" data-figure="shipped-unmerged">8<br>issues</div>'
            '<div class="n" data-figure="did-not-ship">2</div>'
        )
        figures = guard.read_board_figures(board)
        self.assertEqual(figures["shipped-unmerged"], 8.0)
        self.assertEqual(figures["did-not-ship"], 2.0)

    def test_a_figure_element_that_never_closes_is_refused(self):
        with self.assertRaises(ValueError):
            guard.read_board_figures('<div data-figure="shipped-unmerged">8')

    def test_a_block_heading_with_no_table_under_it_is_refused(self):
        """The heading alone anchors nothing. Refusing on the emptiness says so;
        letting it through reports the board's figures as invented."""
        block = guard.read_block_figures("## The run in one screen\n\nnothing yet.\n")
        ok, reason = guard.compare(block, {"shipped-unmerged": 8.0})
        self.assertFalse(ok)
        self.assertIn("no-block-figures", reason)


class ItRefusesRatherThanAssumes(unittest.TestCase):
    """Nothing here reads a silence as a pass.

    `check_commit_order.py` earned this rule the hard way on run
    `414a-483-286335`: it printed `ok` having matched zero rows. An `ok` on five
    figures and an `ok` on nothing are different sentences, so the count is
    printed and an empty read exits 2.
    """

    def test_a_briefing_with_no_block_is_refused(self):
        self.assertIsNone(guard.read_block_figures("## What shipped\n\nnothing.\n"))
        ok, reason = guard.compare(None, {"shipped-unmerged": 8.0})
        self.assertFalse(ok)
        self.assertIn("no-block", reason)

    def test_a_board_carrying_no_figure_at_all_is_refused(self):
        """Otherwise a board with the panel dropped passes every other rule."""
        ok, reason = guard.compare({"shipped-unmerged": 8.0}, {})
        self.assertFalse(ok)
        self.assertIn("no-figures", reason)


class TheCommandTheFinaleRuns(unittest.TestCase):
    """Driven as a subprocess, because that is how the finale meets it.

    Three exit codes. 0 passes. 1 is a disagreement, which is a real finding and
    stops the finale. 2 is "I could read nothing", which must never be reported
    as a pass.
    """

    SCRIPT = str(pathlib.Path(__file__).resolve().parent / "check_run_picture.py")

    def run_it(self, block, board):
        with tempfile.TemporaryDirectory() as room:
            briefing_path = pathlib.Path(room) / "merge-briefing.md"
            board_path = pathlib.Path(room) / "board.html"
            briefing_path.write_text(block)
            board_path.write_text(board)
            return subprocess.run(
                [sys.executable, self.SCRIPT,
                 "--briefing", str(briefing_path), "--board", str(board_path)],
                capture_output=True, text=True,
            )

    # After issue 552 every briefing carries a rail block, and `check_run_rail.py`
    # in step 4 exits 2 without one — a run that shipped nothing still writes an
    # honest rail. So a fixture with no rail is not a shape the finale can meet,
    # and these figure-half cases carry the smallest rail that satisfies the
    # card half: a headline, a `Lit:` line and no rows.
    EMPTY_RAIL = """
## The run on the rail

Headline: Nothing on the rail here; these cases grade the figures.
Lit: none

| Issue | Stage | Kind | Sentence |
|-------|-------|------|----------|
"""
    BLOCK = TheRealShapesAgree.BLOCK + EMPTY_RAIL
    BOARD = TheRealShapesAgree.BOARD

    def test_agreement_exits_zero_and_says_what_it_compared(self):
        done = self.run_it(self.BLOCK, self.BOARD)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ok", done.stdout)

    def test_a_disagreement_exits_one(self):
        done = self.run_it(self.BLOCK, self.BOARD.replace(">8<", ">7<"))
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED", done.stderr)
        self.assertIn("shipped-unmerged", done.stderr)

    def test_a_briefing_with_no_block_exits_two(self):
        done = self.run_it("## What shipped\n\nnothing\n", self.BOARD)
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-block", done.stderr)

    def test_a_board_with_no_panel_exits_two(self):
        done = self.run_it(self.BLOCK, "<p>no panel here</p>")
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-figures", done.stderr)

    def test_a_missing_file_exits_two(self):
        done = subprocess.run(
            [sys.executable, self.SCRIPT,
             "--briefing", "/nowhere/briefing.md", "--board", "/nowhere/board.html"],
            capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 2)


# --------------------------------------------------------------------------
# Issue 553. The board draws the rail above the panel, and the guard widens to
# grade the cards the same way it grades the figures.
# --------------------------------------------------------------------------

RAIL = """## The run in one screen

| What              | Count | Detail lives at |
|-------------------|-------|-----------------|
| Shipped, unmerged |     3 | ## What shipped |

Shipped:      517, 516, 503

## The run on the rail

Headline: The viewer loses the pen on every screen.
Lit: workspace, needs-you

| Issue | Stage     | Kind  | Sentence                                      |
|-------|-----------|-------|-----------------------------------------------|
| 517   | workspace | new   | Admin adds a person and changes a seat        |
| 516   | needs-you | new   | Admin is told a customer waits to be verified |
| 503   | floor     | fix   | Citation checker refuses without a clean bill |
"""


def a_card(issue, stage, kind, lines=("A sentence",), shape="shipped"):
    """One card in the shape the generator draws.

    The attributes sit on the container, the issue chip carries the issue
    number as its own text, and each line of the sentence carries `data-line`.
    """
    text = "".join(
        f'<text class="tv" data-line="{k}">{line}</text>'
        for k, line in enumerate(lines)
    )
    return (
        f'<g data-card="{issue}" data-stage="{stage}" data-kind="{kind}" '
        f'data-shape="{shape}"><rect class="box"/>'
        f'<rect class="c-new"/><text class="tn">{issue}</text>{text}</g>'
    )


# Issue 554's two tables, appended to the same rail block. 522 and 523 are
# holes the run left and neither shipped, so neither may appear in the shipped
# table above.
RAIL_554 = RAIL + """
### Minted and left open

| Issue | Stage     | Sentence                                |
|-------|-----------|-----------------------------------------|
| 522   | quotation | A failed price read shows as 'no price' |
| 524   | floor     | A gate writes a row nothing later reads |

### Forks waiting on you

| Fork | Stage     | Question                                          |
|------|-----------|---------------------------------------------------|
| F1   | workspace | Tell an admin the email belongs to another space? |
| F4   | floor     | Refuse an untracked paste file?                   |
"""


def a_hole(issue, stage, lines=("A hole",)):
    """A dashed card. It carries no kind: a hole has no diff to have a kind of."""
    return a_card(issue, stage, "", lines=lines, shape="minted")


def a_fork(key, stage, lines=("A question?",)):
    return a_card(key, stage, "", lines=lines, shape="fork")


SHIPPED_CARDS = (
    a_card("517", "workspace", "new")
    + a_card("516", "needs-you", "new")
    + a_card("503", "floor", "fix")
)
HOLE_CARDS = a_hole("522", "quotation") + a_hole("524", "floor")
FORK_CARDS = a_fork("F1", "workspace") + a_fork("F4", "floor")


def cards_verdict(board, block=RAIL_554, stages=None):
    return guard.compare_cards(
        guard.read_block_cards(block), guard.read_board_cards(board), stages=stages
    )


class TheHolesAndTheQuestionsAreDrawnToo(unittest.TestCase):
    """Issue 554, criteria 1 and 2. Two more card shapes reach the board and
    both are graded against their own table.

    Issue 553 left `data-shape` here for exactly this and graded `shipped`
    alone, so before this slice a dashed card the renderer invented passed in
    silence. The three shapes are graded apart, and an UNKNOWN shape is still
    counted and passed over — that forward door is what kept 553's guard from
    halting every run the day these two shapes shipped, and the next shape needs
    it just as much.
    """

    def test_the_whole_board_passes(self):
        ok, why = cards_verdict(SHIPPED_CARDS + HOLE_CARDS + FORK_CARDS)
        self.assertTrue(ok, why)
        self.assertIn("2 minted", why)
        self.assertIn("2 fork", why)

    def test_a_dashed_card_the_briefing_never_minted_is_refused(self):
        """The criterion's own test: a dashed card on the board with no minted
        row in the briefing. Before this slice it passed."""
        board = SHIPPED_CARDS + HOLE_CARDS + a_hole("999", "floor") + FORK_CARDS
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("card-not-in-the-block", reason)
        self.assertIn("999", reason)
        self.assertIn("minted", reason)

    def test_a_minted_row_with_no_dashed_card_is_refused(self):
        board = SHIPPED_CARDS + a_hole("522", "quotation") + FORK_CARDS
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("no-card", reason)
        self.assertIn("524", reason)

    def test_a_dashed_card_on_the_wrong_stage_is_refused(self):
        board = SHIPPED_CARDS + a_hole("522", "zoho") + a_hole("524", "floor") + FORK_CARDS
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("card-disagrees", reason)
        self.assertIn("522", reason)
        self.assertIn("quotation", reason)

    def test_an_amber_card_the_briefing_never_asked_is_refused(self):
        board = SHIPPED_CARDS + HOLE_CARDS + FORK_CARDS + a_fork("F9", "floor")
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("card-not-in-the-block", reason)
        self.assertIn("F9", reason)

    def test_a_fork_row_with_no_amber_card_is_refused(self):
        board = SHIPPED_CARDS + HOLE_CARDS + a_fork("F1", "workspace")
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("no-card", reason)
        self.assertIn("F4", reason)

    def test_a_fork_key_is_never_read_as_a_number(self):
        """`F1` and `F4` are keys, not issue ids. 553's reader keeps the
        attribute verbatim and this is the case that holds it there."""
        self.assertIn("F1", guard.read_board_cards(FORK_CARDS))

    def test_a_hole_and_a_fork_are_measured_against_their_box_too(self):
        """A dashed card draws text like a shipped one, so a sentence that
        would reach the browser clipped is refused on all three shapes."""
        wide = "x" * 40
        board = SHIPPED_CARDS + a_hole("522", "quotation", lines=(wide,)) \
            + a_hole("524", "floor") + FORK_CARDS
        ok, reason = cards_verdict(board)
        self.assertFalse(ok)
        self.assertIn("card-overflows", reason)

    def test_an_unknown_shape_is_counted_and_passed_over(self):
        """553's forward door, kept open. A shape this guard does not know is
        not graded and not refused, so the next slice can ship its cards before
        this file learns them."""
        board = SHIPPED_CARDS + HOLE_CARDS + FORK_CARDS + a_card(
            "B1", "workspace", "", lines=(), shape="band"
        )
        ok, why = cards_verdict(board)
        self.assertTrue(ok, why)

    def test_a_shipped_card_still_carries_its_kind_and_the_others_need_none(self):
        """Only the shipped table has a `Kind` column. Grading a kind on a
        dashed card would demand a column that does not exist."""
        board = SHIPPED_CARDS + HOLE_CARDS + FORK_CARDS
        self.assertTrue(cards_verdict(board)[0])
        wrong = (
            a_card("517", "workspace", "fix")
            + a_card("516", "needs-you", "new")
            + a_card("503", "floor", "fix")
            + HOLE_CARDS + FORK_CARDS
        )
        ok, reason = cards_verdict(wrong)
        self.assertFalse(ok)
        self.assertIn("card-disagrees", reason)
        self.assertIn("kind", reason)

    def test_the_register_is_drawn_nowhere(self):
        """Criterion 7. Every register row ends fixed, promoted, refused or
        dropped below the floor, and a fifth road never reaches promotion at
        all. None of the five gets a card, and the guard is what says so: a
        card keyed like a register row is in no table and is refused.
        """
        for row in ("fin45c8b1-01", "vg99e-02", "rg248-01"):
            with self.subTest(row=row):
                board = SHIPPED_CARDS + HOLE_CARDS + FORK_CARDS + a_hole(row, "floor")
                ok, reason = cards_verdict(board)
                self.assertFalse(ok)
                self.assertIn("card-not-in-the-block", reason)


class ARunWithNoHolesAndNoForksDrawsNoSuchCard(unittest.TestCase):
    """Issue 554, criterion 8. The rail block omits both tables rather than
    printing empty ones, and the board is shipped cards only."""

    def test_the_pre_554_block_and_board_still_pass(self):
        ok, why = cards_verdict(SHIPPED_CARDS, block=RAIL)
        self.assertTrue(ok, why)
        self.assertIn("0 minted", why)
        self.assertIn("0 fork", why)

    def test_a_dashed_card_against_a_block_with_no_minted_table_is_refused(self):
        ok, reason = cards_verdict(SHIPPED_CARDS + a_hole("522", "quotation"), block=RAIL)
        self.assertFalse(ok)
        self.assertIn("card-not-in-the-block", reason)


class ACardThatDisagreesWithItsRow(unittest.TestCase):
    """The fault this half of the guard exists for.

    A figure the panel omits is a summary. A card the rail moves is a run whose
    story is drawn wrong, and the drawing is the thing the human reads first.
    """

    def test_a_card_on_the_wrong_stage_is_refused(self):
        board = (
            a_card("517", "workspace", "new")
            + a_card("516", "zoho", "new")
            + a_card("503", "floor", "fix")
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("card-disagrees", reason)
        self.assertIn("516", reason)
        self.assertIn("zoho", reason)
        self.assertIn("needs-you", reason)


class ARowWithNoCardIsRefused(unittest.TestCase):
    """The rule that is the OPPOSITE of the figure rule, on purpose.

    `read_board_figures`'s docstring says the board may carry fewer figures than
    the block and that passes. Cards get no such licence: a figure the panel
    omits is a summary, a card the rail omits is an issue that vanished from the
    picture.
    """

    def test_two_cards_against_three_rows_are_refused(self):
        board = a_card("517", "workspace", "new") + a_card("516", "needs-you", "new")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("no-card", reason)
        self.assertIn("503", reason)

    def test_a_card_the_rail_does_not_name_is_refused(self):
        """The card half of `not-in-the-block`: the renderer derived it."""
        board = (
            a_card("517", "workspace", "new")
            + a_card("516", "needs-you", "new")
            + a_card("503", "floor", "fix")
            + a_card("999", "zoho", "fix")
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("card-not-in-the-block", reason)
        self.assertIn("999", reason)


BANDED = RAIL + """
### Bands

| Band | Stages               | Kind  | Issues   | Caption                    | Seats                          |
|------|----------------------|-------|----------|----------------------------|--------------------------------|
| B1   | workspace..needs-you | guard | 517 516  | Viewer can no longer write | admin ok, member ok, viewer no |

### Band chips

| Band | Issue | Text                  |
|------|-------|-----------------------|
| B1   | 517   | seats change          |
| B1   | 516   | the queue tells them   |
"""


def a_band(key="B1", stages="workspace..needs-you", issues="517 516", chips=None):
    """One band in the shape `draw_run_rail.py` draws it.

    The attributes go on a `<g>` that opens and closes. Measured 2026-09-03
    against this file's own reader: `<rect data-figure="a" width="5"/>` raises
    `no number in ''`, so a self-closing carrier is refused rather than read,
    and no `data-figure` element may sit inside a band — a nested one is
    swallowed and its digits concatenated, `7` and `9` reading as `79.0`.
    """
    if chips is None:
        chips = (("517", ("seats change",)), ("516", ("the queue tells them",)))
    inside = "".join(
        f'<g data-chip="{num}"><rect class="c-guard"/><text class="tn">{num}</text>'
        + "".join(
            f'<text class="tv" data-line="{k}">{line}</text>'
            for k, line in enumerate(lines)
        )
        + "</g>"
        for num, lines in chips
    )
    return (
        f'<g data-band="{key}" data-stages="{stages}" data-issues="{issues}">'
        f'<rect class="band"/><text class="tb">a caption</text>{inside}</g>'
    )


class ABandReplacesTheCardsForItsMembers(unittest.TestCase):
    """Issue 555 ships bands, and this guard is live before any band exists.

    Measured by importing the drawing script this pack's renderer copies: on every one of the five drawn
    runs the card set and the band-chip set are DISJOINT and their union is the
    run's shipped count. So a rule reading `every rail row has a card` halts
    every run at `finale-board` the day 555 ships.
    """

    def test_a_banded_row_owes_no_card(self):
        board = a_card("503", "floor", "fix") + a_band()
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertTrue(ok, reason)
        self.assertIn("1 of the block's 1", reason)

    def test_a_card_for_a_banded_row_is_refused(self):
        """Drawn twice is the other half of the same rule: once as a chip inside
        the band, once as a card beneath it, and the reader counts two."""
        board = (
            a_card("503", "floor", "fix") + a_band() + a_card("517", "workspace", "new")
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("card-in-a-band", reason)
        self.assertIn("517", reason)


class OnlyTheGradedShapesAreGraded(unittest.TestCase):
    """Issue 553 wrote this class as a promise to issue 554: `data-shape` is
    what stops the shipped rule refusing a card that has no shipped row.

    554 has now arrived and grades `minted` and `fork` against their own
    tables, so the promise moves on to the shape after them. The door is the
    same one and it is still open; only its subject changed. A fork card with
    no fork row is refused from this slice onward, and
    `TheHolesAndTheQuestionsAreDrawnToo` is where that is asserted.
    """

    def test_a_card_of_an_unknown_shape_with_no_row_passes(self):
        board = (
            a_card("517", "workspace", "new")
            + a_card("516", "needs-you", "new")
            + a_card("503", "floor", "fix")
            + a_card("B1", "workspace", "", lines=(), shape="band")
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertTrue(ok, reason)

    def test_a_card_with_no_shape_attribute_is_graded_as_shipped(self):
        board = a_card("999", "zoho", "fix", shape="")
        cards = guard.read_board_cards(board)
        self.assertEqual(cards["999"].shape, "shipped")


STAGES = {
    "workspace", "tender", "quote", "award", "quotation",
    "needs-you", "zoho", "catalogue", "floor",
}


class DataStageIsAKeyFromTheVocabulary(unittest.TestCase):
    """The nine keys `docs/agents/run-picture-stages.md` fixes, verbatim.

    No slug rule is derived from a column name. `Zoho push and read` is the
    column and `zoho` is the key; a renderer that slugs the column writes
    `zoho-push-and-read` and disagrees with every rail row. The figure
    convention slugs a row LABEL and this one does not, which is why the two
    rules are stated apart.
    """

    def test_a_slugged_column_name_is_refused(self):
        board = a_card("517", "zoho-push-and-read", "new")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=STAGES
        )
        self.assertFalse(ok)
        self.assertIn("bad-card-stage", reason)
        self.assertIn("zoho-push-and-read", reason)

    def test_the_rule_is_skipped_where_the_repository_has_no_vocabulary(self):
        """Rule 4 of that file: `/run-issues` runs on other repositories, and a
        check that exits wherever the file is missing stops every finale."""
        board = a_card("517", "zoho-push-and-read", "new")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertNotIn("bad-card-stage", reason)


class TheAttributesSitOnAContainer(unittest.TestCase):
    """Measured 2026-09-03: `HTMLParser` turns `<rect data-card="517"/>` into a
    start tag immediately followed by an end tag. A reader that took it would
    see a card with no text and no shapes, and report a pass on markup nobody
    can read."""

    def test_a_self_closing_carrier_is_refused_out_loud(self):
        with self.assertRaises(ValueError) as caught:
            guard.read_board_cards('<rect data-card="517" data-stage="floor"/>')
        self.assertIn("self-closing", str(caught.exception))

    def test_a_self_closing_rect_inside_a_card_does_not_close_it(self):
        """The generator's card shapes ARE self-closing rects. If they moved the
        depth, every card would close on its first shape and lose its text."""
        cards = guard.read_board_cards(
            '<g data-card="517" data-stage="workspace" data-kind="new">'
            '<rect class="box"/><rect class="c-new"/>'
            '<text class="tv" data-line="0">Admin adds a person</text></g>'
        )
        self.assertEqual(cards["517"].stage, "workspace")
        self.assertEqual(cards["517"].lines, ("Admin adds a person",))


class ACardWhoseLinesOverflowIsRefused(unittest.TestCase):
    """The net for a board that did NOT come from `draw_run_rail.py`.

    That script wraps and asserts, so a board it drew cannot fail here. This
    rule catches the other road: a renderer that wrote the SVG by hand, which
    is exactly what step 5 of `finale.md` used to ask for. SVG `<text>` does not
    wrap, so each card's lines are literal strings at fixed coordinates and the
    board can be measured with the generator's own arithmetic.
    """

    def test_a_line_wider_than_the_card_is_refused(self):
        board = a_card(
            "517", "workspace", "new",
            lines=("Admin adds a person and changes a seat",),
        ) + a_card("516", "needs-you", "new") + a_card("503", "floor", "fix")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("card-overflows", reason)
        self.assertIn("517", reason)

    def test_a_fourth_line_is_refused(self):
        board = a_card(
            "517", "workspace", "new",
            lines=("Database refuses an", "unauthorised", "workspace membership", "row"),
        ) + a_card("516", "needs-you", "new") + a_card("503", "floor", "fix")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("card-overflows", reason)
        self.assertIn("4 lines", reason)

    def test_three_lines_of_twenty_characters_pass(self):
        """The bound is per line and per count, and no total is asserted
        anywhere. Three lines of twenty joined by two spaces is a 62-character
        sentence that draws, so a criterion re-testing the 60-character total
        would grade the wrong thing."""
        board = a_card(
            "517", "workspace", "new",
            lines=("12345678901234567890",) * 3,
        ) + a_card("516", "needs-you", "new") + a_card("503", "floor", "fix")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board), stages=None
        )
        self.assertTrue(ok, reason)


class TheCommandGradesBothHalves(unittest.TestCase):
    """End to end, the way `finale.md` step 5 runs it."""

    SCRIPT = str(pathlib.Path(__file__).with_name("check_run_picture.py"))
    STAGES_FILE = """| Key | Column |
|---|---|
| `workspace` | Workspace |
| `tender` | Create a tender |
| `quote` | Invite and quote |
| `award` | Compare and award |
| `quotation` | Customer quotation |
| `needs-you` | Needs-you queue |
| `zoho` | Zoho push and read |
| `catalogue` | Catalogue |
| `floor` | Under the floor |
"""
    PANEL = '<div class="n" data-figure="shipped-unmerged">3</div>'
    CARDS = (
        a_card("517", "workspace", "new")
        + a_card("516", "needs-you", "new")
        + a_card("503", "floor", "fix")
    )

    def run_it(self, briefing, board, stages=None):
        with tempfile.TemporaryDirectory() as tmp:
            here = pathlib.Path(tmp)
            (here / "b.md").write_text(briefing)
            (here / "board.html").write_text(board)
            argv = [sys.executable, self.SCRIPT,
                    "--briefing", str(here / "b.md"),
                    "--board", str(here / "board.html")]
            if stages is not None:
                (here / "stages.md").write_text(stages)
                argv += ["--stages", str(here / "stages.md")]
            return subprocess.run(argv, capture_output=True, text=True, cwd=tmp)

    def test_a_board_that_agrees_passes_and_says_what_it_compared(self):
        done = self.run_it(RAIL, self.PANEL + self.CARDS, self.STAGES_FILE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("1 of the block's 1 figures", done.stdout)
        self.assertIn("3 of the block's 3 card-owing rail rows", done.stdout)

    def test_a_card_on_the_wrong_stage_exits_one(self):
        board = self.PANEL + self.CARDS.replace('data-stage="needs-you"',
                                                'data-stage="zoho"')
        done = self.run_it(RAIL, board, self.STAGES_FILE)
        self.assertEqual(done.returncode, 1)
        self.assertIn("card-disagrees", done.stderr)
        self.assertIn("516", done.stderr)

    def test_a_missing_card_exits_one(self):
        board = self.PANEL + a_card("517", "workspace", "new")
        done = self.run_it(RAIL, board, self.STAGES_FILE)
        self.assertEqual(done.returncode, 1)
        self.assertIn("no-card", done.stderr)

    def test_a_briefing_with_no_rail_exits_two(self):
        done = self.run_it(
            RAIL.split("## The run on the rail")[0], self.PANEL, self.STAGES_FILE
        )
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-rail", done.stderr)

    def test_a_self_closing_carrier_exits_two(self):
        board = self.PANEL + '<rect data-card="517" data-stage="workspace"/>'
        done = self.run_it(RAIL, board, self.STAGES_FILE)
        self.assertEqual(done.returncode, 2)
        self.assertIn("unreadable-card", done.stderr)

    def test_without_stages_the_vocabulary_rule_is_skipped_and_the_rest_runs(self):
        """Rule 4 of `run-picture-stages.md`. `/run-issues` runs on other
        repositories and a check that exited there would stop every finale."""
        done = self.run_it(RAIL, self.PANEL + self.CARDS)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("stage keys", done.stdout)

    def test_the_figure_half_still_refuses_on_its_own(self):
        """A rail that swallowed a figure must not read as a panel showing
        fewer, and the figure rules are unchanged by the cards above them."""
        board = self.PANEL.replace(">3<", ">7<") + self.CARDS
        done = self.run_it(RAIL, board, self.STAGES_FILE)
        self.assertEqual(done.returncode, 1)
        self.assertIn("disagrees", done.stderr)
        self.assertIn("shipped-unmerged", done.stderr)


class TheIssueChipIsNotASentenceLine(unittest.TestCase):
    """Found by the acceptance walk on 2026-09-04, on the sixteen-issue fixture.

    A card draws its issue number as text inside the same container as its
    sentence. A reader that counted every `<text>` measured a three-line card as
    four and refused a board `draw_run_rail.py` had just asserted was fine, so
    the two halves of the change disagreed about the same card. The sentence
    lines carry `data-line` and they are the only ones measured.
    """

    def test_a_three_line_sentence_beside_a_chip_passes(self):
        board = a_card(
            "406", "floor", "guard",
            lines=("A new bare line-", "number citation", "is refused"),
        )
        card = guard.read_board_cards(board)["406"]
        self.assertEqual(len(card.lines), 3)
        self.assertNotIn("406", card.lines)

    def test_a_card_that_marks_no_line_is_unreadable(self):
        """Silence is refused here as everywhere else in this guard: a card
        whose sentence cannot be found cannot be measured, and an unmeasured
        card looks exactly like one that fits."""
        with self.assertRaises(ValueError) as caught:
            guard.read_board_cards(
                '<g data-card="406" data-stage="floor" data-kind="guard">'
                '<text class="tv">A sentence nobody marked</text></g>'
            )
        self.assertIn("data-line", str(caught.exception))


class TheUnmarkedRuleFollowsWhatIsGraded(unittest.TestCase):
    """Found by the review pass on 2026-09-04.

    The raise for a card with no `data-line` applied to every shape, while
    `compare_cards` grades only `shipped`. Issue 554's fork cards are keyed `F1`
    and carry `data-shape="fork"`, so the exemption `data-shape` exists for was
    defeated one function earlier and every run halted at exit 2 the day 554
    shipped. Silence is refused where the guard makes a claim, and it makes none
    about a shape it does not grade.
    """

    def test_a_card_of_an_unknown_shape_with_no_marked_line_is_read_not_refused(self):
        """Issue 554 grades `fork` and measures its lines, so a fork card with
        no marked line IS refused from this slice on. The exemption belongs to
        the shape this guard makes no claim about, which is what it was for."""
        cards = guard.read_board_cards(
            '<g data-card="B1" data-stage="floor" data-shape="band"><rect/></g>'
        )
        self.assertEqual(cards["B1"].shape, "band")

    def test_a_fork_card_with_no_marked_line_is_now_refused(self):
        with self.assertRaises(ValueError) as caught:
            guard.read_board_cards(
                '<g data-card="F1" data-stage="floor" data-shape="fork">'
                '<rect/></g>'
            )
        self.assertIn("data-line", str(caught.exception))

    def test_a_shipped_card_with_no_marked_line_is_still_refused(self):
        with self.assertRaises(ValueError) as caught:
            guard.read_board_cards(
                '<g data-card="517" data-stage="workspace" data-kind="new">'
                '<text class="tv">A sentence nobody marked</text></g>'
            )
        self.assertIn("data-line", str(caught.exception))


# --------------------------------------------------------------------------
# Issue 555. A band is drawn where the block states one, and nowhere else.
# --------------------------------------------------------------------------


class ABandIsDrawnWhereTheBlockStatesOne(unittest.TestCase):
    """Criteria 2 and 4. The board draws what the `### Bands` table states and
    draws nothing where it states nothing — the same rule as the cards, for the
    same reason: the drawing carries no judgement."""

    def board(self, **kw):
        return a_card("503", "floor", "fix") + a_band(**kw)

    def test_the_stated_band_is_drawn_and_agrees(self):
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(self.board()),
            stages=None, bands=guard.read_board_bands(self.board()),
        )
        self.assertTrue(ok, reason)

    def test_a_band_the_block_does_not_name_is_refused(self):
        board = self.board(key="B9")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("band-not-in-the-block", reason)
        self.assertIn("B9", reason)

    def test_a_row_with_no_band_on_the_board_is_refused(self):
        board = a_card("503", "floor", "fix")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("no-band", reason)
        self.assertIn("B1", reason)

    def test_a_span_that_disagrees_with_the_row_is_refused(self):
        board = self.board(stages="workspace..zoho")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("band-disagrees", reason)
        self.assertIn("workspace..zoho", reason)

    def test_an_issue_list_that_disagrees_with_the_row_is_refused(self):
        board = self.board(issues="517")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("band-disagrees", reason)
        self.assertIn("516", reason)

    def test_a_run_with_no_bands_draws_none_and_passes(self):
        """Two of the five drawn runs are this case, and it is the normal one."""
        board = (
            a_card("517", "workspace", "new")
            + a_card("516", "needs-you", "new")
            + a_card("503", "floor", "fix")
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(RAIL), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertTrue(ok, reason)


class ABandsAttributesAreReadableByThisGuard(unittest.TestCase):
    """Criterion 3, measured 2026-09-03 against this file's own readers."""

    def test_a_self_closing_carrier_is_refused_rather_than_read(self):
        with self.assertRaises(ValueError) as caught:
            guard.read_board_bands('<svg><rect data-band="B1" width="5"/></svg>')
        self.assertIn("B1", str(caught.exception))

    def test_a_band_that_never_closes_is_refused(self):
        """The band's own end tag, missing. An end tag from an element that
        opened BEFORE the band closes it instead, exactly as it does for a
        card: this reader counts depth from the carrier and has no view of what
        wraps it."""
        with self.assertRaises(ValueError) as caught:
            guard.read_board_bands('<g data-band="B1"><rect class="band"/>')
        self.assertIn("B1", str(caught.exception))

    def test_a_figure_inside_a_band_is_refused(self):
        """`read_block_figures` swallows a nested `data-figure` and concatenates
        its digits — `7` and `9` read as `79.0` — so a band may hold none."""
        with self.assertRaises(ValueError) as caught:
            guard.read_board_bands(
                '<g data-band="B1"><div data-figure="shipped">7</div></g>'
            )
        self.assertIn("data-figure", str(caught.exception))


class AChipIsMeasuredAgainstTheSpaceItsOwnBandGives(unittest.TestCase):
    """The budget a chip has falls out of the band's span and its chip count,
    so it cannot be graded against a fixed number the way a card's sentence is.

    Measured across the five drawn bands in `34-picture-d-gen.py`: 12.84 units
    a line on `batch-88624c`'s money band, three chips over two columns, up to
    23.15 on a two-chip band over eight columns.
    """

    STAGES = [
        "workspace", "tender", "quote", "award", "quotation",
        "needs-you", "zoho", "catalogue", "floor",
    ]

    def test_the_two_measured_ends_are_what_the_shared_function_returns(self):
        """Both figures are characters a line, not units, and both are the
        generator's own bands: `Money must add up` over `award..quotation` with
        three chips, and the anonymous-caller band over all eight with two."""
        narrow = draw_run_rail.chip_width(2, 3, "Money must add up")
        wide = draw_run_rail.chip_width(
            8, 2, "Anyone at the database meets a closed door"
        )
        self.assertAlmostEqual(narrow / draw_run_rail.PX, 12.84, places=2)
        self.assertAlmostEqual(wide / draw_run_rail.PX, 23.15, places=2)

    def test_a_band_too_narrow_for_a_caption_column_puts_it_on_top(self):
        """The generator's one `layout="top"` band is the two-column money
        band, whose chips would otherwise have 35 units between them."""
        self.assertEqual(
            draw_run_rail.band_layout(2, 3, "Money must add up")[0], "top"
        )
        self.assertEqual(
            draw_run_rail.band_layout(4, 4, "Money, from award to Zoho")[0], "left"
        )

    def test_a_chip_line_wider_than_its_budget_is_refused(self):
        board = a_card("503", "floor", "fix") + a_band(
            chips=(
                ("517", ("a chip line far too long for the space it has",)),
                ("516", ("the queue tells them",)),
            )
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=self.STAGES, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("band-overflows", reason)
        self.assertIn("517", reason)

    def test_a_chip_line_inside_its_budget_passes(self):
        board = a_card("503", "floor", "fix") + a_band()
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=self.STAGES, bands=guard.read_board_bands(board),
        )
        self.assertTrue(ok, reason)


class TheBandRefusalsExitOne(unittest.TestCase):
    """Criterion 4 drives this mutation once: delete the band's briefing row,
    watch the check exit 1, restore it, watch it exit 0.

    The exit code is not free. `main()` ends `return 1 if reason.startswith(...)
    else 2`, so a refusal named anything outside that tuple exits 2 and reads
    as "the guard could grade nothing", which is a different repair.
    """

    SCRIPT = str(pathlib.Path(__file__).with_name("check_run_picture.py"))
    BOARD_HEAD = (
        '<div class="stat"><div class="n" data-figure="shipped-unmerged">3</div></div>'
    )

    def run_it(self, briefing, board):
        with tempfile.TemporaryDirectory() as work:
            b = pathlib.Path(work, "briefing.md")
            h = pathlib.Path(work, "board.html")
            b.write_text(briefing)
            h.write_text(board)
            return subprocess.run(
                [sys.executable, self.SCRIPT, "--briefing", str(b), "--board", str(h)],
                capture_output=True, text=True,
            )

    def board(self):
        return (
            self.BOARD_HEAD
            + a_card("503", "floor", "fix")
            + a_band()
        )

    def test_the_stated_band_drawn_exits_zero(self):
        done = self.run_it(BANDED, self.board())
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_band_with_no_row_exits_one(self):
        without = BANDED.replace(
            "| B1   | workspace..needs-you | guard | 517 516  "
            "| Viewer can no longer write | admin ok, member ok, viewer no |\n",
            "",
        )
        done = self.run_it(without, self.board())
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn("band-not-in-the-block", done.stderr)

    def test_a_row_with_no_band_exits_one(self):
        done = self.run_it(BANDED, self.BOARD_HEAD + a_card("503", "floor", "fix"))
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn("no-band", done.stderr)

    def test_an_unreadable_band_exits_two(self):
        done = self.run_it(BANDED, self.BOARD_HEAD + '<rect data-band="B1"/>')
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("unreadable-band", done.stderr)


class AChipTheBlockDoesNotNameIsRefused(unittest.TestCase):
    """The other direction of the band rule, and the one a first build misses.

    `card-not-in-the-block` refuses a card the block does not name. Without the
    same rule inside a band, a render could add a chip to the run's headline
    band and no guard would say so.
    """

    def test_an_invented_chip_is_refused(self):
        board = a_card("503", "floor", "fix") + a_band(
            chips=(
                ("517", ("seats change",)),
                ("516", ("the queue tells them",)),
                ("999", ("invented",)),
            )
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("chip-not-in-the-block", reason)
        self.assertIn("999", reason)

    def test_a_member_with_no_chip_is_named_as_a_missing_chip(self):
        """Not `no-band`: the band is drawn and one chip inside it is not, and
        the two repairs are different."""
        board = a_card("503", "floor", "fix") + a_band(
            chips=(("517", ("seats change",)),)
        )
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board),
            stages=None, bands=guard.read_board_bands(board),
        )
        self.assertFalse(ok)
        self.assertIn("no-chip:", reason)
        self.assertIn("516", reason)


if __name__ == "__main__":
    unittest.main()
