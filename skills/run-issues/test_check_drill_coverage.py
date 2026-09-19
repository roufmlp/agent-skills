"""Drill for check_drill_coverage.py.

The corpus is issue 114's own shape: an acceptance criterion that names a drill,
and a gate verdict that grades it. The refused case is the one the critical
review gate of run `batch-26c495` actually wrote on 2026-09-17.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "check_drill_coverage", os.path.join(HERE, "check_drill_coverage.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


CRITERIA = """## Acceptance criteria

- [ ] **1. A worker is on a database of its own.** Some words.
      **Drive the mutation once, in this order:** delete the assignment, watch it red.
- [ ] **2. The wall clock is measured before and after.** No drill named here.
- [ ] **7. The shared bucket is answered.**
      **Drive it:** run the two loudest of the nine concurrently on two workers ten times.

## Must still be true
"""


def issue(verdict_body, heading="## Review gate"):
    return CRITERIA + "\n" + heading + "\n\n" + verdict_body + "\n"


def code(verdict_body, heading="## Review gate"):
    return mod.grade(issue(verdict_body, heading), heading)[0]


# ── Which criteria carry a drill ────────────────────────────────────────────

def test_only_the_criteria_naming_a_drill_are_graded():
    assert sorted(mod.criteria_with_drills(CRITERIA)) == [1, 7]


def test_an_issue_naming_no_drill_is_not_this_check_s_business():
    text = "## Acceptance criteria\n\n- [ ] **1. A thing.** No drill.\n"
    assert mod.grade(text, "## Review gate")[0] == 0


# ── The measured fault ──────────────────────────────────────────────────────

def test_leaning_on_the_record_in_silence_is_refused():
    # The shape of issue 114's criterion 7, 2026-09-17.
    body = (
        "1. **A worker is on a database of its own — PASS.** Green 3 of 3 here.\n"
        "7. **The shared bucket is answered — PASS.** Sixteen files rather than\n"
        "   the nine predicted, with the rule in `reset-road.ts` rather than a\n"
        "   list. The record drives unheld against held (17 of 17 twice).\n")
    assert code(body) == 1


def test_the_refusal_names_the_criterion_and_the_one_sentence_repair():
    body = ("1. **PASS.** green 3 of 3\n"
            "7. **PASS.** The record shows 17 of 17.\n")
    lines = "\n".join(mod.grade(issue(body), "## Review gate")[1])
    assert "criterion 7" in lines
    assert "leaned-undisclosed" in lines
    assert "one sentence" in lines


def test_leaning_AND_disclosing_passes_because_that_is_the_honest_case():
    # Issue 114's criterion 6 in round 1 did exactly this and was right to.
    body = (
        "1. **PASS.** green 3 of 3\n"
        "7. **PASS on a subset.** The record drives 49 files. This gate did\n"
        "   not re-drive it; a subset is weaker and the record says so.\n")
    assert code(body) == 0


# ── What must not cry wolf ──────────────────────────────────────────────────

def test_criticising_the_record_is_not_leaning_on_it():
    # The round-2 verify verdict: "the implementation record's criterion 9
    # drill names the wrong kind of file". An early draft refused this.
    body = (
        "1. **PASS.** Restored, green 3 of 3.\n"
        "7. **PASS.** Drove it ten times, 10 of 10 identical.\n"
        "   The implementation record's criterion 9 drill names the wrong file.\n")
    assert code(body) == 0


def test_the_record_explaining_scope_is_not_leaning_on_it():
    # "the implementation record explains why for seven of them" -- also
    # refused by an early draft, also not a source of evidence.
    body = ("1. **PASS.** green 3 of 3\n"
            "7. **PASS.** 10 of 10. The implementation record explains why.\n")
    assert code(body) == 0


def test_a_gate_that_drove_everything_passes():
    body = ("1. **PASS.** Drilled here: red 1 of 1, restored, green 3 of 3.\n"
            "7. **PASS.** Ten runs at two workers, 10 of 10 identical.\n")
    assert code(body) == 0


def test_a_pointer_to_the_gate_s_own_rejection_section_passes():
    # Issue 114's criterion 9 in round 1 read "See below." with a whole
    # section of drives under its own heading.
    body = ("1. **PASS.** green 3 of 3\n"
            "7. **FAIL.** See below.\n")
    assert code(body) == 0


# ── The silent half REPORTS and never refuses ───────────────────────────────

def test_a_criterion_it_cannot_read_is_reported_and_not_refused():
    body = ("1. **PASS.** It behaves correctly in this gate's copy.\n"
            "7. **PASS.** The rule is sound on inspection.\n")
    exit_code, lines = mod.grade(issue(body), "## Review gate")
    blob = "\n".join(lines)
    assert exit_code == 0
    assert "NOT GRADED" in blob
    assert "this reader's blindness" in blob


# ── Could not grade ─────────────────────────────────────────────────────────

def test_a_missing_section_is_exit_two_and_says_it_is_not_a_pass():
    exit_code, lines = mod.grade(CRITERIA, "## Review gate")
    assert exit_code == 2
    assert "not a pass" in "\n".join(lines)


def test_an_empty_section_is_exit_two():
    assert mod.grade(CRITERIA + "\n## Review gate\n\n", "## Review gate")[0] == 2


# ── The accumulate-never-overwrite rule ─────────────────────────────────────

def test_a_findings_table_numbered_from_one_does_not_erase_the_rubric():
    # The bug that made the first working draft report nine criteria silent:
    # the findings table restarts at 1 and overwrote the rubric's entries.
    body = (
        "1. **PASS.** green 3 of 3\n"
        "7. **PASS.** Drove it, 10 of 10.\n"
        "\n| # | finding |\n|---|---|\n"
        "| 1 | something unrelated |\n"
        "| 7 | something else unrelated |\n")
    assert code(body) == 0


def _load_tests(loader=None, tests=None, pattern=None):
    """Wrap this file's plain `test_` functions as a unittest suite.

    The repo's suite runner reads an executed-count from a unittest or pytest
    summary line, and refuses a file that prints neither -- an unread
    instrument and a clean instrument look alike. These checks are plain
    functions rather than `TestCase` methods, so this is what gives them a
    `Ran N tests` line to be counted by.
    """
    import unittest
    suite = unittest.TestSuite()
    for name in sorted(n for n, v in list(globals().items())
                       if n.startswith("test_") and callable(v)):
        suite.addTest(unittest.FunctionTestCase(globals()[name], description=name))
    return suite


load_tests = _load_tests


if __name__ == "__main__":
    import unittest
    unittest.main(argv=["-"], exit=True)
