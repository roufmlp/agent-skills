#!/usr/bin/env python3
"""Refuse a `## The run on the rail` block the board could not transcribe.

Issue 552. The finale runs this in step 4, after it writes the rail block under
the one-screen block, and a refusal stops the finale.

**The judgement lives in the briefing, never in the render.** Picture D lands
every shipped issue on one of nine stages, gives it one of four kinds and one
sentence, and lights the stages that hold a card. Deciding any of that is
judgement, and `finale.md` step 5 forbids the renderer judgement: "The panel
transcribes. It never counts." So the finale writes the block and this guard
refuses one the renderer could not copy.

The block sits directly below the WHOLE of `## The run in one screen`, above
every other `## ` heading, and reads:

    ## The run on the rail

    Headline: The database now refuses a viewer's direct write on every table
    this batch touched. The money road is still open.
    Lit: workspace, quotation, needs-you, zoho

    | Issue | Stage     | Kind  | Sentence                                      |
    |-------|-----------|-------|-----------------------------------------------|
    | 517   | workspace | new   | Admin adds a person and changes a seat        |
    | 503   | floor     | fix   | Citation checker refuses without a clean bill |

Both headings are matched as whole lines. The one-screen table's third column
names headings by design, so a cell reading `## The run on the rail` must never
be taken for the heading itself. A `Label:` field may wrap: continuation lines
that are not blank, not a table row and not another label belong to it, which
is how the real briefings already wrap their `Waiting:` line.

The stage vocabulary is NOT in this file. It is `docs/agents/run-picture-stages.md`
in the repository the run is working on, passed as `--stages`, because this
guard ships in the skills repository and `/run-issues` runs on other
repositories too. A relative path that does not exist from the working
directory is tried again from the git top level, so the finale's command works
from the repo root and from `.scratch/<feature>/runs/<batch-id>/` alike. Where no file exists
in either place the stage rule is not run at all and the guard says so and
carries on, which is that file's own rule 4. A file that exists and holds no
readable table is a different state and is refused.

The shipped list is read from the `Shipped:` line of the one-screen block and
never from `## What shipped`. Measured across five real briefings, that heading
is not stable in name or in shape; `Shipped:` is one line of comma-separated
ids and this guard makes it a required field. `none` means nothing shipped, and
a note after ` - ` is not read.

Only the shipped table is compared against the shipped list. It is found by its
own header row, `| Issue | Stage | Kind | Sentence |`, so the `### Minted and
left open`, `### Forks waiting on you` and `### Bands` tables that issues 554
and 555 add beneath it are never read as shipped rows. `### Bands`, where it
exists, gives the band membership: a band member never takes `floor`. That is
the whole of what this guard checks about bands; issue 555 owns the span rule.
Where the heading is absent there are no bands and every `floor` row passes.

Refusals that exit 1, every one printed and every one naming its row:

    rail-above-block    the rail heading sits above the one-screen heading
    rail-splits-block   the rail heading sits inside the one-screen block:
                        above its table, or between the table and one of the
                        block's field lines (Shipped, Did not ship, Minted,
                        Register, Waiting), which then read as rail text
    heading-between     another `## ` heading sits between the two blocks
    no-headline         the block carries no `Headline:` line, or an empty one
    no-lit              the block carries no `Lit:` line
    bad-lit-stage       a `Lit:` key is not in the vocabulary
    bad-stage           a row's stage is not in the vocabulary
    bad-kind            a row's kind is not new, fix, guard or harness
    bad-row             a row has fewer than four cells
    sentence-too-long   a row's sentence is 60 characters or more
    duplicate-row       an issue has two rows
    no-row              an issue on the `Shipped:` line has no row
    not-shipped         a row names an issue the `Shipped:` line does not
    floor-in-band       a row reads `floor` for an issue a band names

Refusals that exit 2, because nothing could be graded:

    no-block            no `## The run in one screen` heading at all
    no-rail             no `## The run on the rail` heading at all
    no-shipped-line     the one-screen block carries no `Shipped:` line
    no-stages-table     the vocabulary file exists and holds no `Key` table
    unreadable          the briefing could not be read

**It grades keys, counts and lengths and nothing else.** Whether a sentence is
true, whether 516 belongs on `needs-you` rather than `workspace`, whether the
headline is the run's real story: none of that is checked here, and this guard
must never be cited as cover for it. A pass prints what it compared, because an
`ok` on sixteen rows and an `ok` on none are different sentences.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

ONE_SCREEN_HEADING = "## The run in one screen"
RAIL_HEADING = "## The run on the rail"
BANDS_HEADING = "### Bands"
MINTED_HEADING = "### Minted and left open"
FORKS_HEADING = "### Forks waiting on you"
KINDS = ("new", "fix", "guard", "harness")
# A sentence of this many characters or more is refused. The bound as a
# sentence is `59 characters or fewer`, and the rail card cannot draw a longer one.
SENTENCE_LIMIT = 60
SHIPPED_HEADER = ("issue", "stage", "kind", "sentence")
# Issue 554's two tables, each found by its own header row for the same reason
# the shipped table is: a heading can be renamed and a header row states what
# the columns mean.
MINTED_HEADER = ("issue", "stage", "sentence")
FORKS_HEADER = ("fork", "stage", "question")
# Issue 555's two tables, found the same way. The band row carries the whole
# band and the chip row carries one issue's own words, because a chip's text
# holds numbers of its own — `99 reads fail closed now` is one the generator
# draws — and ids read out of a cell holding both would find issue 99.
BANDS_HEADER = ("band", "stages", "kind", "issues", "caption", "seats")
CHIPS_HEADER = ("band", "issue", "text")
CHIPS_HEADING = "### Band chips"
# A band spans `first..last` over the rail's columns.
SPAN = re.compile(r"^([A-Za-z0-9_-]+)\.\.([A-Za-z0-9_-]+)$")
# The three seats, in the order the pills draw them, and the three marks.
SEATS = ("admin", "member", "viewer")
MARKS = ("ok", "no", "dash")
# The smallest band. Below either number the shape is a card, not a band.
BAND_MIN_ISSUES = 2
BAND_MIN_COLUMNS = 2
DECIDE_HEADING = re.compile(r"^## Decide\b", re.M)
# The one-screen row whose figure the fork rows are counted against.
FORKS_FIGURE = "forks to decide"
# The one-screen block's field lines. Any of them found inside the rail body
# means the rail heading was written inside the block rather than below it.
ONE_SCREEN_FIELDS = ("Shipped", "Did not ship", "Minted", "Register", "Waiting")

_ISSUE_ID = re.compile(r"\b\d+[a-z]?\b")
_LABEL_LINE = re.compile(r"^[A-Z][A-Za-z ]*:(\s|$)")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _cells(line: str) -> list[str]:
    """The cells of a pipe-table row, a markdown-escaped `\\|` kept inside its cell."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip().replace("\\|", "|") for cell in _UNESCAPED_PIPE.split(inner)]


def _heading_at(text: str, heading: str) -> int:
    """The index of `heading` as a whole line, or -1. A table cell or a prose
    mention of the same words is not the heading."""
    found = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.M)
    return found.start() if found else -1


def read_stages(text: str) -> list[str] | None:
    """The stage keys from the vocabulary table, or None when it holds no table.

    The table is found by its `Key` header. The key is the first cell with its
    backticks removed. Nothing else in that file is read.

    **The order is the table's, and issue 555 needs it.** A band names its span
    as `first..last` and the columns between them are the ones it covers, so a
    reader holding a set could tell that both keys exist and never that
    `tender..workspace` runs backwards. Rule 1 of `run-picture-stages.md`
    already makes the table order the drawn order, which is why the order is
    read here rather than stated a second time.
    """
    lines = text.splitlines()
    header = next(
        (i for i, line in enumerate(lines) if _cells(line)[:1] == ["Key"]), None
    )
    if header is None:
        return None
    keys: list[str] = []
    for line in lines[header + 2 :]:
        if not line.strip().startswith("|"):
            break
        key = _cells(line)[0].strip("`")
        if key not in keys:
            keys.append(key)
    return keys or None


def locate_stages(path: str) -> pathlib.Path | None:
    """The vocabulary file at `path`, or at `path` under the git top level, or
    None where neither exists. The finale's command names the path relative to
    the repo root and may run from `.scratch/<feature>/runs/<batch-id>/`."""
    given = pathlib.Path(path)
    if given.exists():
        return given
    if given.is_absolute():
        return None
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    candidate = pathlib.Path(top) / given
    return candidate if candidate.exists() else None


def _body_after(text: str, start: int, heading: str) -> tuple[str, int]:
    """The text from just after `heading` at `start` to the next `## ` heading.

    Returns the body and the absolute index of the next heading's first
    character, or len(text) where there is none.
    """
    rest = text[start + len(heading) :]
    end = rest.find("\n## ")
    if end < 0:
        return rest, len(text)
    return rest[:end], start + len(heading) + end + 1


def _field(body: str, name: str) -> str | None:
    """The text of the `Name:` field, or None where the body has no such line.

    Read by line prefix, so `Headline:` trailing text is never mistaken for a
    `Lit:` key. Continuation lines belong to the field until a blank line, a
    table row, a heading or another `Label:` line, which is how a long
    `Shipped:` or `Waiting:` line wraps in the real briefings.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith(name + ":"):
            continue
        parts = [line[len(name) + 1 :].strip()]
        for more in lines[i + 1 :]:
            bare = more.strip()
            if not bare or bare.startswith(("|", "#")) or _LABEL_LINE.match(more):
                break
            parts.append(bare)
        return " ".join(part for part in parts if part)
    return None


def _ids(text: str) -> list[str]:
    """Issue ids on a `Shipped:` line. `none` is empty; a note after ` - ` is
    not read, because the real lines write `none - every issue reached done`."""
    head = text.split(" - ", 1)[0].strip()
    if head.lower() in ("", "none"):
        return []
    return _ISSUE_ID.findall(head)


def _keys(text: str) -> list[str]:
    """Stage keys on a `Lit:` line. `none` is empty."""
    if text.strip().lower() in ("", "none"):
        return []
    return [key for key in re.split(r"[,\s]+", text.strip()) if key]


def _table_rows(body: str, header: tuple[str, ...]) -> list[list[str]] | None:
    """The rows of the table whose header row is `header`, or None.

    Each of the block's tables is found by its OWN header row rather than by
    position or by the `###` heading above it. That is what keeps the three
    apart: issue 552's rule refuses a row naming an issue that did not ship,
    and every row issue 554 adds names an issue that did not ship, so a reader
    taking one flat list of issue numbers over the widened block would refuse a
    correct briefing.

    The read stops at the first line that is not a table row, so a `###`
    sub-heading ends it.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and tuple(
            cell.lower() for cell in _cells(line)
        ) == header:
            rows = []
            for row in lines[i + 2 :]:
                if not row.strip().startswith("|"):
                    break
                rows.append(_cells(row))
            return rows
    return None


def _shipped_rows(body: str) -> list[list[str]] | None:
    """The rows of the table headed `| Issue | Stage | Kind | Sentence |`."""
    return _table_rows(body, SHIPPED_HEADER)


def _figure(body: str, label: str) -> float | None:
    """The `Count` cell of the one-screen row whose label is `label`, or None.

    The label is matched case-folded and stripped of markdown emphasis, so
    `Forks to decide` and `**Forks to decide**` are the same row. Only this one
    figure is read here; `check_run_picture.py` owns the whole table.
    """
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 2 or cells[0].strip("*` ").lower() != label:
            continue
        try:
            return float(cells[1].replace(",", ""))
        except ValueError:
            return None
    return None


# The `Issues` cell's position in a band row, so the one column every other
# reader needs is named once rather than counted at each use.
BAND_ISSUES_AT = BANDS_HEADER.index("issues")


def _band_ids(cell: str) -> list[str]:
    """The `Issues` cell read as whole tokens, in the order it writes them.

    Not `_ids`: that finds issue-shaped runs of digits inside a longer string,
    which is right for a prose `Shipped:` line and wrong here. A band cell is a
    list, so a token that is not an issue — a fork key, a stray word, a number
    split by a space — must reach the membership rule as itself and be refused
    by name, rather than be quietly read as some other issue.
    """
    return [token for token in re.split(r"[,\s]+", cell.strip()) if token]


def _band_rows(body: str) -> list[list[str]]:
    """The rows of the `### Bands` table, or empty where the block has none."""
    return _table_rows(body, BANDS_HEADER) or []


def _band_members(rows: list[list[str]]) -> set[str]:
    """Every issue id the band rows name, over all bands."""
    members: set[str] = set()
    for cells in rows:
        if len(cells) > BAND_ISSUES_AT:
            members.update(_band_ids(cells[BAND_ISSUES_AT]))
    return members


@dataclass(frozen=True)
class Rail:
    """The rail block's shipped rows and its band membership.

    `read_rail` exists so `check_run_picture.py` grades the board's cards
    against the SAME parse this file grades the block with. A second reader of
    the same block in another file drifts, and the two guards then disagree
    about what the briefing says while both report a pass.
    """

    rows: list[list[str]]
    bands: set[str]
    minted: list[list[str]] = field(default_factory=list)
    forks: list[list[str]] = field(default_factory=list)
    band_rows: list[list[str]] = field(default_factory=list)
    chip_rows: list[list[str]] = field(default_factory=list)


def read_rail(briefing: str) -> Rail | None:
    """The rail block, or None where the briefing carries no rail heading.

    It parses and refuses nothing. Every rule about what a row may hold is
    `check()` below, which runs one step earlier in the finale, so a board
    reaching `check_run_picture.py` has already been through it.
    """
    at = _heading_at(briefing, RAIL_HEADING)
    if at < 0:
        return None
    body, _ = _body_after(briefing, at, RAIL_HEADING)
    band_rows = _band_rows(body)
    return Rail(
        rows=_shipped_rows(body) or [],
        bands=_band_members(band_rows),
        minted=_table_rows(body, MINTED_HEADER) or [],
        forks=_table_rows(body, FORKS_HEADER) or [],
        band_rows=band_rows,
        chip_rows=_table_rows(body, CHIPS_HEADER) or [],
    )


@dataclass
class Result:
    """What the check found and what it compared. `fatal` means nothing could
    be graded and the exit is 2; otherwise any refusal exits 1."""

    refusals: list[str] = field(default_factory=list)
    fatal: bool = False
    shipped: int = 0
    rows: int = 0
    longest: int = 0
    lit: int = 0
    minted: int = 0
    forks: int = 0
    bands: int = 0
    stages_graded: bool = True

    def refuse(self, reason: str, fatal: bool = False) -> None:
        self.refusals.append(reason)
        self.fatal = self.fatal or fatal

    def summary(self) -> str:
        graded = "graded" if self.stages_graded else "NOT graded, no vocabulary"
        # `longest` spans all three tables. Every one of them is drawn into the
        # same box, so a figure that counted a shipped sentence and a minted
        # one but not a fork's question would move with the table the text sat
        # in rather than with the text.
        return (
            f"ok: {self.shipped} shipped, {self.rows} rail rows, {self.minted} "
            f"minted rows, {self.forks} fork rows, {self.bands} bands, longest "
            f"card text {self.longest} characters, {self.lit} stages lit, "
            f"stage keys {graded}"
        )


def check(briefing: str, stages: list[str] | None) -> Result:
    """Every refusal the briefing earns, each starting with its reason word.

    `stages` is the vocabulary IN THE TABLE'S ORDER, as `read_stages` returns
    it, because a band's span is a range over that order. None means no
    vocabulary exists here and the stage rule is skipped.
    """
    result = Result(stages_graded=stages is not None)
    one_screen = _heading_at(briefing, ONE_SCREEN_HEADING)
    if one_screen < 0:
        result.refuse(
            f"no-block: the briefing carries no `{ONE_SCREEN_HEADING}` heading, so "
            f"there is no shipped list to check the rail against",
            fatal=True,
        )
        return result
    rail = _heading_at(briefing, RAIL_HEADING)
    if rail < 0:
        result.refuse(
            f"no-rail: the briefing carries no `{RAIL_HEADING}` heading; a run "
            f"that shipped nothing still writes one, with the headline saying so",
            fatal=True,
        )
        return result

    one_body, next_heading = _body_after(briefing, one_screen, ONE_SCREEN_HEADING)
    rail_body, _ = _body_after(briefing, rail, RAIL_HEADING)
    leaked = [name for name in ONE_SCREEN_FIELDS if _field(rail_body, name) is not None]

    if rail < one_screen:
        result.refuse(
            "rail-above-block: the rail heading sits above the one-screen "
            "heading; it goes below the whole of that block"
        )
    elif not any(line.strip().startswith("|") for line in one_body.splitlines()):
        result.refuse(
            "rail-splits-block: the rail heading sits between the one-screen "
            "heading and its table, so check_run_picture.py reads no figure "
            "and exits 2 on every run"
        )
    elif leaked:
        result.refuse(
            f"rail-splits-block: the one-screen block's `{leaked[0]}:` line sits "
            f"below the rail heading; the rail goes below the whole block, its "
            f"field lines included"
        )
    elif next_heading != rail:
        between = briefing[next_heading:].splitlines()[0]
        result.refuse(
            f"heading-between: `{between}` sits between the one-screen block "
            f"and the rail; the rail goes directly below that block"
        )

    shipped_line = _field(one_body, "Shipped")
    if shipped_line is None and "Shipped" in leaked:
        shipped_line = _field(rail_body, "Shipped")
    if shipped_line is None:
        result.refuse(
            "no-shipped-line: the one-screen block carries no `Shipped:` line, "
            "which is the only place the shipped list is read from",
            fatal=True,
        )
        return result
    shipped = _ids(shipped_line)
    result.shipped = len(shipped)

    headline = _field(rail_body, "Headline")
    if not headline:
        result.refuse(
            "no-headline: the rail carries no `Headline:` line, or an empty one; "
            "a run with no story writes the sentence saying so"
        )

    lit = _field(rail_body, "Lit")
    if lit is None:
        result.refuse(
            "no-lit: the rail carries no `Lit:` line; the finale states the lit "
            "stages and the renderer never works them out"
        )
    else:
        result.lit = len(_keys(lit))
        if stages is not None:
            for key in _keys(lit):
                if key not in stages:
                    result.refuse(
                        f"bad-lit-stage: `Lit:` names `{key}`, which is not a "
                        f"stage in the vocabulary"
                    )

    rows = _shipped_rows(rail_body) or []
    result.rows = len(rows)
    seen: dict[str, int] = {}
    for cells in rows:
        if len(cells) < 4:
            result.refuse(
                f"bad-row: `{' | '.join(cells)}` has fewer than four cells; a row "
                f"is issue, stage, kind, sentence"
            )
            continue
        issue, stage, kind, sentence = cells[:4]
        seen[issue] = seen.get(issue, 0) + 1
        if stages is not None and stage not in stages:
            result.refuse(
                f"bad-stage: row {issue} names `{stage}`, which is not a stage in "
                f"the vocabulary"
            )
        if kind not in KINDS:
            result.refuse(
                f"bad-kind: row {issue} names `{kind}`; a kind is one of "
                f"{', '.join(KINDS)}"
            )
        result.longest = max(result.longest, len(sentence))
        if len(sentence) >= SENTENCE_LIMIT:
            result.refuse(
                f"sentence-too-long: row {issue}'s sentence is {len(sentence)} "
                f"characters; the bound is 59 characters or fewer"
            )
    for issue, count in seen.items():
        if count > 1:
            result.refuse(f"duplicate-row: issue {issue} has {count} rows and takes one")

    row_set = set(seen)
    missing = [i for i in shipped if i not in row_set]
    extra = sorted(row_set - set(shipped))
    if missing:
        result.refuse(
            f"no-row: {', '.join(missing)} on the `Shipped:` line and no rail row"
        )
    if extra:
        result.refuse(
            f"not-shipped: rail rows for {', '.join(extra)} and the `Shipped:` "
            f"line does not name them"
        )

    _check_minted(result, rail_body, one_body, shipped, stages)
    _check_forks(result, briefing, rail_body, one_body, stages)
    # Every issue the block names anywhere, with the stage its own row states.
    # A band member may be shipped or may be a hole the run left: the
    # generator's band on `batch-45c8b1` carries `509`, which was minted.
    known = {c[0]: c[1] for c in _table_rows(rail_body, MINTED_HEADER) or [] if len(c) >= 2}
    known.update({c[0]: c[1] for c in rows if len(c) >= 2})
    _check_bands(result, rail_body, stages, known)

    members = _band_members(_band_rows(rail_body))
    for cells in rows:
        if len(cells) >= 4 and cells[1] == "floor" and cells[0] in members:
            result.refuse(
                f"floor-in-band: row {cells[0]} reads `floor` and a band names it; "
                f"a band member is drawn on the rail, never under the floor"
            )

    return result


def _span(cell: str, stages: list[str] | None) -> tuple[list[str] | None, str | None]:
    """The columns a `first..last` cell covers, or a reason it covers none.

    The vocabulary's order is the drawn order, so the span is the slice between
    the two keys and a reversed pair is not the same span read backwards: it is
    a cell nobody can draw. `floor` is never spannable, because the floor row
    is drawn beneath every band rather than beside one.

    Returns `(None, reason)` on a bad cell and `(columns, None)` on a good one.
    Where there is no vocabulary the cell's shape is still graded and its keys
    are not, which is rule 4 of `run-picture-stages.md`.
    """
    found = SPAN.match(cell.strip())
    if not found:
        return None, (
            f"`{cell}` is not a span; a span is two stage keys as `first..last`"
        )
    first, last = found.group(1), found.group(2)
    if stages is None:
        return None, None
    for key in (first, last):
        if key not in stages:
            return None, f"`{key}` is not a stage in the vocabulary"
        if key == "floor":
            return None, (
                "`floor` is never spannable; the floor row is drawn beneath "
                "every band, so a band cannot reach it"
            )
    start, end = stages.index(first), stages.index(last)
    if start > end:
        return None, (
            f"`{first}..{last}` runs backwards; a span is a contiguous range "
            f"in the order docs/agents/run-picture-stages.md sets"
        )
    return [key for key in stages[start : end + 1] if key != "floor"], None


def _bad_seats(cell: str) -> str | None:
    """Why the `Seats` cell cannot be drawn, or None where it can.

    An EMPTY cell is a band with no pills, which is the normal case: two of the
    three banded runs the generator draws carry no seats. A cell that holds
    anything states all three, in the order the pills draw them.
    """
    if not cell.strip():
        return None
    marks = [part.strip() for part in cell.split(",") if part.strip()]
    if len(marks) != len(SEATS):
        return (
            f"`{cell.strip()}` names {len(marks)} seats; a `Seats` cell states "
            f"all three, in the order {', '.join(SEATS)}, or it is empty"
        )
    for seat, mark in zip(SEATS, marks):
        parts = mark.split()
        if len(parts) != 2 or parts[0] != seat:
            return (
                f"`{mark}` is not `{seat} <mark>`; the seats are drawn in the "
                f"fixed order {', '.join(SEATS)} and the cell states that order"
            )
        if parts[1] not in MARKS:
            return (
                f"`{parts[1]}` is not a mark; a seat takes one of "
                f"{', '.join(MARKS)}"
            )
    return None


def _check_chips(result: Result, rail_body: str, held: dict[str, str]) -> None:
    """Every band member has one line of its own words, and no line is spare.

    `held` maps each issue a band names to the band that names it, so a chip
    row is graded against the band it claims: a row under `B9` where no band
    `B9` exists is as wrong as a row for an issue the band never named.
    """
    rows = _table_rows(rail_body, CHIPS_HEADER) or []
    seen: dict[str, int] = {}
    for cells in rows:
        if len(cells) < len(CHIPS_HEADER):
            result.refuse(
                f"bad-chip-row: `{' | '.join(cells)}` has {len(cells)} cells and "
                f"a chip row is {', '.join(CHIPS_HEADER)}"
            )
            continue
        band, issue, text = cells[:3]
        if held.get(issue) != band:
            result.refuse(
                f"chip-not-in-the-band: `{CHIPS_HEADING}` gives {issue} to band "
                f"{band}, and that band's `Issues` cell does not name it"
            )
            continue
        seen[issue] = seen.get(issue, 0) + 1
        if not text.strip():
            result.refuse(
                f"no-chip-text: {issue}'s chip row holds no text; a chip draws "
                f"its own words under it and a blank cell draws a bare number"
            )
        result.longest = max(result.longest, len(text))
    for issue, count in seen.items():
        if count > 1:
            result.refuse(
                f"duplicate-chip: {issue} has {count} rows under "
                f"`{CHIPS_HEADING}` and draws one chip"
            )
    missing = [issue for issue in held if issue not in seen]
    if missing:
        result.refuse(
            f"no-chip-text: {', '.join(sorted(missing))} named by a band and "
            f"given no row under `{CHIPS_HEADING}`; every chip draws its own "
            f"words, and the space one has is 12 to 23 characters a line"
        )


def _check_bands(
    result: Result,
    rail_body: str,
    stages: list[str] | None,
    known: dict[str, str],
) -> None:
    """Every band row is a shape the board can draw, and nothing more.

    **A band is stated, never derived.** Nothing here finds a subject, and a
    run that states no bands passes every rule below. So the floor is only ever
    a refusal of a shape — one issue, or one column, which is a card — and it
    is not what stops a finale inventing a subject. The membership rule is:
    every issue a band names has a row elsewhere in the block, so a band cannot
    carry an issue the run never touched.
    """
    rows = _band_rows(rail_body)
    result.bands = len(rows)
    held: dict[str, str] = {}
    keys: dict[str, int] = {}
    for cells in rows:
        if len(cells) < len(BANDS_HEADER):
            result.refuse(
                f"bad-band-row: `{' | '.join(cells)}` has {len(cells)} cells and "
                f"a band row is {', '.join(BANDS_HEADER)}"
            )
            continue
        key, span_cell, kind, issues_cell = cells[:4]
        keys[key] = keys.get(key, 0) + 1
        issues = _band_ids(issues_cell)
        columns, why = _span(span_cell, stages)
        if why is not None:
            result.refuse(f"bad-band-span: band {key}: {why}")
        width = len(columns) if columns is not None else None
        if len(issues) < BAND_MIN_ISSUES or (
            width is not None and width < BAND_MIN_COLUMNS
        ):
            # The column half is stated only where it was measured. With no
            # vocabulary the span's keys go ungraded, and `0 columns` there
            # would send a reader after a span fault nobody looked for.
            across = (
                f"{width} column{'' if width == 1 else 's'}"
                if width is not None
                else "a span this guard could not measure"
            )
            result.refuse(
                f"band-too-small: band {key} names {len(issues)} issue"
                f"{'' if len(issues) == 1 else 's'} across {across}; a band is "
                f"{BAND_MIN_ISSUES} issues across {BAND_MIN_COLUMNS} columns or "
                f"it is a card"
            )
        for issue in issues:
            stage = known.get(issue)
            if stage is None:
                result.refuse(
                    f"band-not-in-the-block: band {key} names {issue} and neither "
                    f"the shipped table nor `{MINTED_HEADING}` holds a row for "
                    f"it; a band groups what the run touched and states nothing "
                    f"the block does not"
                )
            elif columns is not None and stage not in columns:
                result.refuse(
                    f"member-outside-span: band {key} spans `{span_cell}` and "
                    f"names {issue}, whose row reads `{stage}`; a member's stage "
                    f"is inside its band's span"
                )
            if issue in held:
                result.refuse(
                    f"issue-in-two-bands: {issue} is named by band {held[issue]} "
                    f"and by band {key}; an issue is drawn once, as a chip in one "
                    f"band"
                )
            else:
                held[issue] = key
        if kind not in KINDS:
            result.refuse(
                f"bad-band-kind: band {key} names `{kind}`; a band's kind is one "
                f"of {', '.join(KINDS)}, the same four a card takes"
            )
        why = _bad_seats(cells[BANDS_HEADER.index("seats")])
        if why is not None:
            result.refuse(f"bad-seats: band {key}: {why}")
    for key, count in keys.items():
        if count > 1:
            result.refuse(
                f"duplicate-band: band `{key}` has {count} rows and takes one; "
                f"both guards key a band by that cell, so a second row of the "
                f"same name overwrites the first and one band leaves the picture"
            )
    _check_chips(result, rail_body, held)


def _check_minted(
    result: Result,
    rail_body: str,
    one_body: str,
    shipped: list[str],
    stages: set[str] | None,
) -> None:
    """Every issue the run left open has one dashed row, and no row has no issue.

    The set of holes is the `Minted:` line UNION the `Did not ship:` line, both
    fields of the one-screen block. A dashed card is an issue the run named and
    did not close, and the definition has two halves on purpose: promotion
    minted it, OR the run left it open. On `99b-99e-6e11ba` promotion minted
    nothing and the rail draws `99f` dashed, so a check comparing the rows
    against the minted list alone refuses that run's own correct board.

    An absent line reads as an empty list, which is the strict direction: a
    dashed row with no line naming it is refused rather than passed.
    """
    rows = _table_rows(rail_body, MINTED_HEADER) or []
    result.minted = len(rows)
    holes = set(_ids(_field(one_body, "Minted") or ""))
    holes |= set(_ids(_field(one_body, "Did not ship") or ""))

    seen: dict[str, int] = {}
    for cells in rows:
        if len(cells) < 3:
            result.refuse(
                f"bad-minted-row: `{' | '.join(cells)}` has fewer than three "
                f"cells; a minted row is issue, stage, sentence"
            )
            continue
        issue, stage, sentence = cells[:3]
        seen[issue] = seen.get(issue, 0) + 1
        if stages is not None and stage not in stages:
            result.refuse(
                f"bad-stage: minted row {issue} names `{stage}`, which is not a "
                f"stage in the vocabulary"
            )
        result.longest = max(result.longest, len(sentence))
        if len(sentence) >= SENTENCE_LIMIT:
            result.refuse(
                f"sentence-too-long: minted row {issue}'s sentence is "
                f"{len(sentence)} characters; the bound is 59 characters or fewer"
            )
    for issue, count in seen.items():
        if count > 1:
            result.refuse(
                f"duplicate-minted: issue {issue} has {count} minted rows and takes one"
            )

    missing = [i for i in sorted(holes) if i not in seen]
    if missing:
        result.refuse(
            f"no-minted-row: {', '.join(missing)} on the `Minted:` or `Did not "
            f"ship:` line and no row under `{MINTED_HEADING}`; a hole the run "
            f"left is drawn or it vanished from the picture"
        )
    extra = sorted(set(seen) - holes)
    if extra:
        shipped_too = [i for i in extra if i in shipped]
        result.refuse(
            f"not-minted: minted rows for {', '.join(extra)} and neither the "
            f"`Minted:` nor the `Did not ship:` line names them"
            + (f"; {', '.join(shipped_too)} shipped, and a shipped issue takes a "
               f"card in the table above" if shipped_too else "")
        )


def _check_forks(
    result: Result, briefing: str, rail_body: str, one_body: str,
    stages: set[str] | None,
) -> None:
    """Every fork waiting on the human has one amber row, and the count agrees.

    **The `## Decide` prose is read for one thing: whether it exists.** The
    criterion this was cut from asked for the items under every `## Decide`
    heading to be counted and compared. Measured 2026-09-05 across the five
    runs the picture draws, that cannot be built. All five carry TWO `## Decide`
    headings in three item formats, and two of the five defeat any counter:
    `batch-88624c`'s own first section says "Six open forks, in two places in
    this file", four under the second heading and TWO under `### Refused - 37,
    and two of them are worth your veto`, which is not a `## Decide` heading at
    all; and `99b-99e-6e11ba`'s first section holds one `- **` bullet that is a
    verify gate's REJECT report rather than a fork. A counter over that prose
    refuses two of five correct briefings, which is the fault the criterion
    itself names on `batch-375cbf`.

    So the count comes from the one-screen table's `Forks to decide` row. Both
    it and the fork rows are figures the finale WROTE, in one file, and a
    disagreement is a fork drawn and not counted, or counted and not drawn.
    """
    rows = _table_rows(rail_body, FORKS_HEADER) or []
    result.forks = len(rows)

    seen: dict[str, int] = {}
    for cells in rows:
        if len(cells) < 3:
            result.refuse(
                f"bad-fork-row: `{' | '.join(cells)}` has fewer than three "
                f"cells; a fork row is fork, stage, question"
            )
            continue
        key, stage, question = cells[:3]
        seen[key] = seen.get(key, 0) + 1
        if stages is not None and stage not in stages:
            result.refuse(
                f"bad-stage: fork row {key} names `{stage}`, which is not a "
                f"stage in the vocabulary"
            )
        result.longest = max(result.longest, len(question))
        if len(question) >= SENTENCE_LIMIT:
            result.refuse(
                f"question-too-long: fork row {key}'s question is "
                f"{len(question)} characters; the bound is 59 characters or "
                f"fewer, and the card's question is a compression the finale "
                f"writes rather than a `## Decide` heading copied"
            )
    for key, count in seen.items():
        if count > 1:
            result.refuse(
                f"duplicate-fork: fork `{key}` has {count} rows; a fork key is "
                f"unique across the whole briefing, or two amber cards collide "
                f"and the board's guard cannot tell which row a card came from"
            )

    counted = _figure(one_body, FORKS_FIGURE)
    if counted is None:
        return
    if len(rows) != int(counted):
        result.refuse(
            f"fork-count: {len(rows)} rows under `{FORKS_HEADING}` and the "
            f"one-screen table counts {int(counted)} forks to decide; one fork "
            f"is one row"
        )
    if counted >= 1 and not DECIDE_HEADING.search(briefing):
        result.refuse(
            f"no-decide: the one-screen table counts {int(counted)} forks to "
            f"decide and the briefing carries no `## Decide` heading, so the "
            f"questions themselves are not in the file"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a rail block the board could not transcribe."
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

    stages: set[str] | None = None
    located = locate_stages(args.stages)
    if located is None:
        print(
            f"no stage vocabulary at {args.stages}, here or under the git top level: "
            f"the stage rule is not run here, and everything else is (rule 4 of "
            f"run-picture-stages.md)"
        )
    else:
        stages = read_stages(located.read_text())
        if stages is None:
            print(
                f"REFUSED no-stages-table: {located} exists and holds no table headed "
                f"`Key`, so the vocabulary cannot be read",
                file=sys.stderr,
            )
            return 2

    result = check(briefing, stages)
    if not result.refusals:
        print(result.summary())
        print(
            "It graded keys, counts and lengths and nothing else. Whether a "
            "sentence is true or a stage is the right one passed unread."
        )
        return 0
    for reason in result.refusals:
        print(f"REFUSED {reason}", file=sys.stderr)
    return 2 if result.fatal else 1


if __name__ == "__main__":
    sys.exit(main())
