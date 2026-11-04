#!/usr/bin/env python3
"""Does a failure hold at the base too? The script answers; no verifier decides.

    python3 ~/.claude/skills/workflow/lib/on_main.py --tree <tree> --base <base tree> \\
        [--label <step>] [--twice] -- <command...>

The build-feature verifiers run every step and go on after a failure, and a
failure is a finding only when it is the feature's (final verifier) or the
note's (verifier, step 5, the unnamed screens). Both files used to say "run
the same command at the base and judge". The judgement is now this script:
it runs `<command>` in `--tree`, and when that fails, the same command in
`--base` (the main checkout for the final verifier, the feature worktree for
the note verifier), and compares the failing items by name.

An item is a failing test the output names: a vitest `FAIL <file>` line, or
a Playwright `✘ <n> [project] › <file>:<line>:<col> › <titles>` line. When
the output names none, the whole command is the one item, judged by its
exit code (a grep, a SQL query, a build).

With `--twice` the command runs a second time in the tree before the base
is consulted, and an item that failed only once is a `flake:` line, not a
failure: the screens step reruns a differing screen alone to tell a flake
from a difference. `suite.py` rechecks its own flakes, so the suite steps do
not need it.

It prints, one line each, and nothing else:

    passes: <label>                                    exit 0
    flake: <item>                                      (with --twice)
    on main: <item> fails here and at <base sha>       the `On main:` line
    feature: <item> fails here and passes at <base sha>  the finding, exit 1

Exit 0 when nothing is the feature's, 1 when at least one item is, 3 on a
refusal (no such tree, no command). Both outputs go to
`<git common dir>/suite/logs/<stamp>-on-main-<label>-{tree,base}.log`.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suite  # noqa: E402

REFUSED = 3
PLAYWRIGHT_FAIL = re.compile(
    r"^\s*[✘✗×x]\s+\d+\s+(?:\[[^\]]*\]\s+›\s+)?(.+?)\s*(?:\(\d+(?:\.\d+)?m?s\))?\s*$")


class Refusal(Exception):
    pass


def failing_items(text: str) -> list[str]:
    """The tests the output names as failing, once each, in order."""
    found = list(suite.failing_files(text))
    for line in suite.ANSI.sub("", text).splitlines():
        match = PLAYWRIGHT_FAIL.match(line)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def run_in(tree: pathlib.Path, command: list[str], log: pathlib.Path) -> tuple[int, list[str]]:
    """(exit code, failing items); a failure the output does not name is the command itself."""
    code, text = suite.run_logged(command, tree, log)
    items = failing_items(text) if code else []
    if code and not items:
        items = [" ".join(command)]
    return code, items


def head_of(tree: pathlib.Path) -> str:
    return suite.git(tree, "rev-parse", "--short=9", "HEAD").strip()


def compare(tree: pathlib.Path, base: pathlib.Path, command: list[str], label: str,
            twice: bool, logs: pathlib.Path, stamp: str) -> tuple[list[str], int]:
    """The lines to print and the exit code."""
    code, failing = run_in(tree, command, logs / f"{stamp}-on-main-{label}-tree.log")
    if code == 0:
        return [f"passes: {label}"], 0
    lines = []
    if twice:
        _, again = run_in(tree, command, logs / f"{stamp}-on-main-{label}-tree-again.log")
        for item in failing:
            if item not in again:
                lines.append(f"flake: {item}")
        failing = [item for item in failing if item in again]
        if not failing:
            return lines + [f"passes: {label} (on the second run)"], 0
    _, at_base = run_in(base, command, logs / f"{stamp}-on-main-{label}-base.log")
    sha = head_of(base)
    exit_code = 0
    for item in failing:
        if item in at_base:
            lines.append(f"on main: {item} fails here and at {sha}")
        else:
            lines.append(f"feature: {item} fails here and passes at {sha}")
            exit_code = 1
    return lines, exit_code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tree", required=True, help="the worktree under test")
    parser.add_argument("--base", required=True, help="the checkout of the base: main, or the feature worktree")
    parser.add_argument("--label", default="step", help="the step's name, for the lines and the logs")
    parser.add_argument("--twice", action="store_true", help="rerun in the tree first; a one-time failure is a flake")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the step's command, after --")
    args = parser.parse_args(argv)
    command = [c for c in args.command if c != "--"] if args.command[:1] == ["--"] else args.command
    try:
        tree, base = pathlib.Path(args.tree).resolve(), pathlib.Path(args.base).resolve()
        for name, path in (("tree", tree), ("base", base)):
            if not path.is_dir():
                raise Refusal(f"--{name} {path} is not a folder")
        if not command:
            raise Refusal("no command after --")
        label = re.sub(r"[^A-Za-z0-9._-]+", "-", args.label).strip("-") or "step"
        logs = suite.common_dir(tree) / "suite" / "logs"
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        lines, code = compare(tree, base, command, label, args.twice, logs, stamp)
    except Refusal as refusal:
        print(f"REFUSED: {refusal}")
        return REFUSED
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
