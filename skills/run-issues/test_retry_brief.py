#!/usr/bin/env python3
"""Drill for retry_brief.py.

The one thing this file exists to pin: an owed item must quote the issue's OWN
text, and the gate's proposed remedy is not that text.

Run `batch-d67136`, issue 01, is the whole reason. The verify gate wrote the
invariant as an invariant, with its citation, at line 514 of the issue file --
`I-1 | The loader refuses any host but this machine. Implied by Target
database, "the loader refuses any other host" | FAIL` -- and forty lines later
proposed a remedy, "refuse a connection string whose search parameters contain
`host`". The retry brief carried the remedy and dropped the invariant, so the
implementer fixed exactly what it was told and round 2 rejected on the same
guard for a hostless string. The gate then wrote the SAME invariant, quoted
from the SAME line, and marked it FAIL a second time (line 1392). Round 3 cost
622k tokens and 36.7 minutes, and round 2's review gate had already passed.

    python3 test_retry_brief.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import tempfile
import unittest

import retry_brief as brief


ISSUE = """Status: open

# 01 — foundation and build checks

## Target database

| Database | Owner |
|---|---|
| the local one (`DATABASE_URL` in `.env.local`; the loader refuses any
other host) | the implementer |

## Acceptance criteria

1. The suite runs online against the local database.

## Must still be true

- The browser harness stays configured and drives no flow.
- **M1.** Every connection stays on this machine: the loader refuses any other
  host, whatever the string says.

## Implementation record, attempt 1

I wrote the guard with `new URL(...).hostname`.

## Verify gate

| I-1 | **The loader refuses any host but this machine.** | **FAIL** |

The fix is small: refuse a connection string whose search parameters contain
`host`.

## Review gate

review: pass
"""

OWED = ('Invariant M1, "the loader refuses any other host", is still false: the '
        'guard reads the URL hostname, and the driver dials whatever the '
        'query string says.')

REMEDY = "refuse `host` and `hostaddr`"

NOT_YOURS = ('Not yours this round: "The browser harness stays configured and '
             'drives no flow" is already met and nothing in either verdict '
             'touches it.')


def issue(body: str = ISSUE, name: str = "01-a.md") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="retrybrief-"))
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = brief.main(argv)
    return code, out.getvalue() + err.getvalue()


def args(path, *extra):
    return ["--issue", str(path), "--attempt", "2"] + list(extra)


class TheAdmissibleRegion(unittest.TestCase):
    """Which part of the issue file an owed item may quote."""

    def test_the_issues_own_text_is_admissible(self):
        region = brief.own_text(ISSUE)
        self.assertIn("The browser harness stays configured", region)
        # Wrapped across a line in the fixture, as it is in the real issue 01.
        self.assertTrue(brief.in_own_text(ISSUE, "the loader refuses any other host"))

    def test_a_gate_verdict_is_not_admissible(self):
        region = brief.own_text(ISSUE)
        self.assertNotIn("search parameters contain", region)

    def test_the_implementers_own_record_is_not_admissible(self):
        """It comes before the gate headings and is still not the issue. A
        runner quoting the previous attempt's own words would satisfy the rule
        with the reasoning that failed."""
        region = brief.own_text(ISSUE)
        self.assertNotIn("new URL", region)

    def test_a_quoted_phrase_wrapped_across_lines_still_matches(self):
        """The issue file wraps. A rule that broke on a line break would refuse
        correct briefs, and a check people cannot satisfy is a check they route
        around."""
        self.assertTrue(brief.in_own_text(ISSUE, "the loader refuses any other host"))


class WhatItRefuses(unittest.TestCase):

    def test_a_brief_with_no_owed_item_is_refused(self):
        code, text = run_main(args(issue()))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_an_owed_item_carrying_no_quotation_is_refused(self):
        code, text = run_main(args(issue(), "--owed", "fix the guard"))
        self.assertEqual(code, 1)
        self.assertIn("quote", text.lower())

    def test_the_gates_own_remedy_as_an_owed_item_is_refused(self):
        """This is the incident. The round-2 brief said exactly this."""
        code, text = run_main(args(
            issue(), "--owed",
            'The guard must "refuse a connection string whose search '
            'parameters contain `host`".'))
        self.assertEqual(code, 1)
        self.assertIn("gate", text.lower())

    def test_a_phrase_that_is_nowhere_in_the_issue_is_refused(self):
        code, text = run_main(args(
            issue(), "--owed", 'The guard must "reject every IPv6 literal".'))
        self.assertEqual(code, 1)
        self.assertIn("reject every IPv6 literal", text)

    def test_a_short_token_in_quotes_is_not_a_warrant(self):
        """`"host"` is in the issue, and an item built round it is the gate's
        remedy with a token in quotes — the shape this script exists to refuse.
        A real criterion phrase is long: "the loader refuses any other host" is
        33 characters, so the floor costs a correct brief nothing."""
        code, text = run_main(args(
            issue(), "--owed", 'The guard must refuse "host" parameters.'))
        self.assertEqual(code, 1)

    def test_a_phrase_at_the_floor_is_still_a_warrant(self):
        """The floor must not be so high that a short real criterion fails."""
        self.assertEqual(len(brief.quoted('x "drives no flow today" y')), 1)

    def test_an_owed_item_quoting_the_issue_passes(self):
        code, text = run_main(args(issue(), "--owed", OWED))
        self.assertEqual(code, 0)
        self.assertIn("the loader refuses any other host", text)

    def test_a_remedy_before_any_owed_item_is_refused(self):
        code, text = run_main(args(issue(), "--remedy", REMEDY))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_a_not_yours_item_obeys_the_same_rule(self):
        """Step 7 already says the not-yours list is checked and not asserted.
        Until this script, nothing checked it."""
        code, text = run_main(args(
            issue(), "--owed", OWED, "--not-yours", "the browser harness"))
        self.assertEqual(code, 1)
        self.assertIn("quote", text.lower())

    def test_a_not_yours_item_quoting_the_issue_passes(self):
        code, text = run_main(args(
            issue(), "--owed", OWED, "--not-yours", NOT_YOURS))
        self.assertEqual(code, 0)

    def test_a_first_attempt_is_refused_because_a_retry_starts_at_two(self):
        code, text = run_main(
            ["--issue", str(issue()), "--attempt", "1", "--owed", OWED])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_an_issue_path_inside_a_worktree_is_accepted(self):
        """Ruled by the human, 2026-09-13, reversing the refusal this pinned.

        `SKILL.md` has the gates write their verdict beside the BRANCH,
        so the worktree copy is the only one that holds it. Refusing that path
        made the two preconditions unsatisfiable, and run `batch-19ff9f`
        satisfied them by hand twice. The verdict the brief needs is asserted by
        `test_an_issue_holding_no_gate_verdict_is_refused` below, which asks the
        real question and does not care which path carries it.
        """
        root = pathlib.Path(tempfile.mkdtemp(prefix="retrybrief-wt-"))
        deep = root / ".claude" / "worktrees" / "batch-1" / ".scratch" / "issues"
        deep.mkdir(parents=True)
        path = deep / "01-a.md"
        path.write_text(ISSUE, encoding="utf-8")
        code, text = run_main(args(path, "--owed", OWED))
        self.assertEqual(code, 0, text)
        self.assertNotIn("MAIN CHECKOUT", text)

    def test_a_worktree_path_with_no_verdict_is_still_refused(self):
        """The path never mattered. The missing verdict always did."""
        root = pathlib.Path(tempfile.mkdtemp(prefix="retrybrief-wt2-"))
        deep = root / ".claude" / "worktrees" / "batch-1" / ".scratch" / "issues"
        deep.mkdir(parents=True)
        path = deep / "01-a.md"
        path.write_text("# 01 a thing\n\n## Acceptance criteria\n\n1. a thing\n",
                        encoding="utf-8")
        code, text = run_main(args(path, "--owed", OWED))
        self.assertEqual(code, 1)
        self.assertIn("Verify gate", text)

    def test_an_issue_holding_no_gate_verdict_is_refused(self):
        """A retry exists because a gate rejected. A file with no verdict in it
        means the grounds came from somewhere else."""
        path = issue("# 01 a thing\n\n## Acceptance criteria\n\n1. a thing\n")
        code, text = run_main(args(path, "--owed", OWED))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_an_unreadable_issue_is_refused(self):
        code, text = run_main(
            ["--issue", "/nowhere/01-a.md", "--attempt", "2", "--owed", OWED])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)


class TheVerdictsLiveInTheRun(unittest.TestCase):
    """Issue 24 of the tracker-tooling set, 2026-09-23. A gate writes its
    verdict to `runs/<batch-id>/verdicts/<issue>-attempt-<N>.md`, never into
    the issue file, so the "is there a verdict" question is asked of that
    file."""

    SPEC = ISSUE.split("## Verify gate")[0].split("## Implementation record")[0]
    VERDICTS = "## Verify gate" + ISSUE.split("## Verify gate", 1)[1]

    def test_an_issue_with_no_gate_heading_passes_when_the_verdicts_hold_one(self):
        path = issue(self.SPEC)
        verdicts = issue(self.VERDICTS, name="01-attempt-1.md")
        code, text = run_main(args(path, "--verdicts", str(verdicts),
                                   "--owed", OWED))
        self.assertEqual(code, 0, text)

    def test_a_verdicts_file_holding_no_gate_heading_is_refused(self):
        path = issue(ISSUE)
        verdicts = issue("# nothing here\n", name="01-attempt-2.md")
        code, text = run_main(args(path, "--verdicts", str(verdicts),
                                   "--owed", OWED))
        self.assertEqual(code, 1)
        self.assertIn("01-attempt-2.md", text)

    def test_an_unreadable_verdicts_file_is_refused(self):
        code, text = run_main(args(issue(self.SPEC), "--verdicts",
                                   "/nowhere/01-attempt-1.md", "--owed", OWED))
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)

    def test_a_quote_from_the_verdicts_file_is_still_not_the_issues_text(self):
        path = issue(self.SPEC)
        verdicts = issue(self.VERDICTS, name="01-attempt-1.md")
        code, text = run_main(args(
            path, "--verdicts", str(verdicts), "--owed",
            'Criterion 1: "refuse a connection string whose search parameters '
            'contain" is owed.'))
        self.assertEqual(code, 1, text)



class EachGateHasItsOwnFile(unittest.TestCase):
    """Issue 51 of the tracker-tooling set, AC5: each gate writes its own
    verdict file, and each file is read for its own gate's heading."""

    SPEC = TheVerdictsLiveInTheRun.SPEC
    OWED_TOO = ('Criterion 1, "The suite runs online against the local '
                'database", is still false: the suite never reached it.')

    def spec(self, level="full"):
        return issue(f"Level: {level}\n" + self.SPEC)

    def gate_file(self, gate, body=None):
        heading = "## Review gate" if gate == "review" else "## Verify gate"
        return issue(body if body is not None else f"{heading}\n\nREJECT\n",
                     name=f"01-attempt-1-{gate}.md")

    def brief(self, spec, *files):
        extra = []
        for path in files:
            extra += ["--verdicts", str(path)]
        return run_main(args(spec, *extra, "--owed", OWED,
                             "--owed", self.OWED_TOO))

    def test_both_gate_files_build_one_brief(self):
        code, text = self.brief(self.spec(), self.gate_file("review"),
                                self.gate_file("verify"))
        self.assertEqual(code, 0, text)
        self.assertIn("1. " + OWED, text)
        self.assertIn("2. " + self.OWED_TOO, text)

    def test_a_verify_file_without_its_heading_is_refused(self):
        wrong = self.gate_file("verify", "## Review gate\n\nREJECT\n")
        code, text = self.brief(self.spec(), self.gate_file("review"), wrong)
        self.assertEqual(code, 1)
        self.assertIn(str(wrong), text)
        self.assertIn("## Verify gate", text)

    def test_the_review_file_alone_is_refused_at_full(self):
        code, text = self.brief(self.spec(), self.gate_file("review"))
        self.assertEqual(code, 1)
        self.assertIn("verify file is missing", text)

    def test_the_review_file_alone_builds_the_brief_at_light(self):
        code, text = self.brief(self.spec("light"), self.gate_file("review"))
        self.assertEqual(code, 0, text)

    def test_a_light_issue_with_a_verify_file_on_disk_needs_it_too(self):
        """Code review of issue 51: a light issue the run lifted to full has a
        verify file beside the review file, and its owed items count."""
        review = self.gate_file("review")
        (review.parent / review.name.replace("-review", "-verify")).write_text(
            "## Verify gate\n\nREJECT\n", encoding="utf-8")
        code, text = self.brief(self.spec("light"), review)
        self.assertEqual(code, 1)
        self.assertIn("verify file is missing", text)

    def test_the_legacy_shared_file_alone_still_builds_the_brief(self):
        legacy = issue(TheVerdictsLiveInTheRun.VERDICTS, name="01-attempt-1.md")
        code, text = self.brief(self.spec(), legacy)
        self.assertEqual(code, 0, text)


class NamesACriterion(unittest.TestCase):
    """Tracker-tooling issue 13, fix F10 of the 2026-09-23 audit.

    A retry is a strike, and a strike is bought only on a criterion or an
    invariant the issue holds. Issue 01 of run `batch-d67136` was rejected twice
    on `I-1`, an item the verify gate wrote itself, with all six criteria and
    five invariants passing. The quotation rule let it through: "the loader
    refuses any other host" is the issue's own text, in its Target database
    table, and no criterion states it.
    """

    def test_an_owed_item_naming_no_criterion_is_refused(self):
        item = ('"the loader refuses any other host" is still false: the '
                'guard reads the URL hostname.')
        code, text = run_main(args(issue(), "--owed", item))
        self.assertEqual(code, 1, text)
        self.assertIn("criterion", text.lower())
        self.assertIn("register row", text)
        self.assertIn("criteria re-check", text)

    def test_a_criterion_the_issue_does_not_hold_is_refused(self):
        """The fixture holds one criterion. Criterion 4 is invented."""
        item = ('Criterion 4, "the loader refuses any other host", is still '
                'false.')
        code, text = run_main(args(issue(), "--owed", item))
        self.assertEqual(code, 1, text)
        self.assertIn("C4", text)

    def test_the_gates_own_label_is_not_an_invariant(self):
        """`I-1` is the verify gate's label, written in its verdict. The issue's
        own `## Must still be true` holds no such line."""
        item = ('I-1, "the loader refuses any other host", is still false.')
        code, text = run_main(args(issue(), "--owed", item))
        self.assertEqual(code, 1, text)

    def test_a_numbered_criterion_the_issue_holds_passes(self):
        item = ('Criterion 1, "The suite runs online against the local '
                'database", fails when the loader dials elsewhere.')
        code, text = run_main(args(issue(), "--owed", item))
        self.assertEqual(code, 0, text)

    def test_the_plural_names_its_first_criterion(self):
        """Found by the review of 2026-09-23: "criteria 1 and 2" is a name."""
        item = ('Criteria 1 as written, "The suite runs online against the local '
                'database", fail when the loader dials elsewhere.')
        code, text = run_main(args(issue(), "--owed", item))
        self.assertEqual(code, 0, text)

    def test_the_issues_own_invariant_label_passes(self):
        code, text = run_main(args(issue(), "--owed", OWED))
        self.assertEqual(code, 0, text)
        self.assertIn("M1", text)


class TheNamesAnIssueHolds(unittest.TestCase):
    """`criteria_ids.py`, the one reader of the names issue 14 also reads."""

    BODY = ("## Acceptance criteria\n\n1. **One.** text\n\n   1. nested, not a "
            "criterion\n2. Two.\n\n## Must still be true\n\n1. **A plain "
            "invariant.**\n- **M7 — a labelled one.**\n\n## Blocked by\n\n"
            "3. not an invariant\n\n## Verify gate\n\n- **M8 — the gate's own.**\n")

    def test_criteria_invariants_and_labels_are_read_from_their_sections(self):
        import criteria_ids
        self.assertEqual(criteria_ids.known_ids(self.BODY),
                         {"C1", "C2", "I1", "M7"})

    # Tracker-tooling issue 26: the four forms one tracker's issues held on
    # 2026-09-24, one reader for the launch check and the charging tool.
    FORMS = {
        "numbered": ("1. **One.**\n2. **Two.**\n", {"C1", "C2"}),
        "checklist": ("- [ ] **One.** text\n      more\n- [x] Two, fixture: x\n",
                      {"C1", "C2"}),
        "checklist, numbered in bold": (
            "- [ ] **1. One.**\n- [ ] **2. Two.**\n- [ ] **3. Three.**\n",
            {"C1", "C2", "C3"}),
        "a box naming criterion N": ("- [ ] **Criterion 1, ground (a).**\n"
                                     "- [ ] **Criterion 2: two.**\n", {"C1", "C2"}),
        "a bare bullet naming criterion N": ("- **Criterion 1: one.**\n"
                                             "- **Criterion 2: two.**\n", {"C1", "C2"}),
        # A second tracker's 285: a bold paragraph opening on its number.
        "a bold paragraph on its number": ("Graded on QA.\n\n**1. One.**\n\nmore\n\n"
                                           "**2. Two.**\n", {"C1", "C2"}),
        # That tracker's 421b: a named note above unnumbered boxes is not C4.
        "a named note above boxes": ("- **Criterion 4** went to 421e.\n\n"
                                     "- [ ] **One.**\n- [ ] **Two.**\n", {"C1", "C2"}),
    }

    def test_a_deeper_heading_is_read_and_ends_at_its_own_level(self):
        """The second tracker's 161 files its criteria under
        `### Acceptance criteria`."""
        import criteria_ids
        body = ("## Hardening\n\n### Acceptance criteria\n\n1. **One.**\n\n"
                "#### A table inside it\n\nrow\n\n2. **Two.**\n\n"
                "### Must still be true\n\n1. **Held.**\n")
        self.assertEqual(criteria_ids.known_ids(body),
                         {"C1", "C2", "I1", "M1"})

    def test_every_form_in_use_is_named(self):
        import criteria_ids
        for form, (items, want) in self.FORMS.items():
            with self.subTest(form=form):
                body = f"## Acceptance criteria\n\n{items}\n## Must still be true\n\n- x\n"
                # The one unlabelled invariant bullet is I1, and M1 beside it
                # (issue 232 of run `batch-04dff9`).
                self.assertEqual(criteria_ids.known_ids(body),
                                 want | {"I1", "M1"})

    def test_a_plain_bullet_or_a_nested_box_is_not_a_criterion(self):
        import criteria_ids
        body = ("## Acceptance criteria\n\n**Where to start.** prose\n"
                "- a note, not a criterion\n\n- [ ] **Criterion 1.**\n"
                "  - [ ] a step inside it\n")
        self.assertEqual(criteria_ids.known_ids(body), {"C1"})

    def test_a_bold_date_is_not_a_criterion(self):
        """The review of issue 26: only `**N. ` or `**Criterion N` opens one."""
        import criteria_ids
        body = "## Acceptance criteria\n\n**2026-09-02:** QA held 29 tasks.\n"
        self.assertEqual(criteria_ids.criteria(body), [])

    def test_the_shallowest_heading_wins(self):
        import criteria_ids
        body = ("## Corrections\n\n### Acceptance criteria, what changed\n\n"
                "1. **A note.**\n\n## Acceptance criteria\n\n- [ ] **One.**\n"
                "- [ ] **Two.**\n")
        self.assertEqual(criteria_ids.known_ids(body), {"C1", "C2"})
        self.assertIn("One", criteria_ids.criteria(body)[0][1])

    def test_prose_alone_names_nothing(self):
        import criteria_ids
        body = "## Acceptance criteria\n\nIt must work, on every shape.\n"
        self.assertEqual(criteria_ids.criteria(body), [])

    def test_criteria_come_back_with_their_text(self):
        import criteria_ids
        body = "## Acceptance criteria\n\n- [ ] **One.**\n  more of one\n- [ ] **Two.**\n"
        got = criteria_ids.criteria(body)
        self.assertEqual([number for number, _ in got], ["1", "2"])
        self.assertIn("more of one", got[0][1])
        self.assertNotIn("Two", got[0][1])

    def test_the_prose_spellings_normalise_to_one_name(self):
        import criteria_ids
        self.assertEqual(
            criteria_ids.named_ids(
                "criterion 3 and C4, invariant 2, I5, invariant M9 and M10"),
            ["C3", "C4", "I2", "I5", "M9", "M10"])


class WhatItComposes(unittest.TestCase):

    def test_the_remedy_is_printed_as_an_example_and_not_the_specification(self):
        code, text = run_main(args(
            issue(), "--owed", OWED, "--remedy", REMEDY))
        self.assertEqual(code, 0)
        self.assertIn(REMEDY, text)
        self.assertIn("one example", text.lower())
        self.assertLess(text.index("the loader refuses any other host"),
                        text.index(REMEDY),
                        "the remedy must sit under the invariant, not above it")

    def test_the_prompt_earns_the_cap_hooks_retry_exemption(self):
        """Judged by the HOOK'S OWN function, never by a second copy of its
        rule. A retry brief the cap refuses does not spawn at all."""
        prompt = brief.compose(str(issue()), 2, [(OWED, [])], [])
        hook = brief.hook_module()
        if hook is None:
            self.skipTest("no cap hook installed on this machine")
        self.assertEqual(hook.exemption(prompt), "retry")

    def test_with_no_hook_installed_the_prompt_is_still_emitted(self):
        original = brief.hook_module
        try:
            brief.hook_module = lambda: None
            code, text = run_main(args(issue(), "--owed", OWED))
            self.assertEqual(code, 0)
        finally:
            brief.hook_module = original


# The genuine issue file run `batch-d67136` left behind, for anybody who still
# has it. A machine-local path does not travel and does not belong in a drill, so
# this is opt-in: set `RETRY_BRIEF_CORPUS` to the issue file and the two checks
# below run. Unset, they skip, and the fixture above grades the same rule.
#
# Read against the real file on 2026-09-13: the invariant the brief dropped is
# admissible, and the remedy it carried is not.
REAL = pathlib.Path(os.environ.get("RETRY_BRIEF_CORPUS", "")) if os.environ.get(
    "RETRY_BRIEF_CORPUS") else None


@unittest.skipUnless(REAL is not None and REAL.exists(),
                     "set RETRY_BRIEF_CORPUS to a real rejected issue file")
class AgainstTheIncidentItself(unittest.TestCase):
    """A genuine issue file a gate rejected twice, rather than a fixture."""

    def body(self):
        return REAL.read_text(encoding="utf-8", errors="replace")

    def test_the_invariant_the_brief_dropped_is_admissible(self):
        self.assertTrue(
            brief.in_own_text(self.body(), "the loader refuses any other host"))

    def test_the_remedy_the_brief_carried_is_not_admissible(self):
        self.assertFalse(brief.in_own_text(
            self.body(),
            "refuse a connection string whose search parameters contain"))


if __name__ == "__main__":
    unittest.main()
