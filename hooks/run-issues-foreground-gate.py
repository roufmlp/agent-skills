#!/usr/bin/env python3
"""Refuse a run-issues spawn that does not name run_in_background: false.

Blast radius, before anything else. This is a `PreToolUse` hook on `Agent|Task`.
It reads one field of one tool call: `tool_input.subagent_type`. If that value
does not start with `run-issues-`, the call passes untouched — so
`parallel-hunt`, every other skill in this pack, and ordinary sessions never see
this gate at all. Of the spawns it does judge, it refuses exactly one shape: a
`run-issues-*` spawn whose `run_in_background` is anything other than the
boolean `false`, absent included. It reads no file, writes nothing, and refuses
nothing else. Registering it is a separate step: see `hooks/README.md`.

Why it is a script and not a line of prose. `skills/run-issues/SKILL.md` orders
every spawn in a run to carry the field, named, false. That was a reminder, and
the steering rule in this pack (`steering/CLAUDE.md`, "Refuse, or state a fact.
Never ask an agent to remember.") is that a reminder is either made mechanical
or let go — one run mixed the values with no instruction at all. This gate is
the mechanical form, and the fix travels in the refusal message.

Scope limit worth stating twice, because it is the part that surprises people.
The gate keys on the agent type, not on the session, because only the run-issues
runner spawns those types. It therefore cannot see a spawn that omits the type,
and it cannot see a turn that ends without spawning at all. That second class is
real: on 2026-08-17 at 06:34Z a runner wrote that it was spawning the next issue,
ended its turn, and never made the call. Nothing a `PreToolUse` hook can do
reaches a call that was never made; a resume cron caught it.

Evidence behind the rule, and a correction. An audit first blamed eight long
stalls in one run on background spawns. A re-measure the following day joined
every spawn to its subagent transcript and refuted that: task notifications woke
the runner within seconds of every completion, and the gaps were the workers' own
runtimes. Expect this gate to save no clock. What it buys is that the run stops
betting on notification delivery holding across harness versions, which is the
Agent tool's own guidance — pass false when the next action depends on the result.

Drill it by hand before you trust it. Pipe one JSON payload per run and check the
exit code; nothing else is needed and no fixture file ships:

    echo '{"tool_input":{"subagent_type":"run-issues-implementer",
      "run_in_background":true}}' | python3 run-issues-foreground-gate.py   # 2

    echo '{"tool_input":{"subagent_type":"run-issues-implementer"}}' \
      | python3 run-issues-foreground-gate.py                              # 2

    echo '{"tool_input":{"subagent_type":"run-issues-implementer",
      "run_in_background":false}}' | python3 run-issues-foreground-gate.py  # 0

    echo '{"tool_input":{"subagent_type":"parallel-hunt-finder",
      "run_in_background":true}}' | python3 run-issues-foreground-gate.py   # 0

The first two must refuse, the last two must pass. `decide()` is pure, so a test
file can drive it directly without a subprocess.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import json
import sys


def decide(payload):
    """Return (exit_code, message). Pure, so the drill can drive it."""
    tool_input = payload.get("tool_input") or {}
    agent_type = str(tool_input.get("subagent_type") or "")
    if not agent_type.startswith("run-issues-"):
        return 0, ""
    value = tool_input.get("run_in_background")
    if value is False:
        return 0, ""
    shown = "absent" if value is None else repr(value)
    return 2, (
        f"run-issues spawn refused: Agent({agent_type}) carries "
        f"run_in_background {shown}. Every run-issues spawn names the field "
        f"and sets it false — the runner has nothing to do while a worker "
        f"runs. Reissue this exact call with run_in_background: false. To "
        f"keep the two gates concurrent, spawn both in one message. "
        f"(Gate: ~/.claude/hooks/run-issues-foreground-gate.py)"
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
    sys.exit(main())
