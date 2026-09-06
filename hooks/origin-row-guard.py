#!/usr/bin/env python3
"""Refuse a register row written now that does not name where the fault came from.

BLAST RADIUS, first, because a reader cannot consent to a control whose reach is
unstated:

- Registers on PreToolUse for Edit, Write and NotebookEdit, and for Bash. It
  reads files; it writes none.
- Matches only a file under a `register.d/` shard directory, in any tree. Every
  other path passes untouched.
- Inside such a file it judges only a table whose header carries BOTH `audience`
  and `severity`. That pair is the register row shape every brief states, and no
  prose table in a shard carries both.
- Refuses on two conditions: such a table declaring no `origin` column, and a row
  under one whose origin cell is empty or unreadable.
- DELIBERATELY LETS PAST: every file outside a shard directory, every prose table
  inside one, a shard holding no table, and every Bash write that is not a
  heredoc. On a payload it cannot parse, or with its companion script absent, it
  exits 0.

WHY A HOOK AND NOT ONLY A SCRIPT. `check_origin.py` in the run-issues skill
grades a file that already exists, and it SKIPS a table whose header declares no
`origin` column. It has to: a register holds historical rounds under a dozen
header shapes, the origin rule starts the count the day the key lands, and a
check that refused all of them would report hundreds of faults nobody can act
on. But that leaves a hole -- a NEW table typed without the column is
indistinguishable from a historical one, so the writer who simply omits the
column escapes the very check meant to catch it.

A hook sees only writes happening NOW. It can demand the column outright and
never meet history. That is the whole reason this file exists, and it is why
the rule here is stricter than the rule in the script.

THE BASH LIMIT, STATED, AND IT IS WIDER IN THIS PACK THAN IT IS LIVE. For `Edit`
and `Write` the content is in the payload and is read in full. For `Bash` only a
heredoc body is read, because that is the only shape whose content travels in the
command -- AND that road needs `generated-file-guard.py`, whose `bash_targets`
parser resolves the redirect target. **This pack does not ship that file.**
Without it every Bash write passes here, silently and by design rather than by
accident, and is caught afterwards by `check_origin.py`, which promotion runs
before it resolves a single row. Drop that sibling in beside this file and the
Bash road starts working with no change here.

The block mechanism -- read the payload from stdin, write the reason to stderr,
exit 2 -- is the documented PreToolUse contract, and `coderules-gate.py` in this
same directory is the shape copied.
"""

import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# `hooks` and `skills` are separate repositories, so one can sit at a commit
# where the other's file does not exist. The path is overridable so a test can
# prove what happens then: this guard passes rather than throwing.
CHECK = os.environ.get("ORIGIN_CHECK") or os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "run-issues", "check_origin.py")

# The shard directory. `collect_shards.py` owns the layout: a generated board
# `register.md` keeps its content in `register.d/<tree>/<prefix>.md`.
SHARD_DIR = "register.d"

# The register row shape every brief states: `ID | summary | audience |
# severity | status | origin | owner-notes`. `audience` and `severity` together
# are what identifies it, and no prose table in a shard carries both.
SIGNATURE = ("audience", "severity")

# A heredoc body: `<<EOF`, `<<'EOF'`, `<<-"EOF"`. The only bash shape whose
# content travels in the command string.
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*\n(.*?)\n\s*\1\b",
                     re.DOTALL)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # A dataclass cannot resolve its own
    spec.loader.exec_module(module)     # annotations unless it is here first.
    return module


def is_shard(path: str) -> bool:
    """True for a file inside a register shard directory, in any tree."""
    if not path:
        return False
    return SHARD_DIR in os.path.normpath(path).split(os.sep)


def offences(text: str, check) -> list:
    """Every reason to refuse this content, in the order they appear.

    Two rules. A register row table must DECLARE the origin column -- the rule
    the script cannot enforce -- and every row under it must carry a legal
    value, which the script's own reader answers, so it is not written twice.
    """
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.lower() for c in check.cells(line)]
        if all(word in cells for word in SIGNATURE) and "origin" not in cells:
            found.append(
                f"line {number}: this register table declares no `origin` "
                f"column. Every row needs one.")
    if found:
        return found
    return [f"line {fault.line}: {fault.row_id}: {fault.reason}"
            for fault in check.register_faults(text)]


def _with_header(path: str, written: str) -> str:
    """What is being appended, with the table header already on disk above it.

    An Edit's `new_string`, and a heredoc body, both carry the ROW alone. A row
    with no header above it has no `origin` column to be missing, so every bad
    row appended that way would pass. The header is on disk; judge them
    together. A file that is not there yet is judged on what is being written,
    which is the create case and carries its own header.
    """
    if not written.strip():
        return written
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().rstrip("\n") + "\n" + written
    except OSError:
        return written


def content_of(payload: dict) -> str:
    """What this call would put on disk, as far as the payload shows it."""
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input", {}) or {}
    if tool in ("Write", "Edit", "NotebookEdit"):
        path = data.get("file_path", "")
        if not is_shard(path):
            return ""
        written = data.get("content") or data.get("new_string") or ""
        if data.get("content") is not None:
            return written
        return _with_header(path, written)
    if tool == "Bash":
        command = data.get("command", "") or ""
        if SHARD_DIR not in command:
            return ""   # Cheap first: do not load a parser to answer `ls`.
        parser = os.path.join(HERE, "generated-file-guard.py")
        if not os.path.isfile(parser):
            return ""   # The redirect parser is not beside this file. Pass.
        guard = _load(parser, "generated_file_guard")
        targets = guard.bash_targets(command, matches=is_shard)
        if not targets:
            return ""
        body = "\n".join(part for _, part in HEREDOC.findall(command))
        return _with_header(targets[0], body)
    return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Not a payload this hook can read. Never a halt.
    try:
        text = content_of(payload)
    except Exception:
        return 0   # Never a halt: a payload this cannot read is not a refusal.
    if not text.strip():
        return 0
    try:
        check = _load(CHECK, "check_origin")
    except (OSError, ImportError, AttributeError):
        return 0   # The skills repository does not carry it yet. Pass.
    found = offences(text, check)
    if not found:
        return 0
    print(
        "REFUSED — a register row must name where the fault came from.\n"
        + "\n".join("  " + line for line in found)
        + "\nThe row shape is:\n"
        "  ID | summary | audience | severity | status | origin | owner-notes\n"
        "The origin cell reads `<issue>/<run>` — the issue and the run that "
        "shipped the code this fault is in.\n"
        "Where you genuinely do not know a half, write `unknown` in its place "
        "(`unknown/<run>`), or `unknown` alone for neither. It is legal "
        "and it is counted, so say it rather than guessing.\n"
        "Reissue the call with the column.",
        file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
