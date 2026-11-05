#!/usr/bin/env python3
"""The careful lane's one road to a product's tests.

    python3 ~/.claude/skills/workflow/lib/suite.py full                 # the whole suite, under the machine lock
    python3 ~/.claude/skills/workflow/lib/suite.py scoped --base <ref>  # the tests a change since <ref> reaches
    python3 ~/.claude/skills/workflow/lib/suite.py files <test file>... # one or more named files
    python3 ~/.claude/skills/workflow/lib/suite.py red --base <ref>     # the red check: new tests on the old code
    python3 ~/.claude/skills/workflow/lib/suite.py typecheck | e2e      # the other two commands the block names

Every verifier calls this and none runs the test command itself, so the rules
below are built, not remembered ("How the careful lane keeps the test suite
fast and trusted", workflow v2 ticket 21). `--tree` names the product's
checkout; the default is the current directory's.

## What it reads

The careful-lane block of the product's `CLAUDE.md`, one command per line:
`Suite:`, `Harness suite:` (optional), `Typecheck:`, `End-to-end:` and
`Suite budget: <n> minutes`. A missing line is a refusal, not a default.
`checklists/graduate-stop.md` holds the form.

## What it refuses

- A `core.hooksPath` that is not the tree's own `.githooks`, or is set while
  the tree has none. The note check hooks live there ("Where the note check
  lives", ticket 33); a suite that ran under other hooks would be a green
  nobody can trust. Exit 3, like every refusal here.
- A red check whose new tests do not all fail on the old code (below).

## The machine lock

One whole suite or end-to-end run on the machine at a time; the rest wait.
`take_lock` and `lock_path` are lifted from `run-issues/run_suite.py`, on the
SAME lock file, so a version 1 run and a careful-lane run never run two full
suites at once during the overlap. Scoped and named runs skip the lock and run
at most four workers each.

## Flakes

A failing file runs again alone, up to five files. If every one passes, the
run is green, and the product's flake ledger, `run-suite-flakes.jsonl` in the
git common directory, gains a row per file. Nothing is quarantined or skipped.

## The run time

Each full run appends a row to `suite/runs.jsonl` in the git common directory
with its seconds and the budget. The final verifier copies the last row into
the feature report, and the next `/build-feature` interview reads it to ask
the pruning question when the last reading is over budget. Nothing stops a run.

## The red check

"Whether the build agents work test-first" (ticket 22), with the migration
rule of "What a run does when notes collide or fail" (ticket 32, C5). A
throwaway worktree is made at `--base`, the code from before the note; the
test-side files the note added or changed are copied over it; and the vitest
tests whose titles did not exist before run there with the JSON reporter. Each
must fail: a passing new test proves nothing and refuses the note. A test file
that cannot load counts as failed. A title starting with `keeps:` is skipped
and listed for the reviewer. A new title the report never names is refused
too, because a check that cannot place its input must not pass it.

A title that left a test file deleted or renamed since `--base` is not new,
whatever file holds it now: it passed on the old code before the note. Measured
2026-11-05 on Orderflow note 13, four moved files carried 63 kept titles, each
refused as passing on the old code. A new file the `Suite:` command does not
run (Orderflow's `npm test` excludes `tests/harness/**`) runs once more under
the `Harness suite:` command when the block names one, in the same throwaway
tree; a file neither command runs stays refused.

Migrations revert with the code, because the worktree holds the base's
`supabase/migrations/`. Orderflow's harness fingerprints the files on disk and
rebuilds its template database from empty when they change (`tests/harness/
global-setup.ts`, issue 201); measured 2026-11-03, a build from empty through
`scripts/migrate.mjs` took 0.3 to 0.5 s for 93 files.
"""

from __future__ import annotations

import argparse
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

REFUSED = 3
RECHECK_CAP = 5
# Abdul ruled four on 2026-11-03, overturning ticket 21's two: at two workers a
# 998-file scoped run took 816 s against 245 s at eight and 550 s for the full
# suite, so a note's verifier waited longer than a final verifier. Session 6's
# rehearsal measures four with three notes running at once.
SMALL_RUN = ("--maxWorkers=4",)
FLAKES = "run-suite-flakes.jsonl"
LOCK_ENV = "RUN_SUITE_LOCK"
LINES = ("Suite", "Typecheck", "End-to-end", "Suite budget")
OPTIONAL = ("Harness suite",)
BUDGET = re.compile(r"^(\d+)\s*minutes?$")
KEEPS = "keeps:"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
FAIL_LINE = re.compile(
    r"^\s*FAIL\s+(?:\|[^|]*\|\s+)?(.+?\.[cm]?[jt]sx?)(?:\s+>\s|\s+\[\s|\s*$)")
FILES_LINE = re.compile(r"^\s*Test Files\s.*\((\d+)\)\s*$")
VITEST_TEST = re.compile(r"\.test\.[cm]?[jt]sx?$")
# Test-side: a test file, or anything under a test or end-to-end directory.
# These keep the note's version in the red check; everything else reverts.
TEST_SIDE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$|(^|/)(tests?|__tests__|e2e)/")
TITLE = re.compile(
    r"\b(?:it|test)(?:\.(?:only|skip|todo|concurrent|sequential|fails))*\s*\(\s*"
    r"(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'|`((?:[^`\\]|\\.)*)`)")
VITEST = {"vitest", "vitest.mjs"}
PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
LAUNCHERS = {"npx", "pnpx", "bunx", "node", "nohup", "time", "caffeinate"}


class Refusal(Exception):
    """Printed as `REFUSED: ...`; exit 3."""


def git(tree, *args, check=True) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True)
    if check and done.returncode:
        raise subprocess.CalledProcessError(done.returncode, done.args, done.stdout, done.stderr)
    return done.stdout.strip()


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def common_dir(tree: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(git(tree, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def read_block(tree: pathlib.Path) -> dict:
    """The commands and the budget from the careful-lane block of `CLAUDE.md`."""
    path = tree / "CLAUDE.md"
    if not path.is_file():
        raise Refusal(f"{path} does not exist, so no suite command is known.")
    found = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for key in (*LINES, *OPTIONAL):
            if line.startswith(f"{key}:") and key not in found:
                found[key] = line[len(key) + 1:].strip()
    missing = [key for key in LINES if not found.get(key)]
    if missing:
        raise Refusal(f"{path} has no `{'`, `'.join(k + ':' for k in missing)}` line. "
                      f"The careful-lane block names every command; a missing line "
                      f"is not a default. The form: checklists/graduate-stop.md.")
    match = BUDGET.match(found["Suite budget"])
    if not match:
        raise Refusal(f"`Suite budget: {found['Suite budget']}` is not `<n> minutes`.")
    return {"suite": shlex.split(found["Suite"]),
            "harness": shlex.split(found["Harness suite"]) if found.get("Harness suite") else None,
            "typecheck": shlex.split(found["Typecheck"]),
            "e2e": shlex.split(found["End-to-end"]),
            "budget_seconds": int(match.group(1)) * 60}


def hooks_refusal(tree: pathlib.Path) -> str | None:
    """Why `core.hooksPath` is wrong for this tree, or None."""
    configured = git(tree, "config", "--get", "core.hooksPath", check=False)
    own = tree / ".githooks"
    if not configured:
        if own.is_dir():
            return (f"{tree} has a .githooks directory and core.hooksPath is not set, so "
                    f"its hooks do not run. Run its prepare script, or "
                    f"`git config core.hooksPath .githooks`.")
        return None
    pointed = pathlib.Path(configured)
    if not pointed.is_absolute():
        pointed = tree / pointed
    if own.is_dir() and pointed.resolve() == own.resolve():
        return None
    return (f"core.hooksPath is `{configured}` and the tree's own hooks are {own}"
            f"{'' if own.is_dir() else ', which does not exist'}. A suite run under other "
            f"hooks is not one the lane can trust. Set it back: `git config "
            f"core.hooksPath .githooks`, or unset it where the tree has no hooks.")


# ── The machine lock, lifted from run-issues/run_suite.py (issue 41b) ─────────

def lock_path() -> pathlib.Path:
    """One path outside every tree, the same whatever directory calls. `/tmp`
    and not `tempfile.gettempdir()`: a sandboxed session can carry its own
    `TMPDIR`, and two sessions must meet on one file."""
    override = os.environ.get(LOCK_ENV)
    return pathlib.Path(override) if override else pathlib.Path(f"/tmp/run-suite-{os.getuid()}.lock")


def take_lock() -> tuple[int | None, dict]:
    """Hold the machine's whole-suite lock, waiting as long as it takes. An
    `fcntl.flock` lock: the kernel frees it when its holder dies. Returns the
    descriptor, or None when running without the lock, and what the wait cost."""
    path = lock_path()
    queue = {"lock": "free", "holder": None, "waited": 0.0}
    began = time.monotonic()
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        print(f"suite: could not open the machine lock {path} ({error}); running without it.",
              flush=True)
        queue["lock"] = "none"
        return None, queue
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = os.pread(fd, 32, 0).decode(errors="replace").strip()
            queue["lock"], queue["holder"] = "held", holder or None
            print(f"suite: another whole suite holds the machine lock {path} "
                  f"(pid {holder or 'unknown'}); waiting for it.", flush=True)
            fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as error:
        os.close(fd)
        print(f"suite: could not take the machine lock {path} ({error}); running without it.",
              flush=True)
        queue["lock"] = "none"
        return None, queue
    queue["waited"] = round(time.monotonic() - began, 1)
    os.ftruncate(fd, 0)
    os.pwrite(fd, str(os.getpid()).encode(), 0)
    return fd, queue


# ── Running and reading vitest ────────────────────────────────────────────────

def place_args(command: list[str], extra: list[str]) -> list[str]:
    """`command` with `extra` where vitest reads them: after a vitest launch
    as it stands, after a package manager's script with one `--`."""
    words = [pathlib.PurePath(word).name for word in command]
    index = 0
    while index < len(words) and (words[index] in LAUNCHERS
                                  or (index and words[index].startswith("-"))):
        index += 1
    if words[index:index + 1] and words[index] in VITEST:
        return [*command, *extra]
    if words[index:index + 1] and words[index] in PACKAGE_MANAGERS:
        return [*command, *([] if "--" in command else ["--"]), *extra]
    raise Refusal(f"the command `{' '.join(command)}` is not a vitest launch or a package "
                  f"manager script, so this script cannot name files to it.")


def run_logged(command: list[str], cwd: pathlib.Path, log: pathlib.Path,
               env: dict | None = None) -> tuple[int, str]:
    """Run `command` in `cwd`, the whole output to `log`, and return (exit, output)."""
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                              errors="replace", env=env)
        code, text = done.returncode, done.stdout + done.stderr
    except OSError as error:
        code, text = 127, f"could not start {command[0]}: {error}\n"
    log.write_text(text, encoding="utf-8")
    return code, text


def failing_files(text: str) -> list[str]:
    found = []
    for line in ANSI.sub("", text).splitlines():
        match = FAIL_LINE.match(line)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def files_run(text: str) -> int | None:
    totals = [int(m.group(1)) for m in map(FILES_LINE.match, ANSI.sub("", text).splitlines()) if m]
    return sum(totals) if totals else None


def summary_lines(text: str) -> list[str]:
    return [line.strip() for line in ANSI.sub("", text).splitlines()
            if line.strip().startswith(("Test Files", "Tests", "Duration", "Errors"))]


def recheck(command: list[str], failing: list[str], cwd: pathlib.Path,
            log: pathlib.Path) -> dict:
    """Run the failing files alone, one after another. A pass is a flake only
    when vitest reports it ran exactly the files it was named."""
    if len(failing) > RECHECK_CAP:
        return {"run": False, "why": f"{len(failing)} failing files, over the cap of {RECHECK_CAP}"}
    code, text = run_logged(place_args(command, ["--no-file-parallelism", *failing]), cwd, log)
    ran = files_run(text)
    return {"run": True, "exit": code, "log": str(log), "named": len(failing), "ran": ran,
            "flake": code == 0 and ran == len(failing)}


def record_flakes(tree: pathlib.Path, names: list[str], entry: dict) -> dict[str, int]:
    """Append one ledger line per flaky file and return each file's count."""
    path = common_dir(tree) / FLAKES
    with open(path, "a", encoding="utf-8") as handle:
        for name in names:
            handle.write(json.dumps({"file": name, **entry}) + "\n")
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            counts[json.loads(line).get("file")] = counts.get(json.loads(line).get("file"), 0) + 1
        except ValueError:
            continue
    return {name: counts.get(name, 0) for name in names}


def run_suite(kind: str, command: list[str], tree: pathlib.Path, stem: str,
              suite: str) -> dict:
    """One command, its recheck and its ledger rows. `exit` is 0 when the
    red was a flake."""
    logs = common_dir(tree) / "suite" / "logs"
    started = now()
    code, text = run_logged(command, tree, logs / f"{stem}-{suite}.log")
    named = failing_files(text)
    again = recheck(command, named, tree, logs / f"{stem}-{suite}-recheck.log") \
        if code not in (0, 127) and named else None
    flaky = named if again and again.get("run") and again["flake"] else []
    reading = {"suite": suite, "exit": 0 if flaky else code, "suite_exit": code,
               "seconds": round((now() - started).total_seconds(), 1),
               "log": str(logs / f"{stem}-{suite}.log"), "failing": [] if flaky else named,
               "flaky": flaky, "recheck": again}
    for line in summary_lines(text):
        print(f"  {line}")
    if flaky:
        counts = record_flakes(tree, flaky, {"suite": suite, "kind": kind,
                                             "started": started.isoformat(),
                                             "log": reading["log"], "recheck_log": again["log"]})
        for name in flaky:
            print(f"FLAKY: {name} failed in the run and passed alone ({again['log']}). It has "
                  f"flaked {counts[name]} times in this repository. The run is green.")
    elif again and not again.get("run"):
        print(f"failing files not rechecked: {again['why']}")
    elif again:
        print(f"recheck: the failing files ran alone and exited {again['exit']}, named "
              f"{again['named']} and vitest reported {again['ran']} run; this red is no flake "
              f"({again['log']})")
    if reading["failing"]:
        print("failing files:\n  " + "\n  ".join(reading["failing"]))
    elif code == 127:
        print(f"the command could not start: {text.strip()}")
    elif reading["exit"]:
        print(f"exit {code} and no FAIL line in the output; the cause is in the log.")
    print(f"whole output: {reading['log']}")
    return reading


def record_run(tree: pathlib.Path, row: dict) -> None:
    path = common_dir(tree) / "suite" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def last_full_run(tree: pathlib.Path) -> dict | None:
    """The last full run's row, for the report and the interview."""
    path = common_dir(tree) / "suite" / "runs.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()] if path.is_file() else []
    full = [row for row in rows if row.get("kind") == "full"]
    return full[-1] if full else None


# ── The red check ─────────────────────────────────────────────────────────────

def titles(text: str) -> list[str]:
    """Each `it(` or `test(` title in `text`, once, in order. A template title
    keeps its `${}` as written, and the report then never names it: refused."""
    found = []
    for match in TITLE.finditer(text):
        title = next(group for group in match.groups() if group is not None)
        if title not in found:
            found.append(title)
    return found


def changed_test_side(tree: pathlib.Path, base: str) -> list[str]:
    """Test-side paths added or changed since `base`, working tree included."""
    diffed = [line.split("\t")[-1] for line in
              git(tree, "diff", "--name-status", "--diff-filter=AMR", "-M", base).splitlines()]
    untracked = git(tree, "ls-files", "--others", "--exclude-standard").splitlines()
    found = []
    for path in [*diffed, *untracked]:
        if TEST_SIDE.search(path) and (tree / path).is_file() and path not in found:
            found.append(path)
    return found


def gone_titles(tree: pathlib.Path, base: str) -> set[str]:
    """The titles of every vitest test file deleted or renamed away since
    `base`, read at the base. A title that moved with its file, or into a new
    file, passed on the old code before the note and is not new."""
    gone: set[str] = set()
    for line in git(tree, "diff", "--name-status", "--diff-filter=DR", "-M", base).splitlines():
        path = line.split("\t")[1]
        if VITEST_TEST.search(path):
            gone.update(titles(git(tree, "show", f"{base}:{path}", check=False)))
    return gone


def new_titles(tree: pathlib.Path, base: str, paths: list[str]) -> tuple[dict, list]:
    """Per vitest test file, the titles the note added; and the `keeps:` ones."""
    added, kept = {}, []
    gone = gone_titles(tree, base)
    for path in paths:
        if not VITEST_TEST.search(path):
            continue
        before = set(titles(git(tree, "show", f"{base}:{path}", check=False))) | gone
        fresh = [t for t in titles((tree / path).read_text(encoding="utf-8", errors="replace"))
                 if t not in before]
        for title in fresh:
            if title.startswith(KEEPS):
                kept.append((path, title))
        fresh = [t for t in fresh if not t.startswith(KEEPS)]
        if fresh:
            added[path] = fresh
    return added, kept


def copy_env(tree: pathlib.Path, dest: pathlib.Path) -> None:
    """The tree's `.env*` files, symlinks as symlinks, so the old code reaches
    the same local database and nothing writes through a link."""
    for entry in tree.iterdir():
        if entry.name.startswith(".env") and (entry.is_file() or entry.is_symlink()):
            if entry.is_symlink():
                os.symlink(os.readlink(entry), dest / entry.name)
            else:
                shutil.copy2(entry, dest / entry.name)


def old_tree(tree: pathlib.Path, base: str, paths: list[str]) -> pathlib.Path:
    """A throwaway worktree at `base` carrying the note's test-side files,
    with the tree's `node_modules` linked in."""
    dest = pathlib.Path(tempfile.mkdtemp(prefix="red-check-")) / "tree"
    git(tree, "worktree", "add", "--detach", str(dest), base)
    for path in paths:
        (dest / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tree / path, dest / path)
    modules = tree / "node_modules"
    if modules.exists() and not (dest / "node_modules").exists():
        # An APFS clone (`cp -c`, clonefile(2)): seconds, no new blocks, and a
        # real directory, which Orderflow's served-page tests need because
        # Turbopack refuses a symlinked node_modules (`tests/sessions/
        # served-app.ts`). Where the clone is refused, a symlink.
        cloned = subprocess.run(["cp", "-cRp", "--", str(modules.resolve()),
                                 str(dest / "node_modules")], capture_output=True)
        if cloned.returncode:
            shutil.rmtree(dest / "node_modules", ignore_errors=True)
            os.symlink(modules.resolve(), dest / "node_modules")
    copy_env(tree, dest)
    return dest


def drop_tree(tree: pathlib.Path, dest: pathlib.Path) -> None:
    git(tree, "worktree", "remove", "--force", str(dest), check=False)
    shutil.rmtree(dest.parent, ignore_errors=True)
    git(tree, "worktree", "prune", check=False)


def read_report(path: pathlib.Path, dest: pathlib.Path) -> dict:
    """vitest's JSON report as {relative file: ("loaded", {title: status}) or
    ("failed to load", {})}."""
    if not path.is_file():
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    files = {}
    root = dest.resolve()
    for result in report.get("testResults", []):
        name = pathlib.Path(result["name"])
        if name.is_absolute():
            name = name.resolve()
        rel = str(name.relative_to(root)) if name.is_relative_to(root) else str(name)
        cases = {case["title"]: case["status"] for case in result.get("assertionResults", [])}
        loaded = bool(cases) or result.get("status") != "failed"
        files[rel] = ("loaded" if loaded else "failed to load", cases)
    return files


def red_check(tree: pathlib.Path, block: dict, base: str) -> int:
    """Run the note's new tests on the code from before it. Exit 0 when every
    one fails there, 3 otherwise."""
    paths = changed_test_side(tree, base)
    added, kept = new_titles(tree, base, paths)
    for path, title in kept:
        print(f"keeps: {path} > {title} (skipped; the reviewer reads it)")
    if not added:
        raise Refusal(f"no new test title since {base} in {len(paths)} test-side file(s). "
                      f"A note with no new test proves nothing.")
    stem = f"{now():%Y%m%dT%H%M%S.%fZ}-red"
    logs = common_dir(tree) / "suite" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    report = logs / f"{stem}.json"
    dest = old_tree(tree, base, paths)
    try:
        command = place_args(block["suite"], ["--reporter=json", f"--outputFile={report}",
                                              *SMALL_RUN, *added])
        print(f"red check: {sum(map(len, added.values()))} new test(s) in {len(added)} file(s), "
              f"on the code at {base} ({dest})")
        code, _ = run_logged(command, dest, logs / f"{stem}.log")
        seen = read_report(report, dest)
        not_run = [path for path in added if path not in seen]
        harness_exit = None
        if not_run and block["harness"]:
            # The `Suite:` command excludes some test files (Orderflow's `npm
            # test` leaves out `tests/harness/**`); those run under the
            # `Harness suite:` command, in the same old tree.
            harness_report = logs / f"{stem}-harness.json"
            command = place_args(block["harness"], ["--reporter=json",
                                                    f"--outputFile={harness_report}",
                                                    *SMALL_RUN, *not_run])
            print(f"red check: {len(not_run)} file(s) not run by the suite command; running "
                  f"them under the harness suite command")
            harness_exit, _ = run_logged(command, dest, logs / f"{stem}-harness.log")
            harness_seen = read_report(harness_report, dest)
            seen.update({path: harness_seen[path] for path in not_run if path in harness_seen})
    finally:
        drop_tree(tree, dest)
    wrong = []
    for path, names in added.items():
        state, cases = seen.get(path, ("not run", {}))
        for title in names:
            status = cases.get(title)
            if state == "failed to load":
                verdict = "failed to load"
            elif status == "failed":
                verdict = "failed"
            elif status is None:
                verdict = "not seen in the report" if state == "loaded" else state
            else:
                verdict = status
            print(f"  {'ok ' if verdict in ('failed', 'failed to load') else 'NOT'} {path} > "
                  f"{title}: {verdict} on the old code")
            if verdict not in ("failed", "failed to load"):
                wrong.append(f"{path} > {title}: {verdict}")
    print(f"whole output: {logs / f'{stem}.log'}; report: {report}; vitest exit {code}"
          + (f"; harness run: {logs / f'{stem}-harness.log'}, exit {harness_exit}"
             if harness_exit is not None else ""))
    if wrong:
        raise Refusal("these new tests did not fail on the code from before the note, so "
                      "they prove nothing about it:\n  " + "\n  ".join(wrong) +
                      "\nA test that passes on the old code passes by construction. A test "
                      "the report never names needs a plain string title.")
    print("red check passed: every new test fails on the old code.")
    return 0


# ── The runs ──────────────────────────────────────────────────────────────────

def full_run(tree: pathlib.Path, block: dict) -> int:
    fd, queue = take_lock()
    try:
        started = now()
        stem = f"{started:%Y%m%dT%H%M%S.%fZ}-full"
        readings = [run_suite("full", block["suite"], tree, stem, "app")]
        if block["harness"]:
            readings.append(run_suite("full", block["harness"], tree, stem, "harness"))
        seconds = round((now() - started).total_seconds(), 1)
        exit_code = next((r["exit"] for r in readings if r["exit"]), 0)
        row = {"kind": "full", "tree": str(tree), "started": started.isoformat(),
               "seconds": seconds, "budget_seconds": block["budget_seconds"],
               "over_budget": seconds > block["budget_seconds"], "exit": exit_code,
               "lock": queue["lock"], "waited": queue["waited"],
               "failing": sorted({f for r in readings for f in r["failing"]}),
               "flaky": sorted({f for r in readings for f in r["flaky"]}),
               "logs": [r["log"] for r in readings]}
        record_run(tree, row)
        print(f"full run: {seconds} s against a budget of {block['budget_seconds']} s"
              f"{' — OVER BUDGET; the next interview asks the pruning question' if row['over_budget'] else ''}; "
              f"exit {exit_code}; lock {queue['lock']}, waited {queue['waited']} s")
        return exit_code
    finally:
        if fd is not None:
            os.close(fd)


def small_run(tree: pathlib.Path, block: dict, kind: str, extra: list[str]) -> int:
    stem = f"{now():%Y%m%dT%H%M%S.%fZ}-{kind}"
    reading = run_suite(kind, place_args(block["suite"], [*SMALL_RUN, *extra]), tree, stem, "app")
    record_run(tree, {"kind": kind, "tree": str(tree), "seconds": reading["seconds"],
                      "exit": reading["exit"], "extra": extra, "log": reading["log"],
                      "flaky": reading["flaky"]})
    print(f"{kind} run: {reading['seconds']} s, exit {reading['exit']}")
    return reading["exit"]


def plain_run(tree: pathlib.Path, command: list[str], kind: str, lock: bool) -> int:
    fd = take_lock()[0] if lock else None
    try:
        started = now()
        log = common_dir(tree) / "suite" / "logs" / f"{started:%Y%m%dT%H%M%S.%fZ}-{kind}.log"
        code, text = run_logged(command, tree, log)
        seconds = round((now() - started).total_seconds(), 1)
        record_run(tree, {"kind": kind, "tree": str(tree), "seconds": seconds, "exit": code,
                          "log": str(log)})
        if code:
            print("\n".join(text.strip().splitlines()[-20:]))
        print(f"{kind}: {seconds} s, exit {code}; whole output: {log}")
        return code
    finally:
        if fd is not None:
            os.close(fd)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=("full", "scoped", "files", "red", "typecheck", "e2e"))
    parser.add_argument("--tree", default=os.getcwd())
    parser.add_argument("--base", help="scoped and red: the commit before the change")
    parser.add_argument("paths", nargs="*", help="files: the test files to run")
    args = parser.parse_args(argv)
    try:
        if args.kind in ("scoped", "red") and not args.base:
            raise Refusal(f"{args.kind} needs --base <ref>, the commit before the change.")
        if args.kind == "files" and not args.paths:
            raise Refusal("files needs at least one test file.")
        try:
            tree = pathlib.Path(git(args.tree, "rev-parse", "--show-toplevel"))
        except (subprocess.CalledProcessError, OSError) as error:
            raise Refusal(f"git could not read {args.tree}: {getattr(error, 'stderr', error)}")
        why = hooks_refusal(tree)
        if why:
            raise Refusal(why)
        block = read_block(tree)
        if args.kind == "full":
            return full_run(tree, block)
        if args.kind == "scoped":
            return small_run(tree, block, "scoped", [f"--changed={args.base}"])
        if args.kind == "files":
            return small_run(tree, block, "files", args.paths)
        if args.kind == "red":
            return red_check(tree, block, args.base)
        return plain_run(tree, block[args.kind], args.kind, lock=args.kind == "e2e")
    except Refusal as error:
        print(f"REFUSED: {error}\nNothing ran.")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
