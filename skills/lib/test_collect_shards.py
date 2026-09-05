#!/usr/bin/env python3
"""Tests for collect_shards.

The register and the decisions queue are generated files. Their content lives
in shards, one per writing worktree, committed on that worktree's own branch
(ticket 38 of the pilot-delivery map, the one-run-per-feature layout ticket,
rulings 5, 14, 15 and 18).

Two facts drive every test below, and both were measured on 2026-09-05 rather
than assumed.

A shard name appears in more than one tree. Run state is committed, so a tree
branched from main carries every shard main held at the cut, and a merged
branch puts its own shard into main. Twelve copies of one name is the ordinary
case, and only one of them is the live one. That is the same trap
`find_live_ledger.py` was rewritten for on 2026-09-05, where a run counted
twice filled a two-run ceiling.

The generated file is a PURE concatenation, with no header of its own. Ruling
14 says every existing citation of `register.md` stays true, and the live file
carries line citations — `register.md:1986` in the daily brief's applied log and
`register.md:16-19` in `scripts/watch-production.mjs`. One added line at the top
falsifies both.
"""

import contextlib
import io
import os
import tempfile
import unittest

from collect_shards import (
    ANSWERED,
    CLOSED,
    HISTORY,
    MAIN,
    QUEUE,
    REGISTER,
    collect,
    drift,
    main,
    my_shard,
    render,
    EmptyRefused,
    SplitRefused,
    split,
    unmatched_answers,
    write,
    writer_name,
)


def make(root, relative, text=""):
    """Write `text` to `root/relative`, making the directories it needs."""
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class TreeFixture(unittest.TestCase):
    """A main checkout plus two linked worktrees, as directories only.

    Every function under test takes the tree list as an argument, so nothing
    here needs a real git repository.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = os.path.join(self.tmp.name, "project")
        self.tree_a = os.path.join(self.main, ".claude", "worktrees", "run-a")
        self.tree_b = os.path.join(self.main, ".claude", "worktrees", "run-b")
        for tree in (self.main, self.tree_a, self.tree_b):
            os.makedirs(tree, exist_ok=True)
        self.trees = [self.main, self.tree_a, self.tree_b]
        self.feature = "example-feature"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv):
        """`main()` with this fixture's trees, capturing both streams."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv) + ["--trees", *self.trees])
        return code, out.getvalue(), err.getvalue()

    def shard(self, tree, name, text, owner=None):
        """Write shard `name` into `tree`, under the directory `owner` owns.

        `owner` defaults to the tree's own name, which is the ordinary case: a
        writer writes inside its own tree. Pass it to plant a stale copy of
        another tree's shard, which is what every worktree carries after a cut.
        """
        holder = owner or ("main" if tree == self.main else os.path.basename(tree))
        return make(tree, f".scratch/{self.feature}/register.d/{holder}/{name}.md", text)


class TwoWritersInOneTreeTest(TreeFixture):
    """The fault that decided the shard key, found 2026-09-05 while updating
    the hunt briefs.

    `/parallel-hunt` ruling 6 keeps the finder and the fixer in ONE worktree, on
    purpose: a second tree would hide the finder's pinning tests from the fixer.
    A run's two gates can also run at once in one tree. Agents write with a
    read-modify-write edit, not an appending open, so two of them on one file
    lose a row exactly the way the single register did — which is the fault this
    whole ticket exists to close.

    So the shard is keyed by the writer's row PREFIX, inside the writer's own
    tree (rulings 5 and 15 together). `rg454` and `vg454` are two files.
    """

    def test_two_writers_in_one_tree_get_two_shards(self):
        a = my_shard(REGISTER, self.tree_a, self.trees, self.feature, prefix="rg454")
        b = my_shard(REGISTER, self.tree_a, self.trees, self.feature, prefix="vg454")

        self.assertNotEqual(a, b)
        self.assertTrue(a.endswith(os.path.join("run-a", "rg454.md")), a)
        self.assertTrue(b.endswith(os.path.join("run-a", "vg454.md")), b)

    def test_both_shards_reach_the_generated_register(self):
        self.shard(self.tree_a, "rg454", "| rg454-01 | from the review gate |\n")
        self.shard(self.tree_a, "vg454", "| vg454-01 | from the verify gate |\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature))

        self.assertIn("rg454-01", out)
        self.assertIn("vg454-01", out)

    def test_a_writer_with_no_prefix_falls_back_to_the_tree_s_own_name(self):
        """A hand session and the production watcher carry no row prefix."""
        path = my_shard(REGISTER, self.tree_a, self.trees, self.feature)
        self.assertTrue(path.endswith(os.path.join("run-a", "run-a.md")), path)

    def test_a_prefix_that_would_escape_its_directory_is_refused(self):
        with self.assertRaises(ValueError):
            my_shard(REGISTER, self.tree_a, self.trees, self.feature, prefix="../main")


class ReservedNameTest(TreeFixture):
    """A writer may not claim a name the renderer treats as machinery.

    `answered`, `closed` and `00-history` are read, not rendered, or sorted
    first. Handing one to an ordinary writer makes everything it writes vanish
    with no error, which is the fault this whole ticket exists to close.
    """

    def test_a_writer_cannot_claim_the_briefs_answered_shard(self):
        with self.assertRaises(ValueError):
            my_shard(QUEUE, self.tree_a, self.trees, prefix=ANSWERED)

    def test_a_writer_cannot_claim_the_history_shard(self):
        with self.assertRaises(ValueError):
            my_shard(REGISTER, self.tree_a, self.trees, self.feature, prefix=HISTORY)

    def test_promotion_claims_closed_by_saying_so(self):
        """`closed` is promotion's own road, and it opts in explicitly."""
        path = my_shard(REGISTER, self.tree_a, self.trees, self.feature,
                        prefix=CLOSED, machinery=True)
        self.assertTrue(path.endswith(os.path.join("run-a", "closed.md")), path)

    def test_a_gate_that_types_closed_by_accident_is_refused(self):
        with self.assertRaises(ValueError):
            my_shard(REGISTER, self.tree_a, self.trees, self.feature, prefix=CLOSED)

    def test_closed_is_an_ordinary_name_on_the_queue_which_never_reads_it(self):
        """A name is reserved on the board that reads it, and nowhere else."""
        path = my_shard(QUEUE, self.tree_a, self.trees, prefix=CLOSED)
        self.assertTrue(path.endswith(os.path.join("run-a", "closed.md")), path)

    def test_the_brief_claims_answered_by_saying_so(self):
        path = my_shard(QUEUE, self.tree_a, self.trees, prefix=ANSWERED, machinery=True)
        self.assertTrue(path.endswith(os.path.join("run-a", "answered.md")), path)


class ClosedIdShapeTest(TreeFixture):
    def test_a_comment_line_in_closed_md_closes_nothing(self):
        """Measured 2026-09-05: a bare-word matcher read ten ids out of one
        sentence, `ID` among them, and `ID` is the register's own table header."""
        self.shard(self.main, HISTORY,
                   "| ID | one-line summary | audience |\n"
                   "| rg1-01 | a live row | operator |\n")
        self.shard(self.tree_a, CLOSED,
                   "Closed by promotion, run batch-b5e96d, 2026-09-05. One ID per line.\n"
                   "rg1-01\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertIn("| ID | one-line summary", out)
        self.assertNotIn("rg1-01", out)


class OwnershipTest(TreeFixture):
    def test_a_shard_is_owned_by_the_tree_its_directory_names(self):
        """The stale copy in the main checkout loses to the live one."""
        self.shard(self.main, "rg454", "stale, cut at the branch point\n", owner="run-a")
        live = self.shard(self.tree_a, "rg454", "the row written this morning\n")

        chosen = collect(REGISTER, self.trees, feature=self.feature)

        self.assertEqual([path for _, path in chosen], [live])

    def test_a_shard_whose_owning_tree_is_gone_falls_back_to_the_main_copy(self):
        """A merged run's tree is removed; its shard survives in main."""
        merged = self.shard(self.main, "rg390", "rows from a run that merged\n",
                            owner="run-gone")

        chosen = collect(REGISTER, self.trees, feature=self.feature)

        self.assertEqual([path for _, path in chosen], [merged])

    def test_a_stray_copy_in_a_third_tree_never_wins(self):
        """Only the owning tree and the main checkout can hold the live copy."""
        self.shard(self.tree_b, "rg454", "a copy that rode in on a branch\n", owner="run-a")
        live = self.shard(self.tree_a, "rg454", "the live rows\n")

        chosen = collect(REGISTER, self.trees, feature=self.feature)

        self.assertEqual([path for _, path in chosen], [live])


class OrderTest(TreeFixture):
    def test_history_leads_and_the_rest_sort_by_name(self):
        """`00-history.md` first, so today's file regenerates byte for byte."""
        self.shard(self.main, "00-history", "everything written before the split\n")
        self.shard(self.tree_b, "run-b", "b\n")
        self.shard(self.tree_a, "run-a", "a\n")

        names = [name for name, _ in collect(REGISTER, self.trees, feature=self.feature)]

        self.assertEqual(names, ["00-history", "run-a", "run-b"])


class WriterNameTest(TreeFixture):
    def test_the_main_checkout_writes_the_shard_called_main(self):
        self.assertEqual(writer_name(self.main, self.trees), "main")

    def test_a_worktree_writes_the_shard_named_after_itself(self):
        self.assertEqual(writer_name(self.tree_a, self.trees), "run-a")

    def test_a_directory_inside_a_worktree_names_that_worktree(self):
        deep = os.path.join(self.tree_a, "src", "lib")
        os.makedirs(deep, exist_ok=True)
        self.assertEqual(writer_name(deep, self.trees), "run-a")


if __name__ == "__main__":
    unittest.main()


class RenderTest(TreeFixture):
    def test_one_history_shard_regenerates_the_file_byte_for_byte(self):
        """Day one: the whole of today's register becomes `00-history.md`.

        This is the test ruling 14 rests on. If the generated bytes differ from
        the file that was split, every line citation into `register.md` moves.
        """
        original = "# Register\n\nrow one\nrow two\n"
        self.shard(self.main, HISTORY, original)

        self.assertEqual(render(collect(REGISTER, self.trees, feature=self.feature)), original)

    def test_a_file_with_no_final_newline_survives_being_the_only_shard(self):
        original = "# Register\n\nthe last row, unterminated"
        self.shard(self.main, HISTORY, original)

        self.assertEqual(render(collect(REGISTER, self.trees, feature=self.feature)), original)

    def test_a_shard_that_does_not_end_in_a_newline_never_runs_into_the_next(self):
        self.shard(self.main, HISTORY, "history")
        self.shard(self.tree_a, "rg1", "| rg1 | a row |\n")

        self.assertEqual(
            render(collect(REGISTER, self.trees, feature=self.feature)),
            "history\n| rg1 | a row |\n",
        )

    def test_nothing_is_added_between_shards(self):
        """No header, no separator, no banner. A pure concatenation."""
        self.shard(self.main, HISTORY, "a\n")
        self.shard(self.tree_a, "rg1", "b\n")

        self.assertEqual(render(collect(REGISTER, self.trees, feature=self.feature)), "a\nb\n")


class DriftTest(TreeFixture):
    def test_a_generated_file_matching_its_shards_reports_no_drift(self):
        self.shard(self.main, HISTORY, "a\n")
        make(self.main, f".scratch/{self.feature}/register.md", "a\n")

        self.assertEqual(drift(REGISTER, self.main, self.trees, feature=self.feature), "")

    def test_a_hand_edit_to_the_generated_file_is_drift(self):
        """A write that got past the hook still has to be found."""
        self.shard(self.main, HISTORY, "a\n")
        make(self.main, f".scratch/{self.feature}/register.md", "a\nsomebody typed this\n")

        self.assertIn("differs", drift(REGISTER, self.main, self.trees, feature=self.feature))

    def test_a_missing_generated_file_is_drift_and_says_so(self):
        self.shard(self.main, HISTORY, "a\n")

        self.assertIn("not there", drift(REGISTER, self.main, self.trees, feature=self.feature))


class WriteTest(TreeFixture):
    def test_writing_lands_the_concatenation_in_the_main_checkout(self):
        self.shard(self.main, HISTORY, "a\n")
        self.shard(self.tree_a, "rg1", "b\n")

        written = write(REGISTER, self.main, self.trees, feature=self.feature)

        with open(written, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "a\nb\n")

    def test_writing_the_same_content_twice_leaves_the_file_alone(self):
        """The hunt's resume cron reads an mtime. An idle rewrite is a lie to it."""
        self.shard(self.main, HISTORY, "a\n")
        written = write(REGISTER, self.main, self.trees, feature=self.feature)
        before = os.stat(written).st_mtime_ns
        os.utime(written, ns=(before - 10**9, before - 10**9))
        stamped = os.stat(written).st_mtime_ns

        write(REGISTER, self.main, self.trees, feature=self.feature)

        self.assertEqual(os.stat(written).st_mtime_ns, stamped)


class CommandLineTest(TreeFixture):
    """The modes, each one a reader named in the sitting-3 walk."""

    def test_split_uses_the_tree_the_caller_stands_in(self):
        make(self.tree_a, f".scratch/{self.feature}/register.md", "mine\n")
        code, out, _ = self.run_main(
            "--kind", "register", "--feature", self.feature, "--split",
            "--cwd", self.tree_a)
        self.assertEqual(code, 0)
        self.assertIn(os.path.join("worktrees", "run-a"), out)

    def test_an_unmatched_answered_id_is_reported_by_the_collector(self):
        """A typo in the brief's shard answers nothing. Somebody has to hear."""
        make(self.main, ".scratch/decisions-queue.d/main/00-history.md",
             "## Item `q-main-01`\n\nbody\n")
        make(self.main, f".scratch/decisions-queue.d/main/{ANSWERED}.md",
             "q-main-01\nq-main-77\n")

        code, _, err = self.run_main("--kind", "queue")

        self.assertEqual(code, 0)  # A note, never a stop.
        self.assertIn("q-main-77", err)

    def test_the_default_mode_writes_the_board_and_prints_its_path(self):
        self.shard(self.main, HISTORY, "a\n")
        code, out, _ = self.run_main("--kind", "register", "--feature", self.feature)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), REGISTER.generated(self.main, self.feature))

    def test_check_passes_on_a_generated_board(self):
        self.shard(self.main, HISTORY, "a\n")
        self.run_main("--kind", "register", "--feature", self.feature)
        code, _, _ = self.run_main("--kind", "register", "--feature", self.feature, "--check")
        self.assertEqual(code, 0)

    def test_check_refuses_a_hand_edited_board(self):
        self.shard(self.main, HISTORY, "a\n")
        make(self.main, f".scratch/{self.feature}/register.md", "a\nby hand\n")
        code, _, err = self.run_main("--kind", "register", "--feature", self.feature, "--check")
        self.assertEqual(code, 1)
        self.assertIn("differs", err)

    def test_mtime_reads_the_newest_shard_and_never_the_generated_file(self):
        """`/parallel-hunt` decides a round is dead on this number.

        Under generation the board's own mtime moves when the collector runs,
        which is not when the round moved. The shards are what move with the
        work.
        """
        self.shard(self.main, HISTORY, "a\n")
        newest = self.shard(self.tree_a, "rg1", "b\n")
        os.utime(newest, (1_700_000_500, 1_700_000_500))
        os.utime(self.shard(self.main, HISTORY, "a\n"), (1_700_000_000, 1_700_000_000))
        self.run_main("--kind", "register", "--feature", self.feature)
        board = REGISTER.generated(self.main, self.feature)
        os.utime(board, (1_900_000_000, 1_900_000_000))

        code, out, _ = self.run_main("--kind", "register", "--feature", self.feature, "--mtime")

        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1700000500")

    def test_mtime_with_no_shards_prints_nothing_and_says_so(self):
        code, out, err = self.run_main("--kind", "register", "--feature", self.feature, "--mtime")
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), "")
        self.assertIn("no shard", err)

    def test_my_shard_names_the_file_this_session_appends_to(self):
        code, out, _ = self.run_main(
            "--kind", "register", "--feature", self.feature, "--my-shard", "--cwd", self.tree_a)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.strip(),
            os.path.join(REGISTER.shards(self.tree_a, self.feature), "run-a", "run-a.md"))

    def test_my_shard_from_outside_every_tree_refuses_rather_than_guessing(self):
        code, _, err = self.run_main(
            "--kind", "register", "--feature", self.feature, "--my-shard", "--cwd", self.tmp.name)
        self.assertEqual(code, 1)
        self.assertIn("no worktree", err)

    def test_the_queue_carries_no_feature_and_sits_at_the_scratch_root(self):
        make(self.main, ".scratch/decisions-queue.d/main/00-history.md", "queued\n")
        code, out, _ = self.run_main("--kind", "queue")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), os.path.join(self.main, ".scratch", "decisions-queue.md"))

    def test_the_register_refuses_without_a_feature(self):
        """A per-feature board with no feature would write `.scratch/register.md`."""
        code, _, err = self.run_main("--kind", "register")
        self.assertEqual(code, 1)
        self.assertIn("--feature", err)


class AnsweredTest(TreeFixture):
    """Ruling 18: the brief marks an item answered in its own shard.

    The queue's writers each own a shard, so nothing may reach into another
    writer's file to delete a section. The brief writes an id into
    `answered.md`, which it alone owns, and the concatenation hides the item.
    """

    def queue_shard(self, tree, name, text, owner=None):
        holder = owner or ("main" if tree == self.main else os.path.basename(tree))
        return make(tree, f".scratch/decisions-queue.d/{holder}/{name}.md", text)

    def test_an_answered_item_and_its_whole_body_disappear(self):
        self.queue_shard(
            self.main, HISTORY,
            "## Keep me `q-main-01`\n\nbody one\n\n"
            "## Answer me `q-main-02`\n\nbody two\nmore of body two\n\n"
            "## Keep me too `q-main-03`\n\nbody three\n")
        self.queue_shard(self.main, ANSWERED, "q-main-02\n")

        out = render(collect(QUEUE, self.trees), board=QUEUE)

        self.assertIn("Keep me `q-main-01`", out)
        self.assertIn("Keep me too `q-main-03`", out)
        self.assertNotIn("q-main-02", out)
        self.assertNotIn("more of body two", out)

    def test_an_item_with_no_id_can_never_be_hidden(self):
        """History carries items written before ids existed. They stay visible."""
        self.queue_shard(self.main, HISTORY, "## An old item, no id\n\nbody\n")
        self.queue_shard(self.main, ANSWERED, "q-main-02\n")

        self.assertIn("An old item", render(collect(QUEUE, self.trees), board=QUEUE))

    def test_the_answered_shard_is_never_part_of_the_queue_it_filters(self):
        self.queue_shard(self.main, HISTORY, "## Item `q-main-01`\n\nbody\n")
        self.queue_shard(self.main, ANSWERED, "q-main-99\n")

        self.assertNotIn("q-main-99", render(collect(QUEUE, self.trees), board=QUEUE))

    def test_an_answered_id_crosses_shard_boundaries(self):
        """The brief answers an item another worktree wrote. That is the point."""
        self.queue_shard(self.tree_a, "fin-a", "## From the run `q-run-a-01`\n\nbody\n")
        self.queue_shard(self.main, ANSWERED, "q-run-a-01\n")

        self.assertNotIn("From the run", render(collect(QUEUE, self.trees), board=QUEUE))

    def test_answered_ids_are_read_as_whole_tokens(self):
        """`q-main-1` must not answer `q-main-11`."""
        self.queue_shard(self.main, HISTORY, "## Eleven `q-main-11`\n\nbody\n")
        self.queue_shard(self.main, ANSWERED, "q-main-1\n")

        self.assertIn("Eleven", render(collect(QUEUE, self.trees), board=QUEUE))

    def test_the_register_hides_nothing(self):
        """Only the queue carries this rule. A register row leaves by promotion."""
        self.shard(self.main, HISTORY, "## A row `q-main-02`\n\nbody\n")
        make(self.main, f".scratch/{self.feature}/register.d/main/{ANSWERED}.md", "q-main-02\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertIn("A row", out)


class ClosedRowTest(TreeFixture):
    """Promotion resolves every row, and no row survives it.

    It cannot delete a row out of another tree's shard: ruling 15 says a
    session writes inside its own tree and nowhere else, and the rows it closes
    were written by a gate in one tree, a hardening pass in another and the
    production watcher in the main checkout. So it writes the ids it resolved
    into its OWN `closed.md`, exactly as the daily brief writes answered item
    ids, and the generated register stops carrying them.
    """

    def test_a_closed_row_leaves_the_register(self):
        self.shard(self.main, HISTORY,
                   "| rg1-01 | still open | operator | high | open | b.md |\n"
                   "| rg1-02 | promoted | operator | high | open | b.md |\n")
        self.shard(self.tree_a, CLOSED, "rg1-02\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertIn("rg1-01", out)
        self.assertNotIn("rg1-02", out)

    def test_only_the_row_goes_and_never_the_prose_around_it(self):
        """The register carries headings and paragraphs between its rows."""
        self.shard(self.main, HISTORY,
                   "## PROMOTION CLOSED — run batch-x\n\n"
                   "Row rg1-02 was promoted to issue 561.\n\n"
                   "| rg1-02 | promoted | operator | high | open | b.md |\n")
        self.shard(self.tree_a, CLOSED, "rg1-02\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertIn("Row rg1-02 was promoted to issue 561.", out)
        self.assertNotIn("| rg1-02 |", out)

    def test_the_id_must_be_the_row_s_own_first_cell(self):
        """A row that merely cites another row's id is not that row."""
        self.shard(self.main, HISTORY,
                   "| rg1-09 | supersedes rg1-02 | operator | high | open | b.md |\n")
        self.shard(self.tree_a, CLOSED, "rg1-02\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertIn("rg1-09", out)

    def test_the_closed_shard_never_renders_into_the_register(self):
        self.shard(self.main, HISTORY, "| rg1-01 | open | operator | high | open | b.md |\n")
        self.shard(self.tree_a, CLOSED, "rg1-77\n")

        out = render(collect(REGISTER, self.trees, feature=self.feature), board=REGISTER)

        self.assertNotIn("rg1-77", out)

    def test_the_queue_closes_nothing(self):
        """The queue answers items; it has no rows to close."""
        self.assertFalse(QUEUE.hides_closed)


class UnknownAnsweredIdTest(TreeFixture):
    def test_an_answered_id_matching_no_item_is_named_rather_than_ignored(self):
        """A typo in the brief's shard silently answers nothing. Say so."""
        make(self.main, ".scratch/decisions-queue.d/main/00-history.md",
             "## Item `q-main-01`\n\nbody\n")
        make(self.main, f".scratch/decisions-queue.d/main/{ANSWERED}.md",
             "q-main-01\nq-main-77\n")

        self.assertEqual(unmatched_answers(collect(QUEUE, self.trees)), ["q-main-77"])


class SplitTest(TreeFixture):
    """The one-off migration: today's file becomes `00-history.md`.

    It is a script and not a hand edit because it has to refuse. Run twice it
    would bury the shards under a second history, and run against a file
    another session is holding open it would commit somebody's half-written
    rows as frozen history.
    """

    def test_the_whole_file_becomes_the_history_shard(self):
        original = "# Register\n\nrow one\n"
        make(self.main, f".scratch/{self.feature}/register.md", original)

        split(REGISTER, self.main, self.trees, feature=self.feature)

        with open(os.path.join(
                REGISTER.shards(self.main, self.feature), "main", f"{HISTORY}.md"),
                encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)

    def test_the_generated_file_is_unchanged_by_its_own_split(self):
        """The proof ruling 14 asks for: every line citation still lands."""
        original = "# Register\n\nrow one\nrow two\nrow three\n"
        board = make(self.main, f".scratch/{self.feature}/register.md", original)

        split(REGISTER, self.main, self.trees, feature=self.feature)
        write(REGISTER, self.main, self.trees, feature=self.feature)

        with open(board, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)

    def test_a_second_split_refuses_rather_than_burying_the_first(self):
        make(self.main, f".scratch/{self.feature}/register.md", "a\n")
        split(REGISTER, self.main, self.trees, feature=self.feature)

        with self.assertRaises(SplitRefused):
            split(REGISTER, self.main, self.trees, feature=self.feature)

    def test_a_missing_file_refuses(self):
        with self.assertRaises(SplitRefused):
            split(REGISTER, self.main, self.trees, feature=self.feature)

    def test_it_splits_the_tree_it_was_pointed_at_and_no_other(self):
        """The migration lands on a branch, not in somebody else's tree.

        Run from a worktree it used to rewrite the MAIN checkout, which on
        2026-09-05 held uncommitted register and queue edits from a live daily
        brief — the concurrent write this ticket exists to stop.
        """
        make(self.tree_a, f".scratch/{self.feature}/register.md", "mine\n")
        make(self.main, f".scratch/{self.feature}/register.md", "the main copy\n")

        split(REGISTER, self.tree_a, self.trees, feature=self.feature)

        self.assertTrue(os.path.exists(os.path.join(
            REGISTER.shards(self.tree_a, self.feature), "run-a", f"{HISTORY}.md")))
        self.assertFalse(os.path.exists(os.path.join(
            REGISTER.shards(self.main, self.feature), MAIN, f"{HISTORY}.md")))


class EmptyRenderTest(TreeFixture):
    """A generation that finds nothing may not delete the file.

    Measured 2026-09-05, on the live files. `--split` wrote its history shard
    into a worktree under the holder `main`, so the collector looked for it in
    the MAIN checkout, found nothing, and wrote an empty register over 4,624
    lines and an empty queue over 8,978. Git had them; nothing else did.
    """

    def test_writing_nothing_over_something_refuses(self):
        board = make(self.main, f".scratch/{self.feature}/register.md", "4,624 lines\n")

        with self.assertRaises(EmptyRefused):
            write(REGISTER, self.main, self.trees, feature=self.feature)

        with open(board, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "4,624 lines\n")

    def test_writing_nothing_over_nothing_is_fine(self):
        """A feature with no register and no shards stays that way."""
        write(REGISTER, self.main, self.trees, feature=self.feature)

    def test_a_shard_that_is_genuinely_empty_still_writes(self):
        """Promotion closing every row leaves an empty register, legitimately."""
        make(self.main, f".scratch/{self.feature}/register.md", "old rows\n")
        self.shard(self.main, HISTORY, "")

        write(REGISTER, self.main, self.trees, feature=self.feature)

        with open(REGISTER.generated(self.main, self.feature), encoding="utf-8") as h:
            self.assertEqual(h.read(), "")


class SplitInAWorktreeTest(TreeFixture):
    def test_the_history_shard_belongs_to_the_tree_that_was_split(self):
        """Written under `main/`, the collector looks for it in the main
        checkout, does not find it, and renders nothing."""
        make(self.tree_a, f".scratch/{self.feature}/register.md", "rows\n")

        split(REGISTER, self.tree_a, self.trees, feature=self.feature)

        self.assertTrue(os.path.exists(os.path.join(
            REGISTER.shards(self.tree_a, self.feature), "run-a", f"{HISTORY}.md")))

    def test_the_split_regenerates_the_tree_it_split(self):
        make(self.tree_a, f".scratch/{self.feature}/register.md", "rows\n")

        code, out, err = self.run_main(
            "--kind", "register", "--feature", self.feature, "--split", "--cwd", self.tree_a)

        self.assertEqual(code, 0, err)
        with open(REGISTER.generated(self.tree_a, self.feature), encoding="utf-8") as h:
            self.assertEqual(h.read(), "rows\n")

    def test_the_split_leaves_the_main_checkout_alone(self):
        make(self.tree_a, f".scratch/{self.feature}/register.md", "rows\n")
        untouched = make(self.main, f".scratch/{self.feature}/register.md", "main's own\n")

        self.run_main("--kind", "register", "--feature", self.feature,
                      "--split", "--cwd", self.tree_a)

        with open(untouched, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "main's own\n")


class QueueIdTest(TreeFixture):
    """Ruling 18: every queue item carries an id, so the brief can answer it."""

    def test_every_heading_gains_an_id(self):
        make(self.main, ".scratch/decisions-queue.md",
             "## First item\n\nbody\n\n## Second item\n\nbody\n")

        split(QUEUE, self.main, self.trees)

        with open(os.path.join(QUEUE.shards(self.main), "main", f"{HISTORY}.md"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## First item `q-h-001`", text)
        self.assertIn("## Second item `q-h-002`", text)

    def test_assigning_ids_moves_no_line(self):
        """`decisions-queue.md:518` is cited in `scripts/lib/what-is-owed.mjs`."""
        original = "## First item\n\nbody\n\n## Second item\n\nbody\n"
        make(self.main, ".scratch/decisions-queue.md", original)

        split(QUEUE, self.main, self.trees)
        write(QUEUE, self.main, self.trees)

        with open(QUEUE.generated(self.main), encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(after.count("\n"), original.count("\n"))
        self.assertEqual(
            [line.split(" `q-")[0] for line in after.splitlines()],
            original.splitlines())

    def test_a_heading_that_already_carries_an_id_keeps_it(self):
        make(self.main, ".scratch/decisions-queue.md", "## Item `q-main-04`\n\nbody\n")

        split(QUEUE, self.main, self.trees)

        with open(os.path.join(QUEUE.shards(self.main), "main", f"{HISTORY}.md"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("`q-main-04`", text)
        self.assertNotIn("q-h-001", text)

    def test_the_register_is_never_given_item_ids(self):
        """A register row leaves by promotion, not by being marked answered."""
        make(self.main, f".scratch/{self.feature}/register.md", "## A section\n\nrow\n")

        split(REGISTER, self.main, self.trees, feature=self.feature)

        with open(os.path.join(
                REGISTER.shards(self.main, self.feature), "main", f"{HISTORY}.md"),
                encoding="utf-8") as handle:
            self.assertNotIn("q-h-", handle.read())
