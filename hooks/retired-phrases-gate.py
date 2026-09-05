#!/usr/bin/env python3
"""Refuse a write that puts superseded wording into a steering file.

BLAST RADIUS, first, because a reader cannot consent to a control whose reach is
unstated:

- Registers on PreToolUse for Edit, Write and NotebookEdit. Nothing else.
- Matches FOUR path classes, all inside the reader's own `~/.claude`:
  `~/.claude/CLAUDE.md`, `~/.claude/questionrules.md`,
  `~/.claude/skills/<name>/SKILL.md`, and `~/.claude/agents/<name>.md`.
- Refuses only when the incoming text carries a phrase from the denylist in
  `skills/lib/retired_phrases.py`. That list holds five entries.
- DELIBERATELY LETS PAST: every `decisions.md`, every project file, a repo's own
  CLAUDE.md, a `SKILL.md` nested deeper than one directory, every Bash command,
  and this hook and its test, which carry the phrases by definition.

WHY IT EXISTS. A 2026-08-29 sweep found eighteen instances of one defect: a rule
ruled in one file while another file kept the old wording, and the old wording
won locally, because the agent reading it had no way to know a newer ruling
existed. Each was repaired by hand and nothing refused the next one. A companion
test reports the same defect after the fact; this refuses it at the moment of
the write, which is the difference between a guard and a reminder.

WHY THE MESSAGE SAYS WHAT REPLACED THE PHRASE. Grade a guard by whether its
message names the act that would prevent a repeat, not by whether it refuses. A
sibling guard once refused a lone gate spawn and named the missing VERDICT — the
symptom — and the same slip happened on the very next attempt because nothing
named the missing SPAWN.

The block mechanism — read the payload from stdin, write the reason to stderr,
exit 2 — is the documented PreToolUse contract, and `coderules-gate.py`
in this same directory is the shape copied.

It fails open on anything it cannot read, including its own denylist going
missing, because a hook that raises takes the caller's tool call with it.
"""

import json
import os
import sys
from pathlib import Path

# The denylist has one home, shared with the test that reports on it. Carrying a
# second copy here would be the very defect this hook refuses.
_LIB = os.environ.get(
    "RETIRED_PHRASES_LIB",
    str(Path(os.path.expanduser("~")) / ".claude" / "skills" / "lib"),
)

# This hook and its test quote every retired phrase, so they are never guarded.
SELF = {Path(__file__).resolve(), Path(__file__).resolve().parent
        / "test_retired_phrases_gate.py"}


def refuse(path, found):
    lines = [
        "REFUSED — that write puts retired wording into a steering file.",
        f"  {path}",
        "",
    ]
    for phrase, superseded_by in found:
        lines += [f'  retired: "{phrase}"', f"  replaced by: {superseded_by}", ""]
    lines += [
        "Write the current rule instead, then reissue.",
        "",
        "If you are quoting the dead sentence ON PURPOSE — as history, or as a",
        "supersession note so nobody re-derives the old rule — it belongs in a",
        "decisions.md, which this hook does not guard.",
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


def incoming_text(tool_input):
    """Every field of a write payload that carries prose."""
    parts = []
    for key in ("new_string", "content", "new_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.

    try:
        if str(payload.get("tool_name") or "") not in {"Edit", "Write", "NotebookEdit"}:
            return 0

        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0

        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        text = incoming_text(tool_input)
        if not path or not text:
            return 0

        if _LIB not in sys.path:
            sys.path.insert(0, _LIB)
        import retired_phrases  # noqa: E402  — located at runtime, by design

        try:
            if Path(path).expanduser().resolve() in SELF:
                return 0
        except (OSError, ValueError, RuntimeError):
            pass

        if not retired_phrases.is_steering_file(path):
            return 0

        found = retired_phrases.hits(text)
        return refuse(path, found) if found else 0
    except Exception:
        # H5. A stack trace at a PreToolUse boundary is a fault this hook would
        # be introducing into somebody else's session. Silence is the safe side.
        return 0


if __name__ == "__main__":
    sys.exit(main())
