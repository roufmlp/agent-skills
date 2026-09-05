"""Drill for check_register_status.py.

The corpus is the shape a writer files: a markdown table whose header names a
`status` column and an `owner-notes` column.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "check_register_status", os.path.join(HERE, "check_register_status.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEADER = (
    "| id | what | audience | severity | status | owner-notes |\n"
    "|---|---|---|---|---|---|\n"
)


def row(rid, status, notes):
    return f"| {rid} | something is wrong | operator | medium | {status} | {notes} |\n"


def faults(text):
    return mod.faults(text)


def test_a_clean_table_reports_nothing():
    text = HEADER + row("a-01", "candidate", "candidate; bugs/a-01.md")
    assert faults(text) == []


def test_an_illegal_status_word_is_named():
    text = HEADER + row("a-01", "nearly", "open; bugs/a-01.md")
    found = faults(text)
    assert len(found) == 1
    assert found[0].row_id == "a-01"
    assert "nearly" in found[0].reason


def test_the_transposed_row_is_caught_by_the_disagreement_rule():
    # The measured fault of run batch-b5e96d: `verified` in the status cell
    # and the bare word `open` in the notes cell, on three rows.
    text = HEADER + row("im557b-03", "verified", "open")
    found = faults(text)
    assert len(found) == 1
    assert found[0].row_id == "im557b-03"
    assert "verified" in found[0].reason and "open" in found[0].reason


def test_every_offence_is_reported_not_only_the_first():
    text = HEADER + row("a-01", "nearly", "open") + row("a-02", "verified", "open")
    assert [f.row_id for f in faults(text)] == ["a-01", "a-02"]


def test_bold_and_a_trailing_date_are_stripped_before_judging():
    text = HEADER + row("a-01", "**fixed 2026-08-23**", "fixed; bugs/a-01.md")
    assert faults(text) == []


def test_an_arrow_target_is_stripped_before_judging():
    text = HEADER + row("a-01", "**promoted -> 421e**", "promoted")
    assert faults(text) == []


def test_notes_with_no_status_word_are_not_a_disagreement():
    text = HEADER + row("a-01", "open", "production watcher; bugs/a-01.md")
    assert faults(text) == []


def test_a_table_with_no_status_column_is_skipped():
    text = (
        "| id | what | audience | severity | owner-notes |\n"
        "|---|---|---|---|---|\n"
        "| a-01 | something | operator | medium | open; bugs/a-01.md |\n"
    )
    assert faults(text) == []


def test_prose_outside_a_table_is_ignored():
    text = "- `a-01` - `operator` at `low`. **A sentence.** verified open\n"
    assert faults(text) == []


def test_a_separator_row_is_not_graded():
    text = HEADER
    assert faults(text) == []


def test_an_empty_status_cell_is_a_fault():
    text = HEADER + row("a-01", "", "open")
    found = faults(text)
    assert len(found) == 1
    assert "empty" in found[0].reason


def test_the_live_register_is_readable_and_the_check_runs_over_it():
    path = ("/home/user/project/.scratch/example-feature/"
            "register.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        mod.faults(fh.read())  # must not raise on the real corpus


def test_an_escaped_pipe_inside_a_cell_does_not_shift_the_columns():
    # Measured on the live register 2026-09-06: row `h0903-03` carries
    # `2026 \| 4` inside inline code, and a naive split read its audience cell
    # as the status.
    text = (
        HEADER
        + "| h0903-03 | a claim about `2026 \\| 4` serials | agent | low | "
          "candidate | harden pass; bugs/h0903-03.md |\n"
    )
    assert faults(text) == []


def test_a_history_spelling_is_accepted_and_says_so_in_the_module():
    for word in mod.HISTORY:
        assert faults(HEADER + row("a-01", word, "")) == []


def test_an_audience_word_in_the_status_cell_is_still_refused():
    # The class that survives accepting the history spellings.
    for word in ("operator", "agent", "tester", "medium", "low"):
        found = faults(HEADER + row("a-01", word, ""))
        assert len(found) == 1, word
