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

## The 3 h 37 m it did NOT stop, and what changed

Run `batch-200d42`, 2026-09-11. This check printed `ok: 12 command class(es)
checked, every one covered by .claude/settings` and the run then lost 3 h 37 m of
its 9.22 hours to a permission modal on issue 441's verify gate. The command:

    cd <copy>/441-verify && export PATH=/opt/homebrew/bin:$PATH \
      && sed -n '806p' src/lib/suppliers/capability-repo.ts \
      && npx vitest run <two test files> 2>&1 | tail -20

`npx vitest*` WAS tracked. Two faults, both fixed here.

**The twelve classes were the RUNNER's.** The gates run a different set — the
private-copy recipe, the mutation drills, the checksum stamps, the http probe —
and nothing graded them. A floor that grades a list it wrote itself and prints
`ok` is reporting on its own list. `ROLE_CLASSES` now carries one list per role
and the output NAMES the roles it graded, plus `UNGRADED_ROLES`, the ones it did
not.

**A rule covering one segment of a compound command covers none of the others.**
The classifier admits a compound command only when every segment is admitted, and
`cd`, `export`, `sed` and `tail` were in no allow list. Grading was per-command;
it is now per-SEGMENT, through `segments()` and `judge_command()`.

Measured across batch-200d42's 18 gate transcripts: 1009 of 1011 gate Bash calls
carried at least one segment no tracked rule covered. Ten were refused outright.

## What it cannot see, and does not pretend to

A command no run has issued yet, and any role in `UNGRADED_ROLES`. The class lists
are the set measured across run `414a-483-286335`'s 55 transcripts and run
`batch-200d42`'s 18 gate transcripts, and they go stale the day a run needs
something new. That is a smaller exposure than the one they close: a new class
costs one prompt, and a class that used to work and silently stopped being
inherited costs a night.

**`RULED_UNCOVERED` is the honest half.** Those are measured gate shapes the human
ruled on 2026-09-12 must stay classifier-judged — database writes, arbitrary
execution, git writes. The check REPORTS them and refuses nothing over them,
because refusing would block every run. A gate that meets a refusal there takes
the closed road its brief already names: unprivileged path or report blocked,
never a retry.

Usage:

    python3 check_permission_floor.py --repo .
    python3 check_permission_floor.py --repo . --class "npx playwright test"

Exit 0 when every class is tracked, 1 on any refusal, 2 when a file is unreadable.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# One representative command per class each ROLE actually issues.
#
# The runner's set was counted by command segment across run `414a-483-286335`'s
# 55 transcripts: npx vitest 590, npx tsc 175, npm run lint 144, npm run build
# 68, npx eslint 15. `npm test` and `npm run typecheck` are here although that
# run reached them through other spellings; every earlier run has used them and
# they cost nothing to cover.
#
# The gate sets were counted the same way across one run's 18 gate transcripts
# -- 9 verify, 8 review, 1 review-critical, 1011 Bash calls. The shapes below are
# verbatim, with paths, file names and feature directories generalised. What is
# NOT here is in `RULED_UNCOVERED`.
ROLE_CLASSES: dict[str, tuple[str, ...]] = {
    "runner": (
        "npx vitest run src/example.test.ts",
        "npx tsc --noEmit",
        "npx eslint src",
        "npm test",
        "npm run test",
        "npm run lint",
        "npm run typecheck",
        "npm run build",
    ),
    "verify-gate": (
        # THE ANCHOR. The exact compound shape that halted one run for 3 h 37 m,
        # five variants of it, on one issue's verify gate.
        "cd <private copy>/441-verify && export PATH=/opt/homebrew/bin:$PATH"
        " && sed -n '806p' src/lib/example/repo.ts"
        " && npx vitest run src/app/example/editor.test.tsx"
        " src/lib/example/repo.page.test.ts 2>&1 | tail -20",
        # The full suite with coverage, which the gate brief makes its job.
        "cd <private copy>/441-verify && npx vitest run --coverage.enabled"
        " --coverage.provider=v8 --coverage.reporter=json --coverage.reportsDirectory=coverage"
        " --coverage.reportOnFailure=true 2>&1 | tail -40",
        # The checksum stamp both gate briefs require at open and at close.
        "shasum -a 1 src/lib/example/repo.ts | tee .scratch/example-feature/verify-441-open.sha256",
        "diff .scratch/example-feature/verify-441-open.sha256 .scratch/example-feature/verify-441-close.sha256",
        # Orientation off the ledger header and the issue file.
        "sed -n '1,120p' .scratch/example-feature/runs/batch-000000/run.md",
        "grep -n '^## ' .scratch/example-feature/issues/441-example.md",
        "cat src/lib/ui/save-failure.ts",
        "ls -la .scratch/example-feature/runs/batch-000000/",
        "wc -l .scratch/example-feature/runs/batch-000000/merge-briefing.md",
        "find src -name '*.test.ts' | head -20",
        # Driving the run's own dev server.
        'node scripts/http-probe.mjs "example" http://batch-000000.localhost:3101/app/example',
        "lsof -p 50264 | awk '$4==\"cwd\"{print $NF}'",
        "pgrep -f next-server",
        # The register shard, which the brief makes the only route for a finding.
        "python3 ~/.claude/skills/lib/collect_shards.py --kind register --feature example-feature --my-shard --prefix rv441",
        "env | sort | head -5",
        "date -u +%Y-%m-%dT%H:%M:%SZ",
    ),
    "review-gate": (
        # Reading the diff is this gate's whole job, and it reads it compound.
        "cd /home/user/project && sed -n '1,200p' src/lib/example/repo.ts | grep -n 'workspace_id'",
        "grep -rn 'revalidateExampleSurfaces' src/app/example/ | sort | cut -d: -f1 | tr -d ' '",
        "npm run typecheck 2>&1 | tail -20",
        "npm run lint 2>&1 | tail -20",
        "npx tsc --noEmit 2>&1 | tail -20",
        "npx eslint src 2>&1 | tail -20",
        "cd <private copy>/441-review && npx vitest run src/lib/example/repo.failed-read.test.ts 2>&1 | tail -20",
        "shasum -a 1 src/lib/example/repo.ts | tee .scratch/example-feature/review-441-close.sha256",
        "md5 -q src/lib/example/repo.ts",
        "stat -f %z src/lib/example/repo.ts",
        "head -50 src/lib/example/repo.ts",
        "tail -30 .scratch/example-feature/runs/batch-000000/run-journal.md",
        "python3 ~/.claude/skills/run-issues/check_register_status.py --feature example-feature",
        "python3 ~/.claude/skills/run-issues/check_briefing_commands.py --file .scratch/example-feature/runs/batch-000000/merge-briefing.md",
        "python3 ~/.claude/skills/lib/check_verdict.py --file .scratch/example-feature/issues/441-example.md",
        "printf '%s\\n' done",
        "echo '=== exit 0 ==='",
        "true",
    ),
    # The `-critical` variant ran the review gate's shapes and two of its own.
    # It is its own role here because a floor that folds it into another role
    # cannot tell a reader it was graded. There is NO `verify-gate-critical`:
    # `agents/` holds three run-issues gate briefs, not four.
    "review-gate-critical": (
        "cd /home/user/project && grep -rn 'service_role' src/ | head -20",
        "npm run typecheck 2>&1 | tail -20",
        "cd <private copy>/576-review && npx vitest run src/lib/example/repo.failed-read.test.ts 2>&1 | tail -20",
        "shasum -a 1 src/lib/example/repo.ts",
        "sed -n '300,340p' src/lib/example/repo.ts",
    ),
}

# Kept for the callers and cases that name it. The runner's list is still the
# runner's list.
REQUIRED = ROLE_CLASSES["runner"]

# Roles this check does NOT grade. Naming them is the point: a reader must be
# able to see what the `ok` line did not look at. Measured the same way -- these
# roles appear in the same run's transcripts and nobody has enumerated their
# shapes.
UNGRADED_ROLES: tuple[str, ...] = (
    "implementer",
    "implementer-escalated",
    "finale",
    "promotion",
    "general-purpose",
)

# Measured gate shapes ruled on 2026-09-12 to STAY classifier-judged. Reported at
# every launch, never a refusal: refusing here would block every run, and the
# ruling is that these should meet the classifier every time.
RULED_UNCOVERED: tuple[tuple[str, str], ...] = (
    (
        "psql \"$DATABASE_URL\" -c \"update ...\"",
        "23 segments. A psql rule sends SQL straight at the database and goes "
        "around the project's own write guard, which refuses a write to the "
        "customer-facing project. Widening past a control is the bypass the code "
        "rules forbid.",
    ),
    (
        "bash -s <<'EOF' ... EOF",
        "85 segments. A rule for `bash` is a rule for every command, which would "
        "make every other rule in the file decorative.",
    ),
    (
        "perl -0pi -e 's/a/b/' <file>",
        "32 segments. In-place edit of arbitrary source -- the mutation drill. "
        "Same objection as `bash`.",
    ),
    (
        "python3 - <<'PY' ... PY   /   node -e '<code>'",
        "69 segments. Arbitrary execution by another spelling.",
    ),
    (
        "git add / git commit",
        "2 segments, both from one review gate. A gate that commits is a finding, "
        "not a permission to grant.",
    ),
    (
        "git diff / git status / git show / git log / git rev-parse / git worktree",
        "152 segments, all reads. The largest remaining head. Not ruled in on "
        "2026-09-12 because tier A was the ruling; worth putting to the human again.",
    ),
    (
        "rsync / ln -sfn / cp / mkdir -p / rm -rf / chmod +x",
        "279 segments. The private-copy recipe and the drill teardown -- tier B, "
        "offered on 2026-09-12 and not taken. Each would need narrowing to the "
        "machine's temporary directory and the test cache rather than granted blanket.",
    ),
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
    """Does one `Bash(...)` rule admit this command SEGMENT?

    Three forms, and the difference between them has cost two nights.

    `Bash(cmd:*)` is Claude Code's documented prefix form and the `:` is a
    SEPARATOR, not a literal character: the rule admits `cmd` alone and
    `cmd <anything>`, and stops at the word boundary, so `Bash(cd:*)` does not
    admit `cdrecord`. Measured rather than assumed -- this repo's tracked
    `.claude/settings.json` carries `Bash(node scripts/http-probe.mjs:*)`, and
    batch-200d42's verify gates ran `node scripts/http-probe.mjs "<label>" <url>`
    seven times with no refusal. A literal reading would need that command to
    start with `...http-probe.mjs:`, and it does not.

    `Bash(cmd*)` matches the literal text before the `*` as a prefix. The
    trailing space is the trap worth knowing: `Bash(npx vitest *)` does NOT
    cover a bare `npx vitest`, because the rule's prefix is `npx vitest ` and
    the command is shorter than it. The local file carried exactly that spaced
    form, and that is the 2 h 34 m above.

    A rule with no `*` matches exactly.
    """
    body = rule[len("Bash(") : -1] if rule.endswith(")") else rule[len("Bash(") :]
    if body.endswith(":*"):
        head = body[:-2]
        return command == head or command.startswith(head + " ")
    if body.endswith("*"):
        return command.startswith(body[:-1])
    return command == body


# A segment that is nothing but one of these is shell punctuation, not a command.
KEYWORD_ONLY = frozenset({"do", "done", "then", "fi", "else", "elif", "esac", "in", "}", "{"})
# These lead a segment and the command follows them.
KEYWORD_LEAD = ("do ", "then ", "else ", "! ", "time ", "exec ")
LEADING_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s*")


def _without_heredocs(command: str) -> str:
    """Drop heredoc bodies. They are data the shell feeds a command, never
    commands themselves -- and one gate's `cat > drill.sh <<'SH'` body would
    otherwise be read as a dozen commands nobody ran."""
    kept: list[str] = []
    lines = command.split("\n")
    index = 0
    while index < len(lines):
        kept.append(lines[index])
        opener = re.search(r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?", lines[index])
        if opener:
            terminator = opener.group(1)
            index += 1
            while index < len(lines) and lines[index].strip() != terminator:
                index += 1
        index += 1
    return "\n".join(kept)


def segments(command: str) -> list[str]:
    """Split one Bash invocation into the pieces the classifier judges.

    The classifier admits a compound command only when EVERY piece is admitted.
    Grading the whole string against one rule is what let batch-200d42's
    `cd ... && export ... && sed ... && npx vitest ... | tail -20` through a
    floor that had `npx vitest*` tracked and nothing else in that line.
    """
    found: list[str] = []
    for piece in re.split(r"&&|\|\||;|\||\n", _without_heredocs(command)):
        piece = piece.strip().lstrip("(").strip()
        if piece in KEYWORD_ONLY:
            continue
        for lead in KEYWORD_LEAD:
            if piece.startswith(lead):
                piece = piece[len(lead) :].strip()
                break
        while True:
            stripped = LEADING_ASSIGNMENT.sub("", piece)
            if stripped == piece:
                break
            piece = stripped
        piece = piece.strip()
        if not piece or piece in KEYWORD_ONLY:
            continue
        found.append(piece)
    return found


def judge(command: str, tracked: list[str], local: list[str]) -> tuple[str, str]:
    """Grade one class. Returns (verdict, the rule that covered it)."""
    for rule in tracked:
        if covers(rule, command):
            return "ok", rule
    for rule in local:
        if covers(rule, command):
            return "untracked", rule
    return "uncovered", ""


def judge_command(command: str, tracked: list[str], local: list[str]) -> tuple[str, str, str]:
    """Grade one WHOLE Bash invocation, segment by segment.

    Returns `(verdict, the rule or the offending segment's rule, the segment
    the verdict belongs to)`. The command is only as covered as its worst
    segment, and `uncovered` outranks `untracked` so the reader is told the
    worse fault first.
    """
    first: tuple[str, str, str] | None = None
    untracked: tuple[str, str, str] | None = None
    for segment in segments(command):
        verdict, rule = judge(segment, tracked, local)
        if verdict == "uncovered":
            return "uncovered", "", segment
        if first is None:
            first = ("ok", rule, segment)
        if verdict == "untracked" and untracked is None:
            untracked = (verdict, rule, segment)
    return untracked or first or ("ok", "", "")


# Heads whose first two words are the class; anything else is a bare tool and
# its own name is the class.
MULTIWORD = frozenset({"npm", "npx", "node", "python3", "git", "psql", "uv"})


def suggest(command: str) -> str:
    """The narrowest rule that would cover this segment."""
    parts = command.split()
    if not parts:
        return '"Bash()"'
    if parts[0] == "export" and len(parts) > 1 and "=" in parts[1]:
        # `Bash(export:*)` would admit every environment variable there is.
        # The measured shape is `export PATH=...` and the rule says so.
        return f'"Bash(export {parts[1].split("=")[0]}=*)"'
    if parts[0] == "npm" and parts[1:2] == ["run"]:
        return f'"Bash({" ".join(parts[:3])}*)"'
    if parts[0] in MULTIWORD:
        return f'"Bash({" ".join(parts[:2])}*)"'
    return f'"Bash({parts[0]}:*)"'


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

    wanted: list[tuple[str, str]] = [
        (role, command) for role, shapes in ROLE_CLASSES.items() for command in shapes
    ]
    wanted += [("--class", command) for command in args.classes]

    faults: list[tuple[str, str, str, str, str]] = []
    for role, command in wanted:
        verdict, rule, segment = judge_command(command, tracked, local)
        if verdict != "ok":
            faults.append((verdict, role, command, segment, rule))

    roles = ", ".join(ROLE_CLASSES)
    ungraded = ", ".join(UNGRADED_ROLES)

    if not faults:
        print(
            f"ok: {len(wanted)} command class(es) checked across {len(ROLE_CLASSES)} role(s) "
            f"-- {roles} -- every segment covered by {repo / TRACKED}, which git carries "
            f"into every worktree ({len(tracked)} tracked rule(s), {len(local)} local-only)."
        )
        report_the_blind_spots(ungraded)
        return 0

    for verdict, role, command, segment, rule in faults:
        if verdict == "untracked":
            print(
                f"REFUSED untracked [{role}]: the segment `{segment}` is covered ONLY by "
                f"{LOCAL}, by the rule {rule}. A worktree cut tomorrow will not have it.",
                file=sys.stderr,
            )
        else:
            print(
                f"REFUSED uncovered [{role}]: the segment `{segment}` is in no allow list, "
                "so the classifier decides it every time, on its own.",
                file=sys.stderr,
            )
        if segment != command:
            print(f"    in: {command}", file=sys.stderr)
        print(f"    add {suggest(segment)} to {TRACKED}", file=sys.stderr)

    print(
        f"\n{len(faults)} of {len(wanted)} class(es) refused, across the role(s) {roles}. "
        f"{len(tracked)} tracked rule(s), {len(local)} local-only.",
        file=sys.stderr,
    )
    print(f"\n{REMEDY}", file=sys.stderr)
    report_the_blind_spots(ungraded, stream=sys.stderr)
    return 1


def report_the_blind_spots(ungraded: str, stream=None) -> None:
    """Say what this check did NOT look at.

    A floor that grades its own list and prints `ok` is evidence about the list
    and nothing else. Run batch-200d42 read `ok: 12 command class(es)` and then
    halted for 3 h 37 m on a thirteenth. These two blocks are the price of that
    sentence being honest.
    """
    stream = stream or sys.stdout
    print(f"\nROLES NOT GRADED: {ungraded}.", file=stream)
    print(
        "    Their command shapes have never been enumerated. This check says "
        "nothing about them.",
        file=stream,
    )
    print(
        f"\nRULED CLASSIFIER-JUDGED ({len(RULED_UNCOVERED)}): measured gate shapes the human "
        "ruled on 2026-09-12 must NOT be widened. Expect a refusal on each; a gate takes "
        "the closed road its brief names, never a retry.",
        file=stream,
    )
    for command, reason in RULED_UNCOVERED:
        print(f"    {command}", file=stream)
        print(f"        {reason}", file=stream)


if __name__ == "__main__":
    sys.exit(main())
