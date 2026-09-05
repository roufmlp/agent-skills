"""Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 1: the map, the default file and the launch line."""

import os
import subprocess
import sys
import tempfile
import unittest

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


class TheTwelveRoles(unittest.TestCase):
    """Ruling 5's grammar names one key per agent type without its prefix, and
    ruling 6 scopes this ticket to the twelve loop roles."""

    def test_the_keys_are_ruling_5s_twelve(self):
        self.assertEqual(sorted(ROLES), sorted([
            "implementer", "escalated", "verify", "review", "review-critical",
            "finale", "finder", "fixer", "claim-gate", "fix-gate",
            "fix-gate-critical", "promotion"]))

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

    def test_it_reads_the_twelve_agent_files_as_they_stand_today(self):
        got = role_efforts()
        self.assertEqual(set(got), set(ROLES))
        self.assertEqual(got["finale"], "max")
        self.assertEqual(got["finder"], "xhigh")
        self.assertEqual(got["promotion"], "medium")
        self.assertEqual(got["implementer"], "high")

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

    def test_every_one_of_the_twelve_roles_is_named(self):
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

    def test_a_map_line_naming_fewer_than_twelve_roles_is_a_fault_not_an_absence(self):
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


if __name__ == "__main__":
    unittest.main()
