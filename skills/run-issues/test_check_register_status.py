"""Drill for check_register_status.py.

The corpus is the shape a writer files: a markdown table whose header names a
`status` column and an `owner-notes` column.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The module under test imports `empty_input` from beside it. As a script that
# is sys.path[0]; imported here it is not, unless this says so.
sys.path.insert(0, HERE)
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
    """The offences alone. `mod.faults` returns `(offences, graded)` since the
    empty-input refusal of 2026-09-06; the count has its own cases at the end."""
    return mod.faults(text)[0]


def graded(text):
    return mod.faults(text)[1]


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


# --- The empty-input refusal, ruled by the human 2026-09-06 (ruling 6) -----------
#
# The class: a checker that parses nothing prints the same bytes as a checker
# that passed. `check_commit_order.py` did it six times on run `batch-170a59`.
# Here the vacuous pass was "every status cell reads a legal word" over zero
# cells, and promotion calls this before it resolves a row.

def test_a_clean_table_reports_how_many_rows_it_graded():
    text = HEADER + row("a-01", "candidate", "") + row("a-02", "open", "")
    assert graded(text) == 2


def test_a_file_with_no_status_column_grades_nothing():
    # The denominator that used to be discarded. Same corpus as
    # test_a_table_with_no_status_column_is_skipped, read for its count.
    text = (
        "| id | what | audience |\n"
        "|---|---|---|\n"
        "| a-01 | something | operator |\n"
    )
    assert faults(text) == []
    assert graded(text) == 0


def test_prose_alone_grades_nothing():
    assert graded("# a register\n\nno tables at all.\n") == 0


def test_zero_graded_rows_exits_non_zero_and_names_the_shape(tmp_path, capsys):
    path = tmp_path / "not-a-register.md"
    path.write_text("# a register\n\nno tables at all.\n")
    assert mod.main([str(path)]) == mod.empty_input.EXIT_EMPTY
    err = capsys.readouterr().err
    assert "REFUSED empty-input" in err
    # It NAMES what it could not parse. "no rows" would not do.
    assert "row under a `status` column" in err
    assert "NOT a pass" in err


def test_a_graded_file_still_exits_zero_and_says_the_count(tmp_path, capsys):
    path = tmp_path / "register.md"
    path.write_text(HEADER + row("a-01", "candidate", "") + row("a-02", "fixed", ""))
    assert mod.main([str(path)]) == 0
    assert "2 row(s) graded" in capsys.readouterr().out


def test_a_file_with_faults_is_refused_as_faults_not_as_empty(tmp_path, capsys):
    # Order matters: a file that produced offences is read, so it may never also
    # be called unparseable. Exit 1, not EXIT_EMPTY.
    path = tmp_path / "register.md"
    path.write_text(HEADER + row("a-01", "nearly", ""))
    assert mod.main([str(path)]) == 1
    assert "REFUSED empty-input" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# The sweep completeness check. Ticket 36, rulings 6 and 12.
#
# Ruling 6 puts it HERE rather than in a new script: this file already walks the
# register and grades rows, and a second walker would be the fifth instance of
# the drift tickets 37 and 39 found four times.
#
# Ruling 12 sets the rule. Every row carrying the run's prefixes must be a row
# somebody decided: a status the machine knows, and a note saying why. It runs
# at each issue's commit and again at the finale, and a non-zero exit stops the
# finale before promotion.
# ---------------------------------------------------------------------------

def _write(text):
    """A temp file holding `text`, for the cases that drive `main`."""
    import tempfile
    handle = tempfile.NamedTemporaryFile(
        suffix=".md", delete=False, mode="w", encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


ORIGIN_HEADER = (
    "| id | what | audience | severity | status | origin | owner-notes |\n"
    "|---|---|---|---|---|---|---|\n"
)


def orow(rid, status, origin, notes):
    return (f"| `{rid}` | something is wrong | operator | medium | {status} "
            f"| `{origin}` | {notes} |\n")


def sweep(text, *tokens):
    """The completeness offences alone, for the rows those tokens scope."""
    return mod.sweep_faults(text, tokens)[0]


def swept(text, *tokens):
    """How many rows the sweep found in scope."""
    return mod.sweep_faults(text, tokens)[1]


def told(text, *tokens):
    """How each in-scope row said why."""
    return mod.sweep_faults(text, tokens)[2]


def test_the_sweep_counts_how_each_row_said_why():
    """Returned rather than recomputed. A caller that walked the file again to
    print this would be deciding scope twice, which is the drift this file
    warns about."""
    text = (ORIGIN_HEADER
            + orow("a-01", "open", "1/b", "a stated reason in prose")
            + orow("a-02", "open", "1/b", "open — `bugs/a-02.md`"))
    assert told(text, "b") == {"prose": 1, "citation": 1, "bare": 0, "empty": 0}


def test_a_row_with_an_empty_status_is_reported_once_not_twice():
    """It offends both graders. Printing it twice makes one repair look like
    two, and this file exists so that one pass repairs a whole file."""
    text = ORIGIN_HEADER + orow("a-01", "", "1/batch-207704", "a reason")
    assert mod.main([_write(text), "--sweep", "batch-207704"]) == 1


def test_the_sweep_scopes_by_the_run_named_in_the_origin_cell():
    text = (ORIGIN_HEADER
            + orow("rg436-01", "open", "436/batch-207704", "open — the bug file")
            + orow("rg149e-01", "open", "149e/batch-170a59", "open — the bug file"))
    assert swept(text, "batch-207704") == 1
    assert swept(text, "batch-170a59") == 1
    assert swept(text, "batch-999999") == 0


def test_the_sweep_scopes_by_the_issue_named_in_the_origin_cell():
    """At an issue's commit the runner names the issue, not the run."""
    text = (ORIGIN_HEADER
            + orow("rg436-01", "open", "436/batch-207704", "open — the bug file")
            + orow("rg443-01", "open", "443/batch-207704", "open — the bug file"))
    assert swept(text, "436") == 1


def test_the_sweep_reaches_the_issue_inside_a_row_id():
    """The row-id grammar is `<role><issue>-<n>`, so an issue token is not the
    front of the id. Without this, `--sweep 436` reaches `rg436-01` only
    through the `origin` cell, and a shard written before that column landed
    would grade nothing while looking like a pass."""
    text = (HEADER + row("rg436-01", "open", "")
            + row("vg149g-01", "open", "")
            + row("df-551", "open", ""))
    assert swept(text, "436") == 1
    assert swept(text, "149g") == 1
    assert swept(text, "551") == 1


def test_a_longer_issue_number_is_not_matched_by_a_shorter_one():
    """`436` must not reach `rg4361-01`. The match is bounded on both sides."""
    text = HEADER + row("rg4361-01", "open", "")
    assert swept(text, "436") == 0


def test_the_sweep_scopes_by_a_row_id_prefix_too():
    """A row filed before the origin column landed still answers to its id."""
    text = (ORIGIN_HEADER
            + orow("im557b-01", "open", "unknown", "open — the bug file"))
    assert swept(text, "im557b") == 1


def test_a_row_with_an_empty_note_is_refused():
    """The fault this exists for. Run `batch-170a59` left `vg149g-01` and
    `vg149g-02` reading `open` with nothing at all in owner-notes, and nothing
    said so. Promotion reads the status cell and would mint an issue each."""
    text = ORIGIN_HEADER + orow("vg149g-01", "open", "149g/batch-170a59", "")
    found = sweep(text, "batch-170a59")
    assert len(found) == 1
    assert found[0].row_id == "vg149g-01"
    assert "nothing" in found[0].reason


def test_a_note_repeating_only_the_status_word_is_refused():
    """`open` in the status cell and `open` in the notes says nothing twice."""
    text = ORIGIN_HEADER + orow("rg500-01", "open", "500/batch-207704", "open")
    found = sweep(text, "batch-207704")
    assert len(found) == 1
    assert "nothing" in found[0].reason


def test_a_stated_reason_passes_and_that_is_deliberate():
    """Ruling 12 names these: `batch-170a59` left two rows `open` with stated
    reasons and they pass. Quoted from `rf170a59-01` and `rv149f-01`."""
    text = (ORIGIN_HEADER
            + orow("rf170a59-01", "open", "unknown/batch-170a59",
                   "From the coherence finale of run `batch-170a59`. **Driven, "
                   "not read.** The read pointed at a relation that does not exist.")
            + orow("rv149f-01", "open", "149f/batch-170a59",
                   "From issue 149f's review gate. NOT a rejection ground and "
                   "the placement is defensible."))
    assert sweep(text, "batch-170a59") == []


def test_a_citation_is_a_legal_way_to_say_why():
    """Ruling 13: a file and line, a queue item or a register row id, each
    resolvable by a script. A bug file states the reason in full, so a row
    pointing at one has said why. Measured: 29 of `batch-207704`'s 45 rows read
    this way and that run's promotion resolved all 53."""
    text = ORIGIN_HEADER + orow(
        "rg436-01", "open", "436/batch-207704",
        "open — `.scratch/example-feature/bugs/rg436-01.md`")
    assert sweep(text, "batch-207704") == []


def test_a_terminal_row_saying_nothing_is_refused():
    """A row claiming closure owes the commit or the reason ruling 12 names."""
    text = ORIGIN_HEADER + orow("rg500-02", "verified", "500/batch-207704", "")
    found = sweep(text, "batch-207704")
    assert len(found) == 1
    assert found[0].row_id == "rg500-02"


def test_a_terminal_row_naming_its_commit_passes():
    text = ORIGIN_HEADER + orow(
        "rg561-01", "verified", "561/batch-207704",
        "CLOSED by attempt 2 in commit `92736f85`.")
    assert sweep(text, "batch-207704") == []


def test_a_terminal_row_naming_a_reason_and_no_commit_passes():
    """Measured before this was built: four of the five terminal rows in scope
    on the live register carry NO commit sha. `rg571-01` reads
    `blocks-attempt-1 — <bug file>`. A sha rule would refuse four of five real,
    correct rows and stop the finale, so what is required is that the writer
    said something, not that a sha is present."""
    text = ORIGIN_HEADER + orow(
        "rg571-01", "verified", "571/batch-207704",
        "blocks-attempt-1 — `.scratch/example-feature/bugs/rg571-01.md`")
    assert sweep(text, "batch-207704") == []


def test_an_empty_status_cell_is_refused():
    text = ORIGIN_HEADER + orow("rg500-03", "", "500/batch-207704", "a reason")
    assert len(sweep(text, "batch-207704")) == 1


def test_refused_is_a_status_the_machine_knows():
    """Ruling 12 names it a terminal reading, and `parallel-hunt/SKILL.md`
    carries it under "Three exits bound the register": "a refusal takes a row
    out and leaves it". The shape check must not refuse what the sweep requires.
    """
    text = ORIGIN_HEADER + orow(
        "rg500-04", "refused", "500/batch-207704", "out of scope for 500")
    assert faults(text) == []
    assert sweep(text, "batch-207704") == []


def test_rows_out_of_scope_are_never_graded_by_the_sweep():
    """Ruling 7's rule, copied: nothing backfills. The register holds rounds
    back to `b01` and a sweep that refused them would report hundreds of faults
    nobody can act on."""
    text = (ORIGIN_HEADER
            + orow("rg436-01", "open", "436/batch-207704", "")
            + orow("old-01", "open", "12/bridge-cse", ""))
    found = sweep(text, "batch-207704")
    assert [f.row_id for f in found] == ["rg436-01"]


def test_a_table_with_no_origin_column_is_scoped_by_id_alone():
    text = HEADER + row("rg436-01", "open", "")
    assert swept(text, "batch-207704") == 0
    assert swept(text, "rg436") == 1


def test_no_rows_in_scope_is_legal_and_not_a_refusal():
    """An issue whose gates filed nothing sweeps zero rows. That is a fact, and
    a check that refused it would stop every clean commit."""
    text = ORIGIN_HEADER + orow("rg436-01", "open", "436/batch-207704", "a reason")
    assert sweep(text, "555") == []
    assert swept(text, "555") == 0


def test_the_sweep_prints_every_offence_not_the_first():
    """Copied from the shape check beside it, on the ruling of 2026-09-04: one
    pass repairs a whole file."""
    text = (ORIGIN_HEADER
            + orow("a-01", "open", "1/batch-207704", "")
            + orow("a-02", "open", "1/batch-207704", "")
            + orow("a-03", "open", "1/batch-207704", ""))
    assert len(sweep(text, "batch-207704")) == 3


def test_the_sweep_never_judges_whether_a_status_is_true():
    """The limit this file already states for the shape check holds here too. A
    row saying `verified` on a defect that still reproduces passes, because
    nothing in the file can tell."""
    text = ORIGIN_HEADER + orow(
        "rg500-05", "verified", "500/batch-207704", "fixed in commit `abc1234`")
    assert sweep(text, "batch-207704") == []


def test_the_scoped_entry_point_grades_shape_as_well_as_completeness():
    """The fault the session verifying ticket 36 drove: a row reading
    `verified` with owner-notes `open` -- the transposition of run
    `batch-b5e96d` -- passed the sweep gate hook, because the hook called
    `sweep_faults` alone and `--sweep` on the same file refused it."""
    text = ORIGIN_HEADER + orow("rg436-01", "verified", "436/batch-207704", "open")
    assert sweep(text, "436") == []
    found, swept_count, _ = mod.scoped_faults(text, ("436",))
    assert swept_count == 1
    assert [f.row_id for f in found] == ["rg436-01"]
    assert "transposition" in found[0].reason


def test_the_scoped_entry_point_never_grades_a_row_out_of_scope():
    text = ORIGIN_HEADER + orow("rg443-01", "verified", "443/batch-207704", "open")
    found, swept_count, _ = mod.scoped_faults(text, ("436",))
    assert found == [] and swept_count == 0


def test_the_scoped_entry_point_reports_one_fault_per_row():
    """An empty status cell offends both graders; `main` already prints it
    once, and this entry point copies that rule rather than the caller."""
    text = ORIGIN_HEADER + orow("rg436-01", "", "436/batch-207704", "")
    found, _, _ = mod.scoped_faults(text, ("436",))
    assert len(found) == 1


def test_a_fault_says_whether_its_table_declares_an_origin_column():
    """`vg149g.md` holds two undecided rows in a table with no `origin`
    column, and `origin-row-guard.py` refuses every Edit and Write to such a
    table. A caller told to "repair those cells" is deadlocked unless it is
    also told to add the column, so the fault carries the fact."""
    without = HEADER + row("vg149g-01", "open", "")
    found, _, _ = mod.scoped_faults(without, ("149g",))
    assert [f.has_origin for f in found] == [False]
    with_column = ORIGIN_HEADER + orow("vg149g-01", "open", "149g/batch-170a59", "")
    found, _, _ = mod.scoped_faults(with_column, ("149g",))
    assert [f.has_origin for f in found] == [True]
    assert mod.Fault("x", "y", 1).has_origin is True   # an older caller's shape


def test_the_row_reader_tells_a_missing_origin_column_from_an_empty_cell():
    assert [r.origin for r in mod.rows(HEADER + row("a-01", "open", "x"))] == [None]
    assert [r.origin for r in mod.rows(ORIGIN_HEADER + orow("a-01", "open", "", "x"))] == ["``"]


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
