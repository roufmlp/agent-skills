#!/usr/bin/env python3
"""Compose the correction round's spawn prompt, or refuse to.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling Q7 of round 2, 2026-09-08: the correction round stays and its two
handovers become one script each. Eight of the last twenty-two issues bought a
round, and the wait was eleven to twenty-two minutes each, of which the spawn
itself was four to seventeen.

WHAT IT DOES NOT DO, and this is the part the ticket's own brief got wrong. It
does not read the owed items out of the gate sections. A verdict is free prose:
the two gate briefs in `~/.claude/agents/` set no list shape, and neither file
uses the word "owed" at all. Extracting a list from prose is judgement, and the
runner is the one who reads both verdicts anyway. **The runner names the items;
this refuses a prompt that would not work.**

THE REFUSAL IT IS BOUGHT FOR. `~/.claude/hooks/run-issues-brief-cap.py` grants a
correction brief its exemption from the 400-word cap only when `CORRECTION ROUND`
is inside the first 400 characters (ticket 36 ruling 11). A correction brief that
puts the marker later is capped like a first attempt, and the owed list is the
varying part that cannot be cut. This composes the prompt and then asks the
HOOK'S OWN function whether the exemption is earned. One rule, two readers:
sitting 2 of this ticket found the cap's record re-implementing the refusal's
tests, and a copy of the rule here would drift the same way.

    python3 correction_brief.py --issue <abs path> --item "..." [--item "..."]
    python3 correction_brief.py --issue <abs path> --items-file <path>

Exit 0 prints the prompt on stdout. Exit 1 refuses and says why.
Drill: `test_correction_brief.py` beside this file.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import sys

# `~/.claude/hooks` is NOT in this repo and has no worktree copy, so the hook
# has exactly one home on this machine. Climbing from `__file__` found it
# only from the main checkout: run from a worktree the climb landed on
# `.claude/worktrees/hooks`, `hook_module()` read that as "no hook
# installed", and `earns_exemption` fell open on a machine where the cap
# was in fact installed and armed. The fail-open below is for a machine
# with no hook, never for a checkout that cannot find one.
HOOK = pathlib.Path.home() / ".claude" / "hooks" / "run-issues-brief-cap.py"

# The marker opens the prompt, so it can never fall outside the hook's window.
# `earns_exemption` proves that rather than trusting it.
PREAMBLE = """CORRECTION ROUND for {issue}.

Both gates graded the behaviour correct and enumerated the items below. This is
not a retry and it is not a strike. Do the items and nothing else.

Owed items:
"""

CLOSING = """
This round runs no full suite. Run each item's named evidence test and the
typecheck, and nothing wider. The runner re-runs coverage over this tree when
you return, and that is the whole-tree reading — yours would read the same tree
twice.

Return when each item's NAMED evidence exists: the test is there and green, the
mutation reds. Do not commit — the runner commits.
"""

AFK = (
    "\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR THE HUMAN. The human is AFK "
    "for every run. Take one of the two roads above now and carry on."
)

GATE_HEADINGS = ("## verify gate", "## review gate")


def hook_module():
    """The cap hook, imported from its own file, or None when it is not there.

    Imported rather than copied so the marker rule has exactly one home. A
    machine with no hook installed has no cap to fail, so None is not a fault.
    """
    try:
        spec = importlib.util.spec_from_file_location("run_issues_brief_cap", HOOK)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (OSError, ImportError, SyntaxError):
        return None


def earns_exemption(prompt) -> bool:
    """True when the cap hook would exempt this prompt as a correction round."""
    hook = hook_module()
    if hook is None:
        return True
    return bool(hook.is_correction(prompt))


def compose(issue, items) -> str:
    """The spawn prompt: the marker, the issue, the items, and nothing else."""
    listed = "".join(f"{n}. {text}\n" for n, text in enumerate(items, 1))
    return PREAMBLE.format(issue=issue) + listed + CLOSING


def read_items(args) -> tuple:
    """`(items, refusal)`. The refusal is empty when the list is usable."""
    items = list(args.item)
    if args.items_file:
        try:
            raw = pathlib.Path(args.items_file).read_text(encoding="utf-8")
        except OSError:
            return [], (
                f"REFUSED. Write the owed items to {args.items_file}, one per "
                "line, and re-run.\n"
                "  Nothing is readable at that path.\n"
                "  Two roads out:\n"
                "  1. Write the file and re-run.\n"
                "  2. Pass each item with `--item` instead." + AFK)
        items += [line.strip() for line in raw.splitlines() if line.strip()]

    items = [one.strip() for one in items if one.strip()]
    if not items:
        return [], (
            "REFUSED. Name the owed items with `--item`, one per item, and "
            "re-run.\n"
            "  No item was given, or every one was blank. An empty owed list is "
            "not a correction round: `SKILL.md` reaches this step only when both "
            "gates pass AND a verdict enumerates follow-up items. Nothing owed "
            "is `done`.\n"
            "  Two roads out:\n"
            "  1. Re-read both verdicts, name each owed item, and re-run.\n"
            "  2. If the verdicts owe nothing, mark the row `done` and skip the "
            "round. If they owe more than a round can hold, file a register row "
            "instead — one round is the maximum." + AFK)
    return items, ""


def check_issue(path) -> str:
    """The refusal for an unusable issue path, or empty."""
    text = str(path)
    # NO WORKTREE REFUSAL. Until 2026-09-13 this refused any path containing
    # `/.claude/worktrees/`, on the premise that the worktree twin is "checked
    # out at the fork point" and so carries no gate verdict. That premise is
    # false for a run's OWN issue file: `SKILL.md` tells the runner to check the
    # verdict against the issue file in this run's own worktree, and gives the
    # reason -- passing the worktree path is what turns a gate that wrote beside
    # a private copy into a refusal. The two preconditions could not both hold,
    # and the last runner satisfied them by hand twice (run `batch-19ff9f`,
    # merge briefing, `## Decide` item 1). The hazard the path check was
    # reaching for is caught by the GATE_HEADINGS check below, which asks the
    # real question -- does this file hold a verdict -- and does not care which
    # path carries it. Ruled by the human, 2026-09-13.

    try:
        body = pathlib.Path(text).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return (
            f"REFUSED. Give a readable issue file and re-run.\n"
            f"  Nothing is readable at {text}.\n"
            "  Two roads out:\n"
            "  1. Re-run with the path the ledger header names.\n"
            "  2. If the issue file is genuinely gone, ledger the issue "
            "`blocked` with this message." + AFK)

    lowered = body.lower()
    if not any(head in lowered for head in GATE_HEADINGS):
        return (
            "REFUSED. Check both gates wrote their verdicts into this file, "
            "then re-run.\n"
            f"  {text} holds neither `## Verify gate` nor `## Review gate`. The "
            "scope of a correction round is the verdicts' owed list, so a file "
            "with no verdict in it means the list came from somewhere else — "
            "most often the worktree twin, or a gate that wrote beside its "
            "private copy.\n"
            "  Two roads out:\n"
            "  1. Find where the gate wrote its verdict, move it beside the "
            "branch, and re-run.\n"
            "  2. Run `check_verdict.py --file <this file> --section \"## Verify "
            "gate\"` to see which gate returned nothing, and ledger the issue "
            "`blocked` with what it prints." + AFK)
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", required=True,
                        help="the issue file, absolute, in the main checkout")
    parser.add_argument("--item", action="append", default=[],
                        help="one owed item; repeatable")
    parser.add_argument("--items-file",
                        help="a file of owed items, one per line")
    args = parser.parse_args(argv)

    refusal = check_issue(args.issue)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    items, refusal = read_items(args)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    prompt = compose(args.issue, items)
    if not earns_exemption(prompt):
        print(
            "REFUSED. Move `CORRECTION ROUND` into the opening of this file's "
            "`PREAMBLE` and re-run.\n"
            "  The composed prompt does not earn the cap hook's correction "
            "exemption, so `run-issues-brief-cap.py` would refuse the spawn as "
            "an over-long first attempt. The marker is read in the opening "
            "characters alone (ticket 36 ruling 11), and a correction round's "
            "owed list is the varying part that cannot be cut to fit the cap.\n"
            "  Two roads out:\n"
            "  1. Fix `PREAMBLE` so the marker opens it, and re-run.\n"
            "  2. Spawn with the marker written by hand as the prompt's first "
            "line, and file a register row against this script." + AFK,
            file=sys.stderr)
        return 1

    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
