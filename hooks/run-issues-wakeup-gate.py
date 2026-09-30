#!/usr/bin/env python3
"""Refuse a run-issues spawn while the run's ledger names no wakeup cron of this process.

BLAST RADIUS, first:

- Registers on PreToolUse for Agent and Task. Nothing else.
- Matches every `subagent_type` that starts `run-issues-`. Every other spawn
  passes untouched and pays for nothing -- no git call, no disk.
- Acts only when the spawn's working directory is inside a tree a live RUN owns,
  read by `find_live_ledger.py`. A spawn anywhere else passes. A hunt is not a
  run, and its spawns are `parallel-hunt-*`, so it never meets this.
- REFUSES one shape: no live ledger copy for that tree carries a header line
  `Wakeup cron: <job id> pid <CLAUDE_PID>` naming THIS `claude` process. That is
  a missing line, a cleared one (`none — deleted ...`), and one a dead process
  wrote.
- DELIBERATELY LETS PAST: a hook environment with no `CLAUDE_PID`, where a line
  that names any job passes; every payload, ledger or skill file it cannot read.
- Writes nothing.

WHY IT EXISTS. The author's standing ruling of 2026-09-29, given mid-run: the
wakeup cron fires every 30 minutes and resumes only an idle run, and runs had
been seen to forget to create it at all. The rule is "Refuse, or state a fact.
Never ask an agent to remember", so the cron is refused into being here. `~/.claude/skills/run-issues/wakeup_cron.py` holds the ruling in
full and writes the line this hook reads.

WHY A NEW HOOK and not a clause in `run-issues-foreground-gate.py`. That gate is
a pure function of the payload: no disk, no git, one dictionary lookup per
spawn. This check needs a `git worktree list` and a ledger read, which is the
typecheck gate's shape, so it copies that shape and leaves the pure gate pure.

WHY THE PROCESS ID. A `CronCreate` job lives in the memory of the `claude`
process that made it and dies with it. A resume in a new process -- a new
session, or `--resume` of the old one, which keeps the session id -- has no job,
and its ledger still names the dead one. The process id is what changes, so a
line from a dead process refuses until the resume makes a new job.

What it cannot catch: a line written by hand for a job never made. That is a
lie and not a lapse, and only `CronList` inside the session could tell.

It fails OPEN on anything it cannot read, and says so on stderr. A guard that
blocks a spawn when the guard itself breaks is worse than no guard.

Drill: `test_run_issues_wakeup_gate.py` beside this file.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import json
import os
import sys

# The skill's scripts are imported from where the runner runs them, so there is
# one reading of "live" (`find_live_ledger.py`) and one of the line
# (`wakeup_cron.py`).
SKILL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "skills", "run-issues")

SCRIPT = "~/.claude/skills/run-issues/wakeup_cron.py"

AFK = (
    "\n\nTHIS NEVER WAITS FOR THE HUMAN AND IT IS NOT A HALT. Nobody is at the "
    "keyboard for a run. Do not write a HALT BLOCK for this and do not ask. The three steps "
    "above are yours to take, now.\n"
    "(Gate: ~/.claude/hooks/run-issues-wakeup-gate.py)"
)


def is_run_spawn(tool_input):
    """True when this spawn is one of the run-issues roles."""
    if not isinstance(tool_input, dict):
        return False
    return str(tool_input.get("subagent_type") or "").startswith("run-issues-")


def _inside(child, parent):
    """True when `child` is `parent` itself or below it."""
    child = os.path.realpath(child)
    parent = os.path.realpath(parent)
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def owned_ledgers(cwd, runs):
    """The ledger copies of the run whose named tree holds `cwd`.

    `runs` is (tree, ledger path) pairs. Linked worktrees nest inside the main
    checkout, so the deepest tree holding `cwd` is the one that owns it.
    """
    holding = [tree for tree, _ in runs if tree and _inside(cwd, tree)]
    if not holding:
        return []
    tree = max(holding, key=lambda t: len(os.path.realpath(t)))
    paths = [path for named, path in runs
             if named and os.path.realpath(named) == os.path.realpath(tree)]
    # The copy inside the run's own tree first: it is the one the cron's `check`
    # should read and, where the runner writes the worktree copy, the one it writes.
    return sorted(paths, key=lambda path: not _inside(path, tree))


def fault(wakeup, pid):
    """Why one ledger copy fails, or None when it names a job of this process."""
    if wakeup is None:
        return "its header carries no `Wakeup cron:` line"
    if not wakeup.get("job"):
        return f"its line reads `{wakeup['raw'].strip()}`, which names no job"
    if pid is not None and wakeup.get("pid") != pid:
        return (f"its job {wakeup['job']} was made by process {wakeup['pid']}, "
                f"which is not this one ({pid}), and a job dies with the process "
                f"that made it")
    return None


def decide(payload, ledgers=(), pid=None, read_wakeup=None):
    """Return (exit code, message). Pure: `ledgers` is (path, text) pairs."""
    if not isinstance(payload, dict) or not is_run_spawn(payload.get("tool_input")):
        return 0, ""
    if not ledgers:
        return 0, ""

    faults = []
    for path, text in ledgers:
        why = fault(read_wakeup(text), pid)
        if why is None:
            return 0, ""
        faults.append((path, why))

    path, why = faults[0]
    agent = payload["tool_input"].get("subagent_type")
    # Every copy gets the line. The runner mirrors one copy over the other after
    # each write, so a line recorded in the copy it does not write is erased by
    # the next mirror, and the spawn after it is refused again.
    records = "\n".join(
        f"   python3 {SCRIPT} record --ledger {copy} --id <job id>"
        for copy, _ in ledgers)
    return 2, (
        f"run-issues spawn refused: Agent({agent}) belongs to the run whose "
        f"ledger is {path}, and {why}. The rule: every run "
        f"keeps a wakeup cron that fires every 30 minutes and resumes the run "
        f"only when it has been idle for more than 20. Do this now, then "
        f"reissue this exact call:\n"
        f"1. CronList. If a job's prompt names this run's batch id, keep it and "
        f"use its id. Never make a second one.\n"
        f"2. Otherwise run `python3 {SCRIPT} args --ledger {path}` and pass its "
        f"cron, prompt and recurring to CronCreate unchanged.\n"
        f"3. Record the job in every copy of this run's ledger:\n{records}" + AFK
    )


def load_skill():
    """The two skill modules, imported from the skill's own directory."""
    if SKILL_DIR not in sys.path:
        sys.path.insert(0, SKILL_DIR)
    import find_live_ledger
    import wakeup_cron
    return find_live_ledger, wakeup_cron


def live_runs(ledger, cwd):
    """(named tree, ledger path) for every live copy of every live RUN.

    `runs()` keeps one copy per batch, and a run keeps two: the runner writes
    one and mirrors it over the other. Both are listed, so the refusal can send
    the line to both and the next mirror cannot erase it.
    """
    worktrees = ledger.list_worktrees(cwd)
    candidates = ledger.collect_candidates(worktrees=worktrees)
    pairs = []
    for item in ledger.runs(candidates):
        tree = (ledger.parse_worktree_value(getattr(item, "worktree_line", None))
                or getattr(item, "tree", ""))
        for copy in candidates:
            if (copy.kind == "run" and copy.batch == item.batch
                    and ledger.is_live_copy(copy)):
                pairs.append((tree, copy.path))
    return pairs


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        print(f"run-issues-wakeup-gate: unreadable payload ({err}), so the spawn "
              "passed unchecked.", file=sys.stderr)
        return 0

    # Judged FIRST: every spawn on this machine reaches this hook, and only the
    # run's own roles may pay for a `git worktree list` and a ledger walk.
    if not is_run_spawn(payload.get("tool_input")):
        return 0

    cwd = str(payload.get("cwd") or os.getcwd())
    try:
        ledger, wakeup = load_skill()
        paths = owned_ledgers(cwd, live_runs(ledger, cwd))
        ledgers = []
        for path in paths:
            with open(path, encoding="utf-8", errors="replace") as handle:
                ledgers.append((path, handle.read()))
    except Exception as err:  # not a git repo, git hung, skill not merged yet
        print(f"run-issues-wakeup-gate: cannot read the live ledgers ({err}), so "
              "the spawn passed unchecked.", file=sys.stderr)
        return 0

    raw_pid = os.environ.get("CLAUDE_PID", "")
    pid = int(raw_pid) if raw_pid.isdigit() else None
    code, message = decide(payload, ledgers=ledgers, pid=pid,
                           read_wakeup=wakeup.read_wakeup)
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
