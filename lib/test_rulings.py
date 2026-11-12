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
import shutil
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

# What `record --who panel` adds to an entry: the count, and each condition of the readers it counted.
PANEL_LINE = ("  Panel: road B, 2 of 3, files 03-0123456789\n"
              "  Condition: e2e/price.spec.ts: the bubble shows no price to staff\n")

# A risk question's written default, and the road finder's typed answer to it.
DEFAULT = "keep the old column and add a nullable one"
FINDER = {
    "need": "old rows stay readable while the new code ships",
    "default_cost": "one more column to drop in a later migration",
    "offered": [{"road": "drop the column in this migration", "cost": "a rollback leaves a shape the old code cannot read"}],
    "found": [
        {"road": "add a view that both shapes read", "files": ["db/migrations/0097_owner_view.sql"],
         "evidence": ["src/orders/read.ts:41", "db/migrations/0090_orders.sql:12"],
         "beats": "no code reads the column by name", "fails": "a report that selects every column breaks",
         "undo": "drop the view", "needs_owner_fact": ""},
        {"road": "backfill in production first", "files": ["scripts/backfill.mjs"], "evidence": ["scripts/backfill.mjs:3"],
         "beats": "no row is left without an owner", "fails": "it cannot run before the release",
         "undo": "none after it ran", "needs_owner_fact": "the count of rows with no owner in production"},
    ],
}
REASON = "The old shape stays readable. A rollback needs no backfill. Third sentence."


def vote_text(first, *conditions, reason=REASON):
    """One reader's file: the vote on line 1, the reason, then its conditions."""
    return "\n".join([first, "", reason, "", *[f"Condition: {c}" for c in conditions]]) + "\n"



def entries_of(text):
    entries, faults = mod.read(text)
    return entries, faults


class Seam(unittest.TestCase):

    def test_the_wait_is_one_named_constant(self):
        self.assertEqual(mod.RULING_WAIT_SECONDS, 900)

    def test_the_default_rules_a_question_outside_the_risk_classes(self):
        self.assertEqual(mod.ruler_when_unanswered("none"), "default")
        self.assertEqual(mod.ruler_when_unanswered("re-arm"), "default")

    def test_a_panel_rules_a_risk_question_he_did_not_answer(self):
        for kind in ("money", "access", "migration", "data leaving"):
            self.assertEqual(mod.ruler_when_unanswered(kind), "panel", kind)

    def test_an_unknown_class_and_a_stop_with_no_class_wait(self):
        self.assertEqual(mod.ruler_when_unanswered("pricing"), "wait")
        self.assertEqual(mod.ruler_when_unanswered("unclassified"), "wait")
        self.assertEqual(mod.ruler_when_unanswered(""), "wait")


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
        self.assertIn("The `panel` rules it", found[0])

    def test_a_panel_may_not_rule_outside_the_risk_classes(self):
        found = self.faults(PLAN.replace('default, "keep Reports, as', 'panel, "keep Reports, as'))
        self.assertTrue(any("`panel` may not rule a [none] question" in f for f in found), found)

    def test_a_ruling_by_panel_carries_its_panel_line(self):
        text = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,")
        found = self.faults(text)
        self.assertEqual(len(found), 1, found)
        self.assertIn("no `Panel:` line", found[0])
        counted = text.replace('"no price on the bubble"\n', '"no price on the bubble"\n' + PANEL_LINE)
        self.assertEqual(self.faults(counted), [])
        entry = entries_of(counted)[0][2]
        self.assertEqual(entry["panel"], {"count": "road B, 2 of 3", "files": "03-0123456789"})
        self.assertEqual(entry["conditions"], ["e2e/price.spec.ts: the bubble shows no price to staff"])
        # The folder name goes into a path, so the page may name a note number and a key and nothing else.
        _, found = entries_of(counted.replace("files 03-0123456789", "files ../../03-0123456789"))
        self.assertEqual(len(found), 1, found)
        self.assertIn("is not a ruling line", found[0])
        mine = PLAN.replace('"no price on the bubble"\n', '"no price on the bubble"\n' + PANEL_LINE)
        self.assertTrue(any("`Panel:` line" in f and "panel" in f for f in self.faults(mine)), self.faults(mine))

    def test_a_note_takes_two_rulings_without_him_whoever_gave_them(self):
        text = PLAN.replace("- [money] 03", "- [money] 01: may the label show a price\n"
                            '  Ruled: 2026-11-12, panel, "no price"\n' + PANEL_LINE.replace("03-", "01-") +
                            "  Touches: none\n- [access] 01: may staff see it\n"
                            '  Ruled: 2026-11-12, panel, "owner only"\n' + PANEL_LINE.replace("03-", "01-") +
                            "  Touches: none\n- [money] 03")
        found = self.faults(text)
        self.assertEqual(len(found), 1, found)
        self.assertIn("without Sam already", found[0])

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
        self.assertEqual(sum("without Sam already" in f for f in found), 1, found)
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

    BY_PANEL = PLAN.replace("2026-11-12, Sam,", "2026-11-12, panel,").replace(
        '"no price on the bubble"\n', '"no price on the bubble"\n' + PANEL_LINE)

    def test_a_risk_line_needs_its_own_words(self):
        text = self.BY_PANEL
        entries, _ = entries_of(text)
        self.assertEqual(mod.faults(entries, NUMBERS, "Sam"), [])
        self.assertEqual(self.open_(text), ["01", "02", "03"])
        bare = text.replace("  Undo: a migration\n", "  Undo: a migration\n  Confirmed: 2026-11-13\n")
        self.assertEqual(self.open_(bare), ["01", "02", "03"])
        own = bare.replace("Confirmed: 2026-11-13\n", 'Confirmed: 2026-11-13, "yes, no price"\n')
        self.assertEqual(self.open_(own), ["01", "02"])

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


class Panel(unittest.TestCase):
    """The road finder's answer, one reader's file and the counting rule. No agent is the judge."""

    def roads(self, **changes):
        return mod.read_roads(DEFAULT, {**FINDER, **changes})

    def count(self, *texts):
        roads = self.roads()
        votes = {seat: mod.read_vote(text, roads) for seat, text in zip(mod.SEATS, texts)}
        return mod.count(votes), votes

    def test_the_three_seats_are_fixed(self):
        self.assertEqual(list(mod.SEATS), ["exposed", "operator", "builder"])
        self.assertIn("lets through a read, a write or a wrong result that a narrower road refuses", mod.SEATS["exposed"][1])
        self.assertIn("runs the production migration by hand", mod.SEATS["operator"][1])
        self.assertIn("a guard loosened", mod.SEATS["operator"][1])
        self.assertIn("a check that can no longer go red", mod.SEATS["builder"][1])

    def test_each_road_has_a_fixed_id(self):
        roads = self.roads()
        self.assertEqual([(r["id"], r["kind"]) for r in roads],
                         [("A", "default"), ("B", "offered"), ("F1", "found"), ("F2", "found")])
        self.assertEqual(roads[0]["road"], DEFAULT)
        self.assertEqual(roads[1]["road"], "drop the column in this migration")
        self.assertEqual(roads[2]["evidence"], ["src/orders/read.ts:41", "db/migrations/0090_orders.sql:12"])
        self.assertEqual(roads[3]["needs_owner_fact"], "the count of rows with no owner in production")

    def test_no_better_road_is_a_full_answer(self):
        self.assertEqual([r["id"] for r in self.roads(found=[])], ["A", "B"])
        self.assertEqual([r["id"] for r in self.roads(found=[], offered=[])], ["A"])

    def test_a_finder_answer_outside_the_typed_form_is_refused(self):
        one = FINDER["found"][0]
        for changes, says in (
            ({"found": [one, one, one]}, "at most 2"),
            ({"found": [{**one, "evidence": ["the orders code"]}]}, "file:line"),
            ({"found": [{**one, "evidence": []}]}, "evidence"),
            ({"found": [{k: v for k, v in one.items() if k != "undo"}]}, "undo"),
            ({"found": [{k: v for k, v in one.items() if k != "needs_owner_fact"}]}, "needs_owner_fact"),
            ({"found": "none"}, "list"),
            ({"need": ""}, "need"),
        ):
            with self.assertRaises(mod.Refusal) as caught:
                self.roads(**changes)
            self.assertIn(says, str(caught.exception), changes)
        with self.assertRaises(mod.Refusal):
            mod.read_roads(DEFAULT, ["not", "an", "object"])

    def test_two_or_three_readers_on_one_road_rule_it(self):
        result, _ = self.count("Rule: B", "Rule: A", "Rule: B")
        self.assertEqual((result["outcome"], result["road"], result["seats"]), ("road", "B", ["exposed", "builder"]))
        self.assertEqual(result["mark"], "road B, 2 of 3")
        result, _ = self.count("Rule: A", "Rule: A", "Rule: A")
        self.assertEqual((result["outcome"], result["road"], result["mark"]), ("road", "A", "road A, 3 of 3"))

    def test_a_found_road_needs_two_of_three_like_any_other(self):
        result, _ = self.count("Rule: F1", "Hold: the count of open orders", "Rule: F1")
        self.assertEqual((result["outcome"], result["road"]), ("road", "F1"))
        result, _ = self.count("Rule: F1", "Rule: A", "Rule: B")
        self.assertEqual((result["outcome"], result["road"]), ("default", "A"))

    def test_two_or_three_holds_and_no_road_rules(self):
        result, votes = self.count("Hold: the count of open orders", "Rule: B",
                                   "Hold: whether the old app still reads the column")
        self.assertEqual((result["outcome"], result["road"], result["seats"]), ("hold", None, ["exposed", "builder"]))
        self.assertEqual(votes["builder"]["fact"], "whether the old app still reads the column")
        self.assertEqual(self.count("Hold: a", "Hold: b", "Hold: c")[0]["outcome"], "hold")

    def test_when_no_two_agree_the_written_default_rules_and_is_marked(self):
        result, _ = self.count("Rule: B", "Hold: the count of open orders", "Rule: A")
        self.assertEqual((result["outcome"], result["road"], result["seats"]), ("default", "A", ["builder"]))
        self.assertIn("the readers disagreed", result["mark"])

    def test_a_malformed_first_line_is_no_vote(self):
        roads = self.roads()
        for text in ("**Rule: B**", "Rule B", "rule: B", "Rule: B, because it is narrow", "Rule:B", "\nRule: B",
                     "My answer.\nRule: B", "Rule: Z", "Hold:", "", "Rule: B or A"):
            vote = mod.read_vote(text, roads)
            self.assertIsNone(vote["kind"], text)
            self.assertTrue(vote["why"], text)
        result, _ = self.count("Rule: B", "I rule B.\nRule: B", "Rule: B")
        self.assertEqual((result["outcome"], result["mark"]), ("road", "road B, 2 of 3"))
        result, _ = self.count("Rule: B", "Rule B", "Rule B")
        self.assertEqual((result["outcome"], result["road"], result["seats"]), ("default", "A", []))

    def test_a_road_that_needs_a_fact_from_him_never_rules(self):
        result, votes = self.count("Rule: F2", "Rule: F2", "Rule: F2")
        self.assertEqual((result["outcome"], result["road"]), ("default", "A"))
        self.assertIsNone(votes["exposed"]["kind"])
        self.assertIn("needs a fact", votes["exposed"]["why"])
        result, _ = self.count("Rule: F2", "Rule: F2", "Rule: B")
        self.assertEqual((result["outcome"], result["road"]), ("default", "A"))

    def test_a_reader_gives_its_reason_and_two_conditions_at_most(self):
        vote = mod.read_vote(vote_text("Rule: B", "a.test.ts: one", "b.test.ts: two", "c.test.ts: three"), self.roads())
        self.assertEqual((vote["kind"], vote["road"]), ("rule", "B"))
        self.assertEqual(vote["reason"], REASON)
        self.assertEqual(vote["conditions"], ["a.test.ts: one", "b.test.ts: two"])
        self.assertEqual(mod.read_vote(vote_text("Hold: the count of open orders"), self.roads())["conditions"], [])


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

    def typed(self, note, cls, question, default=""):
        """A stop as `feature_run.py roles` records it from the agent's transcript."""
        self.records.mkdir(parents=True, exist_ok=True)
        with open(self.records / mod.STOPS, "a") as fh:
            fh.write(json.dumps({"note": note, "kind": "question", "class": cls, "question": question,
                                 "default": default}) + "\n")

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
        self.assertEqual(self.run_main("ruler", "money"), (0, "panel after 900 s\n"))
        self.assertEqual(self.run_main("ruler", "unclassified"), (0, "wait\n"))

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

    # ── the panel: a risk question he did not answer ──

    QUESTION = "may the migration drop the old owner column"

    def risk_stop(self, note="02", cls="migration", default=DEFAULT, waited=True):
        """A note stopped on a typed question that went out; returns the panel's folder for that stop."""
        self.rows(**{f"n{note}": f"stopped: {self.QUESTION}"})
        self.typed(note, cls, self.QUESTION, default)
        code, out = self.command("wait", "--note", note)
        self.assertEqual(code, 0, out)
        if waited:
            self.later(mod.RULING_WAIT_SECONDS)
        return mod.panel_dir(mod.Feature(str(self.tree), "bubble"), note, self.QUESTION)

    def panel_files(self, folder, *votes, finder=FINDER):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / mod.FINDER).write_text(json.dumps(finder))
        for seat, text in zip(mod.SEATS, votes):
            (folder / f"{seat}.md").write_text(text)

    def ran(self, note="02", model="claude-opus-5-5", skip=()):
        """The transcripts of the panel's agents, as this session's subagents hold them."""
        folder = mod.PROJECTS / "-product" / SESSION / "subagents"
        folder.mkdir(parents=True, exist_ok=True)
        agents = {"finder": "workflow:build-feature-road-finder",
                  **{seat: "workflow:panel-review-persona" for seat in mod.SEATS}}
        for name, kind in agents.items():
            for path in folder.glob(f"agent-{name}.*"):
                path.unlink()
            if name in skip:
                continue
            label = f"panel {note}: finder" if name == "finder" else f"panel {note}: reader {name}"
            (folder / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": kind, "description": label}))
            (folder / f"agent-{name}.jsonl").write_text(json.dumps(
                {"type": "assistant", "message": {"model": model, "usage": {"input_tokens": 10, "output_tokens": 5}}}) + "\n")

    def by_panel(self, words, note="02", cls="migration"):
        return self.record(note, cls, "panel", words, question=self.QUESTION)

    def test_the_panel_command_walks_the_finder_the_readers_and_the_count(self):
        folder = self.risk_stop(waited=False)
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 3, out)
        self.assertIn("His answer rules until", out)
        self.later(mod.RULING_WAIT_SECONDS)
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("workflow:build-feature-road-finder", out)
        self.assertIn('"panel 02: finder"', out)
        brief = (folder / "finder.brief.md").read_text()
        for part in ("Class: migration", f"Question: {self.QUESTION}", f"Written default: {DEFAULT}",
                     str(folder / mod.FINDER)):
            self.assertIn(part, brief)
        self.panel_files(folder)
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("workflow:panel-review-persona", out)
        self.assertIn("model opus", out)
        for seat in mod.SEATS:
            self.assertIn(f'"panel 02: reader {seat}"', out)
            brief = (folder / f"{seat}.brief.md").read_text()
            self.assertIn(mod.SEATS[seat][1].format(who="Sam"), brief)
            self.assertIn(f"A (the written default): {DEFAULT}", brief)
            self.assertIn("F1 (a road the question did not offer): add a view that both shapes read", brief)
            self.assertIn("src/orders/read.ts:41", brief)
            self.assertIn("No reader rules this road", brief)
            self.assertIn("Rule: <road id>", brief)
            self.assertIn(str(folder / f"{seat}.md"), brief)
        self.assertIn("Sam on release day", (folder / "operator.brief.md").read_text())
        self.panel_files(folder, vote_text("Rule: B", "c1"), vote_text("Rule: B", "c2"),
                         vote_text("Hold: the count of open orders"))
        self.ran(model="claude-fable-5-2")
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 3, out)
        self.assertIn("with the model override `opus`", out)
        self.assertNotIn("road B, 2 of 3", out, "no count is shown before the readers ran on the panel's model")
        self.ran()
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("road B, 2 of 3", out)
        self.assertEqual(sorted(json.loads((folder / mod.AGENTS).read_text())), ["builder", "exposed", "finder", "operator"])
        self.assertIn("drop the column in this migration", out)
        self.assertIn("--who panel", out)
        self.assertEqual(self.row("02"), f"stopped: {self.QUESTION}")

    def test_record_by_panel_is_refused_without_the_panels_files(self):
        folder = self.risk_stop()
        self.ran()
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn(mod.FINDER, out)
        self.panel_files(folder, vote_text("Rule: A"), vote_text("Rule: A"))
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("builder", out)
        self.assertNotIn("## Rulings", self.plan.read_text())
        # The files of one question are not the files of the note's next question.
        self.panel_files(folder, vote_text("Rule: A"), vote_text("Rule: A"), vote_text("Rule: A"))
        other = "may the migration rename the table"
        self.rows(n02=f"stopped: {other}")
        self.typed("02", "migration", other, DEFAULT)
        self.command("wait", "--note", "02")
        self.later(mod.RULING_WAIT_SECONDS)
        code, out = self.record("02", "migration", "panel", DEFAULT, question=other)
        self.assertEqual(code, 3, out)
        self.assertIn(mod.FINDER, out)
        self.assertNotIn("## Rulings", self.plan.read_text())

    def test_record_by_panel_is_refused_before_the_wait_is_over(self):
        folder = self.risk_stop(waited=False)
        self.panel_files(folder, vote_text("Rule: A"), vote_text("Rule: A"), vote_text("Rule: A"))
        self.ran()
        self.later(mod.RULING_WAIT_SECONDS - 1)
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("His answer rules until", out)
        self.later(1)
        self.assertEqual(self.by_panel(DEFAULT)[0], 0)

    def test_record_by_panel_is_refused_outside_the_risk_classes(self):
        folder = self.risk_stop(cls="none")
        self.panel_files(folder, vote_text("Rule: A"), vote_text("Rule: A"), vote_text("Rule: A"))
        self.ran()
        code, out = self.record("02", "none", "panel", DEFAULT, question=self.QUESTION)
        self.assertEqual(code, 3, out)
        self.assertIn("the `default` rules a [none] question", out)
        self.assertEqual(self.command("panel", "--note", "02")[0], 3)
        # Nor a stop with no class on record, a row that waits for him, or a failed row.
        self.rows(n02="stopped: an error nobody typed a class for")
        code, out = self.record("02", "money", "panel", DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("no class on record", out)
        self.assertEqual(self.command("panel", "--note", "02")[0], 3)
        self.command("wait", "--note", "02")
        self.assertEqual(self.row("02"), "waiting: unclassified: an error nobody typed a class for")
        self.later(mod.RULING_WAIT_SECONDS)
        self.assertEqual(self.record("02", "money", "panel", DEFAULT)[0], 3)
        self.rows(n02="failed")
        self.assertEqual(self.record("02", "re-arm", "panel", DEFAULT)[0], 3)
        self.assertEqual(self.record("02", "money", "panel", DEFAULT)[0], 3)
        self.assertNotIn("## Rulings", self.plan.read_text())

    def test_record_by_panel_takes_only_the_road_the_count_gives(self):
        folder = self.risk_stop()
        self.panel_files(folder,
                         vote_text("Rule: B", "e2e/owner.spec.ts: an order with no owner still opens"),
                         vote_text("Rule: A", "lib/a.test.ts: a condition of the road that lost"),
                         vote_text("Rule: B", "db/owner.test.ts: the old column is gone after the migration",
                                   "db/owner.test.ts: a rollback restores it", "a third one"))
        self.ran()
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn('the count gives road B: "drop the column in this migration"', out)
        self.assertEqual(self.by_panel("add a view that both shapes read")[0], 3)
        self.assertNotIn("## Rulings", self.plan.read_text())
        code, out = self.by_panel("drop the column in this migration")
        self.assertEqual(code, 0, out)
        entries = entries_of(self.plan.read_text())[0]
        entry = entries[-1]
        self.assertEqual((entry["who"], entry["kind"], entry["words"]),
                         ("panel", "migration", "drop the column in this migration"))
        self.assertEqual(entry["panel"], {"count": "road B, 2 of 3", "files": folder.name})
        self.assertEqual(entry["conditions"], ["e2e/owner.spec.ts: an order with no owner still opens",
                                               "db/owner.test.ts: the old column is gone after the migration",
                                               "db/owner.test.ts: a rollback restores it"])
        self.assertEqual(self.row("02"), "not started")
        self.assertEqual(sorted(json.loads((folder / mod.AGENTS).read_text())), ["builder", "exposed", "finder", "operator"])
        self.assertEqual([e["number"] for e in mod.open_entries(entries, "Sam")], ["02"])

    def test_a_found_road_rules_with_two_of_three(self):
        folder = self.risk_stop(note="final")
        self.panel_files(folder, vote_text("Rule: F1"), vote_text("Rule: A"), vote_text("Rule: F1"))
        self.ran(note="final")
        self.assertEqual(self.by_panel(DEFAULT, note="final")[0], 3)
        code, out = self.by_panel("add a view that both shapes read", note="final")
        self.assertEqual(code, 0, out)
        self.assertIn(f"  Panel: road F1, 2 of 3, files {folder.name}\n", self.plan.read_text())

    def test_when_the_readers_disagree_the_default_rules_and_the_entry_says_so(self):
        folder = self.risk_stop()
        self.panel_files(folder, vote_text("Rule: B", "cond of b"), vote_text("Hold: the count of open orders"),
                         vote_text("Rule: A", "cond of a"))
        self.ran()
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("the readers disagreed", out)
        self.assertEqual(self.by_panel("drop the column in this migration")[0], 3)
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 0, out)
        self.assertIn(f"  Panel: the readers disagreed, so the written default rules, files {folder.name}\n",
                      self.plan.read_text())
        self.assertEqual(entries_of(self.plan.read_text())[0][-1]["conditions"], ["cond of a"])

    def test_two_holds_make_the_note_wait_and_no_road_rules(self):
        folder = self.risk_stop()
        self.panel_files(folder, vote_text("Hold: the count of open orders"), vote_text("Rule: B"),
                         vote_text("Hold: whether the old app still reads the column"))
        self.ran()
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("the readers hold", out)
        self.assertEqual(self.row("02"), f"stopped: {self.QUESTION}")
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), f"waiting: migration: {self.QUESTION}")
        self.assertIn("the count of open orders", out)
        self.assertIn("whether the old app still reads the column", out)
        self.assertEqual(self.by_panel(DEFAULT)[0], 3)
        self.assertNotIn("## Rulings", self.plan.read_text())
        self.assertTrue((folder / mod.AGENTS).is_file(), "a hold is measured too")
        self.later(30)
        self.says("02: drop it.")
        self.assertEqual(self.record("02", "migration", "Sam", "02: drop it", question=self.QUESTION)[0], 0)

    def test_a_road_that_needs_a_fact_from_him_is_never_recorded(self):
        folder = self.risk_stop()
        self.panel_files(folder, vote_text("Rule: F2"), vote_text("Rule: F2"), vote_text("Rule: F2"))
        self.ran()
        code, out = self.by_panel("backfill in production first")
        self.assertEqual(code, 3, out)
        self.assertIn("the count gives road A", out)
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("no vote", out)
        self.assertIn("needs a fact", out)
        self.assertIn("the count of rows with no owner in production", out)
        self.assertNotIn("## Rulings", self.plan.read_text())

    def test_record_by_panel_needs_the_transcripts_of_its_agents_on_the_panel_model(self):
        folder = self.risk_stop()
        self.panel_files(folder, vote_text("Rule: A"), vote_text("Rule: A"), vote_text("Rule: A"))
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("panel 02: finder", out)
        self.ran(skip=("operator",))
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("panel 02: reader operator", out)
        self.ran(model="claude-fable-5-2")
        code, out = self.by_panel(DEFAULT)
        self.assertEqual(code, 3, out)
        self.assertIn("opus", out)
        self.assertIn("claude-fable-5-2", out)
        self.assertNotIn("## Rulings", self.plan.read_text())
        self.ran(note="03")
        self.assertEqual(self.by_panel(DEFAULT)[0], 3, "the agents of another note are not this panel's")
        self.ran()
        self.assertEqual(self.by_panel(DEFAULT)[0], 0)

    def test_a_stop_with_no_written_default_or_a_third_ruling_without_him_waits(self):
        self.risk_stop(default="")
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("no written default", out)
        self.assertEqual(self.row("02"), f"waiting: migration: {self.QUESTION}")
        two = "".join(f'- [none] 02: question {i}\n  Ruled: 2026-11-12, default, "w"\n  Touches: none\n  Undo: one line\n'
                      for i in (1, 2))
        self.plan.write_text(PLAN.split("## Rulings")[0] + "## Rulings\n\n" + two + "\nApproved: 2026-11-03\n")
        folder = self.risk_stop()
        code, out = self.command("panel", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertIn("without Sam already", out)
        self.assertEqual(self.row("02"), f"waiting: migration: {self.QUESTION}")
        self.assertFalse((folder / "finder.brief.md").exists(), "no agent is spawned for a question that waits")

    def test_the_gate_line_of_a_panel_ruling_has_the_full_form(self):
        folder = self.risk_stop()
        self.panel_files(folder,
                         vote_text("Rule: F1", "e2e/owner.spec.ts: an order with no owner still opens"),
                         vote_text("Hold: the count of open orders",
                                   reason="Nobody counted the open orders. The view hides that."),
                         vote_text("Rule: F1", "db/view.test.ts: both shapes read the view"))
        self.ran()
        self.assertEqual(self.by_panel("add a view that both shapes read")[0], 0)
        self.rows(n02="merged abc123456")
        code, out = self.command("list")
        self.assertEqual(code, 0, out)
        line = next(row for row in out.splitlines() if row.startswith("- **MIGRATION** 02:"))
        for part in (
            f"02: {self.QUESTION}",
            'Road taken: "add a view that both shapes read"',
            "Ruled by panel on 2026-11-12.",
            "The count: road F1, 2 of 3.",
            "exposed: Rule: F1. The old shape stays readable. A rollback needs no backfill.",
            "operator: Hold: the count of open orders. Nobody counted the open orders. The view hides that.",
            "builder: Rule: F1. The old shape",
            "Conditions: e2e/owner.spec.ts: an order with no owner still opens; db/view.test.ts: both shapes read the view.",
            "A road the question did not offer: F1 (the road taken), add a view that both shapes read; "
            "evidence: src/orders/read.ts:41, db/migrations/0090_orders.sql:12; undo: drop the view.",
            "A candidate road that needs a fact from Sam: F2, backfill in production first; "
            "the fact: the count of rows with no owner in production.",
            "Touched: none.",
            "Undo: one line.",
        ):
            self.assertIn(part, line)
        self.assertNotIn("Third sentence", line)
        entries = entries_of(self.plan.read_text())[0]
        self.assertEqual(mod.away_lines(entries, "Sam", records=self.records), [line[2:]],
                         "the report's line is the list's line")
        short = mod.away_lines(entries, "Sam")[0]
        self.assertIn("The count: road F1, 2 of 3. Conditions: e2e/owner.spec.ts", short,
                      "a hook's refusal has the count and the conditions from the page alone")
        shutil.rmtree(folder)
        line = mod.away_lines(entries, "Sam", records=self.records)[0]
        self.assertIn("are not on this machine", line)
        self.assertIn("The count: road F1, 2 of 3.", line)
        self.assertIn("Conditions: e2e/owner.spec.ts", line)
        self.assertIn(folder.name, line)

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

    def test_wait_on_a_risk_question_keeps_the_row_and_names_the_panel(self):
        question = "may a manager refund without the owner"
        self.rows(n02=f"stopped: {question}")
        self.typed("02", "money", question)
        code, out = self.command("wait", "--note", "02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.row("02"), f"stopped: {question}")
        self.assertIn("after that the panel rules", out)
        self.assertIn("rulings.py panel bubble", out)
        self.later(10 * mod.RULING_WAIT_SECONDS)
        code, out = self.record("02", "money", "default")
        self.assertEqual(code, 3, out)
        self.assertIn("the `panel` rules a [money] question", out)
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
        self.assertIn("without Sam already", out)

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
        self.assertEqual(self.row("final"), f"stopped: {question}")
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
        self.rows(n01="merged abc123456", n02="merged abc123456", n03="not started")
        self.plan.write_text(Gate.BY_PANEL)
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
