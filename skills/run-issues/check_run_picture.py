#!/usr/bin/env python3
"""Refuse a board whose figures disagree with the briefing's one-screen block.

Issue 506 item 6b. The finale runs this after the board is written, and a refusal
stops the finale.

**The block is the only place a figure is derived.** `## The run in one screen` at
the top of `merge-briefing.md` holds the run's counts in a markdown table. The
board's panel copies them and does no arithmetic of its own (item 6a). Before that
rule the renderer read 1963 lines, counted the bold issue headings under
`## What shipped`, noticed which of them also sat under `## Skipped or blocked`,
and subtracted. That is judgement, and judgement in a render is what this guard
and item 6c were both written for.

The contract between the two files is one slug and no vocabulary. A block row
labelled `Shipped, unmerged` becomes the key `shipped-unmerged`, and the board
carries the same key as `data-figure` on the element whose own text is the number:

    | Shipped, unmerged |     8 | ## What shipped |

    <div class="n" data-figure="shipped-unmerged">8</div>

The number compared is the number DISPLAYED, read out of that element rather than
from a second attribute, so a board cannot agree in its markup and lie on screen.

**the human ruled the slug on 2026-09-01, for this guard.** The alternative was an alias
table inside this file mapping each board label to a block row. The slug holds no
vocabulary of its own, so a renamed row moves both files together and a rename that
moves only one is refused as `not-in-the-block`. Pairing by POSITION was rejected
harder: a reordered panel compares the wrong pairs and can report a pass on a false
board, which is failure in silence. He ruled the pairing and nothing wider.
Wrapping the number in another tag is fine. The block ends at the next `## `
heading, so a number in the section after it is never read as one of its figures.

Five refusals, plus one for markup it cannot read:

    no-block          the briefing carries no one-screen block, so nothing anchors
    no-block-figures  the block is there and holds no readable figure
    no-figures        the board carries no data-figure at all, so the panel is gone
    not-in-the-block  the board shows a figure the block does not hold
    disagrees         both hold the figure and the numbers differ
    unreadable-figure a data-figure element holds no number, or never closes

**Nothing here reads a silence as a pass.** A figure the reader loses is worse
than one it refuses, because a board is ALLOWED to carry fewer figures than the
block: a dropped figure looks exactly like one the panel chose not to show, while
the wrong number stays on screen. So unreadable markup exits 2 rather than
quietly shrinking what gets compared.

**It catches numbers and nothing else.** A wrong sentence in a `why` line is not a
figure and passes. Saying so is the point: this guard is narrow on purpose and
must not be cited as cover for the prose.

The board may carry FEWER figures than the block, and that passes. The panel is a
summary and the briefing is the source of truth, so a figure the panel leaves out
is a choice; a figure it invents is a fault. Only the second direction is refused.

Exit 0 passes, 1 is a disagreement the finale must stop for, 2 means it could read
nothing. A pass prints how many figures it compared against how many the block
held, because an `ok` on four figures and an `ok` on none are different sentences
(`check_commit_order.py` printed the second one on run `414a-483-286335`).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from html.parser import HTMLParser

BLOCK_HEADING = "## The run in one screen"

# HTML sends no end tag for these, so counting one as a nesting level leaves the
# figure open for ever and swallows every figure after it. The reader then returns
# almost nothing and the run stops on a refusal naming the wrong fault.
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")


def read_block_figures(text: str) -> dict[str, float] | None:
    start = text.find(BLOCK_HEADING)
    if start < 0:
        return None
    rest = text[start + len(BLOCK_HEADING) :]
    end = rest.find("\n## ")
    body = rest if end < 0 else rest[:end]

    figures: dict[str, float] = {}
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        try:
            figures[slug(cells[0])] = float(cells[1].replace(",", ""))
        except ValueError:
            continue
    return figures


class _FigureReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.figures: dict[str, float] = {}
        self._key: str | None = None
        self.open_key: str | None = None
        self._depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._key is not None:
            if tag.lower() not in VOID_TAGS:
                self._depth += 1
            return
        for name, value in attrs:
            if name == "data-figure" and value:
                self._key, self._depth, self._text = value.strip(), 0, []
                self.open_key = self._key
                return

    def handle_endtag(self, tag: str) -> None:
        if self._key is None:
            return
        if self._depth:
            self._depth -= 1
            return
        self.figures[self._key] = _number("".join(self._text))
        self._key = None
        self.open_key = None

    def handle_data(self, data: str) -> None:
        if self._key is not None:
            self._text.append(data)


def _number(text: str) -> float:
    found = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not found:
        raise ValueError(f"no number in {text!r}")
    return float(found.group(0).replace(",", ""))


def read_board_figures(html: str) -> dict[str, float]:
    """Every `data-figure` element's own displayed number, keyed by its slug.

    Raises ValueError where an element carries the attribute and no readable
    number, or where one never closes. Both are silent losses otherwise, and a
    lost figure passes: the board is allowed to carry fewer figures than the
    block, so a dropped one is indistinguishable from one the panel omitted.
    """
    reader = _FigureReader()
    reader.feed(html)
    reader.close()
    if reader.open_key is not None:
        raise ValueError(
            f"the element carrying data-figure={reader.open_key!r} never closed"
        )
    return reader.figures


def compare(
    block: dict[str, float] | None, board: dict[str, float]
) -> tuple[bool, str]:
    if block is None:
        return False, (
            f"no-block: the briefing carries no `{BLOCK_HEADING}` heading, so "
            f"there is nothing for the board to be checked against"
        )
    if not block:
        return False, (
            f"no-block-figures: the briefing carries `{BLOCK_HEADING}` with no "
            f"readable figure under it, so there is nothing to check against"
        )
    if not board:
        return False, (
            "no-figures: the board carries no data-figure element, so the panel "
            "is missing or was rendered without its figure keys"
        )
    for key, shown in sorted(board.items()):
        if key not in block:
            return False, (
                f"not-in-the-block: the board shows {key} as {shown:g} and the "
                f"block holds no such figure, so the render derived it"
            )
        held = block[key]
        if held != shown:
            return False, (
                f"disagrees: the board shows {key} as {shown:g} and the block "
                f"holds {held:g}"
            )
    return True, (
        f"ok: {len(board)} of the block's {len(block)} figures are on the board "
        f"and every one agrees"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a board whose figures disagree with the briefing's block."
    )
    parser.add_argument("--briefing", required=True, help="path to merge-briefing.md")
    parser.add_argument("--board", required=True, help="path to board.html")
    args = parser.parse_args()

    try:
        briefing = pathlib.Path(args.briefing).read_text()
        board_html = pathlib.Path(args.board).read_text()
    except OSError as error:
        print(f"REFUSED unreadable: {error}", file=sys.stderr)
        return 2

    try:
        board = read_board_figures(board_html)
    except ValueError as error:
        print(f"REFUSED unreadable-figure: {error}", file=sys.stderr)
        return 2

    ok, reason = compare(read_block_figures(briefing), board)
    if ok:
        print(reason)
        print(
            "It compared numbers and nothing else. A wrong sentence in a `why` "
            "line is not a figure and passed here."
        )
        return 0
    print(f"REFUSED {reason}", file=sys.stderr)
    return 1 if reason.startswith(("disagrees", "not-in-the-block")) else 2


if __name__ == "__main__":
    sys.exit(main())
