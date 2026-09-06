#!/usr/bin/env python3
"""Stamp start, end and exit code for one of the finale's mechanical steps.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 3, deliverable 3 and ruling 19.

    python3 run_step.py --batch batch-170a59 --kind suite -- npm test

## Why a wrapper and not a stamp

**The runner never stamps a clock** (ticket 36, ruling 3). It is the rule this
file exists to obey rather than to restate. A runner asked to record when a
step started and when it ended writes one time from the other, so the two agree
by construction and the figure measures nothing -- which is exactly why rule 9
of `SKILL.md` was replaced by `check_commit_order.py`, and why ticket 39 ruling
21.3 makes the finale's per-role table read the transcripts rather than the
ledger. A wrapper is the cheapest thing that cannot lie about its own duration:
it holds the clock on both sides of a call it did not make.

## What it covers, and what it deliberately does not

Ruling 19 names five kinds: the citation pass, the suite, the build, the board
render and the cost scripts. Those are SHELL commands, and a shell command
leaves no duration in a transcript at all -- `run_timings.py:40-46` records that
a backgrounded Bash step reads as instant, so only agent steps are timed today.
That gap is the whole reason ruling 5 could not answer "where did the clock go"
for the mechanical half of a finale.

**The board render's own subagent is NOT wrapped, and that is not a hole.** It
is an Agent spawn, so `run_session.spawn_rows` already times it from its
transcript. Ruling 21 asks for the longest step per kind "across agent and
stamped steps", and `run_measures.py` is where the two halves are joined. This
file stamps what the transcript cannot see.

## It can never be the reason a step fails

Every other measurement in this pipeline carries that rule and here it matters
most, because this wrapper sits IN FRONT of the finale's real work rather than
after it. A raise here would stop the suite, the build and the board from
running at all. So:

  * the wrapped command's exit code is passed through UNCHANGED, because
    `finale.md` step 1 makes a refusal from a guard stop the finale, and a
    wrapper that swallowed the code would turn every refusal in the pipeline
    into a pass;
  * a steps file that cannot be written prints `NOT stamped` and the command
    still runs;
  * a command that cannot be started at all is itself stamped, with a null exit
    and `failed_to_start`, because that is a fact about the step.

## No shell, ever

The command arrives as an argument LIST and is run as one. `shell=True` here
would make every finale command a place where a character in a path runs
something else, and it would buy nothing: the finale's commands are fixed,
known and written in `finale.md`.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

# Ruling 19's five, and no sixth. A step stamped under a kind nothing reads is
# a step nobody can find, and ruling 21's longest-step-per-kind reading would
# drop it in silence.
KINDS = ("citation", "suite", "build", "board", "cost")

STEPS = "steps.jsonl"

# The exit code for a command that never started. It is not the command's, so
# it is named here rather than invented at the call site, and it is non-zero
# because a step that could not run did not pass.
COULD_NOT_START = 127


def check_kind(kind):
    """`(ok, reason)`. Refused BEFORE the command runs, because the wrapper
    cannot un-run a command once it has started."""
    if kind in KINDS:
        return True, ""
    return False, (
        f"REFUSED: `{kind}` is not one of the five kinds ruling 19 names: "
        f"{', '.join(KINDS)}. A step stamped under a sixth spelling is left "
        "out of the longest-step-per-kind reading (ruling 21) without saying "
        "so. Nothing was run.")


def steps_beside(ledger_path):
    """The steps file for the run whose ledger this is.

    Ticket 38 ruling 10 puts run state in `.scratch/<feature>/runs/<batch-id>/`
    and `find_live_ledger.journal_for` already resolves the journal beside a
    ledger by the same rule. This is a sibling of both, for a run and a hunt
    alike, so the layout has one shape wherever it is read.
    """
    return os.path.join(os.path.dirname(ledger_path), STEPS)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(steps_path, record):
    """Append one line. `(ok, message)`; it never raises and never halts."""
    try:
        path = pathlib.Path(steps_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError as error:
        return False, (f"the step was NOT stamped into {steps_path}: {error}. "
                       "The command still ran and its exit code is this "
                       "script's.")
    return True, f"stamped {record['kind']} into {os.path.basename(steps_path)}"


def read_steps(steps_path):
    """Every stamped step, and nothing said about the lines that did not parse.

    A damaged line here is not the fault a damaged line in `runs.jsonl` is:
    that file is the record and this one is a reading of one run's clock, so a
    caller that cannot read a line simply has one step fewer to compare.
    `run_records.read_lines` is the one that owes both halves.
    """
    found = []
    try:
        text = pathlib.Path(steps_path).read_text(encoding="utf-8")
    except OSError:
        return found
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            one = json.loads(line)
        except ValueError:
            continue
        if isinstance(one, dict):
            found.append(one)
    return found


def longest_per_kind(lines):
    """`{kind: line}` — the longest stamped step of each kind (ruling 21).

    A kind nothing stamped is ABSENT rather than zero. A zero would say the
    citation pass took no time; absence says nothing measured it, which is
    sitting 2's rule in the human's words: a run with no strikes is a fact, and a
    run whose strikes were never read is not.
    """
    found = {}
    for line in lines:
        kind, seconds = line.get("kind"), line.get("seconds")
        if not kind or not isinstance(seconds, (int, float)):
            continue
        if kind not in found or seconds > found[kind].get("seconds", 0):
            found[kind] = line
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", required=True, help="this run's batch id")
    parser.add_argument("--kind", required=True,
                        help="one of: " + ", ".join(KINDS))
    parser.add_argument("--label", default="",
                        help="what this step is, where the command is noise")
    parser.add_argument("--steps", default="",
                        help="the steps file; default beside the batch's ledger")
    parser.add_argument("--repo", default="",
                        help="checkout whose worktrees hold the ledger")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="-- then the command, as a list. No shell.")
    args = parser.parse_args(argv)

    ok, why = check_kind(args.kind)
    if not ok:
        print(why, file=sys.stderr)
        return 2

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        print("REFUSED: no command. Put it after `--`. Nothing was run.",
              file=sys.stderr)
        return 2

    steps_path = args.steps
    if not steps_path:
        # Deferred until here so that a caller passing --steps pays for no
        # worktree walk, which is the waste the 2026-09-06 review found in the
        # launch reading and again in `run_quality.main`.
        found = _ledger_for(args.batch, args.repo)
        if found is None:
            print(f"NOT stamped: no ledger was found for batch "
                  f"`{args.batch}`, so there is no run directory to stamp "
                  f"into. The command runs anyway.", file=sys.stderr)
            steps_path = ""
        else:
            steps_path = steps_beside(found)

    started = _now()
    failed_to_start = ""
    try:
        done = subprocess.run(command)
        code = done.returncode
    except OSError as error:
        # A missing binary is a fact about the step, not an exception. It is
        # also the one road with no exit code to pass on, so the code is named
        # in `COULD_NOT_START` rather than invented here.
        failed_to_start = str(error)
        code = COULD_NOT_START
    ended = _now()

    record = {
        "batch": args.batch,
        "kind": args.kind,
        "label": args.label,
        "command": command,
        "started": started.isoformat(),
        "ended": ended.isoformat(),
        "seconds": round((ended - started).total_seconds(), 3),
        "exit": None if failed_to_start else code,
        "failed_to_start": failed_to_start or None,
    }
    if steps_path:
        told, message = stamp(steps_path, record)
        if not told:
            print(message, file=sys.stderr)
    if failed_to_start:
        print(f"the step's command could not be started: {failed_to_start}",
              file=sys.stderr)
    return code


def _load(name, filename):
    """Load a sibling script by path, registered before it runs.

    The SAME loader `run_session.py`, `run_quality.py` and `run_measures.py`
    carry, word for word. It had its own `hasattr` variant here until the
    review of 2026-09-06, which is the drift `journal_for` and
    `read_transcript` were consolidated to end -- and the variant was weaker:
    it accepted any `run_session` already in `sys.modules` that happened to
    expose the name, without checking it came from this directory.

    Loaded by PATH rather than imported, because this script is run by
    absolute path from a finale and a plain sibling import throws wherever
    this directory is not on `sys.path`.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    existing = sys.modules.get(name)
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ledger_for(batch, repo):
    """The ledger path for a batch, or None. Never raises.

    `run_session.py` owns the road from a batch id to a ledger (ticket 39,
    ruling 12) and this borrows it rather than growing a second one.
    """
    try:
        found = _load("run_session", "run_session.py").ledger_for_batch(
            batch, repo=repo or None)
        return found.path if found is not None else None
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
