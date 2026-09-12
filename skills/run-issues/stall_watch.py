#!/usr/bin/env python3
"""Watch one run's ledger from OUTSIDE the run's session, and say when it stops moving.

## Why this is not the cron

`SKILL.md` told the runner to create a ~29-minute `CronCreate` wakeup that reads the
ledger's owner line and mtime, and resumes a run that has gone stale. Run
`batch-200d42` stalled for 208.8 minutes on 2026-09-11 behind a permission modal.
The wakeup had at least seven chances in that window and fired none of them.

The reason is in `CronCreate`'s own contract, and it was measured here on
2026-09-12 rather than read: a one-shot job due at 04:44:00 was still sitting
unfired at 04:45:32, because the session that owned it spent 04:42:02 to 04:45:32
inside a single tool call. **Cron jobs fire only while the REPL is idle.** A
session blocked on a permission modal is mid-query by definition, so the test
never runs. The same contract kills the other half: "jobs live only in this Claude
session ... gone when Claude exits", so a job cannot outlive the session it would
report dead.

So the in-session cron can only ever fire for a session that is alive AND idle —
a usage-limit wait, which is the one case `SKILL.md:837` already scopes it to. It
was never able to see a stall or a death. This file is the part that can, because
it is a separate process and nothing the run's session does can silence it.

## What it decides

A frozen ledger alone cannot tell a stalled run from a dead one — that is the
whole difficulty, and it is why there are two tests here and not one:

    owner line says `none`      the run is finished paperwork or a deliberate
                                halt. Not a stall. Stop watching, quietly.

    ledger mtime is fresh       the run is working. Every transition rewrites
                                the file, so mtime is the progress signal
                                (`SKILL.md`, the owner-line rule).

    stale + session ALIVE       STALLED. Something is waiting for a human that
                                nobody is watching. A resume must NOT run: a
                                second runner against a live owner double-writes
                                the tree. Tell the human to look at the screen.

    stale + session GONE        DEAD. This is the case `resume.md` is written
                                for. Tell the human the resume command.

## How liveness is tested

`lsof -a -d cwd -c claude` prints the working directory of every running `claude`
process. The run is alive when one of them sits in the worktree the ledger's
`Worktree:` line names. Measured on this machine 2026-09-12: the probe found the
watching session's own worktree in that listing.

Two limits, stated rather than hidden. A second session sitting in the run's
worktree reads as the run being alive, so a dead run beside a live neighbour is
called STALLED — the safer of the two errors, because it never starts a second
runner. And a run whose session changed directory reads as dead; nothing in the
skill does that today.

## What it never does

It never resumes, never writes the ledger, never touches the tree. It notifies.
Deciding to resume is the human's, and the road is `resume.md`.
"""

import argparse
import os
import re
import subprocess
import sys
import time

OWNER_RE = re.compile(r"^Owner:\s*(.+?)\s*$", re.M)
WORKTREE_RE = re.compile(r"^Worktree:\s*(.+?)\s*$", re.M)

MOVING = 0
STALLED = 3
DEAD = 4
GONE = 5


def read_header(path):
    """Read only the head of the ledger. The rest is a run's whole history."""
    with open(path, errors="replace") as fh:
        head = fh.read(4096)
    owner = OWNER_RE.search(head)
    worktree = WORKTREE_RE.search(head)
    return (
        owner.group(1) if owner else "",
        (worktree.group(1) if worktree else "").strip().strip("`"),
    )


def owner_is_live(owner):
    """`none — MERGED`, `none — awaiting-merge`, `none — HALTED` all mean nobody owns it."""
    return bool(owner) and not owner.lower().startswith("none")


def session_alive(worktree, runner=subprocess.run):
    """True when a running `claude` process sits in that worktree."""
    if not worktree:
        return False
    try:
        out = runner(
            ["lsof", "-a", "-d", "cwd", "-c", "claude", "-Fn"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        # A liveness test that cannot run must not promote a stall to a death:
        # calling it alive withholds a resume, which is the reversible mistake.
        return True
    want = os.path.realpath(worktree)
    for line in out.splitlines():
        if not line.startswith("n"):
            continue
        cwd = os.path.realpath(line[1:])
        if cwd == want or cwd.startswith(want + os.sep):
            return True
    return False


def notify(title, body):
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{body}" with title "{title}"'],
            capture_output=True, timeout=20,
        )
    except Exception:
        pass  # A missing notifier must never stop the watch.


def check(ledger, stale_minutes, now=None, runner=subprocess.run):
    """One tick. Returns (verdict, message)."""
    if not os.path.exists(ledger):
        return GONE, f"ledger {ledger} is gone"
    owner, worktree = read_header(ledger)
    if not owner_is_live(owner):
        return GONE, f"nobody owns {ledger} ({owner or 'no owner line'})"
    now = time.time() if now is None else now
    age = (now - os.path.getmtime(ledger)) / 60.0
    if age <= stale_minutes:
        return MOVING, f"moving, {age:.0f} min since the last write"
    batch = os.path.basename(os.path.dirname(ledger))
    if session_alive(worktree, runner=runner):
        return STALLED, (
            f"{batch} has not moved in {age:.0f} min and its session is ALIVE. "
            f"Something is waiting for you. Look at the screen; do not resume."
        )
    return DEAD, (
        f"{batch} has not moved in {age:.0f} min and its session is GONE. "
        f"Resume it: cd {worktree} && claude, then /run-issues resume"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", required=True, help="path to the run's run.md")
    ap.add_argument("--stale-minutes", type=float, default=60.0)
    ap.add_argument("--interval-seconds", type=float, default=300.0)
    ap.add_argument("--renotify-minutes", type=float, default=30.0)
    ap.add_argument("--once", action="store_true", help="one tick, then exit on the verdict")
    ap.add_argument("--no-notify", action="store_true")
    args = ap.parse_args(argv)

    last_said, last_at = None, 0.0
    while True:
        verdict, message = check(args.ledger, args.stale_minutes)
        stamp = time.strftime("%H:%M:%S")
        print(f"{stamp} {['moving','','','STALLED','DEAD','done'][verdict]}: {message}", flush=True)
        if args.once:
            return verdict
        if verdict == GONE:
            return 0  # The run ended, or its ledger did. Nothing left to watch.
        if verdict in (STALLED, DEAD):
            due = (time.time() - last_at) / 60.0 >= args.renotify_minutes
            if (verdict != last_said or due) and not args.no_notify:
                notify("/run-issues has stopped moving", message)
                last_said, last_at = verdict, time.time()
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
