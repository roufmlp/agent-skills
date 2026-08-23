#!/usr/bin/env python3
"""Refuse a run-issues gate spawn that has no implementation record to judge.

Blast radius, before anything else. This is a `PreToolUse` hook on the
`Agent|Task` matcher. It inspects one field, `tool_input.subagent_type`, and acts
only when that value starts with `run-issues-verify-gate` or
`run-issues-review-gate`. Every other spawn in every other skill passes
untouched, including `run-issues-implementer`, so a `parallel-hunt` round or an
ordinary session never meets it. It reads files; it writes none. On a payload it
cannot parse it exits 0.

What it refuses, when it does act:

    no-issue-file the spawn prompt names no readable file under an `issues/`
                  directory
    no-record     that issue file holds no `## Implementation record`, or the
                  record's body is blank
    stale-record  the newest implementation record sits ABOVE the newest gate
                  section of the kind now being spawned, so this gate would
                  judge a diff its own predecessor already judged

The fault it exists for. A verify or review gate is spawned on the assumption
that an implementer has already built something and written down what it did.
Nothing checked. A gate spawned over an empty issue file reads the criteria,
finds no diff described, and produces a well-formed verdict about nothing — which
then passes `skills/lib/check_verdict.py`, because that script grades a verdict's
SHAPE and this fault is one step upstream of it.

`stale-record` is deliberately narrow, and the narrowness is the whole design.
The obvious rule — refuse whenever a record sits above ANY gate section —
misfires on a case this pipeline hits regularly: one gate of a pair dies writing
nothing while the other writes its verdict, and the runner re-spawns the dead
one. There the surviving section is newer than the record and the record is still
the right one. Keying on the kind being spawned makes that case pass and still
refuses the fault worth catching, which is a gate round re-run over an attempt
that never happened. A gate that misfires costs a run more than no gate at all.

**The heading matching is `check_verdict.py`'s, imported, never re-written.**
Issue files in the wild write `## Implementation record — <date>`,
`## Implementation record (<date>, attempt 1)` and
`## Verify gate, attempt 2 (<date>) — PASS`. One matcher already handles all of
that, including hyphens read as spaces and headings written at `###`. A second
copy of that logic here is the drift class this pack has a separate script to
refuse.

That import is this hook's one dependency, and this pack ships it. It is looked
up at `$RUN_ISSUES_LIB`, defaulting to `~/.claude/skills/lib` — the location the
install note uses. If it cannot be imported the hook refuses rather than passing.
A guard that quietly switches itself off when its dependency moves is worse than
no guard, because the run keeps reporting green.

Drill: `test_run_issues_evidence_gate.py` ships beside this file and drives every
refusal, and every shape that must pass, on temporary issue files it builds
itself. Run it with `python3 test_run_issues_evidence_gate.py`.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import json
import os
import pathlib
import re
import sys

LIB = pathlib.Path(
    os.environ.get("RUN_ISSUES_LIB", pathlib.Path.home() / ".claude" / "skills" / "lib")
).expanduser()
sys.path.insert(0, str(LIB))

try:
    import check_verdict
except Exception as error:  # pragma: no cover - exercised by the import test
    check_verdict = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None

# The gates this guards, mapped to the heading each one writes. A
# `run-issues-review-gate-critical` starts with the review prefix, so it is
# covered without being named twice.
GATE_PREFIXES = {
    "run-issues-verify-gate": "Verify gate",
    "run-issues-review-gate": "Review gate",
}

RECORD = "Implementation record"

# A markdown path token in a spawn prompt. Quotes, backticks and trailing
# punctuation fall outside the character class, so they need no stripping.
MD_PATH = re.compile(r"[A-Za-z0-9_./~-]+\.md")

# What makes a markdown file an ISSUE file rather than the ledger, the journal or
# a bug file: it sits in an `issues/` directory. That is the tracker layout
# `skills/run-issues/SKILL.md` assumes, `.scratch/<feature>/issues/<name>.md`.
#
# **This started as a content rule and the drill killed it.** Keying on an
# `## Acceptance criteria` heading looked safer, and against a live tracker of
# 402 issue files it matched 192 of them; the rest write `## Acceptance`,
# `## Wanted`, or a heading naming the specific finding. That rule would have
# refused a legitimate spawn on more than half the corpus, for nothing. Structure
# is what these files actually agree on. If a project keeps its issues somewhere
# else, change this one constant.
ISSUE_DIR = "issues"


def gate_section(agent_type):
    """The gate heading this spawn will write, or None for a foreign type."""
    for prefix, section in GATE_PREFIXES.items():
        if agent_type.startswith(prefix):
            return section
    return None


def candidate_paths(prompt, cwd):
    """Every readable issue file the prompt names, in the order it names them."""
    roots = [pathlib.Path(cwd)] if cwd else []
    roots.append(pathlib.Path.cwd())
    found = []
    for token in MD_PATH.findall(prompt or ""):
        expanded = pathlib.Path(token).expanduser()
        tries = [expanded] if expanded.is_absolute() else [root / token for root in roots]
        for candidate in tries:
            try:
                if not candidate.is_file():
                    continue
                if ISSUE_DIR not in candidate.parts:
                    continue
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            found.append((candidate, text))
            break
    return found


def judge(path, text, section):
    """Grade one issue file for one gate. Returns (kind, message) or None."""
    body = check_verdict.read_section(text, RECORD)
    if body is None or not body.strip():
        missing = "holds no `## Implementation record`" if body is None else (
            "holds an `## Implementation record` with an empty body"
        )
        return "no-record", (
            f"{path} {missing}. A gate spawned now would judge a diff nobody "
            f"has described. Spawn the implementer, or — if this issue's work "
            f"is already committed — have it write the record before the gate "
            f"round opens."
        )

    record_at = check_verdict.locate_section(text, RECORD)
    gate_at = check_verdict.locate_section(text, section)
    if record_at and gate_at and record_at[0] < gate_at[0]:
        return "stale-record", (
            f"{path} carries `## {section}` at line {gate_at[0] + 1}, below the "
            f"newest `## Implementation record` at line {record_at[0] + 1}. This "
            f"gate would judge the attempt its own predecessor already judged. "
            f"If a new attempt ran, the implementer owes a new record below that "
            f"section. If the previous gate died writing nothing, delete its "
            f"empty section before re-spawning."
        )
    return None


def decide(payload):
    """Return (exit_code, message). Pure, so the drill can drive it."""
    tool_input = payload.get("tool_input") or {}
    agent_type = str(tool_input.get("subagent_type") or "")
    section = gate_section(agent_type)
    if section is None:
        return 0, ""

    if check_verdict is None:
        return 2, (
            f"run-issues gate refused: this hook cannot import check_verdict "
            f"from {LIB} ({IMPORT_ERROR}). It grades every gate spawn and will "
            f"not pass one it cannot grade. Put that file there, point "
            f"RUN_ISSUES_LIB at wherever it lives, or unregister this hook "
            f"deliberately."
        )

    prompt = str(tool_input.get("prompt") or "")
    found = candidate_paths(prompt, payload.get("cwd"))
    if not found:
        return 2, (
            f"run-issues gate refused: Agent({agent_type}) names no readable "
            f"file under an `{ISSUE_DIR}/` directory. A gate spawn prompt "
            f"carries the issue id and its paths; this gate cannot check that an "
            f"implementation record exists without one. Add the issue file's "
            f"path to the prompt and reissue. "
            f"(Gate: run-issues-evidence-gate.py)"
        )

    for path, text in found:
        verdict = judge(path, text, section)
        if verdict:
            kind, message = verdict
            return 2, (
                f"run-issues gate refused ({kind}): {message} "
                f"(Gate: run-issues-evidence-gate.py)"
            )
    return 0, ""


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
