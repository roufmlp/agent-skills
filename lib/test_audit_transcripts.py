#!/usr/bin/env python3
"""Drill for audit_transcripts.py: hours, token dedupe, pricing, context, questions, interruptions.

    python3 test_audit_transcripts.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audit_transcripts as mod

T0 = "2026-10-05T10:00:00.000Z"


def ts(minutes):
    base = 10 * 60 + minutes
    return f"2026-10-05T{base // 60:02d}:{base % 60:02d}:00.000Z"


def assistant(minutes, mid, model="claude-opus-5-5", out=100, read=50_000, write5=1_000, tools=(), text="", version="2.1.300"):
    content = [{"type": "text", "text": text}] if text else []
    for name in tools:
        content.append({"type": "tool_use", "id": "t" + name, "name": name, "input": {"skill": "coderules", "subagent_type": "Explore"}})
    return {
        "type": "assistant", "timestamp": ts(minutes), "version": version, "cwd": "/Users/x/code/orderflow", "gitBranch": "main",
        "message": {"id": mid, "model": model, "role": "assistant", "content": content,
                    "usage": {"input_tokens": 10, "cache_read_input_tokens": read, "cache_creation_input_tokens": write5,
                              "output_tokens": out, "cache_creation": {"ephemeral_5m_input_tokens": write5, "ephemeral_1h_input_tokens": 0}}},
    }


def user(minutes, text, version="2.1.300"):
    return {"type": "user", "timestamp": ts(minutes), "version": version, "cwd": "/Users/x/code/orderflow",
            "message": {"role": "user", "content": text}}


def result(minutes, body):
    return {"type": "user", "timestamp": ts(minutes), "version": "2.1.300",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": body}]}}


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


class Summarise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name)
        self.folder = self.store / "-Users-x-code-orderflow--claude-worktrees-run-1"
        self.main = self.folder / "s1.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_hours_tokens_cost_and_context(self):
        write(self.main, [
            user(0, "/run-issues 1-3"),
            assistant(1, "m1", out=100),
            assistant(1, "m1", out=100),  # a repeated row: counted once
            assistant(5, "m2", out=200, read=100_000),
            {"type": "system", "subtype": "compact_boundary", "timestamp": ts(6)},
            assistant(10, "m3", model="claude-haiku-5-5", out=10, read=1_000, write5=0),
            {"type": "cost-state", "totalCostUSD": 1.5, "modelUsage": {"claude-opus-5-5": {"inputTokens": 1, "outputTokens": 900}}},
        ])
        s = mod.summarise(str(self.main))
        self.assertEqual(s["project"], "orderflow")
        self.assertEqual(s["kind"], "run")
        self.assertAlmostEqual(s["hours"], 10 / 60, places=3)
        self.assertEqual(s["messages"], 3)
        self.assertEqual(s["tokens"]["claude-opus-5-5"]["output"], 300)
        self.assertEqual(s["tokens"]["claude-opus-5-5"]["cache_read"], 150_000)
        # opus: 2 msgs: input 20*4 + write 2000*5 + read 150000*0.2 + out 300*20 = 80+10000+30000+6000 = 46080 / 1e6
        # haiku short: input 10*0.1 + read 1000*0.01 + out 10*0.5 = 1+10+5 = 16 / 1e6
        self.assertAlmostEqual(s["cost_usd"], 0.046096, places=6)
        self.assertEqual(s["cost_state_usd"], 1.5)
        self.assertEqual(s["app_tokens"]["claude-opus-5-5"]["output"], 900)
        self.assertEqual(s["context"]["start"], 51_010)
        self.assertEqual(s["context"]["largest"], 101_010)
        self.assertEqual(s["context"]["compactions"], 1)
        self.assertEqual(s["interruptions"], [])

    def test_unpriced_model_is_named_not_zeroed(self):
        write(self.main, [user(0, "hello"), assistant(1, "m1", model="claude-new-9")])
        s = mod.summarise(str(self.main))
        self.assertEqual(s["cost_usd"], 0)
        self.assertIn("claude-new-9", s["unpriced"])

    def test_questions_skills_agents_drift(self):
        write(self.main, [
            user(0, "direct road, issue 12"),
            assistant(1, "m1", tools=("Skill", "Agent", "AskUserQuestion"), text="Which? ❓ one ❓ two"),
            result(2, "DRIFT: screen moved\nDRIFT: pattern"),
            {"type": "user", "timestamp": ts(3), "attributionSkill": "writingrules", "message": {"role": "user", "content": "x"}},
        ])
        s = mod.summarise(str(self.main))
        self.assertEqual(s["kind"], "direct-road")
        self.assertEqual(s["questions"], {"tool": 1, "marker": 2})
        self.assertEqual(s["skills"], {"coderules": 1})
        self.assertEqual(s["agents"], {"Explore": 1})
        self.assertEqual(s["skills_attributed"], {"writingrules": 1})
        self.assertEqual(s["drift"], 2)

    def test_interruption_causes(self):
        write(self.main, [
            user(0, "start"),
            assistant(1, "m1", text="Done. Shall I continue?"),          # 45 min gap: question
            user(46, "yes"),
            assistant(47, "m2", tools=("Bash",)),                         # 40 min gap, tool open
            result(87, "ok"),
            assistant(88, "m3", text="Finished."),                        # 31 min gap, turn ended
            {"type": "system", "subtype": "stop_hook_summary", "timestamp": ts(88)},  # read past this
            user(119, "more", version="2.1.301"),                        # version changed across the gap
            assistant(120, "m4", text="ok"),
            {"type": "system", "subtype": "api_error", "timestamp": ts(121)},
            assistant(160, "m5", text="retrying"),                        # 39 min after an error
            user(161, "You've reached your usage limit. Resets at 3pm."),
            assistant(200, "m6", text="back"),                            # 39 min after a limit
        ])
        s = mod.summarise(str(self.main))
        causes = [i["cause"] for i in s["interruptions"]]
        self.assertEqual(causes, [
            "question to Abdul",
            "tool call open: permission prompt or long command",
            "turn ended: waiting for Abdul (version changed: restart)",
            "error",
            "usage limit",
        ])
        self.assertEqual(s["limit_waits"], 1)
        self.assertEqual(s["api_errors"], 1)
        self.assertEqual([i["minutes"] for i in s["interruptions"]], [45.0, 40.0, 31.0, 39.0, 39.0])

    def test_subagent_fills_a_gap_and_adds_hours_and_tokens(self):
        write(self.main, [user(0, "go"), assistant(1, "m1", tools=("Agent",)), result(50, "agent done"), assistant(51, "m2")])
        sub = self.folder / "s1" / "subagents" / "agent-a.jsonl"
        write(sub, [assistant(2, "a1", out=5), assistant(25, "a2", out=5), assistant(45, "a3", out=5)])
        s = mod.summarise(str(self.main))
        self.assertEqual(s["interruptions"], [])
        self.assertEqual(s["subagents"], 1)
        self.assertAlmostEqual(s["subagent_hours"], 43 / 60, places=3)
        self.assertEqual(s["tokens"]["claude-opus-5-5"]["output"], 215)
        self.assertEqual(s["messages"], 2)

    def test_skips_prompt_blobs_and_returns_none_without_timestamps(self):
        write(self.main, [{"type": "api-request-blob", "message": {"content": "x" * 10}}, {"type": "mode", "mode": "normal"}])
        self.assertIsNone(mod.summarise(str(self.main)))

    def test_first_prompt_skips_meta_and_reminders(self):
        write(self.main, [
            {"type": "user", "timestamp": ts(0), "isMeta": True, "message": {"role": "user", "content": "meta"}},
            user(0, "<system-reminder>x</system-reminder>"),
            user(1, "/parallel-hunt find bugs"),
        ])
        s = mod.summarise(str(self.main))
        self.assertEqual(s["first_prompt"], "/parallel-hunt find bugs")
        self.assertEqual(s["kind"], "hunt")


class Helpers(unittest.TestCase):
    def test_project_of(self):
        self.assertEqual(mod.project_of("-Users-roufmlp-code-orderflow"), "orderflow")
        self.assertEqual(mod.project_of("-Users-roufmlp-code-orderflow--claude-worktrees-run-12ab"), "orderflow")
        self.assertEqual(mod.project_of("-private-tmp-claude-501--Users-roufmlp-code-procurement--claude-worktrees-x-y"), "procurement")
        self.assertEqual(mod.project_of("-Users-roufmlp--claude-skills"), "skills")
        self.assertEqual(mod.project_of("-Users-roufmlp--claude-skills--claude-worktrees-direct-road-35"), "skills")
        self.assertEqual(mod.project_of("-private-var-folders-6s-T-run-harness-giah9v7u"), "run-harness")
        self.assertEqual(mod.project_of("-Users-roufmlp-Library-Application-Support-Claude-scratch-workspaces-b-2-scratch-2026-09-27-231d27"), "cowork-scratch")
        self.assertEqual(mod.project_of("-Users-roufmlp-Claude-CoWork-01-untitled-folder--claude-worktrees-x-7a02b7"), "cowork")

    def test_max_concurrent(self):
        self.assertEqual(mod.max_concurrent([(1, 5), (2, 3), (4, 6), (7, 8)]), 2)
        self.assertEqual(mod.max_concurrent([]), 0)

    def test_haiku_price_by_context(self):
        self.assertEqual(mod.price_of("claude-haiku-5-5", 50_000), mod.PRICES["claude-haiku-5-5-short"])
        self.assertEqual(mod.price_of("claude-haiku-5-5", 150_000), mod.PRICES["claude-haiku-5-5"])
        self.assertIsNone(mod.price_of("claude-unknown", 1))
        self.assertEqual(mod.price_of("claude-haiku-4-5-20251001", 1), mod.PRICES["claude-haiku-4-5"])
        self.assertEqual(mod.price_of("claude-opus-5-5[1m]", 1), mod.PRICES["claude-opus-5-5"])


if __name__ == "__main__":
    unittest.main()
