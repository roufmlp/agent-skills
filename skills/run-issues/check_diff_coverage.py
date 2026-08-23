#!/usr/bin/env python3
"""Refuse a diff whose changed code no test executes.

The panel review of 2026-08-22 graded every mechanical check this pipeline
already owns and found one Priority 1 check with no existing equivalent:
changed-code coverage. `check_attempt_cap.py` counts attempts,
`check_verdict.py` grades a verdict's shape, `check_finale_stage.py` orders the
finale, `check_manifest_coverage.py` and `check_skill_drift.py` guard the
publication. Nothing anywhere asks whether the lines an issue changed were run
by anything at all.

The nearest thing on disk is prose. `run-issues/SKILL.md` orders one
`git diff --name-only <fork-point>..HEAD -- '*.test.ts'` at prep, and that
answers a different question: which test FILES this run has touched. A run can
satisfy it in full and still ship a new branch nobody executes.

Two refusals, because the sentence "changed code is covered by a test" holds
two separate claims and they fail apart:

    untested        the diff changes source and changes no test file
    uncovered       changed source lines the coverage report shows unexecuted

`untested` is diff-only and costs nothing. `uncovered` is the measured one and
needs a coverage report, so this script also refuses when it cannot grade:

    empty-diff      the range holds no changed file at all
    no-report       the coverage report named does not exist
    stale-report    a changed file on disk is newer than the report

Those three exit 2 rather than 1. A check that cannot see its input must say so
rather than pass. `run-issues/SKILL.md` already carries the general form of that
rule for worktree readiness: a green produced without dependencies on disk is a
false green, and this is the same fault one layer up.

**The threshold defaults to 100 and that is not severity theatre.** Every other
number is arbitrary and would be argued down once per run. One hundred percent
of CHANGED executable lines is the standing expectation of a pipeline whose
implementers work test-first; it says nothing about the rest of the file.
`--threshold` lowers it, and a lowered bar is printed in the output on the line
above the verdict, so a run that bought its green cheaply says so in its own log.

**Report formats: lcov and istanbul JSON.** lcov carries per-line hit counts
(`DA:<line>,<hits>`) and needs no interpretation. Istanbul's `coverage-final.json`
carries a statement map, and a statement counts as its START line, which is what
istanbul's own line metric does. No third format is supported, and a report this
cannot parse is a refusal, never a pass.

**Producing the report is the caller's job, and the project may not be able to
yet.** vitest 4, for one, ships no coverage provider: the report comes from a
separate `@vitest/coverage-v8` package. Where that is missing the `uncovered`
half cannot run, and this script refuses rather than inventing a number. The
`untested` half runs today against any repository with git.

Drill: `test_check_diff_coverage.py` breaks each refusal in front of a temporary
repository built for it. A guard nobody has watched go red is a claim, not a
check.

Exit codes: 0 graded and passed, 1 graded and refused, 2 could not grade.

    python3 check_diff_coverage.py --repo . --diff-range main..HEAD \\
        --coverage coverage/coverage-final.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

# What counts as source, and what counts as a test. Suffix and path shapes
# only: this runs against a TypeScript repo today and a Python one tomorrow,
# and neither list is a judgement about either.
SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py")

# A path is a test if any of these match. `tests/` and `__tests__/` catch the
# directory convention; the rest catch the file-naming one.
TEST_MARKS = (
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)__tests__/"),
    re.compile(r"\.test\.[cm]?[jt]sx?$"),
    re.compile(r"\.spec\.[cm]?[jt]sx?$"),
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"[^/]+_test\.py$"),
)

# Generated, vendored or declaration-only files. Changing one of these is not
# code somebody owes a test for, and grading them would teach the run to
# distrust the whole check.
EXCLUDE_MARKS = (
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.next/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"(^|/)coverage/"),
    re.compile(r"\.d\.ts$"),
    re.compile(r"(^|/)__pycache__/"),
)

REMEDY = {
    "empty-diff": (
        "Name a range that holds the work. An empty range graded green is a "
        "green that means no work was done."
    ),
    "no-report": (
        "Produce the report, then re-run. For a vitest repo: "
        "`npx vitest run --coverage.enabled --coverage.provider=v8 "
        "--coverage.reporter=json` writes coverage/coverage-final.json, and "
        "that needs the @vitest/coverage-v8 dev dependency."
    ),
    "unreadable-report": (
        "The file exists and does not parse as lcov or istanbul JSON. Check "
        "which reporter wrote it. Do not delete it and re-run without one."
    ),
    "stale-report": (
        "Re-run the suite with coverage. The report predates the code it is "
        "being asked to grade, so its silence about a changed line means "
        "nothing."
    ),
    "untested": (
        "Add or change a test in this diff. If the change genuinely cannot "
        "carry one, say which line of the issue file says so in the verdict."
    ),
    "uncovered": (
        "Cover the lines listed, or say in the verdict why each one cannot be "
        "reached. Lowering --threshold is visible in this output and in the "
        "run log."
    ),
}


@dataclass
class Problem:
    """One refusal, in the words the session reading it needs."""

    kind: str
    detail: str
    lines: list[str] = field(default_factory=list)


@dataclass
class Changed:
    """The diff, split the way the two refusals need it."""

    source: dict[str, set[int]] = field(default_factory=dict)
    tests: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return not self.source and not self.tests and not self.other


def is_excluded(path: str) -> bool:
    return any(mark.search(path) for mark in EXCLUDE_MARKS)


def is_test(path: str) -> bool:
    return any(mark.search(path) for mark in TEST_MARKS)


def is_source(path: str) -> bool:
    """Source is a code suffix that is neither a test nor generated."""
    if is_excluded(path) or is_test(path):
        return False
    return path.endswith(SOURCE_SUFFIXES)


def parse_diff(text: str) -> Changed:
    """Collect ADDED lines per file, numbered in the new file.

    Deleted lines are not collected: a line that is gone cannot be executed,
    and asking a coverage report about it would refuse every deletion.
    """
    changed = Changed()
    path: str | None = None
    new_line = 0
    for raw in text.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                path = None
                continue
            path = target[2:] if target.startswith(("a/", "b/")) else target
            if is_source(path):
                changed.source.setdefault(path, set())
            elif is_excluded(path):
                path = None
            elif is_test(path):
                changed.tests.append(path)
            else:
                changed.other.append(path)
            continue
        if path is None:
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            new_line = int(match.group(1)) if match else 0
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            if path in changed.source:
                changed.source[path].add(new_line)
            new_line += 1
        elif raw.startswith(" "):
            new_line += 1
        # A '-' line moves nothing in the new file.
    return changed


def read_diff(repo: pathlib.Path, diff_range: str | None, diff_file: str | None) -> str:
    if diff_file:
        if diff_file == "-":
            return sys.stdin.read()
        return pathlib.Path(diff_file).read_text(encoding="utf-8", errors="replace")
    result = subprocess.run(
        ["git", "diff", "--unified=0", diff_range],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return result.stdout


def drop_empty(hits: dict[str, dict[int, int]]) -> dict[str, dict[int, int]]:
    """Discard file entries that map no line at all.

    A file that maps nothing is indistinguishable from a file whose every
    changed line is a brace, and the second reading passes. The first test run
    of this script found exactly that: `{"src/a.ts": {"lines": 3}}` is not an
    istanbul report, and it graded a diff fully covered. Dropping the entry
    here turns that input into `no SF:`/`no statementMap` at the reader, which
    refuses. The cost is a real source file holding zero statements, which then
    reads as absent from the report and refuses too — the safe direction, and
    visible in the output rather than silent.
    """
    return {path: lines for path, lines in hits.items() if lines}


def parse_lcov(text: str) -> dict[str, dict[int, int]]:
    """`SF:` opens a file, `DA:<line>,<hits>` is one line's hit count."""
    hits: dict[str, dict[int, int]] = {}
    current: dict[int, int] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("SF:"):
            current = hits.setdefault(line[3:], {})
        elif line.startswith("DA:") and current is not None:
            number, _, count = line[3:].partition(",")
            try:
                current[int(number)] = current.get(int(number), 0) + int(count)
            except ValueError:
                continue
        elif line == "end_of_record":
            current = None
    return drop_empty(hits)


def parse_istanbul(data: dict) -> dict[str, dict[int, int]]:
    """A statement counts as its START line, which is istanbul's own rule."""
    hits: dict[str, dict[int, int]] = {}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        path = entry.get("path") or key
        statements = entry.get("statementMap") or {}
        counts = entry.get("s") or {}
        per_line = hits.setdefault(path, {})
        for statement_id, span in statements.items():
            start = (span or {}).get("start") or {}
            number = start.get("line")
            if not isinstance(number, int):
                continue
            count = counts.get(statement_id, 0)
            per_line[number] = per_line.get(number, 0) + (count or 0)
    return drop_empty(hits)


def read_coverage(path: pathlib.Path) -> dict[str, dict[int, int]]:
    """Return {path: {line: hits}}. Raises ValueError on an unreadable report."""
    text = path.read_text(encoding="utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"not valid JSON: {error}") from error
        if not isinstance(data, dict) or not data:
            raise ValueError("JSON holds no file entries")
        hits = parse_istanbul(data)
        if not hits:
            raise ValueError("JSON has no statementMap; not an istanbul report")
        return hits
    hits = parse_lcov(text)
    if not hits:
        raise ValueError("no SF: records; not an lcov report")
    return hits


def index_by_relative(hits, repo: pathlib.Path) -> dict[str, dict[int, int]]:
    """Re-key a report on repo-relative paths, so diff paths can find it.

    Reports carry absolute paths, repo-relative paths, or `./` prefixed ones
    depending on the reporter. Matching on the tail after the repo root covers
    all three without guessing at any of them.
    """
    root = str(repo.resolve())
    out: dict[str, dict[int, int]] = {}
    for path, lines in hits.items():
        key = path
        try:
            resolved = str(pathlib.Path(path).resolve())
        except OSError:
            resolved = path
        if resolved.startswith(root + "/"):
            key = resolved[len(root) + 1 :]
        elif key.startswith("./"):
            key = key[2:]
        merged = out.setdefault(key, {})
        for number, count in lines.items():
            merged[number] = merged.get(number, 0) + count
    return out


def newest_change(repo: pathlib.Path, paths) -> tuple[str | None, float]:
    """The most recently written changed file still on disk, and its mtime."""
    newest_path, newest = None, 0.0
    for path in paths:
        candidate = repo / path
        try:
            stamp = candidate.stat().st_mtime
        except OSError:
            continue  # Deleted or renamed away: it cannot make the report stale.
        if stamp > newest:
            newest_path, newest = path, stamp
    return newest_path, newest


def audit(
    repo: pathlib.Path,
    diff_text: str,
    coverage_path: pathlib.Path,
    threshold: float,
) -> tuple[list[Problem], dict]:
    """Grade one diff. Returns (problems, facts) so the caller can render both."""
    changed = parse_diff(diff_text)
    facts = {
        "source_files": sorted(changed.source),
        "test_files": sorted(changed.tests),
        "other_files": sorted(changed.other),
        "threshold": threshold,
        "changed_lines": sum(len(v) for v in changed.source.values()),
        "covered_lines": 0,
        "graded": False,
    }

    if changed.empty():
        return [Problem("empty-diff", "the range holds no changed file at all")], facts

    # Refusal one, diff-only: source moved and no test moved with it.
    if changed.source and not changed.tests:
        return (
            [
                Problem(
                    "untested",
                    "this diff changes source and changes no test file",
                    [f"    {path}" for path in sorted(changed.source)],
                )
            ],
            facts,
        )

    if not changed.source:
        return [], facts  # Tests or prose only. Nothing to measure, and that is honest.

    # Refusal two, measured: needs a report that exists, parses, and is fresh.
    if not coverage_path.exists():
        return [Problem("no-report", f"no coverage report at {coverage_path}")], facts
    try:
        hits = read_coverage(coverage_path)
    except ValueError as error:
        return [Problem("unreadable-report", f"{coverage_path}: {error}")], facts

    report_stamp = coverage_path.stat().st_mtime
    newest_path, newest = newest_change(repo, changed.source)
    if newest_path and newest > report_stamp:
        return (
            [
                Problem(
                    "stale-report",
                    f"{newest_path} is newer than {coverage_path.name}",
                    [
                        f"    changed file mtime: {newest:.0f}",
                        f"    report mtime:       {report_stamp:.0f}",
                    ],
                )
            ],
            facts,
        )

    by_relative = index_by_relative(hits, repo)
    facts["graded"] = True
    misses: list[str] = []
    covered = 0
    total = 0
    for path in sorted(changed.source):
        numbers = changed.source[path]
        if not numbers:
            continue
        per_line = by_relative.get(path)
        if per_line is None:
            total += len(numbers)
            misses.append(f"    {path}: absent from the report, {len(numbers)} lines")
            continue
        for number in sorted(numbers):
            hit_count = per_line.get(number)
            if hit_count is None:
                continue  # Not an executable statement; blank lines and braces.
            total += 1
            if hit_count > 0:
                covered += 1
            else:
                misses.append(f"    {path}:{number}")

    facts["changed_lines"] = total
    facts["covered_lines"] = covered
    if total == 0:
        return [], facts  # Every changed line was non-executable. Say nothing false.

    percent = 100.0 * covered / total
    if percent + 1e-9 < threshold:
        return (
            [
                Problem(
                    "uncovered",
                    f"{covered} of {total} changed lines executed "
                    f"({percent:.1f}%, threshold {threshold:.1f}%)",
                    misses,
                )
            ],
            facts,
        )
    return [], facts


def render(problems: list[Problem], facts: dict) -> str:
    threshold = facts.get("threshold", 100.0)
    lines: list[str] = []
    if threshold < 100.0:
        lines.append(
            f"THRESHOLD LOWERED to {threshold:.1f}%: this green was bought below "
            "the standing bar of 100% of changed lines."
        )
    if not problems:
        if facts.get("graded"):
            lines.append(
                f"OK: {facts['covered_lines']} of {facts['changed_lines']} changed "
                f"lines executed, across {len(facts['source_files'])} source file(s)."
            )
        elif facts.get("source_files"):
            lines.append("OK: every changed line is non-executable.")
        else:
            lines.append(
                "OK: this diff changes no source file. "
                f"({len(facts.get('test_files', []))} test file(s), "
                f"{len(facts.get('other_files', []))} other file(s).)"
            )
        return "\n".join(lines)

    for problem in problems:
        lines.append(f"REFUSED {problem.kind}: {problem.detail}")
        lines.extend(problem.lines)
        lines.append(f"  {REMEDY[problem.kind]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a diff whose changed code no test executes."
    )
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to cwd.")
    parser.add_argument(
        "--diff-range",
        default=None,
        help="A git range, e.g. main..HEAD. Read with --unified=0.",
    )
    parser.add_argument(
        "--diff-file",
        default=None,
        help="Read a unified diff from this file instead of git. '-' is stdin.",
    )
    parser.add_argument(
        "--coverage",
        default="coverage/coverage-final.json",
        help="lcov or istanbul JSON report. Absent is a refusal, never a pass.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=100.0,
        help="Percent of changed executable lines that must run. Default 100.",
    )
    args = parser.parse_args(argv)

    if not args.diff_range and not args.diff_file:
        print(
            "REFUSED no-range: name --diff-range or --diff-file. This script "
            "grades one diff and will not guess which one.",
            file=sys.stderr,
        )
        return 2

    repo = pathlib.Path(args.repo)
    try:
        diff_text = read_diff(repo, args.diff_range, args.diff_file)
    except (OSError, RuntimeError) as error:
        print(f"REFUSED no-diff: {error}", file=sys.stderr)
        return 2

    problems, facts = audit(
        repo, diff_text, pathlib.Path(args.coverage), args.threshold
    )
    output = render(problems, facts)
    if not problems:
        print(output)
        return 0
    print(output, file=sys.stderr)
    ungradeable = {"empty-diff", "no-report", "unreadable-report", "stale-report"}
    return 2 if problems[0].kind in ungradeable else 1


if __name__ == "__main__":
    sys.exit(main())
