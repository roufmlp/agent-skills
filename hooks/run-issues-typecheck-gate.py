#!/usr/bin/env python3
"""Refuse a gate spawn while the run's own tree does not typecheck.

BLAST RADIUS, first:

- Registers on PreToolUse for Agent and Task. Nothing else.
- Matches three `subagent_type` names: the verify gate and both review gates.
  Every other spawn passes untouched and pays for nothing -- no git call, no
  typecheck, no disk.
- Acts only when the spawn's working directory is inside a tree a live RUN owns.
  A gate spawned anywhere else passes.
- REFUSES one shape: a gate spawn whose tree exits non-zero on the project's own
  `typecheck` script. The refusal names the first failing file and line.
- DELIBERATELY LETS PAST: a tree whose project file declares no `typecheck`
  script, or holds none at all; a tree whose typecheck cannot be run; a hunt's gates, because a hunt has no implementer to send
  a fault back to; every payload it cannot read.
- Writes ONE file, in the machine's temporary directory: the pass cache below.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling Q8, 2026-09-08. It is also rule (a) of one run's coherence finale.
The incident: an implementer wrote in its own record that the typecheck was
clean. It exited 1. Both gates then graded a branch that did not typecheck, the
issue took a strike, and a second implementer was bought to fix what a fourteen
second command would have named. **The build stays green on this class**, because
the bundler typechecks the app graph alone, so nothing downstream catches it
either.

WHAT IT COSTS, measured 2026-09-08 on this machine, in a real checkout of about
950 test files: 17 seconds cold and 2.8 seconds warm, the project's own
`tsconfig` carrying `incremental: true`. One turn per issue.

THE CACHE, and why it holds a PASS only. A verdict is filed under the tree and a
fingerprint of its exact contents, so the second gate of a pair pays nothing --
measured above as most of the cost. A REFUSAL is never cached: a cached refusal
would answer the same spawn twice with nothing changed between, which is the one
shape that could loop. A refusal re-runs, and re-running a failing typecheck is
cheap because it stops at the first fault.

The fingerprint covers `HEAD`, every tracked change, and the name, size and
modification time of every untracked file. Where it cannot be read at all the
check still RUNS and nothing is cached, so an unreadable fingerprint costs
seconds and never a skipped check. A window of CACHE_SECONDS is the second belt
under it.

**This hook cannot ship under scrub rule H6 as it stands, and the reason is not
its own cache.** Running the project's `typecheck` script makes the compiler
write its incremental build file into the tree it checks. That file is ignored by
git in the checkout this was built for, so it reaches no diff, but it is still a
write inside somebody's repository. A published copy has to point the compiler's
build info somewhere temporary first.

IT NEVER HALTS A RUN. Nobody is at the keyboard during a run. A refusal answers ONE tool call
and names two roads out, both of them roads the runner takes alone and now. It
must never edit the fault itself, because an edit made there ships a line no
gate read; where a source-write guard is installed, that write is refused
outright. This refusal's wording is shared by every gate in this pack, so a
refused agent meets one shape and not two.

It fails OPEN on anything it cannot read, and says so on stderr. A guard that
blocks a spawn when the guard itself breaks is worse than no guard.

Drill: `test_run_issues_typecheck_gate.py` beside this file.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time

# The ledger selector lives beside the skill, not the hooks. Imported by path so
# the hook and the skill keep one definition of "live".
LEDGER_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "skills", "run-issues",
    "find_live_ledger.py")

# The three roles that grade one issue's diff on a run. A hunt's gates are NOT
# here: a hunt has no implementer to send the fault to, so the refusal would name
# a road that does not exist there.
GATES = (
    "run-issues-verify-gate",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
)

# The project's own script name. Ruling Q8 names this command, not `tsc`, so a
# project that typechecks some other way is covered by its own package file.
TYPECHECK = ("npm", "run", "typecheck")

# Long enough for a slow cold compile on a large tree, short enough that a hung
# compiler cannot hold a run. On timeout the spawn PASSES.
TIMEOUT_SECONDS = 600

# A pass is trusted for this long even when the fingerprint agrees. Both gates of
# a pair spawn within minutes of each other.
CACHE_SECONDS = 1800

STATE_VERSION = 1

# `src/lib/a.ts(148,7): error TS2345: ...` and, in the pretty form,
# `src/lib/a.ts:148:7 - error TS2345: ...`. Anchored on `error TS`, so a line
# that merely holds a colon and a number -- a debugger address, a URL -- cannot
# be read as a fault.
TSC_FAULT = re.compile(
    r"^(?P<file>[^\s(][^(:]*?)"
    r"(?:\((?P<row>\d+),(?P<col>\d+)\)|:(?P<row2>\d+):(?P<col2>\d+)\s*-)"
    r"\s*:?\s*error TS\d+", re.MULTILINE)

AFK = (
    "\n\nTHIS NEVER WAITS FOR THE HUMAN AND IT IS NOT A HALT. Nobody is at the "
    "keyboard during a run. Take one of the two roads above now and carry on."
    "\n(Gate: ~/.claude/hooks/run-issues-typecheck-gate.py)"
)


def is_gate_spawn(tool_input):
    """True when this spawn is one of the three gates that grade a run's diff."""
    if not isinstance(tool_input, dict):
        return False
    return str(tool_input.get("subagent_type") or "") in GATES


def _inside(child, parent):
    """True when `child` is `parent` itself or below it.

    `os.path.commonpath` rather than `startswith`, so a sibling tree whose name
    shares a prefix -- `run-abc123-old` beside `run-abc123` -- does not match.
    """
    child = os.path.normpath(child)
    parent = os.path.normpath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:  # different drives, or a relative path against absolute
        return False


def tree_of(cwd, run_trees):
    """The live run tree this working directory sits in, or "" for none."""
    if not cwd:
        return ""
    for tree in run_trees:
        if tree and _inside(cwd, os.path.normpath(tree)):
            return os.path.normpath(tree)
    return ""


def first_error(output):
    """`file:row:col` of the first typecheck fault, or "" when none is named."""
    if not isinstance(output, str):
        return ""
    found = TSC_FAULT.search(output)
    if not found:
        return ""
    row = found.group("row") or found.group("row2")
    col = found.group("col") or found.group("col2")
    return f"{found.group('file')}:{row}:{col}"


def tree_has_typecheck(tree):
    """True when the tree's own project file declares a `typecheck` script.

    The package file EXISTING is not enough, and reading the exit code alone is
    the fault: npm exits non-zero on a missing script, so a project that
    typechecks some other way -- or does not typecheck at all -- would have every
    gate of its run refused for ever, under a refusal saying the tree does not
    compile. Found by review on 2026-09-08, before this shipped.

    Anything unreadable answers False, which passes the spawn. A guard that
    cannot read a project file must not refuse its gates.
    """
    try:
        with open(os.path.join(tree, "package.json")) as handle:
            package = json.load(handle)
    except (OSError, ValueError):
        return False
    scripts = package.get("scripts") if isinstance(package, dict) else None
    return isinstance(scripts, dict) and bool(scripts.get("typecheck"))


def tree_fingerprint(tree):
    """A hash of exactly what the compiler would read: HEAD plus every change.

    Tracked changes go in by CONTENT. Untracked files go in by name, size and
    modification time, which is enough to notice a new or rewritten source file
    without reading every one of them.
    """
    parts = []
    for argv in (("rev-parse", "HEAD"),
                 ("status", "--porcelain=v1", "--untracked-files=all"),
                 ("diff", "HEAD")):
        done = subprocess.run(("git", "-C", tree) + argv, capture_output=True,
                              text=True, timeout=120)
        parts.append(done.stdout)

    untracked = []
    for line in parts[1].splitlines():
        if not line.startswith("?? "):
            continue
        path = os.path.join(tree, line[3:].strip().strip('"'))
        try:
            stat = os.stat(path)
            untracked.append(f"{path}:{stat.st_size}:{stat.st_mtime_ns}")
        except OSError:
            untracked.append(f"{path}:gone")

    digest = hashlib.sha256()
    for part in parts + sorted(untracked):
        digest.update(part.encode("utf-8", "replace"))
        digest.update(b"\0")
    return digest.hexdigest()


def run_typecheck(tree):
    """(exit code, output) of the project's own typecheck script in `tree`."""
    done = subprocess.run(TYPECHECK, cwd=tree, capture_output=True, text=True,
                          timeout=TIMEOUT_SECONDS)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def cache_path():
    """One file, in the machine's temporary directory. Nothing else is written."""
    return os.path.join(tempfile.gettempdir(), "run-issues-typecheck.json")


def load_cache(path):
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.pop("version", None) != STATE_VERSION:
        return {}
    return data


def save_cache(path, data):
    try:
        with open(path, "w") as handle:
            json.dump(dict(data, version=STATE_VERSION), handle)
    except OSError:
        pass  # A guard that cannot record must not refuse the next spawn.


def refusal(tree, output):
    """What the runner reads when its branch does not typecheck."""
    site = first_error(output)
    where = f"  first fault: {site}\n" if site else ""
    tail = "\n".join(output.strip().splitlines()[:1]) if output.strip() else ""
    named = f"  {tail}\n" if tail and not site else ""
    return (
        "REFUSED. This tree does not typecheck, so a gate spawned now would "
        "grade a branch that does not compile.\n"
        f"  tree: {tree}\n"
        f"{where}{named}"
        "  command: npm run typecheck\n\n"
        "One run bought a strike and a whole second attempt on exactly this: an "
        "implementer recorded the typecheck as clean, it exited 1, and both "
        "gates graded the branch anyway. The build does not catch this class, "
        "because the bundler typechecks the app graph alone.\n\n"
        "Two roads out:\n"
        "1. Spawn a correction implementer with this fault as its owed list, "
        "then re-issue this gate spawn. That is the road when the fault is in "
        "the diff now under grading.\n"
        "2. Where the fault is somewhere else on the branch, it is still a "
        "correction implementer, and it still comes before the gates. **Do not "
        "fix it yourself.** An edit made here ships a line neither gate read, "
        "and where a source-write guard is installed it is refused outright." + AFK)


def decide(payload, run_trees=(), fingerprint=None, typecheck=None,
           has_typecheck=None, cache=None, now=None):
    """Return (exit code, message). Every side effect is an injected callable.

    The three callables default to None and are resolved HERE rather than in the
    signature, so a drill can replace the module's own copy and reach this
    through `main`. A default bound in the signature cannot be replaced, and the
    first end-to-end drill of this file silently ran the real compiler because of
    it.
    """
    fingerprint = fingerprint or tree_fingerprint
    typecheck = typecheck or run_typecheck
    has_typecheck = has_typecheck or tree_has_typecheck
    if not isinstance(payload, dict):
        return 0, ""
    tool_input = payload.get("tool_input")
    if not is_gate_spawn(tool_input):
        return 0, ""

    tree = tree_of(str(payload.get("cwd") or ""), run_trees)
    if not tree:
        return 0, ""

    try:
        if not has_typecheck(tree):
            return 0, ""
    except OSError as err:
        return 0, (f"run-issues-typecheck-gate: cannot read the tree ({err}), "
                   "so the spawn passed unchecked.")

    now = time.time() if now is None else now
    cache = {} if cache is None else cache

    mark = None
    try:
        mark = fingerprint(tree)
    except Exception as err:  # git hung, not a repository, no git at all
        # The check still runs. Only the CACHE is lost, and losing it costs
        # seconds while skipping the check costs an attempt.
        mark = None
        print(f"run-issues-typecheck-gate: cannot fingerprint the tree ({err}), "
              "so the verdict will not be cached.", file=sys.stderr)

    if mark is not None:
        held = cache.get(tree)
        if (isinstance(held, (list, tuple)) and len(held) == 2
                and held[0] == mark and now - held[1] <= CACHE_SECONDS):
            return 0, ""

    try:
        code, output = typecheck(tree)
    except Exception as err:  # npm missing, no typecheck script, a timeout
        return 0, (f"run-issues-typecheck-gate: cannot run the typecheck "
                   f"({err}), so the spawn passed unchecked.")

    if code == 0:
        if mark is not None:
            cache[tree] = [mark, now]
        return 0, ""

    # A PASS only is ever cached. See the docstring.
    return 2, refusal(tree, output)


def live_run_trees(cwd):
    """Every worktree a live RUN owns, read the way the run ceiling reads it."""
    spec = importlib.util.spec_from_file_location(
        "find_live_ledger", LEDGER_SCRIPT)
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    worktrees = ledger.list_worktrees(cwd)
    candidates = ledger.collect_candidates(worktrees=worktrees)
    return tuple(getattr(item, "tree", "") for item in ledger.runs(candidates))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        print(f"run-issues-typecheck-gate: unreadable payload ({err}), so the "
              "spawn passed unchecked.", file=sys.stderr)
        return 0

    # Judged FIRST: every spawn on this machine reaches this hook, and only three
    # type names may pay for a `git worktree list` and a ledger walk.
    if not is_gate_spawn(payload.get("tool_input")):
        return 0

    cwd = str(payload.get("cwd") or os.getcwd())
    try:
        run_trees = live_run_trees(cwd)
    except Exception as err:  # not a git repo, git hung, selector missing
        print(f"run-issues-typecheck-gate: cannot read the live ledgers ({err}), "
              "so the spawn passed unchecked.", file=sys.stderr)
        return 0

    path = cache_path()
    cache = load_cache(path)
    code, message = decide(payload, run_trees=run_trees, cache=cache)
    save_cache(path, cache)

    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
