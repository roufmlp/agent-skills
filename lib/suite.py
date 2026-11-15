#!/usr/bin/env python3
"""The careful lane's one road to a product's tests.

    python3 ~/.claude/skills/workflow/lib/suite.py full                 # the whole suite, under the machine lock
    python3 ~/.claude/skills/workflow/lib/suite.py scoped --base <ref>  # the tests a change since <ref> reaches
    python3 ~/.claude/skills/workflow/lib/suite.py files <test file>... # one or more named files
    python3 ~/.claude/skills/workflow/lib/suite.py red --base <ref>     # the red check: new tests on the old code
    python3 ~/.claude/skills/workflow/lib/suite.py removal --base <ref> # the removal check: the tests with each hunk taken out
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
- A removal check that finds a hunk of the change no test needs (below).

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

On a note's branch, `note/<feature>/<nn>`, a title in a vitest file the
note's `## Tests` part names counts as the note's own when it exists at
`--base` and a commit that touched the note's file added it: the /build-feature
interview commits each note with its tests before the run (`note <nn>: ...`),
and the run's base is the feature branch. Measured 2026-11-09 on Orderflow
in-house note 01, whose first attempt the rule of new titles alone refused with
"no new test title". The other titles of such a file are older, from the code
before the note or from another note, and passed there already; they are not
asked to fail. Measured 2026-11-13 on Orderflow note 05 of a November feature:
the rule that counted every title of a named file refused 56 older titles of
`tests/scripts/evening-check.test.ts` for passing on the old code. Abdul
approved the change on 2026-11-13. A branch that names a note with no file
under `changes/` is refused.

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

## The removal check

The red check asks whether each new test fails on the old code. It does not
ask whether each piece of the new code has a test. Measured 2026-11-15 on the
59 reject reports of six Orderflow features: 24 named a test that stays green
with the behaviour wrong, and a note rejected on it was rejected again, because
a reviewer names one or two such lines by hand and the next reviewer finds the
next (note 01 of a November feature, the bill warnings: eight rejections in a
row, each on a different line). The implementer brief stated the rule already.
Abdul approved the check on 2026-11-15.

A throwaway worktree holds the change as it stands: the base, with every
changed and untracked file copied over it and every deleted file gone. Its
diff against `--base`, with no context lines, gives the hunks. A hunk counts
when it adds a line to a code file: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`,
`.cjs` or `.sql`, outside the test side, or a harness helper the red check
runs at the base. For each one, alone, the hunk goes back to the base's text
and the note's vitest files run: the test-side files the change touched and
the files the note's `## Tests` part names. A red run proves the hunk. After a
green run the typecheck runs; a typecheck that fails proves the hunk too,
because types and imports have no test. A hunk that leaves both green is
printed with its file, its lines and its first lines of text, and the check
refuses. Every such hunk is printed in the one run.

What it does not ask: a hunk that only removes lines, a hunk of comments and
blank lines, and a changed file that is no code file, which it prints as `not
checked:` for the reviewer. It runs no end-to-end spec, so a hunk only a spec
proves is refused here: a vitest case is the road. A syntax error counts as a
red run, so a hunk cut from the middle of a statement reads as proven; the
check under-reports and the reviewer's first step stays.

The tests must be green with nothing removed, and so must the typecheck before
it is asked about a hunk, or a red would prove nothing: both are refusals. A
test file the `Suite:` command does not run goes to the `Harness suite:`
command, as in the red check. Each run appends a row to `suite/runs.jsonl`
with its seconds, its hunks and the unproven ones.
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
# One exception, Abdul's default of 2026-11-06: a file under a harness folder
# that is no test file and exists at the base is the code a harness note
# changes, so the red check runs the base's version. Copied, the fix travels
# with its test and the test passes on the "old" code (suite-green's note 01,
# `tests/harness/database.ts`). A new helper has no old version and is copied.
HARNESS_FOLDER = re.compile(r"(^|/)tests?/harness/")
TEST_FILE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$")
NOTE_BRANCH = re.compile(r"^note/([a-z0-9-]+)/(\d{2})$")
COMMENT_LINE = re.compile(r"^\s*(//|/\*|\*)")
# The removal check: the files whose hunks it takes out, a comment line of
# SQL, and a hunk's header in a diff with no context lines.
CODE_FILE = re.compile(r"\.([cm]?[jt]sx?|sql)$")
SQL_COMMENT = re.compile(r"^\s*--")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
SHOWN_LINES = 3
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
    keeps its `${}` as written, and the report then never names it: refused.
    A line that opens as a comment is skipped: Orderflow's comment "inside it
    (`forgetOtherBrowsers`)" read as a title no report names (2026-11-09)."""
    code = "\n".join(line for line in text.splitlines() if not COMMENT_LINE.match(line))
    found = []
    for match in TITLE.finditer(code):
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


def old_harness_helpers(tree: pathlib.Path, base: str, paths: list[str]) -> list[str]:
    """The changed paths the red check leaves at the base: see HARNESS_FOLDER."""
    return [path for path in paths
            if HARNESS_FOLDER.search(path) and not TEST_FILE.search(path)
            and git(tree, "ls-tree", "--name-only", base, "--", path).strip()]


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


def note_file(tree: pathlib.Path) -> str | None:
    """On a note's branch, `note/<feature>/<nn>`, the path of its note,
    `changes/<feature>/<nn>-*.md`. Any other branch names none."""
    branch = git(tree, "branch", "--show-current", check=False).strip()
    match = NOTE_BRANCH.match(branch)
    if not match:
        return None
    feature, number = match.groups()
    found = sorted((tree / "changes" / feature).glob(f"{number}-*.md"))
    if len(found) != 1:
        raise Refusal(f"the branch {branch} is a note's branch, and changes/{feature}/{number}-*.md "
                      f"matches {len(found)} file(s), not one.")
    return found[0].relative_to(tree).as_posix()


def note_test_files(tree: pathlib.Path, note: str | None) -> list[str]:
    """The vitest files the note's `## Tests` part names, or none when no note
    is given. The /build-feature interview commits a note with its tests
    before the run, so they exist at the run's base (measured 2026-11-09 on
    Orderflow in-house note 01)."""
    if note is None:
        return []
    named, inside = [], False
    for line in (tree / note).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Tests"
        elif inside:
            for path in re.findall(r"`([^`\s]+)`", line):
                if VITEST_TEST.search(path) and (tree / path).is_file() and path not in named:
                    named.append(path)
    return named


def note_commit_titles(tree: pathlib.Path, base: str, note: str, path: str) -> set[str]:
    """The titles of `path` that the note's commits up to `base` added: each
    commit that touched the note's file, read against its first parent. The
    interview commits a note with its tests, and a ruling commits the note
    with the tests it changes, so those commits are the note's. A commit of
    another note that adds titles to the same file does not touch this note
    and adds none here."""
    added: set[str] = set()
    for commit in git(tree, "log", "--format=%H", base, "--", note).split():
        after = titles(git(tree, "show", f"{commit}:{path}", check=False))
        before = titles(git(tree, "show", f"{commit}^:{path}", check=False))
        added.update(title for title in after if title not in before)
    return added


def new_titles(tree: pathlib.Path, base: str, paths: list[str],
               named: list[str] = (), note: str | None = None) -> tuple[dict, list]:
    """Per vitest test file, the titles the note added, and the `keeps:` ones.
    A title is added when it is not in the file at `base`; in a file of
    `named`, also when it is there and the note's own commits added it."""
    added, kept = {}, []
    gone = gone_titles(tree, base)
    for path in paths:
        if not VITEST_TEST.search(path):
            continue
        before = set(titles(git(tree, "show", f"{base}:{path}", check=False)))
        if note is not None and path in named:
            before -= note_commit_titles(tree, base, note, path)
        before |= gone
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
    note = note_file(tree)
    named = note_test_files(tree, note)
    paths = changed_test_side(tree, base)
    paths += [path for path in named if path not in paths]
    added, kept = new_titles(tree, base, paths, named, note)
    for path, title in kept:
        print(f"keeps: {path} > {title} (skipped; the reviewer reads it)")
    if not added:
        raise Refusal(f"no new test title since {base} in {len(paths)} test-side file(s). "
                      f"A note with no new test proves nothing.")
    stem = f"{now():%Y%m%dT%H%M%S.%fZ}-red"
    logs = common_dir(tree) / "suite" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    report = logs / f"{stem}.json"
    helpers = old_harness_helpers(tree, base, paths)
    for path in helpers:
        print(f"helper: {path} runs at the base here, as code. This is a default of 2026-11-06 "
              f"that Abdul may change: raise it with him if this red or pass looks wrong.")
    dest = old_tree(tree, base, [path for path in paths if path not in helpers])
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


# ── The removal check ─────────────────────────────────────────────────────────

def changed_paths(tree: pathlib.Path, base: str) -> tuple[list[str], list[str]]:
    """The paths that differ from `base`, working tree and untracked files
    included: those that exist now, and those that are gone."""
    present, gone = [], []
    for line in git(tree, "-c", "core.quotePath=false", "diff", "--name-status",
                    "--no-renames", base).splitlines():
        (gone if line.split("\t")[0] == "D" else present).append(line.split("\t")[-1])
    present += git(tree, "-c", "core.quotePath=false", "ls-files", "--others",
                   "--exclude-standard").splitlines()
    return [path for path in dict.fromkeys(present) if (tree / path).is_file()], gone


def note_tree(tree: pathlib.Path, base: str) -> tuple[pathlib.Path, list[str]]:
    """A throwaway worktree holding the change as it stands, staged in the
    worktree's own index, so one hunk can be taken out and put back there. The
    tree and its index are not touched."""
    present, gone = changed_paths(tree, base)
    dest = old_tree(tree, base, present)
    for path in gone:
        (dest / path).unlink(missing_ok=True)
    if present or gone:
        git(dest, "--literal-pathspecs", "add", "-A", "--", *present, *gone)
    return dest, present


def code_hunks(dest: pathlib.Path, base: str, path: str) -> list[dict]:
    """The hunks of `path` against `base` that add a line of code, each with
    the one-hunk patch that takes it out."""
    done = subprocess.run(["git", "-C", str(dest), "--literal-pathspecs", "diff", "--cached",
                           "-U0", "--no-color", "--no-ext-diff", "--no-renames", base, "--", path],
                          capture_output=True, text=True, errors="replace", check=True)
    lines = done.stdout.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("@@")]
    comment = SQL_COMMENT if path.endswith(".sql") else COMMENT_LINE
    found = []
    for start, end in zip(starts, [*starts[1:], len(lines)]):
        first, count = HUNK.match(lines[start]).groups()
        added = [line[1:].rstrip("\n") for line in lines[start + 1:end] if line.startswith("+")]
        if count == "0" or all(not line.strip() or comment.match(line) for line in added):
            continue
        last = int(first) + int(count or 1) - 1
        found.append({"path": path, "where": f"{path}:{first}" + (f"-{last}" if last > int(first) else ""),
                      "added": added, "patch": "".join(lines[:starts[0]] + lines[start:end])})
    return found


def test_runs(block: dict, tests: list[str], dest: pathlib.Path, logs: pathlib.Path,
              stem: str) -> list[tuple[list[str], list[str]]]:
    """Run the note's tests with nothing removed and return (command, files)
    per command that runs them. A red here is a refusal: nothing a later red
    says would be about a hunk."""
    runs, left = [], tests
    for name, command in (("suite", block["suite"]), ("harness", block["harness"])):
        if not left or not command:
            continue
        report = logs / f"{stem}-whole-{name}.json"
        log = logs / f"{stem}-whole-{name}.log"
        code, text = run_logged(place_args(command, ["--reporter=json", f"--outputFile={report}",
                                                     *SMALL_RUN, *left]), dest, log)
        seen = [path for path in left if path in read_report(report, dest)]
        if seen and code:
            raise Refusal(f"the note's tests are red with nothing removed, so a red run would "
                          f"prove nothing about a hunk:\n  "
                          + "\n  ".join(failing_files(text) or seen) + f"\nwhole output: {log}")
        if seen:
            runs.append((command, seen))
        left = [path for path in left if path not in seen]
    if left:
        raise Refusal("neither the `Suite:` command nor a `Harness suite:` command runs these "
                      "test files, so nothing can prove a hunk through them:\n  " + "\n  ".join(left))
    return runs


def removal_check(tree: pathlib.Path, block: dict, base: str) -> int:
    """Take each code hunk of the change out, alone, and run the note's tests.
    Exit 0 when every hunk turns a test or the typecheck red, 3 otherwise."""
    started = now()
    note = note_file(tree)
    side = changed_test_side(tree, base)
    tests = [path for path in dict.fromkeys([*side, *note_test_files(tree, note)])
             if VITEST_TEST.search(path)]
    if not tests:
        raise Refusal(f"no vitest test file changed since {base} and the note names none, so "
                      f"nothing can prove a hunk.")
    stem = f"{started:%Y%m%dT%H%M%S.%fZ}-removal"
    logs = common_dir(tree) / "suite" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    dest, present = note_tree(tree, base)
    unproven, typed = [], None
    try:
        helpers = old_harness_helpers(tree, base, present)
        code_paths = [path for path in present if CODE_FILE.search(path)
                      and (not TEST_SIDE.search(path) or path in helpers)]
        for path in present:
            if path not in code_paths and not TEST_SIDE.search(path):
                print(f"not checked: {path} (no code file; the reviewer reads it)")
        hunks = [hunk for path in code_paths for hunk in code_hunks(dest, base, path)]
        if not hunks:
            print(f"removal check passed: no code hunk since {base} adds a line.")
            return 0
        runs = test_runs(block, tests, dest, logs, stem)
        print(f"removal check: {len(hunks)} hunk(s) in {len({h['path'] for h in hunks})} file(s), "
              f"against {len(tests)} test file(s), on the change since {base} ({dest})", flush=True)
        patch = dest.parent / "hunk.patch"
        for number, hunk in enumerate(hunks, 1):
            patch.write_text(hunk["patch"], encoding="utf-8")
            took = subprocess.run(["git", "-C", str(dest), "apply", "-R", "--unidiff-zero",
                                   "--whitespace=nowarn", str(patch)], capture_output=True, text=True)
            try:
                if took.returncode:
                    verdict = f"could not be taken out ({took.stderr.strip().splitlines()[-1:]})"
                elif any(run_logged(place_args(command, [*SMALL_RUN, "--bail=1", *files]), dest,
                                    logs / f"{stem}-{number}.log")[0] for command, files in runs):
                    verdict = None
                    print(f"  ok  {hunk['where']}: a test goes red without it", flush=True)
                else:
                    if typed is None:
                        git(dest, "--literal-pathspecs", "checkout", "--", hunk["path"])
                        typed = run_logged(block["typecheck"], dest, logs / f"{stem}-whole-typecheck.log")[0]
                        if typed:
                            raise Refusal(f"the typecheck fails in the throwaway tree with nothing "
                                          f"removed, so it cannot say what a hunk is for. Whole "
                                          f"output: {logs / f'{stem}-whole-typecheck.log'}")
                        subprocess.run(["git", "-C", str(dest), "apply", "-R", "--unidiff-zero",
                                        "--whitespace=nowarn", str(patch)], check=True, capture_output=True)
                    if run_logged(block["typecheck"], dest, logs / f"{stem}-{number}-typecheck.log")[0]:
                        verdict = None
                        print(f"  ok  {hunk['where']}: the typecheck fails without it", flush=True)
                    else:
                        verdict = "every test and the typecheck stay green without it"
                if verdict:
                    unproven.append(hunk["where"])
                    print(f"  NOT {hunk['where']}: {verdict}\n" + "\n".join(
                        f"        {line}" for line in hunk["added"][:SHOWN_LINES])
                          + (f"\n        ... {len(hunk['added']) - SHOWN_LINES} more line(s)"
                             if len(hunk["added"]) > SHOWN_LINES else ""), flush=True)
            finally:
                git(dest, "--literal-pathspecs", "checkout", "--", hunk["path"])
    finally:
        drop_tree(tree, dest)
        seconds = round((now() - started).total_seconds(), 1)
    record_run(tree, {"kind": "removal", "tree": str(tree), "seconds": seconds,
                      "exit": REFUSED if unproven else 0, "hunks": len(hunks),
                      "unproven": unproven, "log": str(logs / stem)})
    print(f"removal run: {seconds} s; logs: {logs / stem}-*.log")
    if unproven:
        raise Refusal(f"{len(unproven)} of {len(hunks)} hunk(s) of the change are needed by no "
                      f"test:\n  " + "\n  ".join(unproven) +
                      "\nEach is code the note's tests cannot tell from its absence. Add a case "
                      "to a test file of the note that fails without it, or take the lines out "
                      "when nothing needs them.")
    print(f"removal check passed: each of {len(hunks)} hunk(s) turns a test or the typecheck red "
          f"when it is taken out.")
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
    parser.add_argument("kind", choices=("full", "scoped", "files", "red", "removal", "typecheck", "e2e"))
    parser.add_argument("--tree", default=os.getcwd())
    parser.add_argument("--base", help="scoped, red and removal: the commit before the change")
    parser.add_argument("paths", nargs="*", help="files: the test files to run")
    args = parser.parse_args(argv)
    try:
        if args.kind in ("scoped", "red", "removal") and not args.base:
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
        if args.kind == "removal":
            return removal_check(tree, block, args.base)
        return plain_run(tree, block[args.kind], args.kind, lock=args.kind == "e2e")
    except Refusal as error:
        print(f"REFUSED: {error}\nNothing ran.")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
