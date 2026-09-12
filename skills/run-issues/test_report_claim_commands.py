#!/usr/bin/env python3
"""Drill for report_claim_commands.py.

The three things this file exists to pin, in the order they would hurt:

1. **It never refuses.** The human ruled the check report-only on 2026-09-12 against
   a measurement that says a refusal would delete true sentences. A non-zero
   exit at the finale reads as a fault and would stop a run, so every path here
   asserts exit 0 -- an unreadable range, a missing repo, a hundred hits.
2. **It reports a count, not a verdict.** The number is the deliverable, and the
   flipping fact around it is printed as ADVICE with the ruling named beside it.
3. **The line number is the NEW file's.** A report naming the wrong line sends
   the reader to a sentence nobody wrote, which is the same fault class the
   report exists to find.

    python3 test_report_claim_commands.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import tempfile
import unittest

import report_claim_commands as reporter


# A unified diff at `--unified=0`, the shape `collect` asks git for. Two added
# comment lines, one of which fires, plus an added code line that is neither a
# comment nor a test name.
DIFF = """\
diff --git a/src/a.ts b/src/a.ts
--- a/src/a.ts
+++ b/src/a.ts
@@ -10,0 +11,3 @@
+// every write on the import road upserts on a Zoho id and nothing else does
+const x = 1
+// this comment claims only what the function below it does
@@ -40,0 +44,1 @@
+  it('reads the door and no other route reads wiring', () => {
"""


def run(**kwargs) -> tuple[int, str]:
    """Call `main` with flags, capturing both streams."""
    out, err = io.StringIO(), io.StringIO()
    argv = [item for key, value in kwargs.items()
            for item in (f"--{key.replace('_', '-')}", str(value))]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = reporter.main(argv)
    return code, out.getvalue() + err.getvalue()


def tree(commits) -> pathlib.Path:
    """A throwaway git repo. `commits` is a list of {path: text}."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="claimcmd-"))
    def git(*args):
        subprocess.run(["git", *args], cwd=root, check=True,
                       capture_output=True, text=True)
    git("init", "--initial-branch", "main")
    git("config", "user.email", "drill@example.com")
    git("config", "user.name", "Drill")
    for files in commits:
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "one")
    return root


class TheDiffReaderFindsProseOnly(unittest.TestCase):
    def test_it_keeps_comments_and_test_names(self):
        hits = reporter.added_prose(DIFF)
        kinds = sorted(one.kind for one in hits)
        self.assertEqual(kinds, ["comment", "comment", "test-name"])

    def test_it_drops_added_code(self):
        texts = [one.text for one in reporter.added_prose(DIFF)]
        self.assertNotIn("const x = 1", texts)

    def test_the_line_number_is_the_new_files(self):
        first = reporter.added_prose(DIFF)[0]
        self.assertEqual(first.path, "src/a.ts")
        self.assertEqual(first.line, 11)

    def test_a_later_hunk_restarts_at_its_own_header(self):
        """The counter follows `@@ ... +44`, never the running total. A report
        naming a line the author never wrote is worse than no report."""
        last = reporter.added_prose(DIFF)[-1]
        self.assertEqual(last.line, 44)
        self.assertEqual(last.kind, "test-name")

    def test_an_empty_diff_reads_as_nothing_rather_than_raising(self):
        self.assertEqual(reporter.added_prose(""), [])


class TheTriggerVocabulary(unittest.TestCase):
    def test_it_fires_on_a_tree_wide_claim(self):
        self.assertTrue(reporter.fires("and nothing else in the suite reads it"))

    def test_it_fires_on_no_other(self):
        self.assertTrue(reporter.fires("no other caller reaches this branch"))

    def test_it_is_case_blind(self):
        self.assertTrue(reporter.fires("Nothing Else raises this kind"))

    def test_it_is_silent_on_a_sentence_about_this_file(self):
        self.assertFalse(reporter.fires("reads three tables and returns a row"))

    def test_it_names_which_phrase_fired(self):
        self.assertEqual(reporter.fires("nothing else does"), ["nothing else"])

    def test_the_only_is_deliberately_out(self):
        """Measured, not assumed: `the only` fires 5 to 47 times a run over the
        six runs graded on 2026-09-12, and most of those describe the file they
        sit in. It is in the WIDE vocabulary the record rejected."""
        self.assertFalse(reporter.fires("this is the only place it happens"))


class ItNeverRefuses(unittest.TestCase):
    def test_a_clean_range_exits_zero(self):
        root = tree([{"src/a.ts": "const a = 1\n"},
                     {"src/a.ts": "const a = 1\n// a plain comment\n"}])
        code, _ = run(repo=root, range="HEAD~1..HEAD",
                      out=root / "report.md")
        self.assertEqual(code, 0)

    def test_a_range_full_of_hits_still_exits_zero(self):
        body = "".join(f"// nothing else does thing {n}\n" for n in range(40))
        root = tree([{"src/a.ts": "const a = 1\n"},
                     {"src/a.ts": "const a = 1\n" + body}])
        code, text = run(repo=root, range="HEAD~1..HEAD", out=root / "r.md")
        self.assertEqual(code, 0)
        self.assertIn("40", text)

    def test_a_range_git_cannot_read_exits_zero_and_says_so(self):
        root = tree([{"src/a.ts": "const a = 1\n"}])
        code, text = run(repo=root, range="nosuchref..HEAD", out=root / "r.md")
        self.assertEqual(code, 0)
        self.assertIn("COULD NOT READ", text)

    def test_a_repo_that_is_not_a_repo_exits_zero(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="claimcmd-bare-"))
        code, text = run(repo=root, range="HEAD~1..HEAD", out=root / "r.md")
        self.assertEqual(code, 0)
        self.assertIn("COULD NOT READ", text)

    def test_an_unwritable_report_path_exits_zero(self):
        """The report is the product, but a run that cannot write it has still
        run its suite and its build. It says so on stderr and carries on."""
        root = tree([{"src/a.ts": "// nothing else does\n"}])
        code, text = run(repo=root, range="HEAD..HEAD",
                         out=root / "nodir" / "\0bad")
        self.assertEqual(code, 0)
        self.assertIn("NOT written", text)


class TheReportIsTheDeliverable(unittest.TestCase):
    def setUp(self):
        self.root = tree([
            {"src/a.ts": "const a = 1\n"},
            {"src/a.ts": "const a = 1\n// nothing else raises this kind\n",
             "tests/b.test.ts": "// no other file reads route wiring\n",
             "docs/c.md": "nothing else, but this file is out of scope\n"},
        ])
        self.out = self.root / "runs" / "batch-x" / "claim-commands.md"
        self.code, self.text = run(repo=self.root, range="HEAD~1..HEAD",
                                   out=self.out, batch="batch-x")

    def test_it_writes_the_file_it_was_given(self):
        self.assertTrue(self.out.is_file())

    def test_every_hit_names_its_file_and_line(self):
        written = self.out.read_text(encoding="utf-8")
        self.assertIn("src/a.ts:2", written)
        self.assertIn("tests/b.test.ts:1", written)

    def test_every_hit_quotes_the_line(self):
        written = self.out.read_text(encoding="utf-8")
        self.assertIn("nothing else raises this kind", written)

    def test_a_path_outside_the_three_roots_is_never_read(self):
        written = self.out.read_text(encoding="utf-8")
        self.assertNotIn("docs/c.md", written)

    def test_it_prints_the_count_the_report_exists_to_produce(self):
        self.assertIn("2 lines fire", self.text)

    def test_it_names_the_scanned_total_beside_the_count(self):
        """A rate needs a denominator. Two hits out of two prose lines and two
        out of two thousand are different runs."""
        written = self.out.read_text(encoding="utf-8")
        self.assertIn("added comment and test-name lines", written)

    def test_it_carries_the_flipping_fact_and_names_it_as_advice(self):
        written = self.out.read_text(encoding="utf-8")
        self.assertIn("30", written)
        self.assertIn("REFUSES NOTHING", written)

    def test_it_says_the_verdict_is_abduls(self):
        written = self.out.read_text(encoding="utf-8")
        self.assertIn("the human", written)


class TheFlippingFactReadsBothWays(unittest.TestCase):
    def test_under_the_threshold_it_says_the_trigger_is_narrow_enough(self):
        text = reporter.render([], 100, "a..b", "batch-x")
        self.assertIn("at or below", text)

    def test_over_the_threshold_it_says_drop_the_question(self):
        many = [reporter.Hit("src/a.ts", n, "comment", "nothing else", ["x"])
                for n in range(31)]
        text = reporter.render(many, 100, "a..b", "batch-x")
        self.assertIn("above", text)
        self.assertIn("drop", text.lower())

    def test_the_threshold_is_a_named_constant_not_a_literal(self):
        self.assertEqual(reporter.FLIP, 30)


class TheRunDirectoryIsResolvedLikeEveryOtherRunFile(unittest.TestCase):
    def test_the_report_sits_beside_the_ledger(self):
        got = reporter.report_beside("/x/.scratch/f/runs/batch-y/run.md")
        self.assertEqual(got, "/x/.scratch/f/runs/batch-y/claim-commands.md")


class TheFinaleActuallyRunsIt(unittest.TestCase):
    """A report nothing invokes produces no number.

    the human's three-class test in `~/.claude/CLAUDE.md`: this is the class that
    can refuse, so it is built rather than left to whoever next reads
    `finale.md`. The wiring went into the finale's measurement step on
    2026-09-12, paid for line by line against that file's 803-line ceiling.
    """

    def setUp(self):
        here = pathlib.Path(__file__).resolve().parent
        self.finale = (here / "finale.md").read_text(encoding="utf-8")

    def test_the_finale_names_the_script(self):
        self.assertIn("report_claim_commands.py", self.finale)

    def test_the_finale_places_the_report_beside_the_ledger(self):
        self.assertIn("--ledger <run.md>", self.finale)
        self.assertIn("claim-commands.md", self.finale)

    def test_the_finale_says_in_its_own_words_that_it_refuses_nothing(self):
        """The one sentence a reader must not have to open the script for. A
        finale author who reads this as a gate will treat a hit as a fault."""
        flat = " ".join(self.finale.split())
        self.assertIn("REFUSES NOTHING and exits 0 whatever it finds", flat)

    def test_the_range_is_resolved_rather_than_guessed(self):
        self.assertIn("git merge-base main HEAD", self.finale)


if __name__ == "__main__":
    unittest.main()
