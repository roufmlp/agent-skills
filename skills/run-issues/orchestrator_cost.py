#!/usr/bin/env python3
"""Print what the orchestrator cost at each batch size, from runs of the last N days.

Adopted 2026-08-21, in place of a proposed ceiling on batch size. The ruling refused a
refusal: no cap on how many issues a run may take. What it asks for instead is the cost,
stated when the list is picked, and **only from measurements taken inside the last week**.
The reason: a workflow that is improved daily makes an older figure a description of a
system that no longer exists.

That freshness rule is why this reads transcripts rather than a hand-kept table. A table
needs someone to write a row after every run, and nobody did for two of the five runs
measured. A transcript is written whether anyone remembers or not.

What it measures, per run session:

    orchestrator share = weighted tokens in the main transcript
                       / weighted tokens in the main transcript and every subagent's

    weighted = input + cache_creation + (cache_read / 10) + (output * 5)

**This is not the same accounting as `/explain-usage`, and the difference is measured, not
guessed.** On one measured run the two disagree in both directions:

    /explain-usage      207.6M effective, 81% to subagents, 19% main thread
    this script          84.5M weighted,  85% to subagents, 15% main thread

The transcripts hold 666M raw cache-read tokens for that session and the `/usage` screen
reported 248.4M, so the screen and the transcript are not counting the same events. Which
is nearer the bill is unknown and this script does not claim to be.

**What survives the disagreement is the only thing this is for.** The share is 15% under
every weighting tried — 0.1, 0.25, 0.5 and 1.0 on cache reads, 1 and 5 on output — because
the main thread and the fleet have nearly the same composition. And both instruments put
the thirteen-issue run about ten points above the nine-issue runs:

    run          issues   this script   /explain-usage
    2026-08-16        9           21%              18%
    2026-08-17       13           31%              29%
    2026-08-20        9           15%              19%

Two instruments that count differently agree on the direction and roughly on the size.
Compare readings from this script only against other readings from this script.

It prints numbers and the age of each one. It recommends no batch size, because three runs
is not a sample and a recommendation off three points would be an opinion wearing a
measurement's clothes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

PROJECTS = pathlib.Path.home() / ".claude" / "projects"
DEFAULT_WINDOW_DAYS = 7
MIN_SUBAGENTS = 25  # a hardening pass runs 12 to 14; a run has not gone below 35


def effective(usage: dict) -> float:
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0) / 10
        + usage.get("output_tokens", 0) * 5
    )


def read_transcript(path: pathlib.Path) -> tuple[float, dt.datetime | None, dt.datetime | None]:
    """Return (effective tokens, first timestamp, last timestamp). Duplicate rows are
    counted once: the transcript repeats a message when a turn is retried, and both
    copies carry the same message id."""
    total = 0.0
    first = last = None
    seen: set[str] = set()
    try:
        handle = path.open()
    except OSError:
        return 0.0, None, None
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            stamp = row.get("timestamp")
            if stamp:
                try:
                    when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                except ValueError:
                    when = None
                if when:
                    first = when if first is None else min(first, when)
                    last = when if last is None else max(last, when)
            message = row.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            key = message.get("id") or row.get("uuid")
            if key:
                if key in seen:
                    continue
                seen.add(key)
            total += effective(usage)
    return total, first, last


def count_issues(agent_files: list[pathlib.Path]) -> int:
    """How many distinct issues this session worked on.

    Read off the opening line of each subagent prompt. Counting spawns would count
    retries, and the batch size a human picks is a count of issues.

    **Match loosely on purpose. The prompt format is not stable.** One run opened its
    gates with "Verify gate for issue 261," and a run three days later opened them with
    "Verify gate for issue **385 — ". A matcher written against either one silently
    returns zero on the other, which is how the thirteen-issue run first dropped out of
    this table without saying so.
    """
    pattern = re.compile(
        r'"content":"(?:Implement issue|Verify gate for issue|Review gate'
        r'[^"]{0,24}?for issue) \**([0-9]{1,4}[a-z]?)\b'
    )
    issues = set()
    for path in agent_files:
        try:
            with path.open() as handle:
                head = handle.readline()
        except OSError:
            continue
        found = pattern.search(head)
        if found:
            issues.add(found.group(1))
    return len(issues)


def find_runs(window_days: int) -> list[dict]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=window_days)
    runs = []
    if not PROJECTS.is_dir():
        return runs
    for project in PROJECTS.iterdir():
        if not project.is_dir():
            continue
        for session_dir in project.iterdir():
            subagents = session_dir / "subagents"
            if not session_dir.is_dir() or not subagents.is_dir():
                continue
            agent_files = sorted(subagents.glob("*.jsonl"))
            if len(agent_files) < MIN_SUBAGENTS:
                continue
            issues = count_issues(agent_files)
            if issues == 0:
                continue
            main = session_dir.with_suffix(".jsonl")
            if not main.exists():
                continue
            main_tokens, first, last = read_transcript(main)
            if last is None or last < cutoff:
                continue
            fleet = 0.0
            for agent in agent_files:
                fleet += read_transcript(agent)[0]
            total = main_tokens + fleet
            if total <= 0:
                continue
            runs.append(
                {
                    "session": session_dir.name,
                    "project": project.name,
                    "started": first,
                    "ended": last,
                    "main": main_tokens,
                    "fleet": fleet,
                    "total": total,
                    "share": main_tokens / total,
                    "subagents": len(agent_files),
                    "issues": issues,
                }
            )
    runs.sort(key=lambda r: r["ended"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS)
    parser.add_argument("--issues", type=int, help="how many issues this run is about to take")
    args = parser.parse_args()

    runs = find_runs(args.days)
    if not runs:
        print(
            f"No run measured in the last {args.days} days.\n"
            "Nothing to state. The rule is that a figure older than a week describes a\n"
            "workflow that has since changed, so this prints no older reading."
        )
        return 0

    print(f"Orchestrator cost, runs of the last {args.days} days\n")
    print(
        f"{'ended':<12} {'issues':>6} {'agents':>7} {'weighted':>10} "
        f"{'orchestrator':>13} {'per issue':>10}"
    )
    now = dt.datetime.now(dt.timezone.utc)
    for run in runs:
        age = (now - run["ended"]).days
        print(
            f"{run['ended'].date()!s:<12} {run['issues']:>6} {run['subagents']:>7} "
            f"{run['total'] / 1e6:>9.1f}M {run['share'] * 100:>12.0f}% "
            f"{run['main'] / run['issues'] / 1e6:>9.2f}M"
            f"   ({age}d old)"
        )
    print(
        "\nThe orchestrator is the one session that holds the whole run. Every turn re-reads\n"
        "the conversation before it, so a longer batch is re-read more times. The last column\n"
        "is what one more issue adds to that re-reading, and it is the column to read."
    )
    if args.issues:
        print(f"\nThis run is about to take {args.issues} issues. No reading above is a prediction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
