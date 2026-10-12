#!/usr/bin/env python3
"""Read main's log for a fix of one red test before the run fixes it itself.

    python3 ~/.claude/skills/run-issues/check_main_fix.py --test <red test file> \
        [--repo <run tree>] [--base main]

The human's ruling `q-fin4a2388-06` of 2026-10-11, session walk of that day. On Sunday
11 October a test outside run `batch-4a2388` redded every light commit on the
calendar alone. The runner fixed it in its own gated commit (`80bb4c7a`) while main
fixed the same case a second way the same morning (`df-sn1011`), and both fixes rode
into the merge. The ruling: such a test takes one implementer and one review gate in
its own commit, with no carve, and before that fix starts the runner reads main's log
and takes main's fix where one exists. This script is that read, so it is a step
with an exit code rather than a sentence the runner must remember.

**What counts as main's fix.** A commit on `--base` that the run tree does not hold,
merges left out, and patch-equal cherry-picks dropped (`git log --cherry-pick
--right-only HEAD...<base>`), which either changes the red test file or names its
file name in the message. A fix in the code under test that names neither is not
seen; the review gate on the run's own fix is the net for that case.

**A test path the run tree does not hold is refused**, never read as "no fix on
main": a typo would otherwise send the runner down the implementer road.

Exit 0: main holds no fix; spawn the implementer road.
Exit 3: main holds one or more; each is printed oldest first, with the
        `git cherry-pick -x` command that takes them. No implementer.
Exit 2: no repository, no base, or no such test in HEAD; nothing asserted.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

NO_FIX = 0
NOTHING_ASSERTED = 2
MAIN_HOLDS_FIX = 3


class NothingToRead(Exception):
    pass


def git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if done.returncode:
        raise NothingToRead(done.stderr.strip() or f"git {' '.join(args)} failed")
    return done.stdout.strip()


def subject(repo: pathlib.Path, sha: str) -> str:
    return git(repo, "log", "-1", "--format=%s", sha)


def fixes(repo: pathlib.Path, test: str, base: str) -> list[tuple[str, str]]:
    """Main's commits the run tree lacks that change `test` or name it, oldest first."""
    span = ["log", "--no-merges", "--cherry-pick", "--right-only", "--format=%H", f"HEAD...{base}"]
    touched = set(git(repo, *span, "--", test).split())
    named = set(git(repo, *span, "-F", f"--grep={pathlib.PurePosixPath(test).name}").split())
    order = git(repo, *span[:-1], "--reverse", f"HEAD...{base}").split()
    return [(sha, subject(repo, sha)) for sha in order if sha in touched | named]


def relative(repo: pathlib.Path, test: str) -> str:
    """The test's path from the repository root, as git names it."""
    top = pathlib.Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    path = pathlib.Path(test)
    if path.is_absolute():
        return path.resolve().relative_to(top).as_posix()
    return path.as_posix()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--test", required=True, help="the red test file, from the repository root")
    parser.add_argument("--repo", default=".", help="the run tree (default: cwd)")
    parser.add_argument("--base", default="main", help="the branch the run forks from (default: main)")
    args = parser.parse_args(argv)
    repo = pathlib.Path(args.repo)

    try:
        test = relative(repo, args.test)
        git(repo, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
        try:
            git(repo, "cat-file", "-e", f"HEAD:{test}")
        except NothingToRead:
            raise NothingToRead(f"{test} is not in HEAD of {repo}: name the red file as git does")
        found = fixes(repo, test, args.base)
    except (NothingToRead, ValueError) as error:
        print(f"NOTHING ASSERTED: {error}", file=sys.stderr)
        return NOTHING_ASSERTED

    if not found:
        print(f"no fix on {args.base} for {test}: spawn one implementer and one review gate, "
              "own commit, no carve")
        return NO_FIX
    print(f"{args.base} holds {len(found)} fix(es) for {test}; take them, spawn no implementer:")
    for sha, line in found:
        print(f"  {sha[:12]}  {line}")
    print(f"\n  git cherry-pick -x {' '.join(sha[:12] for sha, _ in found)}")
    print("\nThen re-run the file. Green: ledger the row as taken from main. "
          "Still red: the implementer road, citing these commits.")
    return MAIN_HOLDS_FIX


if __name__ == "__main__":
    sys.exit(main())
