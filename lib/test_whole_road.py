"""The road of one feature from the approval to local main, with no agent.

Every other suite tests one command on a fixture written for it. This one
walks the commands in the order a session runs them, on one product with the
real hooks: a note stops on a money question, a panel rules it and the ruling
changes the note, the note builds and merges, the final check passes, the run
holds, he confirms, and the next start merges the feature into local main.
Each step an agent takes in a real run is a git command here, made as the
agent's file tells it. The rehearsal of 2026-11-12 stopped between two of
these steps, and no suite had walked from one to the next.
"""

import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import feature_run  # noqa: E402
import plan_check  # noqa: E402
import rulings  # noqa: E402
import test_note_check as product  # noqa: E402
import test_rulings as panel  # noqa: E402
from test_suite import BLOCK, FAKE_VITEST  # noqa: E402

QUESTION = "what is the highest refund a manager may give with no second approval"
DEFAULT = "cap it at 50"
CONDITION = "tests/money.test.ts: a refund above the cap is refused"

NOTE = textwrap.dedent("""\
    # 01 Refund cap

    A manager's refund gets a cap. The value of the cap waits for a ruling.

    Screens: none
    Risk: money
    Waits for: none

    ## Done

    - `grep -q CAP src/lib/money.ts`: the module carries the cap

    ## Tests

    `tests/money.test.ts`, committed with this note.
""")

PLAN = textwrap.dedent("""\
    # Bubble plan

    Feature: bubble

    ## Notes

    | Note | What it does | Migration | Waits for | Screens |
    | --- | --- | --- | --- | --- |
    | 01 | A cap on a manager's refund | none | none | none |

    ## Questions

    - [money or access rules] 01: a manager's refund gets a cap; the note leaves its value to a ruling
      Answer: yes, add the cap

    Approved: 2026-11-03
""")


def report(state, row, decide="none"):
    return "\n".join([
        "# Bubble report", "", "Feature: bubble", "Branch: feature/bubble", f"State: {state}", "", "## Notes", "",
        "| Note | State | Strikes | Attempts | Last report |", "| --- | --- | --- | --- | --- |",
        f"| 01 | {row} | 0 | 1 |  |", "", "## Decide", "", decide, ""])


class WholeRoad(unittest.TestCase):
    typed, says, panel_files = panel.Commands.typed, panel.Commands.says, panel.Commands.panel_files
    ran, later, QUESTION = panel.Commands.ran, panel.Commands.later, QUESTION

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        home = root / "home"
        (home / ".claude" / "skills" / "workflow").mkdir(parents=True)
        os.symlink(HERE, home / ".claude" / "skills" / "workflow" / "lib")
        vitest = root / "vitest"
        vitest.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
        vitest.chmod(0o755)
        self.env = {**os.environ, "HOME": str(home), "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                    "RUN_SUITE_LOCK": str(root / "lock"), "FAKE_ARGV": str(root / "argv.jsonl")}
        self.repo = root / "product"
        self.repo.mkdir()
        files = {path: text for path, text in product.FILES.items() if not path.startswith("changes/")}
        for path, text in {**files, "CLAUDE.md": BLOCK.format(vitest=vitest), ".gitignore": ".claude/\n"}.items():
            self.write(self.repo, path, text)
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Sam Doe")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "base")
        shutil.copytree(product.HOOKS, self.repo / ".githooks")
        subprocess.run(["sh", ".githooks/prepare"], cwd=self.repo, env=self.env, check=True, capture_output=True)
        self.git(self.repo, "add", ".githooks")
        self.git(self.repo, "commit", "-qm", "hooks")
        self.tree = self.repo / ".claude" / "worktrees" / "feature-bubble"
        self.git(self.repo, "worktree", "add", "-q", str(self.tree), "-b", "feature/bubble", "main")
        self.note_tree = self.repo / ".claude" / "worktrees" / "note-bubble-01"
        self.records = self.repo / ".git" / "build-feature" / "bubble"
        self.clock = 1_000_000.0
        self.kept = (rulings.now, rulings.PROJECTS, os.environ.get(rulings.SESSION))
        rulings.now = lambda: self.clock
        rulings.PROJECTS = root / "projects"
        os.environ[rulings.SESSION] = panel.SESSION

    def tearDown(self):
        rulings.now, rulings.PROJECTS, session = self.kept
        if session is None:
            os.environ.pop(rulings.SESSION, None)
        else:
            os.environ[rulings.SESSION] = session
        self.tmp.cleanup()

    def write(self, tree, path, text):
        full = tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text)

    def git(self, tree, *args):
        """One git command through the product's hooks; a refusal fails the test with its line."""
        done = subprocess.run(["git", *args], cwd=tree, env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, f"git {' '.join(args)}:\n{done.stdout}\n{done.stderr}")
        return done.stdout.strip()

    def commit(self, tree, message, *paths):
        self.git(tree, "add", "--", *paths)
        self.git(tree, "commit", "-qm", message)
        return self.git(tree, "rev-parse", "HEAD")

    def run_main(self, mod, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(list(args))
        return code, out.getvalue()

    def plan(self):
        return self.run_main(plan_check, "plan", "bubble", "--tree", str(self.tree))

    def pre_run(self):
        return self.run_main(plan_check, "notes", "bubble", "--tree", str(self.tree), "--only", "01")

    def args(self):
        code, out = self.run_main(feature_run, "args", "bubble", "--tree", str(self.tree), "--started", "now")
        return code, json.loads(out) if code == 0 else out

    def rule(self, name, *extra):
        return self.run_main(rulings, name, "bubble", "--tree", str(self.tree), "--date", "2026-11-12", *extra)

    def as_printed(self, out):
        """Run the commit a command printed after `commit it:`, through the hooks."""
        line = next(line for line in out.splitlines() if line.startswith("commit it: "))
        done = subprocess.run(line[len("commit it: "):], shell=True, env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def set_report(self, state, row, message, decide="none"):
        self.write(self.tree, "changes/bubble/report.md", report(state, row, decide))
        self.commit(self.tree, message, "changes/bubble/report.md")

    def note_branch(self):
        """The script's worktree job: a note tree on its branch, from the feature branch as it stands."""
        self.git(self.repo, "worktree", "add", "-q", str(self.note_tree), "-b", "note/bubble/01", "feature/bubble")

    # ── the steps, in the order a session and a run take them ──

    def interview(self):
        self.write(self.tree, "changes/bubble/01-cap.md", NOTE)
        self.write(self.tree, "tests/money.test.ts", 'it("a refund at the cap passes", () => {});\n')
        self.commit(self.tree, "note 01: refund cap", "changes/bubble/01-cap.md", "tests/money.test.ts")
        self.write(self.tree, "changes/bubble/plan.md", PLAN)
        self.commit(self.tree, "plan: bubble approved", "changes/bubble/plan.md")
        code, out = self.plan()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pre_run()[0], 0)
        code, got = self.args()
        self.assertEqual(code, 0, got)
        self.assertEqual([n["state"] for n in got["notes"]], ["not started"])

    def stop(self):
        """Run 1: the implementer stops on the money question, and the run ends."""
        self.note_branch()
        self.set_report("stopped", f"stopped: {QUESTION}", "report: bubble stopped",
                        f"01: [money] {QUESTION} Default: {DEFAULT}")
        self.typed("01", "money", QUESTION, DEFAULT)  # as `feature_run.py roles` writes it
        code, out = self.plan()
        self.assertEqual(code, plan_check.INTERVIEW, out)
        self.assertIn("RULING: notes 01", out)

    def panel_rules(self):
        """Nobody answers inside the wait, so a panel rules, and its ruling changes the note."""
        code, out = self.rule("wait", "--note", "01")
        self.assertIn("after that the panel rules", out)
        self.later(rulings.RULING_WAIT_SECONDS)
        folder = rulings.panel_dir(rulings.Feature(str(self.tree), "bubble"), "01", QUESTION)
        self.assertIn("workflow:build-feature-road-finder", self.rule("panel", "--note", "01")[1])
        self.panel_files(folder)
        self.assertIn("workflow:panel-review-persona", self.rule("panel", "--note", "01")[1])
        self.panel_files(folder, panel.vote_text("Rule: A", CONDITION), panel.vote_text("Rule: A"),
                         panel.vote_text("Hold: the highest refund of last year"))
        self.ran("01")
        code, out = self.rule("panel", "--note", "01")
        self.assertIn("road A, 2 of 3", out)
        code, out = self.rule("record", "--note", "01", "--kind", "money", "--who", "panel", "--question", QUESTION,
                              "--words", DEFAULT, "--touches", "none", "--undo", "one constant")
        self.assertEqual(code, 0, out)
        # The session applies the ruling: the value, and the panel's condition as a done check with its test.
        self.write(self.tree, "changes/bubble/01-cap.md", NOTE.replace(
            "waits for a ruling.", "is 50, by the panel's ruling.").replace(
            "\n## Tests", f"- `grep -q 50 src/lib/money.ts`: {CONDITION}\n\n## Tests"))
        self.write(self.tree, "tests/money.test.ts", 'it("a refund at the cap passes", () => {});\n'
                                                     'it("a refund above the cap is refused", () => {});\n')
        self.as_printed(out)
        self.assertEqual(self.git(self.tree, "log", "-1", "--format=%s"), "ruling: note 01")
        self.assertEqual(self.git(self.tree, "status", "--porcelain"), "")
        code, out = self.plan()
        self.assertEqual(code, 0, out)
        self.assertIn("1 ruling(s), 1 to confirm before the merge", out)
        self.assertEqual(self.pre_run()[0], 0)
        code, out = self.args()
        self.assertEqual(code, plan_check.REFUSED, "the old tree holds the build of the old note")
        for command in re.findall(r"`(git [^`]+)`", out):
            subprocess.run(command, shell=True, env=self.env, check=True, capture_output=True)
        code, got = self.args()
        self.assertEqual(code, 0, got)
        self.assertEqual((got["notes"][0]["state"], got["gate_open"], got["held"]), ("not started", ["01"], False))

    def build_and_merge(self):
        """Run 2: the implementer builds on the note branch, and the merger merges it into the feature."""
        self.note_branch()
        self.write(self.note_tree, "src/lib/money.ts", "export const CAP = 50;\n")
        self.commit(self.note_tree, "note 01: cap a manager refund at 50", "src/lib/money.ts")
        self.git(self.tree, "merge", "--no-ff", "-q", "-m", "merge note 01", "note/bubble/01")
        return self.git(self.tree, "rev-parse", "HEAD")

    def hold(self, merge):
        """The merger writes the row, the final check passes, and the run holds for his answers."""
        self.set_report("running", f"merged {merge}", "report: note 01 merged")
        self.set_report("held", f"merged {merge[:9]}", "report: bubble held")
        code, out = self.plan()
        self.assertEqual(code, plan_check.INTERVIEW, out)
        self.assertIn("GATE: 1 ruling(s) Sam did not make", out)

    def gate(self):
        code, out = self.rule("list")
        self.assertIn("1 ruling(s) to confirm", out)
        self.later(30)
        self.says("01: confirm")
        code, out = self.rule("answer", "--note", "01", "--confirmed", "--words", "01: confirm")
        self.assertEqual(code, 0, out)
        self.as_printed(out)

    # ── the road ──

    def test_a_note_a_panel_ruled_builds_merges_holds_and_reaches_local_main(self):
        self.interview()
        self.stop()
        self.panel_rules()
        merge = self.build_and_merge()
        self.hold(merge)
        self.gate()
        # The next start after his answer. The ruling changed note 01 before the note was built,
        # and the note is merged now: that is no edit of a merged note.
        code, out = self.plan()
        self.assertEqual(code, 0, out)
        self.assertIn("1 ruling(s)", out)
        self.assertNotIn("to confirm", out)
        code, got = self.args()
        self.assertEqual(code, 0, got)
        self.assertEqual((got["notes"][0]["state"], got["gate_open"], got["held"]),
                         (f"merged {merge[:9]}", [], True))
        # The merge run: the held final check stands, and the merger takes the feature into local main.
        self.set_report("merged", f"merged {merge[:9]}", "report: bubble merged")
        main = self.git(self.repo, "rev-parse", "main")
        self.git(self.repo, "merge", "--no-ff", "-q", "-m", "merge feature bubble", "feature/bubble")
        self.assertNotEqual(self.git(self.repo, "rev-parse", "main"), main)
        self.assertEqual((self.repo / "src/lib/money.ts").read_text(), "export const CAP = 50;\n")
        text = (self.repo / "changes/bubble/report.md").read_text()
        self.write(self.repo, "changes/bubble/report.md", text.replace("State: merged\n", "State: merged\nMerged: 2026-11-12 abc\n"))
        self.commit(self.repo, "report: bubble merged", "changes/bubble/report.md")
        code, out = self.run_main(plan_check, "plan", "bubble", "--tree", str(self.repo))
        self.assertEqual(code, plan_check.REFUSED, out)
        self.assertIn("A change to a merged feature is a new feature", out)

    def test_the_gate_holds_local_main_until_he_answers(self):
        self.interview()
        self.stop()
        self.panel_rules()
        self.hold(self.build_and_merge())
        main = self.git(self.repo, "rev-parse", "main")
        done = subprocess.run(["git", "merge", "--no-ff", "-m", "merge feature bubble", "feature/bubble"],
                              cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 ruling(s) Sam did not make have no `Confirmed:` or `Overturned:` line", done.stdout + done.stderr)
        self.assertEqual(self.git(self.repo, "rev-parse", "main"), main)

    def test_a_run_that_ends_between_the_merge_and_its_row_starts_again_with_the_note_merged(self):
        # The rehearsal of 2026-11-12: the merger merged note 01, its edit of the row failed, and the
        # run ended in the final check. The row read `not started`, the pre-run check stopped the
        # merged note as "done check passes before the work", and no restart went through.
        self.interview()
        self.stop()
        self.panel_rules()
        merge = self.build_and_merge()
        self.assertIn("| 01 | not started |", (self.tree / "changes/bubble/report.md").read_text())
        code, out = self.plan()
        self.assertEqual(code, 0, out)
        code, out = self.pre_run()
        self.assertEqual(code, 0, out)
        self.assertIn(f"note 01: merged into feature/bubble at {merge[:9]}", out)
        self.assertNotIn("passes on today's code", out)
        code, got = self.args()
        self.assertEqual(code, 0, got)
        self.assertEqual(got["notes"][0]["state"], f"merged {merge[:9]}", "the script writes this row at its start")
        self.assertFalse(got["notes"][0]["fresh"])


if __name__ == "__main__":
    unittest.main()
