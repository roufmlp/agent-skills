#!/usr/bin/env python3
"""Cases for rulings.py: the `## Rulings` part of a feature plan, who rules a
question Abdul did not answer, and the commands that write a ruling.

    python3 test_rulings.py
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

    def test_a_second_ruled_line_does_not_put_another_name_on_the_ruling(self):
        # Review reproduction R09: the last `Ruled:` line won, so a second line with his name made it his.
        first = next(line for line in PLAN.splitlines() if line.strip().startswith("Ruled:"))
        entries, faults = entries_of(PLAN.replace(first, first + '\n  Ruled: 2026-11-12, Sam, "mine now"', 1))
        self.assertEqual(len(faults), 1)
        self.assertIn("has a `Ruled:` line already", faults[0])
        self.assertNotEqual(entries[0]["who"], "Sam")

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

    def test_a_merged_touched_note_needs_a_fix_note_of_its_own(self):
        # Review finding 10: note 02 keeps its own entry, and merged note 04 has no fix note.
        both = PLAN.replace("Touches: 02\n", "Touches: 02, 04\n")
        found = mod.faults(entries_of(both)[0], NUMBERS | {"04"}, "Sam", merged={"04"})
        self.assertTrue(any("04 are merged" in f and "fix note" in f for f in found), found)
        fixed = both.replace("- [money] 03", '- [follows 01] 05: the fix for merged note 04\n  Ruled: 2026-11-12, '
                             'default, "keep Reports"\n  Touches: none\n- [money] 03')
        self.assertEqual(mod.faults(entries_of(fixed)[0], NUMBERS | {"04", "05"}, "Sam", merged={"04"}), [])

    def test_two_merged_touched_notes_need_two_fix_notes(self):
        both = PLAN.replace("Touches: 02\n", "Touches: 04, 06\n").replace("[follows 01] 02", "[follows 01] 05")
        found = mod.faults(entries_of(both)[0], NUMBERS | {"04", "05", "06"}, "Sam", merged={"04", "06"})
        self.assertTrue(any("04, 06 are merged" in f and "the plan has 1" in f for f in found), found)

    def test_a_touched_note_that_merged_after_its_own_entry_holds(self):
        self.assertEqual(mod.faults(entries_of(PLAN)[0], NUMBERS, "Sam", merged={"02"}), [])

    def test_a_follow_on_carries_the_who_of_the_ruling_it_follows(self):
        found = self.faults(PLAN.replace('2026-11-12, default, "ruling on 01', '2026-11-12, Sam, "ruling on 01'))
        self.assertTrue(any("carries the who" in f for f in found), found)

    def test_a_third_default_on_one_notes_questions_refuses(self):
        # Review finding 12: a note that stops, takes a default and stops again has an end.
        more = "".join(f'- [none] 01: question {i}\n  Ruled: 2026-11-1{i}, default, "d{i}"\n  Touches: none\n'
                       for i in (3, 4))
        text = PLAN.replace("- [money] 03", more + "- [money] 03")
        found = self.faults(text)
        self.assertEqual(sum("took a default already" in f for f in found), 1, found)
        self.assertEqual(mod.MAX_DEFAULT_RULINGS, 2)

    def test_an_unknown_who_refuses(self):
        # Review finding 5: `Default` with a capital is nobody.
        found = self.faults(PLAN.replace('default, "keep', 'Default, "keep'))
        self.assertTrue(any("`Default` is not" in f for f in found), found)

    def test_an_overturned_entry_closes_only_on_a_fix_note_of_its_own(self):
        # Review finding 7: `Fix: 03` names an old note that follows nothing.
        text = PLAN.replace("  Undo: one line in the header component\n",
                            '  Undo: one line\n  Overturned: 2026-11-13, "Messages"\n  Fix: 03\n')
        self.assertTrue(any("never on an old note" in f for f in self.faults(text)), self.faults(text))

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

    BY_SAM = PLAN.replace("2026-11-12, default,", "2026-11-12, Sam,")

    def test_a_default_ruling_and_its_follow_on_wait_for_an_answer(self):
        # Review finding 2: a follow-on of a ruling by default is not free.
        self.assertEqual(self.open_(PLAN), ["01", "02"])

    def test_his_own_ruling_needs_no_answer_and_every_follow_on_does(self):
        # Review 2, N3: a follow-on in his name was free of the gate, and under it a note was
        # rewritten. A follow-on changes a note no question was about, so he sees it once.
        self.assertEqual(self.open_(self.BY_SAM), ["02"])
        confirmed = self.BY_SAM.replace('"ruling on 01: keep Reports"\n',
                                        '"ruling on 01: keep Reports"\n  Confirmed: 2026-11-13\n')
        self.assertEqual(self.open_(confirmed), [])

    def test_nobody_is_the_person_when_git_names_none(self):
        self.assertEqual(self.open_(self.BY_SAM, person=None), ["01", "02", "03"])

    def test_a_name_that_is_not_his_is_not_him(self):
        self.assertEqual(self.open_(PLAN.replace('default, "keep', 'Default, "keep')), ["01", "02"])

    def test_confirmed_closes_each_line_it_is_on(self):
        text = PLAN.replace("  Undo: one line in the header component\n", "  Undo: one line\n  Confirmed: 2026-11-13\n")
        self.assertEqual(self.open_(text), ["02"])
        self.assertEqual(self.open_(text.replace("  Touches: none\n- [money]",
                                                 "  Touches: none\n  Confirmed: 2026-11-13\n- [money]")), [])

    def test_overturned_closes_on_a_fix_note_that_follows_it(self):
        text = PLAN.replace("  Undo: one line in the header component\n",
                            '  Undo: one line\n  Overturned: 2026-11-13, "Messages"\n  Fix: 02\n')
        self.assertEqual(self.open_(text), ["02"])
        self.assertEqual(self.open_(text.replace("Fix: 02", "Fix: 03")), ["01", "02"])

    def test_a_risk_line_needs_its_own_words(self):
        mod_seam = mod.ruler_when_unanswered
        # As item 2 will answer: a panel rules the risk question he did not answer.
        mod.ruler_when_unanswered = lambda kind: "panel" if kind in mod.RISK_CLASSES else "default"
        try:
            text = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,")
            entries, _ = entries_of(text)
            self.assertEqual(mod.faults(entries, NUMBERS, "Sam"), [])
            self.assertEqual(self.open_(text), ["01", "02", "03"])
            bare = text.replace("  Undo: a migration\n", "  Undo: a migration\n  Confirmed: 2026-11-13\n")
            self.assertEqual(self.open_(bare), ["01", "02", "03"])
            own = bare.replace("Confirmed: 2026-11-13\n", 'Confirmed: 2026-11-13, "yes, no price"\n')
            self.assertEqual(self.open_(own), ["01", "02"])
        finally:
            mod.ruler_when_unanswered = mod_seam

    def test_a_class_nobody_knows_is_a_risk_class(self):
        # Review finding 5: `[data-leaving]` with a bare `Confirmed:` line stays open.
        text = PLAN.replace("[none] 01", "[data-leaving] 01").replace(
            "  Undo: one line in the header component\n", "  Undo: one line\n  Confirmed: 2026-11-13\n")
        self.assertIn("01", self.open_(text))

    def test_away_lines_open_a_risk_line_with_its_class_in_bold_capitals(self):
        text = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,")
        entries, _ = entries_of(text)
        lines = mod.away_lines(entries, "Sam")
        self.assertEqual(len(lines), 3)
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


def report_of(rows, decide=()):
    return "\n".join([
        "# Bubble report", "", "State: stopped", "", "## Notes", "",
        "| Note | State | Strikes | Attempts | Last report |", "| --- | --- | --- | --- | --- |",
        *[f"| {number} | {state} | 3 | 3 | /r/{number}.md |" for number, state in rows.items()],
        "", "## Decide", "", *(decide or ["none"]), ""])


SESSION = "feedbeef-0000-4000-8000-000000000000"


class Commands(unittest.TestCase):
    """The commands a session types. The row of the note decides what a
    ruling may be; the clock and the session's transcript decide who gives it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.tree = root / "product"
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
        self.records = self.tree / ".git" / "build-feature" / "bubble"
        self.clock = 1_000_000.0
        self.kept = (mod.now, mod.PROJECTS, os.environ.get(mod.SESSION))
        mod.now = lambda: self.clock
        mod.PROJECTS = root / "projects"
        os.environ[mod.SESSION] = SESSION
        self.records_written = []

    def tearDown(self):
        mod.now, mod.PROJECTS, session = self.kept
        if session is None:
            os.environ.pop(mod.SESSION, None)
        else:
            os.environ[mod.SESSION] = session
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(list(args))
        return code, out.getvalue()

    def command(self, name, *extra):
        return self.run_main(name, "bubble", "--tree", str(self.tree), "--date", "2026-11-12", *extra)

    def record(self, note, kind, who, words="w", question="q", touches="none"):
        return self.command("record", "--note", note, "--kind", kind, "--who", who, "--question", question,
                            "--words", words, "--touches", touches, "--undo", "one line")

    def rows(self, decide=(), **states):
        self.report.write_text(report_of({k.lstrip("n"): v for k, v in states.items()}, decide))

    def row(self, number):
        return mod.report_rows(self.report.read_text())[number]

    def typed(self, note, cls, question):
        """A stop as `feature_run.py roles` records it from the agent's transcript."""
        self.records.mkdir(parents=True, exist_ok=True)
        with open(self.records / mod.STOPS, "a") as fh:
            fh.write(json.dumps({"note": note, "kind": "question", "class": cls, "question": question}) + "\n")

    def says(self, text, at=None, **fields):
        """One record of this session's transcript; a human message unless `fields` say otherwise."""
        folder = mod.PROJECTS / "-product"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = mod.datetime.datetime.fromtimestamp(at if at is not None else self.clock,
                                                    mod.datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        rec = {"type": "user", "timestamp": stamp, "origin": {"kind": "human"},
               "message": {"role": "user", "content": text}, **fields}
        with open(folder / f"{SESSION}.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def later(self, seconds):
        self.clock += seconds

    # ── the seam and the person ──

    def test_person_is_the_first_word_of_the_git_user_name(self):
        self.assertEqual(mod.person(self.tree), "Sam")

    def test_ruler_prints_the_road_and_the_wait(self):
        self.assertEqual(self.run_main("ruler", "none"), (0, "default after 900 s\n"))
        self.assertEqual(self.run_main("ruler", "money"), (0, "wait\n"))

    # ── a failed note: one re-arm ──

    def test_record_writes_the_entry_before_the_approved_line_and_resets_the_row(self):
        code, out = self.record("01", "re-arm", "default", "the done check names the label Reports",
                                "note 01 failed three strikes")
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

    def test_a_default_on_a_failed_note_is_the_re_arm_and_nothing_else(self):
        # Review finding 8: three defaults of kind `none` on one failed note.
        code, out = self.record("01", "none", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("one re-arm", out)
        self.assertNotIn("## Rulings", self.plan.read_text())

    def test_record_refuses_a_second_re_arm(self):
        self.assertEqual(self.record("01", "re-arm", "default")[0], 0)
        self.rows(n01="failed")
        code, out = self.record("01", "re-arm", "default")
        self.assertEqual(code, 3)
        self.assertIn("a note gets one re-arm", out)
        self.assertEqual(self.plan.read_text().count("[re-arm]"), 1)

    def test_record_takes_the_readers_whole_touches_line(self):
        code, out = self.record("01", "re-arm", "default", touches="Touches: 02, 03")
        self.assertEqual(code, 0, out)
        self.assertEqual(entries_of(self.plan.read_text())[0][0]["touches"], ["02", "03"])
        self.assertIn("touched: 02, 03", out)

    # ── a note that did not stop, a merged note, a cut ──

    def test_a_note_that_did_not_stop_takes_no_ruling(self):
        code, out = self.record("02", "none", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("did not stop on a question", out)

    def test_record_refuses_a_merged_note_and_leaves_its_row(self):
        # Review finding 3: `record` set a merged row back to `not started`.
        self.rows(n01="merged abc123456", n02="failed")
        self.says("build it again")
        for who in ("default", "Sam"):
            code, out = self.record("01", "none", who, "build it again")
            self.assertEqual(code, 3, out)
            self.assertIn("a merged note is never edited or built again", out)
        self.assertEqual(self.row("01"), "merged abc123456")
        self.assertEqual(self.record("01", "follows 02", "default")[0], 3)

    def test_a_cut_is_his_ruling_and_the_row_stays_cut(self):
        # Review finding 9: `record` set the row `cut <date>` back to `not started`.
        self.rows(n01="not started", n02="cut 2026-11-12")
        code, out = self.record("02", "none", "default", "cut it")
        self.assertEqual(code, 3, out)
        self.assertIn("only Sam cuts a note", out)
        self.says("Cut it.")
        code, out = self.record("02", "none", "Sam", "cut it")
        self.assertEqual(code, 3, out)
        self.assertIn("was not put in front of Sam yet", out)
        self.assertEqual(self.command("wait", "--note", "02")[0], 0)
        self.assertEqual(self.record("02", "none", "Sam", "cut it")[0], 3, "typed before he was shown the row")
        self.later(30)
        self.says("Cut it.")
        code, out = self.record("02", "none", "Sam", "cut it")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), "cut 2026-11-12")

    def test_his_ruling_on_a_failed_row_needs_the_row_shown_first(self):
        self.says("Build it with the label Reports.")
        code, out = self.record("01", "none", "Sam", "build it with the label Reports")
        self.assertEqual(code, 3, out)
        self.assertIn("rulings.py wait bubble", out)
        code, out = self.command("wait", "--note", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("`failed` shown at", out)
        self.assertEqual(self.row("01"), "failed", "a row he is shown stays as it is")
        self.later(30)
        self.says("Build it with the label Reports.")
        code, out = self.record("01", "none", "Sam", "build it with the label Reports")
        self.assertEqual(code, 0, out)

    # ── a question: the class is the stop's, and the wait is real ──

    def test_the_class_is_the_one_the_agent_typed(self):
        # Review finding 4: a [money] stop recorded as [none] by default.
        question = "may a manager refund without the owner"
        self.rows(n02=f"stopped: {question}")
        self.typed("02", "money", question)
        code, out = self.record("02", "none", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("typed this stop of note 02 as [money]", out)
        code, out = self.record("02", "money", "default")
        self.assertEqual(code, 3, out)
        self.assertNotIn("## Rulings", self.plan.read_text())

    def test_a_stop_with_no_class_on_record_waits_for_him(self):
        self.rows(n02="stopped: an error nobody typed a class for")
        code, out = self.command("wait", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), "waiting: unclassified: an error nobody typed a class for")
        self.assertEqual(self.record("02", "none", "default")[0], 3)
        self.assertEqual(self.record("02", "none", "Sam")[0], 3)
        self.later(30)
        self.says("That is an access question. 02: keep the owner only.")
        code, out = self.record("02", "access", "Sam", "keep the owner only")
        self.assertEqual(code, 3, "a part of a sentence is not his answer")
        code, out = self.record("02", "access", "Sam", "02: keep the owner only")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), "not started")

    def test_wait_on_a_risk_question_sets_the_row_and_only_he_rules(self):
        question = "may a manager refund without the owner"
        self.rows(n02=f"stopped: {question}")
        self.typed("02", "money", question)
        code, out = self.command("wait", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), f"waiting: money: {question}")
        self.later(10 * mod.RULING_WAIT_SECONDS)
        code, out = self.record("02", "money", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("waits for Sam", out)
        self.assertEqual(self.record("02", "access", "Sam")[0], 3)

    def test_the_default_rules_only_after_the_wait(self):
        # Review finding 12: `record --who default` passed the second the stop was written.
        self.rows(n02="stopped: zero or hidden")
        self.typed("02", "none", "zero or hidden")
        code, out = self.record("02", "none", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("was not sent yet", out)
        code, out = self.command("wait", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("the default rules", out)
        self.assertEqual(self.row("02"), "stopped: zero or hidden")
        self.later(mod.RULING_WAIT_SECONDS - 1)
        code, out = self.record("02", "none", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("His answer rules until", out)
        self.later(1)
        self.assertEqual(self.command("wait", "--note", "02")[0], 0)  # a second send does not move the clock
        code, out = self.record("02", "none", "default")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), "not started")

    def test_the_pre_run_stop_is_class_none_with_no_record(self):
        self.rows(n02="stopped: done check passes before the work")
        self.assertEqual(self.command("wait", "--note", "02")[0], 0)
        self.later(mod.RULING_WAIT_SECONDS)
        self.assertEqual(self.record("02", "none", "default")[0], 0)

    def test_a_tool_fault_is_no_question(self):
        self.rows(n02="stopped: tooling: hook: REFUSED")
        self.assertEqual(self.record("02", "none", "default")[0], 3)
        code, out = self.command("wait", "--note", "02")
        self.assertEqual(code, 3, out)
        self.assertIn("asks him nothing", out)
        code, out = self.command("wait", "--note", "02", "--why", "tooling: hook: REFUSED")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), "waiting: tooling: hook: REFUSED")

    def test_two_defaults_on_one_notes_questions_then_it_waits(self):
        for i in (1, 2, 3):
            self.rows(n02=f"stopped: question {i}")
            self.typed("02", "none", f"question {i}")
            self.command("wait", "--note", "02")
            self.later(mod.RULING_WAIT_SECONDS)
            code, out = self.record("02", "none", "default", question=f"question {i}")
            self.assertEqual(code, 0 if i < 3 else 3, out)
        self.assertIn("took a default already", out)

    # ── the final check's question has a home ──

    def test_a_question_of_the_final_check_is_the_row_final(self):
        # Review finding 11: `--note final` was refused by `record` and by `wait`.
        code, out = self.record("final", "none", "default")
        self.assertEqual(code, 3, out)
        question = "may the fix change the price rounding"
        self.rows(n01="merged abc123456", final=f"stopped: {question}")
        self.typed("final", "money", question)
        code, out = self.command("wait", "--note", "final")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("final"), f"waiting: money: {question}")
        self.later(30)
        self.says("Final: round half up, as the invoices do.")
        code, out = self.record("final", "money", "Sam", "final: round half up, as the invoices do", question)
        self.assertEqual(code, 0, out)
        self.assertEqual(entries_of(self.plan.read_text())[0][0]["number"], "final")
        self.assertEqual(self.row("final"), "ruled 2026-11-12")

    def test_a_final_check_no_run_finishes_gets_its_row_from_wait(self):
        # Review 2, N8: with every note merged and no `final` row, nothing could make it wait.
        self.rows(n01="merged abc123456", n02="merged abc123456")
        self.assertEqual(self.command("wait", "--note", "final")[0], 3, "a row is added only with a reason")
        self.assertEqual(self.command("wait", "--note", "09", "--why", "tooling: x")[0], 3, "and only the row `final`")
        code, out = self.command("wait", "--note", "final", "--why", "tooling: the final check did not finish in three starts")
        self.assertEqual(code, 0, out)
        self.assertIn("| final | waiting: tooling: the final check did not finish in three starts | | | |",
                      self.report.read_text())
        self.assertEqual(self.row("02"), "merged abc123456")

    def test_a_finding_that_needs_a_fix_note_is_a_question_of_class_none(self):
        self.rows(n01="merged abc123456", final="stopped: fix note needed: the refund guard has no test")
        self.assertEqual(self.command("wait", "--note", "final")[0], 0)
        self.later(mod.RULING_WAIT_SECONDS)
        self.assertEqual(self.record("final", "none", "default", touches="none")[0], 0)

    # ── a correction by the note checker ──

    def test_a_correction_is_recorded_by_default_and_the_row_stays(self):
        # Review finding 1: a correction had no entry, so nothing held the merge.
        self.rows(["01: [correction] Corrected: the rights test grants the defaults back"], n01="merged abc123456")
        self.assertEqual(self.record("01", "correction", "panel")[0], 3)
        code, out = self.record("01", "correction", "default", "Corrected: the rights test grants the defaults back")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("01"), "merged abc123456")
        entries = entries_of(self.plan.read_text())[0]
        self.assertEqual([e["number"] for e in mod.open_entries(entries, "Sam")], ["01"])
        code, out = self.record("01", "correction", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("holds no correction of note 01 that the plan lacks", out)

    # ── his words ──

    def test_a_ruling_in_his_name_needs_words_he_typed_after_the_question_went_out(self):
        question = "may a manager refund without the owner"
        self.rows(n02=f"stopped: {question}")
        self.typed("02", "money", question)
        self.says("02: yes, up to 50", at=self.clock - 60)  # before the question: not an answer to it
        self.command("wait", "--note", "02")
        code, out = self.record("02", "money", "Sam", "02: yes, up to 50")
        self.assertEqual(code, 3, out)
        self.assertIn("no message Sam typed in this session after", out)
        self.later(30)
        self.says('02:  Yes, up to 50!\nAnd "no more" than that.')
        self.assertEqual(self.record("02", "money", "Sam", "yes, up to 50")[0], 3)
        code, out = self.record("02", "money", "Sam", "02: yes, up to 50")
        self.assertEqual(code, 0, out)

    def test_only_what_he_typed_counts_as_his_words(self):
        self.says("confirm all", isMeta=True)
        self.says("confirm all", origin={"kind": "task-notification"})
        self.says("confirm all", origin={"kind": "peer", "from": "a1"})
        self.says("confirm all", isSidechain=True)
        self.says([{"type": "tool_result", "content": "confirm all"}], origin=None)
        self.assertEqual(mod.human_messages(0.0), [])
        self.says([{"type": "text", "text": "confirm all"}])
        self.assertEqual([text for _, text in mod.human_messages(0.0)], ["confirm all"])
        self.assertEqual(mod.human_messages(self.clock), [], "a message counts only after the time given")

    def test_what_the_app_adds_to_a_message_is_not_his_words(self):
        # Review 2, N2: a `<system-reminder>` block and the text of a slash command counted.
        self.says([{"type": "text", "text": "<system-reminder>\nYou are operating in a git worktree.\n</system-reminder>"},
                   {"type": "text", "text": "hello"}])
        self.says("<command-message>build-feature</command-message>\n<command-name>/build-feature</command-name>\n"
                  "<command-args>bubble</command-args>")
        self.says("/build-feature bubble")
        self.says("/clear")
        self.assertEqual([text for _, text in mod.human_messages(0.0)], ["hello"])

    def test_his_words_are_a_whole_message_or_a_whole_sentence_of_one(self):
        self.assertEqual(mod.sentences("Look at the token cost, please. Confirm all!\nok"),
                         ["look at the token cost, please", "confirm all", "ok"])
        self.assertEqual(mod.spoken('  He said  "Yes".'), "he said 'yes'")
        self.assertTrue(mod.names_line("02: yes, up to 50", "02"))
        self.assertTrue(mod.names_line("yes for 2, up to 50", "02"))
        self.assertTrue(mod.names_line("final: round half up", "final"))
        self.assertFalse(mod.names_line("yes, up to 50", "02"))
        self.assertFalse(mod.names_line("yes for 12 and 20", "02"), "a digit inside another number names nothing")
        self.assertFalse(mod.names_line("02", "02"), "the number alone is no answer")

    def test_no_session_no_words(self):
        os.environ.pop(mod.SESSION)
        with self.assertRaises(mod.Refusal):
            mod.human_messages(0.0)
        os.environ[mod.SESSION] = "00000000-nowhere"
        with self.assertRaises(mod.Refusal):
            mod.human_messages(0.0)

    def test_one_sentence_answers_one_question(self):
        # Review 2, N2: "Default ok", typed once after two questions went out, ruled both.
        for number, question in (("01", "the label reads Reports or Messages"), ("02", "zero or hidden")):
            self.typed(number, "none", question)
        self.rows(n01="stopped: the label reads Reports or Messages", n02="stopped: zero or hidden")
        self.command("wait", "--note", "01")
        self.command("wait", "--note", "02")
        self.later(60)
        self.says("Default ok")
        self.assertEqual(self.record("01", "none", "Sam", "Default ok")[0], 0)
        code, out = self.record("02", "none", "Sam", "Default ok")
        self.assertEqual(code, 3, out)
        self.assertIn("it answered note 01: q already", out)
        self.assertEqual(self.row("02"), "stopped: zero or hidden")
        self.later(60)
        self.says("Default ok")
        self.assertEqual(self.record("02", "none", "Sam", "Default ok")[0], 0, "a second message is a second answer")

    def test_an_answer_typed_before_a_question_went_out_does_not_answer_it(self):
        self.typed("01", "none", "the label reads Reports or Messages")
        self.rows(n01="stopped: the label reads Reports or Messages", n02="not started")
        self.command("wait", "--note", "01")
        self.later(60)
        self.says("Default ok")
        self.later(60)
        self.typed("02", "none", "zero or hidden")
        self.rows(n01="stopped: the label reads Reports or Messages", n02="stopped: zero or hidden")
        self.command("wait", "--note", "02")
        code, out = self.record("02", "none", "Sam", "Default ok")
        self.assertEqual(code, 3, out)
        self.assertIn("(0 message(s) typed since)", out)

    def test_a_risk_question_takes_only_a_sentence_that_names_its_note(self):
        question = "may a manager refund without the owner"
        self.rows(n01="stopped: the label reads Reports or Messages", n02=f"stopped: {question}")
        self.typed("01", "none", "the label reads Reports or Messages")
        self.typed("02", "money", question)
        self.command("wait", "--note", "01")
        self.command("wait", "--note", "02")
        self.later(60)
        self.says("Default ok")
        code, out = self.record("02", "money", "Sam", "Default ok")
        self.assertEqual(code, 3, out)
        self.assertIn("does not name line 02", out)
        self.assertNotIn("## Rulings", self.plan.read_text())
        self.later(60)
        self.says("Default ok. 02: yes, up to 50.")
        self.assertEqual(self.record("01", "none", "Sam", "Default ok")[0], 0)
        self.assertEqual(self.record("02", "money", "Sam", "02: yes, up to 50")[0], 0,
                         "two sentences of one message answer two questions")

    def test_a_follow_on_in_his_name_carries_the_words_of_the_ruling_it_follows(self):
        # Review 2, N3: `record --kind "follows 02" --who Sam` took words he never typed.
        self.rows(n01="not started", n02="failed")
        self.command("wait", "--note", "02")
        self.later(30)
        self.says("Hide the count.")
        code, out = self.record("02", "none", "Sam", "hide the count", touches="01")
        self.assertEqual(code, 0, out)
        code, out = self.record("01", "follows 02", "Sam", "the bubble emails every user")
        self.assertEqual(code, 3, out)
        self.assertIn("carries the words of the ruling it follows, \"hide the count\"", out)
        code, out = self.record("01", "follows 02", "Sam", "Hide the count.", "the header shows no count at zero")
        self.assertEqual(code, 0, out)
        entries = entries_of(self.plan.read_text())[0]
        self.assertEqual([e["number"] for e in mod.open_entries(entries, "Sam")], ["01"],
                         "and he still sees the follow-on once, at the gate")

    # ── the answers at the gate ──

    def gate(self):
        self.rows(n01="merged abc123456", n02="merged abc123456", n03="not started")
        self.plan.write_text(PLAN.replace("2026-11-12, Sam,", "2026-11-12, default,").replace("[money] 03", "[none] 03"))

    def listed(self):
        """He is shown the gate list, and half a minute passes."""
        code, out = self.command("list")
        self.assertEqual(code, 0, out)
        self.later(30)
        return out

    def test_answer_needs_words_he_typed(self):
        self.gate()
        code, out = self.command("answer", "--all")
        self.assertEqual(code, 3, out)
        self.says("confirm all")
        code, out = self.command("answer", "--all", "--words", "confirm all")
        self.assertEqual(code, 3, out)
        self.assertIn("the list was not shown to Sam yet", out)
        self.listed()
        self.says("show me the list")
        code, out = self.command("answer", "--all", "--words", "confirm all")
        self.assertEqual(code, 3, out)
        self.assertIn("no message Sam typed in this session", out)
        self.assertNotIn("Confirmed:", self.plan.read_text())

    def test_words_inside_a_word_or_typed_before_the_list_are_no_answer(self):
        # Review 2, N2: "ok" passed because it is inside "look" and "token", "bubble" from the slash command.
        self.gate()
        self.says("<command-message>build-feature</command-message>\n<command-name>/build-feature</command-name>\n"
                  "<command-args>bubble</command-args>", at=self.clock - 5000)
        self.says("ok", at=self.clock - 4000)
        self.listed()
        self.says("look at the token cost please")
        self.says([{"type": "text", "text": "<system-reminder>confirm all</system-reminder>"}, {"type": "text", "text": "hm"}])
        for words in ("A", "ok", "bubble", "token cost", "confirm all"):
            code, out = self.command("answer", "--all", "--words", words)
            self.assertEqual(code, 3, f"{words}: {out}")
        self.assertNotIn("Confirmed:", self.plan.read_text())
        self.says("OK.")
        self.assertEqual(self.command("answer", "--all", "--words", "ok")[0], 0)

    def test_one_answer_closes_one_line_unless_it_is_confirm_all(self):
        self.gate()
        self.listed()
        self.says("yes")
        self.assertEqual(self.command("answer", "--note", "01", "--confirmed", "--words", "yes")[0], 0)
        code, out = self.command("answer", "--note", "02", "--confirmed", "--words", "yes")
        self.assertEqual(code, 3, out)
        self.assertIn("it answered line 01 of the gate list already", out)
        code, out = self.command("answer", "--all", "--words", "yes")
        self.assertEqual(code, 3, out)
        self.later(30)
        self.says("Confirm all.")
        code, out = self.command("answer", "--all", "--words", "confirm all")
        self.assertEqual(code, 0, out)
        self.assertIn("answered: 02, 03; 0 ruling(s) still wait", out)

    def test_answer_all_confirms_only_the_lines_outside_the_risk_classes(self):
        mod_seam = mod.ruler_when_unanswered
        mod.ruler_when_unanswered = lambda kind: "panel" if kind in mod.RISK_CLASSES else "default"
        try:
            self.rows(n01="merged abc123456", n02="merged abc123456", n03="not started")
            self.plan.write_text(PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,"))
            self.assertIn("for each line in bold one sentence that names its number", self.listed())
            self.says("Confirm all. ok")
            code, out = self.command("answer", "--all", "--words", "confirm all")
            self.assertEqual(code, 0, out)
            self.assertIn("answered: 01, 02; 1 ruling(s) still wait: 03", out)
            # Review 2, N2: the risk line closed on "ok", a word about nothing in particular.
            code, out = self.command("answer", "--note", "03", "--confirmed", "--words", "ok")
            self.assertEqual(code, 3, out)
            self.assertIn("does not name line 03", out)
            self.says("yes, no price")
            code, out = self.command("answer", "--note", "03", "--confirmed", "--words", "yes, no price")
            self.assertEqual(code, 3, out)
            self.says("03: yes, no price")
            code, out = self.command("answer", "--note", "03", "--confirmed", "--words", "03: yes, no price")
            self.assertEqual(code, 0, out)
            self.assertIn("0 ruling(s) still wait", out)
        finally:
            mod.ruler_when_unanswered = mod_seam

    def test_an_overturned_line_closes_only_on_a_new_fix_note(self):
        # Review finding 7: `--fix 01` named an old merged note and closed the gate.
        self.gate()
        self.listed()
        self.says("no, show Messages")
        args = ("answer", "--note", "01", "--overturned", "--words", "no, show Messages")
        self.assertEqual(self.command(*args)[0], 3)
        code, out = self.command(*args, "--fix", "03")
        self.assertEqual(code, 3, out)
        self.assertIn("never on an old note", out)
        (self.plan.parent / "04-messages.md").write_text("# fix note\n")
        code, out = self.record("04", "follows 01", "default", "show Messages")
        self.assertEqual(code, 0, out)
        self.rows(n01="merged abc123456", n02="merged abc123456", n03="not started", n04="merged abc123456")
        code, out = self.command(*args, "--fix", "04")
        self.assertEqual(code, 3, out)
        self.assertIn("a new fix note that the run still builds", out)
        self.rows(n01="merged abc123456", n02="merged abc123456", n03="not started", n04="not started")
        code, out = self.command(*args, "--fix", "04")
        self.assertEqual(code, 0, out)
        self.assertIn("still wait: 02, 03, 04", out)

    def test_list_prints_the_open_lines(self):
        self.gate()
        code, out = self.command("list")
        self.assertEqual(code, 0, out)
        self.assertIn("3 ruling(s) to confirm, of 3 he did not make himself", out)
        self.assertIn("- 01: the label reads Reports or Messages", out)
        self.assertIn("shown at", out)


if __name__ == "__main__":
    unittest.main()
