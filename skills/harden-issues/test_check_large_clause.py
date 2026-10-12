#!/usr/bin/env python3
"""Tests for check_large_clause.py. Run: python3 test_check_large_clause.py

The human's ruling `q-fin-6f777a-04` of 2026-10-11. In run `batch-6f777a` a "no new
LARGE line" clause with no exemption struck issue 470 once and stood against 468
C9, 470 C8 and 474 C7: a line a written ruling or default already kept still read
as new. The fixtures below are cut down from issue 468's criterion 9.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_large_clause as check  # noqa: E402

SCRIPT = pathlib.Path(__file__).parent / "check_large_clause.py"

BARE = (
    "- [ ] 9. Every recaptured row's `differences.md` lists no LARGE line of this issue\n"
    "      other than those recorded under `q-h1010-468-1`, and the new images add no\n"
    "      new LARGE line.\n"
)

EXEMPT = (
    "- [ ] 9. Every recaptured row's `differences.md` lists no LARGE line of this issue\n"
    "      other than those recorded under `q-h1010-468-1`, ~~and the new images add no\n"
    "      new LARGE line~~ and the new images add no new LARGE line that no written\n"
    "      ruling or default keeps, each kept line's row citing its id.\n"
)

PLAIN = "- [ ] 1. **The move box opens on tap.** A test taps it.\n"


def issue(criteria: str) -> str:
    return f"Status: needs-harden\n\n# Issue\n\n## Acceptance criteria\n\n{criteria}\n"


class TheClauseNamesItsExemption(unittest.TestCase):
    def test_a_bare_clause_is_refused(self):
        """Issue 468's criterion 9 as it was stamped."""
        faults = check.faults(issue(PLAIN + BARE))
        self.assertEqual(len(faults), 1)
        self.assertIn("that no written ruling or default keeps", faults[0])

    def test_a_clause_with_the_exemption_passes(self):
        """The struck bare clause does not count; the live one carries the words."""
        self.assertEqual(check.faults(issue(PLAIN + EXEMPT)), [])

    def test_an_issue_with_no_clause_passes(self):
        self.assertEqual(check.faults(issue(PLAIN)), [])

    def test_each_clause_is_judged_alone(self):
        """One exempt clause does not carry a bare one elsewhere in the file."""
        self.assertEqual(len(check.faults(issue(EXEMPT + BARE))), 1)

    def test_the_words_belong_to_the_clause_sentence(self):
        """The exemption in a later sentence does not exempt this one."""
        text = issue(
            "- [ ] 4. The images add no new LARGE line. A gate reads every row\n"
            "      that no written ruling or default keeps.\n"
        )
        self.assertEqual(len(check.faults(text)), 1)

    def test_case_and_line_wrap_do_not_hide_a_clause(self):
        self.assertEqual(len(check.faults(issue("- [ ] 2. Adds No New\n      large line.\n"))), 1)


class TheScript(unittest.TestCase):
    def run_on(self, *texts):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for n, text in enumerate(texts):
                path = pathlib.Path(folder) / f"46{n}-issue.md"
                path.write_text(text)
                paths += ["--issue", str(path)]
            return subprocess.run([sys.executable, str(SCRIPT), *paths],
                                  capture_output=True, text=True)

    def test_a_refused_file_exits_1_and_names_the_issue(self):
        result = self.run_on(issue(BARE))
        self.assertEqual(result.returncode, 1)
        self.assertIn("REFUSED   460", result.stderr)

    def test_a_passing_file_exits_0(self):
        result = self.run_on(issue(EXEMPT))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok        460", result.stdout)

    def test_one_refused_file_refuses_the_run(self):
        self.assertEqual(self.run_on(issue(EXEMPT), issue(BARE)).returncode, 1)

    def test_an_unreadable_file_is_refused(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--issue", "/nonexistent/470-x.md"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unreadable", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
