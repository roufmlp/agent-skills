#!/usr/bin/env python3
"""Refuse a `git commit` by a gate. The runner commits; a gate reports.

BLAST RADIUS, first, because a reader cannot consent to a control whose reach is
unstated:

- Registers on PreToolUse for Bash, and for nothing else. It reads the command
  string and the spawning agent's type; it opens no file and writes nothing.
- Matches only a spawn whose agent type is one of the six adversarial gate roles
  listed in `GATES` below. Every other role passes untouched at any command.
- Refuses `git commit` in any spelling, including the `git -c
  core.hooksPath=... commit` form, because a flag between `git` and `commit` is
  still a commit and that spelling is the one that turns other hooks off.
- DELIBERATELY LETS PAST: every non-gate role and the main session -- the runner
  commits, and that is the design. `git add`, `git stash` and every read, because
  a gate that stages something has not changed history and the commit is where
  this bites. On a payload it cannot parse it exits 0.

WHAT HAPPENED. Both gate rounds of one run ended with the critical review gate
committing its own register shard, one path each. It volunteered both in its
verdicts, and it left the issue diff uncommitted, so nothing was damaged and the
honesty is why anybody knows. It also disclosed using `git -c
core.hooksPath=/dev/null` on the first, and said the flag was reflex rather than
reason.

WHY IT IS REFUSED ANYWAY. `skills/run-issues/SKILL.md` in this pack is explicit
that the runner commits, and that a commit landing under a gate already reading a
diff silently changes what "the diff" means.
`skills/run-issues/check_permission_floor.py` already lists `git add / git
commit` among its classifier-judged classes on exactly that ground, in as many
words: a gate that commits is a finding, not a permission to grant. The rule
existed and was written down. It was broken twice in one run by an agent that had
read its own brief.

That is the test the steering rule in this pack sets (`steering/CLAUDE.md`,
"Refuse, or state a fact. Never ask an agent to remember"): a rule an agent is
asked to remember is not a rule. This one can refuse, so it refuses.

A GATE'S WRITES ARE NOT THIS HOOK'S BUSINESS, and that is deliberate. Whether a
gate may write source in a live tree is a separate rule with a separate control;
`MANIFEST.md` withholds the hook that enforces it, so in this pack that rule is
one the loop holds rather than one you have. This hook is about history anywhere,
and it says nothing about files.

Ruled by the human on 2026-09-17.

The block mechanism -- read the payload from stdin, write the reason to stderr,
exit 2 -- is the documented PreToolUse contract, and `coderules-gate.py` in this
same directory is the shape copied.
"""

import json
import re
import sys

# The six adversarial gate roles, each of which has its definition in `agents/`
# in this pack. The list is written out here rather than imported, because a
# hook runs at a PreToolUse boundary and a sibling whose file name carries a
# hyphen costs an importlib dance to reach. A role added to the pack and not
# added here is a gap, and the only thing that closes it is reading this list.
GATES = (
    "run-issues-verify-gate",
    "run-issues-review-gate",
    "run-issues-review-gate-critical",
    "parallel-hunt-claim-gate",
    "parallel-hunt-fix-gate",
    "parallel-hunt-fix-gate-critical",
)

# `git commit` at a command position, with any number of flags in between --
# `git -c core.hooksPath=/dev/null commit` is the spelling that turns the other
# hooks off, and it is still a commit.
_GIT_COMMIT = re.compile(
    r"(?:^|[|;&(]|\|\||&&)\s*(?:sudo\s+)?git\b(?:\s+-[^\s]+(?:\s+[^\s-][^\s]*)?)*"
    r"\s+commit\b")

AFK = (
    "\n\nTHIS NEVER WAITS FOR THE HUMAN AND IT IS NOT A HALT. Nobody is at the "
    "keyboard during a run. Do not write a HALT BLOCK for this and do not ask - "
    "report the finding in your verdict and carry on.\n"
    "(Gate: ~/.claude/hooks/gate-commit-guard.py)"
)


def verdict(agent_type, command):
    """The refusal text, or None."""
    if agent_type not in GATES:
        return None
    if not command or not _GIT_COMMIT.search(command):
        return None
    return (
        f"Refused: `{agent_type}` may not commit. The runner commits.\n"
        "A gate that writes history is no longer only a reader of the diff it "
        "grades, and the runner can no longer tell the reviewed range from the "
        "gate's own additions.\n"
        "Both gate rounds of one run did this and both disclosed it, which is "
        "the only reason it is known; the rule that a gate which commits is a "
        "finding rather than a permission was already written down when it "
        "happened.\n"
        "The road out: leave the file written and UNCOMMITTED, and name its "
        "absolute path in your verdict. The runner stages and commits it, "
        "which is what it already does for every register shard." + AFK)


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
        reason = verdict(str(payload.get("agent_type") or ""),
                         str(tool_input.get("command") or ""))
        if reason is None:
            return 0
        print(reason, file=sys.stderr)
        return 2
    except Exception:
        return 0  # A stack trace at a PreToolUse boundary is this hook's fault.


if __name__ == "__main__":
    sys.exit(main())
