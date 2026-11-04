#!/usr/bin/env python3
"""Force the code rules to be loaded once per context, before the first code edit.

The rules are the body of the `coderules` skill: nothing is in context until the
skill is invoked, and a skill only loads if the session remembers to invoke it,
and "remember to" is not a control.

So: on the first edit of a code file in a context, block once and name the skill.
Blocking does not cancel the work — Claude invokes the skill and reissues the same
call. It fires at most once per context, and never for prose. See the Code section
of ~/.claude/CLAUDE.md.

The skill is looked up by name, never by a path to a rules file: a machine that
installs the skill through the plugin has no `~/.claude/coderules.md`, and the
message says when the skill cannot be found at all. The state directory can be
moved with CODERULES_GATE_STATE, which is how the test keeps out of the real one.
"""

import glob
import json
import os
import sys

STATE_DIR = os.environ.get("CODERULES_GATE_STATE", "/tmp/claude-coderules-gate")
SKILL = "coderules"
# Where the skill's body can live: the private skills tree, or a plugin's skills folder.
SKILL_HOMES = (
    os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "/nonexistent"), "skills", SKILL, "SKILL.md"),
    os.path.expanduser("~/.claude/skills/*/skills/coderules/SKILL.md"),
    os.path.expanduser("~/.claude/skills/coderules/SKILL.md"),
    os.path.expanduser("~/.claude/plugins/*/skills/coderules/SKILL.md"),
    os.path.expanduser("~/.claude/plugins/*/*/skills/coderules/SKILL.md"),
)

CODE_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".rs",
    ".java", ".kt", ".swift", ".php", ".c", ".h", ".cpp", ".cs", ".sql", ".sh",
    ".bash", ".zsh", ".yml", ".yaml", ".json", ".toml", ".prisma", ".graphql",
}

# Prose and scratch state are not code, whatever their extension.
SKIP_PARTS = {".scratch", "node_modules", ".git"}


def is_code(path: str) -> bool:
    if not path:
        return False
    parts = set(path.split(os.sep))
    if parts & SKIP_PARTS:
        return False
    return os.path.splitext(path)[1].lower() in CODE_SUFFIXES


def installed() -> str:
    """One line saying where the skill was found, or that it was not."""
    for pattern in SKILL_HOMES:
        found = sorted(glob.glob(pattern))
        if found:
            return f"The skill is installed at {found[0]}."
    return (f"The `{SKILL}` skill is not installed on this machine: none of "
            + ", ".join(SKILL_HOMES) + " exists. Install the plugin that carries it.")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.

    path = str((payload.get("tool_input") or {}).get("file_path") or "")
    if not is_code(path):
        return 0

    # A subagent carries the PARENT's session_id plus its own agent_id, and it starts
    # with a FRESH context — it never saw the parent read the rules. So the gate is
    # per context, not per session: key on both, and fire once for each.
    session = str(payload.get("session_id") or "unknown")
    agent = str(payload.get("agent_id") or "main")
    key = f"{session}--{agent}"
    safe = "".join(c for c in key if c.isalnum() or c in "-_")[:128] or "unknown"

    os.makedirs(STATE_DIR, exist_ok=True)
    marker = os.path.join(STATE_DIR, safe)
    if os.path.exists(marker):
        return 0  # Already fired in this context.

    try:
        with open(marker, "w") as fh:
            fh.write(path)
    except OSError:
        return 0

    who = (
        f"You are the subagent `{payload.get('agent_type') or agent}`, working in a "
        "fresh context that has never read the code rules."
        if payload.get("agent_id")
        else "This is the first code edit of this context."
    )
    print(
        f"CODE RULES: {who}\n"
        f"Invoke the `{SKILL}` skill now (Skill tool); its body is the rules. Then "
        "reissue this call.\n"
        f"{installed()}\n"
        "The two that get skipped most: fix the policy instead of bypassing the "
        "control (never swap in an admin key), and RLS goes on the same day the "
        "table is created.\n"
        "If the skill is already loaded in THIS context, say so in one line and "
        "reissue — this fires once per context only.",
        file=sys.stderr,
    )
    return 2  # Blocks this one call and shows the message to Claude.


if __name__ == "__main__":
    sys.exit(main())
