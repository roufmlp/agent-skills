"""Drills for check_budget: a fake plugin tree against a fake budget."""

import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_budget  # noqa: E402

BUDGET = """# Budget
```
skills: 1
agents: 1
hooks: 1
workflows: 1
skill-file-lines: 3
```
```
exempt-from-dates: skills/old/SKILL.md agents/old-*.md
exempt-from-lines: skills/old/SKILL.md
```
"""


class TheBudgetCheck(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "budget.md").write_text(BUDGET)
        self.write("skills/a/SKILL.md", "one\ntwo\n")
        self.write("agents/a.md", "role\n")
        self.write("hooks/a.py", "pass\n")
        self.write("hooks/test_a.py", "pass\n")
        self.write("workflows/a.js", "1\n")

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def test_a_tree_within_budget_passes(self):
        self.assertEqual(check_budget.check(str(self.root)), [])

    def test_a_second_agent_fails_the_count(self):
        self.write("agents/b.md", "role\n")
        self.assertIn("agents: 2 in the tree, budget 1", check_budget.check(str(self.root))[0])

    def test_a_test_hook_is_not_counted(self):
        self.write("hooks/test_b.py", "pass\n")
        self.assertEqual(check_budget.check(str(self.root)), [])

    def test_a_long_skill_file_fails_the_line_limit(self):
        self.write("skills/a/SKILL.md", "1\n2\n3\n4\n")
        self.assertIn("skills/a/SKILL.md: 4 lines, limit 3", check_budget.check(str(self.root))[0])

    def test_a_date_in_an_agent_file_fails(self):
        self.write("agents/a.md", "role\nsince 2026-11-04\n")
        self.assertIn("agents/a.md:2: carries `2026-11-04`", check_budget.check(str(self.root))[0])

    def test_ruled_and_changed_by_fail_as_whole_words_only(self):
        self.write("skills/a/SKILL.md", "overruled in synthesis\n")
        self.assertEqual(check_budget.check(str(self.root)), [])
        self.write("skills/a/SKILL.md", "Ruled on Monday\nChanged by X\n")
        self.assertEqual(len(check_budget.check(str(self.root))), 2)

    def test_an_exempt_file_passes_both_rules(self):
        (self.root / "budget.md").write_text(BUDGET.replace("skills: 1", "skills: 2").replace("agents: 1", "agents: 2"))
        self.write("skills/old/SKILL.md", "1\n2\n3\n4\nruled 2026-01-01\n")
        self.write("agents/old-x.md", "changed by\n")
        self.assertEqual(check_budget.check(str(self.root)), [])


if __name__ == "__main__":
    unittest.main()
