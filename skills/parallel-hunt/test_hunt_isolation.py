#!/usr/bin/env python3
"""Ticket 38 of the pilot-delivery map, sitting 4: a hunt in its own worktree,
beside a live run.

Rulings 6 and 22. The pre-flight refusal that stopped a hunt beside a live run
went with its cause, which was sharing the main checkout. A hunt now takes what
a run takes: a hunt id, a worktree, a QA workspace and user, the dev server by
name with its port read off the result, the Zoho lock, and a finale that deletes
the workspace. The rules live in skill text and agent briefs, so these tests
read that text.
"""

import os
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent
# The agent files live in the plugin's `agents/` folder beside `skills/`.
PLUGIN = SKILLS.parent
SKILL = (HERE / "SKILL.md").read_text()
AGENTS = {
    name: (PLUGIN / "agents" / f"parallel-hunt-{name}.md").read_text()
    for name in ("finder", "fixer", "claim-gate", "fix-gate", "fix-gate-critical")
}

# The env file is the repo's own, and this text is shared by two repos, so
# the skill spells the placeholder and the repo's `.claude/run-classes.json`
# carries the real one. Until 2026-09-13 this text named TenderFlow's file,
# which holds a live service-role key, and every OrderFlow run read it.
ENV = "<the repo's canonical env file>"
TENDERFLOW_ENV = os.path.expanduser("~/code/procurement/.procurement-spine.env")
PREFLIGHT = SKILL[SKILL.index("## Pre-flight"):SKILL.index("## Also fits")]
ROUND_END = SKILL[SKILL.index("6. Round end"):SKILL.index("## Auto-resume")]


class TestTheRefusalWentWithItsCause(unittest.TestCase):
    def test_the_two_main_checkout_bullets_are_gone(self):
        for phrase in ("One skill per checkout", "One tree, one branch",
                       "both work in the main checkout", "hunt/<scope>",
                       "puts two writers in one tree"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, SKILL)

    def test_a_hunt_no_longer_waits_for_awaiting_merge(self):
        self.assertNotIn("awaiting-merge", PREFLIGHT)

    def test_the_register_section_no_longer_defers_to_sitting_4(self):
        self.assertNotIn("is ticket 38's sitting 4", SKILL)


class TestAHuntIsARunForIsolation(unittest.TestCase):
    def test_the_hunt_id_is_minted_like_a_batch_id_and_the_worktree_is_cut_on_it(self):
        self.assertRegex(PREFLIGHT, r"`hunt-` plus\s+six hex characters \(`openssl rand -hex 3`\)")
        self.assertIn("git worktree add", PREFLIGHT)
        self.assertIn("hunt/<hunt-id>", PREFLIGHT)

    def test_the_seed_runs_after_the_id_and_writes_the_brief(self):
        seed = f"node --env-file={ENV} scripts/seed-run-workspace.mjs --batch <hunt-id> --ledger <round-brief.md>"
        self.assertIn(seed, PREFLIGHT)
        self.assertLess(PREFLIGHT.index("openssl rand -hex 3"), PREFLIGHT.index(seed))
        # Sitting 5: the scripts read the id off the brief themselves; the skill states that and never asks a role to set it.
        self.assertIn("seedWorkspaceId", SKILL)
        self.assertNotIn("defaults `SEED_WORKSPACE_ID`", SKILL)
        self.assertNotIn("sets `SEED_WORKSPACE_ID`", SKILL)

    def test_the_round_block_carries_every_place_a_role_needs(self):
        block = re.search(r"```\nHunt:.*?```", SKILL, re.S)
        self.assertIsNotNone(block, "no round block starting with Hunt:")
        for field in ("Hunt:", "Worktree:", "Branch:", "QA workspace:", "Sign-in user:", "Sign-in link:",
                      "Dev server:", "Zoho lock:", "Register shard:", "Bugs:", "Journal:"):
            with self.subTest(field=field):
                self.assertIn(field, block.group(0))

    def test_the_brief_starts_with_the_ledger_header_the_scripts_read(self):
        header = re.search(r"```\n# Round brief — <scope> \(hunt `<hunt-id>`\)\n.*?```", SKILL, re.S)
        self.assertIsNotNone(header, "no header block opening with the title line")
        for line in ("Owner: session", "Worktree:", "Branch:"):
            with self.subTest(line=line):
                self.assertIn(line, header.group(0))
        self.assertLess(SKILL.index("# Round brief — <scope>"), SKILL.index("```\nHunt:"))
        self.assertIn("ledgerHeaderFault", SKILL)

    def test_the_verdict_check_runs_against_the_hunt_worktree(self):
        rule4 = SKILL[SKILL.index("check it wrote a verdict"):SKILL.index("check_verdict.py --file")]
        self.assertNotIn("main checkout", rule4)
        self.assertIn("hunt's worktree", rule4)

    def test_the_finder_signs_in_as_the_hunt_user_on_the_hunt_host(self):
        self.assertIn(f"node --env-file={ENV} scripts/dev-signin-link.mjs --batch <hunt-id> --site http://<hunt-id>.localhost:<port from the preview_start result>", SKILL)
        self.assertNotRegex(SKILL, r"\b3101\b")

    def test_the_live_zoho_suites_go_through_the_lock_with_the_hunt_id(self):
        self.assertIn(f"node --env-file={ENV} scripts/zoho-live-lock.mjs --batch <hunt-id> --journal <round-journal.md>", SKILL)
        self.assertNotIn("ZOHO_LIVE=1 npx vitest", SKILL)

    def test_round_end_deletes_the_workspace_before_the_brief_that_names_it(self):
        delete = f"node --env-file={ENV} scripts/delete-run-workspace.mjs --batch <hunt-id> --ledger <round-brief.md>"
        self.assertIn(delete, ROUND_END)
        order = ROUND_END[:ROUND_END.index(delete)]
        self.assertLess(order.index("delete this round's QA workspace"), order.index("delete `round-brief.md`"))
        self.assertIn("exit 1", ROUND_END)

    def test_every_hunt_path_names_the_hunt_worktree_not_the_main_checkout(self):
        paths = re.search(r"```\n<hunt-worktree>.*?```", SKILL, re.S)
        self.assertIsNotNone(paths, "no paths block rooted at <hunt-worktree>")
        self.assertNotIn("<main-repo-root>/.scratch/<feature>/round-brief.md", SKILL)
        self.assertNotIn("<main-repo-root>/.scratch/<feature>/bugs", SKILL)
        self.assertIn("<hunt-worktree>/.scratch/<feature>/round-brief.md", SKILL)

    def test_resume_keys_on_the_hunt_worktree(self):
        resume = SKILL[SKILL.index("## Auto-resume"):SKILL.index("## Pre-flight")]
        self.assertIn("<hunt-worktree>/.scratch/<feature>/round-brief.md", resume)
        self.assertNotIn("<main-repo-root>", resume)
        self.assertIn("find_live_ledger.py --list", resume)
        self.assertIn("machine-preflight.py", resume)


class TestTheBriefsNameThePlace(unittest.TestCase):
    def test_every_role_works_in_the_hunt_worktree_the_spawn_names(self):
        for name, text in AGENTS.items():
            with self.subTest(agent=name):
                self.assertIn("hunt's worktree", text)
                self.assertNotIn("run's worktree", text)

    def test_finder_and_fixer_read_the_register_without_writing_main(self):
        """They read the whole register from the hunt's worktree. With
        `--write-main` that read changed main's tracked `register.md` under a
        live run; the human chose on 2026-10-01 a print mode that writes nothing,
        which leaves the round no reason to touch the main checkout."""
        for text in (AGENTS["finder"], AGENTS["fixer"], SKILL):
            with self.subTest(text=text[:40]):
                self.assertIn("collect_shards.py --kind register --feature <feature> --print",
                              text)
                self.assertNotIn("--write-main", text)

    def test_the_finder_and_fixer_seed_into_the_hunt_workspace(self):
        for name in ("finder", "fixer"):
            with self.subTest(agent=name):
                self.assertIn("seedWorkspaceId", AGENTS[name])
                self.assertIn("QA workspace:", AGENTS[name])
                self.assertNotIn("Set it to", AGENTS[name])
                self.assertNotIn("defaults `SEED_WORKSPACE_ID`", AGENTS[name])

    def test_the_finder_signs_in_and_locks_through_the_round_block_fields(self):
        """One spelling of each command, in the skill; the briefs point at the block."""
        finder = AGENTS["finder"]
        self.assertIn("`Sign-in link:`", finder)
        self.assertIn("<hunt-id>.localhost:<port>", finder)
        self.assertNotIn("--site http://localhost", finder)
        for name in ("finder", "fixer"):
            with self.subTest(agent=name):
                self.assertIn("`Zoho lock:`", AGENTS[name])
                self.assertNotIn("scripts/zoho-live-lock.mjs", AGENTS[name])

    def test_the_gates_copy_the_hunt_worktree_with_make_copy(self):
        """One maker for every gate copy: APFS clones, and a node_modules of the
        copy's own, because a hunt gate clears the test runner's cache."""
        for name in ("claim-gate", "fix-gate", "fix-gate-critical"):
            with self.subTest(agent=name):
                self.assertIn("make_copy.py --tree <the hunt's worktree>", AGENTS[name])
                self.assertIn(f"<entry>-{name} --own-node-modules", AGENTS[name])
                self.assertIn("Never copy the tree by hand.", AGENTS[name])


# TestTheDailyBriefSweepsHunts retired with daily-brief at the switch to version 2.


# TestTheMintedStatusIsReadWhereItIsRuled retired with issue 36 of the
# tracker-tooling set: a round no longer mints issues, so there is no minted
# status to read and no parked issue to sweep back (ruling q-h0925-36-2).


if __name__ == "__main__":
    unittest.main()
