#!/usr/bin/env python3
"""Drill for plan_check.py: a throwaway product repo with a fixture
`changes/bubble/` folder, where each refusal and each clear road is a real
plan, note, report and commit.

    python3 test_plan_check.py
"""

import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import plan_check as mod  # noqa: E402

NOTE_01 = textwrap.dedent("""\
    # 01 Header bubble

    A bubble in the header of every signed-in screen.

    Screens: all signed-in
    Risk: none
    Waits for: none

    ## Done

    - `sh e2e/bubble.sh`: the bubble opens on Home
    - `sh tests/bubble.sh`: the sheet keeps its text

    ## Tests

    `e2e/bubble.spec.ts` and `tests/bubble.test.ts`, committed with this note.
""")

NOTE_02 = textwrap.dedent("""\
    # 02 Order page

    The order page shows the report count.

    Screens: Order
    Risk: row writes
    Waits for: 01

    ## Done

    - `sh e2e/order.sh`: the count shows on Order

    ## Tests

    `e2e/order.spec.ts`
""")

PLAN = textwrap.dedent("""\
    # Bubble plan

    Feature: bubble

    ## Notes

    | Note | What it does | Migration | Waits for | Screens |
    | --- | --- | --- | --- | --- |
    | 01 | The bubble | none | none | all signed-in |
    | 02 | The count | none | 01 | Order |

    ## Questions

    - [core design] 01: the bubble is a new pattern; its check is `npm run check:controls`
      Answer: yes, add it
    - [money or access rules] 02: the count reads every user's reports
      Answer: no, only the signed-in user's

    Approved: 2026-11-03
""")

REPORT = textwrap.dedent("""\
    # Bubble report

    Feature: bubble
    State: {state}
    {merged}
    ## Notes

    | Note | State | Strikes | Attempts | Last report |
    | --- | --- | --- | --- | --- |
    | 01 | {s01} | 0 | 1 | |
    | 02 | {s02} | 3 | 3 | |
""")

FILES = {
    "changes/bubble/01-header.md": NOTE_01,
    "changes/bubble/02-order.md": NOTE_02,
    "changes/bubble/plan.md": PLAN,
    "e2e/bubble.sh": "exit 1\n",
    "e2e/order.sh": "exit 1\n",
    "tests/bubble.sh": "exit 1\n",
    "e2e/bubble.spec.ts": "// spec\n",
    "e2e/order.spec.ts": "// spec\n",
    "tests/bubble.test.ts": "// test\n",
    "README.md": "# A product\n",
}


def report(state="running", merged="", s01="merged abc1234", s02="not started"):
    return REPORT.format(state=state, merged=merged, s01=s01, s02=s02)


class Product(unittest.TestCase):
    """A product repo on `main` with the fixture committed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.tree = root / "product"
        self.tree.mkdir()
        for path, text in FILES.items():
            self.write(path, text)
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.git("commit", "-qm", "approved plan")
        self.git("checkout", "-qb", "feature/bubble")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        full = self.tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.tree, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def run_check(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main([*args, "--tree", str(self.tree)])
        return code, out.getvalue()

    def commit_all(self, message="more"):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def over_budget(self, over=True):
        common = pathlib.Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / "suite").mkdir(exist_ok=True)
        row = {"kind": "full", "seconds": 550.0, "budget_seconds": 300, "over_budget": over}
        (common / "suite" / "runs.jsonl").write_text(json.dumps(row) + "\n")


class PlanRoad(Product):

    def test_approved_plan_is_clear(self):
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("plan: approved 2026-11-03 at", out)
        self.assertIn("2 note(s); 2 question(s) answered", out)

    def test_no_plan_is_the_interview_road(self):
        (self.tree / "changes/bubble/plan.md").unlink()
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2)
        self.assertIn("INTERVIEW: no plan: changes/bubble/plan.md does not exist", out)

    def test_merged_report_on_main_refuses_with_the_commit(self):
        self.git("checkout", "-q", "main")
        self.write("changes/bubble/report.md", report("merged", "Merged: 2026-11-03 9d4cf45"))
        self.commit_all("merge")
        self.git("checkout", "-q", "feature/bubble")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("report.md on main says `Merged: 2026-11-03 9d4cf45`", out)

    def test_merged_report_on_master_counts_too(self):
        self.git("branch", "-m", "main", "master")
        self.git("checkout", "-q", "master")
        self.write("changes/bubble/report.md", report("merged", "Merged: 2026-11-03 9d4cf45"))
        self.commit_all("merge")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("on master says", out)

    def test_merged_report_only_on_the_feature_branch_does_not_refuse(self):
        self.write("changes/bubble/report.md", report("merged", "Merged: 2026-11-03 9d4cf45"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_no_approved_line_refuses(self):
        self.write("changes/bubble/plan.md", PLAN.replace("Approved: 2026-11-03\n", ""))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("no `Approved: <date>` line", out)

    def test_approved_without_a_date_refuses(self):
        self.write("changes/bubble/plan.md", PLAN.replace("Approved: 2026-11-03", "Approved: <date>"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("no `Approved: <date>` line", out)

    def test_unanswered_question_refuses(self):
        self.write("changes/bubble/plan.md", PLAN.replace("  Answer: yes, add it\n", ""))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("1 question(s) with no answer", out)
        self.assertIn("[core design] 01:", out)

    def test_placeholder_answer_counts_as_no_answer(self):
        self.write("changes/bubble/plan.md", PLAN.replace("yes, add it", "<Abdul's words>"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("no answer", out)

    def test_uncommitted_approval_refuses(self):
        self.write("changes/bubble/plan.md", PLAN.replace("Approved: 2026-11-03\n", ""))
        self.commit_all()
        self.write("changes/bubble/plan.md", PLAN)
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("`Approved:` line of changes/bubble/plan.md is not committed", out)

    def test_note_changed_after_approval_refuses(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Risk: row writes", "Risk: none"))
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("changed after the approval at", out)
        self.assertIn("  changes/bubble/02-order.md", out)
        self.commit_all("changed a note")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, "a committed change after the approval counts too")

    def test_test_file_changed_after_approval_refuses(self):
        self.write("e2e/order.spec.ts", "// changed\n")
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  e2e/order.spec.ts", out)

    def test_a_merged_notes_test_may_change_after_approval(self):
        # The run's own done-check edit, read by the note's reviewer.
        self.write("changes/bubble/report.md", report(s02="merged def5678"))
        self.write("e2e/order.spec.ts", "// the implementer renamed a label\n")
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_note_added_after_approval_refuses(self):
        self.write("changes/bubble/03-extra.md", NOTE_02.replace("# 02", "# 03"))
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  changes/bubble/03-extra.md", out)

    def test_report_and_other_files_may_change_after_approval(self):
        self.write("changes/bubble/report.md", report())
        self.write("src/a.ts", "export const a = 1;\n")
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_question_added_after_approval_refuses_until_approved_again(self):
        self.write("changes/bubble/plan.md", PLAN.replace(
            "\nApproved:", "- [migration] 02: a count column\n  Answer: it only adds\n\nApproved:"))
        self.commit_all("one more question")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  changes/bubble/plan.md", out)

    def test_a_new_approval_clears_a_changed_note(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Risk: row writes", "Risk: none"))
        self.write("changes/bubble/plan.md", PLAN + "Approved: 2026-11-04\n")
        self.commit_all("approved again")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("approved 2026-11-04", out)

    def test_a_note_stopped_on_a_question_is_the_short_interview_road(self):
        self.write("changes/bubble/report.md", report(s02="stopped: done check passes before the work"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("INTERVIEW: failed notes 02", out)

    def test_a_note_stopped_by_the_run_itself_is_not_the_interview_road(self):
        for state in ("stopped: API errors", "stopped: verifier returned no result", "stopped: worktree: Error"):
            self.write("changes/bubble/report.md", report(s02=state))
            self.commit_all()
            code, out = self.run_check("plan", "bubble")
            self.assertEqual(code, 0, (state, out))

    def test_failed_note_is_the_short_interview_road(self):
        self.write("changes/bubble/report.md", report(s02="failed"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2)
        self.assertIn("INTERVIEW: failed notes 02 in changes/bubble/report.md", out)

    def test_over_budget_needs_the_pruning_question(self):
        self.over_budget()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("550.0 s against a budget of 300 s, and changes/bubble/plan.md has no "
                      "`[pruning]` question", out)
        self.write("changes/bubble/plan.md", PLAN.replace(
            "\nApproved:", "- [pruning] suite: 550 s against 300 s\n  Answer: add a pruning note\n\nApproved:")
            + "Approved: 2026-11-03\n")
        self.commit_all("pruning, approved again")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("3 question(s)", out)

    def test_under_budget_needs_no_pruning_question(self):
        self.over_budget(over=False)
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_bad_feature_name_refuses(self):
        code, out = self.run_check("plan", "Bubble/../x")
        self.assertEqual(code, 3)
        self.assertIn("not a feature name", out)


class NotesRoad(Product):

    def test_notes_that_fail_today_are_clear(self):
        code, out = self.run_check("notes", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("note 01: ok (2 done check(s), 2 test file(s))", out)
        self.assertIn("note 02: ok (1 done check(s), 1 test file(s))", out)
        common = pathlib.Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        logs = list((common / "suite" / "logs").glob("*-plan-01.log"))
        self.assertEqual(len(logs), 1)
        self.assertIn("$ sh e2e/bubble.sh\nexit 1\n", logs[0].read_text())

    def test_done_check_that_passes_today_refuses(self):
        self.write("e2e/order.sh", "exit 0\n")
        code, out = self.run_check("notes", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("note 01: ok", out)
        self.assertIn("note 02: REFUSED changes/bubble/02-order.md\n  `sh e2e/order.sh` passes on "
                      "today's code, so it proves nothing about the work (the count shows on Order).", out)
        self.assertIn("REFUSED: 1 of 2 note(s)", out)

    def test_static_skips_running(self):
        self.write("e2e/order.sh", "exit 0\n")
        code, out = self.run_check("notes", "bubble", "--static")
        self.assertEqual(code, 0, out)
        self.assertIn("note 02: ok (1 done check(s), 1 test file(s), static)", out)

    def test_only_limits_the_notes(self):
        self.write("e2e/bubble.sh", "exit 0\n")
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 0, out)
        self.assertNotIn("note 01", out)
        code, out = self.run_check("notes", "bubble", "--only", "09")
        self.assertEqual(code, 3)
        self.assertIn("--only names 09, not in changes/bubble/", out)

    def test_missing_test_file_refuses(self):
        (self.tree / "e2e/order.spec.ts").unlink()
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("test file e2e/order.spec.ts does not exist", out)

    def test_done_check_naming_a_missing_test_side_file_refuses(self):
        self.write("changes/bubble/02-order.md",
                   NOTE_02.replace("sh e2e/order.sh", "npx playwright test e2e/count.spec.ts"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("names e2e/count.spec.ts, which does not exist", out)

    def test_no_tests_part_refuses(self):
        self.write("changes/bubble/02-order.md", NOTE_02.split("## Tests")[0])
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("no test file in `## Tests`", out)

    def test_screen_with_no_end_to_end_check_refuses(self):
        self.write("changes/bubble/02-order.md",
                   NOTE_02.replace("sh e2e/order.sh", "sh tests/bubble.sh"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("`Screens: Order` and no end-to-end done check", out)

    def test_screens_none_needs_no_end_to_end_check(self):
        self.write("changes/bubble/02-order.md",
                   NOTE_02.replace("sh e2e/order.sh", "sh tests/bubble.sh").replace("Screens: Order", "Screens: none"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 0, out)

    def test_spec_file_outside_e2e_is_end_to_end(self):
        self.write("tests/order.spec.ts", "// spec\n")
        self.write("tests/run.sh", "exit 1\n")
        self.write("changes/bubble/02-order.md",
                   NOTE_02.replace("sh e2e/order.sh", "sh tests/run.sh tests/order.spec.ts"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 0, out)

    def test_no_done_list_refuses(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("## Done", "## Checks"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("no `## Done` list. A done check is a command.", out)

    def test_done_line_that_is_not_a_command_refuses(self):
        self.write("changes/bubble/02-order.md",
                   NOTE_02.replace("- `sh e2e/order.sh`: the count shows on Order",
                                   "- `sh e2e/order.sh`: the count shows on Order\n- the count looks right"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("not a command with what a pass proves: `- the count looks right`", out)

    def test_missing_screens_or_risk_line_refuses(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Screens: Order\n", "").replace("Risk: row writes\n", ""))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("no `Screens:` line", out)
        self.assertIn("no `Risk:` line", out)

    def test_waits_for_a_note_not_in_the_folder_refuses(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Waits for: 01", "Waits for: 01, 04"))
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 3)
        self.assertIn("`Waits for: 04` names a note that is not in the folder", out)

    def test_cut_folder_is_not_a_note(self):
        self.write("changes/bubble/cut/03-old.md", NOTE_02.replace("# 02", "# 03"))
        code, out = self.run_check("notes", "bubble", "--static")
        self.assertEqual(code, 0, out)
        self.assertNotIn("note 03", out)

    def test_empty_folder_refuses(self):
        code, out = self.run_check("notes", "nothing")
        self.assertEqual(code, 3)
        self.assertIn("changes/nothing/ has no note", out)

    def test_one_note_change(self):
        self.write("changes/07-csv.md", NOTE_02.replace("# 02 Order page", "# 07 CSV").replace("Waits for: 01", "Waits for: none"))
        code, out = self.run_check("notes", "changes/07-csv.md")
        self.assertEqual(code, 0, out)
        self.assertIn("note 07: ok", out)

    def test_one_note_change_already_merged_refuses(self):
        self.write("changes/07-csv.md", NOTE_02.replace("# 02 Order page", "# 07 CSV\n\nMerged: 2026-11-02 abc1234"))
        code, out = self.run_check("notes", "changes/07-csv.md")
        self.assertEqual(code, 3)
        self.assertIn("`Merged: 2026-11-02 abc1234`: this change is already in main", out)

    def test_not_a_note_file_refuses(self):
        code, out = self.run_check("notes", "changes/bubble/plan.md")
        self.assertEqual(code, 3)
        self.assertIn("is not a note file", out)

    def test_over_budget_prints_the_pruning_notice(self):
        self.over_budget()
        code, out = self.run_check("notes", "bubble", "--static")
        self.assertEqual(code, 0, out)
        self.assertIn("PRUNING: the last full run took 550.0 s against a budget of 300 s. "
                      "The plan needs a `[pruning]` question.", out)

    def test_timeout_refuses(self):
        self.write("e2e/order.sh", "sleep 5\n")
        old = mod.TIMEOUT
        mod.TIMEOUT = 0.2
        try:
            code, out = self.run_check("notes", "bubble", "--only", "02")
        finally:
            mod.TIMEOUT = old
        self.assertEqual(code, 3)
        self.assertIn("did not finish in 0.2 s", out)


class Readers(unittest.TestCase):

    def test_read_note(self):
        note = mod.read_note(NOTE_01)
        self.assertEqual(note["title"], "01 Header bubble")
        self.assertEqual(note["screens"], "all signed-in")
        self.assertEqual(note["waits_for"], [])
        self.assertEqual(note["done"], [("sh e2e/bubble.sh", "the bubble opens on Home"),
                                        ("sh tests/bubble.sh", "the sheet keeps its text")])
        self.assertEqual(note["tests"], ["e2e/bubble.spec.ts", "tests/bubble.test.ts"])
        self.assertEqual(mod.read_note(NOTE_02)["waits_for"], ["01"])

    def test_read_plan(self):
        plan = mod.read_plan(PLAN)
        self.assertEqual(plan["approved"], "2026-11-03")
        self.assertEqual([q["kind"] for q in plan["questions"]], ["core design", "money or access rules"])
        self.assertEqual(plan["questions"][1]["answer"], "no, only the signed-in user's")

    def test_last_approved_line_wins(self):
        self.assertEqual(mod.read_plan(PLAN + "Approved: 2026-11-09\n")["approved"], "2026-11-09")

    def test_read_report(self):
        read = mod.read_report(report(s02="failed"))
        self.assertIsNone(read["merged"])
        self.assertEqual(read["states"], {"01": "merged abc1234", "02": "failed"})
        self.assertEqual(mod.read_report(None), {"merged": None, "states": {}})
        self.assertEqual(mod.read_report(report("merged", "Merged: 2026-11-03 9d4cf45"))["merged"],
                         "2026-11-03 9d4cf45")


if __name__ == "__main__":
    unittest.main()
