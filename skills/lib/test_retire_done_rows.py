#!/usr/bin/env python3
"""Tests for `retire_done_rows.py`, issue 44 of tracker-tooling.

Every test builds its own temporary tree, as `TreeFixture` in
`test_collect_shards.py` does, and passes the tree list with `--trees`. Nothing
here touches a real repository's register: run over one tracker's live register,
the script would retire eight real rows.
"""

import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "run-issues"))

import check_register_status  # noqa: E402
from collect_shards import REGISTER, closed_ids, collect, render  # noqa: E402
from retire_done_rows import main  # noqa: E402

HEADER = ("| ID | summary | audience | severity | status | origin | owner-notes |\n"
          "|---|---|---|---|---|---|---|\n")


def row(row_id, status, notes=None):
    notes = notes if notes is not None else f"{status} — `bugs/{row_id}.md`"
    return f"| {row_id} | a finding | operator | high | {status} | 44/r1 | {notes} |\n"


class Fixture(unittest.TestCase):
    """A main checkout plus one linked worktree, as directories only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = os.path.join(self.tmp.name, "project")
        self.tree = os.path.join(self.main, ".claude", "worktrees", "run-a")
        for tree in (self.main, self.tree):
            os.makedirs(tree, exist_ok=True)
        self.trees = [self.main, self.tree]
        self.feature = "example-feature"

    def tearDown(self):
        self.tmp.cleanup()

    def shard(self, tree, name, text, owner=None):
        holder = owner or ("main" if tree == self.main else os.path.basename(tree))
        path = os.path.join(tree, ".scratch", self.feature, "register.d", holder, f"{name}.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def closed_path(self, tree=None):
        tree = tree or self.tree
        holder = "main" if tree == self.main else os.path.basename(tree)
        return os.path.join(tree, ".scratch", self.feature, "register.d", holder, "closed.md")

    def run_main(self, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--feature", self.feature, "--cwd", cwd or self.tree,
                         "--trees", *self.trees])
        return code, out.getvalue(), err.getvalue()

    def retired(self, tree=None):
        path = self.closed_path(tree)
        return closed_ids([("closed", path)]) if os.path.exists(path) else set()


class DoneRowsRetireTest(Fixture):
    """AC2: every `verified` and `fixed` row retires, and no row at any other word."""

    def test_only_the_done_words_retire(self):
        words = check_register_status.LEGAL
        self.assertEqual(len(words), 11, "the fixture holds one row per word of LEGAL")
        ids = {word: f"rg1-{index:02d}" for index, word in enumerate(words, start=1)}
        self.shard(self.tree, "rg1", HEADER + "".join(row(ids[w], w) for w in words))

        code, _, err = self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual(self.retired(), {ids["verified"], ids["fixed"]})

    def test_a_retired_row_leaves_the_register(self):
        self.shard(self.tree, "rg1", HEADER + row("rg1-01", "fixed") + row("rg1-02", "open"))

        self.run_main()

        out = render(collect(REGISTER, self.trees, self.feature), board=REGISTER)
        self.assertNotIn("rg1-01", out)
        self.assertIn("rg1-02", out)


class NamedRowStaysTest(Fixture):
    """AC6: a row `shape_fault` names is never retired.

    Copied from `agents/promotion.md`: "Never resolve a row the check named." The
    fixture is the shape of run `batch-26c495`: `verified` in the status cell
    and owner-notes ending with the bare word `open`.
    """

    def test_a_named_row_stays_and_is_reported(self):
        self.shard(self.tree, "rg1", HEADER
                   + row("rg1-01", "verified", "`bugs/rg1-01.md` still open")
                   + row("rg1-02", "verified"))

        code, _, err = self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual(self.retired(), {"rg1-02"})
        self.assertIn("rg1-01", err)


class UnretirableRowTest(Fixture):
    """Two done rows the `closed` road cannot take out cleanly. Found by
    `/code-review` of issue 44; neither shape was in either tracker it was
    measured on, on 2026-09-26.
    """

    def test_an_id_the_closed_road_cannot_read_is_held(self):
        """`CLOSED_LINE` and `ROW_ID` never match `**rg1-01**`, so the row would
        never hide and every run would append it again."""
        self.shard(self.tree, "rg1", HEADER + row("**rg1-01**", "fixed"))

        code, _, err = self.run_main()
        size = os.path.getsize(self.closed_path()) if os.path.exists(self.closed_path()) else 0
        self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual(self.retired(), set())
        self.assertEqual(size, 0)
        self.assertIn("**rg1-01**", err)

    def test_an_id_also_on_an_inbox_row_is_held(self):
        """`hide_closed` drops every row carrying the id, the open one too."""
        self.shard(self.main, "00-history", HEADER + row("rg1-02", "verified"))
        self.shard(self.tree, "rg1", HEADER + row("rg1-02", "open"))

        code, _, err = self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual(self.retired(), set())
        self.assertIn("rg1-02", err)
        out = render(collect(REGISTER, self.trees, self.feature), board=REGISTER)
        self.assertIn("| rg1-02 | a finding | operator | high | open |", out)


class DirectRoadRowTest(Fixture):
    """AC3: a `df-` row retires only once its fix is merged.

    The direct road writes its row at `verified` before the merge. Merged reads:
    the main checkout's own copy of that row's shard holds the row, which is the
    copy `collect_shards.collect` falls back to once the owning tree is gone.
    """

    def test_an_unmerged_df_row_waits_and_a_merged_one_retires(self):
        text = HEADER + row("df-7", "verified")
        self.shard(self.tree, "run-a", text)

        self.run_main()
        self.assertNotIn("df-7", self.retired())

        self.shard(self.main, "run-a", text, owner="run-a")
        self.run_main()
        self.assertIn("df-7", self.retired())

    def test_an_id_opening_df_without_the_hyphen_is_not_a_df_row(self):
        self.shard(self.tree, "run-a", HEADER + row("df0918-01", "fixed"))

        self.run_main()

        self.assertIn("df0918-01", self.retired())


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class AppendOnlyTest(Fixture):
    """AC4 and AC8: the script appends to its own shard and touches nothing else.

    The finale and `/daily-brief` can both meet one tree's shard, and a
    read-modify-write "loses a row exactly the way one shared register did"
    (`collect_shards.py`).
    """

    def setUp(self):
        super().setUp()
        self.others = [
            self.shard(self.main, "00-history", HEADER + row("rg0-01", "fixed")),
            self.shard(self.main, "run-a", HEADER + row("rg1-09", "open"), owner="run-a"),
            self.shard(self.tree, "rg1", HEADER + row("rg1-01", "verified")
                       + row("rg1-02", "open")),
            self.shard(self.main, "closed", "rg0-00\n"),
        ]
        # No final newline, so the append has to supply one and keep the prefix.
        self.own = self.shard(self.tree, "closed", "rg9-01")

    def test_only_the_own_shard_changes_and_only_by_growing(self):
        before = {path: digest(path) for path in self.others}
        with open(self.own, "rb") as handle:
            old = handle.read()

        code, _, err = self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual({path: digest(path) for path in self.others}, before)
        with open(self.own, "rb") as handle:
            new = handle.read()
        self.assertTrue(new.startswith(old), new)
        self.assertEqual(self.retired(), {"rg9-01", "rg0-01", "rg1-01"})

    def test_a_second_run_appends_zero_bytes(self):
        self.run_main()
        size = os.path.getsize(self.own)

        code, _, err = self.run_main()

        self.assertEqual(code, 0, err)
        self.assertEqual(os.path.getsize(self.own), size)


class NoTreeTest(Fixture):
    """AC5's boundary: `my_shard` finds no shard for a directory outside every tree."""

    def test_a_cwd_outside_every_tree_is_refused(self):
        code, _, err = self.run_main(cwd=self.tmp.name)

        self.assertEqual(code, 1)
        self.assertIn("--cwd", err)


if __name__ == "__main__":
    unittest.main()
