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

Run it from the run tree, or name it with `--repo`. It refuses a tree the
coverage check has not graded as it stands now, and lists that grading's
refusals after the runner's items: the check comes first by construction.

Exit 0 prints the prompt on stdout. Exit 1 refuses and says why.
Drill: `test_correction_brief.py` beside this file.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import re
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


# Issue 51 of the tracker-tooling set, ruling `q-fin-ea4cfa-05`: each gate
# writes a verdict file of its own, `<issue>-attempt-<N>-review.md` and
# `-verify.md`, so no gate can overwrite the other's. A file of that shape is
# read for its own gate's heading alone. The shared `<issue>-attempt-<N>.md` an
# older run wrote keeps the either-heading question above.
GATE_FILE = re.compile(r"-attempt-\d+-(review|verify)\.md$")
GATE_HEADING = {"review": "## Review gate", "verify": "## Verify gate"}


def gate_of(path):
    """`review` or `verify` for a per-gate verdict file, else None."""
    found = GATE_FILE.search(os.path.basename(str(path)))
    return found.group(1) if found else None


def wrong_heading_refusal(where, gate, body) -> str:
    """The refusal for a gate's file that lacks its own gate's heading."""
    heading = GATE_HEADING[gate]
    if heading.lower() in body.lower():
        return ""
    return (
        f"REFUSED. Check the {gate} gate wrote its verdict into its own file, "
        "then re-run.\n"
        f"  {where} holds no `{heading}`. Each gate writes a verdict file of "
        "its own (ruling q-fin-ea4cfa-05), and the file's name says which.\n"
        "  Two roads out:\n"
        f"  1. Pass the file the round header labels `({gate} gate)`, and "
        "re-run.\n"
        f"  2. Run `check_verdict.py --file {where} --section \"{heading}\"` "
        "to see what the gate returned, and ledger the issue `blocked` with "
        "what it prints." + AFK)


def missing_gate_refusal(issue_text, paths) -> str:
    """The refusal when per-gate files were passed and one the issue's level
    runs is absent. A light issue runs one review gate (ruling
    `q-fin-ea4cfa-01`); a full issue runs both. The issue's own `Level:` line
    is all this holds, and the run lifts a light issue whose risk file cannot
    back it to full, so a verify file on disk beside a passed gate file is
    needed whatever the line says."""
    given = {gate_of(path) for path in paths} - {None}
    if not given:
        return ""
    level = _issue_level().level_in(issue_text)
    needed = ("review",) if level == "light" else ("review", "verify")
    if "verify" not in needed and any(
            _sibling(path, "verify").is_file() for path in paths if gate_of(path)):
        level, needed = "light, lifted to full", ("review", "verify")
    missing = [gate for gate in needed if gate not in given]
    if not missing:
        return ""
    gate = missing[0]
    return (
        f"REFUSED. Pass the {gate} gate's verdict file too, and re-run.\n"
        f"  The {gate} file is missing. This issue runs at `Level: {level}`, "
        f"so {' and '.join(needed)} each wrote a file of their own, and a "
        "brief built from one of them drops the other gate's owed items.\n"
        "  Two roads out:\n"
        f"  1. Add `--verdicts <run tree>/.scratch/<feature>/runs/<batch-id>/"
        f"verdicts/<issue>-attempt-<N>-{gate}.md`, and re-run.\n"
        f"  2. If the {gate} gate wrote nothing, run `check_verdict.py` on its "
        "file and ledger the issue `blocked` with what it prints." + AFK)


def _sibling(path, gate):
    """The same attempt's file for `gate`, beside `path`."""
    path = pathlib.Path(path)
    return path.with_name(GATE_FILE.sub(
        lambda found: found.group(0).replace(found.group(1), gate), path.name))


_LOADED = {}


def _issue_level():
    """`issue_level.py` beside this file, loaded once on first use: it loads
    three more modules, and only a per-gate brief needs it."""
    if "issue_level" not in _LOADED:
        spec = importlib.util.spec_from_file_location(
            "correction_brief_issue_level",
            pathlib.Path(__file__).resolve().parent / "issue_level.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADED["issue_level"] = module
    return _LOADED["issue_level"]


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


def read_items(args, covered=()) -> tuple:
    """`(items, refusal)`. The refusal is empty when the list is usable.
    `covered` is the coverage check's refusals, listed after the runner's."""
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

    items = [one.strip() for one in [*items, *covered] if one.strip()]
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


def coverage_items(repo) -> tuple:
    """`(items, refusal)`: the coverage check's refusals for the tree at
    `repo`, which join the round's items, or the refusal when that tree was
    never graded or could not be.

    Run `batch-e35a25`, issue 227: the runner wrote this brief, then ran the
    coverage check, and its refusals bought a second correction spawn.
    `SKILL.md` step 5 ordered it in a sentence; the stamp the check leaves
    makes the order a refusal here."""
    spec = importlib.util.spec_from_file_location(
        "correction_brief_coverage",
        pathlib.Path(__file__).resolve().parent / "check_diff_coverage.py")
    coverage = sys.modules.get(spec.name)
    if coverage is None:
        coverage = importlib.util.module_from_spec(spec)
        # Registered before it runs: its dataclasses look their own module up
        # by name while each class is built.
        sys.modules[spec.name] = coverage
        spec.loader.exec_module(coverage)
    stamp = coverage.stamp_for(pathlib.Path(repo))
    if stamp is None:
        return [], (
            f"REFUSED. Run `check_diff_coverage.py --repo {repo}` on this tree "
            "first, and re-run.\n"
            "  No coverage grading of the tree as it stands now exists. Its "
            "refusals are items for this ONE round (`SKILL.md` step 5), so a "
            "brief written before it goes out short, and the gap buys a second "
            "spawn: issue 227 of run `batch-e35a25`.\n"
            "  Two roads out:\n"
            "  1. Run the check with the paths off the verify gate's last line, "
            "and re-run this.\n"
            "  2. Where no gate returned a report, run the suite with coverage "
            "in the run tree, run the check without `--report-root`, and re-run "
            "this." + AFK)
    if stamp.get("exit") == 2:
        return [], (
            "REFUSED. Make the coverage check able to grade this tree, and "
            "re-run.\n"
            "  Its last grading of this tree could not grade it:\n"
            + "".join(f"  {item}\n" for item in stamp.get("items") or [])
            + "  Two roads out:\n"
            "  1. Follow the remedy the check printed, run it again, and re-run "
            "this.\n"
            "  2. Ledger the issue `blocked` with this message." + AFK)
    return list(stamp.get("items") or []), ""


def check_issue(path, verdicts=None) -> str:
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

    # Issue 24 of the tracker-tooling set, 2026-09-23: a gate writes its
    # verdict under `runs/<batch-id>/verdicts/` and never into the issue file,
    # so the question below is asked of the verdict files. Since issue 51 each
    # gate has a file of its own, and each is asked for its own heading.
    issue_body = body
    paths = ([verdicts] if isinstance(verdicts, (str, os.PathLike))
             else list(verdicts or []))
    for where in paths or [text]:
        if paths:
            try:
                body = pathlib.Path(where).read_text(encoding="utf-8",
                                                     errors="replace")
            except OSError:
                return (
                    "REFUSED. Give the verdict file the round header's `Verdict "
                    "goes to:` line names, and re-run.\n"
                    f"  Nothing is readable at {where}.\n"
                    "  Two roads out:\n"
                    "  1. Re-run with `--verdicts <run tree>/.scratch/<feature>/"
                    "runs/<batch-id>/verdicts/<issue>-attempt-<N>-review.md`, "
                    "and the same again for `-verify.md`.\n"
                    "  2. Run `check_verdict.py --file <that file> --section "
                    "\"## Verify gate\"` to see which gate returned nothing, and "
                    "ledger the issue `blocked` with what it prints." + AFK)
        gate = gate_of(where) if paths else None
        if gate:
            refusal = wrong_heading_refusal(where, gate, body)
            if refusal:
                return refusal
            continue
        lowered = body.lower()
        if not any(head in lowered for head in GATE_HEADINGS):
            return (
                "REFUSED. Check both gates wrote their verdicts into this file, "
                "then re-run.\n"
                f"  {where} holds neither `## Verify gate` nor `## Review gate`. The "
                "scope of a correction round is the verdicts' owed list, so a file "
                "with no verdict in it means the list came from somewhere else — "
                "most often the worktree twin, or a gate that wrote beside its "
                "private copy.\n"
                "  Two roads out:\n"
                "  1. Pass the run's verdict file with `--verdicts`, and re-run. "
                "Since 2026-09-23 a gate writes there and never into the issue "
                "file.\n"
                "  2. Run `check_verdict.py --file <this file> --section \"## Verify "
                "gate\"` to see which gate returned nothing, and ledger the issue "
                "`blocked` with what it prints." + AFK)
    return missing_gate_refusal(issue_body, paths)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", required=True,
                        help="the issue file, absolute, in the main checkout")
    parser.add_argument("--verdicts", action="append", default=[],
                        help="a run verdict file for the attempt the gates just "
                             "graded, one per gate: runs/<batch-id>/verdicts/"
                             "<issue>-attempt-<N>-review.md and -verify.md, or "
                             "an older run's shared <issue>-attempt-<N>.md; "
                             "repeatable")
    parser.add_argument("--item", action="append", default=[],
                        help="one owed item; repeatable")
    parser.add_argument("--items-file",
                        help="a file of owed items, one per line")
    parser.add_argument("--repo", default=".",
                        help="the run tree the round hands over; its coverage "
                             "grading must exist, and its refusals join the "
                             "items")
    args = parser.parse_args(argv)

    refusal = check_issue(args.issue, args.verdicts)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    covered, refusal = coverage_items(args.repo)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    items, refusal = read_items(args, covered)
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
