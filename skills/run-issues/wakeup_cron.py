#!/usr/bin/env python3
"""Make a /run-issues wakeup cron from its ledger, record it, and judge each firing.

**The human's standing ruling of 2026-09-29**, given mid-run:

  1. The wakeup cron fires every 30 minutes. It used to fire every five hours at
     :17 (`17 */5 * * *`), the usage-limit interval, which is what that run's
     launch created.
  2. A firing resumes the run ONLY when the run has been idle for more than 20
     minutes: the ledger's mtime is older than 20 minutes and no agent of the
     run is still running. Otherwise it does nothing.
  3. The cron is deleted when the run finishes (`awaiting-merge`) or halts.
  4. The human has seen runs forget to create the cron at all. By their rule "Refuse, or
     state a fact. Never ask an agent to remember", creating it is refused into
     being, not reminded: `~/.claude/hooks/run-issues-wakeup-gate.py` refuses
     every `run-issues-*` spawn whose live ledger lacks the `Wakeup cron:` line
     that `record` writes for THIS process.

Four verbs, one ledger each:

  args    Print the `CronCreate` arguments for this run as JSON. Pass `cron`,
          `prompt` and `recurring` unchanged. The prompt names the ledger by
          absolute path and runs `check` below, so the idle test is code.
  record  Write `Wakeup cron: <job id> pid <CLAUDE_PID>` into the ledger header,
          replacing any earlier line. Refuses without `CLAUDE_PID`.
  clear   Rewrite that line to `Wakeup cron: none — deleted <date> <HH:MM>`.
          Run it after `CronDelete`, at `awaiting-merge` and at every halt.
          `check_finale_stage.py` refuses `awaiting-merge` while the line still
          names a job.
  check   The verdict of one firing, one line on stdout, always exit 0:
            STOPPED  the run reads `awaiting-merge`, its owner line reads
                     `none`, or its ledger is gone: delete the job.
            BUSY     the ledger moved inside the last 20 minutes: do nothing.
            IDLE     the ledger has been still for more than 20 minutes: resume,
                     unless an agent of this run is still running.

**Why the line carries the process id, not the session id.** A `CronCreate` job
is held in memory by the `claude` process that made it: nothing is written to
disk, and it dies when that process exits. A session resumed with `--resume`
keeps its session id and has lost its jobs, so a session id would pass a job
that no longer exists. `CLAUDE_PID` is set by the harness in both the Bash tool's
environment and every hook's, and it names the process the job lives in.

**Why `check` is a script and not the `find`/`grep` pair the ruling's own prompt
used.** That prompt matched `^State: awaiting-merge`, and the pilot's ledgers
have carried `State: **awaiting-merge, reached 15:45.**`, which an anchored match
misses. `check_finale_stage.read_state` already reads the decorated forms, so the
stop test uses it and there is one reading of the state line.

What `check` cannot see: whether a background agent of this run is still
running. Agents are session state and no file holds them, so the IDLE line hands
that one test to the session the cron wakes.
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import sys

from check_finale_stage import read_state

CRON = "7,37 * * * *"
IDLE_MINUTES = 20

# `find_live_ledger.py` reads this many lines as the header, and so does the hook.
HEAD_LINES = 60

SCRIPT = "~/.claude/skills/run-issues/wakeup_cron.py"

WAKEUP_LINE = re.compile(r"^Wakeup cron:\s*(?P<value>.*)$")
LIVE_VALUE = re.compile(r"^`?(?P<job>[A-Za-z0-9_-]+)`?\s+pid\s+(?P<pid>\d+)\b")
JOB_ID = re.compile(r"^[A-Za-z0-9_-]{4,64}$")

def batch_of(ledger):
    """The run's batch id: the directory the ledger sits in."""
    name = pathlib.Path(ledger).parent.name
    return name if name.startswith("batch-") else None


def read_wakeup(text):
    """The header's `Wakeup cron:` line, parsed.

    None when the header carries no such line. Otherwise a dict with `raw`, and
    `job` and `pid` when the line names a live job; both are None for a cleared
    line or one in any other shape.
    """
    for line in text.splitlines()[:HEAD_LINES]:
        found = WAKEUP_LINE.match(line)
        if not found:
            continue
        live = LIVE_VALUE.match(found.group("value").strip())
        if live and live.group("job").lower() != "none":
            return {"raw": line, "job": live.group("job"),
                    "pid": int(live.group("pid"))}
        return {"raw": line, "job": None, "pid": None}
    return None


def owner_is_none(text):
    """True when the header's owner line reads `none`, in any decoration."""
    for line in text.splitlines()[:HEAD_LINES]:
        if line.startswith("Owner:"):
            value = line.split(":", 1)[1].strip().lower().lstrip("*`_ ")
            return value.startswith("none")
    return False


def with_line(text, line):
    """`text` with its `Wakeup cron:` line replaced, or inserted after `Owner:`."""
    lines = text.splitlines(keepends=True)
    head = min(len(lines), HEAD_LINES)
    for index in range(head):
        if WAKEUP_LINE.match(lines[index].rstrip("\n")):
            lines[index] = line + "\n"
            return "".join(lines)
    anchor = next((i for i in range(head) if lines[i].startswith("Owner:")), None)
    if anchor is None:
        anchor = next((i for i in range(head) if lines[i].startswith("Worktree:")), 0)
    lines.insert(anchor + 1, line + "\n")
    return "".join(lines)


def cron_args(ledger):
    """The `CronCreate` arguments for the run whose ledger is `ledger`."""
    path = os.path.abspath(ledger)
    prompt = (
        f"Run-issues idle check for {batch_of(path)}. Run "
        f"`python3 {SCRIPT} check --ledger {path}` and do exactly what its one "
        f"line says. Nothing else.")
    return {"cron": CRON, "prompt": prompt, "recurring": True}


def verdict(ledger, now=None):
    """The one line `check` prints."""
    now = datetime.datetime.now().timestamp() if now is None else now
    batch = batch_of(ledger) or "this run"
    delete = (f"Delete this cron job now with CronDelete (CronList shows it: its "
              f"prompt names {batch}), then stop.")
    try:
        text = pathlib.Path(ledger).read_text(encoding="utf-8", errors="replace")
        mtime = os.path.getmtime(ledger)
    except FileNotFoundError:
        return f"STOPPED: the ledger {ledger} is gone, so the run is over. {delete}"
    except OSError as error:
        return (f"UNREADABLE: cannot read {ledger} ({error}). Do nothing and "
                f"reply in one line.")

    wakeup = read_wakeup(text) or {}
    if wakeup.get("job"):
        delete = (f"Delete this cron job now with CronDelete {wakeup['job']}, "
                  f"run `python3 {SCRIPT} clear --ledger {ledger}`, then stop.")
    state = read_state(text)
    if state == "awaiting-merge":
        return f"STOPPED: the ledger reads State {state}. {delete}"
    if owner_is_none(text):
        return f"STOPPED: the ledger's owner line reads none. {delete}"

    minutes = (now - mtime) / 60
    if minutes <= IDLE_MINUTES:
        return (f"BUSY: the ledger was written {minutes:.0f} minutes ago, inside "
                f"the {IDLE_MINUTES}-minute window. Do nothing and reply in one line.")
    return (f"IDLE: the ledger has been still for {minutes:.0f} minutes. If any "
            f"background agent of this run is still running, do nothing and reply "
            f"in one line. Otherwise continue the run as /run-issues resume.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("verb", choices=("args", "record", "clear", "check"))
    parser.add_argument("--ledger", required=True, help="the run's run.md")
    parser.add_argument("--id", help="the job id CronCreate returned (record)")
    args = parser.parse_args(argv)
    ledger = args.ledger

    if args.verb == "check":
        print(verdict(ledger))
        return 0

    if args.verb == "args":
        if not batch_of(os.path.abspath(ledger)):
            print(f"REFUSED: {ledger} does not sit in a runs/batch-<id>/ "
                  f"directory, so the cron cannot name its run.", file=sys.stderr)
            return 1
        print(json.dumps(cron_args(ledger), indent=2))
        return 0

    try:
        text = pathlib.Path(ledger).read_text(encoding="utf-8")
    except OSError as error:
        print(f"REFUSED: cannot read {ledger} ({error}).", file=sys.stderr)
        return 1

    if args.verb == "record":
        if not args.id or not JOB_ID.match(args.id):
            print("REFUSED: --id takes the job id CronCreate returned, such as "
                  "d1ab29e9.", file=sys.stderr)
            return 1
        pid = os.environ.get("CLAUDE_PID", "")
        if not pid.isdigit():
            print("REFUSED: CLAUDE_PID is not set. Run this through the Bash tool "
                  "of the session that ran CronCreate: the job lives in that "
                  "process, and the line must name it.", file=sys.stderr)
            return 1
        line = f"Wakeup cron: {args.id} pid {pid}"
    else:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"Wakeup cron: none — deleted {stamp}"

    pathlib.Path(ledger).write_text(with_line(text, line), encoding="utf-8")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
