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


ISSUE_HEADER = (
    "Status: needs-harden\n"
    "Direct-road: no\n"
    "Owed: unsorted\n"
    "Origin: 149e/batch-170a59\n"
    "\n"
    "# 561 — the fetch timer charges every read for its own parse\n"
    "\n"
    "Category: performance. Severity: medium. Audience: operator.\n"
)


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
