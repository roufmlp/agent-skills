#!/usr/bin/env python3
"""Refuse a kill that selects processes by PATTERN rather than by pid.

BLAST RADIUS, first, because a reader cannot consent to a control whose reach is
unstated:

- Registers on PreToolUse for Bash, and for nothing else. It reads the command
  string; it opens no file, reads no tree and no ledger, and writes nothing.
- Matches `pkill` and `killall` in any spelling, and `kill` whose targets come
  from a substitution that SELECTS BY PATTERN -- `kill $(pgrep -f <name>)` and
  its backtick form. Those three are the roads to killing a process you did not
  start.
- DELIBERATELY LETS PAST: `kill <pid>` and `kill -9 <pid>` with literal numbers,
  a pid read back from a file the caller wrote, `pgrep` alone (a read), and every
  other command on the machine. On a payload it cannot parse it exits 0.
- It has no opinion about who typed the command. A machine-wide kill is wrong
  from a gate, from an implementer and from the runner alike, because every one
  of them shares the machine with the others.

WHAT HAPPENED. One run spawned its two gates concurrently, each in its own
private copy, which is the design: the wall clock is the slower of the two rather
than their sum. The verify gate of round 1 needed to prove a criterion that asks
what a SIGKILL mid-run leaves behind. It reached for `pkill -9 -f vitest`.

That pattern does not match "my suite". It matches every `vitest` on the machine,
and at that moment a second gate was running its own suite in its own tree, and a
third tree could have been running one too. The gate disclosed the call itself,
in its verdict, which is the only reason anybody knows. Nothing refused it and
nothing recorded which processes died.

WHY A HOOK AND NOT A LINE IN A BRIEF. The steering rule in this pack
(`steering/CLAUDE.md`, "Refuse, or state a fact. Never ask an agent to remember")
sorts every proposal into three classes, and the deciding question is whether the
thing can refuse. This can. A brief that says "kill only what you started" is a
reminder, and the rule it replaces was already implicit in every gate brief on
the day it was broken.

Ruled by the human on 2026-09-17.

The block mechanism -- read the payload from stdin, write the reason to stderr,
exit 2 -- is the documented PreToolUse contract, and `coderules-gate.py` in this
same directory is the shape copied.
"""

import json
import re
import sys

# `pkill`/`killall` anywhere a command can start: line start, or after a pipe,
# `;`, `&&`, `||`, a subshell paren, or a backgrounding `&`.
_PATTERN_KILLERS = re.compile(
    r"(?:^|[|;&(]|\|\||&&)\s*(?:sudo\s+)?(pkill|killall)\b")

# `kill` whose targets come from a substitution that SELECTS BY PATTERN.
#
# The substitution alone is not the fault, and an early draft of this hook got
# that wrong: it refused `kill "$(cat /tmp/dev.pid)"`, which is the exact road
# the refusal text recommends. A guard that refuses its own advice teaches the
# reader to work around it. What makes a target a pattern is the selector inside
# the substitution -- `pgrep`, `pidof`, or a `ps` piped through a filter.
_KILL_FROM_PATTERN = re.compile(
    r"(?:^|[|;&(]|\|\||&&)\s*(?:sudo\s+)?kill\b[^|;&\n]*"
    r"(?:\$\(|`)\s*(?:sudo\s+)?(pgrep|pidof|ps)\b")

_ADVICE = (
    "Kill only a pid you started and captured:\n"
    "    nohup <command> > <log> 2>&1 &\n"
    "    echo $! > /tmp/<name>.pid\n"
    "    kill \"$(cat /tmp/<name>.pid)\"\n"
    "A literal `kill <pid>` is never refused here."
)


def verdict(command):
    """The refusal text for this command, or None.

    Reads the raw string rather than a parse, because the thing being caught is
    a shell line and `shlex` gives up on the substitutions that matter most.
    """
    if not command:
        return None
    text = command.strip()

    match = _PATTERN_KILLERS.search(text)
    if match:
        return (
            f"REFUSED: `{match.group(1)}` selects processes by PATTERN, across "
            "the whole machine.\n"
            "Other trees on this machine run their own suites and their own "
            "servers, and a concurrent gate, run or hunt is the normal case "
            "rather than the exception. On 2026-09-17 a verify gate ran "
            "`pkill -9 -f vitest` while a second gate was running its own "
            "suite; it disclosed the call itself, which is the only reason it "
            "is known.\n" + _ADVICE)

    if _KILL_FROM_PATTERN.search(text):
        return (
            "REFUSED: `kill` fed from a pattern selector kills by pattern, not "
            "by pid.\n"
            "`kill $(pgrep -f <name>)` reaches every matching process on the "
            "machine, including one another tree started. Reading a pid you "
            "captured yourself is fine and is not refused.\n" + _ADVICE)

    return None


GUARDED_TOOLS = ("Bash",)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.
    try:
        if str(payload.get("tool_name") or "") not in GUARDED_TOOLS:
            return 0
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0
        reason = verdict(str(tool_input.get("command") or ""))
        if reason is None:
            return 0
        print(reason, file=sys.stderr)
        return 2
    except Exception:
        return 0  # A stack trace at a PreToolUse boundary is this hook's fault.


if __name__ == "__main__":
    sys.exit(main())
