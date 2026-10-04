#!/usr/bin/env python3
"""Refuse an issue whose criteria name an e2e spec that is already red at the fork.

    python3 ~/.claude/skills/run-issues/fork_specs.py --tree <the run worktree> \\
        --harness "<RUN FACTS' Browser harness command; the spec is appended>" \\
        --ledger <run.md> --briefing <merge-briefing.md> \\
        --issue <path> [--issue <path> ...] [--override <id> ...]

The human's ruling `q-07853b-04` of 2026-10-01, fork F3 of run `batch-07853b`.
Issue 313's criterion 6 said `e2e/contrast-and-targets.spec.ts` passes. The
spec was already red at the fork `9587b5a8` in four cases, none of them a
picker 313 moved, so no diff could meet the criterion. The review gate graded
it `fault`, 313 stopped, and 315, 316, 317 and 314 stopped behind it: five of
the eight issues.

## What it does

1. Refuses, exit 3, a tree with uncommitted work outside run state: that tree
   is not the fork, and its reading would not be the fork's.
2. Reads every issue's `## Acceptance criteria` through `criteria_ids.py`, the
   reader `check_issue_ready.py` and `charge_round.py` use, and takes each
   path matching `SPEC` that a criterion names. Invariants are not read.
3. Runs each named spec once, whoever names it, through the harness, from the
   tree's root, with its whole output in `<ledger dir>/fork-specs/`. A spec
   absent at the fork is not run: the issue writes it.
4. A spec is green on exit 0 with at least one passed case and no failed one.
   Anything else is red: a failed case, a red exit with no case it can read,
   and a spec whose every case skipped (one project's `browserSkipReason()`
   turns a missing road into a green exit). One exception, below.
5. Refuses each issue that names a red spec, exit 1. It sets that issue's row
   in the ledger's status table to `blocked (fork spec red)`, and writes the
   spec and its red cases under `## Refused at the fork <sha>` in the ledger
   and the merge briefing. The other issues run.

## Which specs it runs

Every spec a criterion names that exists at the fork, not only the ones the
criterion calls passing. Of 14 criteria in one project naming an e2e spec on
2026-10-01, 12 used a pass word and 2 named a spec as a pattern to copy. A
reader of pass words is a list of spellings, and it passes the spelling it
missed. A red spec an issue copies from is worth knowing before spawn too.
Measured cost: about 35 s per spec (313's gate log).

## A spec that skips itself

A spec whose every case skipped, on exit 0, is not red when another spec in
the same reading passed a case. A missing road skips every spec that needs
it, so a passed case proves the road open, and the skip is the spec's own
gate. That spec is printed as `skipped`, and nothing is known about it.
Run `batch-471bd4`, fork `920c03a9`: issue 362's criterion 2 named
`e2e/fidelity-shots.spec.ts`, which skips unless `npm run fidelity:shots --
<row-id>` sets `FIDELITY_ROW`. Two other specs passed, and 362 was refused.
With no passed case anywhere in the reading, the skip stays red.

## The override

`--override <id>` runs a refused issue anyway, with the human's word, per issue.
The issue whose job is to turn a red spec green is the case for it. The
briefing still names the spec and its red cases, marked as overridden.

## Exits

0 every issue may run; 1 one or more issues refused; 3 nothing is known: the
tree is not the fork, an issue file will not open, or the harness cannot
start.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shlex
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import criteria_ids  # noqa: E402

REFUSED = 1
UNKNOWN = 3
RUN_STATE = (".scratch/",)
TIMEOUT = 900
EVERY_CASE_SKIPPED = "no case passed, every case skipped"
SPEC = re.compile(r"\be2e/[\w./-]*?\.spec\.[cm]?[jt]sx?\b")
ID_FROM_NAME = re.compile(r"^(\d+[a-z]?)(?:[-_.]|$)")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# Playwright's closing counts, as the list and line reporters print them.
COUNT = re.compile(r"^\s*(\d+) (failed|flaky|passed|skipped|did not run|interrupted)\b")
# A case under the `N failed` count: `[project] › file:line:col › title ───`.
CASE = re.compile(r"^\s*(?:\[[^\]]+\] › )?\S+:\d+:\d+ › (.+?)\s*─*\s*$")
BLOCKED = "blocked (fork spec red)"


def issue_id(path: pathlib.Path) -> str:
    found = ID_FROM_NAME.match(path.name)
    return found.group(1) if found else path.stem


def git(tree: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def named_specs(body: str) -> list[tuple[str, str]]:
    """(criterion name, spec) for every spec a criterion names, in order."""
    found = []
    for number, text in criteria_ids.criteria(body):
        for spec in SPEC.findall(text):
            if (f"C{number}", spec) not in found:
                found.append((f"C{number}", spec))
    return found


def read_spec(text: str, exit_code: int) -> tuple[bool, list[str], str, int]:
    """Whether the run is green, its red cases, why it is red, and how many
    cases passed."""
    counts: dict[str, int] = {}
    cases: list[str] = []
    in_failed = False
    for line in ANSI.sub("", text).splitlines():
        count = COUNT.match(line)
        if count:
            counts[count.group(2)] = int(count.group(1))
            in_failed = count.group(2) == "failed"
            continue
        case = CASE.match(line) if in_failed else None
        if case:
            cases.append(case.group(1))
    passed = counts.get("passed", 0)
    if exit_code == 0 and passed > 0 and not counts.get("failed"):
        return True, [], "", passed
    if cases:
        return False, cases, f"{len(cases)} red cases", passed
    if exit_code == 0 and counts.get("skipped", 0) > 0 and not passed:
        return False, [], EVERY_CASE_SKIPPED, passed
    if exit_code == 0:
        return False, [], "no case passed", passed
    return False, [], f"exit {exit_code} and no red case it can read", passed


def run_spec(command: list[str], tree: pathlib.Path, spec: str,
             log: pathlib.Path) -> tuple[bool, list[str], str, int]:
    """Run one spec through the harness, logged. Raises OSError when the
    harness cannot start."""
    try:
        done = subprocess.run([*command, spec], cwd=tree, capture_output=True,
                              text=True, timeout=TIMEOUT)
        text, exit_code = done.stdout + done.stderr, done.returncode
    except subprocess.TimeoutExpired as error:
        text = f"{error.stdout or ''}{error.stderr or ''}"
        if isinstance(text, bytes):
            text = text.decode(errors="replace")
        log.write_text(text, encoding="utf-8")
        return False, [], f"timed out after {TIMEOUT} s", 0
    log.write_text(text, encoding="utf-8")
    return read_spec(text, exit_code)


def append_once(path: pathlib.Path, heading: str, lines: list[str]) -> None:
    """Append the lines under the heading, skipping any already in the file."""
    text = path.read_text(encoding="utf-8")
    new = [line for line in lines if line not in text]
    if not new:
        return
    block = "" if heading in text else f"\n{heading}\n\n"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block + "\n".join(new) + "\n", encoding="utf-8")


def block_rows(ledger: pathlib.Path, ids: list[str]) -> list[str]:
    """Set each refused issue's status cell to BLOCKED, in the table under
    `## Status` only. Returns the ids it found no row for."""
    lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
    missing = list(ids)
    in_status = False
    for n, line in enumerate(lines):
        if line.startswith("## "):
            in_status = line.strip() == "## Status"
            continue
        cells = line.split("|")
        if not in_status or len(cells) < 5:
            continue
        issue = cells[2].strip()
        for one in ids:
            if re.match(rf"`?{re.escape(one)}\b", issue):
                cells[3] = f" {BLOCKED} "
                lines[n] = "|".join(cells)
                if one in missing:
                    missing.remove(one)
    ledger.write_text("".join(lines), encoding="utf-8")
    return missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tree", required=True, help="The run worktree, at the fork.")
    parser.add_argument("--harness", required=True,
                        help="The browser harness command; the spec path is appended.")
    parser.add_argument("--ledger", required=True, help="The run's run.md.")
    parser.add_argument("--briefing", required=True, help="The run's merge-briefing.md.")
    parser.add_argument("--issue", action="append", required=True, dest="issues")
    parser.add_argument("--override", action="append", default=[], dest="overrides",
                        help="An issue id to run anyway, with the human's word. Per issue.")
    args = parser.parse_args(argv)
    tree = pathlib.Path(args.tree).resolve()
    ledger, briefing = pathlib.Path(args.ledger), pathlib.Path(args.briefing)
    command = shlex.split(args.harness)

    try:
        fork = git(tree, "rev-parse", "--short=8", "HEAD")
        dirty = [line[3:] for line in git(tree, "status", "--porcelain",
                                          "--untracked-files=all").splitlines()
                 if not line[3:].strip('"').startswith(RUN_STATE)]
    except (subprocess.CalledProcessError, OSError) as error:
        print(f"REFUSED: git could not read {tree} ({error}). Nothing ran.")
        return UNKNOWN
    if dirty:
        print(f"REFUSED: {tree} is not the fork {fork}: it holds uncommitted work "
              f"in {', '.join(dirty[:5])}. Run this before spawn 1. Nothing ran.")
        return UNKNOWN

    wanted: dict[str, list[tuple[str, str]]] = {}
    for path in map(pathlib.Path, args.issues):
        try:
            body = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"REFUSED: issue file {path} will not open ({error}). Nothing ran.")
            return UNKNOWN
        wanted[issue_id(path)] = named_specs(body)

    logs = ledger.parent / "fork-specs"
    logs.mkdir(parents=True, exist_ok=True)
    readings: dict[str, tuple[bool, list[str], str, str]] = {}
    proof: list[str] = []
    for spec in dict.fromkeys(spec for pairs in wanted.values() for _, spec in pairs):
        if not (tree / spec).is_file():
            print(f"not run, absent at the fork {fork}; the issue writes it: {spec}")
            continue
        log = logs / (spec.replace("/", "__") + ".log")
        try:
            green, cases, why, passed = run_spec(command, tree, spec, log)
        except OSError as error:
            print(f"REFUSED: the harness `{args.harness}` could not start ({error}). "
                  f"Nothing is known about any spec.")
            return UNKNOWN
        readings[spec] = (green, cases, why, str(log))
        if passed:
            proof.append(spec)

    # A passed case anywhere, in a green spec or a red one, proves the road
    # open, so a spec that skipped every case skipped on its own gate. It is
    # neither green nor red.
    skipped = []
    for spec, (green, cases, why, log) in list(readings.items()):
        if why != EVERY_CASE_SKIPPED:
            continue
        if proof:
            skipped.append(spec)
            del readings[spec]
        else:
            readings[spec] = (green, cases, why + "; no spec in this reading passed a "
                              "case, so the road may be missing", log)
    for spec, (green, _cases, why, _log) in readings.items():
        print(f"{'green' if green else 'RED'} at the fork {fork}: {spec}"
              + ("" if green else f" ({why})"))
    for spec in skipped:
        print(f"skipped at the fork {fork}: {spec} (every case skipped while "
              f"{proof[0]} passed a case, so the skip is the spec's own gate; "
              f"nothing is known about it)")

    heading = f"## Refused at the fork {fork}"
    refused, lines = [], []
    for one, pairs in wanted.items():
        red = [(name, spec) for name, spec in pairs
               if spec in readings and not readings[spec][0]]
        if not red:
            continue
        overridden = one in args.overrides
        if not overridden:
            refused.append(one)
        for name, spec in red:
            _, cases, why, log = readings[spec]
            named = "; ".join(cases) if cases else "none named"
            lines.append(f"- {one} {name}: `{spec}` red at the fork {fork}, {why}: "
                         f"{named}. Log: {log}."
                         + (" Runs on the human's override." if overridden else
                            f" Status `{BLOCKED}`."))
        print(("OVERRIDDEN " if overridden else "REFUSED ") + one + ": "
              + "; ".join(f"{name} names `{spec}`, red at the fork: "
                          + ("; ".join(readings[spec][1]) or readings[spec][2])
                          for name, spec in red))

    if lines:
        append_once(ledger, heading, lines)
        append_once(briefing, heading, lines)
    if refused:
        missing = block_rows(ledger, refused)
        for one in missing:
            print(f"no status row for {one} in {ledger}: write it as `{BLOCKED}`.")
        print(f"\nREFUSED: {len(refused)} issue(s) name a spec already red at the fork. "
              f"Spawn none of them. The others run.")
        return REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
