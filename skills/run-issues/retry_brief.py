#!/usr/bin/env python3
"""Compose a retry brief's spawn prompt, or refuse to.

WHY IT EXISTS. Run `batch-d67136`, issue 01, F3, queued as `q-finale-d67136-2`.
The issue spent all three of its attempts on one connection-string guard, and
round 3 alone cost 622k tokens and 36.7 minutes across the implementer and both
gates. Round 2's review gate had PASSED, so round 3 exists for one reason and
that reason is the retry brief.

WHAT THE RECORD SHOWS, and it is worse than "the runner forgot". The verify gate
wrote the invariant AS an invariant, with its citation, at line 514 of the issue
file:

    | I-1 | **The loader refuses any host but this machine.** Implied by Target
    database, "`DATABASE_URL` in `.env.local`; the loader refuses any other
    host" | **FAIL** |

and forty lines later proposed a remedy, "refuse a connection string whose
search parameters contain `host`". The retry brief carried the remedy and
dropped the invariant. The implementer fixed exactly what it was told. Round 2
rejected on the same guard for a hostless string, because `""` is in
`LOCAL_HOSTS` and `pg` takes the address from `PGHOST` -- which the invariant
covers and the remedy does not. The gate then quoted the SAME phrase off the
SAME line and marked I-1 `FAIL` a second time (line 1392).

WHY THIS IS NOT A LINE IN THE IMPLEMENTER BRIEF. That brief already ends with
"do not trust its diagnosis. Re-derive from the issue and the code." The
reminder is there, it is exact, and it failed. `run-issues-implementer.md` is
185 lines of reminders, and the one that mattered most on this run did not hold.
A second reminder is not the answer: the human's three-class test refuses that
class outright. This refuses instead.

THE RULE IT REFUSES ON. **Every owed item quotes the issue's OWN text**, and the
issue's own text stops at the first gate verdict or implementation record. A
gate's proposed remedy lives inside a verdict, so it cannot satisfy the rule; the
invariant it serves lives in the issue, so it can. A runner that cannot write the
item without opening the issue has read the invariant by the time it writes one.
"refuse `host` and `hostaddr`" is refused here. "the loader refuses any other
host" passes, and it is on line 57 of that issue, where it was before the run
started.

The same rule serves the not-yours list, which `SKILL.md` step 7 already calls
"checked, not asserted" and which until now nothing checked.

THE SECOND RULE: **every owed item names the criterion or invariant it fails**,
and the issue holds that name (tracker-tooling issue 13, fix F10 of the audit of
2026-09-23). A retry is a strike, and a strike bought on a ground the issue
never stated is the verify gate grading its own rubric: issue 01 above was
rejected twice on `I-1`, a label the gate wrote, with every criterion passing.
The quotation alone did not stop that, because "the loader refuses any other
host" is the issue's own text in a table no criterion names. A ground with no
name is not a strike: it is a register row, or the criteria are short and
step 8's criteria re-check corrects them. `criteria_ids.py` says what a name is.
The not-yours list needs no name: it excludes, and charges nothing.

WHAT IT DOES NOT DO. It does not read the owed items out of the gate sections.
A verdict is free prose, the gate briefs set no list shape, and extracting a list
from prose is judgement. **The runner names the items; this refuses a brief that
would not work.** That is `correction_brief.py`'s sentence beside this file, and
it is the same division of labour.

Nor does it judge whether a quoted phrase is the RIGHT one. A runner may quote a
real phrase and append the remedy to it, or quote an irrelevant phrase. Neither
is catchable by any script. The quotation is the load-bearing part.

    python3 retry_brief.py --issue <abs path> --attempt 2 \
        --owed 'Invariant "..." is still false: ...' \
        --remedy 'one thing the gate proposed' \
        --not-yours 'Not yours: "..." is already met.'

`--remedy` attaches to the `--owed` item before it. Exit 0 prints the prompt on
stdout. Exit 1 refuses and says why.
Drill: `test_retry_brief.py` beside this file.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import re
import sys

# The one reader of criterion and invariant names, beside this file. Loaded by
# path, so the script works from any directory it is run in.
_IDS_SPEC = importlib.util.spec_from_file_location(
    "criteria_ids", pathlib.Path(__file__).resolve().parent / "criteria_ids.py")
criteria_ids = importlib.util.module_from_spec(_IDS_SPEC)
_IDS_SPEC.loader.exec_module(criteria_ids)

# The per-gate verdict file rules of issue 51 have one home, in
# `correction_brief.py` beside this file: both briefs read the same files.
_CORRECTION_SPEC = importlib.util.spec_from_file_location(
    "retry_brief_correction_brief",
    pathlib.Path(__file__).resolve().parent / "correction_brief.py")
_correction = importlib.util.module_from_spec(_CORRECTION_SPEC)
_CORRECTION_SPEC.loader.exec_module(_correction)
gate_of = _correction.gate_of
wrong_heading_refusal = _correction.wrong_heading_refusal
missing_gate_refusal = _correction.missing_gate_refusal

# `~/.claude/hooks` is NOT in this repo and has no worktree copy, so the hook has
# exactly one home on this machine. Climbing from `__file__` finds
# `.claude/worktrees/hooks` when this runs from a worktree, reads that as "no
# hook installed", and falls open on a machine where the cap is armed. The
# fail-open below is for a machine with no hook, never for a checkout that
# cannot find one. (`correction_brief.py` records the run that taught this.)
HOOK = pathlib.Path.home() / ".claude" / "hooks" / "run-issues-brief-cap.py"

# Where the issue's own text stops. The two gate headings are obvious; the
# implementation record is here because it comes BEFORE them in the file and is
# still not the issue -- it is the previous attempt's own words, and a runner
# allowed to quote those could satisfy this rule with the reasoning that failed.
OWN_TEXT_ENDS = re.compile(
    r"^##\s+(?:verify\s+gate|review\s+gate|implementation\s+record)",
    re.IGNORECASE | re.MULTILINE)

# A retry exists because a gate rejected, so the file holds a verdict.
GATE_HEADINGS = ("## verify gate", "## review gate")

# Straight and typographic double quotes. A phrase in backticks is not a
# quotation: the issue files are full of `identifiers`, and treating one as the
# warrant would let `host` alone satisfy the rule.
#
# TWENTY CHARACTERS, not four. At four, `The guard must refuse "host"
# parameters.` passed -- the gate's remedy with a token in quotes, which is the
# exact shape this file exists to refuse. A criterion phrase is long: "the
# loader refuses any other host", the one the incident dropped, is 33
# characters. The floor costs a correct brief nothing and closes the road round.
WARRANT_CHARS = 20
QUOTED = re.compile(
    r'"([^"]{%d,})"|“([^”]{%d,})”' % (WARRANT_CHARS, WARRANT_CHARS))

AFK = ("\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR THE HUMAN. The human is AFK "
       "for every run. Take one of the two roads above now and carry on.")

# `attempt N` opens the prompt, so it is the FIRST marker the cap hook reads and
# the exemption can never fall to a number written later in an owed item.
PREAMBLE = """RETRY, attempt {attempt}, for {issue}.

Your previous attempt was rejected. Each item below names what is still not true,
quoted from the issue itself. Correct the substance and move on: do not narrate
the earlier mistake, and do not trust any diagnosis attached to it.

Owed:
"""

NOT_YOURS_HEADING = """
Not yours this round, each excluded by the issue's own words:
"""

CLOSING = """
Re-derive from the issue and the code. Return when every owed item is true.
"""

REMEDY_LABEL = ("   One example a gate offered, which is not the specification "
                "and may be incomplete: ")


def hook_module():
    """The cap hook, imported from its own file, or None when it is not there.

    Imported rather than copied so the exemption rule has exactly one home. A
    machine with no hook installed has no cap to fail, so None is not a fault.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "run_issues_brief_cap", HOOK)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (OSError, ImportError, SyntaxError):
        return None


def earns_retry_exemption(prompt) -> bool:
    """True when the cap hook would let this prompt past as a retry."""
    hook = hook_module()
    if hook is None:
        return True
    return hook.exemption(prompt) == "retry"


def own_text(body: str) -> str:
    """The part of an issue file an owed item may quote.

    Everything above the first gate verdict or implementation record: what the
    issue said before anybody worked it.
    """
    end = OWN_TEXT_ENDS.search(body)
    return body[:end.start()] if end else body


def _flat(text: str) -> str:
    """Whitespace collapsed and case dropped, for comparing a quoted phrase.

    The issue file wraps, so a phrase a runner quotes correctly can carry a
    newline the source does not. A rule that broke on a line break would refuse
    correct briefs, and a check people cannot satisfy is a check they route
    around.
    """
    return " ".join(text.split()).lower()


def in_own_text(body: str, phrase: str) -> bool:
    return _flat(phrase) in _flat(own_text(body))


def in_gate_text(body: str, phrase: str) -> bool:
    """True where the phrase is in the file but only below the issue's own text."""
    return _flat(phrase) in _flat(body) and not in_own_text(body, phrase)


def quoted(text: str) -> list:
    """Every double-quoted span of four characters or more, in order."""
    return [(one or two) for one, two in QUOTED.findall(text)]


class Ordered(argparse.Action):
    """Record the flags in the order they were typed.

    `--remedy` attaches to the `--owed` before it, and three separate `append`
    lists cannot say which came first.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        current = getattr(namespace, "ordered", None) or []
        current.append((option_string, values))
        namespace.ordered = current


def read_items(ordered) -> tuple:
    """`(owed, not_yours, refusal)`. `owed` is `(text, [remedies])` pairs."""
    owed, not_yours = [], []
    for flag, value in ordered or []:
        value = (value or "").strip()
        if not value:
            continue
        if flag == "--owed":
            owed.append((value, []))
        elif flag == "--not-yours":
            not_yours.append(value)
        elif flag == "--remedy":
            if not owed:
                return [], [], (
                    "REFUSED. Put the `--owed` item this remedy belongs to "
                    "before it, and re-run.\n"
                    f"  `--remedy {value!r}` arrived with no owed item in front "
                    "of it. A remedy on its own IS the brief that cost issue 01 "
                    "its third attempt: it names what to type and not what must "
                    "become true.\n"
                    "  Two roads out:\n"
                    "  1. Write the owed item first, quoting the invariant from "
                    "the issue, then pass the remedy after it.\n"
                    "  2. Drop the remedy. It is optional, and the owed item is "
                    "not." + AFK)
            owed[-1][1].append(value)
    if not owed:
        return [], [], (
            "REFUSED. Name what is still owed with `--owed`, one per item, and "
            "re-run.\n"
            "  No owed item was given. A retry with nothing owed is not a "
            "retry: `SKILL.md` step 7 reaches this only after a gate rejected, "
            "and a rejection names something.\n"
            "  Two roads out:\n"
            "  1. Re-read the verdicts, name each owed item with a phrase "
            "quoted from the issue, and re-run.\n"
            "  2. If the rejection ground is attributable to your own brief, "
            "annul the strike, journal it as a runner error, and re-spawn "
            "without this script." + AFK)
    return owed, not_yours, ""


def check_warrants(body, items, what) -> str:
    """The refusal for an item that does not quote the issue, or empty."""
    for text in items:
        spans = quoted(text)
        if not spans:
            return (
                f"REFUSED. Quote the issue inside this {what} item, and "
                "re-run.\n"
                f"  {text!r} carries no quoted phrase of "
                f"{WARRANT_CHARS} characters or more. Every {what} item names "
                "the thing the issue itself demands, in the issue's own words, "
                "in double quotes. A sentence in your words is a summary, and a "
                "summary is where a gate's proposed remedy gets in.\n"
                "  Two roads out:\n"
                "  1. Open the issue, find the criterion or the line under "
                "`## Must still be true` that this item fails, and quote it.\n"
                "  2. If nothing in the issue demands it, it is not owed — drop "
                "it, or file a register row." + AFK)
        if any(in_own_text(body, span) for span in spans):
            continue
        from_gate = [span for span in spans if in_gate_text(body, span)]
        if from_gate:
            return (
                "REFUSED. Quote the invariant this item serves, not the gate's "
                "answer to it, and re-run.\n"
                f"  {from_gate[0]!r} is in this issue file, but only inside a "
                "gate verdict or an implementation record. That is a proposed "
                "remedy or a previous attempt's own words, and neither is the "
                "specification. This is the exact shape that cost run "
                "`batch-d67136` issue 01 its third attempt: the brief carried "
                "the gate's fix, the implementer built precisely that, and the "
                "next round rejected on the same guard.\n"
                "  Two roads out:\n"
                "  1. The verdict that proposed it almost certainly names the "
                "invariant too — it is the row that reads FAIL. Quote the "
                "phrase that row cites OUT OF THE ISSUE, and put the remedy "
                "after it with `--remedy`.\n"
                "  2. If no invariant in the issue covers it, the criteria are "
                "at fault: take step 8's criteria re-check rather than buying "
                "another attempt." + AFK)
        return (
            "REFUSED. Quote a phrase that is actually in the issue, and "
            "re-run.\n"
            f"  {spans[0]!r} is nowhere in this issue file above its first gate "
            "verdict. The quotation is the whole warrant: it is what proves the "
            f"{what} item came from the specification rather than from a "
            "verdict, a memory or a paraphrase.\n"
            "  Two roads out:\n"
            "  1. Open the issue and copy the phrase exactly, including its "
            "punctuation.\n"
            "  2. If the issue genuinely does not say it, it is not owed — take "
            "step 8's criteria re-check." + AFK)
    return ""


def check_names(body, items) -> str:
    """The refusal for an owed item that names no criterion the issue holds."""
    held = criteria_ids.known_ids(own_text(body))
    for text in items:
        named = criteria_ids.named_ids(text)
        missing = [name for name in named if name not in held]
        if named and not missing:
            continue
        what = (f"names {', '.join(missing)}, which the issue does not hold"
                if missing else "names no criterion and no invariant")
        return (
            "REFUSED. Name the criterion or invariant this owed item fails, "
            "and re-run.\n"
            f"  {text!r} {what}. The issue holds "
            f"{', '.join(sorted(held)) or 'no numbered criterion at all'}. A "
            "retry is a strike, and a strike is bought only on a ground the "
            "issue states. Write `criterion 3` or `C3`, `invariant 4` or "
            "`I4`, or the issue's own label such as `M9`.\n"
            "  Two roads out, and neither charges a strike:\n"
            "  1. The ground is real and outside this issue: file it as a "
            "register row and drop it from the owed list.\n"
            "  2. The ground is real and the issue should have stated it: "
            "take step 8's criteria re-check, which corrects the criteria." + AFK)
    return ""


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
            "REFUSED. Give a readable issue file and re-run.\n"
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
                "REFUSED. Check the rejecting gate wrote its verdict into this "
                "file, then re-run.\n"
                f"  {where} holds neither `## Verify gate` nor `## Review gate`. A "
                "retry exists because a gate rejected, so a file with no verdict in "
                "it means the grounds came from somewhere else — most often the "
                "worktree twin, or a gate that wrote beside its private copy.\n"
                "  Two roads out:\n"
                "  1. Pass the run's verdict file with `--verdicts`, and re-run. "
                "Since 2026-09-23 a gate writes there and never into the issue "
                "file.\n"
                "  2. Run `check_verdict.py --file <this file> --section \"## Verify "
                "gate\"` to see which gate returned nothing, and ledger the issue "
                "`blocked` with what it prints." + AFK)
    return missing_gate_refusal(issue_body, paths)


def compose(issue, attempt, owed, not_yours) -> str:
    """The spawn prompt: the marker, the issue, the two lists, and nothing else."""
    body = PREAMBLE.format(attempt=attempt, issue=issue)
    for number, (text, remedies) in enumerate(owed, 1):
        body += f"{number}. {text}\n"
        for remedy in remedies:
            body += REMEDY_LABEL + remedy + "\n"
    if not_yours:
        body += NOT_YOURS_HEADING
        for number, text in enumerate(not_yours, 1):
            body += f"{number}. {text}\n"
    return body + CLOSING


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
    parser.add_argument("--attempt", required=True, type=int,
                        help="which attempt this brief buys; 2 or more")
    parser.add_argument("--owed", action=Ordered, dest="ordered",
                        metavar="TEXT", help="one owed item; repeatable")
    parser.add_argument("--remedy", action=Ordered, dest="ordered",
                        metavar="TEXT",
                        help="an example fix, attached to the --owed before it")
    parser.add_argument("--not-yours", action=Ordered, dest="ordered",
                        metavar="TEXT", help="one excluded item; repeatable")
    args = parser.parse_args(argv)

    if args.attempt < 2:
        print(
            "REFUSED. Pass the attempt number this brief buys, which is 2 or "
            "more, and re-run.\n"
            f"  `--attempt {args.attempt}` is a first attempt, and a first "
            "attempt is not a retry. The number is also what earns the cap "
            "hook's retry exemption: at 1 the composed brief is measured "
            "against the 400-word cap and refused at the spawn.\n"
            "  Two roads out:\n"
            "  1. Re-run with the real attempt number off the ledger.\n"
            "  2. If this genuinely is the first attempt, it needs no owed list "
            "— spawn from the issue file." + AFK, file=sys.stderr)
        return 1

    refusal = check_issue(args.issue, args.verdicts)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    body = pathlib.Path(args.issue).read_text(encoding="utf-8", errors="replace")

    owed, not_yours, refusal = read_items(getattr(args, "ordered", None))
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    refusal = (check_warrants(body, [text for text, _ in owed], "owed")
               or check_names(body, [text for text, _ in owed])
               or check_warrants(body, not_yours, "not-yours"))
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    prompt = compose(args.issue, args.attempt, owed, not_yours)
    if not earns_retry_exemption(prompt):
        print(
            "REFUSED. Move `attempt <n>` into the opening of this file's "
            "`PREAMBLE` and re-run.\n"
            "  The composed prompt does not earn the cap hook's retry "
            "exemption, so `run-issues-brief-cap.py` would refuse the spawn as "
            "an over-long first attempt. The marker is read off the FIRST "
            "`attempt N` in the prompt, and a retry's owed list is the varying "
            "part that cannot be cut to fit the cap.\n"
            "  Two roads out:\n"
            "  1. Fix `PREAMBLE` so the marker opens it, and re-run.\n"
            "  2. Spawn with `attempt <n>` written by hand as the prompt's "
            "first line, and file a register row against this script." + AFK,
            file=sys.stderr)
        return 1

    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
