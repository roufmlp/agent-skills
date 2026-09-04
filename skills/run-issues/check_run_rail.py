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
from the repo root and from `.scratch/<feature>/` alike. Where no file exists
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
KINDS = ("new", "fix", "guard", "harness")
# A sentence of this many characters or more is refused. The bound as a
# sentence is `59 characters or fewer`, and the rail card cannot draw a longer one.
SENTENCE_LIMIT = 60
SHIPPED_HEADER = ("issue", "stage", "kind", "sentence")
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


def read_stages(text: str) -> set[str] | None:
    """The stage keys from the vocabulary table, or None when it holds no table.

    The table is found by its `Key` header. The key is the first cell with its
    backticks removed. Nothing else in that file is read.
    """
    lines = text.splitlines()
    header = next(
        (i for i, line in enumerate(lines) if _cells(line)[:1] == ["Key"]), None
    )
    if header is None:
        return None
    keys: set[str] = set()
    for line in lines[header + 2 :]:
        if not line.strip().startswith("|"):
            break
        keys.add(_cells(line)[0].strip("`"))
    return keys or None


def locate_stages(path: str) -> pathlib.Path | None:
    """The vocabulary file at `path`, or at `path` under the git top level, or
    None where neither exists. The finale's command names the path relative to
    the repo root and may run from `.scratch/<feature>/`."""
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


def _shipped_rows(body: str) -> list[list[str]] | None:
    """The rows of the table headed `| Issue | Stage | Kind | Sentence |`.

    None where the block holds no such header. The read stops at the first
    line that is not a table row, so a `###` sub-heading ends it.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and tuple(
            cell.lower() for cell in _cells(line)
        ) == SHIPPED_HEADER:
            rows = []
            for row in lines[i + 2 :]:
                if not row.strip().startswith("|"):
                    break
                rows.append(_cells(row))
            return rows
    return None


def _band_members(body: str) -> set[str]:
    """Every issue id a `### Bands` table names. Empty where there is no table."""
    start = body.find(BANDS_HEADING)
    if start < 0:
        return set()
    lines = body[start:].splitlines()
    header = next((i for i, line in enumerate(lines) if line.strip().startswith("|")), None)
    if header is None:
        return set()
    columns = [cell.lower() for cell in _cells(lines[header])]
    if "issues" not in columns:
        return set()
    at = columns.index("issues")
    members: set[str] = set()
    for row in lines[header + 2 :]:
        if not row.strip().startswith("|"):
            break
        cells = _cells(row)
        if len(cells) > at:
            members.update(_ids(cells[at]))
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
    return Rail(rows=_shipped_rows(body) or [], bands=_band_members(body))


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
    stages_graded: bool = True

    def refuse(self, reason: str, fatal: bool = False) -> None:
        self.refusals.append(reason)
        self.fatal = self.fatal or fatal

    def summary(self) -> str:
        graded = "graded" if self.stages_graded else "NOT graded, no vocabulary"
        return (
            f"ok: {self.shipped} shipped, {self.rows} rail rows, longest sentence "
            f"{self.longest} characters, {self.lit} stages lit, stage keys {graded}"
        )


def check(briefing: str, stages: set[str] | None) -> Result:
    """Every refusal the briefing earns, each starting with its reason word.

    `stages` None means no vocabulary exists here, and the stage rule is skipped.
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

    members = _band_members(rail_body)
    for cells in rows:
        if len(cells) >= 4 and cells[1] == "floor" and cells[0] in members:
            result.refuse(
                f"floor-in-band: row {cells[0]} reads `floor` and a band names it; "
                f"a band member is drawn on the rail, never under the floor"
            )

    return result


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
