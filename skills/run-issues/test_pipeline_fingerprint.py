#!/usr/bin/env python3
"""Cases for pipeline_fingerprint.py — ticket 37, ruling 23.

Every per-run line carries the HEAD of the skills, agents and hooks
repositories, with a `dirty` mark per repository when its tree holds
uncommitted files. A dirty tree still runs; the mark is a fact, not a refusal.

Why it matters, measured in the ticket's round 3 on 2026-09-05: the three
repositories were at `5215fb5`, `24f37ef` and `19b097f`, and NO ledger or row
named any of them. So a row saying a run got faster could not say what the
pipeline was when it ran, which is the whole question ticket 37 exists to
answer. The skills tree held four uncommitted files at that same read, which is
why the dirty mark is here at all.

    python3 -m unittest test_pipeline_fingerprint
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

import pipeline_fingerprint as tool


def git_repo(dirty: bool = False) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    run = lambda *args: subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True)
    run("init", "-q")
    run("config", "user.email", "t@example.test")
    run("config", "user.name", "t")
    (root / "a.py").write_text("one\n")
    run("add", "a.py")
    run("commit", "-qm", "one")
    if dirty:
        (root / "a.py").write_text("two\n")
    return root


class Measure(unittest.TestCase):

    def test_a_clean_repository_reads_its_head_and_is_not_dirty(self):
        root = git_repo()
        found = tool.measure({"skills": root})
        self.assertFalse(found["skills"].dirty)
        self.assertEqual(12, len(found["skills"].head))

    def test_an_uncommitted_change_marks_the_repository_dirty(self):
        root = git_repo(dirty=True)
        self.assertTrue(tool.measure({"skills": root})["skills"].dirty)

    def test_a_dirty_tree_is_never_a_refusal(self):
        """Ruling 23 states it: a dirty tree still runs, and the mark is a
        fact. A launch that refused here would stop a run for a stray
        `__pycache__` file, and the hooks repository held seven uncommitted
        files on 2026-09-06 with none of them code."""
        root = git_repo(dirty=True)
        found = tool.measure({"skills": root})
        self.assertTrue(found["skills"].head)

    def test_a_path_that_is_not_a_repository_reads_unknown(self):
        """Not an exception. This runs inside a launch, and ticket 39's
        rulings 10 and 22 keep a launch moving whatever it finds."""
        found = tool.measure({"skills": pathlib.Path(tempfile.mkdtemp())})
        self.assertEqual(tool.UNKNOWN, found["skills"].head)


class HeaderRoundTrip(unittest.TestCase):
    """The launch writes these lines into the ledger header; `run_costs.py`
    reads them back out and copies them onto the per-run line."""

    def test_the_header_names_all_three_repositories(self):
        text = tool.header_lines(tool.measure(
            {"skills": git_repo(), "agents": git_repo(), "hooks": git_repo()}))
        for name in ("skills", "agents", "hooks"):
            self.assertIn(name, text)

    def test_what_the_launch_writes_is_what_the_finale_reads(self):
        marks = tool.measure({"skills": git_repo(dirty=True),
                              "agents": git_repo(), "hooks": git_repo()})
        read_back = tool.from_ledger(tool.header_lines(marks))
        self.assertEqual({n: (m.head, m.dirty) for n, m in marks.items()},
                         {n: (m.head, m.dirty) for n, m in read_back.items()})

    def test_the_dirty_mark_survives_the_round_trip(self):
        """The one bit that decides whether a row may be compared at all."""
        marks = tool.measure({"skills": git_repo(dirty=True)})
        self.assertTrue(tool.from_ledger(tool.header_lines(marks))["skills"].dirty)

    def test_a_ledger_with_no_fingerprint_reads_empty_not_an_error(self):
        """Every ledger written before this sitting. Ruling 3 keeps them."""
        self.assertEqual({}, tool.from_ledger("# Run ledger\n\nState: merged\n"))

    def test_a_real_ledger_header_is_read_past(self):
        """The fingerprint lines sit among ticket 39's map lines, and the
        reader must not take one of those for a repository."""
        ledger = (
            "# Run ledger — `batch-x`\n"
            "Session model at launch: claude-opus-5\n"
            "Model map at launch: `implementer=opus verify=opus`\n"
            + tool.header_lines(tool.measure({"skills": git_repo()}))
            + "\nState: `merged`\n")
        found = tool.from_ledger(ledger)
        self.assertEqual(["skills"], list(found))


if __name__ == "__main__":
    unittest.main()
