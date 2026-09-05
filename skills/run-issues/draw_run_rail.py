#!/usr/bin/env python3
"""Draw the run's rail as one SVG, from the briefing's `## The run on the rail`.

**The human ruled on 2026-09-04 that the rail comes from this script and
not from prose in `finale.md`.** The drawn shape is computed geometry: eight
columns at a fixed pitch, a card of fixed width and height, a floor row, a
legend, and two assertions that refuse a sentence that will not fit its box. A
subagent briefed in prose cannot assert, so the one criterion saying the render
must FAIL rather than draw clipped text is true on this road and on no other.

The shape is a hand-run drawing script in the project this was written for,
drawn there on five real runs and approved by the human on 2026-09-03. Every
constant here matches that file.

**The script decides nothing.** It reads the block the finale wrote and draws
it. The stage, the kind and the sentence are all copied; the columns and their
order come from `docs/agents/run-picture-stages.md`, which rule 1 of that file
requires; the lit stages are the block's own `Lit:` line and are never worked
out from the cards. `finale.md` step 5's rule — the panel transcribes, it never
counts — covers cards because of this.

**The one thing it computes is where a sentence breaks**, and that is
arithmetic on a copied string rather than a judgement. It wraps greedily to the
card's width and asserts, so a sentence that cannot be drawn stops the finale
here with the issue named, instead of reaching a browser as clipped text.
`check_run_rail.py` refuses a sentence of 60 characters or more one step
earlier; that bound is a cheap filter and not the real one. Measured
2026-09-03: `Database refuses an unauthorised workspace membership row` is 57
characters, passes that filter, and wraps into four lines here.

The board's own guard, `check_run_picture.py`, measures the lines it finds
DRAWN on the board with the same arithmetic. That is not a duplicate of the
assertion below: it is what catches a board whose SVG was written by hand
instead of by this script.

Usage, from the repository root:

    python3 ~/.claude/skills/run-issues/draw_run_rail.py \\
        --briefing .scratch/<feature>/runs/<batch-id>/merge-briefing.md \\
        --stages docs/agents/run-picture-stages.md

It prints the SVG and the CSS tokens it needs to standard output, for the
renderer to paste into `board.html` above the run panel. Exit 2 means it could
draw nothing: no rail block, or no stage vocabulary. Exit 1 means a card would
not fit, and names the issue.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import check_run_rail

# Geometry, byte for byte from the drawing script this copies. A change to one number
# moves every picture, which is why they are here and not spread through the
# drawing functions.
X0, W, G = 5, 120, 10
CH = 66            # card height
PX = 5.4           # average glyph width at 10px, system sans, measured generously
MAX_LINES = 3
LINE_W = W - 12    # the text's own width inside a card
KIND = {"new": "c-new", "fix": "c-fix", "guard": "c-guard", "harness": "c-gray"}
# Issue 555. The band's wash, one per kind. A band takes the same four kinds a
# card does; `check_run_rail.py` refuses any other, and `harness` is the
# fallback here so a briefing that reached this script ungraded still draws.
BAND_KIND = {
    "new": "b-new", "fix": "b-fix", "guard": "b-guard", "harness": "b-harness",
}

# The nine tokens the rail adds. `board.html` defines none of them, measured
# 2026-09-03, and a token defined only in the light block is a card that
# vanishes into a dark background — so both blocks are emitted, always.
TOKENS_LIGHT = """  --new: #1a7f4b; --new-soft: #e6f4ec;
  --fix: #b3261e; --fix-soft: #fdecea;
  --guard: #6f42a1; --guard-soft: #f1ebfa;
  --fork: #a8690a; --fork-soft: #fdf2e2;
  --quiet-soft: #eef0f4;
  --chip-ink: #ffffff;"""
TOKENS_DARK = """  --new: #5cc48f; --new-soft: #16301f;
  --fix: #f2857c; --fix-soft: #2d1917;
  --guard: #b18cea; --guard-soft: #221a33;
  --fork: #e0a24a; --fork-soft: #2e2415;
  --quiet-soft: #20242c;
  --chip-ink: #12151c;"""

# The rail keeps its natural width and scrolls only when the window is narrower
# than it. RULED by the human on
# 2026-09-04: `board.html` is `max-width: 720px` with 20px of padding each
# side, leaving 680 units of content, and a 1040-unit rail scaled into that
# draws its 10-unit card text at 6.5 CSS pixels. They were asked and answered
# "keep full width and scroll". Only the rail is full-bleed; the rest of the
# board keeps its reading column.
_RAIL_CSS = """  /* The rail keeps its natural width and scrolls only when the WINDOW is
     narrower than it. RULED by the human on 2026-09-04: scaling 1040 units into
     the board's 680 draws the 10-unit card text at 6.5 CSS pixels, so scroll
     rather than shrink. WIDENED on their ruling of 2026-09-05: the rule below
     reclaimed the board's own 20px padding and nothing more, so the rail drew
     at 720 pixels whatever the size of the window, and a 1400-pixel monitor
     that could hold the whole picture still made them scroll.

     The 720-pixel reading column moves off `body` and on to each of body's
     OTHER children, so the rail's container is the page. 680px is what the old
     rule gave the prose — a 720px body less its own 20px of padding each side —
     so no column changes width and no card moves.

     Two roads were not taken, and both for a measured reason. A full bleed
     built on `calc(50% - 50vw)` overshoots: `50vw` counts the vertical
     scrollbar and `50%` does not, so the container drew 649 against a
     634-pixel root and the whole board scrolled 7.5 pixels sideways, measured
     in a browser on 2026-09-04. `html { overflow-x: clip }` did not stop it.
     Nothing here uses a viewport unit. And `body { display: grid }` with the
     rail spanning every column is the other way to a full-bleed child, but a
     grid stops adjacent margins collapsing, which loosens the spacing of every
     heading on the board — a change nobody asked for. `body` stays in normal
     block flow. */
  body { max-width: none; }
  body > *:not(.rail-bleed) { max-width: 680px; margin-inline: auto; }
  .rail-bleed { margin: 12px -20px 0; padding: 0 20px; overflow-x: auto; }
  /* Fixed at its natural width, never stretched: scaling UP past 1040 would
     draw the card text larger than the size every bound here is measured at.
     `margin-inline: auto` centres it where the window has room and resolves to
     zero where it does not, so an overflowing rail is never clipped on its
     left. */
  .rail-bleed svg { display: block; height: auto; width: {width}px; margin-inline: auto; }
  .rail .thl { font: 600 15px -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif; fill: var(--ink); letter-spacing: -0.01em; }
  .rail .tt { font: 600 11px -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif; fill: var(--ink); }
  .rail .tv { font: 400 10px -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif; fill: var(--ink); }
  .rail .ts { font: 500 10.5px ui-monospace, SFMono-Regular, Menlo, monospace; fill: var(--muted); }
  .rail .tn { font: 700 10px ui-monospace, SFMono-Regular, Menlo, monospace; fill: var(--chip-ink); }
  .rail .tb { font: 700 12.5px -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif; fill: var(--ink); }
  .rail .box { fill: var(--card); stroke: var(--line); stroke-width: 1.5; }
  .rail .lit { fill: var(--card); stroke: var(--ink); stroke-width: 1.5; }
  .rail .c-new { fill: var(--new); stroke: var(--new); }
  .rail .c-fix { fill: var(--fix); stroke: var(--fix); }
  .rail .c-guard { fill: var(--guard); stroke: var(--guard); }
  .rail .c-gray { fill: var(--quiet); stroke: var(--quiet); }
  /* Issue 554. A hole is the card outline with the work taken out of it, so it
     keeps the box fill and takes a dashed stroke; a question waits on the human, so
     it is amber filled. Both are explained in the legend. */
  .rail .hole { fill: var(--card); stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 5 4; }
  .rail .waits { fill: var(--fork-soft); stroke: var(--fork); stroke-width: 1.5; }
  .rail .c-fork { fill: var(--fork); stroke: var(--fork); }
  /* Issue 555. A band is one subject crossing several stages, so it is drawn
     as the subject's own colour washed under the columns it touches. Its
     chips keep their kind's full colour, which is what makes the strip read
     as a group of issues rather than as a coloured rectangle. */
  .rail .b-new { fill: var(--new-soft); stroke: var(--new); stroke-width: 1.5; }
  .rail .b-fix { fill: var(--fix-soft); stroke: var(--fix); stroke-width: 1.5; }
  .rail .b-guard { fill: var(--guard-soft); stroke: var(--guard); stroke-width: 1.5; }
  .rail .b-harness { fill: var(--quiet-soft); stroke: var(--quiet); stroke-width: 1.5; }
  .rail .tp { font: 600 9.5px -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif; }
  .rail .seat-ok { fill: var(--new-soft); }
  .rail .seat-no { fill: var(--fix-soft); }
  .rail .seat-dash { fill: var(--quiet-soft); }"""


def rail_css(width: int) -> str:
    """The board's CSS for the rail, floored at the rail's natural width.

    `%` formatting cannot be used here: the full-bleed rule carries
    `calc(50% - 50vw)`, and a stray format character in a stylesheet is a
    `ValueError` at the moment the finale needs the output.
    """
    return _RAIL_CSS.replace("{width}", str(width))


# Issue 555. A band's geometry, byte for byte from `def band(b, y)` in
# `34-picture-d-gen.py`.
BAND_H = 80          # the band's height, left-caption layout
BAND_GAP = 10        # between one band and the next
CAPTION_MIN = 140    # the narrowest caption column the generator sets
CAPTION_MAX = 240    # and the widest a computed one may reach
CHIP_PITCH = 135     # the widest a chip may be; few chips pack left
CHIP_MIN = 60        # below this beside the caption, the caption goes on top
CHIP_LINES = 2       # what fits between the chip row and the band's floor
CAPTION_LINES = 2    # the generator's captions are one line or two


def band_width(columns: int) -> int:
    """The drawn width of a band spanning `columns` adjacent rail columns."""
    return columns * W + (columns - 1) * G


# The caption draws in `tb`, 12.5px bold, where every other string on the rail
# draws in `tv` at 10px. Same generous ratio as `PX`, at the larger size.
CAPTION_PX = 6.75
# The headline draws in `thl`, 15px semibold, and is the widest class here.
# Measuring it at `PX` under-reads it by half: run `batch-b5e96d`'s 186-character
# headline came to 1004 units against a 1030-unit bound and drew its last third
# off the edge of the picture. Seen in a browser on 2026-09-05.
HEADLINE_PX = 8.1


def caption_width(caption: str) -> float:
    """The caption column's width, from the caption's own longest wrapped line.

    The generator carries this as a hand-set `caption_w` — 200, 210 and 140
    across its five bands. A hand-set number is one more judgement per band,
    and the caption is already in the block, so it is computed here instead.
    """
    lines = _greedy(caption, CAPTION_MAX - 24, px=CAPTION_PX)
    longest = max((len(line) for line in lines), default=0)
    return min(max(CAPTION_MIN, longest * CAPTION_PX + 24), CAPTION_MAX)


def band_layout(columns: int, chips: int, caption: str) -> tuple[str, float, float]:
    """The band's layout, its caption column, and the units one chip's text has.

    **A chip's budget is computed, and it is not the card's.** A card is fixed
    at `LINE_W`; a chip falls out of the band it sits in. Measured across the
    five drawn bands in `34-picture-d-gen.py`, it runs from 12.84 characters a
    line — the money band, three chips over two columns — to 23.15 on a
    two-chip band over eight. So a check that graded a chip against a fixed
    number would grade nothing, and the render and the board's guard both call
    this one function rather than each doing the arithmetic.

    The caption sits beside the chips where that leaves each chip `CHIP_MIN`
    units, and on top of them where it does not. That reproduces the
    generator's own choice on all five: its one `layout="top"` band is the
    two-column money band, whose chips would otherwise have 35 units between
    them, and its other four are `left`.
    """
    full = band_width(columns)
    cw = caption_width(caption)
    beside = min((full - cw - 6) / max(chips, 1), CHIP_PITCH) - 10
    if beside >= CHIP_MIN:
        return "left", cw, beside
    return "top", full, min((full - 12) / max(chips, 1), CHIP_PITCH) - 10


def chip_width(columns: int, chips: int, caption: str) -> float:
    """The units one chip's line has. See `band_layout`."""
    return band_layout(columns, chips, caption)[2]


class WillNotFit(Exception):
    """A card's sentence cannot be drawn. The finale stops and names the issue."""


def read_columns(text: str) -> list[tuple[str, str]] | None:
    """The rail's columns as `(key, label)`, left to right, `floor` excluded.

    Read from the `Key` table of `docs/agents/run-picture-stages.md`. The table
    order is the drawn order and the `Column` cell is the display text. `floor`
    is a row beneath the rail rather than a column, so it is dropped here and
    drawn separately. None where the file holds no such table.
    """
    lines = text.splitlines()
    header = next(
        (i for i, line in enumerate(lines)
         if check_run_rail._cells(line)[:1] == ["Key"]),
        None,
    )
    if header is None:
        return None
    columns: list[tuple[str, str]] = []
    for line in lines[header + 2:]:
        if not line.strip().startswith("|"):
            break
        cells = check_run_rail._cells(line)
        if len(cells) < 2:
            continue
        key = cells[0].strip("`")
        if key != "floor":
            columns.append((key, cells[1]))
    return columns or None


def spec_from_briefing(briefing: str) -> dict:
    """The rail block as the values this script draws.

    Every value is copied. Nothing here reads a diff, an issue file or the
    board, and nothing works out which stage an issue belongs to.
    """
    rail = check_run_rail.read_rail(briefing)
    if rail is None:
        raise ValueError(
            f"the briefing carries no `{check_run_rail.RAIL_HEADING}` heading"
        )
    at = check_run_rail._heading_at(briefing, check_run_rail.RAIL_HEADING)
    body, _ = check_run_rail._body_after(briefing, at, check_run_rail.RAIL_HEADING)
    bands = rail.bands
    return {
        "headline": check_run_rail._field(body, "Headline") or "",
        "lit": check_run_rail._keys(check_run_rail._field(body, "Lit") or ""),
        "cards": [
            {"issue": c[0], "stage": c[1], "kind": c[2], "sentence": c[3]}
            for c in rail.rows
            if len(c) >= 4 and c[0] not in bands
        ],
        # Every shipped row, band member included. A chip takes its issue's own
        # kind for its colour, and that kind is stated in the shipped table.
        "shipped": [
            {"issue": c[0], "stage": c[1], "kind": c[2], "sentence": c[3]}
            for c in rail.rows if len(c) >= 4
        ],
        # Issue 554. Two more tables, each keyed on its own header row and kept
        # apart from the shipped one. A band may carry a hole as well as a
        # shipped issue — `batch-45c8b1`'s band carries `509`, which was left
        # open — so the minted rows are filtered by band membership too.
        "minted": [
            {"issue": c[0], "stage": c[1], "sentence": c[2]}
            for c in rail.minted if len(c) >= 3 and c[0] not in bands
        ],
        "forks": [
            {"issue": c[0], "stage": c[1], "sentence": c[2]}
            for c in rail.forks if len(c) >= 3
        ],
        # Issue 555. One band per row, in the table's own order, each carrying
        # the words its chips draw. A chip whose text has no row draws bare;
        # `check_run_rail.py` refuses that block one step earlier, and the
        # render states what it was given rather than inventing the words.
        "bands": [
            {
                "band": c[0],
                "span": c[1],
                "kind": c[2],
                "issues": check_run_rail._band_ids(c[3]),
                "caption": c[4],
                "seats": c[5],
                "text": {
                    chip[1]: chip[2]
                    for chip in rail.chip_rows
                    if len(chip) >= 3 and chip[0] == c[0]
                },
            }
            for c in rail.band_rows
            if len(c) >= len(check_run_rail.BANDS_HEADER)
        ],
    }


def _greedy(sentence: str, width: float, px: float = PX) -> list[str]:
    """The sentence broken greedily to `width` units, with nothing asserted.

    `wrap` refuses what will not fit and is what every drawn string goes
    through. This is the same break used where a width is being COMPUTED and a
    refusal would be circular.

    `px` is the glyph width of the class the string DRAWS in. A caption draws
    in `tb` and everything else in `tv`, and measuring a caption at the card's
    glyph under-reads it by a quarter: seen in a browser on 2026-09-05,
    `batch-45c8b1`'s caption then wrapped to one 37-character line and ran
    under the band's first chip.
    """
    lines: list[str] = []
    for word in sentence.split():
        if lines and (len(lines[-1]) + 1 + len(word)) * px <= width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    return lines


def wrap(sentence: str, width: float, issue: str, px: float = PX) -> list[str]:
    """The sentence broken greedily to `width` units, at most `MAX_LINES` lines.

    Raises `WillNotFit` rather than returning something the box cannot hold. A
    single word longer than the line is its own line and is refused by the same
    width test, which is right: shortening it is the finale's job, not this
    script's.
    """
    if not sentence.strip():
        raise WillNotFit(
            f"{issue}: the sentence is empty; `check_run_rail.py` grades a "
            f"row's cell count and its length and neither catches a blank "
            f"`Sentence` cell, so fill it in the rail block"
        )
    lines = _greedy(sentence, width, px)
    for line in lines:
        need = len(line) * px
        if need > width:
            raise WillNotFit(
                f"{issue}: '{line}' needs {need:.0f} units and the card gives "
                f"{width}; shorten the sentence in the rail block"
            )
    if len(lines) > MAX_LINES:
        raise WillNotFit(
            f"{issue}: '{sentence}' wraps into {len(lines)} lines and a card "
            f"draws {MAX_LINES}; shorten the sentence in the rail block"
        )
    return lines


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def _cx(i: int) -> int:
    return X0 + i * (W + G)


def _chip(num: str, css: str, x: float, y: float) -> str:
    """The card's key in a coloured pill. `css` is the class, not the kind: a
    hole and a question have no kind, and the caller is what knows the shape."""
    w = 10 + 6.2 * len(num)
    return (
        f'<rect class="{css}" x="{x:.0f}" y="{y:.0f}" '
        f'width="{w:.0f}" height="16" rx="4"/>'
        f'<text class="tn" x="{x + w / 2:.0f}" y="{y + 8.5:.0f}" '
        f'text-anchor="middle" dominant-baseline="central">{esc(num)}</text>'
    )


# Each shape's box class and the class its chip takes. `shipped` reads its chip
# colour from the row's kind instead, which is why it is not here.
SHAPES = {"minted": ("hole", "c-gray"), "fork": ("waits", "c-fork")}


def _card(card: dict, x: float, y: float, shape: str = "shipped") -> str:
    """One card, with its values on the `<g>` that wraps its shapes and text.

    The attributes go on the container and never on a shape. Measured
    2026-09-03: `HTMLParser` turns `<rect data-card="517"/>` into a start tag
    immediately followed by an end tag, so a reader sees an empty card and
    raises on markup that renders perfectly well.
    """
    lines = wrap(card["sentence"], LINE_W, card["issue"])
    box, chip = SHAPES.get(shape, ("box", KIND.get(card.get("kind", ""), "c-gray")))
    # Only a shipped row has a `Kind` column, so only a shipped card carries the
    # attribute. `check_run_picture.py` grades a kind on no other shape, and
    # writing one here would state a fact the briefing does not hold.
    kind = f'data-kind="{esc(card["kind"])}" ' if shape == "shipped" else ""
    # `data-line` is what tells the board's guard which text is the sentence.
    # The issue chip below draws text into the same container, and a reader
    # that counted it measured every three-line card as four.
    text = "".join(
        f'<text class="tv" data-line="{k}" x="{x + 6:.0f}" '
        f'y="{y + 36 + 11 * k:.0f}">{esc(line)}</text>'
        for k, line in enumerate(lines)
    )
    return (
        f'<g data-card="{esc(card["issue"])}" data-stage="{esc(card["stage"])}" '
        f'{kind}data-shape="{shape}">'
        f'<rect class="{box}" x="{x:.0f}" y="{y:.0f}" width="{W}" height="{CH}" rx="6"/>'
        f'{_chip(card["issue"], chip, x + 6, y + 7)}{text}</g>'
    )


# The seat marks, byte for byte from `def seat_pills(x, y, states)` in the
# generator. The order is fixed and the block states it in that order, so the
# drawing reads the cell and never works out which seat a mark belongs to.
SEAT_MARK = {"ok": "\u2713", "no": "\u2715", "dash": "\u2013"}
SEAT_CSS = {"ok": "seat-ok", "no": "seat-no", "dash": "seat-dash"}


def _seat_pills(x: float, y: float, cell: str) -> str:
    """The three pills, or nothing at all where the `Seats` cell is empty.

    **Whether a band is about seats is the finale's judgement, like the
    caption.** Nothing here reads the caption or guesses: an empty cell draws
    no pills, and a cell that holds anything has been graded by
    `check_run_rail.py` into three marks in the order the pills draw them.
    """
    if not cell.strip():
        return ""
    out = []
    for part in (piece.strip() for piece in cell.split(",")):
        seat, mark = part.split()
        out.append(
            f'<rect class="{SEAT_CSS[mark]}" x="{x:.0f}" y="{y:.0f}" width="54" '
            f'height="15" rx="7"/>'
            f'<text class="tp" x="{x + 27:.0f}" y="{y + 8:.0f}" '
            f'text-anchor="middle" dominant-baseline="central">'
            f'{esc(seat)} {SEAT_MARK[mark]}</text>'
        )
        x += 58
    return "".join(out)


def _band(band: dict, x: float, y: float, columns: int, kinds: dict[str, str]) -> str:
    """One band: a strip over the columns it spans, with its issues as chips.

    The attributes go on the `<g>` that opens and closes, and nothing carrying
    `data-figure` goes inside it. Measured 2026-09-03 against
    `check_run_picture.py`'s own readers: a self-closing carrier raises, and a
    nested `data-figure` is swallowed with its digits concatenated — `7` and
    `9` reading as `79.0` — so a band that held one would corrupt the panel's
    figures in silence.
    """
    issues = band["issues"]
    layout, cw, budget = band_layout(columns, len(issues), band["caption"])
    width = band_width(columns)
    box = BAND_KIND.get(band["kind"], "b-harness")
    parts = [
        f'<rect class="{box}" x="{x:.0f}" y="{y:.0f}" width="{width}" '
        f'height="{BAND_H}" rx="8"/>'
    ]
    caption_room = (cw if layout == "left" else width) - 24
    caption = wrap(
        band["caption"], caption_room, f'band {band["band"]}', px=CAPTION_PX
    )
    if len(caption) > CAPTION_LINES:
        raise WillNotFit(
            f'band {band["band"]}: the caption wraps into {len(caption)} lines '
            f'and a band draws {CAPTION_LINES}; shorten the `Caption` cell'
        )
    if layout == "left":
        for k, line in enumerate(caption):
            parts.append(
                f'<text class="tb" x="{x + 12:.0f}" y="{y + 24 + 16 * k:.0f}">'
                f'{esc(line)}</text>'
            )
        parts.append(_seat_pills(x + 12, y + 52, band["seats"]))
        area_x, chip_y, verb_y = x + cw, y + 16, y + 46
    else:
        for k, line in enumerate(caption):
            parts.append(
                f'<text class="tb" x="{x + 12:.0f}" y="{y + 22 + 16 * k:.0f}">'
                f'{esc(line)}</text>'
            )
        parts.append(_seat_pills(x + 12, y + 34, band["seats"]))
        area_x, chip_y, verb_y = x + 6, y + 36, y + 66
    pitch = budget + 10
    for k, issue in enumerate(issues):
        px = area_x + k * pitch + 6
        parts.append(f'<g data-chip="{esc(issue)}">')
        parts.append(_chip(issue, kinds.get(issue, "c-gray"), px, chip_y))
        for j, line in enumerate(wrap(band["text"].get(issue, issue), budget, issue)):
            if j >= CHIP_LINES:
                raise WillNotFit(
                    f"{issue}: its chip text wraps into more than {CHIP_LINES} "
                    f"lines and a chip draws {CHIP_LINES}; shorten the `Text` "
                    f"cell under {check_run_rail.CHIPS_HEADING}"
                )
            parts.append(
                f'<text class="tv" data-line="{j}" x="{px:.0f}" '
                f'y="{verb_y + 11 * j:.0f}">{esc(line)}</text>'
            )
        parts.append("</g>")
    return (
        f'<g data-band="{esc(band["band"])}" data-stages="{esc(band["span"])}" '
        f'data-issues="{esc(" ".join(issues))}">' + "".join(parts) + "</g>"
    )


def _legend(y: float) -> str:
    """The four kind circles, then the two shapes issue 554 draws.

    No issue in 550 to 556 owned the legend. Issue 553 drew the four circles
    because it was what first drew a kind, and this slice draws the dashed box
    and the amber box for the same reason: the shape that puts a treatment on
    the picture is the one that has to explain it.

    The two captions say what the reader is looking at and never what to do
    about it. A dashed card is a hole, never a plan: the wording must not read
    as work somebody has started.
    """
    parts, lx = [], X0
    for kind, label in (("new", "New"), ("fix", "Fix"),
                        ("guard", "Guard"), ("harness", "Harness")):
        parts.append(
            f'<circle class="{KIND[kind]}" cx="{lx + 6}" cy="{y + 6:.0f}" r="6"/>'
        )
        parts.append(
            f'<text class="ts" x="{lx + 18}" y="{y + 6:.0f}" '
            f'dominant-baseline="central">{label}</text>'
        )
        lx += 22 + 12 + len(label) * 7 + 14
    for css, label in (("hole", "Open, not built"), ("waits", "Waits on you")):
        parts.append(
            f'<rect class="{css}" x="{lx}" y="{y:.0f}" width="18" height="12" rx="3"/>'
        )
        parts.append(
            f'<text class="ts" x="{lx + 24}" y="{y + 6:.0f}" '
            f'dominant-baseline="central">{label}</text>'
        )
        lx += 24 + len(label) * 7 + 16
    return "".join(parts)


def _shipped_of(spec: dict) -> list[dict]:
    """Every shipped row, band member or not, so a chip can take its own kind.

    `spec["cards"]` holds the rows that owe a card, which is the rows a band
    does NOT name. A chip's colour is its issue's kind and that kind lives in
    the shipped table, so the rows are read again here rather than derived from
    anything the band states.
    """
    return spec.get("shipped", [])


def _span_columns(
    span: str, order: dict[str, int], key: str
) -> tuple[int, int]:
    """The first and last column index a `first..last` span covers.

    `check_run_rail.py` has already refused a span that is not two keys of the
    vocabulary in order, so a failure here is a briefing that never went
    through step 4's guard.
    """
    first, _, last = span.strip().partition("..")
    if first not in order or last not in order or order[last] < order[first]:
        raise WillNotFit(
            f"band {key}: `{span}` is not a span of the rail's columns in "
            f"order; run check_run_rail.py on the briefing first"
        )
    return order[first], order[last]


def render(spec: dict, columns: list[tuple[str, str]]) -> str:
    """The rail as one `<svg>`, at its natural width.

    Every column is drawn whether or not it holds a card, so a two-issue run
    draws the whole rail and an empty column is the shape rather than a hole.
    """
    width = X0 * 2 + len(columns) * W + (len(columns) - 1) * G
    order = {key: i for i, (key, _) in enumerate(columns)}
    lit = set(spec.get("lit", ()))
    parts = [
        f'<text class="thl" x="{X0}" y="18">{esc(spec.get("headline", ""))}</text>'
    ]
    headline = spec.get("headline", "")
    need = len(headline) * HEADLINE_PX
    if need > width - 10:
        raise WillNotFit(
            f"headline: '{headline}' needs {need:.0f} units at 15px and the rail "
            f"gives {width - 10}; shorten the `Headline:` line. A headline is one "
            f"line and the rail never wraps it"
        )

    ry = 40
    parts.append(
        f'<line x1="{X0}" y1="{ry + 20}" x2="{width - X0}" y2="{ry + 20}" '
        f'stroke="var(--muted)" stroke-width="2"/>'
    )
    for i, (key, label) in enumerate(columns):
        cls = "lit" if key in lit else "box"
        parts.append(
            f'<rect class="{cls}" x="{_cx(i)}" y="{ry}" width="{W}" '
            f'height="40" rx="6"/>'
            f'<text class="tt" x="{_cx(i) + W / 2:.0f}" y="{ry + 20}" '
            f'text-anchor="middle" dominant-baseline="central">{esc(label)}</text>'
        )

    # The bands go directly under the column heads and the cards start beneath
    # the last of them, which is the generator's own order: `for b in
    # run.get("bands", []): svg, h = band(b, y); y += h + 10`, then the cards.
    # Two bands stack in the table's row order and never collide, which matters
    # because an overlapping span is the normal case — on `batch-375cbf`
    # `award..zoho` sits wholly inside `workspace..catalogue`.
    band_y = ry + 40 + 14
    kinds = {
        card["issue"]: KIND.get(card["kind"], "c-gray")
        for card in _shipped_of(spec)
    }
    for band in spec.get("bands", []):
        first, last = _span_columns(band["span"], order, band["band"])
        parts.append(
            _band(band, _cx(first), band_y, last - first + 1, kinds)
        )
        band_y += BAND_H + BAND_GAP

    top = band_y
    bottom = top
    stacked: dict[int, float] = {}
    floor: list[tuple[dict, str]] = []
    # Shipped first, then the holes, then the questions. The order is what makes
    # a column read downward as "what the run did, then what it left": on
    # `batch-45c8b1` the quotation column goes six cards tall, three shipped,
    # two found and one fork, and that is the column the run left the most
    # behind. Nothing in the briefing says so today.
    for shape, key in (("shipped", "cards"), ("minted", "minted"), ("fork", "forks")):
        for card in spec.get(key, []):
            if card["stage"] == "floor":
                floor.append((card, shape))
                continue
            i = order.get(card["stage"])
            if i is None:
                raise WillNotFit(
                    f"{card['issue']}: stage `{card['stage']}` is not a column and "
                    f"is not `floor`"
                )
            y = stacked.get(i, top)
            parts.append(_card(card, _cx(i), y, shape))
            stacked[i] = y + CH + 8
            bottom = max(bottom, stacked[i])

    fy = (bottom if bottom > top else top + 8) + 8
    parts.append(
        f'<line x1="{X0}" y1="{fy}" x2="{width - X0}" y2="{fy}" '
        f'stroke="var(--line)" stroke-width="1" stroke-dasharray="5 4"/>'
    )
    fy += 14
    parts.append(f'<text class="tb" x="{X0}" y="{fy + 24}">Under the floor</text>')
    parts.append(f'<text class="ts" x="{X0}" y="{fy + 40}">what holds the</text>')
    parts.append(f'<text class="ts" x="{X0}" y="{fy + 52}">product up</text>')
    # The floor row starts at column index 1, under the caption, so it has one
    # column fewer than the rail. A vocabulary of a single non-floor column
    # leaves it zero, and the division below raised ZeroDivisionError — an
    # uncaught crash where every other bad input here is a named refusal.
    per_row = len(columns) - 1
    if per_row < 1:
        raise WillNotFit(
            f"the vocabulary holds {len(columns)} column besides `floor`, and "
            f"the floor row needs at least two; add a row to "
            f"docs/agents/run-picture-stages.md"
        )
    for k, (card, shape) in enumerate(floor):
        row, col = divmod(k, per_row)
        parts.append(_card(card, _cx(col + 1), fy + row * (CH + 8), shape))
    rows = max(1, -(-len(floor) // per_row))
    ly = fy + rows * (CH + 8) + 10
    parts.append(_legend(ly))

    return (
        f'<svg class="rail" viewBox="0 0 {width} {ly + 20:.0f}" role="img" '
        f'aria-label="{esc(spec.get("headline", "The run on the rail"))}">'
        + "".join(parts)
        + "</svg>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draw the run's rail from the briefing's rail block."
    )
    parser.add_argument("--briefing", required=True, help="path to merge-briefing.md")
    parser.add_argument(
        "--stages",
        required=True,
        help="path to docs/agents/run-picture-stages.md in the repository the run is on",
    )
    args = parser.parse_args()

    try:
        briefing = pathlib.Path(args.briefing).read_text()
    except OSError as error:
        print(f"REFUSED unreadable: {error}", file=sys.stderr)
        return 2

    located = check_run_rail.locate_stages(args.stages)
    if located is None:
        print(
            f"REFUSED no-stages: no vocabulary at {args.stages}, here or under "
            f"the git top level; the rail's columns come from that file and "
            f"this script holds none of its own",
            file=sys.stderr,
        )
        return 2
    columns = read_columns(located.read_text())
    if columns is None:
        print(
            f"REFUSED no-stages-table: {located} exists and holds no table "
            f"headed `Key`, so the columns cannot be read",
            file=sys.stderr,
        )
        return 2

    try:
        svg = render(spec_from_briefing(briefing), columns)
    except ValueError as error:
        print(f"REFUSED no-rail: {error}", file=sys.stderr)
        return 2
    except WillNotFit as error:
        print(f"REFUSED will-not-fit: {error}", file=sys.stderr)
        return 1

    width = X0 * 2 + len(columns) * W + (len(columns) - 1) * G
    # Four blocks, each opened by a marker line the renderer can split on. The
    # markers carry no angle brackets of their own: a marker holding `<div ...>`
    # cannot be cut out with the obvious pattern, which cost one assembly on
    # 2026-09-04.
    print("=== BLOCK 1 of 4: tokens for board.html's :root ===")
    print(TOKENS_LIGHT)
    print("=== BLOCK 2 of 4: the same tokens for its dark :root ===")
    print(TOKENS_DARK)
    print("=== BLOCK 3 of 4: CSS, beside the board's own ===")
    print(rail_css(width))
    print("=== BLOCK 4 of 4: the rail, inside a div of class rail-bleed, "
          "directly above the run panel ===")
    print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
