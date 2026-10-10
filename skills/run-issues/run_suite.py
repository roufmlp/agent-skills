#!/usr/bin/env python3
"""Run the whole suite once per tree: log it, hash the tree, refuse a repeat.

    python3 ~/.claude/skills/run-issues/run_suite.py --stage issue -- <the suite command>

Fix F4 of a run-time audit of 2026-09-23: `the suite runs through one wrapper`.

## Why

Four runs on one project spent 665 minutes on 206 whole suites. Implementers
ran 128 of them, and 62 of those re-ran a tree that had not changed: 202
minutes. About 50 were `rm -rf .vitest-cache && npm test` with no reason given,
and 9 re-ran because the first output had gone through `grep` or `tail` and the
line wanted was gone. So the output is kept here, whole, and a tree that ran
green once is not run again.

## What it does

0. Takes the machine's whole-suite lock (`take_lock`), so a second
   whole suite anywhere on the machine waits for this one. The record keeps
   when the suite asked (`asked`), the seconds it waited (`waited`), whether
   another suite held the lock (`lock`: free, held or none) and that suite's
   pid (`lock_holder`). `started` is when the suite itself started.
1. Hashes the tree the suite is about to read (`tree_hash`), `.scratch/` left
   out. Refuses, exit 3, a harness contract it cannot place (`harness_contract`).
2. Refuses, exit 3, when a green record for that tree and that stage exists,
   and prints that run's log path. A `baseline` is refused after any green
   baseline in this tree, whatever the hash: a run takes one.
3. Runs the command from an argument list, never a shell, with the whole
   output going to a log, and with coverage where it can read the command
   (`with_coverage`); the report is kept beside the log (`keep_report`).
4. Runs the repo's harness suite after it where one is owed (`run_harness`),
   and rechecks a red harness reading as it rechecks a red whole suite.
5. Prints vitest's summary lines, the failing files, the log's path and the
   report's, and appends one record, with the tree the suite left as
   `tree_after`. The exit is the suite's, or the harness suite's where the
   suite was green.

At `issue` the call names its spawn, `--spawn logic` or `--spawn final`, and
both are refused where the scoped road can run (`issue_refusal`):

- `logic`, always. Where a runner gives a screen issue's first attempt two
  spawns, a logic spawn and then a screen spawn, the screen spawn runs the
  whole suite on the tree the gates read. The logic spawn's suite is read by nobody.
- `final`, until the newest `scoped` record for this tree is green, or `wide`:
  `scoped_suite.py --whole-if-wide` runs nothing where the change reaches more
  than half the suite, since its scoped suite would cost a whole one. The
  whole suite runs once, on a tree the scoped road has passed or found wide.

One run on one project (2026-10-06) ran 12 whole suites in 47.5 minutes
on two screen issues. The logic spawns' suites took 23.7 of them. Four reds took
15.6, and each failed in the repo-wide checks or a test importing the change,
which the scoped road runs in about a minute and a half. A tree with no
`node_modules/.bin/vitest` has no scoped road, and `final` runs there.

A red whole suite re-runs only its failing files, one after another, with no
coverage (`recheck`), where it names at most `RECHECK_CAP` of them and the
command is one this wrapper can name files to. A file that passes there is a
flake: the call is green, the record names it under `flaky`, and the
repository's flake ledger (`run-suite-flakes.jsonl` in the git common
directory, the run tree's for a gate's copy) gains a line. `flake_report.py`
reads the ledger. A file that fails alone too keeps the call red. Nine flaky
reds cost 34.5 minutes of whole-suite re-runs in the three suite stores on disk
on 2026-10-06, and 42 run records name a flake (the human, 2026-10-06). The recheck
takes seconds and runs under the same machine lock.

A red harness reading takes the same recheck, through the contract's command
(`harness_args`): a file that passes alone is a flake, and the harness reading
is green. The human, 2026-10-11, changing a ruling of 2026-10-05. One project's
`tests/views/home-badge-time.test.ts` reds under two parallel runs (594 ms
against a 450 ms bound), and each such red re-ran all 453 harness files. Each
ledger line names its `suite`, `app` or `harness`.

At `verify` and `correction` it may answer without a run. The perf audit of
2026-09-28 (one project, `.scratch/workflow-audit/perf-audit-2026-09-28/`)
counted 4 to 9 whole suites per full issue:

- `verify` answers with the implementer's newest `issue` record for the same
  tree, red or green, where it kept a report (`reusable`, `reuse`), and
  refuses a copy `make_copy.py` did not make.
- `correction` refuses the whole suite when the correction changed test files
  only, and names `scoped_suite.py` (`correction_refusal`).

A red run is never refused, so a flake can be re-run.

## The stages, and whose each one is

`issue` is an implementer's. `baseline`, `correction` and `finale` are the
runner's: before spawn 1, the coverage re-run `SKILL.md` step 5 orders after a
correction round, and `finale.md` step 1. `verify` is the verify gate's, in the copy
`make_copy.py` made. `scoped` is `scoped_suite.py`'s, which writes to the
same store. The refusal is per stage, so a finale that reads the
tree the last implementer read is not refused here.
`~/.claude/hooks/run-issues-suite-gate.py` is what holds each caller to its
own stages and refuses a whole suite that does not come through this file.

## Where it writes

`run-suite/` in the worktree's own git directory (`git rev-parse --git-path
run-suite`): `records.jsonl`, one JSON line per run, and `logs/`. `git status`
never sees it, and every worktree has its own.

A gate's copy is a `git clone --shared` (`make_copy.py`), so it has a store of
its own, and `git config run-suite.source` names the run tree whose store the
`verify` stage reads. A directory outside git is refused: an rsync copy without `.git`, which this
file once read, made 11 git tests red in every verify suite, and it is gone.

Each record keeps its coverage report under `coverage/<log stem>/`, so the next
suite in the tree cannot overwrite the report an earlier record names.

## Exit codes

The command's own, passed through, or the harness suite's where the suite was
green; at a reused `verify`, the reused record's. 3 is this wrapper's refusal:
a repeat on a green tree, a tree git could not read, a copy `make_copy.py` did
not make, a test-only correction, a harness contract it cannot place, or an
`issue` call that names no spawn, the logic spawn, or a tree the scoped road
has not passed. 127 is
a command that could not start.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import fcntl
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

STAGES = ("issue", "baseline", "correction", "finale", "verify")
# Stage `issue` names which spawn calls. `logic`: the first of a screen issue's
# two. `final`: every spawn that hands its tree to the gates.
SPAWNS = ("logic", "final")

# The lines of vitest's own footer that the summary prints. The rest of the
# output is in the log.
SUMMARY_MARKS = ("Test Files", "Tests ", "Duration")

RECORDS = "records.jsonl"

# Where a run keeps its state in the tree. Never part of the hash.
RUN_STATE = (".scratch",)

# What `with_coverage` adds to a suite it can read. `reportOnFailure` because
# vitest writes no report at all when a test fails, and most suites are red.
COVERAGE_FLAGS = ("--coverage.enabled", "--coverage.reporter=json",
                  "--coverage.reportOnFailure=true")
REPORT = "coverage-final.json"

# The recheck: at most this many failing files, run one after another.
RECHECK_CAP = 5
RECHECK_FLAGS = ("--no-file-parallelism",)
FLAKES = "run-suite-flakes.jsonl"

# A test module the scoped road can find: a test file by its name, or a script
# module under a test or end-to-end directory, which tests import. Not a
# fixture: a test reads one with `fs`, no import graph holds that read, and
# the scoped road would not run the test. The perf audit of 2026-09-28, fix 3.
TEST_PATH = re.compile(
    r"\.(test|spec)\.[cm]?[jt]sx?$|(^|/)(tests?|__tests__|e2e)/(?!(.*/)?fixtures/)"
    r".*\.[cm]?[jt]sx?$")
SCOPED = "python3 ~/.claude/skills/run-issues/scoped_suite.py"

# A project's harness contract (ruled 2026-09-28), where it has one: the
# `harnessSuite` key of this file names a command and `requiredWhen`, the paths
# whose change makes it required. Each entry is a repository-relative file, or
# a directory ending in `/**`.
CONTRACT = pathlib.PurePath(".claude") / "run-isolation.json"
# The stages that run the harness when the diff touches a named path. The
# finale runs it every time; the baseline reads main, which needs no reading.
HARNESS_STAGES = ("issue", "verify", "correction", "scoped")

# `make_copy.py` writes the run tree's path here, in the copy's git config.
SOURCE_KEY = "run-suite.source"
MAKE_COPY = ("python3 ~/.claude/skills/run-issues/make_copy.py --tree <the run "
             "worktree> --dest <a path naming the issue and your role>")
VITEST = {"vitest", "vitest.mjs"}
PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
LAUNCHERS = {"npx", "pnpx", "bunx", "node", "nohup", "time", "caffeinate"}

# One whole suite at a time on the machine. The environment variable
# points the lock elsewhere; `test_run_suite.py` sets it in every case, since the
# outer wrapper holds the real lock while the whole suite runs that file.
LOCK_ENV = "RUN_SUITE_LOCK"


def lock_path() -> pathlib.Path:
    """One path outside every tree, the same whatever directory calls. `/tmp`
    and not `tempfile.gettempdir()`: a sandboxed session can carry its own
    `TMPDIR`, and two sessions must meet on one file. The uid keeps another
    user's lock file, which this one could not open, out of the way."""
    override = os.environ.get(LOCK_ENV)
    return pathlib.Path(override) if override else pathlib.Path(f"/tmp/run-suite-{os.getuid()}.lock")

# The wrapper's own refusal. vitest exits 1 on a red suite, so 3 is never read
# as a suite result.
REFUSED = 3

# A command that never started, the shell's own number for it, and the one
# `run_step.py` uses.
COULD_NOT_START = 127

ANSI = re.compile(r"\x1b\[[0-9;]*m")
# The file must end in a script extension. A test's own drill can print
# `FAIL  <a sentence> > <case>`, and a sentence is not a file.
FAIL_LINE = re.compile(
    r"^\s*FAIL\s+(?:\|[^|]*\|\s+)?(.+?\.[cm]?[jt]sx?)(?:\s+>\s|\s+\[\s|\s*$)")


def git(tree, *args, env=None):
    return subprocess.run(["git", "-C", str(tree), *args], check=True,
                          capture_output=True, text=True, env=env).stdout.strip()


def tree_hash(tree: pathlib.Path) -> str:
    """The tree the suite is about to read: tracked changes and untracked files
    that are not ignored.

    `git stash create` is the audit's suggestion and it misses untracked files,
    and an implementer's new test file stays untracked until the runner commits
    it. So the tree is staged into a THROWAWAY index, a copy of the real one so
    its stat cache spares a re-read of every file, and read back with
    `git write-tree`. The real index is never touched. `RUN_STATE` is left
    out: the run's ledger, primer and verdicts live there, the runner and the
    gates write them after the implementer's suite, and no suite reads them
    (the vitest configs exclude `.scratch/**`). Were they hashed, no verify
    copy would ever match the implementer's record. The cost, stated: a few
    tests read files under `.scratch` (one project's PRD, another's map),
    so a run's own write there does not move the hash. A run edits no
    specification, and the finale's whole suite reads the final tree. The blobs this writes are
    loose objects nothing refers to, and `git gc` takes them.
    """
    real_index = pathlib.Path(git(tree, "rev-parse", "--git-path", "index"))
    if not real_index.is_absolute():
        real_index = tree / real_index
    with tempfile.TemporaryDirectory() as scratch:
        index = pathlib.Path(scratch) / "index"
        if real_index.exists():
            # copy2 and not copyfile: the copy must keep the index's mtime.
            # Git re-hashes an entry no older than the index file, because
            # its stat cannot be trusted; a copy with a NEW mtime makes every
            # entry look trustworthy, and a same-size edit made in the second
            # of the last `git add` then reads as no change.
            shutil.copy2(real_index, index)
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        git(tree, "add", "-A", env=env)
        git(tree, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--",
            *RUN_STATE, env=env)
        return git(tree, "write-tree", env=env)


def locate(cwd: str) -> tuple[pathlib.Path, str, pathlib.Path]:
    """The tree the suite reads, its hash, and the store its records go to: the
    git work tree holding `cwd`, and `run-suite/` in that worktree's own git
    directory. A directory outside git raises, and `main` refuses it: a gate's
    copy is made by `make_copy.py`, which gives it history."""
    tree = pathlib.Path(git(cwd, "rev-parse", "--show-toplevel"))
    return tree, tree_hash(tree), store_of(tree)


def store_of(tree: pathlib.Path) -> pathlib.Path:
    """`run-suite/` in this worktree's own git directory. `git status` never
    sees it, and every worktree has its own."""
    path = pathlib.Path(git(tree, "rev-parse", "--git-path", "run-suite"))
    return path if path.is_absolute() else (tree / path).resolve()


@dataclasses.dataclass
class Queue:
    """What the machine lock cost this suite, for its record.

    `lock` is `free` where no other whole suite held the lock when this one
    asked, `held` where one did and this one waited, and `none` where the
    suite ran without the lock. `holder` is the pid the lock file named when
    this one found it held. The perf audit of 2026-09-28 is why this exists:
    `started` was stamped after the lock was taken, so 28.5 minutes of queue
    across two runs were in no record, and one run's ledger blamed
    "the other run's load" on a suite no other suite held back."""
    asked: datetime.datetime
    waited: float = 0.0
    lock: str = "free"
    holder: str | None = None


def take_lock() -> tuple[int | None, Queue]:
    """Hold the machine's whole-suite lock, waiting as long as it takes.

    An `fcntl.flock` lock: the kernel frees it when its holder dies, even by
    `SIGKILL`, so a lock file naming a dead pid never blocks. The pid written
    here is for the one waiting line and nothing reads it as a lock. The
    descriptor is not inheritable, so the suite never holds the lock itself,
    and it closes, freeing the lock, when this process exits. A lock that
    cannot be opened or taken prints one line and the suite runs without it.
    Returns the descriptor, or None when running without the lock, and the
    `Queue` the record carries."""
    path = lock_path()
    queue = Queue(asked=now())
    began = time.monotonic()
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        print(f"run_suite: could not open the machine lock {path} ({error}); "
              f"running the suite without the lock.", flush=True)
        queue.lock = "none"
        return None, queue
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = os.pread(fd, 32, 0).decode(errors="replace").strip()
            queue.lock, queue.holder = "held", holder or None
            print(f"run_suite: another whole suite holds the machine lock {path}"
                  f" (pid {holder or 'unknown'}); waiting for it.", flush=True)
            fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as error:
        os.close(fd)
        print(f"run_suite: could not take the machine lock {path} ({error}); "
              f"running the suite without the lock.", flush=True)
        queue.lock, queue.holder = "none", None
        return None, queue
    queue.waited = round(time.monotonic() - began, 1)
    os.ftruncate(fd, 0)
    os.pwrite(fd, str(os.getpid()).encode(), 0)
    return fd, queue


def queue_line(queue: Queue) -> str:
    """The one line that says what the lock cost. A ledger that blames another
    run's load cites this line, or has nothing to cite."""
    if queue.lock == "held":
        return (f"run_suite: waited {queue.waited} s for the machine lock, held "
                f"by pid {queue.holder or 'unknown'}.")
    if queue.lock == "none":
        return "run_suite: ran without the machine lock."
    return ("run_suite: the machine lock was free: no other whole suite held it "
            "when this one asked.")


def with_coverage(command: list[str],
                  reports: pathlib.Path) -> tuple[list[str], pathlib.Path | None]:
    """The command to run, and the directory its coverage report will land in,
    or None where this cannot tell.

    The perf audit of 2026-09-28, fix 2: a verify gate reuses the implementer's
    suite only where that suite left a report. A vitest launch, by any path and
    behind `npx` or `node`, takes `COVERAGE_FLAGS` and a directory in this
    store; a package manager's `test` script takes them after one `--`. A
    command that already names a `--coverage` option runs as written, and its
    report is read from its own `reportsDirectory`, `coverage` by default. Any
    other command runs as written and leaves no report: a reading this cannot
    place is never guessed at."""
    named = [word for word in command if word.startswith("--coverage")]
    if named:
        where = next((word.split("=", 1)[1] for word in named
                      if word.startswith("--coverage.reportsDirectory=")), "coverage")
        return list(command), pathlib.Path(where)
    flags = [*COVERAGE_FLAGS, f"--coverage.reportsDirectory={reports}"]
    placed = vitest_args(command, flags)
    return (placed, reports) if placed is not None else (list(command), None)


def vitest_args(command: list[str], extra: list[str]) -> list[str] | None:
    """`command` with `extra` where vitest reads them, or None where this
    cannot tell: after a vitest launch, or after one `--` of a package
    manager's `test` script."""
    words = [pathlib.PurePath(word).name for word in command]
    index = 0
    while index < len(words) and (words[index] in LAUNCHERS
                                  or (index and words[index].startswith("-"))):
        index += 1
    head, rest = words[index:index + 1], words[index + 1:]
    if head and head[0] in VITEST:
        return [*command, *extra]
    if head and head[0] in PACKAGE_MANAGERS and (
            rest[:1] in (["test"], ["t"]) or rest[:2] == ["run", "test"]):
        return [*command, *([] if "--" in command else ["--"]), *extra]
    return None


def harness_args(command: list[str], extra: list[str]) -> list[str] | None:
    """`command` with `extra` where the harness command reads them: where
    `vitest_args` places them, or after one `--` of a package manager's
    `run <script>`. One project's `npm run test:harness` runs
    `scripts/test-harness.mjs`, which takes file names and runs only the
    config that collects them."""
    placed = vitest_args(command, extra)
    if placed is not None:
        return placed
    words = [pathlib.PurePath(word).name for word in command]
    if len(words) >= 3 and words[0] in PACKAGE_MANAGERS and words[1] == "run" \
            and not words[2].startswith("-"):
        return [*command, *([] if "--" in command else ["--"]), *extra]
    return None


def recheck(command: list[str], failing: list[str], log: pathlib.Path,
            place=vitest_args) -> dict:
    """Run only the failing files of a red suite, one after another, with no
    coverage. The module docstring holds the measurement."""
    if len(failing) > RECHECK_CAP:
        return {"run": False, "why": f"{len(failing)} failing files, over the "
                                     f"cap of {RECHECK_CAP}"}
    placed = place(command, [*RECHECK_FLAGS, *failing])
    if placed is None:
        return {"run": False, "why": "the command is not one this wrapper can "
                                     "name files to"}
    began = time.monotonic()
    exit_code, text = run_logged(placed, log)
    return {"run": True, "command": placed, "exit": exit_code,
            "seconds": round(time.monotonic() - began, 1), "log": str(log),
            "failing": failing_files(text)}


def flake_ledger(tree: pathlib.Path) -> pathlib.Path:
    """The repository's flake ledger: in the git common directory, so every
    worktree and every gate's copy of one repository writes one file."""
    source = source_of(tree) or tree
    common = pathlib.Path(git(source, "rev-parse", "--git-common-dir"))
    return (common if common.is_absolute() else source / common).resolve() / FLAKES


def record_flakes(tree: pathlib.Path, names: list[str], entry: dict) -> dict[str, int]:
    """Append one ledger line per flaky file and return each file's count."""
    path = flake_ledger(tree)
    with open(path, "a", encoding="utf-8") as handle:
        for name in names:
            handle.write(json.dumps({"file": name, **entry}) + "\n")
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            name = json.loads(line).get("file")
        except ValueError:
            continue
        counts[name] = counts.get(name, 0) + 1
    return {name: counts.get(name, 0) for name in names}


def keep_report(directory: pathlib.Path | None, started: datetime.datetime,
                kept: pathlib.Path) -> pathlib.Path | None:
    """The run's `coverage-final.json`, inside the store, or None.

    A report older than the run is another run's and is not this one's. One
    written outside the store is copied to `kept`, so the next suite in the
    same tree cannot overwrite the report a record names."""
    if directory is None:
        return None
    report = directory / REPORT
    try:
        if report.stat().st_mtime < started.timestamp() - 1:
            return None
    except OSError:
        return None
    if kept in report.parents:
        return report
    kept.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report, kept / REPORT)
    return kept / REPORT


def after_hash(tree: pathlib.Path) -> str | None:
    """The tree the suite left. Every whole suite of the project the audit
    measured rewrites `tsconfig.json` (the perf audit of 2026-09-28, pair 2,
    section 5), and a copy made after that matches this and not the tree the
    suite started on. None where git cannot read it: the record then matches
    on `tree` alone."""
    try:
        return tree_hash(tree)
    except (subprocess.CalledProcessError, OSError):
        return None


def source_of(tree: pathlib.Path) -> pathlib.Path | None:
    """The run tree a `make_copy.py` copy came from, or None for any other
    tree."""
    try:
        return pathlib.Path(git(tree, "config", "--get", SOURCE_KEY))
    except subprocess.CalledProcessError:
        return None


def reusable(source: pathlib.Path, tree_id: str) -> dict | None:
    """The implementer's newest `issue` record for this tree, where it left a
    coverage report that still exists, or None.

    Any exit is reused, red as well as green: the same tree gives the same
    answer, and a flake is told from a fault by running its file alone, which
    is not a whole suite. The newest record decides, so an implementer's green
    re-run after a red one is the reading reused."""
    try:
        records = read_records(store_of(source))
    except (subprocess.CalledProcessError, OSError):
        return None
    for record in reversed(records):
        if record.get("stage") == "issue" and tree_id in (
                record.get("tree"), record.get("tree_after")):
            report = record.get("coverage")
            return record if report and pathlib.Path(report).exists() else None
    return None


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def failing_files(text: str) -> list[str]:
    """Each file vitest named on a ` FAIL ` line, once, in the order it came.

    vitest writes ` FAIL  <file> > <suite> > <case>` for a failed case,
    ` FAIL  <file> [ <file> ]` for a file that failed to load, and puts a
    `|project|` tag before the file in a workspace. Colour codes are stripped
    first, because a terminal-shaped log carries them around the word."""
    found = []
    for line in ANSI.sub("", text).splitlines():
        match = FAIL_LINE.match(line)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def summary_lines(text: str) -> list[str]:
    return [line.strip() for line in ANSI.sub("", text).splitlines()
            if line.strip().startswith(SUMMARY_MARKS)]


def read_records(store: pathlib.Path) -> list[dict]:
    """Every record this tree's store holds. A line that will not parse is
    skipped, never fatal: a torn last line must not stop a suite."""
    path = store / RECORDS
    if not path.exists():
        return []
    found = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            found.append(json.loads(line))
        except ValueError:
            continue
    return found


def green_before(records: list[dict], tree_id: str, stage: str) -> dict | None:
    """The earlier green run this one would repeat, or None.

    Keyed on the tree and the stage, and NOT on the command: a repeat with a flag
    added reads the same tree and gets the same answer. A red run never counts,
    so a flake can be re-run.

    A baseline is refused whatever the tree: a run takes one, and a run's tree
    is its own, so a second green baseline in the same store is a second run's
    worth of baseline in one run."""
    for record in reversed(records):
        if record.get("exit") != 0 or record.get("stage") != stage:
            continue
        if stage == "baseline" or record.get("tree") == tree_id:
            return record
    return None


class ContractError(Exception):
    """The harness contract exists and this wrapper cannot read all of it."""


def placeable(entry) -> bool:
    """A `requiredWhen` entry of a form the contract names: a relative file
    path, or a directory path ending in `/**`, with no other pattern in it."""
    if not isinstance(entry, str):
        return False
    body = entry[:-3] if entry.endswith("/**") else entry
    parts = pathlib.PurePosixPath(body).parts
    return bool(body) and not body.startswith("/") and not body.endswith("/") \
        and ".." not in parts and not any(mark in body for mark in "*?[{")


def harness_contract(tree: pathlib.Path) -> tuple[list[str], list[str]] | None:
    """The harness command as argv and its `requiredWhen` entries, or None
    where the tree declares no harness suite.

    It reads the whole block and refuses what it cannot place, rather than
    skipping it: an entry it could not read would be a path whose change
    runs no harness, and nothing would say so."""
    path = tree / CONTRACT
    if not path.exists():
        return None
    try:
        block = json.loads(path.read_text(encoding="utf-8")).get("harnessSuite")
    except (ValueError, AttributeError, OSError) as error:
        raise ContractError(f"{path} does not read as a JSON object ({error})")
    if block is None:
        return None
    command, entries = (block.get("command"), block.get("requiredWhen")) \
        if isinstance(block, dict) else (None, None)
    if not isinstance(command, str) or not shlex.split(command):
        raise ContractError(f"{path}: harnessSuite.command is not a command")
    if not isinstance(entries, list) or not entries:
        raise ContractError(f"{path}: harnessSuite.requiredWhen names no path")
    unplaced = [entry for entry in entries if not placeable(entry)]
    if unplaced:
        raise ContractError(
            f"{path}: harnessSuite.requiredWhen holds entries of a form this "
            f"wrapper cannot place: {unplaced!r}. An entry is a relative file "
            f"path, or a directory path ending in /**.")
    return shlex.split(command), entries


def touched(tree: pathlib.Path) -> list[str]:
    """The paths the tree's uncommitted work changes: tracked changes against
    HEAD, and new files git does not ignore. The runner commits each issue
    after its gates, so this is the issue in progress."""
    changed = git(tree, "diff", "--name-only", "HEAD").splitlines()
    changed += git(tree, "ls-files", "--others", "--exclude-standard").splitlines()
    return changed


def harness_wanted(stage: str, tree: pathlib.Path,
                   entries: list[str]) -> tuple[bool, str]:
    """Whether this call runs the harness suite, and why, in one line."""
    if stage == "finale":
        return True, "the finale runs it every time"
    if stage not in HARNESS_STAGES:
        return False, f"stage {stage} runs no harness suite"
    hits = [path for path in touched(tree)
            if any(path.startswith(entry[:-2]) if entry.endswith("/**")
                   else path == entry for entry in entries)]
    if hits:
        return True, f"the diff touches {', '.join(hits)}"
    return False, "the diff touches no path the harness contract names"


def run_logged(command: list[str], log: pathlib.Path) -> tuple[int, str]:
    """Run `command` from an argument list, never a shell, with its whole
    output in `log`. Returns the exit code and the output."""
    with open(log, "w", encoding="utf-8") as handle:
        try:
            exit_code = subprocess.run(command, stdout=handle,
                                       stderr=subprocess.STDOUT).returncode
        except OSError as error:
            handle.write(f"could not start {command[0]}: {error}\n")
            exit_code = COULD_NOT_START
    return exit_code, log.read_text(encoding="utf-8", errors="replace")


def run_harness(stage: str, tree: pathlib.Path, tree_id: str, contract,
                log: pathlib.Path) -> dict:
    """The harness reading this call owes, run where it is owed. A red reading
    rechecks its failing files alone; where they pass, `exit` is 0, the red
    exit is kept as `suite_exit`, and the ledger counts each file."""
    if contract is None:
        return {"run": False, "why": "the tree declares no harness suite"}
    command, entries = contract
    try:
        wanted, why = harness_wanted(stage, tree, entries)
    except (subprocess.CalledProcessError, OSError):
        wanted, why = True, "git could not read the diff, so it runs"
    if not wanted:
        return {"run": False, "why": why}
    started = now()
    began = time.monotonic()
    exit_code, text = run_logged(command, log)
    reading = {"run": True, "why": why, "command": command, "exit": exit_code,
               "seconds": round(time.monotonic() - began, 1), "log": str(log),
               "failing": failing_files(text), "summary": summary_lines(text)}
    named = reading["failing"]
    if exit_code in (0, COULD_NOT_START) or not named:
        return reading
    again = recheck(command, named, log.with_name(f"{log.stem}-recheck.log"),
                    place=harness_args)
    reading["recheck"] = again
    if again.get("run") and again["exit"] == 0:
        reading.update({"suite_exit": exit_code, "exit": 0, "failing": [],
                        "flaky": named})
        reading["flaked"] = record_flakes(tree, named, {
            "suite": "harness", "tree": tree_id, "stage": stage,
            "started": started.isoformat(), "log": str(log),
            "recheck_log": again["log"]})
    return reading


def harness_line(harness: dict | None) -> str:
    if not harness or not harness.get("run"):
        return f"harness suite not run: {(harness or {}).get('why', 'no reading')}"
    lines = [f"harness suite exit {harness['exit']} ({harness['why']}); whole "
             f"output: {harness['log']}"]
    again = harness.get("recheck") or {}
    for name in harness.get("flaky", []):
        lines.append(f"FLAKY: {name} failed in the harness suite and passed alone "
                     f"({again.get('log')}). It has flaked "
                     f"{harness.get('flaked', {}).get(name, '?')} times in this "
                     f"repository. The harness reading is green; do not run it "
                     f"again.")
    if again and not again.get("run"):
        lines.append(f"failing harness files not rechecked: {again['why']}")
    elif again and not harness.get("flaky"):
        lines.append(f"harness recheck: the failing files ran alone and exited "
                     f"{again['exit']}, so this red is no flake ({again['log']})")
    return "\n".join(lines)


def is_test_path(path: str) -> bool:
    return bool(TEST_PATH.search(path))


def correction_refusal(store: pathlib.Path, tree: pathlib.Path,
                       tree_id: str) -> str | None:
    """Why a correction's whole suite is refused, or None where it runs.

    The perf audit of 2026-09-28, fix 3: seven runner suites, 36 minutes of
    main-thread time, re-read whole trees after corrections that changed test
    files only. Such a correction cannot red a file it does not import, so it
    takes the scoped road a light issue takes, whose set holds every test
    that imports a changed file and the repo-wide checks.

    The tree the gates graded is the newest `issue` record here: the
    implementer's last whole suite. Both hashes are tree objects `tree_hash`
    wrote, so git diffs them. No such record, or a diff git cannot read, and
    the whole suite runs: the refusal never guesses."""
    issue = next((record for record in reversed(read_records(store))
                  if record.get("stage") == "issue"), None)
    if not issue or not issue.get("tree"):
        return None
    try:
        graded = issue.get("tree_after") or issue["tree"]
        changed = git(tree, "diff", "--name-only", graded, tree_id).splitlines()
    except subprocess.CalledProcessError:
        return None
    if not changed:
        return (f"tree {tree_id} is the tree the implementer's suite read at "
                f"{issue.get('started')}, exit {issue.get('exit')}. Read that "
                f"log: {issue.get('log')}. Its coverage report: "
                f"{issue.get('coverage')}. Where the report is absent, grade "
                f"through the scoped road: {SCOPED}")
    if all(is_test_path(path) for path in changed):
        return (f"the correction since the implementer's suite at "
                f"{issue.get('started')} changes test files only: "
                f"{', '.join(changed)}. It is graded as a light issue is, by "
                f"the tests that import a changed file and the repo-wide "
                f"checks: {SCOPED}")
    return None


def issue_refusal(spawn: str | None, tree: pathlib.Path, store: pathlib.Path,
                  tree_id: str) -> str | None:
    """Why an implementer's whole suite is refused, or None where it runs. The
    module docstring holds the measurement. The scoped road is vitest's, so a
    tree without vitest is judged on its spawn's name alone."""
    if spawn is None:
        return ("stage issue names its spawn. `--spawn logic` is the first "
                "spawn of a screen issue's two-spawn attempt. `--spawn final` "
                "is every spawn that hands its tree to the gates: the screen "
                "spawn, a one-spawn attempt, a retry, an escalation.")
    if not (tree / "node_modules" / ".bin" / "vitest").exists():
        return None
    if spawn == "logic":
        return (f"the logic spawn runs no whole suite. The screen spawn after "
                f"it runs one on the tree the gates read, and the verify gate "
                f"reuses only that record. Your reading is the scoped road, "
                f"which runs every test whose imports reach your change and "
                f"the repo-wide checks:\n  {SCOPED}")
    for record in reversed(read_records(store)):
        if record.get("stage") != "scoped" or tree_id not in (
                record.get("tree"), record.get("tree_after")):
            continue
        if record.get("exit") == 0 or record.get("wide"):
            return None
        return (f"the newest scoped reading of tree {tree_id}, at "
                f"{record.get('started')}, exited {record.get('exit')}. Failing "
                f"files: {', '.join(record.get('failing') or []) or 'none named'}. "
                f"Whole output: {record.get('log')}. Fix the red, run the "
                f"scoped road again, then this:\n  {SCOPED} --whole-if-wide")
    return (f"no scoped reading exists for tree {tree_id}. The whole suite "
            f"runs once, on a tree the scoped road has passed. Run it, fix "
            f"its reds, then run this again. Where it answers WIDE it ran "
            f"nothing, and this runs at once:\n  {SCOPED} --whole-if-wide")


def reuse(earlier: dict, tree_id: str, store: pathlib.Path, queue: Queue) -> int:
    """Answer a verify suite with the implementer's record for the same tree.

    The perf audit of 2026-09-28, fix 2: the verify gate's own suite was the
    tail of 9 of 12 gate pairs, 3 to 5 minutes of critical path each. The
    record was written by this wrapper, which hashed the tree itself, so the
    reading is the wrapper's and not the implementer's word. A `verify` record
    naming the reused log goes to the copy's store."""
    exit_code = earlier.get("exit")
    record = {"tree": tree_id, "stage": "verify", "exit": exit_code,
              "command": earlier.get("command"), "asked": queue.asked.isoformat(),
              "waited": queue.waited, "lock": queue.lock,
              "lock_holder": queue.holder, "started": now().isoformat(),
              "seconds": 0.0, "log": earlier.get("log"),
              "failing": earlier.get("failing") or [],
              "coverage": earlier.get("coverage"),
              "report_root": earlier.get("report_root"),
              "reused": earlier.get("log"), "harness": earlier.get("harness")}
    with open(store / RECORDS, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(f"REUSED: tree {tree_id} already ran its whole suite at stage issue, "
          f"at {earlier.get('started')}, exit {exit_code}. The same tree gives "
          f"the same answer, so the suite did not start.")
    try:
        text = pathlib.Path(earlier.get("log") or "").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for line in summary_lines(text):
        print(f"  {line}")
    if record["failing"]:
        print("failing files:")
        for name in record["failing"]:
            print(f"  {name}")
        print("Run each failing file alone, by name, to tell a flake from a "
              "fault. A named file is not a whole suite.")
    print(f"whole output: {earlier.get('log')}")
    print(harness_line(earlier.get("harness")))
    print(f"Coverage report: {earlier.get('coverage')}\n"
          f"Report root:     {earlier.get('report_root')}")
    return exit_code if isinstance(exit_code, int) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--spawn", choices=SPAWNS,
                        help="Stage issue only: which implementer spawn calls.")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.spawn and args.stage != "issue":
        parser.error("--spawn belongs to stage issue only")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("no suite command after `--`")

    # Before the tree is read: a waiting call hashes the tree the suite will
    # run on, and sees a green record the holder wrote while it waited.
    _, queue = take_lock()
    try:
        tree, tree_id, store = locate(os.getcwd())
    except (subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"REFUSED: git could not read {os.getcwd()} ({detail.strip()}). "
              f"The wrapper records the tree it read and cannot name this one, "
              f"so the suite did not start. A gate's private copy is made "
              f"with history by: {MAKE_COPY}")
        return REFUSED
    (store / "logs").mkdir(parents=True, exist_ok=True)
    try:
        contract = harness_contract(tree)
    except ContractError as error:
        print(f"REFUSED: {error}\nThe suite did not start.")
        return REFUSED

    if args.stage == "verify":
        source = source_of(tree)
        if source is None:
            print(f"REFUSED: {tree} is not a copy `make_copy.py` made, so this "
                  f"wrapper cannot find the implementer's suite for this tree. "
                  f"The suite did not start. Make the copy with: {MAKE_COPY}")
            return REFUSED
        earlier = reusable(source, tree_id)
        if earlier:
            return reuse(earlier, tree_id, store, queue)
    if args.stage == "correction":
        why = correction_refusal(store, tree, tree_id)
        if why:
            print(f"REFUSED: {why}\nThe whole suite did not start.")
            return REFUSED

    if args.stage == "issue":
        why = issue_refusal(args.spawn, tree, store, tree_id)
        if why:
            print(f"REFUSED: {why}\nThe whole suite did not start.")
            return REFUSED

    earlier = green_before(read_records(store), tree_id, args.stage)
    if earlier:
        print(f"REFUSED: tree {tree_id} already ran green at stage "
              f"{args.stage}, at {earlier.get('started')}. The same tree gives "
              f"the same answer, so the suite did not start.\n"
              f"Read that run's whole output: {earlier.get('log')}\n"
              f"Change the tree and run again, or cite that log.")
        return REFUSED

    started = now()
    # Microseconds in the name: a red run and its re-run can share a second.
    stem = f"{started:%Y%m%dT%H%M%S.%fZ}-{args.stage}-{tree_id[:12]}"
    log = store / "logs" / f"{stem}.log"
    kept = store / "coverage" / stem
    plain = list(command)
    command, reports = with_coverage(command, kept)
    if reports is not None and not reports.is_absolute():
        reports = pathlib.Path(os.getcwd()) / reports
    suite_exit, text = run_logged(command, log)
    report = keep_report(reports, started, kept)
    named = failing_files(text)
    again = (recheck(plain, named, store / "logs" / f"{stem}-recheck.log")
             if suite_exit not in (0, COULD_NOT_START) and named else None)
    flaky = named if again and again.get("run") and again["exit"] == 0 else []
    harness = run_harness(args.stage, tree, tree_id, contract,
                          store / "logs" / f"{stem}-harness.log")
    ended = now()
    tree_after = after_hash(tree)
    suite_failing = [] if flaky else named
    failing = suite_failing + [name for name in harness.get("failing", [])
                               if name not in suite_failing]
    exit_code = (0 if flaky else suite_exit) or harness.get("exit", 0)

    record = {"tree": tree_id, "tree_after": tree_after, "stage": args.stage,
              "exit": exit_code, "suite_exit": suite_exit, "harness": harness,
              "command": command, "asked": queue.asked.isoformat(),
              "waited": queue.waited, "lock": queue.lock,
              "lock_holder": queue.holder, "started": started.isoformat(),
              "seconds": round((ended - started).total_seconds(), 1),
              "log": str(log), "failing": failing,
              "coverage": str(report) if report else None,
              "report_root": str(tree) if report else None}
    if args.spawn:
        record["spawn"] = args.spawn
    if again:
        record["recheck"] = again
    if flaky:
        record["flaky"] = flaky
    with open(store / RECORDS, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    print(f"suite exit {suite_exit} at stage {args.stage}, tree {tree_id}")
    print(queue_line(queue))
    for line in summary_lines(text):
        print(f"  {line}")
    if flaky:
        counts = record_flakes(tree, flaky, {
            "suite": "app", "tree": tree_id, "stage": args.stage, "started": started.isoformat(),
            "log": str(log), "recheck_log": again["log"]})
        for name in flaky:
            print(f"FLAKY: {name} failed in the whole suite and passed alone "
                  f"({again['log']}). It has flaked {counts[name]} times in this "
                  f"repository. The call is green; do not run the suite again. "
                  f"The list: python3 ~/.claude/skills/run-issues/flake_report.py")
    elif again and not again.get("run"):
        print(f"failing files not rechecked: {again['why']}")
    elif again:
        print(f"recheck: the failing files ran alone and exited {again['exit']}, "
              f"so this red is no flake ({again['log']})")
    if failing:
        print("failing files:")
        for name in failing:
            print(f"  {name}")
    elif suite_exit == COULD_NOT_START:
        print(f"the suite command could not start: {text.strip()}")
    elif suite_exit != 0:
        print(f"exit {exit_code} and no FAIL line in the output. The cause is "
              f"in the log, not in a test file.")
    print(f"whole output: {log}")
    print(harness_line(harness))
    if report:
        print(f"Coverage report: {report}\nReport root:     {tree}")
    else:
        print("no coverage report: the command named none this wrapper could "
              "read, or the run wrote none.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
