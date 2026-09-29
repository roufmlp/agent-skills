#!/usr/bin/env python3
"""Tests for check_queue_shard.

The fixtures copy the two shapes that actually reached a board unnamed: an
issue-drafting heading with a bare id and no `q-`, and a hardening
heading with a `q-` id that was never backticked. Both rendered forever, and
both are refused here.
"""

import contextlib
import io
import os
import tempfile
import unittest

from check_queue_shard import CLEAN, EMPTY, WRONG, check_file, check_text, main

try:
    from rulings import parse
    RULINGS_READER = True
except ImportError:  # pragma: no cover - a pack shipped without the reader
    # `rulings.py` is optional in this pack, and so is the guard that reads it.
    # The two classes below are skipped rather than deleted: they are the
    # acceptance tests for that guard and they run the moment the reader is
    # beside them. Everything above them runs either way.
    RULINGS_READER = False

NAMED = (
    "# a shard\n\n"
    "## 01-Q1: Which local Postgres `q-h0912-1`\n\nbody\n\n"
    "## 01-Q2: Where does the radius come from `q-h0912-2`\n\nbody\n"
)
BARE = "## to-issues-2026-09-12-61 [irreversible] 14-Q1: declined credit\n\nbody\n"
UNTICKED = "## q-h0908-3 [reversible] the storage meter\n\nbody\n"


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class Text(unittest.TestCase):
    def test_a_shard_whose_headings_all_carry_ids_passes(self):
        self.assertEqual(check_text(NAMED), [])

    def test_the_bare_shape_is_refused_and_names_the_line(self):
        refusals = check_text("# shard\n\n" + BARE, "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertTrue(refusals[0].startswith("s.md:3:"), refusals[0])
        self.assertIn("no backticked `q-` id", refusals[0])

    def test_the_unticked_shape_without_backticks_is_refused(self):
        refusals = check_text(UNTICKED)
        self.assertEqual(len(refusals), 1)
        self.assertIn("no backticked", refusals[0])

    def test_the_id_may_sit_anywhere_on_the_line(self):
        self.assertEqual(check_text("## `q-x-1` [reversible] leading id\n\nbody\n"), [])

    def test_a_heading_inside_a_fence_is_an_example_not_an_item(self):
        text = NAMED + "\n```\n## not a heading\n```\n"
        self.assertEqual(check_text(text), [])

    def test_two_headings_sharing_an_id_are_refused(self):
        text = NAMED + "## a third `q-h0912-2`\n\nbody\n"
        refusals = check_text(text, "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertIn("already names the heading on line 7", refusals[0])

    def test_a_file_with_no_heading_asserts_nothing(self):
        refusals = check_text("# only a title\n\nprose\n", "s.md")
        self.assertEqual(len(refusals), 1)
        self.assertIn("nothing was checked", refusals[0])

    def test_every_unnamed_heading_is_reported_not_only_the_first(self):
        text = "# s\n\n" + BARE + "\n" + UNTICKED
        self.assertEqual(len(check_text(text)), 2)


class File(unittest.TestCase):
    def test_exit_codes_follow_the_directory_convention(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_file(write(tmp, "a.md", NAMED))[0], CLEAN)
            self.assertEqual(check_file(write(tmp, "b.md", "# t\n" + BARE))[0], WRONG)
            self.assertEqual(check_file(write(tmp, "c.md", "# t\n"))[0], EMPTY)
            self.assertEqual(check_file(os.path.join(tmp, "missing.md"))[0], EMPTY)


def drive(*paths):
    """`main` run over `paths`, as `(exit code, stdout, stderr)`.

    Lifted out of `Main` when `AnIncompleteRecord` needed the same road. One
    driver, because two would drift on which stream they captured.
    """
    err = io.StringIO()
    out = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = main(list(paths))
    return code, out.getvalue(), err.getvalue()


class Main(unittest.TestCase):
    def run_main(self, *paths):
        return drive(*paths)

    def test_a_clean_shard_exits_zero_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.run_main(write(tmp, "a.md", NAMED))
        self.assertEqual(code, CLEAN)
        self.assertIn("every heading carries an id", out)
        self.assertEqual(err, "")

    def test_one_bad_shard_among_good_ones_fails_the_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = write(tmp, "a.md", NAMED)
            bad = write(tmp, "b.md", "# t\n\n" + BARE)
            code, out, err = self.run_main(good, bad)
        self.assertEqual(code, WRONG)
        self.assertIn("REFUSED", err)
        self.assertIn("b.md:3:", err)
        self.assertEqual(out, "")

    def test_an_empty_shard_beside_a_wrong_one_reports_the_worse_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = write(tmp, "a.md", "# t\n")
            bad = write(tmp, "b.md", "# t\n\n" + BARE)
            code, _, _ = self.run_main(empty, bad)
        self.assertEqual(code, EMPTY)


RULINGS = (
    "# Rulings\n\n"
    "## 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency\n"
    "Ruled: one Postgres 16 container per worktree, tests serial.\n"
    "Carried by: `.scratch/example-feature/issues/01-the-test-database.md`\n\n"
    "## 2026-09-10 `03-Q2` — where the search radius comes from\n"
    "Ruled: the radius is a column on the depot row, not a constant.\n"
    "Carried by: `.scratch/example-feature/issues/03-the-radius.md`\n"
)
ASKED = ("## 05-Q2: which local Postgres at what concurrency `q-ti04-1`\n\n"
         "The batch needs a database. Which one, and how many at once?\n")
CHECKED = (
    "## 05-Q2: which local Postgres at what concurrency `q-ti04-1`\n\n"
    "Rulings checked: none match\n"
    "> 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency\n"
    "> 2026-09-10 `03-Q2` — where the search radius comes from\n\n"
    "01-Q1 fixes the container. This asks who tears it down between batches.\n"
)


@unittest.skipUnless(RULINGS_READER, "`rulings.py` is not beside this script")
class TheRulingsGuard(unittest.TestCase):
    """Acceptance criteria 1 and 2 of issue 04."""

    def setUp(self):
        self.entries = parse(RULINGS)

    def test_a_question_already_ruled_is_refused_with_the_entry_printed(self):
        refusals = check_text("# s\n\n" + ASKED, "s.md", self.entries)
        self.assertEqual(len(refusals), 1)
        self.assertTrue(refusals[0].startswith("s.md:3:"), refusals[0])
        self.assertIn("`01-Q1`", refusals[0])
        self.assertIn("one Postgres 16 container", refusals[0])
        self.assertIn(".scratch/example-feature/issues/01-the-test-database.md",
                      refusals[0])

    def test_the_same_item_that_checked_the_rulings_passes(self):
        self.assertEqual(check_text("# s\n\n" + CHECKED, "s.md", self.entries), [])

    def test_a_declaration_that_quotes_neither_entry_is_still_refused(self):
        item = ASKED.replace("The batch needs",
                             "Rulings checked: none match\n\nThe batch needs")
        refusals = check_text("# s\n\n" + item, "s.md", self.entries)
        self.assertEqual(len(refusals), 1)
        self.assertIn("quotes no entry", refusals[0])

    def test_a_declaration_that_skips_the_matching_entry_is_refused(self):
        """Reading around the answer is not reading it.

        The item declares a check and quotes an entry, but not the one that
        rules its subject. Without this the escape line would pass any item
        that quoted anything at all.
        """
        item = (
            "## 05-Q2: which local Postgres at what concurrency `q-ti04-1`\n\n"
            "Rulings checked: none match\n"
            "> 2026-09-10 `03-Q2` — where the search radius comes from\n\n"
            "The batch needs a database, and nothing on record says which.\n"
        )
        refusals = check_text("# s\n\n" + item, "s.md", self.entries)
        self.assertEqual(len(refusals), 1)
        self.assertIn("`01-Q1`", refusals[0])
        self.assertIn("does not quote", refusals[0])

    def test_an_unruled_question_needs_no_declaration(self):
        item = "## 05-Q3: how the invoice pdf is rendered `q-ti04-2`\n\nbody\n"
        self.assertEqual(check_text("# s\n\n" + item, "s.md", self.entries), [])

    def test_an_empty_rulings_file_changes_nothing(self):
        self.assertEqual(check_text("# s\n\n" + ASKED, "s.md", []), [])

    def test_the_unnamed_refusal_still_fires_under_the_guard(self):
        refusals = check_text("# s\n\n" + BARE, "s.md", self.entries)
        self.assertEqual(len(refusals), 1)
        self.assertIn("no backticked `q-` id", refusals[0])


# The rulings file of 2026-09-17, with one entry whose `Carried by:` line
# carries two backticked paths. `rulings.parse` read one entry out of two.
HALF_READ = (
    "# Rulings\n\n"
    "## 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency\n"
    "Ruled: one Postgres 16 container per worktree, tests serial.\n"
    "Carried by: `.scratch/example-feature/issues/01-the-test-database.md`\n\n"
    "## 2026-09-17 `ti06-9` — where the search radius comes from\n"
    "Ruled: the radius is a column on the depot row.\n"
    "Carried by: `run-issues/SKILL.md` line 1020, and `.scratch/x.md`\n"
)


# A shard asking something no entry of `HALF_READ` or `RULINGS` rules, so the
# only thing under test here is whether the record itself read whole.
UNRULED = "# s\n\n## how the invoice pdf is rendered `q-x-1`\n\nbody\n"


def stage(tmp, rulings, shard):
    """A shard under a `.scratch` tree, with a rulings file governing it.

    This is the layout `rulings.path_for` walks: the shard sits at
    `<tree>/.scratch/decisions-queue.d/<owner>/<x>.md` and the record two
    directories above it.
    """
    scratch = os.path.join(tmp, ".scratch")
    owner = os.path.join(scratch, "decisions-queue.d", "t")
    os.makedirs(owner)
    with open(os.path.join(scratch, "rulings.md"), "w", encoding="utf-8") as h:
        h.write(rulings)
    path = os.path.join(owner, "x.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(shard)
    return path, os.path.join(scratch, "rulings.md")


@unittest.skipUnless(RULINGS_READER, "`rulings.py` is not beside this script")
class AnIncompleteRecord(unittest.TestCase):
    """This is the consumer whose silence causes the harm.

    A dropped entry cannot refuse the question it answered, so the pass asks
    the human again — the exact failure the rulings file exists to prevent. A
    shard graded against a record this reader could not fully read is not a
    clean shard, whatever its own headings say.
    """

    def test_a_shard_graded_against_a_dropped_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            shard, rulings = stage(tmp, HALF_READ, UNRULED)
            code, refusals = check_file(shard)
        self.assertEqual(code, WRONG)
        self.assertTrue(any("ti06-9" in line for line in refusals), refusals)
        self.assertTrue(any(rulings in line for line in refusals), refusals)

    def test_a_record_that_reads_whole_leaves_a_clean_shard_clean(self):
        """The other direction. This guard refuses a broken entry, never a
        file that parses."""
        with tempfile.TemporaryDirectory() as tmp:
            shard, _ = stage(tmp, RULINGS, UNRULED)
            code, refusals = check_file(shard)
        self.assertEqual((code, refusals), (CLEAN, []))

    def test_the_command_line_says_nothing_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            shard, _ = stage(tmp, HALF_READ, UNRULED)
            code, out, err = drive(shard)
        self.assertEqual(code, WRONG)
        self.assertIn("REFUSED", err)
        self.assertNotIn("every heading carries an id", out)

    def test_a_rulings_file_named_on_the_command_line_is_graded_too(self):
        """`--rulings` parses the file itself, so the same hole is open on
        that road."""
        with tempfile.TemporaryDirectory() as tmp:
            rulings = write(tmp, "rulings.md", HALF_READ)
            code, out, err = drive(write(tmp, "a.md", UNRULED),
                                   "--rulings", rulings)
        self.assertEqual(code, WRONG)
        self.assertIn("ti06-9", err)
        self.assertIn(rulings, err)
        self.assertNotIn("every heading carries an id", out)

# The pair that escaped on 2026-09-22, reconstructed from the two headings.
# The ids are IDENTICAL. The subjects name one thing in different words --
# "cleanup" against "clear", "fails" against "refusing" -- so they share one
# content word against a threshold of three, and the word heuristic said
# nothing. The item carried no `Rulings checked:` line; it was simply missed.
SAME_NAME_RULINGS = (
    "# Rulings\n\n"
    "## 2026-09-22 `q-h0922b-124-1` — which road stops a refused subscription "
    "clear from refusing the sign-in\n"
    "Ruled: the clear is best effort; a failure is logged and the sign-in "
    "proceeds.\n"
    "Carried by: `.scratch/example-feature/issues/124-the-push-subscription.md`\n"
)
SAME_NAME_ITEM = (
    "## `q-h0922b-124-1` [irreversible] — a failed push cleanup fails the "
    "sign-in\n\n"
    "A push subscription that will not clear leaves the sign-in refused.\n"
    "Which road does the session take?\n"
)


@unittest.skipUnless(RULINGS_READER, "`rulings.py` is not beside this script")
class TheSameQuestionByName(unittest.TestCase):
    """An id match is a certainty, and a certainty has no escape line.

    The declaration exists for a writer who read a near-miss entry and judged
    it a different question. That is a judgement. An identical id is not a
    judgement -- it is the same question by name -- so the only road onwards
    is a follow-up under a NEW id.
    """

    def setUp(self):
        self.entries = parse(SAME_NAME_RULINGS)
        # The record has to read, or every assertion below is graded against
        # nothing and passes for the wrong reason.
        self.assertEqual([entry.question for entry in self.entries],
                         ["q-h0922b-124-1"])

    def test_the_case_that_escaped_on_22_september_is_refused(self):
        refusals = check_text("# s\n\n" + SAME_NAME_ITEM, "s.md", self.entries)
        self.assertEqual(len(refusals), 1, refusals)
        self.assertTrue(refusals[0].startswith("s.md:3:"), refusals[0])
        self.assertIn("`q-h0922b-124-1`", refusals[0])
        self.assertIn("id", refusals[0])
        self.assertIn("best effort", refusals[0])
        self.assertIn(".scratch/example-feature/issues/124-the-push-subscription.md",
                      refusals[0])

    def test_the_declaration_line_does_not_wave_an_id_match_through(self):
        item = SAME_NAME_ITEM.replace(
            "A push subscription",
            "Rulings checked: none match\n"
            "> 2026-09-22 `q-h0922b-124-1` — which road stops a refused "
            "subscription clear\n\n"
            "A push subscription")
        refusals = check_text("# s\n\n" + item, "s.md", self.entries)
        self.assertEqual(len(refusals), 1, refusals)
        self.assertIn("`q-h0922b-124-1`", refusals[0])

    def test_a_follow_up_under_a_new_id_passes(self):
        item = SAME_NAME_ITEM.replace("q-h0922b-124-1", "q-h0922b-124-2")
        self.assertEqual(check_text("# s\n\n" + item, "s.md", self.entries), [])

    def test_the_exit_code_and_the_refusal_reach_the_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            shard, _ = stage(tmp, SAME_NAME_RULINGS, "# s\n\n" + SAME_NAME_ITEM)
            code, out, err = drive(shard)
        self.assertEqual(code, WRONG)
        self.assertIn("q-h0922b-124-1", err)
        self.assertNotIn("no item asks a question already ruled", out)


@unittest.skipUnless(RULINGS_READER, "`rulings.py` is not beside this script")
class ANearMissKeepsItsEscape(unittest.TestCase):
    """The regression that matters most.

    A different id and a close subject is exactly what the word heuristic was
    built for, and the declaration is exactly what passes it. Nothing here
    changes because an id certainty was added beside it.
    """

    def setUp(self):
        self.entries = parse(RULINGS)

    def test_a_near_miss_under_a_different_id_is_still_refused_undeclared(self):
        refusals = check_text("# s\n\n" + ASKED, "s.md", self.entries)
        self.assertEqual(len(refusals), 1, refusals)
        self.assertIn("`01-Q1`", refusals[0])

    def test_a_near_miss_under_a_different_id_still_takes_the_escape(self):
        self.assertEqual(check_text("# s\n\n" + CHECKED, "s.md", self.entries), [])

    def test_the_ids_that_differ_here_are_what_makes_it_a_near_miss(self):
        """Pins the fixture rather than the code: were `q-ti04-1` ever the
        same string as an entry's question id, the test above would be
        measuring the id road and would pass while the escape was broken."""
        held = {entry.question for entry in self.entries}
        self.assertEqual(held & {"q-ti04-1", "05-Q2"}, set())


class WithoutTheRulingsReader(unittest.TestCase):
    """What `--rulings` does where a copy of the pack leaves out `rulings.py`.

    It refuses rather than reporting a clean walk it did not perform. A flag
    that silently checked nothing would read as "no ruling covers this".
    """

    @unittest.skipIf(RULINGS_READER, "the reader is present in this pack")
    def test_the_flag_refuses_rather_than_passing_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = drive(write(tmp, "a.md", NAMED),
                                   "--rulings", write(tmp, "r.md", "# Rulings\n"))
        self.assertEqual(code, WRONG)
        self.assertIn("REFUSED", err)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
