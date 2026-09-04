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

| Caption                   | Span                | Issues   |
|---------------------------|---------------------|----------|
| Viewer can no longer write | workspace..needs-you | 517, 516 |
"""


class ABandReplacesTheCardsForItsMembers(unittest.TestCase):
    """Issue 555 ships bands, and this guard is live before any band exists.

    Measured by importing the drawing script this pack's renderer copies: on every one of the five drawn
    runs the card set and the band-chip set are DISJOINT and their union is the
    run's shipped count. So a rule reading `every rail row has a card` halts
    every run at `finale-board` the day 555 ships.
    """

    def test_a_banded_row_owes_no_card(self):
        board = a_card("503", "floor", "fix")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board), stages=None
        )
        self.assertTrue(ok, reason)
        self.assertIn("1 of the block's 1", reason)

    def test_a_card_for_a_banded_row_is_refused(self):
        """Drawn twice is the other half of the same rule: once as a chip inside
        the band, once as a card beneath it, and the reader counts two."""
        board = a_card("503", "floor", "fix") + a_card("517", "workspace", "new")
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED), guard.read_board_cards(board), stages=None
        )
        self.assertFalse(ok)
        self.assertIn("card-in-a-band", reason)
        self.assertIn("517", reason)


class OnlyShippedCardsAreGraded(unittest.TestCase):
    """Issue 554 adds minted and fork cards, keyed `F1` and `F4`, with no row in
    the shipped table. `data-shape` is what stops this guard refusing every one
    of them on the day 554 ships."""

    def test_a_fork_card_with_no_row_passes(self):
        board = (
            a_card("517", "workspace", "new")
            + a_card("516", "needs-you", "new")
            + a_card("503", "floor", "fix")
            + a_card("F1", "workspace", "fork", shape="fork")
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

    def test_a_fork_card_with_no_marked_line_is_read_not_refused(self):
        cards = guard.read_board_cards(
            '<g data-card="F1" data-stage="floor" data-kind="fork" '
            'data-shape="fork"><rect/></g>'
        )
        self.assertEqual(cards["F1"].shape, "fork")

    def test_a_shipped_card_with_no_marked_line_is_still_refused(self):
        with self.assertRaises(ValueError) as caught:
            guard.read_board_cards(
                '<g data-card="517" data-stage="workspace" data-kind="new">'
                '<text class="tv">A sentence nobody marked</text></g>'
            )
        self.assertIn("data-line", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
