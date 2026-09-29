#!/usr/bin/env python3
"""Drill for correction_brief.py.

The one thing this file exists to pin: the composed prompt earns the cap hook's
correction exemption, judged by the HOOK'S OWN function and never by a second
copy of its rule. A correction brief that puts the marker late is capped like a
first attempt, and its owed list is the varying part that cannot be cut.

    python3 test_correction_brief.py
"""

from __future__ import annotations

import io
import contextlib
import pathlib
import tempfile
import unittest

import subprocess

import check_diff_coverage as coverage
import correction_brief as brief


GATED = """# 501 something

## Verify gate

verify: pass

## Review gate

review: pass
"""


def issue(body: str = GATED, name: str = "501-a.md",
          prefix: str = "corrbrief-") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix=prefix))
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path


RUN_FACTS = ("register", "dev server", "workspace", "sign-in", "qa")


def run_facts_in(prompt: str, issue_path) -> list:
    """The run-fact words the prompt carries OUTSIDE the issue path.

    The path is the runner's argument, echoed whole. Its temp folder name is
    random, so a scan that includes it tests `mkdtemp`, not this script.
    """
    text = prompt.replace(str(issue_path), "").lower()
    return [word for word in RUN_FACTS if word in text]


def graded_repo(exit_code: int = 0, items=()) -> pathlib.Path:
    """A git work tree whose current tree carries a coverage stamp, as
    `check_diff_coverage.py` leaves one."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-repo-"))
    (root / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"], ["add", "-A"],
                 ["commit", "-q", "-m", "one"]):
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True)
    if exit_code is not None:
        coverage.write_stamp(root, exit_code, list(items))
    return root


def run_main(argv):
    """`main`, run from a tree the coverage check has graded green, unless
    the case names its own `--repo`."""
    if "--repo" not in argv:
        argv = [*argv, "--repo", str(graded_repo())]
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = brief.main(argv)
    return code, out.getvalue()


class Compose(unittest.TestCase):
    def test_the_marker_lands_inside_the_hooks_opening_window(self):
        """Read by the hook's own `is_correction`, imported, not copied. Ticket
        36 ruling 11 reads `CORRECTION ROUND` in the opening alone."""
        text = brief.compose(issue(), ["a missing pin on the totals test"])
        self.assertTrue(brief.earns_exemption(text))

    def test_every_item_reaches_the_prompt(self):
        text = brief.compose(issue(), ["the first owed thing",
                                       "the second owed thing"])
        self.assertIn("the first owed thing", text)
        self.assertIn("the second owed thing", text)

    def test_the_items_are_numbered(self):
        text = brief.compose(issue(), ["one", "two"])
        self.assertIn("1. one", text)
        self.assertIn("2. two", text)

    def test_the_issue_path_is_carried_in_full(self):
        path = issue()
        self.assertIn(str(path), brief.compose(path, ["x"]))

    def test_it_says_the_runner_commits(self):
        """`SKILL.md`: an implementer never commits its own work. A correction
        implementer is an implementer."""
        self.assertIn("commit", brief.compose(issue(), ["x"]).lower())

    def test_it_carries_no_run_facts(self):
        """The round's whole shape: the items, the marker and nothing else. The
        run's facts are in the ledger header the implementer reads first."""
        path = issue()
        self.assertEqual(run_facts_in(brief.compose(path, ["x"]), path), [])

    def test_a_temp_folder_that_spells_a_run_fact_is_not_a_leak(self):
        """The issue path is the runner's, not this script's. `mkdtemp` names
        its folder with eight random characters, and about one run in two
        hundred spelled `qa` (`corrbrief-3dptbqau`), so the check above failed
        at random on 2026-09-26. Pinned here with the spelling forced."""
        path = issue(prefix="corrbrief-qa-register-workspace-")
        self.assertEqual(run_facts_in(brief.compose(path, ["x"]), path), [])

    def test_a_run_fact_outside_the_path_is_still_caught(self):
        """The control: removing the path must not blind the check."""
        path = issue(prefix="corrbrief-qa-")
        prompt = brief.compose(path, ["x"]) + "Read the register first.\n"
        self.assertEqual(run_facts_in(prompt, path), ["register"])


class Refusal(unittest.TestCase):
    def test_no_owed_items_refuses(self):
        """An empty owed list is not a correction round. `SKILL.md`: both gates
        pass and a verdict enumerates follow-up items. Nothing owed is `done`."""
        code, text = run_main(["--issue", str(issue())])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_a_missing_issue_file_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        code, text = run_main(["--issue", str(root / "nope.md"), "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("nope.md", text)

    def test_an_issue_file_with_no_gate_section_refuses(self):
        """The scope of the round is the verdicts' owed list. No verdict on disk
        means the list was built from something else."""
        code, text = run_main(["--issue", str(issue("# 501\n\nnothing\n")),
                               "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("gate", text.lower())

    def test_an_issue_path_inside_a_worktree_is_accepted(self):
        """Ruled by the human, 2026-09-13, reversing the refusal this pinned.

        The gates write their verdict beside the BRANCH, so the worktree copy is
        the one that holds the owed list. The GATE_HEADINGS check below is what
        actually protects the round, and it is path-agnostic.
        """
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        deep = root / ".claude" / "worktrees" / "batch-1" / ".scratch"
        deep.mkdir(parents=True)
        path = deep / "501-a.md"
        path.write_text(GATED, encoding="utf-8")
        code, text = run_main(["--issue", str(path), "--item", "x"])
        self.assertEqual(code, 0, text)
        self.assertNotIn("MAIN CHECKOUT", text)

    def test_a_worktree_path_with_no_verdict_is_still_refused(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief2-"))
        deep = root / ".claude" / "worktrees" / "batch-1" / ".scratch"
        deep.mkdir(parents=True)
        path = deep / "501-a.md"
        path.write_text("# 501 a thing\n\n## Acceptance criteria\n\n1. x\n",
                        encoding="utf-8")
        code, text = run_main(["--issue", str(path), "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("Verify gate", text)

    def test_the_verdicts_file_answers_the_heading_question(self):
        """Issue 24 of the tracker-tooling set, 2026-09-23: the verdicts live
        in `runs/<batch-id>/verdicts/`, so the issue file holds none."""
        spec = issue("# 501 a thing\n\n## Acceptance criteria\n\n1. x\n")
        verdicts = issue(GATED, name="501-attempt-1.md")
        code, text = run_main(["--issue", str(spec), "--verdicts",
                               str(verdicts), "--item", "x"])
        self.assertEqual(code, 0, text)

    def test_a_verdicts_file_with_no_gate_heading_is_refused(self):
        verdicts = issue("# nothing\n", name="501-attempt-1.md")
        code, text = run_main(["--issue", str(issue()), "--verdicts",
                               str(verdicts), "--item", "x"])
        self.assertEqual(code, 1)
        self.assertIn("501-attempt-1.md", text)

    def test_a_blank_item_refuses(self):
        code, text = run_main(["--issue", str(issue()), "--item", "   "])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_the_refusal_says_it_never_waits_for_the_human(self):
        _, text = run_main(["--issue", str(issue())])
        self.assertIn("AFK", text)

    def test_a_composed_prompt_that_lost_its_marker_refuses(self):
        """The guard is on the OUTPUT, so a later edit to the preamble that
        pushes the marker past the window is caught here rather than on a run."""
        original = brief.PREAMBLE
        try:
            brief.PREAMBLE = "x" * 500 + "\nCORRECTION ROUND for {issue}.\n"
            code, text = run_main(["--issue", str(issue()), "--item", "x"])
            self.assertEqual(code, 1)
            self.assertIn("exemption", text.lower())
        finally:
            brief.PREAMBLE = original



class EachGateHasItsOwnFile(unittest.TestCase):
    """Issue 51 of the tracker-tooling set, AC5: each gate writes its own
    verdict file, and each file is read for its own gate's heading."""

    def spec(self, level="full"):
        return issue(f"Level: {level}\n\n# 501 something\n", name="501-a.md")

    def gate_file(self, gate, body=None):
        heading = "## Review gate" if gate == "review" else "## Verify gate"
        return issue(body if body is not None else f"{heading}\n\npass\n",
                     name=f"501-attempt-1-{gate}.md")

    def brief(self, spec, *files, items=("from review", "from verify")):
        argv = ["--issue", str(spec)]
        for path in files:
            argv += ["--verdicts", str(path)]
        for item in items:
            argv += ["--item", item]
        return run_main(argv)

    def test_both_gate_files_build_one_brief(self):
        code, text = self.brief(self.spec(), self.gate_file("review"),
                                self.gate_file("verify"))
        self.assertEqual(code, 0, text)
        self.assertIn("1. from review", text)
        self.assertIn("2. from verify", text)

    def test_a_verify_file_without_its_heading_is_refused(self):
        wrong = self.gate_file("verify", "## Review gate\n\npass\n")
        code, text = self.brief(self.spec(), self.gate_file("review"), wrong)
        self.assertEqual(code, 1)
        self.assertIn(str(wrong), text)
        self.assertIn("## Verify gate", text)

    def test_the_review_file_alone_is_refused_at_full(self):
        code, text = self.brief(self.spec(), self.gate_file("review"))
        self.assertEqual(code, 1)
        self.assertIn("verify file is missing", text)

    def test_the_review_file_alone_builds_the_brief_at_light(self):
        code, text = self.brief(self.spec("light"), self.gate_file("review"))
        self.assertEqual(code, 0, text)

    def test_a_light_issue_with_a_verify_file_on_disk_needs_it_too(self):
        """Code review of issue 51: a light issue the run lifted to full has a
        verify file beside the review file, and its owed items count."""
        review = self.gate_file("review")
        (review.parent / review.name.replace("-review", "-verify")).write_text(
            "## Verify gate\n\nREJECT\n", encoding="utf-8")
        code, text = self.brief(self.spec("light"), review)
        self.assertEqual(code, 1)
        self.assertIn("verify file is missing", text)

    def test_the_legacy_shared_file_alone_still_builds_the_brief(self):
        code, text = self.brief(self.spec(), issue(GATED, name="501-attempt-1.md"))
        self.assertEqual(code, 0, text)


class ItemsFile(unittest.TestCase):
    def test_items_come_off_a_file_one_per_line(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        listing = root / "owed.txt"
        listing.write_text("first\n\nsecond\n", encoding="utf-8")
        code, text = run_main(["--issue", str(issue()),
                               "--items-file", str(listing)])
        self.assertEqual(code, 0)
        self.assertIn("1. first", text)
        self.assertIn("2. second", text)

    def test_a_missing_items_file_refuses(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="corrbrief-"))
        code, _ = run_main(["--issue", str(issue()),
                            "--items-file", str(root / "gone.txt")])
        self.assertEqual(code, 1)


class SharedRule(unittest.TestCase):
    def test_the_exemption_is_the_hooks_own_function_when_the_hook_is_there(self):
        """One rule, two readers. Sitting 2 of this ticket found the cap's
        record re-implementing the refusal's exemption tests, and a later change
        to one alone would have the two disagreeing."""
        self.assertTrue(brief.hook_module() is None
                        or hasattr(brief.hook_module(), "is_correction"))

    def test_the_real_hook_lets_the_real_prompt_past(self):
        """End to end, not a stand-in. The hook's own `decide` is handed the
        payload shape a spawn produces, carrying this script's own output."""
        hook = brief.hook_module()
        if hook is None:
            self.skipTest("no cap hook installed on this machine")
        prompt = brief.compose(issue(), ["x " * 500])
        code, _ = hook.decide({
            "tool_input": {"subagent_type": "run-issues-implementer",
                           "prompt": prompt}})
        self.assertEqual(code, 0)

    def test_the_same_prompt_without_the_marker_is_refused_by_the_real_hook(self):
        """The counterpart: proof the exemption is what carried it, not brevity."""
        hook = brief.hook_module()
        if hook is None:
            self.skipTest("no cap hook installed on this machine")
        prompt = brief.compose(issue(), ["x " * 500]).replace(
            "CORRECTION ROUND", "Follow-up work")
        code, _ = hook.decide({
            "tool_input": {"subagent_type": "run-issues-implementer",
                           "prompt": prompt}})
        self.assertEqual(code, 2)

    def test_with_no_hook_installed_the_prompt_is_still_emitted(self):
        """No hook means no cap to fail. Refusing there would stop a run over a
        guard that is not present."""
        original = brief.hook_module
        try:
            brief.hook_module = lambda: None
            code, text = run_main(["--issue", str(issue()), "--item", "x"])
            self.assertEqual(code, 0)
            self.assertIn("CORRECTION ROUND", text)
        finally:
            brief.hook_module = original


class TheCorrectionSpawnIsExemptedFromTheFullSuite(unittest.TestCase):
    """Criterion 3 of issue 06, `three suites per issue`.

    A correction round runs its named evidence tests and the typecheck. The
    runner's coverage re-run that follows is the whole-tree reading, so the
    spawn's own full suite reads a tree the runner is about to read again.
    """

    def test_the_prompt_states_the_exemption(self):
        text = brief.compose(issue(), ["a missing pin on the totals test"])
        self.assertIn("full suite", text)
        self.assertIn("typecheck", text)

    def test_the_exemption_survives_main_and_reaches_the_spawn(self):
        code, text = run_main(["--issue", str(issue()), "--item",
                               "a missing pin on the totals test"])
        self.assertEqual(code, 0, text)
        self.assertIn("full suite", text)

    def test_the_exemption_is_not_bought_at_the_cost_of_the_marker(self):
        """The sentence must not push `CORRECTION ROUND` out of the hook's
        400-character opening window. A brief that gains the sentence and
        loses its exemption is refused by the cap and never spawns."""
        text = brief.compose(issue(), ["a missing pin on the totals test"])
        self.assertTrue(
            brief.earns_exemption(text),
            "the exemption sentence pushed `CORRECTION ROUND` out of the "
            "hook's opening window, so the prompt no longer earns the cap "
            "exemption",
        )

    def test_the_marker_still_opens_the_prompt(self):
        """Pinned directly, so a future edit cannot satisfy the test above by
        weakening the hook."""
        text = brief.compose(issue(), ["one owed item"])
        self.assertTrue(text.lstrip().startswith("CORRECTION ROUND"))


class CoverageIsGradedBeforeTheBrief(unittest.TestCase):
    """Run `batch-e35a25`, issue 227: the runner wrote the correction brief,
    then ran the coverage check, and its refusals bought a second correction
    spawn. `SKILL.md` step 5 made the order a sentence. The brief now refuses
    without a coverage grading of the tree it is about to hand over, and
    carries that grading's refusals itself."""

    def test_a_tree_the_coverage_check_never_graded_is_refused(self):
        code, text = run_main(["--issue", str(issue()), "--item", "one",
                               "--repo", str(graded_repo(exit_code=None))])
        self.assertEqual(code, 1)
        self.assertIn("check_diff_coverage.py", text)

    def test_a_tree_changed_since_its_grading_is_refused(self):
        repo = graded_repo()
        (repo / "a.ts").write_text("export const a = 2;\n", encoding="utf-8")
        code, text = run_main(["--issue", str(issue()), "--item", "one",
                               "--repo", str(repo)])
        self.assertEqual(code, 1)
        self.assertIn("check_diff_coverage.py", text)

    def test_the_coverage_refusals_reach_the_brief_as_items(self):
        repo = graded_repo(1, ["REFUSED uncovered: src/a.ts lines 3-5"])
        code, text = run_main(["--issue", str(issue()), "--item", "M4 pin",
                               "--repo", str(repo)])
        self.assertEqual(code, 0, text)
        self.assertIn("1. M4 pin", text)
        self.assertIn("2. REFUSED uncovered: src/a.ts lines 3-5", text)

    def test_a_coverage_refusal_alone_is_a_brief(self):
        repo = graded_repo(1, ["REFUSED uncovered: src/a.ts lines 3-5"])
        code, text = run_main(["--issue", str(issue()), "--repo", str(repo)])
        self.assertEqual(code, 0, text)
        self.assertIn("1. REFUSED uncovered: src/a.ts lines 3-5", text)

    def test_a_grading_that_could_not_grade_is_refused(self):
        repo = graded_repo(2, ["REFUSED no-report: coverage-final.json"])
        code, text = run_main(["--issue", str(issue()), "--item", "one",
                               "--repo", str(repo)])
        self.assertEqual(code, 1)
        self.assertIn("no-report", text)


if __name__ == "__main__":
    unittest.main()
