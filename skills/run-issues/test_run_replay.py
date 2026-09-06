#!/usr/bin/env python3
"""Cases for run_replay.py — ticket 37, ruling 16's one-time replay.

    python3 -m unittest test_run_replay

Ruling 16 asks for "a one-time replay over the seven finale runs' transcripts
to backfill the new fields, so the first trend reads on the day the build
lands". Every figure sittings 2, 3 and 4 built reads `not measured` on today's
record, so until this runs `run_compare.py` reports nothing and the whole
reader is unproven against real figures.

**`runs.jsonl` is append-only and `run_records.append_run` refuses a second
line for a batch already present.** So the replay cannot append beside a line;
it must REWRITE it in place. Two things stop a half-finished replay leaving a
line part-filled, and both are pinned below:

  1. **Per line, all or nothing.** A line's replacement record is built whole
     in memory and validated through the appender's own rules before anything
     is written. A line the replay could not measure is left byte for byte as
     it was.
  2. **Per file, all or nothing.** The whole file is rendered and written to a
     temporary file in the same directory, then moved over the original with
     `os.replace`, which is atomic on one filesystem. A reader opening the
     file mid-replay sees the old file or the new one, never a truncated one.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

import run_records
import run_replay as tool


def a_line(batch, **fields):
    found = {"batch": batch, "kind": "run", "taken": "2026-09-01",
             "version": "not stated"}
    found.update(fields)
    return json.dumps(found, sort_keys=True)


class TheRewriteIsAllOrNothing(unittest.TestCase):
    """`runs.jsonl` is append-only with a duplicate refusal, so the replay's
    only road is to render the whole file and move it into place."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.path = self.dir / "runs.jsonl"

    def write(self, *lines):
        self.path.write_text("".join(one + "\n" for one in lines),
                             encoding="utf-8")

    def test_a_named_line_is_replaced_and_its_neighbours_are_untouched(self):
        first, second, third = (a_line("a"), a_line("b"), a_line("c"))
        self.write(first, second, third)
        ok, said = tool.rewrite(self.path, {"b": {"batch": "b", "kind": "run",
                                                  "hours": 9.0}})
        self.assertTrue(ok, said)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(first, lines[0])
        self.assertEqual(third, lines[2])
        self.assertEqual(9.0, json.loads(lines[1])["hours"])

    def test_a_line_that_is_not_json_survives_word_for_word(self):
        """Ruling 3: no existing history may be lost. `run_records.read_lines`
        hands a caller only the records that parsed, and rendering the file
        from those alone would silently delete every line that did not."""
        rubbish = "this line is not JSON and never was"
        self.write(a_line("a"), rubbish, a_line("b"))
        ok, _ = tool.rewrite(self.path, {"a": {"batch": "a", "kind": "run"}})
        self.assertTrue(ok)
        self.assertIn(rubbish, self.path.read_text(encoding="utf-8"))

    def test_a_batch_the_file_does_not_hold_refuses_and_writes_nothing(self):
        """A replay that quietly skipped a line it was asked to fill would
        report success over a line still reading `not measured`."""
        self.write(a_line("a"))
        original = self.path.read_text(encoding="utf-8")
        ok, said = tool.rewrite(self.path,
                                {"zzz": {"batch": "zzz", "kind": "run"}})
        self.assertFalse(ok)
        self.assertIn("zzz", said)
        self.assertEqual(original, self.path.read_text(encoding="utf-8"))

    def test_two_lines_for_one_batch_refuse_rather_than_pick_one(self):
        """Ticket 36's fault 9 put two `review-375cbf` rows in the source
        table. Ruling 4 refuses a second at the finale, but a file corrected by
        hand can still hold one, and rewriting only the first would leave the
        second reading the old figures under the same key."""
        self.write(a_line("a"), a_line("a"))
        original = self.path.read_text(encoding="utf-8")
        ok, said = tool.rewrite(self.path,
                                {"a": {"batch": "a", "kind": "run"}})
        self.assertFalse(ok)
        self.assertIn("twice", said.lower())
        self.assertEqual(original, self.path.read_text(encoding="utf-8"))

    def test_a_record_the_appender_would_refuse_is_refused_here_too(self):
        """The replay writes through the same rules a finale writes through.
        `run_records.append_run` refuses a note over 160 characters, a version
        that is not a version, and a count with no denominator beside it; a
        road that walked round them would let the replay put into the file
        exactly what the finale is stopped from putting in."""
        self.write(a_line("a"))
        original = self.path.read_text(encoding="utf-8")
        ok, said = tool.rewrite(self.path, {"a": {
            "batch": "a", "kind": "run", "version": "claude-opus-5"}})
        self.assertFalse(ok)
        self.assertIn("version", said.lower())
        self.assertEqual(original, self.path.read_text(encoding="utf-8"))

    def test_nothing_is_written_when_any_one_line_is_refused(self):
        """Per file, all or nothing. Two good replacements and one bad one
        leave the file exactly as it was, so a replay is never half done."""
        self.write(a_line("a"), a_line("b"), a_line("c"))
        original = self.path.read_text(encoding="utf-8")
        ok, _ = tool.rewrite(self.path, {
            "a": {"batch": "a", "kind": "run", "hours": 1.0},
            "b": {"batch": "b", "kind": "run", "hours": 2.0},
            "c": {"batch": "c", "kind": "run", "version": "not-a-version"}})
        self.assertFalse(ok)
        self.assertEqual(original, self.path.read_text(encoding="utf-8"))

    def test_the_file_is_moved_into_place_rather_than_truncated(self):
        """`open(path, "w")` empties the file before the first byte is
        written, so a reader between those two moments sees an empty record
        and a crash there leaves one. The replacement is written beside it and
        moved over it, which is atomic on one filesystem."""
        self.write(a_line("a"))
        seen = []
        real = os.replace

        def watched(source, target):
            seen.append((pathlib.Path(source).parent,
                         pathlib.Path(target).parent))
            return real(source, target)

        os.replace = watched
        try:
            tool.rewrite(self.path, {"a": {"batch": "a", "kind": "run"}})
        finally:
            os.replace = real
        self.assertEqual(1, len(seen))
        self.assertEqual(seen[0][0], seen[0][1],
                         "the temporary file must sit in the same directory, "
                         "or the move crosses a filesystem and is a copy")

    def test_running_it_twice_leaves_the_same_file(self):
        """A one-time replay that no second hand dares repeat is one nobody
        can re-run after a partial failure."""
        self.write(a_line("a"), a_line("b"))
        record = {"batch": "a", "kind": "run", "hours": 3.0}
        tool.rewrite(self.path, {"a": dict(record)})
        once = self.path.read_text(encoding="utf-8")
        tool.rewrite(self.path, {"a": dict(record)})
        self.assertEqual(once, self.path.read_text(encoding="utf-8"))

    def test_an_absent_file_refuses_rather_than_creating_one(self):
        """A replay pointed at the wrong repository would otherwise mint an
        empty record file there and report that it had rewritten nothing."""
        ok, said = tool.rewrite(self.dir / "nothing.jsonl",
                                {"a": {"batch": "a", "kind": "run"}})
        self.assertFalse(ok)
        self.assertFalse((self.dir / "nothing.jsonl").exists(), said)


if __name__ == "__main__":
    unittest.main()


class WhatTheReplayMayWriteOntoALine(unittest.TestCase):
    """The human ruled the reach at the keyboard on 2026-09-06, after the delta
    was measured: the replay backfills the new fields AND repairs the five
    cells sitting 2 marked `borrowed`, dropping the mark.

    `Per issue` is the figure that settled it. Across the five marked lines it
    is stored at 1.34M to 1.87M and measures at 4.29M to 9.98M -- wrong by a
    factor of three to six on every one. Ruling 3 is met by git: the record
    file is committed, so every replaced cell stays readable for ever.
    """

    def old(self, **fields):
        found = {"batch": "b", "kind": "run", "taken": "2026-09-02",
                 "version": "not stated", "carried": True,
                 "note": "a note from the day",
                 "borrowed": ["issues", "subagents", "weighted",
                              "orchestrator", "per_issue"],
                 "issues": 8, "subagents": 73,
                 "weighted": {"not stated": 125900000.0},
                 "quality": {"issues_graded": None}}
        found.update(fields)
        return found

    def new(self, **fields):
        found = {"batch": "b", "kind": "run", "taken": "2026-09-06",
                 "version": "2.1.261", "note": "",
                 "issues": 16, "subagents": 74,
                 "weighted": {"opus": 103100000.0},
                 "quality": {"issues_graded": 16, "strikes": 3},
                 "trial": {"state": "unmeasured", "spawns": 0, "proved": 0,
                           "mismatches": 0}}
        found.update(fields)
        return found

    def test_the_day_the_run_finished_survives(self):
        """`build_record` stamps `taken` with `date.today()`, so taking it
        would move every replayed line to the day of the replay -- and ruling
        12 orders lines by it. Seven runs would all read 2026-09-06 and the
        trend would be one point."""
        self.assertEqual("2026-09-02",
                         tool.merged(self.old(), self.new())["taken"])

    def test_the_note_the_line_already_carried_survives(self):
        """Six carried notes run past ruling 15's 160-character cap and hold
        1,293 characters nothing else holds. Sitting 2 settled ruling 3
        against ruling 15 in ruling 3's favour for what already exists."""
        found = tool.merged(self.old(), self.new())
        self.assertEqual("a note from the day", found["note"])
        self.assertTrue(found["carried"])

    def all_five(self, **fields):
        found = self.new(orchestrator={"opus": 0.195},
                         per_issue={"opus": 6440000.0})
        found.update(fields)
        return found

    def test_the_five_repaired_cells_are_taken_and_the_mark_goes(self):
        found = tool.merged(self.old(), self.all_five())
        self.assertEqual(16, found["issues"])
        self.assertEqual(74, found["subagents"])
        self.assertEqual({"opus": 103100000.0}, found["weighted"])
        self.assertNotIn("borrowed", found)

    def test_a_cell_the_replay_could_not_re_measure_stays_marked(self):
        """The mark names WHICH cells came from another run, and sitting 4's
        reader skips a marked line per FIGURE. Dropping the whole mark when
        four of five were repaired would tell that reader the fifth is the
        run's own when it is not."""
        found = tool.merged(self.old(), self.all_five(per_issue=None))
        self.assertEqual(["per_issue"], found["borrowed"])

    def test_the_new_fields_are_taken(self):
        found = tool.merged(self.old(), self.new())
        self.assertEqual(16, found["quality"]["issues_graded"])
        self.assertEqual("unmeasured", found["trial"]["state"])

    def test_a_line_that_was_never_marked_keeps_its_own_figures_repaired(self):
        """`batch-170a59` is the one unmarked line of the eighteen. The
        repair is the same reading either way -- what today's `run_costs.py`
        would have written -- so nothing depends on the mark."""
        found = tool.merged(self.old(borrowed=None), self.new())
        self.assertEqual(16, found["issues"])

    def test_a_figure_the_replay_could_not_measure_leaves_the_old_one(self):
        """A run whose transcript yields no cache reading must not blank the
        cell it already had. `None` means nothing measured it, and writing
        that over a figure is a loss, not a correction."""
        found = tool.merged(self.old(cache={"ratio": 50.0}),
                            self.new(cache=None))
        self.assertEqual({"ratio": 50.0}, found["cache"])


class TheMeasurementProvesItsLedgerBeforeItReadsIt(unittest.TestCase):
    """Slice 5's seam. The fixture is `test_cost_scripts_batch.Fixture`, the
    one the finale's own cases run against, so the replay is measured through
    the same shape a real run leaves behind rather than a second one built
    for it."""

    def setUp(self):
        from test_cost_scripts_batch import Fixture, TWO_SPAWNS
        import run_session
        self.fx = Fixture(spawns=TWO_SPAWNS)
        self.session = run_session
        self.original = run_session.PROJECTS
        run_session.PROJECTS = str(self.fx.projects)

    def tearDown(self):
        self.session.PROJECTS = self.original

    def measure(self, **kw):
        given = {"repo": self.fx.tree, "batch": self.fx.batch,
                 "ledger": self.fx.ledger, "briefing": None}
        given.update(kw)
        return tool.measure(**given)

    def test_a_real_run_yields_every_field_the_finale_would_have_written(self):
        record, why = self.measure()
        self.assertEqual("", why)
        for name in ("quality", "faster", "trial", "longest_steps",
                     "issues", "subagents", "weighted"):
            self.assertIn(name, record, f"{name} is missing")

    def with_a_status_table(self):
        """The shared fixture's ledger carries no status table, and zero issue
        lines from it is the correct answer. A per-issue population needs the
        table whose header declares `issue` -- the bound sitting 3 put on
        `check_commit_order.status_rows` after run `batch-170a59` graded twelve
        rows for six issues."""
        path = self.fx.ledger
        path.write_text(path.read_text(encoding="utf-8") + (
            "\n## Status\n\n"
            "| Issue | Est | Status | Notes |\n"
            "|---|---|---|---|\n"
            "| 545 | 60-90m | done | attempt 1: gates both pass |\n"
            "| 546 | 30-45m | done | attempt 1: gates both pass |\n"),
            encoding="utf-8")
        return path

    def test_the_per_issue_lines_come_back_with_it(self):
        """Ruling 17's second file. They are built ONCE and used by both the
        per-run figures and `issues.jsonl`: `build_record` divides ruling 5's
        figures by this population, so two builds would be one run with two
        populations that agree only by accident."""
        record, why = self.measure(ledger=self.with_a_status_table())
        self.assertEqual("", why)
        self.assertEqual(["545", "546"],
                         [one["issue"] for one in record["issue_lines"]])
        self.assertEqual({self.fx.batch},
                         {one["batch"] for one in record["issue_lines"]})

    def test_the_inside_run_counts_are_read_from_that_table(self):
        """Ruling 6's four counts and their denominator, which sitting 2
        refused to write and sitting 3 filled once the reader was repaired."""
        record, _ = self.measure(ledger=self.with_a_status_table())
        self.assertEqual(2, record["quality"]["issues_graded"])
        self.assertEqual(2, record["quality"]["first_attempt_passes"])

    def test_a_ledger_with_no_worktree_line_refuses_and_says_what_it_wanted(self):
        """The `Worktree:` line is the only road from a batch id to its
        transcripts (ticket 39, ruling 12). Without it nothing says which
        directory's transcripts belong to this run."""
        bare = self.fx.tree / "bare.md"
        bare.write_text("# Run ledger\n\nno worktree line here\n",
                        encoding="utf-8")
        record, why = self.measure(ledger=bare)
        self.assertIsNone(record)
        self.assertIn("Worktree:", why)

    def test_a_transcript_that_never_names_the_batch_is_refused(self):
        """The trap that cost run `batch-88624c` its 2026-08-31 row: a
        directory full of unrelated sessions, one of them picked, 1.01 h
        reported for an 8.4 h run. A figure from a session this could not
        identify looks exactly like a figure from one it could."""
        record, why = self.measure(batch="batch-nobody")
        self.assertIsNone(record)
        self.assertIn("batch-nobody", why)

    def test_an_absent_ledger_refuses_rather_than_measuring_nothing(self):
        record, why = self.measure(ledger=self.fx.tree / "gone.md")
        self.assertIsNone(record)
        self.assertIn("gone.md", why)

    def test_the_measurement_writes_nothing(self):
        """Ruling 22's discipline, carried onto the replay's reading half:
        taking a measurement must not change what is being measured."""
        import hashlib

        def digest():
            found = []
            for path in sorted(self.fx.tree.rglob("*")):
                if path.is_file():
                    found.append(str(path) + hashlib.sha256(
                        path.read_bytes()).hexdigest())
            return found

        before = digest()
        self.measure()
        self.assertEqual(before, digest())


class ThePerIssueFileIsWrittenWholeAndCanBeRerun(unittest.TestCase):
    """`run_records.append_issues` refuses a second write for a batch already
    present, for ruling 4's reason carried onto this file. The replay writes
    six batches at once and must survive being run twice, so it renders the
    whole file the way `rewrite` does rather than appending."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.path = self.dir / "issues.jsonl"

    def rows(self, batch, *issues):
        return [{"batch": batch, "issue": one} for one in issues]

    def test_a_batch_not_in_the_map_keeps_its_lines(self):
        """Another run's per-issue population is not this replay's to touch."""
        self.path.write_text(
            json.dumps({"batch": "other", "issue": "1"}, sort_keys=True) + "\n",
            encoding="utf-8")
        ok, said = tool.rewrite_issues(self.path,
                                       {"a": self.rows("a", "5", "6")})
        self.assertTrue(ok, said)
        found = [json.loads(one) for one in
                 self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(["other", "a", "a"], [one["batch"] for one in found])

    def test_running_it_twice_does_not_double_the_population(self):
        """A run written twice here would double every per-issue population a
        trend reads -- ruling 4's reason, and it is why `append_issues`
        refuses rather than appends."""
        for _ in range(2):
            ok, said = tool.rewrite_issues(self.path,
                                           {"a": self.rows("a", "5", "6")})
            self.assertTrue(ok, said)
        self.assertEqual(
            2, len(self.path.read_text(encoding="utf-8").splitlines()))

    def test_a_row_naming_no_issue_refuses_and_writes_nothing(self):
        """Together with the batch id the issue is this file's key. A row
        without one cannot be read back against the ledger it came from."""
        ok, said = tool.rewrite_issues(self.path,
                                       {"a": [{"batch": "a", "issue": ""}]})
        self.assertFalse(ok)
        self.assertIn("issue", said.lower())
        self.assertFalse(self.path.exists())

    def test_rows_naming_a_different_batch_refuse(self):
        """A caller holding rows for two runs under one key has lost track of
        which run it is measuring."""
        ok, said = tool.rewrite_issues(
            self.path, {"a": [{"batch": "b", "issue": "5"}]})
        self.assertFalse(ok)
        self.assertIn("b", said)
        self.assertFalse(self.path.exists())

    def test_a_line_that_is_not_json_survives(self):
        """Ruling 3 again, on the second file."""
        rubbish = "not JSON"
        self.path.write_text(rubbish + "\n", encoding="utf-8")
        ok, _ = tool.rewrite_issues(self.path, {"a": self.rows("a", "5")})
        self.assertTrue(ok)
        self.assertIn(rubbish, self.path.read_text(encoding="utf-8"))

    def test_it_creates_the_file_when_there_is_none(self):
        """Unlike `runs.jsonl`, this file does not exist yet: the writers
        landed in sitting 3 and no finale has run since."""
        ok, said = tool.rewrite_issues(self.path, {"a": self.rows("a", "5")})
        self.assertTrue(ok, said)
        self.assertTrue(self.path.exists())


class TheSevenLinesRuling16Names(unittest.TestCase):
    """Measured 2026-09-06, not assumed: 11 of the 18 lines on the record
    carry `backfilled: true` and those seven do not."""

    def test_the_table_names_exactly_seven(self):
        self.assertEqual(7, len(tool.SEVEN))
        self.assertEqual(
            {"backfilled-2026-08-30", "batch-88624c", "review-375cbf",
             "batch-45c8b1", "batch-44d0a8", "batch-b5e96d", "batch-170a59"},
            set(tool.SEVEN))

    def test_every_replayable_batch_has_a_briefing_named_beside_its_ledger(self):
        """The briefing carries two of ruling 20's five kind facts -- the
        rail's stage keys and the `## Ruled` section. A ledger named without
        one would read `cut_on_a_default: false` for every issue of that run,
        which is the false `false` sitting 3 found in `ruled_section`."""
        self.assertEqual(set(tool.LEDGERS), set(tool.BRIEFINGS))

    def test_the_unreplayable_line_is_named_rather_than_left_out(self):
        """Reporting six of seven and saying nothing about the seventh is the
        `ok`-on-nothing shape sitting 1 met on the live register."""
        self.assertIn("backfilled-2026-08-30", tool.UNREPLAYABLE)
        self.assertIn("synthetic",
                      tool.UNREPLAYABLE["backfilled-2026-08-30"])

    def test_no_batch_is_both_replayable_and_not(self):
        self.assertEqual(set(),
                         set(tool.LEDGERS) & set(tool.UNREPLAYABLE))


CORPUS = pathlib.Path("/home/user/project")


class TheWholeRecord(unittest.TestCase):
    """Measured against the real record and the real ledgers, never against a
    fixture alone.

    The instruction was earned twice over. Sitting 3 of this ticket shipped
    two false-negative readings that were correct on the runs they were built
    against; sitting 4 of ticket 39 was blind to seven dialects after
    measuring one ledger. Skipped where the corpus is absent, because these
    files are in another repository.
    """

    def setUp(self):
        if not (CORPUS / "runs.jsonl").exists() and not (
                CORPUS / ".scratch" / "workflow-audit" / "runs.jsonl").exists():
            self.skipTest(f"{CORPUS} holds no record")

    def test_every_line_ruling_16_names_is_on_the_record(self):
        """A typed table that names a batch the file does not hold would make
        `rewrite` refuse the whole replay, and the refusal would arrive only
        when somebody ran it."""
        seen = run_records.read_runs(CORPUS)
        on_file = {str(one.get("batch") or "") for one in seen.records}
        for batch in tool.SEVEN:
            with self.subTest(batch=batch):
                self.assertIn(batch, on_file)

    def test_the_eleven_backfilled_lines_are_not_among_the_seven(self):
        """The seven ARE the finale-written lines, measured rather than
        listed: 11 of the 18 carry `backfilled: true` and those seven do
        not."""
        seen = run_records.read_runs(CORPUS)
        marked = {str(one.get("batch") or "") for one in seen.records
                  if one.get("backfilled")}
        self.assertEqual(11, len(marked))
        self.assertEqual(set(), marked & set(tool.SEVEN))
        self.assertEqual(18, len(seen.records))

    def test_every_named_ledger_exists_and_proves_its_own_batch(self):
        """The proof a foreign ledger cannot pass. Measured 2026-09-06:
        `archive-run-batch-44d0a8.md` names `batch-45c8b1` in its own text and
        `runs/batch-170a59/run.md` names `batch-b5e96d`, so a search for "the
        file that mentions this batch" picks the wrong ledger for two of the
        six. This asserts the named one is right, by the transcript."""
        for batch, named in tool.LEDGERS.items():
            with self.subTest(batch=batch):
                path = CORPUS / named
                self.assertTrue(path.is_file(), f"{path} is gone")
                mains, why = tool.sessions_named_by(
                    path.read_text(encoding="utf-8", errors="replace"), batch)
                self.assertEqual("", why)
                self.assertTrue(mains)

    def test_no_named_ledger_is_named_twice(self):
        """Two batches pointed at one file would replay one run's figures onto
        the other's line."""
        self.assertEqual(len(tool.LEDGERS), len(set(tool.LEDGERS.values())))


class TheCommand(unittest.TestCase):
    """`replay` takes the tables so the orchestration can be measured without
    a machine-shaped checkout. The real tables are pinned by `TheWholeRecord`
    above, against the real ledgers and the real record."""

    def setUp(self):
        from test_cost_scripts_batch import Fixture, TWO_SPAWNS
        import run_session
        self.fx = Fixture(spawns=TWO_SPAWNS)
        self.session = run_session
        self.original = run_session.PROJECTS
        run_session.PROJECTS = str(self.fx.projects)
        self.audit = self.fx.tree / ".scratch" / "workflow-audit"
        self.audit.mkdir(parents=True)
        (self.audit / "runs.jsonl").write_text(
            a_line(self.fx.batch, borrowed=["issues"], issues=99) + "\n",
            encoding="utf-8")
        self.ledgers = {self.fx.batch: str(
            self.fx.ledger.relative_to(self.fx.tree))}

    def tearDown(self):
        self.session.PROJECTS = self.original

    def run_it(self, *extra):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--repo", str(self.fx.tree), *extra],
                             ledgers=self.ledgers, briefings={})
        return code, out.getvalue()

    def test_a_dry_run_reports_and_writes_nothing(self):
        before = (self.audit / "runs.jsonl").read_text(encoding="utf-8")
        code, text = self.run_it("--dry-run")
        self.assertEqual(0, code)
        self.assertIn(self.fx.batch, text)
        self.assertEqual(before,
                         (self.audit / "runs.jsonl").read_text(encoding="utf-8"))
        self.assertFalse((self.audit / "issues.jsonl").exists())

    def test_the_real_run_fills_the_line_and_drops_the_mark(self):
        code, text = self.run_it()
        self.assertEqual(0, code, text)
        found = json.loads(
            (self.audit / "runs.jsonl").read_text(encoding="utf-8").strip())
        self.assertNotEqual(99, found["issues"])
        self.assertNotIn("borrowed", found)
        self.assertIn("trial", found)

    def test_the_view_is_regenerated_from_disk_after_the_rewrite(self):
        """The review of 2026-09-06 found `write_view` rendering the caller's
        snapshot, so a page could be published missing the line that had just
        been written. It renders from disk now, and the replay must publish
        AFTER it has rewritten, not before."""
        self.run_it()
        page = (self.audit / "run-costs.md").read_text(encoding="utf-8")
        self.assertIn(self.fx.batch, page)

    def test_every_line_it_could_not_replay_is_named_with_its_reason(self):
        """Six of seven reported and the seventh unmentioned is the
        `ok`-on-nothing shape this ticket has met three times."""
        _, text = self.run_it("--dry-run")
        self.assertIn("backfilled-2026-08-30", text)
        self.assertIn("synthetic", text)

    def test_a_batch_whose_ledger_is_gone_is_reported_and_halts_nothing(self):
        """A measurement never stops a replay from doing what it can. It stops
        the WRITE for that line, which is a different thing."""
        ledgers = dict(self.ledgers, ghost=".scratch/nowhere/run.md")
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["--repo", str(self.fx.tree), "--dry-run"],
                             ledgers=ledgers, briefings={})
        self.assertEqual(0, code)
        self.assertIn("ghost", out.getvalue())
        self.assertIn(self.fx.batch, out.getvalue())


class ALineAgreesWithItself(unittest.TestCase):
    """The fault the first real replay exposed, pinned so it cannot return.

    `faster` is computed from the reading the replay takes. Keeping the
    stored `hours` beside it left `batch-170a59` reading `hours 8.06` against
    `82.6` wall minutes per issue, which is 8.26 h over its six issues. Both
    are `run_timings.py` on one transcript at two moments, and the gap ran up
    to 2.48 per cent across the six lines. One reading, one moment.
    """

    def test_the_hours_cell_and_the_per_issue_figure_are_one_reading(self):
        old = {"batch": "b", "kind": "run", "taken": "2026-09-06",
               "hours": 8.06, "idle": 0.20}
        new = {"batch": "b", "kind": "run", "hours": 8.26, "idle": 0.23,
               "quality": {"issues_graded": 6},
               "faster": {"wall_minutes_per_issue": 82.6}}
        found = tool.merged(old, new)
        self.assertEqual(8.26, found["hours"])
        self.assertEqual(0.23, found["idle"])
        self.assertAlmostEqual(
            found["hours"],
            found["faster"]["wall_minutes_per_issue"]
            * found["quality"]["issues_graded"] / 60, places=2)

    def test_an_unread_clock_leaves_the_one_the_line_had(self):
        """A transcript `run_timings.py` could not read must not blank the
        figure the finale measured. Null is a missing measurement."""
        found = tool.merged({"batch": "b", "kind": "run", "hours": 8.06},
                            {"batch": "b", "kind": "run", "hours": None})
        self.assertEqual(8.06, found["hours"])


class AnEmptyMeasurementIsNotAReading(unittest.TestCase):
    """The `/code-review` pass of 2026-09-06. `merged` took any value that was
    not `None`, and two readers answer "nothing" with an object rather than
    with `None`: `pipeline_fingerprint.as_record` returns `{}` for a ledger
    carrying no header, and `run_costs.quality_counts` returns five keys all
    reading `None` for a ledger carrying no status table.

    Both were written straight over whatever the line already held. It is the
    same fault as the `hours` one this sitting fixed an hour earlier, wearing
    a dict instead of a number: null is not a zero, and empty is not a
    reading."""

    def test_an_empty_fingerprint_leaves_the_one_the_line_had(self):
        old = {"batch": "b", "kind": "run",
               "fingerprint": {"skills": {"head": "abc", "dirty": False}}}
        found = tool.merged(old, {"batch": "b", "kind": "run",
                                  "fingerprint": {}})
        self.assertEqual({"skills": {"head": "abc", "dirty": False}},
                         found["fingerprint"])

    def test_an_all_null_quality_block_leaves_the_counts_the_line_had(self):
        old = {"batch": "b", "kind": "run",
               "quality": {"issues_graded": 9, "strikes": 1}}
        new = {"batch": "b", "kind": "run",
               "quality": {"issues_graded": None, "strikes": None}}
        self.assertEqual({"issues_graded": 9, "strikes": 1},
                         tool.merged(old, new)["quality"])

    def test_a_block_holding_one_real_count_is_still_taken(self):
        """A partly-read block is a reading. Only a block with nothing in it
        at all is silence."""
        old = {"batch": "b", "kind": "run",
               "quality": {"issues_graded": 9, "strikes": 1}}
        new = {"batch": "b", "kind": "run",
               "quality": {"issues_graded": 6, "strikes": None}}
        self.assertEqual(6, tool.merged(old, new)["quality"]["issues_graded"])

    def test_a_measured_zero_is_a_reading_and_is_taken(self):
        """A run with no strikes is a fact. Treating `0` as silence would be
        the null-is-not-a-zero rule inverted."""
        old = {"batch": "b", "kind": "run", "quality": {"strikes": 4}}
        new = {"batch": "b", "kind": "run", "quality": {"strikes": 0}}
        self.assertEqual(0, tool.merged(old, new)["quality"]["strikes"])


class TheTwoFilesAreWrittenTogetherOrNotAtAll(unittest.TestCase):
    """The `/code-review` pass of 2026-09-06, and the sharper half of it.

    `main` wrote `issues.jsonl` and then `runs.jsonl`. A refusal on the second
    left 80 per-issue lines on disk for six runs whose per-run lines still
    read `not measured` -- a replay half applied ACROSS the two files, which
    the per-line and per-file guarantees say nothing about.

    Every write is now validated before the first byte of either file."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.runs = self.dir / "runs.jsonl"
        self.issues = self.dir / "issues.jsonl"
        self.runs.write_text(a_line("a") + "\n", encoding="utf-8")

    def test_a_run_line_that_would_be_refused_stops_the_issue_write(self):
        ok, said = tool.check_before_writing(
            self.runs,
            {"a": {"batch": "a", "kind": "run", "version": "claude-opus-5"}},
            {"a": [{"batch": "a", "issue": "5"}]})
        self.assertFalse(ok)
        self.assertIn("version", said.lower())

    def test_an_issue_row_that_would_be_refused_stops_the_run_write(self):
        ok, said = tool.check_before_writing(
            self.runs,
            {"a": {"batch": "a", "kind": "run"}},
            {"a": [{"batch": "a", "issue": ""}]})
        self.assertFalse(ok)
        self.assertIn("issue", said.lower())

    def test_a_batch_absent_from_the_record_stops_both(self):
        ok, said = tool.check_before_writing(
            self.runs, {"zzz": {"batch": "zzz", "kind": "run"}}, {})
        self.assertFalse(ok)
        self.assertIn("zzz", said)

    def test_everything_valid_passes(self):
        ok, said = tool.check_before_writing(
            self.runs, {"a": {"batch": "a", "kind": "run"}},
            {"a": [{"batch": "a", "issue": "5"}]})
        self.assertTrue(ok, said)


class AFileWithNoTrailingNewlineIsRewrittenOnce(unittest.TestCase):
    """The `/code-review` pass of 2026-09-06. `render` splits and rejoins with
    a newline after every line, so a file whose last line carries none gained
    one -- and the "already what the replay would write" test then failed for
    ever, rewriting the file on every single run."""

    def test_the_second_run_writes_nothing(self):
        path = pathlib.Path(tempfile.mkdtemp()) / "runs.jsonl"
        path.write_text(a_line("a"), encoding="utf-8")   # no trailing newline
        tool.rewrite(path, {"a": {"batch": "a", "kind": "run"}})
        first = path.stat().st_mtime_ns
        ok, said = tool.rewrite(path, {"a": {"batch": "a", "kind": "run"}})
        self.assertTrue(ok)
        self.assertIn("already", said)
        self.assertEqual(first, path.stat().st_mtime_ns)
