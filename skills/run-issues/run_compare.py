#!/usr/bin/env python3
"""Read the pipeline's own records across runs. The fact behind `/run-compare`.

    python3 run_compare.py last
    python3 run_compare.py show <batch-id>
    python3 run_compare.py since <days>
    python3 run_compare.py compare <a> <b>
    python3 run_compare.py versions

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 4, deliverable 4. Rulings 8, 12, 13, 14 and 24.

## It reads. It never writes and never measures.

`run_costs.py` at a finale is the only writer of `runs.jsonl` and
`issues.jsonl`, and `run_records.write_view` the only writer of the view. This
script opens those three and nothing else, so a question asked twice gets the
same answer and asking it costs a run nothing.

## The comparison rule, and why it is not the row above

Ruling 12: a line compares against the previous line OF THE SAME KIND by
finale time. `run-costs.md`'s own header told a reader to compare against the
row above until today, and ticket 38 puts two runs and a hunt in flight at
once, so the row above is not the run before. A hunt never takes a run as its
predecessor; that is what replaced `parallel-hunt`'s `--no-append`.

`taken` is a DATE, so two lines finishing on one day tie, and the append index
breaks the tie. The file is append-only and a finale appends at its end, so
that index IS the finale order -- as close to "by finale time" as the record
can be read.
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_records


def ordered(records):
    """`[(index, record)]` in finale order.

    The index is the line's position in the file, kept because it is the only
    tie-break the record carries and because a refusal that names a line by
    its number is one a reader can go and find.
    """
    numbered = list(enumerate(records))
    return sorted(numbered, key=lambda pair: (str(pair[1].get("taken") or ""),
                                              pair[0]))


def previous_of_kind(found, position):
    """The previous line of the same kind, or None. Ruling 12."""
    kind = found[position][1].get("kind")
    for _, record in reversed(found[:position]):
        if record.get("kind") == kind:
            return record
    return None


# --------------------------------------------------------------------------
# The figures, and where each one lives on a line.
#
# `source` is the RECORD FIELD a figure is drawn from, and it is what the
# `borrowed` mark names. Sitting 2 marked seventeen of the eighteen lines and
# the mark is a LIST of exactly those five field names, so the skip is per
# figure: `hours` and `idle` were the run's own on every line ever written and
# a blanket skip would delete the two figures the whole history can answer.
#
# `better` says which way is an improvement, and it is used for the WORD only.
# Ruling 14 allows one threshold and this is not it: no figure here fires an
# alarm, whatever direction it moves.
# --------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class Figure:
    label: str
    path: tuple          # where the value sits on a record
    source: str          # the record field the `borrowed` mark would name
    unit: str = ""
    better: int = 0      # -1 lower is better, +1 higher is better, 0 neither
    per_model: bool = False
    # How the quantity is written. `run_records.render_view` renders weighted
    # tokens in millions and both shares as percentages, and a reader whose
    # units disagree with the page it points at is two readings of one figure.
    # `millions` renders to one decimal and `millions2` to two, which is what
    # `render_view` writes in the `Weighted` and `Per issue` columns.
    scale: str = "plain"  # plain | millions | millions2 | share


FIGURES = {
    "issues": Figure("issues", ("issues",), "issues"),
    "hours": Figure("wall clock", ("hours",), "hours", unit="h"),
    "subagents": Figure("subagents", ("subagents",), "subagents"),
    "idle": Figure("idle share", ("idle",), "idle", better=-1,
                   scale="share"),
    # Ruling 5's five, recorded rather than divided.
    "wall_min_per_issue": Figure(
        "wall minutes per issue", ("faster", "wall_minutes_per_issue"),
        "faster", unit="min", better=-1),
    "idle_min_per_issue": Figure(
        "idle minutes per issue", ("faster", "idle_minutes_per_issue"),
        "faster", unit="min", better=-1),
    "agent_h_per_issue": Figure(
        "agent hours per issue", ("faster", "agent_hours_per_issue"),
        "faster", unit="h", better=-1),
    "estimate_ratio": Figure(
        "estimate median ratio", ("faster", "estimate_median_ratio"),
        "faster", unit="x"),
    "issues_rated": Figure(
        "issues rated", ("faster", "issues_rated"), "faster"),
    # Ruling 6's four counts and their denominator.
    "issues_graded": Figure(
        "issues graded", ("quality", "issues_graded"), "quality"),
    "first_attempt_passes": Figure(
        "first-attempt gate passes", ("quality", "first_attempt_passes"),
        "quality", better=1),
    "correction_rounds": Figure(
        "correction rounds", ("quality", "correction_rounds"), "quality",
        better=-1),
    "strikes": Figure("strikes", ("quality", "strikes"), "quality", better=-1),
    "escalations": Figure(
        "escalations", ("quality", "escalations"), "quality", better=-1),
    # Ruling 14's one threshold.
    "cache_ratio": Figure(
        "cache read-to-write", ("cache", "ratio"), "cache", unit="to 1",
        better=1),
    # Per model, and never one number. Ticket 39 sitting 3.
    "weighted": Figure("weighted tokens", ("weighted",), "weighted",
                       per_model=True, scale="millions"),
    "per_issue": Figure("weighted per issue", ("per_issue",), "per_issue",
                        per_model=True, scale="millions2"),
    "orchestrator": Figure("orchestrator share", ("orchestrator",),
                           "orchestrator", per_model=True, scale="share"),
}


# The five cells the `borrowed` mark has ever named, measured by sitting 2 on
# 2026-09-06. `hours` and `idle` came from the run's own transcript throughout
# and are not in it.
BORROWABLE = ("issues", "subagents", "weighted", "orchestrator", "per_issue")


def comparable(record, name):
    """`(ok, reason)`. A figure drawn from a borrowed field is not comparable.

    The mark names WHICH fields were borrowed, so this is read as a list and
    never as a flag. Reading it as a flag would delete `hours` and `idle` from
    seventeen lines that hold them honestly.
    """
    marked = record.get("borrowed")
    if not marked:
        return True, ""
    if not isinstance(marked, (list, tuple, set, frozenset)):
        # A mark this reader cannot read: a bool from a writer that flattened
        # the list, or a string, which fell through to a SUBSTRING test and
        # half-honoured the mark in silence. Every field the mark has ever
        # named is suspect -- and only those. The mark has ONE historical
        # cause and sitting 2 measured which five cells it covers; widening it
        # to `hours` and `idle` would delete the two figures this history can
        # actually answer, which is what the per-figure skip exists to avoid.
        marked = BORROWABLE
    source = FIGURES[name].source
    if source in marked:
        return False, (
            f"`{record.get('batch')}` is marked **borrowed** on `{source}`: "
            "that cell came from `orchestrator_cost.py --days 7`'s last data "
            "row, whatever run it described, and not from this run.")
    return True, ""


def value_of(record, name):
    """The scalar a figure names, or None. A per-model figure has none."""
    figure = FIGURES[name]
    if figure.per_model:
        return None
    found = record
    for step in figure.path:
        if not isinstance(found, dict):
            return None
        found = found.get(step)
    return found if isinstance(found, (int, float)) else None


def by_model(now, before, name):
    """`{model: (now, before)}` for a per-model figure, paired models only.

    A model only one of the two lines used is left out rather than compared
    against zero: the run did not use it, which is not the same as spending
    nothing on it.
    """
    here = now.get(FIGURES[name].source) or {}
    there = before.get(FIGURES[name].source) or {}
    if not isinstance(here, dict) or not isinstance(there, dict):
        return {}
    return {model: (here[model], there[model])
            for model in sorted(set(here) & set(there))}


# --------------------------------------------------------------------------
# Direction, range, and the ONE threshold.
#
# Ruling 14: one threshold only, on the cache read-to-write ratio. Every other
# figure is direction and range, never an alarm. Ruling 25 fixes the words the
# skill above this may use: figures, directions, and a figure named as outside
# its observed range -- no cause and no advice.
#
# The measured reason for the rule, from `daily-brief/SKILL.md`: consecutive
# rows swung by as much as 75 per cent, so a 25 per cent flag would have fired
# on seven of twelve transitions and taught them to ignore it.
# --------------------------------------------------------------------------

# `cache_probe.py --days 60` over the 26 fleet sessions on this machine on
# 2026-09-06: 25.9 to 78.8, median about 54. The floor sits 23 per cent below
# the lowest of those 26 readings, so it cannot fire on ordinary variance. A
# high ratio is the cheap state -- a cache read costs about a tenth of a write
# in this pipeline's weighting -- so the alarm is a FLOOR, not a ceiling.
CACHE_FLOOR = 20.0

# Measured over all 159 sessions on this machine holding a subagent directory,
# 2026-09-06: every session reading under 3 to 1 wrote under 0.45M, and four
# reading 0.00 wrote 0.07M to 0.14M on two spawns each. The ratio is unstable
# at that volume, so the alarm is silent below it and says why.
CACHE_VOLUME_FLOOR = 500_000

THRESHOLDS = {"cache_ratio": CACHE_FLOOR}

# Two readings are not a range. `daily-brief/SKILL.md` says so in its own words
# and this is the same rule, held by a number.
RANGE_FLOOR = 4


@dataclass(frozen=True)
class Movement:
    direction: str
    change: float
    percent: float = None


def movement(now, before):
    """`Movement`, or None where either side is missing.

    A missing figure is missing. It is never treated as zero: every one of the
    eighteen lines on disk reads null for ruling 6's counts, and reading those
    as zeroes would report eighteen runs that took no strikes.
    """
    if now is None or before is None:
        return None
    change = now - before
    direction = "level" if change == 0 else ("up" if change > 0 else "down")
    percent = (100.0 * change / abs(before)) if before else None
    return Movement(direction, change, percent)


def render_movement(name, found) -> str:
    """One figure moved, in words. No alarm, whatever the size.

    **A share moves in POINTS.** Idle went 0.10 to 0.23 between two real runs;
    rendering that as "up 130%" invites the reader to think idle time more
    than doubled as a share of the run, which is a larger-sounding claim than
    the one the figures support.
    """
    if found is None:
        return "no previous reading"
    if found.direction == "level":
        return "level"
    if FIGURES[name].scale == "share":
        return f"{found.direction} {abs(found.change) * 100:.0f} points"
    if FIGURES[name].scale in ("millions", "millions2"):
        size = (f" ({abs(found.percent):.0f}%)"
                if found.percent is not None else "")
        return f"{found.direction} {abs(found.change) / 1e6:.2f}M{size}"
    size = (f" ({abs(found.percent):.0f}%)"
            if found.percent is not None else "")
    return f"{found.direction} {abs(found.change):.2f}{size}"


def _measured(records, name):
    return [value for record in records
            if comparable(record, name)[0]
            and (value := value_of(record, name)) is not None]


def observed_range(records, name):
    """`(low, high, count)` over lines that are comparable AND measured."""
    seen = _measured(records, name)
    if not seen:
        return (None, None, 0)
    return (min(seen), max(seen), len(seen))


def range_note(records, name, value) -> str:
    """Ruling 25's one judgement, or "".

    Silent under `RANGE_FLOOR` readings, because two or three readings are not
    a range and naming a figure "outside" one would be an alarm wearing a
    range's clothes.
    """
    low, high, count = observed_range(records, name)
    if value is None or count < RANGE_FLOOR:
        return ""
    if low <= value <= high:
        return ""
    return (f"outside the observed range of {low:g} to {high:g} "
            f"over {count} lines")


def cache_alarm(ratio, written=None) -> str:
    """Ruling 14's one alarm, or "". Never raises on a missing reading.

    Silent where the fleet wrote too little for the ratio to mean anything.
    A run that spawned almost nothing would otherwise raise an alarm about its
    cache and mean nothing by it, which is the alarm-nobody-reads shape the
    daily brief's own rule was written against.
    """
    if ratio is None or ratio >= CACHE_FLOOR:
        return ""
    if written is not None and written < CACHE_VOLUME_FLOOR:
        return ""
    return (f"CACHE: the read-to-write ratio is {ratio:.1f} to 1, under the "
            f"floor of {CACHE_FLOOR} to 1. Measured across the 26 run-shaped "
            "sessions on this machine on 2026-09-06 the ratio ran 25.9 to "
            "78.8, so this is a collapse in cache reuse and not variance. "
            "This is the only threshold in this reader (ruling 14).")


def cache_note(ratio, written=None) -> str:
    """The alarm, or the reason there is none. Never silent about a low ratio.

    A ratio under the floor on too small a fleet is still worth a sentence:
    saying nothing at all would look identical to a healthy reading.
    """
    alarm = cache_alarm(ratio, written)
    if alarm:
        return alarm
    if (ratio is not None and ratio < CACHE_FLOOR
            and written is not None and written < CACHE_VOLUME_FLOOR):
        return (f"The cache read-to-write ratio is {ratio:.1f} to 1, under "
                f"ruling 14's floor, but the fleet wrote only "
                f"{written / 1e6:.2f}M -- too little for the ratio to be "
                "read. No alarm is raised.")
    return ""


# --------------------------------------------------------------------------
# Ruling 8's four direction lines, and the escaped-faults figure behind one of
# them. Everything else stays in the view (ruling 13).
# --------------------------------------------------------------------------

NOT_MEASURED = "not measured"

DIRECTION_LINES = ("idle_min_per_issue", "first_attempt_passes",
                   "escaped_faults", "estimate_ratio")


def _origin():
    """`check_origin`, loaded lazily and by path.

    Sitting 1 and sitting 2 both met the same fault: a plain sibling import
    throws wherever this directory is not on `sys.path`, and it broke every
    spawn on the machine once. This module puts `HERE` on the path at import,
    so the import here is safe -- it is lazy only so that a missing
    `check_origin.py` costs one figure rather than every subcommand.
    """
    import importlib
    return importlib.import_module("check_origin")


def escaped_faults(register_text):
    """`(count, graded, why)` — faults traced to the issue and run that shipped.

    Ruling 7 built the `Origin:` key for this figure and sitting 1 landed it.
    `check_origin.graded` is the walk and `check_origin.parse_origin` the
    parser; neither is written again here, because a second reader of one
    table drifts in silence.

    **A row counts only where BOTH halves are named.** Ruling 7's own wording
    is "the issue AND the run that shipped the code", and a row reading
    `unknown/<run>` cannot be traced to an issue, so it is graded and not
    counted. `unknown` is legal by design -- the production watcher genuinely
    knows neither half -- so the rate it is taken at is what keeps this honest,
    and `graded` is printed beside the count for exactly that reason.

    `count` is None where nothing was graded. **That is the whole point of the
    figure today:** measured 2026-09-06, no table in the live register declares
    an `origin` column, so the honest reading is "nothing graded" and never "no
    faults escaped". Ruling 7 says the count starts the day the key lands.
    """
    try:
        origin = _origin()
    except Exception as error:  # noqa: BLE001 - a reading never raises
        return None, 0, f"`check_origin.py` could not be loaded ({error})"

    if not (register_text or "").strip():
        return None, 0, (
            "no register was read, so nothing was graded. This is a statement "
            "about a file that was not opened, never about its contents.")

    rows = list(origin.graded(register_text))
    if not rows:
        return None, 0, (
            "no table in this register declares an `origin` column, so nothing "
            "was graded. Ruling 7 starts the count the day the key lands, and "
            "a table with no such column is history and is skipped (sitting "
            "1). This is a missing measurement, not a clean pipeline.")

    counted = 0
    for _, cell, _number in rows:
        parsed = origin.parse_origin(cell)
        if not parsed:
            continue
        issue, run = parsed
        if issue != origin.UNKNOWN and run != origin.UNKNOWN:
            counted += 1
    return counted, len(rows), ""


def quantity(name, value) -> str:
    """One figure's value in the units the generated view uses for it.

    The single renderer. `_figure_text` and the per-model block both call it,
    because two renderers of one quantity drift -- the lesson `journal_for`
    taught ticket 39 in sitting 2 and `read_transcript` in sitting 3.
    """
    if value is None:
        return NOT_MEASURED
    figure = FIGURES[name]
    if figure.scale == "millions":
        return f"{value / 1e6:.1f}M"
    if figure.scale == "millions2":
        return f"{value / 1e6:.2f}M"
    if figure.scale == "share":
        return f"{value * 100:.0f}%"
    unit = f" {figure.unit}" if figure.unit else ""
    return f"{value:g}{unit}"


def _figure_text(record, name) -> str:
    return quantity(name, value_of(record, name))


def compare_figure(records, now, before, name) -> str:
    """One figure, its movement, and every reason it could not be compared.

    The skips are STATED. Sitting 2's ledger left this sitting one
    instruction -- skip marked lines when reading a trend -- and a skip nobody
    is told about is the `ok` on a table nobody could read that sitting 1 met
    on the live register.
    """
    label = FIGURES[name].label
    here, why_here = comparable(now, name)
    if not here:
        return f"{label}: {_figure_text(now, name)} — skipped. {why_here}"

    value = value_of(now, name)
    text = f"{label}: {_figure_text(now, name)}"
    note = range_note(records, name, value)
    if note:
        text += f" — {note}"

    if before is None:
        return text + " — no previous line of this kind"
    there, why_there = comparable(before, name)
    if not there:
        # The whole reason, never a slice of it. Cutting the sentence on its
        # first colon dropped the word `borrowed` out of a message whose only
        # job is to say that a line was skipped and why.
        return f"{text} — not compared against the previous line. {why_there}"
    if value is None or value_of(before, name) is None:
        if value is None:
            # `text` already reads `not measured`. Saying it twice in one line
            # reads as two findings and is one.
            return f"{text} on this line"
        return f"{text} — {NOT_MEASURED} on `{before.get('batch')}`"
    return (f"{text} — {render_movement(name, movement(value, value_of(before, name)))}"
            f" against `{before.get('batch')}`")


def direction_line(records, now, before, name) -> str:
    """One of ruling 8's four. `escaped_faults` is not a per-run field, so it
    is filled by the caller through `escaped_line`."""
    return compare_figure(records, now, before, name)


def escaped_line(count, graded, why) -> str:
    if count is None:
        return f"escaped faults: {NOT_MEASURED} — {why}"
    return (f"escaped faults: {count} traced to an issue and a run, "
            f"of {graded} register row(s) graded")


# --------------------------------------------------------------------------
# The five subcommands (ruling 24). Fixed, so the script is the fact and
# `/run-compare` above it only reads what this prints.
# --------------------------------------------------------------------------

SUBCOMMANDS = ("last", "show", "since", "compare", "versions")

# What `last`, `show` and `compare` print for the run itself, above ruling 8's
# four direction lines. Ruling 13 keeps everything else in the view.
HEADLINE = ("issues", "hours", "wall_min_per_issue", "agent_h_per_issue",
            "subagents", "idle", "cache_ratio")

PER_MODEL = ("weighted", "per_issue", "orchestrator")


def _find(records, batch):
    for record in records:
        if str(record.get("batch") or "") == batch:
            return record
    return None


def _skipped_note(records) -> str:
    """What the reader could not read, said out loud.

    Sitting 2's ledger left this sitting one instruction and this is it: skip
    marked lines when reading a trend, and say that you skipped them.
    """
    marked = [one for one in records if one.get("borrowed")]
    unmeasured = [one for one in records
                  if (one.get("quality") or {}).get("issues_graded") is None]
    lines = []
    if marked:
        lines.append(
            f"**{len(marked)} of {len(records)} lines are marked `borrowed`.** "
            "Five cells on each -- issues, subagents, weighted, orchestrator, "
            "per issue -- came from another run, so no trend below reads them "
            "on those lines. `hours` and `idle` were always the run's own.")
    if unmeasured:
        lines.append(
            f"**{len(unmeasured)} of {len(records)} lines read `{NOT_MEASURED}` "
            "for ruling 6's four counts.** Sitting 3 of 2026-09-06 repaired "
            "the reader that filled them; a line written before that carries "
            "no count, and a count is never read as a zero.")
    return "\n".join(lines)


def _block(records, now, before, escaped) -> str:
    """One line's block. `escaped` is `escaped_faults(...)` already taken.

    Passed in rather than read here: the figure is one reading of one file and
    cannot differ between blocks, and `since` walked the 4,675-line register
    once per line it rendered.
    """
    text = [f"## `{now.get('batch')}` ({now.get('kind')}), "
            f"taken {now.get('taken')}, Claude Code {now.get('version')}",
            ""]
    for name in HEADLINE:
        text.append("- " + compare_figure(records, now, before, name))

    said = cache_note(value_of(now, "cache_ratio"),
                      (now.get("cache") or {}).get("written")
                      if isinstance(now.get("cache"), dict) else None)
    if said:
        text += ["", said]

    text += ["", "### Per model — never added together", ""]
    for name in PER_MODEL:
        here = now.get(FIGURES[name].source) or {}
        ok, why = comparable(now, name)
        if not ok:
            text.append(f"- {FIGURES[name].label}: skipped. {why}")
            continue
        if not isinstance(here, dict) or not here:
            text.append(f"- {FIGURES[name].label}: {NOT_MEASURED}")
            continue
        paired = by_model(now, before, name) if before is not None else {}
        parts = []
        for model, value in sorted(here.items()):
            said = f"{model} {quantity(name, value)}"
            if model in paired:
                said += (" ("
                         + render_movement(name, movement(*paired[model]))
                         + ")")
            parts.append(said)
        text.append(f"- {FIGURES[name].label}: " + "; ".join(parts))

    text += ["", "### The four directions (ruling 8)", ""]
    for name in DIRECTION_LINES:
        if name == "escaped_faults":
            text.append("- " + escaped_line(*escaped))
            continue
        text.append("- " + direction_line(records, now, before, name))
    return "\n".join(text)


def render_last(records, register_text="") -> str:
    """The newest line of every kind, each against its own predecessor."""
    found = ordered(records)
    if not found:
        return (f"No lines in `{run_records.RUNS}`. The next finale writes the "
                "first one.")
    escaped = escaped_faults(register_text)
    text = ["# The last line of each kind", ""]
    note = _skipped_note(records)
    if note:
        text += [note, ""]
    seen = set()
    for position in range(len(found) - 1, -1, -1):
        record = found[position][1]
        kind = record.get("kind")
        if kind in seen:
            continue
        seen.add(kind)
        text += [_block(records, record, previous_of_kind(found, position),
                        escaped), ""]
    absent = [kind for kind in run_records.KINDS if kind not in seen]
    if absent:
        text.append(
            "No line of kind " + ", ".join(f"`{k}`" for k in absent)
            + f" is on file at all, so nothing is reported for it. A hunt's "
              "cost was never recorded before 2026-09-06, when ruling 11 "
              "reversed `parallel-hunt`'s `--no-append`.")
        text.append("")
    text.append(f"The one-look page is `{run_records.VIEW}` (ruling 13): the "
                "per-run table, the per-issue table and the longest steps by "
                "kind.")
    return "\n".join(text)


def render_show(records, batch, register_text="") -> str:
    found = ordered(records)
    positions = [index for index, (_, one) in enumerate(found)
                 if str(one.get("batch") or "") == batch]
    if not positions:
        return (f"There is no line for `{batch}` in `{run_records.RUNS}`. "
                f"{len(records)} line(s) are on file.")
    position = positions[0]
    text = [_block(records, found[position][1],
                   previous_of_kind(found, position),
                   escaped_faults(register_text))]
    note = _skipped_note(records)
    if note:
        text += ["", note]
    text.append(f"\nThe one-look page is `{run_records.VIEW}` (ruling 13).")
    return "\n".join(text)


def _taken(record):
    """The day a line was taken, or None where the cell cannot be read.

    `taken` is compared as a STRING everywhere in this module, and a value
    that is not a date sorts above every real one: `not stated` was inside
    every window however short, so a run from three weeks ago read as
    yesterday's. Parsing it is the guard.
    """
    import datetime
    try:
        return datetime.date.fromisoformat(str(record.get("taken") or ""))
    except (TypeError, ValueError):
        return None


def _in_window(records, days, today):
    """`(inside, unreadable)`. Never raises, whatever `days` reads.

    `timedelta` raises OverflowError and not ValueError on a large integer,
    and `daily-brief/SKILL.md` runs this mid-section: a mistyped window costs
    the figure, never the brief.
    """
    import datetime
    try:
        edge = datetime.date.fromisoformat(today) - datetime.timedelta(
            days=int(days))
    except (TypeError, ValueError, OverflowError):
        return [], []
    inside, unreadable = [], []
    for index, record in enumerate(records):
        day = _taken(record)
        if day is None:
            unreadable.append(record)
            continue
        if day >= edge:
            inside.append(index)
    return inside, unreadable


def render_since(records, days, today=None, register_text="") -> str:
    """Every line in the window, per kind, with the window said out loud.

    Selection is by the line's POSITION in the file, never by its content.
    `runs.jsonl` is hand-editable by `run_records`' own instruction, so two
    lines can hold identical content, and a value test took or left both
    together.
    """
    import datetime
    today = today or datetime.date.today().isoformat()
    indexes, unreadable = _in_window(records, days, today)
    inside = {index for index in indexes}
    text = [f"# The last {days} day(s), to {today}", ""]
    if unreadable:
        text += ["**" + ", ".join(f"`{one.get('batch')}`" for one in unreadable)
                 + f"** carr{'y' if len(unreadable) > 1 else 'ies'} a `taken` "
                 "cell that is not a date, so no window can hold "
                 f"{'them' if len(unreadable) > 1 else 'it'}. Read "
                 f"{'those lines' if len(unreadable) > 1 else 'that line'} by "
                 "hand.", ""]
    if not inside:
        newest = max((str(one.get("taken") or "") for one in records),
                     default="(none)")
        text.append(
            f"There is no line taken in that window. {len(records)} line(s) "
            f"are on file, the newest {newest}.")
        return "\n".join(text)
    picked = [one for index, one in enumerate(records) if index in inside]
    note = _skipped_note(picked)
    if note:
        text += [note, ""]
    escaped = escaped_faults(register_text)
    found = ordered(records)
    for position, (index, record) in enumerate(found):
        if index not in inside:
            continue
        text += [_block(records, record, previous_of_kind(found, position),
                        escaped=escaped), ""]
    text.append(f"The one-look page is `{run_records.VIEW}` (ruling 13).")
    return "\n".join(text)


def render_compare(records, first, second, register_text="") -> str:
    """Two lines named by hand — the one road that could walk around ruling 12.

    So it refuses two kinds. A run against a hunt is not a comparison, and the
    whole reason `parallel-hunt` carried `--no-append` was that a hunt row
    among run rows reads as a run.
    """
    here, there = _find(records, first), _find(records, second)
    missing = [name for name, one in ((first, here), (second, there))
               if one is None]
    if missing:
        return (f"REFUSED: there is no line for {', '.join(f'`{m}`' for m in missing)} "
                f"in `{run_records.RUNS}`.")
    if here.get("kind") != there.get("kind"):
        return (f"REFUSED: `{first}` is a {here.get('kind')} and `{second}` is "
                f"a {there.get('kind')}. Ruling 12 compares a line against the "
                "previous line of the SAME KIND, and naming two by hand is the "
                "one road that could walk around it.")
    # The SAME tie-break `ordered()` uses, and for the same reason. Sorting on
    # `taken` alone let two lines taken on one day be ordered by which was
    # NAMED first, so the pair had two opposite answers and nothing said which
    # was backwards.
    rank = {id(one): position for position, (_, one) in enumerate(ordered(records))}
    older, newer = sorted((here, there),
                          key=lambda one: rank.get(id(one), 0))
    text = [f"# `{newer.get('batch')}` against `{older.get('batch')}`", ""]
    note = _skipped_note([older, newer])
    if note:
        text += [note, ""]
    text.append(_block(records, newer, older,
                       escaped_faults(register_text)))
    return "\n".join(text)


@dataclass
class Group:
    key: tuple
    records: list


def _key(record):
    found = record.get("fingerprint") or {}
    if not isinstance(found, dict) or not found:
        return ()
    return tuple(sorted(
        (name, str((mark or {}).get("head") or ""),
         bool((mark or {}).get("dirty")))
        for name, mark in found.items() if isinstance(mark, dict)))


def fingerprint_groups(records):
    """Consecutive lines that ran the same three commits, in finale order.

    Consecutive rather than gathered: a pipeline that changed and changed back
    is two spells of the same commits, and calling them one group would put a
    later run before an earlier one.
    """
    groups = []
    for _, record in ordered(records):
        key = _key(record)
        if groups and groups[-1].key == key:
            groups[-1].records.append(record)
            continue
        groups.append(Group(key, [record]))
    return groups


def git_log(name, first, second):
    """The commit subjects between two heads of one repository, or []."""
    import subprocess
    import pipeline_fingerprint
    root = pipeline_fingerprint.REPOS.get(name)
    if root is None:
        return []
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "log", "--oneline", "--no-decorate",
             f"{first}..{second}"],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    return [row for row in done.stdout.splitlines() if row.strip()]


def render_versions(records, log=git_log) -> str:
    """Ruling 24's fifth: lines grouped by fingerprint, and what changed."""
    groups = fingerprint_groups(records)
    text = ["# What ran each line, grouped by pipeline", ""]
    if all(not group.key for group in groups):
        text.append(
            f"Every line reads `{NOT_MEASURED}` for its pipeline fingerprint. "
            "Ruling 23's header landed in sitting 2 of 2026-09-06 and is "
            "written by the LAUNCH, so a run that started before it carries "
            "none. The next run to launch writes the first one. Grouping "
            f"{len(records)} lines into one group here would say they all ran "
            "the same pipeline, which nothing measured.")
        return "\n".join(text)

    for index, group in enumerate(groups):
        batches = ", ".join(f"`{one.get('batch')}`" for one in group.records)
        if not group.key:
            text.append(f"- **no fingerprint** ({NOT_MEASURED}): {batches}")
            continue
        marks = ", ".join(f"{name} `{head}`" + (" dirty" if dirty else "")
                          for name, head, dirty in group.key)
        text.append(f"- **{marks}**: {batches}")
        if index == 0 or log is None:
            continue
        before = dict((name, head) for name, head, _ in groups[index - 1].key)
        for name, head, _dirty in group.key:
            first = before.get(name)
            if not first or first == head:
                continue
            subjects = log(name, first, head)
            if not subjects:
                continue
            text.append(f"  - {name} `{first}` to `{head}`:")
            text += [f"    - {one}" for one in subjects]
    return "\n".join(text)


def main(argv=None) -> int:
    """The five subcommands. Reads; never writes, never raises.

    `finale.md` and `daily-brief/SKILL.md` both run this, and a reader that
    threw in the middle of a brief would cost the brief rather than the figure.
    """
    import argparse

    # `--repo` sits on the top level AND on every subcommand, because both
    # forms get typed. **The default on the subparser must be SUPPRESS.** With
    # an empty default the subparser writes its own value over the top-level
    # one, so `--repo X last` silently read the working directory instead of
    # X -- the reader answering about a repository nobody asked about, which
    # is the borrowed-figure fault this whole ticket exists to end. Found by
    # the `/code-review` pass of 2026-09-06 and measured.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=argparse.SUPPRESS,
                        help="the repository holding .scratch/workflow-audit; "
                             "the working directory by default")

    parser = argparse.ArgumentParser(
        parents=[common],
        description=("Read the pipeline's own records across runs (ticket 37, "
                     "ruling 24). It reads; it never writes."))
    sub = parser.add_subparsers(dest="what")
    sub.add_parser("last", parents=[common],
                   help="the newest line of each kind")
    one = sub.add_parser("show", parents=[common],
                         help="one line by batch id")
    one.add_argument("batch")
    window = sub.add_parser("since", parents=[common],
                            help="every line in a window of days")
    window.add_argument("days", type=int)
    pair = sub.add_parser("compare", parents=[common],
                          help="two lines of one kind")
    pair.add_argument("first")
    pair.add_argument("second")
    sub.add_parser("versions", parents=[common],
                   help="lines grouped by pipeline fingerprint")

    args = parser.parse_args(argv)
    if not args.what:
        parser.print_help()
        return 2

    # `getattr`, because both `--repo` options default to SUPPRESS and so
    # leave the attribute absent when neither is typed. A `set_defaults` here
    # instead re-applied the empty default OVER a value the top-level flag had
    # already set, which is the fault this line was written to fix.
    named = getattr(args, "repo", "")
    repo = pathlib.Path(named) if named else pathlib.Path.cwd()
    seen = run_records.read_runs(repo)
    # `.scratch/*/register.md`, the way `find_live_ledger.py` finds a ledger:
    # the feature directory is named per project and no reader may assume one.
    # Where a repo holds no register, or more than one and none is chosen, the
    # escaped-fault reading is simply absent and every other figure still prints.
    found = sorted(repo.glob(".scratch/*/register.md"))
    text = ""
    if len(found) == 1:
        try:
            text = found[0].read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""

    if args.what == "last":
        print(render_last(seen.records, text))
    elif args.what == "show":
        print(render_show(seen.records, args.batch, text))
    elif args.what == "since":
        print(render_since(seen.records, args.days, register_text=text))
    elif args.what == "compare":
        print(render_compare(seen.records, args.first, args.second, text))
    else:
        print(render_versions(seen.records))

    if seen.damaged:
        print(f"\n{len(seen.damaged)} line(s) of {run_records.RUNS} could not "
              "be parsed and are NOT in anything above. Read them by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
