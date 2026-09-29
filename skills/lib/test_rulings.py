#!/usr/bin/env python3
"""Tests for rulings.

The fixture is the collision the issue was opened on: the human ruled the local
Postgres question on issue 01, and a later pass queued the same subject against
issue 05.
"""

import contextlib
import io
import os
import stat
import sys
import tempfile
import unittest

from rulings import (check_answered, check_commit, content_words,
                     declared, issue_of, matches, nearest, parse,
                     fold, main, path_for, quoted_ids, ruled_by_id)
from collect_shards import RULED
from rulings import EMPTY, HEADING, RULED_SHARD, WRONG, skipped

# The shared refusal lives beside the checkers that first needed it. The reach
# across directories is the one `rulings.py` itself makes.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "run-issues"))
from empty_input import EXIT_EMPTY  # noqa: E402

# THE THREE CORPUS CASES DO NOT TRAVEL, AND THE FACT THEY CARRIED DOES.
# Live, a `PROJECT_RULINGS` constant pointed at the author's own
# `skills/.scratch/rulings.md` and three cases graded this reader against it:
# `--list` on that file listed every entry it held and exited 0 with an empty
# stderr, `skipped()` found nothing unreadable in it, and the count never fell
# below a floor of 17 entries. That is a record no other machine has, so the
# reading is written down here and the pinning stays behind. Every case below
# builds its own fixture; nothing skips.

FILE = """# Rulings

## 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency
Ruled: one Postgres 16 container per worktree, tests serial, no concurrency knob.
Carried by: `.scratch/example-feature/issues/01-the-test-database.md`

## 2026-09-10 `03-Q2` — where the search radius comes from
Ruled: the radius is a column on the depot row, not a constant.
Carried by: `.scratch/example-feature/issues/03-the-radius.md`
"""


class Constants(unittest.TestCase):
    def test_the_refused_shard_is_the_one_an_attended_session_writes(self):
        """`RULED_SHARD` is derived from the collector's own prefix. A name
        that shadowed it would make this depend on statement order."""
        self.assertEqual(RULED_SHARD, RULED + ".md")
        self.assertEqual(RULED_SHARD, "ruled.md")


class Parse(unittest.TestCase):
    def test_every_entry_is_read(self):
        self.assertEqual(len(parse(FILE)), 2)

    def test_an_entry_carries_its_five_fields(self):
        first = parse(FILE)[0]
        self.assertEqual(first.date, "2026-09-13")
        self.assertEqual(first.question, "01-Q1")
        self.assertEqual(first.subject,
                         "local Postgres for tests, and at what concurrency")
        self.assertIn("one Postgres 16 container", first.ruling)
        self.assertEqual(first.home,
                         ".scratch/example-feature/issues/01-the-test-database.md")

    def test_a_file_with_no_entry_parses_to_nothing(self):
        self.assertEqual(parse("# Rulings\n\nnothing yet\n"), [])



class Words(unittest.TestCase):
    def test_stop_words_and_punctuation_fall_away(self):
        self.assertEqual(content_words("Which local Postgres, at what concurrency?"),
                         {"local", "postgres", "concurrency"})

    def test_a_word_counts_once_however_often_it_is_written(self):
        self.assertEqual(content_words("radius radius radius"), {"radius"})


class IssueOf(unittest.TestCase):
    def test_a_question_reference_yields_its_issue_number(self):
        self.assertEqual(issue_of("05-Q2"), "05")

    def test_a_wide_issue_number_is_read_whole(self):
        self.assertEqual(issue_of("641-Q11"), "641")

    def test_a_retirement_id_carries_no_issue_number(self):
        self.assertEqual(issue_of("q-h0912-1"), "")


class Matches(unittest.TestCase):
    """Acceptance criterion 1, at the module seam.

    The queued question sits on issue 05 and the ruling answered 01-Q1, so the
    issue numbers differ. Three shared content words is the match, which is
    what makes a question already answered ELSEWHERE catchable at all.
    """

    def setUp(self):
        self.entries = parse(FILE)

    def test_the_same_subject_under_another_issue_number_still_matches(self):
        hit = matches("which local Postgres at what concurrency", self.entries,
                      issue="05")
        self.assertEqual([entry.question for entry in hit], ["01-Q1"])

    def test_two_shared_words_are_not_enough_across_issues(self):
        self.assertEqual(matches("which local Postgres", self.entries, issue="05"), [])

    def test_two_shared_words_are_enough_on_the_issue_that_was_ruled(self):
        hit = matches("which local Postgres", self.entries, issue="01")
        self.assertEqual([entry.question for entry in hit], ["01-Q1"])

    def test_the_issue_number_alone_never_matches(self):
        self.assertEqual(matches("who signs the depot contract", self.entries,
                                 issue="01"), [])

    def test_an_unrelated_question_matches_nothing(self):
        self.assertEqual(matches("how the invoice pdf is rendered", self.entries), [])


# The pair measured on 2026-09-22. The ids are identical and the subjects
# describe one thing in different words -- "cleanup" against "clear", "fails"
# against "refusing" -- so one content word is shared and the word heuristic
# never fired.
SAME_NAME = """# Rulings

## 2026-09-22 `q-h0922b-124-1` — which road stops a refused subscription clear from refusing the sign-in
Ruled: the clear is best effort; a failure is logged and the sign-in proceeds.
Carried by: `.scratch/example-feature/issues/124-the-push-subscription.md`
"""
SAME_NAME_HEADING = ("## `q-h0922b-124-1` [irreversible] — a failed push "
                     "cleanup fails the sign-in")


class RuledById(unittest.TestCase):
    """The certainty beside the heuristic.

    An item carrying a ruling entry's own question id is that question by
    name, whatever words either heading chose. The word overlap is what
    `matches` reads and it cannot see this: on the measured pair the two
    headings share one content word against a threshold of three.
    """

    def setUp(self):
        self.entries = parse(SAME_NAME)
        # The fixture has to parse, or this class asserts against an empty
        # record and passes for the wrong reason.
        self.assertEqual(len(self.entries), 1)

    def test_the_word_heuristic_does_not_see_the_measured_pair(self):
        subject = ("a failed push cleanup fails the sign-in")
        self.assertEqual(matches(subject, self.entries), [])

    def test_the_same_id_on_the_heading_is_a_match(self):
        hit = ruled_by_id(SAME_NAME_HEADING, self.entries)
        self.assertEqual([entry.question for entry in hit],
                         ["q-h0922b-124-1"])

    def test_a_question_reference_names_an_entry_too(self):
        entries = parse("## 2026-09-13 `05-Q2` — who owns the depot import\n"
                        "Ruled: Ops owns it.\nCarried by: `x.md`\n")
        hit = ruled_by_id("## 05-Q2: something else entirely `q-a-1`", entries)
        self.assertEqual([entry.question for entry in hit], ["05-Q2"])

    def test_a_different_id_is_not_a_match(self):
        head = SAME_NAME_HEADING.replace("124-1", "124-2")
        self.assertEqual(ruled_by_id(head, self.entries), [])

    def test_a_heading_with_no_id_matches_nothing(self):
        self.assertEqual(ruled_by_id("## a heading with no name", self.entries), [])

    def test_an_empty_record_matches_nothing(self):
        self.assertEqual(ruled_by_id(SAME_NAME_HEADING, []), [])


DECLARED = """## 05-Q2: which local Postgres at what concurrency `q-ti04-1`

Rulings checked: none match
> 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency
> 2026-09-10 `03-Q2` — where the search radius comes from

The ruling on 01-Q1 fixes the container. This asks who tears it down.
"""


class Declaration(unittest.TestCase):
    def setUp(self):
        self.entries = parse(FILE)

    def test_an_item_that_checked_the_rulings_says_so(self):
        self.assertTrue(declared(DECLARED))

    def test_an_item_that_did_not_check_says_nothing(self):
        self.assertFalse(declared("## 05-Q2: a question `q-ti04-1`\n\nbody\n"))

    def test_the_quoted_entries_are_read_off_the_item(self):
        self.assertEqual(quoted_ids(DECLARED, self.entries), {"01-Q1", "03-Q2"})

    def test_an_items_own_heading_is_not_a_quote_of_itself(self):
        """The hole the review of 2026-09-13 found. An item re-asking a ruled
        question carries that entry's id on its own heading, so scanning the
        whole item let an exact duplicate satisfy the quote requirement with
        nothing read."""
        entries = parse("## 2026-09-13 `05-Q2` — who owns the depot import\n"
                        "Ruled: Ops owns it.\nCarried by: `x.md`\n")
        item = ("## 05-Q2: who owns the depot import `q-a-1`\n\n"
                "Rulings checked: none match\n\nnothing was read\n")
        self.assertEqual(quoted_ids(item, entries), set())

    def test_a_quote_inside_a_fenced_example_is_not_a_quote(self):
        entries = parse("## 2026-09-13 `05-Q2` — who owns the depot import\n"
                        "Ruled: Ops owns it.\nCarried by: `x.md`\n")
        item = "## 07-Q1: a question `q-a-1`\n\n```\n> `05-Q2` an example\n```\n"
        self.assertEqual(quoted_ids(item, entries), set())

    def test_a_declaration_inside_a_fenced_example_is_not_a_declaration(self):
        item = "## 07-Q1: a question `q-a-1`\n\n```\nRulings checked: none match\n```\n"
        self.assertFalse(declared(item))

    def test_an_id_the_rulings_file_does_not_hold_is_not_a_quote(self):
        item = "Rulings checked: none match\n> `99-Q9` — invented\n"
        self.assertEqual(quoted_ids(item, self.entries), set())


class Nearest(unittest.TestCase):
    def setUp(self):
        self.entries = parse(FILE)

    def test_the_closest_entries_come_first(self):
        near = nearest("which local Postgres at what concurrency", self.entries)
        self.assertEqual([entry.question for entry in near], ["01-Q1", "03-Q2"])

    def test_it_never_returns_more_than_it_was_asked_for(self):
        self.assertEqual(len(nearest("anything at all", self.entries, count=1)), 1)

    def test_an_empty_rulings_file_has_no_nearest_entry(self):
        self.assertEqual(nearest("anything", []), [])


ANSWERED = """# answered by the brief of 2026-09-14

q-h0912-1
q-h0912-2
"""
QUEUE = """# decisions-queue

## 01-Q1: Which local Postgres `q-h0912-1`

body

## 01-Q2: Where does the search radius come from `q-h0912-2`

body

## 07-Q1: Who owns the depot import `q-h0912-3`

body
"""


class PathFor(unittest.TestCase):
    """The walk upward is bounded by the tree that owns the shard.

    `collect_shards.py` is built on per-worktree ownership: a shard under
    `<tree>/` belongs to that tree and no session reads or writes across the
    boundary (ruling 18). A walk with no bound crosses it, because a worktree
    lives INSIDE the checkout it was cut from.
    """

    def test_the_shard_finds_its_own_tree_rulings_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            shard = os.path.join(tmp, ".scratch", "decisions-queue.d", "t", "x.md")
            os.makedirs(os.path.dirname(shard))
            self.assertEqual(path_for(shard),
                             os.path.join(tmp, ".scratch", "rulings.md"))

    def test_the_walk_stops_at_the_tree_that_owns_the_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".scratch"))
            os.makedirs(os.path.join(tmp, ".git"))
            inner = os.path.join(tmp, ".claude", "worktrees", "other")
            os.makedirs(os.path.join(inner, ".git"))
            shard = os.path.join(inner, "decisions-queue.d", "t", "x.md")
            os.makedirs(os.path.dirname(shard))
            self.assertEqual(path_for(shard), "",
                             "a tree with no `.scratch` borrowed its parent's")

    def test_a_path_under_no_tree_at_all_finds_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(path_for(os.path.join(tmp, "loose.md")), "")


class Answered(unittest.TestCase):
    """Acceptance criterion 3: one rulings entry per answered item.

    The fixture answers two of the queue's three items. `01-Q1` has an entry,
    `01-Q2` does not, and `07-Q1` was never answered so it is owed nothing.
    """

    def setUp(self):
        self.entries = parse(FILE)

    def test_an_answered_item_with_no_entry_is_named(self):
        gaps = check_answered(ANSWERED, QUEUE, self.entries)
        self.assertEqual(len(gaps), 1)
        self.assertIn("q-h0912-2", gaps[0])
        self.assertIn("01-Q2", gaps[0])

    def test_an_entry_under_either_id_on_the_heading_counts(self):
        """The brief writes the question reference; the shard retires by the
        `q-` id. An entry under either one answers the item."""
        by_retirement = FILE.replace("`01-Q1`", "`q-h0912-1`")
        gaps = check_answered(ANSWERED, QUEUE, parse(by_retirement))
        self.assertEqual(len(gaps), 1)
        self.assertIn("q-h0912-2", gaps[0])

    def test_an_unanswered_item_is_owed_no_entry(self):
        gaps = check_answered(ANSWERED, QUEUE, self.entries)
        self.assertNotIn("q-h0912-3", "".join(gaps))

    def test_an_answered_id_the_queue_does_not_hold_is_named(self):
        gaps = check_answered("q-h0912-9\n", QUEUE, self.entries)
        self.assertEqual(len(gaps), 1)
        self.assertIn("q-h0912-9", gaps[0])
        self.assertIn("no item", gaps[0])

    def test_a_brief_that_wrote_every_entry_walks_clean(self):
        full = FILE + (
            "\n## 2026-09-14 `01-Q2` — where the search radius comes from\n"
            "Ruled: read it off the depot row.\n"
            "Carried by: `.scratch/example-feature/issues/03-the-radius.md`\n")
        self.assertEqual(check_answered(ANSWERED, QUEUE, parse(full)), [])


class Commit(unittest.TestCase):
    """Acceptance criterion 4: the ruling lands with the edit it caused.

    An attended session records a ruling by writing its own `ruled.md` shard.
    The file list of the commit that carries it must also carry the rulings
    file, or the ruling is retired off the board with nothing on record.
    """

    RULED = ".scratch/decisions-queue.d/issue-04-1bf724/ruled.md"
    RULINGS = ".scratch/rulings.md"
    ISSUE = ".scratch/example-feature/issues/01-the-test-database.md"

    def test_a_ruling_without_its_rulings_file_is_refused(self):
        gaps = check_commit([self.RULED, self.ISSUE])
        self.assertEqual(len(gaps), 1)
        self.assertIn("ruled.md", gaps[0])
        self.assertIn("rulings.md", gaps[0])

    def test_the_same_commit_carrying_both_passes(self):
        self.assertEqual(
            check_commit([self.RULED, self.ISSUE, self.RULINGS]), [])

    def test_a_commit_that_rules_nothing_is_owed_nothing(self):
        self.assertEqual(check_commit([self.ISSUE, "lib/rulings.py"]), [])

    def test_the_brief_own_answered_shard_is_not_an_attended_ruling(self):
        """`answered.md` is the daily brief's, and the brief's entries are
        checked by `check_answered` against the queue, not by file list."""
        answered = ".scratch/decisions-queue.d/main/answered.md"
        self.assertEqual(check_commit([answered, self.ISSUE]), [])

    def test_two_trees_ruling_at_once_are_both_named(self):
        second = ".scratch/decisions-queue.d/issue-05-aa11bb/ruled.md"
        self.assertEqual(len(check_commit([self.RULED, second])), 2)

    def test_a_rulings_file_in_another_directory_does_not_count(self):
        """The entry has to land in the `.scratch` the retirement shard lives
        in. Another feature's copy, or a doc of the same name, leaves this
        project's own record untouched."""
        gaps = check_commit([self.RULED, "docs/rulings.md"])
        self.assertEqual(len(gaps), 1)

    def test_a_windows_style_path_is_read_the_same_way(self):
        gaps = check_commit([self.RULED.replace("/", "\\")])
        self.assertEqual(len(gaps), 1)


LOG = """# decisions-log

## 01-Q1: Which local Postgres, and at what concurrency `q-h0912-1`

Answered 2026-09-13. One Postgres 16 container per worktree, tests serial.
Written into `.scratch/example-feature/issues/01-the-test-database.md`.

## 09-Q4: no answer was ever written here `q-h0912-8`
"""


class Fold(unittest.TestCase):
    """`decisions-log.md`, where a project has one, becomes rulings entries.

    The log is the answered half of the queue, so it carries queue items. The
    ruling is the item's first prose line and the subject is its heading; a
    date on that line is used, and today's is not invented for one that has
    none.
    """

    def test_an_answered_item_becomes_an_entry(self):
        entries = parse(fold(LOG, home="docs/decisions-log.md"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].question, "01-Q1")
        self.assertEqual(entries[0].date, "2026-09-13")
        self.assertIn("Postgres 16 container", entries[0].ruling)
        self.assertEqual(entries[0].home, "docs/decisions-log.md")

    def test_the_subject_keeps_the_heading_and_drops_its_ids(self):
        entries = parse(fold(LOG, home="docs/decisions-log.md"))
        self.assertEqual(entries[0].subject,
                         "Which local Postgres, and at what concurrency")

    def test_an_item_with_no_answer_is_not_folded(self):
        self.assertNotIn("09-Q4", fold(LOG, home="docs/decisions-log.md"))

    def test_an_answer_carrying_no_date_still_parses_back(self):
        """Folding must never emit an entry its own reader drops. An undated
        answer is a worse record than a dated one and a far better one than a
        ruling that vanishes between the write and the read."""
        undated = "## 02-Q1: who owns the depot import `q-x-1`\n\nOps owns it.\n"
        text = fold(undated, home="docs/decisions-log.md")
        entries = parse(text)
        self.assertEqual(len(entries), 1, text)
        self.assertEqual(entries[0].date, "undated")
        self.assertEqual(entries[0].ruling, "Ops owns it.")

    def test_the_question_reference_names_the_entry_not_the_retirement_id(self):
        entries = parse(fold(LOG, home="docs/decisions-log.md"))
        self.assertEqual(entries[0].question, "01-Q1")

    def test_the_folded_file_guards_the_question_it_answered(self):
        """The point of folding: a subject in the log now refuses a new ask."""
        entries = parse(fold(LOG, home="docs/decisions-log.md"))
        self.assertTrue(matches("which local Postgres at what concurrency",
                                entries, issue="05"))


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def drive(*argv):
    """`main` run over `argv`, as `(exit code, stdout, stderr)`.

    Lifted out of `Main` when `UnreadablePaths` needed the same road. One
    driver, because two would drift on which stream they captured.
    """
    err = io.StringIO()
    out = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Main(unittest.TestCase):
    def run_main(self, *argv):
        return drive(*argv)

    def test_a_brief_that_recorded_nothing_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_main(
                "--answered", write(tmp, "answered.md", ANSWERED),
                "--queue", write(tmp, "queue.md", QUEUE),
                "--rulings", write(tmp, "rulings.md", FILE))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertIn("q-h0912-2", err)

    def test_a_commit_file_list_is_graded_from_the_command_line(self):
        code, _, err = self.run_main(
            "--commit", ".scratch/decisions-queue.d/t/ruled.md")
        self.assertEqual(code, 1)
        self.assertIn("rulings.md", err)

    def test_a_clean_commit_exits_zero_and_says_so(self):
        code, out, err = self.run_main(
            "--commit", ".scratch/decisions-queue.d/t/ruled.md",
            "--commit", ".scratch/rulings.md")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("rulings", out)

    def test_the_fold_prints_entries_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = write(tmp, "decisions-log.md", LOG)
            code, out, _ = self.run_main("--fold", log)
        self.assertEqual(code, 0)
        self.assertIn("`01-Q1`", out)
        self.assertEqual(len(parse(out)), 1)

    def test_listing_a_rulings_file_prints_one_line_per_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_main("--list", write(tmp, "r.md", FILE))
        self.assertEqual(code, 0)
        self.assertEqual(len([line for line in out.splitlines() if line.strip()]), 2)

    def test_an_invocation_that_selects_no_work_asserts_nothing(self):
        """The directory's own convention: nothing read, nothing passes. A
        dropped or mistyped flag must not read as a clean walk."""
        code, out, err = self.run_main()
        self.assertEqual(code, EMPTY)
        self.assertIn("nothing was checked", err)
        self.assertEqual(out, "")

    def test_answered_without_its_rulings_file_is_an_error_not_a_wall(self):
        """Without the file every retired id reads as unrecorded, which blames
        the operator for entries they did write. `--queue` already works this
        way one line above."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                main(["--answered", write(tmp, "a.md", ANSWERED),
                      "--queue", write(tmp, "q.md", QUEUE)])


class UnreadablePaths(unittest.TestCase):
    """A path the operator NAMED and this reader could not open is a refusal.

    Measured 2026-09-17:
    `rulings.py --rulings .scratch/rulings.md --list ti06` printed
    `ti06: no ruling on record.` and exited 0, while that rulings file held
    sixteen entries. That sentence is byte-for-byte what `--list` prints for a
    rulings file which exists and holds none, so a search term, a typo or a
    moved file read as "nothing is ruled". The reader then asks the human a
    question already answered, which is the one failure the rulings file
    exists to prevent.

    The two cases this separates BOTH parse to zero entries, so the trigger is
    whether the path could be opened, never how many entries came back.
    """

    def test_the_exit_code_is_the_directory_own_shared_one(self):
        """`EMPTY` is `empty_input.EXIT_EMPTY`, not a second 2 beside it.

        The guard's docstring is explicit that 1 is "read and wrong" and 2 is
        "could not be read, so nothing is asserted". Two names holding one
        number is the drift this directory keeps writing rules against.
        """
        self.assertEqual(EMPTY, EXIT_EMPTY)

    def test_the_measured_search_term_is_refused(self):
        """The exact invocation of 2026-09-17, pinned as it was typed: a search
        term where `--list` wants a path, against a rulings file that holds
        entries. The term is refused and the entries are never printed."""
        with tempfile.TemporaryDirectory() as tmp:
            held = write(tmp, "rulings.md", FILE)
            code, out, err = drive("--rulings", held, "--list", "ti06")
        self.assertEqual(code, EMPTY)
        self.assertIn("REFUSED", err)
        self.assertIn("ti06", err)
        self.assertNotIn("no ruling on record", out)

    def test_a_path_that_is_not_there_is_refused_and_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            gone = os.path.join(tmp, "gone.md")
            code, out, err = drive("--list", gone)
        self.assertEqual(code, EMPTY)
        self.assertIn("REFUSED", err)
        self.assertIn(gone, err)
        self.assertEqual(out, "")

    def test_a_missing_rulings_file_is_refused_not_crashed(self):
        """A refusal, not a traceback. The reader is told which path failed and
        why, and no exception escapes `main`."""
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = drive("--list", os.path.join(tmp, "gone.md"))
        self.assertEqual(code, EMPTY)
        self.assertIn("No such file", err)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root reads a file whatever its mode, so the unreadable "
                     "case cannot be staged here")
    def test_a_path_that_cannot_be_read_is_refused(self):
        """Present but unreadable is the second half of the same refusal. It
        used to answer the empty string exactly as a missing path did."""
        with tempfile.TemporaryDirectory() as tmp:
            shut = write(tmp, "shut.md", FILE)
            os.chmod(shut, 0)
            try:
                code, out, err = drive("--list", shut)
            finally:
                os.chmod(shut, stat.S_IRUSR | stat.S_IWUSR)
        self.assertEqual(code, EMPTY)
        self.assertIn("REFUSED", err)
        self.assertIn(shut, err)
        self.assertEqual(out, "")

    def test_a_readable_file_holding_no_entry_keeps_its_own_wording(self):
        """The other half of the pair, unchanged. A project that has recorded
        no ruling yet is a state, not a fault, and still exits clean."""
        with tempfile.TemporaryDirectory() as tmp:
            bare = write(tmp, "rulings.md", "# Rulings\n\nnothing yet\n")
            code, out, err = drive("--list", bare)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), f"{bare}: no ruling on record.")
        self.assertEqual(err, "")

    def test_an_empty_file_is_not_the_same_answer_as_a_missing_one(self):
        """The whole defect in one assertion: the two roads must not print the
        same sentence at the same exit code."""
        with tempfile.TemporaryDirectory() as tmp:
            bare = write(tmp, "rulings.md", "# Rulings\n")
            kept = drive("--list", bare)
            gone = drive("--list", os.path.join(tmp, "gone.md"))
        self.assertNotEqual(kept[0], gone[0])
        self.assertNotEqual((kept[1], kept[2]), (gone[1], gone[2]))

    def test_a_rulings_file_that_holds_entries_lists_every_one_of_them(self):
        """The road every skill types. The count is read off `parse` rather
        than written as a number, so the case pins that the listing is short by
        nothing -- which is the regression worth pinning."""
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "rulings.md", FILE)
            held = len(parse(FILE))
            code, out, err = drive("--list", path)
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(len(lines), held)
        self.assertGreaterEqual(len(lines), 2)

    def test_the_fold_refuses_a_path_that_is_not_there(self):
        """`--fold` printed one blank line and exited 0, which reads exactly
        like a log holding no answered item."""
        with tempfile.TemporaryDirectory() as tmp:
            gone = os.path.join(tmp, "decisions-log.md")
            code, out, err = drive("--fold", gone)
        self.assertEqual(code, EMPTY)
        self.assertIn("REFUSED", err)
        self.assertIn(gone, err)
        self.assertEqual(out, "")

    def test_the_answered_road_refuses_a_path_that_is_not_there(self):
        """The worst of the three. With no `answered.md` there were no ids to
        grade, so it printed its own pass sentence over a file that does not
        exist."""
        with tempfile.TemporaryDirectory() as tmp:
            gone = os.path.join(tmp, "answered.md")
            code, out, err = drive(
                "--answered", gone,
                "--queue", write(tmp, "queue.md", QUEUE),
                "--rulings", write(tmp, "rulings.md", FILE))
        self.assertEqual(code, EMPTY)
        self.assertIn("REFUSED", err)
        self.assertIn(gone, err)
        self.assertNotIn("every answer on record", out)

    def test_the_answered_road_refuses_a_queue_that_is_not_there(self):
        """A missing queue blamed the brief for every id it had retired. The
        operator named this path too, so its absence is a typo, not a state."""
        with tempfile.TemporaryDirectory() as tmp:
            gone = os.path.join(tmp, "queue.md")
            code, _, err = drive(
                "--answered", write(tmp, "answered.md", ANSWERED),
                "--queue", gone,
                "--rulings", write(tmp, "rulings.md", FILE))
        self.assertEqual(code, EMPTY)
        self.assertIn(gone, err)

    def test_the_answered_road_refuses_a_rulings_file_that_is_not_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            gone = os.path.join(tmp, "rulings.md")
            code, _, err = drive(
                "--answered", write(tmp, "answered.md", ANSWERED),
                "--queue", write(tmp, "queue.md", QUEUE),
                "--rulings", gone)
        self.assertEqual(code, EMPTY)
        self.assertIn(gone, err)

    def test_a_project_with_no_rulings_file_is_still_read_as_empty(self):
        """The derived road's swallow is NOT changed, and this pins that. A
        project that has never recorded a ruling legitimately has no file, and
        `check_queue_shard` refuses questions rather than the absence of a
        record. The guard's own rule: where zero is legitimate and the reader
        says so, leave it."""
        from rulings import entries_for
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(entries_for(os.path.join(tmp, "shard.md")), ([], []))


# The entry measured on 2026-09-17, copied as it was written. Two backticked
# paths on one `Carried by:` line, which the capture forbids, so the whole
# entry left the file with nothing said about it.
BROKEN_CARRIED = """# Rulings

## 2026-09-13 `01-Q1` — local Postgres for tests, and at what concurrency
Ruled: one Postgres 16 container per worktree, tests serial, no concurrency knob.
Carried by: `.scratch/example-feature/issues/01-the-test-database.md`

## 2026-09-17 `ti06-9` — a subject
Ruled: something was ruled.
Carried by: `run-issues/SKILL.md` line 1020, and `.scratch/x.md`
"""

# The other half of the same shape: a heading and a home, and no ruling on the
# `Ruled:` line to apply.
BROKEN_RULED = """# Rulings

## 2026-09-17 `ti06-8` — a second subject
Ruled:
Carried by: `lib/rulings.py`
"""

# An entry that carries no `Carried by:` line at all.
ABSENT_CARRIED = """# Rulings

## 2026-09-17 `ti06-7` — a third subject
Ruled: something else was ruled.
"""


class Skipped(unittest.TestCase):
    """An entry this reader cannot parse is NAMED, never dropped in silence.

    `parse` dropped it on a `continue`, and every road out of this module turns
    a dropped entry into "no such ruling": `--list` printed a shorter file than
    the one on disk, and `check_queue_shard.py` let through the question the
    entry had already answered. That is the failure the rulings file was built
    to prevent, and the silence meant nobody learned the entry was bad.
    """

    def test_a_well_formed_file_is_skipped_over_nothing(self):
        self.assertEqual(skipped(FILE), [])

    def test_the_measured_carried_line_is_named_rather_than_dropped(self):
        reasons = skipped(BROKEN_CARRIED)
        self.assertEqual(len(reasons), 1)
        self.assertIn("ti06-9", reasons[0])
        self.assertIn("Carried by:", reasons[0])

    def test_the_good_entries_of_a_file_still_parse(self):
        """The refusal is per entry. A file is not thrown away over one line."""
        held = parse(BROKEN_CARRIED)
        self.assertEqual([one.question for one in held], ["01-Q1"])

    def test_a_ruled_line_that_does_not_parse_is_named(self):
        reasons = skipped(BROKEN_RULED)
        self.assertEqual(len(reasons), 1)
        self.assertIn("ti06-8", reasons[0])
        self.assertIn("Ruled:", reasons[0])
        self.assertEqual(parse(BROKEN_RULED), [])

    def test_an_empty_ruled_line_does_not_reach_across_the_break(self):
        """The other silence in the same function. `\\s*` crosses a newline, so
        an entry with nothing on its `Ruled:` line used to record its
        `Carried by:` line as the ruling and parse clean."""
        held = parse(BROKEN_RULED)
        self.assertEqual(held, [])
        self.assertNotIn("Carried by", "".join(one.ruling for one in held))

    def test_an_absent_line_is_named_as_absent(self):
        """Missing and malformed want different repairs, so they read
        differently."""
        reasons = skipped(ABSENT_CARRIED)
        self.assertEqual(len(reasons), 1)
        self.assertIn("ti06-7", reasons[0])
        self.assertIn("no `Carried by:` line", reasons[0])

    def test_the_refusal_names_the_heading_and_the_failing_line(self):
        """Both halves, because one without the other sends the reader
        hunting: the heading says WHICH entry, the line says what to fix."""
        reason = skipped(BROKEN_CARRIED)[0]
        self.assertIn("`ti06-9`", reason)
        self.assertIn("a subject", reason)
        self.assertIn("run-issues/SKILL.md", reason)
        self.assertIn(".scratch/x.md", reason)

    def test_the_refusal_opens_with_the_line_number_of_the_heading(self):
        """`<line>: ...`, so a caller prefixes its path and gets the
        `path:line:` shape the rest of this directory prints."""
        reason = skipped(BROKEN_CARRIED)[0]
        self.assertTrue(reason.startswith("7:"), reason)


class EveryHeadingIsAccountedFor(unittest.TestCase):
    """One entry in, one entry out. A file of seventeen entries of which one is
    unreadable parses to a perfectly confident sixteen, so the count this reads
    back is graded against the file's own headings rather than a number."""

    def test_a_clean_record_reads_back_one_entry_per_heading(self):
        text = FILE + "".join(
            f"\n## 2026-09-{day:02d} `{day:02d}-Q1` — subject number {day}\n"
            f"Ruled: the ruling for {day}.\n"
            f"Carried by: `.scratch/example-feature/issues/{day:02d}-a.md`\n"
            for day in range(10, 25))
        self.assertEqual(skipped(text), [])
        self.assertEqual(len(parse(text)), len(HEADING.findall(text)))
        self.assertGreaterEqual(len(parse(text)), 17)

    def test_one_unreadable_entry_is_the_difference_between_the_two_counts(self):
        text = FILE + ("\n## 2026-09-20 `20-Q1` — an entry with no ruling line\n"
                       "Carried by: `.scratch/example-feature/issues/20-a.md`\n")
        self.assertEqual(len(HEADING.findall(text)), 3)
        self.assertEqual(len(parse(text)), 2)
        self.assertEqual(len(skipped(text)), 1)


class SkippedOnTheCommandLine(unittest.TestCase):
    def test_the_list_road_refuses_and_still_prints_what_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = drive(
                "--list", write(tmp, "rulings.md", BROKEN_CARRIED))
        self.assertEqual(code, WRONG)
        self.assertIn("REFUSED", err)
        self.assertIn("ti06-9", err)
        self.assertIn("01-Q1", out)

    def test_a_file_whose_only_entry_is_broken_is_not_read_as_empty(self):
        """`no ruling on record` is the sentence for a file that holds none.
        An entry this reader could not read is not an absence of rulings."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = drive(
                "--list", write(tmp, "rulings.md", BROKEN_RULED))
        self.assertEqual(code, WRONG)
        self.assertNotIn("no ruling on record", out)
        self.assertIn("ti06-8", err)

    def test_the_refusal_names_the_file_it_was_read_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "rulings.md", BROKEN_CARRIED)
            _, _, err = drive("--list", path)
        self.assertIn(f"{path}:7:", err)

    def test_the_answered_road_refuses_a_record_it_could_not_fully_read(self):
        """`--answered` grades retired ids against the entries it parsed, so a
        dropped entry blames the brief for a ruling it did write."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = drive(
                "--answered", write(tmp, "answered.md", ANSWERED),
                "--queue", write(tmp, "queue.md", QUEUE),
                "--rulings", write(tmp, "rulings.md", BROKEN_CARRIED))
        self.assertEqual(code, WRONG)
        self.assertIn("ti06-9", err)
        self.assertNotIn("every answer on record", out)



if __name__ == "__main__":
    unittest.main()
