#!/usr/bin/env python3
"""The pipeline's own records: one line per run, one line per issue attempt.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 2. Rulings 2, 3, 4, 6, 9, 10, 11, 15, 17 and 23.

## Why a table became a file plus a view

`.scratch/workflow-audit/run-costs.md` held 18 rows and could not be parsed.
Not "was awkward to parse" -- could not be. A correction paragraph about the
2026-08-31 row sits BETWEEN two data rows, so the file is prose with a table in
it. Every quality fact lived in a free-text `Note` cell, so no figure could be
read down a column. Ruling 2 splits the two jobs: `runs.jsonl` is the record and
is machine-readable, and `run-costs.md` is a VIEW generated from it, which keeps
the name so that every citation written since 2026-08-18 stays true.

## Why a duplicate is refused rather than reported

Run `review-375cbf` appended two rows for itself on 2026-09-01 (ticket 36,
fault 9). They differ: 16.16 h against 16.2 h, 118.9M against 119.8M weighted.
Nothing noticed, and the run's own merge briefing carried the number. The table
says in its header to compare a row against the row above it, so the second row
made the run its own predecessor and reported a 0.8 per cent change that was
really the same run measured twice. `append_run` refuses a second line for a
batch id already present. The 18 rows are carried over by `migrate_view.py` and
the duplicate is deleted ONCE by hand, with the reason in the generated
header (ruling 3).

## The inside-run counts: declared in sitting 2, filled in sitting 3

Ruling 6 puts four counts on the per-run line -- first-attempt gate passes,
correction rounds, strikes and escalations -- with the count of issues graded
beside them, so the view can show a rate.

**Sitting 2 declared all five and wrote each an explicit `None`, and refused
every figure offered for them.** Its reason was ruling 28: three of the four
are read by `run_quality.issue_quality`, and that reader graded 12 rows for the
six-issue run `batch-170a59`, because `check_commit_order.status_rows` accepted
any table row on a ledger page whose first cell held an issue id and that
ledger carries a carry-forward table of test counts at `run.md:35-43` whose
rows read `149c (-13, -3)`. The totals were right and the DENOMINATOR was
wrong, so every rate would have been wrong. The human chose branch A: declare the
schema once, write nulls, and let one reader fill all five at one moment.

**Sitting 3 (2026-09-06) is that moment.** `status_rows` is bounded to the
table whose header declares `issue`; the corpus reads 149 rows across
seventeen ledgers where it read 155, and `batch-170a59` reads its own six.
Escalations, which were "not read anywhere at all", are counted off the
transcript by role name. So the blanket refusal is gone and
`normalise_quality` holds four narrower ones in its place.

**A key present and null still means this writer knew the field and had
nothing true to put in it.** An omitted key is indistinguishable from a schema
written before the field existed, and these files are append-only, so that
difference would be permanent. A `0` now means something different and real:
a run with no strikes is a fact, and it must be recordable as one.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from dataclasses import dataclass, field

WORKFLOW_AUDIT = ".scratch/workflow-audit"
RUNS = f"{WORKFLOW_AUDIT}/runs.jsonl"
ISSUES = f"{WORKFLOW_AUDIT}/issues.jsonl"
VIEW = f"{WORKFLOW_AUDIT}/run-costs.md"

# Ruling 15. Measured reason for the number: the note cell of the 2026-09-05
# row runs to 559 characters and carries five separate facts, so nothing can be
# read from it and nobody scans a column that wide. 160 holds one fact.
NOTE_LIMIT = 160

# Ruling 11. A third spelling would silently drop a line out of both trends,
# because ruling 12 compares a line against the previous line OF THE SAME KIND.
KINDS = ("run", "hunt")

# Ruling 10. The cell holds the Claude Code version and nothing else. The live
# table carries `claude-opus-5` in one version cell, typed by an agent that
# `finale.md` asks for `--version <cc-version>`.
NOT_STATED = "not stated"
VERSION = re.compile(r"^\d+(?:\.\d+)*$")
CLAUDE_CODE_SUFFIX = re.compile(r"\s*\(Claude Code\)\s*$")

# Ruling 6's four counts, and the denominator that lets the view show a rate
# beside each. All five are written `None` by this sitting -- see the module
# docstring, and ruling 28.
QUALITY_FIELDS = ("issues_graded", "first_attempt_passes", "correction_rounds",
                  "strikes", "escalations")

# The denominator ruling 6 puts beside the counts, so the view can show a rate.
DENOMINATOR = "issues_graded"

# The counts that are one per issue at most, so none of them can exceed the
# denominator. Correction rounds and strikes are NOT here: an issue can take
# several of either, and `batch-b5e96d` did.
PER_ISSUE_COUNTS = ("first_attempt_passes", "escalations")


@dataclass
class Read:
    """Every record that parsed, and every line that did not.

    Both halves are returned because a caller that sees only the records cannot
    tell a short history from a damaged one, and `run_quality.py`'s "an
    unreadable journal was reported as a journal holding no lines" was that
    same fault caught in review on 2026-09-06.
    """

    records: list = field(default_factory=list)
    damaged: list = field(default_factory=list)


def read_lines(path: pathlib.Path) -> Read:
    """Every JSON object in a `.jsonl` file, and every line that is not one."""
    seen = Read()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return seen
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            found = json.loads(line)
        except ValueError:
            seen.damaged.append((number, line))
            continue
        if not isinstance(found, dict):
            seen.damaged.append((number, line))
            continue
        seen.records.append(found)
    return seen


def read_runs(repo) -> Read:
    return read_lines(pathlib.Path(repo) / RUNS)


def read_issues(repo) -> Read:
    return read_lines(pathlib.Path(repo) / ISSUES)


def append_run(repo, record):
    """`(ok, message)`. One line per run, refused twice for the same batch."""
    root = pathlib.Path(repo)
    record, why = validate_run(record)
    if why:
        return False, why
    batch = str(record.get("batch") or "").strip()

    seen = read_runs(root)
    if any(str(one.get("batch") or "") == batch for one in seen.records):
        return False, (
            f"REFUSED: `{RUNS}` already holds a line for batch `{batch}`, and "
            "one run gets one line.\n"
            "This is ticket 36's fault 9: run `review-375cbf` appended two "
            "rows for itself on 2026-09-01, four minutes and 0.9M weighted "
            "tokens apart, and the table's own rule is to compare a row "
            "against the row above it -- so the run became its own "
            "predecessor.\n"
            f"If the first line is wrong, edit `{RUNS}` by hand and say why in "
            "the commit message. Do NOT append a second one.")

    return _append(root / RUNS, record)


def validate_run(record):
    """`(record, refusal)` — every rule a per-run line must pass, and no I/O.

    **Split out of `append_run` by ticket 37 sitting 5.** Ruling 16's replay
    REWRITES seven lines in place rather than appending beside them, because
    this file is append-only and `append_run` refuses a second line for a
    batch already present. A replay that wrote round these rules could put
    into the record exactly what a finale is stopped from putting in, so both
    roads pass through here and there is one set of rules rather than two.

    The duplicate refusal stays in `append_run` alone: it is a fact about the
    file, not about the record, and rewriting a line whose batch is already
    present is the replay's whole purpose.
    """
    batch = str(record.get("batch") or "").strip()
    if not batch:
        return None, ("REFUSED: the record names no batch id. The batch id is "
                       f"the key of `{RUNS}`; a line without one can never be "
                       "found, compared or de-duplicated.")

    kind = str(record.get("kind") or "").strip()
    if kind not in KINDS:
        return None, (
            f"REFUSED: `kind` reads `{kind or '(absent)'}`, and the only two "
            f"values are {' and '.join(KINDS)} (ruling 11). Ruling 12 compares "
            "a line against the previous line of the SAME KIND, so a third "
            "spelling removes this line from both trends and reports nothing.")

    version, why = normalise_version(record.get("version"))
    if why:
        return None, why
    record = dict(record, version=version)

    # Ruling 3 against ruling 15, settled for the one-time migration only. Six
    # of the 18 rows carried on 2026-09-06 hold notes over the cap -- the
    # longest 538 characters -- and truncating them would have lost 1,293
    # characters of history that nothing else holds. A row written by a finale
    # carries no `carried` flag, so this road is closed to it.
    note = str(record.get("note") or "")
    if record.get("carried"):
        note = ""
    if len(note) > NOTE_LIMIT:
        return None, (
            f"REFUSED: the note is {len(note)} characters and the limit is "
            f"{NOTE_LIMIT} (ruling 15). The note cell is \"what changed since "
            "the last line\", one fact. Everything else belongs in the merge "
            "briefing, which has no limit and which the view links to.")

    quality, why = normalise_quality(record.get("quality"))
    if why:
        return None, why
    record = dict(record, quality=quality)
    return record, ""


def normalise_quality(offered) -> tuple:
    """`(quality, refusal)` for ruling 6's four counts and their denominator.

    **Sitting 2 refused every figure here and sitting 3 is the change that
    lifts it.** That refusal was ruling 28's: `run_quality.issue_quality`
    returned 12 rows for the six-issue run `batch-170a59`, because
    `check_commit_order.status_rows` accepted any table row on the page whose
    first cell held an issue id and that ledger carries a carry-forward table
    of test counts. The totals were right and the DENOMINATOR was wrong, so
    every rate ruling 6 asks for was wrong. The reader is now bounded to the
    status table, so the figures are true and the blanket refusal is gone.

    Four narrower ones replace it, and each refuses a shape rather than a
    value:

      * the five names are the schema, so a sixth writes into a column no view
        renders and no reader compares;
      * a count is a non-negative whole number or null;
      * **a count may not be written without `issues_graded` beside it.**
        Ruling 6's own wording is "with the issue count beside them", because
        the view shows a rate beside each -- and a rate over a denominator
        nobody read is exactly the fault ruling 28 was raised about;
      * a per-issue count may not exceed that denominator. Ruling 28's own
        fault would have failed this one: twelve rows graded against six real
        issues.

    A key present and null still means this writer knew the field and had
    nothing true to put in it. A zero now means something different and real:
    a run with no strikes is a fact, and it must be recordable as one.

    Refuses, never raises. Everything on this road answers `(value, reason)`,
    because a measurement that could halt a finale would cost a run the thing
    the measurement is about.
    """
    blank = {name: None for name in QUALITY_FIELDS}
    if offered is None:
        return blank, ""
    if not isinstance(offered, dict):
        return None, (f"REFUSED: `quality` is a {type(offered).__name__} and "
                      "must be a mapping of the five count names to their "
                      "values, or to null where nothing measured one.")

    unknown = sorted(set(offered) - set(QUALITY_FIELDS))
    if unknown:
        return None, (
            f"REFUSED: `quality` names {', '.join(unknown)}, which is not one "
            f"of the five (ruling 6): {', '.join(QUALITY_FIELDS)}. A figure "
            "under a sixth name is written into a column no view renders and "
            "no reader compares.")

    found = dict(blank)
    for name, value in offered.items():
        if value is None:
            continue
        # `bool` is an `int` in Python and `True` would store as 1, which is a
        # count nobody measured wearing the shape of one somebody did.
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None, (
                f"REFUSED: `quality.{name}` reads `{value!r}`. A count is a "
                "non-negative whole number, or null where nothing measured it.")
        found[name] = value

    counts = [name for name in QUALITY_FIELDS
              if name != DENOMINATOR and found[name] is not None]
    if counts and found[DENOMINATOR] is None:
        return None, (
            f"REFUSED: `quality` carries {', '.join(counts)} and no "
            f"`{DENOMINATOR}`. Ruling 6 puts the counts on the line \"with the "
            "issue count beside them\", because the view shows a RATE beside "
            "each one. A rate over a denominator nobody read is the fault "
            "ruling 28 of 2026-09-06 was raised about.")

    graded = found[DENOMINATOR]
    if graded is not None:
        for name in PER_ISSUE_COUNTS:
            if found[name] is not None and found[name] > graded:
                return None, (
                    f"REFUSED: `quality.{name}` is {found[name]} and "
                    f"`{DENOMINATOR}` is {graded}. {name} is counted one per "
                    "issue, so it can never exceed the issues graded, and the "
                    "cheapest reading of that is that the two figures did not "
                    "come from the same pass over the ledger.")
    return found, ""


def append_issues(repo, rows) -> tuple:
    """`(ok, message)`. One line per issue, ruling 17's second file.

    **The whole run at once, or none of it.** These rows are written at one
    moment by one reader, and a half-written run is a run whose per-issue
    population is smaller than its own `issues_graded` with nothing to say
    which rows were lost.

    A second write for a batch already present is refused for ruling 4's
    reason, carried onto this file: run `review-375cbf` wrote itself twice into
    the per-run table on 2026-09-01, four minutes apart, and nothing noticed.
    A run written twice here would double every per-issue population a trend
    reads.

    No rows is not an error. A hunt shares these files (ruling 11) and has no
    issues at all, so refusing here would print a fault at every round end.
    """
    root = pathlib.Path(repo)
    rows = list(rows or ())
    if not rows:
        return True, f"no issue lines to append to {ISSUES}"

    batch, why = validate_issues(rows)
    if why:
        return False, why

    seen = read_issues(root)
    if any(str(one.get("batch") or "") == batch for one in seen.records):
        return False, (
            f"REFUSED: `{ISSUES}` already holds line(s) for batch `{batch}`, "
            "and one run writes its issues once.\n"
            "This is ruling 4's reason carried onto the per-issue file. Run "
            "`review-375cbf` appended two per-run rows for itself on "
            "2026-09-01 and nothing noticed; a run written twice here would "
            "double every per-issue population a trend reads.\n"
            f"If the first write is wrong, edit `{ISSUES}` by hand and say why "
            "in the commit message. Do NOT append a second set.")

    path = root / ISSUES
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # One open, one write. Two appends interleaving mid-run is what ticket
        # 38's concurrent runs make possible, and a run's rows are read as a
        # population, so a set split across another run's is still readable but
        # a set split MID-LINE is not.
        with path.open("a", encoding="utf-8") as handle:
            handle.write("".join(json.dumps(one, sort_keys=True) + "\n"
                                 for one in rows))
    except OSError as error:
        return False, f"the issue lines were NOT appended: {error}"
    return True, f"appended {len(rows)} issue line(s) to {path.name}"


def validate_issues(rows):
    """`(batch, refusal)` — every rule a set of per-issue lines must pass.

    Split out of `append_issues` by ticket 37 sitting 5, for the reason
    `validate_run` was: ruling 16's replay renders this file whole rather than
    appending to it, so that it can be run twice, and a second set of rules
    would drift from these.
    """
    rows = list(rows or ())
    if not rows:
        # `set.pop()` below raises on an empty set. Both of today's callers
        # guard first; a third would have crashed rather than been refused,
        # on a road whose contract is that a measurement never halts.
        return "", ("REFUSED: no rows were offered, so there is no batch to "
                    "write them under.")
    batches = {str(one.get("batch") or "").strip() for one in rows}
    if len(batches) > 1:
        return "", (
            "REFUSED: these rows name more than one batch "
            f"({', '.join(sorted(b or '(absent)' for b in batches))}). One "
            "call writes one run; a caller holding two has lost track of "
            "which run it is measuring.")
    batch = batches.pop()
    if not batch:
        return "", (f"REFUSED: the rows name no batch id. It is the key of "
                    f"`{ISSUES}`, and a line without one can never be "
                    "found or joined to its run.")
    missing = [index for index, one in enumerate(rows, start=1)
               if not str(one.get("issue") or "").strip()]
    if missing:
        return "", (
            f"REFUSED: row(s) {', '.join(map(str, missing))} of {len(rows)} "
            "name no issue, and nothing was written. Together with the batch "
            "id the issue is this file's key; a row without one cannot be "
            "read back against the ledger it came from.")
    return batch, ""


def _append(path: pathlib.Path, record) -> tuple:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError as error:
        return False, f"the line was NOT appended: {error}"
    return True, f"appended to {path.name}"


def normalise_version(offered):
    """`(value, refusal)` for the version cell. Ruling 10.

    `not stated` survives because the eleven backfilled rows carry it and
    ruling 3 keeps every one of them.
    """
    value = CLAUDE_CODE_SUFFIX.sub("", str(offered or "").strip())
    if not value or value == NOT_STATED:
        return NOT_STATED, ""
    if not VERSION.match(value):
        return "", (
            f"REFUSED: the version cell reads `{value}`, which is not a Claude "
            "Code version (ruling 10). The live table already carries "
            "`claude-opus-5` in this cell, typed by an agent that `finale.md` "
            "asks for `--version <cc-version>`. The model belongs in the two "
            "model cells (ruling 9); this cell holds `2.1.261` and nothing "
            "else. Measure it with `claude --version`.")
    return value, ""


# --------------------------------------------------------------------------
# The generated view. Ruling 2 keeps the name `run-costs.md` so that every
# citation written since 2026-08-18 stays true; ruling 13 makes it the
# one-look page. Nothing is typed into it and a hook refuses the write.
# --------------------------------------------------------------------------

NOT_MEASURED = "not measured"

VIEW_HEADER = """# What each run cost itself

**This file is GENERATED from `{runs}`. Do not edit it by hand.**
A row typed here is gone the next time a finale regenerates the page, and
nothing reports the loss. `generated-file-guard.py` in the hooks refuses the
write and names this line. To correct a figure, edit the JSON line in
`{runs}` and say why in the commit message; to add one, let `run_costs.py`
append it at the finale.

One line per run and per hunt, keyed by batch id. `run_costs.py` refuses a
second line for a batch id already present (ticket 37, ruling 4), which is
ticket 36's fault 9: run `review-375cbf` appended two rows for itself on
2026-09-01, four minutes and 0.9M weighted tokens apart, and nothing noticed.

**Compare a line against the previous line OF THE SAME KIND** (ruling 12),
never the row physically above it. Ticket 38 puts two runs and a hunt in
flight at once, so the row above is no longer the run before.

The issue mix is NOT controlled here, so a difference of a few per cent is the
batch, not the change. A line whose fingerprint is marked `dirty` ran from a
tree holding uncommitted files, so the commit it names is not exactly what ran.

## What was deleted by hand, once

The duplicate `review-375cbf` line of 2026-09-01 was deleted once, by hand, on
2026-09-06, when the markdown table was carried into `{runs}`. The source
table held 19 data rows; one of them was that duplicate, so {total} lines are here. It is in git history. Every other row is kept (ruling 3).

The eleven rows taken on 2026-08-30 are marked `backfilled`: they were read
from `orchestrator_cost.py` after the fact and carry no `Hours` and no `Idle`
figure, because those need each run's own transcript. {synthetic} lines carry
a key beginning `backfilled-`, minted here because the row named no batch id —
that is one more than the backfilled count, because the 2026-08-30 row is a
real finale row written before `run_costs.py` put the id in the note.

## Rows whose figures are not their own

**{borrowed} of the {total} lines below are marked `borrowed`.** Until skills
commit `aa94b3b` (2026-09-06), `run_costs.py` scraped `Issues`, `Subagents`,
`Weighted`, `Orchestrator` and `Per issue` out of `orchestrator_cost.py
--days 7`'s LAST data row, whatever run it described. `Hours` and `Idle` were
the run's own throughout.

The mark is a measurement, not a date: divide `Weighted` by `Per issue` and
see whether it lands on the line's own `Issues`. **There is no per-issue
baseline in this table yet.** Do not quote a range from a marked line, and do
not compare an unmarked line against one.

## The inside-run counts, and which lines carry them

**{measured} of the {total} lines below carry ruling 6's four counts.** Sitting
3 of 2026-09-06 repaired the reader that made them wrong: `status_rows` had
accepted any table row on a ledger page whose first cell held an issue id, so
run `batch-170a59` graded 12 rows for six issues -- the totals right, the
denominator doubled, and every rate wrong. It is now bounded to the table whose
header declares `issue`.

A count reads `not measured` where nothing read it, and a `0` means a run that
genuinely had none. The rate beside each is over `Issues graded`, never over
the run's own issue count, because a row the reader could not grade is not a
row that passed.

**A strike is DERIVED**, from rounds rejected since the last criteria reset,
because two roads in `SKILL.md` cancel one in prose and write no marker. A line
whose own rows disagree with the count is marked in the per-issue table.
"""


# Ruling 18: "the view buckets it (small under 60, medium 60 to 120, large over
# 120). The rule lives in the view." So the RECORD keeps the midpoint in
# minutes alone, and moving a boundary re-reads every line already written
# rather than stranding the ones written under the old rule.
SMALL = 60
MEDIUM = 120


def size_bucket(minutes):
    """An estimate midpoint as ruling 18's size class."""
    if minutes is None:
        return NOT_MEASURED
    if minutes < SMALL:
        return "small"
    return "medium" if minutes <= MEDIUM else "large"


def _cell(value, absent=NOT_MEASURED) -> str:
    """One table cell, safe to put between two pipes.

    A note is free text written by an agent at a finale. One `|` in it would
    silently add a column to that row and shift every cell after it, and one
    newline would split the row in two -- and both would look like a rendering
    bug rather than a bad cell.
    """
    if value is None or value == "":
        return absent
    text = str(value).replace("|", "\\|")
    return " ".join(text.split())


def _models(record) -> str:
    found = record.get("weighted") or {}
    if not isinstance(found, dict) or not found:
        return NOT_MEASURED
    return " / ".join(f"{model} {value / 1e6:.1f}M"
                      for model, value in sorted(found.items(),
                                                 key=lambda kv: -kv[1]))


def _per_issue(record) -> str:
    found = record.get("per_issue") or {}
    if not isinstance(found, dict) or not found:
        return NOT_MEASURED
    return " / ".join(f"{model} {value / 1e6:.2f}M"
                      for model, value in sorted(found.items(),
                                                 key=lambda kv: -kv[1]))


def _share(record) -> str:
    found = record.get("orchestrator") or {}
    if not isinstance(found, dict) or not found:
        return NOT_MEASURED
    return " / ".join(f"{model} {value * 100:.0f}%"
                      for model, value in sorted(found.items(),
                                                 key=lambda kv: -kv[1]))


def _trial(record) -> str:
    """Ruling 22's mark, from ticket 39 sitting 4, in one cell.

    It sits beside the two model cells because the three answer one question:
    what ran this line, and may that answer be trusted. A VOID line ran
    something other than what its map asked for, so it is not a trial of that
    map whatever else it measured.

    **`holds` carries what it proved, and that is not decoration.** Ticket 39
    sitting 4 found five parentheticals the landed check writes that compared
    nothing at all, and every one of them was reported as `holds` until its
    reviews. `holds 3/88` and `holds 88/88` are different claims.
    """
    found = record.get("trial")
    if not isinstance(found, dict) or not found.get("state"):
        return NOT_MEASURED
    state = str(found.get("state"))
    spawns = found.get("spawns") or 0
    if state == "void":
        return f"**void** ({found.get('mismatches') or 0} mismatch)"
    if state == "holds":
        return f"holds {found.get('proved') or 0}/{spawns}"
    # `unmeasured`: the journal held no landed line, or not one of them
    # compared anything. Never drawn as a pass.
    return NOT_MEASURED


def _fingerprint(record) -> str:
    found = record.get("fingerprint") or {}
    if not isinstance(found, dict) or not found:
        return NOT_MEASURED
    parts = []
    for name in ("skills", "agents", "hooks"):
        mark = found.get(name)
        if not isinstance(mark, dict):
            continue
        head = str(mark.get("head") or "")[:7]
        parts.append(f"{name} {head}" + (" dirty" if mark.get("dirty") else ""))
    return ", ".join(parts) or NOT_MEASURED


def _percent(value) -> str:
    if value is None:
        return NOT_MEASURED
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return NOT_MEASURED


COST_COLUMNS = ("Batch", "Kind", "Taken", "Version", "Issues", "Hours",
                "Weighted", "Per issue", "Subagents", "Orchestrator", "Idle",
                "Note")

QUALITY_COLUMNS = ("Batch", "Orchestrator model", "Worker map", "Pipeline",
                   "Trial", "Issues graded", "First-attempt passes",
                   "Correction rounds", "Strikes", "Escalations")

# Ruling 5's five, RECORDED rather than left to be divided. The human's aim, in their
# own framing: one look tells them where to optimise, with no mental arithmetic.
# A reader who had to divide `Hours` by `Issues` to get the first of these
# would not have that.
FASTER_COLUMNS = ("Batch", "Wall min/issue", "Idle min/issue",
                  "Agent h/issue", "Estimate ratio", "Issues rated")

# Ruling 20's five kind facts sit in the last five columns, so a reader
# scanning for "did a migration slow this issue down" reads one block.
ISSUE_COLUMNS = ("Batch", "Issue", "Est min", "Size", "Span min", "Agent min",
                 "Ratio", "Attempts", "Verify", "Review", "Corrections",
                 "Strikes", "Stage", "Critical", "Migration", "Default")

# `run_step.py` and the transcript. The column says which, because the two are
# taken by different instruments and a reader comparing them must see that.
STEP_COLUMNS = ("Batch", "Kind", "Longest", "Measured by", "Which step")


def _rate(count, graded) -> str:
    """`5 (83%)` — ruling 6 asks the view to show the rate beside each count.

    Over `issues_graded` and never over the run's own issue count: a row the
    reader could not grade is not a row that passed, and dividing by the larger
    number is the shape of the fault ruling 28 repaired.
    """
    if count is None:
        return NOT_MEASURED
    if not graded:
        # A count with no denominator cannot reach here through `append_run`,
        # which refuses it, but the view renders history too and ruling 3 keeps
        # every row whatever shape it was written in.
        return str(count)
    return f"{count} ({round(100 * count / graded):.0f}%)"


def _minutes(value) -> str:
    return NOT_MEASURED if value is None else f"{float(value):.0f}"


def _ratio(value) -> str:
    return NOT_MEASURED if value is None else f"{float(value):.2f}x"


def _flag(value) -> str:
    """A tri-state cell. `null` is not `no`: one says nothing looked and the
    other says something looked and found none."""
    if value is None:
        return NOT_MEASURED
    return "yes" if value else "no"


def _table(columns, rows) -> str:
    head = "| " + " | ".join(columns) + " |"
    rule = "|" + "|".join(["---"] * len(columns)) + "|"
    return "\n".join([head, rule] + ["| " + " | ".join(row) + " |" for row in rows])


def render_view(records, issues=None) -> str:
    """The whole page. Pure: it reads nothing and writes nothing.

    Ruling 13 makes this the one-look page: the per-run table, the per-issue
    table, and the longest steps by kind. `issues` is `issues.jsonl`; a page
    rendered without it says so rather than printing an empty table, which is
    a claim that there are no issue lines rather than that none were passed.
    """
    # Counted, never typed. Every number in the header is a fact about the
    # records below it, so it cannot go stale the way the table's own "18
    # rows" did within a day of being written.
    text = [VIEW_HEADER.format(
        runs=RUNS,
        total=len(records),
        borrowed=sum(1 for one in records if one.get("borrowed")),
        synthetic=sum(1 for one in records if one.get("batch_synthetic")),
        measured=sum(1 for one in records
                     if (one.get("quality") or {}).get(DENOMINATOR) is not None),
    )]

    if not records:
        text.append(
            "\nNo lines yet. The next finale writes the first one.\n")
        return "\n".join(text)

    cost, quality = [], []
    for record in records:
        note = _cell(record.get("note"), absent="—")
        if record.get("borrowed"):
            # Ruling 3 keeps the row; this mark is what keeps it honest. The
            # five column names are NOT repeated per row: they are the same
            # five on every marked line, because they have one historical
            # cause, and repeating them cost 60 characters on 17 of 18 lines
            # in a column a person is meant to scan. The header names them
            # once, and the JSON line carries the list for a machine.
            note = "**borrowed.** " + (note if note != "—" else "")
        if record.get("backfilled"):
            note = f"backfilled. {note}" if note != "—" else "backfilled"
        cost.append((
            f"`{_cell(record.get('batch'), absent='?')}`",
            _cell(record.get("kind"), absent="?"),
            _cell(record.get("taken")),
            _cell(record.get("version"), absent=NOT_STATED),
            _cell(record.get("issues")),
            _cell(record.get("hours")),
            _models(record),
            _per_issue(record),
            _cell(record.get("subagents")),
            _share(record),
            _percent(record.get("idle")),
            note,
        ))
        counts = record.get("quality") or {}
        graded = counts.get(DENOMINATOR)
        quality.append((
            f"`{_cell(record.get('batch'), absent='?')}`",
            _cell(record.get("orchestrator_model"), absent=NOT_STATED),
            _cell(record.get("worker_models"), absent=NOT_STATED),
            _fingerprint(record),
            _trial(record),
            _cell(graded),
            *[_rate(counts.get(name), graded)
              for name in QUALITY_FIELDS if name != DENOMINATOR],
        ))

    text.append("\n## What each line cost\n")
    text.append(_table(COST_COLUMNS, cost))
    text.append("\n## What ran it, and how it went inside the run\n")
    text.append(
        "The model cells are ruling 9; the pipeline cell is ruling 23; the "
        "four counts are ruling 6, read by `run_quality.py` and filled "
        "since 2026-09-06. The trial cell is ticket 39's ruling 22, read by "
        "`run_quality.trial_verdict` -- the same function the merge briefing "
        "prints, so the two cannot disagree. **A VOID line ran something "
        "other than what its map asked for**, so it is not a trial of that "
        "map whatever else it measured.\n")
    text.append(_table(QUALITY_COLUMNS, quality))

    # Ruling 5. Every one of the five is recorded, so none of them is a
    # division a reader has to do.
    text.append("\n## How fast each line was, five ways\n")
    text.append(
        "Wall clock, idle and agent time are all PER ISSUE, which is the "
        "figure `run_timings.py`\nsays to compare across runs rather than the "
        "idle share -- the share moved from 9 per\ncent to 17 per cent "
        "between two runs on 2026-08-31 while idle time itself barely "
        "moved,\nbecause agent time had halved. The estimate ratio is the "
        "MEDIAN of the per-issue\nratios, so one runaway issue cannot decide "
        "it, and `Issues rated` is how many issues\ncarried both an estimate "
        "and a span.\n")
    text.append(_table(FASTER_COLUMNS, [
        (f"`{_cell(one.get('batch'), absent='?')}`",
         _minutes((one.get("faster") or {}).get("wall_minutes_per_issue")),
         _minutes((one.get("faster") or {}).get("idle_minutes_per_issue")),
         _cell((one.get("faster") or {}).get("agent_hours_per_issue")),
         _ratio((one.get("faster") or {}).get("estimate_median_ratio")),
         _cell((one.get("faster") or {}).get("issues_rated")))
        for one in records]))

    # Ruling 21, across agent and stamped steps (ruling 19). One row per kind
    # per line, because a run with no long step of a kind has nothing to show
    # and a column per kind would be mostly empty.
    steps = [(f"`{_cell(one.get('batch'), absent='?')}`", _cell(kind),
              f"{float(found.get('minutes') or 0):.1f}m",
              _cell(found.get("measured")), _cell(found.get("label"), absent="—"))
             for one in records
             for kind, found in sorted((one.get("longest_steps") or {}).items(),
                                       key=lambda kv: -(kv[1].get("minutes") or 0))
             if isinstance(found, dict)]
    text.append("\n## The longest step of each kind\n")
    if steps:
        text.append(
            "A finale's mechanical steps leave NO duration in a transcript "
            "(`run_timings.py:40-46`:\na backgrounded Bash call reads as "
            "instant), and an agent step leaves none in\n`steps.jsonl`. "
            "`Measured by` says which instrument took each figure: `stamped` "
            "is a wall\nclock `run_step.py` held around a command, and "
            "`agent` is a tool call's own span.\n")
        text.append(_table(STEP_COLUMNS, steps))
    else:
        text.append(
            "No line carries a step reading yet. `run_step.py` stamps the "
            "finale's five named\nmechanical kinds from the run this landed "
            "in onward (ruling 19).\n")

    # Ruling 13's per-issue table, and ruling 20's five kind facts in its last
    # five columns.
    text.append("\n## One line per issue\n")
    if issues:
        text.append(
            "`Ratio` is the span against the estimate, which is what an "
            "estimate predicts (ruling\n18); `Size` buckets the midpoint, and "
            f"that rule lives HERE -- small under {SMALL} minutes,\nmedium to "
            f"{MEDIUM}, large above -- so moving a boundary re-reads every line "
            "already\nwritten. The last four columns are ruling 20's kind "
            "facts. A `*` on `Strikes` is a row\nwhose own words disagree with "
            "the derived count; read the row before quoting it.\n")
        rows = []
        for one in issues:
            estimate, span = one.get("estimate_minutes"), one.get("span_minutes")
            rows.append((
                f"`{_cell(one.get('batch'), absent='?')}`",
                _cell(one.get("issue"), absent="?"),
                _minutes(estimate),
                size_bucket(estimate),
                _minutes(span),
                _minutes(one.get("agent_minutes")),
                _ratio(span / estimate if estimate and span else None),
                _cell(one.get("attempts")),
                _cell(one.get("verify"), absent=NOT_MEASURED),
                _cell(one.get("review"), absent=NOT_MEASURED),
                _cell(one.get("correction_rounds")),
                _cell(one.get("strikes")) + ("*" if one.get(
                    "derived_strike_disputed") else ""),
                _cell(one.get("stage")),
                _flag(one.get("critical_gate")),
                _flag(one.get("migration")),
                _flag(one.get("cut_on_a_default")),
            ))
        text.append(_table(ISSUE_COLUMNS, rows))
    else:
        text.append(
            f"No per-issue lines were read. They live in `{ISSUES}`, one per "
            "issue per run\n(ruling 17), and `run_costs.py` writes them at the "
            "finale.\n")

    text.append("")
    return "\n".join(text)


def write_view(repo, records=None) -> tuple:
    """Regenerate `run-costs.md`. The only writer it has.

    `records` defaults to whatever `runs.jsonl` holds AT THIS MOMENT rather
    than to a snapshot the caller read earlier. Ticket 38 puts two runs and a
    hunt in flight at once, so two finales can append seconds apart; rendering
    a caller's older snapshot would write a page missing the other run's line,
    and it would stay missing until something regenerated it. Reading here
    makes the last writer the most complete one instead of the least.

    The write is atomic: render to a temporary file in the same directory and
    replace. A reader never sees a half-written page, and two writers cannot
    interleave into one file.
    """
    root = pathlib.Path(repo)
    path = root / VIEW
    if records is None:
        records = read_runs(root).records
    # Read here for the same reason `records` is: ticket 38 puts two runs in
    # flight, so rendering a caller's older snapshot publishes a page missing
    # the other run's lines, and it stays missing until something regenerates.
    issues = read_issues(root).records
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(render_view(records, issues),
                             encoding="utf-8")
        os.replace(temporary, path)
    except OSError as error:
        return False, f"the view was NOT regenerated: {error}"
    return True, f"regenerated {VIEW}"
