#!/usr/bin/env python3
"""Join a run's ledger ESTIMATES to what each issue actually took.

The human asked for this on 2026-08-30, after a hand-join of run `414a-483-286335`
showed every one of its nine issues finishing under estimate, median 0.45x. That
batch was scoped for 26.5 hours of agent time and took 14.3. Batch size is a
decision the human makes at the top of every run, and nothing in this pipeline
told them whether that sizing was any good.

`run_timings.py` already says where the clock went, per STEP. It cannot say
whether that was more or less than expected, because the estimate lives in the
ledger and nothing reads both.

## Two different actuals, and the difference matters

    span     first spawn for the issue to last result for it. Wall clock the
             issue OCCUPIED, including the runner's own turns between steps.
             This is what an estimate predicts, so this is the ratio reported.
    agent    the sum of every agent step's own duration. LARGER than the span
             whenever two steps overlapped, which they should: the two gates are
             spawned in one message and run concurrently.

On run `414a-483-286335` the agent sum came to 14.3 h against `run_timings.py`'s
13.86 h of "a subagent running", and the gap is exactly that concurrency. A tool
reporting only the sum would quietly credit the run for time it never spent.

## What it will not do

It will not call an issue that ran long a failure, or one that ran short a
success. An issue can overrun because it was hard, because its criteria were
wrong, or because the harness stalled — 99f on that run reads 0.98x only
because a permission prompt sat for 146 minutes inside it. **Read this beside
`harness_cost.py`**, never alone.

It also will not adjust anything. The ratio is a fact for the human; the sizing
rule is theirs.

Usage:

    python3 estimate_accuracy.py --ledger .scratch/<feature>/runs/<batch-id>/run.md \\
        --transcript ~/.claude/projects/<run-dir>/<session>.jsonl

Exit 0 when it graded at least one issue and attributed every per-issue spawn.
Exit 2 when it could not read its inputs, matched nothing, or left a spawn
unattributed. A pass over nothing is not a pass, and neither is a table built
from part of the run.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import statistics
import sys

# `3.5h`, `4h`, `2.5h, expect long`, `30-45 min`, `2-2.5 h`, `1 hour`.
# The FIRST number-and-unit in the cell wins; a range becomes its midpoint,
# because taking either end would flatter or damn the estimate by construction.
DURATION = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:-|to|–)?\s*(\d+(?:\.\d+)?)?\s*(hours?|hrs?|h|minutes?|mins?|m)\b",
    re.IGNORECASE,
)

# The id as the row's issue cell opens: `483`, `414a`, `99f`.
ID_IN_CELL = re.compile(r"^(?P<issue>[0-9]+[a-z]?)(?![0-9a-z])")
SEPARATOR = re.compile(r"^\|[\s|:-]+\|?\s*$")

# The issue an agent spawn is about, read from the word `issue` in the prompt's
# HEADING LINE. Every per-issue brief opens with one: `Implement issue **201 —
# …`, `Verify gate for issue **201 — …`, `**CORRECTION ROUND — issue 201.**`.
#
# **The `\*\*` before the digits is the whole fix, and run `batch-88624c` is the
# evidence.** The first version read `\*\*(\d{2,4}[a-z]?)\*\*|\bissue\s+(\d{2,4}[a-z]?)\b`.
# Neither half matches `issue **201 — pin the remaining …**`: the bold span holds
# the TITLE as well as the id, so it is not `**201**`, and `issue\s+` cannot cross
# the two asterisks. `re.search` then walked on and matched some LATER number in
# the brief's body. Measured over that run's 30 per-issue spawns, 18 of 30 went to
# the wrong issue: issue 201's implementer was booked to 207, 224's gates to 156,
# 339's review gate to 224, and issue 224c was never named by any prompt at all,
# which is why it went ungraded. Issue 201 absorbed eight steps and read 7.34x.
ISSUE_IN_PROMPT = re.compile(r"\bissue\s+\**(?P<issue>\d{2,4}[a-z]?)\b", re.IGNORECASE)

# ONLY these agent types belong to one issue. The filter is not tidiness — the
# first version of this script had none, and the run-wide roles wrecked it. The
# finale, the promotion phase and the board rebuild all open by naming the RUN,
# `**414a-483-286335**`, whose first token is `414a`. Issue 414a therefore
# absorbed every step to the end of the run and read 908 minutes against a
# 210-minute estimate: 4.32x, and the spans then totalled 29.7 h inside a 15.5 h
# run, which is impossible and is how the fault was caught.
PER_ISSUE = (
    "run-issues-implementer",
    "run-issues-implementer-escalated",
    "run-issues-verify-gate",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
)


def minutes_from(cell: str) -> float | None:
    """An estimate cell as minutes, or None when it names no duration."""
    found = DURATION.search(cell or "")
    if not found:
        return None
    low, high, unit = found.group(1), found.group(2), found.group(3).lower()
    value = (float(low) + float(high)) / 2 if high else float(low)
    return value * 60 if unit.startswith("h") else value


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def columns(text: str) -> tuple[int, int | None]:
    """(issue column, estimate column). The header decides both."""
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        lowered = [cell.lower() for cell in cells(line)]
        if "issue" not in lowered:
            continue
        issue = lowered.index("issue")
        for name in ("est", "estimate", "size"):
            if name in lowered:
                return issue, lowered.index(name)
        return issue, None
    return 0, None


def estimates(text: str) -> dict[str, float]:
    """Every issue in the ledger that carries a readable estimate."""
    issue_at, est_at = columns(text)
    if est_at is None:
        return {}
    found: dict[str, float] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or SEPARATOR.match(stripped):
            continue
        parts = cells(stripped)
        if len(parts) <= max(issue_at, est_at):
            continue
        token = ID_IN_CELL.match(parts[issue_at])
        if not token:
            continue
        value = minutes_from(parts[est_at])
        if value:
            found[token.group("issue")] = value
    return found


def stamp(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def issue_of(prompt: str) -> str | None:
    """The issue a brief is about, or None.

    **Only the heading line is read, and that is deliberate.** The body of a
    correction round or an attempt-2 brief names other issues, quotes gate
    verdicts and cites register rows, so a reader allowed to fall through to it
    will always find A number and will report it with the same confidence as a
    right one. A brief whose heading names no issue is UNATTRIBUTED, counted by
    the caller and printed. Guessing is what produced the 0.06x-to-7.34x spread.
    """
    for line in (prompt or "").splitlines():
        if not line.strip():
            continue
        found = ISSUE_IN_PROMPT.search(line)
        return found.group("issue") if found else None
    return None


def actuals(path: pathlib.Path) -> tuple[dict[str, dict], list[str]]:
    """Per issue: the wall-clock span it occupied, and the sum of its steps.

    Returns that map and a list of the heading lines of every per-issue spawn
    this could NOT attribute. The second value is the census that makes a
    silent loss impossible: 30 spawns went into run `batch-88624c` and 18 of
    them came out booked to the wrong issue, and nothing said so.
    """
    spans: dict[str, dict] = {}
    orphans: list[str] = []
    open_calls: dict[str, tuple[str, str]] = {}
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            when = event.get("timestamp")
            content = (event.get("message") or {}).get("content")
            if not isinstance(content, list) or not when:
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") in ("Task", "Agent"):
                    given = block.get("input") or {}
                    if str(given.get("subagent_type") or "") not in PER_ISSUE:
                        continue  # A run-wide role. It belongs to no single issue.
                    open_calls[block.get("id")] = (when, str(given.get("prompt") or ""))
                elif block.get("type") == "tool_result":
                    got = open_calls.pop(block.get("tool_use_id"), None)
                    if not got:
                        continue
                    started, prompt = got
                    issue = issue_of(prompt)
                    if not issue:
                        head = next((l.strip() for l in prompt.splitlines() if l.strip()), "")
                        orphans.append(head[:90] or "(an empty prompt)")
                        continue
                    try:
                        begin, end = stamp(started), stamp(when)
                    except ValueError:
                        continue
                    row = spans.setdefault(
                        issue, {"first": begin, "last": end, "agent": 0.0, "steps": 0}
                    )
                    row["first"] = min(row["first"], begin)
                    row["last"] = max(row["last"], end)
                    row["agent"] += (end - begin).total_seconds() / 60
                    row["steps"] += 1
    return spans, orphans


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="the run ledger, run.md")
    parser.add_argument("--transcript", required=True, help="the run's main .jsonl")
    args = parser.parse_args(argv)

    try:
        text = pathlib.Path(args.ledger).read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"REFUSED unreadable-ledger: {error}", file=sys.stderr)
        return 2
    path = pathlib.Path(args.transcript)
    if not path.exists():
        print(f"REFUSED unreadable-transcript: {path} does not exist", file=sys.stderr)
        return 2

    planned = estimates(text)
    if not planned:
        print(
            f"REFUSED no-estimates: {args.ledger} has no `Est` column this could read, "
            "or no row in it names a duration. Nothing was graded, which is not a pass.",
            file=sys.stderr,
        )
        return 2

    measured, orphans = actuals(path)
    rows = []
    for issue, estimate in planned.items():
        got = measured.get(issue)
        if not got or got["agent"] <= 0:
            continue
        span = (got["last"] - got["first"]).total_seconds() / 60
        rows.append((issue, estimate, span, got["agent"], got["steps"]))

    if not rows:
        print(
            f"REFUSED no-match: {len(planned)} estimate(s) read and {len(measured)} issue(s) "
            "found in the transcript, and none of them joined. Check that the ledger and "
            "the transcript are from the SAME run.",
            file=sys.stderr,
        )
        return 2

    rows.sort(key=lambda r: r[2] / r[1])
    print(f"{'issue':8s} {'est min':>8} {'span min':>9} {'ratio':>7} {'agent min':>10} {'steps':>6}")
    for issue, estimate, span, agent, steps in rows:
        print(f"{issue:8s} {estimate:8.0f} {span:9.0f} {span / estimate:6.2f}x "
              f"{agent:10.0f} {steps:6d}")

    ratios = [span / estimate for _, estimate, span, _, _ in rows]
    est_total = sum(r[1] for r in rows)
    span_total = sum(r[2] for r in rows)
    agent_total = sum(r[3] for r in rows)

    print()
    print(f"median {statistics.median(ratios):.2f}x, spread {min(ratios):.2f}x to {max(ratios):.2f}x, "
          f"{len(rows)} issue(s) graded of {len(planned)} estimated")
    print(f"planned {est_total / 60:.1f} h, spans totalled {span_total / 60:.1f} h, "
          f"agent time {agent_total / 60:.1f} h")
    print("    Span and agent time pull in OPPOSITE directions and neither is wrong.")
    print("    A span is longer than its agent time by the runner's own turns between")
    print("    steps; it is shorter by however much the two gates overlapped, which they")
    print("    should. The span is what an estimate predicts, so the span sets the ratio.")

    median = statistics.median(ratios)
    if median < 0.7:
        print(f"\n    Estimates run LONG: the median issue takes {median:.2f} of what it was "
              f"given. A batch scoped at {est_total / 60:.1f} h of issue time occupied "
              f"{span_total / 60:.1f} h.")
    elif median > 1.3:
        print(f"\n    Estimates run SHORT: the median issue takes {median:.2f} of what it was "
              "given. A batch scoped from these will overrun.")
    else:
        print(f"\n    Estimates hold: median {median:.2f}x.")
    print("    ONE run is not a sizing rule. Read this beside harness_cost.py — an issue")
    print("    can read near 1.00x only because a permission prompt sat inside it.")

    graded = sum(r[4] for r in rows)
    booked = sum(row["steps"] for row in measured.values())
    print()
    print(f"attribution: {booked + len(orphans)} per-issue spawn(s) in the transcript, "
          f"{booked} attributed to an issue, {graded} of those inside a graded row")
    if not orphans:
        return 0

    print(
        f"\n    REFUSED unattributed-steps: {len(orphans)} per-issue spawn(s) name no issue "
        "in their\n    heading line, so the rows above are graded on part of the run. Every "
        "issue takes\n    an implementer and two gates, so no issue can hold fewer than "
        "three steps.\n    The heading lines this could not read:",
    )
    for head in orphans:
        print(f"      {head}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
