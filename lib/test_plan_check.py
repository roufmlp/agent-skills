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
        self.git("config", "user.name", "Sam Doe")
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

    def merge_note(self, number, path, text):
        """The merger's first step alone: the note's branch is in the feature, and nobody wrote the row."""
        self.git("checkout", "-qb", f"note/bubble/{number}")
        self.write(path, text)
        self.commit_all(f"note {number}")
        self.git("checkout", "-q", "feature/bubble")
        self.git("merge", "--no-ff", "-qm", f"merge note {number}", f"note/bubble/{number}")
        return self.git("rev-parse", "HEAD")

    def test_a_note_merged_in_git_is_merged_whatever_its_row_says(self):
        # The rehearsal of 2026-11-12: the merger merged the note and its edit of the row failed.
        self.write("changes/bubble/report.md", report(s02="not started"))
        self.commit_all("report: bubble running")
        self.merge_note("02", "e2e/order.spec.ts", "// the implementer renamed a label\n")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_git_changes_no_row_that_asks_waits_or_was_cut(self):
        merge = self.merge_note("02", "src/a.ts", "export const a = 1;\n")
        for state in ("not started", "running", "merged", "", "stopped: tooling: hook: the note check refused",
                      "stopped: worktree: the merge did not go through, and the note starts again in a new tree"):
            self.assertEqual(mod.with_merges(self.tree, "bubble", {"02": state}), {"02": f"merged {merge[:9]}"}, state)
        for state in ("merged abc1234", "cut 2026-11-12", "failed", "waiting: money: a question",
                      "stopped: may the count read every user's reports"):
            self.assertEqual(mod.with_merges(self.tree, "bubble", {"02": state}), {"02": state})
        self.assertEqual(mod.with_merges(self.tree, "bubble", {"01": "not started"}), {"01": "not started", "02": f"merged {merge[:9]}"},
                         "a note with no merge commit keeps its row, and a merged one with no row gets one")

    def test_a_merge_of_main_into_the_feature_is_no_note(self):
        self.git("checkout", "-q", "main")
        self.write("src/main.ts", "export const m = 1;\n")
        self.commit_all("a change on main")
        self.git("branch", "note/bubble/01", "feature/bubble")
        self.git("checkout", "-q", "feature/bubble")
        self.git("merge", "--no-ff", "-qm", "main-in", "main")
        self.assertEqual(mod.merged_in_git(self.tree, "bubble"), {})

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

    def test_a_note_stopped_on_a_question_is_the_ruling_road(self):
        self.write("changes/bubble/report.md", report(s02="stopped: done check passes before the work"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("RULING: notes 02 (stopped: done check passes before the work)", out)

    def test_a_note_stopped_by_the_run_itself_is_not_the_interview_road(self):
        for state in ("stopped: API errors", "stopped: verifier returned no result", "stopped: worktree: Error",
                      "stopped: tooling: hook: PreToolUse:Write hook error: an isolated git worktree"):
            self.write("changes/bubble/report.md", report(s02=state))
            self.commit_all()
            code, out = self.run_check("plan", "bubble")
            self.assertEqual(code, 0, (state, out))

    def test_failed_note_is_the_ruling_road(self):
        self.write("changes/bubble/report.md", report(s02="failed"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2)
        self.assertIn("RULING: notes 02 (failed) in changes/bubble/report.md", out)

    def test_a_note_that_waits_for_abdul_does_not_hold_the_other_notes(self):
        self.write("changes/bubble/report.md", report(s01="not started", s02="waiting: failed again after its re-arm"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("plan: approved", out)
        self.assertIn("waiting for Sam: 02", out)

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


RULING_02 = textwrap.dedent("""\
    ## Rulings

    - [none] 02: the count shows zero or hides at zero
      Ruled: 2026-11-12, default, "hide it at zero"
      Touches: none
      Undo: one line in the order page

""")


def ruled(part=RULING_02, plan=PLAN):
    return plan.replace("Approved: 2026-11-03", part + "Approved: 2026-11-03")


class Rulings(Product):
    """A ruling written after the approval covers the change it names."""

    def change_02(self):
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "the count, hidden at zero"))
        self.write("e2e/order.spec.ts", "// spec, hidden at zero\n")

    def test_a_ruled_line_covers_a_changed_note_and_its_test(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled())
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("plan: approved 2026-11-03", out)
        self.assertIn("1 ruling(s)", out)

    def test_a_screen_ruling_covers_the_screen_it_adds_and_waits_for_his_confirmation(self):
        # The listed repair of a hook's refusal (Abdul, 2026-11-13): the
        # session adds the screen and records it by default; the run goes on,
        # and he confirms the line at the gate like any ruling by default.
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Screens: Order", "Screens: Order, Reports"))
        self.write("changes/bubble/plan.md", ruled(RULING_02.replace(
            "[none] 02: the count shows zero or hides at zero",
            "[screen] 02: tooling: hook: REFUSED: src/app/reports/list.tsx is in the route folder of screen "
            "`Reports` (/reports), and note changes/bubble/02-order.md does not name it.").replace(
            '"hide it at zero"', '"add `Reports` to the Screens line"')))
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("1 ruling(s), 1 to confirm before the merge", out)

    def test_a_changed_note_with_no_ruled_line_still_refuses(self):
        self.change_02()
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("changed after the approval at", out)
        self.assertIn("  changes/bubble/02-order.md", out)
        self.assertIn("  e2e/order.spec.ts", out)

    def test_a_ruling_on_one_note_does_not_cover_another(self):
        self.write("changes/bubble/01-header.md", NOTE_01.replace("A bubble", "A round bubble"))
        self.write("changes/bubble/report.md", report(s01="not started"))
        self.write("changes/bubble/plan.md", ruled())
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  changes/bubble/01-header.md", out)
        self.assertNotIn("  changes/bubble/plan.md", out)

    def test_a_ruling_from_before_the_approval_covers_nothing_new(self):
        self.write("changes/bubble/plan.md", ruled() + "Approved: 2026-11-12\n")
        self.commit_all("ruled and approved again")
        self.change_02()
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  changes/bubble/02-order.md", out)

    def test_the_plan_may_change_only_in_its_rulings_part(self):
        self.write("changes/bubble/plan.md", ruled().replace("Answer: yes, add it", "Answer: no"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("  changes/bubble/plan.md", out)

    def test_a_ruled_line_with_no_touches_line_refuses_the_restart(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(RULING_02.replace("  Touches: none\n", "")))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("no `Touches:` line", out)

    def test_a_merged_note_is_never_edited_even_under_a_ruling(self):
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(s01=f"merged {merge}"))
        self.write("changes/bubble/01-header.md", NOTE_01.replace("A bubble", "A round bubble"))
        self.write("changes/bubble/plan.md", ruled(RULING_02.replace("] 02:", "] 01:")))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("changes/bubble/01-header.md", out)
        self.assertIn("a merged note is never edited", out)

    def test_a_note_ruled_and_then_merged_stays_covered(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled())
        self.commit_all("ruling: note 02")
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(s02=f"merged {merge}"))
        self.commit_all("report: note 02 merged")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_a_fix_note_passes_with_its_own_entry(self):
        fix = NOTE_02.replace("# 02 Order page", "# 03 Order count at zero").replace(
            "Waits for: 01", "Waits for: 02").replace("e2e/order", "e2e/zero")
        self.write("changes/bubble/03-zero.md", fix)
        self.write("e2e/zero.spec.ts", "// spec\n")
        self.write("e2e/zero.sh", "exit 1\n")
        self.commit_all("fix note")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, "an added note with no ruling refuses")
        part = RULING_02 .rstrip("\n") + textwrap.dedent("""
            - [follows 02] 03: the fix note for the count at zero
              Ruled: 2026-11-12, default, "ruling on 02: hide it at zero"
              Touches: none

            """)
        self.write("changes/bubble/plan.md", ruled(part))
        self.commit_all("ruling")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_a_touched_note_waits_for_the_ruled_note(self):
        part = textwrap.dedent("""\
            ## Rulings

            - [none] 01: the bubble opens a sheet or a page
              Ruled: 2026-11-12, default, "a sheet"
              Touches: 02
              Undo: one component
            - [follows 01] 02: the count sits in the sheet
              Ruled: 2026-11-12, default, "ruling on 01: a sheet"
              Touches: none

            """)
        self.write("changes/bubble/report.md", report(s01="not started"))
        self.write("changes/bubble/01-header.md", NOTE_01.replace("A bubble", "A bubble that opens a sheet"))
        self.write("changes/bubble/02-order.md", NOTE_02.replace("Waits for: 01", "Waits for: none"))
        self.write("changes/bubble/plan.md", ruled(part))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("note 02 follows the ruling on 01 and its `Waits for:` line does not name 01", out)
        self.write("changes/bubble/02-order.md", NOTE_02)
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)

    def test_a_default_may_not_rule_a_risk_class(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(RULING_02.replace("[none]", "[money]")))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3)
        self.assertIn("may not rule a [money] question", out)

    # ── a ruling by panel ──

    CONDITION = "e2e/order.spec.ts: the count hides at zero for staff"
    PANEL_02 = RULING_02.replace("[none]", "[money]").replace("default,", "panel,").replace(
        '"hide it at zero"\n', '"hide it at zero"\n  Panel: road A, 2 of 3, files 02-0123456789\n'
        f"  Condition: {CONDITION}\n")

    def change_02_with_its_condition(self):
        self.change_02()
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "the count, hidden at zero").replace(
            "the count shows on Order\n", f"the count shows on Order\n- `sh e2e/order.sh`: {self.CONDITION}\n"))

    def test_a_panel_ruling_needs_each_condition_among_the_notes_done_checks(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(self.PANEL_02))
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)
        self.assertIn("note 02 lacks a condition of its panel ruling", out)
        self.assertIn(self.CONDITION, out)

    def test_a_panel_ruling_whose_conditions_the_note_carries_passes(self):
        self.change_02_with_its_condition()
        self.write("changes/bubble/plan.md", ruled(self.PANEL_02))
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)

    def test_the_gate_shows_a_panel_ruling_in_its_full_form(self):
        self.change_02_with_its_condition()
        self.write("changes/bubble/plan.md", ruled(self.PANEL_02))
        self.commit_all("ruling: note 02")
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(state="held", s02=f"merged {merge}"))
        self.commit_all("held")
        folder = pathlib.Path(self.tree) / ".git" / "build-feature" / "bubble" / "panel" / "02-0123456789"
        folder.mkdir(parents=True)
        (folder / "finder.json").write_text(json.dumps({"need": "no price leaks", "offered": [], "found": []}))
        for seat in ("exposed", "operator"):
            (folder / f"{seat}.md").write_text("Rule: A\n\nStaff see no count they cannot act on.\n")
        (folder / "builder.md").write_text("Hold: how many orders have zero reports\n\nNobody counted them.\n")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("GATE: 1 ruling(s) Sam did not make wait for him", out)
        self.assertIn("**MONEY** 02: the count shows zero or hides at zero", out)
        self.assertIn("The count: road A, 2 of 3.", out)
        self.assertIn("exposed: Rule: A. Staff see no count they cannot act on.", out)
        self.assertIn("builder: Hold: how many orders have zero reports. Nobody counted them.", out)
        self.assertIn(f"Conditions: {self.CONDITION}.", out)

    # ── the gate before local main ──

    def held(self, part=RULING_02):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(part))
        self.commit_all("ruling: note 02")
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(state="held", s02=f"merged {merge}"))
        self.commit_all("held")

    def test_a_held_run_with_an_unanswered_ruling_is_the_gate_road(self):
        self.held()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("GATE: 1 ruling(s) Sam did not make wait for him", out)
        self.assertIn("02: the count shows zero or hides at zero", out)

    def test_a_confirmed_ruling_clears_the_gate(self):
        self.held(RULING_02.replace("  Undo:", "  Confirmed: 2026-11-13\n  Undo:"))
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("plan: approved", out)

    def test_a_run_that_is_not_held_goes_on_with_an_open_ruling(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled())
        self.write("changes/bubble/report.md", report(state="running"))
        self.commit_all()
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)

    # ── the commands, with a session he typed in ──

    def session(self):
        """This session's transcript, and a clock that moves ten seconds at each
        command and each message, so "typed after he was shown it" is exact."""
        import datetime
        import rulings
        if not hasattr(self, "transcript"):
            kept = (rulings.PROJECTS, os.environ.get(rulings.SESSION), rulings.now)
            self.clock = [datetime.datetime.now().timestamp()]
            rulings.PROJECTS = pathlib.Path(self.tmp.name) / "projects"
            rulings.now = lambda: self.clock[0]
            os.environ[rulings.SESSION] = "feedbeef-1111-4000-8000-000000000000"

            def restore():
                rulings.PROJECTS, rulings.now = kept[0], kept[2]
                os.environ.pop(rulings.SESSION, None) if kept[1] is None else os.environ.update({rulings.SESSION: kept[1]})
            self.addCleanup(restore)
            self.transcript = rulings.PROJECTS / "-product" / f"{os.environ[rulings.SESSION]}.jsonl"
            self.transcript.parent.mkdir(parents=True)
        self.clock[0] += 10
        return rulings

    def rule(self, *args):
        rulings = self.session()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rulings.main([args[0], "bubble", "--tree", str(self.tree), *args[1:]])
        return code, out.getvalue()

    def says(self, text):
        """One message he types in this session."""
        import datetime
        self.session()
        stamp = datetime.datetime.fromtimestamp(self.clock[0], datetime.timezone.utc).isoformat()
        with open(self.transcript, "a") as fh:
            fh.write(json.dumps({"type": "user", "timestamp": stamp, "origin": {"kind": "human"},
                                 "message": {"role": "user", "content": text}}) + "\n")

    def test_the_whole_road_through_the_commands_the_skill_names(self):
        """A failed note and its re-arm with a touched note, a risk question he
        answers, the restart, the held run, and at the gate one confirmed line
        and one overturned line with its fix note: each step through the
        command a session types, and the plan check after each."""
        question = "may the bubble show a price"
        self.write("changes/bubble/report.md", report(state="stopped", s01=f"stopped: {question}", s02="failed"))
        self.commit_all("report: stopped")
        self.assertEqual(self.run_check("plan", "bubble")[0], 2)
        # Note 01 stopped on a question no agent typed a class for: it waits for him, and he rules it.
        self.assertEqual(self.rule("wait", "--note", "01")[0], 0)
        self.assertEqual(self.rule("record", "--note", "01", "--kind", "none", "--who", "default", "--question",
                                   question, "--words", "no", "--touches", "none", "--undo", "x")[0], 3)
        self.says("That is a money question. 01: no price on the bubble, ever.")
        code, out = self.rule("record", "--note", "01", "--kind", "money", "--who", "Sam", "--question", question,
                              "--words", "01: no price on the bubble, ever", "--touches", "none", "--undo", "a migration")
        self.assertEqual(code, 0, out)
        self.write("changes/bubble/01-header.md", NOTE_01.replace("A bubble", "A bubble with no price"))
        self.commit_all("ruling: note 01")
        # Note 02 failed: its one re-arm by default.
        self.change_02()
        code, out = self.rule("record", "--note", "02", "--kind", "re-arm", "--who", "default",
                              "--question", "note 02 failed three strikes", "--words", "hide the count at zero",
                              "--touches", "Touches: none", "--undo", "one line in the order page")
        self.assertEqual(code, 0, out)
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("2 ruling(s), 1 to confirm before the merge", out)
        # The run builds both notes and holds.
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(state="held", s01=f"merged {merge}", s02=f"merged {merge}"))
        self.commit_all("report: bubble held")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("GATE: 1 ruling(s)", out)
        self.assertNotIn("01: may the bubble", out, "his own ruling needs no answer")
        self.assertIn("02: note 02 failed three strikes", self.rule("list")[1])
        # He overturns it. The line closes only on a new fix note, which is then his to confirm.
        self.says("no, show the zero")
        overturn = ("answer", "--note", "02", "--overturned", "--words", "no, show the zero")
        self.assertEqual(self.rule(*overturn, "--fix", "01")[0], 3)
        fix = NOTE_02.replace("# 02 Order page", "# 03 The zero shows").replace(
            "Waits for: 01", "Waits for: 02").replace("e2e/order", "e2e/zero")
        self.write("changes/bubble/03-zero.md", fix)
        self.write("e2e/zero.spec.ts", "// spec\n")
        self.write("e2e/zero.sh", "exit 1\n")
        code, out = self.rule("record", "--note", "03", "--kind", "follows 02", "--who", "default", "--question",
                              "the fix note for the overturned ruling on 02", "--words", "show the zero",
                              "--touches", "none", "--undo", "one line")
        self.assertEqual(code, 0, out)
        code, out = self.rule(*overturn, "--fix", "03")
        self.assertEqual(code, 0, out)
        self.commit_all("rulings: answered")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("03: the fix note for the overturned ruling", out)
        self.assertIn("03: the fix note for the overturned ruling", self.rule("list")[1])
        self.says("Confirm all.")
        self.assertEqual(self.rule("answer", "--all", "--words", "confirm all")[0], 0)
        self.commit_all("rulings: answered")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertNotIn("to confirm", out)

    def test_a_cut_under_his_ruling_passes_and_stays_cut(self):
        # Review finding 9: the cut's `## Cut` line refused the plan, and `record` undid the row.
        self.write("changes/bubble/report.md", report(s01="not started", s02="failed"))
        self.commit_all("report")
        os.makedirs(self.tree / "changes/bubble/cut")
        self.git("mv", "changes/bubble/02-order.md", "changes/bubble/cut/02-order.md")
        self.git("rm", "-q", "e2e/order.spec.ts")
        cut = PLAN.replace("Approved: 2026-11-03", "## Cut\n\n02 Order page, cut 2026-11-12: Sam cut it\n\nApproved: 2026-11-03")
        self.write("changes/bubble/plan.md", cut)
        self.write("changes/bubble/report.md", report(s01="not started", s02="cut 2026-11-12"))
        self.commit_all("cut")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, "a cut with no ruling of his refuses")
        self.assertEqual(self.rule("wait", "--note", "02")[0], 0)
        self.says("Cut it. It goes to the next feature.")
        code, out = self.rule("record", "--note", "02", "--kind", "none", "--who", "Sam", "--question",
                              "note 02 failed three strikes", "--words", "cut it", "--touches", "none", "--undo", "x")
        self.assertEqual(code, 0, out)
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("| 02 | cut 2026-11-12 |", (self.tree / "changes/bubble/report.md").read_text())

    def test_his_cut_of_a_note_an_earlier_ruling_touches_passes(self):
        # Review 2, N10: `Touches: 01` on his ruling, then he cut note 01, and every tool
        # refused "names no other note of the feature".
        import feature_run
        self.follow_on("Sam", "01")
        os.makedirs(self.tree / "changes/bubble/cut")
        self.git("mv", "changes/bubble/01-header.md", "changes/bubble/cut/01-header.md")
        text = (self.tree / "changes/bubble/plan.md").read_text()
        self.write("changes/bubble/plan.md", text.replace(
            "Approved: 2026-11-03", "## Cut\n\n01 Header, cut 2026-11-12: Sam cut it\n\nApproved: 2026-11-03"))
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "the count, hidden at zero").replace(
            "Waits for: 01", "Waits for: none"))
        self.write("changes/bubble/report.md", report(s01="cut 2026-11-12", s02="not started"))
        self.assertEqual(self.rule("wait", "--note", "01")[0], 0)
        self.says("Cut note 01.")
        code, out = self.rule("record", "--note", "01", "--kind", "none", "--who", "Sam", "--question", "cut note 01",
                              "--words", "cut note 01", "--touches", "none", "--undo", "x")
        self.assertEqual(code, 0, out)
        self.commit_all("ruling: note 01")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        got = feature_run.build_args("bubble", self.tree, [], None, "2026-11-12 09:00")
        self.assertEqual([(n["number"], n["state"]) for n in got["notes"]],
                         [("01", "cut 2026-11-12"), ("02", "not started")])

    def test_the_commit_line_record_prints_takes_the_tests_of_the_ruling(self):
        # Review 2, N7: the line was `git add changes/<feature>`, the test edit stayed out of
        # the commit, and the plan check then refused it for ever.
        self.write("changes/bubble/report.md", report(state="stopped", s02="failed"))
        self.commit_all("report: failed")
        self.change_02()
        code, out = self.rule("record", "--note", "02", "--kind", "re-arm", "--who", "default",
                              "--question", "note 02 failed three strikes", "--words", "hide the count at zero",
                              "--touches", "none", "--undo", "x")
        self.assertEqual(code, 0, out)
        line = [text for text in out.splitlines() if text.startswith("commit it: ")][0][len("commit it: "):]
        self.assertIn("e2e/order.spec.ts", line)
        subprocess.run(line, shell=True, check=True, capture_output=True)
        self.assertEqual(self.git("status", "--porcelain"), "", "the one commit took every file of the ruling")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("plan: approved", out)

    def test_the_last_commit_line_of_a_ruling_takes_the_tests_of_the_notes_that_follow_it(self):
        self.write("changes/bubble/report.md", report(state="stopped", s01="not started", s02="failed"))
        self.commit_all("report: failed")
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "the count, hidden at zero").replace(
            "Waits for: 01", "Waits for: none"))
        self.write("e2e/order.spec.ts", "// spec, hidden at zero\n")
        self.write("changes/bubble/01-header.md", NOTE_01.replace("A bubble", "A bubble with no count at zero").replace(
            "Waits for: none", "Waits for: 02"))
        self.write("tests/bubble.test.ts", "// the header test, with no count at zero\n")
        fields = ("--who", "default", "--words", "hide the count at zero", "--undo", "x")
        code, out = self.rule("record", "--note", "02", "--kind", "re-arm", "--question", "note 02 failed three strikes",
                              "--touches", "01", *fields)
        self.assertEqual(code, 0, out)
        code, out = self.rule("record", "--note", "01", "--kind", "follows 02", "--question", "the header shows no count",
                              "--touches", "none", *fields)
        self.assertEqual(code, 0, out)
        line = [text for text in out.splitlines() if text.startswith("commit it: ")][0][len("commit it: "):]
        subprocess.run(line, shell=True, check=True, capture_output=True)
        self.assertEqual(self.git("status", "--porcelain"), "")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 0, out)
        self.assertIn("2 ruling(s), 2 to confirm before the merge", out)

    def test_a_cut_line_for_a_note_he_did_not_rule_on_refuses(self):
        self.write("changes/bubble/plan.md", ruled(RULING_02).replace(
            "Approved: 2026-11-03", "## Cut\n\n02 Order page, cut 2026-11-12: nobody asked\n\nApproved: 2026-11-03"))
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)
        self.assertIn("  changes/bubble/plan.md", out)

    # ── what a ruling covers ──

    OWNER_02 = RULING_02.replace("default", "Sam")

    def test_a_later_edit_of_a_ruled_note_is_refused(self):
        # Review finding 6: a ruling covered its note and tests for ever.
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(self.OWNER_02))
        self.commit_all("ruling: note 02")
        self.assertEqual(self.run_check("plan", "bubble")[0], 0)
        self.write("e2e/order.spec.ts", "// every assertion removed, days later, no new ruling\n")
        self.commit_all("a later edit")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)
        self.assertIn("e2e/order.spec.ts (changed after the commit that applied the ruling on note 02", out)

    def test_an_edit_nobody_committed_is_not_covered(self):
        self.change_02()
        self.write("changes/bubble/plan.md", ruled(self.OWNER_02))
        self.commit_all("ruling: note 02")
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "something else"))
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)

    def test_a_test_two_notes_name_needs_a_ruling_for_each(self):
        # Review finding 6: note 01's test, weakened under a ruling on note 02.
        self.write("changes/bubble/report.md", report(s01="not started", s02="not started"))
        self.write("changes/bubble/02-order.md", NOTE_02.replace("`e2e/order.spec.ts`", "`e2e/order.spec.ts` and `tests/bubble.test.ts`"))
        self.write("tests/bubble.test.ts", "// note 01's test, weakened\n")
        self.write("changes/bubble/plan.md", ruled(self.OWNER_02))
        self.commit_all("ruling: note 02")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)
        self.assertIn("tests/bubble.test.ts (also named by note 01, which no ruling covers)", out)

    # ── a follow-on ──

    def follow_on(self, who, touches, weaken=False, new_test=False):
        """His ruling on 02, and an edit to note 01 that rides on `[follows 02] 01`."""
        self.write("changes/bubble/report.md", report(s01="not started", s02="not started"))
        part = self.OWNER_02.replace("Touches: none", f"Touches: {touches}").rstrip("\n") + textwrap.dedent(f"""
            - [follows 02] 01: anything at all
              Ruled: 2026-11-12, {who}, "a new rule nobody asked for"
              Touches: none
              Undo: unknown

            """)
        self.write("changes/bubble/plan.md", ruled(part))
        self.write("changes/bubble/02-order.md", NOTE_02.replace("the report count", "the count, hidden at zero").replace(
            "Waits for: 01", "Waits for: none"))
        note = NOTE_01.replace("A bubble", "A bubble that also emails every user").replace(
            "Waits for: none", "Waits for: 02")
        if new_test:
            self.assertIn("`e2e/bubble.spec.ts` and `tests/bubble.test.ts`", note)
            note = note.replace("`e2e/bubble.spec.ts` and `tests/bubble.test.ts`", "`tests/new.test.ts`")
            self.write("tests/new.test.ts", "// asserts nothing\n")
        self.write("changes/bubble/01-header.md", note)
        if weaken:
            self.write("tests/bubble.test.ts", "// weakened\n")
        self.commit_all("ruling: note 02 and what follows")
        return self.run_check("plan", "bubble")

    def test_a_follow_on_by_default_under_his_ruling_refuses(self):
        # Review finding 2, as the reviewer wrote it.
        code, out = self.follow_on("default", "none", weaken=True)
        self.assertEqual(code, 3, out)
        self.assertIn("a follow-on carries the who of the ruling it follows", out)

    def test_a_follow_on_his_touches_line_does_not_name_waits_for_him(self):
        code, out = self.follow_on("Sam", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)

    def test_a_follow_on_in_his_name_waits_for_him_though_his_ruling_names_the_note(self):
        # Review 2, N3: under such an entry note 01 was rewritten and nothing waited for him.
        code, out = self.follow_on("Sam", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)

    def test_a_follow_on_that_weakens_a_test_waits_for_him(self):
        code, out = self.follow_on("Sam", "01", weaken=True)
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)

    def test_a_follow_on_that_swaps_the_approved_tests_for_an_empty_one_holds_the_gate(self):
        # Review 2, N3: the note's Tests part named a new empty test, the approved test files
        # stayed as they were, and the guard on weakened tests saw nothing.
        code, out = self.follow_on("Sam", "01", new_test=True)
        self.assertEqual(code, 0, out)
        self.assertIn("1 to confirm before the merge", out)
        merge = self.git("rev-parse", "HEAD")[:9]
        self.write("changes/bubble/report.md", report(state="held", s01=f"merged {merge}", s02=f"merged {merge}"))
        self.commit_all("report: bubble held")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("GATE: 1 ruling(s)", out)
        self.assertIn("01: anything at all", out)

    # ── an overturned line, a correction ──

    def test_an_overturned_line_with_an_old_fix_note_does_not_hold(self):
        # Review finding 7, on the page: `Fix: 01` names a merged note that follows nothing.
        self.held(RULING_02.replace("  Undo:", '  Overturned: 2026-11-13, "no, show the zero"\n  Fix: 01\n  Undo:'))
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 3, out)
        self.assertIn("never on an old note", out)

    def test_a_correction_nobody_recorded_is_the_ruling_road(self):
        # Review finding 1: a correction by the note checker reached main with no line at the gate.
        decide = "\n## Decide\n\n01: [correction] Corrected: the rights test grants the defaults back\n"
        self.write("changes/bubble/report.md", report(state="held") + decide)
        self.commit_all("report: bubble held")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("RULING: notes 01 (corrected by the note checker", out)
        code, out = self.rule("record", "--note", "01", "--kind", "correction", "--who", "default", "--question",
                              "the note checker corrected note 01", "--words", "the rights test grants the defaults back",
                              "--touches", "none", "--undo", "one test")
        self.assertEqual(code, 0, out)
        self.commit_all("ruling: note 01")
        code, out = self.run_check("plan", "bubble")
        self.assertEqual(code, 2, out)
        self.assertIn("GATE: 1 ruling(s)", out)

    # ── the session's folder ──

    def test_a_session_in_its_own_worktree_of_the_repo_refuses(self):
        other = self.tree / ".claude" / "worktrees" / "trusting-boyd"
        self.git("worktree", "add", "-q", str(other), "-b", "app/session", "main")
        here = os.getcwd()
        try:
            os.chdir(other)
            code, out = self.run_check("plan", "bubble")
            self.assertEqual(code, 3, out)
            self.assertIn("this session's folder is the worktree", out)
            self.assertIn("main checkout", out)
            os.chdir(self.tree)
            code, out = self.run_check("plan", "bubble")
            self.assertEqual(code, 0, out)
        finally:
            os.chdir(here)


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

    def test_no_done_check_runs_before_work_that_git_shows_merged(self):
        # The same rehearsal: the row read `not started`, so the session named the merged note in
        # `--only`, its done check passed, and the note stopped as "done check passes before the work".
        self.git("checkout", "-qb", "note/bubble/02")
        self.write("e2e/order.sh", "exit 0\n")
        self.commit_all("note 02")
        self.git("checkout", "-q", "feature/bubble")
        self.git("merge", "--no-ff", "-qm", "merge note 02", "note/bubble/02")
        merge = self.git("rev-parse", "HEAD")
        code, out = self.run_check("notes", "bubble", "--only", "02")
        self.assertEqual(code, 0, out)
        self.assertIn(f"note 02: merged into feature/bubble at {merge[:9]}", out)
        self.assertNotIn("passes on today's code", out)

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
        self.assertEqual(mod.read_report(None), {"merged": None, "state": None, "states": {}})
        self.assertEqual(mod.read_report(report("held"))["state"], "held")
        self.assertEqual(mod.read_report(report("merged", "Merged: 2026-11-03 9d4cf45"))["merged"],
                         "2026-11-03 9d4cf45")


if __name__ == "__main__":
    unittest.main()
