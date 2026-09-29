#!/usr/bin/env python3
"""Retire every done row of a register, so the register holds only the inbox.

Issue 44 of tracker-tooling, cut by the human's ruling `q-h0925-seam-8`: done rows
(`verified`, `fixed`, and a merged direct-road `df-NN`) leave the register at
each finale and in `/daily-brief`, and the bug file keeps the record.

Promotion's `fixed` exit used to take a done row out. Issues 36 and 39 took
promotion out of `/parallel-hunt` and `/run-issues`, so without this script done
rows build up in the file the human reads as their inbox.

THE ROAD IS THE ONE PROMOTION BUILT. A register shard belongs to the tree that
wrote it (ruling 15), so nothing deletes a row. The script appends the row's id
to this tree's own `closed.md` shard, and `collect_shards.render` drops every
table row whose first cell is a closed id (`hides_closed=True` on `REGISTER`).
Reusing `closed` is the default of `q-h0925b-44-1`: one tracker already
holds 1,150 ids there, and a second name would be two roads doing one thing.

It only ever APPENDS. The finale and the brief can both meet one tree's shard,
and `collect_shards.py` records what a read-modify-write costs: "loses a row
exactly the way one shared register did".

Usage:
    retire_done_rows.py --feature F [--repo PATH] [--cwd PATH]
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "run-issues"))

from check_register_status import CLAIMS_DONE, rows, shape_fault  # noqa: E402  One walk, every grader.
from collect_shards import (  # noqa: E402
    CLOSED, CLOSED_LINE, REGISTER, ROW_ID, collect, hide_closed, list_worktrees, my_shard,
    render, reserved_names)

# A direct-road row: `df-` then a digit (`~/.claude/CLAUDE.md`, "prefix `df-NN`").
# `df0918-01` in one tracker's register is not one: it opens `df` with no hyphen.
DIRECT_ROAD = re.compile(r"^df-\d")


def _ids_in(path: str) -> set:
    """Every table row id `path` holds as a row's first cell."""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        return {found.group(1) for found in map(ROW_ID.match, handle) if found}


def merged(row_id: str, chosen: list, main_tree: str, feature: str) -> bool:
    """True when the main checkout's own copy of the row's shard holds the row.

    The default of `q-h0925b-44-2`. A direct-road merge puts the shard into
    main, and main's copy is the one `collect` keeps once the owning tree is
    gone. Reading git instead would need a branch name, and a `df-` row carries
    one only in prose.
    """
    for name, path in chosen:
        if name in reserved_names(REGISTER) or row_id not in _ids_in(path):
            continue
        holder = os.path.basename(os.path.dirname(path))
        main_copy = os.path.join(REGISTER.shards(main_tree, feature), holder, f"{name}.md")
        if row_id in _ids_in(main_copy):
            return True
    return False


def done_ids(chosen: list, main_tree: str, feature: str) -> tuple:
    """`(ids, held)`: the done rows to retire, and `(id, reason)` for each kept back.

    A row `check_register_status.shape_fault` names is held, never retired.
    `agents/promotion.md` ruled it: "Never resolve a row the check named." Run
    `batch-26c495` carried 28 rows reading `verified` whose notes ended `open`,
    and retiring those would hide live defects with no record in the register.

    A `df-` row waits, unheld and unreported, until its fix is merged: the
    direct road writes it at `verified` before the merge.

    Two more are held because the `closed` road cannot take them out cleanly,
    and this reads the road itself rather than listing the shapes it misses. An
    id that `hide_closed` still leaves on the board, or that `CLOSED_LINE` would
    not read back, would be appended again at every run. An id that also sits on
    a row at another word would take that row out too, because `hide_closed`
    drops every row carrying it.
    """
    text = render(chosen, board=REGISTER)
    board = list(rows(text))
    elsewhere = {row.row_id for row in board if row.status not in CLAIMS_DONE}
    ids, held = [], []
    for row in board:
        if row.status not in CLAIMS_DONE or row.row_id in ids + [h for h, _ in held]:
            continue
        if shape_fault(row):
            held.append((row.row_id, "check_register_status.py names its shape"))
        elif row.row_id in elsewhere:
            held.append((row.row_id, "the same id sits on a row nobody has built"))
        elif DIRECT_ROAD.match(row.row_id) and not merged(row.row_id, chosen, main_tree, feature):
            continue
        else:
            ids.append(row.row_id)
    left = {row.row_id for row in rows(hide_closed(text, set(ids)))}
    for found in list(ids):
        line = CLOSED_LINE.match(found)
        if found in left or not line or line.group(1) != found:
            ids.remove(found)
            held.append((found, "the closed shard cannot hold this id as written"))
    return ids, held


def append(path: str, ids: list) -> None:
    """Add `ids` to the end of `path`, one per line. The old bytes stay a prefix."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lead = ""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, "rb") as handle:
            handle.seek(-1, os.SEEK_END)
            lead = "" if handle.read(1) == b"\n" else "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(lead + "".join(f"{found}\n" for found in ids))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feature", required=True, help="the register's feature directory")
    parser.add_argument("--repo", help="checkout to enumerate; defaults to cwd")
    parser.add_argument("--cwd", default="", help="the tree whose shard is written; defaults to cwd")
    parser.add_argument("--trees", nargs="+", help="worktrees, main first; testing only")
    args = parser.parse_args(argv)

    trees = args.trees if args.trees else list_worktrees(args.repo)
    here = args.cwd or os.getcwd()
    target = my_shard(REGISTER, here, trees, args.feature, prefix=CLOSED, machinery=True)
    if not target:
        print(f"{here} is in no worktree of this repository, so no shard belongs "
              "to it. Pass the checkout to write from as --cwd.", file=sys.stderr)
        return 1

    ids, held = done_ids(
        collect(REGISTER, trees, args.feature), trees[0], args.feature)
    for found, reason in held:
        print(f"held: {found} reads done, but {reason}. Repair the row; it "
              "retires on the next run.", file=sys.stderr)
    if ids:
        append(target, ids)
    print(f"retired {len(ids)} row(s) into {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
