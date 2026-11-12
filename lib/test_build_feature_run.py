#!/usr/bin/env python3
"""Drill for workflows/build-feature-run.js without a live run.

The script is plain JavaScript that sees only `args` and five functions the
runtime gives it (`agent`, `parallel`, `log`, `phase`, and its own `return`).
This drill runs it under node with those functions faked: each agent call is
answered from a scenario by its label, and every call's label and prompt are
kept. So the script's own logic is tested, and no agent runs: the stop forms,
the second failure, the gate before local main, the fix rounds.

    python3 test_build_feature_run.py

It needs `node` on the path; every case is skipped without it.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "workflows" / "build-feature-run.js"
NODE = shutil.which("node")

HARNESS = r"""
const fs = require('fs')
const [scriptPath, scenarioPath] = process.argv.slice(2)
const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'))
const source = fs.readFileSync(scriptPath, 'utf8').replace('export const meta', 'const meta')
const calls = []
const queues = {}
async function agent(prompt, opts) {
  calls.push({ label: opts.label, role: opts.agentType, phase: opts.phase, prompt })
  for (const rule of scenario.answers) {
    if (!new RegExp(rule.label).test(opts.label)) continue
    queues[rule.label] = queues[rule.label] || [...rule.returns]
    const queue = queues[rule.label]
    const out = queue.length > 1 ? queue.shift() : queue[0]
    if (out !== null) {
      for (const key of opts.schema.required) {
        if (!(key in out)) throw new Error(`scenario answer for ${opts.label} lacks ${key}`)
      }
    }
    return out
  }
  throw new Error('no scenario answer for ' + opts.label)
}
const parallel = fns => Promise.all(fns.map(f => f()))
const logs = []
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const run = new AsyncFunction('args', 'agent', 'parallel', 'log', 'phase', source)
run(scenario.args, agent, parallel, m => logs.push(m), () => {}).then(result => {
  process.stdout.write(JSON.stringify({ result, calls, logs }))
}).catch(err => { console.error(err); process.exit(1) })
"""

SHA = "a" * 40
NO_STOP = {"kind": "none", "class": "none", "question": "", "default": "", "tool": ""}
DONE = {"outcome": "done", "commit": SHA, "line": "done"}
BUILT = {"line": "built it", "edits": [], "defaults": [], "keeps": [], "needs_note": [], "stop": NO_STOP}
PASS = {"verdict": "PASS", "line": "all steps passed", "stop": NO_STOP}
REJECT = {"verdict": "REJECT", "line": "REJECT: the label is wrong", "stop": NO_STOP}
FINDINGS = {"verdict": "FINDINGS", "line": "FINDINGS: step 3 fails", "stop": NO_STOP}
SOUND = {"outcome": "sound", "line": "Sound: both attempts missed the label", "stop": NO_STOP}

ROLES = {role: {"model": "sonnet", "effort": "high", "override": False}
         for role in ("implementer", "verifier", "reviewer", "note-checker", "merger",
                      "final-verifier", "final-reviewer")}


def note(number, state="not started", waits_for=(), **more):
    return {"number": number, "path": f"changes/bubble/{number}-x.md", "waits_for": list(waits_for),
            "screens": "none", "risk": "none", "state": state, "strikes": 0, "attempts": 0,
            "last_report": "", "fresh": False, "rearmed": False, "branch": f"note/bubble/{number}",
            "worktree": f"/repo/.claude/worktrees/note-bubble-{number}", **more}


def args(notes, **more):
    return {"feature": "bubble", "tree": "/repo/.claude/worktrees/feature-bubble", "repo": "/repo",
            "main": "main", "reports": "/repo/.git/build-feature/bubble", "batch": "batch-1",
            "started": "2026-11-12 09:00", "staging": None, "risk": False, "notes": notes,
            "roles": ROLES, "earlier": {"defaults": [], "edits": [], "final": [], "tooling": [], "strikes": {}},
            "ruling_wait_seconds": 900, "gate_open": [], "away": [], "held": False, **more}


def answers(*rules):
    """Scenario rules, first match wins; these defaults sit behind the given ones."""
    given = [{"label": label, "returns": returns} for label, returns in rules]
    return given + [
        {"label": r"implementer", "returns": [BUILT]},
        {"label": r"^note \d+: (verifier|reviewer)", "returns": [PASS]},
        {"label": r"note checker", "returns": [SOUND]},
        {"label": r"^final (verifier|reviewer)", "returns": [PASS]},
        {"label": r".", "returns": [DONE]},  # every merger job
    ]


@unittest.skipUnless(NODE, "node is not on the path")
class Script(unittest.TestCase):

    def run_script(self, scenario_args, rules=()):
        with tempfile.TemporaryDirectory() as tmp:
            harness = pathlib.Path(tmp) / "harness.js"
            harness.write_text(HARNESS)
            scenario = pathlib.Path(tmp) / "scenario.json"
            scenario.write_text(json.dumps({"args": scenario_args, "answers": answers(*rules)}))
            done = subprocess.run([NODE, str(harness), str(SCRIPT), str(scenario)],
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)
        return out["result"], out["calls"]

    def labels(self, calls, pattern):
        return [c["label"] for c in calls if re.search(pattern, c["label"])]

    def prompt(self, calls, pattern):
        found = [c["prompt"] for c in calls if re.search(pattern, c["label"])]
        self.assertTrue(found, f"no call matches {pattern}: {[c['label'] for c in calls]}")
        return found[-1]

    def state_of(self, result, number):
        return next(n["state"] for n in result["notes"] if n["number"] == number)

    # ── the road with no ruling ──

    def test_a_run_with_no_ruling_merges_as_before(self):
        result, calls = self.run_script(args([note("01"), note("02", waits_for=["01"])]))
        self.assertEqual(result["state"], "merged")
        self.assertEqual(len(self.labels(calls, r"^main-out$")), 1)
        self.assertEqual(self.labels(calls, r"^fix round"), [])
        self.assertEqual(result["ruling_wait_seconds"], 900)
        self.assertEqual((result["stops"], result["fix_notes"]), ([], []))

    # ── a stop carries its class, its question and its default ──

    def test_a_question_stops_one_note_with_its_typed_parts_and_the_others_go_on(self):
        stop = {"kind": "question", "class": "money", "question": "the count may show a price",
                "default": "no price on the bubble", "tool": ""}
        result, calls = self.run_script(
            args([note("01"), note("02")]),
            [(r"^note 01: implementer", [{**BUILT, "stop": stop}])])
        self.assertEqual(self.state_of(result, "01"), "stopped: the count may show a price")
        self.assertTrue(self.state_of(result, "02").startswith("merged"))
        self.assertEqual(result["stops"], [{"number": "01", "role": "implementer", "kind": "question",
                                            "class": "money", "question": "the count may show a price",
                                            "default": "no price on the bubble"}])
        report = self.prompt(calls, r"^report: stopped$")
        self.assertIn("01: [money] the count may show a price Default: no price on the bubble", report)
        self.assertEqual(self.labels(calls, r"^note 01: verifier"), [], "nothing is built past the stop")
        self.assertEqual(self.labels(calls, r"^final verifier"), [], "no final check while a note is stopped")

    def test_the_note_checker_stops_with_the_same_typed_parts(self):
        stop = {"kind": "question", "class": "none", "question": "the label is Reports or Messages",
                "default": "keep Reports", "tool": ""}
        result, _ = self.run_script(
            args([note("01")]),
            [(r"^note 01: verifier", [REJECT]),
             (r"note checker", [{"outcome": "stopped", "line": "Stopped: the label", "stop": stop}])])
        self.assertEqual(self.state_of(result, "01"), "stopped: the label is Reports or Messages")
        self.assertEqual(result["stops"][0]["default"], "keep Reports")
        self.assertEqual(result["stops"][0]["role"], "note-checker")

    def test_a_stop_with_no_typed_class_is_never_read_as_outside_the_risk_classes(self):
        result, _ = self.run_script(
            args([note("01")]),
            [(r"^note 01: verifier", [REJECT]),
             (r"note checker", [{"outcome": "stopped", "line": "Stopped: a new rule", "stop": NO_STOP}])])
        self.assertEqual(result["stops"][0]["class"], "unclassified")
        self.assertEqual(result["stops"][0]["question"], "Stopped: a new rule")

    # ── tool faults ──

    def test_a_tool_fault_is_a_tooling_stop_with_no_strike_and_no_decide_line(self):
        line = "PreToolUse:Write hook error: This session is running in an isolated git worktree"
        stop = {"kind": "tooling", "class": "none", "question": line, "default": "", "tool": "desktop app"}
        result, calls = self.run_script(
            args([note("01")]),
            [(r"^note 01: reviewer", [{**PASS, "verdict": "REJECT", "stop": stop}])])
        self.assertEqual(self.state_of(result, "01"), f"stopped: tooling: desktop app: {line}")
        self.assertEqual(result["notes"][0]["strikes"], 0)
        self.assertEqual(result["stops"], [{"number": "01", "role": "reviewer", "kind": "tooling",
                                            "tool": "desktop app", "line": line}])
        report = self.prompt(calls, r"^report: stopped$")
        self.assertIn(f"2026-11-12 01: desktop app: {line}", report)
        decide = report.split("Decide, one line per question")[1].split("\n\n")[0]
        self.assertIn("none", decide)
        self.assertNotIn("isolated git worktree", decide)

    def test_earlier_tooling_stops_stay_in_the_report(self):
        earlier = {"defaults": [], "edits": [], "final": [], "strikes": {},
                   "tooling": ["2026-11-11 02: hook: the note check refused"]}
        _, calls = self.run_script(args([note("01")], earlier=earlier))
        self.assertIn("2026-11-11 02: hook: the note check refused", self.prompt(calls, r"^report: start$"))

    # ── three strikes, the re-arm and the second failure ──

    def test_three_strikes_fail_a_note_that_had_no_re_arm(self):
        result, _ = self.run_script(args([note("01")]), [(r"^note 01: verifier", [REJECT])])
        self.assertEqual(self.state_of(result, "01"), "failed")
        self.assertEqual(result["notes"][0]["strikes"], 3)

    def test_a_second_failure_after_the_re_arm_waits_for_the_human(self):
        result, calls = self.run_script(
            args([note("01", rearmed=True), note("02")]), [(r"^note 01: verifier", [REJECT])])
        self.assertEqual(self.state_of(result, "01"), "waiting: failed again after its re-arm")
        self.assertTrue(self.state_of(result, "02").startswith("merged"), "the other notes continue")
        self.assertEqual(result["state"], "stopped")

    def test_a_waiting_note_does_not_run_and_holds_only_the_notes_that_wait_for_it(self):
        result, calls = self.run_script(args([
            note("01", state="waiting: a money question"), note("02", waits_for=["01"]), note("03")]))
        self.assertEqual(self.labels(calls, r"^note 0[12]: implementer"), [])
        self.assertEqual(self.state_of(result, "02"), "not started")
        self.assertTrue(self.state_of(result, "03").startswith("merged"))
        self.assertEqual(self.labels(calls, r"^final verifier"), [])

    # ── the fresh tree ──

    def test_a_fresh_note_refuses_to_reuse_its_old_tree(self):
        _, calls = self.run_script(args([note("01", fresh=True)]))
        prompt = self.prompt(calls, r"^note 01: worktree$")
        self.assertIn("Fresh: yes", prompt)
        self.assertIn("If Fresh is yes and the worktree exists, stop: answer outcome error", prompt)

    # ── the gate before local main ──

    def test_a_run_with_an_unconfirmed_ruling_holds_before_local_main(self):
        away = ['02: the count at zero Road taken: "hide it". Ruled by default on 2026-11-12. Touched: none. Undo: one line.']
        result, calls = self.run_script(args([note("01")], gate_open=["02"], away=away))
        self.assertEqual(result["state"], "held")
        self.assertEqual(len(self.labels(calls, r"^final verifier")), 1, "the final check completes first")
        self.assertEqual(self.labels(calls, r"^main-out$"), [], "nothing merges into local main")
        report = self.prompt(calls, r"^report: held$")
        self.assertIn("State: held", report)
        self.assertIn("Ruled while you were away", report)
        self.assertIn(away[0], report)
        self.assertIn("1 ruling(s) to confirm before the merge into main", result["notice"])
        self.assertIsNone(result["mergeCommit"])

    def test_confirmed_rulings_do_not_hold_the_merge(self):
        result, calls = self.run_script(args([note("01")], gate_open=[], away=["02: confirmed line"]))
        self.assertEqual(result["state"], "merged")
        self.assertIn("02: confirmed line", self.prompt(calls, r"^report: merged, before main-out$"))

    def test_a_held_run_goes_straight_to_the_merge_once_the_gate_is_clear(self):
        result, calls = self.run_script(args([note("01", state="merged abc123456")], held=True))
        self.assertEqual(result["state"], "merged")
        self.assertEqual(self.labels(calls, r"^final (verifier|reviewer)|^main-in$"), [])
        self.assertEqual(len(self.labels(calls, r"^main-out$")), 1)

    def test_a_held_run_whose_gate_is_still_open_stays_held(self):
        result, calls = self.run_script(args([note("01", state="merged abc123456")], held=True, gate_open=["02"]))
        self.assertEqual(result["state"], "held")
        self.assertEqual(self.labels(calls, r"^main-out$|^final verifier"), [])

    def test_a_held_run_checks_again_when_main_moved(self):
        moved = {"outcome": "main moved", "commit": "", "line": "main moved"}
        result, calls = self.run_script(
            args([note("01", state="merged abc123456")], held=True), [(r"^main-out$", [moved, DONE])])
        self.assertEqual(result["state"], "merged")
        self.assertEqual(len(self.labels(calls, r"^final verifier")), 1)
        self.assertEqual(len(self.labels(calls, r"^main-out$")), 2)

    # ── the final check's fix rounds ──

    def test_the_fix_rounds_are_one_named_constant(self):
        self.assertRegex(SCRIPT.read_text(), r"(?m)^const FIX_ROUNDS = 3\b")

    def test_the_final_check_gets_three_fix_rounds_and_then_stops(self):
        result, calls = self.run_script(args([note("01")]), [(r"^final verifier", [FINDINGS])])
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(self.labels(calls, r"^fix round"), [
            "fix round 1: implementer", "fix round 2: implementer", "fix round 3: implementer"])
        self.assertEqual(len(self.labels(calls, r"^final verifier")), 4)
        self.assertEqual(self.labels(calls, r"^main-out$"), [])
        self.assertIn("Attempt: 3 of 3", self.prompt(calls, r"^fix round 3"))

    def test_a_final_check_that_passes_after_the_second_fix_round_merges(self):
        result, calls = self.run_script(
            args([note("01")]), [(r"^final verifier", [FINDINGS, FINDINGS, PASS])])
        self.assertEqual(result["state"], "merged")
        self.assertEqual(len(self.labels(calls, r"^fix round")), 2)

    def test_a_fix_round_gets_every_finding_in_one_batch(self):
        review = {"verdict": "FINDINGS", "line": "FINDINGS: a rule no note names", "stop": NO_STOP}
        _, calls = self.run_script(
            args([note("01")]),
            [(r"^final verifier", [FINDINGS, PASS]), (r"^final reviewer", [review, PASS])])
        prompt = self.prompt(calls, r"^fix round 1")
        self.assertIn("final verifier: FINDINGS: step 3 fails", prompt)
        self.assertIn("final reviewer: FINDINGS: a rule no note names", prompt)
        self.assertIn("final-1-verifier.md", prompt)
        self.assertIn("final-1-reviewer.md", prompt)
        self.assertEqual(len(self.labels(calls, r"^fix round")), 1)

    def test_a_finding_that_needs_a_new_test_becomes_a_fix_note_not_a_stop(self):
        needs = {**BUILT, "needs_note": ["the tracking page draws the card and no test covers it"]}
        result, calls = self.run_script(
            args([note("01")]),
            [(r"^final verifier", [FINDINGS]), (r"^fix round", [needs])])
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(result["fix_notes"], ["the tracking page draws the card and no test covers it"])
        self.assertEqual(len(self.labels(calls, r"^fix round")), 1, "no further round can pass without the note")
        self.assertEqual(len(self.labels(calls, r"^final verifier")), 1)
        self.assertIn("Fix note needed: the tracking page draws the card and no test covers it",
                      result["finalLines"])

    def test_a_tool_fault_in_the_final_check_spends_no_fix_round(self):
        line = "PreToolUse:Write hook error: the report file is in the base repo checkout"
        stop = {"kind": "tooling", "class": "none", "question": line, "default": "", "tool": "desktop app"}
        result, calls = self.run_script(
            args([note("01")]), [(r"^final reviewer", [{**FINDINGS, "stop": stop}])])
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(self.labels(calls, r"^fix round"), [])
        self.assertEqual(result["stops"], [{"number": "final", "role": "final-reviewer", "kind": "tooling",
                                            "tool": "desktop app", "line": line}])

    def test_main_moved_runs_the_final_check_again_with_no_further_fix_round(self):
        moved = {"outcome": "main moved", "commit": "", "line": "main moved"}
        result, calls = self.run_script(
            args([note("01")]),
            [(r"^main-out$", [moved, DONE]), (r"^final verifier", [PASS, FINDINGS])])
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(self.labels(calls, r"^fix round"), [])


if __name__ == "__main__":
    unittest.main()
