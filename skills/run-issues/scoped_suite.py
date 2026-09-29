#!/usr/bin/env python3
"""Run the scoped suite: every test whose imports reach a changed file, plus the
repo-wide checks, with coverage, logged and recorded as `run_suite.py` records.

    python3 ~/.claude/skills/run-issues/scoped_suite.py [--since <ref>]

The perf audit of 2026-09-28 (one project, `.scratch/workflow-audit/
perf-audit-2026-09-28/`), fixes 3 and 4.

## Who runs it

- A `Level: light` issue's implementer, as its one suite (rule 5 of
  tracker-tooling issue 40 still refuses it the whole suite).
- The runner, after a correction round that changed test files only.
  `run_suite.py --stage correction` refuses the whole suite there and names
  this script.

## Why the set is wider than the touched files

A light issue's scoped run used to read the tests of the files it touched,
and three reds escaped to the finale: issue 181 broke
`tests/documents/brief-route.test.ts`, whose imports reach a file 181 changed;
254 broke `tests/build-checks/design-values.test.ts` and 234c broke
`tests/sessions/standing-rules.test.ts`, repo-wide checks that read source as
text and import nothing either changed.

So the set is two parts:

1. **The import closure.** `vitest list --filesOnly --changed=<since>` names
   every test file that transitively imports a changed file, changed test
   files included. vitest walks its own module graph, so aliases resolve as
   the suite resolves them. Changed means the uncommitted work, since the
   runner commits each issue after its gates; `--since <ref>` widens it. A
   change to a file vitest's `forceRerunTriggers` names, `package.json` or the
   vitest config by default, lists every file: a whole suite by that road,
   and correctly so.
2. **The repo-wide checks.** vitest filters, `tests/build-checks/` and
   `standing-rules.test.` by default. A repo replaces them with a
   `sweepTests` list in `.claude/run-isolation.json`. A filter matches a test
   file whose path holds it, and the config's own `exclude` still applies, so
   a harness file named by a filter stays out.

The harness suite runs after it where the diff touches a path the harness
contract names (`run_suite.harness_wanted`).

## What it refuses, exit 3

A `sweepTests` value that is not a list of non-empty strings, a harness
contract it cannot place, a `vitest list` that fails (an empty set read as
"nothing to test" would be a false green), a directory outside git, and a
second green run on an unchanged tree.

The command's exit passes through, and 127 is a command that could not start.
The record goes to the same store as `run_suite.py`'s, at stage `scoped`, with
the files and filters it ran and the coverage report it kept.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_suite  # noqa: E402

STAGE = "scoped"
DEFAULT_SWEEP = ("tests/build-checks/", "standing-rules.test.")
REFUSED = run_suite.REFUSED
SCOPED = run_suite.SCOPED


def refuse(why: str) -> int:
    print(f"REFUSED: {why}\nThe scoped suite did not start.")
    return REFUSED


def sweep_filters(tree: pathlib.Path) -> list[str]:
    """The repo-wide checks: the repo's `sweepTests`, or the default. Raises
    `run_suite.ContractError` on a value it cannot use."""
    path = tree / run_suite.CONTRACT
    if not path.exists():
        return list(DEFAULT_SWEEP)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        declared = data.get("sweepTests")
    except (ValueError, AttributeError, OSError) as error:
        raise run_suite.ContractError(f"{path} does not read as a JSON object ({error})")
    if declared is None:
        return list(DEFAULT_SWEEP)
    if not isinstance(declared, list) or not declared or not all(
            isinstance(item, str) and item for item in declared):
        raise run_suite.ContractError(
            f"{path}: sweepTests is {declared!r}. It must be a list of vitest "
            f"filters, each a non-empty string.")
    return declared


def related(vitest: list[str], tree: pathlib.Path, since: str) -> list[str]:
    """Every test file whose imports reach a change since `since`, as vitest's
    module graph names them, relative to the tree. Raises on a failed list."""
    with tempfile.TemporaryDirectory() as scratch:
        out = pathlib.Path(scratch) / "list.json"
        done = subprocess.run(
            [*vitest, "list", "--filesOnly", f"--changed={since}", f"--json={out}"],
            cwd=tree, capture_output=True, text=True)
        if done.returncode != 0 or not out.exists():
            raise RuntimeError(f"`vitest list` exited {done.returncode}: "
                               f"{(done.stdout + done.stderr).strip()[-2000:]}")
        entries = json.loads(out.read_text(encoding="utf-8"))
    found = []
    for entry in entries:
        path = pathlib.Path(entry["file"])
        name = str(path.relative_to(tree)) if path.is_relative_to(tree) else str(path)
        if name not in found:
            found.append(name)
    return found


def light_commit_refusal(tree: pathlib.Path, level: str) -> str | None:
    """Why the runner may not commit a light issue's tree yet, or None.

    The perf audit of 2026-09-28, fix 4: three light-issue reds reached the
    finale because nothing read more than the touched files before the
    commit. The newest `scoped` record for the tree being committed decides:
    green passes, red or none refuses. A full issue is not judged here; its
    implementer's whole suite and the verify gate read its tree. Nor is a
    tree with no vitest installed: the scoped road is vitest's, and the skills
    repository runs light issues on Python suites."""
    if level != "light" or not (tree / "node_modules" / ".bin" / "vitest").exists():
        return None
    tree_id = run_suite.tree_hash(tree)
    for record in reversed(run_suite.read_records(run_suite.store_of(tree))):
        if record.get("stage") != STAGE or tree_id not in (
                record.get("tree"), record.get("tree_after")):
            continue
        if record.get("exit") == 0:
            return None
        return (f"the newest scoped reading of tree {tree_id}, at "
                f"{record.get('started')}, exited {record.get('exit')}. Failing "
                f"files: {', '.join(record.get('failing') or []) or 'none named'}. "
                f"Whole output: {record.get('log')}. Fix the red, then run "
                f"`{SCOPED}` again.")
    return (f"no scoped reading exists for tree {tree_id}, the tree this commit "
            f"stages. A light issue commits only on a green one, which runs every "
            f"test whose imports reach the change and the repo-wide checks:\n"
            f"  {SCOPED}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="HEAD",
                        help="The ref the change is measured from. HEAD: the uncommitted work.")
    parser.add_argument("--vitest", default="npx vitest",
                        help="How vitest is launched in this tree.")
    args = parser.parse_args(argv)
    vitest = shlex.split(args.vitest)

    _, queue = run_suite.take_lock()
    try:
        tree, tree_id, store = run_suite.locate(os.getcwd())
    except (subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        return refuse(f"git could not read {os.getcwd()} ({detail.strip()}).")
    tree = tree.resolve()
    (store / "logs").mkdir(parents=True, exist_ok=True)
    try:
        contract = run_suite.harness_contract(tree)
        sweep = sweep_filters(tree)
    except run_suite.ContractError as error:
        return refuse(str(error))

    earlier = run_suite.green_before(run_suite.read_records(store), tree_id, STAGE)
    if earlier:
        return refuse(f"tree {tree_id} already ran green at stage {STAGE}, at "
                      f"{earlier.get('started')}. Read that log: {earlier.get('log')}")
    try:
        files = related(vitest, tree, args.since)
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        return refuse(f"vitest could not name the tests the change reaches. {error}")

    started = run_suite.now()
    stem = f"{started:%Y%m%dT%H%M%S.%fZ}-{STAGE}-{tree_id[:12]}"
    log = store / "logs" / f"{stem}.log"
    kept = store / "coverage" / stem
    command, reports = run_suite.with_coverage(
        [*vitest, "run", *(str(tree / name) for name in files), *sweep,
         "--passWithNoTests"], kept)
    suite_exit, text = run_suite.run_logged(command, log)
    report = run_suite.keep_report(reports, started, kept)
    harness = run_suite.run_harness(STAGE, tree, contract,
                                    store / "logs" / f"{stem}-harness.log")
    ended = run_suite.now()
    tree_after = run_suite.after_hash(tree)
    failing = run_suite.failing_files(text)
    failing += [name for name in harness.get("failing", []) if name not in failing]
    exit_code = suite_exit or harness.get("exit", 0)

    record = {"tree": tree_id, "tree_after": tree_after, "stage": STAGE,
              "exit": exit_code,
              "suite_exit": suite_exit, "harness": harness, "command": command,
              "files": files, "sweep": sweep, "since": args.since,
              "asked": queue.asked.isoformat(), "waited": queue.waited,
              "lock": queue.lock, "lock_holder": queue.holder,
              "started": started.isoformat(),
              "seconds": round((ended - started).total_seconds(), 1),
              "log": str(log), "failing": failing,
              "coverage": str(report) if report else None,
              "report_root": str(tree) if report else None}
    with open(store / run_suite.RECORDS, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    print(f"scoped suite exit {suite_exit}, tree {tree_id}: {len(files)} files "
          f"whose imports reach the change since {args.since}, and the checks "
          f"{', '.join(sweep)}")
    print(run_suite.queue_line(queue))
    for line in run_suite.summary_lines(text):
        print(f"  {line}")
    if failing:
        print("failing files:")
        for name in failing:
            print(f"  {name}")
    print(f"whole output: {log}")
    print(run_suite.harness_line(harness))
    if report:
        print(f"Coverage report: {report}\nReport root:     {tree}")
    else:
        print("no coverage report: the run wrote none.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
