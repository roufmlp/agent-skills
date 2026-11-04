"""on_main.py: the failing items of a command here against the base, by name."""

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "on_main.py")
sys.path.insert(0, HERE)

import on_main as mod  # noqa: E402

# A command that fails on the items its folder's `.fails` file lists, one per
# line, in Playwright's shape; `vitest:` lines come out in vitest's shape. A
# `.once` file makes the first run fail on everything and the second on
# nothing, the shape of a flake.
FAKE = textwrap.dedent("""\
    import pathlib, sys
    fails = pathlib.Path(".fails")
    items = fails.read_text().splitlines() if fails.exists() else []
    once = pathlib.Path(".once")
    if once.exists():
        once.unlink()
    elif fails.exists() and pathlib.Path(".flaky").exists():
        items = []
    for item in items:
        if item.startswith("vitest:"):
            print(f" FAIL  {item[7:]} > a suite > a case")
        elif item == "plain":
            print("something went wrong")
        else:
            print(f"  ✘   3 [phone] › {item} (12ms)")
    print(f"  {len(items)} failed" if items else "  4 passed (1.0s)")
    sys.exit(1 if items else 0)
    """)


class Trees(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.fake = root / "fake.py"
        self.fake.write_text(FAKE)
        self.tree, self.base = root / "tree", root / "base"
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for path in (self.tree, self.base):
            path.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
            subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "base"], cwd=path, env=env, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def fails(self, tree, *items, flaky=False):
        (tree / ".fails").write_text("".join(f"{i}\n" for i in items))
        if flaky:
            (tree / ".once").write_text("")
            (tree / ".flaky").write_text("")

    def run_script(self, *extra):
        done = subprocess.run([sys.executable, SCRIPT, "--tree", str(self.tree), "--base", str(self.base),
                               "--label", "screens", *extra, "--", sys.executable, str(self.fake)],
                              capture_output=True, text=True)
        return done.returncode, done.stdout.strip().splitlines()

    def test_a_passing_command_is_passes_and_the_base_is_not_run(self):
        code, lines = self.run_script()
        self.assertEqual((code, lines), (0, ["passes: screens"]))
        self.assertFalse(list((self.base / ".git").glob("suite/logs/*")))

    def test_an_item_failing_here_and_at_the_base_is_on_main(self):
        self.fails(self.tree, "e2e/screens.spec.ts:95:11 › screens › home-390")
        self.fails(self.base, "e2e/screens.spec.ts:95:11 › screens › home-390")
        code, lines = self.run_script()
        self.assertEqual(code, 0, lines)
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r"^on main: e2e/screens\.spec\.ts:95:11 › screens › home-390 fails here and at [0-9a-f]{9}$")

    def test_an_item_failing_here_only_is_the_features_and_exits_1(self):
        self.fails(self.tree, "e2e/screens.spec.ts:95:11 › screens › home-390", "e2e/screens.spec.ts:95:11 › screens › bills-390")
        self.fails(self.base, "e2e/screens.spec.ts:95:11 › screens › home-390")
        code, lines = self.run_script()
        self.assertEqual(code, 1, lines)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("on main: e2e/screens.spec.ts:95:11 › screens › home-390 fails here and at "))
        self.assertTrue(lines[1].startswith("feature: e2e/screens.spec.ts:95:11 › screens › bills-390 fails here and passes at "))

    def test_vitest_files_are_items_too(self):
        self.fails(self.tree, "vitest:tests/money.test.ts")
        code, lines = self.run_script()
        self.assertEqual(code, 1, lines)
        self.assertTrue(lines[0].startswith("feature: tests/money.test.ts fails here and passes at "))

    def test_a_failure_the_output_does_not_name_is_the_command_itself(self):
        self.fails(self.tree, "plain")
        self.fails(self.base, "plain")
        code, lines = self.run_script()
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].startswith(f"on main: {sys.executable} {self.fake} fails here and at "))

    def test_twice_calls_a_one_time_failure_a_flake(self):
        self.fails(self.tree, "e2e/screens.spec.ts:95:11 › screens › home-390", flaky=True)
        code, lines = self.run_script("--twice")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["flake: e2e/screens.spec.ts:95:11 › screens › home-390",
                                 "passes: screens (on the second run)"])

    def test_twice_keeps_a_failure_that_holds(self):
        self.fails(self.tree, "e2e/screens.spec.ts:95:11 › screens › home-390")
        code, lines = self.run_script("--twice")
        self.assertEqual(code, 1, lines)
        self.assertTrue(lines[0].startswith("feature: "))

    def test_a_missing_base_is_refused(self):
        done = subprocess.run([sys.executable, SCRIPT, "--tree", str(self.tree), "--base", str(self.base / "nowhere"),
                               "--", "true"], capture_output=True, text=True)
        self.assertEqual(done.returncode, mod.REFUSED)
        self.assertIn("REFUSED: --base", done.stdout)

    def test_logs_land_under_the_trees_git_dir(self):
        self.fails(self.tree, "plain")
        self.run_script()
        names = sorted(p.name for p in (self.tree / ".git" / "suite" / "logs").iterdir())
        self.assertEqual(len(names), 2, names)
        self.assertTrue(names[0].endswith("-on-main-screens-base.log"))
        self.assertTrue(names[1].endswith("-on-main-screens-tree.log"))


class Parsing(unittest.TestCase):
    def test_playwright_and_vitest_lines(self):
        text = ("  ✘   22 [phone] › e2e/a.spec.ts:146:5 › at 390 px › reads the answer (505ms)\n"
                "  ✓   23 [phone] › e2e/a.spec.ts:150:5 › passes (5ms)\n"
                " FAIL  tests/money.test.ts > money > counts\n"
                "  ✘   22 [phone] › e2e/a.spec.ts:146:5 › at 390 px › reads the answer (505ms)\n")
        self.assertEqual(mod.failing_items(text),
                         ["tests/money.test.ts", "e2e/a.spec.ts:146:5 › at 390 px › reads the answer"])


if __name__ == "__main__":
    unittest.main()
