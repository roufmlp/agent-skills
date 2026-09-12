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

import os
import tempfile
import unittest

from check_issue_links import (
    NOTE,
    REFUSE,
    classify,
    index,
    links,
    main,
    markdown_files,
)

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
        for link in ("pending-on-abdul", "nnn", ":space:", "NNN", "536b-x"):
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


if __name__ == "__main__":
    unittest.main()
