#!/usr/bin/env python3
"""Refuse a paste file whose confirmation query is commented out.

A paste file is the road a migration takes to a database no script may write
to. Where a repo guards its production ref in code, the migration is pasted
into the SQL editor by hand instead, and the confirmation query under it is the
only thing that says whether the migration landed.

**One run shipped two such files with that query behind `--`.** Both ended with
an instruction to run the query on its own, and the SQL under it commented out.
Pasted as written, a commented query returns no rows, no error and no output —
which reads exactly like a clean result.

It mattered most on the first of them, whose own reading rule was to COUNT the
rows before reading the words: ten rows was a pass, and nine meant a constraint
drop had committed while its re-add had not, leaving a column with no foreign
key at all. Nothing in that state reads `SET NULL`, so only the count catches
it, and a commented query gives nobody any rows to count.

Nine agents touched those two files, including a correction round on each. The
two paste files immediately before them both shipped a live query, so this was
a regression rather than the house shape.

Two refusals:

    commented-only   every `select` in the file is behind `--`, so the reader
                     pastes it and gets silence
    no-query         the file hands the reader no `select` at all, commented or
                     otherwise, so nothing confirms the migration landed

A third refusal, which is about the file's place rather than its content:

    untracked        git does not know this file, so it exists for the agent
                     that wrote it and for nobody else

**Run `batch-45c8b1`, 2026-09-02, wrote seven paste files and committed none of
them.** Seven gates ran this script over them and all seven exited 0, because
until now the script graded content alone. The finale caught all seven by hand
as finding F1. A paste file is the instruction the human follows at the SQL editor
after the merge, and an untracked file does not survive the merge — it is not in
the branch, so it is not in main, and the deploy goes out with the migration
unapplied and nothing to paste.

And one that is a contract, not a fault in the file:

    unreadable       the path names nothing this process can read

`no-query` is separated from `commented-only` on purpose. They want different
repairs: one is a comment marker to delete, the other is a query somebody has
to write and run. Reporting both as one refusal sends a reader looking for a
`--` that was never there. `untracked` is separated from both for the same
reason and takes its own exit code: its repair is `git add` and a commit, and
repairing a comment marker in a file nobody can pull repairs nothing.

**Tracked means the index holds it, which is what the human ruled on 2026-09-02.**
A file added but not yet committed reads as tracked here. That is deliberate:
the finale writes and commits paste files in the same round, so demanding a
commit at gate time would refuse a file that is about to be committed correctly.

Usage:

    python3 check_paste_file.py <path>...

Exit 0 when every file is tracked and hands the reader a runnable query, 1 on
any content refusal, 2 when a path could not be read or the tracking question
could not be asked, 3 when git does not know a file. 3 outranks 1: a reader
handed both faults repairs the tracking one first.
"""

import os
import re
import subprocess
import sys

# A statement the reader runs to see an answer. `select` is the only verb the
# repo's paste files have ever used for a confirmation, and widening this to
# every SQL verb would match the migration body itself, which is exactly what
# this check must not grade.
SELECT = re.compile(r"^\s*select\b", re.IGNORECASE)
COMMENTED_SELECT = re.compile(r"^\s*--+\s*select\b", re.IGNORECASE)

REMEDY = (
    "Delete the `--` in front of the confirmation query, paste the file into the QA\n"
    "SQL editor, and run the query there before this file reaches anyone. A query\n"
    "nobody has run is a claim, not a check."
)

TRACKING_REMEDY = (
    "Run `git add` on the file and commit it on this branch. A paste file the merge\n"
    "does not carry reaches nobody: the deploy goes out and the migration it names is\n"
    "never applied, with no file left for anyone to paste."
)

# What each ungradeable tracking answer says. Neither is a fault in the file, so
# both exit 2 with the rest of the checks that cannot see their input.
UNGRADEABLE = {
    "no-repository": (
        "this path sits in no git working tree, so the tracking question cannot be "
        "asked here at all."
    ),
    "no-git": "git is not on this machine, so the tracking question cannot be asked.",
}


def _git(args, cwd):
    """Run git and return its exit status, or None when git itself is missing.

    Output is dropped on purpose. Every question asked here is answered by the
    status alone, and reading stdout would invite a parser where a number does.
    """
    try:
        finished = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    return finished.returncode


def track_state(path, git=_git):
    """Does git know this file? Returns tracked, untracked, no-repository or no-git.

    Asked from the file's own directory rather than from the caller's, because a
    gate runs from the repo root in one run and from a worktree in the next, and
    the answer must be about the file.
    """
    directory = os.path.dirname(os.path.abspath(path)) or os.curdir
    name = os.path.basename(path)

    inside = git(["rev-parse", "--is-inside-work-tree"], directory)
    if inside is None:
        return "no-git"
    if inside != 0:
        return "no-repository"

    # `--error-unmatch` is what turns a silent empty listing into a status. Plain
    # `ls-files` exits 0 on a path it has never seen, which would pass every
    # untracked file this check exists to refuse.
    if git(["ls-files", "--error-unmatch", "--", name], directory) == 0:
        return "tracked"
    return "untracked"


def judge(text):
    """Grade one paste file. Returns (kind, detail) or None when it may ship."""
    live = []
    commented = []
    for number, line in enumerate(text.splitlines(), start=1):
        # Order matters: a commented select matches SELECT only after its `--`
        # is stripped, so test the commented form first and never both.
        if COMMENTED_SELECT.match(line):
            commented.append(number)
        elif SELECT.match(line):
            live.append(number)

    if live:
        return None
    if commented:
        lines = ", ".join(str(n) for n in commented)
        return "commented-only", (
            f"every `select` in this file is commented out (line(s) {lines}). "
            f"Pasted as written it returns no rows, no error and no output, which "
            f"reads exactly like a clean result."
        )
    return "no-query", (
        "this file carries no `select` at all. Nothing in it tells the reader "
        "whether the migration landed, and the reader cannot write that query "
        "for themselves at the SQL editor."
    )


def main(argv=None, track=track_state):
    paths = list(argv if argv is not None else sys.argv[1:])
    if not paths:
        print("usage: check_paste_file.py <path>...", file=sys.stderr)
        return 2

    refused = 0
    untracked = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as error:
            print(f"REFUSED unreadable: {path}: {error}", file=sys.stderr)
            return 2

        state = track(path)
        if state in UNGRADEABLE:
            print(
                f"REFUSED ungradeable-tracking: {path}: {UNGRADEABLE[state]}",
                file=sys.stderr,
            )
            return 2
        if state == "untracked":
            print(
                f"REFUSED untracked: {path}: git does not know this file, so it "
                f"exists for the agent that wrote it and for nobody else. The merge "
                f"cannot carry it and the reader will never see it.",
                file=sys.stderr,
            )
            untracked += 1

        verdict = judge(text)
        if verdict is None:
            # Only a file with neither fault gets the `ok` line. An `ok` printed
            # beside a refusal for the same path reads as a pass to a reader
            # skimming stdout, which is the whole failure this check closes.
            if state == "tracked":
                print(f"ok: {path} is tracked and hands the reader a runnable query")
        else:
            kind, detail = verdict
            print(f"REFUSED {kind}: {path}: {detail}", file=sys.stderr)
            refused += 1

    if untracked:
        print(f"\n{TRACKING_REMEDY}", file=sys.stderr)
    if refused:
        print(f"\n{REMEDY}", file=sys.stderr)

    # Tracking outranks content. Both remedies are printed above, so nothing is
    # hidden; the code names the repair that has to happen first.
    if untracked:
        return 3
    if refused:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
