#!/usr/bin/env python3
"""Drill for charge_round.py: what a gate round charges, read from the grades.

Tracker-tooling issue 14, fix F11 of the audit of 2026-09-23. The runner chose
between two rules for one event by hand. Issue 146 round 3 became a correction
round although both gates rejected; issue 53 round 2 had the same shape and took
a strike "because both gates rejected". These cases pin one answer for each
shape, so the choice no longer depends on who reads the verdicts.

    python3 test_charge_round.py
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import pathlib
import tempfile
import unittest

import charge_round


ISSUE = """Status: open

# 146 — storage budget unset throws

## Acceptance criteria

1. **The meter is reached only on a road that stored an object.**
2. **With the variable deleted, a road that stored nothing answers 200.**
3. **A guard refuses a call it cannot place.**

## Must still be true

- **M1 — `storageBudgetBytes` keeps throwing.**
- **M2 — admin's home keeps answering 500.**

## Verify gate

- **M7 — a label the gate wrote itself.**
"""


def issue() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="chargeround-"))
    path = root / "146-a.md"
    path.write_text(ISSUE, encoding="utf-8")
    return path


def run(verify, review, *extra):
    out, err = io.StringIO(), io.StringIO()
    argv = ["--issue", str(issue()), "--round", "3",
            "--verify", verify, "--review", review, *extra]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = charge_round.main(argv)
    return code, out.getvalue(), err.getvalue()


ALL_PASS = "Grades: C1=pass C2=pass C3=pass M1=pass M2=pass"


class WhatARoundCharges(unittest.TestCase):

    def test_both_gates_passing_charges_nothing(self):
        code, out, _ = run(ALL_PASS, ALL_PASS)
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=pass review=pass charge=none", out)

    def test_a_fail_both_gates_agree_on_is_a_strike(self):
        fail = "Grades: C1=pass C2=fail C3=pass"
        code, out, _ = run(fail, fail)
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=reject review=reject charge=strike", out)
        self.assertIn("C2", out)

    def test_a_fail_the_other_gate_never_graded_is_a_strike(self):
        code, out, _ = run("Grades: C1=pass C2=fail", "Grades: C1=pass M1=pass")
        self.assertEqual(code, 0)
        self.assertIn("charge=strike", out)

    def test_owed_work_at_both_gates_is_a_correction_and_no_strike(self):
        """Issue 146 round 3 and issue 53 round 2: both gates reject, both grade
        the behaviour correct, and only the standing guard is short. One shape,
        one answer, whatever the count of rejecting gates."""
        owed = "Grades: C1=pass C2=pass C3=owed M1=pass"
        code, out, _ = run(owed, owed)
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=reject review=reject charge=correction",
                      out)
        self.assertIn("C3", out)

    def test_owed_work_at_one_gate_is_a_correction(self):
        code, out, _ = run(ALL_PASS, "Grades: C1=pass C3=owed")
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=pass review=reject charge=correction",
                      out)

    def test_a_faulty_criterion_charges_nothing_and_sends_it_to_the_recheck(self):
        code, out, _ = run("Grades: C1=pass C2=fault", "Grades: C2=fail")
        self.assertEqual(code, 0)
        self.assertIn("charge=none", out)
        self.assertIn("criteria re-check", out)


class TheFactualSplit(unittest.TestCase):
    """One gate observed wrong behaviour on an item the other graded right.
    `SKILL.md` settles that by driving it, never by reading the code, and never
    by taking the stricter verdict."""

    def test_a_fail_against_a_pass_is_not_decided(self):
        code, out, err = run("Grades: C1=pass C2=pass",
                             "Grades: C1=pass C2=fail")
        self.assertEqual(code, 2)
        self.assertNotIn("charge=", out)
        self.assertIn("C2", err)
        self.assertIn("--driven C2=", err)

    def test_a_fail_against_owed_is_not_decided_either(self):
        """One gate says the behaviour is wrong, the other says it is right and
        its proof is short. That is a disagreement about behaviour."""
        code, _, err = run("Grades: C3=owed", "Grades: C3=fail")
        self.assertEqual(code, 2)
        self.assertIn("C3", err)

    def test_a_drive_that_reproduces_the_fail_is_a_strike(self):
        code, out, _ = run("Grades: C1=pass C2=pass", "Grades: C1=pass C2=fail",
                           "--driven", "C2=fail")
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=pass review=reject charge=strike", out)

    def test_a_drive_that_clears_the_fail_charges_nothing(self):
        """The token still records what the gates answered."""
        code, out, _ = run("Grades: C1=pass C2=pass", "Grades: C1=pass C2=fail",
                           "--driven", "C2=pass")
        self.assertEqual(code, 0)
        self.assertIn("gates 3: verify=pass review=reject charge=none", out)

    def test_a_cleared_fail_beside_owed_work_is_a_correction(self):
        code, out, _ = run("Grades: C3=owed", "Grades: C3=fail",
                           "--driven", "C3=pass")
        self.assertEqual(code, 0)
        self.assertIn("charge=correction", out)


class WhatItReads(unittest.TestCase):
    """Found by the review of 2026-09-23."""

    def test_the_parts_of_one_criterion_are_graded_apart(self):
        """One tracker's issue 92 has a criterion 3c. `C3a` and `C3c` are two
        items, never one item graded twice."""
        code, out, err = run("Grades: C1=pass C3a=pass C3c=owed",
                             "Grades: C1=pass C3a=pass C3c=owed")
        self.assertEqual(code, 0, err)
        self.assertIn("charge=correction", out)
        self.assertIn("C3c", out)

    def test_a_line_copied_with_its_backticks_is_read(self):
        """The gate briefs print the line in backticks, and a gate copies it."""
        code, out, err = run("`Grades: C1=pass C2=pass`",
                             "**Grades:** C1=pass C2=pass")
        self.assertEqual(code, 0, err)
        self.assertIn("charge=none", out)


class WhatItRefuses(unittest.TestCase):

    def test_a_name_the_issue_does_not_hold_is_refused(self):
        """`M7` sits in a gate's section, below the issue's own text."""
        code, out, err = run(ALL_PASS, "Grades: C1=pass M7=fail")
        self.assertEqual(code, 1)
        self.assertIn("M7", err)
        self.assertIn("register row", err)

    def test_a_criterion_past_the_last_is_refused(self):
        code, _, err = run("Grades: C4=fail", ALL_PASS)
        self.assertEqual(code, 1)
        self.assertIn("C4", err)

    def test_a_grade_word_outside_the_four_is_refused(self):
        code, _, err = run("Grades: C1=pass C2=reject", ALL_PASS)
        self.assertEqual(code, 1)
        self.assertIn("C2=reject", err)

    def test_a_gate_that_gave_no_grades_is_refused(self):
        code, _, err = run("", ALL_PASS)
        self.assertEqual(code, 1)
        self.assertIn("verify", err)

    def test_one_name_graded_twice_two_ways_is_refused(self):
        code, _, err = run("Grades: C1=pass C1=fail", ALL_PASS)
        self.assertEqual(code, 1)
        self.assertIn("C1", err)

    def test_a_drive_of_a_name_the_issue_does_not_hold_is_refused(self):
        code, _, err = run(ALL_PASS, ALL_PASS, "--driven", "C9=pass")
        self.assertEqual(code, 1)
        self.assertIn("C9", err)


CHECKLIST = """Status: ready-for-agent

# 33b — the launch document

## Acceptance criteria

- [ ] **The document holds every deploy step.** Fixture: the file.
      check: a gate reads it.
- [ ] **The first-user script refuses an origin without a scheme.**

## Must still be true

- **M1 — the pending-actions file keeps its order.**
"""


class TheChecklistForm(unittest.TestCase):
    """Tracker-tooling issue 26, ruling `q-fin-46e4de-06` of 2026-09-24.

    Run `batch-46e4de` launched 33b with `- [ ]` criteria. The reader found no
    names, every grade was refused, and an implementation fail was spent as a
    criteria reset. The cap blocked 33b one attempt early.
    """

    def test_a_fail_on_a_checklist_criterion_is_a_strike(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="chargeround-"))
        path = root / "33b-a.md"
        path.write_text(CHECKLIST, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = charge_round.main([
                "--issue", str(path), "--round", "1",
                "--verify", "Grades: C1=pass C2=fail M1=pass",
                "--review", "Grades: C1=pass C2=fail"])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn("charge=strike", out.getvalue())


class TheLightRound(unittest.TestCase):
    """Tracker-tooling issue 40, default `q-h0925-40-2`, and its seam case from
    issue 38: a `Level: light` round has the review gate alone, so it is
    charged on `--review` alone and its token names that gate only."""

    def light(self, level="Level: light"):
        root = pathlib.Path(tempfile.mkdtemp(prefix="chargeround-light-"))
        path = root / "146-a.md"
        path.write_text(level + "\n" + ISSUE, encoding="utf-8")
        return path

    def charge(self, path, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = charge_round.main(["--issue", str(path), "--round", "2",
                                      *argv])
        return code, out.getvalue(), err.getvalue()

    def test_a_light_round_is_charged_on_the_review_alone(self):
        for review, token in (
                ("Grades: C1=pass C2=fail", "gates 2: review=reject charge=strike"),
                ("Grades: C1=pass C2=owed", "gates 2: review=reject charge=correction"),
                ("Grades: C1=pass C2=pass", "gates 2: review=pass charge=none")):
            with self.subTest(review=review):
                code, out, err = self.charge(self.light(), "--review", review)
                self.assertEqual(code, 0, err)
                self.assertEqual(out.splitlines()[0], token)

    def test_a_full_round_without_the_verify_grades_is_refused(self):
        for level in ("Level: full", ""):
            with self.subTest(level=level):
                code, out, err = self.charge(self.light(level), "--review",
                                             "Grades: C1=pass")
                self.assertEqual((code, out), (1, ""))
                self.assertIn("--verify", err)

    def test_a_fault_on_a_light_round_strikes_or_carves_and_spawns_no_attacker(self):
        """Ruled 2026-10-07: on one issue of one run this road printed
        `blocked (criteria)`, retired on 2026-10-06, and the runner routed it
        by hand. The live road
        strikes or carves the faulty part, resets the criteria and carries on."""
        code, out, err = self.charge(self.light(), "--review",
                                     "Grades: C1=pass C2=fault")
        self.assertEqual(code, 0, err)
        token, road = out.splitlines()[:2]
        self.assertEqual(token, "gates 2: review=reject charge=none")
        self.assertNotIn("blocked", road)
        self.assertIn("~~", road)
        self.assertIn("`carve after gates 2: C2`", road)
        self.assertIn("reset", road)
        self.assertNotIn("step 8", road)

    def test_a_light_rounds_review_grades_are_still_held_to_the_issue(self):
        code, _, err = self.charge(self.light(), "--review", "Grades: C9=fail")
        self.assertEqual(code, 1)
        self.assertIn("C9", err)


# Issue 232 of run `batch-04dff9`: its invariants are unlabelled bullets, as in
# 154 of the 255 issues of one tracker, measured on 2026-09-28. Both gates
# numbered them by position, M1 to M14, and every name was refused. The runner
# re-ran on C1-C9 alone, and the review gate's M8=fail was never charged.
UNLABELLED = """Status: open

# 232 — config lists use six row shapes

## Acceptance criteria

1. **Every list draws one row shape.**
2. **The sheet saves once.**

## Must still be true

- **Every model write still happens.**
- **A coded row still never retires.**
  - a nested bullet is part of the one above, never an invariant
- **Users keeps its page cap and its order.**

Added by the seam pass of `h0925b`. Each item names the sibling issue.

- **The user sheet's one Save lands whole or not at all.**

## The test that fails today

- **Not an invariant: this bullet sits under another heading.**
"""

# Issue 227d of run `batch-e35a25`: numbered invariants under sub-headings. The
# gate wrote `M10` for invariant 10 and `M16c` for a part of invariant 16.
NUMBERED = """Status: open

# 227d — job and line pages read as forms

## Acceptance criteria

18. **The job page reads as a form.**
32. **Drive once.**

## Must still be true

### The job and line pages
10. The Money card still offers every control.
11. The line page keeps its tabs.

### The sheet
16. The sheet keeps its focus trap.
"""


def charge_on(body, verify, review):
    root = pathlib.Path(tempfile.mkdtemp(prefix="chargeround-labels-"))
    path = root / "issue.md"
    path.write_text(body, encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = charge_round.main(["--issue", str(path), "--round", "1",
                                  "--verify", verify, "--review", review])
    return code, out.getvalue(), err.getvalue()


class TheGatesOwnInvariantLabels(unittest.TestCase):
    """An invariant is named by its place under `## Must still be true`, as
    `I<n>`, and as `M<n>` too where the issue writes no `M` label of its own."""

    def test_unlabelled_bullets_are_named_by_their_place(self):
        held = charge_round.criteria_ids.known_ids(UNLABELLED)
        self.assertEqual(held, {"C1", "C2", "I1", "I2", "I3", "I4",
                                "M1", "M2", "M3", "M4"})

    def test_the_232_shape_charges_the_fail_the_gate_graded(self):
        verify = "Grades: C1=pass C2=pass M1=pass M2=fail M3=pass M4=pass"
        review = "Grades: C1=pass C2=pass M1=pass M2=fail M3=owed M4=pass"
        code, out, err = charge_on(UNLABELLED, verify, review)
        self.assertEqual(code, 0, err)
        self.assertIn("charge=strike", out)
        self.assertIn("I2", out)

    def test_the_227d_shape_reads_m10_as_invariant_10(self):
        verify = "Grades: C18=pass C32=pass I10=pass I11=pass I16=pass"
        review = "Grades: C18=pass C32=pass M10=fail M11=pass M16c=pass"
        code, out, err = charge_on(NUMBERED, verify, review)
        self.assertEqual(code, 2, err)       # a split: I10 pass against M10 fail
        self.assertIn("--driven I10=", err)

    def test_one_invariant_under_two_names_graded_alike_is_one_item(self):
        verify = "Grades: C18=pass C32=pass I10=fail"
        review = "Grades: C18=pass C32=pass M10=fail"
        code, out, err = charge_on(NUMBERED, verify, review)
        self.assertEqual(code, 0, err)
        self.assertIn("charge=strike", out)

    def test_a_place_past_the_last_bullet_is_still_refused(self):
        code, _, err = charge_on(UNLABELLED, "Grades: C1=pass M5=fail",
                                 "Grades: C1=pass")
        self.assertEqual(code, 1)
        self.assertIn("M5", err)

    def test_a_label_the_gate_invented_is_still_refused(self):
        """The 232 review gate also wrote S1-S4 for the seam pass's items. No
        issue labels an item `S`, so the name cannot be placed."""
        code, _, err = charge_on(UNLABELLED, "Grades: C1=pass S1=owed",
                                 "Grades: C1=pass")
        self.assertEqual(code, 1)
        self.assertIn("S1", err)

    def test_an_issue_with_its_own_m_labels_keeps_them_apart(self):
        """ISSUE labels M1 and M2. Its bullets are not renamed by place, so a
        gate's `M3` still names nothing."""
        code, _, err = run("Grades: C1=pass M3=fail", ALL_PASS)
        self.assertEqual(code, 1)
        self.assertIn("M3", err)


SCREEN_ISSUE = """Status: open
Claims: OPS-S07, OPS-S08

# 366 — new request files

## Acceptance criteria

1. **The waiting files show on the job page.**
2. **For each of OPS-S07 and OPS-S08, the pair for the row exists under the fidelity folder, and every difference names a ruling.**
3. **Home shows the File coming chip.**
"""


class ScreenGrounds(unittest.TestCase):
    """The human, 2026-10-05: a screen difference never blocks an issue. A strike
    whose every failed item is a screen criterion (one naming a row the issue's
    `Claims:` line claims) says so, so the attempt cap can land it short."""

    def charge(self, review, body=SCREEN_ISSUE):
        """Both gates grade alike, so no split is left to drive."""
        return charge_round.decide(body, 2, review, review)

    def test_a_strike_on_screen_criteria_alone_says_grounds_screen(self):
        code, out, _ = self.charge("Grades: C1=pass C2=fail C3=pass")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "gates 2: verify=reject "
                         "review=reject charge=strike grounds=screen")
        self.assertIn("lands short", out)

    def test_a_strike_with_any_other_criterion_says_nothing_more(self):
        code, out, _ = self.charge("Grades: C1=pass C2=fail C3=fail")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0],
                         "gates 2: verify=reject review=reject charge=strike")

    def test_an_issue_that_claims_no_row_has_no_screen_criterion(self):
        body = SCREEN_ISSUE.replace("Claims: OPS-S07, OPS-S08\n", "")
        _, out, _ = self.charge("Grades: C1=pass C2=fail C3=pass", body)
        self.assertNotIn("grounds=screen", out)

    def test_a_claims_line_below_the_title_claims_nothing(self):
        body = SCREEN_ISSUE.replace("Claims: OPS-S07, OPS-S08\n", "").replace(
            "## Acceptance", "Claims: OPS-S07, OPS-S08\n\n## Acceptance")
        _, out, _ = self.charge("Grades: C1=pass C2=fail C3=pass", body)
        self.assertNotIn("grounds=screen", out)

    def test_a_correction_round_carries_no_grounds(self):
        _, out, _ = self.charge("Grades: C1=pass C2=owed C3=pass")
        self.assertNotIn("grounds=", out)


SKILL = pathlib.Path(charge_round.__file__).with_name("SKILL.md")
SPAN = re.compile(r"`([^`\n]+)`")


def ledger_statuses(skill: str) -> tuple[set[str], set[str]]:
    """(live, retired) from the one place the statuses are written: the
    `Ledger statuses:` sentence of `run-issues/SKILL.md`. A status after
    "in ledgers older than" is retired."""
    start = skill.index("Ledger statuses:")
    sentence = skill[start:skill.index("Both gates run", start)]
    live, _, retired = sentence.partition("in ledgers older than")
    spans = lambda text: {one.strip() for span in SPAN.findall(text)
                          for one in span.split("→")}
    return spans(live), spans(retired)


def printed_statuses(source: str, words: set[str]) -> list[str]:
    """Every backticked span in a string the script can print whose first word
    is a ledger status word and holds nothing but that word and a bracket, so
    the round token `gates N:` is not a status. Docstrings are not read."""
    tree = ast.parse(source)
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef,
                                       ast.AsyncFunctionDef))
                  and node.body and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    docstrings |= {id(part) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr)
                   for part in node.values}  # read once, inside their f-string
    texts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            texts.append("".join(part.value if isinstance(part, ast.Constant) else "{}"
                                 for part in node.values))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
              and id(node) not in docstrings):
            texts.append(node.value)
    form = re.compile(r"(?P<word>[\w-]+)(?:\s*\([^)]*\))?")
    found = []
    for text in texts:
        for span in SPAN.findall(text):
            shape = form.fullmatch(span.strip())
            if shape and shape.group("word").lower() in words:
                found.append(span.strip())
    return found


class EveryPrintedStatusIsLive(unittest.TestCase):
    """Ruled 2026-10-07: a test fails when the script prints a status outside
    the live list. A ruling retired the `blocked` statuses on 2026-10-06, and
    this script went on printing `blocked (criteria)` until one run met it."""

    def setUp(self):
        self.live, self.retired = ledger_statuses(SKILL.read_text())
        self.words = {one.split()[0] for one in self.live | self.retired}

    def test_the_live_and_retired_lists_are_read(self):
        self.assertIn("done (carved)", self.live)
        self.assertIn("in-progress", self.live)
        self.assertEqual(self.retired, {"blocked", "blocked (criteria)",
                                        "blocked (depends on NN)",
                                        "blocked (light: two attempts spent)"})

    def test_a_retired_status_in_a_printed_string_is_found(self):
        for retired in sorted(self.retired):
            with self.subTest(status=retired):
                source = f'road = "ledger it `{retired}` and go on."\n'
                self.assertEqual(printed_statuses(source, self.words), [retired])

    def test_a_status_built_in_an_f_string_is_found(self):
        source = 'n = 4\nroad = f"ledger it `blocked (depends on {n})`"\n'
        self.assertEqual(printed_statuses(source, self.words), ["blocked (depends on {})"])

    def test_a_live_status_passes_and_a_docstring_is_not_read(self):
        source = '"""`blocked` once."""\nroad = "ledger `done (carved)`."\n'
        self.assertEqual(printed_statuses(source, self.words), ["done (carved)"])

    def test_charge_round_prints_no_status_outside_the_live_list(self):
        source = pathlib.Path(charge_round.__file__).read_text()
        printed = printed_statuses(source, self.words)
        self.assertEqual([one for one in printed if one not in self.live], [])


if __name__ == "__main__":
    unittest.main()
