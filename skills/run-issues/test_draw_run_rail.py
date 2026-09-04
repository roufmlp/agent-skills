#!/usr/bin/env python3
"""Tests for draw_run_rail.py. Run: python3 test_draw_run_rail.py

The reason this file exists at all: the human ruled on 2026-09-04
that the rail comes from a checked-in script rather than from prose in
`finale.md`. The drawn shape is computed geometry — eight columns, a floor row,
a legend, and two assertions that refuse a card whose sentence will not fit —
and a subagent briefed in prose cannot assert. So the geometry lives here, in
code, with its assertions, and the finale runs it.

The shape is copied from a hand-run drawing script in the project this was
written for, which the human read on 2026-09-03 and approved. Every constant
below matches it.
"""

import unittest

import check_run_picture as guard
import draw_run_rail as draw

STAGES_FILE = """# Run picture stages

| Key | Column | Source | Sentence |
|---|---|---|---|
| `workspace` | Workspace | invented here | The walk starts with a workspace. |
| `tender` | Create a tender | MAP journey 1 | Create a tender. |
| `quote` | Invite and quote | MAP journey 2 | Invite suppliers. |
| `award` | Compare and award | MAP journey 3 | Compare quotes. |
| `quotation` | Customer quotation | MAP journey 4 | Build the quotation. |
| `needs-you` | Needs-you queue | MAP journey 5 | Work the queue. |
| `zoho` | Zoho push and read | MAP journey 6 | Push to Zoho Books. |
| `catalogue` | Catalogue | MAP journey 7 | The catalogue. |
| `floor` | Under the floor | invented here | Anything no user sees. |
"""

TWO_ISSUE_BRIEFING = """# Merge briefing

## The run in one screen

| What              | Count | Detail lives at |
|-------------------|-------|-----------------|
| Shipped, unmerged |     2 | ## What shipped |

Shipped:      99b, 99e

## The run on the rail

Headline: The code goes out and the reply comes back, and nothing reads it yet.
Lit: quote

| Issue | Stage | Kind | Sentence                                |
|-------|-------|------|-----------------------------------------|
| 99b   | quote | new  | Supplier gets a code with the invite    |
| 99e   | floor | fix  | Token reader stops trusting the subject |
"""


class TheColumnsComeFromTheVocabularyFile(unittest.TestCase):
    """Rule 1 of `docs/agents/run-picture-stages.md`: a skill reads that file and
    never hard-codes a stage key. The `Column` cell is the display text and the
    table order is the left-to-right order."""

    def test_eight_columns_in_the_files_order_and_floor_is_not_one(self):
        columns = draw.read_columns(STAGES_FILE)
        self.assertEqual(
            [key for key, _ in columns],
            ["workspace", "tender", "quote", "award", "quotation",
             "needs-you", "zoho", "catalogue"],
        )
        self.assertEqual(columns[6][1], "Zoho push and read")

    def test_a_file_with_no_table_reads_as_no_vocabulary(self):
        self.assertIsNone(draw.read_columns("# Run picture stages\n\nnothing here.\n"))


class ATwoCardRunDrawsTheWholeRail(unittest.TestCase):
    """Criterion 2. A small run makes a quiet picture, not a broken one.

    Every column is drawn unconditionally, so an empty column is the drawn shape
    rather than a hole, and the floor row and its caption are there whether or
    not anything sits under it.
    """

    def setUp(self):
        self.svg = draw.render(
            draw.spec_from_briefing(TWO_ISSUE_BRIEFING),
            draw.read_columns(STAGES_FILE),
        )

    def test_all_eight_column_headers_appear_in_order(self):
        labels = [label for _, label in draw.read_columns(STAGES_FILE)]
        at = [self.svg.index(label) for label in labels]
        self.assertEqual(at, sorted(at))

    def test_the_floor_line_and_its_caption_appear(self):
        self.assertIn("Under the floor", self.svg)
        self.assertIn("stroke-dasharray", self.svg)

    def test_the_headline_appears(self):
        self.assertIn("The code goes out and the reply comes back", self.svg)

    def test_exactly_two_cards_sit_among_them(self):
        self.assertEqual(len(guard.read_board_cards(self.svg)), 2)

    def test_the_guard_reads_back_what_the_briefing_said(self):
        """The round trip is the whole contract: this script draws, and
        `check_run_picture.py` reads what it drew."""
        ok, reason = guard.compare_cards(
            guard.read_block_cards(TWO_ISSUE_BRIEFING),
            guard.read_board_cards(self.svg),
            stages={key for key, _ in draw.read_columns(STAGES_FILE)} | {"floor"},
        )
        self.assertTrue(ok, reason)


class ASentenceThatCannotBeDrawnStopsTheFinale(unittest.TestCase):
    """Criterion 5, and the whole reason the human ruled a script rather than prose.

    `check_run_rail.py` refuses a sentence of 60 characters or more one step
    earlier. That bound is neither sufficient nor necessary, so it is a cheap
    upstream filter and this is the net that bites.
    """

    def test_the_measured_counter_example_is_refused(self):
        """57 characters, which SATISFIES the 59-character rule, and still needs
        four lines. Measured 2026-09-03 against the generator this copies."""
        sentence = "Database refuses an unauthorised workspace membership row"
        self.assertLess(len(sentence), 60)
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.wrap(sentence, draw.LINE_W, "486")
        self.assertIn("486", str(caught.exception))
        self.assertIn("4 lines", str(caught.exception))

    def test_a_single_word_wider_than_the_card_is_refused(self):
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.wrap("Supercalifragilisticexpialidocious", draw.LINE_W, "99z")
        self.assertIn("99z", str(caught.exception))
        self.assertIn("units", str(caught.exception))

    def test_a_sentence_that_fits_wraps_to_three_lines_or_fewer(self):
        lines = draw.wrap(
            "Admin is told a customer waits to be verified", draw.LINE_W, "516"
        )
        self.assertLessEqual(len(lines), draw.MAX_LINES)
        self.assertEqual(" ".join(lines),
                         "Admin is told a customer waits to be verified")

    def test_the_refusal_reaches_the_render_and_names_the_issue(self):
        briefing = TWO_ISSUE_BRIEFING.replace(
            "Supplier gets a code with the invite    ",
            "Database refuses an unauthorised workspace membership row",
        )
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.render(draw.spec_from_briefing(briefing),
                        draw.read_columns(STAGES_FILE))
        self.assertIn("99b", str(caught.exception))


class ARunThatShippedNothingDrawsAnHonestRail(unittest.TestCase):
    """Never a blank panel, which reads as a render that failed."""

    NOTHING = """## The run in one screen

| What              | Count | Detail lives at |
|-------------------|-------|-----------------|
| Shipped, unmerged |     0 | ## What shipped |

Shipped:      none

## The run on the rail

Headline: Nothing shipped. Both issues were blocked on a decision.
Lit: none

| Issue | Stage | Kind | Sentence |
|-------|-------|------|----------|
"""

    def test_it_draws_the_headline_the_columns_and_no_cards(self):
        svg = draw.render(draw.spec_from_briefing(self.NOTHING),
                          draw.read_columns(STAGES_FILE))
        self.assertIn("Nothing shipped.", svg)
        self.assertIn("Under the floor", svg)
        for _, label in draw.read_columns(STAGES_FILE):
            self.assertIn(label, svg)
        self.assertEqual(guard.read_board_cards(svg), {})


class TheLitStagesAreCopiedAndNeverWorkedOut(unittest.TestCase):
    """`Lit:` is a stated field. Measured on `batch-45c8b1`: `catalogue` is
    unlit while issue 485 shipped there, because 485 is a band chip and a chip
    lights nothing. A renderer that lit the columns holding cards would draw a
    different picture from the one the finale described."""

    def test_only_the_lit_column_carries_the_bordered_head(self):
        svg = draw.render(draw.spec_from_briefing(TWO_ISSUE_BRIEFING),
                          draw.read_columns(STAGES_FILE))
        self.assertEqual(svg.count('class="lit"'), 1)
        self.assertEqual(svg.count('class="box"'), 7 + 2)  # 7 unlit heads, 2 cards

    def test_a_stage_lit_with_no_card_is_still_lit(self):
        briefing = TWO_ISSUE_BRIEFING.replace("Lit: quote", "Lit: quote, zoho")
        svg = draw.render(draw.spec_from_briefing(briefing),
                          draw.read_columns(STAGES_FILE))
        self.assertEqual(svg.count('class="lit"'), 2)


class TheRailAddsSevenTokensTwice(unittest.TestCase):
    """`board.html` defines none of the seven, measured 2026-09-03. A token
    defined only in the light block is a card that vanishes into a dark
    background, so both blocks carry all seven."""

    def test_all_seven_are_in_both_blocks(self):
        seven = ["--new:", "--new-soft:", "--fix:", "--fix-soft:",
                 "--guard:", "--guard-soft:", "--chip-ink:"]
        for token in seven:
            self.assertIn(token, draw.TOKENS_LIGHT, token)
            self.assertIn(token, draw.TOKENS_DARK, token)

    def test_the_two_blocks_hold_different_values(self):
        self.assertNotEqual(draw.TOKENS_LIGHT, draw.TOKENS_DARK)


class TheLegendExplainsTheFourKinds(unittest.TestCase):
    """No issue in 550 to 556 owned the legend, and grepped 2026-09-04 the word
    appears in none of the seven files. Without it the four kind colours are
    unexplained, and this slice is what first draws a kind."""

    def test_the_four_kind_labels_are_drawn(self):
        svg = draw.render(draw.spec_from_briefing(TWO_ISSUE_BRIEFING),
                          draw.read_columns(STAGES_FILE))
        for label in ("New", "Fix", "Guard", "Harness"):
            self.assertIn(f">{label}</text>", svg)


class TheRailIsNotScaledBelowOneToOne(unittest.TestCase):
    """RULED by the human on 2026-09-04: "keep full width and scroll".

    `board.html` is `max-width: 720px` with 20px of padding each side, leaving
    680 units. 1040 into 680 is 0.65, which draws the 10-unit card text at 6.5
    CSS pixels and makes every width assertion above a statement about a
    coordinate space nobody sees.
    """

    def test_the_natural_width_is_the_1040_the_exploration_drew(self):
        columns = draw.read_columns(STAGES_FILE)
        width = draw.X0 * 2 + len(columns) * draw.W + (len(columns) - 1) * draw.G
        self.assertEqual(width, 1040)

    def test_the_css_floors_the_svg_at_its_natural_width_and_scrolls(self):
        css = draw.rail_css(1040)
        self.assertIn("min-width: 1040px", css)
        self.assertIn("overflow-x: auto", css)
        self.assertNotIn("width: 100%", css)

    def test_the_board_itself_never_scrolls_sideways(self):
        """Measured 2026-09-04 in a browser: the full-bleed rule built on
        `calc(50% - 50vw)` overshot the page by the scrollbar's width, 649
        against a 634-pixel body, and the whole board scrolled 8 pixels."""
        css = draw.rail_css(1040)
        self.assertIn("margin: 12px -20px 0", css)
        # A bleed built on viewport units overshoots by the scrollbar's width:
        # measured in a browser on 2026-09-04, 649 against a 634-pixel root,
        # and the whole board scrolled 7.5 pixels sideways.
        rules = "\n".join(
            line for line in css.splitlines()
            if line.strip().startswith(".") or line.strip().startswith("html")
        )
        self.assertNotIn("vw", rules)


class TheRefusalsFoundByTheReviewPass(unittest.TestCase):
    """Two inputs that crashed or misreported, found on 2026-09-04."""

    def test_a_vocabulary_of_one_column_refuses_rather_than_crashing(self):
        """`per_row = len(columns) - 1` was divided by with no guard, so a
        single non-floor column raised ZeroDivisionError and the finale got a
        traceback instead of a named refusal. That file is the human's to edit and
        its rule 1 says a stage is one row."""
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.render({"headline": "h", "lit": [], "cards": []},
                        [("workspace", "Workspace")])
        self.assertIn("column", str(caught.exception))

    def test_an_empty_sentence_is_refused_by_name_and_by_issue(self):
        """`check_run_rail.py` lets a blank `Sentence` cell through: it grades
        the cell count and the length, and a blank cell fails neither. The card
        then drew no lines and the board's guard refused it as bad markup, which
        sent the reader hunting an SVG fault one step away from the blank cell."""
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.wrap("   ", draw.LINE_W, "517")
        self.assertIn("517", str(caught.exception))
        self.assertIn("empty", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
