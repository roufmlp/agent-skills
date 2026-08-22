#!/usr/bin/env python3
"""Tests for check_manifest_coverage.py.

The fault this guards is a measured one, so the fixtures have its shape: a live
skill directory holding one file more than the MANIFEST lists. Everything else
here exists to stop the check crying wolf, because a check that alarms on a
healthy tree gets switched off and then the fault comes back.
"""

import pathlib
import tempfile
import unittest

import check_manifest_coverage as guard

MANIFEST = """# Manifest

| Published | Live source |
|-----------|-------------|
| `skills/run-issues/SKILL.md` | `~/.claude/skills/run-issues/SKILL.md` |
| `skills/run-issues/check_attempt_cap.py` | `~/.claude/skills/run-issues/check_attempt_cap.py` |
| `skills/run-issues/test_*.py` | `~/.claude/skills/run-issues/test_*.py` (tests) |
| `docs/case-study.md` | written for this repo; no live source |

Session records never ship:

```withheld
~/.claude/skills/run-issues/panel-review-*.md
```
"""


def build(root, live_files, repo_files, manifest=MANIFEST):
    """A live tree, a repo tree and a MANIFEST describing them."""
    live, repo = root / "home", root / "repo"
    for relative in live_files:
        path = live / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    for relative in repo_files:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    (repo / "MANIFEST.md").write_text(manifest)
    return live, repo


HEALTHY_LIVE = [
    ".claude/skills/run-issues/SKILL.md",
    ".claude/skills/run-issues/check_attempt_cap.py",
    ".claude/skills/run-issues/test_check_attempt_cap.py",
    ".claude/skills/run-issues/test_skill_structure.py",
]
HEALTHY_REPO = [
    "skills/run-issues/SKILL.md",
    "skills/run-issues/check_attempt_cap.py",
    "skills/run-issues/test_check_attempt_cap.py",
    "skills/run-issues/test_skill_structure.py",
    "docs/case-study.md",
]


class Parsing(unittest.TestCase):
    def test_reads_the_two_columns_and_skips_the_header_and_rule(self):
        parsed = guard.parse_manifest(MANIFEST)
        self.assertIn("skills/run-issues/SKILL.md", parsed.published)
        self.assertIn("~/.claude/skills/run-issues/SKILL.md", parsed.sources)
        self.assertNotIn("Published", parsed.published)

    def test_a_row_with_no_live_source_contributes_no_source(self):
        """`written for this repo` rows are published, not mirrored."""
        parsed = guard.parse_manifest(MANIFEST)
        self.assertIn("docs/case-study.md", parsed.published)
        self.assertEqual(len([s for s in parsed.sources if "case-study" in s]), 0)

    def test_reads_the_withheld_block(self):
        parsed = guard.parse_manifest(MANIFEST)
        self.assertEqual(
            parsed.withheld, ["~/.claude/skills/run-issues/panel-review-*.md"])


class HealthyTree(unittest.TestCase):
    def test_a_tree_the_manifest_describes_raises_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(pathlib.Path(tmp), HEALTHY_LIVE, HEALTHY_REPO)
            self.assertEqual(guard.audit(repo / "MANIFEST.md", live, repo), [])

    def test_a_glob_row_covers_the_files_it_expands_to(self):
        """`test_*.py` is one row and two files; neither is unlisted."""
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(pathlib.Path(tmp), HEALTHY_LIVE, HEALTHY_REPO)
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertNotIn("unlisted", [kind for kind, _ in problems])

    def test_a_withheld_file_is_not_unlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [
                    ".claude/skills/run-issues/panel-review-2026-07-27.md"],
                HEALTHY_REPO,
            )
            self.assertEqual(guard.audit(repo / "MANIFEST.md", live, repo), [])

    def test_pycache_and_dot_directories_are_not_walked(self):
        """Compiler droppings and `.git` are not decisions anyone records."""
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [
                    ".claude/skills/run-issues/__pycache__/check.cpython-314.pyc",
                    ".claude/skills/run-issues/.git/config",
                ],
                HEALTHY_REPO,
            )
            self.assertEqual(guard.audit(repo / "MANIFEST.md", live, repo), [])


class Unlisted(unittest.TestCase):
    """The recorded fault: two scripts written live sat unpublished for days,
    because the sync reminder fires only on files a MANIFEST row already names."""

    def test_a_new_live_script_no_row_names_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [".claude/skills/run-issues/orchestrator_cost.py"],
                HEALTHY_REPO,
            )
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertEqual(len(problems), 1)
            kind, subject = problems[0]
            self.assertEqual(kind, "unlisted")
            self.assertTrue(subject.endswith("orchestrator_cost.py"))

    def test_a_file_in_a_new_subdirectory_is_refused(self):
        """A row's `*` must not reach across a directory separator, or a whole
        new folder of live files publishes itself as covered."""
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [
                    ".claude/skills/run-issues/references/test_deep.py"],
                HEALTHY_REPO,
            )
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertEqual([kind for kind, _ in problems], ["unlisted"])

    def test_it_names_every_unlisted_file_not_only_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [
                    ".claude/skills/run-issues/one.py",
                    ".claude/skills/run-issues/two.md",
                ],
                HEALTHY_REPO,
            )
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertEqual(len(problems), 2)


class DeadRows(unittest.TestCase):
    def test_a_row_whose_live_source_is_gone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                [f for f in HEALTHY_LIVE if not f.endswith("check_attempt_cap.py")],
                HEALTHY_REPO,
            )
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertIn(
                ("dead-source", "~/.claude/skills/run-issues/check_attempt_cap.py"),
                problems,
            )

    def test_a_row_whose_published_file_is_gone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE,
                [f for f in HEALTHY_REPO if f != "docs/case-study.md"],
            )
            problems = guard.audit(repo / "MANIFEST.md", live, repo)
            self.assertIn(("dead-publication", "docs/case-study.md"), problems)


class ExitCodes(unittest.TestCase):
    def test_a_healthy_tree_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(pathlib.Path(tmp), HEALTHY_LIVE, HEALTHY_REPO)
            self.assertEqual(guard.main(self._argv(live, repo)), 0)

    def test_an_unlisted_file_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, repo = build(
                pathlib.Path(tmp),
                HEALTHY_LIVE + [".claude/skills/run-issues/new.py"],
                HEALTHY_REPO,
            )
            self.assertEqual(guard.main(self._argv(live, repo)), 1)

    @staticmethod
    def _argv(live, repo):
        return ["--manifest", str(repo / "MANIFEST.md"),
                "--live-root", str(live), "--repo-root", str(repo)]


class TheRealTrees(unittest.TestCase):
    """The check has to pass on the repo that ships it, or it is decoration."""

    def test_this_repos_manifest_describes_the_live_tree(self):
        repo = pathlib.Path(__file__).resolve().parent
        if not (pathlib.Path.home() / ".claude" / "skills").is_dir():
            self.skipTest("no live ~/.claude/skills on this machine")
        problems = guard.audit(repo / "MANIFEST.md", pathlib.Path.home(), repo)
        self.assertEqual(problems, [], guard.render(problems))


if __name__ == "__main__":
    unittest.main()
