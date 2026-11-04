#!/usr/bin/env python3
"""Fail when the plugin tree goes past `budget.md`.

Counts `skills/*/SKILL.md`, `agents/*.md`, `hooks/*.py` that are not tests, and
`workflows/*.js`; measures each `SKILL.md` against the line limit; and refuses a
`SKILL.md` or agent file that carries a date, the word "ruled" or "changed by",
unless the budget exempts it. Prints one line per failure and exits 1.

    python3 lib/check_budget.py [--root <plugin root>]
"""

import fnmatch
import glob
import os
import re
import sys

DATED = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\bruled\b|\bchanged by\b", re.IGNORECASE)


def read_budget(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in open(path, encoding="utf-8"):
        match = re.match(r"^([a-z-]+):\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def exempt(path: str, patterns: str) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns.split())


def check(root: str) -> list[str]:
    budget = read_budget(os.path.join(root, "budget.md"))
    rel = lambda p: os.path.relpath(p, root)
    found = {
        "skills": sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))),
        "agents": sorted(glob.glob(os.path.join(root, "agents", "*.md"))),
        "hooks": sorted(p for p in glob.glob(os.path.join(root, "hooks", "*.py"))
                        if not os.path.basename(p).startswith("test_")),
        "workflows": sorted(glob.glob(os.path.join(root, "workflows", "*.js"))),
    }
    failures = []
    for kind, paths in found.items():
        limit = int(budget[kind])
        if len(paths) > limit:
            failures.append(f"{kind}: {len(paths)} in the tree, budget {limit}; raise budget.md in the same commit")
    limit = int(budget["skill-file-lines"])
    for path in found["skills"]:
        lines = sum(1 for _ in open(path, encoding="utf-8"))
        if lines > limit and not exempt(rel(path), budget.get("exempt-from-lines", "")):
            failures.append(f"{rel(path)}: {lines} lines, limit {limit}")
    for path in found["skills"] + found["agents"]:
        if exempt(rel(path), budget.get("exempt-from-dates", "")):
            continue
        for number, line in enumerate(open(path, encoding="utf-8"), 1):
            hit = DATED.search(line)
            if hit:
                failures.append(f"{rel(path)}:{number}: carries `{hit.group(0)}`; history belongs in the map or a change note")
    return failures


def main(argv: list[str]) -> int:
    root = argv[argv.index("--root") + 1] if "--root" in argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    failures = check(os.path.abspath(root))
    for line in failures:
        print(line)
    if failures:
        print(f"BUDGET: {len(failures)} failure(s)")
        return 1
    print("budget: within limits")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
