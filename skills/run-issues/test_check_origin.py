"""Drill for check_origin.py.

The corpus is the shape a writer files: a register table whose header names an
`origin` column, and a minted issue file whose header carries an `Origin:` line.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "check_origin", os.path.join(HERE, "check_origin.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEADER = (
    "| id | what | audience | severity | status | origin | owner-notes |\n"
    "|---|---|---|---|---|---|---|\n"
)


def row(rid, origin):
    return (f"| {rid} | something is wrong | operator | medium | candidate "
            f"| {origin} | candidate; bugs/{rid}.md |\n")


def faults(text):
    return mod.register_faults(text)


def test_a_row_naming_its_issue_and_its_run_passes():
    assert faults(HEADER + row("a-01", "149e/batch-170a59")) == []


def test_an_empty_origin_cell_is_named():
    found = faults(HEADER + row("a-01", ""))
    assert len(found) == 1
    assert found[0].row_id == "a-01"
    assert "empty" in found[0].reason


def test_a_value_that_is_neither_shape_is_named():
    found = faults(HEADER + row("a-01", "the 149e review gate"))
    assert len(found) == 1
    assert "149e review gate" in found[0].reason


def test_unknown_alone_is_legal_because_the_watcher_knows_neither_half():
    assert faults(HEADER + row("a-01", "unknown")) == []


def test_either_half_may_be_unknown_on_its_own():
    assert faults(HEADER + row("a-01", "unknown/batch-170a59")) == []
    assert faults(HEADER + row("a-02", "149e/unknown")) == []


def test_a_table_declaring_no_origin_column_is_history_and_is_skipped():
    # The register carries rounds back to `b01` under a dozen header shapes.
    # Ruling 7 starts the count the day the key lands, so none of them is graded.
    history = (
        "| id | what | audience | severity | owner-notes |\n"
        "|---|---|---|---|---|\n"
        "| ph10-01 | something is wrong | operator | medium | open |\n"
    )
    assert faults(history) == []


def test_history_below_a_graded_table_does_not_inherit_its_columns():
    text = HEADER + row("a-01", "149e/batch-170a59") + "\n" + (
        "| id | what | audience | severity | owner-notes |\n"
        "|---|---|---|---|---|\n"
        "| ph10-01 | something is wrong | operator | medium | open |\n"
    )
    assert faults(text) == []


def test_every_offence_is_reported_not_only_the_first():
    text = HEADER + row("a-01", "") + row("a-02", "nonsense") + row(
        "a-03", "149e/batch-170a59")
    assert [f.row_id for f in faults(text)] == ["a-01", "a-02"]


def test_bold_and_backticks_are_stripped_before_judging():
    assert faults(HEADER + row("a-01", "**`149e/batch-170a59`**")) == []


def test_an_escaped_pipe_inside_a_cell_does_not_shift_the_columns():
    # `document_counters` row h0903-03 carries `2026 \| 4` in the live register.
    line = ("| a-01 | it holds 2026 \\| 4 | operator | medium | candidate "
            "| 149e/batch-170a59 | candidate; bugs/a-01.md |\n")
    assert faults(HEADER + line) == []


def test_the_row_id_is_read_from_the_id_column_not_the_first_column():
    header = (
        "| # | id | what | audience | severity | origin | owner-notes |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    line = ("| 1 | a-07 | something is wrong | operator | medium | "
            "| candidate; bugs/a-07.md |\n")
    found = faults(header + line)
    assert len(found) == 1
    assert found[0].row_id == "a-07"


# The file promotion mints. `tester/medium` naming no blocker is parked, the
# rule of issue 03 of the tracker-tooling set, ruled by the human, 2026-09-13.
ISSUE_HEADER = (
    "Status: parked\n"
    "Parked: 2026-09-13\n"
    "Direct-road: no\n"
    "Owed: unsorted\n"
    "Origin: 149e/batch-170a59\n"
    "Rows: rv149e-1 tester/medium\n"
    "\n"
    "# 561 — the fetch timer charges every read for its own parse\n"
    "\n"
    "Category: performance. Severity: medium. Audience: tester.\n"
    "\n"
    "## Blocked by\n"
    "\n"
    "- Unknown until hardened\n"
)

PARKED_LINES = "Status: parked\nParked: 2026-09-13\n"
HIGH = (ISSUE_HEADER.replace(PARKED_LINES, "Status: needs-harden\n")
        .replace("tester/medium", "tester/high"))


def issue_faults(text):
    return mod.issue_faults(text)


def test_a_minted_issue_naming_its_origin_passes():
    assert issue_faults(ISSUE_HEADER) == []


def test_a_minted_issue_with_no_origin_line_is_refused():
    text = ISSUE_HEADER.replace("Origin: 149e/batch-170a59\n", "")
    found = issue_faults(text)
    assert len(found) == 1
    assert "no `Origin:` line" in found[0].reason


def test_a_minted_issue_whose_origin_does_not_parse_is_refused():
    text = ISSUE_HEADER.replace("149e/batch-170a59", "the 149e review gate")
    found = issue_faults(text)
    assert len(found) == 1
    assert "149e review gate" in found[0].reason


def test_an_origin_below_the_title_does_not_satisfy_the_check():
    # The key is a header field beside `Owed:` and `Stage:`. A sentence in the
    # body that happens to open with the word must not pass for one.
    text = (ISSUE_HEADER.replace("Origin: 149e/batch-170a59\n", "")
            + "\nOrigin: 149e/batch-170a59\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "no `Origin:` line" in found[0].reason


def test_a_minted_issue_with_no_rows_line_is_refused():
    # The merge licence of 2026-09-13 lets one file resolve up to three rows.
    # The ceiling can only bite a file that declares what it resolved, so the
    # line is mandatory at one row as well as at three. The fact is already in
    # the prose of every file batch-d67136 minted -- "Promoted from register row
    # `rv01-6` ... Audience operator, severity medium" -- and this gives it a
    # cell, the same move `Origin:` made.
    text = ISSUE_HEADER.replace("Rows: rv149e-1 tester/medium\n", "")
    found = issue_faults(text)
    assert len(found) == 1
    assert "`Rows:` line" in found[0].reason


def test_a_rows_line_below_the_title_does_not_satisfy_the_check():
    text = (ISSUE_HEADER.replace("Rows: rv149e-1 tester/medium\n", "")
            + "\nRows: rv149e-1 tester/medium\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "`Rows:` line" in found[0].reason


def test_a_rows_line_that_does_not_parse_is_refused():
    text = ISSUE_HEADER.replace("Rows: rv149e-1 tester/medium",
                                "Rows: the three date picker rows")
    found = issue_faults(text)
    assert len(found) == 1
    assert "date picker" in found[0].reason


def test_three_rows_agreeing_on_audience_and_severity_pass():
    text = ISSUE_HEADER.replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: rv149e-1 tester/medium; rv149e-2 tester/medium; "
        "vg149e-1 tester/medium")
    assert issue_faults(text) == []


def test_a_fourth_row_breaks_the_ceiling():
    # Clause 1. A merge rule with no ceiling is how three real defects become
    # one unreviewable ticket.
    text = ISSUE_HEADER.replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 tester/medium; a-2 tester/medium; a-3 tester/medium; "
        "a-4 tester/medium")
    found = issue_faults(text)
    assert len(found) == 1
    assert "4" in found[0].reason and "3" in found[0].reason


def test_rows_disagreeing_on_severity_are_refused():
    # Clause 3. This is what protects the floor: merging a `low` into a
    # `medium` smuggles a row past the operator floor set on 2026-08-09.
    text = ISSUE_HEADER.replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 tester/medium; a-2 tester/low")
    found = issue_faults(text)
    assert len(found) == 1
    assert "severity" in found[0].reason


def test_rows_disagreeing_on_audience_are_refused():
    text = ISSUE_HEADER.replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 operator/medium; a-2 tester/medium")
    found = issue_faults(text)
    assert len(found) == 1
    assert "audience" in found[0].reason


def test_a_merged_file_may_not_be_a_direct_road_candidate():
    # Clause 5. Three rows in one file is exactly the unreviewable ticket the
    # direct road must not take.
    text = ISSUE_HEADER.replace(
        "Direct-road: no", "Direct-road: candidate").replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 tester/medium; a-2 tester/medium")
    found = issue_faults(text)
    assert len(found) == 1
    assert "Direct-road" in found[0].reason


def test_a_single_row_file_may_still_be_a_direct_road_candidate():
    text = ISSUE_HEADER.replace("Direct-road: no", "Direct-road: candidate")
    assert issue_faults(text) == []


def test_every_offence_in_one_issue_file_is_reported_not_only_the_first():
    # The file prints every offence for the same reason the register mode does:
    # both grade a file somebody is about to repair by hand.
    text = ISSUE_HEADER.replace(
        "Origin: 149e/batch-170a59", "Origin: nonsense").replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 tester/medium; a-2 tester/low")
    found = issue_faults(text)
    assert len(found) == 2


# --- the parked rule --------------------------------------------------------
#
# Issue 03 of the tracker-tooling set, ruled by the human, 2026-09-13, on one
# project's tracker: 641 issues, 149 of them needs-harden, and none of the 149
# named as a blocker by any other issue. Promotion parks a medium or low row
# that names no blocker; high and above stays needs-harden. The rule is graded
# here rather than remembered in the brief.


def test_a_medium_row_naming_no_blocker_is_parked():
    assert issue_faults(ISSUE_HEADER) == []


def test_a_medium_row_written_needs_harden_is_refused():
    text = ISSUE_HEADER.replace(PARKED_LINES, "Status: needs-harden\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "parked" in found[0].reason and "medium" in found[0].reason


def test_a_high_row_is_needs_harden():
    assert issue_faults(HIGH) == []


def test_a_high_row_written_parked_is_refused():
    text = HIGH.replace("Status: needs-harden\n", PARKED_LINES)
    found = issue_faults(text)
    assert len(found) == 1
    assert "needs-harden" in found[0].reason and "high" in found[0].reason


def test_a_critical_row_is_needs_harden_too():
    text = HIGH.replace("tester/high", "tester/critical")
    assert issue_faults(text) == []


def test_a_low_row_is_parked_like_a_medium_one():
    text = ISSUE_HEADER.replace("tester/medium", "tester/low")
    assert issue_faults(text) == []


def test_a_medium_row_that_names_a_blocker_is_needs_harden():
    """Parked is for an issue nothing waits on and that waits on nothing. A file
    naming an edge at mint time is already tied to other work."""
    text = (ISSUE_HEADER.replace(PARKED_LINES, "Status: needs-harden\n")
            .replace("- Unknown until hardened", "- 149e-rights-engine"))
    assert issue_faults(text) == []


def test_a_medium_row_naming_a_blocker_may_not_be_parked():
    text = ISSUE_HEADER.replace("- Unknown until hardened", "- 149e-rights-engine")
    found = issue_faults(text)
    assert len(found) == 1
    assert "149e" in found[0].reason


def test_a_parked_file_with_no_parked_date_is_refused():
    """The parked sweep ages an issue off that line. Without it the issue is
    parked for ever, which is the deletion the status must not become."""
    text = ISSUE_HEADER.replace("Parked: 2026-09-13\n", "")
    found = issue_faults(text)
    assert len(found) == 1
    assert "`Parked:`" in found[0].reason


def test_a_parked_date_that_is_not_a_date_is_refused():
    text = ISSUE_HEADER.replace("Parked: 2026-09-13", "Parked: today")
    found = issue_faults(text)
    assert len(found) == 1
    assert "today" in found[0].reason


def test_a_parked_date_below_the_title_does_not_satisfy_the_check():
    text = (ISSUE_HEADER.replace("Parked: 2026-09-13\n", "")
            + "\nParked: 2026-09-13\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "`Parked:`" in found[0].reason


def test_the_status_rule_is_silent_where_the_rows_line_cannot_be_read():
    """One cause, one fault. The `Rows:` refusal already names the repair, and a
    second line guessing at a severity nobody declared teaches the reader to
    skim."""
    text = ISSUE_HEADER.replace("Rows: rv149e-1 tester/medium",
                                "Rows: the three date picker rows")
    found = issue_faults(text)
    assert len(found) == 1
    assert "date picker" in found[0].reason


def test_the_status_rule_is_silent_where_the_rows_disagree_on_severity():
    """One cause, one fault, the same rule this file states for a `Rows:` line
    it cannot read. Grading on the first row would tell the writer to park a
    file carrying a `high` row, and a parked high finding is offered by
    nothing until the thirty-day sweep."""
    text = (ISSUE_HEADER.replace(PARKED_LINES, "Status: needs-harden\n")
            .replace("Rows: rv149e-1 tester/medium",
                     "Rows: a-1 tester/medium; a-2 tester/high"))
    found = issue_faults(text)
    assert len(found) == 1
    assert "different severity" in found[0].reason


def test_the_status_may_carry_its_own_bold_like_every_field_beside_it():
    text = ISSUE_HEADER.replace("Status: parked", "Status: **parked**")
    assert issue_faults(text) == []


def test_a_status_line_promotion_never_writes_is_refused():
    text = ISSUE_HEADER.replace("Status: parked", "Status: ready-for-agent")
    found = issue_faults(text)
    assert len(found) == 1
    assert "ready-for-agent" in found[0].reason


def test_a_file_with_no_status_line_is_refused():
    text = ISSUE_HEADER.replace("Status: parked\n", "")
    found = issue_faults(text)
    assert len(found) == 1
    assert "`Status:`" in found[0].reason


# --- the audience clause ----------------------------------------------------
#
# Ruled by the human on 2026-09-19, on one tracker's measurement: 50 parked
# issues and every one of them `operator`/`medium`. Among them a list page
# showing none of the design files it exists to show, a raise form that never
# names the customer it just created, and two primary buttons painting dark ink
# on dark green. The rule above read severity and a blocker and never the
# audience, so it could not tell a screen from a build check. An `operator` row
# now goes to needs-harden whatever its severity; only `tester` and `agent` rows
# park.
#
# The fault this section closes was measured on 2026-09-21: all nine issues
# promotion minted from one run exited 1 on this one point and nothing else, and
# about 50 issues in that tracker carried a hand-written `Un-parked: 2026-09-19`
# repair line.

OPERATOR = ISSUE_HEADER.replace("tester/medium", "operator/medium").replace(
    "Audience: tester.", "Audience: operator.")


def test_an_operator_row_naming_no_blocker_is_needs_harden():
    text = OPERATOR.replace(PARKED_LINES, "Status: needs-harden\n")
    assert issue_faults(text) == []


def test_an_operator_row_written_parked_is_refused():
    """The measured fault: the nine files one run's promotion minted."""
    found = issue_faults(OPERATOR)
    assert len(found) == 1
    assert "operator" in found[0].reason
    assert "needs-harden" in found[0].reason


def test_an_operator_row_at_low_is_needs_harden_too():
    """The clause reads the audience before the severity, so the floor the
    severity rule sets never reaches an `operator` row."""
    text = OPERATOR.replace(PARKED_LINES, "Status: needs-harden\n").replace(
        "operator/medium", "operator/low")
    assert issue_faults(text) == []


def test_an_operator_row_at_low_written_parked_is_refused():
    text = OPERATOR.replace("operator/medium", "operator/low")
    found = issue_faults(text)
    assert len(found) == 1
    assert "operator" in found[0].reason


def test_an_agent_row_parks_like_a_tester_one():
    text = ISSUE_HEADER.replace("tester/medium", "agent/medium")
    assert issue_faults(text) == []


def test_an_agent_row_written_needs_harden_is_refused():
    text = ISSUE_HEADER.replace("tester/medium", "agent/medium").replace(
        PARKED_LINES, "Status: needs-harden\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "parked" in found[0].reason


def test_an_operator_row_that_names_a_blocker_is_needs_harden():
    text = (OPERATOR.replace(PARKED_LINES, "Status: needs-harden\n")
            .replace("- Unknown until hardened", "- 149e-rights-engine"))
    assert issue_faults(text) == []


def test_a_high_operator_row_is_needs_harden_like_any_other_high_one():
    text = HIGH.replace("tester/high", "operator/high")
    assert issue_faults(text) == []


def test_an_operator_row_at_high_is_refused_on_its_severity_not_its_audience():
    """Both are true of an `operator`/`high` file, and the message names one.
    It names the rule that has been there since 2026-09-13, because that is the
    one a reader repairing the file already knows."""
    text = HIGH.replace("tester/high", "operator/high").replace(
        "Status: needs-harden\n", PARKED_LINES)
    found = issue_faults(text)
    assert len(found) == 1
    assert "high" in found[0].reason
    assert "operator" not in found[0].reason


def test_the_status_rule_is_silent_where_the_rows_disagree_on_audience():
    """One cause, one fault, the same rule this file states for a severity the
    rows disagree about. `_rows_faults` already refuses the merge and names the
    repair, and the audience clause cannot be graded on a file that declares
    two audiences without picking one of them for the writer."""
    text = ISSUE_HEADER.replace(
        "Rows: rv149e-1 tester/medium",
        "Rows: a-1 operator/medium; a-2 tester/medium")
    found = issue_faults(text)
    assert len(found) == 1
    assert "audience" in found[0].reason


def test_an_audience_the_clause_cannot_place_is_refused():
    """The clause is an allowlist of the audiences that may park, so a word it
    cannot recognise lands in the refused pile rather than passing silently.
    Promotion writes one of three words and a fourth is a mislabelled row."""
    text = ISSUE_HEADER.replace("tester/medium", "reviewer/medium")
    found = issue_faults(text)
    assert len(found) == 1
    assert "reviewer" in found[0].reason


def test_an_audience_the_clause_cannot_place_is_refused_at_needs_harden_too():
    """It refuses the word, not the status. A file whose audience nothing can
    place is a file the parked rule was never graded on, whichever status it
    happens to carry."""
    text = ISSUE_HEADER.replace("tester/medium", "reviewer/medium").replace(
        PARKED_LINES, "Status: needs-harden\n")
    found = issue_faults(text)
    assert len(found) == 1
    assert "reviewer" in found[0].reason


def test_the_audience_may_carry_its_own_case_like_every_field_beside_it():
    text = OPERATOR.replace(PARKED_LINES, "Status: needs-harden\n").replace(
        "operator/medium", "Operator/medium")
    assert issue_faults(text) == []


# --- the minted sweep -------------------------------------------------------
#
# The corpus is run `batch-d67136`'s own thirteen files, by their real names and
# real origins. Seven shipped issues minted thirteen, and three of the thirteen
# pairs are the same defect written twice: the runner's own close of issue 03
# says so of 34 and 35, and the merge briefing asked promotion to read two other
# pairs together and it had no licence to.

D67136 = [
    ("34-date-picker-stale-note.md", "03/batch-d67136"),
    ("35-date-picker-note-dead-end.md", "03/batch-d67136"),
    ("36-refusal-live-region-mounted-full.md", "03b/batch-d67136"),
    ("37-db-type-imported-from-test-tree.md", "01/batch-d67136"),
    ("38-signed-url-no-ownership-check.md", "04b/batch-d67136"),
    ("39-storage-criteria-undrivable.md", "04b/batch-d67136"),
    ("40-ci-runs-no-next-build.md", "01/batch-d67136"),
    ("41-database-ready-no-connect-timeout.md", "01/batch-d67136"),
    ("42-rls-owner-needs-bypassrls.md", "02/batch-d67136"),
    ("43-jpg-dimension-check-undrivable.md", "04b/batch-d67136"),
    ("44-ci-database-ready-reads-zero.md", "01/batch-d67136"),
    ("45-tailwind-default-grey-on-screen.md", "01/batch-d67136"),
    ("46-file-decode-failure-silent.md", "04b/batch-d67136"),
]


def minted(name, origin, siblings=None):
    text = ISSUE_HEADER.replace("Origin: 149e/batch-170a59", f"Origin: {origin}")
    if siblings:
        text = text.replace("Rows: ", f"Siblings: {siblings}\nRows: ")
    return (name, text)


def corpus(siblings=None):
    siblings = siblings or {}
    return [minted(name, origin, siblings.get(name))
            for name, origin in D67136]


def pairs(faults):
    return sorted(f.row_id for f in faults)


def test_a_slug_keeps_its_own_words_and_drops_english_function_words():
    assert mod.slug_words("40-ci-runs-no-next-build.md") == {
        "ci", "runs", "next", "build"}


def test_two_files_of_one_origin_sharing_a_slug_word_are_refused_as_a_pair():
    files = [minted("34-date-picker-stale-note.md", "03/batch-d67136"),
             minted("35-date-picker-note-dead-end.md", "03/batch-d67136")]
    found = mod.minted_faults("batch-d67136", files)
    assert len(found) == 1
    assert "35-date-picker-note-dead-end.md" in found[0].reason


def test_one_siblings_line_naming_the_other_settles_the_pair():
    files = [minted("34-date-picker-stale-note.md", "03/batch-d67136",
                    "35 — 34 is the stale note, 35 is the refusal with no reason"),
             minted("35-date-picker-note-dead-end.md", "03/batch-d67136")]
    assert mod.minted_faults("batch-d67136", files) == []


def test_a_siblings_line_with_no_reason_is_refused():
    files = [minted("34-date-picker-stale-note.md", "03/batch-d67136", "35"),
             minted("35-date-picker-note-dead-end.md", "03/batch-d67136")]
    found = mod.minted_faults("batch-d67136", files)
    assert any("reason" in f.reason for f in found)


def test_one_origin_alone_is_not_enough_to_fire():
    # Grouping on `Origin:` alone fires on 11 of this run's 13 files and finds
    # 3 true pairs among 17 -- a rule promotion learns to wave through.
    files = [minted("37-db-type-imported-from-test-tree.md", "01/batch-d67136"),
             minted("45-tailwind-default-grey-on-screen.md", "01/batch-d67136")]
    assert mod.minted_faults("batch-d67136", files) == []


def test_a_shared_word_across_two_origins_is_not_a_pair():
    files = [minted("40-ci-runs-no-next-build.md", "01/batch-d67136"),
             minted("99-ci-runs-nothing.md", "03/batch-d67136")]
    assert mod.minted_faults("batch-d67136", files) == []


def test_a_file_from_another_run_is_not_selected():
    files = [minted("34-date-picker-stale-note.md", "03/batch-d67136"),
             minted("35-date-picker-note-dead-end.md", "03/batch-170a59")]
    assert mod.minted_faults("batch-d67136", files) == []


def test_a_file_carrying_no_origin_line_is_history_and_is_skipped():
    # Nothing backfills, held mechanically rather than by a date. Every issue
    # minted before ticket 37 landed carries no `Origin:` line by design.
    history = ("512-an-old-date-picker-note.md",
               "Status: open\n\n# an old thing\n")
    files = [minted("34-date-picker-stale-note.md", "03/batch-d67136"), history]
    assert mod.minted_faults("batch-d67136", files) == []


def test_the_run_fires_on_five_pairs_and_three_of_them_are_the_true_ones():
    found = mod.minted_faults("batch-d67136", corpus())
    reported = {(f.row_id, f.reason.split("`")[1]) for f in found}
    assert len(found) == 5
    true_pairs = {
        ("34-date-picker-stale-note.md", "35-date-picker-note-dead-end.md"),
        ("39-storage-criteria-undrivable.md", "43-jpg-dimension-check-undrivable.md"),
        ("40-ci-runs-no-next-build.md", "44-ci-database-ready-reads-zero.md"),
    }
    assert true_pairs <= reported


def test_the_run_goes_clean_once_every_pair_is_answered():
    # Three merged, two answered with a `Siblings:` line. Thirteen files become
    # ten, which is the 23.1 per cent cut measured on this run.
    answered = corpus(siblings={
        "34-date-picker-stale-note.md":
            "35 — 34 is the stale note, 35 is the silent refusal",
        "39-storage-criteria-undrivable.md":
            "43 — 39 is storage, 43 is the image decode",
        "40-ci-runs-no-next-build.md":
            "44 — 40 is the build step, 44 is the database wait",
        "41-database-ready-no-connect-timeout.md":
            "44 — 41 is the script's own timeout, 44 is what CI reads from it",
        "38-signed-url-no-ownership-check.md":
            "43 — 38 is an ownership hole, 43 is an undrivable criterion",
    })
    assert mod.minted_faults("batch-d67136", answered) == []


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_a_clean_register_exits_zero(tmp_path, capsys):
    path = write(tmp_path, "register.md", HEADER + row("a-01", "149e/batch-170a59"))
    assert mod.main(["--register", path]) == 0


def test_a_register_holding_an_offence_exits_one_and_names_the_row(tmp_path, capsys):
    path = write(tmp_path, "register.md", HEADER + row("a-01", ""))
    assert mod.main(["--register", path]) == 1
    printed = capsys.readouterr().out
    assert "a-01" in printed and "empty" in printed


def test_a_file_that_cannot_be_read_exits_two(tmp_path):
    assert mod.main(["--register", str(tmp_path / "absent.md")]) == 2


def test_the_unknown_count_is_printed_so_the_rate_stays_visible(tmp_path, capsys):
    text = HEADER + row("a-01", "unknown") + row("a-02", "149e/batch-170a59")
    path = write(tmp_path, "register.md", text)
    assert mod.main(["--register", path]) == 0
    assert "1" in capsys.readouterr().out


def test_a_clean_minted_issue_exits_zero(tmp_path):
    path = write(tmp_path, "561-a-thing.md", ISSUE_HEADER)
    assert mod.main(["--issue", path]) == 0


def test_a_minted_issue_with_no_origin_exits_one(tmp_path, capsys):
    path = write(tmp_path, "561-a-thing.md",
                 ISSUE_HEADER.replace("Origin: 149e/batch-170a59\n", ""))
    assert mod.main(["--issue", path]) == 1
    assert "Origin:" in capsys.readouterr().out


def test_the_pass_line_says_how_many_rows_it_actually_graded(tmp_path, capsys):
    # A file with no origin-declaring table grades NOTHING. Reporting that as
    # "every graded row names its origin" is the `ok` on a table nobody could
    # read that `check_commit_order.status_rows` exists to prevent.
    history = (
        "| id | what | audience | severity | owner-notes |\n"
        "|---|---|---|---|---|\n"
        "| ph10-01 | something is wrong | operator | medium | open |\n"
    )
    path = write(tmp_path, "register.md", history)
    assert mod.main(["--register", path]) == 0
    printed = capsys.readouterr().out
    assert "0 row(s) graded" in printed


def test_a_graded_file_names_its_row_count_too(tmp_path, capsys):
    path = write(tmp_path, "register.md",
                 HEADER + row("a-01", "149e/batch-170a59") + row("a-02", "unknown"))
    assert mod.main(["--register", path]) == 0
    printed = capsys.readouterr().out
    assert "2 row(s) graded" in printed


def test_refusing_an_issue_says_that_files_minted_before_the_key_are_not_faults(
        tmp_path, capsys):
    # Measured 2026-09-06: issue 512, minted 2026-09-01, carries no `Origin:`
    # line, and neither does any other issue in the tracker. Ruling 7 starts the
    # count the day the key lands, so this mode grades a file promotion has JUST
    # written and is never run over the directory.
    path = write(tmp_path, "512-a-thing.md",
                 ISSUE_HEADER.replace("Origin: 149e/batch-170a59\n", ""))
    assert mod.main(["--issue", path]) == 1
    printed = capsys.readouterr().out.lower()
    assert "just minted" in printed
    assert "before ticket 37 landed" in printed


def sweep_dir(tmp_path, files):
    folder = tmp_path / "issues"
    folder.mkdir()
    for name, text in files:
        (folder / name).write_text(text, encoding="utf-8")
    return str(folder)


def test_the_sweep_of_a_clean_run_exits_zero_and_says_what_it_selected(
        tmp_path, capsys):
    answered = corpus(siblings={
        "34-date-picker-stale-note.md": "35 — one is stale, one is silent",
        "39-storage-criteria-undrivable.md": "43 — storage, then decode",
        "40-ci-runs-no-next-build.md": "44 — the build step, then the wait",
        "41-database-ready-no-connect-timeout.md": "44 — its timeout, then CI",
        "38-signed-url-no-ownership-check.md": "43 — a hole, then a criterion",
    })
    folder = sweep_dir(tmp_path, answered)
    assert mod.main(["--minted", "batch-d67136", "--issues", folder]) == 0
    assert "13 file(s)" in capsys.readouterr().out


def test_the_sweep_exits_one_and_names_both_files_of_every_pair(tmp_path, capsys):
    folder = sweep_dir(tmp_path, corpus())
    assert mod.main(["--minted", "batch-d67136", "--issues", folder]) == 1
    printed = capsys.readouterr().out
    assert "34-date-picker-stale-note.md" in printed
    assert "35-date-picker-note-dead-end.md" in printed
    assert "5 pair(s)" in printed


def test_the_sweep_says_so_when_the_run_id_selected_nothing(tmp_path, capsys):
    # A sweep that graded nothing and prints `ok` is the `ok` on a table nobody
    # could read that `check_commit_order.status_rows` exists to prevent.
    folder = sweep_dir(tmp_path, corpus())
    assert mod.main(["--minted", "batch-170a59", "--issues", folder]) == 0
    assert "0 file(s)" in capsys.readouterr().out


def test_an_empty_run_id_is_refused_and_never_reaches_a_path(tmp_path, capsys):
    # `--minted ""` used to be falsy, skip the sweep branch, and reach
    # `os.path.exists(None)`. `--register ""` and `--issue ""` both exit 2, so
    # the sweep must not be the one mode that raises.
    import pytest
    with pytest.raises(SystemExit):
        mod.main(["--minted", ""])


def test_a_file_named_outside_the_tracker_shape_shares_no_word_with_another():
    # The fallback used to keep the extension, so `notes.md` and `plan.md` both
    # carried the word "md" and were reported as one finding written twice.
    assert "md" not in mod.slug_words("notes.md")
    header = "Origin: 01/r\n\n# a thing\n"
    assert mod.minted_faults("r", [("notes.md", header),
                                   ("plan.md", header)]) == []


def test_a_sweep_of_a_directory_that_is_not_there_exits_two(tmp_path):
    assert mod.main(
        ["--minted", "batch-d67136", "--issues", str(tmp_path / "gone")]) == 2


def test_the_sweep_refuses_to_run_without_a_run_id_to_scope_it(tmp_path, capsys):
    # Scoped by run id is what makes it backfill nothing. A sweep over the whole
    # tracker would report every issue minted before this rule existed.
    import pytest
    folder = sweep_dir(tmp_path, corpus())
    with pytest.raises(SystemExit):
        mod.main(["--issues", folder])


if __name__ == "__main__":
    # These are pytest checks, and no `python3` on this machine imports pytest.
    # The ritual runs every suite as `python3 <file>`, so the block finds pytest
    # through `uv` when the import fails, and REFUSES when neither road exists.
    # Exiting 0 here without running them is the silence this block closes.
    import subprocess
    import sys as _sys
    try:
        import pytest
    except ImportError:
        try:
            raise SystemExit(subprocess.call(
                ["uv", "run", "--with", "pytest", "pytest", "-q", __file__]))
        except FileNotFoundError:
            print("REFUSED silent-suite: this file holds pytest checks and this "
                  "machine has neither an importable pytest nor `uv` to fetch "
                  "one.\n  Nothing ran. This is not a pass.", file=_sys.stderr)
            raise SystemExit(2)
    raise SystemExit(pytest.main([__file__, "-q"]))
