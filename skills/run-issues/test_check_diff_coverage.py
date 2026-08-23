#!/usr/bin/env python3
"""Prove the changed-code coverage guard can fail.

Every refusal below is driven on a temporary tree built for it, so the failure
is observed rather than assumed: a guard nobody has watched go red is a claim,
not a check.

**What is deliberately NOT tested here: whether any real repository passes.**
That is the script's job at the moment it runs, and the answer changes on every
commit. A test asserting the live tree is covered would go red on somebody
else's work and be switched off within a week.

**One trap this file is written around.** The `untested` refusal and the
`uncovered` refusal both fire on the same input shape, so a test that gives a
diff with no test file can never reach the coverage code at all. Every coverage
test below therefore changes a test file as well, which is also the honest
shape: a real diff that owes coverage has a test in it.

    python3 test_check_diff_coverage.py
"""

from __future__ import annotations

import io
import json
import contextlib
import os
import pathlib
import tempfile
import time
import unittest

import check_diff_coverage as guard


def tree(files: dict[str, str]) -> pathlib.Path:
    """Write a throwaway repository and return its root."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="diffcov-"))
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def diff(*entries: tuple[str, int, int]) -> str:
    """Build a unified diff that ADDS `count` lines at `start` in each path."""
    out: list[str] = []
    for path, start, count in entries:
        out.append(f"--- a/{path}")
        out.append(f"+++ b/{path}")
        out.append(f"@@ -{start},0 +{start},{count} @@")
        for offset in range(count):
            out.append(f"+  line {start + offset}")
    return "\n".join(out) + "\n"


def istanbul(path: str, hits: dict[int, int]) -> str:
    """A minimal coverage-final.json holding one file's statement hits."""
    statements = {}
    counts = {}
    for index, (line, count) in enumerate(sorted(hits.items())):
        statements[str(index)] = {
            "start": {"line": line, "column": 0},
            "end": {"line": line, "column": 10},
        }
        counts[str(index)] = count
    return json.dumps({path: {"path": path, "statementMap": statements, "s": counts}})


def lcov(path: str, hits: dict[int, int]) -> str:
    lines = [f"SF:{path}"]
    lines += [f"DA:{line},{count}" for line, count in sorted(hits.items())]
    lines.append("end_of_record")
    return "\n".join(lines) + "\n"


def age(path: pathlib.Path, seconds: int) -> None:
    """Backdate a file, so staleness can be driven without sleeping."""
    stamp = time.time() - seconds
    os.utime(path, (stamp, stamp))


def run(root, diff_text, report="coverage/coverage-final.json", threshold=100.0):
    return guard.audit(root, diff_text, root / report, threshold)


class Classification(unittest.TestCase):
    def test_source_is_code_that_is_not_a_test(self):
        self.assertTrue(guard.is_source("src/lib/quote.ts"))
        self.assertTrue(guard.is_source("scripts/apply-migration.mjs"))
        self.assertTrue(guard.is_source("check_diff_coverage.py"))

    def test_tests_are_not_source(self):
        for path in (
            "tests/schema/grain-pin.live.test.ts",
            "src/lib/quote.spec.ts",
            "src/__tests__/quote.ts",
            "test_check_diff_coverage.py",
            "quote_test.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(guard.is_test(path), path)
                self.assertFalse(guard.is_source(path), path)

    def test_generated_and_declaration_files_are_excluded(self):
        for path in (
            "node_modules/react/index.js",
            ".next/server/page.js",
            "coverage/lcov-report/index.js",
            "src/types/supabase.d.ts",
        ):
            with self.subTest(path=path):
                self.assertTrue(guard.is_excluded(path), path)
                self.assertFalse(guard.is_source(path), path)

    def test_prose_is_neither_source_nor_test(self):
        self.assertFalse(guard.is_source("CONTEXT.md"))
        self.assertFalse(guard.is_test("CONTEXT.md"))


class DiffParsing(unittest.TestCase):
    def test_added_lines_are_numbered_in_the_new_file(self):
        changed = guard.parse_diff(diff(("src/a.ts", 10, 3)))
        self.assertEqual(changed.source["src/a.ts"], {10, 11, 12})

    def test_a_deleted_line_moves_nothing(self):
        text = (
            "--- a/src/a.ts\n+++ b/src/a.ts\n@@ -4,2 +4,1 @@\n"
            "-  gone\n+  kept\n"
        )
        changed = guard.parse_diff(text)
        self.assertEqual(changed.source["src/a.ts"], {4})

    def test_a_context_line_advances_the_counter(self):
        text = (
            "--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1,3 +1,4 @@\n"
            "   kept\n   kept\n+  added\n"
        )
        changed = guard.parse_diff(text)
        self.assertEqual(changed.source["src/a.ts"], {3})

    def test_a_deleted_file_is_not_collected(self):
        text = "--- a/src/gone.ts\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-  a\n-  b\n"
        changed = guard.parse_diff(text)
        self.assertTrue(changed.empty())

    def test_the_three_buckets_are_kept_apart(self):
        changed = guard.parse_diff(
            diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1), ("CONTEXT.md", 1, 1))
        )
        self.assertEqual(sorted(changed.source), ["src/a.ts"])
        self.assertEqual(changed.tests, ["src/a.test.ts"])
        self.assertEqual(changed.other, ["CONTEXT.md"])


class Untested(unittest.TestCase):
    def test_source_with_no_test_file_refuses(self):
        root = tree({"src/a.ts": "x\n"})
        problems, _ = run(root, diff(("src/a.ts", 1, 2)))
        self.assertEqual([p.kind for p in problems], ["untested"])

    def test_the_refusal_names_the_file(self):
        root = tree({"src/a.ts": "x\n"})
        problems, facts = run(root, diff(("src/a.ts", 1, 2)))
        self.assertIn("src/a.ts", guard.render(problems, facts))

    def test_a_test_file_in_the_same_diff_clears_it(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": istanbul("src/a.ts", {1: 1, 2: 1}),
            }
        )
        problems, _ = run(root, diff(("src/a.ts", 1, 2), ("src/a.test.ts", 1, 1)))
        self.assertEqual(problems, [])


class CannotGrade(unittest.TestCase):
    def test_an_empty_diff_refuses(self):
        root = tree({})
        problems, _ = run(root, "")
        self.assertEqual([p.kind for p in problems], ["empty-diff"])

    def test_a_missing_report_refuses(self):
        root = tree({"src/a.ts": "x\n"})
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual([p.kind for p in problems], ["no-report"])

    def test_the_missing_report_remedy_names_the_command(self):
        root = tree({"src/a.ts": "x\n"})
        problems, facts = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        rendered = guard.render(problems, facts)
        self.assertIn("@vitest/coverage-v8", rendered)

    def test_an_unparseable_report_refuses(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": "this is not a report\n",
            }
        )
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual([p.kind for p in problems], ["unreadable-report"])

    def test_json_without_a_statement_map_refuses(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": json.dumps({"src/a.ts": {"lines": 3}}),
            }
        )
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual([p.kind for p in problems], ["unreadable-report"])

    def test_a_report_older_than_the_code_refuses(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": istanbul("src/a.ts", {1: 1}),
            }
        )
        age(root / "coverage/coverage-final.json", 600)
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual([p.kind for p in problems], ["stale-report"])

    def test_a_report_newer_than_the_code_is_graded(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": istanbul("src/a.ts", {1: 1}),
            }
        )
        age(root / "src/a.ts", 600)
        problems, facts = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual(problems, [])
        self.assertTrue(facts["graded"])

    def test_a_changed_file_deleted_from_disk_does_not_make_it_stale(self):
        root = tree({"coverage/coverage-final.json": istanbul("src/a.ts", {1: 1})})
        age(root / "coverage/coverage-final.json", 600)
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual(problems, [])


class Uncovered(unittest.TestCase):
    def build(self, hits, added=2, threshold=100.0, report=None):
        body = report if report is not None else istanbul("src/a.ts", hits)
        root = tree({"src/a.ts": "x\n", "coverage/coverage-final.json": body})
        age(root / "src/a.ts", 600)
        return run(
            root,
            diff(("src/a.ts", 1, added), ("src/a.test.ts", 1, 1)),
            threshold=threshold,
        )

    def test_an_unexecuted_line_refuses(self):
        problems, _ = self.build({1: 1, 2: 0})
        self.assertEqual([p.kind for p in problems], ["uncovered"])

    def test_the_refusal_names_the_line(self):
        problems, facts = self.build({1: 1, 2: 0})
        self.assertIn("src/a.ts:2", guard.render(problems, facts))

    def test_every_line_executed_passes(self):
        problems, facts = self.build({1: 3, 2: 7})
        self.assertEqual(problems, [])
        self.assertEqual((facts["covered_lines"], facts["changed_lines"]), (2, 2))

    def test_a_file_absent_from_the_report_refuses_as_whole_file(self):
        problems, facts = self.build(
            {}, report=istanbul("src/elsewhere.ts", {1: 1})
        )
        self.assertEqual([p.kind for p in problems], ["uncovered"])
        self.assertIn("absent from the report", guard.render(problems, facts))

    def test_a_non_executable_changed_line_is_not_counted_against_it(self):
        # Only line 1 is a statement; line 2 is a brace the report never maps.
        problems, facts = self.build({1: 1})
        self.assertEqual(problems, [])
        self.assertEqual(facts["changed_lines"], 1)

    def test_a_lowered_threshold_can_pass_a_half_covered_diff(self):
        problems, _ = self.build({1: 1, 2: 0}, threshold=50.0)
        self.assertEqual(problems, [])

    def test_a_lowered_threshold_is_printed_above_the_verdict(self):
        problems, facts = self.build({1: 1, 2: 0}, threshold=50.0)
        rendered = guard.render(problems, facts)
        self.assertTrue(rendered.startswith("THRESHOLD LOWERED"), rendered)

    def test_a_threshold_of_100_prints_no_warning(self):
        problems, facts = self.build({1: 1, 2: 1})
        self.assertNotIn("THRESHOLD LOWERED", guard.render(problems, facts))

    def test_an_lcov_report_grades_the_same_as_istanbul(self):
        problems, _ = self.build({}, report=lcov("src/a.ts", {1: 1, 2: 0}))
        self.assertEqual([p.kind for p in problems], ["uncovered"])


class ReportPaths(unittest.TestCase):
    def test_an_absolute_path_in_the_report_finds_the_diff_path(self):
        root = tree({"src/a.ts": "x\n"})
        absolute = str(root / "src/a.ts")
        (root / "coverage").mkdir(exist_ok=True)
        (root / "coverage/coverage-final.json").write_text(
            istanbul(absolute, {1: 1}), encoding="utf-8"
        )
        age(root / "src/a.ts", 600)
        problems, facts = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual(problems, [])
        self.assertEqual(facts["covered_lines"], 1)

    def test_a_dot_slash_path_in_the_report_finds_the_diff_path(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": istanbul("./src/a.ts", {1: 0}),
            }
        )
        age(root / "src/a.ts", 600)
        problems, _ = run(root, diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)))
        self.assertEqual([p.kind for p in problems], ["uncovered"])


class NothingToMeasure(unittest.TestCase):
    def test_a_test_only_diff_passes_and_says_so(self):
        root = tree({})
        problems, facts = run(root, diff(("src/a.test.ts", 1, 4)))
        self.assertEqual(problems, [])
        self.assertIn("changes no source file", guard.render(problems, facts))

    def test_a_prose_only_diff_passes_and_says_so(self):
        root = tree({})
        problems, facts = run(root, diff(("CONTEXT.md", 1, 4)))
        self.assertEqual(problems, [])
        self.assertIn("changes no source file", guard.render(problems, facts))


class ExitCodes(unittest.TestCase):
    def call(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = guard.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_no_range_named_exits_two(self):
        code, text = self.call(["--repo", "."])
        self.assertEqual(code, 2)
        self.assertIn("no-range", text)

    def test_a_pass_exits_zero(self):
        root = tree({})
        path = root / "d.diff"
        path.write_text(diff(("src/a.test.ts", 1, 2)), encoding="utf-8")
        code, text = self.call(
            ["--repo", str(root), "--diff-file", str(path)]
        )
        self.assertEqual(code, 0)
        self.assertIn("OK", text)

    def test_a_graded_refusal_exits_one(self):
        root = tree(
            {
                "src/a.ts": "x\n",
                "coverage/coverage-final.json": istanbul("src/a.ts", {1: 0}),
            }
        )
        age(root / "src/a.ts", 600)
        path = root / "d.diff"
        path.write_text(
            diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)), encoding="utf-8"
        )
        code, text = self.call(
            [
                "--repo",
                str(root),
                "--diff-file",
                str(path),
                "--coverage",
                str(root / "coverage/coverage-final.json"),
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("REFUSED uncovered", text)

    def test_an_ungradeable_input_exits_two(self):
        root = tree({"src/a.ts": "x\n"})
        path = root / "d.diff"
        path.write_text(
            diff(("src/a.ts", 1, 1), ("src/a.test.ts", 1, 1)), encoding="utf-8"
        )
        code, text = self.call(
            [
                "--repo",
                str(root),
                "--diff-file",
                str(path),
                "--coverage",
                str(root / "nowhere.json"),
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("REFUSED no-report", text)

    def test_an_unreadable_range_exits_two(self):
        root = tree({})
        code, text = self.call(
            ["--repo", str(root), "--diff-range", "no-such-ref..HEAD"]
        )
        self.assertEqual(code, 2)
        self.assertIn("no-diff", text)


class EveryRefusalHasARemedy(unittest.TestCase):
    def test_no_refusal_can_print_without_one(self):
        kinds = {
            "empty-diff",
            "no-report",
            "unreadable-report",
            "stale-report",
            "untested",
            "uncovered",
        }
        self.assertEqual(set(guard.REMEDY), kinds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
