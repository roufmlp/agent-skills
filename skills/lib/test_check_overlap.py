#!/usr/bin/env python3
"""Tracker-tooling issue 35, a new issue names the open ones it meets.

`check_overlap.py` reads a drafted issue against the open issues of one tracker and
refuses the draft unless it names each one whose `Touches:` paths meet its own. The UI
audit of 25 September wrote 35 issues in one tracker without reading the 29 open ones,
and a fold found 18 duplicate pairs.

Run: python3 test_check_overlap.py
"""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_overlap.py"


def issue(status, touches, title="An issue", body=""):
    lines = [f"Status: {status}", "Sentence: something"]
    if touches is not None:
        lines.append(f"Touches: {touches}")
    lines += ["Kind: product", "", f"# {title}", "", "## What to build", "", "Words.", ""]
    return "\n".join(lines) + body


def draft(touches="`src/lib/orders.ts`", blocked_by="- None", parent="`01-root.md`",
          header_extra=""):
    lines = ["Status: needs-harden", "Sentence: a draft"]
    if touches is not None:
        lines.append(f"Touches: {touches}")
    lines += ["Kind: product", "Level: light"]
    if header_extra:
        lines.append(header_extra)
    return "\n".join(lines + [
        "", "# 99 — The draft", "", "## Parent", "", parent, "",
        "## What to build", "", "Words.", "", "## Blocked by", "", blocked_by, ""])


OPEN_12 = issue("ready-for-agent", "`src/lib/**`", "12 — The orders library")
NAMES_12 = "- `12-orders.md` — it owns the library"


class Tracker:
    """A temporary git repository holding one tracker and a draft outside it."""

    def __init__(self, issues, draft_text):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.issues = self.root / ".scratch" / "t" / "issues"
        self.issues.mkdir(parents=True)
        for name, text in issues.items():
            (self.issues / name).write_text(text, encoding="utf-8")
        self.draft = self.root / "scratch-draft.md"
        self.draft.write_text(draft_text, encoding="utf-8")

    def run(self, target=None):
        done = subprocess.run(
            [sys.executable, str(SCRIPT), str(target or self.draft), "--issues", str(self.issues)],
            capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def hashes(self):
        files = sorted(self.issues.iterdir()) + [self.draft]
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

    def close(self):
        self._dir.cleanup()


class Case(unittest.TestCase):

    def tracker(self, issues, draft_text=None):
        made = Tracker(issues, draft_text if draft_text is not None else draft())
        self.addCleanup(made.close)
        return made


class AnOpenIssueThatMeetsIsListed(Case):
    """AC1."""

    def test_the_line_names_the_issue_the_draft_path_and_its_pattern(self):
        code, out = self.tracker({"12-orders.md": OPEN_12}).run()
        line = next(l for l in out.splitlines() if "12" in l and "src/lib/**" in l)
        self.assertIn("src/lib/orders.ts", line)
        self.assertEqual(code, 1, out)

    def test_a_tracker_nothing_meets_is_clean(self):
        code, out = self.tracker({"12-orders.md": issue("open", "`docs/a.md`")}).run()
        self.assertEqual(code, 0, out)


class AClosedIssueIsNotListed(Case):
    """AC2, with the closed set of default `q-h0925-35-2`."""

    CLOSED = ("done", "closed", "wontfix", "folded", "folded-into-7", "superseded",
              "split", "resolved")

    def test_no_closed_status_is_listed(self):
        issues = {f"{13 + i}-closed.md": issue(status, "`src/lib/orders.ts`")
                  for i, status in enumerate(self.CLOSED)}
        code, out = self.tracker(issues).run()
        for i in range(len(self.CLOSED)):
            self.assertNotIn(f"{13 + i}-closed.md", out)
        self.assertEqual(code, 0, out)

    def test_a_bold_closed_status_is_closed(self):
        code, out = self.tracker({"13-b.md": issue("**done**", "`src/lib/orders.ts`")}).run()
        self.assertNotIn("13-b.md", out)
        self.assertEqual(code, 0, out)

    def test_parked_and_blocked_are_open(self):
        for status in ("parked", "blocked", "needs-harden"):
            with self.subTest(status=status):
                code, out = self.tracker({"13-p.md": issue(status, "`src/lib/orders.ts`")}).run()
                self.assertIn("13-p.md", out)
                self.assertEqual(code, 1, out)


class NamingMeansABullet(Case):
    """AC3."""

    def test_a_blocked_by_bullet_names_it(self):
        code, out = self.tracker({"12-orders.md": OPEN_12}, draft(blocked_by=NAMES_12)).run()
        self.assertEqual(code, 0, out)
        self.assertIn("12-orders.md", out)

    def test_named_nowhere_exits_1(self):
        code, out = self.tracker({"12-orders.md": OPEN_12}).run()
        self.assertEqual(code, 1, out)

    def test_a_number_inside_a_sentence_is_not_a_bullet_naming_it(self):
        code, out = self.tracker({"12-orders.md": OPEN_12},
                                 draft(blocked_by="- None; 12 is close")).run()
        self.assertEqual(code, 1, out)


class AFoldTargetNamesIt(Case):
    """AC4, the `Folds:` form of default `q-h0925-35-6`."""

    def test_a_folds_line_names_it(self):
        code, out = self.tracker({"12-orders.md": OPEN_12},
                                 draft(header_extra="Folds: 12")).run()
        self.assertEqual(code, 0, out)

    def test_a_folds_line_naming_another_issue_does_not(self):
        code, out = self.tracker({"12-orders.md": OPEN_12},
                                 draft(header_extra="Folds: 120")).run()
        self.assertEqual(code, 1, out)

    def test_numbers_in_prose_after_the_target_name_nothing(self):
        code, out = self.tracker({"4-other.md": issue("open", "`src/lib/orders.ts`")},
                                 draft(header_extra="Folds: 12 (item 4 of 2026-09-25)")).run()
        self.assertIn("UNNAMED 4", out)
        self.assertEqual(code, 1, out)

    def test_two_fold_targets(self):
        issues = {"12-orders.md": OPEN_12, "13-more.md": issue("open", "`src/lib/orders.ts`")}
        code, out = self.tracker(issues, draft(header_extra="Folds: 12, `13`")).run()
        self.assertEqual(code, 0, out)


class TwoFilesSharingANumber(Case):
    """A stray file sharing a number is reported under its own name."""

    def test_each_file_is_its_own_line(self):
        issues = {"12-orders.md": OPEN_12, "12-stray.md": OPEN_12}
        code, out = self.tracker(issues).run()
        self.assertIn("12-orders.md", out)
        self.assertIn("12-stray.md", out)


class AnIssueWithNoPathsIsUnplaceable(Case):
    """AC5."""

    def test_no_touches_line_is_listed_on_its_own_line(self):
        code, out = self.tracker({"30-old.md": issue("open", None)}).run()
        line = next(l for l in out.splitlines() if "30-old.md" in l)
        self.assertIn("UNPLACEABLE", line)
        self.assertEqual(code, 0, out)

    def test_a_value_with_no_backticked_token_is_unplaceable(self):
        for value in ("unswept", "137, 149, 153"):
            with self.subTest(value=value):
                code, out = self.tracker({"31-u.md": issue("open", value)}).run()
                line = next(l for l in out.splitlines() if "31-u.md" in l)
                self.assertIn("UNPLACEABLE", line)
                self.assertEqual(code, 0, out)

    def test_a_backticked_path_inside_prose_is_read(self):
        code, out = self.tracker(
            {"32-p.md": issue("open", "a new script under `src/lib/orders.ts` and its test")}).run()
        self.assertIn("UNNAMED 32", out)
        self.assertEqual(code, 1, out)

    def test_a_closed_issue_with_no_touches_is_not_listed(self):
        code, out = self.tracker({"33-c.md": issue("done", None)}).run()
        self.assertNotIn("33-c.md", out)


class TheDraftIsNeverReadAgainstItself(Case):
    """AC7."""

    def test_a_written_draft_names_12_and_never_itself(self):
        made = self.tracker({"12-orders.md": OPEN_12, "20-draft.md": draft()})
        code, out = made.run(made.issues / "20-draft.md")
        self.assertIn("12-orders.md", out)
        self.assertNotIn("20", out.replace("src/lib", ""))
        self.assertEqual(code, 1, out)


class ADraftMustStateItsPaths(Case):
    """AC8, ruling Q10 of 2026-09-25."""

    def test_no_touches_line_exits_1_and_names_it(self):
        code, out = self.tracker({}, draft(touches=None)).run()
        self.assertEqual(code, 1, out)
        self.assertIn("Touches:", out)

    def test_prose_with_no_backticked_path_exits_1(self):
        code, out = self.tracker({}, draft(touches="the order model")).run()
        self.assertEqual(code, 1, out)
        self.assertIn("Touches:", out)

    def test_none_exits_1(self):
        code, out = self.tracker({}, draft(touches="none")).run()
        self.assertEqual(code, 1, out)


class AContinuedValueIsReadToItsEnd(Case):
    """AC9."""

    def test_the_second_line_of_a_touches_value_meets(self):
        wrapped = issue("open", "`docs/a.md`,\n`src/lib/orders.ts`")
        code, out = self.tracker({"14-wrapped.md": wrapped}).run()
        self.assertIn("UNNAMED 14", out)
        self.assertEqual(code, 1, out)


class ADirectoryMeetIsItsOwnLine(Case):
    """AC10, default `q-h0925-35-1`."""

    def test_directory_and_none(self):
        issues = {"12-orders.md": OPEN_12,
                  "15-dir.md": issue("open", "`src/lib/`"),
                  "16-none.md": issue("open", "none"),
                  "17-none-prose.md": issue("open", "none. It only reads.")}
        code, out = self.tracker(issues, draft(blocked_by=NAMES_12)).run()
        line = next(l for l in out.splitlines() if "15-dir.md" in l)
        self.assertIn("DIRECTORY", line)
        self.assertNotIn("16-none.md", out)
        self.assertNotIn("17-none-prose.md", out)
        self.assertEqual(code, 0, out)

    def test_a_directory_meet_beside_a_file_meet_still_refuses(self):
        both = issue("open", "`src/lib/`, `src/lib/orders.ts`")
        code, out = self.tracker({"18-both.md": both}).run()
        self.assertIn("UNNAMED 18", out)
        self.assertEqual(code, 1, out)


class TheParentCountsAsNamed(Case):
    """AC11, default `q-h0925-35-3`."""

    def test_the_parent_names_it(self):
        code, out = self.tracker({"12-orders.md": OPEN_12},
                                 draft(parent="`12-parent.md`")).run()
        self.assertEqual(code, 0, out)


class ItWritesNothing(Case):
    """Must still be true: a refused draft is left for the drafter to fix."""

    def test_a_refusing_run_changes_no_file(self):
        made = self.tracker({"12-orders.md": OPEN_12, "30-old.md": issue("open", None)})
        before = made.hashes()
        code, _ = made.run()
        self.assertEqual(code, 1)
        self.assertEqual(made.hashes(), before)


class ItCannotRead(Case):
    """Exit 2 is kept for a file that cannot be read, never for an offence."""

    def test_a_missing_draft_exits_2(self):
        made = self.tracker({"12-orders.md": OPEN_12})
        code, out = made.run(made.root / "absent.md")
        self.assertEqual(code, 2, out)

    def test_a_tracker_outside_git_exits_2(self):
        with tempfile.TemporaryDirectory() as bare:
            (Path(bare) / "d.md").write_text(draft(), encoding="utf-8")
            done = subprocess.run([sys.executable, str(SCRIPT), str(Path(bare) / "d.md"),
                                   "--issues", bare], capture_output=True, text=True)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
