#!/usr/bin/env python3
"""Prove the evidence gate can fail, and prove it stays out of the way.

Every refusal is driven on a temporary issue file built for it, and every pass
is driven on one too: a guard nobody has watched go red is a claim, not a check.

**Half this file exists for the misfires, not the refusals.** A gate that fires
on good work costs a run more than no gate at all, so the `DoesNotMisfire` class
below walks the shapes a real run produces that must all pass: a first attempt
with no gate sections yet, a fresh attempt whose record sits below the previous
round's verdicts, a re-spawn of the gate that died writing nothing while its
partner wrote, and every agent type that is not a run-issues gate.

    python3 test_run_issues_evidence_gate.py
"""

from __future__ import annotations

import importlib
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "run_issues_evidence_gate",
    pathlib.Path(__file__).resolve().parent / "run-issues-evidence-gate.py",
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


CRITERIA = "## Acceptance criteria\n\n- The thing works.\n"
RECORD = "## Implementation record (2026-08-23, attempt 1)\n\nBuilt the thing.\n"


def issue(*sections: str) -> pathlib.Path:
    """Write a throwaway issue file, in the tracker's own layout."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="evidence-")) / "issues"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "405-a-thing.md"
    path.write_text("# Issue 405\n\n" + "\n".join(sections), encoding="utf-8")
    return path


def spawn(agent_type: str, prompt: str) -> dict:
    return {"tool_input": {"subagent_type": agent_type, "prompt": prompt}}


def verify(path: pathlib.Path) -> tuple[int, str]:
    return gate.decide(spawn("run-issues-verify-gate", f"Issue 405 at {path}"))


def review(path: pathlib.Path) -> tuple[int, str]:
    return gate.decide(spawn("run-issues-review-gate", f"Issue 405 at {path}"))


class Scope(unittest.TestCase):
    def test_a_foreign_agent_type_passes_untouched(self):
        for agent_type in (
            "run-issues-implementer",
            "parallel-hunt-fix-gate",
            "harden-issues-attacker",
            "general-purpose",
            "",
        ):
            with self.subTest(agent_type=agent_type):
                self.assertEqual(gate.decide(spawn(agent_type, "no path here")), (0, ""))

    def test_both_gate_types_are_in_scope(self):
        self.assertEqual(gate.gate_section("run-issues-verify-gate"), "Verify gate")
        self.assertEqual(gate.gate_section("run-issues-review-gate"), "Review gate")

    def test_the_critical_review_variant_is_covered_without_being_named(self):
        self.assertEqual(
            gate.gate_section("run-issues-review-gate-critical"), "Review gate"
        )

    def test_unreadable_stdin_is_not_a_refusal(self):
        self.assertEqual(gate.decide({}), (0, ""))


class NoIssueFile(unittest.TestCase):
    def test_a_prompt_with_no_path_refuses(self):
        code, message = gate.decide(spawn("run-issues-verify-gate", "go and verify"))
        self.assertEqual(code, 2)
        self.assertIn("no readable file under an `issues/` directory", message)

    def test_a_path_that_does_not_exist_refuses(self):
        code, _ = gate.decide(
            spawn("run-issues-verify-gate", "issue at /nowhere/405.md")
        )
        self.assertEqual(code, 2)

    def test_the_ledger_beside_the_issues_directory_is_not_mistaken_for_one(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="evidence-"))
        ledger = root / "run.md"
        ledger.write_text("# Ledger\n\n| issue | status |\n", encoding="utf-8")
        code, message = gate.decide(
            spawn("run-issues-verify-gate", f"ledger at {ledger}")
        )
        self.assertEqual(code, 2)
        self.assertIn("no readable file under an `issues/` directory", message)

    def test_the_refusal_says_what_to_add(self):
        _, message = gate.decide(spawn("run-issues-verify-gate", "go"))
        self.assertIn("Add the issue file's path to the prompt", message)

    def test_the_refusal_names_the_rule_it_applied(self):
        """A reader meets this message at the moment their work is blocked, so
        it has to say which rule refused them."""
        _, message = gate.decide(spawn("run-issues-verify-gate", "go"))
        self.assertIn(gate.ISSUE_DIR, message)
        self.assertIn("Add the issue file's path to the prompt", message)


class NoRecord(unittest.TestCase):
    def test_an_issue_file_with_no_record_refuses(self):
        code, message = verify(issue(CRITERIA))
        self.assertEqual(code, 2)
        self.assertIn("no-record", message)

    def test_an_empty_record_body_refuses(self):
        path = issue(CRITERIA, "## Implementation record (attempt 1)\n\n")
        code, message = verify(path)
        self.assertEqual(code, 2)
        self.assertIn("empty body", message)

    def test_the_review_gate_refuses_the_same_way(self):
        code, message = review(issue(CRITERIA))
        self.assertEqual(code, 2)
        self.assertIn("no-record", message)

    def test_the_refusal_names_the_file(self):
        path = issue(CRITERIA)
        _, message = verify(path)
        self.assertIn(str(path), message)


class StaleRecord(unittest.TestCase):
    def test_a_gate_round_re_run_over_the_same_attempt_refuses(self):
        path = issue(CRITERIA, RECORD, "## Verify gate — PASS\n\nLooked fine.\n")
        code, message = verify(path)
        self.assertEqual(code, 2)
        self.assertIn("stale-record", message)

    def test_the_refusal_names_both_line_numbers(self):
        path = issue(CRITERIA, RECORD, "## Verify gate — PASS\n\nLooked fine.\n")
        _, message = verify(path)
        self.assertIn("line 7", message)  # the record
        self.assertIn("line 11", message)  # the gate section

    def test_a_review_re_run_over_the_same_attempt_refuses(self):
        path = issue(CRITERIA, RECORD, "## Review gate — PASS\n\nRead it.\n")
        code, message = review(path)
        self.assertEqual(code, 2)
        self.assertIn("stale-record", message)

    def test_a_gate_section_at_h3_depth_still_counts(self):
        path = issue(CRITERIA, RECORD, "### Verify gate — PASS\n\nLooked fine.\n")
        code, _ = verify(path)
        self.assertEqual(code, 2)

    def test_a_hyphenated_gate_heading_still_counts(self):
        path = issue(CRITERIA, RECORD, "## Verify-gate — PASS\n\nLooked fine.\n")
        code, _ = verify(path)
        self.assertEqual(code, 2)


class DoesNotMisfire(unittest.TestCase):
    def test_a_first_attempt_with_a_record_and_no_gates_passes(self):
        self.assertEqual(verify(issue(CRITERIA, RECORD)), (0, ""))
        self.assertEqual(review(issue(CRITERIA, RECORD)), (0, ""))

    def test_a_second_attempt_record_below_the_first_round_passes(self):
        path = issue(
            CRITERIA,
            "## Implementation record (attempt 1)\n\nFirst go.\n",
            "## Verify gate — REJECT\n\nOne defect.\n",
            "## Review gate — PASS\n\nFine.\n",
            "## Implementation record (attempt 2)\n\nFixed it.\n",
        )
        self.assertEqual(verify(path), (0, ""))
        self.assertEqual(review(path), (0, ""))

    def test_re_spawning_the_gate_that_died_while_its_partner_wrote_passes(self):
        # The verify gate died writing nothing; review wrote. Re-spawn verify.
        path = issue(
            CRITERIA,
            "## Implementation record (attempt 2)\n\nFixed it.\n",
            "## Review gate, attempt 2 — PASS\n\nRead it.\n",
        )
        self.assertEqual(verify(path), (0, ""))

    def test_a_record_carrying_a_date_and_no_attempt_number_passes(self):
        path = issue(CRITERIA, "## Implementation record — 2026-08-02\n\nDone.\n")
        self.assertEqual(verify(path), (0, ""))

    def test_a_record_written_as_h3_passes(self):
        path = issue(CRITERIA, "### Implementation record (attempt 1)\n\nDone.\n")
        self.assertEqual(verify(path), (0, ""))

    def test_a_prompt_naming_several_files_grades_the_issue_file(self):
        path = issue(CRITERIA, RECORD)
        prompt = f"Read {path.parent}/run.md and the issue at {path}, then judge."
        self.assertEqual(
            gate.decide(spawn("run-issues-verify-gate", prompt)), (0, "")
        )

    def test_an_issue_file_with_none_of_the_usual_headings_is_still_recognised(self):
        # The regression guard for the rule this hook was rewritten to use.
        # A live tracker of 402 issue files held 78 whose headings were `## Find`,
        # `## Wanted` or `## The gap` and nothing resembling criteria. A content
        # marker refused all of them; the structural rule must not.
        path = issue("## Find\n\nSomething is wrong.\n", RECORD)
        self.assertEqual(verify(path), (0, ""))

    def test_a_backticked_path_is_found(self):
        path = issue(CRITERIA, RECORD)
        prompt = f"Issue file: `{path}`"
        self.assertEqual(
            gate.decide(spawn("run-issues-verify-gate", prompt)), (0, "")
        )


class ReusesTheSharedMatcher(unittest.TestCase):
    """The heading logic must stay in one place, or it drifts."""

    def test_it_imports_check_verdict_rather_than_copying_it(self):
        self.assertIsNotNone(gate.check_verdict, "check_verdict did not import")
        self.assertTrue(hasattr(gate.check_verdict, "locate_section"))
        self.assertTrue(hasattr(gate.check_verdict, "read_section"))

    def test_the_hook_defines_no_heading_regex_of_its_own(self):
        source = (
            pathlib.Path(gate.__file__).read_text(encoding="utf-8")
            if getattr(gate, "__file__", None)
            else (
                pathlib.Path(__file__).resolve().parent / "run-issues-evidence-gate.py"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn("implementation record\\b", source.lower())

    def test_a_missing_library_refuses_rather_than_passes(self):
        saved = gate.check_verdict
        try:
            gate.check_verdict = None
            code, message = verify(issue(CRITERIA, RECORD))
            self.assertEqual(code, 2)
            self.assertIn("cannot import check_verdict", message)
        finally:
            gate.check_verdict = saved


if __name__ == "__main__":
    unittest.main(verbosity=2)
