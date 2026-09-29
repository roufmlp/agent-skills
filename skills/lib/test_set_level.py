#!/usr/bin/env python3
"""Tracker-tooling issue 34, the level follows the risk file.

`set_level.py` reads an issue's `Touches:` line against the repository's risk file,
`docs/agents/risk-paths.md`, and writes `Level: full` or `Level: light` into the
issue. Before it, the drafter set the level by hand (issue 33), and a hand is what
forgets that `src/controls/money/` is money.

Run: python3 test_set_level.py
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "set_level.py"
sys.path.insert(0, str(HERE))

RISK_FILE = """# Risk paths

| Pattern | Class |
|---|---|
| `supabase/migrations/**` | migrations |
| `src/controls/money/` | money |
"""


def issue(touches: str, level: str | None = "light", writes_rows: str = "no") -> str:
    lines = [
        "Status: needs-harden",
        "Sentence: A slice",
        f"Touches: {touches}" if touches is not None else None,
        "Kind: product",
        f"Level: {level}" if level is not None else None,
        "",
        "# 90 — A slice",
        "",
        "## Target database",
        "",
        f"`Writes rows: {writes_rows}`",
        "",
        "## Acceptance criteria",
        "",
        "- [ ] AC1. Something.",
        "",
    ]
    return "\n".join(line for line in lines if line is not None)


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class Repo(unittest.TestCase):
    """A temporary repository holding a risk file and one issue directory."""

    risk = RISK_FILE

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "product"
        self.root.mkdir()
        git("init", "-q", "-b", "main", cwd=self.root)
        if self.risk is not None:
            (self.root / "docs" / "agents").mkdir(parents=True)
            (self.root / "docs" / "agents" / "risk-paths.md").write_text(self.risk)
        self.issues = self.root / ".scratch" / "t" / "issues"
        self.issues.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text: str, name: str = "90-a-slice.md") -> Path:
        path = self.issues / name
        path.write_bytes(text.encode())
        return path

    def run_script(self, *paths: Path):
        done = subprocess.run([sys.executable, str(SCRIPT), *map(str, paths)],
                              capture_output=True, text=True, cwd=self.root,
                              env=dict(os.environ, HOME=str(self.root.parent)))
        return done.returncode, done.stdout, done.stderr

    def level_lines(self, path: Path) -> list[str]:
        return [line for line in path.read_text().splitlines() if line.startswith("Level:")]


class APathUnderARiskPatternIsFull(Repo):

    def test_a_migration_makes_the_issue_full(self):
        before = issue("`supabase/migrations/0090_x.sql`")
        path = self.write(before)
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: full"])
        self.assertIn("supabase/migrations/**", out)
        self.assertIn("migrations", out)
        changed = [(a, b) for a, b in zip(before.splitlines(), path.read_text().splitlines()) if a != b]
        self.assertEqual(changed, [("Level: light", "Level: full")])
        self.assertEqual(len(before.splitlines()), len(path.read_text().splitlines()))

    def test_a_path_under_a_directory_pattern_is_full(self):
        path = self.write(issue("`src/controls/money/pay.ts`"))
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: full"])
        self.assertIn("money", out)


class APathUnderNoPatternIsLight(Repo):

    def test_a_button_is_light(self):
        path = self.write(issue("`src/components/Button.tsx`"))
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: light"])


class ARefusalLeavesTheFileAlone(Repo):

    def assert_refused(self, text: str, *expected: str) -> str:
        path = self.write(text)
        code, out, err = self.run_script(path)
        self.assertEqual(code, 1, out + err)
        for words in expected:
            self.assertIn(words, err)
        self.assertEqual(path.read_bytes(), text.encode())
        return err

    def test_an_issue_with_no_touches_line_is_refused(self):
        self.assert_refused(issue(None), "`Touches:`")

    def test_every_form_that_names_no_path_is_refused(self):
        """AC8. Forms: the `Touches:` lines of the four repositories that hold a
        chain tracker, measured 2026-09-25 by the command the criterion states."""
        forms = {
            "none": "none",
            "none yet. It would change `~/.claude/skills/run-issues/`": "none",
            "none. The sort changed no rule any other issue rests on.": "none",
            "unswept": "no-token",
            "395, 395b, 349": "no-token",
        }
        for line, form in forms.items():
            with self.subTest(line=line):
                self.assert_refused(issue(line), form)

    def test_a_wrapped_touches_line_is_refused(self):
        text = issue("`~/.claude/hooks/`, `~/.claude/skills/run-issues/`,").replace(
            "Kind: product", "  `~/.claude/skills/lib/`\nKind: product")
        self.assert_refused(text, "wrapped")

    def test_prose_between_backticked_items_is_read(self):
        path = self.write(issue("a new script and its test under `supabase/migrations/0091_y.sql`"))
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: full"])

    def test_a_level_outside_its_two_words_is_refused(self):
        self.assert_refused(issue("`src/a.ts`", level="medium"), "medium")

    def test_a_target_database_with_no_answer_is_refused(self):
        self.assert_refused(issue("`src/a.ts`", writes_rows="the code decides"), "Writes rows")


class ARepoWithNoRiskFileIsRefused(Repo):

    risk = None

    def test_the_refusal_names_the_path_it_looked_for(self):
        text = issue("`src/components/Button.tsx`")
        path = self.write(text)
        code, out, err = self.run_script(path)
        self.assertEqual(code, 1, out + err)
        self.assertIn(str(self.root / "docs" / "agents" / "risk-paths.md"), err)
        self.assertEqual(path.read_bytes(), text.encode())


class TheLevelLineIsWrittenOnce(Repo):

    def test_twice_leaves_one_level_line(self):
        path = self.write(issue("`src/components/Button.tsx`", level=None))
        for _ in range(2):
            code, out, err = self.run_script(path)
            self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: light"])
        lines = path.read_text().splitlines()
        self.assertLess(lines.index("Level: light"), lines.index("# 90 — A slice"))
        self.assertEqual(lines[lines.index("Level: light") - 1], "Kind: product")

    def test_a_level_line_in_the_body_is_left_alone(self):
        text = issue("`src/components/Button.tsx`", level=None).replace(
            "- [ ] AC1. Something.", "- [ ] AC1. Something.\nLevel: full")
        path = self.write(text)
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: light", "Level: full"])


class TheScriptNeverLowersALevel(Repo):

    def test_a_full_level_stays_full_over_light_paths(self):
        path = self.write(issue("`src/components/Button.tsx`", level="full"))
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: full"])
        self.assertIn("stricter than the paths give", out)


class ARowWritingIssueIsFull(Repo):

    def test_writes_rows_yes_is_full_with_no_path_meeting(self):
        path = self.write(issue("`src/components/Button.tsx`", writes_rows="yes"))
        code, out, err = self.run_script(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.level_lines(path), ["Level: full"])
        self.assertIn("writes rows", out)


class TheRiskFileForms(Repo):
    """AC10: three risk-file forms, three exit codes, and the row named."""

    def run_with(self, risk: str):
        (self.root / "docs" / "agents" / "risk-paths.md").write_text(risk)
        text = issue("`src/components/Button.tsx`")
        path = self.write(text)
        code, out, err = self.run_script(path)
        return code, out, err, path.read_bytes() == text.encode()

    def test_a_file_with_no_row_and_no_reason_is_refused(self):
        code, out, err, untouched = self.run_with("# Risk paths\n\n| Pattern | Class |\n|---|---|\n")
        self.assertEqual(code, 1)
        self.assertIn("No risk paths", err)
        self.assertTrue(untouched)

    def test_a_row_naming_another_class_is_refused_and_named(self):
        code, out, err, untouched = self.run_with(
            "| Pattern | Class |\n|---|---|\n| `src/billing/**` | billing |\n")
        self.assertEqual(code, 1)
        self.assertIn("`src/billing/**` | billing", err)
        self.assertTrue(untouched)

    def test_no_risk_paths_with_a_reason_makes_every_issue_light(self):
        code, out, err, untouched = self.run_with(
            "# Risk paths\n\nNo risk paths: its issues touch skills and hooks only.\n")
        self.assertEqual(code, 0, err)
        self.assertIn("Level: light", out)

    def test_a_row_under_any_other_header_is_refused_and_named(self):
        """Rows the reader cannot place are refused, never skipped: a skipped
        money row beside a `No risk paths:` line would read as all light."""
        code, out, err, untouched = self.run_with(
            "No risk paths: none here.\n\n| Pattern | Class | Note |\n|---|---|---|\n"
            "| `src/controls/money/` | money | pay |\n")
        self.assertEqual(code, 1)
        self.assertIn("| Pattern | Class | Note |", err)
        self.assertTrue(untouched)

    def test_a_bold_header_is_read(self):
        code, out, err, untouched = self.run_with(
            "| **Pattern** | **Class** |\n|---|---|\n| `src/components/` | money |\n")
        self.assertEqual(code, 0, err)
        self.assertIn("Level: full", out)

    def test_no_risk_paths_with_no_reason_is_refused(self):
        code, out, err, untouched = self.run_with("No risk paths:\n")
        self.assertEqual(code, 1)


class TheMeetRule(unittest.TestCase):
    """AC9 and the seam pass h0925's meet bullet, on the importable function."""

    main = "/home/u/code/product"

    def level(self, item: str, pattern: str) -> str:
        from set_level import meet, normalise
        return "full" if meet(normalise(item, self.main), normalise(pattern, self.main)) else "light"

    def test_the_five_fixtures_and_the_seam_fixture(self):
        cases = [
            ("supabase/", "supabase/migrations/**", "full"),
            ("supabase/**", "supabase/migrations/**", "full"),
            ("./supabase/migrations/0090_x.sql", "supabase/migrations/**", "full"),
            ("src/lib/orders.ts", "src/lib/payments/**", "light"),
            ("~/.claude/hooks/x.py", "~/.claude/hooks/**", "full"),
            ("src/controls/money/pay.ts", "src/controls/money/", "full"),
        ]
        for item, pattern, expected in cases:
            with self.subTest(item=item, pattern=pattern):
                self.assertEqual(self.level(item, pattern), expected)

    def test_one_star_stays_inside_a_segment(self):
        self.assertEqual(self.level("src/lib/a/b.ts", "src/lib/*"), "light")
        self.assertEqual(self.level("src/lib/a.ts", "src/lib/*"), "full")

    def test_brackets_are_literal(self):
        self.assertEqual(self.level("src/app/[number]/page.tsx", "src/app/[number]/page.tsx"), "full")
        self.assertEqual(self.level("src/app/n/page.tsx", "src/app/[number]/*"), "light")

    def test_the_meet_names_how(self):
        from set_level import meet
        self.assertEqual(meet("/a/b", "/a/b"), "equal")
        self.assertEqual(meet("/a/b", "/a/*"), "glob")
        self.assertEqual(meet("/a/", "/a/b"), "directory")
        self.assertIsNone(meet("/a/b", "/a/c"))

    def test_a_worktree_path_is_rebased_onto_the_main_checkout(self):
        from set_level import normalise
        tree = self.main + "/.claude/worktrees/wt"
        self.assertEqual(normalise(tree + "/lib/x.py", self.main, tree), self.main + "/lib/x.py")


class TheRiskFileReaderIsImportable(unittest.TestCase):
    """Issue 42's hook imports the reader rather than parsing the file again."""

    def test_the_reader_returns_the_rows(self):
        from set_level import read_risk_file
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk-paths.md"
            path.write_text(RISK_FILE)
            rows = read_risk_file(path).rows
        self.assertEqual([(r.pattern, r.risk_class) for r in rows],
                         [("supabase/migrations/**", "migrations"), ("src/controls/money/", "money")])


from set_level import RISK_FILE as SKILLS_RELATIVE  # noqa: E402

SKILLS_RISK_FILE = HERE.parent / SKILLS_RELATIVE


@unittest.skipUnless(SKILLS_RISK_FILE.is_file(),
                     "this skills tree carries no risk file of its own")
class TheSkillsRepoCarriesItsRiskFile(unittest.TestCase):
    """Default `q-h0925-34-6`: this issue writes the skills repo's own file.

    It reads the tree this file sits in, so it skips where that tree has no
    `docs/agents/risk-paths.md`. A skills tree that wants `set_level.py` to
    level its own issues writes one, and this case then grades it.
    """

    def test_the_skills_risk_file_reads(self):
        from set_level import RISK_FILE as RELATIVE, read_risk_file
        found = read_risk_file(HERE.parent / RELATIVE)
        self.assertEqual(found.rows, ())
        self.assertTrue(found.no_risk_reason)


if __name__ == "__main__":
    unittest.main()
