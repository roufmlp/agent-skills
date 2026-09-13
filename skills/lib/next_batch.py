#!/usr/bin/env python3
"""Pick the next batch of issues for a run, in an order that honours every blocker.

    python3 ~/.claude/skills/lib/next_batch.py <issues dir> --count N
        [--theme <name>] [--by number]

Asked for on 2026-09-13. The human scheduled runs by hand, and on that day nearly put
issue 05 ahead of issue 37, which builds the connection every one of 05's criteria
needs, because 05's `## Blocked by` named only a merged issue and the real dependency
sat in prose. This tool reads every issue file, works out what is reachable, and
prints a table of the batch plus up to three commands:

    /harden-issues 64 66 67          harden these BEFORE the run; see HOW IT RANKS
    /harden-issues 34 35 45          members whose Status: is needs-harden
    /run-issues 37 05 05d 38 ...     members whose Status: is ready-for-agent, in order

A command with nothing to list is not printed at all.

WHAT IT READS. An issue number is any run of digits with an optional letter suffix:
`07`, `05b`, `641`, `149e`. It was capped at two digits until 2026-09-13, which
dropped every issue from 100 up: the file did not match, `load_issues` never held it,
and the tool neither offered it nor counted it. That broke this file's own promise
that it never silently drops work. One tracker in use carries 641 issues,
measured that day, so the case is live. A leading ISO date is
not an issue number: a bullet opening `- 2026-09-13 ruling ...` is prose, and a dated
note beside the issue files is a note.

`Status:` is the first token after the colon; `done` and `closed` are
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
each step the one with the largest FAN-OUT goes first, and the lowest number breaks
that tie (`05` before `05b` before `09` before `10`). An issue's fan-out is the count
of open issues downstream of it through `## Blocked by`, transitively and counted
once each, so a diamond gives the top issue three and not four. Open means neither
`done` nor `closed` nor held by a run ledger. `--by number` restores the old order,
which is number alone, so a reader can compare the two on one tracker.
A `needs-harden` member does not satisfy anything, because hardening writes criteria
and ships no code: an issue behind one is out of reach until the hardening lands and
this tool is run again.

Ruled by the human on 2026-09-13. Until that day the tie-break was the number alone.
Measured the same day on one tracker: issue 37 sat upstream of 56 open issues and
the 05 family upstream of 48 to 55 each, and the script still listed them by number.

HOW IT RANKS THE HARDEN LINE, the same ruling. A needs-harden issue never appeared in
a `/harden-issues` line unless the count exhausted every ready issue, because its
number is higher, so no agent ever told the human to harden an upstream issue before a
run. The first command line names two kinds of needs-harden issue:

    BLOCKING   it stands in the way of a candidate the placement wanted. That
               candidate is listed under the count line as `35 waits on harden of
               34`, and only where EVERY blocker still in its way is a harden: a
               promise with a second condition hidden in it is worse than no line.
               An issue that also waits on a run stays out of that list, and the
               count line's refusal names the run instead. Ruled by the human on
               2026-09-13, walking the three defaults this line was built on.
    MINTED     its `Origin:` issue has a fan-out above zero. `Origin: 05/batch-<id>`
               means the issue changes what 05 built, and everything downstream of 05
               calls that code, so it inherits 05's fan-out as its rank. Severity from
               its `Rows:` line breaks the tie inside one rank, high before medium, and
               the number breaks that. An origin of `unknown`, an origin no file
               carries, and an origin with fan-out zero all stay out of the line.

The blocking kind is listed before the minted kind, because a blocker holds up work
the count asked for today; fan-out orders each kind inside itself. A batch member is
named by the members line below and never by this one: both are commands a reader
pastes, and a number carried by both teaches the reader to skip one. Both ruled by
the human on 2026-09-13.

This answers "which of the run's new issues do I harden before the next run" without
anyone reading the briefing. The human read it by hand for one run on 2026-09-13,
and the answer was the five issues minted from 05, 05b and 05d. A run-held issue is
never offered in either kind.

WHAT THE LEDGERS ADD. `Status:` in an issue file does not change until a run MERGES,
so an issue that a run has built, or is building now, still reads `ready-for-agent`.
Measured 2026-09-13: one run had all eight of its issues at `done` and this
tool still offered five of them as a fresh batch, and it missed that issue 05 had just
become unblocked by two of them. So the tool also reads every run ledger,
`<feature>/runs/<batch>/run.md`, where `runs/` is the sibling of the issues directory
(a missing `runs/` is harmless). Each ledger's issue table (`| Issue | ... | Status |`)
answers two separate questions per issue:

    SATISFIED (may stand as a blocker)   a row reads `done`
    HELD      (never offered)            a row reads `done`, `in-progress`, `gates`
                                         or `correction`
    RELEASED  (offered again)            `queued`, or `blocked (criteria)` — the run
                                         gave up without building it; not satisfied

Any other row status is a REFUSAL naming the status, the run and the issue. The
vocabulary is the run-issues skill's and it grows; a tool that guessed an unknown
status meant "available" would hand out an issue another session is building, and a
second writer on one issue is how a run rejects correct work. Issues a run holds are
listed under the table with the run id and the row status, so a missing issue explains
itself. A row naming an issue no file carries is also a refusal.

WHAT THE COUNT LINE SAYS. Under the table: `10 of 14 reachable, 4 not shown`. The tool
never silently drops work.

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

# Ledger row statuses, from the run-issues skill: `queued -> in-progress -> gates ->
# done`, plus `correction` and `blocked (criteria)`. Anything else is a refusal.
LEDGER_SATISFIES = ("done",)
LEDGER_HOLDS = ("done", "in-progress", "gates", "correction")
LEDGER_RELEASES = ("queued", "blocked (criteria)")
LEDGER_KNOWN = LEDGER_HOLDS + LEDGER_RELEASES

# The two tie-breaks among the candidates free at one step. Fan-out first is the
# ruling of 2026-09-13; `--by number` restores the old order so a reader can
# compare the two on one tracker.
FAN_OUT = "fan-out"
BY_NUMBER = "number"

# An issue number, the identifier `run-issues/check_origin.py` also reads: any run of
# digits with an optional letter suffix. `07`, `05b`, `641`, and the `149e` of an
# `Origin: 149e/batch-<id>` field.
ISSUE_ID = r"\d+[a-z]?"
# A leading ISO date is not an issue number. A `## Blocked by` bullet may open with a
# ruling date (`- 2026-09-13 ruling ...`), and a dated note may sit beside the issue
# files. The old two-digit cap rejected both by accident; `\d+` would read the first as
# issue 2026 and refuse "blocked by 2026, and no file carries that number", and would
# read the second as an issue file with no Status: line. So the guard is written against
# the date shape itself, at each place a leading number is read.
NOT_A_DATE = r"(?!\d{4}-\d{2}-\d{2})"
FILE_RE = re.compile(rf"^{NOT_A_DATE}({ISSUE_ID})-.*\.md$")
HEADER_RE = re.compile(r"^([A-Z][A-Za-z-]*):\s*(.*)$")
BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
BLOCKER_RE = re.compile(rf"^(?:\*\*)?`?{NOT_A_DATE}({ISSUE_ID})(?:[-`\s]|$)")
SECTION_RE = re.compile(r"^## Blocked by\b")
HEADING_RE = re.compile(r"^## ")
TITLE_RE = re.compile(r"^# ")

# `Origin: <issue>/<run>` and `Rows: <row id> <audience>/<severity>; ...`, the two
# header fields promotion writes on a minted issue. The grammar is
# `run-issues/check_origin.py`'s, which owns it; only the halves this tool ranks by
# are read here. The refusals are deliberately left there and not copied: grading a
# malformed line belongs to the check promotion runs on the file it has just
# written, and a scheduler that refused on one could print no order at all for a
# tracker holding issues minted before those fields existed.
ORIGIN_RE = re.compile(rf"^({ISSUE_ID}|unknown)/", re.IGNORECASE)
ROWS_ENTRY_RE = re.compile(r"^\S+\s+[A-Za-z]+\s*/\s*([A-Za-z]+)$")

# Highest first, and an unranked word sits below `low` rather than refusing: the
# severity only breaks a tie inside one origin's rank.
SEVERITIES = ("critical", "high", "medium", "low")


class Refusal(Exception):
    """A reason the tool will not print an order."""


@dataclass
class Issue:
    id: str
    file: str
    status: str
    blockers: list
    themes: list = field(default_factory=list)
    origin: str = ""       # the issue half of `Origin:`, where it names a real one
    severity: str = ""     # the worst severity on the `Rows:` line


@dataclass
class Plan:
    """What one placement learned: the batch, how much was reachable, and the
    candidates that only a hardening pass can release."""
    order: list
    reachable: int
    waiting: list = field(default_factory=list)


@dataclass
class LedgerRow:
    issue: str
    run: str
    status: str


def sort_key(issue_id: str):
    match = re.fullmatch(r"(\d+)([a-z]?)", issue_id)
    return (int(match.group(1)), match.group(2))


def parse_issue(path: Path) -> Issue:
    lines = path.read_text(encoding="utf-8").splitlines()
    issue_id = FILE_RE.match(path.name).group(1)
    status = None
    themes = []
    origin = severity = ""
    in_header = True
    for line in lines:
        if TITLE_RE.match(line):
            in_header = False
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
        elif key == "Origin" and in_header and not origin:
            origin = origin_issue(value)
        elif key == "Rows" and in_header and not severity:
            severity = worst_severity(value)
    if status is None:
        raise Refusal(f"{path.name}: no Status: line in the header")
    if status not in KNOWN_STATUSES:
        raise Refusal(
            f"{path.name}: Status: {status!r} is not one this tool knows "
            f"({', '.join(KNOWN_STATUSES)})")
    return Issue(issue_id, path.name, status, blockers_of(lines), themes,
                 origin, severity)


def origin_issue(value: str) -> str:
    """The issue half of an `Origin:` line, or "" where it names no single issue.

    `unknown` is legal in that grammar and is exactly the case with no issue to
    rank by, so it reads the same here as a line nobody wrote.
    """
    text = value.replace("*", "").strip().strip("`").strip().lower()
    found = ORIGIN_RE.match(text)
    if not found or found.group(1).lower() == "unknown":
        return ""
    return found.group(1)


def worst_severity(value: str) -> str:
    """The worst severity on a `Rows:` line, or "" where it is not that grammar."""
    worst = ""
    for part in value.replace("*", "").replace("`", "").split(";"):
        found = ROWS_ENTRY_RE.match(part.strip())
        if not found:
            continue
        word = found.group(1).lower()
        if word in SEVERITIES and (not worst
                                   or SEVERITIES.index(word) < SEVERITIES.index(worst)):
            worst = word
    return worst


def severity_rank(issue: Issue) -> int:
    """Higher sorts first. An unranked or absent severity sits below `low`."""
    if issue.severity in SEVERITIES:
        return len(SEVERITIES) - SEVERITIES.index(issue.severity)
    return 0


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


def runs_dir_for(issues_dir: Path) -> Path:
    """`runs/` sits beside the issues directory under the feature directory."""
    return issues_dir.resolve().parent / "runs"


def load_ledgers(runs_dir: Path, issues: dict) -> list:
    """Read every `<runs_dir>/<batch>/run.md` issue table. Missing dir: no rows."""
    rows = []
    if not runs_dir.is_dir():
        return rows
    for ledger in sorted(runs_dir.glob("*/run.md")):
        run_id = ledger.parent.name
        for issue_id, status in ledger_rows(ledger.read_text(encoding="utf-8")):
            if issue_id not in issues:
                raise Refusal(
                    f"run {run_id}: ledger row for issue {issue_id}, and no file carries "
                    "that number")
            if status not in LEDGER_KNOWN:
                raise Refusal(
                    f"run {run_id}: issue {issue_id} has ledger status {status!r}, which "
                    f"this tool does not know ({', '.join(LEDGER_KNOWN)}); it will not "
                    "guess whether the run holds the issue")
            rows.append(LedgerRow(issue_id, run_id, status))
    return rows


def ledger_rows(text: str):
    """Yield (issue id, status) from every table whose header has Issue and Status."""
    issue_col = status_col = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            issue_col = status_col = None
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if issue_col is None:
            if "Issue" in cells and "Status" in cells:
                issue_col, status_col = cells.index("Issue"), cells.index("Status")
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) <= max(issue_col, status_col):
            continue
        if re.fullmatch(ISSUE_ID, cells[issue_col]):
            yield cells[issue_col], cells[status_col]


def held_by(rows: list) -> dict:
    """issue id -> the LedgerRow that keeps it out of a new batch."""
    return {r.issue: r for r in rows if r.status in LEDGER_HOLDS}


def satisfied_by(rows: list) -> dict:
    """issue id -> the LedgerRow whose `done` lets it stand as a blocker."""
    return {r.issue: r for r in rows if r.status in LEDGER_SATISFIES}


def open_ids(issues: dict, rows=()) -> set:
    """The issues that still have to be built: neither `done`/`closed` in the file
    nor held by a run ledger. Fan-out counts these and nothing else."""
    held = held_by(rows)
    return {i.id for i in issues.values()
            if i.status not in SATISFIED and i.id not in held}


def fan_out(issues: dict, rows=()) -> dict:
    """issue id -> how many OPEN issues sit downstream of it through `## Blocked by`.

    An edge runs blocker -> blocked: `05` blocked by `37` puts 05 downstream of 37.
    Counted transitively and as a set, so a diamond (A blocks B and C, both block D)
    gives A three and not four. The subject may be any issue, open or not: a `done`
    issue's fan-out is what its code carries, which is the rank criterion 4 of the
    ruling asks a minted issue to inherit.

    Breadth-first from each node rather than a memo over a topological order,
    because `find_cycle` has not necessarily run yet and a cycle must not hang the
    walk.
    """
    downstream = {i: [] for i in issues}
    for issue in issues.values():
        for blocker in issue.blockers:
            if blocker in downstream:
                downstream[blocker].append(issue.id)
    still_open = open_ids(issues, rows)
    counts = {}
    for start in issues:
        seen, todo = set(), list(downstream[start])
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(downstream[node])
        seen.discard(start)
        counts[start] = len(seen & still_open)
    return counts


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


def schedule(issues: dict, count: int, theme=None, rows=(), by=FAN_OUT,
             counts=None) -> Plan:
    """Return the Plan: the batch in order, how much was reachable, and what only a
    hardening pass can release. Raise Refusal when the count cannot be honoured.
    `by` picks the tie-break among the candidates free at each step: fan-out
    descending then number ascending, or number alone."""
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

    if counts is None:
        counts = fan_out(issues, rows)
    pick_key = (sort_key if by == BY_NUMBER
                else lambda i: (-counts[i], sort_key(i)))

    held = held_by(rows)
    wanted -= set(held)
    satisfied = {i.id for i in issues.values() if i.status in SATISFIED}
    satisfied |= set(satisfied_by(rows))
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

    # A held issue can be a wanted issue's unsatisfied ancestor (a run is building
    # it now). It is never a member, and nothing can be placed behind it.
    pool = needed_for(wanted) - set(held)
    # Place until nothing is free. The greedy pick is deterministic, so the
    # count-limited batch is a prefix of this full placement.
    while True:
        free = [issues[i] for i in sorted(pool - set(placed), key=pick_key)
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
            reasons = ", ".join(
                f"{b} ({issues[b].status}; {held[b].status} in run {held[b].run})"
                if b in held else f"{b} ({issues[b].status})"
                for b in waiting)
            lines.append(f"  {sid} waits on {reasons}")
        raise Refusal("\n".join(lines))

    cut = placed.index(reached[count - 1]) + 1
    batch = placed[:cut]
    verify_order(batch, issues, satisfied)
    return Plan(batch, len(reached), waiting_on_harden(
        sorted(pool - set(placed), key=sort_key), issues, satisfied, placed_ready,
        held))


def waiting_on_harden(stuck, issues: dict, satisfied, placed_ready, held=()) -> list:
    """`(issue id, the needs-harden issues it waits on)` for every stuck candidate
    that a hardening pass would release, in order.

    An issue is listed only when EVERY blocker still standing in its way is
    `needs-harden`. One that also waits on a run, or on a ready issue the placement
    could not reach, is left out: the line is a promise that hardening these frees
    that issue, and a promise with a second condition hidden in it is worse than
    no line.
    """
    waiting = []
    for issue_id in stuck:
        standing = [b for b in issues[issue_id].blockers
                    if b not in satisfied and b not in placed_ready]
        if standing and all(issues[b].status == "needs-harden" and b not in held
                           for b in standing):
            waiting.append((issue_id, standing))
    return waiting


def verify_order(order: list, issues: dict, satisfied=frozenset()) -> None:
    """Independent check: every blocker of every member is satisfied before it.
    `satisfied` carries the ids the ledgers mark `done`; file status is read here."""
    seen_ready = set()
    for issue_id in order:
        issue = issues[issue_id]
        for blocker in issue.blockers:
            other = issues.get(blocker)
            if other is None:
                raise Refusal(f"{issue.file}: blocked by {blocker}, which no file carries")
            if other.status in SATISFIED or blocker in satisfied or blocker in seen_ready:
                continue
            raise Refusal(
                f"{issue.file}: blocked by {blocker} ({other.status}), which the order "
                "does not satisfy before it")
        if issue.status == "ready-for-agent":
            seen_ready.add(issue_id)


def harden_before_the_run(plan: Plan, issues: dict, counts: dict, held=()) -> list:
    """The issues to harden BEFORE the next run, highest leverage first. Two kinds.

    FIRST, every issue that stands between the placement and work it wanted: the
    `needs-harden` blockers of the issues `waiting_on_harden` found, ordered by their
    own fan-out and then by number.

    SECOND, every minted issue whose `Origin:` issue has a fan-out above zero. An
    issue carrying `Origin: 05/batch-<id>` changes what issue 05 built, and
    everything downstream of 05 calls that code, so it inherits 05's fan-out as its
    rank; severity from its `Rows:` line breaks the tie inside one rank, and the
    number breaks that. A minted issue whose origin has fan-out zero is left out.
    This answers "which of the run's new issues do I harden before the next run"
    without anyone reading the briefing. The human read it by hand for one run on
    2026-09-13, and the answer was the five issues minted from 05, 05b and 05d.

    A run-held issue is never offered, in either kind.
    """
    blockers = {b for _, standing in plan.waiting for b in standing}
    first = sorted(blockers, key=lambda i: (-counts[i], sort_key(i)))
    minted = [i for i in issues.values()
              if i.status == "needs-harden" and i.id not in held
              and i.id not in blockers and counts.get(i.origin, 0) > 0]
    second = sorted(minted, key=lambda i: (-counts[i.origin], -severity_rank(i),
                                           sort_key(i.id)))
    return first + [i.id for i in second]


def render(plan: Plan, issues: dict, ledger_rows=(), counts=None) -> str:
    if counts is None:
        counts = fan_out(issues, ledger_rows)
    order, reachable = plan.order, plan.reachable
    done_in = satisfied_by(ledger_rows)
    rows = []
    for issue_id in order:
        issue = issues[issue_id]
        waited = []
        for b in issue.blockers:
            other = issues[b]
            if other.status in SATISFIED:
                waited.append(f"{b} ({other.status})")
            elif b in done_in:
                waited.append(f"{b} (done in {done_in[b].run})")
            else:
                waited.append(b)
        rows.append((issue_id, issue.status, str(counts[issue_id]),
                     ", ".join(waited) or "-"))
    width_id = max(len("Issue"), *(len(r[0]) for r in rows))
    width_st = max(len("Status"), *(len(r[1]) for r in rows))
    width_fo = max(len("Fan-out"), *(len(r[2]) for r in rows))
    out = [f"{'Issue':<{width_id}}  {'Status':<{width_st}}  "
           f"{'Fan-out':<{width_fo}}  Waited on"]
    out += [f"{r[0]:<{width_id}}  {r[1]:<{width_st}}  {r[2]:<{width_fo}}  {r[3]}"
            for r in rows]
    out.append("")
    out.append(f"{len(order)} of {reachable} reachable, {reachable - len(order)} not shown")
    held = [r for r in ledger_rows
            if r.status in LEDGER_HOLDS and issues[r.issue].status in CANDIDATES]
    if held:
        out.append("")
        out.append("Held by a run (Status: in the file is still a candidate):")
        for r in sorted(held, key=lambda r: sort_key(r.issue)):
            out.append(f"  {r.issue:<{width_id}}  {r.status} in run {r.run}")
    if plan.waiting:
        out.append("")
        out.append("Waiting on a harden (not offered, and not counted as reachable):")
        for issue_id, standing in plan.waiting:
            out.append(f"  {issue_id:<{width_id}}  waits on harden of "
                       + ", ".join(standing))
    out.append("")
    harden = [i for i in order if issues[i].status == "needs-harden"]
    # A member is named by the members line below and never by this one. Both are
    # commands a reader pastes, and a number carried by both teaches the reader to skip one.
    before = [i for i in harden_before_the_run(plan, issues, counts,
                                               held_by(ledger_rows))
              if i not in harden]
    if before:
        out.append("/harden-issues " + " ".join(before))
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
    parser.add_argument("--by", choices=(FAN_OUT, BY_NUMBER), default=FAN_OUT,
                        help="tie-break among free candidates (default: fan-out)")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")
    if not args.issues_dir.is_dir():
        parser.error(f"{args.issues_dir} is not a directory")
    try:
        issues = load_issues(args.issues_dir)
        rows = load_ledgers(runs_dir_for(args.issues_dir), issues)
        counts = fan_out(issues, rows)
        plan = schedule(issues, args.count, args.theme, rows, args.by, counts)
    except Refusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1
    sys.stdout.write(render(plan, issues, rows, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
