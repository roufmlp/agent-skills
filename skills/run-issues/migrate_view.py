#!/usr/bin/env python3
"""Carry the 18 markdown rows of `run-costs.md` into `runs.jsonl`. Once.

Ticket 37 of the pilot-delivery map, sitting 2, ruling 3: "All 18 rows are
kept. The backfilled rows are marked, the duplicate `review-375cbf` row is
deleted once by hand with the reason in the header." The human added: no existing
history may be lost.

**Why this is a script with tests rather than a hand edit.** Most of the
eleven backfilled rows can no longer be re-derived. They were read on
2026-08-30 by `orchestrator_cost.py`, which reads a WEEK window, and the runs
they describe ran between 2026-08-16 and 2026-08-26. A parser that dropped one
silently would lose the only copy.

**The table could not be parsed, and that is not a figure of speech.** A
correction paragraph about the 2026-08-31 row sits BETWEEN two data rows, so
any reader that stops at the first non-row line stops two rows early. This
parser reads every line that looks like a data row, wherever it sits, and
ignores everything else.

**What is lost on purpose, and it is one row.** Run `review-375cbf` holds two
rows, four minutes and 0.9M weighted tokens apart (ticket 36, fault 9). The
FIRST is kept, not the last: it is the one the run's own merge briefing
quoted, so keeping it makes the record agree with a document already written.
The second is reported, never dropped in silence, and it stays in git history.

**The eleven backfilled rows carry no batch id**, because the table records
only a date for them. The record is keyed by batch id, so a stable synthetic
key is minted -- `backfilled-2026-08-16`, and `-b` where a date carries two
rows -- and every one is marked `batch_synthetic` so that nobody goes looking
for a ledger that never existed.

    python3 migrate_view.py --repo <checkout> --write
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

import run_records

ROW = re.compile(r"^\|(?P<body>.*)\|\s*$")
SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BATCH = re.compile(r"run `(?P<batch>[A-Za-z0-9-]+)`\.?\s*")
FIGURE = re.compile(r"(?:(?P<model>[A-Za-z0-9-]+)\s+)?(?P<value>[\d.]+)M")
NOT_READ = {"not read", "not stated", "", "—", "-"}

# Every row before 2026-09-06 wrote a bare token figure with no model beside
# it. Ticket 39 sitting 3 measured that 13 of the top 14 sessions on this
# machine already mixed models, so the number is real and the model behind it
# is genuinely unknown. That is a different fact from "no figure", and filing
# it under a named unknown keeps both readable.
UNKNOWN_MODEL = "not stated"

# The five columns `run_costs.py` scraped from `orchestrator_cost.py --days 7`'s
# LAST data row -- whatever run that row described -- until skills commit
# `aa94b3b` on 2026-09-06. `Hours` and `Idle` were read from the run's own
# transcript throughout and are NOT here.
#
# Found by the daily brief on 2026-09-06 and landed on main as `09db35d1` and
# `c6005ddc` while this sitting was being built. Ruling 3 keeps every row, so
# the mark is what makes keeping them safe: sitting 4's `run_compare.py` would
# otherwise compute a trend across another run's numbers and say nothing about
# it.
BORROWED_COLUMNS = ("issues", "subagents", "weighted", "orchestrator",
                    "per_issue")

# How a row is judged, and it is a measurement rather than the date. The file's
# own header states the check: divide Weighted by Per issue and see whether it
# lands on the row's own Issues count. Measured over the live file on
# 2026-09-06: 18 of 19 rows do not, and the one that does is `batch-170a59`,
# the first row written after the repair. A row missing either figure is
# marked, because absence of evidence is not evidence the row is sound -- every
# row before the repair came out of the same code.
TOLERANCE = 0.6


def borrowed_columns(issues, weighted, per_issue):
    """`()` when the row's own three figures agree, the five names otherwise."""
    if not issues or not weighted or not per_issue:
        return BORROWED_COLUMNS
    total = sum(weighted.values())
    each = sum(per_issue.values())
    if not each:
        return BORROWED_COLUMNS
    return () if abs(total / each - issues) <= TOLERANCE else BORROWED_COLUMNS


def _cells(line):
    match = ROW.match(line.strip())
    return [cell.strip() for cell in match.group("body").split("|")] if match else None


def _number(cell):
    if cell.strip().lower() in NOT_READ:
        return None
    try:
        return float(cell.strip().rstrip("%"))
    except ValueError:
        return None


def _fraction(cell):
    value = _number(cell)
    return value / 100 if value is not None else None


def _by_model(cell, divisor=1.0):
    """`opus 51.9M / fable 0.3M` or a bare `56.9M`, as `{model: tokens}`."""
    if cell.strip().lower() in NOT_READ:
        return None
    found = {}
    for match in FIGURE.finditer(cell):
        model = match.group("model") or UNKNOWN_MODEL
        found[model] = float(match.group("value")) * 1e6 / divisor
    return found or None


def _share(cell):
    if cell.strip().lower() in NOT_READ:
        return None
    found = {}
    for match in re.finditer(r"(?:([A-Za-z0-9-]+)\s+)?(\d+)%", cell):
        found[match.group(1) or UNKNOWN_MODEL] = int(match.group(2)) / 100
    return found or None


def parse_with_report(text):
    """`(records, dropped)`. `dropped` names every row this did not keep."""
    records, dropped, seen, dates = [], [], set(), {}

    for line in (text or "").splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 10 or SEPARATOR.match(line.strip()):
            continue
        taken = cells[0]
        if not DATE.match(taken):
            continue          # The header row, and any prose table on the page.

        note = cells[9]
        match = BATCH.search(note)
        backfilled = "backfilled" in note.lower() and not match
        synthetic = not match
        if match:
            batch = match.group("batch")
            note = BATCH.sub("", note, count=1).strip()
        else:
            # A stable synthetic key. Stable so that re-running the migration
            # produces the same file, and suffixed so that two rows on one
            # date stay two rows -- 2026-08-23 carries two.
            dates[taken] = dates.get(taken, 0) + 1
            suffix = "" if dates[taken] == 1 else f"-{chr(ord('a') + dates[taken] - 1)}"
            batch = f"backfilled-{taken}{suffix}"
            # A backfilled row's whole note is the word `backfilled`, which the
            # view now writes from the flag. Any other note is a real finale
            # row's own words and is kept: the 2026-08-30 row names no batch
            # id -- `run_costs.py` only began writing one into the note later
            # -- and its note is the only record of what that run was.
            note = "" if backfilled else note.strip()

        if batch in seen:
            dropped.append(
                f"DROPPED a second row for `{batch}`, taken {taken}: "
                f"{line.strip()}\n  Ticket 36's fault 9. The first row for "
                "this batch is kept, because it is the one the run's own merge "
                "briefing quoted. This row stays in git history.")
            continue
        seen.add(batch)

        record = {
            "batch": batch,
            "kind": "run",
            "taken": taken,
            # One rule for the version cell, and it lives in `run_records`
            # (ruling 10). A second copy here would drift, which is what
            # `journal_for` taught in ticket 39 sitting 2.
            "version": run_records.normalise_version(cells[1])[0],
            "issues": int(cells[2]) if cells[2].isdigit() else None,
            "hours": _number(cells[3]),
            "weighted": _by_model(cells[4]),
            "per_issue": _by_model(cells[5]),
            "subagents": int(cells[6]) if cells[6].isdigit() else None,
            "orchestrator": _share(cells[7]),
            "idle": _fraction(cells[8]),
            "note": note,
            # Ruling 3: this row predates the record and keeps its own words,
            # however long. `append_run` exempts it from ruling 15's cap on
            # this flag alone, and a finale never writes the flag.
            "carried": True,
            "orchestrator_model": run_records.NOT_STATED,
            "worker_models": run_records.NOT_STATED,
            "fingerprint": {},
            "quality": {name: None for name in run_records.QUALITY_FIELDS},
        }
        marked = borrowed_columns(record["issues"], record["weighted"],
                                  record["per_issue"])
        if marked:
            record["borrowed"] = list(marked)
        # Two independent facts. `batch_synthetic` says this key was minted
        # here because the row names no batch id; `backfilled` says the row was
        # read from transcripts after the fact on 2026-08-30. The 2026-08-30
        # row is the first and not the second.
        if synthetic:
            record["batch_synthetic"] = True
        if backfilled:
            record["backfilled"] = True
        records.append({k: v for k, v in record.items() if v is not None
                        or k in ("hours", "idle")})

    return records, dropped


def parse(text):
    return parse_with_report(text)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.repo)
    view = repo / run_records.VIEW
    records, dropped = parse_with_report(view.read_text(encoding="utf-8"))

    print(f"{len(records)} row(s) carried from {run_records.VIEW}.")
    for line in dropped:
        print(line)
    if not args.write:
        print("\n(nothing written: pass --write)")
        return 0

    records_path = repo / run_records.RUNS
    if records_path.exists():
        print(f"REFUSED: {run_records.RUNS} already exists. This migration "
              "runs once. Delete it deliberately if you mean to re-run.")
        return 1
    for record in records:
        ok, why = run_records.append_run(repo, record)
        if not ok:
            print(why)
            return 1
    ok, said = run_records.write_view(repo, run_records.read_runs(repo).records)
    print(said)
    return 0


if __name__ == "__main__":
    sys.exit(main())
