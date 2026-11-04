#!/usr/bin/env python3
"""Drill for audit_week.py: the store refresh, the growth snapshot, the page and the proposals.

    python3 test_audit_week.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audit_week as mod
from test_audit_transcripts import assistant, user, write


def session(folder, name, day, minutes=(0, 1, 5), text="hello", mid="m", skills=()):
    records = [user(minutes[0], text)]
    for i, m in enumerate(minutes[1:]):
        records.append(assistant(m, f"{mid}{i}", tools=tuple("Skill" for _ in skills)))
    for r in records:
        r["timestamp"] = r["timestamp"].replace("2026-10-05", day)
    write(folder / f"{name}.jsonl", records)


class Weekly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.projects = root / "projects"
        self.ideas = root / "ideas"
        self.home = root / "home"
        (self.ideas / "pages").mkdir(parents=True)
        (self.ideas / "mvps.md").write_text(
            "| Name | Repo | Type | For | Start | Live | Done | Result |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| kit | r | site | c | 2026-10-20 | 2026-10-25 | | |\n"
        )
        subprocess.run(["git", "init", "-q", str(self.ideas)], check=True)
        subprocess.run(["git", "-C", str(self.ideas), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "start"], check=True)
        (self.home / "skills" / "coderules").mkdir(parents=True)
        (self.home / "skills" / "coderules" / "SKILL.md").write_text("x")
        (self.home / "skills" / "unused").mkdir()
        (self.home / "skills" / "unused" / "SKILL.md").write_text("x")
        (self.home / "agents").mkdir()
        (self.home / "agents" / "finder.md").write_text("x")
        (self.home / "CLAUDE.md").write_text("a\nb\n")
        (self.home / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": "python3 /h/guard.py"}]}]}}))
        self.folder = self.projects / "-Users-x-code-kit"
        session(self.folder, "a", "2026-10-03", skills=("coderules",))
        session(self.folder, "b", "2026-10-20")
        session(self.folder, "c", "2026-09-12")

    def tearDown(self):
        self.tmp.cleanup()

    def run_week(self, today="2026-10-25"):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        os.environ.update(env)
        return mod.run(str(self.projects), str(self.ideas), str(self.home), today, push=False)

    def test_first_run_writes_store_snapshot_and_page(self):
        out = self.run_week()
        self.assertEqual(out["read"], 3)
        self.assertEqual(out["sessions"], 3)
        self.assertEqual(out["git"], "committed, not pushed")
        page = Path(out["page"])
        self.assertEqual(page.name, "2026-11-01-audit.md")
        text = page.read_text()
        self.assertIn("| Cost | 2 sessions", text)
        self.assertIn("| Speed | kit 5 days |", text)
        self.assertIn("| Not used | unused, finder |", text)
        self.assertIn("2 skills, 1 agents, 1 hooks, 0 workflows; CLAUDE.md 2 lines, memory 0 lines", text)
        self.assertIn("| Version 1 |", text)
        self.assertIn("not measured |", text)
        growth = Path(self.ideas / "audit" / "growth.jsonl").read_text().strip().splitlines()
        self.assertEqual(json.loads(growth[0])["hooks"], ["PreToolUse:guard.py"])

    def test_second_run_reads_only_changed_transcripts(self):
        self.run_week()
        session(self.folder, "d", "2026-10-22")
        with open(self.folder / "b.jsonl", "a") as fh:
            fh.write(json.dumps(assistant(30, "late")).replace("2026-10-05", "2026-10-20") + "\n")
        os.utime(self.folder / "b.jsonl", (2_000_000_000, 2_000_000_000))
        out = self.run_week("2026-10-26")
        self.assertEqual(out["read"], 2)
        self.assertEqual(out["sessions"], 4)
        rows = mod.load_jsonl(str(self.ideas / "audit" / "sessions.jsonl"))
        b = next(r for r in rows if r["id"] == "b")
        self.assertEqual(b["messages"], 3)
        self.assertEqual(b["summarised"], "2026-10-26")
        growth = Path(self.ideas / "audit" / "growth.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(growth), 2)

    def test_deleted_transcript_keeps_its_line(self):
        self.run_week()
        os.remove(self.folder / "c.jsonl")
        out = self.run_week("2026-10-26")
        self.assertEqual(out["sessions"], 3)

    def test_v1_column_and_retire_proposal(self):
        (self.ideas / "audit").mkdir()
        (self.ideas / "audit" / "v1-baseline.json").write_text(json.dumps({"column": {"Cost": "69.4 min per issue"}}))
        first = self.run_week("2026-09-27")
        self.assertEqual(first["proposals"], [], "no retirement on the first table")
        (self.home / "skills" / "new-this-month").mkdir()
        (self.home / "skills" / "new-this-month" / "SKILL.md").write_text("x")
        out = self.run_week()
        self.assertNotIn("retire the skill new-this-month: not used in two audits, yes or no?", out["proposals"])
        text = Path(out["page"]).read_text()
        self.assertIn("| Cost | 2 sessions, 0.2 h; per change note: not measured until stage two | 1 sessions, 0.1 h; per change note: not measured until stage two | 69.4 min per issue |", text)
        self.assertIn("retire the skill unused: not used in two audits, yes or no?", out["proposals"])
        self.assertIn("retire the agent finder: not used in two audits, yes or no?", out["proposals"])
        self.assertNotIn("retire the skill coderules: not used in two audits, yes or no?", out["proposals"])

    def test_month_window(self):
        import datetime as dt
        self.assertEqual(mod.month_window(dt.date(2026, 10, 25)), ("2026-10", "2026-09", "2026-11-01"))
        self.assertEqual(mod.month_window(dt.date(2026, 12, 28)), ("2026-12", "2026-11", "2027-01-01"))
        self.assertEqual(mod.month_window(dt.date(2026, 1, 4)), ("2026-01", "2025-12", "2026-02-01"))

    def test_refuses_missing_ideas_repo(self):
        self.assertEqual(mod.main(["--ideas", str(self.ideas / "nope"), "--projects", str(self.projects)]), 2)


if __name__ == "__main__":
    unittest.main()
