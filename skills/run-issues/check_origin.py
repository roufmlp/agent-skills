#!/usr/bin/env python3
"""Refuse a register row, or a minted issue, that does not name where it came from.

Ticket 37 of the pilot-delivery map, ruling 7, ruled by the human on 2026-09-05.

WHY IT EXISTS. "Escaped faults" -- a fault found later that traces back to the
run that shipped it -- is the only measure of what the pipeline lets through,
and it was not measurable at all. Measured 2026-09-05: no register row, issue
file or commit message carries a field naming the run or the issue that shipped
the code. The finder's row shape carries no origin field, and promotion writes
the fact as a blockquote that nothing reads.

THE FACT ALREADY EXISTS, IN PROSE. Shard `rv149e.md` of run `batch-170a59`
opens its owner-notes with "From issue 149e's review gate, run `batch-170a59`".
So the writer knows it and writes it; it is uncountable because it is a
sentence. This gives it a cell.

NOTHING BACKFILLS, and that is held mechanically rather than by a date. Ruling 7
starts the count the day the key lands. A table whose header does not declare an
`origin` column is history and is skipped whole -- not graded and not reported.
The register holds rounds going back to `b01` under a dozen header shapes, and a
check that refused them would report hundreds of faults nobody can act on, which
is a check people learn to ignore.

That leaves one hole this file cannot close: a NEW table typed without the
column escapes, because a missing column and a historical table look alike here.
`origin-row-guard.py` in the hooks closes it at the moment of writing, which is
the only place the difference is visible.

THE GRAMMAR. Two parts, an issue and a run, written `<issue>/<run>`:

    149e/batch-170a59     both known
    unknown/batch-170a59  the run is known and no single issue is
    149e/unknown          the issue is known and the run is not
    unknown               neither is known

`unknown` is the explicit null, and it is legal on purpose. It copies `Owed:
unsorted`, ruled by the human on 2026-08-13: a null that is present cannot be told
from a field somebody forgot, and a writer with no legal way to say "I do not
know" invents one. The production watcher files rows from Sentry groups and
genuinely does not know either half. The count of `unknown` is printed, so the
rate stays visible without a refusal.

WHAT IT DOES NOT DO. It never judges whether an origin is TRUE. A row naming the
wrong run passes here, because nothing in the file can tell. It grades the shape
a writer filed.

It prints EVERY offence, not the first, so one pass repairs a whole file. That
copies `check_register_status.py` beside it, which is correct for the same
reason: both grade a file a person is about to repair by hand, and stopping at
the first turns one repair into many passes.

THE MERGE CEILING, ruled by the human on 2026-09-13. Run `batch-d67136` shipped 7
issues and minted 13, because the promotion brief said "One issue file per
promoted row" and nothing else. Three of the 13 were one finding written twice,
and two of those three were asked for in plain words by the finale's own merge
briefing, which promotion had no licence to obey. Promotion may now resolve up
to three rows into one file. `--issue` grades the ceiling on the file promotion
has just written; `--minted` grades the pairs it did not merge, which needs two
files and so cannot live in the per-file mode.

THE PARKED RULE, ruled by the human on 2026-09-13, issue 03 of the
tracker-tooling set. One project's tracker carried 641 issues, 149 of them at
`needs-harden`, and not one of those 149 was named as a blocker by any other
issue: under `next_batch.py`'s
fan-out order an issue nothing waits on sits last for ever, so the backlog only
grows. A minted row at `medium` or `low` that names no blocker is now written
`Status: parked` with a `Parked: <ISO date>` line beside it; `high` and above
stays `needs-harden`. `--issue` grades that too, because it is a rule that can
refuse and CLAUDE.md's three classes say a rule that can refuse is built rather
than written down twice. The date is what the parked sweep ages the
issue off, and a parked issue with no date is parked for ever, which is the
deletion this status must not become.

THE AUDIENCE CLAUSE, ruled by the human on 2026-09-19, narrows the rule above:
an `operator` row goes to `needs-harden` whatever its severity, and only
`tester` and `agent` rows park. MEASURED on 2026-09-19 on one tracker: 50
parked issues, and every one of them `operator`/`medium`. Among them a list
page showing none of the design files it exists to show, a raise form that
never names the customer it just created, and two primary buttons painting dark
ink on dark green. The old rule read severity and a blocker and never the
audience, so it could not tell a screen from a build check. The cost, recorded
because the human must be able to overturn it: an `operator`/`medium` issue
nothing blocks still sorts last under `next_batch.py`'s fan-out, so the drain
for it is their eye rather than the sweep -- the gain is that it is visible and
offerable. THE SCRIPT LEARNED THE CLAUSE ON 2026-09-21, two days after the
ruling. Until then all nine issues promotion minted from one run exited 1 here
and nowhere else, and about 50 issues in that tracker carried a hand-written
`Un-parked: 2026-09-19` repair line, so the workaround was the majority case
and promotion was overriding its own checker every time.

Usage:
    python3 check_origin.py --register <register.md>
    python3 check_origin.py --issue <issue file>
    python3 check_origin.py --minted <run id> --issues <issue directory>

Exit 0 clean, 1 one or more offences, 2 the file could not be read. A third
meaning is never put on a code a caller reads.
"""

import argparse
import datetime
import os
import re
import sys
from collections import namedtuple
from pathlib import Path

# The parked rule below asks one question of the body -- does this file name a
# blocker -- and `next_batch.py` already answers it for the scheduler. The
# library is IMPORTED rather than copied, the shape
# `~/.claude/hooks/run-issues-evidence-gate.py` takes with `check_verdict`: two
# readers of one `## Blocked by` section that disagreed about what a bullet
# means would be a fault neither would report. The path is this file's own tree,
# so a worktree grades against the copy it is changing. A failed import REFUSES;
# a guard that switches itself off when its dependency moves is worse than none.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

try:
    import next_batch
except Exception as error:  # pragma: no cover - exercised by the import test
    next_batch = None
    LIB_IMPORT_ERROR = error
else:
    LIB_IMPORT_ERROR = None

Fault = namedtuple("Fault", "row_id reason line")

# The tracker's issue id: `512`, `149e`, `402b`. Same shape as
# `check_issue_ready.ID_FROM_NAME`, which reads it off a file name.
ISSUE = re.compile(r"^\d+[a-z]?$", re.IGNORECASE)

# A run or round id is one bare token. Deliberately not pinned harder: the
# record holds `batch-170a59`, `review-375cbf`, `bridge-cse` and `round-10`,
# and a pattern narrow enough to exclude a typo would exclude four of those.
RUN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

UNKNOWN = "unknown"

_BOLD = re.compile(r"\*+")

# A literal pipe inside a cell is written `\|`. Splitting on every pipe shifts
# every column after it and reports a clean row as a fault: the lesson
# `check_register_status.py` records from 2026-09-06.
_SPLIT = re.compile(r"(?<!\\)\|")


def cells(line):
    text = line.strip()
    text = text[1:] if text.startswith("|") else text
    text = text[:-1] if text.endswith("|") and not text.endswith("\\|") else text
    return [c.strip() for c in _SPLIT.split(text)]


def _is_separator(row):
    return all(set(c) <= set("-: ") for c in row if c != "")


def parse_origin(value):
    """The two halves of a legal origin, or None.

    Returns `(issue, run)`, either of which may be the word `unknown`.
    """
    text = _BOLD.sub("", value or "").strip().strip("`").strip().lower()
    if not text:
        return None
    if text == UNKNOWN:
        return (UNKNOWN, UNKNOWN)
    parts = text.split("/")
    if len(parts) != 2:
        return None
    issue, run = (p.strip().strip("`").strip() for p in parts)
    if not (issue == UNKNOWN or ISSUE.match(issue)):
        return None
    if not (run == UNKNOWN or RUN.match(run)):
        return None
    return (issue, run)


def graded(text):
    """Every row this file judges: `(row_id, origin cell, line number)`.

    ONE walk, used by both readers. `check_origin` grew a second copy of this
    loop for the `unknown` count, which is the drift `journal_for` taught in
    ticket 39 sitting 2: two readers of one shape disagree eventually, and the
    disagreement is silent.

    A table whose header declares no `origin` column yields nothing. That is
    where "nothing backfills" lives, and it is one line so it cannot be
    half-applied by one caller and not the other.
    """
    origin_at = id_at = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            origin_at = id_at = None
            continue
        row = cells(line)
        lower = [c.lower() for c in row]
        if "origin" in lower:
            origin_at = lower.index("origin")
            id_at = lower.index("id") if "id" in lower else 0
            continue
        if origin_at is None or _is_separator(row) or origin_at >= len(row):
            continue
        row_id = row[id_at].strip("` ") if id_at < len(row) else "(no id)"
        yield (row_id, row[origin_at], number)


def register_faults(text):
    """Every offence in one register or shard, in the order they appear."""
    found = []
    for row_id, cell, number in graded(text):
        if not _BOLD.sub("", cell).strip():
            found.append(Fault(row_id, "the origin cell is empty", number))
            continue
        if parse_origin(cell) is None:
            found.append(Fault(
                row_id,
                f"the origin cell reads {cell!r}, which is not "
                f"`<issue>/<run>` and is not `unknown`", number))
    return found


# The header field, on its own line, beside `Owed:` and `Stage:`. Anchored at
# the start of the line so a sentence opening with the word cannot pass for one.
ORIGIN_LINE = re.compile(r"^Origin:\s*(.*)$", re.MULTILINE | re.IGNORECASE)

# The issue's own title. Everything above it is the header; a field below it is
# body prose, whatever it is called.
TITLE = re.compile(r"^#\s+", re.MULTILINE)


# The rows this file resolves, on their own line in the header beside `Origin:`.
# One entry per row, `<row id> <audience>/<severity>`, entries split on `;`.
ROWS_LINE = re.compile(r"^Rows:\s*(.*)$", re.MULTILINE | re.IGNORECASE)

# The status the file was minted at, and the day it was parked. Both are header
# fields on their own line, read the same anchored way as `Origin:`.
STATUS_LINE = re.compile(r"^Status:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
# `**parked**` is the same answer as `parked`, the reading `Rows:` and `Origin:`
# already take. A refusal over a writer's own bold is a false alarm.
PARKED_LINE = re.compile(r"^Parked:\s*(.*)$", re.MULTILINE | re.IGNORECASE)

# The two statuses promotion writes, and the severities that decide between
# them. Issue 03 of the tracker-tooling set, ruled by the human, 2026-09-13.
PARKED = "parked"
NEEDS_HARDEN = "needs-harden"
PARKS = ("medium", "low")
HARDENS = ("critical", "high")

# The audience clause, ruled by the human on 2026-09-19. The three words
# promotion writes, and the two of them that may park. It is an ALLOWLIST of
# what parks rather than a list of what does not: a fourth word is a
# mislabelled row, and the one direction that must never happen by accident is
# a file going invisible. `operator` is the word that means a person using the
# product, so a row carrying it is always offered.
AUDIENCES = ("operator", "tester", "agent")
PARK_AUDIENCES = ("tester", "agent")

# The direct-road stamp, so a merged file can be refused one.
DIRECT_ROAD = re.compile(r"^Direct-road:\s*(\S+)", re.MULTILINE | re.IGNORECASE)

# The merge ceiling, ruled by the human on 2026-09-13. Three, not four: a merge
# rule with no ceiling is how three real defects become one unreviewable ticket.
CEILING = 3

Row = namedtuple("Row", "row_id audience severity")

_ENTRY = re.compile(r"^(\S+)\s+([A-Za-z]+)\s*/\s*([A-Za-z]+)$")


def parse_rows(value):
    """The rows a `Rows:` line declares, or None where it is not the grammar.

    An empty list is never returned: a line declaring nothing is not the
    grammar either, and a caller that could not tell them apart would report a
    file resolving no row as a file resolving some.
    """
    text = _BOLD.sub("", value or "").strip()
    if not text:
        return None
    found = []
    for part in text.split(";"):
        part = part.strip().strip("`").strip()
        if not part:
            return None
        match = _ENTRY.match(part.replace("`", ""))
        if not match:
            return None
        found.append(Row(match.group(1), match.group(2).lower(),
                         match.group(3).lower()))
    return found or None


def header_of(text):
    """Everything above the issue's own title.

    A field below the title is body prose, whatever it is called. Both header
    fields read it, so a sentence in the body opening with `Origin:` or `Rows:`
    cannot pass for the field.
    """
    title = TITLE.search(text)
    return text[:title.start()] if title else text


def _line_of(header, match):
    return header[:match.start()].count("\n") + 1


def _origin_faults(header):
    match = ORIGIN_LINE.search(header)
    if not match:
        return [Fault("(the issue file)",
                      "it carries no `Origin:` line in its header, above the "
                      "title, so nothing can say which run shipped the code "
                      "this fault is in", 0)]
    line = _line_of(header, match)
    value = match.group(1)
    if not _BOLD.sub("", value).strip():
        return [Fault("(the issue file)", "its `Origin:` line is empty", line)]
    if parse_origin(value) is None:
        return [Fault(
            "(the issue file)",
            f"its `Origin:` line reads {value.strip()!r}, which is not "
            f"`<issue>/<run>` and is not `unknown`", line)]
    return []


def _rows_faults(header):
    """The merge ceiling, clauses 1 to 3 and 5, ruled by the human, 2026-09-13.

    WHY THE LINE IS MANDATORY AT ONE ROW. The ceiling can only bite a file that
    declares what it resolved, and a line written only when a file merges is a
    line a merging writer can simply not write. The fact is already in the prose
    of every file run `batch-d67136` minted -- "Promoted from register row
    `rv01-6` ... Audience operator, severity medium". This gives it a cell, which
    is the move `Origin:` itself made three weeks earlier.

    WHAT IT CANNOT DO, and the limit is the same one this file already records
    for `Origin:`. It grades the DECLARATION. A file that resolves four rows and
    declares one passes, because the register those rows came from is deleted by
    the time anybody could compare the two.
    """
    match = ROWS_LINE.search(header)
    if not match:
        return [Fault("(the issue file)",
                      "it carries no `Rows:` line in its header, above the "
                      "title, so nothing can tell how many register rows it "
                      "resolves and the merge ceiling has nothing to count", 0)]
    line = _line_of(header, match)
    value = match.group(1)
    rows = parse_rows(value)
    if rows is None:
        return [Fault(
            "(the issue file)",
            f"its `Rows:` line reads {value.strip()!r}, which is not one or "
            f"more `<row id> <audience>/<severity>` entries split on `;`", line)]

    found = []
    if len(rows) > CEILING:
        found.append(Fault(
            "(the issue file)",
            f"its `Rows:` line declares {len(rows)} rows and the ceiling is "
            f"{CEILING}. Split it.", line))
    for field in ("audience", "severity"):
        values = sorted({getattr(r, field) for r in rows})
        if len(values) > 1:
            found.append(Fault(
                "(the issue file)",
                f"its `Rows:` line merges rows of different {field} "
                f"({', '.join(values)}). Merging a lower one into a higher one "
                f"carries it past the floor that dropped it.", line))
    if len(rows) > 1:
        stamp = DIRECT_ROAD.search(header)
        if stamp and stamp.group(1).strip("`").lower() == "candidate":
            found.append(Fault(
                "(the issue file)",
                f"it merges {len(rows)} rows and carries "
                f"`Direct-road: candidate`. A merged file is never a candidate: "
                f"one review pass reading three defects is the unreviewable "
                f"ticket that road must not take.",
                _line_of(header, stamp)))
    return found


def _status_faults(header, text):
    """The parked rule, issue 03 of the tracker-tooling set, ruled by the human,
    2026-09-13.

    A medium or low row that names no blocker is minted `Status: parked`, and
    high and above stays `needs-harden`. The measurement: one project's tracker
    carried 641 issues and 149 of them at needs-harden, and not one of the 149
    was named as a blocker by any other issue. Under `next_batch.py`'s fan-out order an issue
    nothing waits on sits last for ever, so the backlog only grows.

    THE AUDIENCE IS READ BEFORE THE SEVERITY, the clause the human ruled on
    2026-09-19. An `operator` row never parks, whatever its severity; only
    `tester` and `agent` rows reach the severity question at all. `operator` is
    the audience word that means a person using the product, and on 2026-09-19
    all 50 of one tracker's parked issues were `operator`/`medium` -- among
    them a list page showing none of the design files it exists to show. The
    same rule is written out in `~/.claude/agents/promotion.md`, which is the
    writer this grades; the two are kept in step by the drill beside this file.

    AN AUDIENCE THE CLAUSE CANNOT PLACE IS REFUSED BY NAME, whatever status the
    file carries. The clause is an allowlist of what may park, so an unknown
    word lands in the refused pile rather than passing quietly: promotion writes
    one of three words, and a fourth is a mislabelled row. This is the one field
    a silent pass would decide, because a wrong audience is the difference
    between a file the human is offered and one they never see. The severity
    vocabulary is still silent on a word it does not know, which is older than
    this clause and is not what 2026-09-19 ruled on.

    IT IS GRADED HERE RATHER THAN REMEMBERED IN THE BRIEF. Promotion already
    runs this check on every file it mints, and a rule that can refuse is built
    rather than written down twice (`~/.claude/CLAUDE.md`, the three classes).

    A parked file carries `Parked: <ISO date>`, because the parked sweep ages
    an issue off that line and a parked issue with no date is parked for ever --
    the deletion the status must not become.

    IT IS SILENT WHERE THE `Rows:` LINE CANNOT BE READ, and where the rows
    declared disagree about severity. Both are already a refusal from
    `_rows_faults`, which names the repair; one cause, one fault. Grading a
    disagreement on the first row would tell the writer to park a file carrying
    a `high` row, and a parked high finding is offered by nothing until the
    thirty-day sweep.
    """
    if next_batch is None:  # pragma: no cover - exercised by the import test
        return [Fault("(the issue file)",
                      f"the parked rule needs `next_batch.py` beside this "
                      f"script and it could not be imported "
                      f"({LIB_IMPORT_ERROR}). Nothing was graded.", 0)]
    rows_line = ROWS_LINE.search(header)
    rows = parse_rows(rows_line.group(1)) if rows_line else None
    if not rows:
        return []
    declared = {r.severity for r in rows}
    if len(declared) > 1:
        return []
    if len({r.audience for r in rows}) > 1:
        return []
    severity = rows[0].severity
    if severity not in PARKS + HARDENS:
        return []
    audience = rows[0].audience
    if audience not in AUDIENCES:
        return [Fault("(the issue file)",
                      f"its `Rows:` line reads the audience {audience!r}, which "
                      f"is not `operator`, `tester` or `agent`, so nothing can "
                      f"tell whether this file parks. Name the row's own "
                      f"audience.", _line_of(header, rows_line))]

    status_line = STATUS_LINE.search(header)
    if not status_line:
        return [Fault("(the issue file)",
                      "it carries no `Status:` line in its header, above the "
                      "title, so nothing can tell whether it was parked", 0)]
    status = _BOLD.sub("", status_line.group(1)).strip("`").lower()
    line = _line_of(header, status_line)
    blockers = next_batch.blockers_of(text.splitlines())
    parks = (severity in PARKS and audience in PARK_AUDIENCES and not blockers)
    wanted = PARKED if parks else NEEDS_HARDEN
    if status != wanted and wanted == PARKED:
        return [Fault("(the issue file)",
                      f"its rows are `{audience}`/`{severity}` and its "
                      f"`## Blocked by` names no issue, so promotion writes "
                      f"`Status: parked` and this file reads {status!r}. A "
                      f"needs-harden issue nothing waits on sits last for "
                      f"ever.", line)]
    if status != wanted:
        # Where two of the three reasons are true at once the message names
        # one, and it names the oldest: a blocker, then the severity, then the
        # audience. A reader repairing an `operator`/`high` file needs to be
        # told the thing that has been true since 2026-09-13, not the newest
        # clause that also happens to catch it.
        if blockers:
            why = f"its `## Blocked by` names {blockers[0]}"
        elif severity in HARDENS:
            why = f"its rows are `{severity}`"
        else:
            why = (f"its rows are `{audience}`, the audience of a person using "
                   f"the product")
        return [Fault("(the issue file)",
                      f"{why}, so promotion writes `Status: needs-harden` and "
                      f"this file reads {status!r}. Parked is for an issue "
                      f"nothing waits on, that waits on nothing, and that no "
                      f"person using the product ever sees.", line)]
    if status != PARKED:
        return []

    parked_line = PARKED_LINE.search(header)
    if not parked_line:
        return [Fault("(the issue file)",
                      "it is parked and carries no `Parked:` line in its "
                      "header, so the parked sweep cannot age it and it is "
                      "parked for ever", line)]
    value = _BOLD.sub("", parked_line.group(1)).strip().strip("`")
    try:
        datetime.date.fromisoformat(value.split()[0])
    except (ValueError, IndexError):
        return [Fault("(the issue file)",
                      f"its `Parked:` line reads {value!r}, which is not an ISO "
                      f"date (`2026-09-13`), so the sweep cannot age it",
                      _line_of(header, parked_line))]
    return []


def issue_faults(text):
    """Every offence in one minted issue file.

    A list, not a single fault, so one caller shape serves both halves of this
    check and a future second rule on the same file has somewhere to land.
    """
    header = header_of(text)
    return (_origin_faults(header) + _rows_faults(header)
            + _status_faults(header, text))


# The sweep over one run's minted files -------------------------------------
#
# Ordinary English function words, and nothing from any domain. A domain word in
# this list would be a list tuned to run `batch-d67136`, which is one run.
STOPWORDS = frozenset("""
a an and as at but by for from in is it its no not of on or that the to with
""".split())

# `40-ci-runs-no-next-build.md` -> the number token, then the slug.
_NAME = re.compile(r"^(\d+[a-z]?)-(.+)\.md$", re.IGNORECASE)

# The line that says two files of one origin are deliberately two.
SIBLINGS_LINE = re.compile(r"^Siblings:\s*(.*)$", re.MULTILINE | re.IGNORECASE)

# An em dash, or the two hyphens a keyboard reaches for instead.
_REASON_SPLIT = re.compile(r"\s+(?:\u2014|--)\s+")


def issue_number(name):
    """The tracker number a minted file's name carries, or None."""
    match = _NAME.match(os.path.basename(name))
    return match.group(1).lower() if match else None


def slug_words(name):
    """The words of a minted file's slug, function words dropped.

    WHY THE SLUG AND NOT THE ORIGIN ALONE. Measured over run `batch-d67136`'s
    thirteen files: grouping on `Origin:` alone fires on 11 of the 13 and finds
    the 3 true pairs among 17, which is 17.6 per cent precision and a rule
    promotion learns to wave through. Adding one shared slug word fires on 5
    pairs and still catches all 3 -- 60 per cent precision at the same recall.
    A false fire costs one `Siblings:` line, and that line is worth writing.
    """
    base = os.path.basename(name)
    match = _NAME.match(base)
    # The extension is dropped on BOTH roads. It used to survive the fallback,
    # so two files outside the tracker's naming shape shared the word `md` and
    # were reported as one finding written twice.
    slug = match.group(2) if match else os.path.splitext(base)[0]
    words = {w.lower() for w in re.split(r"[-_.]+", slug) if w}
    return {w for w in words if w not in STOPWORDS}


def parse_siblings(value):
    """`(the ids named, the reason)`, or None where it is not the grammar.

    The reason is required. A bare id says two files are two and does not say
    why, which is the sentence the reader of the tracker actually needs.
    """
    text = _BOLD.sub("", value or "").strip()
    if not text:
        return None
    parts = _REASON_SPLIT.split(text, maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        return None
    ids = set()
    for part in parts[0].split(","):
        part = part.strip().strip("`").strip()
        if not ISSUE.match(part):
            return None
        ids.add(part.lower())
    return (ids, parts[1].strip()) if ids else None


def _minted_file(name, text):
    """What the sweep needs off one file, or None where it is history.

    A file carrying no `Origin:` line is skipped whole -- not graded and not
    reported. That is the same fence the register walk holds: ruling 7 starts
    the count the day the key lands, and every issue minted before it carries
    none. The hole it leaves, a NEW file written without the line, is closed by
    `--issue`, which promotion runs on every file at the moment it mints it.
    """
    header = header_of(text)
    match = ORIGIN_LINE.search(header)
    if not match:
        return None
    origin = parse_origin(match.group(1))
    if origin is None:
        return None
    return (origin, header)


def _selected(run, files):
    """`(entries, faults)` for one run's minted files, parsed ONCE.

    An entry is `(name, issue, slug words, siblings)`. The faults are bad
    `Siblings:` lines, which are found while reading and have nowhere else to
    come from. One parse and one call site: this file's own `graded` records
    why a second reader of one shape is the fault to avoid.
    """
    run = (run or "").strip().lower()
    entries, faults = [], []
    for name, text in files:
        parsed = _minted_file(name, text)
        if parsed is None:
            continue
        (issue, origin_run), header = parsed
        if origin_run != run:
            continue
        base = os.path.basename(name)
        siblings = set()
        match = SIBLINGS_LINE.search(header)
        if match:
            read = parse_siblings(match.group(1))
            if read is None:
                faults.append(Fault(
                    base,
                    f"its `Siblings:` line reads "
                    f"{match.group(1).strip()!r}, which does not name an issue "
                    f"number and give a reason after an em dash. A bare number "
                    f"says two files are two without saying why.",
                    _line_of(header, match)))
            else:
                siblings = read[0]
        entries.append((base, issue, slug_words(base), siblings))
    return entries, faults


def _pair_faults(run, entries):
    """Every two entries of one origin that share a word and name no sibling."""
    found = []
    for index, first in enumerate(entries):
        for second in entries[index + 1:]:
            one, one_issue, one_words, one_sibs = first
            two, two_issue, two_words, two_sibs = second
            if one_issue != two_issue:
                continue
            shared = sorted(one_words & two_words)
            if not shared:
                continue
            if issue_number(two) in one_sibs or issue_number(one) in two_sibs:
                continue
            found.append(Fault(
                one,
                f"it and `{two}` came out of the same issue "
                f"({one_issue}/{run}) and share "
                f"{', '.join(repr(word) for word in shared)}. "
                f"Merge them into one file, or give one of them a `Siblings:` "
                f"line naming the other and saying in one line why they are two.",
                0))
    return found


def minted_faults(run, files):
    """Two files of one run that look like one finding written twice.

    `files` is `(name, text)` pairs. Run `batch-d67136` shipped 7 issues and
    minted 13, and 3 of the 13 were pairs: the runner's own close of issue 03
    says 34 and 35 "describe the same thing", and the merge briefing asked
    promotion in plain words to read two further pairs together (lines 625 and
    633). Promotion had no licence to merge and resolved each one alone.
    """
    entries, faults = _selected(run, files)
    return faults + _pair_faults((run or "").strip().lower(), entries)


def graded_rows(text):
    """`(graded, unknown)` — how many rows were judged, and how many took `unknown`.

    The pass line prints both. Ruling 7 skips a table declaring no `origin`
    column, so a file can be clean because nothing in it was graded, and a pass
    that does not say so is the `ok` on a table nobody could read that
    `check_commit_order.status_rows` exists to prevent.

    `unknown` is legal and refused by nothing, so the only way its rate stays
    honest is for the pass to say how many took it.
    """
    rows = list(graded(text))
    blank = sum(1 for _, cell, _ in rows if parse_origin(cell) == (UNKNOWN, UNKNOWN))
    return (len(rows), blank)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--register", help="a register or shard file to grade")
    what.add_argument("--issue", help="a minted issue file to grade")
    what.add_argument("--minted", metavar="RUN",
                      help="sweep one run's minted files for pairs; needs "
                           "--issues. Scoped by run id, so it backfills nothing")
    parser.add_argument("--issues", metavar="DIR",
                        help="the issue directory --minted sweeps")
    parser.add_argument("--quiet", action="store_true",
                        help="print the offences and nothing else")
    args = parser.parse_args(argv)

    # `is not None`, never truthiness. `--minted ""` is falsy, and reading it as
    # "no sweep asked for" sent `path` to None and `os.path.exists` to a
    # TypeError. `--register ""` and `--issue ""` both exit 2, so the sweep must
    # not be the one mode that raises.
    if args.minted is not None and args.issues is None:
        parser.error("--minted needs --issues <issue directory>")
    if args.issues is not None and args.minted is None:
        parser.error("--issues is only read with --minted <run id>")

    if args.minted is not None:
        return _sweep(args.minted, args.issues, args.quiet)

    path = args.register or args.issue
    if not os.path.exists(path):
        print(f"check_origin: no such file: {path}", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as err:
        print(f"check_origin: cannot read {path}: {err}", file=sys.stderr)
        return 2

    found = (register_faults(text) if args.register else issue_faults(text))
    for fault in found:
        where = f"{path}:{fault.line}" if fault.line else path
        print(f"{where}: {fault.row_id}: {fault.reason}")
    if found:
        if args.register:
            print(f"{len(found)} row(s) refused. Add the origin and run this "
                  f"again.")
        else:
            print(
                f"{len(found)} offence(s) in this issue file. Repair them and "
                f"run this again.\n"
                f"This mode grades a file promotion has JUST minted. Every issue "
                f"written before ticket 37 landed carries no `Origin:` line by "
                f"design — ruling 7 starts the count the day the key lands and "
                f"backfills nothing — and none carries a `Rows:` line either, "
                f"so do not run it over the issue directory.")
        return 1
    if not args.quiet:
        if args.register:
            graded, blank = graded_rows(text)
            print(f"{path}: {graded} row(s) graded, all naming an origin; "
                  f"{blank} took `unknown`. A table declaring no `origin` "
                  f"column is history and is not graded.")
        else:
            print(f"{path}: the `Origin:` and `Rows:` lines are present and "
                  f"read, and the `Status:` line matches the parked rule.")
    return 0


def _sweep(run, folder, quiet):
    """`--minted`: the pairs one run left unmerged, across its own files."""
    if not os.path.isdir(folder):
        print(f"check_origin: no such directory: {folder}", file=sys.stderr)
        return 2
    files = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".md"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                files.append((name, handle.read()))
        except OSError as err:
            print(f"check_origin: cannot read {name}: {err}", file=sys.stderr)
            return 2

    entries, found = _selected(run, files)
    selected = len(entries)
    found = found + _pair_faults(run.strip().lower(), entries)
    for fault in found:
        where = os.path.join(folder, fault.row_id)
        where = f"{where}:{fault.line}" if fault.line else where
        print(f"{where}: {fault.reason}")
    if found:
        print(f"{len(found)} pair(s) refused out of {selected} file(s) minted "
              f"by run {run}. Merge each pair, up to three rows in one file, or "
              f"give one file of it a `Siblings:` line naming the other.")
        return 1
    if not quiet:
        print(f"{folder}: {selected} file(s) carry an `Origin:` naming run "
              f"{run}, and no two of them look like one finding written twice. "
              f"A file naming another run, or carrying no `Origin:` line at "
              f"all, is not selected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
