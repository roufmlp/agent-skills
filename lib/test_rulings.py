#!/usr/bin/env python3
"""Cases for rulings.py: the `## Rulings` part of a feature plan, who rules a
question Abdul did not answer, and the commands that write a ruling.

    python3 test_rulings.py
"""

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulings as mod  # noqa: E402

PLAN = textwrap.dedent("""\
    # Bubble plan

    Feature: bubble

    ## Questions

    - [core design] 01: the bubble is a new pattern
      Answer: yes, add it

    ## Rulings

    - [none] 01: the label reads Reports or Messages
      Ruled: 2026-11-12, default, "keep Reports, as the core design names it"
      Touches: 02
      Undo: one line in the header component
    - [follows 01] 02: the count uses the label note 01 keeps
      Ruled: 2026-11-12, default, "ruling on 01: keep Reports"
      Touches: none
    - [money] 03: the count may show a price
      Ruled: 2026-11-12, Sam, "no price on the bubble"
      Touches: none
      Undo: a migration

    Approved: 2026-11-03
""")

REPORT = textwrap.dedent("""\
    # Bubble report

    State: stopped

    ## Notes

    | Note | State | Strikes | Attempts | Last report |
    | --- | --- | --- | --- | --- |
    | 01 | failed | 3 | 3 | /r/01-attempt-3-reviewer.md |
    | 02 | not started | 0 | 0 | |

    ## Roles

    | Role | Model | Effort | Tokens | Cost | Strikes |
    | --- | --- | --- | --- | --- | --- |
    | implementer | sonnet | high | | | 3 |
""")

NUMBERS = {"01", "02", "03"}


def entries_of(text):
    entries, faults = mod.read(text)
    return entries, faults


class Seam(unittest.TestCase):

    def test_the_wait_is_one_named_constant(self):
        self.assertEqual(mod.RULING_WAIT_SECONDS, 900)

    def test_the_default_rules_a_question_outside_the_risk_classes(self):
        self.assertEqual(mod.ruler_when_unanswered("none"), "default")
        self.assertEqual(mod.ruler_when_unanswered("re-arm"), "default")

    def test_a_risk_question_waits_for_abdul(self):
        for kind in ("money", "access", "migration", "data leaving"):
            self.assertEqual(mod.ruler_when_unanswered(kind), "wait", kind)

    def test_an_unknown_class_waits(self):
        self.assertEqual(mod.ruler_when_unanswered("pricing"), "wait")


class Reading(unittest.TestCase):

    def test_reads_each_entry(self):
        entries, faults = entries_of(PLAN)
        self.assertEqual(faults, [])
        self.assertEqual([e["number"] for e in entries], ["01", "02", "03"])
        one, two, three = entries
        self.assertEqual(one["kind"], "none")
        self.assertEqual(one["who"], "default")
        self.assertEqual(one["date"], "2026-11-12")
        self.assertEqual(one["words"], "keep Reports, as the core design names it")
        self.assertEqual(one["touches"], ["02"])
        self.assertEqual(one["undo"], "one line in the header component")
        self.assertEqual(two["follows"], "01")
        self.assertEqual(two["touches"], [])
        self.assertEqual(three["who"], "Sam")

    def test_a_plan_with_no_rulings_part_has_no_entry(self):
        entries, faults = entries_of("# Plan\n\n## Questions\n\nApproved: 2026-11-03\n")
        self.assertEqual((entries, faults), ([], []))

    def test_a_line_it_cannot_place_is_a_fault(self):
        text = PLAN.replace("  Undo: a migration\n", "  Undo: a migration\n  Maybe: later\n")
        _, faults = entries_of(text)
        self.assertEqual(len(faults), 1)
        self.assertIn("Maybe: later", faults[0])

    def test_a_ruled_line_outside_the_part_is_a_fault(self):
        text = PLAN.replace("## Questions\n", '## Questions\n\nRuled: 2026-11-12, default, "x"\n')
        _, faults = entries_of(text)
        self.assertTrue(any("outside `## Rulings`" in f for f in faults), faults)

    def test_the_part_ends_at_the_approved_line(self):
        outside = mod.outside(PLAN)
        self.assertIn("Approved: 2026-11-03", outside)
        self.assertIn("Answer: yes, add it", outside)
        self.assertNotIn("Ruled:", outside)
        self.assertNotIn("## Rulings", outside)

    def test_outside_is_the_same_text_with_and_without_the_part(self):
        bare = PLAN.split("## Rulings")[0] + "Approved: 2026-11-03\n"
        self.assertEqual(mod.outside(PLAN), mod.outside(bare))


class Faults(unittest.TestCase):

    def faults(self, text, person="Sam"):
        entries, found = entries_of(text)
        return found + mod.faults(entries, NUMBERS, person)

    def test_the_fixture_is_clean(self):
        self.assertEqual(self.faults(PLAN), [])

    def test_a_ruled_line_with_no_touches_line_refuses(self):
        text = PLAN.replace("  Touches: 02\n", "")
        found = self.faults(text)
        self.assertEqual(len(found), 1, found)
        self.assertIn("no `Touches:` line", found[0])
        self.assertIn("01", found[0])

    def test_an_entry_with_no_ruled_line_refuses(self):
        text = PLAN.replace('  Ruled: 2026-11-12, Sam, "no price on the bubble"\n', "")
        self.assertTrue(any("no `Ruled:` line" in f for f in self.faults(text)))

    def test_touches_must_name_notes_of_the_feature(self):
        found = self.faults(PLAN.replace("Touches: 02", "Touches: 02, 09"))
        self.assertTrue(any("`Touches: 09`" in f for f in found), found)

    def test_a_touched_note_needs_its_own_entry(self):
        text = PLAN.replace("Touches: 02", "Touches: 02, 03")
        found = self.faults(text)
        self.assertTrue(any("note 03" in f and "follows 01" in f for f in found), found)

    def test_an_unknown_kind_refuses(self):
        found = self.faults(PLAN.replace("[none] 01", "[pricing] 01"))
        self.assertTrue(any("[pricing]" in f for f in found), found)

    def test_a_name_that_is_not_the_person_refuses(self):
        found = self.faults(PLAN.replace("default, \"keep", "defualt, \"keep"))
        self.assertTrue(any("`defualt`" in f for f in found), found)

    def test_the_default_may_not_rule_a_risk_class(self):
        found = self.faults(PLAN.replace("2026-11-12, Sam,", "2026-11-12, default,"))
        self.assertEqual(len(found), 1, found)
        self.assertIn("[money]", found[0])
        self.assertIn("waits for Sam", found[0])

    def test_a_follow_on_takes_the_class_of_its_first_ruling(self):
        text = PLAN.replace("[none] 01", "[access] 01").replace(
            '2026-11-12, default, "keep', '2026-11-12, Sam, "keep')
        found = self.faults(text)
        self.assertTrue(any("02" in f and "[access]" in f for f in found), found)

    def test_a_merged_touched_note_needs_a_fix_note_in_its_place(self):
        entries, _ = entries_of(PLAN.replace("[follows 01] 02", "[follows 01] 04"))
        found = mod.faults(entries, NUMBERS | {"04"}, "Sam", merged={"02"})
        self.assertEqual(found, [])
        entries, _ = entries_of(PLAN)
        found = mod.faults(entries, NUMBERS, "Sam", merged={"02"})
        self.assertTrue(any("note 02 is merged" in f and "fix note" in f for f in found), found)

    def test_follows_must_name_a_ruled_note(self):
        found = self.faults(PLAN.replace("[follows 01] 02", "[follows 07] 02"))
        self.assertTrue(any("follows 07" in f for f in found), found)

    def test_a_note_gets_one_re_arm(self):
        text = PLAN.replace("[none] 01", "[re-arm] 01")
        again = text.replace("\nApproved:", textwrap.dedent("""\
            - [re-arm] 01: note 01 failed three strikes again
              Ruled: 2026-11-13, default, "change the done check"
              Touches: none

            Approved:"""), 1)
        found = self.faults(again)
        self.assertTrue(any("one re-arm" in f for f in found), found)

    def test_both_answers_on_one_entry_refuse(self):
        text = PLAN.replace("  Undo: one line in the header component\n",
                            "  Undo: one line\n  Confirmed: 2026-11-13\n"
                            '  Overturned: 2026-11-13, "no"\n  Fix: 02\n')
        self.assertTrue(any("both" in f for f in self.faults(text)))

    def test_an_overturned_entry_names_its_fix_note(self):
        text = PLAN.replace("  Undo: one line in the header component\n",
                            '  Undo: one line\n  Overturned: 2026-11-13, "Messages"\n')
        found = self.faults(text)
        self.assertTrue(any("no `Fix:` line" in f for f in found), found)
        fixed = text.replace('"Messages"\n', '"Messages"\n  Fix: 09\n')
        self.assertTrue(any("`Fix: 09`" in f for f in self.faults(fixed)))


class Gate(unittest.TestCase):

    def open_(self, text, person="Sam"):
        entries, _ = entries_of(text)
        return [e["number"] for e in mod.open_entries(entries, person)]

    def test_a_default_ruling_waits_for_an_answer(self):
        self.assertEqual(self.open_(PLAN), ["01"])

    def test_a_ruling_by_the_person_needs_none(self):
        text = PLAN.replace('default, "keep Reports', 'Sam, "keep Reports')
        self.assertEqual(self.open_(text), [])

    def test_a_follow_on_is_answered_with_its_first_ruling(self):
        self.assertNotIn("02", self.open_(PLAN))

    def test_confirmed_closes_it(self):
        text = PLAN.replace("  Undo: one line in the header component\n",
                            "  Undo: one line\n  Confirmed: 2026-11-13\n")
        self.assertEqual(self.open_(text), [])

    def test_overturned_with_a_fix_note_closes_it(self):
        text = PLAN.replace("  Undo: one line in the header component\n",
                            '  Undo: one line\n  Overturned: 2026-11-13, "Messages"\n  Fix: 02\n')
        self.assertEqual(self.open_(text), [])

    def test_a_risk_line_needs_its_own_words(self):
        mod_seam = mod.ruler_when_unanswered
        # As item 2 will answer: a panel rules the risk question he did not answer.
        mod.ruler_when_unanswered = lambda kind: "panel" if kind in mod.RISK_CLASSES else "default"
        try:
            text = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,")
            entries, _ = entries_of(text)
            self.assertEqual(mod.faults(entries, NUMBERS, "Sam"), [])
            self.assertEqual(self.open_(text), ["01", "03"])
            bare = text.replace("  Undo: a migration\n", "  Undo: a migration\n  Confirmed: 2026-11-13\n")
            self.assertEqual(self.open_(bare), ["01", "03"])
            own = bare.replace("Confirmed: 2026-11-13\n", 'Confirmed: 2026-11-13, "yes, no price"\n')
            self.assertEqual(self.open_(own), ["01"])
        finally:
            mod.ruler_when_unanswered = mod_seam

    def test_away_lines_open_a_risk_line_with_its_class_in_bold_capitals(self):
        text = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,")
        entries, _ = entries_of(text)
        lines = mod.away_lines(entries, "Sam")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("**MONEY** 03:"), lines[0])
        self.assertIn("Ruled by panel on 2026-11-12", lines[0])
        self.assertIn("Undo: a migration", lines[0])
        self.assertTrue(lines[1].startswith("01:"), lines[1])
        self.assertIn("Touched: 02", lines[1])
        self.assertIn('"keep Reports, as the core design names it"', lines[1])

    def test_new_entries_since_an_older_page(self):
        older = PLAN.replace(textwrap.dedent("""\
            - [money] 03: the count may show a price
              Ruled: 2026-11-12, Sam, "no price on the bubble"
              Touches: none
              Undo: a migration
            """), "")
        now, _ = entries_of(PLAN)
        then, _ = entries_of(older)
        self.assertEqual(mod.new_since(now, then), {"03"})


class Commands(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = pathlib.Path(self.tmp.name)
        folder = self.tree / "changes" / "bubble"
        folder.mkdir(parents=True)
        self.plan = folder / "plan.md"
        self.report = folder / "report.md"
        self.plan.write_text(PLAN.split("## Rulings")[0] + "Approved: 2026-11-03\n")
        self.report.write_text(REPORT)
        for name in ("01-header.md", "02-order.md", "03-price.md"):
            (folder / name).write_text("# note\n")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.tree, check=True)
        subprocess.run(["git", "config", "user.name", "Sam Doe"], cwd=self.tree, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(list(args))
        return code, out.getvalue()

    def record(self, *extra):
        return self.run_main("record", "bubble", "--tree", str(self.tree), "--date", "2026-11-12", *extra)

    def test_person_is_the_first_word_of_the_git_user_name(self):
        self.assertEqual(mod.person(self.tree), "Sam")

    def test_ruler_prints_the_road_and_the_wait(self):
        self.assertEqual(self.run_main("ruler", "none"), (0, "default after 900 s\n"))
        self.assertEqual(self.run_main("ruler", "money"), (0, "wait\n"))

    def test_record_writes_the_entry_before_the_approved_line_and_resets_the_row(self):
        code, out = self.record("--note", "01", "--kind", "re-arm", "--who", "default",
                                "--question", "note 01 failed three strikes",
                                "--words", "the done check names the label Reports",
                                "--touches", "none", "--undo", "one line")
        self.assertEqual(code, 0, out)
        text = self.plan.read_text()
        self.assertLess(text.index("## Rulings"), text.index("Approved: 2026-11-03"))
        self.assertTrue(text.rstrip().endswith("Approved: 2026-11-03"))
        entries, faults = entries_of(text)
        self.assertEqual(faults, [])
        self.assertEqual(entries[0]["kind"], "re-arm")
        self.assertEqual(entries[0]["words"], "the done check names the label Reports")
        self.assertIn("| 01 | not started | 0 | 3 | /r/01-attempt-3-reviewer.md |", self.report.read_text())
        self.assertIn("| 02 | not started | 0 | 0 | |", self.report.read_text())
        self.assertIn("| implementer | sonnet | high | | | 3 |", self.report.read_text())
        self.assertIn("git -C", out)

    def test_record_appends_to_an_existing_part(self):
        self.record("--note", "01", "--kind", "none", "--who", "default", "--question", "q1",
                    "--words", "w1", "--touches", "none", "--undo", "u")
        code, out = self.record("--note", "03", "--kind", "money", "--who", "Sam", "--question", "q3",
                                "--words", "w3", "--touches", "none", "--undo", "u")
        self.assertEqual(code, 0, out)
        text = self.plan.read_text()
        self.assertEqual(text.count("## Rulings"), 1)
        self.assertEqual([e["number"] for e in entries_of(text)[0]], ["01", "03"])

    def test_record_takes_the_readers_whole_touches_line(self):
        code, out = self.record("--note", "01", "--kind", "none", "--who", "default", "--question", "q1",
                                "--words", "w1", "--touches", "Touches: 02, 03", "--undo", "u")
        self.assertEqual(code, 0, out)
        self.assertEqual(entries_of(self.plan.read_text())[0][0]["touches"], ["02", "03"])
        self.assertIn("touched: 02, 03", out)

    def test_record_refuses_a_default_on_a_risk_class_and_writes_nothing(self):
        before = self.plan.read_text()
        code, out = self.record("--note", "03", "--kind", "money", "--who", "default", "--question", "q",
                                "--words", "w", "--touches", "none", "--undo", "u")
        self.assertEqual(code, 3)
        self.assertIn("REFUSED", out)
        self.assertEqual(self.plan.read_text(), before)
        self.assertIn("| 01 | failed | 3 |", self.report.read_text())

    def test_record_refuses_a_second_re_arm(self):
        args = ("--note", "01", "--kind", "re-arm", "--who", "default", "--question", "q",
                "--words", "w", "--touches", "none", "--undo", "u")
        self.assertEqual(self.record(*args)[0], 0)
        code, out = self.record(*args)
        self.assertEqual(code, 3)
        self.assertIn("one re-arm", out)

    def test_wait_sets_the_row(self):
        code, out = self.run_main("wait", "bubble", "--tree", str(self.tree), "--note", "01",
                                  "--why", "failed again after its re-arm")
        self.assertEqual(code, 0, out)
        self.assertIn("| 01 | waiting: failed again after its re-arm | 3 | 3 |", self.report.read_text())

    def test_answer_all_confirms_only_the_lines_outside_the_risk_classes(self):
        self.plan.write_text(PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,"))
        seam = mod.ruler_when_unanswered
        mod.ruler_when_unanswered = lambda kind: "panel" if kind in mod.RISK_CLASSES else "default"
        try:
            code, out = self.run_main("answer", "bubble", "--tree", str(self.tree), "--all", "--date", "2026-11-13")
            self.assertEqual(code, 0, out)
            entries, _ = entries_of(self.plan.read_text())
            self.assertEqual([e["number"] for e in mod.open_entries(entries, "Sam")], ["03"])
            code, out = self.run_main("answer", "bubble", "--tree", str(self.tree), "--note", "03",
                                      "--confirmed", "--words", "yes, no price", "--date", "2026-11-13")
            self.assertEqual(code, 0, out)
            entries, _ = entries_of(self.plan.read_text())
            self.assertEqual(mod.open_entries(entries, "Sam"), [])
        finally:
            mod.ruler_when_unanswered = seam

    def test_answer_overturned_needs_the_fix_note(self):
        self.plan.write_text(PLAN)
        code, out = self.run_main("answer", "bubble", "--tree", str(self.tree), "--note", "01",
                                  "--overturned", "--words", "Messages", "--date", "2026-11-13")
        self.assertEqual(code, 3)
        self.assertIn("--fix", out)
        code, out = self.run_main("answer", "bubble", "--tree", str(self.tree), "--note", "01",
                                  "--overturned", "--words", "Messages", "--fix", "02", "--date", "2026-11-13")
        self.assertEqual(code, 0, out)
        self.assertIn('  Overturned: 2026-11-13, "Messages"\n  Fix: 02\n', self.plan.read_text())

    def test_list_prints_the_open_lines(self):
        self.plan.write_text(PLAN)
        code, out = self.run_main("list", "bubble", "--tree", str(self.tree))
        self.assertEqual(code, 0)
        self.assertIn("1 ruling(s) to confirm", out)
        self.assertIn("01: the label reads Reports or Messages", out)
        self.assertNotIn("03:", out)


if __name__ == "__main__":
    unittest.main()
