#!/usr/bin/env python3
"""How much wall clock a run lost to the HARNESS rather than to work.

The human asked for this on 2026-08-30, in these words: "is there any way I can
track how much time I lose here". Until now the answer was to ask a session to
go and count, which is how the 2 h 34 m permission block went unnoticed until
the run was over.

Three costs, and they are different things with different remedies:

    prompt     a Bash call that sat PENDING with no result, waiting for a human
               to answer a permission prompt. This is the expensive one.
    poll       a Bash call that slept or looped waiting for something the
               harness would have notified about for free.
    denied     a call the auto-mode classifier refused outright. Cheap: the
               agent rewords and moves on within seconds. Counted, not timed,
               because the cost is the agent's next turn, not the clock.

**Read the three separately and never add them up.** On run `414a-483-286335`,
2026-08-30, denials outnumbered everything (5 of them) and cost minutes, while
ONE prompt cost 146 minutes. A total would have hidden that.

## What the numbers looked like when this was written

Measured across all 33 run-issues sessions on this machine, 2026-08-30:

    polling      435.6 minutes across 735 calls, but concentrated in old runs
    prompts      3 Bash calls ever pending over 15 minutes: 146m, 80m, 18m
    denials      81, of which 46 were sourcing the env file

**Polling is a solved problem, and this records why so nobody re-solves it.**
The runs over 5 per cent are `batch-dc132b` (11.4%, 15 Aug) and
`208-174-184` (6.8%, 2 Aug), both polling a BACKGROUND subagent's task-output
file — closed by the foreground-spawn rule of 18 August and its hook of 23
August. Then `416-419-421` (10.1%) and `batch-34455f` (5.9%), both 25 August,
both polling the citation pass with `ps -p <pid>` — closed by the human's ruling of
26 August that narrowed that pass. Run `414a-483-286335` on 30 August: 0.3%.

So a guard against `sleep` would buy nothing today, and would refuse the
legitimate short waits (`sleep 6; node …` while a dev server boots) along with
the bad ones. Do not build one without re-running this first.

Usage:

    python3 harness_cost.py                      # the newest run
    python3 harness_cost.py --run <worktree-name-fragment>
    python3 harness_cost.py --all                # every run, one row each

Exit 0 always. This measures; it never refuses.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys

PROJECTS = os.path.expanduser("~/.claude/projects")


def _run_session():
    """`run_session.py` owns the road from a batch id to a session."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "run_session.py")
    existing = sys.modules.get("run_session")
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing
    spec = importlib.util.spec_from_file_location("run_session", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_session"] = module
    spec.loader.exec_module(module)
    return module


def _repo_root() -> str:
    """The checkout whose worktree runs are being measured.

    RUN_ISSUES_REPO wins if it is set. Otherwise this asks git for the MAIN
    checkout, because the answer must be the same whether this is invoked from
    the main tree or from a worktree inside it: --git-common-dir points at the
    main tree's .git in both cases. A directory that is not a checkout falls
    back to the working directory.
    """
    override = os.environ.get("RUN_ISSUES_REPO")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
        if common.returncode == 0 and common.stdout.strip():
            return os.path.dirname(os.path.abspath(common.stdout.strip()))
    except (OSError, subprocess.SubprocessError):
        pass
    return os.getcwd()


def _encode(path: str) -> str:
    """Claude Code names a project directory after its path, with every `/` and
    `.` rewritten to `-`. So `/w/repo/.claude/worktrees` becomes
    `-w-repo--claude-worktrees`, and the doubled dash is the leading dot of
    `.claude`, not a separator."""
    return re.sub(r"[/.]", "-", path)


PREFIX = _encode(os.path.join(_repo_root(), ".claude", "worktrees")) + "-"

# A command that waits by sleeping, rather than by letting the harness say so.
POLL = re.compile(
    r"(?<![\w-])sleep\s+[\d$]|while\s+.*\bsleep\b|until\s+.*\bsleep\b|for\s+\w+\s+in.*\bsleep\b",
    re.IGNORECASE | re.DOTALL,
)

# Polling a harness background task, or a raw pid. These are the avoidable ones:
# the harness re-invokes the caller when a background task finishes.
AVOIDABLE = re.compile(r"/tasks/[0-9a-f]+\.output|\bps\s+-p\s+\d+", re.IGNORECASE)

DENIED = ("Blocked by classifier", "denied by the Claude Code auto mode")

# Under this, a pending call is just a slow command. A permission prompt that a
# human answers within a few minutes is not what this is hunting.
PENDING_MINUTES = 15.0


def stamp(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def runs() -> list[str]:
    found = [d for d in os.listdir(PROJECTS) if d.startswith(PREFIX) and "run-issues" in d]
    return sorted(found, key=lambda d: os.path.getmtime(os.path.join(PROJECTS, d)))


def measure(directory: str, paths=None) -> dict:
    """Walk one run's transcripts. Returns the three costs and the run's span.

    `paths` names the transcripts outright, which is what `--batch` passes: a
    batch id selects sessions by ledger, not by directory, so a slug holding
    four sessions contributes only the ones that name the batch.
    """
    facts = {
        "first": None, "last": None,
        "poll_seconds": 0.0, "poll_calls": 0,
        "avoidable_seconds": 0.0, "avoidable_calls": 0,
        "pending": [], "denied": [], "bash_calls": 0,
    }
    if paths is None:
        paths = glob.glob(
            os.path.join(PROJECTS, directory, "**", "*.jsonl"), recursive=True)
    for path in paths:
        try:
            handle = open(path, errors="replace")
        except OSError:
            continue
        with handle:
            seen: dict = {}
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                when = event.get("timestamp")
                if when:
                    moment = stamp(when)
                    if facts["first"] is None or moment < facts["first"]:
                        facts["first"] = moment
                    if facts["last"] is None or moment > facts["last"]:
                        facts["last"] = moment
                content = (event.get("message") or {}).get("content")
                if not isinstance(content, list) or not when:
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        command = str((block.get("input") or {}).get("command") or "")
                        seen[block.get("id")] = (when, block.get("name"), command)
                        if block.get("name") == "Bash":
                            facts["bash_calls"] += 1
                    elif block.get("type") == "tool_result":
                        got = seen.get(block.get("tool_use_id"))
                        if not got:
                            continue
                        started, tool, command = got
                        body = block.get("content")
                        text = body if isinstance(body, str) else json.dumps(body)
                        if any(mark in text for mark in DENIED):
                            facts["denied"].append((started, tool, command[:70]))
                            continue
                        if tool != "Bash":
                            continue
                        try:
                            seconds = (stamp(when) - stamp(started)).total_seconds()
                        except ValueError:
                            continue
                        if POLL.search(command):
                            facts["poll_seconds"] += seconds
                            facts["poll_calls"] += 1
                            if AVOIDABLE.search(command):
                                facts["avoidable_seconds"] += seconds
                                facts["avoidable_calls"] += 1
                        elif seconds / 60 >= PENDING_MINUTES:
                            facts["pending"].append((seconds / 60, command[:70]))
    return facts


def hours(facts: dict) -> float:
    if not facts["first"] or not facts["last"]:
        return 0.0
    return (facts["last"] - facts["first"]).total_seconds() / 3600


def report(name: str, facts: dict) -> None:
    span = hours(facts)
    print(f"\n=== {name}")
    print(f"    span {span:.1f} h, {facts['bash_calls']} Bash call(s)")

    print(f"\n    PROMPTS — Bash calls left pending over {PENDING_MINUTES:.0f} minutes")
    if not facts["pending"]:
        print("        none. This is the expensive class, so an empty list is the good answer.")
    else:
        total = sum(m for m, _ in facts["pending"])
        for minutes, command in sorted(facts["pending"], reverse=True):
            share = f", {minutes / (span * 60) * 100:.1f}% of the run" if span else ""
            print(f"        {minutes:6.0f} min{share}  {command}")
        print(f"        total {total:.0f} min"
              + (f", {total / (span * 60) * 100:.1f}% of the run" if span else ""))
        print("        A pending call is a human being waited for. Cover the class with a")
        print("        rule in .claude/settings.json and it can never be asked again.")

    poll = facts["poll_seconds"] / 60
    avoid = facts["avoidable_seconds"] / 60
    share = f" ({poll / (span * 60) * 100:.1f}% of the run)" if span else ""
    print(f"\n    POLLING — {poll:.1f} min across {facts['poll_calls']} call(s){share}")
    if facts["avoidable_calls"]:
        print(f"        of which AVOIDABLE: {avoid:.1f} min across "
              f"{facts['avoidable_calls']} call(s) polling a task file or a pid.")
        print("        The harness re-invokes the caller when a background task ends.")
    else:
        print("        none of it polls a task file or a pid, so the rest is a short wait")
        print("        for something real — a dev server booting, a build. Leave it alone.")

    print(f"\n    DENIALS — {len(facts['denied'])}, counted not timed")
    kinds: dict = {}
    for _, tool, command in facts["denied"]:
        head = command.strip().split()[0] if command.strip() else tool
        kinds[head] = kinds.get(head, 0) + 1
    for head, count in sorted(kinds.items(), key=lambda kv: -kv[1])[:6]:
        print(f"        {count:4d}  {head}")
    if facts["denied"]:
        print("        A denial costs the agent one turn. It is not the thing to fix first.")


def batch_paths(batch: str, repo=None):
    """Every transcript belonging to a batch: its sessions and their subagents."""
    session = _run_session()
    mains, why = session.sessions_for_batch(batch, repo=repo)
    if not mains:
        return [], why
    paths = list(mains)
    for main in mains:
        folder = session.subagents_dir(main)
        paths += sorted(glob.glob(os.path.join(folder, "*.jsonl")))
    return paths, ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=None, help="fragment of a run worktree name")
    parser.add_argument("--batch", default=None,
                        help="a run or hunt batch id; the sessions are found "
                             "from that batch's ledger, whatever the worktree "
                             "is called (ticket 39, ruling 12)")
    parser.add_argument("--repo", default=None,
                        help="checkout whose worktrees hold the ledger")
    parser.add_argument("--all", action="store_true", help="one row per run, newest last")
    args = parser.parse_args(argv)

    if args.batch:
        paths, why = batch_paths(args.batch, repo=args.repo)
        if not paths:
            print(f"NO READING TAKEN for batch `{args.batch}`: {why}")
            print("\nThis is a missing measurement, not a failed run. Carry on.")
            return 0
        report(f"batch `{args.batch}`  ({len(paths)} transcript(s))",
               measure("", paths=paths))
        return 0

    every = runs()
    if not every:
        print("no run-issues transcripts found", file=sys.stderr)
        return 0

    if args.all:
        print(f"{'run':44s} {'hours':>6} {'prompt min':>11} {'poll min':>9} {'denied':>7}")
        for directory in every:
            facts = measure(directory)
            pending = sum(m for m, _ in facts["pending"])
            print(f"{directory[len(PREFIX):]:44s} {hours(facts):6.1f} "
                  f"{pending:11.0f} {facts['poll_seconds'] / 60:9.1f} "
                  f"{len(facts['denied']):7d}")
        return 0

    if args.run:
        picked = [d for d in every if args.run in d]
        if not picked:
            print(f"no run matching {args.run!r}", file=sys.stderr)
            return 0
        directory = picked[-1]
    else:
        directory = every[-1]

    report(directory[len(PREFIX):], measure(directory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
