#!/usr/bin/env python3
"""Read the level an issue runs at, fresh from its file, on every call.

    python3 issue_level.py --ledger <run.md> --issue <id>
    python3 issue_level.py --ledger <run.md>          # the one issue in progress

Tracker-tooling issue 40, a light issue runs the light rules (rule 5, ruling Q5).
`run-issues-suite-gate.py` and `check_attempt_cap.py` both import this module, and
issue 42's risk-path hook, which this pack does not ship, imports it too, so the
three cannot read a level three ways.

WHERE THE ISSUE FILE IS (default `q-h0925-40-1`, seam pass h0925). The ledger sits
at `.scratch/<feature>/runs/<batch-id>/run.md`. The issue file is
`.scratch/<feature>/issues/<id>-*.md` in the RUN'S worktree, the tree the ledger's
`Worktree:` line names, and never the copy beside the ledger: issue 42's runner
rewrites `Level:` in the run tree's copy. A ledger with no `Worktree:` line reads
its own tree.

WHICH ISSUE, for the hook. The one status-table row whose Status cell, read by the
header, is `in-progress` or `correction`.

IT NEVER CACHES. Every call opens the file again, so an issue whose line is
rewritten from `light` to `full` mid-run is judged full at the next call (rule 6).

ONLY `Level: light` READS LIGHT, through issue 33's one reader, `headers()` in
`check_issue_ready.py`. Everything else reads full: no line, another word, no row,
two rows, no file, two files. So does a light issue in a tree with no usable risk
file (default seam h0925 Q6), found through issue 34's `set_level.RISK_FILE` and
graded by its `read_risk_file()`: a hand-written `Level: light` there has no
backstop. Each fall to full that is not the plain no-line case carries a `note`
naming what could not be read; the callers print it on stderr.

Exit 0 and the level on stdout. It never refuses: the callers decide.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import pathlib
import re
import sys
from collections import namedtuple

HERE = pathlib.Path(__file__).resolve().parent

LIGHT = "light"
FULL = "full"
LIVE_STATUSES = ("in-progress", "correction")


def _load(name, path):
    # Registered before it runs: a dataclass under `from __future__ import
    # annotations` looks its own module up in `sys.modules`.
    spec = importlib.util.spec_from_file_location(f"issue_level_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ledger = _load("find_live_ledger", HERE / "find_live_ledger.py")
_ready = _load("check_issue_ready", HERE / "check_issue_ready.py")
_risk = _load("set_level", HERE.parent / "lib" / "set_level.py")


# `(level, issue, path, note)`. `note` says why the reading fell to full, for
# stderr, and is None on a plain reading. A namedtuple, not a dataclass: the
# callers load this file by path, unregistered in `sys.modules`.
Reading = namedtuple("Reading", "level issue path note", defaults=(None, None, None))


def _cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def status_word(cell):
    """The cell's first word, lower-cased, past emphasis: `**blocked** (x)`."""
    words = re.split(r"[\s(;,.]+", cell.translate(str.maketrans("", "", "*`")).strip())
    return words[0].lower() if words and words[0] else ""


def _issue_id(cell):
    return re.split(r"[\s—–-]", cell.strip().strip("*`"), maxsplit=1)[0].strip().lower()


def status_rows(ledger_text):
    """`(issue id, Status cell)` for every row of the status table, read by header."""
    rows, columns = [], None
    for line in (ledger_text or "").splitlines():
        if not line.strip().startswith("|"):
            columns = None if not line.strip() else columns
            continue
        cells = _cells(line)
        lowered = [cell.strip("*` ").lower() for cell in cells]
        if "issue" in lowered and "status" in lowered:
            columns = (lowered.index("issue"), lowered.index("status"))
            continue
        if columns is None or all(set(cell) <= set("-: ") for cell in cells):
            continue
        if len(cells) > max(columns):
            rows.append((_issue_id(cells[columns[0]]), cells[columns[1]]))
    return rows


def run_tree(ledger_path, ledger_text):
    """The run's worktree: the `Worktree:` line's, else the tree the ledger is in."""
    for line in (ledger_text or "").splitlines()[:_ledger.HEAD_LINES]:
        if line.startswith("Worktree:"):
            named = _ledger.parse_worktree_value(line)
            if named:
                return named
            break
    parts = pathlib.Path(os.path.abspath(ledger_path)).parts
    if ".scratch" in parts:
        return str(pathlib.Path(*parts[:parts.index(".scratch")]))
    return None


def feature_of(ledger_path):
    parts = pathlib.Path(os.path.abspath(ledger_path)).parts
    at = parts.index(".scratch") if ".scratch" in parts else -1
    return parts[at + 1] if 0 <= at < len(parts) - 1 else None


def _read_text(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def level_in(issue_text):
    """`light` when the issue's own `Level:` line says so, else `full`. The line
    alone, with no risk-file backstop: for a caller that holds only the issue."""
    return LIGHT if _ready.headers(issue_text or "").level == LIGHT else FULL


def read_level(ledger_path, issue, ledger_text=None):
    """The level `issue` runs at, read now from its file in the run's tree."""
    try:
        text = ledger_text if ledger_text is not None else _read_text(ledger_path)
    except OSError as error:
        return Reading(FULL, issue, None, f"cannot read the ledger {ledger_path} "
                       f"({error}), so issue {issue} runs as full")
    tree, feature = run_tree(ledger_path, text), feature_of(ledger_path)
    if not tree or not feature:
        return Reading(FULL, issue, None, f"{ledger_path} is not at "
                       ".scratch/<feature>/runs/<batch-id>/run.md, so issue "
                       f"{issue} runs as full")
    pattern = os.path.join(tree, ".scratch", feature, "issues", f"{issue}-*.md")
    found = sorted(glob.glob(pattern))
    if len(found) != 1:
        what = "no issue file" if not found else f"{len(found)} issue files"
        return Reading(FULL, issue, None, f"{what} at {pattern}, so issue "
                       f"{issue} runs as full")
    try:
        level = _ready.headers(_read_text(found[0])).level
    except OSError as error:
        return Reading(FULL, issue, found[0], f"cannot read {found[0]} ({error}), "
                       f"so issue {issue} runs as full")
    if level is None:
        return Reading(FULL, issue, found[0])
    if level != LIGHT:
        note = None if level == FULL else (
            f"{found[0]} says `Level: {level}`, which is neither light nor full, "
            f"so issue {issue} runs as full")
        return Reading(FULL, issue, found[0], note)
    risk_path = pathlib.Path(tree) / _risk.RISK_FILE
    try:
        _risk.read_risk_file(risk_path)
    except (_risk.Refused, OSError, UnicodeDecodeError) as error:
        return Reading(FULL, issue, found[0], f"issue {issue} says `Level: light`, "
                       f"but the risk file at {risk_path} cannot back it ({error}), "
                       "so it runs as full")
    return Reading(LIGHT, issue, found[0])


def live_issue(ledger_text):
    """`(issue id, None)` for the one row in progress, or `(None, why not)`."""
    live = [issue for issue, status in status_rows(ledger_text)
            if status_word(status) in LIVE_STATUSES]
    if len(live) == 1:
        return live[0], None
    if not live:
        return None, "no status-table row reads `in-progress` or `correction`"
    return None, (f"{len(live)} status-table rows read `in-progress` or "
                  f"`correction` ({', '.join(live)})")


def read_live_level(ledger_path, ledger_text=None):
    """The level of the one issue this run has in progress."""
    try:
        text = ledger_text if ledger_text is not None else _read_text(ledger_path)
    except OSError as error:
        return Reading(FULL, None, None, f"cannot read the ledger {ledger_path} "
                       f"({error}), so the issue runs as full")
    issue, why = live_issue(text)
    if issue is None:
        return Reading(FULL, None, None, f"{ledger_path}: {why}, so the issue "
                       "runs as full")
    return read_level(ledger_path, issue, text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="path to run.md")
    parser.add_argument("--issue", help="issue id; omitted, the one in progress")
    args = parser.parse_args(argv)
    reading = (read_level(args.ledger, args.issue) if args.issue
               else read_live_level(args.ledger))
    if reading.note:
        print(f"issue_level: {reading.note}.", file=sys.stderr)
    print(reading.level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
