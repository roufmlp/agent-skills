#!/usr/bin/env python3
"""The pending-actions file's closed sections move to an archive.

The mover's class is REFUSES. It matches only `#` or `##` headings carrying a
dated `DONE`, `STRUCK`, `CLOSED` or `SUPERSEDED`; it appends the matched section
verbatim to the archive *before* removing it from the live file; and it refuses
mixed blocks, body-text matches and anything it cannot classify, printing the
refused list. Nothing is ever deleted.

Every heading quoted below is a real line from a live pending-actions file,
copied verbatim on 2026-08-17. They are quoted rather than cited, because the
file is newest-first and grows daily, so it has no stable line numbers. One
counterexample moved three times in one working day while three readers checked
it.

The tests below pin the halves that can rot:

  It refuses open work sitting inside a marked heading. A naive matcher archives
  live work.

  It refuses a mixed block whole. An H2 reading `DONE` inside an H1 that still
  holds open work must not be lifted out of its parent on its own.

  It appends before it removes, and it rolls the append back when the live file
  moves under it. Several sessions write this file. A half-applied move would
  leave the section in neither copy.

Run: python3 test_move_closed_sections.py
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import move_closed_sections as mover  # noqa: E402

SCRIPT = HERE / "move_closed_sections.py"
SKILL = HERE / "SKILL.md"

# Real heading lines, copied verbatim from a live pending-actions file on
# 2026-08-17. A marker and open work in the same line. Every one of these would
# be archived by a matcher that reads the marker and stops reading.
MIXED = [
    "# NEWEST — 2026-08-14: ticket 27 is MERGED to local main. Actions 1 and 2 "
    "are DONE. Steps 5, 7 and 8 remain.",
    "# SUPERSEDED — 2026-08-12 evening: run 316-327 is merged, pushed and "
    "decided. One action left.",
    "# SUPERSEDED — 2026-08-12 morning: run 1 of ticket 24 is finished. Action 1 "
    "is DONE. Three actions remain.",
    "## Added 2026-08-10 — ticket 10, the founder walk: what is DONE and what is "
    "left",
    "## 5. The post-merge smoke walk — HALF DONE, and the other half needs a "
    "signed-in session",
    "## EARLIER — 2026-08-04: `/harden-issues 231 225 228 226 227 237` is DONE; "
    "four of the six wait on you",
    "## PREVIOUS — 2026-08-08 (round-10 acceptance walk): the walk is DONE; two "
    "new defects block the founders, and the sign-in mail is dead",
]

# Real heading lines whose only open-work word is negated in its own clause.
# These are closed sections and must be archived, not refused.
NEGATED = [
    "# NEWEST — 2026-08-11 night: ticket 24 is CLOSED. Nothing on it waits on "
    "you.",
    "## 1. All three checks are DONE, 2026-08-10 — nothing here waits on you",
]

# Real heading lines that are cleanly closed and dated.
CLEAN = [
    "## 1. DONE 2026-08-15 — both run blockers are closed",
    "## 0. STRUCK — the three Supabase reads were answered on 2026-08-14 and "
    "never removed from here",
    "## CLOSED 2026-08-02 — the mispricing question is answered, and NO real "
    "document is affected",
    "## SUPERSEDED 2026-08-02 — arm B (DeepSeek) harden pass, 11 of 14 stamped",
    "## PREVIOUS — 2026-08-07 (later): THE APPLY IS DONE. Nothing from that "
    "brief is owed.",
    "## 3. DONE — you answered all three rulings, in session on 14 August",
]

# Real heading lines carrying a marker and no date at all.
UNDATED = [
    "## ACTION 1 — DONE. Merged, pushed, deployed.",
    "## Issue 315 is DONE — the road's first use, and it found a real defect",
]

LIVE_BLOCK = "# NEWEST — 2026-08-17: today's live block\n\nBody of the live block.\n\n"


def document(*blocks):
    """A pending-file-shaped document: a live block on top, then the blocks."""
    return LIVE_BLOCK + "".join(blocks)


def block(heading, body="Body text.\n"):
    return f"{heading}\n\n{body}\n"


def run_cli(*args):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )
    return done.returncode, done.stdout, done.stderr


class Bench:
    """A live file and an archive path in a scratch directory."""

    def __init__(self, root, text, archive_text=None):
        self.live = Path(root) / "pending-actions.md"
        self.live.write_text(text, encoding="utf-8")
        self.archive = Path(root) / "pending-actions-closed.md"
        if archive_text is not None:
            self.archive.write_text(archive_text, encoding="utf-8")

    def move(self, **kwargs):
        return mover.apply_move(self.live, self.archive, **kwargs)

    def live_text(self):
        return self.live.read_text(encoding="utf-8")

    def archive_text(self):
        return self.archive.read_text(encoding="utf-8") if self.archive.exists() else ""


class TestItMatchesOnlyADatedMarkerHeading(unittest.TestCase):
    def test_a_clean_dated_marker_heading_is_archived(self):
        for heading in CLEAN:
            with tempfile.TemporaryDirectory() as tmp:
                bench = Bench(tmp, document(block(heading)))
                result = bench.move()
                self.assertEqual([s.heading for s in result.archived], [heading])
                self.assertNotIn(heading, bench.live_text())
                self.assertIn(heading, bench.archive_text())

    def test_an_undated_marker_heading_is_refused_and_stays(self):
        for heading in UNDATED:
            with tempfile.TemporaryDirectory() as tmp:
                bench = Bench(tmp, document(block(heading)))
                result = bench.move()
                self.assertEqual(result.archived, [])
                self.assertEqual([r.heading for r in result.refused], [heading])
                self.assertIn("date", result.refused[0].reason.lower())
                self.assertIn(heading, bench.live_text())

    def test_an_h3_marker_heading_is_not_matched(self):
        """The matcher is `#` or `##`, and a `###` marker is left where it is.
        Widening the matcher is a decision, not a reflex."""
        heading = "### Model-comparison harness — CLOSED 2026-08-02"
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, document(block(heading)))
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual(result.refused, [])
            self.assertIn(heading, bench.live_text())

    def test_a_marker_in_body_text_is_never_a_section(self):
        text = document(
            block(
                "## 4. The Vercel variable",
                "This action is DONE 2026-08-15 and the ticket is CLOSED 2026-08-15.\n"
                "SUPERSEDED 2026-08-14 by the block above. STRUCK 2026-08-13.\n",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual(result.refused, [])
            self.assertEqual(bench.live_text(), text)

    def test_a_lowercase_done_is_not_a_marker(self):
        heading = (
            "# NEWEST — 2026-08-13, ticket 10: the auth work was "
            "already done, and the testers are the real blocker."
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, document(block(heading)))
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertIn(heading, bench.live_text())

    def test_a_heading_with_no_marker_is_left_alone_without_a_refusal(self):
        """Silence, not noise. Most of this file carries no marker at all, and a
        refusal line for each would bury the list that matters."""
        heading = "# NEWEST — 2026-08-16 (run `0a1b2c` finale): all nine issues shipped"
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, document(block(heading)))
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual(result.refused, [])


class TestItRefusesOpenWorkInsideTheHeading(unittest.TestCase):
    """Headings that read as closed to a matcher that stops at the marker."""

    def test_every_measured_mixed_heading_is_refused(self):
        for heading in MIXED:
            with tempfile.TemporaryDirectory() as tmp:
                bench = Bench(tmp, document(block(heading)))
                result = bench.move()
                self.assertEqual(result.archived, [], heading)
                self.assertEqual([r.heading for r in result.refused], [heading])
                self.assertIn(heading, bench.live_text())

    def test_the_refusal_names_the_open_work_it_read(self):
        heading = MIXED[0]
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, document(block(heading)))
            reason = bench.move().refused[0].reason
            self.assertIn("remain", reason.lower())

    def test_a_negated_open_work_word_does_not_refuse(self):
        """`Nothing on it waits on you` is a closure statement, and refusing it
        would leave two of the largest closed blocks in the file for ever."""
        for heading in NEGATED:
            with tempfile.TemporaryDirectory() as tmp:
                bench = Bench(tmp, document(block(heading)))
                result = bench.move()
                self.assertEqual([s.heading for s in result.archived], [heading])

    def test_the_negation_does_not_reach_across_a_clause(self):
        heading = (
            "## DONE 2026-08-10 — nothing is owed on the migrations. "
            "Three actions remain."
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, document(block(heading)))
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual([r.heading for r in result.refused], [heading])

    def test_blockers_is_not_the_word_block(self):
        """`both run blockers are closed` is a closed heading. Substring matching
        refuses it, and a matcher that refuses the clean cases is noise."""
        self.assertEqual(
            mover.open_work_in("## 1. DONE 2026-08-15 — both run blockers are closed"),
            [],
        )


class TestItRefusesMixedBlocks(unittest.TestCase):
    def test_a_marked_parent_holding_open_work_below_is_refused_whole(self):
        text = document(
            block("# NEWEST — 2026-08-13: the run is DONE."),
            block("## 1. DONE 2026-08-13 — the migration is applied"),
            block("## 2. The deploy still needs your hand"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual(len(result.refused), 1)
            self.assertIn("mixed", result.refused[0].reason.lower())
            self.assertEqual(bench.live_text(), text)

    def test_a_done_child_of_a_refused_parent_is_not_lifted_out(self):
        """The real case: ticket 27's H1 still holds steps 5, 7 and 8, and two
        H2s below it read `DONE 2026-08-14`. Archiving those two on their own
        would strip a live block of the record of what was already finished."""
        parent = MIXED[0]
        child = "## 1. DONE 2026-08-14 — `promotion.md` now writes `Owed: unsorted`"
        text = document(block(parent), block(child))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertIn(child, bench.live_text())
            self.assertEqual([r.heading for r in result.refused], [parent])

    def test_a_refused_parent_reports_once(self):
        """The refused unit is the block, so the report names the parent and not
        every heading inside it. The parent is what the human acts on."""
        parent = MIXED[0]
        child = MIXED[3]
        text = document(block(parent), block(child))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual([r.heading for r in result.refused], [parent])
            self.assertIn(child, bench.live_text())

    def test_a_marked_parent_with_clean_marked_children_takes_them_with_it(self):
        text = document(
            block("# NEWEST — 2026-08-13, run 327a/327b: BOTH STEPS ARE DONE."),
            block("## 1. DONE — apply migration `0090` to the pilot project"),
            block("## 2. DONE — merge the branch to local main"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual(len(result.archived), 1)
            self.assertIn("migration `0090`", bench.archive_text())
            self.assertNotIn("migration `0090`", bench.live_text())

    def test_an_ask_shaped_subheading_refuses_its_parent(self):
        """Real blocks read closed at H1 and hold an ask at H2 or H3. The
        open-work word list does not reach any of them, because this file writes
        an ask as a heading shape rather than as a sentence.

        Filing an unanswered ask into an archive nobody reads is the exact
        defect the archive exists to stop — the system loses asks, not answers —
        so the four shapes below are refusals in their own right."""
        parents = {
            # run 327a/327b, headed BOTH STEPS ARE DONE
            "## 5. OPEN — walk the new grain on the pilot project, in a browser":
                "OPEN",
            # ticket 24, headed CLOSED. Nothing on it waits on you.
            "## Your next step on this: draft the issues for ticket 24": "next step",
            # round 10, headed DONE, MERGED, PUSHED and DEPLOYING
            "### On you": "on you",
            # round 9, headed CLOSED — MERGED later that day
            "### On the human, in order": "on the human",
        }
        for child, signal in parents.items():
            with self.subTest(child=child):
                parent = "# NEWEST — 2026-08-13: the run is DONE and MERGED."
                text = document(block(parent), block(child))
                with tempfile.TemporaryDirectory() as tmp:
                    bench = Bench(tmp, text)
                    result = bench.move()
                    self.assertEqual(result.archived, [])
                    self.assertEqual([r.heading for r in result.refused], [parent])
                    self.assertIn(signal.lower(), result.refused[0].reason.lower())
                    self.assertEqual(bench.live_text(), text)

    def test_a_negated_on_you_is_still_a_closure(self):
        """`nothing here waits on you` must not trip the `on you` shape, or the
        two blocks that say so most plainly never leave the file."""
        for heading in NEGATED:
            self.assertEqual(mover.open_work_in(heading), [], heading)


class TestNothingIsDeleted(unittest.TestCase):
    """The archive append happens first, always."""

    def test_every_removed_byte_reaches_the_archive_verbatim(self):
        text = document(*[block(h) for h in CLEAN])
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            archive = bench.archive_text()
            for section in result.archived:
                self.assertIn(section.text, archive)
            live = bench.live_text()
            self.assertEqual(
                len(live) + sum(len(s.text) for s in result.archived), len(text)
            )

    def test_a_failing_archive_write_leaves_the_live_file_untouched(self):
        text = document(block(CLEAN[0]))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            bench.archive = Path(tmp) / "no-such-directory" / "closed.md"
            with self.assertRaises(OSError):
                bench.move()
            self.assertEqual(bench.live_text(), text)

    def test_a_live_file_that_moved_under_the_move_rolls_the_archive_back(self):
        """Several sessions write this file. If it changes between the read and
        the rewrite, the mover must not remove what it planned against, and must
        not leave its append behind either."""
        text = document(block(CLEAN[0]))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text, archive_text="# Closed\n\nan earlier run\n")
            before = bench.archive_text()

            def concurrent_write():
                bench.live.write_text(
                    text + "\n# NEWEST — a later session wrote this\n",
                    encoding="utf-8",
                )

            with self.assertRaises(mover.LiveFileMoved):
                bench.move(_after_archive=concurrent_write)

            self.assertEqual(bench.archive_text(), before)
            self.assertIn(CLEAN[0], bench.live_text())

    def test_dry_run_writes_nothing(self):
        text = document(block(CLEAN[0]))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move(dry_run=True)
            self.assertEqual(len(result.archived), 1)
            self.assertEqual(bench.live_text(), text)
            self.assertFalse(bench.archive.exists())

    def test_the_archive_is_appended_to_not_overwritten(self):
        text = document(block(CLEAN[0]))
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text, archive_text="# Closed\n\nan earlier run\n")
            bench.move()
            self.assertIn("an earlier run", bench.archive_text())
            self.assertIn(CLEAN[0], bench.archive_text())

    def test_the_live_rewrite_is_atomic(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("os.replace", source)


class TestItIsIdempotent(unittest.TestCase):
    def test_a_second_run_moves_nothing_and_changes_neither_file(self):
        text = document(*[block(h) for h in CLEAN])
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            bench.move()
            live_once, archive_once = bench.live_text(), bench.archive_text()
            second = bench.move()
            self.assertEqual(second.archived, [])
            self.assertEqual(bench.live_text(), live_once)
            self.assertEqual(bench.archive_text(), archive_once)

    def test_the_archive_is_not_itself_moved(self):
        """The archive is nothing but marked headings. Pointed at itself the
        mover would empty it into itself."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "pending-actions-closed.md"
            archive.write_text(document(block(CLEAN[0])), encoding="utf-8")
            code, _, err = run_cli(str(archive), "--archive", str(archive))
            self.assertEqual(code, 1)
            self.assertIn("same file", err.lower())


class TestItRespectsCodeFences(unittest.TestCase):
    def test_a_heading_inside_a_fence_is_not_a_heading(self):
        text = document(
            block(
                "## 4. Paste this into the SQL editor",
                "```sql\n-- ## 1. DONE 2026-08-15 — a sample heading\nselect 1;\n```\n",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            result = bench.move()
            self.assertEqual(result.archived, [])
            self.assertEqual(bench.live_text(), text)

    def test_a_fenced_block_travels_with_its_archived_section(self):
        text = document(
            block(
                "## 1. DONE 2026-08-15 — the SQL you ran",
                "```sql\nselect count(*) from items;\n```\n",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            bench.move()
            self.assertIn("select count(*) from items;", bench.archive_text())
            self.assertNotIn("select count(*) from items;", bench.live_text())


class TestTheCliContract(unittest.TestCase):
    def test_the_live_file_is_a_required_argument(self):
        """The pack ships with no personal default path. A bare invocation must
        say so rather than guess at a file to rewrite."""
        code, _, err = run_cli()
        self.assertNotEqual(code, 0)
        self.assertIn("file", err.lower())

    def test_the_archive_defaults_to_closed_beside_the_live_file(self):
        text = document(block(CLEAN[0]))
        with tempfile.TemporaryDirectory() as tmp:
            live = Path(tmp) / "pending-actions.md"
            live.write_text(text, encoding="utf-8")
            code, out, _ = run_cli(str(live))
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "pending-actions-closed.md").exists())
            self.assertIn("pending-actions-closed.md", out)

    def test_the_refused_list_is_printed(self):
        # Each mixed heading gets its own live H1, so none is nested inside
        # another refused block. See test_a_refused_parent_reports_once.
        text = document(
            *[
                block(f"# NEWEST — 2026-08-{day:02d}: a live block") + block(heading)
                for day, heading in enumerate(MIXED, start=1)
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            code, out, _ = run_cli(
                str(bench.live), "--archive", str(bench.archive), "--dry-run"
            )
            self.assertEqual(code, 0)
            for heading in MIXED:
                self.assertIn(heading[:40], out)

    def test_it_reports_what_it_moved(self):
        text = document(*[block(h) for h in CLEAN])
        with tempfile.TemporaryDirectory() as tmp:
            bench = Bench(tmp, text)
            code, out, _ = run_cli(str(bench.live), "--archive", str(bench.archive))
            self.assertEqual(code, 0)
            self.assertIn(str(len(CLEAN)), out)

    def test_a_missing_live_file_exits_non_zero(self):
        code, _, err = run_cli("/no/such/pending.md")
        self.assertEqual(code, 1)
        self.assertIn("no/such/pending.md", err)

    def test_it_cites_the_file_by_heading_text_and_never_by_line_number(self):
        """A newest-first file that grows daily has no stable line numbers. One
        counterexample sat at three different lines in one day while three
        readers checked it."""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("heading", source)
        for banned in ("pending-actions.md:", "pending-actions.md line"):
            self.assertNotIn(banned, source)


class TestItIsWiredIn(unittest.TestCase):
    """The build is the script plus its invocation. A mover nobody calls moves
    nothing, and the skill puts the call in the apply step."""

    def test_the_apply_step_invokes_the_mover(self):
        skill = SKILL.read_text(encoding="utf-8")
        apply_half = skill.split("## Half one: apply", 1)[1].split("## Half two:", 1)[0]
        self.assertIn("move_closed_sections.py", apply_half)


class TestTheLiveFileStillParses(unittest.TestCase):
    """A read-only probe of a real file, when one is named. Point
    `PENDING_ACTIONS_FILE` at your live pending-actions file to run it. It
    asserts no count, because every count in this class of check goes stale
    inside one working day.

    An EMPTY plan is a decision, and it is the right one on a file that carries
    no `#` or `##` closure marker. That is a pending-actions file's ordinary
    state after a `/daily-brief` sweep, and one live file was in that state on
    2026-09-04, when the two markers it held were both at `###` — the level the
    mover refuses on purpose. This case asserted a non-empty plan until then, so
    it failed on correct behaviour and made a passing run depend on what the
    file happened to hold that morning. It now asserts only what the mover owes
    whatever the content is."""

    def test_the_mover_plans_the_live_file_without_writing_to_it(self):
        named = os.environ.get("PENDING_ACTIONS_FILE")
        if not named:
            self.skipTest("PENDING_ACTIONS_FILE is not set")
        live = Path(named)
        if not live.exists():
            self.skipTest(f"no live pending-actions file at {live}")
        before = hashlib.sha256(live.read_bytes()).hexdigest()
        text = live.read_text(encoding="utf-8")
        result = mover.plan(text)
        self.assertIsInstance(result, mover.Result)
        for section in result.archived:
            self.assertIn(section.text, text)
        self.assertEqual(before, hashlib.sha256(live.read_bytes()).hexdigest())

    def test_the_code_fences_of_the_live_file_balance(self):
        """The empty plan has to be empty for the right reason. One unbalanced
        fence in a file several sessions write makes `headings()` treat the
        whole tail as code and swallow every heading in it, and the plan then
        reads empty with nothing wrong in the matcher. An odd fence count is the
        only way that happens, so this counts fences rather than headings: it
        needs no marker in the file and no count that can go stale."""
        named = os.environ.get("PENDING_ACTIONS_FILE")
        if not named:
            self.skipTest("PENDING_ACTIONS_FILE is not set")
        live = Path(named)
        if not live.exists():
            self.skipTest(f"no live pending-actions file at {live}")
        lines = live.read_text(encoding="utf-8").splitlines(keepends=True)
        fences = [line for line in lines if mover.FENCE.match(line)]
        self.assertEqual(len(fences) % 2, 0, "a code fence in the live file is unclosed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
