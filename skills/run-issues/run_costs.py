#!/usr/bin/env python3
"""Measure the run that has just finished, from its own transcript.

The human asked for this on 2026-08-30: where and when do those results come, or
do they have to be prompted for manually. Today the answer is manually, and that
is the whole fault this closes.

Both readings already existed and neither was wired to anything:

  * `orchestrator_cost.py` runs at LAUNCH (`SKILL.md:989`) and reads the LAST
    WEEK. It never measures the run it opens.
  * `run_timings.py` was built on 2026-08-26, when a fourteen-hour run could not
    say which step ate the clock. It is named in no skill file. It has only ever
    been run by hand.

So a run states what other runs cost and never records its own. There is nothing
to compare a skill change or a version change against, which is exactly what
the human wanted the comparison for.

WHAT IT COSTS THE RUN: nothing measurable. Two Python scripts read files that are
already on disk. No agent is spawned, no database is read, no repository is
touched beyond appending one row.

IT CANNOT HALT A RUN. Every failure below is caught and printed as a line in the
output. The human ruled on 2026-08-30 that nothing stops a run for their input, and a
measurement that could break a finale would be worse than no measurement.

    python3 run_costs.py --issues 9 --note "first run with the two new hooks"

## Finding the transcript, and why the old rule could not work

It used to be "the newest `.jsonl` under this working directory's project slug",
on the reasoning that the run holds the worktree. **Run `batch-88624c` disproved
it on 2026-08-31.** The finale ran this from the MAIN checkout rather than the
run's worktree, and that checkout's slug directory held 64 transcripts from
months of unrelated sessions. It picked one of those: a wall clock of 1.01 h for an 8.4 h
run, with a longest step of "Gather week git activity", which this run never ran.
The row it appended was wrong in every timing column and nothing in the script
could tell.

The rule now needs a RUN NAME, and every path to one ends in a check:

  1. `--run <name>`, which the finale knows and states.
  2. otherwise the current directory's own branch, when it reads
     `claude/run-issues-<name>`.
  3. otherwise nothing. It refuses and lists the run worktrees it can see.

The name then selects one project directory, and **the chosen transcript must
contain the run name in its own text** or it is refused. A foreign session cannot
pass that: it never names this run. `batch-88624c`'s own transcript names it 1231
times, and no other transcript in the repository's slug names it at all.

**An unverified transcript appends NO row.** The old code appended one anyway,
with `not read` in the cells it could not fill, and the cells it filled wrongly
looked exactly like the cells it filled rightly.
"""

import argparse
import datetime
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
LEDGER = ".scratch/workflow-audit/run-costs.md"

HEADER = """# What each run cost itself

One row per run, appended by `run_costs.py` at the finale. A row is written by the
machine, never by hand, because two of the five runs to 2026-08-20 had no row when
the table was kept by hand.

Compare a row against the row above it to read what a skill change or a version
change did. The issue mix is NOT controlled here, so a difference of a few per cent
is the batch, not the change.

| Taken | Version | Issues | Hours | Weighted | Per issue | Subagents | Orchestrator | Idle | Note |
|---|---|---|---|---|---|---|---|---|---|
"""


def last_stamp(path: pathlib.Path) -> str:
    """The newest timestamp inside a transcript, or "" if it holds none.

    Modification time is NOT a proxy for this and the drill proved it: on
    2026-08-30 the newest file by mtime in the main checkout's project directory
    held records from 2026-07-27, because a file can be rewritten long after its
    last turn.
    """
    newest = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                found = re.search(r'"timestamp"\s*:\s*"([^"]+)"', line)
                if found and found.group(1) > newest:
                    newest = found.group(1)
    except OSError:
        return ""
    return newest


RUN_BRANCH = re.compile(r"^claude/run-issues-(?P<run>.+)$")


def run_name(cwd: pathlib.Path):
    """This run's name, from the branch checked out where this is running.

    A run works on `claude/run-issues-<name>` in a worktree of that name, so the
    branch IS the identity. Reading it from `git worktree list` instead would be
    ambiguous the moment two run worktrees exist, and three did on 2026-08-31.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=30)
    except Exception as error:
        return None, f"git could not be run in {cwd}: {error}"
    if done.returncode != 0:
        return None, f"{cwd} is not a git working tree"
    found = RUN_BRANCH.match(done.stdout.strip())
    if not found:
        return None, (
            f"the branch here is `{done.stdout.strip()}`, which is not a run branch. "
            "Pass --run <name>, or run this from the run's own worktree."
        )
    return found.group("run"), ""


def worktrees_seen(cwd: pathlib.Path) -> list:
    """Every run branch this repository can see, for a refusal that helps."""
    try:
        done = subprocess.run(["git", "-C", str(cwd), "worktree", "list"],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return []
    return [found.group("run")
            for line in done.stdout.splitlines()
            for found in [re.search(r"\[claude/run-issues-(?P<run>[^\]]+)\]", line)]
            if found]


def names_the_run(path: pathlib.Path, run: str) -> bool:
    """Does this transcript name the run it claims to be?

    The check a foreign session cannot pass. It is a substring scan of a file
    already on disk and costs milliseconds.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            return any(run in line for line in handle)
    except OSError:
        return False


def transcript(run: str):
    """The transcript of the named run, or a refusal saying why not."""
    directories = [d for d in PROJECTS.glob(f"*run-issues*{run}*") if d.is_dir()]
    if not directories:
        return None, f"no transcript directory under {PROJECTS} names run `{run}`"
    if len(directories) > 1:
        listed = ", ".join(sorted(d.name for d in directories))
        return None, f"run `{run}` matches more than one transcript directory: {listed}"
    directory = directories[0]
    files = list(directory.glob("*.jsonl"))
    if not files:
        return None, f"no .jsonl transcript under {directory}"
    dated = [(last_stamp(f), f) for f in files]
    dated = [(stamp, f) for stamp, f in dated if stamp] or [("", f) for f in files]
    dated.sort()
    chosen = dated[-1][1]
    if not names_the_run(chosen, run):
        return None, (
            f"{chosen} never names run `{run}`, so it is a different session that "
            "happened to sit in the same directory. Nothing was read and no row "
            "was appended."
        )
    return chosen, ""


def run(args: list) -> str:
    """Run one reading. A failure becomes text, never an exception."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=300)
    except Exception as error:
        return f"(this reading failed: {error})"
    if done.returncode != 0:
        return f"(this reading exited {done.returncode})\n{done.stderr.strip()}"
    return done.stdout.rstrip() or "(this reading printed nothing)"


def number(pattern: str, text: str, cast=float):
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return cast(match.group(1).replace(",", ""))
    except ValueError:
        return None


def append_row(repo: pathlib.Path, row: str) -> str:
    path = repo / LEDGER
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(HEADER, encoding="utf-8")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(row + "\n")
    except OSError as error:
        return f"the row was NOT appended: {error}"
    return f"appended to {LEDGER}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issues", type=int, default=0)
    parser.add_argument("--note", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--transcript", default="",
                        help="an explicit path, still checked against the run name")
    parser.add_argument("--run", default="",
                        help="the run's own name, e.g. batch-88624c; derived from "
                             "the branch when this runs in the run's worktree")
    parser.add_argument("--days", type=int, default=2,
                        help="window for orchestrator_cost.py; 2 covers a run "
                             "that started yesterday and ended today")
    parser.add_argument("--no-append", action="store_true")
    args = parser.parse_args(argv)

    cwd = pathlib.Path.cwd()
    this_run, why = (args.run, "") if args.run else run_name(cwd)

    print("## What this run cost\n")
    if not this_run:
        print(f"NO READING TAKEN: {why}")
        seen = worktrees_seen(cwd)
        if seen:
            print(f"Run worktrees this repository can see: {', '.join(sorted(seen))}.")
        print("\nThis is a missing measurement, not a failed run. Carry on.")
        return 0

    if args.transcript:
        path = pathlib.Path(args.transcript)
        why = "" if names_the_run(path, this_run) else (
            f"{path} never names run `{this_run}`. A transcript given by hand is checked "
            "the same way one this script chose would be."
        )
        if why:
            path = None
    else:
        path, why = transcript(this_run)

    if path is None:
        print(f"NO READING TAKEN for run `{this_run}`: {why}")
        print("\nThis is a missing measurement, not a failed run. Carry on.")
        print("NO ROW WAS APPENDED. A row from a transcript this could not identify "
              "is worse than no row: run `batch-88624c` appended one on 2026-08-31 "
              "reading 1.01 h for an 8.4 h run.")
        return 0
    print(f"Run: `{this_run}`. Transcript read: `{path}`, which names the run.\n")

    cost = run([sys.executable, str(HERE / "orchestrator_cost.py"), "--days", str(args.days)])
    timings = run([sys.executable, str(HERE / "run_timings.py"), str(path)])

    print("### Orchestrator share, this run\n")
    print("```\n" + cost + "\n```\n")
    print("### Where the clock went, per step\n")
    print("```\n" + timings + "\n```\n")

    # run_timings.py's own three header lines, and nothing else.
    hours = number(r"wall clock\s+([\d.,]+)\s*h", timings)
    idle_h = number(r"nobody running\s+([\d.,]+)\s*h", timings)
    idle = f"{100 * idle_h / hours:.0f}%" if hours and idle_h is not None else None

    # orchestrator_cost.py's LAST data row, which is the most recent run — the
    # one that has just ended. Its columns are ended, issues, agents, weighted,
    # orchestrator share, per issue.
    rows = re.findall(
        r"^(\d{4}-\d{2}-\d{2})\s+(\d+)\s+(\d+)\s+([\d.]+M)\s+(\d+)%\s+([\d.]+M)",
        cost, re.M)
    tokens = agents = share = per_issue = None
    if rows:
        _, counted, agents, tokens, share, per_issue = rows[-1]
        agents = int(agents)
        share = share + "%"
        if not args.issues:
            args.issues = int(counted)

    def show(value, suffix=""):
        if value is None:
            return "not read"
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return f"{value:,}{suffix}"
        return f"{value:g}{suffix}"

    stamp = datetime.date.today().isoformat()
    row = (
        f"| {stamp} | {args.version or 'not stated'} | {args.issues or 'not stated'} "
        f"| {show(hours)} | {show(tokens)} | {show(per_issue)} | {show(agents)} "
        f"| {show(share)} | {show(idle)} | run `{this_run}`. {args.note or '—'} |"
    )
    print("### The row for the comparison table\n")
    print(row)
    if args.no_append:
        print("\n(not appended: --no-append)")
    else:
        print("\n" + append_row(cwd, row))
    print(
        "\nAny cell reading `not read` means this script could not find that figure "
        "in the output above. The output above is the measurement; the row is a "
        "convenience. Do not halt for a `not read` cell."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
