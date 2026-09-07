#!/usr/bin/env python3
"""Run every python suite under `~/.claude/skills` and `~/.claude/hooks`, and
refuse a suite that reported no executed check.

## The class

A test file that defines checks and never runs them exits zero and prints
nothing alarming. That silence is byte-for-byte the silence of a clean run, so
the ritual "run every python suite in both trees" reports green over checks
nobody executed. The class has been met three times:

    2026-09-07  `run-issues/test_skill_structure.py` carried 27 cases BELOW its
                `if __name__ == "__main__"` block. The block ran, the loader
                collected what was defined at that moment, and the suite
                reported 79 passing while 27 sat unreachable.

    2026-09-07  five files carried no runner block at all. Four of them are in
                this pack -- `run-issues/test_check_origin.py`,
                `run-issues/test_check_register_status.py`,
                `run-issues/test_cost_scripts_batch.py` and
                `run-issues/test_empty_input.py`; the fifth was a hook test that
                does not ship here. Under `python3 <file>` all five imported
                cleanly, defined their functions, executed none and exited zero.
                129 checks.

    standing    the shape is old and it is not confined to this tree: a check
                that looks built and never runs.

## Why prose did not close it

Every one of those files was written by someone who knew the rule. The ritual
is performed by hand, one `python3 <file>` at a time, and a missing block is
invisible at the moment it matters. the human's three-class test in
`~/.claude/CLAUDE.md` sorts this into the first class: it can refuse, so it is
built rather than remembered.

## The two refusals

    static      a file that defines `test_` functions and carries no top-level
                `if __name__ == "__main__":` block. Nothing can reach its
                checks, so it is refused before it is run.

    arithmetic  a file whose run reported FEWER executed checks than it defines.
                This is the dead-block shape, where some checks are reached and
                the rest are not. The comparison is one-sided on purpose:
                executed ABOVE defined is normal -- pytest parametrises, and
                unittest counts a method inherited from a base class once per
                subclass -- and is never refused.

A file that defines no `test_` function is graded on its exit code alone.
`skills/lib/test_check_decision_ledger.py` is that shape: a hand-rolled runner
whose checks live inside `main()`. It is not an exemption written for one file;
a file defining nothing has no check for this script to lose.

Exit codes follow the rest of this directory. 0 is a clean walk, 1 is "a file
was read and it is wrong", and 2 is "nothing could be read, so nothing is
asserted" -- which is what an empty walk gets, for the same reason a checker
that parsed zero rows may not report a pass.
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass

DEFAULT_ROOTS = (
    os.path.expanduser("~/.claude/skills"),
    os.path.expanduser("~/.claude/hooks"),
)

# `Ran 135 tests in 0.075s`, and `Ran 1 test` for the singular.
UNITTEST_COUNT = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
# `12 passed in 0.01s`, `10 passed, 2 skipped in 0.01s`, `3 failed, 1 passed...`
PYTEST_TERM = re.compile(
    r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed|deselected)")
PYTEST_SUMMARY = re.compile(r"^=*\s*(?:no tests ran|.*\b(?:passed|failed|error)\b).*$",
                            re.MULTILINE)
PYTEST_NONE = re.compile(r"^=*\s*no tests ran\b", re.MULTILINE)


def defined_tests(source, filename="<unknown>"):
    """The qualified names of every check this file promises to run.

    Module-level `def test_*` and `def test_*` on a module-level class. A
    function nested inside another function is skipped: no loader can reach it,
    so counting it would refuse a file that is not at fault.

    A file that will not parse raises. Reading a syntax error as "defines
    nothing" is the vacuous pass this script exists to refuse. `filename`
    travels into the parse so a SyntaxError, and any compiler warning the
    file provokes, names the file rather than `<unknown>`.
    """
    tree = ast.parse(source, filename=filename)
    names = []
    funcs = (ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, funcs) and node.name.startswith("test_"):
            names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, funcs) and child.name.startswith("test_"):
                    names.append(f"{node.name}.{child.name}")
    return names


def has_entry_point(source):
    """Whether `python3 <file>` has anything to reach.

    Top level only. The same three lines indented inside a function run when
    that function is called, and nothing calls it -- which is the dead-runner
    shape wearing the right words.
    """
    for node in ast.parse(source).body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], ast.Eq):
            continue
        sides = [test.left, test.comparators[0]]
        names = {s.id for s in sides if isinstance(s, ast.Name)}
        strings = {s.value for s in sides
                   if isinstance(s, ast.Constant) and isinstance(s.value, str)}
        if "__name__" in names and "__main__" in strings:
            return True
    return False


def executed_count(stdout, stderr):
    """How many checks the run says it executed, or None if it did not say.

    None and zero are different answers and the caller treats them differently.
    Zero is "it counted, and the answer was none". None is "it printed no
    figure", which for a file that defines checks is itself a refusal, because
    an unread instrument and a clean instrument look alike.

    Skips, failures and errors all count. A skipped check was collected and
    reached; it is not a silence. The last summary in the output wins, so a
    file running two suites in one process is read at its total rather than at
    its first.
    """
    runs = UNITTEST_COUNT.findall(stderr) + UNITTEST_COUNT.findall(stdout)
    if runs:
        return int(runs[-1])
    text = stdout + "\n" + stderr
    if PYTEST_NONE.search(text):
        return 0
    lines = PYTEST_SUMMARY.findall(text)
    for line in reversed(lines):
        counts = PYTEST_TERM.findall(line)
        if counts:
            return sum(int(n) for n, word in counts if word != "deselected")
    return None


@dataclass
class Verdict:
    """One file's result: whether it may be reported as run, and why not."""
    path: str
    ok: bool
    reason: str = ""
    defined: int = 0
    executed: int = None


def grade(path, defined, has_entry, returncode, stdout, stderr):
    """The verdict on one file, from what it defines and what it reported."""
    executed = executed_count(stdout, stderr)

    if defined and not has_entry:
        return Verdict(path, False, defined=defined, executed=executed, reason=(
            f"REFUSED silent-suite: {path} defines {defined} check(s) and "
            f"carries no `if __name__ == \"__main__\":` block.\n"
            f"  Run as `python3 {os.path.basename(path)}` it imports, defines "
            f"all {defined}, executes none and exits 0. That is indistinguishable "
            f"from a pass.\n"
            f"  Add a top-level `if __name__ == \"__main__\":` block that runs "
            f"them."))

    if returncode != 0:
        return Verdict(path, False, defined=defined, executed=executed, reason=(
            f"REFUSED silent-suite: {path} exited {returncode}.\n"
            f"  This is a red suite, not a silent one. Its own output is below."))

    if not defined:
        return Verdict(path, True, defined=0, executed=executed)

    if executed is None:
        return Verdict(path, False, defined=defined, executed=None, reason=(
            f"REFUSED silent-suite: {path} defines {defined} check(s) and its "
            f"run printed no count of what it executed.\n"
            f"  Nothing here says the checks ran, so nothing here says they "
            f"passed.\n"
            f"  Make the runner block print a total -- `unittest.main()` and "
            f"pytest both do."))

    if executed < defined:
        return Verdict(path, False, defined=defined, executed=executed, reason=(
            f"REFUSED silent-suite: {path} defines {defined} check(s) and "
            f"executed {executed}.\n"
            f"  {defined - executed} of them were never reached. The usual "
            f"cause is a check written BELOW the runner block, where the loader "
            f"cannot see it at the moment the block runs.\n"
            f"  Move the runner block to the end of the file."))

    return Verdict(path, True, defined=defined, executed=executed)


def discover(roots):
    """Every `test_*.py` under `roots`, ordered, cached copies left out.

    A root that does not exist raises rather than contributing nothing. A walk
    over a mistyped path returns an empty list and would otherwise read as a
    tree with no faults in it.
    """
    found = []
    for root in roots:
        if not os.path.isdir(root):
            raise FileNotFoundError(f"no such directory to walk: {root}")
        for base, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if name.startswith("test_") and name.endswith(".py"):
                    found.append(os.path.join(base, name))
    return sorted(found)


def run_one(path, timeout=600):
    """Run one file the way the ritual runs it: `python3 <basename>` from its
    own directory. The suites import siblings by relative path, so the working
    directory is part of the invocation and not a detail."""
    return subprocess.run(
        [sys.executable, os.path.basename(path)],
        cwd=os.path.dirname(path), capture_output=True, text=True,
        timeout=timeout)


def check(path, timeout=600):
    """Grade one file, running it.

    Every failure here becomes a refusal naming this file, never an exception.
    A traceback out of the middle of a walk exits non-zero, which reads like a
    refusal, and leaves every later file ungraded with nothing saying so.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
    except OSError as err:
        return Verdict(path, False, reason=(
            f"REFUSED silent-suite: cannot read {path}: {err}.\n"
            f"  A file this walker could not open is not a file that passed."),
            executed=None)
    try:
        defined = len(defined_tests(source, filename=path))
    except SyntaxError as err:
        return Verdict(path, False, reason=(
            f"REFUSED silent-suite: {path} will not parse: {err}.\n"
            f"  A file this reader cannot parse is not a file with no checks "
            f"in it."), executed=None)
    entry = has_entry_point(source)

    if defined and not entry:
        # Nothing can reach the checks, so running it proves nothing and its
        # exit code would be a zero that means nothing.
        return grade(path, defined, entry, 0, "", "")

    try:
        done = run_one(path, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Verdict(path, False, defined=defined, executed=None, reason=(
            f"REFUSED silent-suite: {path} timed out after {timeout} second(s) "
            f"and was killed.\n"
            f"  Nothing is asserted about its {defined} check(s). A suite that "
            f"never finished did not pass.\n"
            f"  Raise --timeout if the suite is honestly this slow."))
    return grade(path, defined, entry, done.returncode, done.stdout, done.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("roots", nargs="*", default=list(DEFAULT_ROOTS),
                        help="directories to walk (default: the two trees the "
                             "ritual names)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="seconds one file may take (default: 600)")
    args = parser.parse_args(argv)
    roots = args.roots or list(DEFAULT_ROOTS)

    try:
        paths = discover(roots)
    except FileNotFoundError as err:
        print(f"run_python_suites: {err}", file=sys.stderr)
        return 2

    if not paths:
        print(f"REFUSED empty-input: {', '.join(roots)} yields no `test_*.py` "
              f"file this walker could find.\n"
              f"  This is NOT a pass. A walk that ran nothing and a walk that "
              f"found no fault look alike, and reporting the second when the "
              f"first happened is the class this script exists to close.",
              file=sys.stderr)
        return 2

    refused, defined_total, executed_total = [], 0, 0
    for path in paths:
        verdict = check(path, timeout=args.timeout)
        defined_total += verdict.defined
        executed_total += verdict.executed or 0
        if verdict.ok:
            continue
        refused.append(verdict)
        print(verdict.reason, file=sys.stderr)

    if refused:
        print(f"\n{len(refused)} of {len(paths)} file(s) refused. Nothing about "
              f"the rest of this walk is asserted by that.", file=sys.stderr)
        return 1

    print(f"{len(paths)} file(s) walked, {defined_total} check(s) defined, "
          f"{executed_total} executed. Every file ran what it defines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
