#!/usr/bin/env python3
"""Tests for check_issue_links.

The fixtures copy the four file-name shapes this tracker actually holds, because
telling them apart is the whole job:

    536-a-purchase-order-...   a plain issue whose title starts with an article
    312d-the-...               a split half, letter with no hyphen
    308a / 308b                a split whose parent has no file of its own
    221-a-sale-can-never-...   an issue that closed and moved to the archive

The article case is the one that paid for this script. `536-a-...` and `536a-...`
are one character apart, and a reader that splits a file name at the first hyphen
gets `536-a` out of the first.
"""

import contextlib
import io
import os
import tempfile
import unittest

import check_issue_links as cil
from check_issue_links import (
    NOTE,
    REFUSE,
    classify,
    index,
    links,
    main,
    markdown_files,
)

# The two-direction edge refusals arrived after the link walk and are a
# separate module in this pack's history. Probe for them rather than assume:
# where `check_issue_links.py` here predates them, `Edges` below skips instead
# of failing, and runs unchanged the moment the module carries them.
EDGE_REFUSALS = hasattr(cil, "edge_findings")

# The tracker as it stands: an article-titled issue, a split half, a split whose
# parent is gone, and an archived issue that still answers live links.
ISSUE_FILES = (
    "536-a-purchase-order-preview-failure-blanks-the-whole-deal-page.md",
    "583-capability-categories-read-crashes-deal-page.md",
    "312d-the-zoho-status-readback.md",
    "308a-the-brand-stage-and-the-platform-admin-load-route.md",
    "308b-the-catalogue-stage-loads-in-one-transaction.md",
)
ARCHIVE_FILES = ("221-a-sale-can-never-be-zero-rated.md",)


def tracker(tmp, issue_bodies=None):
    """Write a tracker under tmp and return (issues dir, archive dir)."""
    issues = os.path.join(tmp, "issues")
    archive = os.path.join(tmp, "archive")
    os.makedirs(issues)
    os.makedirs(archive)
    bodies = issue_bodies or {}
    for name in ISSUE_FILES:
        with open(os.path.join(issues, name), "w", encoding="utf-8") as handle:
            handle.write(bodies.get(name, "# an issue with no links\n"))
    for name in ARCHIVE_FILES:
        with open(os.path.join(archive, name), "w", encoding="utf-8") as handle:
            handle.write("# a closed issue\n")
    return issues, archive


class Index(unittest.TestCase):
    def test_an_article_title_does_not_become_a_letter_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, _ = tracker(tmp)
            whole, halves = index([issues])
        self.assertIn("536", whole)
        self.assertNotIn("536a", whole)
        self.assertNotIn("536", halves)

    def test_a_letter_suffix_is_read_as_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, _ = tracker(tmp)
            whole, halves = index([issues])
        self.assertIn("312d", whole)
        self.assertEqual(halves["308"], ["308a", "308b"])

    def test_an_archive_root_resolves_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp)
            whole, _ = index([issues, archive])
        self.assertIn("221", whole)

    def test_a_file_that_starts_with_no_number_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, _ = tracker(tmp)
            with open(os.path.join(issues, "README.md"), "w",
                      encoding="utf-8") as handle:
                handle.write("# not an issue\n")
            whole, _ = index([issues])
        self.assertNotIn("README", whole)
        self.assertEqual(len(whole), len(ISSUE_FILES))


class Scanner(unittest.TestCase):
    def test_it_reports_the_line_a_link_sits_on(self):
        found = list(links("one\ntwo [[536]] here\nthree [[583]]\n"))
        self.assertEqual(found, [("536", 2), ("583", 3)])

    def test_a_hyphenated_link_is_read_rather_than_skipped(self):
        self.assertEqual(list(links("[[536-a]]")), [("536-a", 1)])

    def test_markdown_files_ignores_everything_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "a.md"), "w").close()
            open(os.path.join(tmp, "b.txt"), "w").close()
            found = [os.path.basename(p) for p in markdown_files(tmp)]
        self.assertEqual(found, ["a.md"])


class Classify(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp)
            self.whole, self.halves = index([issues, archive])

    def verdict(self, link):
        return classify(link, self.whole, self.halves)

    def test_a_link_that_resolves_is_allowed(self):
        for link in ("536", "583", "312d", "308a", "221"):
            with self.subTest(link=link):
                self.assertIsNone(self.verdict(link))

    def test_the_hyphenated_shape_is_refused_and_names_both_readings(self):
        severity, reason = self.verdict("536-a")
        self.assertEqual(severity, REFUSE)
        self.assertIn("`536`", reason)
        self.assertIn("`536a`", reason)

    def test_the_hyphenated_refusal_does_not_depend_on_the_number_existing(self):
        # `742` has no file at all. The shape is wrong whatever it points at, so
        # this must refuse on the shape and never fall through to "unknown".
        severity, reason = self.verdict("742-b")
        self.assertEqual(severity, REFUSE)
        self.assertIn("never an", reason)

    def test_a_split_parent_is_a_note_and_names_its_halves(self):
        severity, reason = self.verdict("308")
        self.assertEqual(severity, NOTE)
        self.assertIn("`308a`", reason)
        self.assertIn("`308b`", reason)

    def test_a_number_nobody_minted_is_refused(self):
        severity, reason = self.verdict("742")
        self.assertEqual(severity, REFUSE)
        self.assertIn("no issue file", reason)

    def test_a_link_that_is_not_identifier_shaped_is_ignored(self):
        for link in ("pending-actions", "nnn", ":space:", "NNN", "536b-x"):
            with self.subTest(link=link):
                self.assertIsNone(self.verdict(link))


class Main(unittest.TestCase):
    def run_main(self, bodies, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp, bodies)
            argv = ["--issues", issues, "--archive", archive] + list(extra)
            return main(argv)

    def test_a_tracker_whose_links_all_resolve_exits_zero(self):
        body = "Blocked by [[583]] and [[312d]]. See [[221]].\n"
        code = self.run_main({ISSUE_FILES[0]: body})
        self.assertEqual(code, 0)

    def test_the_fault_this_script_exists_for_exits_one(self):
        code = self.run_main(
            {ISSUE_FILES[1]: "**Build this BEFORE [[536-a]].**\n"})
        self.assertEqual(code, 1)

    def test_a_tracker_with_no_link_at_all_exits_two(self):
        # Zero links read is not a pass. Nothing was asserted.
        self.assertEqual(self.run_main({}), 2)

    def test_a_root_that_is_not_there_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp, {ISSUE_FILES[0]: "[[583]]\n"})
            code = main(["--issues", issues, "--archive", archive,
                         "--scan", os.path.join(tmp, "no-such-dir")])
        self.assertEqual(code, 2)

    def test_an_issue_directory_holding_no_issue_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = os.path.join(tmp, "issues")
            os.makedirs(empty)
            self.assertEqual(main(["--issues", empty]), 2)

    def test_a_scanned_directory_outside_issues_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp, {ISSUE_FILES[0]: "[[583]]\n"})
            harden = os.path.join(tmp, "harden")
            os.makedirs(harden)
            with open(os.path.join(harden, "seam.md"), "w",
                      encoding="utf-8") as handle:
                handle.write("finding 2 cites [[536-a]]\n")
            code = main(["--issues", issues, "--archive", archive,
                         "--scan", harden])
        self.assertEqual(code, 1)

    def test_scanning_the_issues_directory_twice_does_not_double_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues, archive = tracker(tmp, {ISSUE_FILES[0]: "[[583]]\n"})
            code = main(["--issues", issues, "--archive", archive,
                         "--scan", issues])
        self.assertEqual(code, 0)

    def test_a_split_parent_citation_passes_on_its_own(self):
        # The first real walk found 92 of these and nothing else. A checker that
        # refused them would refuse the tracker's own convention.
        code = self.run_main({ISSUE_FILES[1]: "It follows [[308]] on one page.\n"})
        self.assertEqual(code, 0)

    def test_the_flag_promotes_that_note_to_a_refusal(self):
        code = self.run_main({ISSUE_FILES[1]: "It follows [[308]] on one page.\n"},
                             extra=["--split-parent-refuses"])
        self.assertEqual(code, 1)

    def test_a_split_parent_note_never_hides_a_real_refusal(self):
        body = "It follows [[308]], and [[536-a]] blocks it.\n"
        self.assertEqual(self.run_main({ISSUE_FILES[1]: body}), 1)


@unittest.skipUnless(EDGE_REFUSALS,
                     "this pack's check_issue_links has no edge refusals")
class Edges(unittest.TestCase):
    """The two-direction edge refusals, issue 02 of the set that added them.

    Promotion cannot know what a minted issue blocks: it reads a register row and
    never the code. The harden pass reads the code, so it is the one place the
    edge can be written, and these refusals are what make it write both
    directions. Measured in one project on 2026-09-13: none of the 22
    needs-harden issues was named as a blocker by any other issue, and issue 64,
    the tab bar, was needed by every screen in prose only.
    """

    def edges_tracker(self, tmp, bodies):
        """A tracker holding exactly the files named, plus one resolvable link.

        The link is here because a walk that reads no `[[link]]` exits 2 and
        asserts nothing, and these tests are about the exit-1 road.
        """
        issues = os.path.join(tmp, "issues")
        os.makedirs(issues)
        for name, body in bodies.items():
            with open(os.path.join(issues, name), "w", encoding="utf-8") as handle:
                handle.write(body)
        return issues

    def run_main(self, bodies, extra=()):
        """(exit code, everything the run said) for a tracker of these files."""
        with tempfile.TemporaryDirectory() as tmp:
            issues = self.edges_tracker(tmp, bodies)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["--issues", issues] + list(extra))
            return code, out.getvalue() + err.getvalue()

    def test_a_stamped_issue_with_no_blocked_by_is_refused(self):
        """Criterion 1. The stamp says the pass read the code; the section is
        what it read the code FOR, so a stamp without one is a pass that did
        not do the work."""
        code, said = self.run_main({
            "64-the-tab-bar.md": (
                "Status: ready-for-agent\n"
                "Hardened: 2026-09-13 — 2 sharpened, 0 questions resolved.\n"
                "\n# The tab bar\n\nIt follows [[65]] on one page.\n"
            ),
            "65-the-screen-behind-it.md": "Status: needs-harden\n\n# behind\n",
        })
        self.assertEqual(code, 1)
        self.assertIn("64", said)
        self.assertIn("## Blocked by", said)

    # The fixture the criterion names: a screen that depends on the tab bar in
    # prose and nowhere else. This is the shape one tracker showed, where issue
    # 64 was needed by every screen and named as a blocker by none of them.
    TAB_BAR = "Status: needs-harden\n\n# The tab bar\n\nIt draws the tabs.\n"

    def screen(self, blocked_by):
        return (
            "Status: needs-harden\n"
            "\n# The settings screen\n\n"
            "It cites [[64]] for the shape. This screen assumes issue 64 has "
            "built the tab bar, so it only adds the panel.\n"
            f"\n## Blocked by\n\n{blocked_by}\n"
        )

    def test_a_prose_dependency_missing_from_the_section_is_refused(self):
        """Criterion 2. The sentence is quoted because the refusal has to be
        actionable without opening the file: the reader needs to see the
        dependency it read, not just the number it wants written down."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen("- None"),
        })
        self.assertEqual(code, 1)
        self.assertIn("This screen assumes issue 64 has built the tab bar", said)

    def test_the_same_file_passes_once_the_section_names_it(self):
        """Criterion 3. The repair is one bullet, and nothing else changes."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen("- 64"),
        })
        self.assertEqual(code, 0, said)

    def test_a_dependency_on_a_closed_issue_is_not_a_missing_edge(self):
        """A `done` issue blocks nothing: the code it builds is already there.
        Refusing here would ask every file to list its own history."""
        code, said = self.run_main({
            "64-the-tab-bar.md": "Status: done\n\n# The tab bar\n\nIt draws.\n",
            "65-the-settings-screen.md": self.screen("- None"),
        })
        self.assertEqual(code, 0, said)

    def test_a_sentence_that_only_names_an_issue_is_not_a_dependency(self):
        """The provenance line every minted issue carries names another issue
        and depends on nothing. A checker that refused those would refuse most
        of the tracker on its first day."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": (
                "Status: needs-harden\n\n# The settings screen\n\n"
                "It cites [[64]] for the shape. Measured on 2026-09-13, issue "
                "64 sat upstream of 56 open issues.\n"
                "\n## Blocked by\n\n- None\n"
            ),
        })
        self.assertEqual(code, 0, said)

    def test_a_verb_governing_another_clause_is_not_a_dependency(self):
        """The narrowing, pinned on the sentence that paid for it. This is one
        tracker's issue 47b, word for word: the verb belongs to `Nothing under
        src/`, and the numbers sit in a later clause saying who will call this
        issue's code — the edge runs the other way. Read sentence-wide, this and
        92 others refused across the 112 files of that tracker on 2026-09-13."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": (
                "Status: needs-harden\n\n# The settings screen\n\n"
                "It cites [[64]] for the shape. Nothing under `src/` calls the "
                "composer yet — no screen uploads a file until issue 64, and "
                "this issue writes no caller.\n"
                "\n## Blocked by\n\n- None\n"
            ),
        })
        self.assertEqual(code, 0, said)

    def test_a_blocker_declared_as_a_link_answers_the_prose(self):
        """A tracker writes half its blockers as `- [[240]] — the reason`: 122
        of a second tracker's `## Blocked by` bullets open with a link, measured
        2026-09-13. A reader of that section that saw only bare numbers would
        refuse the files that answer the question properly."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen("- [[64]] — the tabs."),
        })
        self.assertEqual(code, 0, said)

    def test_a_section_that_names_the_issue_has_answered_the_question(self):
        """A second tracker's issue 418, word for word in shape: the section
        names 421 and says the two do not block each other, and the body then
        says this issue runs after it. The writer read the edge and wrote the
        reason, which is everything this refusal exists to ask for — it catches
        silence."""
        code, said = self.run_main({
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen(
                "- None. Can start immediately.\n"
                "- Worth reading beside [[64]], which changes what the shortlist "
                "contains. It does not change what a tick means, so neither "
                "blocks the other."),
        })
        self.assertEqual(code, 0, said)

    @unittest.skipIf(os.geteuid() == 0, "root reads a file with no read bit")
    def test_an_unreadable_file_is_not_counted_as_a_missing_edge(self):
        """The count line is the sentence a reader acts on. A file this walk
        could not open says nothing about the edges in it, and a refusal that
        files it under `do not carry the edges they should` sends the reader to
        write a section into a file they cannot read."""
        with tempfile.TemporaryDirectory() as tmp:
            issues = self.edges_tracker(tmp, {
                "64-the-tab-bar.md": self.TAB_BAR,
                "65-the-settings-screen.md": self.screen("- 64"),
            })
            shut = os.path.join(issues, "66-the-unreadable-one.md")
            with open(shut, "w", encoding="utf-8") as handle:
                handle.write("Status: needs-harden\n\n# shut\n")
            os.chmod(shut, 0o000)
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), \
                        contextlib.redirect_stderr(err):
                    code = main(["--issues", issues])
            finally:
                os.chmod(shut, 0o644)
        said = out.getvalue() + err.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("cannot read the file", said)
        self.assertIn("1 file(s) could not be read", said)
        self.assertNotIn("do not carry the edges", said)

    def test_grade_narrows_the_edge_refusals_to_the_files_named(self):
        """The harden pass stamps the issues it just hardened, and it cannot
        repair a tracker's whole backlog to do it: 128 of a second tracker's 641
        files carry a stamp and no section, measured 2026-09-13, every one of
        them minted before the rule existed. Ungraded, the walk still resolves
        every link — only the edge refusals narrow. Same reason
        `check_origin.py` is run on one file and never over the directory."""
        bodies = {
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen("- None"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            issues = self.edges_tracker(tmp, bodies)
            graded = os.path.join(issues, "64-the-tab-bar.md")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["--issues", issues, "--grade", graded])
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())

    def test_grade_still_refuses_the_file_it_was_given(self):
        bodies = {
            "64-the-tab-bar.md": self.TAB_BAR,
            "65-the-settings-screen.md": self.screen("- None"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            issues = self.edges_tracker(tmp, bodies)
            graded = os.path.join(issues, "65-the-settings-screen.md")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["--issues", issues, "--grade", graded])
        self.assertEqual(code, 1)
        self.assertIn("issue 65 depends on open issue 64", err.getvalue())

    def test_a_graded_file_outside_the_issues_directory_refuses(self):
        """A path the walk never reads would grade nothing and report a pass,
        which is the one answer a checker may never give."""
        with tempfile.TemporaryDirectory() as tmp:
            issues = self.edges_tracker(tmp, {"64-the-tab-bar.md": self.TAB_BAR})
            stray = os.path.join(tmp, "66-elsewhere.md")
            with open(stray, "w", encoding="utf-8") as handle:
                handle.write("Status: needs-harden\n\n# stray\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = main(["--issues", issues, "--grade", stray])
        self.assertEqual(code, 2)
        self.assertIn("66-elsewhere.md", err.getvalue())


if __name__ == "__main__":
    unittest.main()
