#!/usr/bin/env python3
"""Turn the finale suite's red files into register rows, one row per file.

    python3 ~/.claude/skills/run-issues/finale_reds.py --run <run directory>
        [--coverage <report> --diff-range <fork-point>..HEAD]

Tracker-tooling issue 39 (issue 32, item 6, first half). The finale runs the whole
suite once, through `run_suite.py --stage finale`. This reads the newest `finale`
record in that tree's store and, when it is red, writes one row per failing file to
the tree's own register shard, `collect_shards.py --my-shard --prefix fs`. The rows
wait there for the human: the finale no longer spawns promotion.

WHICH ISSUE A FILE BELONGS TO (default Q1). Every issue in the ledger's status table
whose `Touches:` meets the file, and every issue whose own commit in this run
changed it. `Touches:` is read by `headers()` in `check_issue_ready.py`, issue 33's
one reader; a meet is `set_level.meet()` after `set_level.normalise()`, issue 34's
one definition, so a file named inside the run's worktree is read against the main
checkout. The commits come from `seams_from_commits.py`. One issue gives the origin
`<issue>/<batch-id>`; none, or more than one, gives `unknown/<batch-id>`, the null
`check_origin.py` makes legal, and the summary names every issue found.

A RED RECORD NAMING NO FILE gets one row carrying the record's log. `run_suite.py`
names only vitest files, so a Python suite's red always lands here.

COVERAGE (default Q5). Given `--coverage` and `--diff-range`, the report the finale
suite wrote is graded by `check_diff_coverage.audit()`, imported. Each file it
refuses becomes a row mapped as a red file is. A refusal naming no file (no report,
a stale one) becomes one row naming the refusal.

THE NEWEST `finale` RECORD DECIDES (default Q7). A red record followed by a green
re-run writes nothing. A row whose file and log are already in a live shard is not
written again, so the finale may re-enter this step.

Exit 0: rows written, or none owed; the ids written are printed for the merge
briefing. 2: no `finale` record, no ledger, or no git repository, so nothing was
asserted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))

import check_commit_order  # noqa: E402
import check_diff_coverage  # noqa: E402
import run_suite  # noqa: E402
import seams_from_commits  # noqa: E402
from check_issue_ready import headers  # noqa: E402  Issue 33's one reader.
from collect_shards import REGISTER, collect, list_worktrees, my_shard  # noqa: E402
from next_batch import FILE_RE  # noqa: E402
from set_level import NotARepository, meet, normalise, roots  # noqa: E402  Issue 34's.

PREFIX = "fs"
HEADER = ("| ID | one-line summary | audience | severity | status | origin | owner-notes |\n"
          "|---|---|---|---|---|---|---|\n")
NOTES_LIMIT = 200  # `parallel-hunt/SKILL.md`: owner-notes is 200 characters, hard.
RED = "red in the finale suite"
UNCOVERED = "unexecuted under the finale coverage"
FILE_IN_LINE = re.compile(r"^\s*(\S+?)(?::\d+|: absent from the report.*)?\s*$")
FILE_REFUSALS = ("untested", "uncovered")


class Unreadable(Exception):
    """An input this step needs is missing: exit 2."""


def newest_finale(store: Path) -> dict:
    finale = [r for r in run_suite.read_records(store) if r.get("stage") == "finale"]
    if not finale:
        raise Unreadable(f"no `finale` record in {store}; run the suite through "
                         "`run_suite.py --stage finale` first")
    return finale[-1]


def run_issues(ledger: str, issues_dir: Path) -> dict[str, Path]:
    """Every issue in the ledger's status table, with its file where one exists."""
    files = {}
    for path in sorted(issues_dir.iterdir()) if issues_dir.is_dir() else []:
        found = FILE_RE.match(path.name)
        if found and path.is_file():
            files.setdefault(found.group(1).lower(), path)
    return {issue: files.get(issue.lower()) for issue, _ in check_commit_order.status_rows(ledger)}


class Mapper:
    """Which of the run's issues a file belongs to."""

    def __init__(self, repo: Path, ledger: str, issues: dict[str, Path | None]):
        self.tree_root, self.main_root = roots(repo)
        self.touches = {}
        for issue, path in issues.items():
            tokens = headers(path.read_text(encoding="utf-8")).touches if path else ()
            self.touches[issue] = [self.spell(t) for t in tokens]
        self.committed = {}
        for issue, sha in seams_from_commits.committed_shas(ledger):
            for name in seams_from_commits.files_in(repo, sha):
                self.committed.setdefault(self.spell(name), []).append(issue)

    def spell(self, item: str) -> str:
        return normalise(item, self.main_root, self.tree_root)

    def issues_of(self, file: str) -> list[str]:
        spelled = self.spell(file)
        found = [i for i, entries in self.touches.items() if any(meet(spelled, e) for e in entries)]
        for issue in self.committed.get(spelled, []):
            if issue not in found:
                found.append(issue)
        return found


def coverage_files(repo: Path, report: Path, diff_range: str) -> tuple[list[str], list[str]]:
    """The files the coverage check refuses, and its refusals that name no file."""
    diff = check_diff_coverage.read_diff(repo, diff_range, None)
    problems, _ = check_diff_coverage.audit(repo, diff, report, 100.0)
    files, other = [], []
    for problem in problems:
        if problem.kind not in FILE_REFUSALS:
            other.append(f"{problem.kind}: {problem.detail}")
            continue
        for line in problem.lines:
            found = FILE_IN_LINE.match(line)
            if found and found.group(1) not in files:
                files.append(found.group(1))
    return files, other


def notes(what: str, log: str) -> str:
    full = f"open — {what}; log {log}"
    return full if len(full) <= NOTES_LIMIT else f"open — {what}; log {os.path.basename(log)}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="the run directory holding run.md")
    parser.add_argument("--coverage", type=Path, help="the coverage report the finale suite wrote")
    parser.add_argument("--diff-range", help="the run's range, <fork-point>..HEAD")
    parser.add_argument("--trees", nargs="+", help="worktrees, main first; testing only")
    args = parser.parse_args(argv)
    if bool(args.coverage) != bool(args.diff_range):
        parser.error("--coverage and --diff-range go together")

    run_dir = args.run.resolve()
    batch, tracker = run_dir.name, run_dir.parent.parent
    try:
        ledger = (run_dir / "run.md").read_text(encoding="utf-8")
        tree_root, _ = roots(run_dir)
        repo = Path(tree_root)
        record = newest_finale(run_suite.store_of(repo))
        trees = args.trees or list_worktrees(str(repo))
        shard = my_shard(REGISTER, str(repo), trees, tracker.name, prefix=PREFIX)
        if not shard:
            raise Unreadable(f"{repo} is in no worktree of this repository")
        mapper = Mapper(repo, ledger, run_issues(ledger, tracker / "issues"))
        found = []  # (subject, what); subject is a file, or None for the whole record
        if record.get("exit") != 0:
            found += [(name, RED) for name in record.get("failing") or []] or [(None, RED)]
        if args.coverage:
            files, other = coverage_files(repo, args.coverage, args.diff_range)
            found += [(name, UNCOVERED) for name in files]
            found += [(None, f"{UNCOVERED}, {why}") for why in other]
    except (Unreadable, NotARepository, OSError, RuntimeError) as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return 2

    log = str(record.get("log") or "")
    live = "".join(Path(path).read_text(encoding="utf-8") for _, path in collect(REGISTER, trees, tracker.name))
    live_lines = live.splitlines()
    stamp = os.path.basename(log)  # In every row's notes, whole or shortened.
    rows, written = [], []
    for subject, what in found:
        mark = f"`{subject}`" if subject else f"`{log}`"
        if any(mark in line and stamp in line and what in line for line in live_lines + rows):
            continue
        issues = mapper.issues_of(subject) if subject else []
        single = issues[0] if len(issues) == 1 else None
        stem = f"{PREFIX}{single}-" if single else f"{PREFIX}-{batch}-"
        taken = set(re.findall(rf"(?<![\w-]){re.escape(stem)}(\d+)(?![\w-])", live + "".join(rows)))
        row_id = f"{stem}{max([int(n) for n in taken] + [0]) + 1}"
        who = ("issue" + ("s " if len(issues) > 1 else " ") + ", ".join(issues) + " touch" +
               ("" if len(issues) > 1 else "es") + " it") if issues else "no issue in the run touches it"
        if subject:
            summary = f"{mark} is {what} of `{batch}`; {who}"
        else:
            summary = f"`{batch}`: {what}, and no file named; the cause is in {mark}"
        origin = f"{single or 'unknown'}/{batch}"
        rows.append(f"| {row_id} | {summary} | tester | high | open | {origin} | {notes(what, log)} |\n")
        written.append(row_id)

    if rows:
        path = Path(shard)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        lead = "" if existing else f"## Rows the finale suite wrote\n\n{HEADER}"
        if existing and not existing.endswith("\n"):
            lead = "\n"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lead + "".join(rows))
    print(f"finale record exit {record.get('exit')}, log {log}")
    print(f"wrote {len(written)} row(s) to {shard}" + (": " + ", ".join(written) if written else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
