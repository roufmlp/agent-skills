#!/usr/bin/env python3
"""Refuse to launch a run whose own commands are not in the TRACKED allow list.

## The 2 h 34 m this exists to stop

Run `414a-483-286335`, 2026-08-30. The permission classifier refused two plain
`npx vitest run` calls at 07:22 while the human slept, and allowed the identical
commands on retry at 09:56. The cause is measured: `Bash(npx vitest *)` was in
the MAIN checkout's `.claude/settings.local.json` and not in the run worktree's
copy of it.

    diff (run worktree allow list) (main checkout allow list)
    20a21
    > Bash(npx vitest *)

`.claude/settings.local.json` is gitignored (`.gitignore:31`). A worktree
therefore freezes that file on the day it was cut and never sees a rule added
afterwards. The run lost 2 h 34 m of wall clock, its single largest step, for a
25-line test.

## Why this checks the allow list and does NOT dry-run

The run's pre-flight DID dry-run `npx vitest` successfully at 04:00, and the
classifier still refused the same class at 07:22. **A class verified at launch is
not a class verified for the run.** A dry run proves the command works; it
proves nothing about what the classifier will decide three hours later, because
the classifier is not the thing the dry run consulted.

The tracked allow list IS that thing. A rule in `.claude/settings.json` is
checked before the classifier and short-circuits it, and git carries that file
into every worktree. So the question worth asking at launch is not "does this
command run" but "is this command's rule in a file this worktree can inherit".

## Two refusals

    untracked   a class covered only by `.claude/settings.local.json`, which a
                worktree freezes and which git does not carry. This is the exact
                shape of the 2 h 34 m.
    uncovered   a class in no allow list at all

Both exit 1. An unreadable settings file exits 2, because a check that cannot
see its input must not pass.

## Where it runs

At run launch, inside the run's own worktree, before the first issue is spawned.
`SKILL.md` step 0. It costs about one second and it reads two files.

## What it cannot see, and does not pretend to

A command no run has issued yet. The class list below is the set measured across
run `414a-483-286335`'s 55 transcripts, and it will go stale the day a run needs
something new. That is a smaller exposure than the one it closes: a new class
costs one prompt, and a class that used to work and silently stopped being
inherited costs a night.

Usage:

    python3 check_permission_floor.py --repo .
    python3 check_permission_floor.py --repo . --class "npx playwright test"

Exit 0 when every class is tracked, 1 on any refusal, 2 when a file is unreadable.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# One representative command per class the run actually issues, counted by
# command segment across run `414a-483-286335`'s 55 transcripts:
#
#     npx vitest 590   npx tsc 175   npm run lint 144   npm run build 68
#     npx eslint 15
#
# `npm test` and `npm run typecheck` are here although this run reached them
# through other spellings; every earlier run has used them and they cost
# nothing to cover.
REQUIRED = (
    "npx vitest run src/example.test.ts",
    "npx tsc --noEmit",
    "npx eslint src",
    "npm test",
    "npm run test",
    "npm run lint",
    "npm run typecheck",
    "npm run build",
)

# A project that isolates its runs outside git — a seeded workspace, a sign-in
# link, a lock wrapper around a live third-party suite, a teardown — runs those
# as unattended commands too, and every one needs a rule. They are the project's
# own, so they are NOT listed above: pass each as `--classes "<command>"`. The
# seed runs BEFORE this check in pre-flight, so a missing rule stops the launch
# here on the very next line rather than hours into an unattended run.

TRACKED = ".claude/settings.json"
LOCAL = ".claude/settings.local.json"

REMEDY = (
    "Add the missing rule to `.claude/settings.json`, which git carries into every\n"
    "worktree. Do NOT add it to `.claude/settings.local.json`: that file is gitignored\n"
    "at `.gitignore:31`, so a worktree freezes it on the day it was cut and a rule added\n"
    "later never reaches a run. That gap cost run `414a-483-286335` 2 h 34 m.\n"
    "\n"
    "An agent cannot make this edit — the auto-mode classifier refuses every write to\n"
    "`.claude/settings.json`, which is correct. Ask the human, and give them the exact lines."
)


def rules_in(path: pathlib.Path) -> list[str]:
    """Every `Bash(...)` allow rule in one settings file. Missing file, no rules."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"{path}: {error}") from error
    allow = ((data or {}).get("permissions") or {}).get("allow") or []
    return [one for one in allow if isinstance(one, str) and one.startswith("Bash(")]


def covers(rule: str, command: str) -> bool:
    """Does one `Bash(...)` rule admit this command?

    Claude Code matches a Bash rule by PREFIX when it ends in `*`, and exactly
    otherwise. The trailing space matters and is the trap worth knowing:
    `Bash(npx vitest *)` does NOT cover a bare `npx vitest`, because the rule's
    prefix is `npx vitest ` and the command is shorter than it. The local file
    carried exactly that spaced form.
    """
    body = rule[len("Bash(") : -1] if rule.endswith(")") else rule[len("Bash(") :]
    if body.endswith("*"):
        return command.startswith(body[:-1])
    return command == body


def judge(command: str, tracked: list[str], local: list[str]) -> tuple[str, str]:
    """Grade one class. Returns (verdict, the rule that covered it)."""
    for rule in tracked:
        if covers(rule, command):
            return "ok", rule
    for rule in local:
        if covers(rule, command):
            return "untracked", rule
    return "uncovered", ""


def suggest(command: str) -> str:
    """The narrowest rule that would cover this class."""
    parts = command.split()
    head = " ".join(parts[:3]) if parts[0] == "npm" and parts[1:2] == ["run"] else " ".join(parts[:2])
    return f'"Bash({head}*)"'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a run whose own commands are not in the tracked allow list."
    )
    parser.add_argument("--repo", default=".", help="the run's worktree. Defaults to cwd.")
    parser.add_argument(
        "--class",
        action="append",
        default=[],
        dest="classes",
        help="an extra command this run needs; repeat for each. Adds to the built-in set.",
    )
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.repo)
    try:
        tracked = rules_in(repo / TRACKED)
        local = rules_in(repo / LOCAL)
    except RuntimeError as error:
        print(f"REFUSED unreadable: {error}", file=sys.stderr)
        return 2

    wanted = list(REQUIRED) + list(args.classes)
    faults: list[tuple[str, str, str]] = []
    for command in wanted:
        verdict, rule = judge(command, tracked, local)
        if verdict != "ok":
            faults.append((verdict, command, rule))

    if not faults:
        print(
            f"ok: {len(wanted)} command class(es) checked, every one covered by "
            f"{repo / TRACKED}, which git carries into every worktree "
            f"({len(tracked)} tracked rule(s), {len(local)} local-only)."
        )
        return 0

    for verdict, command, rule in faults:
        if verdict == "untracked":
            print(
                f"REFUSED untracked: `{command}` is covered ONLY by {LOCAL}, "
                f"by the rule {rule}. A worktree cut tomorrow will not have it.",
                file=sys.stderr,
            )
        else:
            print(
                f"REFUSED uncovered: `{command}` is in no allow list, so the "
                "classifier decides it every time, on its own.",
                file=sys.stderr,
            )
        print(f"    add {suggest(command)} to {TRACKED}", file=sys.stderr)

    print(
        f"\n{len(faults)} of {len(wanted)} class(es) refused. "
        f"{len(tracked)} tracked rule(s), {len(local)} local-only.",
        file=sys.stderr,
    )
    print(f"\n{REMEDY}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
