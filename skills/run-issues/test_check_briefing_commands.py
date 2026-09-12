#!/usr/bin/env python3
"""Drill for check_briefing_commands.py.

The one thing this file exists to pin: the check tells a HANDED-OVER COMMAND
apart from a quoted identifier. Run `batch-207704`'s merge briefing holds 1,332
inline code spans and 24 distinct commands. A check that fired on every span
would refuse the briefing for naming `storableRow`, and a check that fired on
every fenced block would refuse it for quoting a cost table.

    python3 test_check_briefing_commands.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import tempfile
import unittest

import check_briefing_commands as check


def briefing(body: str) -> pathlib.Path:
    """A throwaway merge briefing holding `body`."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="briefcmd-"))
    path = root / "merge-briefing.md"
    path.write_text(body, encoding="utf-8")
    return path


class WhatCountsAsACommand(unittest.TestCase):
    """The definition is the whole difficulty, so it is pinned from both sides."""

    def found(self, body: str) -> list:
        return [one.text for one in check.commands(body)]

    def test_a_verb_with_an_argument_is_a_command(self):
        self.assertEqual(self.found("- ran `npx tsc --noEmit` here"),
                         ["npx tsc --noEmit"])

    def test_a_bare_tool_name_is_a_noun_and_is_not_a_command(self):
        """`tsc` and `lint` clean" hands over nothing. Run `batch-207704`'s
        briefing writes the bare word four times as a noun."""
        self.assertEqual(self.found("- `tsc` and `lint` were both clean"), [])

    def test_a_source_file_citation_is_not_a_command(self):
        """The briefing cites 60-odd source paths. Firing on them is the noise
        that makes a check unusable."""
        body = "- `src/lib/deals/room.read.ts` and `tests/lint/paid-call-meter.test.ts`"
        self.assertEqual(self.found(body), [])

    def test_an_identifier_is_not_a_command(self):
        self.assertEqual(self.found("- `storableRow` refused `22P05` under `\\p{C}`"), [])

    def test_a_bare_script_path_under_scripts_is_a_command(self):
        """Fault 5 of the eight: three seeders handed over as bare paths, none
        of them carrying the execute bit."""
        self.assertEqual(self.found("- run `scripts/seed-fat-deal.mjs` first"),
                         ["scripts/seed-fat-deal.mjs"])

    def test_a_script_name_with_no_directory_needs_an_argument(self):
        """`check_register_status.py` named in prose is a citation. The same
        name carrying a flag is a handover."""
        self.assertEqual(self.found("- see `check_register_status.py`"), [])
        self.assertEqual(self.found("- run `dev-signin-link.mjs --batch b1`"),
                         ["dev-signin-link.mjs --batch b1"])

    def test_leading_environment_assignments_are_stripped_before_the_verb(self):
        body = "- `SUPABASE_DB_URL=$QA_SUPABASE_DB_URL node scripts/seed.mjs`"
        self.assertEqual(len(self.found(body)), 1)

    def test_a_command_inside_a_fenced_block_is_found(self):
        body = "para\n\n```\npython3 ~/.claude/skills/run-issues/check_run_rail.py x\n```\n"
        self.assertEqual(len(self.found(body)), 1)

    def test_a_table_row_inside_a_fenced_block_is_not_a_command(self):
        """Run `batch-207704` fences 16 blocks and only two hold a command. The
        rest are rails, cost tables and JSON."""
        body = "```\n| Issue | Turns | Minutes |\n| 571 | 42 | 12.7 |\n```\n"
        self.assertEqual(self.found(body), [])

    def test_the_line_number_is_the_line_the_command_sits_on(self):
        body = "one\n\ntwo\n\n- `npm test` here\n"
        self.assertEqual(check.commands(body)[0].line, 5)


class TheMark(unittest.TestCase):
    def audit(self, body: str) -> list:
        return check.audit(body)

    def test_a_command_marked_ran_passes(self):
        found = self.audit("- ran `npm test` myself, read-only. RAN\n")
        self.assertEqual([one.marked for one in found], ["RAN"])

    def test_a_command_marked_unrun_passes(self):
        found = self.audit("- `npm test` — UNRUN, I could not reach the tree\n")
        self.assertEqual([one.marked for one in found], ["UNRUN"])

    def test_a_backticked_mark_counts(self):
        found = self.audit("- `npm test`, marked `UNRUN` beside it\n")
        self.assertEqual([one.marked for one in found], ["UNRUN"])

    def test_an_unmarked_command_is_the_fault(self):
        found = self.audit("- the suite was green: `npm test`\n")
        self.assertEqual([one.marked for one in found], [None])

    def test_a_lowercase_ran_in_prose_is_not_a_mark(self):
        """"I ran it" is the sentence every gate writes. The mark is a token,
        and a check reading the prose word would pass every briefing."""
        found = self.audit("- I ran `npm test` and it was green\n")
        self.assertEqual([one.marked for one in found], [None])

    def test_a_mark_reaches_a_command_on_a_later_line_of_the_same_item(self):
        """Fault 4 of the eight: `npx tsc --noEmit` broke across a line break.
        A list item is one block however many lines it takes."""
        found = self.audit("- UNRUN. This one needs a tree:\n  `npx tsc --noEmit`\n")
        self.assertEqual([one.marked for one in found], ["UNRUN"])

    def test_a_mark_in_a_different_block_does_not_reach(self):
        found = self.audit("- UNRUN, on the item above.\n\n- `npm test` here\n")
        self.assertEqual([one.marked for one in found], [None])

    def test_a_mark_in_a_different_heading_section_does_not_reach(self):
        found = self.audit("## One\n\nRAN\n\n## Two\n\n- `npm test`\n")
        self.assertEqual([one.marked for one in found], [None])

    def test_a_command_may_not_mark_itself(self):
        """The mark is read from what is LEFT of the line once the command text
        is removed. Without that, a command carrying the token — an env var, a
        quoted diff line — authorises itself and the rule refuses nothing."""
        found = self.audit("- `RAN=1 npm test` is the shape\n")
        self.assertEqual([one.marked for one in found], [None])

    def test_a_comment_beside_a_fenced_command_still_marks_it(self):
        """Removing the command text leaves the comment, which is a real place
        to write the mark."""
        body = "```\nnpm test   # RAN\n```\n"
        self.assertEqual([one.marked for one in check.audit(body)], ["RAN"])

    def test_a_second_fenced_block_does_not_inherit_the_first_one_s_mark(self):
        """A mark written for one fence may not authorise the next. Otherwise a
        finale that ran the suite and wrote RAN above it also authorises the
        seeder in the block below, which it never ran."""
        body = "Run this. RAN\n\n```\nnpm test\n```\n\n```\nscripts/seed.mjs\n```\n"
        self.assertEqual([one.marked for one in check.audit(body)], ["RAN", None])

    def test_a_paragraph_mark_reaches_the_fenced_block_under_it(self):
        """A fence is handed over by the sentence above it, and markdown puts a
        blank line between the two."""
        body = "Run this yourself. RAN\n\n```\nnpm test\n```\n"
        self.assertEqual([one.marked for one in check.audit(body)], ["RAN"])


class Report(unittest.TestCase):
    def test_a_clean_briefing_authorises(self):
        code, text = check.report(check.audit("- `npm test` RAN\n"), "b.md")
        self.assertEqual(code, 0)
        self.assertIn("1", text)

    def test_a_briefing_with_no_command_at_all_authorises(self):
        code, text = check.report(check.audit("Nothing to run here.\n"), "b.md")
        self.assertEqual(code, 0)

    def test_an_unmarked_command_refuses_and_names_it(self):
        code, text = check.report(check.audit("- `npm test`\n"), "b.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)
        self.assertIn("npm test", text)

    def test_the_refusal_gives_the_line_number(self):
        code, text = check.report(check.audit("a\n\n- `npm test`\n"), "b.md")
        self.assertIn(":3", text)

    def test_the_refusal_offers_two_roads_and_never_waits(self):
        """Copied from run-state-path-guard.py: one call refused, two roads out,
        and a line saying it never waits for the human."""
        code, text = check.report(check.audit("- `npm test`\n"), "b.md")
        self.assertIn("1.", text)
        self.assertIn("2.", text)
        self.assertIn("AFK", text)

    def test_the_refusal_names_unrun_as_the_free_road(self):
        """the human's ruling of 2026-09-08: a gate may always mark UNRUN and pay
        nothing, so the worst case is honest rather than expensive."""
        code, text = check.report(check.audit("- `npm test`\n"), "b.md")
        self.assertIn("UNRUN", text)

    def test_every_unmarked_command_is_named_not_just_the_first(self):
        code, text = check.report(check.audit("- `npm test`\n\n- `npx eslint .`\n"), "b.md")
        self.assertIn("npm test", text)
        self.assertIn("npx eslint .", text)


class Main(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_a_clean_briefing_exits_zero(self):
        path = briefing("- `npm test` RAN\n")
        code, text = self.run_main([str(path)])
        self.assertEqual(code, 0)

    def test_an_unmarked_command_exits_one(self):
        path = briefing("- `npm test`\n")
        code, text = self.run_main([str(path)])
        self.assertEqual(code, 1)
        self.assertIn("npm test", text)

    def test_a_missing_file_refuses_rather_than_passing_silently(self):
        code, text = self.run_main(["/nowhere/merge-briefing.md"])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_list_names_every_command_and_authorises(self):
        """The measurement road. A gate reads what the check reads before it
        marks anything, and reading may not refuse."""
        path = briefing("- `npm test`\n\n- `npx eslint .` RAN\n")
        code, text = self.run_main([str(path), "--list"])
        self.assertEqual(code, 0)
        self.assertIn("npm test", text)
        self.assertIn("npx eslint .", text)


class TheRealBriefing(unittest.TestCase):
    """A check whose only evidence is its own fixtures has not been measured."""

    REAL = pathlib.Path(
        "/home/user/project/.scratch/example-feature/runs/"
        "batch-207704/merge-briefing.md")

    def setUp(self):
        if not self.REAL.exists():
            self.skipTest("run batch-207704's briefing is not on this machine")
        self.body = self.REAL.read_text(encoding="utf-8", errors="replace")

    def test_it_names_the_seven_fault_classes_the_finale_found_by_hand(self):
        """The finale found eight faults by hand. Seven are written commands and
        this check names every one. The eighth is twelve suite figures quoted
        with NO command, and no check reading what is written can see an absence.
        """
        texts = {one.text for one in check.commands(self.body)}
        self.assertIn("tsc --noEmit", texts)
        self.assertIn("npx eslint", texts)
        self.assertIn("git show HEAD:", texts)
        self.assertIn("npx tsc", texts)
        self.assertIn("scripts/seed-fat-deal.mjs", texts)
        self.assertIn("git diff --stat -- .scratch/example-feature/citation-deltas/",
                      texts)
        self.assertIn("git diff -U0", texts)

    def test_it_does_not_fire_on_the_identifiers_the_briefing_quotes(self):
        texts = {one.text for one in check.commands(self.body)}
        for quoted in ("storableRow", "meterParse", "src/lib/deals/room.read.ts",
                       "22P05", "docs/patterns.md", "mnuwqjbopswqqgcwryvn"):
            self.assertNotIn(quoted, texts)

    def test_it_refuses_this_briefing_because_nothing_in_it_is_marked(self):
        code, text = check.report(check.audit(self.body), str(self.REAL))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
