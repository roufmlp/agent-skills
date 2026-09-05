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

**The human ruled the slug on 2026-09-01, for this guard.** The alternative was an alias
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
from dataclasses import dataclass, field
from html.parser import HTMLParser

import check_run_rail
import draw_run_rail

BLOCK_HEADING = "## The run in one screen"

# The three shapes this guard grades, each against its own table. A shape
# outside this tuple is counted and passed over, which is the forward door
# issue 553 left open and the reason its guard did not halt every run the day
# these two shipped. Whatever draws next needs the same door.
GRADED_SHAPES = ("shipped", "minted", "fork")

# A refusal that names a real disagreement between the two files exits 1, which
# the finale reads as "fix one of them and re-render". Everything else exits 2,
# meaning the guard could grade nothing, which is a different repair.
EXIT_ONE = (
    "disagrees",
    "not-in-the-block",
    "card-disagrees",
    "card-not-in-the-block",
    "card-in-a-band",
    "card-overflows",
    "bad-card-stage",
    "no-card",
    "band-not-in-the-block",
    "band-disagrees",
    "band-overflows",
    "chip-not-in-the-block",
    "no-band",
    "no-chip",
)

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


# --------------------------------------------------------------------------
# The rail's cards. Issue 553.
#
# The figure rules above and the card rules here are DELIBERATELY OPPOSITE in
# one place, and a later reader must not delete either as a mistake. The board
# may carry FEWER figures than the block and that passes, because the panel is
# a summary and a figure it leaves out is a choice. The rail is not a summary:
# every shipped issue the block names is drawn exactly once, so a row with no
# card is an issue that VANISHED from the picture the human reads first, and it is
# refused.
#
# `data-shape` is what keeps that rule from halting a future run. Issue 554
# adds minted cards and fork cards, whose keys have no row in the shipped
# table. Only `shipped` cards are graded here; every other shape is counted and
# passed over. An absent attribute reads as `shipped`.
#
# Issue 555 adds a `### Bands` table, and a band REPLACES the cards for the
# issues it names: on all five drawn runs the card set and the chip set are
# disjoint and their union is the shipped count. So a shipped row a band names
# owes no card, and a card for one is refused.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Card:
    """One card as the board draws it.

    `stage` and `kind` are ATTRIBUTES, and they are the only things compared
    against the block. The figure reader's rule that the number compared is the
    number DISPLAYED does not carry over: a card displays a sentence, not its
    stage, so there is no displayed value to check it against.

    `lines` is the card's drawn sentence, one string per `<text data-line=...>`
    element, and it is read for one purpose only — measuring whether the
    sentence fits the box. The card's issue chip is text inside the same
    container and is NOT one of them: counting it measured a three-line card as
    four on the sixteen-issue fixture, which refused a board the generator had
    just asserted was sound.
    """

    stage: str
    kind: str
    shape: str
    lines: tuple[str, ...] = ()


@dataclass
class BlockCards:
    """The rail block as the guard grades cards against it.

    Three tables, kept apart. Issue 552's rule refuses a row naming an issue
    that did not ship, and every row issue 554 adds names an issue that did not
    ship, so one flat dictionary keyed by issue number would make the two
    slices refuse each other on the first run that mints anything.
    """

    rows: dict[str, tuple[str, str]] = field(default_factory=dict)
    bands: set[str] = field(default_factory=set)
    minted: dict[str, str] = field(default_factory=dict)
    forks: dict[str, str] = field(default_factory=dict)
    # Issue 555. Each band row keyed by its `Band` cell, holding its `Stages`
    # cell and the ids of its `Issues` cell in the order it writes them.
    band_rows: dict[str, tuple[str, tuple[str, ...], str]] = field(
        default_factory=dict
    )

    @property
    def owed(self) -> dict[str, tuple[str, str]]:
        """The rows that owe a card: every shipped row no band names."""
        return {k: v for k, v in self.rows.items() if k not in self.bands}

    @property
    def minted_owed(self) -> dict[str, str]:
        """The holes that owe a card: every minted row no band names.

        A band may carry an issue the run left open — `batch-45c8b1`'s band
        carries `509` as a dashed chip — and that issue is then drawn inside
        the band and not as a card beneath it, exactly like a shipped member.
        """
        return {k: v for k, v in self.minted.items() if k not in self.bands}


def read_block_cards(text: str) -> BlockCards | None:
    """The rail block's rows keyed by issue, with its band membership.

    None where the briefing carries no rail block at all. The parse is
    `check_run_rail.read_rail`, so both guards read the block through one
    reader and cannot come to disagree about what it says.
    """
    rail = check_run_rail.read_rail(text)
    if rail is None:
        return None
    rows = {
        cells[0]: (cells[1], cells[2]) for cells in rail.rows if len(cells) >= 3
    }
    at = check_run_rail.BAND_ISSUES_AT
    cap = check_run_rail.BANDS_HEADER.index("caption")
    return BlockCards(
        rows=rows,
        bands=rail.bands,
        minted={c[0]: c[1] for c in rail.minted if len(c) >= 2},
        forks={c[0]: c[1] for c in rail.forks if len(c) >= 2},
        band_rows={
            c[0]: (c[1], tuple(check_run_rail._band_ids(c[at])), c[cap])
            for c in rail.band_rows
            if len(c) > cap
        },
    )


class _CardReader(HTMLParser):
    """Every `data-card` element's attributes and its drawn lines.

    A self-closing carrier is refused rather than read. Measured 2026-09-03:
    `HTMLParser` turns `<rect data-card="517"/>` into a start tag immediately
    followed by an end tag, so a reader built like `_FigureReader` sees an empty
    card. The generator's own card shapes ARE self-closing rects, so the
    attributes go on the `<g>` that wraps them and this reader says so out loud
    rather than reporting a card with no text.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: dict[str, Card] = {}
        self._key: str | None = None
        self.open_key: str | None = None
        self._depth = 0
        self._attrs: dict[str, str] = {}
        self._lines: list[str] = []
        self._text: list[str] | None = None

    @staticmethod
    def _carrier(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: (value or "").strip() for name, value in attrs}

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """A self-closing tag nests nothing, so it must not move the depth.

        The base class calls `handle_starttag` then `handle_endtag`, which would
        close an open card on the first `<rect/>` inside it.
        """
        found = self._carrier(attrs)
        if found.get("data-card"):
            raise ValueError(
                f"data-card={found['data-card']!r} sits on a self-closing "
                f"<{tag}/>, which wraps nothing; it goes on the container "
                f"element that holds the card's shapes and text"
            )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = self._carrier(attrs)
        if self._key is not None:
            if found.get("data-card"):
                raise ValueError(
                    f"data-card={found['data-card']!r} sits inside the element "
                    f"carrying data-card={self._key!r}; cards do not nest"
                )
            if tag.lower() not in VOID_TAGS:
                self._depth += 1
            if tag.lower() == "text" and "data-line" in found:
                self._text = []
            return
        if found.get("data-card"):
            self._key = found["data-card"]
            self.open_key = self._key
            self._depth, self._attrs, self._lines, self._text = 0, found, [], None

    def handle_endtag(self, tag: str) -> None:
        if self._key is None:
            return
        if tag.lower() == "text" and self._text is not None:
            self._lines.append("".join(self._text).strip())
            self._text = None
        if self._depth:
            self._depth -= 1
            return
        self.cards[self._key] = Card(
            stage=self._attrs.get("data-stage", ""),
            kind=self._attrs.get("data-kind", ""),
            shape=self._attrs.get("data-shape", "") or "shipped",
            lines=tuple(self._lines),
        )
        self._key = None
        self.open_key = None

    def handle_data(self, data: str) -> None:
        if self._text is not None:
            self._text.append(data)


def read_board_cards(html: str) -> dict[str, Card]:
    """Every `data-card` element on the board, keyed by the attribute verbatim.

    The key is never parsed as a number. Issue 554's fork cards are keyed `F1`
    and `F4`, which are `## Decide` item ids, and a reader that expected digits
    would refuse them.

    Raises ValueError where a card carries no readable markup, which exits 2 for
    the same reason `read_board_figures` does: a card the reader silently loses
    looks exactly like a card the render never drew.
    """
    reader = _CardReader()
    reader.feed(html)
    reader.close()
    if reader.open_key is not None:
        raise ValueError(
            f"the element carrying data-card={reader.open_key!r} never closed"
        )
    # Every GRADED shape, and no other. `compare_cards` measures these three
    # against their boxes, so a card of one whose lines cannot be found cannot
    # be measured. A shape outside the three is passed over: raising on it
    # would defeat `data-shape` one function early, which is what would have
    # halted every run at exit 2 the day issue 554's cards shipped.
    unmarked = [
        key for key, card in reader.cards.items()
        if card.shape in GRADED_SHAPES and not card.lines
    ]
    if unmarked:
        raise ValueError(
            f"card {unmarked[0]!r} marks no sentence line; each line of the "
            f"sentence carries data-line, and a graded card whose lines "
            f"cannot be found cannot be measured against its box"
        )
    return reader.cards


@dataclass(frozen=True)
class Band:
    """One band as the board draws it.

    `stages` is the `Stages` cell verbatim and `issues` the ids of the `Issues`
    cell in the order it writes them. `chips` is each chip's drawn lines, keyed
    by issue, and it is read for one purpose: measuring the words against the
    space the band's own arithmetic gives them.
    """

    stages: str
    issues: tuple[str, ...]
    chips: dict[str, tuple[str, ...]] = field(default_factory=dict)


class _BandReader(HTMLParser):
    """Every `data-band` element, its attributes and the chips inside it.

    Measured 2026-09-03 against the live readers in this file, and both
    findings are enforced here rather than written down and hoped for:
    `read_board_figures('<svg><rect data-figure="a" width="5"/></svg>')` raises
    `no number in ''`, so a self-closing carrier is refused; and
    `'<div data-figure="a">7<span data-figure="b">9</span></div>'` returns
    `{'a': 79.0}`, silently concatenating the digits, so no `data-figure` may
    sit inside a band.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.bands: dict[str, Band] = {}
        self._key: str | None = None
        self.open_key: str | None = None
        self._depth = 0
        self._attrs: dict[str, str] = {}
        self._chips: dict[str, list[str]] = {}
        self._chip: str | None = None
        self._text: list[str] | None = None

    @staticmethod
    def _found(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: (value or "").strip() for name, value in attrs}

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        found = self._found(attrs)
        if found.get("data-band"):
            raise ValueError(
                f"data-band={found['data-band']!r} sits on a self-closing "
                f"<{tag}/>, which wraps nothing; it goes on the container "
                f"element that holds the band's shapes, caption and chips"
            )
        if self._key is not None and "data-figure" in found:
            raise ValueError(
                f"data-figure={found['data-figure']!r} sits inside the band "
                f"{self._key!r}; the figure reader takes every nested "
                f"data-figure and concatenates their digits, so a band holds none"
            )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = self._found(attrs)
        if self._key is not None:
            if "data-figure" in found:
                raise ValueError(
                    f"data-figure={found['data-figure']!r} sits inside the band "
                    f"{self._key!r}; the figure reader takes every nested "
                    f"data-figure and concatenates their digits, so a band "
                    f"holds none"
                )
            if found.get("data-band"):
                raise ValueError(
                    f"data-band={found['data-band']!r} sits inside the element "
                    f"carrying data-band={self._key!r}; bands do not nest"
                )
            if tag.lower() not in VOID_TAGS:
                self._depth += 1
            if found.get("data-chip"):
                self._chip = found["data-chip"]
                self._chips.setdefault(self._chip, [])
            if tag.lower() == "text" and "data-line" in found:
                self._text = []
            return
        if found.get("data-band"):
            self._key = found["data-band"]
            self.open_key = self._key
            self._depth, self._attrs = 0, found
            self._chips, self._chip, self._text = {}, None, None

    def handle_endtag(self, tag: str) -> None:
        if self._key is None:
            return
        if tag.lower() == "text" and self._text is not None:
            if self._chip is not None:
                self._chips[self._chip].append("".join(self._text).strip())
            self._text = None
        if self._depth:
            self._depth -= 1
            if self._depth == 0:
                self._chip = None
            return
        self.bands[self._key] = Band(
            stages=self._attrs.get("data-stages", ""),
            issues=tuple(self._attrs.get("data-issues", "").split()),
            chips={k: tuple(v) for k, v in self._chips.items()},
        )
        self._key = None
        self.open_key = None

    def handle_data(self, data: str) -> None:
        if self._text is not None:
            self._text.append(data)


def read_board_bands(html: str) -> dict[str, Band]:
    """Every `data-band` element on the board, keyed by the attribute verbatim.

    Raises ValueError where a band carries markup this guard cannot read, which
    exits 2 for the same reason the figure and card readers do: a band the
    reader silently loses looks exactly like a band the render never drew.
    """
    reader = _BandReader()
    reader.feed(html)
    reader.close()
    if reader.open_key is not None:
        raise ValueError(
            f"the element carrying data-band={reader.open_key!r} never closed"
        )
    return reader.bands


def _drawn_badly(key: str, card: Card, stages: list[str] | None) -> str | None:
    """What is wrong with the card as DRAWN, before any table is consulted.

    Stage vocabulary and box measurement apply to all three shapes: a dashed
    card and an amber card draw text exactly as a shipped one does, so a
    sentence that would reach the browser clipped is refused on any of them.
    """
    if stages is not None and card.stage not in stages:
        return (
            f"bad-card-stage: the board draws {key} on `{card.stage}`, "
            f"which is not a stage in the vocabulary; the key is the "
            f"`Key` cell of docs/agents/run-picture-stages.md verbatim and "
            f"never the column name slugged"
        )
    if len(card.lines) > draw_run_rail.MAX_LINES:
        return (
            f"card-overflows: the board draws {key} on {len(card.lines)} "
            f"lines and a card holds {draw_run_rail.MAX_LINES}; the "
            f"sentence is shortened in the rail block, never here"
        )
    for line in card.lines:
        need = len(line) * draw_run_rail.PX
        if need > draw_run_rail.LINE_W:
            return (
                f"card-overflows: the board draws {key}'s line "
                f"{line!r} at {need:.0f} units and the card gives "
                f"{draw_run_rail.LINE_W}; it would reach the browser "
                f"clipped"
            )
    return None


def _compare_stage_only(
    shape: str,
    table: str,
    rows: dict[str, str],
    board: dict[str, Card],
    stages: list[str] | None,
) -> str | None:
    """Grade one shape whose table carries an issue, a stage and a text.

    Issue 554's two tables both take this form, and neither has a `Kind`
    column: a hole has no diff to have a kind of, and neither does a question.
    Grading one would demand a column that does not exist.

    Every row owes a card and every card owes a row. There is no band rule
    here: a band replaces the cards for the SHIPPED issues it spans, and a hole
    or a fork is not one of them.
    """
    drawn = {key: card for key, card in board.items() if card.shape == shape}
    for key, card in sorted(drawn.items()):
        bad = _drawn_badly(key, card, stages)
        if bad is not None:
            return bad
        stage = rows.get(key)
        if stage is None:
            return (
                f"card-not-in-the-block: the board draws {key} as a {shape} "
                f"card on `{card.stage}` and the rail's `{table}` table holds "
                f"no row for it, so the render derived it"
            )
        if card.stage != stage:
            return (
                f"card-disagrees: the board draws {shape} card {key} on "
                f"`{card.stage}` and its `{table}` row reads `{stage}`"
            )
    missing = [key for key in rows if key not in drawn]
    if missing:
        return (
            f"no-card: {', '.join(sorted(missing))} under `{table}` and not "
            f"drawn on the board; every row in that table is drawn exactly "
            f"once, and a row with no card is a thing that vanished from the "
            f"picture"
        )
    return None


def _compare_bands(
    block: BlockCards,
    bands: dict[str, Band],
    stages: list[str] | None,
) -> str | None:
    """Whether every band drawn agrees with the row it was copied from.

    The band is where the run's whole story lands when it has one, so both
    directions bite: a band on the board with no row is a subject the render
    INVENTED, and a row with no band is the story missing from the picture.

    The `Stages` cell is compared verbatim and the `Issues` cell as its list of
    ids in order. Spacing inside a markdown cell is the writer's, and a rule
    that made a wider column a refusal would refuse a correct briefing.
    """
    for key, band in sorted(bands.items()):
        row = block.band_rows.get(key)
        if row is None:
            return (
                f"band-not-in-the-block: the board draws band {key} over "
                f"`{band.stages}` and the rail's `{check_run_rail.BANDS_HEADING}` "
                f"table holds no row for it, so the render derived it"
            )
        span, issues, caption = row
        if band.stages != span:
            return (
                f"band-disagrees: the board draws band {key} over "
                f"`{band.stages}` and its row reads `{span}`"
            )
        if band.issues != issues:
            return (
                f"band-disagrees: the board draws band {key} over "
                f"{', '.join(band.issues) or 'no issues'} and its row names "
                f"{', '.join(issues)}"
            )
        drawn = set(band.chips)
        invented = sorted(drawn - set(issues))
        if invented:
            return (
                f"chip-not-in-the-block: the board draws {invented[0]} as a chip "
                f"inside band {key} and its row does not name it, so the render "
                f"put an issue in the run's story that the block does not"
            )
        for issue in issues:
            lines = band.chips.get(issue)
            if lines is None:
                return (
                    f"no-chip: band {key} names {issue} and the board draws no "
                    f"chip for it; the band is there and one of its members is "
                    f"not, so the issue vanished from the picture"
                )
            if stages is None:
                continue
            columns, why = check_run_rail._span(span, stages)
            if columns is None:
                continue
            budget = draw_run_rail.chip_width(
                len(columns), len(issues), caption
            )
            for line in lines:
                need = len(line) * draw_run_rail.PX
                if need > budget:
                    return (
                        f"band-overflows: the board draws {issue}'s chip line "
                        f"{line!r} at {need:.0f} units and the band gives "
                        f"{budget:.0f}; the space a chip has falls out of the "
                        f"band's span and its chip count, so shorten the text "
                        f"in `{check_run_rail.CHIPS_HEADING}`"
                    )
    missing = [key for key in block.band_rows if key not in bands]
    if missing:
        return (
            f"no-band: {', '.join(sorted(missing))} under "
            f"`{check_run_rail.BANDS_HEADING}` and not drawn on the board; a "
            f"band carries the run's story and a row with no band is that "
            f"story missing from the picture"
        )
    return None


def compare_cards(
    block: BlockCards | None,
    board: dict[str, Card],
    stages: list[str] | None,
    bands: dict[str, Band] | None = None,
) -> tuple[bool, str]:
    """Whether every card agrees with the row it was copied from.

    `stages` None means the repository has no `docs/agents/run-picture-stages.md`
    and the stage-vocabulary rule is not run, which is rule 4 of that file.
    """
    if block is None:
        return False, (
            f"no-rail: the briefing carries no `{check_run_rail.RAIL_HEADING}` "
            f"heading, so there is nothing for the cards to be checked against"
        )
    # **The bands are compared first**, because they decide which rows owe a
    # card at all. A board and a block that disagree about a band disagree
    # about every card under it too, and `no-card: 517, 516` on a run whose
    # band row was deleted names the symptom while the band names the cause.
    bad = _compare_bands(block, bands or {}, stages)
    if bad is not None:
        return False, bad

    shipped = {key: card for key, card in board.items() if card.shape == "shipped"}
    for key, card in sorted(shipped.items()):
        bad = _drawn_badly(key, card, stages)
        if bad is not None:
            return False, bad
        row = block.rows.get(key)
        if row is None:
            return False, (
                f"card-not-in-the-block: the board draws {key} on "
                f"`{card.stage}` and the rail holds no row for it, so the "
                f"render derived it"
            )
        if key in block.bands:
            return False, (
                f"card-in-a-band: the board draws {key} as a card and the "
                f"rail's `### Bands` table names it; a band member is drawn "
                f"once, as a chip inside its band, and never also as a card"
            )
        stage, kind = row
        if card.stage != stage:
            return False, (
                f"card-disagrees: the board draws {key} on `{card.stage}` and "
                f"its rail row reads `{stage}`"
            )
        if card.kind != kind:
            return False, (
                f"card-disagrees: the board draws {key} as kind `{card.kind}` "
                f"and its rail row reads `{kind}`"
            )
    missing = [key for key in block.owed if key not in shipped]
    if missing:
        return False, (
            f"no-card: {', '.join(missing)} on the rail and not drawn on the "
            f"board; every shipped row a band does not name is drawn exactly "
            f"once, and a row with no card is an issue that vanished from the "
            f"picture"
        )

    for shape, table, rows in (
        ("minted", check_run_rail.MINTED_HEADING, block.minted_owed),
        ("fork", check_run_rail.FORKS_HEADING, block.forks),
    ):
        bad = _compare_stage_only(shape, table, rows, board, stages)
        if bad is not None:
            return False, bad

    return True, (
        f"ok: {len(shipped)} of the block's {len(block.owed)} card-owing rail "
        f"rows are drawn on the board, with {len(block.minted_owed)} minted and "
        f"{len(block.forks)} fork cards and {len(block.band_rows)} bands beside "
        f"them, and every one agrees"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a board whose figures disagree with the briefing's block."
    )
    parser.add_argument("--briefing", required=True, help="path to merge-briefing.md")
    parser.add_argument("--board", required=True, help="path to board.html")
    parser.add_argument(
        "--stages",
        help="path to docs/agents/run-picture-stages.md in the repository the "
             "run is on; without it the stage-vocabulary rule is not run",
    )
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

    try:
        cards = read_board_cards(board_html)
    except ValueError as error:
        print(f"REFUSED unreadable-card: {error}", file=sys.stderr)
        return 2

    try:
        bands = read_board_bands(board_html)
    except ValueError as error:
        print(f"REFUSED unreadable-band: {error}", file=sys.stderr)
        return 2

    stages: list[str] | None = None
    graded = "NOT graded, no vocabulary"
    if args.stages:
        located = check_run_rail.locate_stages(args.stages)
        if located is None:
            print(
                f"no stage vocabulary at {args.stages}, here or under the git "
                f"top level: the stage rule is not run here, and everything "
                f"else is (rule 4 of run-picture-stages.md)"
            )
        else:
            stages = check_run_rail.read_stages(located.read_text())
            if stages is None:
                print(
                    f"REFUSED no-stages-table: {located} exists and holds no "
                    f"table headed `Key`, so the vocabulary cannot be read",
                    file=sys.stderr,
                )
                return 2
            graded = "graded"

    figures_ok, figures_why = compare(read_block_figures(briefing), board)
    cards_ok, cards_why = compare_cards(
        read_block_cards(briefing), cards, stages, bands
    )
    if figures_ok and cards_ok:
        print(figures_why)
        print(f"{cards_why}, stage keys {graded}")
        print(
            "It compared numbers, keys and drawn line widths and nothing else. "
            "A wrong sentence on a card, like a wrong sentence in a `why` "
            "line, is not one of them and passed here."
        )
        return 0
    worst = 0
    for ok, reason in ((figures_ok, figures_why), (cards_ok, cards_why)):
        if ok:
            continue
        print(f"REFUSED {reason}", file=sys.stderr)
        worst = max(worst, 1 if reason.startswith(EXIT_ONE) else 2)
    return worst


if __name__ == "__main__":
    sys.exit(main())
