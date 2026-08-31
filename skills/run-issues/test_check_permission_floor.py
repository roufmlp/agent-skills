#!/usr/bin/env python3
"""Cases for check_permission_floor.py, driven on throwaway settings files.

The anchor case is run `414a-483-286335`'s real launch state: nineteen tracked
rules, and `Bash(npx vitest *)` present only in the untracked local file. That
run then lost 2 h 34 m to a classifier refusal on `npx vitest run`.

    python3 -m unittest test_check_permission_floor
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import check_permission_floor as guard


def settings(root: pathlib.Path, name: str, rules: list[str]) -> None:
    target = root / ".claude" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"permissions": {"allow": rules}}))


def tree(tracked: list[str] | None = None, local: list[str] | None = None) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="permfloor-"))
    if tracked is not None:
        settings(root, "settings.json", tracked)
    if local is not None:
        settings(root, "settings.local.json", local)
    return root


EVERYTHING = [
    "Bash(npx vitest*)",
    "Bash(npx tsc*)",
    "Bash(npx eslint*)",
    "Bash(npm test*)",
    "Bash(npm run test*)",
    "Bash(npm run lint*)",
    "Bash(npm run typecheck*)",
    "Bash(npm run build*)",
]


class Covers(unittest.TestCase):
    def test_a_star_rule_matches_by_prefix(self):
        self.assertTrue(guard.covers("Bash(npx vitest*)", "npx vitest run a.test.ts"))

    def test_a_rule_with_no_star_matches_exactly(self):
        self.assertTrue(guard.covers("Bash(npm test)", "npm test"))
        self.assertFalse(guard.covers("Bash(npm test)", "npm test -- --watch"))

    def test_the_trailing_space_is_the_trap(self):
        """`Bash(npx vitest *)` does NOT cover a bare `npx vitest`.

        That spaced form is what the local file carried, and it is why the
        tracked rule this session added has no space.
        """
        self.assertFalse(guard.covers("Bash(npx vitest *)", "npx vitest"))
        self.assertTrue(guard.covers("Bash(npx vitest*)", "npx vitest"))

    def test_a_broad_rule_covers_a_narrow_command(self):
        self.assertTrue(guard.covers("Bash(npm run *)", "npm run lint"))

    def test_an_unrelated_rule_covers_nothing(self):
        self.assertFalse(guard.covers("Bash(vercel deploy*)", "npx vitest run"))


class Judge(unittest.TestCase):
    def test_a_tracked_rule_passes(self):
        verdict, rule = guard.judge("npx vitest run", ["Bash(npx vitest*)"], [])
        self.assertEqual(verdict, "ok")
        self.assertEqual(rule, "Bash(npx vitest*)")

    def test_a_local_only_rule_is_untracked_not_ok(self):
        """The whole fault. The command WORKS today and stops working in the
        next worktree, which is worse than never having worked."""
        verdict, rule = guard.judge("npx vitest run", [], ["Bash(npx vitest *)"])
        self.assertEqual(verdict, "untracked")
        self.assertEqual(rule, "Bash(npx vitest *)")

    def test_no_rule_anywhere_is_uncovered(self):
        self.assertEqual(guard.judge("npx vitest run", [], [])[0], "uncovered")

    def test_tracked_wins_when_both_files_carry_it(self):
        verdict, _ = guard.judge("npm run lint", ["Bash(npm run lint*)"], ["Bash(npm run *)"])
        self.assertEqual(verdict, "ok")


class TheRunsOwnLaunchState(unittest.TestCase):
    """Run `414a-483-286335`, 2026-08-30, 04:00."""

    def test_the_launch_state_is_refused(self):
        root = tree(tracked=["Bash(vercel deploy*)"], local=["Bash(npx vitest *)"])
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_the_state_after_this_sessions_fix_passes(self):
        root = tree(tracked=EVERYTHING, local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 0)

    def test_a_worktree_that_never_saw_the_local_rule_is_also_refused(self):
        """The run worktree's own copy did not carry `Bash(npx vitest *)` at
        all, so its verdict is `uncovered` rather than `untracked`. Both
        refuse, which is the point."""
        root = tree(tracked=["Bash(vercel deploy*)"], local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 1)


class Main(unittest.TestCase):
    def test_an_extra_class_is_graded_too(self):
        root = tree(tracked=EVERYTHING, local=[])
        self.assertEqual(guard.main(["--repo", str(root), "--class", "npx playwright test"]), 1)

    def test_an_extra_class_that_is_tracked_passes(self):
        root = tree(tracked=EVERYTHING + ["Bash(npx playwright*)"], local=[])
        self.assertEqual(guard.main(["--repo", str(root), "--class", "npx playwright test"]), 0)

    def test_a_missing_tracked_file_is_a_refusal_not_a_crash(self):
        root = tree(tracked=None, local=EVERYTHING)
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_an_unparseable_settings_file_exits_two(self):
        root = tree(tracked=EVERYTHING, local=[])
        (root / ".claude" / "settings.json").write_text("{not json")
        self.assertEqual(guard.main(["--repo", str(root)]), 2)

    def test_a_repo_with_no_claude_directory_is_refused(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="permfloor-bare-"))
        self.assertEqual(guard.main(["--repo", str(root)]), 1)


class Suggest(unittest.TestCase):
    def test_an_npm_run_class_keeps_its_script_name(self):
        self.assertEqual(guard.suggest("npm run lint"), '"Bash(npm run lint*)"')

    def test_an_npx_class_keeps_two_words(self):
        self.assertEqual(guard.suggest("npx vitest run a.test.ts"), '"Bash(npx vitest*)"')

    def test_the_suggestion_actually_covers_the_class(self):
        """A remedy that does not fix the refusal is worse than no remedy."""
        for command in guard.REQUIRED:
            rule = guard.suggest(command).strip('"')
            with self.subTest(command=command):
                self.assertTrue(guard.covers(rule, command), f"{rule} misses {command}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
