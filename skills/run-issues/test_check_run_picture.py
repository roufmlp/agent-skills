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

    BLOCK = TheRealShapesAgree.BLOCK
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


if __name__ == "__main__":
    unittest.main()
