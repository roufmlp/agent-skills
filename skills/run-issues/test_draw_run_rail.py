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

    def test_the_css_draws_the_svg_at_its_natural_width_and_scrolls(self):
        """Was `min-width: 1040px`, which let the svg STRETCH to its container.
        On their ruling of 2026-09-05 the container became the window, and a
        stretched rail would draw the card text larger than the size every
        bound in this file is measured at. The width is exact now."""
        css = draw.rail_css(1040)
        self.assertIn("width: 1040px", css)
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



# --------------------------------------------------------------------------
# Issue 554. Two more card shapes reach the picture: a dashed card for an issue
# the run left open, and an amber card for a question waiting on the human.
# --------------------------------------------------------------------------

BRIEFING_554 = TWO_ISSUE_BRIEFING + """
### Minted and left open

| Issue | Stage | Sentence                                |
|-------|-------|-----------------------------------------|
| 99f   | quote | Nothing reads the code yet              |
| 525   | floor | A gate writes a row nothing later reads |

### Forks waiting on you

| Fork | Stage | Question                                    |
|------|-------|---------------------------------------------|
| F1   | quote | How much of a reply may advance an order?   |
| F2   | floor | Refuse an untracked paste file?             |
"""


def columns():
    return draw.read_columns(STAGES_FILE)


def board_554():
    return draw.render(draw.spec_from_briefing(BRIEFING_554), columns())


class TheHolesAndTheQuestionsAreDrawn(unittest.TestCase):
    """Issue 554, criteria 1 and 2. The script transcribes both tables the same
    way it transcribes the shipped one: the stage, the key and the text are
    copied, and the only thing computed is where a line breaks."""

    def test_the_spec_carries_both_tables_apart(self):
        spec = draw.spec_from_briefing(BRIEFING_554)
        self.assertEqual([c["issue"] for c in spec["cards"]], ["99b", "99e"])
        self.assertEqual([c["issue"] for c in spec["minted"]], ["99f", "525"])
        self.assertEqual([c["issue"] for c in spec["forks"]], ["F1", "F2"])

    def test_every_card_reaches_the_board_under_its_own_shape(self):
        cards = guard.read_board_cards(board_554())
        self.assertEqual(cards["99b"].shape, "shipped")
        self.assertEqual(cards["99f"].shape, "minted")
        self.assertEqual(cards["F1"].shape, "fork")

    def test_a_hole_is_drawn_dashed_and_a_question_amber(self):
        """The two treatments the legend explains. A dashed stroke says the
        work is not there; amber says it waits on the human.

        The treatment is a class and the CSS carries it, exactly as the four
        kind colours do. Asserting the dash inline would pin the drawing to a
        shape 553 deliberately did not take.
        """
        svg = board_554()
        hole = svg[svg.index('data-card="99f"'):]
        self.assertIn('class="hole"', hole[:hole.index("</g>")])
        fork = svg[svg.index('data-card="F1"'):]
        self.assertIn('class="waits"', fork[:fork.index("</g>")])
        css = draw.rail_css(1040)
        self.assertIn("stroke-dasharray", css[css.index(".rail .hole"):])
        self.assertIn("var(--fork)", css[css.index(".rail .waits"):])

    def test_a_hole_and_a_question_carry_their_stage(self):
        cards = guard.read_board_cards(board_554())
        self.assertEqual(cards["99f"].stage, "quote")
        self.assertEqual(cards["525"].stage, "floor")
        self.assertEqual(cards["F2"].stage, "floor")

    def test_the_board_the_script_draws_passes_the_board_guard(self):
        """The two halves of this slice meet here. Anything the script draws
        that the guard would refuse is a fault in one of them."""
        ok, why = guard.compare_cards(
            guard.read_block_cards(BRIEFING_554),
            guard.read_board_cards(board_554()),
            stages=set(k for k, _ in columns()) | {"floor"},
        )
        self.assertTrue(ok, why)

    def test_a_question_too_long_for_its_box_stops_the_render(self):
        """The assertion is the reason this is a script. A question that would
        reach the browser clipped stops the finale here, with the fork named."""
        # One word wider than the line. A greedy wrap cannot break it, so the
        # width test is what catches it, and shortening it is the finale's job.
        long = BRIEFING_554.replace(
            "How much of a reply may advance an order?",
            "Antidisestablishmentarianismisation" + "x" * 20,
        )
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.render(draw.spec_from_briefing(long), columns())
        self.assertIn("F1", str(caught.exception))

    def test_the_legend_explains_all_six_shapes(self):
        """The seam pass put the dashed and amber halves here: this slice is
        what first draws them, so it is what has to explain them. 553 drew the
        four kind circles for the same reason."""
        svg = board_554()
        legend = svg[svg.rindex("Harness") - 400:]
        for word in ("New", "Fix", "Guard", "Harness", "Open", "Waits"):
            with self.subTest(word=word):
                self.assertIn(word, legend)

    def test_a_run_with_neither_table_draws_neither_shape(self):
        """Criterion 8. The pre-554 briefing still draws, and draws nothing
        this slice added."""
        svg = draw.render(draw.spec_from_briefing(TWO_ISSUE_BRIEFING), columns())
        cards = guard.read_board_cards(svg)
        self.assertEqual(sorted(cards), ["99b", "99e"])
        self.assertNotIn('data-shape="minted"', svg)
        self.assertNotIn('data-shape="fork"', svg)

    def test_the_amber_token_is_defined_in_both_colour_blocks(self):
        """A token defined only in the light block is a card that vanishes into
        a dark background, which is why 553 emits both, always."""
        self.assertIn("--fork:", draw.TOKENS_LIGHT)
        self.assertIn("--fork:", draw.TOKENS_DARK)

# --------------------------------------------------------------------------
# Issue 555. The band is the highest-judgement thing on the picture and the
# renderer makes none of it: it draws the strip the block states, over the
# columns the block names, holding the words the block wrote.
# --------------------------------------------------------------------------

BANDED_BRIEFING = TWO_ISSUE_BRIEFING + """
### Bands

| Band | Stages         | Kind  | Issues   | Caption                    | Seats                          |
|------|----------------|-------|----------|----------------------------|--------------------------------|
| B1   | workspace..quote | guard | 99b 99e  | The code goes out and back | admin ok, member ok, viewer no |

### Band chips

| Band | Issue | Text            |
|------|-------|-----------------|
| B1   | 99b   | code with it    |
| B1   | 99e   | subject unread  |
"""


class ABandIsDrawnOverTheColumnsTheBlockNames(unittest.TestCase):
    """Criterion 2. The span and the issues are attributes the board's guard
    reads back, in the shape it can read: on an element that opens and closes,
    never on a self-closing `<rect/>`."""

    def setUp(self):
        self.columns = draw.read_columns(STAGES_FILE)
        self.spec = draw.spec_from_briefing(BANDED_BRIEFING)
        self.svg = draw.render(self.spec, self.columns)

    def test_the_band_carries_its_span_and_its_issues(self):
        bands = guard.read_board_bands(self.svg)
        self.assertEqual(list(bands), ["B1"])
        self.assertEqual(bands["B1"].stages, "workspace..quote")
        self.assertEqual(bands["B1"].issues, ("99b", "99e"))

    def test_every_member_draws_a_chip_with_its_own_words(self):
        bands = guard.read_board_bands(self.svg)
        self.assertEqual(bands["B1"].chips["99b"], ("code with it",))
        self.assertEqual(bands["B1"].chips["99e"], ("subject unread",))

    def test_a_band_member_is_not_also_drawn_as_a_card(self):
        """Criterion 8, measured disjoint on all five drawn runs: nine cards
        plus seven chips make `batch-45c8b1`'s sixteen."""
        self.assertEqual(guard.read_board_cards(self.svg), {})

    def test_the_board_guard_accepts_what_this_script_drew(self):
        ok, reason = guard.compare_cards(
            guard.read_block_cards(BANDED_BRIEFING),
            guard.read_board_cards(self.svg),
            stages=draw.check_run_rail.read_stages(STAGES_FILE),
            bands=guard.read_board_bands(self.svg),
        )
        self.assertTrue(ok, reason)

    def test_the_seat_pills_draw_where_the_row_states_them(self):
        self.assertIn("admin ✓", self.svg)
        self.assertIn("member ✓", self.svg)
        self.assertIn("viewer ✕", self.svg)

    def test_no_seats_cell_draws_no_pills(self):
        bare = BANDED_BRIEFING.replace("| admin ok, member ok, viewer no |", "|  |")
        svg = draw.render(draw.spec_from_briefing(bare), self.columns)
        self.assertNotIn("admin ✓", svg)
        self.assertNotIn("viewer", svg)


class ARunWithNoBandDrawsNone(unittest.TestCase):
    """Two of the five drawn runs are this case and it is the normal one. A
    picture that must always find a subject will invent one."""

    def test_the_two_issue_run_draws_no_band_and_still_draws_its_cards(self):
        svg = draw.render(
            draw.spec_from_briefing(TWO_ISSUE_BRIEFING), draw.read_columns(STAGES_FILE)
        )
        self.assertEqual(guard.read_board_bands(svg), {})
        self.assertEqual(sorted(guard.read_board_cards(svg)), ["99b", "99e"])


class TwoBandsStackRatherThanCollide(unittest.TestCase):
    """Criterion 9. An overlapping span is the normal case, on two of the three
    banded runs: `batch-375cbf` has `award..zoho` wholly inside
    `workspace..catalogue`. The generator stacks them in the table's row order."""

    TWO = BANDED_BRIEFING.replace(
        "| B1   | workspace..quote | guard | 99b 99e  "
        "| The code goes out and back | admin ok, member ok, viewer no |",
        "| B1   | workspace..quote | guard | 99b      "
        "| The code goes out and back | admin ok, member ok, viewer no |\n"
        "| B2   | workspace..tender | fix  | 99e      "
        "| Nothing reads it yet       |                                |",
    ).replace(
        "| B1   | 99e   | subject unread  |", "| B2   | 99e   | subject unread  |"
    )

    def test_both_draw_and_neither_overlaps_the_other(self):
        svg = draw.render(
            draw.spec_from_briefing(self.TWO), draw.read_columns(STAGES_FILE)
        )
        bands = guard.read_board_bands(svg)
        self.assertEqual(sorted(bands), ["B1", "B2"])
        tops = [
            float(svg.split(f'data-band="{key}"')[1].split('y="')[1].split('"')[0])
            for key in ("B1", "B2")
        ]
        self.assertGreaterEqual(tops[1] - tops[0], draw.BAND_H)


class AChipThatWillNotFitStopsTheRender(unittest.TestCase):
    """The same rule a card's sentence obeys, against a budget that is computed
    rather than fixed. Prose cannot assert; this is why the render is a script."""

    def test_a_chip_line_too_wide_for_its_band_is_refused(self):
        bad = BANDED_BRIEFING.replace(
            "| code with it    |", "| a chip line far too long for its band |"
        )
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.render(draw.spec_from_briefing(bad), draw.read_columns(STAGES_FILE))
        self.assertIn("99b", str(caught.exception))


class TheCaptionIsMeasuredAtItsOwnSize(unittest.TestCase):
    """The caption draws in `tb`, 12.5px bold, and every other string on the
    rail draws in `tv`, 10px regular. Measuring the caption at the card's glyph
    under-reads it by a quarter, and the drawn line then runs under the first
    chip. Seen in a browser on 2026-09-05 on `batch-45c8b1`'s own band, whose
    caption wrapped to a single 37-character line where the generator's author
    had split it into 24 and 19.
    """

    def test_the_caption_glyph_is_wider_than_the_card_glyph(self):
        self.assertGreater(draw.CAPTION_PX, draw.PX)

    def test_the_caption_never_reaches_the_first_chip(self):
        caption = "Viewer, on every screen, can no longer write"
        layout, cw, budget = draw.band_layout(8, 8, caption)
        self.assertEqual(layout, "left")
        lines = draw._greedy(caption, cw - 24, px=draw.CAPTION_PX)
        self.assertLessEqual(len(lines), draw.CAPTION_LINES)
        for line in lines:
            with self.subTest(line=line):
                self.assertLessEqual(len(line) * draw.CAPTION_PX, cw - 24)


class TheHeadlineIsMeasuredAtItsOwnSize(unittest.TestCase):
    """The headline draws in `thl`, 15px semibold, and is measured against the
    rail's width. Measuring it at the card's 10px glyph under-reads it by half.

    Seen in a browser on 2026-09-05 on run `batch-b5e96d`, whose headline is 186
    characters: 1004 units at the card's glyph, which passes, and about 1507 at
    its own, which does not. The assertion passed and the browser drew the last
    third of the sentence off the edge of the picture. This is the same fault
    the caption carried, in the one place left that measures a larger class.
    """

    LONG = (
        "The product can now read the PDFs its customers and suppliers actually "
        "send, on every road that receives one. What a person then does with the "
        "row it raises is where this batch was weakest."
    )

    def test_the_headline_glyph_is_wider_than_the_card_glyph(self):
        self.assertGreater(draw.HEADLINE_PX, draw.PX)

    def test_a_headline_that_would_draw_off_the_edge_is_refused(self):
        briefing = TWO_ISSUE_BRIEFING.replace(
            "Headline: The code goes out and the reply comes back, and nothing reads it yet.",
            f"Headline: {self.LONG}",
        )
        with self.assertRaises(draw.WillNotFit) as caught:
            draw.render(
                draw.spec_from_briefing(briefing), draw.read_columns(STAGES_FILE)
            )
        self.assertIn("headline", str(caught.exception))

    def test_a_headline_that_fits_still_passes(self):
        svg = draw.render(
            draw.spec_from_briefing(TWO_ISSUE_BRIEFING), draw.read_columns(STAGES_FILE)
        )
        self.assertIn("nothing reads it yet", svg)


class TheRailTakesTheWindowsWidthNotTheReadingColumns(unittest.TestCase):
    """the human, 2026-09-05: "cant we make it full width?"

    His ruling of 2026-09-04 was scroll rather than shrink, and that stands.
    What did not work is that the rail only ever reclaimed the board's own 20
    pixels of padding, so it drew at 720 pixels whatever the size of the
    window. On a 1400-pixel monitor the whole 1040-unit rail fits with room to
    spare and the board still made them scroll.

    The fix moves the 720-pixel reading column off `body` and on to each of
    body's other children, so the rail's container is the page. No viewport
    unit is used anywhere: the earlier attempt at this was built on
    `calc(50% - 50vw)` and overshot by the scrollbar's width, because `50vw`
    counts it and `50%` does not.
    """

    def test_the_reading_column_moves_from_the_body_to_its_other_children(self):
        css = draw.rail_css(1040)
        self.assertIn("body { max-width: none", css)
        self.assertIn("body > *:not(.rail-bleed)", css)
        # 680 is what the old rule gave the prose: a 720-pixel body less its
        # own 20 pixels of padding each side. The column must not change width.
        self.assertIn("max-width: 680px", css)

    def test_the_svg_draws_at_its_natural_width_and_is_centred(self):
        css = draw.rail_css(1040)
        self.assertIn("width: 1040px", css)
        self.assertIn("margin-inline: auto", css)
        self.assertIn("overflow-x: auto", css)

    def test_no_rule_uses_a_viewport_unit(self):
        """The regression this replaces. Measured in a browser on 2026-09-04:
        649 against a 634-pixel root, and the whole board scrolled sideways."""
        rules = "\n".join(
            line for line in draw.rail_css(1040).splitlines()
            if line.strip().startswith((".", "html", "body"))
        )
        self.assertNotIn("vw", rules)
        self.assertNotIn("vh", rules)

    def test_the_vertical_rhythm_is_untouched(self):
        """`body` stays in normal block flow. A grid would have been the other
        road to a full-bleed child, and it stops adjacent margins collapsing,
        which loosens the spacing of every heading on the board — a change they
        did not ask for."""
        rules = "\n".join(
            line for line in draw.rail_css(1040).splitlines()
            if line.strip().startswith((".", "html", "body"))
        )
        self.assertNotIn("display: grid", rules)
        self.assertNotIn("margin-block", rules)


if __name__ == "__main__":
    unittest.main()
