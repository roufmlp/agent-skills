#!/usr/bin/env python3
"""Generate a board file from the shards its writers own, one shard per worktree.

The findings register and the decisions queue used to be one file each with one
live copy, in the main checkout, and every session wrote that path. Two sessions
that wrote it at once each read, modified and wrote, and the last writer won
with no error (ticket 38 of the pilot-delivery map, the one-run-per-feature
layout ticket, collision point 3). Nothing reported the loss.

So the content lives in shards now. Each writing worktree owns one shard, writes
it INSIDE its own tree and commits it on its own branch (ruling 15), and no
session writes by absolute path into another tree. `register.md` and
`decisions-queue.md` are generated from the shards (ruling 14) and a hand edit to
either is refused by `generated-file-guard.py` in the hooks.

Two rules, and both are here rather than in prose because prose does not refuse.

  Layout      `register.d/<tree>/<prefix>.md`. The directory names the worktree
              that owns the shard; the file names the writer inside it, by the
              row prefix it stamps its rows with (`rg454`, `vg412`, `ph10`).
              One file per writer, because two agents in ONE tree write at the
              same time — `/parallel-hunt` keeps its finder and its fixer in one
              worktree on purpose, and a run's two gates can run at once — and
              an agent writes with a read-modify-write edit, which loses a row
              exactly the way one shared register did.
  Ownership   A shard under `<tree>/` belongs to the worktree of that name.
              Every other copy is a snapshot: a tree cut from main carries
              everything main held at the cut, and a merged branch leaves its
              shards in main. Where the owning tree is gone — a run that merged
              and had its worktree removed — the main checkout's copy is the
              survivor and wins.
  Order       `00-history.md` first, then by tree and prefix. History first is
              what makes the first generation byte-for-byte identical to the
              file it replaces.

**The generated file is a pure concatenation and carries no header of its own.**
Ruling 14 says every existing citation of `register.md` stays true, and the live
file is cited by line: `register.md:1986` in the daily brief's applied log and
`register.md:16-19` in `scripts/watch-production.mjs`. One added line at the top
falsifies both. What says the file is generated is the refusal, not a banner —
a banner is a reminder, and `~/.claude/CLAUDE.md` rules that reminders do not
work.

Usage:
    collect_shards.py --kind register --feature example-feature [--repo PATH]
    collect_shards.py --kind queue [--repo PATH]
    collect_shards.py --kind register --feature F --check    # drift, exit 1
    collect_shards.py --kind register --feature F --mtime    # newest shard mtime
    collect_shards.py --kind register --feature F --my-shard # where to write
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from dataclasses import dataclass

GIT_TIMEOUT = 5  # seconds; a hung git surfaces as a note, never as a silent kill

# The shard that holds everything written before the split. First, always.
HISTORY = "00-history"
# The main checkout's own shard, for a session standing in it.
MAIN = "main"
# The daily brief's own shard. It holds ids, never items, and never renders.
ANSWERED = "answered"
# Promotion's own shard, the same shape: the register row ids it resolved.
CLOSED = "closed"

# A queue item's id: the last `q-...` token on its `## ` heading. Whole token,
# so `q-main-1` never answers `q-main-11`.
ITEM_ID = re.compile(r"`(q-[A-Za-z0-9][A-Za-z0-9._-]*)`")
# The same id in `answered.md`, where backticks are optional.
ANSWER_TOKEN = re.compile(r"(?<![\w-])(q-[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9])(?![\w-])")
SECTION = re.compile(r"^## ", re.MULTILINE)

# A register row:
# `| ID | summary | audience | severity | status | origin | owner-notes |`.
# The `origin` column arrived with ticket 37 ruling 7 on 2026-09-06; rows
# written before it have one cell fewer, and this pattern reads only the first.
# The id is the first cell, and only the first cell makes a line that row.
ROW_ID = re.compile(r"^\|\s*`?([A-Za-z][A-Za-z0-9._-]*)`?\s*\|")
# A closed id in `closed.md`: one id ALONE on its line, backticked or not. A
# register row id has no shape of its own the way a queue id's `q-` does, so a
# token matcher here reads every word promotion writes as an id. Measured
# 2026-09-05: "One ID per line." yields `ID`, and `ID` is the register's own
# table header, so every header row in the file disappeared.
CLOSED_LINE = re.compile(r"^\s*[-*]?\s*`?([A-Za-z][A-Za-z0-9._-]*)`?\s*$")


@dataclass(frozen=True)
class Generated:
    """A generated file and the shard directory beside it.

    `holder` is the directory holding both, relative to a worktree root, with
    `{feature}` where a per-feature board carries one.
    """

    kind: str
    holder: str
    name: str
    hides_answered: bool = False
    hides_closed: bool = False

    @property
    def shard_dir_name(self) -> str:
        """`register.md` -> `register.d`, the convention `.d` directories carry."""
        return self.name[: -len(".md")] + ".d"

    def directory(self, tree: str, feature: str = "") -> str:
        return os.path.join(tree, self.holder.format(feature=feature))

    def generated(self, tree: str, feature: str = "") -> str:
        return os.path.join(self.directory(tree, feature), self.name)

    def shards(self, tree: str, feature: str = "") -> str:
        return os.path.join(self.directory(tree, feature), self.shard_dir_name)


REGISTER = Generated("register", os.path.join(".scratch", "{feature}"), "register.md",
                     hides_closed=True)
QUEUE = Generated("queue", ".scratch", "decisions-queue.md", hides_answered=True)
GENERATED = {item.kind: item for item in (REGISTER, QUEUE)}


def list_worktrees(repo=None):
    """Every worktree of the repository, main checkout first, as git prints them.

    The same call `find_live_ledger.py` makes, and for the same reason: git is
    the only thing that knows which trees exist today.
    """
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


def tree_name(tree: str) -> str:
    """The shard name a worktree owns: its own directory name."""
    return os.path.basename(os.path.normpath(tree))


def writer_name(cwd: str, trees: list) -> str:
    """The shard the session standing in `cwd` writes.

    The main checkout writes `main`. A linked worktree writes its own name. A
    directory inside a tree names that tree, so no caller has to find the root
    itself. The longest matching tree wins, because every linked worktree sits
    under the main checkout and a prefix match alone would answer `main` for all
    of them — the same trap `find_live_ledger.py` records at its "A tree, not a
    prefix" rule.
    """
    here = os.path.realpath(cwd)
    best = ""
    for tree in trees:
        root = os.path.realpath(tree)
        if here == root or here.startswith(root + os.sep):
            if len(root) > len(best):
                best = root
    if not best:
        return ""
    if trees and os.path.realpath(trees[0]) == best:
        return MAIN
    return tree_name(best)


def _owner_tree(holder: str, trees: list) -> str:
    """The tree that owns the shards under `holder/`, or main as the survivor."""
    if holder == MAIN:
        return trees[0] if trees else ""
    for tree in trees[1:]:
        if tree_name(tree) == holder:
            return tree
    return trees[0] if trees else ""


def collect(board: Generated, trees: list, feature: str = "") -> list:
    """`(name, path)` for every live shard, in the order they concatenate.

    Every copy of a shard is found first, then its owning tree decides which
    one is read. A shard whose owning tree holds no copy falls back to the main
    checkout's, which is what a merged run leaves behind.
    """
    found = {}
    for tree in trees:
        pattern = os.path.join(board.shards(tree, feature), "*", "*.md")
        for path in glob.glob(pattern):
            holder = os.path.basename(os.path.dirname(path))
            name = os.path.basename(path)[: -len(".md")]
            found.setdefault((holder, name), {})[os.path.realpath(tree)] = path

    chosen = []
    for holder, name in sorted(found, key=lambda key: (key[1] != HISTORY, key)):
        copies = found[(holder, name)]
        owner = _owner_tree(holder, trees)
        path = copies.get(os.path.realpath(owner)) if owner else None
        if path is None and trees:
            path = copies.get(os.path.realpath(trees[0]))
        if path is None:
            continue  # Owned by a tree that is gone, with no copy in main.
        chosen.append((name, path))
    return chosen


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def answered_ids(chosen: list) -> set:
    """Every id the daily brief has marked answered, across the shards.

    An id counts wherever it appears in that shard, backticked or bare. The
    file holds ids and the date each was answered, and nothing else, so a
    looser read costs nothing and a stricter one would turn a stray backtick
    into an item that will not go away.
    """
    ids = set()
    for name, path in chosen:
        if name == ANSWERED:
            ids.update(ANSWER_TOKEN.findall(_read(path)))
    return ids


def closed_ids(chosen: list) -> set:
    """Every register row id promotion has resolved, across the shards."""
    ids = set()
    for name, path in chosen:
        if name != CLOSED:
            continue
        for line in _read(path).splitlines():
            found = CLOSED_LINE.match(line)
            if found:
                ids.add(found.group(1))
    return ids


def hide_closed(text: str, closed: set) -> str:
    """Drop every TABLE ROW whose own first cell is a closed id.

    Only the row. The register carries headings and paragraphs that name a row
    by id — promotion's own archive sections do — and those are the record of
    what happened to it.
    """
    if not closed:
        return text
    kept = []
    for line in text.splitlines(keepends=True):
        found = ROW_ID.match(line)
        if found and found.group(1) in closed:
            continue
        kept.append(line)
    return "".join(kept)


def item_id(section: str) -> str:
    """The id on a section's heading line, or empty when it carries none."""
    found = ITEM_ID.findall(section.split("\n", 1)[0])
    return found[-1] if found else ""


def split_items(text: str) -> list:
    """A shard's text as `## ` sections, with anything above the first kept.

    A `## ` inside a fenced code block is an example, not a heading. Queue
    items carry fenced commands, and splitting on one would let an answered
    item leave half of itself behind under no heading.
    """
    marks = []
    offset = 0
    fenced = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            marks.append(offset)
        offset += len(line)
    if not marks:
        return [text]
    bounds = [0] + marks + [len(text)]
    return [text[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]


def hide_answered(text: str, answered: set) -> str:
    """Drop every section whose id is answered. An item with no id always shows."""
    if not answered:
        return text
    kept = [part for part in split_items(text)
            if not (item_id(part) and item_id(part) in answered)]
    return "".join(kept)


def unmatched_answers(chosen: list) -> list:
    """Answered ids that match no item — a typo answers nothing, silently."""
    answered = answered_ids(chosen)
    if not answered:
        return []
    present = set()
    for name, path in chosen:
        if name in (ANSWERED, CLOSED):
            continue
        for part in split_items(_read(path)):
            found = item_id(part)
            if found:
                present.add(found)
    return sorted(answered - present)


def render(chosen: list, board: Generated = None) -> str:
    """The generated file's bytes: every shard in order, and nothing else.

    A shard that does not end in a newline gets one before the next shard
    starts, or its last row and the next shard's first row become one line. The
    LAST shard is emitted exactly as it sits, so a board that is one shard long
    reproduces the file it was split from byte for byte.

    The queue hides items the brief has answered, and the brief's `answered.md`
    shard never renders — it holds ids, not items.
    """
    hiding = bool(board and board.hides_answered)
    closing = bool(board and board.hides_closed)
    answered = answered_ids(chosen) if hiding else set()
    closed = closed_ids(chosen) if closing else set()
    reserved = {ANSWERED} if hiding else set()
    if closing:
        reserved.add(CLOSED)
    rendered = [(name, path) for name, path in chosen if name not in reserved]
    parts = []
    for index, (_, path) in enumerate(rendered):
        text = _read(path)
        if hiding:
            text = hide_answered(text, answered)
        if closing:
            text = hide_closed(text, closed)
        last = index == len(rendered) - 1
        if text and not text.endswith("\n") and not last:
            text += "\n"
        parts.append(text)
    return "".join(parts)


def drift(board: Generated, main_tree: str, trees: list, feature: str = "") -> str:
    """One sentence naming how the generated file differs from its shards.

    Empty when it matches. The hook refuses the writes it can see; this catches
    a write that never passed through it — an editor, another tool, a merge.
    """
    target = board.generated(main_tree, feature)
    expected = render(collect(board, trees, feature), board)
    try:
        with open(target, encoding="utf-8") as handle:
            found = handle.read()
    except OSError:
        return f"{target} is not there, and its shards hold {len(expected)} bytes."
    if found == expected:
        return ""
    return (
        f"{target} differs from its shards: {len(found)} bytes there, "
        f"{len(expected)} bytes across the shards. Regenerate it."
    )


def write(board: Generated, main_tree: str, trees: list, feature: str = "") -> str:
    """Generate the board into the main checkout. Returns the path written.

    An unchanged board is left alone. `/parallel-hunt` reads this file's mtime
    to decide a round is dead (`parallel-hunt/SKILL.md`, "Staleness is a FILE's
    mtime"), so touching it on an idle pass would report progress nobody made.
    """
    target = board.generated(main_tree, feature)
    chosen = collect(board, trees, feature)
    expected = render(chosen, board)
    found = None
    try:
        with open(target, encoding="utf-8") as handle:
            found = handle.read()
    except OSError:
        pass
    if found == expected:
        return target
    if not chosen and found:
        # Nothing to build from, and something to destroy. A shard filed under
        # the wrong holder, a worktree not yet listed, a --repo pointing
        # elsewhere: every one of them reaches here, and every one of them
        # would take the file with it.
        raise EmptyRefused(
            f"{target} holds {len(found)} bytes and no shard was found under "
            f"{board.shards(main_tree, feature)} or any worktree's copy of it. "
            "Writing would empty it, so nothing was written. Check which tree "
            "holds the shards.")
    # Through a temporary file and a rename, so a reader never sees half a
    # board. The register runs to thousands of lines and the daily brief reads
    # it while a run may be regenerating it.
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = f"{target}.tmp-{os.getpid()}"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(expected)
    os.replace(temporary, target)
    return target


def newest_shard_mtime(board: Generated, trees: list, feature: str = "") -> int:
    """The newest mtime across the live shards, or -1 when there are none.

    `/parallel-hunt` decides a round is dead when the register has not moved for
    an hour. Under generation the board's own mtime moves when the collector
    runs, which is not when the round moved, so the shards are what it must read.
    """
    stamps = []
    for _, path in collect(board, trees, feature):
        try:
            stamps.append(int(os.stat(path).st_mtime))
        except OSError:
            continue  # A tree removed, or a branch checked out, mid-walk.
    return max(stamps) if stamps else -1


def reserved_names(board: Generated) -> set:
    """Shard names this board reads as machinery rather than as content.

    A writer handed one of these loses everything it writes, silently: an
    `answered` or `closed` shard is read for ids and never rendered, and
    `00-history` sorts ahead of every other shard.
    """
    names = {HISTORY}
    if board.hides_answered:
        names.add(ANSWERED)
    if board.hides_closed:
        names.add(CLOSED)
    return names


def my_shard(board: Generated, cwd: str, trees: list, feature: str = "",
             prefix: str = "", machinery: bool = False) -> str:
    """The shard this session appends to. Empty when cwd is in no worktree.

    `prefix` is the row prefix the writer stamps its rows with, and it is what
    keeps two agents in one tree off one file. A writer with no prefix — a hand
    session, the production watcher — takes the tree's own name, which is one
    writer per tree and is true for them.

    `machinery` is for the two roles that own a reserved name on purpose: the
    daily brief's `answered` and promotion's `closed`. Everything else is
    refused one, because a writer that quietly loses its rows is the fault this
    file exists to remove.
    """
    holder = writer_name(cwd, trees)
    if not holder:
        return ""
    name = prefix or holder
    if os.sep in name or name in ("", ".", ".."):
        raise ValueError(
            f"{name!r} is not a shard name: a row prefix is one path segment.")
    if name in reserved_names(board) and not (machinery and name != HISTORY):
        raise ValueError(
            f"{name!r} is a reserved shard name on the {board.kind}: it is read "
            "for ids and never rendered. Everything written to it would "
            "disappear. Use your own row prefix.")
    tree = _owner_tree(holder, trees)
    return os.path.join(board.shards(tree, feature), holder, f"{name}.md")


class SplitRefused(Exception):
    """The one-off migration cannot run safely. The caller stops."""


class EmptyRefused(Exception):
    """The shards render to nothing over a file that holds something."""


def assign_ids(text: str) -> str:
    """Give every `## ` heading that lacks one a stable id, in file order.

    Ruling 18: an item the brief cannot name is an item it cannot answer, and
    every item written before this change carries no name. The id is appended
    to the heading LINE, so no line moves — `decisions-queue.md:518` is cited
    in `scripts/lib/what-is-owed.mjs` and every such citation has to keep
    landing.
    """
    parts = split_items(text)
    numbered = []
    counter = 0
    for part in parts:
        head, sep, rest = part.partition("\n")
        if not head.startswith("## ") or item_id(part):
            numbered.append(part)
            continue
        counter += 1
        numbered.append(f"{head.rstrip()} `q-h-{counter:03d}`{sep}{rest}")
    return "".join(numbered)


def split(board: Generated, tree: str, trees: list, feature: str = "") -> str:
    """Move the generated file into `00-history.md`. Once, per board.

    Everything written before the shards existed becomes one shard that sorts
    first, so the first regeneration reproduces the file byte for byte. The
    queue's items are given ids on the way through; the register's rows are
    not, because a row leaves by promotion rather than by being answered.
    """
    source = board.generated(tree, feature)
    try:
        text = _read(source)
    except OSError as error:
        raise SplitRefused(
            f"{source} is not there, so there is nothing to split: {error}")

    # Under the holder of the tree being split, not `main`. A history shard
    # filed under `main/` is looked for in the main checkout, and splitting a
    # worktree then renders nothing at all — measured on the live files,
    # 2026-09-05, where it wrote an empty register over 4,624 lines.
    holder = writer_name(tree, trees) or MAIN
    target = os.path.join(board.shards(tree, feature), holder, f"{HISTORY}.md")
    if os.path.exists(target):
        raise SplitRefused(
            f"{target} already exists. This board was split already, and a "
            "second split would bury every shard written since under a new "
            "history.")

    if board.hides_answered:
        text = assign_ids(text)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(text)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=sorted(GENERATED), required=True)
    parser.add_argument("--feature", default="", help="required for --kind register")
    parser.add_argument("--repo", help="checkout to enumerate; defaults to cwd")
    parser.add_argument("--cwd", default="", help="where the caller stands; defaults to cwd")
    parser.add_argument("--trees", nargs="+", help="worktrees, main first; testing only")
    parser.add_argument("--check", action="store_true", help="report drift, exit 1")
    parser.add_argument("--mtime", action="store_true", help="newest shard mtime, epoch seconds")
    parser.add_argument("--my-shard", action="store_true", help="the shard this session writes")
    parser.add_argument("--prefix", default="",
                        help="the row prefix this writer stamps, e.g. rg454")
    parser.add_argument("--machinery", action="store_true",
                        help="claim a reserved name: the brief's `answered`, "
                             "promotion's `closed`. Nothing else may.")
    parser.add_argument("--split", action="store_true",
                        help="one-off: move the generated file into 00-history.md")
    args = parser.parse_args(argv)

    board = GENERATED[args.kind]
    if board.holder.count("{feature}") and not args.feature:
        print(f"--feature is required for --kind {args.kind}: it names the "
              "directory the board sits in.", file=sys.stderr)
        return 1

    trees = args.trees if args.trees else list_worktrees(args.repo)
    if not trees:
        print("no worktree found — is this a git checkout?", file=sys.stderr)
        return 1
    main_tree = trees[0]

    if args.my_shard:
        try:
            path = my_shard(board, args.cwd or os.getcwd(), trees, args.feature,
                            args.prefix, args.machinery)
        except ValueError as refusal:
            print(f"REFUSED — {refusal}", file=sys.stderr)
            return 1
        if not path:
            print(f"{args.cwd or os.getcwd()} is in no worktree of this repository, "
                  "so no shard belongs to it. Stand in the checkout you are writing "
                  "from and reissue.", file=sys.stderr)
            return 1
        print(path)
        return 0

    if args.mtime:
        stamp = newest_shard_mtime(board, trees, args.feature)
        if stamp < 0:
            print(f"no shard under {board.shards(main_tree, args.feature)} or any "
                  "worktree's copy of it, so there is no mtime to read.",
                  file=sys.stderr)
            return 1
        print(stamp)
        return 0

    if args.split:
        # The tree the caller stands in, never `trees[0]`. The migration is a
        # commit on a branch like any other, and writing it into the main
        # checkout would land it in a tree somebody else may be holding open.
        here = args.cwd or os.getcwd()
        holder = writer_name(here, trees)
        if not holder:
            print(f"{here} is in no worktree of this repository, so there is no "
                  "tree to split. Stand in the checkout you mean and reissue.",
                  file=sys.stderr)
            return 1
        tree = _owner_tree(holder, trees)
        try:
            target = split(board, tree, trees, args.feature)
            # Regenerate the tree that was split, not the main checkout: the
            # migration is a commit on this branch and must not reach into
            # anybody else's working tree.
            written = write(board, tree, trees, args.feature)
        except (SplitRefused, EmptyRefused) as refusal:
            print(f"REFUSED — {refusal}", file=sys.stderr)
            return 1
        print(target)
        print(written)
        return 0

    if args.check:
        report = drift(board, main_tree, trees, args.feature)
        if report:
            print(report, file=sys.stderr)
            return 1
        return 0

    try:
        written = write(board, main_tree, trees, args.feature)
    except EmptyRefused as refusal:
        print(f"REFUSED — {refusal}", file=sys.stderr)
        return 1
    # A typo in the brief's shard answers nothing at all, silently, and the
    # same settled question then reaches the human a second time. Say so; never
    # stop over it.
    for stray in unmatched_answers(collect(board, trees, args.feature)):
        print(f"note: {stray} is marked answered and matches no item in "
              f"{written}. Check the id.", file=sys.stderr)
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
