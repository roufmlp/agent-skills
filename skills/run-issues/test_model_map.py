"""Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 1: the map, the default file and the launch line."""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import pipeline_fingerprint
import model_map as _mm

model_map_file = _mm.__file__
from model_map import (
    GATES,
    SPAWNED_BY,
    INHERIT,
    ROLES,
    WORKERS,
    DEFAULT_MAP_FILE,
    inheriting,
    inversions,
    parse_map,
    header_lines,
    ledger_map,
    read_default_map,
    read_map,
    resolve,
    resolve_launch,
    worker_cell,
    orchestrator_cell,
    EFFORTS,
    GATES,
    ROLES,
    role_efforts,
)


class ReadMap(unittest.TestCase):
    """Grammar only, no session model. `machine-preflight.py` row 14 reads a
    map at PROMPT-SUBMIT time, before a batch id is minted or a QA workspace is
    seeded (the human, 2026-09-05: a refusal must arrive in the first two minutes,
    not after the ledger exists). It cannot resolve `inherit` there without
    refusing on an unreadable session model, which the hook must never do, so
    the grammar half is split out and both callers share it."""

    def test_no_models_word_reads_the_default_file_and_inherits_everything(self):
        typed, applied, refusals = read_map("512 513")
        self.assertEqual(refusals, [])
        self.assertEqual(typed, read_default_map())
        self.assertEqual(set(applied.values()), {INHERIT})

    def test_the_models_word_typed_empty_is_refused(self):
        _, _, refusals = read_map("512 models:")
        self.assertEqual(len(refusals), 1)
        self.assertIn("REFUSED", refusals[0])

    def test_a_token_the_grammar_cannot_read_is_named_in_the_refusal(self):
        _, _, refusals = read_map("512 models: implementer=sonet gate=opus")
        self.assertEqual(len(refusals), 1)
        self.assertIn("implementer=sonet", refusals[0])
        self.assertIn("gate=opus", refusals[0])

    def test_a_full_map_leaves_nothing_inheriting(self):
        _, applied, refusals = read_map("512 models: all=opus implementer=sonnet")
        self.assertEqual(refusals, [])
        self.assertEqual(applied["implementer"], "sonnet")
        self.assertEqual(applied["promotion"], "opus")
        self.assertEqual(inheriting(applied), ())

    def test_a_partial_map_names_exactly_the_roles_still_inheriting(self):
        _, applied, refusals = read_map("512 models: implementer=sonnet gates=opus")
        self.assertEqual(refusals, [])
        self.assertEqual(
            inheriting(applied),
            ("escalated", "finale", "finder", "fixer", "promotion"))


class TheFourteenRoles(unittest.TestCase):
    """Ruling 5's grammar names one key per agent type without its prefix.

    Ticket 39 ruling 6 scoped the map to twelve loop roles and deferred the two
    hardening roles to ticket 33 by name. Ticket 33 ruling 2 of 2026-09-07 adds
    them as `attacker` and `seam` inside the `gates` group, so the map is
    fourteen roles and `model-map-gate.py` stops passing a harden spawn in
    silence."""

    def test_the_keys_are_ruling_5s_twelve_plus_ticket_33s_two(self):
        self.assertEqual(sorted(ROLES), sorted([
            "implementer", "escalated", "verify", "review", "review-critical",
            "finale", "finder", "fixer", "claim-gate", "fix-gate",
            "fix-gate-critical", "promotion", "attacker", "seam"]))

    def test_the_two_hardening_roles_name_the_two_harden_issues_briefs(self):
        self.assertEqual(ROLES["attacker"], "harden-issues-attacker")
        self.assertEqual(ROLES["seam"], "harden-issues-seam")

    def test_both_hardening_roles_sit_inside_the_gates_group(self):
        """Ruling 2's stated width. `gates=fable` therefore reaches them, which
        is the whole point: one word still names every adversarial role."""
        self.assertIn("attacker", GATES)
        self.assertIn("seam", GATES)
        self.assertEqual(resolve([("gates", "fable")], "opus")["attacker"], "fable")
        self.assertEqual(resolve([("gates", "fable")], "opus")["seam"], "fable")

    def test_neither_hardening_role_checks_a_worker_so_neither_can_invert(self):
        """Ruling 14 refuses a gate below the worker it checks. An attacker
        checks an ISSUE FILE, not a worker's diff, so it is in no pair. Putting
        it in one would force `attacker` up to the implementer's tier for a job
        that reads a markdown file, and would refuse a legal map."""
        checked = {gate for gate, _ in _mm.CHECKS}
        self.assertNotIn("attacker", checked)
        self.assertNotIn("seam", checked)
        self.assertEqual(
            inversions(resolve([("implementer", "opus"), ("gates", "opus"),
                                ("attacker", "haiku"), ("seam", "haiku")],
                               "opus")),
            [])

    def test_every_key_names_an_agent_file_that_exists(self):
        agents = os.path.expanduser("~/.claude/agents")
        for role, agent_type in ROLES.items():
            self.assertTrue(
                os.path.exists(os.path.join(agents, agent_type + ".md")),
                f"{role} names {agent_type}, which has no agent file")

    def test_workers_and_gates_do_not_overlap(self):
        self.assertEqual(set(WORKERS) & set(GATES), set())


class WhichRolesACommandCanSpawn(unittest.TestCase):
    """A run never spawns a finder; a hunt never spawns a verify gate. Row 14
    refuses what INHERITS, so it must count only the roles the command in front
    of it can actually spawn, or it names roles that cannot run."""

    def test_the_two_lists_cover_every_role_between_them(self):
        self.assertEqual(
            set(SPAWNED_BY["/run-issues"]) | set(SPAWNED_BY["/parallel-hunt"]),
            set(ROLES))

    def test_promotion_is_the_only_role_both_commands_spawn(self):
        self.assertEqual(
            set(SPAWNED_BY["/run-issues"]) & set(SPAWNED_BY["/parallel-hunt"]),
            {"promotion"})

    def test_a_run_spawns_no_hunt_role(self):
        self.assertEqual(set(SPAWNED_BY["/run-issues"]) & set(WORKERS),
                         {"implementer", "escalated"})

    def test_a_run_spawns_both_hardening_roles_and_a_hunt_spawns_neither(self):
        """Strike-2 mode spawns `harden-issues-attacker` inside a run today, and
        the launch phase of ticket 33 sitting 2 spawns both. A hunt hardens
        nothing, so naming them there would list roles that cannot start --
        the exact fault the 2026-09-05 review of sitting 2 found for finders."""
        self.assertTrue({"attacker", "seam"} <= set(SPAWNED_BY["/run-issues"]))
        self.assertEqual(
            {"attacker", "seam"} & set(SPAWNED_BY["/parallel-hunt"]), set())

    def test_a_run_map_naming_only_the_old_twelve_leaves_the_two_inheriting(self):
        """The behaviour change row 14 of `machine-preflight.py` now sees. Before
        ticket 33 this map named every role a run could spawn."""
        _, applied, refusals = read_map(
            "512 models: implementer=opus escalated=opus verify=opus "
            "review=opus review-critical=opus finale=opus promotion=opus")
        self.assertEqual(refusals, [])
        spawnable = set(SPAWNED_BY["/run-issues"])
        self.assertEqual(
            tuple(r for r in inheriting(applied) if r in spawnable),
            ("attacker", "seam"))


class ParseMap(unittest.TestCase):
    def test_ruling_5s_own_example(self):
        self.assertEqual(parse_map("implementer=opus gates=fable"),
                         ([("implementer", "opus"), ("gates", "fable")], []))

    def test_an_empty_map_is_no_assignments_and_no_bad_token(self):
        self.assertEqual(parse_map(""), ([], []))

    def test_an_override_word_typed_inside_the_map_is_not_a_bad_token(self):
        """The scope grammar has skipped `force-machine`, `force-version` and
        `force-model` since they existed; the map grammar did not, so
        `models: implementer=opus force-model` was refused as a typo. The words
        are addressed to `machine-preflight.py`, and a person types them where
        the sentence ends."""
        pairs, bad = parse_map("implementer=opus force-model")
        self.assertEqual(pairs, [("implementer", "opus")])
        self.assertEqual(bad, [])

    def test_the_override_word_is_read_whatever_its_case(self):
        """`machine-preflight.py` lowercases the prompt before it parses, and the
        launch line does not. So `Force-Model` cleared prompt submit and then
        died at the launch line, after the batch id and the QA workspace existed
        — the exact late failure the human ruled against on 2026-09-05."""
        self.assertEqual(parse_map("implementer=opus Force-Model"),
                         ([("implementer", "opus")], []))

    def test_a_key_the_grammar_does_not_know_is_reported_not_dropped(self):
        pairs, bad = parse_map("implementer=opus reviewer=sonnet")
        self.assertEqual(pairs, [("implementer", "opus")])
        self.assertEqual(bad, ["reviewer=sonnet"])

    def test_a_model_the_agent_tool_cannot_reach_is_reported(self):
        pairs, bad = parse_map("implementer=deepseek")
        self.assertEqual((pairs, bad), ([], ["implementer=deepseek"]))

    def test_a_token_carrying_no_equals_is_reported(self):
        self.assertEqual(parse_map("opus")[1], ["opus"])

    def test_commas_separate_as_they_do_in_the_scope(self):
        self.assertEqual(parse_map("implementer=opus,gates=sonnet")[0],
                         [("implementer", "opus"), ("gates", "sonnet")])

    def test_inherit_is_a_legal_value_because_the_default_file_carries_it(self):
        self.assertEqual(parse_map("all=inherit"), ([("all", "inherit")], []))


class Resolve(unittest.TestCase):
    """Ruling 4: the map is resolved fully at launch. Every role gets a concrete
    name and `inherit` never appears in a ledger."""

    def test_an_empty_map_puts_the_session_model_on_all_twelve(self):
        got = resolve([], "opus")
        self.assertEqual(set(got), set(ROLES))
        self.assertEqual(set(got.values()), {"opus"})

    def test_inherit_resolves_to_the_session_model_and_never_survives(self):
        got = resolve([("all", "inherit")], "fable")
        self.assertEqual(set(got.values()), {"fable"})
        self.assertNotIn("inherit", got.values())

    def test_a_role_key_beats_a_group(self):
        got = resolve([("gates", "sonnet"), ("verify", "opus")], "haiku")
        self.assertEqual(got["verify"], "opus")
        self.assertEqual(got["review"], "sonnet")

    def test_a_group_beats_all_whatever_the_order_typed(self):
        typed_after = resolve([("all", "sonnet"), ("workers", "opus")], "haiku")
        typed_before = resolve([("workers", "opus"), ("all", "sonnet")], "haiku")
        self.assertEqual(typed_after, typed_before)
        self.assertEqual(typed_after["implementer"], "opus")
        self.assertEqual(typed_after["promotion"], "sonnet")

    def test_the_last_value_wins_at_one_specificity(self):
        got = resolve([("implementer", "opus"), ("implementer", "sonnet")], "haiku")
        self.assertEqual(got["implementer"], "sonnet")

    def test_the_session_model_is_taken_as_a_bare_tier_name(self):
        """The ledger records `claude-opus-5`; the Agent tool takes `opus`."""
        self.assertEqual(set(resolve([], "claude-opus-5").values()), {"opus"})

    def test_a_session_model_it_cannot_read_refuses_rather_than_guessing(self):
        with self.assertRaises(ValueError):
            resolve([], "unmeasured")

    def test_a_session_model_is_not_needed_when_every_role_is_named(self):
        got = resolve([("all", "sonnet")], "unmeasured")
        self.assertEqual(set(got.values()), {"sonnet"})


class Inversions(unittest.TestCase):
    """Ruling 1 and ruling 14, standing on the 2026-08-15 gate-tier ruling
    (`~/.claude/rulings.md:99-121`): no adversarial gate runs below the tier of
    the worker it checks. A wrong reject costs one retry round; a wrong pass has
    no catcher until the merge. Tier order `haiku < sonnet < opus < fable`."""

    def test_the_tickets_own_example_map_is_the_inversion_it_refuses(self):
        found = inversions(resolve([("implementer", "opus"), ("gates", "sonnet")], "opus"))
        self.assertTrue(found)
        self.assertTrue(any("verify" in line for line in found))
        self.assertTrue(any("review" in line for line in found))

    def test_equal_is_legal(self):
        self.assertEqual(inversions(resolve([("all", "sonnet")], "sonnet")), [])

    def test_a_gate_above_its_worker_is_legal(self):
        got = resolve([("workers", "sonnet"), ("gates", "opus")], "opus")
        self.assertEqual(inversions(got), [])

    def test_a_gate_is_measured_against_the_escalated_implementer_too(self):
        got = resolve([("implementer", "sonnet"), ("escalated", "fable"),
                       ("gates", "sonnet")], "sonnet")
        self.assertTrue(inversions(got))

    def test_the_claim_gate_is_measured_against_the_finder(self):
        got = resolve([("finder", "opus"), ("claim-gate", "haiku")], "opus")
        self.assertEqual(len(inversions(got)), 1)
        self.assertIn("claim-gate", inversions(got)[0])

    def test_the_fix_gates_are_measured_against_the_fixer(self):
        got = resolve([("fixer", "fable"), ("fix-gate", "opus"),
                       ("fix-gate-critical", "fable")], "fable")
        found = inversions(got)
        self.assertEqual(len(found), 1)
        self.assertIn("fix-gate", found[0])

    def test_a_hunt_gate_is_not_measured_against_a_run_worker(self):
        """The finder never checks an implementer, so a cheap finder beside an
        expensive implementer is not an inversion."""
        got = resolve([("implementer", "fable"), ("finder", "haiku"),
                       ("claim-gate", "haiku"), ("gates", "fable")], "fable")
        self.assertEqual(inversions(got), [])

    def test_a_refusal_names_both_models_so_it_can_be_retyped(self):
        line = inversions(resolve([("implementer", "opus"), ("verify", "haiku")], "opus"))[0]
        self.assertIn("haiku", line)
        self.assertIn("opus", line)


class TheDefaultFile(unittest.TestCase):
    """Ruling 3: one map file in the skill directory, read at launch when no map
    is typed, starting at `all=inherit`."""

    def test_the_shipped_file_exists_and_starts_at_all_inherit(self):
        self.assertTrue(os.path.exists(DEFAULT_MAP_FILE), DEFAULT_MAP_FILE)
        pairs, bad = parse_map(read_default_map())
        self.assertEqual(bad, [])
        self.assertEqual(pairs, [("all", "inherit")])

    def test_the_shipped_default_leaves_every_role_on_the_session_model(self):
        got = resolve(parse_map(read_default_map())[0], "opus")
        self.assertEqual(set(got.values()), {"opus"})
        self.assertEqual(inversions(got), [])

    def test_comments_and_blank_lines_are_not_tokens(self):
        with tempfile.NamedTemporaryFile("w", suffix=".default", delete=False) as handle:
            handle.write("# the default\n\nall=inherit\ngates=opus\n")
            path = handle.name
        try:
            self.assertEqual(parse_map(read_default_map(path)),
                             ([("all", "inherit"), ("gates", "opus")], []))
        finally:
            os.unlink(path)

    def test_a_missing_default_file_reads_as_all_inherit(self):
        self.assertEqual(read_default_map("/nonexistent/model-map.default").strip(),
                         "all=inherit")


class RoleEfforts(unittest.TestCase):
    """Ruling 7: effort stays in the agent file and the ledger records it. The
    Agent tool has no effort field, so this is read, never set."""

    def test_it_reads_the_fourteen_agent_files_as_they_stand_today(self):
        got = role_efforts()
        self.assertEqual(set(got), set(ROLES))
        self.assertEqual(got["finale"], "max")
        self.assertEqual(got["finder"], "xhigh")
        self.assertEqual(got["promotion"], "medium")
        self.assertEqual(got["implementer"], "high")

    def test_the_two_hardening_briefs_state_their_effort_and_are_read(self):
        """`harden-issues/SKILL.md` states `high` for both, and the ledger now
        records it rather than the skill line being the only home."""
        got = role_efforts()
        self.assertEqual(got["attacker"], "high")
        self.assertEqual(got["seam"], "high")

    def test_an_unreadable_agent_file_reads_unmeasured_never_a_guess(self):
        got = role_efforts(agents_dir="/nonexistent")
        self.assertEqual(set(got.values()), {"unmeasured"})

    def test_only_the_frontmatter_counts_never_the_brief_below_it(self):
        """A brief is long prose about how hard to work. If a file lost its
        frontmatter `effort:`, a sentence in the body starting with the same word
        would be stamped into the ledger as measured fact -- which is the guessed
        stamp this whole header exists to prevent."""
        directory = tempfile.mkdtemp()
        for role, agent_type in ROLES.items():
            with open(os.path.join(directory, agent_type + ".md"), "w",
                      encoding="utf-8") as handle:
                handle.write("---\nname: x\nmodel: inherit\n---\n\n"
                             "effort: max\n\nBody prose.\n")
        got = role_efforts(agents_dir=directory)
        self.assertEqual(set(got.values()), {"unmeasured"})


class HeaderLines(unittest.TestCase):
    """Rulings 4 and 7: a concrete name per role in the ledger, effort beside it."""

    def setUp(self):
        self.resolved = resolve([("gates", "fable")], "opus")
        self.efforts = role_efforts()
        self.text = header_lines(self.resolved, self.efforts, "claude-opus-5", "gates=fable")

    def test_every_one_of_the_fourteen_roles_is_named(self):
        for role in ROLES:
            self.assertIn(role + "=", self.text)

    def test_the_word_inherit_never_reaches_the_ledger(self):
        self.assertNotIn("inherit", header_lines(
            resolve([], "opus"), self.efforts, "claude-opus-5", "all=inherit").split("(")[0])

    def test_it_records_what_was_typed_and_the_session_model_it_resolved_against(self):
        self.assertIn("claude-opus-5", self.text)
        self.assertIn("gates=fable", self.text)

    def test_the_header_stays_small_because_every_reader_stops_at_line_60(self):
        """`find_live_ledger.py` reads `HEAD_LINES = 60` and
        `scripts/lib/run-workspace.mjs` slices the same 60. A header that grows
        past that window makes `Worktree:` invisible and the seed refuses the
        ledger. Twelve roles as twelve rows would have spent a fifth of it."""
        self.assertLessEqual(len(self.text.splitlines()), 4)

    def test_the_effort_it_writes_is_the_agent_files_own(self):
        self.assertIn("finale=max", self.text)
        self.assertIn("promotion=medium", self.text)

    def test_a_ledger_reads_back_exactly_what_the_launch_wrote(self):
        """Sitting 2's hook and sitting 3's cost scripts read this line. A format
        only the writer understands is a map the hook cannot enforce."""
        ledger = "# Run ledger\n\nOwner: sess-a\n" + self.text + "\nWorktree: `/x`\n"
        self.assertEqual(ledger_map(ledger), self.resolved)

    def test_a_ledger_with_no_map_line_reads_as_nothing_not_as_a_guess(self):
        self.assertIsNone(ledger_map("# Run ledger\n\nOwner: sess-a\n"))

    def test_a_map_line_naming_fewer_than_fourteen_roles_is_a_fault_not_an_absence(self):
        """Sitting 2's hook owes two different answers here: no ledger map passes
        the spawn (ruling 9), and a fault inside the check passes it AND journals
        a line (ruling 16). One `None` for both cannot carry that, so a damaged
        line reads as an empty map and an absent one reads as None."""
        damaged = "Model map at launch: `implementer=opus verify=opus`\n"
        self.assertEqual(ledger_map(damaged), {})
        self.assertIsNone(ledger_map("Owner: sess-a\n"))

    def test_a_map_line_naming_a_model_the_agent_tool_cannot_reach_is_a_fault(self):
        full = " ".join(f"{role}=opus" for role in ROLES).replace(
            "promotion=opus", "promotion=deepseek")
        self.assertEqual(ledger_map(f"Model map at launch: `{full}`\n"), {})


class AMapWrittenBeforeARoleJoined(unittest.TestCase):
    """Widening `ROLES` makes every ledger written before the widening read as
    DAMAGED, and two readers want different answers about that.

    The GATE wants strict: it may only refuse against a map that names every
    role, so a twelve-role line has to read `{}`. The COST CELL wants whatever
    the ledger stated: run `batch-170a59` and run `batch-207704` both carry a
    twelve-role line, and `worker_cell({})` returns `not stated`, so re-taking
    either reading would overwrite a row that names seven roles today with a
    row that names none. Measured 2026-09-07 against both ledgers on disk.
    """

    def old_line(self):
        """A ledger as the launch wrote it before ticket 33 ruling 2."""
        twelve = [role for role in ROLES if role not in ("attacker", "seam")]
        return ("Model map at launch: `"
                + " ".join(f"{role}=opus" for role in twelve) + "`\n")

    def test_the_strict_reader_still_calls_it_damaged(self):
        self.assertEqual(ledger_map(self.old_line()), {})

    def test_the_lax_reader_returns_the_roles_the_ledger_did_name(self):
        found = _mm.ledger_map_partial(self.old_line())
        self.assertEqual(len(found), len(ROLES) - 2)
        self.assertNotIn("attacker", found)
        self.assertEqual(found["implementer"], "opus")

    def test_the_lax_reader_still_answers_nothing_for_no_map_line(self):
        """An absent map is not a partial one. `{}` here means the ledger
        stated nothing, which is what `not stated` is for."""
        self.assertEqual(_mm.ledger_map_partial("Owner: sess-a\n"), {})

    def test_the_lax_reader_drops_a_model_the_agent_tool_cannot_reach(self):
        """`deepseek` in a ledger is a typo or another API. Rendering it into
        the comparison table would put a tier nothing can group beside real
        ones."""
        line = self.old_line().replace("promotion=opus", "promotion=deepseek")
        self.assertNotIn("promotion", _mm.ledger_map_partial(line))

    def test_an_old_ledger_still_renders_a_worker_cell(self):
        """The regression this pair of readers exists to prevent."""
        found = _mm.ledger_map_partial(self.old_line())
        cell = worker_cell(found, {role: "high" for role in ROLES})
        self.assertNotEqual(cell, _mm.NOT_STATED)
        self.assertIn("workers=opus", cell)

    def test_a_half_named_group_is_never_rendered_as_the_whole_group(self):
        """`gates=opus` on a ledger that named six of the eight gates would
        state a tier for `attacker` and `seam` that the launch never recorded.
        The cell's own docstring promises it is not lossy, so a group is named
        only when every one of its roles is in the map."""
        found = _mm.ledger_map_partial(self.old_line())
        cell = worker_cell(found, {role: "high" for role in ROLES})
        self.assertNotIn("gates=", cell)
        self.assertIn("verify=opus", cell)
        self.assertNotIn("attacker", cell)

    def test_a_full_map_still_groups_exactly_as_it_did(self):
        resolved = resolve([("all", "opus")], "opus")
        cell = worker_cell(resolved, {role: "high" for role in ROLES})
        self.assertEqual(cell, "all=opus/high")


class ResolveLaunch(unittest.TestCase):
    """The launch line itself: one call from the command text to the header."""

    def test_a_launch_with_no_map_typed_uses_the_default_file(self):
        header, refusals = resolve_launch("512 513", "claude-opus-5")
        self.assertEqual(refusals, [])
        self.assertEqual(set(ledger_map(header).values()), {"opus"})

    def test_a_typed_map_beats_the_default_file(self):
        header, refusals = resolve_launch(
            "512 513 models: gates=fable", "claude-opus-5")
        self.assertEqual(refusals, [])
        self.assertEqual(ledger_map(header)["verify"], "fable")
        self.assertEqual(ledger_map(header)["implementer"], "opus")

    def test_an_inverted_map_is_refused_and_writes_no_header(self):
        header, refusals = resolve_launch(
            "512 models: implementer=opus gates=sonnet", "claude-opus-5")
        self.assertEqual(header, "")
        self.assertTrue(refusals)

    def test_the_refusal_states_the_rule_once_and_lists_every_pair(self):
        """Nine inverted pairs used to print the same 60-word rationale nine
        times. The human reads this text at the keyboard, and a wall of repetition
        buries the one thing they need: which pairs are wrong."""
        _, refusals = resolve_launch(
            "512 models: implementer=opus gates=sonnet", "claude-opus-5")
        whole = "\n".join(refusals)
        self.assertEqual(whole.count("no catcher until the merge"), 1)
        for gate in ("verify", "review", "review-critical", "claim-gate",
                     "fix-gate", "fix-gate-critical"):
            self.assertIn(gate + "=sonnet", whole)

    def test_a_bad_map_token_is_refused_and_never_silently_dropped(self):
        header, refusals = resolve_launch("512 models: reviewer=opus", "claude-opus-5")
        self.assertEqual(header, "")
        self.assertIn("reviewer=opus", " ".join(refusals))

    def test_the_models_word_typed_with_nothing_after_it_is_refused(self):
        header, refusals = resolve_launch("512 models:", "claude-opus-5")
        self.assertEqual(header, "")
        self.assertTrue(refusals)

    def test_a_hunt_line_takes_the_same_word_and_the_same_parser(self):
        header, refusals = resolve_launch(
            "src/lib/zoho models: finder=fable claim-gate=fable fixer=opus",
            "claude-opus-5")
        self.assertEqual(refusals, [])
        self.assertEqual(ledger_map(header)["finder"], "fable")
        self.assertEqual(ledger_map(header)["fixer"], "opus")

    def test_ruling_20s_own_example_is_refused_by_ruling_14(self):
        """Measured, not assumed. `models: finder=fable fixer=opus` is the hunt
        example ruling 20 prints. On any session below fable it leaves the claim
        gate under the finder, which ruling 14 refuses. The example is illegal as
        written; both rulings stand and this pins which one wins."""
        header, refusals = resolve_launch(
            "src/lib/zoho models: finder=fable fixer=opus", "claude-opus-5")
        self.assertEqual(header, "")
        self.assertIn("claim-gate", refusals[0])

    def test_an_unreadable_session_model_is_refused_not_guessed(self):
        header, refusals = resolve_launch("512", "unmeasured")
        self.assertEqual(header, "")
        self.assertTrue(refusals)


SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_map.py")


def cli(*args):
    return subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True)


class TheLaunchLine(unittest.TestCase):
    """What the runner actually types before spawn 1."""

    def test_it_prints_the_header_for_the_ledger_and_exits_0(self):
        done = cli("--session-model", "claude-opus-5", "512 513 models: gates=fable")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(ledger_map(done.stdout)["verify"], "fable")

    def test_it_refuses_an_inverted_map_on_stderr_and_exits_1(self):
        done = cli("--session-model", "claude-opus-5",
                   "512 models: implementer=opus gates=sonnet")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stdout.strip(), "")
        self.assertIn("REFUSED", done.stderr)

    def test_a_launch_with_no_map_typed_still_writes_a_full_header(self):
        done = cli("--session-model", "claude-opus-5", "512 513")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(set(ledger_map(done.stdout).values()), {"opus"})

    def test_an_unreadable_session_model_refuses_rather_than_stamping_a_guess(self):
        done = cli("--session-model", "", "512")
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED", done.stderr)


class TheLaunchHeaderCarriesThePipelineFingerprint(unittest.TestCase):
    """Ticket 37, ruling 23, additive to ticket 39's ruling 4 header.

    The three repositories this pipeline runs from sat at `5215fb5`, `24f37ef`
    and `19b097f` on 2026-09-05, and no ledger and no cost row named any of
    them. A row saying a run got faster could not say what the pipeline was
    when it ran."""

    def test_the_header_names_the_three_repositories(self):
        header, refusals = resolve_launch("512 513", "claude-opus-5")
        self.assertEqual([], refusals)
        for name in ("skills", "agents", "hooks"):
            self.assertIn(name, header)

    def test_the_model_map_lines_are_still_there(self):
        """Additive means additive: ticket 39's two lines are untouched, and
        `ledger_map` reads them out of the same header."""
        header, _ = resolve_launch("512 models: all=opus", "claude-opus-5")
        self.assertIn("Model map at launch:", header)
        self.assertIn("Role effort at launch:", header)
        self.assertEqual(len(ROLES), len(ledger_map(header) or {}))

    def test_the_fingerprint_is_readable_back_out_of_the_header(self):
        header, _ = resolve_launch("512 513", "claude-opus-5")
        self.assertTrue(pipeline_fingerprint.from_ledger(header))

    def test_a_refusal_still_writes_no_header(self):
        """Ruling 23 says a dirty tree runs and the mark is a fact. It must not
        become a way for a fingerprint reading to write a header that the model
        map refused."""
        header, refusals = resolve_launch("512 models: reviewer=opus",
                                          "claude-opus-5")
        self.assertTrue(refusals)
        self.assertEqual("", header)


class TheWorkerCellIsTheShortestFormOfTheMap(unittest.TestCase):
    """Ticket 37, ruling 9: the second model cell reads `all=opus/high` or
    `implementer=opus/high gates=fable/high`.

    Shortest form matters because the cell sits in a markdown table a person
    scans. The full twelve-role map is 220 characters and would push every
    column after it off the page; the ledger keeps the long form, and the
    per-role table in the merge briefing keeps the proof."""

    def test_one_model_everywhere_collapses_to_all(self):
        cell = worker_cell({role: "claude-opus-5" for role in ROLES},
                           {role: "high" for role in ROLES})
        self.assertEqual("all=opus/high", cell)

    def test_a_split_names_the_group_that_differs(self):
        models = {role: "claude-opus-5" for role in ROLES}
        efforts = {role: "high" for role in ROLES}
        for gate in GATES:
            models[gate] = "claude-fable-5"
        cell = worker_cell(models, efforts)
        self.assertIn("gates=fable/high", cell)
        self.assertNotIn("verify=", cell)

    def test_effort_travels_with_the_model(self):
        """The human confirmed it after round 3: model AND effort, for the
        orchestrator AND every subagent."""
        efforts = {role: "high" for role in ROLES}
        efforts["finale"] = "max"
        cell = worker_cell({role: "claude-opus-5" for role in ROLES}, efforts)
        self.assertIn("finale=opus/max", cell)

    def test_every_role_is_named_somewhere(self):
        """Shortest form may not be lossy. A role dropped from the cell is a
        role whose tier nobody can read off the table."""
        models = {role: "claude-opus-5" for role in ROLES}
        efforts = {role: "high" for role in ROLES}
        models["implementer"] = "claude-fable-5"
        efforts["promotion"] = "medium"
        cell = worker_cell(models, efforts)
        self.assertIn("implementer=fable/high", cell)
        self.assertIn("promotion=opus/medium", cell)

    def test_an_empty_map_says_so_rather_than_inventing_a_default(self):
        """Every run before ticket 39 sitting 1, and ruling 3 keeps them."""
        self.assertEqual("not stated", worker_cell({}, {}))


# Every dialect of the ledger's own model line, measured 2026-09-06 across all
# 22 files on this machine that carry one. Only three matched the reader before
# this test: `SESSION_MODEL` anchored on `\s*$`, so bold markers or any trailing
# word made the line invisible and ruling 9's first model cell read `not
# stated` on a ledger that plainly states the model.
#
# Sitting 4's warning holds -- widening a pattern with no dialect behind it is
# how a reader stops meaning anything -- so each row below is a real line from a
# real ledger, and the file it came from is named.
SESSION_LINES = (
    ("runs/batch-170a59/run.md",
     "Session model at launch: claude-opus-5", "claude-opus-5"),
    ("archive-run-batch-375cbf-merged.md",
     "Session model at launch: claude-opus-5", "claude-opus-5"),
    ("archive-run-batch-45c8b1.md",
     "Session model at launch: **claude-opus-5** (measured from the process "
     "command line, `--model`).", "claude-opus-5"),
    ("run-prev-run-batch-88624c.md",
     "Session model at launch: claude-opus-5   (read from "
     "`ps -o args= -p $CLAUDE_PID`)", "claude-opus-5"),
)

# The other dialect, and it is NOT widened into. Twelve of the 22 write the
# DISPLAY name and no id. `Opus 5/high` in the model cell would be a second
# spelling of one model, which is the eighth-dialect fault sitting 3 refused
# when it fixed the gate token to `pass` and `reject` alone.
DISPLAY_ONLY = (
    ("archive-run-b3f7a1-merged.md", "Session model at launch: **Opus 5**."),
    ("archive-run-402-251d11-merged.md",
     "Session model at launch: Opus 5 (`claude-opus-5`)"),
    ("run-prev-325b-snapshot.md",
     "Session model at launch was Opus 5."),
)


class TheOrchestratorCellReadsTheLedgersOwnModelLine(unittest.TestCase):
    """Ticket 37, ruling 9's FIRST model cell. It had no test at all until
    sitting 5, and it was wrong on 19 of the 22 ledgers on this machine.

    A session cannot read its own model out of its context, so the ledger's
    launch line is the only measured road there is. A reader that cannot read
    it writes `not stated` onto a line whose ledger states the model, and
    every model trial ticket 39 exists to run is read off that cell.
    """

    def test_every_measured_dialect_is_read(self):
        for source, line, expected in SESSION_LINES:
            with self.subTest(source=source):
                text = f"# Run ledger\n\n{line}\n"
                self.assertEqual(expected, orchestrator_cell(text))

    def test_the_effort_travels_with_it(self):
        text = ("Session model at launch: **claude-opus-5** (measured from "
                "the process command line, `--model`).\n"
                "Session effort at launch: **high** (measured from the "
                "process command line, `--effort`).\n")
        self.assertEqual("claude-opus-5/high", orchestrator_cell(text))

    def test_a_display_name_alone_is_refused_rather_than_spelled_twice(self):
        """`Opus 5` is not a model id. Writing it into the cell would give one
        model two spellings, and nothing downstream could group them."""
        for source, line in DISPLAY_ONLY:
            with self.subTest(source=source):
                self.assertEqual("not stated",
                                 orchestrator_cell(f"{line}\n"))

    def test_an_empty_model_line_does_not_read_the_line_below_it(self):
        """The `/code-review` pass of 2026-09-06, and the widening's own
        risk. `\\s*` matches a NEWLINE, so `Session model at launch:` with
        nothing after it captured the first word of the NEXT line. A ledger
        reading `Session model at launch:` above `claude-opus-5 was chosen
        later` reported `claude-opus-5/high` with confidence, for a run whose
        ledger stated nothing -- a measured figure invented from an adjacent
        line, which is the fault class this whole ticket exists to end."""
        text = ("Session model at launch:\n"
                "claude-opus-5 was chosen later\n"
                "Session effort at launch: high\n")
        self.assertEqual("not stated", orchestrator_cell(text))

    def test_an_empty_effort_line_does_not_read_the_line_below_it(self):
        text = ("Session model at launch: claude-opus-5\n"
                "Session effort at launch:\n"
                "high\n")
        self.assertEqual("claude-opus-5", orchestrator_cell(text))

    def test_a_ledger_with_no_such_line_says_not_stated(self):
        self.assertEqual("not stated", orchestrator_cell("# Run ledger\n"))


CORPUS = pathlib.Path("/home/user/project/.scratch/example-feature")


class TheWholeLedgerCorpus(unittest.TestCase):
    """Measured against every ledger on this machine, never against one.

    Sitting 3 of this ticket shipped two false-negative readings that were
    correct on the runs they were built against, and sitting 4 of ticket 39 was
    blind to seven dialects after measuring one ledger. This class is the net.
    It is deliberately weak on which ledger reads what -- that is the reader's
    own arithmetic handed back to it -- and asserts the two properties a
    narrowed or a widened pattern breaks first: enough lines are read at all,
    and nothing but a `claude-` id ever reaches the cell.

    Skipped where the corpus is absent, because these files are in another
    repository and this suite must run without it.
    """

    def setUp(self):
        if not CORPUS.is_dir():
            self.skipTest(f"{CORPUS} is not on this machine")
        self.ledgers = sorted(
            list(CORPUS.glob("archive-run-*.md"))
            + list(CORPUS.glob("run-prev-*.md"))
            + list(CORPUS.glob("runs/*/run.md")))
        self.stating = [one for one in self.ledgers
                        if "Session model at launch" in one.read_text(
                            encoding="utf-8", errors="replace")]

    def test_the_corpus_is_big_enough_to_be_a_net(self):
        """Measured 2026-09-06: 21 files carry the line."""
        self.assertGreaterEqual(len(self.stating), 21)

    def test_every_ledger_carrying_a_model_id_is_read(self):
        """Measured 2026-09-06: 7 of the 21, and 3 before the widening. The
        seven are every ledger whose line carries a `claude-` id at all."""
        read = [one for one in self.stating
                if orchestrator_cell(one.read_text(
                    encoding="utf-8", errors="replace")) != "not stated"]
        self.assertGreaterEqual(len(read), 7,
                                f"read: {[one.name for one in read]}")

    def test_no_cell_in_the_corpus_holds_anything_but_a_model_id(self):
        """The widening's own risk, pinned. `Opus 5` reaching this cell would
        give one model two spellings across the record."""
        for one in self.stating:
            cell = orchestrator_cell(one.read_text(
                encoding="utf-8", errors="replace"))
            if cell == "not stated":
                continue
            with self.subTest(ledger=one.name):
                model, _, effort = cell.partition("/")
                self.assertRegex(model, r"^claude-")
                if effort:
                    self.assertIn(effort, EFFORTS)


class TheHooksLoadThisFileByPath(unittest.TestCase):
    """The hooks are a SEPARATE repository and load `model_map.py` by path,
    with the skills directory NOT on `sys.path`. A plain top-level import of a
    sibling therefore throws on every spawn on the machine.

    This is the fault ticket 37 sitting 1 already met and recorded: "a missing
    `check_origin.py` raised rather than passing, and hooks and skills are
    separate repositories that can sit at different commits, so that would have
    thrown on every write to a shard." The fingerprint is a LAUNCH-time
    reading; no hook needs it."""

    def _loaded_without_the_skills_dir(self):
        import importlib.util
        import os
        here = os.path.dirname(os.path.abspath(model_map_file))
        saved = [p for p in sys.path]
        sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != here]
        for name in ("pipeline_fingerprint",):
            sys.modules.pop(name, None)
        try:
            spec = importlib.util.spec_from_file_location("mm_probe", model_map_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules["mm_probe"] = module
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path[:] = saved
            sys.modules.pop("mm_probe", None)

    def test_the_module_imports_with_the_skills_directory_off_the_path(self):
        self.assertTrue(self._loaded_without_the_skills_dir().ROLES)

    def test_the_hook_road_still_reads_a_map(self):
        module = self._loaded_without_the_skills_dir()
        line = "Model map at launch: `" + " ".join(
            f"{role}=opus" for role in module.ROLES) + "`"
        self.assertEqual(len(ROLES), len(module.ledger_map(line)))

    def test_a_launch_with_no_fingerprint_module_still_writes_a_header(self):
        """Fail open. Ruling 23 says a dirty tree still runs and the mark is a
        fact, never a refusal; a MISSING reading is weaker evidence than a
        dirty one and must stop even less."""
        module = self._loaded_without_the_skills_dir()
        header, refusals = module.resolve_launch("512 513", "claude-opus-5")
        self.assertEqual([], refusals)
        self.assertIn("Model map at launch:", header)


if __name__ == "__main__":
    unittest.main()
