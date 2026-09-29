#!/usr/bin/env python3
"""Move gate verdicts out of issue files and into the runs that wrote them.

    python3 move_verdicts.py --issues <dir> [--min-bytes 100000] [--apply] [--no-git]

Issue 24 of the tracker-tooling set, fix F13 of the audit at
`.scratch/tracker-tooling/evidence/audit-2026-09-23-run-time-and-strikes/`.
Until 2026-09-23 both gates wrote their verdicts into the issue file, and every
implementer reads the whole file. One tracker's issue 53 reached 549 KB, 367 KB
of it verdicts. A gate now writes to `runs/<batch-id>/verdicts/`, and a write
guard, which this pack does not ship, refuses the old road where it is
installed. This moves what the old road left behind.

Each gate writes its own file (`q-fin-ea4cfa-05`): `<issue>-attempt-<N>-review.md`, `<issue>-attempt-<N>-verify.md`.
That ruling of 2026-09-27, built by issue 51 of the same set, means no gate can
overwrite another's, and that guard, where installed, refuses a gate the other
gate's file. This script still writes `<issue>-moved.md`, and it runs in the
main session, which no such guard refuses.

WHAT MOVES. A gate section: a level-two heading reading `Verify gate`, `Review
gate` or `Critical review gate`, with any qualifier `lib/check_verdict.py`
accepts, and everything to the next level-two heading. Headings inside a fence
are not headings. The implementation records, the strike-2 re-checks and the
spec stay.

WHERE IT GOES. `<feature>/runs/<batch-id>/verdicts/<issue>-moved.md`, appended,
byte for byte, in the file's order. The issue keeps one `## Gate verdicts, moved
out` section where the first moved section stood, naming each file.

WHICH RUN. The first of these that answers:

1. the heading names `batch-xxxxxx`;
2. the nearest `Implementation record` heading above it names one;
3. git: blame the heading line, find the commit on the checked-out branch's
   first-parent chain that brought it in, walk forward to the first merge, and
   read the batch off that merge's subject. The walk exists because one
   tracker's run `batch-2846b5` was fast-forwarded onto main and has no merge
   of its own.

A batch counts only where `runs/<batch-id>/run.md` exists and a row of its
status table names the issue.
Anything else stays in the issue file and is printed as KEPT. Road 3 can name
the wrong run where a commit made straight on the branch last touched a gate
heading; the ledger check is what catches most of that, not all of it.

It is a dry run unless `--apply` is given. It deletes nothing: every byte it
takes out of an issue file is appended to a `-moved.md` file first.

Drill: `test_move_verdicts.py` beside this file.
"""

import argparse
import bisect
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import check_verdict  # noqa: E402  the one reading of a heading and a fence

BATCH = re.compile(r"\b(?:batch|run-issues)-([0-9a-f]{6})\b")
ISSUE_ID = re.compile(r"^(\d+[a-z]*)-")
POINTER = "## Gate verdicts, moved out"


@dataclass
class Section:
    title: str
    start: int          # first line, zero-based
    end: int            # one past the last line
    batch: str = ""


@dataclass
class Plan:
    path: pathlib.Path
    issue_id: str
    lines: list
    moves: list = field(default_factory=list)
    kept: list = field(default_factory=list)


def is_gate_title(title):
    flat = check_verdict._flatten(title)
    if flat.startswith("critical "):
        flat = flat[len("critical "):]
    return (check_verdict._matches(flat, "verify gate")
            or check_verdict._matches(flat, "review gate"))


def gate_sections(text):
    """Every level-two gate section, in file order."""
    lines = text.splitlines(keepends=True)
    level_two = [(index, title) for index, depth, title
                 in check_verdict._headings(text) if depth <= 2]
    found = []
    for position, (index, title) in enumerate(level_two):
        if not is_gate_title(title) or not lines[index].startswith("## "):
            continue
        end = (level_two[position + 1][0] if position + 1 < len(level_two)
               else len(lines))
        found.append(Section(title=title, start=index, end=end))
    return found


def _batch_in(title):
    found = BATCH.search(title)
    return f"batch-{found.group(1)}" if found else None


def _names_issue(ledger_text, issue_id):
    """True when a row of the ledger's status table is this issue: a cell that
    is the id alone, or the id followed by a dash and its title. A bare number
    in prose is not a row, because a short id is also a duration or a count."""
    cell = re.compile(rf"^\**{re.escape(issue_id)}\**(?:\s+[—–-]\s|$)")
    for line in ledger_text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for part in line.strip().strip("|").split("|"):
            if cell.match(part.strip()):
                return True
    return False


def plan(path, blame):
    """What would move, and what would stay. `blame(line)` answers road 3 for a
    one-based line number, or None."""
    path = pathlib.Path(path)
    text = path.read_bytes().decode("utf-8")
    found = ISSUE_ID.match(path.name)
    issue_id = found.group(1) if found else path.stem
    runs = path.parent.parent / "runs"
    result = Plan(path=path, issue_id=issue_id,
                  lines=text.splitlines(keepends=True))

    records = [(index, title) for index, depth, title
               in check_verdict._headings(text)
               if depth <= 2 and check_verdict._flatten(title)
               .startswith("implementation record")]

    for section in gate_sections(text):
        batch = _batch_in(section.title)
        if batch is None:
            above = [title for index, title in records if index < section.start]
            batch = _batch_in(above[-1]) if above else None
        if batch is None:
            batch = blame(section.start + 1)
        ledger = runs / batch / "run.md" if batch else None
        if ledger is not None and ledger.is_file() and _names_issue(
                ledger.read_text(encoding="utf-8", errors="replace"), issue_id):
            section.batch = batch
            result.moves.append(section)
        else:
            result.kept.append(section)
    return result


def _repo_root(path):
    try:
        out = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip()
        return pathlib.Path(out)
    except (OSError, subprocess.CalledProcessError):
        return None


def _shown(target, root):
    try:
        return str(target.resolve().relative_to(root.resolve()))
    except (ValueError, AttributeError):
        return str(target)


def pointer_text(plan_, targets, today, root):
    counts = {}
    for section in plan_.moves:
        counts[section.batch] = counts.get(section.batch, 0) + 1
    lines = [
        POINTER + "\n", "\n",
        f"{len(plan_.moves)} gate verdict sections moved on {today}, byte for "
        "byte, to the runs that wrote them, by `run-issues/move_verdicts.py` "
        "(tracker-tooling issue 24). They are a record and grade nothing. A "
        "gate now writes to `runs/<batch-id>/verdicts/` and never here.\n", "\n",
    ]
    for batch in sorted(counts):
        word = "section" if counts[batch] == 1 else "sections"
        lines.append(f"- `{_shown(targets[batch], root)}`, "
                     f"{counts[batch]} {word}\n")
    lines.append("\n")
    return lines


def apply(plan_, today, root=None):
    """Write the move. Appends every section first, then rewrites the issue."""
    if not plan_.moves:
        return []
    root = root or _repo_root(plan_.path) or plan_.path.parent.parent.parent.parent
    runs = plan_.path.parent.parent / "runs"
    targets, chunks = {}, {}
    for section in plan_.moves:
        targets[section.batch] = (runs / section.batch / "verdicts"
                                  / f"{plan_.issue_id}-moved.md")
        chunks.setdefault(section.batch, []).append(
            "".join(plan_.lines[section.start:section.end]))

    for batch, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        header = ""
        if not target.exists():
            header = (
                f"# Issue {plan_.issue_id}, gate verdicts moved out of the issue "
                "file\n\n"
                f"Moved on {today} by `run-issues/move_verdicts.py` from "
                f"`{_shown(plan_.path, root)}`. Each section below is byte for "
                "byte what the issue file held, in its order. This is a record "
                "and it grades nothing.\n\n")
        with open(target, "ab") as handle:
            handle.write((header + "".join(chunks[batch])).encode("utf-8"))

    moved = set()
    for section in plan_.moves:
        moved.update(range(section.start, section.end))
    first = plan_.moves[0].start
    out = []
    for index, line in enumerate(plan_.lines):
        if index == first:
            out.extend(pointer_text(plan_, targets, today, root))
        if index not in moved:
            out.append(line)
    plan_.path.write_bytes("".join(out).encode("utf-8"))
    return sorted(targets.values())


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True).stdout


# One first-parent chain and one commit-to-batch answer per repository, shared by
# every issue file a run of this script reads.
_CHAINS = {}


def git_blame_batch(repo, path):
    """Road 3, as a function of a one-based line number."""
    repo = pathlib.Path(repo)
    key = str(repo.resolve())
    if key not in _CHAINS:
        chain = _git(repo, "rev-list", "--first-parent", "--reverse",
                     "HEAD").split()
        _CHAINS[key] = (chain, {c: i for i, c in enumerate(chain)}, {})
    chain, position, cache = _CHAINS[key]

    def is_ancestor(commit, descendant):
        return subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit,
             descendant], capture_output=True).returncode == 0

    def introduced_at(commit):
        if commit in position:
            return position[commit]
        # Ancestry along the chain is monotonic: once a chain commit holds
        # `commit`, every later one does.
        index = bisect.bisect_left(
            range(len(chain)), True,
            key=lambda i: is_ancestor(commit, chain[i]))
        return index if index < len(chain) else None

    def batch_of(commit):
        if commit in cache:
            return cache[commit]
        answer = None
        index = introduced_at(commit)
        if index is not None:
            for later in chain[index:]:
                parents = _git(repo, "rev-list", "--parents", "-n", "1",
                               later).split()
                if len(parents) > 2:
                    subject = _git(repo, "log", "-1", "--format=%s", later)
                    answer = _batch_in(subject)
                    break
        cache[commit] = answer
        return answer

    def blame(line):
        try:
            out = _git(repo, "blame", "--porcelain", "-L", f"{line},{line}",
                       "--", str(pathlib.Path(path).resolve()))
        except subprocess.CalledProcessError:
            return None
        commit = out.split()[0] if out else ""
        if not commit or set(commit) == {"0"}:
            return None
        return batch_of(commit)

    return blame


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issues", required=True,
                        help="the issues directory; runs/ sits beside it")
    parser.add_argument("--min-bytes", type=int, default=100_000)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-git", action="store_true",
                        help="skip road 3, the git blame")
    parser.add_argument("--today", default=None)
    args = parser.parse_args(argv)

    import datetime
    today = args.today or datetime.date.today().isoformat()
    issues = pathlib.Path(args.issues)
    root = _repo_root(issues / "x") if not args.no_git else None
    print("APPLY" if args.apply else "DRY RUN: nothing is written. Pass --apply.")
    moved_total = kept_total = 0
    for path in sorted(issues.glob("*.md")):
        size = path.stat().st_size
        if size < args.min_bytes:
            continue
        if args.no_git or root is None:
            blame = lambda line: None  # noqa: E731
        else:
            blame = git_blame_batch(root, path)
        try:
            result = plan(path, blame)
        except UnicodeDecodeError as error:
            print(f"SKIPPED {path.name}: not UTF-8 ({error})")
            continue
        moved_bytes = sum(len("".join(result.lines[s.start:s.end]).encode())
                          for s in result.moves)
        print(f"{path.name}: {size} bytes, {len(result.moves)} sections move "
              f"({moved_bytes} bytes), {len(result.kept)} kept")
        for section in result.moves:
            print(f"  move  line {section.start + 1:>5}  {section.batch}  "
                  f"{section.title}")
        for section in result.kept:
            print(f"  KEPT  line {section.start + 1:>5}  no run named  "
                  f"{section.title}")
        moved_total += len(result.moves)
        kept_total += len(result.kept)
        if args.apply:
            apply(result, today, root)
    print(f"total: {moved_total} sections move, {kept_total} kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
