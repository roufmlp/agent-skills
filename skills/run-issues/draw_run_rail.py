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
        --briefing .scratch/<feature>/merge-briefing.md \\
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

# The seven tokens the rail adds. `board.html` defines none of them, measured
# 2026-09-03, and a token defined only in the light block is a card that
# vanishes into a dark background — so both blocks are emitted, always.
TOKENS_LIGHT = """  --new: #1a7f4b; --new-soft: #e6f4ec;
  --fix: #b3261e; --fix-soft: #fdecea;
  --guard: #6f42a1; --guard-soft: #f1ebfa;
  --chip-ink: #ffffff;"""
TOKENS_DARK = """  --new: #5cc48f; --new-soft: #16301f;
  --fix: #f2857c; --fix-soft: #2d1917;
  --guard: #b18cea; --guard-soft: #221a33;
  --chip-ink: #12151c;"""

# The rail keeps its natural width and scrolls sideways. RULED by the human on
# 2026-09-04: `board.html` is `max-width: 720px` with 20px of padding each
# side, leaving 680 units of content, and a 1040-unit rail scaled into that
# draws its 10-unit card text at 6.5 CSS pixels. They were asked and answered
# "keep full width and scroll". Only the rail is full-bleed; the rest of the
# board keeps its reading column.
_RAIL_CSS = """  /* The rail keeps its natural width and scrolls sideways inside its own
     container. RULED by the human on 2026-09-04: scaling 1040 units into the
     board's 680 draws the 10-unit card text at 6.5 CSS pixels.
     The container reclaims the board's own 20px padding and uses NO viewport
     units. A bleed built on `calc(50% - 50vw)` was measured in a browser on
     2026-09-04 and it overshoots: `50vw` counts the vertical scrollbar and
     `50%` does not, so the container drew 649 against a 634-pixel root and the
     whole board scrolled 7.5 pixels sideways. `html { overflow-x: clip }` did
     not stop it. Negative margins equal to the body's padding cannot overshoot,
     because the body's content box plus its padding is its border box. */
  .rail-bleed { margin: 12px -20px 0; padding: 0 20px; overflow-x: auto; }
  .rail-bleed svg { display: block; height: auto; min-width: {width}px; }
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
  .rail .c-gray { fill: var(--quiet); stroke: var(--quiet); }"""


def rail_css(width: int) -> str:
    """The board's CSS for the rail, floored at the rail's natural width.

    `%` formatting cannot be used here: the full-bleed rule carries
    `calc(50% - 50vw)`, and a stray format character in a stylesheet is a
    `ValueError` at the moment the finale needs the output.
    """
    return _RAIL_CSS.replace("{width}", str(width))


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
    }


def wrap(sentence: str, width: int, issue: str) -> list[str]:
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
    lines: list[str] = []
    for word in sentence.split():
        if lines and (len(lines[-1]) + 1 + len(word)) * PX <= width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    for line in lines:
        need = len(line) * PX
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


def _chip(num: str, kind: str, x: float, y: float) -> str:
    w = 10 + 6.2 * len(num)
    return (
        f'<rect class="{KIND.get(kind, "c-gray")}" x="{x:.0f}" y="{y:.0f}" '
        f'width="{w:.0f}" height="16" rx="4"/>'
        f'<text class="tn" x="{x + w / 2:.0f}" y="{y + 8.5:.0f}" '
        f'text-anchor="middle" dominant-baseline="central">{esc(num)}</text>'
    )


def _card(card: dict, x: float, y: float) -> str:
    """One card, with its values on the `<g>` that wraps its shapes and text.

    The attributes go on the container and never on a shape. Measured
    2026-09-03: `HTMLParser` turns `<rect data-card="517"/>` into a start tag
    immediately followed by an end tag, so a reader sees an empty card and
    raises on markup that renders perfectly well.
    """
    lines = wrap(card["sentence"], LINE_W, card["issue"])
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
        f'data-kind="{esc(card["kind"])}" data-shape="shipped">'
        f'<rect class="box" x="{x:.0f}" y="{y:.0f}" width="{W}" height="{CH}" rx="6"/>'
        f'{_chip(card["issue"], card["kind"], x + 6, y + 7)}{text}</g>'
    )


def _legend(y: float) -> str:
    """The four kind circles. No issue in 550 to 556 owned the legend, and this
    slice is what first draws a kind, so the four colours are explained here.
    The dashed and amber halves belong to issue 554, which draws those shapes."""
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
    return "".join(parts)


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
    if len(headline) * PX > width - 10:
        raise WillNotFit(
            f"headline: '{headline}' needs {len(headline) * PX:.0f} units and "
            f"the rail gives {width - 10}; shorten the `Headline:` line"
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

    top = ry + 40 + 14
    bottom = top
    stacked: dict[int, float] = {}
    floor = []
    for card in spec.get("cards", []):
        if card["stage"] == "floor":
            floor.append(card)
            continue
        i = order.get(card["stage"])
        if i is None:
            raise WillNotFit(
                f"{card['issue']}: stage `{card['stage']}` is not a column and "
                f"is not `floor`"
            )
        y = stacked.get(i, top)
        parts.append(_card(card, _cx(i), y))
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
    for k, card in enumerate(floor):
        row, col = divmod(k, per_row)
        parts.append(_card(card, _cx(col + 1), fy + row * (CH + 8)))
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
