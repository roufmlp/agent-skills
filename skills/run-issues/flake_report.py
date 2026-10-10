#!/usr/bin/env python3
"""List the test files `run_suite.py` has found flaky in one repository.

    python3 ~/.claude/skills/run-issues/flake_report.py [--repo PATH]

`run_suite.py` re-runs a red whole suite's failing files alone. A file that
passes there is a flake, and the wrapper appends a line to
`run-suite-flakes.jsonl` in the repository's git common directory. This reads
that ledger and prints each file once, most flakes first, with the day it last
flaked. A file that flaked twice or more is marked `repeat`: the wrapper keeps
the run moving, so the fix is owed by an issue, not by the next run.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

FLAKES = "run-suite-flakes.jsonl"


def ledger(repo: pathlib.Path) -> pathlib.Path:
    common = pathlib.Path(subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
        check=True, capture_output=True, text=True).stdout.strip())
    return (common if common.is_absolute() else repo / common).resolve() / FLAKES


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    path = ledger(pathlib.Path(args.repo))
    if not path.exists():
        print(f"no flake recorded: {path} does not exist")
        return 0
    seen: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        seen.setdefault(entry.get("file") or "?", []).append(entry.get("started") or "")
    print(f"flakes  last seen   file   ({path})")
    for name, times in sorted(seen.items(), key=lambda item: (-len(item[1]), item[0])):
        mark = "  repeat" if len(times) > 1 else ""
        print(f"{len(times):>6}  {max(times)[:10]:<10}  {name}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
