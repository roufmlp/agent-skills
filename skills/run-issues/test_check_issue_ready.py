#!/usr/bin/env python3
"""Tests for check_issue_ready.py. Run: python3 test_check_issue_ready.py

The run this guard exists for is `bridge-cse`, 2026-08-24. Its ledger and journal
are on main. The cases below quote it rather than inventing shapes.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

import check_issue_ready as guard


def write(directory: pathlib.Path, name: str, body: str) -> pathlib.Path:
    path = directory / name
    path.write_text(body)
    return path


class ReadsTheIssueId(unittest.TestCase):
    def test_a_plain_number(self):
        self.assertEqual(guard.issue_id("408-the-create-form-tells-the-operator.md"), "408")

    def test_a_lettered_slice(self):
        """A live tracker mints these constantly: 402b, 146b, 224c."""
        self.assertEqual(guard.issue_id("402b-correct-the-match.md"), "402b")

    def test_a_two_digit_legacy_id(self):
        self.assertEqual(guard.issue_id("07-email-oauth-channel.md"), "07")

    def test_a_name_with_no_leading_id_is_its_own_id(self):
        """Never guess. A file nobody can identify is reported under its own name."""
        self.assertEqual(guard.issue_id("primer.md"), "primer.md")


class GradesTheCriteriaSection(unittest.TestCase):
    def test_graded_criteria_pass(self):
        """Issue 409's shape: a `## Acceptance criteria` section."""
        verdict, _ = guard.grade("# Issue\n\n## Acceptance criteria\n\n1. A thing.\n")
        self.assertEqual(verdict, guard.GRADED)

    def test_invariants_alone_are_allowed_and_named(self):
        """Issue 338's shape. The journal calls it the closest thing to criteria
        in that batch, and it still cost two attempts. Allowed, never silent."""
        verdict, _ = guard.grade("# Issue\n\n## Must still be true\n\n- A thing.\n")
        self.assertEqual(verdict, guard.INVARIANTS_ONLY)

    def test_neither_section_is_refused(self):
        """Issues 408 and 407: promoted register rows with a fault and a remedy
        direction, and no criteria at all."""
        verdict, _ = guard.grade("# Issue\n\n## What is wrong\n\n## Remedy direction\n")
        self.assertEqual(verdict, guard.NO_CRITERIA)

    def test_the_heading_must_be_a_heading(self):
        """A sentence mentioning acceptance criteria is not a section of them."""
        verdict, _ = guard.grade("# Issue\n\nThis file has no acceptance criteria yet.\n")
        self.assertEqual(verdict, guard.NO_CRITERIA)

    def test_a_deeper_heading_still_counts(self):
        """`### Acceptance criteria` under a parent section is the same section."""
        verdict, _ = guard.grade("# Issue\n\n### Acceptance criteria\n\n1. A thing.\n")
        self.assertEqual(verdict, guard.GRADED)


class JudgesABatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_ready_batch_passes(self):
        write(self.dir, "409-a.md", "## Acceptance criteria\n1. A thing.\n")
        write(self.dir, "338-b.md", "## Must still be true\n- A thing.\n")
        allowed, rows = guard.judge([self.dir / "409-a.md", self.dir / "338-b.md"], set())
        self.assertTrue(allowed)
        self.assertEqual([row.verdict for row in rows], [guard.GRADED, guard.INVARIANTS_ONLY])

    def test_one_bad_file_refuses_the_batch(self):
        write(self.dir, "409-a.md", "## Acceptance criteria\n1. A thing.\n")
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, rows = guard.judge([self.dir / "409-a.md", self.dir / "408-b.md"], set())
        self.assertFalse(allowed)
        self.assertEqual(rows[1].verdict, guard.NO_CRITERIA)

    def test_an_override_lets_one_issue_through_and_stays_named(self):
        """The human's rule: the override is per issue and it prints what it costs.
        A batch-wide `--override` with no id would defeat the whole guard."""
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, rows = guard.judge([self.dir / "408-b.md"], {"408"})
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.NO_CRITERIA)
        self.assertTrue(rows[0].overridden)

    def test_an_override_for_an_issue_not_in_the_batch_does_not_pass_it(self):
        write(self.dir, "408-b.md", "## What is wrong\n")
        allowed, _ = guard.judge([self.dir / "408-b.md"], {"407"})
        self.assertFalse(allowed)

    def test_an_unreadable_file_is_refused_not_assumed(self):
        allowed, rows = guard.judge([self.dir / "no-such-issue.md"], set())
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.UNREADABLE)

    def test_an_unreadable_file_cannot_be_overridden(self):
        """An override says "I know this issue has no criteria". It cannot say
        anything about a file nobody could read."""
        allowed, rows = guard.judge([self.dir / "412-gone.md"], {"412"})
        self.assertFalse(allowed)
        self.assertFalse(rows[0].overridden)


class TheCostLineIsMeasured(unittest.TestCase):
    def test_the_cost_names_the_run_that_earned_it(self):
        """A rule outlives its incident, and a later editor who meets the rule
        with no measurement deletes it as ceremony."""
        self.assertIn("bridge-cse", guard.COST)
        self.assertIn("2026-08-24", guard.COST)

    def test_the_cost_names_the_damage_rather_than_a_feeling(self):
        self.assertIn("correction round", guard.COST)


GUARD = (
    "1. **No file under `src/` names a colour from Tailwind's own palette.** A build\n"
    "   check reads the source tree and refuses a class it cannot place.\n"
)
FORMS = (
    "   Forms: `.ts`, `.tsx`, `.css` under `src/`\n"
    "   Measured by: `git ls-files src | sed -n 's/.*\\.//p' | sort -u`, 2026-09-24\n"
    "   Outside the list: a form a gate plants that this list does not hold is a register\n"
    "   row, not a rejection.\n"
)


def issue(criterion: str, stamp: str = "Hardened: 2026-09-24 — 3 sharpened.") -> str:
    return f"Status: ready-for-agent\n{stamp}\n\n# Issue\n\n## Acceptance criteria\n\n{criterion}"


class RefusesAnOpenGuard(unittest.TestCase):
    """Fix F7 of the audit of 2026-09-23, tracker-tooling issue 22. Issue 53 was
    rejected seven times, each time on a spelling a gate planted, because its
    guard criterion named no population a build could meet."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def judge(self, body: str, **options):
        write(self.dir, "53-a.md", body)
        return guard.judge([self.dir / "53-a.md"], set(), **options)

    def test_a_guard_with_no_forms_is_refused(self):
        allowed, rows = self.judge(issue(GUARD))
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.OPEN_GUARD)
        self.assertIn("criterion 1", rows[0].detail)

    def test_a_guard_carrying_all_three_lines_passes(self):
        allowed, rows = self.judge(issue(GUARD + FORMS))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_forms_with_no_command_are_refused(self):
        """A list nobody can re-measure is a guess, and it goes stale unseen.
        Issue 139's "twenty-two" families had no command; Tailwind ships 26."""
        body = FORMS.replace("Measured by: `git ls-files src | sed -n 's/.*\\.//p' | sort -u`", "Measured by: hand")
        allowed, rows = self.judge(issue(GUARD + body))
        self.assertFalse(allowed)
        self.assertIn("Measured by:", rows[0].detail)

    def test_forms_that_do_not_say_where_a_planted_form_goes_are_refused(self):
        """The gate reads this line. Without it a planted form is a rejection again."""
        body = FORMS.split("   Outside the list:")[0]
        allowed, rows = self.judge(issue(GUARD + body))
        self.assertFalse(allowed)
        self.assertIn("Outside the list:", rows[0].detail)

    def test_a_forms_line_is_graded_even_where_the_detector_is_silent(self):
        """A criterion that declares itself a guard is one, whatever its wording."""
        body = "1. **Every route answers a signed-out request with the login page.**\n" + FORMS.split("   Measured by:")[0]
        allowed, rows = self.judge(issue(body))
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.OPEN_GUARD)

    def test_forms_with_no_form_named_are_refused(self):
        body = FORMS.replace("Forms: `.ts`, `.tsx`, `.css` under `src/`", "Forms: whatever the tree holds")
        allowed, rows = self.judge(issue(GUARD + body))
        self.assertFalse(allowed)
        self.assertIn("backticked form", rows[0].detail)

    def test_a_scope_with_no_refusal_is_not_a_guard(self):
        """Issue 87's criterion 3 names `src/` to say the diff is tests only."""
        body = "1. **Nothing in `src/` changes.** `git diff --stat` names no file under `src/`.\n"
        allowed, rows = self.judge(issue(body))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_a_checklist_criterion_is_read(self):
        """Issue 166 of one project writes `- [ ] **Criterion 1, ground (a): ...**`.
        Read as numbered items only, its twelve criteria were invisible."""
        body = "- [ ] **Criterion 1: no file under `src/` holds a file's bytes.** The walk refuses what it cannot place.\n"
        allowed, rows = self.judge(issue(body))
        self.assertFalse(allowed)
        self.assertIn("criterion 1", rows[0].detail)

    def test_a_sub_heading_does_not_end_the_section(self):
        body = "### The case table\n\n| a | b |\n\n" + GUARD
        allowed, _ = self.judge(issue(body))
        self.assertFalse(allowed)

    def test_an_override_of_an_open_guard_prints_its_own_cost(self):
        write(self.dir, "53-a.md", issue(GUARD))
        _, rows = guard.judge([self.dir / "53-a.md"], {"53"})
        self.assertIn("seven", guard.cost_of(rows))
        self.assertNotIn("bridge-cse", guard.cost_of(rows))

    def test_a_wrong_flag_is_cleared_by_saying_why(self):
        """About half the flags measured on 2026-09-23 were not guards."""
        body = GUARD + "   Not a guard: it grades one fixture's answer, not a set of files.\n"
        allowed, rows = self.judge(issue(body))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_an_empty_reason_does_not_clear_a_flag(self):
        allowed, _ = self.judge(issue(GUARD + "   Not a guard:\n"))
        self.assertFalse(allowed)

    def test_a_criterion_that_is_not_a_guard_passes_silently(self):
        body = "1. **The note keeps what the operator typed.** Fixture: the late day. Answer: the text.\n"
        allowed, rows = self.judge(issue(body))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_only_the_criteria_section_is_read(self):
        """An invariant that mentions the tree is not a criterion."""
        body = issue("1. A thing.\n") + "\n## Must still be true\n\n1. No file under `src/` gains a guard.\n"
        allowed, rows = self.judge(body)
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_the_fault_names_the_right_criterion(self):
        body = "1. **The note keeps its text.**\n   2. an indented step, not a criterion\n" + GUARD.replace("1.", "2.", 1)
        _, rows = self.judge(issue(body))
        self.assertIn("criterion 2", rows[0].detail)
        self.assertNotIn("criterion 1", rows[0].detail)

    def test_a_stamp_before_the_rule_warns_and_passes(self):
        """Issues 53 and 166 were closed in their own words on 2026-09-23, and
        session S6 runs them. The refusal must not block that run."""
        allowed, rows = self.judge(issue(GUARD, "Hardened (provisional): 2026-09-23 — 13 sharpened."))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.OPEN_GUARD_BEFORE_RULE)

    def test_no_stamp_warns_and_passes(self):
        allowed, rows = self.judge(issue(GUARD, "Provenance: promoted"))
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.OPEN_GUARD_BEFORE_RULE)

    def test_a_provisional_stamp_on_the_rule_date_binds(self):
        allowed, _ = self.judge(issue(GUARD, "Hardened (provisional): 2026-09-24 — 2 defaults pending."))
        self.assertFalse(allowed)

    def test_all_guards_binds_an_old_stamp(self):
        """The hardening pass grades a file before it writes the new stamp."""
        allowed, rows = self.judge(issue(GUARD, "Hardened: 2026-09-01 — 1 sharpened."), all_guards=True)
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.OPEN_GUARD)

    def test_an_override_clears_an_open_guard(self):
        write(self.dir, "53-a.md", issue(GUARD))
        allowed, rows = guard.judge([self.dir / "53-a.md"], {"53"})
        self.assertTrue(allowed)
        self.assertTrue(rows[0].overridden)


class TheCommandLine(unittest.TestCase):
    """What the launch and the hardening pass actually run."""

    SCRIPT = pathlib.Path(__file__).with_name("check_issue_ready.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_it(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), "--issue", str(self.dir / "53-a.md"), *extra],
            capture_output=True, text=True,
        )

    def test_an_old_open_guard_is_printed_and_passes(self):
        write(self.dir, "53-a.md", issue(GUARD, "Hardened: 2026-09-20 — 1 sharpened."))
        done = self.run_it()
        self.assertEqual(done.returncode, 0)
        self.assertIn("GUARD?", done.stdout)
        self.assertIn("criterion 1", done.stdout)

    def test_all_guards_refuses_and_says_what_to_write(self):
        write(self.dir, "53-a.md", issue(GUARD, "Hardened: 2026-09-20 — 1 sharpened."))
        done = self.run_it("--all-guards")
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED   53", done.stderr)
        self.assertIn("Forms:", done.stderr)


class OneReaderNamesTheCriteria(unittest.TestCase):
    """Tracker-tooling issue 26, ruling `q-fin-46e4de-06` of 2026-09-24. This
    check had its own pattern and the charging tool another, so 33b passed
    launch while `charge_round.py` read its criteria as no names."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_a_section_the_reader_cannot_name_is_refused(self):
        write(self.dir, "200-a.md", "## Acceptance criteria\n\nIt must work, "
                                    "on every shape a gate can think of.\n")
        allowed, rows = guard.judge([self.dir / "200-a.md"], set())
        self.assertFalse(allowed)
        self.assertEqual(rows[0].verdict, guard.UNNAMED)

    def test_the_refusal_takes_the_per_issue_override(self):
        write(self.dir, "200-a.md", "## Acceptance criteria\n\nprose only\n")
        allowed, rows = guard.judge([self.dir / "200-a.md"], {"200"})
        self.assertTrue(allowed)
        self.assertTrue(rows[0].overridden)

    def test_the_checklist_form_passes(self):
        write(self.dir, "33b-a.md", "## Acceptance criteria\n\n- [ ] **One.**\n"
                                    "- [ ] **Two.**\n")
        allowed, rows = guard.judge([self.dir / "33b-a.md"], set())
        self.assertTrue(allowed)
        self.assertEqual(rows[0].verdict, guard.GRADED)

    def test_the_guard_check_reads_checklist_criteria_too(self):
        body = ("Hardened: 2026-09-24 — 1 sharpened.\n\n## Acceptance criteria\n\n"
                "- [ ] **One.** A guard refuses every file under `src/app/`.\n")
        self.assertEqual(len(guard.criteria(body)), 1)
        self.assertTrue(guard.guard_faults(body))


HEADER = "Touches: `run-issues/`\nKind: machinery. Every repo gets it.\nLevel: light\n"


def headed(lines: str = HEADER, stamp: str | None = None) -> str:
    """A graded issue stamped on the header rule date unless told otherwise.
    The stamp is built from the constant, never typed (`q-h0925-33-4`)."""
    if stamp is None:
        stamp = f"Hardened: {guard.HEADER_RULE_FROM} — 1 sharpened."
    return f"Status: ready-for-agent\n{stamp}\nSentence: A thing\n{lines}\n# Issue\n\n" \
           "## Acceptance criteria\n\n1. A thing.\n"


def day_before(date: str) -> str:
    import datetime
    return (datetime.date.fromisoformat(date) - datetime.timedelta(days=1)).isoformat()


class RefusesAnIssueWithoutItsHeaderLines(unittest.TestCase):
    """Tracker-tooling issue 33. Every issue names the files it touches, its
    kind and its level, so a script can place it by path."""

    SCRIPT = pathlib.Path(__file__).with_name("check_issue_ready.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_it(self, body: str, *extra):
        write(self.dir, "53-a.md", body)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), "--issue", str(self.dir / "53-a.md"), *extra],
            capture_output=True, text=True,
        )

    def refused_line(self, done) -> str:
        lines = [line for line in done.stderr.splitlines() if line.startswith("REFUSED   53")]
        self.assertEqual(len(lines), 1, done.stderr)
        return lines[0]

    def test_ac1_a_missing_touches_line_is_refused(self):
        done = self.run_it(headed(HEADER.replace("Touches: `run-issues/`\n", "")))
        self.assertEqual(done.returncode, 1)
        self.assertIn("Touches:", self.refused_line(done))

    def test_ac2_a_missing_kind_or_level_is_refused_and_named(self):
        for label, line in (("Kind:", "Kind: machinery. Every repo gets it.\n"),
                            ("Level:", "Level: light\n")):
            with self.subTest(label):
                done = self.run_it(headed(HEADER.replace(line, "")))
                self.assertEqual(done.returncode, 1)
                self.assertIn(label, self.refused_line(done))

    def test_ac2_a_file_missing_all_three_names_each_in_one_row(self):
        done = self.run_it(headed(""))
        self.assertEqual(done.returncode, 1)
        line = self.refused_line(done)
        for label in ("Touches:", "Kind:", "Level:"):
            self.assertIn(label, line)

    def test_ac3_a_value_outside_the_forms_is_refused_and_quoted(self):
        for bad in ("Level: medium", "Level: Light", "Kind: tool",
                    "Touches: the checker and its test", "Touches: none", "Touches: 588"):
            label = bad.split(":")[0] + ":"
            lines = [bad if line.startswith(label) else line for line in HEADER.splitlines()]
            with self.subTest(bad):
                done = self.run_it(headed("\n".join(lines) + "\n"))
                self.assertEqual(done.returncode, 1)
                self.assertIn(bad.split(": ", 1)[1], self.refused_line(done))

    def test_ac4_machinery_with_no_sentence_is_refused(self):
        for bad in ("Kind: machinery", "Kind: machinery."):
            with self.subTest(bad):
                done = self.run_it(headed(HEADER.replace("Kind: machinery. Every repo gets it.", bad)))
                self.assertEqual(done.returncode, 1)
                line = self.refused_line(done)
                self.assertIn("Kind:", line)
                self.assertIn("how the change helps every repo", line)

    def test_ac5_all_three_in_the_forms_pass(self):
        done = self.run_it(headed())
        self.assertEqual(done.returncode, 0, done.stderr)
        _, rows = guard.judge([self.dir / "53-a.md"], set())
        self.assertEqual(rows[0].verdict, guard.GRADED)
        for label in ("Touches:", "Kind:", "Level:"):
            self.assertNotIn(label, done.stdout + done.stderr)

    def test_ac7_a_stamp_before_the_rule_date_warns_and_passes(self):
        """Mutation driven 2026-09-26. The stamp is built from the constant, so
        moving `HEADER_RULE_FROM` to 2026-09-01 moves this fixture with it and
        reddens seven older cases stamped 2026-09-24 instead. Binding every stamp
        whatever its date turned this case red; restored, it went green."""
        old = f"Hardened: {day_before(guard.HEADER_RULE_FROM)} — 1 sharpened."
        done = self.run_it(headed("", stamp=old))
        self.assertEqual(done.returncode, 0, done.stderr)
        _, rows = guard.judge([self.dir / "53-a.md"], set())
        self.assertEqual(rows[0].verdict, guard.GRADED)
        warned = [line for line in done.stdout.splitlines() if line.startswith("HEADER?")]
        self.assertEqual(len(warned), 1, done.stdout)
        for label in ("Touches:", "Kind:", "Level:"):
            self.assertIn(label, warned[0])

    def test_ac8_kind_or_level_binds_a_file_with_no_stamp(self):
        done = self.run_it(headed("Kind: product\nLevel: light\n", stamp="Provenance: drafted"))
        self.assertEqual(done.returncode, 1)
        self.assertIn("Touches:", self.refused_line(done))

    def test_ac8_no_stamp_and_neither_line_warns(self):
        done = self.run_it(headed("", stamp="Provenance: drafted"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("HEADER?", done.stdout)

    def test_ac9_all_guards_binds_the_header_on_any_stamp(self):
        body = headed("", stamp="Hardened: 2026-09-01 — 1 sharpened.")
        self.assertEqual(self.run_it(body).returncode, 0)
        done = self.run_it(body, "--all-guards")
        self.assertEqual(done.returncode, 1)
        self.assertIn("Touches: `", done.stderr)
        self.assertIn("Level: light", done.stderr)

    def test_ac10_an_override_by_id_clears_a_header_refusal_for_that_issue(self):
        write(self.dir, "53-a.md", headed(HEADER.replace("Touches: `run-issues/`\n", "")))
        allowed, rows = guard.judge([self.dir / "53-a.md"], {"53"})
        self.assertTrue(allowed)
        self.assertTrue(rows[0].overridden)
        self.assertIn("not measured", guard.cost_of(rows))
        allowed, rows = guard.judge([self.dir / "53-a.md"], {"54"})
        self.assertFalse(allowed)

    def test_a_file_refused_for_both_prints_both(self):
        body = headed("").replace("## Acceptance criteria\n\n1. A thing.\n", "## What is wrong\n")
        done = self.run_it(body)
        self.assertEqual(done.returncode, 1)
        refused = [line for line in done.stderr.splitlines() if line.startswith("REFUSED   53")]
        self.assertEqual(len(refused), 2, done.stderr)


class OneReaderReadsTheHeaderLines(unittest.TestCase):
    """Default h0925 Q6 and the seam pass: issues 34, 35, 37, 39, 41 and 42
    import this reader rather than parse the lines again."""

    def test_a_strict_line_gives_its_tokens_in_order(self):
        found = guard.headers("Touches: `b/`, `a.py`, `src/**/*.ts`\nKind: product\nLevel: full\n")
        self.assertEqual(found.touches, ("b/", "a.py", "src/**/*.ts"))
        self.assertEqual(found.touches_form, guard.STRICT)
        self.assertEqual((found.kind, found.level), ("product", "full"))

    def test_issue_32s_wrapped_line_gives_five_tokens(self):
        text = ("Touches: `~/.claude/hooks/`, `~/.claude/skills/run-issues/`, `~/.claude/skills/to-issues/`,\n"
                "`~/.claude/skills/parallel-hunt/`, `~/.claude/agents/`\n"
                "Kind: machinery. Every item helps every repo that runs the chain.\n")
        found = guard.headers(text)
        self.assertEqual(len(found.touches), 5)
        self.assertEqual(found.touches[-1], "~/.claude/agents/")
        self.assertEqual(found.touches_form, guard.WRAPPED)

    def test_each_other_form_is_named(self):
        for line, form in (("Touches: a new script under `lib/`\n", guard.PROSE),
                           ("Touches: none\n", guard.NONE),
                           ("Touches: 588\n", guard.NO_TOKEN),
                           ("Title only\n", guard.NO_LINE)):
            with self.subTest(form):
                self.assertEqual(guard.headers(line).touches_form, form)

    def test_the_first_line_with_the_label_is_read(self):
        found = guard.headers("Level: light\n\n# Issue\n\nLevel: full\n")
        self.assertEqual(found.level, "light")

    def test_the_statuses_that_leave_the_pool(self):
        for status in ("done", "closed", "wontfix", "folded", "folded-into-41",
                       "superseded", "split", "resolved — by 40"):
            with self.subTest(status):
                self.assertTrue(guard.leaves_pool(status))
        for status in ("ready-for-agent", "needs-triage", ""):
            with self.subTest(status):
                self.assertFalse(guard.leaves_pool(status))


class ALightLineIsNotAHeaderLine(unittest.TestCase):
    """Issue 43. A `Level: light` issue skips hardening and carries a `Light:`
    line in place of the stamp. This check never read a stamp to pass a file,
    measured on 2026-09-25, so these are regression guards against issue 43b's
    rule 7 refusing a light file, and not the red test (that is in
    `lib/test_next_batch.py`)."""

    SCRIPT = pathlib.Path(__file__).with_name("check_issue_ready.py")
    LIGHT = f"Light: {guard.HEADER_RULE_FROM} — not hardened, rule 5 of issue 32."

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_it(self, body: str):
        write(self.dir, "43-a.md", body)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), "--issue", str(self.dir / "43-a.md")],
            capture_output=True, text=True,
        )

    def test_a_light_issue_with_a_light_line_and_no_stamp_passes(self):
        """AC1. The header lines are in issue 33's forms, because a file that
        carries `Level:` is held to them whatever its stamp."""
        body = headed(stamp=self.LIGHT)
        self.assertNotIn("Hardened", body)
        self.assertEqual(guard.judge([write(self.dir, "43-a.md", body)], set())[1][0].verdict,
                         guard.GRADED)
        done = self.run_it(body)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_light_line_on_a_full_issue_is_not_refused(self):
        """AC2, default `q-h0925b-43-2`: issue 42's lift leaves this pair on
        every lifted issue, so refusing it would hold that issue out of every
        later run. The scheduler names it instead."""
        body = headed(HEADER.replace("Level: light", "Level: full"), stamp=self.LIGHT)
        done = self.run_it(body)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)



class AFullIssueWithAPendingDefaultStaysOut(unittest.TestCase):
    """Issue 43b, rule 7 of issue 32 (ruling Q19 of 2026-09-25): a provisional
    stamp may enter a run, except a `Level: full` issue whose pending default
    changes a criterion. The mark is ``Default (`q-<pass>-<issue>-<n>`)``,
    written inside the criterion it changes (default `q-h0925b-43-1`)."""

    SCRIPT = pathlib.Path(__file__).with_name("check_issue_ready.py")
    FULL = HEADER.replace("Level: light", "Level: full")
    MARKED = "1. A thing. Default (`q-h9-43b-1`): the thing is built plain.\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def body(self, lines=None, stamp=None, criterion=None, opening=""):
        if stamp is None:
            stamp = f"Hardened (provisional): {guard.PENDING_RULE_FROM} — 1 default pending."
        text = headed(self.FULL if lines is None else lines, stamp=stamp)
        return text.replace("## Acceptance criteria\n\n1. A thing.\n",
                            "## Acceptance criteria\n\n" + opening
                            + (self.MARKED if criterion is None else criterion))

    def run_it(self, body, *extra):
        write(self.dir, "43b-a.md", body)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), "--issue", str(self.dir / "43b-a.md"), *extra],
            capture_output=True, text=True,
        )

    def test_a_full_provisional_issue_with_the_mark_is_refused(self):
        """AC1: non-zero exit naming the criterion."""
        done = self.run_it(self.body())
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("criterion 1", done.stderr)
        self.assertIn("q-h9-43b-1", done.stderr)

    def test_the_same_file_stamped_final_passes(self):
        stamp = f"Hardened: {guard.PENDING_RULE_FROM} — 1 sharpened."
        done = self.run_it(self.body(stamp=stamp))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_the_same_file_at_level_light_passes(self):
        """The light fixture that goes red when the refusal ignores `Level:`."""
        done = self.run_it(self.body(lines=HEADER))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_mark_only_in_the_opening_paragraph_passes(self):
        """Issue 33 opens its section by describing the mark; that is not one."""
        opening = "A mark ``Default (`q-h9-43b-1`)`` is a recommendation.\n\n"
        done = self.run_it(self.body(criterion="1. A thing.\n", opening=opening))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_criterion_quoting_the_placeholder_form_passes(self):
        """Issue 43b's own AC3 quotes the form inside a criterion. The
        placeholder is no question id, and no ruling could ever clear it."""
        criterion = "1. The form is ``Default (`q-<pass>-<issue>-<n>`)``.\\n"
        done = self.run_it(self.body(criterion=criterion))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_ruled_mark_does_not_refuse(self):
        """Default `q-h0925b-43-3`: an entry in the project's rulings file, read
        through `lib/rulings.py`, rules the mark."""
        scratch = self.dir / ".scratch"
        scratch.mkdir()
        (scratch / "rulings.md").write_text(
            "# Rulings\n\n## 2026-09-26 `q-h9-43b-1` — the thing is built plain\n\n"
            "Ruled: build it plain.\nCarried by: `43b-a.md`\n")
        done = self.run_it(self.body())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_all_guards_does_not_bind_it_on_an_unstamped_file(self):
        """Default `q-h0925b-43-4`: the harden pass can still stamp it."""
        body = self.body(stamp="Hardened: pending")
        body = body.replace("Hardened: pending\n", "")
        self.assertNotIn("Hardened", body)
        done = self.run_it(body, "--all-guards")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_stamp_before_the_rule_date_warns_and_passes(self):
        """AC2: exit 0, and one stdout line names the criterion and the rule date.
        The refusal binds stamps from the day issue 43b merged, never earlier, so
        pass h0925b's provisional stamps of 2026-09-25 warn."""
        self.assertGreaterEqual(guard.PENDING_RULE_FROM, "2026-09-27")
        stamp = f"Hardened (provisional): {day_before(guard.PENDING_RULE_FROM)} — 1 pending."
        done = self.run_it(self.body(stamp=stamp))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        warned = [line for line in done.stdout.splitlines()
                  if "criterion 1" in line and guard.PENDING_RULE_FROM in line]
        self.assertEqual(len(warned), 1, done.stdout)

    def test_an_override_clears_it_and_prints_the_cost(self):
        """Default `q-h0925b-43-5`: the per-issue override clears it, and the
        cost line says the cost is not measured."""
        path = write(self.dir, "43b-a.md", self.body())
        allowed, rows = guard.judge([path], {"43b"})
        self.assertTrue(allowed)
        self.assertTrue(rows[0].overridden)
        self.assertIn("not measured", guard.cost_of(rows))
        self.assertFalse(guard.judge([path], set())[0])


if __name__ == "__main__":
    unittest.main()
