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
The human wanted the comparison for.

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
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

import model_map
import pipeline_fingerprint
import run_records


def _module(name):
    """Load a sibling script by path. One instance per file, whoever loads it:
    two would diverge on any module state, and a caller pointing one of them at
    a different transcript root would be patching a copy nobody reads."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    existing = sys.modules.get(name)
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_session():
    """`run_session.py` owns the road from a batch id to a session, and the
    per-model accounting the four cost scripts share (ticket 39, ruling 12)."""
    return _module("run_session")

HERE = pathlib.Path(__file__).resolve().parent
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
# The view's path lives in `run_records.VIEW`, which owns both record files
# and the page rendered from them. A second copy here is the drift that took
# `journal_for` in ticket 39 sitting 2 and `read_transcript` in sitting 3.

# The version cell holds the Claude Code version and nothing else (ruling 10).
# It is MEASURED here rather than typed, because `finale.md` asks an agent for
# `--version <cc-version>` and on 2026-08-30 an agent typed the model:
# `claude-opus-5` is in the live table's version column today.
def read_cc_version():
    """`claude --version`, or "" when it cannot be read. Never raises."""
    try:
        done = subprocess.run(["claude", "--version"], capture_output=True,
                              text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def quality_counts(ledger_text, spans=None, orphans=None):
    """Ruling 6's four counts and the denominator beside them.

    **This is the reading sitting 2 refused to take**, and ruling 28 is why:
    `run_quality.issue_quality` graded 12 rows for the six-issue run
    `batch-170a59`, because `check_commit_order.status_rows` accepted any table
    row on the page whose first cell held an issue id. Sitting 3 bounded that
    reader to the table whose header declares `issue`, so the denominator is
    now the run's own issue count and every rate over it is true.

    **Two sources, and losing one costs only what came from it.** Three counts
    are the ledger's; escalations are the transcript's, by role name (ticket 39
    ruling 21.3 -- the ledger records what was ASKED for). A run whose ledger
    could not be read carries five nulls, never five zeros: a run with no
    strikes is a fact, and a run whose strikes were never read is not.

    **`orphans` is not optional bookkeeping and the review of 2026-09-06 is
    why.** `estimate_accuracy.actuals` returns it as the census that makes a
    silent loss impossible -- 30 per-issue spawns went into run `batch-88624c`
    and 18 came out booked to the wrong issue. Reading `spans` alone made an
    empty map mean "no issue was named", so a transcript whose spawns were ALL
    unattributed recorded `escalations: 0`: a measured zero for a figure
    nothing read, written by the sitting whose whole purpose is to end those.
    One orphan is enough to refuse the figure, because the escalation may be
    the spawn that was lost.
    """
    rows = _module("run_quality").issue_quality(ledger_text or "")
    if not rows:
        return {name: None for name in run_records.QUALITY_FIELDS}
    measures = _module("run_measures")
    counted = spans is not None and not orphans
    return {
        "issues_graded": len(rows),
        "first_attempt_passes": sum(
            1 for one in rows if one.first_attempt == "pass"),
        "correction_rounds": sum(one.corrections for one in rows),
        "strikes": sum(one.strikes for one in rows),
        "escalations": sum(
            1 for one in rows
            if measures.ESCALATED in ((spans.get(one.issue) or {}).get("roles")
                                      or ())) if counted else None,
    }


def trial_record(journal_text):
    """Ruling 22's verdict, as three numbers and a word. Ticket 39 sitting 4.

    **That sitting handed this ticket one line and nothing carried it.** Its
    decision ledger reads "the merge briefing alone, with the answer behind one
    function `trial_verdict` ... Ticket 37 calls the same function", and
    sittings 2, 3 and 4 all passed it. So the VOID mark ruling 22 raises has
    lived only in a briefing, which nothing reads across runs -- the exact
    shape this ticket exists to end.

    The verdict is READ and never re-derived, so the briefing and this line
    cannot answer differently. `mismatches` is stored as a COUNT: the verdict
    carries whole journal lines naming a role and a model, and a sentence in a
    field a reader counts would travel into every future reading of the file.
    """
    verdict = _module("run_quality").trial_verdict(journal_text or "")
    return {"state": verdict.state, "spawns": verdict.spawns,
            "proved": verdict.proved, "mismatches": len(verdict.mismatches)}


def build_record(batch, kind, version="", note="", ledger_text="",
                 version_reader=None, spans=None, orphans=None, stamped=None,
                 agent_steps=None, idle_hours=None, agent_hours=None,
                 issue_lines=None, journal_text="", **figures):
    """One per-run line, ready for `run_records.append_run`.

    Pure apart from `version_reader`, so every field can be tested without a
    transcript, a ledger or a git repository.

    The fingerprint is COPIED off the ledger header, never re-measured here
    (ruling 23). The finale runs days after the launch and in a different tree,
    so a fresh `git rev-parse` would record what the pipeline is now rather
    than what ran, which is the whole value of the field.
    """
    reader = version_reader or read_cc_version
    stated = version or reader() or run_records.NOT_STATED

    marks = pipeline_fingerprint.from_ledger(ledger_text)
    models = model_map.ledger_map(ledger_text) or {}
    efforts = model_map.ledger_efforts(ledger_text) or {}

    record = {
        "batch": batch,
        "kind": kind,
        "taken": datetime.date.today().isoformat(),
        "version": stated,
        "note": note,
        "orchestrator_model": model_map.orchestrator_cell(ledger_text),
        "worker_models": model_map.worker_cell(models, efforts),
        "fingerprint": pipeline_fingerprint.as_record(marks),
        # Ruling 6, filled by sitting 3 now that the reader is repaired.
        "quality": quality_counts(ledger_text, spans, orphans),
        # Ruling 22, by way of ticket 39 sitting 4. Sitting 5 wires it.
        "trial": trial_record(journal_text),
    }
    record.update({name: value for name, value in figures.items()
                   if value is not None})

    # Rulings 5 and 21. The per-issue population these divide by is the GRADED
    # count rather than `figures["issues"]`: a row the reader could not grade
    # has no span and no estimate, so dividing by it would flatter every
    # per-issue figure on the line.
    #
    # **`issue_lines` is passed IN, and the review of 2026-09-06 is why.** This
    # built its own with no briefing and no git, while `report` built a second
    # set with both. They agree today because `faster` reads only the estimate
    # and the span, and they would stop agreeing the moment a faster figure
    # drew on a briefing-sourced field -- one run, two populations, nothing
    # comparing them.
    measures = _module("run_measures")
    if issue_lines is None:
        issue_lines = measures.issue_records(
            batch=batch, ledger_text=ledger_text or "", spans=spans)
    record["faster"] = measures.faster(
        issue_lines,
        wall_hours=record.get("hours"),
        idle_hours=idle_hours,
        agent_hours=agent_hours)
    record["longest_steps"] = measures.longest_steps(stamped, agent_steps)
    return record



def cache_reading(probed):
    """`{read, written, ratio}` for a run, or None. Ticket 37, ruling 14.

    **The figure was printed at every finale and stored on no line.** The
    ticket's facts of 2026-09-05 list `cache_probe.py:113`'s read-to-write
    ratio under "Printed and not stored", and sitting 4 builds ruling 14's one
    threshold, which cannot fire over a field nothing writes.

    The arithmetic is `cache_probe.report`'s own, including its filter on
    subagents that hold usage rows: two readers of one quantity that disagree
    are worse than one, and this must answer what the finale prints.

    Pure. `report` does the probing, so this can be measured without a
    transcript.
    """
    agents = [one for one in (probed or {}).get("agents") or ()
              if one.get("rows")]
    if not agents:
        return None
    written = sum(one.get("written") or 0 for one in agents)
    read = sum(one.get("read") or 0 for one in agents)
    # Null, never zero: a ratio of zero would fire ruling 14's floor on a run
    # whose cache nobody could read.
    ratio = round(read / written, 2) if written else None
    return {"read": read, "written": written, "ratio": ratio}


def probe_cache(path):
    """The fleet cache reading for one run's transcript, or None.

    Never raises: a measurement that could break a finale would be worse than
    no measurement (the human, 2026-08-30).
    """
    try:
        return cache_reading(_module("cache_probe").probe(
            pathlib.Path(path).with_suffix("")))
    except Exception:  # noqa: BLE001 - a reading never raises
        return None


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


def in_process(call) -> str:
    """Take one reading in this process. A failure becomes text, as `run` does.

    Used for the batch reading, which `orchestrator_cost.py` already holds in
    memory: a subprocess would re-walk every transcript on the machine to
    answer a question this process has already answered, and could not be told
    where the transcripts are.

    The guarantee is unchanged and it is the important part. The human ruled on
    2026-08-30 that nothing stops a run for their input, and a measurement that
    could break a finale would be worse than no measurement.
    """
    import contextlib
    import io

    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            call()
    except Exception as error:  # noqa: BLE001 - a measurement never raises
        return (out.getvalue() + f"\n(this reading failed: {error})").strip()
    return out.getvalue().rstrip() or "(this reading printed nothing)"


def run(args: list) -> str:
    """Run one reading in a subprocess. A failure becomes text, never an exception."""
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


def append_record(repo: pathlib.Path, record) -> str:
    """Append the line, then regenerate the view. Never raises, never halts.

    Ruling 4 refuses a second line for a batch already present, which is ticket
    36's fault 9. The refusal is PRINTED and the finale carries on: a
    measurement that could break a finale would be worse than no measurement
    (the human, 2026-08-30).
    """
    ok, why = run_records.append_run(repo, record)
    if not ok:
        return why
    seen = run_records.read_runs(repo)
    _, said = run_records.write_view(repo)
    note = f"{why}; {said}"
    if seen.damaged:
        note += (f"\n{len(seen.damaged)} line(s) of {run_records.RUNS} could "
                 "not be parsed and are NOT in the view. Read them by hand.")
    return note


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
    parser.add_argument("--batch", default="",
                        help="a run or hunt batch id. The ledger names the "
                             "worktree and the worktree names the transcripts, "
                             "so nothing depends on what the worktree is called "
                             "(ticket 39, ruling 12). Prefer this to --run.")
    parser.add_argument("--repo", default="",
                        help="checkout whose worktrees hold the ledger")
    parser.add_argument("--days", type=int, default=2,
                        help="window for orchestrator_cost.py; 2 covers a run "
                             "that started yesterday and ended today")
    parser.add_argument("--kind", default="run", choices=sorted(run_records.KINDS),
                        help="ruling 11: a run and a hunt share these files, "
                             "and ruling 12 compares a line against the "
                             "previous line of the SAME kind")
    parser.add_argument("--no-append", action="store_true")
    args = parser.parse_args(argv)

    cwd = pathlib.Path.cwd()
    session = _run_session()

    # `--batch` is the road ruling 12 asks for and it needs no worktree name.
    # `--run` stays because `finale.md` passes it, and because a hand reading
    # of a run whose ledger is gone still has to work.
    spawns = []
    if args.batch:
        mains, why = session.sessions_for_batch(args.batch, repo=args.repo or None)
        if not mains:
            print("## What this run cost\n")
            print(f"NO READING TAKEN for batch `{args.batch}`: {why}")
            print("\nThis is a missing measurement, not a failed run. Carry on.")
            print("NO ROW WAS APPENDED. A row from a transcript this could not "
                  "identify is worse than no row: run `batch-88624c` appended "
                  "one on 2026-08-31 reading 1.01 h for an 8.4 h run.")
            return 0
        this_run, path = args.batch, pathlib.Path(mains[-1])
        spawns = session.spawn_rows(mains)
        print("## What this run cost\n")
        print(f"Batch `{this_run}`. {len(mains)} session(s) read; "
              f"timings from `{path}`.\n")
        return report(args, session, this_run, path, spawns, cwd, mains=mains)

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
    return report(args, session, this_run, path, session.spawn_rows([str(path)]), cwd)


def _by_model(session, spawns, field):
    """`{model: value}` for one field, models the run did not use left out.

    Raw, not rendered. Ruling 5 says record everything and show everything;
    `run_records.render_view` does the showing, so the record keeps figures a
    later reader can do arithmetic on. The old code stored the rendered string
    `opus 149.7M / fable 0.3M` and nothing could ever divide it.
    """
    found = session.by_model(spawns)
    real = {m: v for m, v in found.items() if m not in session.NOT_A_MODEL}
    if not real:
        return None
    return {session.tier_of(model) or model: slot[field]
            for model, slot in real.items()}


def _per_issue_by_model(session, spawns, issues):
    if not issues:
        return None
    found = _by_model(session, spawns, "weighted")
    return {m: v / issues for m, v in found.items()} if found else None


def _share_by_model(session, mains, spawns):
    if not mains:
        return None
    orchestrator = {}
    for one in mains:
        for model, weighted in session.main_thread_by_model(one).items():
            orchestrator[model] = orchestrator.get(model, 0.0) + weighted
    shares = {m: v for m, v in session.share_by_model(orchestrator, spawns).items()
              if m not in session.NOT_A_MODEL}
    if not shares:
        return None
    return {session.tier_of(m) or m: v for m, v in shares.items()}


def issues_for(typed, session, spawns):
    """How many issues this run shipped, or None. Never the week window.

    The one place the count is decided, so that a test can hold it. Until
    2026-09-06 `run_costs.py` took it from `orchestrator_cost.py --days 7`'s
    LAST data row, whatever run that row described, and wrote it as this run's
    own; `aa94b3b` closed that on the `--batch` road and `finale.md` still
    keeps the `--run` road "for a run whose ledger is gone", where the week
    window is still what gets read.

    So: a number typed by hand, else this batch's own spawns, else None. A null
    is a missing measurement. A borrowed number is a wrong one that reads
    exactly like a right one, and seventeen of the eighteen lines carried into
    `runs.jsonl` on 2026-09-06 are marked `borrowed` because of it.
    """
    if typed:
        return typed
    return session.issue_count(spawns) or None if spawns else None


def report(args, session, this_run, path, spawns, cwd, mains=None):
    """The whole reading, and the one row it appends.

    With a batch id the orchestrator reading is THIS batch, not the week
    window. The window exists to state what OTHER runs cost at each batch size,
    which is a launch-time question; reading it here made the appended row
    borrow another run\'s issue count, its agent count and its share -- and on
    2026-09-06 it borrowed all three from a fifteen-issue run into a two-spawn
    fixture without a word.
    """
    if mains:
        orchestrator = _module("orchestrator_cost")
        cost = in_process(
            lambda: orchestrator.report_batch(this_run, repo=args.repo or None))
    else:
        cost = run([sys.executable, str(HERE / "orchestrator_cost.py"),
                    "--days", str(args.days)])
    timings = run([sys.executable, str(HERE / "run_timings.py"), str(path)])

    print("### Orchestrator share, this run\n")
    print("```\n" + cost + "\n```\n")
    print("### Where the clock went, per step\n")
    print("```\n" + timings + "\n```\n")

    # Ruling 15: a model column per role, and one row per subagent carrying
    # role, model, effort, tokens by kind, wall clock and rows.
    print("### What each role ran on, per role and per model\n")
    print("```\n" + session.render_roles(spawns) + "\n```\n")
    print("### One row per subagent\n")
    print("```\n" + session.render_spawns(spawns) + "\n```\n")

    # run_timings.py's own three header lines, and nothing else.
    hours = number(r"wall clock\s+([\d.,]+)\s*h", timings)
    idle_h = number(r"nobody running\s+([\d.,]+)\s*h", timings)
    agent_h = number(r"a subagent running\s+([\d.,]+)\s*h", timings)
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
        # `counted` is deliberately NOT read. See `issues_for`.

    issues = issues_for(args.issues, session, spawns)

    ledger_text, briefing_text, journal_text, stamped = "", "", "", []
    found = session.ledger_for_batch(this_run, repo=args.repo or None)
    if found is not None:
        ledger_text = _text(found.path)
        # `find_live_ledger` owns where a journal sits beside its ledger, and a
        # hunt's is `round-journal.md`. Two hooks each grew their own copy of
        # that answer in ticket 39 sitting 2 and the review of 2026-09-05
        # refused both, so this asks the owner.
        journal_text = _text(
            _module("find_live_ledger").journal_for(found.path))
        # `merge-briefing.md` sits in the run directory beside the ledger
        # (ticket 38, ruling 10). It carries the rail's stage keys and the
        # `## Ruled` section, which are two of ruling 20's five kind facts.
        briefing_text = _text(os.path.join(os.path.dirname(found.path),
                                           "merge-briefing.md"))
        stamped = _module("run_step").read_steps(
            _module("run_step").steps_beside(found.path))

    # The per-issue spans and the role names, off the run's own transcript
    # (ticket 39, ruling 21.3). `None` where nothing was read, so that the
    # figures drawn from it are null rather than zero.
    spans, orphans = None, None
    try:
        spans, orphans = _module("estimate_accuracy").actuals(pathlib.Path(path))
    except Exception as error:
        print(f"The per-issue spans could not be read from {path} ({error}), "
              "so every figure drawn from the transcript is null on this "
              "line. The ledger's own figures are unaffected.\n")
    if orphans:
        print(f"{len(orphans)} per-issue spawn(s) name no issue in their "
              "heading line, so the escalation count is null rather than a "
              "figure: the escalation may be one of the spawns that was "
              "lost.\n")

    # Ruling 17's second file, built ONCE and used by both roads. `build_record`
    # divides ruling 5's figures by this population and the lines themselves go
    # to `issues.jsonl`, so two builds would be one run with two populations.
    issue_lines = _module("run_measures").issue_records(
        batch=this_run,
        ledger_text=ledger_text,
        briefing_text=briefing_text,
        spans=spans,
        touched=_touched(args.repo or str(cwd)))

    record = build_record(
        batch=this_run,
        kind=args.kind,
        version=args.version,
        note=args.note,
        ledger_text=ledger_text,
        journal_text=journal_text,
        spans=spans,
        orphans=orphans,
        issue_lines=issue_lines,
        stamped=stamped,
        agent_steps=_agent_steps(session, spawns),
        idle_hours=idle_h,
        agent_hours=agent_h,
        issues=issues,
        hours=hours,
        weighted=_by_model(session, spawns, "weighted"),
        per_issue=_per_issue_by_model(session, spawns, issues),
        subagents=len(spawns) if spawns else agents,
        orchestrator=_share_by_model(session, mains, spawns),
        idle=(idle_h / hours) if hours and idle_h is not None else None,
        # Ruling 14's one threshold needs a figure on the line. The finale has
        # printed this at every run since 2026-08-16 and stored it on none.
        cache=probe_cache(path),
    )

    print("### The line for the comparison record\n")
    print("```json\n" + json.dumps(record, indent=2, sort_keys=True) + "\n```\n")
    if issue_lines:
        print(f"### The {len(issue_lines)} per-issue line(s)\n")
        print("```json\n"
              + "\n".join(json.dumps(one, sort_keys=True) for one in issue_lines)
              + "\n```\n")
    if args.no_append:
        print("(not appended: --no-append)")
    else:
        # **The issue lines go FIRST, and the order is the fix.**
        # `append_record` regenerates the view as its last act, so appending
        # the per-run line first published a page whose per-issue table was
        # missing the run that had just finished, and a second render was
        # needed to repair it. One render, and it is the correct one.
        ok, message = run_records.append_issues(cwd, issue_lines)
        print(message)
        if not ok:
            print("The per-run line below still stands. A refusal here costs "
                  "the per-issue population of ONE run and halts nothing.")
        print(append_record(cwd, record))
    print(
        "\nAny field reading `null` means nothing measured it -- not that it "
        "was zero. A run\nwith no strikes is a fact; a run whose strikes were "
        "never read is not, and the two\nmust not read alike. The output above "
        "is the measurement and the line is a\nconvenience. Do not halt for a "
        "null."
    )
    return 0


def _text(path):
    """A file's text, or "". Never raises: every caller here is measuring."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _agent_steps(session, spawns):
    """Every subagent spawn as a step, for ruling 21's join.

    The KIND of an agent step is its role, which is what makes "the longest
    step by kind" answer the human's stated use: a two-hour citation pass and a
    two-hour verify gate are different kinds of slow.
    """
    return [{"kind": one.role or one.agent_type,
             "seconds": one.seconds,
             "label": one.description or ""}
            for one in spawns or ()]


def _touched(repo):
    """A callable answering "what paths did this sha change", or None.

    Injected rather than called inline so that `run_measures` stays pure and
    testable without a repository. It answers None on any failure, and
    `_migration` turns that into a null: a repository git cannot read has not
    told us the commit held no migration.
    """
    def paths(sha):
        try:
            done = subprocess.run(
                ["git", "-C", str(repo), "show", "--name-only",
                 "--format=", sha],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        return [line.strip() for line in done.stdout.splitlines() if line.strip()]
    return paths


if __name__ == "__main__":
    sys.exit(main())
