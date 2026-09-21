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


def test_a_status_word_at_the_END_of_the_notes_is_caught_too():
    # The measured fault of run batch-26c495, 2026-09-17: 28 rows carried
    # `verified` in the status cell and ENDED their owner-notes with the bare
    # word `open`. Reading the opening word alone passed all 28. Promotion's
    # `fixed` exit deletes a row, so resolving them would have destroyed 28
    # possibly live defects with no record anywhere.
    text = HEADER + row(
        "rv06b-01",
        "verified",
        "the fix landed in the commit the gate was reading, so this is open")
    found = faults(text)
    assert len(found) == 1
    assert found[0].row_id == "rv06b-01"
    assert "verified" in found[0].reason and "open" in found[0].reason
    assert "ends with" in found[0].reason


def test_a_notes_cell_ending_in_its_OWN_status_word_still_passes():
    # The agreeing case must stay legal, or every well-formed row refuses.
    text = HEADER + row("a-07", "fixed", "the route now refuses an empty body; fixed")
    assert faults(text) == []


def test_a_one_word_notes_cell_reads_the_same_from_both_ends():
    # `open` is one token, so head and tail are the same word. A status cell of
    # `open` agrees with both and there is nothing to refuse.
    text = HEADER + row("a-08", "open", "open")
    assert faults(text) == []


def test_prose_ending_in_an_ordinary_word_is_not_read_as_a_status():
    # Only the status vocabulary counts, so a note ending in an English word
    # that is not a status must pass.
    text = HEADER + row("a-09", "open", "nobody has finished reading")
    assert faults(text) == []


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
    # `unplaced` joined the four on 2026-09-21: a row whose table declares no
    # `owner-notes` column said nothing in a cell that was never there, and
    # counting it as `empty` was the false reading itself.
    assert told(text, "b") == {"prose": 1, "citation": 1, "bare": 0,
                               "empty": 0, "unplaced": 0}


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


def test_fixed_with_only_a_citation_is_refused():
    """TIGHTEN, ruled by the human in the daily-brief walk of 2026-09-08, item 2.
    A row claiming the work is done states the reason where the claim is, so a
    reader deciding whether to promote it never has to open a second file."""
    text = ORIGIN_HEADER + orow(
        "rg436-01", "fixed", "436/batch-207704",
        "fixed — `.scratch/example-feature/bugs/rg436-01.md`")
    found = sweep(text, "batch-207704")
    assert len(found) == 1
    assert "rg436-01" == found[0].row_id


def test_verified_with_only_a_citation_is_refused():
    text = ORIGIN_HEADER + orow(
        "rg436-01", "verified", "436/batch-207704",
        "verified · `bugs/rg436-01.md`")
    assert len(sweep(text, "batch-207704")) == 1


def test_open_with_only_a_citation_stays_legal():
    """The ruled width. The human tightened `fixed` and `verified` ONLY, and left
    `open` with a bug-file citation legal. Measured across every register shard
    on 2026-09-09: 37 citation-only rows, every one of them `open`, so this
    tightening refuses nothing that is on disk today."""
    text = ORIGIN_HEADER + orow(
        "rg436-01", "open", "436/batch-207704",
        "open — `.scratch/example-feature/bugs/rg436-01.md`")
    assert sweep(text, "batch-207704") == []


def test_the_other_four_terminal_words_keep_their_citation():
    """`TERMINAL` holds six words. The ruling named two. Recording a decision at
    the width it was stated is the human's own rule, so the other four are untouched
    and this pins that rather than leaving it to be inferred."""
    for status in ("refused", "retracted", "promoted", "closed"):
        text = ORIGIN_HEADER + orow(
            "rg436-01", status, "436/batch-207704",
            f"{status} — `bugs/rg436-01.md`")
        assert sweep(text, "batch-207704") == [], status


def test_fixed_with_prose_beside_the_citation_is_legal():
    """The rule is about a note that says nothing but a path. A sentence and a
    citation is the shape it asks for, not a shape it refuses."""
    text = ORIGIN_HEADER + orow(
        "rg436-01", "fixed", "436/batch-207704",
        "fixed at `a1b2c3d`, the null guard landed — `bugs/rg436-01.md`")
    assert sweep(text, "batch-207704") == []


def test_the_refused_terminal_citation_still_counts_as_a_citation():
    """`told` reports the rate, and a refusal must not move a row into another
    bucket: the count is how the next reader judges whether the rule was worth
    it."""
    text = ORIGIN_HEADER + orow(
        "rg436-01", "fixed", "436/batch-207704",
        "fixed — `bugs/rg436-01.md`")
    assert told(text, "batch-207704")["citation"] == 1


def test_the_refusal_names_what_the_row_owes():
    text = ORIGIN_HEADER + orow(
        "rg436-01", "fixed", "436/batch-207704",
        "fixed — `bugs/rg436-01.md`")
    said = sweep(text, "batch-207704")[0].reason
    assert "fixed" in said
    assert "commit" in said or "reason" in said


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


# ---------------------------------------------------------------------------
# NAME THE COLUMN YOU COULD NOT FIND. The human ruled it on 2026-09-21.
#
# The reader looked for `owner-notes`, did not find it, put "" in the cell and
# carried on. MEASURED 2026-09-21 on a throwaway shard whose last column read
# `Owner notes`: without `--sweep` it exited 0 over a row whose note ended in
# the bare word `open` against a status of `verified`, printing "every status
# cell ... agreeing with its own owner-notes" having compared nothing; with
# `--sweep` it refused and blamed the ROW, "owner-notes is empty", so the
# writer rewrites a note that was already right.
#
# Five shards of run `batch-246a7d` hit it, the fifth after the runner had
# written the habit into the ledger's Carry-forward. It is live beyond the
# throwaway too: two gate shards, `v11.md` and `v21.md`, head their tables
# `... | status | issue/run | note |`, and on 2026-09-21 the checker graded 25
# of their rows without reading one note.
#
# IT DOES NOT LEARN A SECOND SPELLING. The human refused that in the ruling
# itself: a reader that takes both hides the misspelling from the writer who
# typed it.
# ---------------------------------------------------------------------------

MISSPELT_HEADER = (
    "| id | origin | severity | status | Owner notes |\n"
    "|---|---|---|---|---|\n"
)


def mrow(rid, status, notes, origin="09/batch-246a7d"):
    return f"| `{rid}` | {origin} | medium | {status} | {notes} |\n"


# The shard of the ruling, byte for byte in shape: one row whose note ends in
# the bare word `open` while the status cell reads `verified`.
MEASURED = MISSPELT_HEADER + mrow(
    "rgzz9-01", "verified",
    "the fix landed, but the gate still reads open")


def test_the_measured_shard_is_refused_rather_than_passed_silently():
    """Fault 1 of the ruling. This exited 0 on 2026-09-21."""
    found = faults(MEASURED)
    assert len(found) == 1
    assert found[0].line == 1          # the header, not the row


def test_the_refusal_names_the_column_it_looked_for():
    reason = faults(MEASURED)[0].reason
    assert "owner-notes" in reason


def test_the_refusal_prints_the_header_as_the_writer_typed_it():
    """Naming `owner-notes` alone leaves the writer hunting. The header is
    quoted back, so `Owner notes` is visible sitting in it."""
    assert "Owner notes" in faults(MEASURED)[0].reason


def test_the_sweep_does_not_blame_the_row_for_a_column_the_header_never_had():
    """Fault 2 of the ruling. The note was already right; only the header was
    wrong, and no rewriting of any cell could have cleared it."""
    found, _, _ = mod.scoped_faults(MEASURED, ("batch-246a7d",))
    assert len(found) == 1
    assert "is empty" not in found[0].reason
    assert "says nothing about why" not in found[0].reason


def test_a_second_spelling_is_not_quietly_accepted():
    """The fix the ruling refused. `Owner notes` must not work as a synonym, or
    the misspelling survives and nobody ever learns of it."""
    text = MISSPELT_HEADER + mrow("a-01", "open", "open; a stated reason")
    assert faults(text) != []


def test_a_missing_id_column_is_named_the_same_way():
    """The reader's other silent fallback: no `id` column and it reads column
    zero. Measured 2026-09-21 across every register and shard on disk, two
    header rows declare `status` with no `id`, both of the promotion-summary
    shape `row | issue | audience/severity | status`, and the only one carrying
    data rows is already refused today on its `parked` status words."""
    text = (
        "| row | issue | audience/severity | status |\n"
        "|---|---|---|---|\n"
        "| rn-7f5b53-01 | 156 | operator/medium | open |\n"
    )
    found = faults(text)
    assert len(found) == 1
    assert "`id`" in found[0].reason


def test_both_missing_columns_are_named_in_one_offence():
    text = (
        "| row | issue | audience/severity | status |\n"
        "|---|---|---|---|\n"
        "| rn-7f5b53-01 | 156 | operator/medium | open |\n"
    )
    reason = faults(text)[0].reason
    assert "`id`" in reason and "`owner-notes`" in reason


def test_one_offence_per_table_never_one_per_row():
    """The repair is one header edit. Thirteen copies of it make one repair
    look like thirteen, which is the rule this file already applies when a row
    offends both graders. One live shard printed thirteen on 2026-09-21."""
    text = MISSPELT_HEADER + "".join(
        mrow(f"a-{n:02d}", "open", "a stated reason") for n in range(13))
    assert len(faults(text)) == 1


def test_two_bad_tables_in_one_file_are_two_offences():
    """One per table, so a file with two of them is repaired in one pass."""
    text = MEASURED + "\nsome prose between the tables\n\n" + MISSPELT_HEADER + mrow(
        "b-01", "open", "a stated reason")
    assert len(faults(text)) == 2


def test_a_bad_header_over_no_rows_is_not_an_offence():
    """Measured 2026-09-21: ten header rows on disk declare `status` with no
    `owner-notes`, and every one of them heads an EMPTY table -- a gate's
    finding table filed with nothing in it. Refusing those would red the
    register and four shards for nothing. The reader refuses a column it could
    not place for a row it is grading, not a header in the abstract."""
    assert faults(MISSPELT_HEADER) == []
    assert graded(MISSPELT_HEADER) == 0


def test_the_status_word_is_still_graded_under_a_bad_header():
    """The `status` column WAS placed, so the rule that reads it still runs.
    Only the rules reading the column that was not placed go quiet."""
    found = faults(MISSPELT_HEADER + mrow("a-01", "nearly", "a reason"))
    assert len(found) == 2
    assert any("nearly" in f.reason for f in found)


def test_no_rule_that_reads_the_note_runs_when_the_note_was_never_placed():
    """The transposition rule reads both cells. Under a header it could not
    place it must be silent, or it fires a reason that cannot be true."""
    found = faults(MEASURED)
    assert not any("transposition" in f.reason for f in found)


def test_a_row_under_a_bad_header_still_counts_as_graded():
    """The denominator the empty-input refusal reads. These rows were read;
    calling the file unparseable on top of naming its header would be a second,
    wrong reason for one fault."""
    assert graded(MEASURED) == 1


def test_the_row_reader_tells_an_unplaced_note_column_from_an_empty_cell():
    """`None` and `""` are different repairs, exactly as they already are for
    `origin`: an empty cell is filled, a missing column is renamed."""
    assert [r.notes for r in mod.rows(MEASURED)] == [None]
    assert [r.notes for r in mod.rows(HEADER + row("a-01", "open", ""))] == [""]


def test_the_header_fault_says_whether_its_table_declares_an_origin_column():
    """The hook names the two-step road off `has_origin`, because
    `origin-row-guard.py` refuses every write to a table without the column.
    A header fault carries the fact for the same reason a row fault does."""
    assert faults(MEASURED)[0].has_origin is True
    without = (
        "| id | severity | status | Owner notes |\n"
        "|---|---|---|---|\n"
        "| `a-01` | medium | open | a reason |\n"
    )
    assert faults(without)[0].has_origin is False


def test_an_origin_column_is_still_optional():
    """`HEADER`, this drill's own corpus, declares none, and `vg149g.md` holds
    live rows in a table that predates the column. Its absence is a designed
    state carried by `has_origin`, not a column the reader could not place."""
    assert faults(HEADER + row("a-01", "open", "a stated reason")) == []


def test_the_live_gate_shard_shape_is_refused_once(tmp_path, capsys):
    """The live gate shard that graded 25 rows without reading one note:
    `note` for `owner-notes` and `issue/run` for `origin`. One offence, naming
    `owner-notes`, and none of the thirteen false row refusals it printed under
    `--sweep` on 2026-09-21."""
    text = (
        "| id | finding | owner | severity | status | issue/run | note |\n"
        "|---|---|---|---|---|---|---|\n"
        "| rc11-1 | a 10 MB download inside the transaction | operator | high "
        "| open | 11/batch-d41839 | ground 1 |\n"
        "| rc11-2 | the exemption is file-scoped | operator | medium "
        "| open | 11/batch-d41839 | ground 2 |\n"
    )
    path = tmp_path / "v11.md"
    path.write_text(text)
    assert mod.main([str(path), "--sweep", "11"]) == 1
    out = capsys.readouterr().out
    assert out.count("owner-notes` column") == 1
    assert "is empty, so the row says nothing about why" not in out


def test_the_pass_sentence_cannot_be_printed_over_an_unplaced_note_column(
        tmp_path, capsys):
    """The sentence claims every status cell agrees with its own owner-notes.
    It is now true by construction: a file holding a row whose note cell the
    reader never found exits 1 before it is reached."""
    path = tmp_path / "shard.md"
    path.write_text(MEASURED)
    assert mod.main([str(path)]) == 1
    assert "agreeing with its own owner-notes" not in capsys.readouterr().out


def test_a_clean_file_still_says_the_sentence(tmp_path, capsys):
    """The control. A guard driven only on what it must refuse is a guard that
    could be refusing everything."""
    path = tmp_path / "shard.md"
    path.write_text(ORIGIN_HEADER
                    + orow("a-01", "open", "1/batch-246a7d", "a stated reason"))
    assert mod.main([str(path)]) == 0
    assert "agreeing with its own owner-notes" in capsys.readouterr().out


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
