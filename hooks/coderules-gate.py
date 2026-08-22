#!/usr/bin/env python3
"""Force the code rules to be read once per context, before the first code edit.

Blast radius, before anything else. This is a `PreToolUse` hook on
`Edit|Write|NotebookEdit`. It reads one field, `tool_input.file_path`, and
refuses at most ONE call per context: the first edit whose path has a code
suffix (see `CODE_SUFFIXES`) and does not sit under a skipped directory. Prose,
Markdown, scratch state, `node_modules` and `.git` pass untouched, and so does
every code edit after the first. It writes one empty marker file per context
under a temporary directory and touches nothing in the reader's repository.
Registering it is a separate step: see `hooks/README.md`.

Blocking does not cancel the work. The model reads the rules and reissues the
same call, which is why one refusal is enough and a second would only cost the
reader turns.

Why it is a script and not a line of prose. The rules used to be an `@import`
in `CLAUDE.md`, so every session paid roughly 2.8k tokens for them whether or
not it wrote a line of code. They now load on demand behind a skill — but a
skill loads only if the session remembers to invoke it, and "remember to" is
not a control. See the Code section of `steering/CLAUDE.md` in this pack.

Point it at your own rules. `CODERULES_PATH` overrides the default,
`~/.claude/coderules.md`; this pack publishes a copy of mine as
`steering/coderules.md`, which is meant to be replaced rather than adopted. If
you replace it, the two sentences in the refusal message below are about MY
rules file and should be edited to name the two of yours that get skipped most.

Fails open throughout: an unparseable payload, an unwritable temporary
directory, or a path it cannot classify all return 0.
"""

import json
import os
import sys

STATE_DIR = "/tmp/claude-coderules-gate"
RULES = os.environ.get("CODERULES_PATH") or os.path.expanduser("~/.claude/coderules.md")

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
        f"Read {RULES} in full now, then reissue this call.\n"
        "The two that get skipped most: fix the policy instead of bypassing the "
        "control (never swap in an admin key), and RLS goes on the same day the "
        "table is created.\n"
        "If you have already read that file in THIS context, say so in one line and "
        "reissue — this fires once per context only.",
        file=sys.stderr,
    )
    return 2  # Blocks this one call and shows the message to Claude.


if __name__ == "__main__":
    sys.exit(main())
