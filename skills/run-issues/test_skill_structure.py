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
# The promotion and attacker briefs live in `agents/` beside `skills/`, so
# `SKILLS` does not reach them. This file already names
# `~/.claude/agents/promotion.md` once, but only as a string to search for.
AGENTS = SKILLS.parent / "agents"

SKILL = RUN_ISSUES / "SKILL.md"
FINALE = RUN_ISSUES / "finale.md"
DECISIONS = RUN_ISSUES / "decisions.md"
RESUME = RUN_ISSUES / "resume.md"
# Ticket 33 of the pilot-delivery map, ruling 16, ruled by the human 2026-09-07.
# The launch hardening phase, off the common path for the same reason the
# finale is: a run with nothing unstamped in scope never opens it.
LAUNCH_HARDEN = RUN_ISSUES / "launch-harden.md"

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

# Sentences that live inside the launch hardening phase and nowhere else.
# Same shape as FINALE_MARKS: present in `launch-harden.md`, absent from
# SKILL.md. The phase is a full load, paid only by a run that has an unstamped
# issue in scope, so a paste-back into SKILL.md bills every other run for it.
LAUNCH_HARDEN_MARKS = [
    # Ruling 21 -- the wave recipe, read at spawn time.
    "Five attackers at a time, and no more.",
    "Nothing is dropped to fit the cap",
    # Ruling 3 -- the split.
    "A split this phase can complete is cut here",
    "A split that changes a migration's direction is a drop",
    # Rulings 4 and 11 -- the three drop classes, and the closed list.
    "Only three things drop an issue from this run",
    "Every other fork takes its recommended default",
    # Ruling 10 -- the commit.
    "Harden at launch: NN, NN",
    # Ruling 12 -- what the run owes the merge briefing.
    "Every default this phase took is an item under",
    # Ruling 15 -- one pass at launch, never one before each implementer.
    "every unstamped issue in scope, at launch, in one pass",
    # Ruling 18 -- no off switch.
    "There is no off switch on the command line.",
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
    # Ticket 39 ruling 10 REVERSED this rule on 2026-09-05. The mark used to be
    # "never pass a `model:` value on a spawn", which the rewritten bullet still
    # quotes while describing the reversal -- so the old mark passed while
    # guarding a sentence that states the opposite of the rule.
    "Every spawn carries its own role's model, read off the ledger",
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
        # The INTERIM R2 block was here. Its expiry was met: issue 379 shipped in
        # run batch-375cbf, merged 2026-09-01, and the block was replaced with the
        # pinned background pass on the human's ruling of the same day. A guard that
        # demands text a met expiry deleted is a guard against the wrong thing.
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
        return sorted(SKILLS.glob("*/SKILL.md")) + [FINALE, RESUME, LAUNCH_HARDEN]

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


class TheRunPictureLandsOnBothSurfaces(unittest.TestCase):
    """Issue 506. A finished run showed the human nothing at a glance.

    Run `batch-88624c` handed them a 1963-line briefing. Of the six things they
    look for afterwards, three sat past line 1700 and they found none of them;
    the second time that happened it cost four cost measurements they had
    commissioned the day before. The finale now writes `## The run in one
    screen` at the top of the briefing and the board renders it as a panel.

    These read the live `finale.md`, like every other check in this file. A
    fixture would pass while the real instructions drifted, which is the whole
    failure being guarded.
    """

    def board_step(self):
        """Just the board step, cut at the next numbered step.

        Slicing to the end of the file would let a sentence in a LATER step
        satisfy these checks, which is the fault they exist to catch.
        """
        finale = read(FINALE)
        start = finale.index("**Regenerate the action board**")
        after = re.search(r"\n\d\. \*\*", finale[start:])
        return finale[start:start + after.start()] if after else finale[start:]

    def test_the_finale_is_told_to_write_the_block(self):
        self.assertIn("## The run in one screen", read(FINALE))

    def test_the_finale_is_told_to_render_the_panel_on_the_board(self):
        self.assertIn("The run in one screen", self.board_step())

    def test_the_block_is_named_as_the_only_place_a_figure_is_derived(self):
        """Item 6a. A panel that counts for itself re-creates the fault 6b
        refuses, and the licence for a cheap model rests on the render having no
        judgement in it."""
        board_step = self.board_step()
        self.assertIn("never counts", board_step)
        self.assertRegex(board_step, r"single place a figure\s+is\s+derived")

    def test_the_comparison_guard_is_named_and_on_disk(self):
        """Item 6b, and the only part of item 6 that catches a false number at
        any model."""
        self.assertIn("check_run_picture.py", self.board_step())
        self.assertTrue((RUN_ISSUES / "check_run_picture.py").exists())

    def test_the_cost_measurement_runs_before_the_board(self):
        """Item 3. The panel carries the wall clock, so at render time
        `## What this run cost` has to exist already. It used to be written two
        steps after the board."""
        finale = read(FINALE)
        self.assertLess(
            finale.index("run_costs.py"),
            finale.index("**Regenerate the action board**"),
        )

    def test_the_board_spawn_still_names_a_model_explicitly(self):
        """Item 6c changes WHICH model, never the rule that one is named. An
        unnamed spawn inherits the session model, which is what this step was
        written to stop."""
        board_step = self.board_step()
        self.assertRegex(board_step, r'model: "\w+"')
        self.assertIn("Naming the model is not optional", board_step)

    def test_the_board_step_tells_the_renderer_to_draw_the_rail(self):
        """Issue 553. The rail is the picture the human reads first, and step 5 is
        where it is drawn. Naming the block it is copied from is what keeps the
        transcription rule true of cards as well as figures: the renderer does
        not read a diff, does not read an issue file, and does not work out
        which stage a screen belongs to."""
        board_step = self.board_step()
        self.assertIn("## The run on the rail", board_step)
        self.assertIn("draw_run_rail.py", board_step)
        self.assertTrue((RUN_ISSUES / "draw_run_rail.py").exists())

    def test_the_transcription_rule_covers_cards_and_not_only_figures(self):
        """`The panel transcribes. It never counts.` predates the rail. A card
        carries a stage and a kind, which are judgements, and the sentence has
        to say so in those words or the next renderer infers a stage from a
        diff and re-creates the fault item 6a removed."""
        board_step = self.board_step()
        self.assertRegex(board_step, r"transcribes[^.]*\. It never counts")
        self.assertRegex(board_step, r"card[s]?\b")
        self.assertIn("never works out", board_step)

    def test_the_rail_is_drawn_by_a_script_and_not_by_the_model(self):
        """The human ruled this on 2026-09-04. The drawn shape is computed geometry
        with two assertions in it, and a subagent briefed in prose cannot
        assert, so the criterion that an overflowing card must FAIL rather than
        reach a browser clipped is true on this road and on no other."""
        board_step = self.board_step()
        self.assertIn("The script is the only road to it", board_step)

    def test_the_model_line_carries_the_two_limits_of_its_measurement(self):
        """The Fable reading is one measurement of a checking task, not a trend
        and not an HTML render. The issue requires both limits stated wherever it
        is cited, or the citation outgrows its evidence. It is still cited: it
        is why the render is not dropped further than Opus."""
        board_step = self.board_step()
        self.assertIn("citation-recheck-fable.md", board_step)
        self.assertIn("one reading", board_step)

    def test_the_board_render_is_pinned_to_opus(self):
        """Ruled by the human 2026-09-06, closing `q-t39-s2-1`. The pin was
        `fable`, and ruling 14 of ticket 39 made `fable` the top tier, so the
        pin named the most expensive model for the cheapest job in the
        pipeline. Measured on run `batch-b5e96d`: the render cost 0.30M
        weighted tokens against the run's 149.70M."""
        self.assertIn('model: "opus"', self.board_step())
        self.assertNotIn('model: "fable"', self.board_step())

    def test_the_skill_file_names_the_same_model_as_the_finale(self):
        """These two drifted apart before. The review of sitting 2 found
        `SKILL.md` still citing `haiku` and a line number about migration
        `0086`, months after the finale had moved on. One rule, two files, and
        nothing compared them until this."""
        skill = read(SKILL)
        self.assertIn('model: "opus"', skill)
        self.assertNotIn('requires\n  `model: "fable"`', skill)

    def test_the_pin_no_longer_justifies_itself_by_the_top_tier(self):
        """The justifying sentence said an unnamed spawn "pays the top tier",
        written when the session was Opus and the pin was Haiku. Ruling 14 then
        fixed the tier order as haiku < sonnet < opus < fable, so that sentence
        read backwards against its own pin. The tier order ranks REVIEW
        AUTHORITY, never price, and the sentence has to say which it means."""
        board_step = self.board_step()
        self.assertNotIn("pays the top tier", board_step)
        self.assertNotIn("paying the top tier", board_step)


class TheDailyBriefShowsWhatTheRunCost(unittest.TestCase):
    """Issue 506 item 5. The cost table existed and nothing read it.

    `run_costs.py` appends a row per run to `.scratch/workflow-audit/run-costs.md`
    and that file says what it is for: compare a row against the row above it.
    Measured 2026-08-31, the only files naming it were inside the run-issues
    skill. The brief never opened it, so the finale printed the cost at line 1790
    of 1963 and a second print in the same document was never the fix.
    """

    def section_one(self):
        text = read(SKILLS / "daily-brief" / "SKILL.md")
        return text[text.index("### 1. Merge reads"):text.index("### 1b.")]

    def test_section_one_reads_the_cost_table(self):
        self.assertIn(".scratch/workflow-audit/run-costs.md", self.section_one())

    def test_it_compares_against_the_previous_line_of_the_same_kind(self):
        """Inverted by ticket 37 sitting 4, and the inversion is the point.

        This test used to assert the section said "the row above it", which was
        the table's own rule and is now wrong twice over. Ruling 12 compares a
        line against the previous line of the SAME KIND by finale time: ticket
        38 puts two runs and a hunt in flight at once, so position in the file
        is not order of finishing, and ruling 11 puts hunts in the same file.
        Ruling 27 deletes the old rule with its cause.
        """
        section = self.section_one()
        self.assertNotIn("the row above", section)
        self.assertIn("SAME KIND", section)
        self.assertIn("run_compare.py last", section)

    def test_the_brief_holds_no_reader_of_its_own(self):
        """Ruling 27: one reader. Two readers of one file disagree eventually,
        which is what `journal_for` taught ticket 39 in sitting 2."""
        self.assertIn("only reader", self.section_one())

    def test_it_invents_no_alarm_threshold(self):
        """Even inside the old borrowed numbers, consecutive rows swung by up
        to 75 per cent. A 25 per cent flag would fire on seven of twelve
        transitions and train them to ignore it."""
        self.assertIn("Invent no alarm threshold", self.section_one())

    def test_it_refuses_the_old_per_issue_range_instead_of_quoting_it(self):
        """Inverted on 2026-09-06, and the inversion is the point.

        This test used to assert that the section QUOTED 0.96M to 2.45M as an
        observed range. That range was never observed. Before skills commit
        aa94b3b, run_costs.py scraped five of its columns out of
        `orchestrator_cost.py --days 7`'s last data row, whatever run that row
        described, so `Issues`, `Subagents`, `Weighted`, `Orchestrator` and
        `Per issue` were all borrowed. The section must now forbid the range,
        not repeat it, and it must say where the fault was fixed.

        Narrowed by ticket 37 sitting 4. The "read no row above 2026-09-06"
        phrase went with the date rule behind it: sitting 2 measured that the
        mark is a property of the LINE and not of the day -- divide `Weighted`
        by `Per issue` and see whether it lands on the line's own `Issues` --
        so `run_compare.py` reads the mark per line and the brief no longer
        asks a reader to date a row.
        """
        section = self.section_one()
        self.assertIn("aa94b3b", section)
        self.assertIn("measured, not dated", section)
        self.assertIn("you must not invent one", section)

    def test_it_names_which_columns_were_borrowed_and_which_were_not(self):
        """A reader who does not know WHICH columns are affected will either
        distrust the whole table or trust the wrong half. Hours and Idle came
        from the run's own transcript and survive."""
        section = self.section_one()
        for column in ("`Issues`", "`Subagents`", "`Weighted`",
                       "`Orchestrator`", "`Per issue`"):
            self.assertIn(column, section)
        self.assertIn("`Idle` and `Hours` survive intact", section)

    def test_it_gives_the_arithmetic_that_exposes_a_borrowed_row(self):
        """The fault is checkable without reading the script's history: a
        finale passing --issues N overrode the borrowed issue count while
        Weighted and Per issue stayed borrowed, so the two divide to 85-114
        and never to the row's own Issues cell."""
        self.assertIn("85 and 114", self.section_one())

    def test_idle_is_still_declared_not_to_be_a_trend(self):
        """Four readings now: 12, 17, 10 and 23 per cent. Idle was never
        borrowed, so the readings stand -- but four is still not a trend, and
        that was the original point of this test."""
        self.assertIn("still not a trend", self.section_one())

    def test_the_block_stays_inside_section_one(self):
        """The brief has thirty minutes and this must not become a fifth
        section."""
        text = read(SKILLS / "daily-brief" / "SKILL.md")
        self.assertNotIn("### 1c.", text)


class AnIssueCarriesTheOneLineItsCardWillDraw(unittest.TestCase):
    """Issue 551. Every card on a run's rail needs a sentence, and until now
    nothing wrote one.

    Ticket 34 priced two roads for that sentence: the finale compresses sixteen
    titles at run end, or the author writes one line when the issue is cut and
    the finale transcribes it. `~/.claude/CLAUDE.md` prefers the second, because
    a fact written once beats a fact re-derived and a transcription is not a
    judgement the renderer has to make.

    The bound is `59 characters or fewer`, never "under 60". Issue 552's
    `check_run_rail.py` refuses at 60, so a sentence of exactly 60 characters is
    legal under the looser phrase and refused by the only guard that counts.

    These read the live files, like every other check here. A fixture would pass
    while the real template drifted, which is the whole failure being guarded.

    Three cases, one per author of the field: `/to-issues` writes it, promotion
    stamps it, `/harden-issues` may repair it.
    """

    WINDOW = 400
    # The bound, spelled out. Asserting the bare "59" would be satisfied by a
    # year, a line number or a percentage that drifts past the field one day.
    BOUND = "`59 characters or fewer`"
    # The phrase the batch's only mechanical guard disagrees with. Forbidden
    # across the whole document, not just beside the field: a rival bound stated
    # anywhere in these four files is what this issue exists to stop.
    RIVAL = "under 60"

    def template(self):
        """Just the `<issue-template>` block.

        Slicing the whole SKILL.md would let a mention in the prose around the
        template satisfy these checks, and the prose is not what `/to-issues`
        copies into an issue file.
        """
        path = SKILLS / "to-issues" / "SKILL.md"
        if not path.exists():
            # This pack does not ship `to-issues` (see MANIFEST.md: it is a fork
            # of an upstream skill). Where it is installed beside the pack, the
            # check runs; where it is not, there is no template to grade.
            self.skipTest("no to-issues skill installed beside this pack")
        text = read(path)
        start = text.index("<issue-template>")
        return text[start:text.index("</issue-template>", start)]

    def rule_after(self, text, where):
        """The characters that state the field's rule, from the field onward.

        Squashed first, like the class-A and class-B marks above. A markdown
        paragraph rewraps whenever anyone edits the line before it, and a guard
        that a rewrap can break is a guard that reports the wrong thing.

        `where` names the document, so a missing field fails with the file that
        lost it instead of a bare "substring not found".
        """
        rule = squash(text)
        self.assertIn("Sentence:", rule, f"{where} names no `Sentence:` field")
        self.assertNotIn(self.RIVAL, rule, f"{where} states a rival bound")
        return rule[rule.index("Sentence:"):][:self.WINDOW]

    def test_the_issue_template_carries_the_field_and_its_rule(self):
        """`/to-issues` writes the line. A length with no shape gives an author a
        59-character noun phrase, and a card needs a sentence saying what the
        change does."""
        rule = self.rule_after(self.template(), "the `/to-issues` template")
        self.assertIn(self.BOUND, rule)
        for word in ("subject", "verb", "present tense"):
            with self.subTest(word=word):
                self.assertIn(word, rule)

    def test_promotion_is_told_to_write_the_field(self):
        """Promotion mints issue files from register rows and a row carries a
        description it can compress. It already stamps `Owed: unsorted` in the
        same header, so this is the same stamp in the same place.

        `Owed:` is written only where the project holds a `milestones.md`. Every
        project's run draws cards, so the sentence carries no such condition, and
        copying `Owed:`'s wording would silently lose the field on a project with
        no milestones file.
        """
        rule = self.rule_after(read(AGENTS / "promotion.md"), "the promotion brief")
        self.assertIn(self.BOUND, rule)
        self.assertIn("milestones.md", rule)

    def test_the_harden_pass_may_rewrite_the_line_in_place(self):
        """The attacker brief is append-only outside the two graded sections and
        refuses the `Status:` and `Hardened:` header lines outright. Without an
        explicit grant a missing or over-long sentence is a finding no attacker
        may fix, and the title it compresses is already written.

        The grant is one line wide. The two lines the brief never owned stay
        refused, so a half-finished pass is never mistaken for a complete one.
        """
        for path in (SKILLS / "harden-issues" / "SKILL.md",
                     AGENTS / "harden-issues-attacker.md"):
            with self.subTest(path=path.name):
                rule = self.rule_after(read(path), path.name)
                self.assertIn("in place", rule)
                self.assertIn(self.BOUND, rule)
        attacker = read(AGENTS / "harden-issues-attacker.md")
        self.assertIn("Never touch the", attacker)
        self.assertIn("`Status:` or `Hardened:` lines", attacker)


class TheBriefingSaysWhereEachIssueLanded(unittest.TestCase):
    """Issue 552. Picture D needs a stage, a kind and a sentence per shipped
    issue, and deciding those is judgement the renderer may not have.

    `finale.md` step 5 licenses the board's cheap render on "The panel
    transcribes. It never counts." A renderer that worked out where issue 516
    lands would break that rule and expire the licence with it. So the finale
    writes `## The run on the rail` under the one-screen block at the end of
    step 4, and `check_run_rail.py` refuses a block the renderer could not copy.

    These read the live `finale.md`, like every other check in this file.
    """

    RAIL_MARK = "**Then write `## The run on the rail`"

    def rail_step(self):
        """From the rail instruction to the board step, and no further.

        Slicing to the end of the file would let the board step's own command
        satisfy the no-other-command check below, which is the fault it exists
        to catch.
        """
        finale = read(FINALE)
        start = finale.index(self.RAIL_MARK)
        return finale[start:finale.index("**Regenerate the action board**", start)]

    def board_step(self):
        finale = read(FINALE)
        start = finale.index("**Regenerate the action board**")
        after = re.search(r"\n\d\. \*\*", finale[start:])
        return finale[start:start + after.start()] if after else finale[start:]

    def test_the_finale_is_told_to_write_the_rail_below_the_one_screen_block(self):
        finale = read(FINALE)
        one_screen = finale.index("**Then write `## The run in one screen`")
        rail = finale.index(self.RAIL_MARK)
        board = finale.index("**Regenerate the action board**")
        self.assertLess(one_screen, rail)
        self.assertLess(rail, board)
        self.assertIn("below the whole of", squash(self.rail_step()))

    def test_the_finale_is_told_to_run_the_check_and_it_is_on_disk(self):
        step = self.rail_step()
        self.assertIn("check_run_rail.py", step)
        self.assertIn("--stages docs/agents/run-picture-stages.md", step)
        self.assertTrue((RUN_ISSUES / "check_run_rail.py").exists())

    def test_the_rail_step_adds_no_command_but_the_check(self):
        """Cut the way `board_step()` cuts, then every `python3` invocation in
        the step must be the one check and there must be no `node` one."""
        step = self.rail_step()
        commands = re.findall(r"python3\s+(\S+)", step)
        self.assertTrue(commands, "the step names no python3 command at all")
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(command.endswith("check_run_rail.py"), command)
        self.assertNotRegex(step, r"\bnode\s+\S+\.mjs")

    def test_the_step_states_the_cost_instead_of_denying_it(self):
        """Ticket 34 priced it at sixteen judgements a run with the sentence as
        the real cost. "Adds no new measurement" is prose every build satisfies."""
        step = squash(self.rail_step())
        self.assertIn("judgements a run", step)
        self.assertIn("the real cost", step)
        self.assertNotIn("adds no new measurement", step.lower())

    def test_the_panel_transcribes_sentence_survives_in_the_board_step(self):
        """`test_the_block_is_named_as_the_only_place_a_figure_is_derived`
        asserts "never counts". The sentence before it was asserted nowhere,
        and it is the licence the whole slice exists to keep."""
        self.assertIn("The panel transcribes.", self.board_step())

    def test_the_shipped_line_is_pinned_as_a_required_field(self):
        """The check reads the shipped list from the one-screen block's
        `Shipped:` line and from nowhere else, and that line was absent from
        the live `batch-44d0a8` briefing."""
        self.assertIn("`Shipped:` line is a required field", squash(read(FINALE)))

    def test_the_stage_is_judged_from_what_the_change_is_about(self):
        """The refuted premise was that the verify gate names the screen. It
        sweeps every route the diff touches: 488's list spans five stages and
        486's is empty. The gate's list is evidence, never the decision."""
        step = squash(self.rail_step())
        self.assertIn("what the change is about", step)
        self.assertIn("`Drove:`", step)
        self.assertIn("evidence", step)
        self.assertNotIn("names the screen it walked", step)

    def test_floor_means_what_no_user_sees_and_a_band_member_never_takes_it(self):
        step = squash(self.rail_step())
        self.assertIn("no user", step)
        self.assertIn("inside its band's span", step)

    def test_the_bound_is_stated_as_a_refusal_and_the_fallback_as_the_normal_case(self):
        step = squash(self.rail_step())
        self.assertIn("59 characters or fewer", step)
        self.assertNotIn("under 60", squash(read(FINALE)))
        self.assertIn("`Sentence:`", step)
        self.assertIn("normal case", step)

    def test_the_ledger_chain_is_untouched(self):
        """The rail is written in step 4 while the ledger reads
        `finale-promotion`. No stage is added, renamed or reordered."""
        import check_finale_stage
        self.assertEqual(
            check_finale_stage.CHAIN,
            ["finale-mechanical", "finale-judgment", "finale-promotion",
             "finale-board", "awaiting-merge"],
        )



class TheHolesAndTheQuestionsLandOnTheRail(unittest.TestCase):
    """Issue 554. The rail drew shipped issues only. Two more things belong on
    it — an issue the run left open, and a question waiting on the human — and one
    does not, which is the register.

    These read the live `finale.md` and the live promotion brief, like every
    other check in this file.
    """

    MINTED_MARK = "### Minted and left open"
    FORKS_MARK = "### Forks waiting on you"

    def rail_step(self):
        finale = read(FINALE)
        start = finale.index("**Then write `## The run on the rail`")
        return finale[start:finale.index("**Regenerate the action board**", start)]

    def test_the_rail_step_names_both_tables(self):
        step = self.rail_step()
        for mark in (self.MINTED_MARK, self.FORKS_MARK):
            with self.subTest(mark=mark):
                self.assertIn(mark, step)

    def test_the_register_is_named_as_the_thing_that_is_never_drawn(self):
        """Criterion 7, and it is the answer to their third question. Every
        register row ends fixed, promoted, refused or dropped below the floor,
        and a fifth road never reaches promotion at all. The one fact left over
        is "none left", which the one-screen block already carries."""
        step = squash(self.rail_step())
        self.assertIn("register", step.lower())
        self.assertIn("Register rows left", step)
        for bucket in ("refused", "fixed", "dropped"):
            with self.subTest(bucket=bucket):
                self.assertIn(bucket, step.lower())

    def test_the_one_screen_counts_are_named_as_unchanged(self):
        """`Forks to decide`, `Issues minted` and `Register rows left` are what
        `/daily-brief` reads and issue 506 shipped them. This slice adds rows
        below them and changes none of them."""
        step = squash(self.rail_step())
        self.assertIn("Forks to decide", step)
        self.assertIn("Issues minted", step)

    def test_the_fork_numbering_rule_is_stated_beside_the_table(self):
        """The seam pass's finding: a fork key must be unique across the WHOLE
        briefing. Every one of the five drawn runs carries TWO `## Decide`
        headings, each numbering its items from 1, so `F1` alone is not a key."""
        step = squash(self.rail_step())
        self.assertIn("unique", step)
        self.assertIn("whole briefing", step)

    def test_the_card_question_is_named_as_a_compression(self):
        """It is not the `## Decide` heading copied. On `batch-45c8b1`, the one
        drawn run whose Decide items are questions at all, five of the six
        headings run 61 to 89 characters against a card that holds 60."""
        step = squash(self.rail_step())
        self.assertIn("compression", step)
        self.assertIn("59 characters or fewer", step)
        self.assertNotIn("under 60", squash(read(FINALE)))

    def test_a_run_with_neither_omits_the_tables_rather_than_printing_them_empty(self):
        step = squash(self.rail_step())
        self.assertIn("omit", step.lower())

    def test_promotion_is_told_to_write_the_stage(self):
        """Criterion 6. The brief's minting list named no stage, so every issue
        promotion minted reached the next run's rail with nowhere to land.

        Like `Sentence:` and unlike `Owed:`, the field carries no
        `milestones.md` condition: every project's run draws a rail, so a
        project with no milestones file would silently lose it.
        """
        brief = squash(read(AGENTS / "promotion.md"))
        self.assertIn("Stage:", brief)
        rule = brief[brief.index("Stage:"):][:900]
        self.assertIn("run-picture-stages.md", rule)
        self.assertIn("floor", rule)
        self.assertIn("milestones.md", rule)

    def test_promotion_is_told_the_stage_is_a_transcription_not_a_guess(self):
        """The brief's own standing rule is that promotion decides on the row
        and never reads code. A stage it cannot honestly name is `floor`, which
        is the explicit answer rather than a guess at a journey."""
        brief = squash(read(AGENTS / "promotion.md"))
        rule = brief[brief.index("Stage:"):][:900]
        self.assertIn("transcription", rule)

    def test_the_stage_vocabulary_file_is_never_copied_into_a_brief(self):
        """Rule 1 of `docs/agents/run-picture-stages.md`: a skill reads that
        file and never hard-codes a stage key. `floor` is the one exception and
        it is named as the null, not as a vocabulary."""
        for path in (FINALE, AGENTS / "promotion.md"):
            with self.subTest(path=path.name):
                text = read(path)
                for key in ("needs-you", "catalogue"):
                    self.assertNotIn(f"`{key}`", text.split("## The run on the rail")[0])



class TheFinaleStatesTheBandAndItsFloor(unittest.TestCase):
    """Issue 555. `grep -c "band" finale.md` returned 0 on 2026-09-03, so every
    assertion here failed before this slice.

    Two things must be on the file's face. The floor, because the first run
    that draws a silly band is then answered by changing one number rather than
    by re-arguing the shape. And that a run may state NO bands, because two of
    the five runs the picture draws have none, and a later session reading an
    absent table as a bug starts lowering the threshold instead.
    """

    def rail_step(self):
        finale = read(FINALE)
        start = finale.index("**Then write `## The run on the rail`")
        return squash(finale[start:finale.index("**Regenerate the action board**", start)])

    def test_the_bands_table_is_named(self):
        self.assertIn("### Bands", self.rail_step())
        self.assertIn("### Band chips", self.rail_step())

    def test_the_floor_is_stated_as_a_number(self):
        step = self.rail_step()
        self.assertIn("two issues across two", step)

    def test_no_band_is_stated_as_a_normal_answer(self):
        step = self.rail_step()
        self.assertIn("may state no bands", step)

    def test_the_floor_is_marked_provisional_and_not_as_an_invention_guard(self):
        """It rests on five runs and no counter-example, and nothing derives a
        band, so the floor is only ever a refusal of a shape. A later session
        citing it as the thing that stopped a made-up subject would be wrong."""
        step = self.rail_step()
        self.assertIn("provisional", step)
        self.assertIn("nothing derives a band", step)

    def test_the_renderer_is_told_it_draws_bands_and_never_finds_them(self):
        """The rule the cheap-model licence rests on. A renderer that grouped
        issues by colour or by shared stage and called the group a band would
        have broken it, and with it what issues 552 and 553 both stand on."""
        board = squash(read(FINALE))
        self.assertIn("never counts, and neither does the rail", board)
        self.assertIn("draws bands, it never finds them", board)


class TheFinaleTakesTheReadingByBatchId(unittest.TestCase):
    """Ticket 39 of the pilot-delivery map, sitting 3, ruling 12.

    `--run` matched the run's name against the PROJECT DIRECTORY name, which
    holds only while a worktree is named after the run inside it. Two rows of
    `.scratch/workflow-audit/run-costs.md` say it did not: 2026-09-02 and
    2026-09-05 each carry "the worktree was reused and its name does not match
    the branch, so --transcript had to be passed by hand". Run `batch-b5e96d`
    ran in a worktree called `run-issues-414a-99f-286335`.

    Prose is asserted against whitespace-collapsed text. A sentence in a
    markdown file is wrapped where the column runs out, so a raw substring
    check pins the line breaks as though they were the rule.

    These read the live `finale.md`, like every other check in this file.
    """

    def setUp(self):
        self.finale = read(FINALE)
        self.flat = " ".join(self.finale.split())

    def test_the_cost_reading_is_taken_by_batch_id(self):
        self.assertIn("run_costs.py --batch <batch-id>", self.finale)

    def test_the_harness_reading_is_taken_by_batch_id_too(self):
        """It matched a worktree-name fragment against a hard-coded
        one repository's prefix, so it could measure that repository alone and could not
        find run `batch-b5e96d` at all."""
        self.assertIn("harness_cost.py --batch <batch-id>", self.finale)

    def test_the_finale_says_why_a_run_name_is_not_the_road(self):
        self.assertIn("does not match the branch", self.flat)

    def test_the_finale_states_that_no_figure_spans_two_models(self):
        """Ruling 11, and the human's ruling of 2026-09-06: record everything,
        display everything per model, refuse only the merged total."""
        self.assertIn("cross-model multiplier", self.flat)
        self.assertIn("compare the SAME ROLE across runs", self.flat)

    def test_the_finale_sends_him_to_usage_for_money(self):
        """Ruling 11 keeps the dollar figure out of every script, so the
        finale has to say where the dollar figure actually is."""
        self.assertIn("For money, read `/usage` by hand", self.flat)

    def test_the_finale_asks_for_both_new_tables(self):
        """Ruling 15: a model column per role, and one row per subagent."""
        self.assertIn("One row per subagent", self.flat)
        self.assertIn("per role and per model", self.flat)

    def test_the_two_table_paragraph_is_written_once(self):
        """It stood twice, back to back, from sitting 3 until 2026-09-06.

        A rule written twice is a rule that can be repaired in one copy, and
        the reader then obeys whichever they reach first.
        """
        self.assertEqual(self.flat.count("ones a model trial is read from"), 1)


class TheFinaleWritesTheTrialTable(unittest.TestCase):
    """Ticket 39, sitting 4, deliverable 4 and rulings 13, 15, 21.3 and 22.

    `model-landed-check.py` has written one line per spawn into the run journal
    since sitting 2 and, until this sitting, nothing read them. These pin the
    three sentences that decide how the finale reads them.
    """

    def setUp(self):
        self.finale = read(FINALE)
        self.flat = " ".join(self.finale.split())
        self.hunt = " ".join(read(SKILLS / "parallel-hunt" / "SKILL.md").split())
        self.skill = " ".join(read(SKILL).split())

    def test_the_finale_takes_the_trial_reading_by_batch_id(self):
        self.assertIn("run_quality.py --batch <batch-id>", self.finale)

    def test_the_hunt_takes_it_too_and_before_the_brief_is_deleted(self):
        """Ruling 12 gives a hunt the same readings, and sitting 3's lesson
        holds harder here: this one also reads `round-journal.md`, which sits
        beside the brief the round end deletes."""
        self.assertIn("run_quality.py --batch <hunt-id>", self.hunt)
        self.assertIn("must happen before the brief is deleted", self.hunt)

    def test_the_table_is_named_as_read_from_the_transcripts(self):
        """Ruling 21.3. The ledger is the thing under test, so a table built
        from it agrees with the map by construction and could never fail."""
        self.assertIn("read from the TRANSCRIPTS, never from the ledger",
                      self.flat)

    def test_a_void_trial_is_named_as_halting_nothing(self):
        """Ruling 22, and the sentence a reader needs beside the word VOID."""
        self.assertIn("halts nothing, unmerges nothing", self.flat)
        self.assertIn("stops nothing and reverses nothing", self.hunt)

    def test_not_measured_is_named_as_not_a_pass(self):
        """The third state. Silence is a missing reading, never a clean run."""
        self.assertIn("must never be read as a pass", self.flat)
        self.assertIn("`not measured`, which is not a pass", self.skill)

    def test_the_strike_column_is_named_as_derived(self):
        """`SKILL.md` step 5's prose-deletion road and a runner-error
        annulment both cancel a strike in prose and write no marker."""
        self.assertIn("The strike column is derived and says so", self.flat)

    def test_the_skill_no_longer_says_nothing_reads_the_landed_lines(self):
        """It said so, and named sitting 4 as the owner. Sitting 4 has landed."""
        self.assertNotIn("Nothing yet READS those lines", self.skill)
        self.assertIn("run_quality.py` is what reads them", self.skill)


class TicketThirtySevenSittingThree(unittest.TestCase):
    """The step wrapper and the minted marker, pinned in the files that drive
    them. `SKILL.md` and `finale.md` have drifted apart on exactly this kind of
    line before -- ticket 39 sitting 2 found `SKILL.md` citing `finale.md:147`
    for the board render's model, where line 147 is about migration `0086`."""

    def setUp(self):
        self.finale = " ".join(read(FINALE).split())
        self.skill = " ".join(read(SKILL).split())

    def test_the_finale_runs_the_named_steps_under_the_wrapper(self):
        """Ruling 19. A step run bare leaves no duration anywhere: a
        backgrounded Bash call reads as instant in the transcript."""
        self.assertIn("run_step.py --batch <batch-id> --kind suite", self.finale)
        self.assertIn("run_step.py --batch <batch-id> --kind build", self.finale)
        self.assertIn("run_step.py --batch <batch-id> --kind citation", self.finale)
        self.assertIn("run_step.py --batch <batch-id> --kind board", self.finale)
        self.assertIn("run_step.py --batch <batch-id> --kind cost", self.finale)

    def test_every_kind_the_finale_names_is_one_the_wrapper_accepts(self):
        """The drift this class exists to catch, made mechanical: a kind typed
        into `finale.md` that `run_step.py` refuses would stop the finale at
        the step, and nothing else would have said so."""
        import re as _re
        import run_step
        for kind in _re.findall(r"run_step\.py [^`]*?--kind (\w+)", self.finale):
            with self.subTest(kind=kind):
                self.assertIn(kind, run_step.KINDS)

    def test_the_finale_says_the_runner_never_stamps_a_clock(self):
        """Ticket 36 ruling 3, and the whole reason this is a wrapper."""
        self.assertIn("You never write a clock yourself", self.finale)

    def test_the_finale_no_longer_says_the_counts_are_null_on_purpose(self):
        """It said so and named sitting 3 as the owner. Sitting 3 has landed."""
        self.assertNotIn("written null on purpose", self.finale)

    def test_the_runner_is_told_to_write_the_gate_round_marker(self):
        """Ruling 28's second half. A marker nothing writes is not a marker."""
        self.assertIn("gates <N>: verify=<pass|reject> review=<pass|reject>",
                      self.skill)

    def test_the_marker_the_skill_states_is_the_one_the_reader_reads(self):
        """The two live in different repositories' worth of files, and a token
        the skill spells one way and the reader matches another is a marker
        that silently never fires. So the skill's own example is run through
        the pattern."""
        import run_quality
        example = "attempt 1; gates 1: verify=pass review=reject"
        self.assertTrue(run_quality.GATE_ROUND.search(example))

    def test_the_skill_says_nothing_refuses_a_row_without_the_marker(self):
        """Ruling 3 loses no history: sixteen ledgers hold 143 rows written
        before it existed, and the prose reader stays for them."""
        self.assertIn("Nothing refuses a row without it", self.skill)

    def test_the_skill_says_the_strike_stays_derived(self):
        """Ruling 28 is explicit that minting the token does not make a strike
        countable: two roads cancel one in prose and write no marker."""
        self.assertIn("A strike is still DERIVED", self.skill)


class PromotionWritesTheOriginKey(unittest.TestCase):
    """Ticket 37 ruling 7, the issue half, built at ticket 33 sitting 1.

    Sitting 1 of ticket 37 gave seven briefs the register COLUMN and built
    `check_origin.py`. Its `--issue` mode had no caller: nothing wrote the key
    into an issue file, so an escaped fault could be counted at the row and lost
    at the file promotion minted from it. This is that caller.
    """

    def brief(self):
        return squash(read(AGENTS / "promotion.md"))

    def rule(self):
        """The Origin bullet, read from the key to the start of the next one.

        A fixed character window was 1200 and cut the paragraph that says the
        check is never run over the issue directory. Ending at the next bullet
        is what the rule actually occupies, so it cannot go silently stale as
        the text grows.
        """
        brief = self.brief()
        rule = brief[brief.index("Origin:"):]
        end = rule.find("- **A `## Target database` section.**")
        return rule[:end] if end > 0 else rule

    def test_promotion_is_told_to_write_the_origin_line(self):
        # assertTrue, not assertIn: the haystack is the whole brief, and a red
        # that buries its message under a 20 KB document is one people switch
        # off. Same convention as the harden-issues structure test.
        self.assertTrue("Origin:" in self.brief(),
                        "promotion.md names no `Origin:` key")

    def test_the_line_carries_both_halves_in_the_checkers_own_grammar(self):
        """`<issue>/<run>`. A shape only the writer understands is a key the
        check refuses on the file it was just written into."""
        self.assertIn("<issue>/<run>", self.rule())

    def test_unknown_is_stated_as_legal_for_either_half(self):
        """The explicit null, copied from `Owed: unsorted`. A writer with no
        legal way to say "I do not know" invents one, and the production watcher
        genuinely does not know either half."""
        self.assertIn("unknown", self.rule())

    def test_the_line_sits_in_the_header_beside_the_other_keys(self):
        """`check_origin.py` reads only what is ABOVE the title. A key written
        below it is body prose, whatever it is called."""
        rule = self.rule()
        self.assertIn("header", rule)
        self.assertIn("Owed:", rule)

    def test_promotion_runs_the_check_on_the_file_it_just_wrote(self):
        """The rule without its caller is the remember class. `check_origin.py
        --issue` grades one file promotion has just written."""
        rule = self.rule()
        self.assertIn("check_origin.py", rule)
        self.assertIn("--issue", rule)

    def test_the_check_is_run_before_the_row_is_closed(self):
        """A row closed on an ungraded file is a fault nobody comes back to:
        the register row is gone and the issue file is the only record left."""
        self.assertIn("before you close the row", self.rule())

    def test_the_brief_says_the_check_is_never_run_over_the_issue_directory(self):
        """The check backfills nothing on purpose. Pointing it at the tracker
        would refuse every issue minted before 2026-09-07, which is a check
        people learn to ignore."""
        self.assertIn("never over the issue directory", self.rule())


class TheLaunchHardenPhaseIsOffTheCommonPath(unittest.TestCase):
    """Ticket 33 of the pilot-delivery map, sitting 2. Rulings 9, 16 and 18.

    Deliverable 3 folds the hardening pass into a run's launch. Ruling 16 put
    the phase in its own file for the same reason the finale sits in one: it is
    a full load, and a run whose scope is entirely stamped must not be billed
    for reading it. That split breaks in two ways nobody would notice by
    reading either file -- the body gets pasted back into SKILL.md, or the
    trigger line goes and the file is never opened. These are the refusal.
    """

    def test_the_phase_file_exists_beside_the_skill(self):
        self.assertTrue(LAUNCH_HARDEN.is_file(), f"{LAUNCH_HARDEN} does not exist")

    def test_every_phase_sentence_lives_in_the_phase_file(self):
        phase = squash(read(LAUNCH_HARDEN))
        for mark in LAUNCH_HARDEN_MARKS:
            with self.subTest(mark=mark):
                self.assertTrue(
                    squash(mark) in phase,
                    f"the phase file no longer carries its own rule: {mark!r}",
                )

    def test_the_phase_body_is_not_resident_in_the_skill(self):
        """A paste-back costs every run that has nothing to harden."""
        skill = squash(read(SKILL))
        for mark in LAUNCH_HARDEN_MARKS:
            with self.subTest(mark=mark):
                self.assertFalse(
                    squash(mark) in skill,
                    f"the phase is resident in SKILL.md again: {mark!r}",
                )

    def test_the_skill_still_carries_the_trigger(self):
        skill = read(SKILL)
        self.assertIn("launch-harden.md", skill)

    def test_the_trigger_ties_the_missing_stamp_to_the_read(self):
        """A pointer that says the file exists is a reminder. The trigger has
        to name both halves in one sentence: the condition the runner reads off
        the issue files, and the file it opens because of it."""
        skill = read(SKILL)
        sentences = re.split(r"(?<=[.:])\s", skill)
        tying = [s for s in sentences
                 if "launch-harden.md" in s and "Hardened:" in s]
        self.assertTrue(
            tying,
            "no single sentence names both a missing `Hardened:` line and "
            "`launch-harden.md`",
        )

    def test_the_skill_no_longer_defers_hardening_to_the_next_run(self):
        """The bullet the phase replaces said `/harden-issues` was the fix FOR
        THE NEXT RUN and that it must never run against issues this run holds.
        Both sentences refuse the phase outright, so a green suite with either
        still resident would be describing a machine that cannot start."""
        skill = squash(read(SKILL))
        self.assertNotIn("naming `/harden-issues` as the fix **for the next run**",
                         skill)
        self.assertNotIn("Never run it against issues this run holds", skill)

    def test_the_citation_bullet_grades_stamped_and_unstamped_apart(self):
        """Ruling 9's second half. One instrument, two jobs: it repairs an
        unstamped file, because the phase holds the write authority to repair
        it, and it reports on a stamped one, because a run may not write an
        issue file it did not harden."""
        skill = squash(read(SKILL))
        self.assertIn("report-only on a stamped file", skill)
        self.assertIn("the phase repairs an unstamped one", skill)

    def test_the_phase_names_the_wave_cap_as_a_number(self):
        """Ruling 21. `five` is the recipe; a cap written as "a few" is a cap
        every runner resolves differently."""
        self.assertIn("Five attackers at a time", squash(read(LAUNCH_HARDEN)))

    def test_the_phase_names_all_three_drop_classes(self):
        """Ruling 4 made the list closed, so the phase has to enumerate it.
        A fourth class invented mid-run is an issue dropped on nobody's rule."""
        phase = squash(read(LAUNCH_HARDEN))
        for clause in ("[irreversible]", "split", "premise check"):
            with self.subTest(clause=clause):
                self.assertIn(clause, phase)

    def test_the_commit_is_named_and_sits_before_spawn_one(self):
        """Ruling 10. A halt between the phase and spawn 1 must keep the
        hardened files, and an uncommitted worktree loses them."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("Harden at launch: NN, NN", phase)
        self.assertIn("before spawn 1", phase)

    def test_the_phase_does_not_restate_the_attack_checklist(self):
        """The checklist has one home, `harden-issues/SKILL.md`. A second copy
        drifts, and the drift is invisible: both files read as authoritative.
        The phase says which pass to run, never how to attack."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertNotIn("Unstated invariants", phase)
        self.assertNotIn("Joint satisfiability", phase)
        self.assertIn("harden-issues/SKILL.md", phase)

    def test_the_phase_names_the_run_scoped_findings_path(self):
        """Ruling 7, landed at sitting 1. A phase that writes to the shared
        directory overwrites the last attended pass's file for that issue."""
        self.assertIn("runs/<batch-id>/harden/", squash(read(LAUNCH_HARDEN)))

    def test_the_phase_names_the_two_model_map_keys(self):
        """Ruling 2, landed at sitting 1. `model-map-gate.py` refuses a spawn
        carrying the wrong model or none, so a phase that does not read the
        ledger stops on its first attacker."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("attacker", phase)
        self.assertIn("seam", phase)
        self.assertIn("Model map at launch:", phase)

    def test_a_drop_clears_every_place_the_ledger_reader_looks(self):
        """`find_live_ledger.parse_scope_ids` reads the title line, any `Scope`
        line and the status table. An id left in one of the three is an issue
        this ledger still holds, so `machine-preflight.py` refuses another run
        that types it -- for the whole remaining life of the batch, on an issue
        this run deliberately let go."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("status table", phase)
        self.assertIn("title line", phase)
        self.assertIn("`Scope` line", phase)
        self.assertIn("parse_scope_ids", phase)

    def test_a_failed_attacker_is_not_a_fourth_drop_class(self):
        """Ruling 4's list is closed, and it closes over FORKS. An attacker
        that wrote nothing settled no fork, so the file has to say which of the
        two things it is -- otherwise a runner meeting an empty findings file
        twice either invents a class or stamps an unattacked issue."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("not a fourth drop class", phase)

    def test_the_criteria_gate_runs_over_what_survived_the_drops(self):
        """A dropped issue handed to `check_issue_ready.py` exits 1 on the
        section it never had, and stops a launch on an issue the phase had
        already removed."""
        self.assertIn("over the scope that survived", squash(read(LAUNCH_HARDEN)))

    def test_the_seam_condition_is_stated_in_both_files_that_carry_it(self):
        """The class ticket 33's own gap 1 names: a rule ruled in one file and
        not written into the file that enforces it. A launch caller reads the
        harden skill for the checklist and this file for the phase, so the
        condition has to read the same way in both."""
        harden = squash(read(SKILLS / "harden-issues" / "SKILL.md"))
        self.assertIn("skipped where only ONE issue was attacked", harden)
        self.assertIn("where two or more", squash(read(LAUNCH_HARDEN)))

    def test_the_phase_says_a_run_still_never_widens_its_own_batch(self):
        """Ruling 1. The phase hardens what was typed; it does not go looking
        for the 148 `needs-harden` issues the backlog holds."""
        self.assertIn("does not pick its own batch", squash(read(LAUNCH_HARDEN)))


class TheProseRoleCountIsTheRealOne(unittest.TestCase):
    """Ticket 33 sitting 2, the item sitting 1 carried forward.

    Ruling 2 widened `model_map.ROLES` from twelve to fourteen. SKILL.md stated
    the old count in five places and enumerated the old key list in a sixth,
    and every one of them is descriptive: `SKILL.md` has the runner paste what
    `model_map.py` prints rather than type a role list, so a ledger header
    carried fourteen roles whatever the prose said. What the stale prose cost
    is a reader who counts roles off it and concludes the two hardening roles
    are outside the map -- which is the opposite of ruling 2.

    A count in prose beside a list in code goes stale on the next widening too,
    so this is a refusal rather than a correction. It reads the live `ROLES`
    dict, and the next role to join sends it red on the day it lands.
    """

    WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
             13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen"}

    def setUp(self):
        import model_map
        self.map = model_map
        self.raw = read(SKILL)
        self.skill = squash(self.raw)

    def keys_paragraph(self):
        """The `models:` key list, from `Keys are` to the end of its sentence."""
        start = self.skill.index("Keys are `all`")
        return self.skill[start:start + 600]

    def test_every_role_the_map_knows_is_named_in_the_key_list(self):
        """A key a runner cannot see is a key nobody types. `attacker` and
        `seam` were absent for the whole of sitting 1."""
        listed = self.keys_paragraph()
        for role in self.map.ROLES:
            with self.subTest(role=role):
                self.assertIn(f"`{role}`", listed)

    def test_the_skill_states_the_current_role_count(self):
        self.assertIn(self.WORDS[len(self.map.ROLES)], self.skill)

    def test_no_stale_count_survives_outside_a_historical_clause(self):
        """Every counted mention of the roles states today's count.

        The one legal `twelve` is the sentence about the era before ticket 39,
        where twelve was true. A sentence is historical only if it says so in
        its own words, so this reads the sentence rather than a line number --
        the five stale ones moved six lines during this same sitting.

        A group count is legal at its own size: `the four roles that build` is
        `WORKERS`, not a stale reading of `ROLES`, and the sentence naming the
        group is what tells the two apart.
        """
        words = "|".join(self.WORDS.values())
        counted = re.compile(
            rf"\b({words})\b(?:\s+\S+){{0,2}}\s+(?:roles?|agent files?)\b"
        )
        whole = self.WORDS[len(self.map.ROLES)]
        workers = self.WORDS[len(self.map.WORKERS)]
        history = ("That was right while",)
        seen = 0
        for sentence in re.split(r"(?<=[.:])\s", self.raw):
            flat = squash(sentence)
            for found in counted.finditer(flat):
                word = found.group(1)
                seen += 1
                if any(clause in flat for clause in history):
                    continue
                if "that build" in flat and word == workers:
                    continue
                with self.subTest(sentence=flat[:90]):
                    self.assertEqual(
                        word, whole,
                        "a role count states a number the map does not hold: "
                        f"{flat[:160]!r}",
                    )
        # A guard that matched nothing would pass on a file that had deleted
        # every count, which is not the same thing as a file that is right.
        self.assertGreater(seen, 3)

    def test_the_group_sizes_in_prose_match_the_groups_in_code(self):
        """`workers` and `gates` are what a launch line actually types, and
        ruling 2 put the two hardening roles in `gates`, so the group grew with
        the role list."""
        self.assertIn(f"the {self.WORDS[len(self.map.WORKERS)]} roles that build",
                      self.skill)
        self.assertIn(f"the {self.WORDS[len(self.map.GATES)]} that check",
                      self.skill)


class ThePeerHardenBranchIsRefusedBeforeThePhaseSpends(unittest.TestCase):
    """Ticket 33 sitting 3, the mock drive. Drive D measured this.

    `check_harden_branch.py` refuses a launch while an unmerged
    `claude/harden-issues-*` branch holds an issue in the batch. Before the
    fold that refusal cost the run nothing: it arrived while the pre-flight was
    still reading files. The fold put the hardening phase ABOVE it in the
    bullet order, so an unstamped issue a peer branch already holds is attacked,
    repaired, stamped and committed -- and only then is the launch refused.
    That is the fault `check_harden_branch.py` exists to prevent, made worse: two
    hardening passes now write the same issue file at the same time.

    Measured on mock drive D, 2026-09-07: `/run-issues 909 models: all=sonnet`
    against an unmerged `claude/harden-issues-909-mock33`. The prompt gate
    passed, the map resolved, the batch id was minted, the ledger was written,
    the hardening-stamp bullet listed 909 as unstamped -- and the refusal came
    four bullets later. A live ledger holding 909 was left behind by a launch
    that never started, so `machine-preflight.py` then refused the retry as an
    overlapping range.

    Two refusals, and both are about ORDER rather than about wording.
    """

    def setUp(self):
        self.skill = read(SKILL)
        self.phase = squash(read(LAUNCH_HARDEN))

    def _at(self, needle):
        where = self.skill.find(needle)
        self.assertNotEqual(where, -1, f"{needle!r} is not in SKILL.md at all")
        return where

    GATE_BULLET = "**Concurrency gate — REFUSE to start while an unmerged"

    def test_the_concurrency_gate_is_read_before_the_phase_is_triggered(self):
        """The hardening-stamp bullet is what opens `launch-harden.md`. A peer
        branch holding one of these issues has to have refused the launch
        already, or the phase spends five attacker spawns on a file another
        session is hardening at the same moment.

        Anchored on the BULLET's own opening words, not on the bare script name:
        the script is named in the resume section and in cross-references, and
        an earlier mention would satisfy a name search while the bullet itself
        sat back below the trigger -- which is the regression this class
        exists to catch."""
        gate = self._at(self.GATE_BULLET)
        trigger = self._at("is the trigger to read `launch-harden.md`")
        self.assertLess(
            gate, trigger,
            "the hardening phase is triggered above the concurrency gate, so "
            "a launch a peer harden branch refuses has already attacked, "
            "repaired, stamped and committed its issue files",
        )

    def test_the_refusing_gate_runs_before_the_batch_id_is_minted(self):
        """A refused launch must leave nothing. The batch id is what mints the
        run directory and what `find_live_ledger.py` reads, so a refusal after
        it leaves a live ledger holding an issue nothing is building."""
        gate = self._at(self.GATE_BULLET)
        mint = self._at("Then mint the batch id")
        self.assertLess(
            gate, mint,
            "the batch id is minted before the concurrency gate can refuse, so "
            "a refused launch leaves a live ledger holding its issues",
        )

    def test_the_phase_file_names_the_peer_branch_as_something_it_never_takes(self):
        """The phase's own `What this phase never does` list is where a caller
        reads its scope. The never-attack guard covers an issue a live LEDGER
        holds; a peer hardening BRANCH is the other second writer, and ruling 5
        does not reach it."""
        self.assertIn("check_harden_branch.py", self.phase)


class TheCitationVerdictComesFromTheRowsNotTheExitCode(unittest.TestCase):
    """Ticket 33 sitting 3, the mock drive. Drives A and B measured this.

    Ruling 9 gave the pre-flight citation bullet two jobs: repair an unstamped
    file, report on a stamped one. Both need to know WHICH scoped files are
    broken, and the obvious instrument -- the process exit code -- cannot say.

    `scripts/check-issue-citations.mjs --quiet <one issue file>` always runs the
    decision pass over the whole repository beside the citation pass over the
    named file, and there is no flag to turn it off. Measured 2026-09-07 on the
    mock feature: a file with `0 citations ... 0 moved` exits 1, and a file with
    two genuinely moved citations exits 1. The 1 came from eight `Touches:`
    faults in `docs/adr/` and `.scratch/pilot-delivery/issues/`, none of them in
    the batch.

    So a runner reading the exit code names every scoped file as broken, and the
    phase repairs files that have nothing wrong with them. The verdict is the
    summary line and the rows that NAME the file. Both places that read the
    instrument have to say so.
    """

    MARK = "never the exit code"

    def test_the_preflight_bullet_says_which_reading_is_the_verdict(self):
        self.assertIn(self.MARK, squash(read(SKILL)))

    def test_the_phase_step_says_it_too(self):
        """The phase is the caller that WRITES on this reading, so it is the one
        place where a wrong reading edits an issue file."""
        self.assertIn(self.MARK, squash(read(LAUNCH_HARDEN)))


class ThePhaseHardensTheCopyOnTheRunsOwnBranch(unittest.TestCase):
    """Ticket 33 sitting 3, the mock drive. Drive A measured this.

    `launch-harden.md` said to commit the phase's work "on the run's own branch"
    and never said which TREE the attackers read and write. Every other path in
    the phase is absolute or run-scoped -- the findings file, the ledger, the
    decisions shard -- so the issue file is the one path a runner has to guess.

    Drive A guessed the main checkout, and both failure halves landed at once.
    The run worktree's copy of issue 901 still read the unhardened text, so the
    implementer would have been graded against criteria the phase had already
    replaced; and `git status` in the MAIN checkout showed two modified issue
    files, which is a run writing main. `SKILL.md` says main belongs to the human and
    that a run may not write an issue file it did not harden -- the phase is the
    exception to the second, and it is not an exception to the first.

    Nothing mechanical would have caught it. The commit step would have found
    nothing to commit on the run's branch and reported success on an empty diff.
    """

    def setUp(self):
        self.phase = squash(read(LAUNCH_HARDEN))

    def test_the_phase_names_the_tree_it_works_in(self):
        self.assertIn("run's own worktree", self.phase)

    def test_the_phase_says_the_main_checkout_is_never_written(self):
        """The half a reader is likeliest to skip: knowing where to work does
        not by itself say that the other copy is out of bounds."""
        self.assertIn("never the main checkout", self.phase)

    def test_the_attacker_spawn_carries_that_path(self):
        """A rule the phase states and the spawn prompt does not carry is a rule
        the attacker never sees: the brief is the only thing it reads."""
        self.assertIn("worktree path", self.phase)


class ASeamFindingAgainstAStampedIssueHasSomewhereToGo(unittest.TestCase):
    """Ticket 33 sitting 3, the mock drive. Drive A's seam pass measured this.

    The seam agent reads every issue in the batch, stamped ones included, because
    a gap between two issues does not care which of them was hardened today. But
    the phase may only WRITE the unstamped ones -- a run may not write an issue
    file it did not harden, and editing a criterion under an existing stamp
    leaves the stamp describing a file it no longer matches.

    Drive A hit it on the first try. The seam found that issue 901's criterion 1
    carried an export-style ambiguity its own attacker had missed, applied the
    fix to 901, and found the identical gap in 903 -- which was already stamped.
    It correctly declined to edit 903 and recorded the fact in `seam.md`. The
    phase reads counts and `## Checks for the human` out of that file and nothing
    else, so the finding would have died there while 903's implementer built to
    the criterion the seam had just shown to be short.

    The remedy costs nothing and needs no write authority: the runner already
    builds a spawn prompt per issue, and the merge briefing already has a place
    for what the run learned. Ruling 4's drop list stays closed -- a seam finding
    against a stamped issue drops nothing.
    """

    def test_the_phase_says_where_a_stamped_issues_seam_finding_goes(self):
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("seam finding against a stamped issue", phase)

    def test_it_reaches_the_implementer_and_the_briefing(self):
        """A finding recorded only in `seam.md` is a finding nobody reads: the
        phase takes counts and questions out of that file, never the working."""
        phase = squash(read(LAUNCH_HARDEN))
        self.assertIn("spawn prompt", phase)
        self.assertIn("merge briefing", phase)


class ACheckOnlyTheHumanCanRunHasAHomeInsideARun(unittest.TestCase):
    """Ticket 33 sitting 3, the mock drive. Drive B measured this.

    `harden-issues/SKILL.md` heads a whole section "Checks only the human can run
    happen HERE, not mid-run", and settles them by putting the list to the human
    at the end of the attended pass. The launch phase is mid-run. There is no end of an
    attended pass, nobody to put a list to, and nothing in a run ever waits.

    So the fold gave the pass a third caller and left one of its outputs without a
    reader. Drive B produced one on the first batch that could: issue 907's
    attacker exhausted the instruments this machine has, read the premise out of a
    dated snapshot, and filed the live re-read as a check -- correctly, since only
    a read outside the sandbox closes it. The issue stays in scope, so no drop
    class covers it, and `seam.md` is not a place anyone acts from.

    A check is not a fork, so ruling 4's list is untouched and ruling 12's
    `## Ruled` items are the wrong home: nobody has ruled anything. It goes where
    every other thing a run needs from the human's hands goes -- the pending file,
    which the daily brief reads every morning -- and it is named under `## Decide`
    so the merge read sees it too.
    """

    def setUp(self):
        self.phase = squash(read(LAUNCH_HARDEN))

    def test_the_phase_says_where_a_check_for_the_human_goes(self):
        self.assertIn("Checks for the human", self.phase)

    def test_it_lands_in_the_projects_pending_actions_file(self):
        """The live tree names one file by its absolute path, because there the
        path is real and a bare name sent a merge briefing's reader searching a
        repo tree on 2026-08-03. No reader of this pack has that file, so the
        phase names the role instead and carries the citation rule with it."""
        phase = read(LAUNCH_HARDEN)
        self.assertIn("pending-actions file", phase)
        self.assertIn("cite its path in full", phase)

    def test_a_check_does_not_drop_the_issue(self):
        """907's attacker was explicit that the issue stays in scope. Reading a
        check as a fourth drop class would take an issue out of a run over a
        question nobody had to answer to build it."""
        self.assertIn("does not drop the issue", self.phase)


class EveryBulletThatReadsAnIssueFileNamesItsTree(unittest.TestCase):
    """Ticket 33 sitting 3's review, and drive G measured the fault.

    `launch-harden.md` now pins every issue file the phase reads and writes to
    the run's own worktree. Two bullets in `SKILL.md` feed that phase and named
    no tree at all: the citation check, whose rows the phase repairs from, and
    the hardening stamp, whose reading decides which issues enter the phase.

    A worktree freezes the tracker at the moment it was cut, so the two copies
    are not interchangeable. Drive `batch-800f60` was cut at `3d5fe7bf` while
    issue 914 landed on main at `b81bf6a4`: the worktree did not hold that file
    at all, an attacker was handed a path that did not exist, and it edited the
    main checkout instead -- and said so, which is the only reason it was
    caught. The same freeze makes a file stamped on main after the cut read
    unstamped in the worktree, so the stamp bullet can put an issue into the
    phase twice or skip it once, depending only on which copy the runner opened.
    """

    def setUp(self):
        self.skill = squash(read(SKILL))

    def test_the_citation_bullet_names_the_tree_it_reads(self):
        bullet = self.skill.split("Run the citation check over the batch's own")[1][:2200]
        self.assertIn("run's own worktree", bullet)

    def test_the_stamp_bullet_names_the_tree_it_reads(self):
        bullet = self.skill.split("Hardening stamp, and the phase it triggers")[1][:2200]
        self.assertIn("run's own worktree", bullet)


if __name__ == "__main__":
    unittest.main()
