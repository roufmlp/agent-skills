#!/usr/bin/env python3
"""The lint over the seven build-feature agent files.

    python3 check_build_agents.py [--dir ~/.claude/agents]

The `build-feature-run` workflow spawns seven roles, one agent file each in
`~/.claude/skills/workflow/agents/`: implementer, verifier, reviewer, note-checker, merger,
final-verifier and final-reviewer. Each file's frontmatter sets the role's
model and effort, so Abdul changes a role in one line; this lint refuses a
file that lost the line, spelled a value the docs do not list, or dropped a
rule the design hangs on.

What it reads, per file:

  frontmatter  `name` equal to the file stem; `description`; `model` from
               the documented aliases or a full model id; `effort` from the
               five documented levels; `autoCompactWindow: 400000`, the
               window every version 2 session runs at; `tools`, a short list
               (one to eight names) of known tool names; and `permissionMode`
               never `bypassPermissions`, since bypass mode is disabled on
               this machine. `omitClaudeMd`, when present, is `true` or
               `false`.
  body         never the phrase "final message": every role answers the
               workflow in the typed form its schema asks for;
               then the lines the design puts in each role, as plain phrases:
               `/tdd`, "do not wait for a seam" and `keeps:` for the
               implementer; "hostile walk" and its six cases for the
               verifier; the seven gate steps and the baseline retake for
               the final verifier; renumbering and the report table header
               for the merger; the money, access and secrets rubric for the
               final reviewer.

Model and effort VALUES are not pinned here: the file is the one place a
role's model lives, and the lint checks the spelling, not the choice.
Exit 0 is clean; exit 1 lists every refusal, one per line, as
`<file>: <what>`.
"""

import argparse
import os
import re
import sys

ROLES = ("implementer", "verifier", "reviewer", "note-checker", "merger", "final-verifier", "final-reviewer")
MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
MODEL_ID = re.compile(r"^claude-[a-z0-9-]+$")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
WINDOW = "400000"
TOOLS = {"Read", "Edit", "Write", "Bash", "Grep", "Glob", "Skill", "Agent", "WebFetch", "WebSearch", "NotebookEdit"}
MAX_TOOLS = 8

# The phrases each role's body must carry. Lower-cased before the search.
PHRASES = {
    "implementer": ["/tdd", "do not wait for a seam", "keeps:"],
    "verifier": ["hostile walk", "reload", "second road", "two fast clicks", "390", "empty state", "error state", "on_main.py"],
    "reviewer": ["code-review", "keeps:"],
    "note-checker": ["corrected:", "sound:", "stopped:", "decide"],
    "merger": ["renumber", "| note | state |", "merge --abort", "fast-forward", "--no-ff"],
    "final-verifier": ["retake", "pre-launch gate", "rls", "service_role", "npm audit", "429", "on_main.py"],
    "final-reviewer": ["money", "access", "secrets", "code-review"],
}
GATE_STEPS = 7
# Every role answers the workflow in a typed form (the script's schemas), never
# in a prose "final message" the script would have to read: a file that brings
# the phrase back brings the parse back with it.
FORBIDDEN = ("final message",)


def frontmatter(text):
    """The frontmatter as {key: value} and the body, or (None, text) when the file has none."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields, text[end + 5:]


def tool_list(value):
    """A `tools:` value as a list: `Read, Bash` or a YAML flow list `[Read, Bash]`."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [t.strip().strip("\"'") for t in value.split(",") if t.strip()]


def check_file(path, role):
    """Every refusal for one agent file, as strings without the file name."""
    out = []
    if not os.path.isfile(path):
        return [f"missing"]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fields, body = frontmatter(text)
    if fields is None:
        return ["no frontmatter"]
    stem = os.path.splitext(os.path.basename(path))[0]
    if fields.get("name") != stem:
        out.append(f"name must be `{stem}`, is `{fields.get('name')}`")
    if not fields.get("description"):
        out.append("no description")
    model = fields.get("model", "")
    if model not in MODELS and not MODEL_ID.match(model):
        out.append(f"model `{model}` is not sonnet, opus, haiku, fable, inherit or a full model id")
    if fields.get("effort") not in EFFORTS:
        out.append(f"effort `{fields.get('effort')}` is not one of low, medium, high, xhigh, max")
    if fields.get("autoCompactWindow") != WINDOW:
        out.append(f"autoCompactWindow must be {WINDOW}, is `{fields.get('autoCompactWindow')}`")
    if "tools" not in fields:
        out.append("no tools list")
    else:
        tools = tool_list(fields["tools"])
        if not 1 <= len(tools) <= MAX_TOOLS:
            out.append(f"tools list has {len(tools)} names; one to {MAX_TOOLS}")
        for t in tools:
            if t not in TOOLS:
                out.append(f"tool `{t}` is not a known tool name")
    if fields.get("permissionMode") == "bypassPermissions":
        out.append("permissionMode bypassPermissions is disabled on this machine")
    if "omitClaudeMd" in fields and fields["omitClaudeMd"] not in ("true", "false"):
        out.append(f"omitClaudeMd must be true or false, is `{fields['omitClaudeMd']}`")
    low = body.lower()
    for phrase in PHRASES[role]:
        if phrase not in low:
            out.append(f"body lacks `{phrase}`")
    for phrase in FORBIDDEN:
        if phrase in low:
            out.append(f"body says `{phrase}`: the role answers in the typed form, not in prose")
    if role == "final-verifier":
        for n in range(1, GATE_STEPS + 1):
            if not re.search(rf"^\s+{n}\. ", body, re.M):
                out.append(f"body lacks gate step {n}")
    return out


def check_dir(directory):
    """Every refusal across the seven files, as `<file>: <what>` lines."""
    lines = []
    for role in ROLES:
        name = f"build-feature-{role}.md"
        for what in check_file(os.path.join(directory, name), role):
            lines.append(f"{name}: {what}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
    args = parser.parse_args(argv)
    lines = check_dir(args.dir)
    for line in lines:
        print(line)
    if lines:
        return 1
    print(f"build agents: {len(ROLES)} files pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
