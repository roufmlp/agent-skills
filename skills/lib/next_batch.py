#!/usr/bin/env python3
"""Pick the next batch of issues for a run, in an order that honours every blocker.

    python3 ~/.claude/skills/lib/next_batch.py <issues dir> --count N [--theme <name>]

Asked for on 2026-09-13. The human scheduled runs by hand, and on that day nearly put
issue 05 ahead of issue 37, which builds the connection every one of 05's criteria
needs, because 05's `## Blocked by` named only a merged issue and the real dependency
sat in prose. This tool reads every issue file, works out what is reachable, and
prints a table of the batch plus up to two commands:

    /harden-issues 34 35 45          members whose Status: is needs-harden
    /run-issues 37 05 05d 38 ...     members whose Status: is ready-for-agent, in order

A command with nothing to list is not printed at all.

WHAT IT READS. `Status:` is the first token after the colon; `done` and `closed` are
satisfied and never batch members, `ready-for-agent` and `needs-harden` are candidates,
anything else is a refusal. The `## Blocked by` section, when present, is read bullet by
bullet (a heading such as `## Blocked by, and the order` counts too): a bullet
counts as a blocker only when its first token, after any `**` and
backticks, is an issue number (`02c`, `02-sign-in-users-sessions`). Bullets like
`None`, `Not blocked by ...`, `Nothing waits on the human` and prose paragraphs are not
blockers. A file with no section has no blockers; measured on 2026-09-13, the nine such
files genuinely had none.

HOW IT ORDERS. A candidate joins the batch once every blocker is satisfied: `done`,
`closed`, or a `ready-for-agent` member already placed. Among the candidates free at
each step the lowest number goes first (`05` before `05b` before `09` before `10`). A
`needs-harden` member does not satisfy anything, because hardening writes criteria and
ships no code: an issue behind one is out of reach until the hardening lands and this
tool is run again.

WHY IT REFUSES. An order the human cannot trust is worse than none. It exits 1 and says why
when the count exceeds what is reachable (naming what stands in the way), when a
blocker names an issue no file carries, when the graph has a cycle (printing it), or
when a file has no `Status:` or one it does not know. It never drops an issue to make
the batch fit. Before printing, the finished order is checked once more, independently
of how it was built, and a stranded issue is a refusal.

THEMES. `--theme <name>` keeps only candidates whose `Themes:` header line (comma
separated) carries the name; their unsatisfied blockers are pulled in ahead of them and
shown in the table. It refuses when no file carries `Themes:` at all, because there is
no theme data to filter on. No file carries one today; the door is left open only.

Exit codes: 0 batch printed; 1 refusal (reason on stderr); 2 bad usage.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SATISFIED = ("done", "closed")
CANDIDATES = ("ready-for-agent", "needs-harden")
KNOWN_STATUSES = SATISFIED + CANDIDATES

ISSUE_ID = r"\d{1,2}[a-z]?"
FILE_RE = re.compile(rf"^({ISSUE_ID})-.*\.md$")
HEADER_RE = re.compile(r"^([A-Z][A-Za-z-]*):\s*(.*)$")
BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
BLOCKER_RE = re.compile(rf"^(?:\*\*)?`?({ISSUE_ID})(?:[-`\s]|$)")
SECTION_RE = re.compile(r"^## Blocked by\b")
HEADING_RE = re.compile(r"^## ")


class Refusal(Exception):
    """A reason the tool will not print an order."""


@dataclass
class Issue:
    id: str
    file: str
    status: str
    blockers: list
    themes: list = field(default_factory=list)


def sort_key(issue_id: str):
    match = re.fullmatch(r"(\d+)([a-z]?)", issue_id)
    return (int(match.group(1)), match.group(2))


def parse_issue(path: Path) -> Issue:
    lines = path.read_text(encoding="utf-8").splitlines()
    issue_id = FILE_RE.match(path.name).group(1)
    status = None
    themes = []
    for line in lines:
        header = HEADER_RE.match(line)
        if not header:
            if line.startswith("## "):
                break
            continue
        key, value = header.groups()
        if key == "Status" and status is None:
            status = value.split()[0] if value.split() else ""
        elif key == "Themes":
            themes = [t.strip() for t in value.split(",") if t.strip()]
    if status is None:
        raise Refusal(f"{path.name}: no Status: line in the header")
    if status not in KNOWN_STATUSES:
        raise Refusal(
            f"{path.name}: Status: {status!r} is not one this tool knows "
            f"({', '.join(KNOWN_STATUSES)})")
    return Issue(issue_id, path.name, status, blockers_of(lines), themes)


def blockers_of(lines) -> list:
    blockers = []
    inside = False
    for line in lines:
        if SECTION_RE.match(line):
            inside = True
            continue
        if inside and HEADING_RE.match(line):
            break
        if not inside:
            continue
        bullet = BULLET_RE.match(line)
        if not bullet:
            continue
        found = BLOCKER_RE.match(bullet.group(1))
        if found and found.group(1) not in blockers:
            blockers.append(found.group(1))
    return blockers


def load_issues(issues_dir: Path) -> dict:
    paths = sorted(p for p in issues_dir.iterdir() if FILE_RE.match(p.name))
    if not paths:
        raise Refusal(f"{issues_dir}: no issue files (NN-slug.md) found")
    issues = {}
    for path in paths:
        issue = parse_issue(path)
        if issue.id in issues:
            raise Refusal(f"{path.name} and {issues[issue.id].file} share number {issue.id}")
        issues[issue.id] = issue
    for issue in issues.values():
        for blocker in issue.blockers:
            if blocker not in issues:
                raise Refusal(
                    f"{issue.file}: blocked by {blocker}, and no file carries that number")
    return issues


def find_cycle(issues: dict):
    """Return one cycle as a list of ids (first repeated at the end), or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {i: WHITE for i in issues}
    stack = []

    def visit(node):
        colour[node] = GREY
        stack.append(node)
        for nxt in issues[node].blockers:
            if colour[nxt] == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if colour[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    for start in sorted(issues, key=sort_key):
        if colour[start] == WHITE:
            found = visit(start)
            if found:
                return found
    return None


def schedule(issues: dict, count: int, theme=None) -> list:
    """Return the batch in order. Raise Refusal when the count cannot be honoured."""
    cycle = find_cycle(issues)
    if cycle:
        raise Refusal("the dependency graph has a cycle: " + " -> ".join(cycle))

    if theme is not None:
        if not any(i.themes for i in issues.values()):
            raise Refusal(
                "--theme asked for, but no issue file carries a Themes: header line; "
                "there is no theme data to filter on")
        wanted = {i.id for i in issues.values()
                  if i.status in CANDIDATES and theme in i.themes}
        if not wanted:
            raise Refusal(f"no candidate issue carries theme {theme!r}")
    else:
        wanted = {i.id for i in issues.values() if i.status in CANDIDATES}

    satisfied = {i.id for i in issues.values() if i.status in SATISFIED}
    placed = []
    placed_ready = set()

    def is_free(issue):
        return all(b in satisfied or b in placed_ready for b in issue.blockers)

    def needed_for(ids):
        """The candidates in `ids` plus every unsatisfied ancestor."""
        needed, todo = set(), list(ids)
        while todo:
            node = todo.pop()
            if node in needed or node in satisfied:
                continue
            needed.add(node)
            todo.extend(issues[node].blockers)
        return needed

    pool = needed_for(wanted)
    while len([p for p in placed if p in wanted]) < count:
        free = [issues[i] for i in sorted(pool - set(placed), key=sort_key)
                if is_free(issues[i])]
        if not free:
            break
        pick = free[0]
        placed.append(pick.id)
        if pick.status == "ready-for-agent":
            placed_ready.add(pick.id)

    reached = [p for p in placed if p in wanted]
    if len(reached) < count:
        stuck = sorted(pool - set(placed), key=sort_key)
        lines = [f"asked for {count}, only {len(reached)} reachable"]
        if not stuck:
            lines.append("  every candidate (ready-for-agent or needs-harden) is already in the batch")
        for sid in stuck:
            waiting = [b for b in issues[sid].blockers
                       if b not in satisfied and b not in placed_ready]
            reasons = ", ".join(f"{b} ({issues[b].status})" for b in waiting)
            lines.append(f"  {sid} waits on {reasons}")
        raise Refusal("\n".join(lines))

    verify_order(placed, issues)
    return placed


def verify_order(order: list, issues: dict) -> None:
    """Independent check: every blocker of every member is satisfied before it."""
    seen_ready = set()
    for issue_id in order:
        issue = issues[issue_id]
        for blocker in issue.blockers:
            other = issues.get(blocker)
            if other is None:
                raise Refusal(f"{issue.file}: blocked by {blocker}, which no file carries")
            if other.status in SATISFIED or blocker in seen_ready:
                continue
            raise Refusal(
                f"{issue.file}: blocked by {blocker} ({other.status}), which the order "
                "does not satisfy before it")
        if issue.status == "ready-for-agent":
            seen_ready.add(issue_id)


def render(order: list, issues: dict) -> str:
    rows = []
    for issue_id in order:
        issue = issues[issue_id]
        waited = []
        for b in issue.blockers:
            other = issues[b]
            waited.append(f"{b} ({other.status})" if other.status in SATISFIED else b)
        rows.append((issue_id, issue.status, ", ".join(waited) or "-"))
    width_id = max(len("Issue"), *(len(r[0]) for r in rows))
    width_st = max(len("Status"), *(len(r[1]) for r in rows))
    out = [f"{'Issue':<{width_id}}  {'Status':<{width_st}}  Waited on"]
    out += [f"{r[0]:<{width_id}}  {r[1]:<{width_st}}  {r[2]}" for r in rows]
    out.append("")
    harden = [i for i in order if issues[i].status == "needs-harden"]
    ready = [i for i in order if issues[i].status == "ready-for-agent"]
    if harden:
        out.append("/harden-issues " + " ".join(harden))
    if ready:
        out.append("/run-issues " + " ".join(ready))
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues_dir", type=Path)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--theme", default=None)
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")
    if not args.issues_dir.is_dir():
        parser.error(f"{args.issues_dir} is not a directory")
    try:
        issues = load_issues(args.issues_dir)
        order = schedule(issues, args.count, args.theme)
    except Refusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1
    sys.stdout.write(render(order, issues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
