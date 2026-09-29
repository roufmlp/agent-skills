#!/usr/bin/env python3
"""Drill for move_verdicts.py.

Issue 24 of the tracker-tooling set, criterion 9. The move takes every gate
section out of an issue file and into the run that wrote it, byte for byte, and
deletes nothing.

    python3 test_move_verdicts.py
"""

import contextlib
import io
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import move_verdicts as mv

SPEC = """Status: blocked
Sentence: a thing

# 53 — a thing

## Acceptance criteria

1. It works.

```
# RAN — a comment inside a fence, not a heading
```

"""

RECORD_1 = """## Implementation record, attempt 1

Built it.

"""

REVIEW_1 = """## Review gate

### THE VERDICT: REJECT

A finding.

```
## Verify gate
# not a heading either, it is fenced
```

"""

VERIFY_1 = """## Verify gate, round 2

PASS.

"""

RECORD_2 = """## Implementation record, attempt 2 of run `batch-bbb222`

Built it again.

"""

REVIEW_2 = """## Critical review gate, round 3

REJECT.

"""

VERIFY_2 = """## Verify gate — batch-ccc333, attempt 1

PASS.

"""

TAIL = """## Ruled by the human, 2026-09-23

A ruling.
"""

LEDGER = "| 1 | 53 — a thing | blocked | attempt 1 |\n"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


class Room(unittest.TestCase):
    """A throwaway feature directory with a runs/ beside issues/."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="move-verdicts-"))
        self.feature = self.root / ".scratch" / "feat"
        self.issues = self.feature / "issues"
        self.issues.mkdir(parents=True)
        for batch in ("batch-aaa111", "batch-bbb222", "batch-ccc333"):
            run = self.feature / "runs" / batch
            run.mkdir(parents=True)
            (run / "run.md").write_text(LEDGER)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def issue(self, text, name="53-a-thing.md"):
        path = self.issues / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def moved(self, batch, issue_id="53"):
        path = self.feature / "runs" / batch / "verdicts" / f"{issue_id}-moved.md"
        return path.read_text(encoding="utf-8") if path.exists() else None


class WhatIsAGateSection(unittest.TestCase):

    def test_level_two_gate_headings_with_any_qualifier(self):
        text = SPEC + RECORD_1 + REVIEW_1 + VERIFY_1 + RECORD_2 + REVIEW_2 + VERIFY_2 + TAIL
        titles = [section.title for section in mv.gate_sections(text)]
        self.assertEqual(titles, [
            "Review gate", "Verify gate, round 2", "Critical review gate, round 3",
            "Verify gate — batch-ccc333, attempt 1"])

    def test_a_section_runs_to_the_next_level_two_heading(self):
        text = SPEC + REVIEW_1 + TAIL
        (section,) = mv.gate_sections(text)
        lines = text.splitlines(keepends=True)
        self.assertEqual("".join(lines[section.start:section.end]), REVIEW_1)

    def test_fenced_lines_and_deeper_headings_are_not_sections(self):
        text = SPEC + "### Review gate\n\nx\n\n" + TAIL
        self.assertEqual(mv.gate_sections(text), [])

    def test_a_note_about_a_gate_is_not_a_gate_section(self):
        text = SPEC + "## Review gate notes\n\nx\n\n## What a gate can see\n\ny\n"
        self.assertEqual(mv.gate_sections(text), [])


class WhichRunWroteIt(Room):
    """The three roads, in their order."""

    def test_the_heading_names_the_batch(self):
        path = self.issue(SPEC + RECORD_2 + VERIFY_2 + TAIL)
        plan = mv.plan(path, blame=lambda line: None)
        self.assertEqual([m.batch for m in plan.moves], ["batch-ccc333"])

    def test_the_record_above_names_the_batch(self):
        path = self.issue(SPEC + RECORD_2 + REVIEW_2 + TAIL)
        plan = mv.plan(path, blame=lambda line: "batch-aaa111")
        self.assertEqual([m.batch for m in plan.moves], ["batch-bbb222"])

    def test_the_blame_answers_last(self):
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        plan = mv.plan(path, blame=lambda line: "batch-aaa111")
        self.assertEqual([m.batch for m in plan.moves], ["batch-aaa111"])

    def test_a_batch_whose_ledger_does_not_name_the_issue_is_refused(self):
        (self.feature / "runs" / "batch-aaa111" / "run.md").write_text(
            "| 1 | 530 — another | done |\n")
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        plan = mv.plan(path, blame=lambda line: "batch-aaa111")
        self.assertEqual(plan.moves, [])
        self.assertEqual(len(plan.kept), 1)

    def test_a_bare_number_in_the_ledger_is_not_a_row(self):
        """A short id is everywhere in prose: durations, counts, dates."""
        (self.feature / "runs" / "batch-aaa111" / "run.md").write_text(
            "Scope: 53 minutes of suite time, 14 issues.\n"
            "| 1 | 530 — another | done |\n")
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        plan = mv.plan(path, blame=lambda line: "batch-aaa111")
        self.assertEqual(plan.moves, [])

    def test_both_ledger_row_shapes_name_the_issue(self):
        for row in ("| 53  | **blocked** | large |\n",
                    "| 9 | 53 — signed-in group has no guard | blocked |\n",
                    "| 9 | **53** — signed-in | blocked |\n"):
            with self.subTest(row=row):
                (self.feature / "runs" / "batch-aaa111" / "run.md").write_text(row)
                path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
                plan = mv.plan(path, blame=lambda line: "batch-aaa111")
                self.assertEqual(len(plan.moves), 1)

    def test_a_batch_with_no_run_directory_is_refused(self):
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        plan = mv.plan(path, blame=lambda line: "batch-fff999")
        self.assertEqual(plan.moves, [])
        self.assertEqual(len(plan.kept), 1)

    def test_no_answer_keeps_the_section(self):
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        plan = mv.plan(path, blame=lambda line: None)
        self.assertEqual(plan.moves, [])
        self.assertEqual([k.title for k in plan.kept], ["Review gate"])


class TheMoveDeletesNothing(Room):

    FULL = SPEC + RECORD_1 + REVIEW_1 + VERIFY_1 + RECORD_2 + REVIEW_2 + VERIFY_2 + TAIL

    def apply(self, path, blame=lambda line: "batch-aaa111"):
        return mv.apply(mv.plan(path, blame=blame), today="2026-09-23")

    def test_each_section_lands_in_its_batch_byte_for_byte(self):
        path = self.issue(self.FULL)
        self.apply(path)
        first = self.moved("batch-aaa111")
        self.assertIn(REVIEW_1 + VERIFY_1, first)
        self.assertIn(REVIEW_2, self.moved("batch-bbb222"))
        self.assertIn(VERIFY_2, self.moved("batch-ccc333"))

    def test_the_rest_of_the_issue_is_unchanged(self):
        path = self.issue(self.FULL)
        self.apply(path)
        after = path.read_text(encoding="utf-8")
        pointer_at = after.index("## Gate verdicts, moved out")
        pointer_end = after.index("## Implementation record, attempt 2")
        self.assertEqual(
            after[:pointer_at] + after[pointer_end:],
            SPEC + RECORD_1 + RECORD_2 + TAIL)

    def test_the_pointer_names_every_file_by_its_repo_relative_path(self):
        path = self.issue(self.FULL)
        self.apply(path)
        after = path.read_text(encoding="utf-8")
        for batch, count in (("batch-aaa111", 2), ("batch-bbb222", 1),
                             ("batch-ccc333", 1)):
            self.assertIn(
                f"`.scratch/feat/runs/{batch}/verdicts/53-moved.md`, "
                f"{count} section", after)

    def test_every_moved_byte_is_somewhere(self):
        path = self.issue(self.FULL)
        before = path.read_bytes()
        self.apply(path)
        moved = b"".join(
            (self.feature / "runs" / b / "verdicts" / "53-moved.md").read_bytes()
            for b in ("batch-aaa111", "batch-bbb222", "batch-ccc333"))
        for section in (REVIEW_1, VERIFY_1, REVIEW_2, VERIFY_2):
            self.assertIn(section.encode(), before)
            self.assertIn(section.encode(), moved)
            self.assertNotIn(section.encode(), path.read_bytes())

    def test_a_second_run_moves_nothing(self):
        path = self.issue(self.FULL)
        self.apply(path)
        after = path.read_bytes()
        moved = self.moved("batch-aaa111")
        plan = mv.plan(path, blame=lambda line: "batch-aaa111")
        self.assertEqual(plan.moves, [])
        mv.apply(plan, today="2026-09-24")
        self.assertEqual(path.read_bytes(), after)
        self.assertEqual(self.moved("batch-aaa111"), moved)

    def test_an_existing_moved_file_is_appended_to_never_overwritten(self):
        target = self.feature / "runs" / "batch-aaa111" / "verdicts"
        target.mkdir(parents=True)
        (target / "53-moved.md").write_text("EARLIER\n")
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL)
        self.apply(path)
        text = self.moved("batch-aaa111")
        self.assertTrue(text.startswith("EARLIER\n"))
        self.assertIn(REVIEW_1, text)

    def test_a_kept_section_stays_where_it_was(self):
        path = self.issue(SPEC + RECORD_1 + REVIEW_1 + RECORD_2 + REVIEW_2 + TAIL)
        self.apply(path, blame=lambda line: None)
        after = path.read_text(encoding="utf-8")
        self.assertIn(RECORD_1 + REVIEW_1, after)
        self.assertNotIn(REVIEW_2, after)


class TheBlameRoad(unittest.TestCase):
    """Git: the commit that brought the heading line onto the first-parent
    chain, walked forward to the first merge, whose subject names the batch."""

    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp(prefix="move-verdicts-git-"))
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.test")
        git(self.repo, "config", "user.name", "t")
        self.issue = self.repo / "53-a.md"
        self.issue.write_text(SPEC)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "spec")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def append_on(self, branch, text, message):
        git(self.repo, "checkout", "-q", branch)
        with open(self.issue, "a") as handle:
            handle.write(text)
        git(self.repo, "commit", "-q", "-am", message)

    def line_of(self, heading):
        return self.issue.read_text().splitlines().index(heading) + 1

    def test_a_merged_run_is_named_by_its_merge(self):
        git(self.repo, "checkout", "-q", "-b", "run")
        self.append_on("run", REVIEW_1, "a gate wrote")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--no-ff", "run", "-m",
            "Merge run batch-aaa111: one issue")
        blame = mv.git_blame_batch(self.repo, self.issue)
        self.assertEqual(blame(self.line_of("## Review gate")), "batch-aaa111")

    def test_a_fast_forwarded_run_is_named_by_the_merge_after_it(self):
        git(self.repo, "checkout", "-q", "-b", "run")
        self.append_on("run", REVIEW_1, "a gate wrote")
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "other.txt").write_text("x\n")
        git(self.repo, "add", "other.txt")
        git(self.repo, "commit", "-q", "-m", "main moved")
        git(self.repo, "checkout", "-q", "run")
        git(self.repo, "merge", "-q", "--no-ff", "main", "-m",
            "Merge main into run batch-bbb222, ready for main to fast-forward")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "run")
        blame = mv.git_blame_batch(self.repo, self.issue)
        self.assertEqual(blame(self.line_of("## Review gate")), "batch-bbb222")

    def test_a_merge_naming_no_batch_answers_nothing(self):
        git(self.repo, "checkout", "-q", "-b", "harden")
        self.append_on("harden", REVIEW_1, "a pass wrote")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--no-ff", "harden", "-m",
            "Merge hardening pass h0923")
        blame = mv.git_blame_batch(self.repo, self.issue)
        self.assertIsNone(blame(self.line_of("## Review gate")))

    def test_an_uncommitted_line_answers_nothing(self):
        with open(self.issue, "a") as handle:
            handle.write(REVIEW_1)
        blame = mv.git_blame_batch(self.repo, self.issue)
        self.assertIsNone(blame(self.line_of("## Review gate")))


class TheCommandLine(Room):

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = mv.main(list(argv))
        return code, out.getvalue()

    def test_it_is_a_dry_run_unless_told_to_apply(self):
        path = self.issue(SPEC + RECORD_2 + VERIFY_2 + TAIL + "x" * 200)
        before = path.read_bytes()
        code, out = self.run_main("--issues", str(self.issues),
                                  "--min-bytes", "100", "--no-git")
        self.assertEqual(code, 0, out)
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("batch-ccc333", out)
        self.assertIn("DRY RUN", out)

    def test_apply_moves_and_a_small_file_is_left_alone(self):
        big = self.issue(SPEC + RECORD_2 + VERIFY_2 + TAIL + "x" * 200)
        small = self.issue(SPEC + RECORD_2 + VERIFY_2, name="54-small.md")
        small_before = small.read_bytes()
        code, out = self.run_main("--issues", str(self.issues),
                                  "--min-bytes", "300", "--no-git", "--apply")
        self.assertEqual(code, 0, out)
        self.assertNotIn(VERIFY_2, big.read_text())
        self.assertEqual(small.read_bytes(), small_before)

    def test_a_kept_section_is_reported(self):
        self.issue(SPEC + RECORD_1 + REVIEW_1 + TAIL + "x" * 200)
        code, out = self.run_main("--issues", str(self.issues),
                                  "--min-bytes", "100", "--no-git")
        self.assertEqual(code, 0, out)
        self.assertIn("KEPT", out)
        self.assertIn("Review gate", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
