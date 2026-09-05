#!/usr/bin/env python3
"""Find the live /run-issues ledgers, and pick the one the current directory owns.

Run state is keyed by batch id: `.scratch/<feature>/runs/<batch-id>/run.md`,
with `primer.md`, `merge-briefing.md` and `run-journal.md` beside it (ticket 38
of the pilot-delivery map, the one-run-per-feature layout ticket, ruling 10,
2026-09-05). A hunt is a run for isolation (the same ticket, ruling 22, sitting
4): its ledger is `.scratch/<feature>/round-brief.md` in the hunt's own
worktree, carrying the same header lines, written at launch and deleted at
round end. Both kinds are read here under one rule, and every listing carries
the kind. Any number of runs can hold
state at once, so this script no longer returns "the" ledger. It has three modes:

  (default)   Resume. Print the ledger whose `Worktree:` line names the tree the
              current directory is in, exit 0. From the main checkout, or from a
              tree no live run owns, list the live runs by batch id on stderr
              and exit 1 (ruling 11). Nothing is picked by count: one live run
              seen from the main checkout is still a listing, not a choice.
  --list      Every live ledger, one per line: batch id, ledger path, worktree,
              kind (`run` or `hunt`), tab separated. Exit 0, even with zero
              lines. This is what the machine-preflight hook counts and what
              the daily brief re-reads. A hunt's brief holds no issue rows.
  --overlap   A comma-separated issue range. Exit 1 naming the live run that
              already holds any of them (ruling 21). Whole-id match, leading
              zeros ignored, so `34` never matches `345` and `05` is `5`. Only
              runs are searched: a brief's prose carries numbers that are not
              issue ids.

Every worktree carries its own copies. On 2026-08-16 that was twelve copies of
which one was live. Run state is committed, so every worktree branched from that
commit carries a copy frozen at whatever the ledger said when it branched.

Two things decide it, and neither is a timestamp:

  Where:     a live copy is either the one in the MAIN checkout, which is where
             `SKILL.md` tells a run to keep its ledger, or one whose `Worktree:`
             line names the tree it is sitting in. Every other copy is a
             snapshot — never resume from one, never write to one.
  Owner:     a named session is live, and `none — HALTED` is live too, because a
             halt is exactly what `resume` resumes. `none — awaiting-merge`,
             `none — merged` and a missing line are finished paperwork.

The `Worktree:` line was the whole rule until 2026-08-19, when a live run refused
to resume. `SKILL.md` puts run state in the main checkout, so the live ledger sits
there and its `Worktree:` line names the run's own tree — a different path, which
the old rule read as a snapshot. Under that rule a ledger written where the
skill says to write it could never be selected. The line still says which run
owns the ledger; it stopped saying where the ledger lives.

Never pick by timestamp. On one measured chase the freshest ledger belonged to an
already-merged run and chasing it cost 25 minutes.

Exit 0 prints exactly one path on stdout. Exit 1 prints what it found on stderr
and chooses nothing — a launch-time stop, before anything is spawned, is not a
mid-run stall.

Two more rules, both from the 2026-09-05 review of this file:

  One run is one ledger. A run can be live in the main checkout AND in its own
  tree, and both shapes are admissible on purpose, so live copies are deduped by
  batch id, the main copy preferred. Otherwise one run filled a two-run ceiling.
  A tree, not a prefix. Every linked worktree sits under the main checkout, so
  "cwd is under the named tree" is not ownership. Ownership is: the worktree
  cwd sits in, read off `git worktree list`, IS the tree the ledger names.

Usage:
    find_live_ledger.py [--repo /path/to/checkout]
    find_live_ledger.py --list [--repo ...]
    find_live_ledger.py --overlap 533,546 [--repo ...]
"""

import argparse
import glob
import os
import re
import dataclasses
import subprocess
import sys
from dataclasses import dataclass

HEAD_LINES = 60
GIT_TIMEOUT = 5  # seconds; a hung git must surface as a note, never as a silent kill

# An issue id: digits with an optional letter suffix (`557b`, `262a`).
ISSUE_ATOM = r"\d{1,4}[a-z]?"
# One id or a numeric range, standing alone in prose (not inside a time like
# 13:45, a date, a sha, or a longer word).
ISSUE_OR_RANGE = re.compile(
    r"(?<![\w.:])(" + ISSUE_ATOM + r")(?:-(\d{1,4}))?(?![\w.:-])")
SCOPE_TOKEN = re.compile(r"^(" + ISSUE_ATOM + r")(?:-(\d{1,4}))?$")
BATCH_MARK = re.compile(r"`([^`]*)`")
TABLE_SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
OVERRIDE_WORDS = ("force-machine", "force-version", "force-model")


@dataclass(frozen=True)
class Candidate:
    """One `run.md` copy, reduced to the lines the selector reads."""

    path: str
    tree: str
    worktree_line: str | None
    owner_line: str | None
    scope_text: str = ""
    is_main: bool = False
    batch: str = ""
    title_batch: str = ""
    kind: str = "run"


def parse_worktree_value(line):
    """The path a `Worktree:` line names, or None. The ledger writes backticks."""
    if not line:
        return None
    value = line.split(":", 1)[1] if ":" in line else ""
    value = value.strip().strip("`").strip()
    value = value.rstrip("/")
    return value or None


def is_admissible_owner(line):
    """True when the owner line describes a run that still has somewhere to go.

    A named session is live. `none — HALTED ...` is live, because a halt is what
    resume resumes. Owner lines are prose, so only a line whose first word after
    `none` IS "halted" counts; the word appearing later in a finished line
    ("awaiting-merge ..., after the halted finale was revived") does not.
    """
    if not line:
        return False
    value = line.split(":", 1)[1] if ":" in line else ""
    value = value.strip()
    if not value:
        return False
    lowered = value.lower().lstrip("*`_ ")
    if not lowered.startswith("none"):
        return True
    rest = lowered[len("none"):].lstrip(" \t—–-*`_")
    return rest.startswith("halted")


def names_own_tree(candidate):
    """True when this copy's `Worktree:` line names the tree it sits in."""
    named = parse_worktree_value(candidate.worktree_line)
    if not named:
        return False
    return os.path.realpath(named) == os.path.realpath(candidate.tree)


def is_live_copy(candidate):
    """True when this copy is somewhere a run actually keeps its ledger."""
    return candidate.is_main or names_own_tree(candidate)


def live_ledgers(candidates):
    """Every live RUN, one candidate each, in batch order of first sight.

    A run may be live in the main checkout and in its own tree at once; the
    main copy is the one returned. A candidate with no batch (hand-built) is
    kept as itself.
    """
    chosen = {}
    for c in candidates:
        if not (is_live_copy(c) and is_admissible_owner(c.owner_line)):
            continue
        key = c.batch or c.path
        if key not in chosen or (c.is_main and not chosen[key].is_main):
            chosen[key] = c
    return list(chosen.values())


def _expand(start, end):
    """`316`,`318` -> 316, 317, 318 at the width of `start`; a bad range is []."""
    if not end:
        return [start]
    if not start.isdigit() or int(end) < int(start):
        return []
    return [str(n).zfill(len(start)) for n in range(int(start), int(end) + 1)]


def _add(ids, found):
    for one in found:
        if one not in ids:
            ids.append(one)


def parse_scope_ids(text):
    """The issue ids a ledger holds, in order.

    Two sources, read in this order: the title line (`# Run ledger — 533, 546
    (run batch-x)`, ranges expanded) and the status table's `Issue`
    column, which every ledger carries, plus any `Scope` line. The fenced batch id is cut before the
    title is read, and only the first cell of a table row is an issue, so a
    clock time or a note cell never reads as one.
    """
    ids = []
    lines = (text or "").splitlines()
    prose = [lines[0]] if lines and lines[0].startswith("#") else []
    prose += [line for line in lines[:HEAD_LINES] if line.startswith("Scope")]
    for line in prose:
        _add(ids, [i for s, e in ISSUE_OR_RANGE.findall(BATCH_MARK.sub(" ", line))
                   for i in _expand(s, e)])
    column = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or TABLE_SEPARATOR.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if column is None:
            lowered = [c.lower() for c in cells]
            if "issue" in lowered:
                column = lowered.index("issue")
            continue
        if column < len(cells):
            cell = cells[column].strip("`* ")
            if re.fullmatch(ISSUE_ATOM, cell):
                _add(ids, [cell])
    return ids


MODELS_WORD = "models:"


def split_models(text):
    """`(scope_text, map_text)` around the `models:` word (ticket 39, ruling 5).

    The map is typed after the issue list, so everything from `models:` on is
    the map and nothing before it is. The word is matched on its own, case
    folded; a second one is map text, not a second split, because the map
    grammar reports its own bad tokens and a silent re-split would hide one.
    Returns `map_text` of `None` when the word is absent, which is not the same
    as an empty map: absent means "read the default file", empty means "the
    word was typed with nothing after it", and the launch refuses the latter.
    """
    words = (text or "").split()
    for index, word in enumerate(words):
        if word.lower() == MODELS_WORD:
            return " ".join(words[:index]), " ".join(words[index + 1:])
    return " ".join(words), None


def parse_scope_argument(text):
    """`/run-issues <scope>` grammar, shared by the hook and the launch.

    Returns `(ids, bad)`. Forms (SKILL.md, "Scope argument"): `05`, `05-09`,
    `13c 20 14 22`, `all`; commas are separators; override words are neither.
    A token the grammar cannot read goes into `bad` rather than being dropped,
    because a dropped token is a launch the overlap guard never saw.

    The scope ENDS at the `models:` word (ticket 39, ruling 5). Without that
    the map's own tokens land in `bad`, and `machine-preflight.py` refuses
    every launch that carries a map -- measured on this file 2026-09-05.
    """
    scope_text, _ = split_models(text)
    ids, bad = [], []
    for word in scope_text.replace(",", " ").split():
        if word in OVERRIDE_WORDS:
            continue
        if word == "all":
            ids.append("all")
            continue
        match = SCOPE_TOKEN.match(word)
        expanded = _expand(match.group(1), match.group(2)) if match else []
        if expanded:
            _add(ids, expanded)
        else:
            bad.append(word)
    return ids, bad


def _issue_key(issue):
    """`05` and `5` are one issue; `557b` stays itself."""
    match = re.fullmatch(r"(\d+)([a-z]?)", issue.strip().lower())
    if not match:
        return issue.strip().lower()
    return f"{int(match.group(1))}{match.group(2)}"


def overlapping(candidates, issues):
    """`[(candidate, [held issue, ...]), ...]` for every live run holding any of `issues`.
    Hunts hold none, and a brief's prose carries numbers that are not issue ids."""
    wanted = {_issue_key(i) for i in issues if i.strip()}
    if not wanted:
        return []
    hits = []
    for c in runs(candidates):
        held = [own for own in parse_scope_ids(c.scope_text) if _issue_key(own) in wanted]
        if held:
            hits.append((c, held))
    return hits


def journal_for(ledger_path):
    """The append-only journal beside a ledger.

    A run keeps `run-journal.md` in its own `runs/<batch-id>/` directory
    (SKILL.md, "Run state"). A hunt keeps `round-journal.md` beside
    `round-brief.md` (parallel-hunt/SKILL.md:86). This file owns the layout, so
    it owns this too: two hooks needed the answer in sitting 2 of ticket 39 and
    each grew its own copy, which the review of 2026-09-05 refused.
    """
    return os.path.join(
        os.path.dirname(ledger_path),
        "round-journal.md" if os.path.basename(ledger_path) == "round-brief.md"
        else "run-journal.md")


def live_ledger_for(cwd):
    """`(path, text)` for the live ledger this directory belongs to, or None.

    None is the answer for every ordinary session on this machine: no live run
    owns the tree. `(path, None)` means a ledger was found and could not be
    read, which is a fault its caller reports rather than acting on.

    This walks the worktrees, so it costs a `git worktree list`. Every caller
    judges whether it cares BEFORE calling it.
    """
    worktrees = list_worktrees(cwd)
    candidates = collect_candidates(worktrees=worktrees)
    path, _ = select_ledger(candidates, cwd, worktrees)
    if not path:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return path, handle.read()
    except OSError:
        return path, None


def tree_of(path, worktrees):
    """The worktree `path` sits in, or None. Linked trees nest under the main
    checkout, so the deepest matching root wins, not the first."""
    real = os.path.realpath(path)
    best = None
    for tree in worktrees:
        root = os.path.realpath(tree)
        if real == root or real.startswith(root.rstrip(os.sep) + os.sep):
            if best is None or len(root) > len(os.path.realpath(best)):
                best = tree
    return best


def _describe(candidates):
    lines = []
    for c in candidates:
        named = parse_worktree_value(c.worktree_line) or "no Worktree: line"
        owner = (c.owner_line or "NO OWNER LINE").strip()
        where = "main checkout" if c.is_main else "linked worktree"
        batch = c.batch or "(no batch)"
        lines.append(f"  {batch}  {c.path}  [{where}]\n    {owner}\n    Worktree: {named}")
    return "\n".join(lines)


def select_ledger(candidates, cwd, worktrees):
    """Return (path, None) for the live ledger whose run owns `cwd`, else (None, reason).

    The ledger's `Worktree:` line names the run's tree. When the worktree `cwd`
    sits in IS that tree, that run is the one being resumed. From any other
    tree there is nothing to pick: the listing is the answer, and a human
    chooses by changing directory (ticket 38, ruling 11).
    """
    live = live_ledgers(candidates)
    if not live:
        return None, (
            "No live ledger found. Every copy examined is a snapshot (it "
            "sits in a linked worktree and its Worktree: line names another "
            "tree) or finished paperwork (no owner line, or "
            "awaiting-merge/merged).\n"
            f"Examined {len(candidates)} copies:\n{_describe(candidates)}"
        )

    here = tree_of(cwd, worktrees)
    owned = [
        c for c in live
        if here and parse_worktree_value(c.worktree_line)
        and os.path.realpath(parse_worktree_value(c.worktree_line)) == os.path.realpath(here)
    ]
    if len(owned) == 1:
        return owned[0].path, None
    if len(owned) > 1:
        return None, (
            f"{len(owned)} live ledgers name the tree {here}. Choosing "
            f"between them needs a human.\n{_describe(owned)}"
        )
    return None, (
        f"{len(live)} live ledger{'s' if len(live) != 1 else ''}, and "
        f"{here or cwd} is not a tree any of them names. Resume from inside "
        "the run's own worktree; nothing is picked by count or by freshness.\n"
        f"{_describe(live)}"
    )


def list_worktrees(repo=None):
    """Every worktree of the repository, main checkout first, as git prints them."""
    cmd = ["git"]
    if repo:
        cmd += ["-C", repo]
    cmd += ["worktree", "list", "--porcelain"]
    listing = subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT
    ).stdout
    return [
        line[len("worktree "):].strip()
        for line in listing.splitlines() if line.startswith("worktree ")
    ]


def main_checkout(repo=None, worktrees=None):
    """The main checkout: the first tree `git worktree list` prints."""
    trees = worktrees if worktrees is not None else list_worktrees(repo)
    return trees[0] if trees else None


def collect_candidates(repo=None, worktrees=None):
    """Every `.scratch/*/runs/*/run.md` and every `.scratch/*/round-brief.md`
    under every worktree of this repository.

    The old fixed name, `.scratch/<feature>/run.md`, is not a ledger any more
    and is not read (ticket 38, ruling 9: no old path keeps working). A round
    brief is a hunt's ledger (ruling 22, sitting 4): its id is the fenced
    `hunt-` token on its title line, since it has no directory named after it,
    and it is never committed, so no tree carries a snapshot of another's.
    """
    trees = worktrees if worktrees is not None else list_worktrees(repo)
    candidates = []
    main_real = os.path.realpath(trees[0]) if trees else None
    for tree in trees:
        is_main = os.path.realpath(tree) == main_real
        pattern = os.path.join(tree, ".scratch", "*", "runs", "*", "run.md")
        for path in sorted(glob.glob(pattern)):
            batch = os.path.basename(os.path.dirname(path))
            candidates.append(_read(path, tree, is_main, batch))
        for path in sorted(glob.glob(os.path.join(tree, ".scratch", "*", "round-brief.md"))):
            brief = _read(path, tree, is_main, "", kind="hunt")
            candidates.append(dataclasses.replace(brief, batch=brief.title_batch))
    return candidates


def hunts(candidates):
    """The live hunts among `candidates`. Liveness has one rule for both kinds."""
    return [c for c in live_ledgers(candidates) if c.kind == "hunt"]


def runs(candidates):
    """The live runs among `candidates`."""
    return [c for c in live_ledgers(candidates) if c.kind == "run"]


def mismatched(candidates):
    """Ledgers whose fenced title id names a different batch than their directory."""
    return [
        c for c in candidates
        if c.title_batch and c.batch and c.title_batch != c.batch
    ]


def _read(path, tree, is_main=False, batch="", kind="run"):
    owner = worktree = None
    title_batch = ""
    text = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        print(f"warning: cannot read {path}: {error}", file=sys.stderr)
    lines = text.splitlines()
    for index, line in enumerate(lines[:HEAD_LINES]):
        if index == 0:
            fenced = [m for m in BATCH_MARK.findall(line)
                      if m.startswith("batch-") or m.startswith("hunt-")]
            title_batch = fenced[0] if fenced else ""
        elif owner is None and line.startswith("Owner:"):
            owner = line
        elif worktree is None and line.startswith("Worktree:"):
            worktree = line
    return Candidate(path, tree, worktree, owner, text, is_main, batch, title_batch, kind)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="checkout to enumerate; defaults to cwd")
    parser.add_argument(
        "--list", action="store_true",
        help="print every live ledger (batch, path, worktree, kind; tab separated) and exit 0")
    parser.add_argument(
        "--overlap",
        help="comma-separated issue ids; exit 1 naming any live run that holds one")
    args = parser.parse_args(argv)

    try:
        worktrees = list_worktrees(args.repo)
        candidates = collect_candidates(worktrees=worktrees)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", None) or error
        print(f"Cannot enumerate worktrees: {detail}".strip(), file=sys.stderr)
        return 1

    wrong = mismatched(candidates)
    if wrong:
        for c in wrong:
            print(
                f"REFUSED: {c.path} sits in {c.batch} but its title names "
                f"{c.title_batch}. One run, one id: fix the title or the directory.",
                file=sys.stderr)
        return 1

    if args.list:
        for c in live_ledgers(candidates):
            tree = parse_worktree_value(c.worktree_line) or c.tree
            print(f"{c.batch}\t{c.path}\t{tree}\t{c.kind}")
        return 0

    if args.overlap:
        issues = [part.strip() for part in args.overlap.split(",") if part.strip()]
        hits = overlapping(candidates, issues)
        if not hits:
            return 0
        for c, held in hits:
            print(
                f"REFUSED: live run {c.batch} already holds {', '.join(held)} "
                f"({c.path}).", file=sys.stderr)
        print(
            "Two implementers on one issue is the collision ticket 38, the "
            "one-run-per-feature layout ticket, exists to remove. Drop those "
            "issues from the range, or wait for that run.",
            file=sys.stderr)
        return 1

    path, reason = select_ledger(candidates, os.getcwd(), worktrees)
    if path:
        print(path)
        return 0
    print(reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
