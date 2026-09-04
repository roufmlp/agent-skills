#!/usr/bin/env python3
"""Refuse a run-issues spawn whose run_in_background is not the value its type needs.

Blast radius, before anything else. This is a `PreToolUse` hook on `Agent|Task`.
It reads one field of one tool call: `tool_input.subagent_type`. If that value
does not start with `run-issues-`, the call passes untouched — so
`parallel-hunt`, every other skill in this pack, and ordinary sessions never see
this gate at all. Of the spawns it does judge, it refuses two shapes, keyed on
the agent type:

    run-issues-verify-gate    refused unless run_in_background is the boolean true
    every other run-issues-*  refused unless run_in_background is the boolean false

Absent counts as wrong in both cases. It reads no file, writes nothing, and
refuses nothing else. Registering it is a separate step: see `hooks/README.md`.

Why it is a script and not a line of prose. `skills/run-issues/SKILL.md` orders
every spawn in a run to carry the field, named. That was a reminder, and
the steering rule in this pack (`steering/CLAUDE.md`, "Refuse, or state a fact.
Never ask an agent to remember.") is that a reminder is either made mechanical
or let go — one run mixed the values with no instruction at all. This gate is
the mechanical form, and the fix travels in the refusal message.

Why the verify gate is the exception. Until 2026-09-04 this gate required false
everywhere, and the only concurrent shape that left was both gates in one
message. One run of fifteen issues never once produced that shape: every gate
pair went out in two messages, the second waiting on the first, and
`run_timings.py` priced the serialisation at 97 minutes, about a fifth of the
run. The runner accepted a correction and repeated the fault one turn later,
which is what a reminder does. A verify gate in the background needs no second
call in the same message: the review gate follows in the foreground on the next
turn, and the two overlap by construction. The verify gate's brief names Read
and Write and drives the browser, and none of the tools a background agent
drops is among them.

Scope limit worth stating twice, because it is the part that surprises people.
The gate keys on the agent type, not on the session, because only the run-issues
runner spawns those types. It therefore cannot see a spawn that omits the type,
and it cannot see a turn that ends without spawning at all. That second class is
real: on 2026-08-17 at 06:34Z a runner wrote that it was spawning the next issue,
ended its turn, and never made the call. Nothing a `PreToolUse` hook can do
reaches a call that was never made; a resume cron caught it.

Evidence behind the false rule, and a correction. An audit first blamed eight
long stalls in one run on background spawns. A re-measure the following day
joined every spawn to its subagent transcript and refuted that: task
notifications woke the runner within seconds of every completion, and the gaps
were the workers' own runtimes. So the false rule saves no clock. It stands on
the Agent tool's own guidance — pass false when the next action depends on the
result — and an implementer, a review gate and the finale are each the runner's
next dependency.

Drill it before you trust it. `python3 run-issues-foreground-gate.py --drill`
runs eleven payloads through `decide()` and prints each against the exit code it
must produce; nothing else is needed and no fixture file ships. Or pipe one JSON
payload per run by hand and check the exit code:

    echo '{"tool_input":{"subagent_type":"run-issues-implementer",
      "run_in_background":true}}' | python3 run-issues-foreground-gate.py   # 2

    echo '{"tool_input":{"subagent_type":"run-issues-verify-gate",
      "run_in_background":true}}' | python3 run-issues-foreground-gate.py   # 0

    echo '{"tool_input":{"subagent_type":"run-issues-implementer",
      "run_in_background":false}}' | python3 run-issues-foreground-gate.py  # 0

    echo '{"tool_input":{"subagent_type":"parallel-hunt-finder",
      "run_in_background":true}}' | python3 run-issues-foreground-gate.py   # 0

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import json
import sys

VERIFY = "run-issues-verify-gate"

AFK = (
    "\n\nTHIS NEVER WAITS FOR THE HUMAN AND IT IS NOT A HALT. Nobody is at the "
    "keyboard during a run. Do not write a HALT BLOCK for this, do not ask, and do not end "
    "the run — reissuing the call is yours to do, now.\n"
    "(Gate: ~/.claude/hooks/run-issues-foreground-gate.py)"
)


def decide(payload):
    """Return (exit_code, message). Pure, so the drill can drive it."""
    tool_input = payload.get("tool_input") or {}
    agent_type = str(tool_input.get("subagent_type") or "")
    if not agent_type.startswith("run-issues-"):
        return 0, ""
    value = tool_input.get("run_in_background")
    shown = "absent" if value is None else repr(value)

    if agent_type == VERIFY:
        if value is True:
            return 0, ""
        return 2, (
            f"run-issues spawn refused: Agent({agent_type}) carries "
            f"run_in_background {shown}. The verify gate is the ONE run-issues "
            f"spawn that runs in the background, so that the review gate can "
            f"run beside it. Reissue this exact call with run_in_background: "
            f"true. Then, in your NEXT turn, spawn the review gate with "
            f"run_in_background: false. Do not wait for the verify gate's "
            f"notification before spawning the review gate. The round ends "
            f"when BOTH verdicts are in: the review gate's return and the "
            f"verify gate's task notification, in either order. Read both "
            f"before step 4." + AFK
        )

    if value is False:
        return 0, ""
    return 2, (
        f"run-issues spawn refused: Agent({agent_type}) carries "
        f"run_in_background {shown}. Every run-issues spawn other than the "
        f"verify gate names the field and sets it false — the runner has "
        f"nothing to do while this worker runs. Reissue this exact call with "
        f"run_in_background: false." + AFK
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Unreadable input is not a spawn to judge; stay out of the way.
    code, message = decide(payload)
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drill":
        def spawn(kind, **fields):
            return decide({"tool_input": {"subagent_type": kind, **fields}})[0]

        checks = [
            ("implementer false", spawn("run-issues-implementer", run_in_background=False), 0),
            ("implementer true", spawn("run-issues-implementer", run_in_background=True), 2),
            ("implementer absent", spawn("run-issues-implementer"), 2),
            ("review gate false", spawn("run-issues-review-gate", run_in_background=False), 0),
            ("critical review true", spawn("run-issues-review-gate-critical", run_in_background=True), 2),
            ("verify gate true", spawn(VERIFY, run_in_background=True), 0),
            ("verify gate false", spawn(VERIFY, run_in_background=False), 2),
            ("verify gate absent", spawn(VERIFY), 2),
            ("verify gate string 'true'", spawn(VERIFY, run_in_background="true"), 2),
            ("foreign type, true", spawn("general-purpose", run_in_background=True), 0),
            ("foreign type, absent", spawn("Explore"), 0),
        ]
        bad = 0
        for label, code, want in checks:
            ok = code == want
            bad += not ok
            print(f"{'ok  ' if ok else 'FAIL'}  {label}: exit {code}, wanted {want}")
        sys.exit(1 if bad else 0)
    sys.exit(main())
