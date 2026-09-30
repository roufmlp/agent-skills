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

import importlib.util
import re
import unittest
from pathlib import Path

RUN_ISSUES = Path(__file__).resolve().parent
SKILLS = RUN_ISSUES.parent
# The promotion and attacker briefs live in `agents/` beside `skills/`, so
# `SKILLS` does not reach them. `agents/` and `hooks/` are installed under
# `~/.claude` and have exactly one home on a machine, with no worktree copy, so
# an absolute anchor is what reaches them. A climb from `__file__` lands on
# `.claude/worktrees` when this checkout is a worktree, which is the fault
# `lib/check_claude_home.py` refuses -- and that checker names THIS file as the
# one whose comment knew the fact and wrote the climb anyway.
CLAUDE = Path.home() / ".claude"
AGENTS = CLAUDE / "agents"

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
    "Preview deploy: do what the repo's own CLAUDE.md documents.",
    "A published checksum expires the moment the file moves.",
    "Main moved while you worked. Read it before you write a question.",
    "Sweep the register for rows their own issue already fixed.",
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
    # Rulings 4 and 11 -- the drop classes, and the closed list. Four since
    # issue 43b, default `q-h0925b-seam-1`: rule 7 of issue 32.
    "Only four things drop an issue from this run",
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
        self.assertIn("void experiment", window)
        # Ticket 36 sitting 5 moved the measurement itself to decisions.md.
        decisions = read(DECISIONS).lower()
        self.assertIn("1.51m", decisions)
        self.assertIn("2026-08-21", decisions)


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
        self.assertIn("ready-for-agent", window)
        # Ticket 36 sitting 5 moved the base rate to the guard's own docstring.
        self.assertIn("32 issue files", read(RUN_ISSUES / "check_issue_ready.py"))

    def test_the_criteria_gate_does_not_claim_to_replace_the_stamp(self):
        """The human ruled on 2026-08-21 that an explicitly named issue always runs,
        stamped or not. This guard checks a different thing and must keep saying
        so, or the next reader takes it for an overturn."""
        skill = read(SKILL)
        start = skill.index("Criteria gate")
        window = skill[start:start + 2000]
        self.assertIn("2026-08-21", window)

    def test_a_light_line_stamps_a_light_issue_only(self):
        """Tracker-tooling issue 43, AC5: rule 5 of issue 32. A `Level: light`
        issue skips hardening and carries a `Light:` line, which counts as
        stamped for the `all` scope on that level and on no other."""
        skill = read(SKILL)
        start = skill.index("An `all` run takes stamped issues")
        paragraph = skill[start:skill.index("\n\n", start)]
        self.assertIn("Light:", paragraph)
        self.assertIn("Level: light", paragraph)

    def test_the_provisional_stamp_sentence_names_the_full_exception(self):
        """Tracker-tooling issue 43b, AC4: rule 7 of issue 32. A `Level: full`
        issue whose criterion carries a pending default is the exception to
        the provisional stamp counting. Checked inside the sentence, not the
        bullet, because issue 43's `Light:` words name `Level:` there too."""
        skill = " ".join(read(SKILL).split())
        anchor = "`Hardened (provisional)` counts as stamped"
        at = skill.index(anchor)
        start = skill.rindex(". ", 0, at) + 2
        sentence = skill[start:skill.index(". ", at)]
        self.assertIn("Level: full", sentence)

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
        # Ticket 36 sitting 5 moved the two incidents to decisions.md.
        decisions = read(DECISIONS)
        for mark in ("17:05", "vitest transform cache"):
            self.assertIn(mark, decisions)

    def test_the_gate_copy_has_history_and_one_recipe(self):
        """The `.git` exclusion was reversed on 2026-09-29 (the perf audit of
        2026-09-28): 11 git tests red in every verify copy, and a second copy
        per gate. `make_copy.py` borrows the object store, so the 87 MB that
        justified the exclusion is not copied."""
        skill = squash(read(SKILL))
        self.assertIn("made by `make_copy.py`, and by nothing else", skill)
        self.assertIn("make_copy.py --tree", skill)
        self.assertNotIn("REFUSED no-git-repository", skill)
        self.assertIn("87 MB", read(DECISIONS))
        self.assertIn("make_copy.py", read(DECISIONS))

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
        """The brief has thirty minutes, and the cost reading is one block of
        section one rather than a section of its own.

        NARROWED 2026-09-13, issue 03 of the tracker-tooling set. This used to
        refuse the heading `### 1c.` whatever stood under it, which is a fence
        around a heading rather than around the rule. The human then ruled that the
        parked sweep gets its own section, and the brief's own budget rule
        ("Keep it to thirty minutes") is what holds the length — the heading
        never was. What this now refuses is the thing it was built to refuse:
        the cost reading leaving section one.
        """
        text = read(SKILLS / "daily-brief" / "SKILL.md")
        start = text.index("### 1. Merge reads")
        self.assertIn("run_compare.py last", text[start:text.index("### 1b.")])
        self.assertNotIn("### 1c. Cost", text)


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

    def test_a_row_written_before_the_marker_is_never_refused(self):
        """Ruling 3 loses no history: sixteen ledgers hold 143 rows written
        before it existed. Tracker-tooling issue 15 refuses a rejected round
        with no charge, and only on a row that carries a gate token at all."""
        import check_attempt_cap
        self.assertEqual(check_attempt_cap.charge_faults(
            "attempt 1 — verify pass, review REJECT; criteria reset"), [])

    def test_the_strike_stays_derived_where_no_charge_was_written(self):
        """Ruling 28 kept the strike derived because two roads cancelled one in
        prose and wrote no marker. Issue 15 gave those roads `charge=none`;
        a row that carries no charge is still read the old way."""
        import run_quality
        self.assertIsNone(run_quality.charged_strikes(
            "attempt 1; gates 1: verify=pass review=reject"))


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



class RuleSevenReachesTheLaunchPhase(unittest.TestCase):
    """Tracker-tooling issue 43b, seam pass h0925b. The launch phase stamps
    at step 5 and the criteria gate runs at step 7, where "Exit 1 blocks the
    launch". So a `Level: full` issue rule 7 refuses is dropped at step 5
    (default `q-h0925b-seam-1`), and the agents that write a default are told
    the one mark the gate reads (default `q-h0925b-seam-2`)."""

    FORM = "Default (`q-<pass>-<issue>-<n>`)"

    def test_step_5_names_rule_7_among_its_drops(self):
        text = " ".join(read(LAUNCH_HARDEN).split())
        start = text.index("## Step 5")
        step = text[start:text.index("## Step 6", start)]
        self.assertIn("rule 7", step)
        self.assertIn("Level: full", step)
        self.assertIn(self.FORM, step)

    def test_each_brief_that_writes_a_default_states_the_form(self):
        agents = Path.home() / ".claude" / "agents"
        for path in (LAUNCH_HARDEN, agents / "harden-issues-attacker.md",
                     agents / "harden-issues-seam.md"):
            with self.subTest(path.name):
                self.assertGreaterEqual(path.read_text().count(self.FORM), 1)

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
        """The `models:` key list, from `Keys are` to the end of its sentence.

        Ticket 36 sitting 5 moved the grammar to `model_map.py`'s docstring: the
        runner pastes the typed line into the script and never types a key, so
        the list is for the person typing the launch line, and the script's
        `--help` is where that person reads it.
        """
        doc = squash(read(RUN_ISSUES / "model_map.py"))
        start = doc.index("Keys are `all`")
        return doc[start:start + 600]

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



# --- Ticket 36 sitting 5: the details leave by destination (2026-09-09) ----
#
# Ruling 9 of ticket 36 (2026-09-07), on the human's own road: a rule a script
# enforces puts its reason in that script's docstring, which the runner never
# reads and which therefore costs a run nothing; a rule no script enforces puts
# its reason in `decisions.md`, which exists for exactly this. Ruling 14: the
# ceiling is set AFTER the move and never at the count of the day, because a
# ceiling at today's count permits the file to stay as it is. The human set the
# SKILL.md figure himself on 2026-09-09: below 1200, and 600 the target. The
# finale's figure is the exact count the move left, so every later line added
# to it is paid for by a line moved out; queue item q-t36-s5-1 records it.
#
# The reason to cut the file is that 1474 lines hide a rule, not that they cost
# money: the token prize was measured at three tenths of one per cent of a run.
# A detail file read during a run is billed from that turn to the end, so a
# move saves only what nobody opens -- and nothing in a run opens a docstring.

SKILL_LINE_CEILING = 1200     # exclusive: the file stays BELOW this
FINALE_LINE_CEILING = 803     # inclusive: the count the move left, 2026-09-09

HOOKS = CLAUDE / "hooks"
LIB = SKILLS / "lib"

# Stories that left SKILL.md or finale.md for the file of the script that
# enforces the rule they explain. Asserted present in that file AND absent from
# both loaded files. Same shape as DECISIONS_MARKS: a story joins this list only
# once it has landed at its destination.
SCRIPT_MARKS = {
    HOOKS / "run-issues-foreground-gate.py": [
        "97 minutes",
        "158 minutes",
    ],
    HOOKS / "run-issues-brief-cap.py": [
        "averaged 1,243 words",
        "381 words",
    ],
    RUN_ISSUES / "check_attempt_cap.py": [
        "`retry 00:18` is a clock",
    ],
    RUN_ISSUES / "check_commit_order.py": [
        "68 and 95 minutes",
        "09:38",
        "26 minutes early",
        "having matched zero rows",
    ],
    RUN_ISSUES / "check_run_journal.py": [
        "committed six issues and journalled two",
    ],
    RUN_ISSUES / "check_harden_branch.py": [
        "merged at 23:12",
    ],
    RUN_ISSUES / "check_issue_ready.py": [
        "32 issue files",
    ],
    RUN_ISSUES / "check_register_status.py": [
        "swept 112 rows",
        "Nine of those sixteen",
    ],
    RUN_ISSUES / "check_diff_coverage.py": [
        "951 files and 11,329 tests",
        # The ordering story, moved 2026-09-13. `SKILL.md` broke its own ceiling
        # by 45 lines carrying it; the rule and the commands stayed behind.
        "the branch every record in the product rendered that day",
        "shipped 21",
        "never reaches `git status`",
    ],
    RUN_ISSUES / "citation_pass.py": [
        "5h50m",
        "17,200 citations",
        "four of six commits had no pass",
    ],
    RUN_ISSUES / "run_quality.py": [
        "on runs that had charged them",
        "bolded verdicts in 17 rows",
    ],
    RUN_ISSUES / "check_finale_stage.py": [
        "the last at 15:10 on 2026-08-20",
    ],
    RUN_ISSUES / "check_paste_file.py": [
        "seven paste files, committed none of them",
        "Nine agents touched that run's two paste files",
    ],
    RUN_ISSUES / "run_costs.py": [
        "1.01 hours for an 8.48-hour run",
        "slug holds 64 sessions",
    ],
    RUN_ISSUES / "estimate_accuracy.py": [
        "lost 18 of 30",
        "spread 0.31x to 1.04x",
    ],
    RUN_ISSUES / "cache_probe.py": [
        "61.7 to 1",
    ],
    RUN_ISSUES / "harness_cost.py": [
        "146 minutes",
    ],
    LIB / "check_verdict.py": [
        "attempt-2 gates died with their",
    ],
    # Sitting 6, 2026-09-13: these reasons were in the script AND written a
    # second time into SKILL.md. The second copy is what the sweep removed.
    RUN_ISSUES / "check_permission_floor.py": [
        "3 h 37 m",
        "1009 of 1011",
    ],
    RUN_ISSUES / "stall_watch.py": [
        "208.8 minutes",
        "04:44:00",
    ],
}

# Stories that left SKILL.md for decisions.md in this sitting. Same contract as
# DECISIONS_MARKS above, and kept apart from it only so a reader can see which
# sitting moved what.
SKILL_STORIES_MOVED = [
    "1.51M weighted",
    "reported this field as unobservable",
    "02:33, 08:26",
    "four sections were still empty placeholders",
    "produced nothing for 81 minutes",
    "appended three lines to a file inside a",
    "deleted the RUN worktree's vitest transform cache",
    "three gates deleted the run's cache on 2026-08-27",
    "87 MB against a 66 MB copy",
    "reverted to the pre-fix file for two minutes",
    "both picked the scratchpad name",
    "Issue 319's recorded default would have seeded",
    "every route answered HTTP 500, including",
    "Compiled successfully",
    "stale error naming a line that no longer existed",
    "Exit 6 was added 2026-09-02",
    "died after 48 lines and read clean",
    "About 30 to 40 minutes across the two",
    "four bullets lower",
    "cut at `3d5fe7bf`",
    "106 citations, 83 holding",
    "169 broken citations",
    "nine cost 1.44M",
    "30 to 60 seconds per worktree",
    "leaving it off cost six hours",
    "CLI 2.1.257",
    "failed a third time in the",
    # Sitting 6, 2026-09-13. The first of these had no home at all and is now
    # under that sitting's heading; the rest were already there twice over.
    "lost 5.7 hours of 9.22",
    "the first trial of `medium` effort",
    "87 of 89 changed lines executed",
]

# Stories that left finale.md for decisions.md. Present there, absent from the
# finale.
FINALE_STORIES_MOVED = [
    "had run since 02:27",
    "created a supplier on QA",
    "`check (rank between 1 and 3)`",
    "Both 202 checksums were correct at gate close",
    "had ruled twice on issue 276",
    "Three of seventeen issues minted on 2026-08-09 were stale",
    "296-276-297",
    "roughly 35,000 tokens in and 3,000 out",
]

# The rule sentence each move of this sitting LEAVES BEHIND in SKILL.md, in
# the SKILL_MARKS shape: asserted present, so a move that took the rule with
# the story goes red here.
SITTING_FIVE_ANCHORS = [
    "**The field is enforced, not remembered.**",
    "**Do NOT stamp transitions with the time.**",
    "**The register is swept at every issue's commit too",
    "**Run `npm run build` at every commit step, not only at the finale.**",
    "**A build result is never read from log text.",
    "**Build in a copy, never in the tree a dev server is serving.**",
    "**Pin to the commit just made, never to branch head.**",
    "**A zero from that check is a fact about the FILE, not about the instrument.**",
    "Never split an issue yourself",
    "**A drill that writes proves its copy is not hard-linked, before it writes.**",
    "Delete nothing under `node_modules` from inside a copy.",
    "**Each gate drills in its OWN private whole-tree copy",
    "**Concurrent gates share a tree but not a pen.**",
]


class TheDetailsLeftByDestination(unittest.TestCase):
    """Ticket 36 sitting 5, rulings 9 and 14."""

    def test_the_skill_is_below_its_ceiling(self):
        lines = len(read(SKILL).splitlines())
        self.assertLess(
            lines, SKILL_LINE_CEILING,
            f"SKILL.md is {lines} lines; the ceiling is {SKILL_LINE_CEILING}, "
            "exclusive. Move a story out by ruling 9 before adding a line.",
        )

    def test_the_finale_is_within_its_ceiling(self):
        lines = len(read(FINALE).splitlines())
        self.assertLessEqual(
            lines, FINALE_LINE_CEILING,
            f"finale.md is {lines} lines; the ceiling is {FINALE_LINE_CEILING}. "
            "Move a story out by ruling 9 before adding a line.",
        )

    def test_decisions_takes_no_ceiling(self):
        """Ruling 14's own reason: nothing in a run reads it, so its size
        costs nothing. Pinned so nobody adds one in the name of symmetry."""
        self.assertNotIn("DECISIONS_LINE_CEILING", globals())

    def test_every_moved_story_is_in_its_scripts_own_file(self):
        for path, marks in SCRIPT_MARKS.items():
            self.assertTrue(path.is_file(), f"{path} does not exist")
            text = squash(read(path))
            for mark in marks:
                with self.subTest(script=path.name, mark=mark):
                    self.assertIn(squash(mark), text)

    def test_no_script_story_is_still_resident_in_a_loaded_file(self):
        skill = squash(read(SKILL))
        finale = squash(read(FINALE))
        for path, marks in SCRIPT_MARKS.items():
            for mark in marks:
                with self.subTest(script=path.name, mark=mark):
                    self.assertNotIn(squash(mark), skill,
                                     "the story is still loaded by SKILL.md")
                    self.assertNotIn(squash(mark), finale,
                                     "the story is still loaded by finale.md")

    def test_every_skill_story_landed_in_decisions_and_left_the_skill(self):
        decisions = squash(read(DECISIONS))
        skill = squash(read(SKILL))
        for mark in SKILL_STORIES_MOVED:
            with self.subTest(mark=mark):
                self.assertIn(squash(mark), decisions)
                self.assertNotIn(squash(mark), skill)

    def test_every_finale_story_landed_in_decisions_and_left_the_finale(self):
        decisions = squash(read(DECISIONS))
        finale = squash(read(FINALE))
        for mark in FINALE_STORIES_MOVED:
            with self.subTest(mark=mark):
                self.assertIn(squash(mark), decisions)
                self.assertNotIn(squash(mark), finale)

    def test_every_anchor_of_this_sitting_is_still_in_the_skill(self):
        skill = squash(read(SKILL))
        for mark in SITTING_FIVE_ANCHORS:
            with self.subTest(mark=mark):
                self.assertIn(squash(mark), skill,
                              "a sitting-5 move took its rule anchor with it")

    def test_the_lists_are_not_empty_and_do_not_overlap(self):
        self.assertTrue(SCRIPT_MARKS)
        self.assertTrue(SKILL_STORIES_MOVED)
        self.assertTrue(FINALE_STORIES_MOVED)
        stories = set(SKILL_STORIES_MOVED) | set(FINALE_STORIES_MOVED)
        for marks in SCRIPT_MARKS.values():
            stories |= set(marks)
        anchors = set(SKILL_MARKS) | set(SITTING_FIVE_ANCHORS)
        self.assertEqual(stories & anchors, set())


# --- Sitting 6: the file grew back to the ceiling (2026-09-13) --------------
#
# Ruling 14 of ticket 36 set the ceiling below 1200 and named 600 as the target,
# so every later line added to SKILL.md is paid for by a line moved out. Nobody
# paid, and the file reached 1244: `test_the_skill_is_below_its_ceiling` went red
# and `lib/run_python_suites.py` then refused this file on every walk, which
# hides any new red suite behind a known one.
#
# This sitting is ruling 9's own remedy applied again -- the stories left, the
# rules stayed. Two lists, in the SITTING_FIVE shape and written at different
# times: the anchors went in BEFORE one line moved, so the anchor test was
# already green and already watching while the edits happened; a story joined
# the second list only once it had landed in `decisions.md`.
#
# Most of what moved was a SECOND COPY of a story `decisions.md` already held in
# full. That duplication is the defect the whole exercise exists to remove, so
# each mark below is a phrase the two copies shared: after the move it is
# present in the home and absent from SKILL.md, and a paste-back goes red.

SITTING_SIX_ANCHORS = [
    # M1 -- the cron's one rescue. Its second clause, "so shortening the
    # interval buys nothing", was overruled on 2026-09-29 when the human set the
    # cron to every 30 minutes; `decisions.md` holds why.
    "cannot prevent a call that was never made",
    # M2 -- the foreground gate. The two measurements are already in the hook's
    # own docstring, which SCRIPT_MARKS pins; the skill kept a summary of them.
    "its message says how to reissue",
    # M3 -- where the coverage check runs. Ruling Q4's justification is the
    # story; the ordering is the rule the runner acts on.
    "never before the gates, and BEFORE STEP 5 — not at the commit step",
    # M4 -- the coverage refusals belong to the one correction round.
    "items for the ONE correction round, exactly as a gate's are",
    # M5 -- the re-run after a correction round. The `git status` fact itself
    # left for `check_diff_coverage.py`'s docstring in master's own slim of the
    # same day, and SCRIPT_MARKS pins it there; the flag the runner must drop is
    # what stays here.
    "with NO `--report-root`",
    # M6 -- the concurrency gate's ordering.
    "It needs no batch id, no ledger and no worktree, which is why it can run"
    " first",
    # M7 -- the stall watch. Why a cron cannot do this job is the rule; the
    # unfired job and the stalled run are the story.
    "The stall watch is a separate PROCESS, and the cron cannot replace it",
    "a session behind a modal is mid-query, so it is never evaluated",
    "Jobs die with the session too, so one can never report the death it was"
    " made to catch",
    # M8 -- the launch mode.
    "The mode is part of the launch line, not an option",
    "turns off the classifier, not the hooks",
    "the human's guards keep their teeth; the modal goes",
    # M9 -- the permission floor grades per segment, and says that the list it
    # graded is its own. The compound-command reason left for the script's
    # docstring in master's own slim of the same day, so only the two sentences
    # still resident are anchored.
    "it grades every role in its own list per SEGMENT",
    "It grades a list it wrote itself",
    # M10 -- the allowlist is derived per role, not read off the bullet.
    "Derive the list from the roles this run will spawn, not from this bullet",
    # M11 -- the gate-round marker carries its charge. It refused nothing until
    # tracker-tooling issue 15 (fix F12 of the audit of 2026-09-23) made a
    # rejected round without a charge refusable.
    "charge=<strike|correction|none>",
    # M12 -- the citation checker's refusal codes.
    "Codes 4, 5 and 6 are refusals to answer, not answers, and all three"
    " outrank 1",
    # M13 -- picking the ledger is a script.
    "the procedure is a script and not a judgement",
]

# The story each move of this sitting took, paired with its ONE HOME. Filled as
# each move landed, never before. The home is not always `decisions.md`: ruling 9
# sends the reason for a script-enforced rule to that script's docstring, and
# several of these were already there while `SKILL.md` carried a second copy.
SITTING_SIX_STORIES_MOVED = [
    # M3 -- ruling Q4's justification for the `before step 5` ordering.
    ("fork `q-finale-be624c-03` of run `batch-be624c`", DECISIONS),
    # M4 -- the two coverage gaps that shipped while the round was already spent.
    ("a later hardening pass and a later run slot", DECISIONS),
    # M5 -- where the re-run-after-a-correction fact was first written down.
    ("in its ledger's carry-forward", DECISIONS),
    # M6 -- the run that built four issues from files a peer branch had hardened.
    ("built four issues from unhardened files", DECISIONS),
    # M10 -- the night the dev server was left off the allowlist.
    ("an illustrative list as a complete one", DECISIONS),
    # The round header's third failure.
    ("restated as a check", DECISIONS),
    # The handwritten field the ledger's owner line replaced.
    ("`heartbeat <HH:MM>`", DECISIONS),
    # M7 -- the cron job that never fired, and the run that stalled behind it.
    ("job due at 04:44:00 sat unfired at 04:45:32", DECISIONS),
    ("stalled for 208.8 minutes with a wakeup installed", DECISIONS),
    # M8 -- what two modals cost one run, and the hooks measured under the mode.
    ("lost 5.7 hours of its 9.22 to two permission prompts", DECISIONS),
    # M9 -- the floor that printed a pass over the wrong role's list.
    ("`ok: 12 command class(es)`", DECISIONS),
    ("The command that halted was a gate's", DECISIONS),
    # M13 -- what one guess at the right ledger cost.
    ("cost 25 minutes", RESUME),
    # The gate-round token's seven dialects, and the rows written before it.
    ("143 issue rows", RUN_ISSUES / "run_quality.py"),
    ("Getting there cost SEVEN", RUN_ISSUES / "run_quality.py"),
    # Why the orchestrator reading comes from inside one week.
    ("a system that no longer exists", RUN_ISSUES / "orchestrator_cost.py"),
    # Why a map refusal is rarely met: the same parser refuses at prompt-submit.
    ("before the batch id is minted and before the QA workspace is seeded",
     RUN_ISSUES / "model_map.py"),
    # The allow rule that sat in the main checkout and not in the worktree.
    ("and not in the run worktree's copy",
     RUN_ISSUES / "check_permission_floor.py"),
]


class TheFileWasBroughtBackUnderItsCeiling(unittest.TestCase):
    """Sitting 6, on the same two rulings as sitting 5."""

    def test_every_anchor_of_this_sitting_is_still_in_the_skill(self):
        skill = squash(read(SKILL))
        for mark in SITTING_SIX_ANCHORS:
            with self.subTest(mark=mark):
                self.assertTrue(
                    squash(mark) in skill,
                    f"a sitting-6 move took its rule anchor with it: {mark!r}",
                )

    def test_every_story_landed_in_its_one_home(self):
        for mark, home in SITTING_SIX_STORIES_MOVED:
            with self.subTest(mark=mark):
                self.assertTrue(home.is_file(), f"{home} does not exist")
                self.assertTrue(
                    squash(mark) in squash(read(home)),
                    f"story is not in its declared home {home.name}: {mark!r}",
                )

    def test_no_moved_story_is_still_resident_in_a_loaded_file(self):
        """A move that copies rather than moves saves nothing and doubles the
        maintenance surface, which is the defect this sitting exists to close."""
        skill = squash(read(SKILL))
        finale = squash(read(FINALE))
        for mark, _home in SITTING_SIX_STORIES_MOVED:
            with self.subTest(mark=mark):
                self.assertFalse(squash(mark) in skill,
                                 f"story is still resident in SKILL.md: {mark!r}")
                self.assertFalse(squash(mark) in finale,
                                 f"story is still resident in finale.md: {mark!r}")

    def test_the_story_list_is_not_empty(self):
        """An empty catalogue is a green that means no work was done."""
        self.assertTrue(SITTING_SIX_STORIES_MOVED)

    def test_the_two_lists_do_not_overlap_with_each_other_or_the_earlier_ones(self):
        """One string cannot be required to be present in and absent from the
        same file, and the earlier sittings' lists make the same claims."""
        anchors = (set(SKILL_MARKS) | set(SITTING_FIVE_ANCHORS)
                   | set(SITTING_SIX_ANCHORS))
        stories = (set(SKILL_STORIES_MOVED) | set(FINALE_STORIES_MOVED)
                   | {mark for mark, _home in SITTING_SIX_STORIES_MOVED})
        for marks in SCRIPT_MARKS.values():
            stories |= set(marks)
        self.assertEqual(stories & anchors, set())


class PromotionMayMergeUpToThreeRows(unittest.TestCase):
    """Ruled by the human on 2026-09-13, out of run `batch-d67136`.

    That run shipped 7 issues and minted 13, because the brief said "One issue
    file per promoted row" and nothing else. Three of the 13 were one finding
    written twice, and two of those three were asked for in plain words by the
    finale's own merge briefing (lines 625 and 633), which promotion had no
    licence to obey.

    A merge rule with no ceiling is how three real defects become one
    unreviewable ticket, so every clause of the ceiling is mechanical and
    `check_origin.py` refuses a file that breaks one. An editor who keeps the
    licence and drops a clause leaves promotion free to merge without limit,
    and nothing downstream would notice.
    """

    PROMOTION = AGENTS / "promotion.md"

    def brief(self):
        return read(self.PROMOTION)

    def test_the_one_row_per_file_rule_is_gone(self):
        """The licence to merge and the old rule cannot both stand. An editor who
        restores the sentence leaves every clause of the ceiling in place, and no
        clause of the ceiling fires on a file that never merges."""
        self.assertNotIn("One issue file per promoted row", self.brief())

    def test_the_narrow_detector_carries_the_measurement_that_keeps_it_narrow(self):
        """Merging on `Origin:` alone reaches 13 files to 7, which is the rate at
        which the backlog stops growing, and it is the wrong trade: hardening
        splits most of it back and the saving at build time is not measured. A
        brief holding the narrow rule without that figure invites the widening."""
        brief = self.brief()
        self.assertIn("not measured", brief)
        self.assertIn("13 files to 7", brief)

    def test_every_clause_of_the_ceiling_is_stated(self):
        brief = self.brief()
        for clause in (
            "at most three",
            "same `Origin:`",
            "same audience and the same severity",
            "`Rows:` line",
            "never `Direct-road: candidate`",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, brief)

    def test_the_ceiling_names_the_check_that_refuses_it(self):
        """Every clause is checkable, and a clause with no check beside it is a
        reminder. The three-class test refuses those."""
        brief = self.brief()
        self.assertIn("check_origin.py --issue", brief)
        self.assertIn("--minted", brief)

    def test_the_sweep_is_scoped_by_run_id_so_it_backfills_nothing(self):
        brief = self.brief()
        start = brief.index("--minted")
        window = brief[start - 1200:start + 1200]
        self.assertIn("backfill", window.lower())

    def test_append_is_refused_and_the_blocker_is_recorded(self):
        """Measured over run `batch-d67136`: no promoted row named an existing
        unbuilt issue as the place its criterion belongs, so append would have
        fired zero times. An editor who meets a bare "do not append" will read
        it as caution and argue with it. The blocker is the reason."""
        brief = self.brief()
        self.assertIn("Never append", brief)
        self.assertIn("Never investigate", brief)
        self.assertIn("zero times", brief)

    def test_the_floor_is_named_as_what_the_severity_clause_protects(self):
        """Merging a `low` into a `medium` carries a row past the operator floor
        set on 2026-08-09. Clause 3 is the only thing standing there."""
        brief = self.brief()
        start = brief.index("same audience and the same severity")
        window = brief[start:start + 700]
        self.assertIn("floor", window)


class ParkedIsBelowTheBatchLine(unittest.TestCase):
    """Issue 03 of the tracker-tooling set, ruled by the human, 2026-09-13.

    Promotion mints a medium or low row that names no blocker at `Status:
    parked`, and nothing offers a parked issue again. `all` is the one scope
    that resolves itself off the `Status:` line, so a run that did not know the
    fifth status would build a backlog nobody has ever scheduled.

    The skill also has to name the door back. A status a run silently skips and
    no command ever re-offers is a deletion with a nicer name, which is the
    fault this issue exists to avoid rather than create.
    """

    PROMOTION = AGENTS / "promotion.md"

    def test_the_all_scope_skips_parked_beside_the_needs_rule(self):
        skill = squash(read(SKILL))
        start = skill.index("Skip `ready-for-human`")
        window = skill[start:start + 400]
        self.assertIn("`parked`", window)

    def test_the_skill_names_the_sweep_as_the_door_back(self):
        self.assertIn("sweep_parked.py", read(SKILL))

    def test_the_brief_parks_a_medium_row_that_names_no_blocker(self):
        brief = squash(read(self.PROMOTION))
        self.assertIn("Status: parked", brief)
        self.assertIn("`medium` or `low`", brief)

    def test_the_brief_keeps_needs_harden_for_high_and_above(self):
        brief = squash(read(self.PROMOTION))
        start = brief.index("Status: parked")
        window = brief[start - 600:start + 900]
        self.assertIn("high", window)
        self.assertIn("needs-harden", window)

    def test_the_brief_writes_the_date_the_sweep_ages_the_issue_off(self):
        """Either spelling of the sweep satisfies this, and that is deliberate.
        The live tree names the sweep script; this pack does not ship it and
        names the sweep by role instead. Both say the same thing, and the two
        facts that must travel are the same in both: the date field exists, and
        something ages the issue off it."""
        brief = squash(read(self.PROMOTION))
        self.assertIn("Parked:", brief)
        self.assertTrue(
            "parked sweep" in brief or "sweep_parked" in brief,
            "the brief writes `Parked:` and names nothing that reads it, so a "
            "parked issue is parked for ever",
        )

    def test_the_rule_names_the_check_that_refuses_it(self):
        """A rule that can refuse is built rather than written down twice
        (`~/.claude/CLAUDE.md`, the three classes). `check_origin.py --issue`
        already runs on every minted file, so it is where this lands."""
        brief = squash(read(self.PROMOTION))
        self.assertIn("check_origin.py --issue", brief)

    def test_the_finale_does_not_restate_the_minted_status(self):
        """The thresholds live in the promotion brief and nowhere else, and the
        status is now decided by the same row the thresholds read. A second copy
        here would go stale the next time the rule moves."""
        finale = squash(read(FINALE))
        self.assertNotIn("issue file at `Status: needs-harden`", finale)


class TheRetryBriefStatesTheInvariant(unittest.TestCase):
    """F3 of run `batch-d67136`, queued as `q-finale-d67136-2`.

    Issue 01 spent all three of its attempts on one connection-string guard.
    The round-1 verify verdict named the invariant AS an invariant, with its
    citation — `I-1 | The loader refuses any host but this machine | FAIL`, at
    line 514 of the issue file — and forty lines later proposed a remedy. The
    retry brief carried the remedy and dropped the invariant, so the implementer
    fixed exactly what it was told, and round 2 rejected on the same guard for a
    string the invariant covers and the remedy does not. Round 2's review gate
    PASSED, so round 3 — 622k tokens, 36.7 minutes — exists for that one reason.

    The fix is NOT a line in `run-issues-implementer.md`. That brief already
    ends with "do not trust its diagnosis. Re-derive from the issue and the
    code", the reminder is exact, and it failed. A second reminder is the class
    the human's three-class test refuses outright. `retry_brief.py` refuses instead,
    and this pins the step to it.
    """

    RETRY = RUN_ISSUES / "retry_brief.py"

    def test_the_script_it_names_is_on_disk(self):
        self.assertTrue(self.RETRY.exists())

    def test_step_seven_names_the_script(self):
        self.assertIn("retry_brief.py", read(SKILL))

    def test_the_rule_is_stated_for_both_lists(self):
        """One rule serves the owed list and the not-yours list. Step 7 already
        called the not-yours list checked and not asserted, and until this
        script nothing checked it."""
        skill = read(SKILL)
        start = skill.index("retry_brief.py")
        window = skill[start - 1500:start + 2000]
        self.assertIn("quotes the issue's own text", window)
        self.assertIn("not-yours", window)

    def test_the_story_landed_in_decisions_and_not_in_the_skill(self):
        """Ruling 9. `SKILL.md` sat one line under its ceiling, so the rule
        anchor stays there and the round it cost goes to `decisions.md`. An
        editor who pastes the story back breaks the ceiling that forced it out."""
        decisions, skill = read(DECISIONS), read(SKILL)
        for mark in ("622k tokens and 36.7 minutes", "q-finale-d67136-2"):
            with self.subTest(mark=mark):
                self.assertIn(mark, decisions)
                self.assertNotIn(mark, skill)

    def test_the_remedy_is_demoted_and_not_banned(self):
        """A gate's proposed fix is often right and always useful. What it may
        not be is the owed item. An editor who reads this as a ban will drop
        `--remedy`, and the next brief will carry the remedy in the owed text."""
        decisions = read(DECISIONS)
        self.assertIn("--remedy", decisions)
        self.assertIn("one example", decisions)

    def test_the_skill_keeps_the_rule_and_points_at_the_round_it_cost(self):
        """The anchor without the pointer is a rule with no cost beside it, and
        a rule with no cost reads as caution and gets waived."""
        skill = read(SKILL)
        start = skill.index("retry_brief.py")
        self.assertIn("decisions.md", skill[start:start + 400])


# --------------------------------------------------------------------------
# A whole-tree reading is bought only where the tree has changed since the last
# one, and only by a party that did not write the change. Three readings satisfy
# that rule: the implementer's own, the verify gate's with coverage, and the
# runner's after the correction round. Every other reading in the loop reads a
# tree that has not moved since one of the three.
#
# Graded against the RULE and not against a list of names. A sixth role added
# later earns a reading by the rule; a gate that reads an unmoved tree breaches
# it even though it is not named below.

# Both halves of the sentence are required. A brief that denies itself the suite
# and then names no substitute has told the gate to read less and given it
# nothing to cite, which is how a gate talks itself back into the suite.
NO_SUITE_DENIAL = ("runs no full suite", "no whole-suite run", "runs no whole suite")
NO_SUITE_SUBSTITUTE = ("verify gate's", "verify gate’s")


def review_gate_briefs():
    """Every review-gate brief, derived rather than named.

    Three hard-coded names would pass a fifth brief added later that orders a
    whole suite, which is the breach the rule exists to catch.
    """
    return sorted(AGENTS.glob("run-issues-review-gate*.md"))


class NoGateBuysAnUnmovedTreeReading(unittest.TestCase):
    """Criterion 1 of issue 06, `three suites per issue`."""

    def test_at_least_one_review_gate_brief_is_found(self):
        """The derived list is the point of the criterion. An empty glob would
        make every assertion below vacuous and still report green."""
        self.assertTrue(
            review_gate_briefs(),
            f"no run-issues-review-gate*.md under {AGENTS}; the glob found "
            "nothing, so the assertions below would pass on an empty list",
        )

    READ_PROOF = "THE LEDGER'S HEADER CARRIES THE RUN FACTS"

    def _proof(self, path, brief):
        """Quote text found INSIDE the brief in every failure message.

        Criterion 1's drive has a wrong reason it could go red: the briefs
        resolve through `Path.home()`, so a red caused by the path reaching
        nothing looks exactly like the assertion working. A message carrying
        text this test just read out of the file tells the two apart.
        """
        found = self.READ_PROOF in brief
        return (f"read {len(brief)} chars from {path}; it "
                f"{'contains' if found else 'DOES NOT contain'} "
                f"\"{self.READ_PROOF}\"")

    def test_every_review_gate_brief_denies_itself_a_whole_suite(self):
        for path in review_gate_briefs():
            brief = squash(read(path))
            self.assertTrue(
                any(mark in brief for mark in NO_SUITE_DENIAL),
                f"{path.name} does not deny itself a whole-suite run. "
                f"Expected one of {NO_SUITE_DENIAL}. "
                + self._proof(path, brief),
            )

    def test_every_review_gate_brief_names_the_reading_it_cites_instead(self):
        """Both halves in the SAME passage, not merely both in the file.

        `verify gate's` occurs twice in the plain brief for unrelated reasons,
        so a file-wide search for it passes a brief that denies itself the
        suite and names no substitute at all — which is the exact breach
        criterion 1 asks this case to catch. The window is measured from the
        denial.
        """
        for path in review_gate_briefs():
            brief = squash(read(path))
            at = -1
            for mark in NO_SUITE_DENIAL:
                at = brief.find(mark)
                if at != -1:
                    break
            if at == -1:
                continue        # the denial case above owns this failure
            passage = brief[at:at + 500]
            self.assertTrue(
                any(mark in passage for mark in NO_SUITE_SUBSTITUTE),
                f"{path.name} denies itself the suite and names no substitute "
                "in the same passage. Name the verify gate's report as the "
                "whole-tree reading it cites instead. Passage read: "
                f"\"{passage[:200]}\"",
            )

    def test_the_review_gates_keep_the_drills_and_the_shared_header(self):
        """`Must still be true`: the cut is whole-suite runs, never single
        files. A brief that loses the header line while gaining the no-suite
        sentence is a breach, not a saving."""
        for path in review_gate_briefs():
            brief = squash(read(path))
            self.assertIn(
                "the full suite runs WITHOUT the canonical", brief,
                f"{path.name} lost the shared header line",
            )

    def test_the_implementer_brief_exempts_the_correction_spawn(self):
        brief = squash(read(AGENTS / "run-issues-implementer.md"))
        self.assertIn(
            "correction", brief.lower(),
            "the implementer brief never names the correction spawn",
        )
        self.assertTrue(
            any(mark in brief for mark in CORRECTION_EXEMPTION),
            "the implementer brief does not exempt the correction spawn from "
            f"the full suite. Expected one of {CORRECTION_EXEMPTION}.",
        )

    def test_the_verify_gates_whole_suite_is_untouched(self):
        """`Must still be true`: ruling Q4 gave the verify gate the suite. An
        edit that reads as trimming it is a breach of Q4, not a saving. Since
        2026-09-29 the gate's wrapper call may answer with the implementer's
        record for the same tree (the perf audit of 2026-09-28, fix 2); the
        reading is still the gate's to name."""
        brief = read(AGENTS / "run-issues-verify-gate.md")
        self.assertIn("RUN THE WHOLE SUITE IN THAT COPY, WITH COVERAGE", brief)


CORRECTION_EXEMPTION = (
    "correction spawn runs no full suite",
    "correction round runs no full suite",
    "A correction spawn does not run the full suite",
)



# --------------------------------------------------------------------------
# Criterion 2 of issue 06. A command that PRODUCES a coverage report carries
# `--coverage.reportOnFailure`; without it one timed-out file destroys the whole
# report and the runner regenerates it, which happened five times in
# `batch-7f5b53`.
#
# Graded by the property "invokes vitest or npm test AND asks for coverage",
# never by a count. Today exactly one command in SKILL.md matches, and a test
# that asserted "the one command" would pass a file that had lost it.

COVERAGE_ON_FAILURE = "--coverage.reportOnFailure"


SUITE_HEADS = ("npx vitest run", "vitest run", "npm test", "npm run test")


def command_texts(path):
    """Every shell command SKILL.md states, fenced blocks and inline spans.

    Markdown here is hard-wrapped, so a command routinely sits across two lines
    with its flags split. Each candidate is squashed before it is read, or the
    flag on the second line reads as absent.

    Inline spans are NOT found by pairing backticks across the file. SKILL.md
    holds 904 of them, and bold-inside-code plus fenced markers make sequential
    pairing drift until the spans it returns are prose. Each suite invocation is
    located directly instead and read to the next backtick, which is what closes
    every command this document states.
    """
    raw = read(path)
    found, inside, buffer = [], False, []
    for line in raw.splitlines():
        if line.lstrip().startswith("```"):
            if inside:
                found.append(" ".join(buffer))
                buffer = []
            inside = not inside
            continue
        if inside:
            buffer.append(line.strip())
    flat = squash(raw)
    for head in SUITE_HEADS:
        at = flat.find(head)
        while at != -1:
            stop = flat.find("`", at)
            found.append(flat[at:stop if stop != -1 else at + 200])
            at = flat.find(head, at + 1)
    return [squash(one) for one in found if one.strip()]


def produces_coverage(command):
    """A command that RUNS a suite and asks that suite for coverage.

    `check_diff_coverage.py --coverage <path>` CONSUMES a report and is not one
    of these: it invokes no suite, so it never reaches the first test.
    """
    runs_a_suite = ("vitest run" in command or "npm test" in command
                    or "npm run test" in command)
    return runs_a_suite and "coverage" in command


class EveryCoverageRunKeepsItsReportOnFailure(unittest.TestCase):
    """Criterion 2 of issue 06, `three suites per issue`."""

    def test_the_wrapper_adds_the_flag_to_every_suite_it_can_read(self):
        """Guard, since the perf audit of 2026-09-28. SKILL.md states no
        coverage command any more: `run_suite.py` adds the coverage flags to
        the Full suite command itself, so the property below may read an
        empty list, and this case is what holds the flag."""
        spec = importlib.util.spec_from_file_location(
            "run_suite", Path(__file__).resolve().parent / "run_suite.py")
        run_suite = importlib.util.module_from_spec(spec)
        # Registered first: its dataclass looks its own module up by name.
        __import__("sys").modules.setdefault("run_suite", run_suite)
        spec.loader.exec_module(run_suite)
        for command in (["npm", "test"], ["npx", "vitest", "run"],
                        ["npm", "run", "test", "--", "--silent"]):
            with self.subTest(command=command):
                ran, _ = run_suite.with_coverage(command, Path("/r"))
                self.assertIn(COVERAGE_ON_FAILURE + "=true", ran)

    def test_every_coverage_producing_command_carries_the_flag(self):
        for command in command_texts(SKILL):
            if not produces_coverage(command):
                continue
            self.assertIn(
                COVERAGE_ON_FAILURE, command,
                f"this command produces a coverage report without "
                f"{COVERAGE_ON_FAILURE}, so one timeout destroys it:\n  {command}",
            )

    def test_a_consumer_of_a_report_is_not_asked_for_the_flag(self):
        """`check_diff_coverage.py --coverage <path>` reads a report. A test
        that demanded the flag there would refuse a correct file."""
        consumers = [one for one in command_texts(SKILL)
                     if "check_diff_coverage.py" in one]
        self.assertTrue(consumers, "SKILL.md no longer states the check command")
        for one in consumers:
            self.assertFalse(
                produces_coverage(one),
                f"the check command is being read as a producer:\n  {one}",
            )


# --------------------------------------------------------------------------
# Tracker-tooling issue 13, fix F10 of the audit of 2026-09-23. A gate rejects
# only on a criterion or an invariant the issue holds. Eleven rejections across
# six runs graded beyond the criteria, and the verify gate's brief licensed it
# in so many words.

def gate_briefs():
    """The verify gate and every review gate, derived rather than named."""
    return [AGENTS / "run-issues-verify-gate.md"] + review_gate_briefs()


class TheGatesRejectOnlyOnTheCriteria(unittest.TestCase):

    def test_no_gate_brief_licenses_implied_criteria(self):
        for path in gate_briefs():
            brief = squash(read(path)).lower()
            for licence in ("implies rather than spells out",
                            "criteria the issue implies"):
                with self.subTest(brief=path.name, licence=licence):
                    self.assertNotIn(licence, brief)

    def test_every_gate_brief_names_the_rejection_rule(self):
        for path in gate_briefs():
            with self.subTest(brief=path.name):
                self.assertIn("Every REJECT ground names a criterion or an "
                              "invariant", squash(read(path)))

    def test_every_gate_brief_says_where_a_finding_beyond_them_goes(self):
        for path in gate_briefs():
            with self.subTest(brief=path.name):
                self.assertIn("Beyond the criteria:", read(path))

    def test_unrequired_scope_is_no_longer_a_rejection_by_itself(self):
        for path in review_gate_briefs():
            with self.subTest(brief=path.name):
                self.assertNotIn("Unrequired scope is a rejection",
                                 squash(read(path)))

    def test_step_seven_says_an_owed_item_names_what_it_fails(self):
        skill = squash(read(SKILL))
        start = skill.index("retry_brief.py")
        self.assertIn("names the criterion or invariant it fails",
                      skill[start - 1500:start + 1500])


# --------------------------------------------------------------------------
# Tracker-tooling issue 14, fix F11 of the audit of 2026-09-23. A script
# decides split against strike; the runner no longer chooses between two rules.

class TheSplitIsTheScripts(unittest.TestCase):

    def test_no_split_takes_the_stricter_verdict(self):
        self.assertNotIn("stricter verdict", squash(read(SKILL)))

    def test_the_script_the_skill_names_is_on_disk(self):
        self.assertTrue((RUN_ISSUES / "charge_round.py").exists())
        self.assertIn("charge_round.py", read(SKILL))

    def test_the_standards_split_paragraph_hands_the_decision_to_the_script(self):
        skill = squash(read(SKILL))
        start = skill.index("A standards-shaped split is a correction")
        self.assertIn("charge_round.py", skill[start:start + 900])

    def test_every_gate_brief_ends_its_verdict_with_a_grades_line(self):
        for path in gate_briefs():
            brief = squash(read(path))
            with self.subTest(brief=path.name):
                self.assertIn("Grades: C1=pass", brief)
                for word in ("`pass`", "`fail`", "`owed`", "`fault`"):
                    self.assertIn(word, brief)



# --------------------------------------------------------------------------
# Tracker-tooling issue 15, fix F12 of the audit of 2026-09-23. A round states
# what it charged, and a check refuses a row that does not.

class TheLedgerStatesEachCharge(unittest.TestCase):

    def test_step_one_stamps_the_charge(self):
        self.assertIn("charge=<strike|correction|none>", squash(read(SKILL)))

    def test_a_reset_names_its_round(self):
        self.assertIn("criteria reset after gates <N>", squash(read(SKILL)))

    def test_the_commit_step_runs_the_charge_check(self):
        self.assertIn("check_attempt_cap.py --ledger <run.md> --issue <id> "
                      "--charges", squash(read(SKILL)))

    def test_the_skill_no_longer_says_nothing_refuses_the_row(self):
        self.assertNotIn("Nothing refuses a row without it", squash(read(SKILL)))



# --------------------------------------------------------------------------
# Tracker-tooling issue 16, the verify-gate half of fix F14 of the audit of
# 2026-09-23: the coverage suite took about 180 seconds alone on one project and
# about 400 with a second run beside it, and the brief said 83.

class TheVerifyGateStatesTheMeasuredSuiteTime(unittest.TestCase):

    def test_no_stale_suite_time(self):
        brief = squash(read(AGENTS / "run-issues-verify-gate.md"))
        self.assertNotIn("about 83 seconds", brief)

    def test_the_figure_carries_its_date_and_repository(self):
        brief = squash(read(AGENTS / "run-issues-verify-gate.md"))
        start = brief.index("RUN THE WHOLE SUITE IN THAT COPY")
        passage = brief[start:start + 1200]
        self.assertIn("2026-09-23", passage)
        # The live drill pins the project's name here; the published brief
        # names it by role, and this pins that wording instead.
        self.assertIn("On one project", passage)


# --------------------------------------------------------------------------
# Tracker-tooling issue 24, criterion 10. `~/.claude/hooks/run-issues-suite-gate.py`
# refuses every runner suite that does not go through `run_suite.py` at
# `baseline`, `correction` or `finale` (ruling `q-ti17-1`, 2026-09-23). A command
# this skill states and that hook refuses stops a run at the step that states it,
# so every one is put through the hook's own `decide()`, never a copy of its rule.

def suite_gate():
    spec = importlib.util.spec_from_file_location(
        "run_issues_suite_gate", HOOKS / "run-issues-suite-gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stated_commands(path):
    """Every line of every fenced block, a trailing `\\` joined to the next,
    and every inline code span outside the fences, whitespace squashed."""
    text = read(path)
    fenced = []
    for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S):
        fenced.extend(block.replace("\\\n", " ").splitlines())
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    spans = re.findall(r"`([^`]+)`", prose)
    return [" ".join(one.split()) for one in fenced + spans if one.strip()]


class EveryStatedSuitePassesTheSuiteGate(unittest.TestCase):

    TREE = "/Users/x/code/p/.claude/worktrees/run-issues-batch-abc123"

    def judged(self, path, state):
        gate = suite_gate()
        runs = [(self.TREE, state)]
        found = []
        for command in stated_commands(path):
            calls = gate.calls_of(command, self.TREE)
            if not calls:
                continue
            found.extend(calls)
            with self.subTest(file=path.name, command=command[:120]):
                self.assertIsNone(gate.decide("", command, self.TREE, runs))
        return found

    def test_every_suite_the_skill_states_passes(self):
        found = self.judged(SKILL, None)
        self.assertIn(("wrapper", "correction", self.TREE), found,
                      "SKILL.md states no correction-stage wrapper call")

    def test_every_suite_the_finale_states_passes_once_the_finale_is_written(self):
        found = self.judged(FINALE, "finale-mechanical")
        self.assertIn(("wrapper", "finale", self.TREE), found,
                      "finale.md states no finale-stage wrapper call")

    def test_the_finale_suite_stays_under_the_step_clock(self):
        line = [one for one in stated_commands(FINALE)
                if "run_suite.py --stage finale" in one]
        self.assertTrue(line)
        self.assertTrue(all("run_step.py" in one and "--kind suite" in one
                            for one in line), line)

    def test_the_refused_plain_suite_is_no_longer_offered(self):
        self.assertNotIn("Run one only where neither has read the tree",
                         squash(read(SKILL)))

    def test_the_ledger_header_puts_the_suite_after_the_wrappers_dashes(self):
        skill = squash(read(SKILL))
        at = skill.index("Full suite:")
        self.assertIn("run_suite.py --stage <stage> -- <this command>",
                      skill[at:at + 400])


# --------------------------------------------------------------------------
# Tracker-tooling issue 24, criterion 11. A gate writes its verdict to
# `runs/<batch-id>/verdicts/<issue>-attempt-<N>.md`, never into the issue file;
# the author's `gate-issue-write-guard.py` refuses the old road. That hook is not in
# this pack; the briefs still name it, as a guard the reader may register.

GATE_BRIEFS = ("run-issues-verify-gate.md", "run-issues-review-gate.md",
               "run-issues-review-gate-critical.md")

OLD_ROAD = (
    "Write your verdict into the issue file",
    "Write the verdict into the issue file",
    "Gates write verdicts into issue files",
    "the full text lives in the issue files",
)


class VerdictsGoToTheRun(unittest.TestCase):

    def test_no_brief_and_not_the_skill_sends_a_verdict_to_the_issue_file(self):
        for path in [SKILL] + [AGENTS / name for name in GATE_BRIEFS]:
            text = squash(read(path))
            for phrase in OLD_ROAD:
                with self.subTest(file=path.name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_every_gate_brief_names_the_verdicts_directory(self):
        for name in GATE_BRIEFS:
            with self.subTest(brief=name):
                text = squash(read(AGENTS / name))
                self.assertIn("runs/<batch-id>/verdicts/", text)
                self.assertIn("Verdict goes to:", text)
                self.assertIn("gate-issue-write-guard.py", text)

    def test_the_two_copies_paragraph_names_the_verdict_file_as_the_run_trees(self):
        """Each brief says every given path names the MAIN CHECKOUT copy. The
        verdict path names the run's own tree, and a gate that "corrects" it
        to the main checkout leaves `check_verdict.py` reading `absent`."""
        for name in GATE_BRIEFS:
            with self.subTest(brief=name):
                text = squash(read(AGENTS / name))
                at = text.index("THE RUN'S RECORDS EXIST TWICE")
                self.assertIn("The verdict file is the exception",
                              text[at:at + 1500])

    def test_the_round_header_names_the_verdict_file(self):
        """Issue 51 split the one file into one per gate."""
        skill = squash(read(SKILL))
        at = skill.index("Verdict goes to:")
        self.assertIn("verdicts/<issue>-attempt-<N>-review.md", skill[at:at + 300])

    def test_the_checks_are_pointed_at_the_verdict_file(self):
        """Issue 51: each check and each brief builder reads its gate's file."""
        skill = squash(read(SKILL))
        self.assertIn('check_verdict.py --file <verify file> --section "## '
                      'Verify gate"', skill)
        self.assertIn("check_drill_coverage.py --issue <issue file> --verdict "
                      "<review file>", skill)
        self.assertIn("--verdicts <review file> --verdicts <verify file>", skill)


class ALightIssueRunsTheLightRules(unittest.TestCase):
    """Tracker-tooling issue 40, AC4, AC5, AC7's finale call, AC8 and AC9."""

    HARDEN_TRIGGER = ("A typed issue in scope with no `Hardened:` line is the "
                      "trigger to read `launch-harden.md`")

    @staticmethod
    def paragraph_holding(text, needle):
        for paragraph in re.split(r"\n\s*\n", text):
            if needle in squash(paragraph):
                return squash(paragraph)
        raise AssertionError(f"no paragraph holds {needle!r}")

    def test_step_one_opens_with_the_level_branch_and_names_each_cut(self):
        """AC4."""
        skill = read(SKILL)
        start = skill.index("\n1. ", skill.index("## Per-issue loop"))
        step = squash(skill[start:skill.index("\n2. ", start)])
        self.assertTrue(step.startswith("1. **Branch on the issue's `Level:` "
                                        "line first**"), step[:80])
        branch = step[:step.index("**Settle the road before spawning.**")]
        for words in ("Level: light", "`run-issues-verify-gate` is spawned for "
                      "a full issue only", "`check_attempt_cap.py` caps it at two "
                      "attempts", "no `harden-issues-attacker`", "no whole suite",
                      "`run_suite.py --stage correction`",
                      "issue_level.py"):
            with self.subTest(words=words):
                self.assertIn(words, branch)

    def test_the_hardening_trigger_exempts_a_light_issue(self):
        """AC5, read in the trigger's own paragraph: the bullet's later
        paragraph already names `Level: light` for issue 43's `Light:` line."""
        paragraph = self.paragraph_holding(read(SKILL), self.HARDEN_TRIGGER)
        self.assertIn("a `Level: light` issue never is", paragraph)

    def test_the_finale_checks_the_briefing_names_every_blocked_issue(self):
        """AC7: the check is one the finale runs."""
        finale = squash(read(FINALE))
        self.assertIn("python3 ~/.claude/skills/run-issues/check_briefing_blocked.py"
                      " --ledger <run.md> --briefing", finale)
        self.assertTrue((RUN_ISSUES / "check_briefing_blocked.py").is_file())

    def test_the_implementer_brief_names_the_light_exception(self):
        """AC8."""
        text = read(AGENTS / "run-issues-implementer.md")
        paragraph = self.paragraph_holding(
            text, "**Run the FULL suite before you call the issue gate-ready.**")
        self.assertIn("Level: light", paragraph)
        light = paragraph[paragraph.index("Level: light"):]
        self.assertIn("the tests of the files it touched", light)
        self.assertIn("no whole suite", light)

    def test_the_review_brief_says_what_a_light_round_reads(self):
        """AC9, default `q-h0925-40-3`."""
        paragraph = self.paragraph_holding(
            read(AGENTS / "run-issues-review-gate.md"),
            "**This gate runs no full suite.**")
        self.assertIn("Level: light", paragraph)
        light = paragraph[paragraph.index("Level: light"):]
        self.assertIn("no verify gate", light)



class ALightIssueMeetsARiskPath(unittest.TestCase):
    """Tracker-tooling issue 42. AC5: the runner's road for a "needs the full
    level" report; AC7: the implementer's road out of the refusal."""

    PHRASE = "needs the full level"

    def step_holding(self, needle):
        skill = read(SKILL)
        loop = skill[skill.index("## Per-issue loop"):]
        loop = loop[:loop.index("\n## ", 1)]
        steps = re.split(r"\n(?=\d+\. )", loop)
        found = [squash(step) for step in steps if needle in squash(step)]
        self.assertEqual(len(found), 1, f"{len(found)} steps hold {needle!r}")
        return found[0]

    def test_one_step_names_the_whole_road(self):
        """AC5: `Level: full`, the critical review gate and the criteria fault,
        all inside the one step that holds the phrase."""
        step = self.step_holding(self.PHRASE)
        for mark in ("Level: full", "run-issues-review-gate-critical",
                     "criteria fault", "run-issues-implementer",
                     "run-issues-risk-path-guard.py", "run's own tree"):
            with self.subTest(mark=mark):
                self.assertIn(mark, step)

    def test_the_no_issue_writes_paragraph_allows_the_rewrite(self):
        """AC5's second half: the paragraph that forbids the runner an issue
        write names the `Level:` rewrite it allows."""
        skill = read(SKILL)
        for paragraph in re.split(r"\n\s*\n", skill):
            if paragraph.startswith("**Nothing in a run writes an issue file.**"):
                self.assertIn("Level:", paragraph)
                self.assertIn("step 2", paragraph)
                return
        self.fail("no paragraph opens **Nothing in a run writes an issue file.**")

    def test_the_implementer_brief_names_the_refusal_and_the_road_out(self):
        """AC7: one paragraph says stop, write the record, leave the work
        uncommitted, and report the phrase."""
        text = read(AGENTS / "run-issues-implementer.md")
        paragraphs = [squash(p) for p in re.split(r"\n\s*\n", text)
                      if self.PHRASE in squash(p)]
        self.assertEqual(len(paragraphs), 1, paragraphs)
        for mark in ("stop", "## Implementation record, attempt N",
                     "uncommitted", "final message"):
            with self.subTest(mark=mark):
                self.assertIn(mark, paragraphs[0])

    def test_the_stories_that_paid_for_it_left_the_skill(self):
        """Ruling 9: the step's lines were paid for by story text whose home
        already held it, or that moved to `decisions.md` here. A paste-back
        breaks the ceiling that forced it out."""
        skill = read(SKILL)
        for mark in ("Effort is often NOT a flag",
                     "the night three agents each discovered",
                     "the run whose line printed too late",
                     "the night the advice was broken",
                     "silently failed to land"):
            with self.subTest(mark=mark):
                self.assertNotIn(mark, skill)
        homes = ((DECISIONS, "failed to land"),
                 (DECISIONS, "**The full suite runs without the canonical env file.**"),
                 (DECISIONS, "**The scopeless negative that shipped.**"),
                 (RUN_ISSUES / "read_session_settings.py", "batch-26c495"))
        for home, mark in homes:
            with self.subTest(home=home.name, mark=mark):
                self.assertIn(mark, read(home))


class TheCriteriaWinOverTheProse(unittest.TestCase):
    """Tracker-tooling issue 48. The implementer brief says the criteria win
    where an issue's prose disagrees; ruling `q-fin-bbc605-02`."""

    PHRASE = "the criteria win"

    # AC3: the paragraph at `54238bc`, where the agents repository stood when
    # this issue's branch started. The criteria win over the prose, and an
    # implementer who finds the criteria themselves wrong still stops.
    WRONG = (
        "**If the acceptance criteria are WRONG** — not merely hard, but "
        "incorrect or materially incomplete — stop, do not build to them, and "
        "say so with the concrete evidence that shows it. A gate will confirm "
        "or reject your claim. This is not an exit from difficult work; \"I "
        "could not meet the criteria\" is a different report and belongs under "
        "blocked.")

    def paragraphs(self):
        text = read(AGENTS / "run-issues-implementer.md")
        return [squash(p) for p in re.split(r"\n\s*\n", text)]

    def index_holding(self, paragraphs, needle):
        found = [i for i, p in enumerate(paragraphs) if needle in p]
        self.assertEqual(len(found), 1, f"{len(found)} paragraphs hold {needle!r}")
        return found[0]

    def test_one_paragraph_says_the_criteria_win(self):
        """AC1 and AC2: one paragraph names both sections, the rulings and the
        prose, between the Hold paragraph and the Scope paragraph."""
        paragraphs = self.paragraphs()
        here = self.index_holding(paragraphs, self.PHRASE)
        for mark in ("## Acceptance criteria", "## Must still be true",
                     "ruling", "prose"):
            with self.subTest(mark=mark):
                self.assertIn(mark, paragraphs[here])
        hold = self.index_holding(paragraphs,
                                  "**Hold what the issue does not mention.**")
        scope = self.index_holding(paragraphs, "**Scope.**")
        self.assertLess(hold, here)
        self.assertLess(here, scope)

    def test_the_wrong_criteria_paragraph_is_unchanged(self):
        """AC3."""
        paragraphs = self.paragraphs()
        here = self.index_holding(paragraphs,
                                  "**If the acceptance criteria are WRONG**")
        self.assertEqual(paragraphs[here], self.WRONG)



class EachGateHasItsOwnVerdictFile(unittest.TestCase):
    """Issue 51 of the tracker-tooling set, AC6, ruling `q-fin-ea4cfa-05`: the
    round header names one verdict file per gate, and so does every brief."""

    HEADER = (
        "Verdict goes to:  <run tree>/.scratch/<feature>/runs/<batch-id>/"
        "verdicts/<issue>-attempt-<N>-review.md (review gate); <same directory>/"
        "<issue>-attempt-<N>-verify.md (verify gate)")
    BRIEFS = {"run-issues-review-gate.md": "-review.md",
              "run-issues-review-gate-critical.md": "-review.md",
              "run-issues-verify-gate.md": "-verify.md"}

    def test_the_round_header_names_both_files(self):
        self.assertIn(self.HEADER, read(SKILL))

    def test_each_check_reads_its_own_gates_file(self):
        skill = read(SKILL)
        for script in ("lib/check_verdict.py --file",
                       "check_drill_coverage.py --issue <issue file> --verdict"):
            for gate, heading in (("review", "Review"), ("verify", "Verify")):
                with self.subTest(script=script, gate=gate):
                    self.assertIn(f"{script} <{gate} file> --section "
                                  f'"## {heading} gate"', skill)
        self.assertNotIn("<verdict file>", skill)

    def test_each_brief_names_its_own_file_and_no_shared_one(self):
        for name, ending in self.BRIEFS.items():
            brief = read(AGENTS / name)
            with self.subTest(brief=name):
                self.assertNotIn("attempt-<N>.md", brief)
                self.assertIn(ending, brief)
        self.assertNotIn("Append only", read(AGENTS / "run-issues-verify-gate.md"))


# --- The wakeup cron ruling (the human, 2026-09-29) -------------------------
#
# Every 30 minutes, resume only a run idle for more than 20, delete at
# awaiting-merge or halt, and a forgotten cron is refused by a hook rather than
# reminded. The cadence and the idle test live in `wakeup_cron.py` and its own
# tests; these pin that each loaded file sends the runner to the machinery.

WAKEUP = RUN_ISSUES / "wakeup_cron.py"
WAKEUP_GATE = HOOKS / "run-issues-wakeup-gate.py"


class TheWakeupCronIsMadeRecordedAndDeleted(unittest.TestCase):
    def test_the_script_and_the_hook_are_on_disk(self):
        self.assertTrue(WAKEUP.is_file())
        self.assertTrue(WAKEUP_GATE.is_file())

    def test_the_skill_makes_the_cron_from_the_script_and_names_the_hook(self):
        skill = squash(read(SKILL))
        self.assertIn("wakeup_cron.py args --ledger <run.md>", skill)
        self.assertIn("wakeup_cron.py record --ledger <run.md> --id <job id>", skill)
        self.assertIn("run-issues-wakeup-gate.py", skill)
        self.assertIn("at launch and on every resume, before spawn 1", skill)

    def test_the_skill_deletes_the_cron_where_it_clears_the_owner_line(self):
        skill = squash(read(SKILL))
        at = skill.index("The owner line is cleared, and the cron deleted")
        window = skill[at:at + 500]
        self.assertIn("CronDelete", window)
        self.assertIn("wakeup_cron.py clear", window)

    def test_the_overruled_interval_claim_is_gone(self):
        self.assertNotIn("shortening the interval buys nothing", read(SKILL))
        self.assertNotIn("at its usage-limit interval", read(SKILL))

    def test_the_preflight_allows_all_three_cron_tools(self):
        skill = squash(read(SKILL))
        at = skill.index("**The runner itself**")
        for tool in ("CronList", "CronCreate", "CronDelete"):
            self.assertIn(tool, skill[at:at + 200])

    def test_the_finale_deletes_the_cron_before_awaiting_merge(self):
        finale = squash(read(FINALE))
        self.assertIn("**Before `awaiting-merge`, `CronDelete` the wakeup cron", finale)
        self.assertIn("wakeup_cron.py clear --ledger <run.md>", finale)

    def test_the_resume_recreates_without_doubling(self):
        resume = squash(read(RESUME))
        self.assertIn("Recreate it, never double it.", resume)
        self.assertIn("Run `CronList` first.", resume)

    def test_decisions_holds_the_ruling_and_the_option_taken(self):
        decisions = squash(read(DECISIONS))
        self.assertIn("The wakeup cron fires every 30 minutes and cannot be"
                      " forgotten (2026-09-29)", decisions)
        self.assertIn("Taken: the first, with the process id on the line.",
                      decisions)

    def test_the_round_header_reason_moved_and_did_not_stay(self):
        mark = "settlement parity into a structural fact"
        self.assertIn(mark, squash(read(DECISIONS)))
        self.assertNotIn(mark, squash(read(SKILL)))


if __name__ == "__main__":
    unittest.main()
