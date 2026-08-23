#!/usr/bin/env python3
"""Prove the drift guard can fail.

A guard nobody has watched fail is a guard nobody knows the shape of. Every
test below drives one refusal on a temporary tree built for it, so the failure
is observed rather than assumed.

**What is deliberately NOT tested here: whether the live tree is clean.** That
is the script's job at the moment it runs, not a property of this code, and the
live tree changes without this file changing. A unit test asserting the live
tree is clean would go red on somebody else's edit and be switched off. The
real-tree tests below grade the CATALOGUE instead: that it points at files that
exist, that it is not empty, and that it holds no duplicate assertion.
"""

from __future__ import annotations

import io
import contextlib
import pathlib
import tempfile
import unittest

import check_skill_drift as guard

RUN_ISSUES = guard.RUN_ISSUES
PARALLEL_HUNT = guard.PARALLEL_HUNT


def tree(files: dict[str, str]) -> pathlib.Path:
    """A throwaway ~/.claude, holding exactly the files given."""
    root = pathlib.Path(tempfile.mkdtemp())
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return root


def present(needle, path=RUN_ISSUES, invariant="INV-TEST"):
    return guard.Predicate(
        invariant=invariant, kind="present", path=path, needle=needle, note="test rule"
    )


def absent(needle, path=PARALLEL_HUNT, invariant="INV-TEST"):
    return guard.Predicate(
        invariant=invariant, kind="absent", path=path, needle=needle, note="test rule"
    )


class HealthyTree(unittest.TestCase):
    def test_a_tree_the_catalogue_describes_raises_nothing(self):
        root = tree({RUN_ISSUES: "the runner commits\n", PARALLEL_HUNT: "workers run\n"})
        problems = guard.audit(root, [present("the runner commits"), absent("three refusals")])
        self.assertEqual(problems, [])

    def test_a_needle_may_span_the_middle_of_a_line(self):
        """Needles are substrings, not whole lines. A rule reworded around its
        operative clause must not trip the guard."""
        root = tree({RUN_ISSUES: "Note well: the runner commits, always.\n"})
        self.assertEqual(guard.audit(root, [present("the runner commits")]), [])


class Lost(unittest.TestCase):
    def test_a_rule_deleted_from_a_file_is_refused(self):
        root = tree({RUN_ISSUES: "nothing of the kind here\n"})
        problems = guard.audit(root, [present("the runner commits")])
        self.assertEqual([kind for kind, _ in problems], ["lost"])

    def test_it_names_every_lost_rule_not_only_the_first(self):
        root = tree({RUN_ISSUES: "empty\n"})
        problems = guard.audit(root, [present("first rule"), present("second rule")])
        self.assertEqual(len(problems), 2)


class Stale(unittest.TestCase):
    def test_a_false_claim_still_in_a_file_is_refused(self):
        """C5's shape: both skills said `check_verdict.py` has three refusals
        and it has four."""
        root = tree({PARALLEL_HUNT: "check_verdict.py has three refusals\n"})
        problems = guard.audit(root, [absent("three refusals")])
        self.assertEqual([kind for kind, _ in problems], ["stale"])

    def test_the_same_needle_can_be_required_in_one_file_and_banned_in_another(self):
        """A rule's home must keep it; the file that restates it wrongly must not."""
        root = tree({RUN_ISSUES: "shared clause\n", PARALLEL_HUNT: "shared clause\n"})
        problems = guard.audit(
            root, [present("shared clause"), absent("shared clause")]
        )
        self.assertEqual([kind for kind, _ in problems], ["stale"])


class MissingFile(unittest.TestCase):
    def test_a_catalogued_file_absent_from_disk_is_refused_not_passed(self):
        """The dangerous case: a renamed skill file silently satisfying every
        `absent` assertion while grading nothing."""
        root = tree({RUN_ISSUES: "present\n"})
        problems = guard.audit(root, [absent("anything", path=PARALLEL_HUNT)])
        self.assertEqual([kind for kind, _ in problems], ["missing-file"])

    def test_a_missing_file_is_reported_once_per_predicate(self):
        root = tree({})
        problems = guard.audit(root, [present("a"), present("b")])
        self.assertEqual([kind for kind, _ in problems], ["missing-file", "missing-file"])


class Rendering(unittest.TestCase):
    def test_the_refusal_names_the_invariant_the_file_and_the_needle(self):
        root = tree({RUN_ISSUES: "empty\n"})
        problems = guard.audit(root, [present("the runner commits", invariant="INV-42")])
        text = guard.render(problems)
        self.assertIn("INV-42", text)
        self.assertIn(RUN_ISSUES, text)
        self.assertIn("the runner commits", text)

    def test_an_entry_waiting_on_a_ruling_says_so_and_still_refuses(self):
        root = tree({PARALLEL_HUNT: "naming the model is not optional\n"})
        blocked = guard.Predicate(
            invariant="INV-25",
            kind="absent",
            path=PARALLEL_HUNT,
            needle="naming the model is not optional",
            note="contradicts the never-pass-a-model rule",
            ruling="C7: which of the two model rules governs a spawn",
        )
        problems = guard.audit(root, [blocked])
        self.assertEqual(len(problems), 1)
        self.assertIn("WAITS ON A RULING", guard.render(problems))

    def test_a_clean_tree_says_so(self):
        self.assertEqual(guard.render([]), "The two skill files still agree.")


class ExitCodes(unittest.TestCase):
    def test_an_empty_catalogue_refuses_rather_than_reporting_green(self):
        """A guard that asserts nothing must never print a pass. This is the
        state the file shipped in before its catalogue was filled."""
        catalogue, clashes = guard.CATALOGUE[:], guard.CONTRADICTIONS[:]
        guard.CATALOGUE.clear()
        guard.CONTRADICTIONS.clear()
        try:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = guard.main(["--root", str(tree({}))])
        finally:
            guard.CATALOGUE[:] = catalogue
            guard.CONTRADICTIONS[:] = clashes
        self.assertEqual(code, 2)
        self.assertIn("empty-catalogue", err.getvalue())

    def test_drift_exits_one_and_prints_to_stderr(self):
        root = tree({RUN_ISSUES: "empty\n", PARALLEL_HUNT: "empty\n"})
        original = guard.CATALOGUE[:]
        guard.CATALOGUE[:] = [present("a rule that is not there")]
        try:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = guard.main(["--root", str(root)])
        finally:
            guard.CATALOGUE[:] = original
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err.getvalue())

    def test_agreement_exits_zero(self):
        root = tree({RUN_ISSUES: "a rule that is there\n"})
        original = guard.CATALOGUE[:]
        guard.CATALOGUE[:] = [present("a rule that is there")]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = guard.main(["--root", str(root)])
        finally:
            guard.CATALOGUE[:] = original
        self.assertEqual(code, 0)


class TheCatalogue(unittest.TestCase):
    """Grades the catalogue itself, never the live tree's cleanliness."""

    def test_the_catalogue_is_not_empty(self):
        self.assertTrue(
            guard.CATALOGUE,
            "An empty catalogue grades nothing. Fill it from the skills audit.",
        )

    def test_every_entry_points_at_a_file_that_exists(self):
        root = pathlib.Path.home() / ".claude"
        missing = sorted(
            {p.path for p in guard.CATALOGUE if not (root / p.path).exists()}
        )
        self.assertEqual(missing, [], f"catalogue points at files not on disk: {missing}")

    def test_no_entry_is_duplicated(self):
        seen = [(p.path, p.kind, p.needle) for p in guard.CATALOGUE]
        duplicates = {item for item in seen if seen.count(item) > 1}
        self.assertEqual(duplicates, set(), f"duplicate assertions: {duplicates}")

    def test_every_entry_carries_a_note_and_a_known_kind(self):
        for predicate in guard.CATALOGUE:
            self.assertIn(predicate.kind, ("present", "absent"), predicate.invariant)
            self.assertTrue(predicate.note.strip(), predicate.invariant)

    def test_no_needle_is_short_enough_to_match_by_accident(self):
        """A three-word needle will match prose nobody meant to grade.

        Word count alone is the wrong measure, and this test caught its own
        first version being wrong: `run-issues/SKILL.md:479-487` is a single
        token and is about as distinctive as a string gets. Length is the
        second road to the same property, so either satisfies it.
        """
        for predicate in guard.CATALOGUE:
            words = len(predicate.needle.split())
            self.assertTrue(
                words >= 4 or len(predicate.needle) >= 20,
                f"{predicate.invariant}: needle too short to be distinctive: "
                f"{predicate.needle!r}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
