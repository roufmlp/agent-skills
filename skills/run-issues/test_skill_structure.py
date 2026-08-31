#!/usr/bin/env python3
"""Tests for the shape of run-issues/SKILL.md itself.

Three workflow-audit rows changed this file's structure rather than its rules,
and each one can be undone by an ordinary edit that looks harmless:

- Row 7 moved the finale and the ledger procedure off the orchestrator's common
  load path into `finale.md` and `resume.md`. A later edit that pastes either
  block back, or that drops the trigger line pointing at the moved file, breaks
  the split without breaking anything a reader would notice.
- Row 17 gave the effort table a justification column. A new role row added
  without a justification returns the table to a dial nothing licenses.
- Row 4 governed how a skill cites a file that lives outside the repo. Here it
  is published as its inverse: no skill may cite a machine-local absolute path,
  because such a path resolves on no reader's machine.

The checks read the live files, not fixtures. That is deliberate: these rows
are claims about the files as they stand, and a fixture would pass while the
real file drifted.

Run: python3 test_skill_structure.py
"""

import re
import unittest
from pathlib import Path

RUN_ISSUES = Path(__file__).resolve().parent
SKILLS = RUN_ISSUES.parent

SKILL = RUN_ISSUES / "SKILL.md"
FINALE = RUN_ISSUES / "finale.md"
DECISIONS = RUN_ISSUES / "decisions.md"
RESUME = RUN_ISSUES / "resume.md"

# Sentences that live inside the finale block and nowhere else. Every one is
# load-bearing prose a reader would miss if the move dropped it.
FINALE_MARKS = [
    "Preview deploy is **skipped in this repo**",
    "A published checksum expires the moment the file moves.",
    "Main moved while you worked. Read it before you write a question.",
    "Sweep the register for rows their own issue already fixed.",
    "The thresholds live in `~/.claude/agents/promotion.md` and nowhere else.",
    "**Regenerate the action board**",
    "**The post-deploy smoke walk**, owned by `/daily-brief`.",
    "**Recommend follow-ups; start none.**",
]

# The ledger-selection procedure, which row 9 had already reduced to one
# invocation before row 7 moved it.
RESUME_MARKS = [
    "**Find the right ledger before reading any of it.**",
    "python3 ~/.claude/skills/run-issues/find_live_ledger.py",
    # The refusal semantics. Wrapped over two lines in the source, so the
    # marker stops at the line break.
    "report what it printed in the launch message and spawn nothing",
    "chasing it cost 25 minutes",
    "recreate the cron",
]

# --- The class-(a) slim, 2026-08-23 -----------------------------------------
#
# The panel review of 2026-08-22 walked SKILL.md for passages that are pure
# history and found roughly 130-160 lines of them, with a warning attached: six
# other passages read as history and are rules wearing narrative clothes, and
# moving one of those deletes a live rule. Its inv-5 was marked GAP for exactly
# this reason — nothing refused a move that took the rule away with the story.
#
# These two lists are that refusal.
#
#   SKILL_MARKS      the rule sentence each move must LEAVE BEHIND. Asserted
#                    present in SKILL.md. If a move takes the anchor with the
#                    story, this goes red.
#   DECISIONS_MARKS  the story each move took. Asserted present in decisions.md
#                    AND absent from SKILL.md — the FINALE_MARKS shape above.
#
# **The two lists were written at different times, deliberately.** Every anchor
# went in before one line moved, so the anchor test was already green and
# already watching while the edits happened. A story joined the second list only
# once it had landed in decisions.md. A passage in neither list is one nobody
# has moved yet, not one exempt from the rule.
#
# The target shape for every move is the sentence at "Small-issue coalescing was
# retired": rule loaded, evidence moved, prohibition intact.
SKILL_MARKS = [
    "The launch line is a gate, not an announcement.",
    "Export the `QA_*` variables only when you deliberately",
    "A field you cannot fill stops the spawn",
    "**A prohibition in a brief names the SYSTEM, not the verb.**",
    "is what makes that a refusal instead of a silent pass",
    "the repair belongs to the next",
    "a scopeless negative is not",
    "One grep for a distinctive phrase from the deleted sentence.",
    "*Never write that something is the only copy.*",
    "*A recorded cause is tested against a control, never merely observed.*",
    "*Every citation carries its repo-relative path in full, every time.*",
    # No terminal full stop: the move turned this sentence's period into a
    # colon introducing the pointer. The clause is the rule; the
    # punctuation is not.
    "The class survives its own cure",
    "Ledger actuals derive from commit times, full stop.",
    "This paragraph states the intent; the pre-spawn",
    "A ruling that creates work gets its issue number in the same sitting",
    "staleness is the FILE's mtime",
    "Re-derive every fact the run will carry into its spawns, from source",
    "never pass a `model:` value on a spawn",
    "A green produced without dependencies on disk is",
    "It is a floor, not a definition.",
    # The permission-floor block. The mechanism sentences are the rule: they
    # say WHY the check reads a tracked allow rule rather than dry-running,
    # and a move that took them with the cost figures would leave a check
    # nobody could reason about.
    "a worktree freezes it on the day it was cut",
    "A class verified at launch is not a class verified",
    "The remedy is the human's hands",
]

DECISIONS_MARKS = [
    "three red suites in one night",
    "picked the blind one and drove a whole acceptance",
    "three files landed at the shared worktree root",
    "175-line verdict",
    "went from 1 broken citation to 251",
    "Two of the first three implementers on the",
    "was broken the same night",
    "its twin sat one",
    "asserted issue 201's file was the only",
    "having watched it succeed there",
    "a bare `review.ts` used eleven times",
    "transcribed figure off by 960",
    "7 attempts and 14 gate runs where the skill promises three",
    "it was minted as 234",
    "failed twice in one run, on a runner",
    "the line printed at 22:22",
    "answers null when the count is not one",
    "it moved to `inherit` on 2026-08-02",
    "resolved off a global install",
    "task counter reading 6h 00m 05s",
    # The permission floor's cost, moved to decisions.md on 2026-09-01.
    "the single largest step of a 14.76 hour run",
    "dry-run `npx vitest` successfully at 04:00",
]

EFFORT_ROLES = [
    "run-issues-implementer",
    "run-issues-implementer-escalated",
    "run-issues-verify-gate",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
    "run-issues-finale",
    "promotion",
]


def read(path):
    return path.read_text(encoding="utf-8")


def squash(text):
    """Collapse every run of whitespace to one space.

    The slim's marks are compared against this rather than the raw file. These
    are hard-wrapped markdown documents, so a sentence that fits on one line
    today sits across two the moment anything before it grows by a word — and
    the very edits this test polices are the ones that reflow paragraphs. The
    first move of the 2026-08-23 slim proved it: the rule sentence survived
    intact, the line break inside it moved, and the raw-substring check called
    that a deleted rule. A guard that goes red on a reflow is a guard somebody
    switches off.

    FINALE_MARKS and RESUME_MARKS predate this and cope by choosing marks short
    enough to fit one line; they are left alone rather than churned.
    """
    return " ".join(text.split())


class TestFinaleIsOffTheCommonPath(unittest.TestCase):
    """Row 7, the finale half."""

    def test_finale_file_exists_beside_the_skill(self):
        self.assertTrue(FINALE.is_file(), f"{FINALE} does not exist")

    def test_every_finale_sentence_survived_the_move(self):
        finale = read(FINALE)
        for mark in FINALE_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(mark, finale)

    def test_the_finale_body_is_no_longer_resident_in_the_skill(self):
        skill = read(SKILL)
        for mark in FINALE_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(mark, skill)

    def test_the_skill_still_carries_the_trigger(self):
        """The instruction to write `finale-mechanical` sits inside the moved
        block, so the trigger has to be on the common path or nothing reads
        the file."""
        skill = read(SKILL)
        self.assertIn("finale-mechanical", skill)
        self.assertIn("finale.md", skill)

    def test_the_trigger_ties_the_ledger_write_to_the_read(self):
        """A pointer that says the file exists is a reminder. The trigger has
        to name both halves in one sentence: the state the runner writes, and
        the file it reads."""
        skill = read(SKILL)
        sentences = re.split(r"(?<=[.:])\s", skill)
        tying = [
            s for s in sentences if "finale-mechanical" in s and "finale.md" in s
        ]
        self.assertTrue(
            tying,
            "no single sentence names both the `finale-mechanical` ledger write "
            "and `finale.md`",
        )


class TestResumeProcedureIsOffTheCommonPath(unittest.TestCase):
    """Row 7, the ledger half, carrying row 9's invocation with it."""

    def test_resume_file_exists_beside_the_skill(self):
        self.assertTrue(RESUME.is_file(), f"{RESUME} does not exist")

    def test_every_ledger_sentence_survived_the_move(self):
        resume = read(RESUME)
        for mark in RESUME_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(mark, resume)

    def test_the_ledger_procedure_is_no_longer_resident_in_the_skill(self):
        skill = read(SKILL)
        for mark in RESUME_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(mark, skill)

    def test_the_skill_still_carries_the_resume_trigger(self):
        skill = read(SKILL)
        self.assertIn("resume.md", skill)

    def test_the_script_it_names_is_on_disk(self):
        """Row 9's script moved citation, not location."""
        self.assertTrue((RUN_ISSUES / "find_live_ledger.py").is_file())


class TestTheSlimLeftEveryRuleBehind(unittest.TestCase):
    """The p6 class-(a) slim: inv-5, made mechanical."""

    def test_every_anchor_is_still_in_the_skill(self):
        """The refusal that matters. A move that carried its rule out with the
        story goes red here, and only here — a reader would not notice."""
        skill = squash(read(SKILL))
        for mark in SKILL_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(
                    squash(mark),
                    skill,
                    "a class-(a) move took its rule anchor with it",
                )

    def test_every_moved_story_landed_in_decisions(self):
        decisions = squash(read(DECISIONS))
        for mark in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(squash(mark), decisions)

    def test_no_moved_story_is_still_resident_in_the_skill(self):
        """A move that copies rather than moves saves nothing and doubles the
        maintenance surface."""
        skill = squash(read(SKILL))
        for mark in DECISIONS_MARKS:
            with self.subTest(mark=mark):
                self.assertNotIn(squash(mark), skill)

    def test_the_anchor_list_is_not_empty(self):
        """An empty catalogue is a green that means no work was done."""
        self.assertTrue(SKILL_MARKS)

    def test_no_story_is_listed_as_its_own_anchor(self):
        """The two lists must not intersect: one string cannot be required to
        be present in and absent from the same file."""
        self.assertEqual(set(SKILL_MARKS) & set(DECISIONS_MARKS), set())

    def test_the_model_sentence_is_still_the_model(self):
        """Every move copies this shape, so a later edit that deletes it takes
        the pattern with it."""
        skill = read(SKILL)
        self.assertIn("Small-issue coalescing was retired", skill)
        self.assertIn("`decisions.md` holds the measurement", skill)


class TestTheClassBPassagesWereNotTouched(unittest.TestCase):
    """The six passages p6 marked 'moving this deletes a rule'.

    They are not anchors of a move — nothing was moved near them. They are
    listed because the slim is the exact edit that would take them, and the
    next editor reading the class-(a) list may not read the warning beside it.
    """

    CLASS_B = [
        # The cron's own justification.
        "cannot prevent a call that was never made",
        # The recoverability test and the standing xhigh refusal.
        "No value in the effort column was measured against a lower one",
        # The INTERIM R2 block: its expiry and its restore obligation.
        "INTERIM, from 2026-08-19 until issue 379 ships",
        "must restore per-commit passes and say so in its briefing",
        # The self-commit contingency, stated nowhere else.
        "The runner commits. An implementer never commits its own work",
        "do not revert it — record it and give the gates the range",
        # the human's 2026-08-21 orchestrator-cost ruling.
        "Do not go looking for an older number",
        # The halt block as the only resume document.
        "a second copy goes stale",
    ]

    def test_every_class_b_passage_is_still_loaded(self):
        skill = squash(read(SKILL))
        for mark in self.CLASS_B:
            with self.subTest(mark=mark):
                self.assertIn(
                    squash(mark),
                    skill,
                    "this reads as history and is a live rule; p6 class (b)",
                )


class TestEffortTableCarriesItsEvidence(unittest.TestCase):
    """Row 17."""

    def effort_table(self):
        """The one table whose header names a Stage and an Effort."""
        for block in re.findall(r"(?:^\|.*\n)+", read(SKILL), re.MULTILINE):
            rows = block.strip().splitlines()
            if "Stage" in rows[0] and "Effort" in rows[0]:
                return rows
        self.fail("no effort table found in SKILL.md")

    def cells(self, row):
        return [c.strip() for c in row.strip().strip("|").split("|")]

    def test_the_table_has_a_justification_column(self):
        header = self.cells(self.effort_table()[0])
        self.assertEqual(
            4,
            len(header),
            f"expected Stage, Agent type, Effort and a justification; got {header}",
        )

    def test_every_role_justifies_its_effort(self):
        rows = self.effort_table()[2:]
        seen = {}
        for row in rows:
            cells = self.cells(row)
            for role in EFFORT_ROLES:
                if f"`{role}`" in cells[1]:
                    seen[role] = cells[3] if len(cells) > 3 else ""
        for role in EFFORT_ROLES:
            with self.subTest(role=role):
                self.assertIn(role, seen, f"{role} is not in the effort table")
                self.assertTrue(
                    len(seen[role]) > 10,
                    f"{role}'s justification cell says nothing: {seen[role]!r}",
                )

    def test_downgrade_safety_is_stated_as_recoverability(self):
        """The measured rule: a downgrade is safe where a wrong verdict is
        recoverable, not where the model looks strong enough."""
        skill = read(SKILL).lower()
        self.assertIn("recoverab", skill)


class TestCitationsResolveAnywhere(unittest.TestCase):
    """Every path a published skill cites must resolve where the reader is.

    A machine-local absolute path (`/Users/...`, `/home/...`) resolves only on
    the author's machine. The pack allows home-relative `~/.claude/...` paths,
    because that is where it installs, and repo-relative runtime paths like
    `.scratch/<feature>/`.

    This is the published inverse of a live case. The live tree asserts that
    every mention of its pending-actions file carries that file's absolute
    path, because there the path is real and a bare name misleads. Here no such
    file exists for any reader, so the same concern becomes its opposite.
    """

    def files(self):
        return sorted(SKILLS.glob("*/SKILL.md")) + [FINALE, RESUME]

    def test_no_skill_cites_a_machine_local_absolute_path(self):
        for path in self.files():
            if not path.is_file():
                continue
            text = read(path)
            for prefix in ("/Users/", "/home/"):
                with self.subTest(path=f"{path.parent.name}/{path.name}",
                                  prefix=prefix):
                    self.assertNotIn(
                        prefix,
                        text,
                        "a machine-local absolute path resolves on no other "
                        "machine; cite a home-relative or repo-relative path",
                    )

    def test_the_spawn_instruction_names_run_in_background_false(self):
        """The rule: every run-issues spawn names run_in_background: false,
        because the runner has nothing to do while a worker runs.

        The evidence history matters more than the rule. The 2026-08-17 audit of
        run cab74e blamed eight 17-to-23-minute stalls, 158 minutes, on
        background spawns. The 2026-08-18 re-measure joined each spawn to its
        subagent transcript and refuted that: a task notification woke the
        runner within seconds of every completion, and the gaps were the
        workers' own runtimes. The field stays on the Agent tool's own guidance
        and saves no measured clock; a PreToolUse hook
        (~/.claude/hooks/run-issues-foreground-gate.py) enforces it. This test
        pins the text that tells the runner why.
        """
        self.assertIn(
            "run_in_background: false",
            read(SKILL),
            "SKILL.md must name the field, and the hook that enforces it "
            "refuses a spawn that does not.",
        )

    def test_the_reason_travels_with_the_instruction(self):
        """A bare field is a value a later edit flips back without noticing.

        Two facts must sit next to the field. The cron is a usage-limit resume,
        not the pacemaker: its one real rescue in cab74e was a spawn the runner
        announced and never made. And the original 158-minute stall claim was
        refuted on 2026-08-18. Both travel with the field so a later editor
        inherits the correction rather than the myth.
        """
        text = read(SKILL)
        start = text.index("run_in_background: false")
        window = text[max(0, start - 1200):start + 1200].lower()
        self.assertIn("cron", window)
        self.assertIn("refuted", window)


class TestTheRunStampsItsOwnSettings(unittest.TestCase):
    """A run that does not record its own model and effort cannot be used as
    evidence about either.

    The 2026-08-21 run of 395, 394, 396, 397 and 395b was the first trial of
    `medium` effort. `orchestrator_cost.py` read it at 1.51M weighted tokens per
    issue on 2026-08-23 — above the threshold that would have ended the effort
    question — and the reading was thrown away, because neither `run.md` nor
    `run-journal.md` contained the word "effort" anywhere. The model line was a
    habit that happened to hold; the effort line did not exist. These assertions
    make both a rule, so the next trial is readable.
    """

    def test_the_ledger_header_requires_both_stamps(self):
        skill = read(SKILL)
        for mark in ("Session model at launch:", "Session effort at launch:"):
            with self.subTest(mark=mark):
                self.assertIn(mark, skill)

    def test_the_launch_line_reads_the_effort_aloud(self):
        """The launch line is the interrupt window. A setting not named there
        cannot be corrected before spawn 1."""
        skill = read(SKILL)
        start = skill.index("The launch line is a gate")
        window = skill[start:start + 900].lower()
        self.assertIn("session model", window)
        self.assertIn("session effort", window)

    def test_the_void_trial_travels_with_the_rule(self):
        """A rule outlives the incident that made it, and a later editor who
        meets the rule without the measurement deletes it as ceremony. The
        1.51M reading is the measurement here."""
        skill = read(SKILL)
        start = skill.index("Session effort at launch:")
        window = skill[max(0, start - 600):start + 1200].lower()
        self.assertIn("1.51m", window)
        self.assertIn("2026-08-21", window)


class TestTheBridgeCseChangesSurvive(unittest.TestCase):
    """Six changes the human approved on 2026-08-24, after run `bridge-cse` ran 7h49m
    against an estimate of 3h15m to 4h45m.

    Two are guards with their own tests. Four are prose, and prose is what an
    ordinary edit drops without anything going red. Each assertion below pins the
    part a later editor would delete as ceremony, and pins its measurement beside
    it, because a rule met without its evidence reads as ceremony and gets
    deleted for it.
    """

    def test_both_new_guards_are_on_disk_and_named_in_the_skill(self):
        skill = read(SKILL)
        for script in ("check_issue_ready.py", "check_harden_branch.py"):
            self.assertTrue((RUN_ISSUES / script).exists(), f"{script} is missing")
            self.assertIn(script, skill, f"{script} is not named in the skill")

    def test_the_criteria_gate_keeps_its_override_and_its_measurement(self):
        """An override with no cost printed is a rubber stamp, and a refusal with
        no measured base rate reads as an obstacle rather than a cheap check."""
        skill = read(SKILL)
        start = skill.index("Criteria gate")
        window = skill[start:start + 2000]
        self.assertIn("--override", window)
        self.assertIn("32 issue files", window)
        self.assertIn("ready-for-agent", window)

    def test_the_criteria_gate_does_not_claim_to_replace_the_stamp(self):
        """The human ruled on 2026-08-21 that an explicitly named issue always runs,
        stamped or not. This guard checks a different thing and must keep saying
        so, or the next reader takes it for an overturn."""
        skill = read(SKILL)
        start = skill.index("Criteria gate")
        window = skill[start:start + 2000]
        self.assertIn("2026-08-21", window)

    def test_the_concurrency_gate_names_the_run_it_was_earned_on(self):
        skill = read(SKILL)
        start = skill.index("Concurrency gate")
        window = skill[start:start + 1600]
        self.assertIn("bridge-cse", window)
        self.assertIn("harden-issues", window)

    def test_the_two_copy_hazards_are_stated_as_facts_not_warnings(self):
        """Neither is guessable from the command. `cp -al` hard-links, so a write
        in the copy lands in the worktree; the rsync copy's `node_modules`
        symlink resolves back to the real directory. Both cost run `bridge-cse`
        something on 2026-08-24."""
        skill = read(SKILL)
        self.assertIn("HARD LINKS", skill)
        self.assertIn("TWO-WAY DOOR", skill)
        for mark in ("17:05", "vitest transform cache"):
            self.assertIn(mark, skill)

    def test_the_git_exclusion_carries_its_fix_and_not_only_its_warning(self):
        """The `.git` exclusion is deliberate and measured (87 MB against a 66 MB
        copy). What makes it safe is that the two affected cases skip and the
        script refuses by name. An editor who deletes the fix meets the reason."""
        skill = read(SKILL)
        self.assertIn("87 MB", skill)
        self.assertIn("REFUSED no-git-repository", skill)
        self.assertIn("check-issue-citations.test.ts", skill)

    def test_the_prose_deletion_rule_keeps_all_four_conditions(self):
        """Dropping any one of them turns a narrow saving into a road for
        skipping correction rounds generally."""
        skill = read(SKILL)
        start = skill.index("Where EVERY owed item is prose")
        window = skill[start:start + 2600]
        for condition in (
            "grades the behaviour correct",
            "non-executable",
            "delete-only",
            "by grep",
        ):
            self.assertIn(condition, window)

    def test_the_prose_deletion_rule_records_why_it_is_not_a_register_row(self):
        """The human approved the register-row shape. It was built as a deletion
        because promotion refuses `audience: agent` at any severity, so a false
        comment filed as a row would ship and never be repaired. An editor who
        meets the rule without that reason will "restore" their words and reopen
        the hole."""
        skill = read(SKILL)
        start = skill.index("Where EVERY owed item is prose")
        window = skill[start:start + 2600]
        self.assertIn("audience: agent", window)
        self.assertIn("promotion.md", window)


if __name__ == "__main__":
    unittest.main()
