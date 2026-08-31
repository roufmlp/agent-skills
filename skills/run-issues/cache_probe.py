#!/usr/bin/env python3
"""Per-agent cache reader for a /run-issues batch. Experiment 2 of the workflow audit.

    python3 cache_probe.py --days 7            the runs in the window, newest last
    python3 cache_probe.py --session <name>    one session by directory name

The question, fixed in `pass-a-cost.md` section 6 before any run: does a fresh subagent
ever read a cache it did not write? A cross-spawn cache hit shows as a cache read on an
agent's FIRST usage row, before that agent has written anything. Pass A expected about
zero on 2.1.220 and nobody has measured it since.

`orchestrator_cost.py` already parses both cache fields, at its `effective()`, and then
collapses them into one weighted number. This script keeps them apart and adds the
first-turn split, which is the part that answers the question. It reads the same
transcripts and reuses that script's run definition, so a run either script names is the
same run.

It counts a repeated message once, by message id, for the reason `read_transcript` gives:
a retried turn writes the row twice.

What it will not do: convert tokens into money, or call a low first-turn number a saving.
A cache read costs a tenth of a write in the weighting this pipeline uses, and whether
that is worth anything depends on a price this script does not know.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load_orchestrator_cost():
    """Import the sibling script by path, so this one runs from any directory."""
    spec = importlib.util.spec_from_file_location(
        "orchestrator_cost", HERE / "orchestrator_cost.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_cache(path: pathlib.Path) -> dict:
    """Cache writes and reads for one transcript, plus the first usage row's reads.

    `first_read` is the whole point: it is what the agent read before it had written
    anything of its own.
    """
    empty = {"written": 0, "read": 0, "first_read": None, "rows": 0}
    written = read = rows = 0
    first_read = None
    seen: set[str] = set()
    try:
        handle = path.open()
    except OSError:
        return empty
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            message = row.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            key = message.get("id") or row.get("uuid")
            if key:
                if key in seen:
                    continue
                seen.add(key)
            if first_read is None:
                first_read = usage.get("cache_read_input_tokens", 0)
            written += usage.get("cache_creation_input_tokens", 0)
            read += usage.get("cache_read_input_tokens", 0)
            rows += 1
    return {"written": written, "read": read, "first_read": first_read, "rows": rows}


def probe(session_dir: pathlib.Path) -> dict:
    agents = []
    for path in sorted((session_dir / "subagents").glob("*.jsonl")):
        entry = read_cache(path)
        entry["name"] = path.stem
        agents.append(entry)
    return {
        "session": session_dir.name,
        "main": read_cache(session_dir.with_suffix(".jsonl")),
        "agents": agents,
    }


def report(result: dict, verbose: bool) -> None:
    agents = [a for a in result["agents"] if a["rows"]]
    if not agents:
        print(f"{result['session']}: no subagent usage rows")
        return

    warm = [a for a in agents if (a["first_read"] or 0) > 0]
    total_written = sum(a["written"] for a in agents)
    total_read = sum(a["read"] for a in agents)
    first_read_total = sum(a["first_read"] or 0 for a in agents)

    print(f"session {result['session']}")
    print(f"  subagents with usage rows   {len(agents)}")
    print(f"  cache written by the fleet  {total_written / 1e6:.2f}M")
    print(f"  cache read by the fleet     {total_read / 1e6:.2f}M")
    if total_written:
        print(f"  read-to-write ratio         {total_read / total_written:.1f} to 1")
    print()
    print("  THE QUESTION: does a fresh subagent read a cache it did not write?")
    print(f"  subagents whose first turn read a cache   {len(warm)} of {len(agents)}")
    print(f"  tokens read on those first turns          {first_read_total / 1e6:.2f}M")
    if warm:
        share = first_read_total / total_read if total_read else 0
        print(f"  Answer: yes, on {len(warm)}. That is {share:.1%} of all fleet reads.")
    else:
        print("  Answer: no. Every subagent started cold.")

    main = result["main"]
    if main["rows"]:
        print()
        print(f"  main thread written         {main['written'] / 1e6:.2f}M")
        print(f"  main thread read            {main['read'] / 1e6:.2f}M")

    if verbose:
        print()
        print(f"  {'agent':<40} {'rows':>5} {'written':>12} {'read':>12} {'1st read':>10}")
        for a in sorted(agents, key=lambda a: -(a["first_read"] or 0)):
            print(
                f"  {a['name'][:40]:<40} {a['rows']:>5} "
                f"{a['written']:>12,} {a['read']:>12,} {(a['first_read'] or 0):>10,}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--session", help="one session directory name, instead of the window")
    parser.add_argument("--verbose", action="store_true", help="one line per subagent")
    args = parser.parse_args()

    cost = load_orchestrator_cost()

    if args.session:
        sessions = [
            project / args.session
            for project in cost.PROJECTS.iterdir()
            if project.is_dir() and (project / args.session / "subagents").is_dir()
        ]
        if not sessions:
            print(f"no session directory named {args.session}", file=sys.stderr)
            return 1
    else:
        runs = cost.find_runs(args.days)
        if not runs:
            print(f"no run with {cost.MIN_SUBAGENTS} or more subagents in {args.days} days")
            return 1
        sessions = [cost.PROJECTS / r["project"] / r["session"] for r in runs]

    for index, session_dir in enumerate(sessions):
        if index:
            print()
        report(probe(session_dir), args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
