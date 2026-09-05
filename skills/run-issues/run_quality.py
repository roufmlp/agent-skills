#!/usr/bin/env python3
"""What a run was worth inside itself, and whether its model trial holds.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 4 (deliverable 4; rulings 13, 15, 21.3 and 22).

## The three things this prints, and where each comes from

1. **The per-role table, FROM THE TRANSCRIPTS.** Ruling 21.3 is explicit that
   the finale reads what RAN, never what the ledger asked for -- the ledger is
   the thing under test, so a table built from it could not fail. Sitting 3
   built the reading; `run_session.render_roles` is it, and this module calls it
   rather than growing a second one.
2. **Three quality figures per issue** (rulings 13 and 15): first-attempt gate
   passes against rejections, correction rounds, strikes. These come off the
   ledger's status table, which is the only place they exist.
3. **The trial verdict** (ruling 22). `model-landed-check.py` has written one
   line per spawn into the run journal since sitting 2, saying what each
   subagent actually ran on and marking `**MISMATCH**` on a fault. Until this
   sitting nothing read those lines. Any mismatch voids the run's trial row.

## The per-issue figures parse PROSE, and that is the limit worth stating

The ledger's Notes cell is free text. Three of the figures ruling 15 asks for
have a marker the runner writes -- `attempt N` and `criteria reset`, which
`check_attempt_cap.py` reads -- and the rest do not. A gate's verdict and a
strike are sentences.

Measured 2026-09-06 over the 16 ledgers in `.scratch/example-feature` that
hold a status table, 143 issue rows: this reader grades 141 and leaves 2
`unread`, and both of those genuinely state no verdict. Getting there cost SEVEN
dialects the first reading could not see, and the first reading was measured
against `batch-b5e96d` alone. Bolded verdicts, `attempt 1:` and `attempt 1.`,
`gates both pass`, `v: pass · r: reject`, `rejected by BOTH gates`, `one
correction round`, `correction 18:48->18:54` and `correction open 04:06` are all
in use, and every one of them was read as silence.

**The durable fix is a marker, not a wider regex**, and it is the story
`check_attempt_cap.py` tells about itself: the older `implement`/`retry`
vocabulary could not be counted, so `attempt N` was minted and the runner writes
it. A `verdict:` and a `strike:` marker would do the same here. That is not this
sitting's build -- it changes what the runner writes into every row and it only
starts counting from the next run -- and ticket 37 ruling 6 puts these figures
on a per-run line, so it is that ticket's question. Until then: a row this
cannot read prints `unread`, never a pass, and the corpus test beside this file
is what catches a regex narrowed by a later edit.

## Void is not a failure, and this can never halt anything

Ruling 22, in the human's terms: the work is still good work and only the
experiment is void. So a void verdict is a sentence in the merge briefing, and
every road through `main` exits 0 -- the same discipline `run_costs.py` carries,
for the same reason. A finale that stopped on a measurement would cost a run.

## Where the void mark lives, and why it is not written anywhere else

Ruling 22 marks "the run's trial row", and ticket 37 of the pilot-delivery map
owns that table. It is not built yet, and the series order is 38, 39, 36, 37,
33. The human ruled on 2026-09-06: they start ticket 37 immediately after this
sitting and before any run, so no run occurs in the gap and any interim home
would never hold a row. The mark therefore goes into the merge briefing alone,
and the ANSWER lives in `trial_verdict` -- one function, which ticket 37 calls
to fill its per-run field. One reader, so the two can never drift.
"""

from __future__ import annotations

# The three states a trial can be in. `unmeasured` is not `holds`: a journal
# with no landed line proves nothing, and reporting it as a pass would tell
# ticket 37 that the map landed when nothing looked.
VOID = "void"
HOLDS = "holds"
UNMEASURED = "unmeasured"

import re
from dataclasses import dataclass

# The line `model-landed-check.py` appends per spawn, anchored at the start of
# the line. The marker word alone is not enough: a journal is prose plus
# records, and the finale writes ABOUT mismatches in the same file.
LANDED = re.compile(r"^- model landed: .*$", re.MULTILINE)
MISMATCH = "**MISMATCH**"

# **A landed line is not automatically evidence.** The hook ends each line with
# a parenthetical saying what it had to compare against, and only one of the
# four is a comparison: `(ledger asked opus)`. The other three -- `no map in the
# ledger`, `the ledger's map line is damaged`, `the ledger could not be read` --
# say the spawn ran and nothing about whether it ran on what was ASKED. So does
# `ran on unmeasured`, which is a transcript the hook could not read.
#
# Found by the review of 2026-09-06: without this, a journal of lines that
# compared against nothing printed "All 2 mapped spawn(s) ran on the model and
# at the effort the ledger asked for". This module's docstring already forbids
# that reasoning one level up; the rule now runs per line as well.
COMPARED = "(ledger asked "

# Three ways a line carrying `(ledger asked ...)` still compared nothing. The
# first two are the hook's own words for a reading it could not make: a model
# name whose tier `model_map.tier_name` does not know leaves it with no tier to
# compare, and its comment says so -- "a gap in the reading, not evidence the
# map failed". The third is an effort nothing read, and ruling 7 puts effort in
# the ledger beside the model, so a line missing it has proved half of what the
# `holds` sentence claims.
PROVES_NOTHING = ("ran on unmeasured", "(unknown tier)",
                  "at effort unmeasured")


def _is_evidence(line):
    return COMPARED in line and not any(mark in line for mark in PROVES_NOTHING)


@dataclass
class Verdict:
    """Whether this run's model trial may be compared against another's."""

    state: str = UNMEASURED
    spawns: int = 0
    # How many of those spawns the hook could actually compare against the map.
    # `spawns - proved` is the number that prove nothing either way.
    proved: int = 0
    mismatches: tuple = ()

    @property
    def void(self):
        return self.state == VOID


def trial_verdict(journal_text):
    """The trial's state, read off the journal lines the landed check writes.

    **This is the function ticket 37 calls.** Text in, verdict out, no disk, so
    the briefing and ticket 37's per-run row answer from one reader.
    """
    lines = LANDED.findall(journal_text or "")
    if not lines:
        return Verdict()
    faults = tuple(line for line in lines if MISMATCH in line)
    proved = sum(1 for line in lines if _is_evidence(line))
    if faults:
        state = VOID
    elif proved:
        state = HOLDS
    else:
        # Every line compared against nothing, so the journal is as silent on
        # the map as an empty one is.
        state = UNMEASURED
    return Verdict(state=state, spawns=len(lines), proved=proved,
                   mismatches=faults)



import argparse
import importlib.util
import os
import sys


def _load(name, filename):
    """Load a sibling script by path, exactly as `run_session.py` does.

    Registered in `sys.modules` before it runs: a `@dataclass` in the loaded
    file resolves its annotations through `sys.modules[cls.__module__]`, and on
    Python 3.14 that lookup raises when the module is absent.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    existing = sys.modules.get(name)
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing  # One instance per file; two would diverge on any state.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The status table is read by `check_commit_order.py:115`, which already owns
# the two header shapes and the id-by-column rule. Reusing it rather than
# copying it is the lesson `journal_for` taught this ticket in sitting 2: two
# readers of one table drift, and the drift is silent.
_ORDER = _load("check_commit_order", "check_commit_order.py")

status_rows = _ORDER.status_rows

# A correction round, in the two shapes the ledgers use: `correction: open ->
# closed 12:33` and `correction 18:48→18:54`. A colon or a digit must follow,
# which is what keeps `no correction round` out of the count -- the denial is
# followed by a word.
#
# **The colon was required until the review of 2026-09-06**, which found three
# rounds in `archive-run-b3f7a1-merged.md` and seven in `f180e3` written the
# second way and counted as none.
ROUND = re.compile(r"\bcorrection\b\s*(?::|\d|open\b)", re.IGNORECASE)

# A third shape, counted by the number it names: `one correction round ·
# committed ...`. Seven rows of `archive-run-batch-fd4fa2-merged.md` are
# written this way and were counted as none.
#
# **`a correction round` is deliberately NOT an alternative**, and the reason is
# measured: across the corpus it matches three times and not one is a record of
# a round -- once reasoning about one, and twice inside `not a correction
# round`, which is a DENIAL. It has no true positive anywhere. Three rows say
# `no correction round` and two say `not a correction round`; the lookbehind
# holds the numbered words to the same rule.
WORDED_ROUNDS = re.compile(
    r"(?<!not )(?<!Not )\b(one|two|three|four)\s+correction\s+rounds?\b",
    re.IGNORECASE)
HOW_MANY = {"one": 1, "two": 2, "three": 3, "four": 4}

# `attempt 1`, `attempt 2` — the marker `check_attempt_cap.py:37` reads, and the
# only countable record of a round.
#
# **The lookahead is narrower here than in that file, and the difference is
# measured.** It forbids `attempt 1:` and `attempt 1.` there, so that `retry
# 00:18` (a clock) and `retry 10.2` (minutes) cannot be counted. Fifteen rows of
# `archive-run-batch-44d0a8.md` write `attempt 1.` and one row of
# `archive-run-batch-fd4fa2-merged.md` writes `attempt 1:`, and the borrowed
# pattern DELETED those rounds: issue 386 read one attempt passing when its
# first was rejected twice. So a clock and a decimal are still refused -- a
# digit may not follow the `:` or the `.` -- and ordinary punctuation is not.
ATTEMPT = re.compile(r"\battempt\s+(\d+)(?!\d)(?!:\d)(?!\.\d)",
                     re.IGNORECASE)

# `criteria reset`, `criteria-fault reset`. Same pattern, same file.
RESET = _load("check_attempt_cap",
              "check_attempt_cap.py").MARKER["criteria reset"]

# A gate stating its verdict, and NOTHING else that names a gate. The verdict
# word must sit against the role word, with only a variant name, a separator
# and markdown emphasis allowed between: `verify: pass`, `review REJECT`,
# `Verify pass`, `review(critical): **reject**`, `verify **reject** + review`.
#
# **The emphasis half was missing until the review of 2026-09-06.** Measured
# that day over the 16 ledgers holding a status table: 7 of them bold a verdict
# word somewhere, across 17 rows, and `batch-b5e96d` -- the only ledger this was
# first measured against -- is one of the 9 that never do. Two of the seven,
# `archive-run-395-397-merged.md` and `archive-run-batch-45c8b1.md`, reported
# `0 strike(s)` without this half; the other five undercounted. On 45c8b1 issue
# 520b the plain `verify: pass` beside `review(critical): **reject**` was read,
# and the row came out a first-attempt pass.
#
# It still matches none of the prose about gates: `the review gate's own words`,
# `both gates concurrent` and `the gates SPLIT` all fall outside it, because a
# verdict word must follow.
VERDICT = re.compile(
    r"\b(verify|review|v|r)\b(?:\s*\([a-z-]+\))?(?:\s+gate)?\s*:?\s*\**"
    r"\b(pass(?:es|ed)?|accept(?:s|ed)?|reject(?:s|ed)?)\b",
    re.IGNORECASE)

# The verdict stated as a verb, with the gates after it: `attempt 1 rejected by
# BOTH gates`. Two rows of `archive-run-batch-44d0a8.md`.
BY_THE_GATES = re.compile(
    r"\b(passed|accepted|rejected)\s+by\s+(?:both\s+)?(?:the\s+)?gates?\b",
    re.IGNORECASE)

# One verdict for the PAIR, which is how the older ledgers write a round:
# `gates r1 **both reject** 03:03/03:05`, `gates 07:36→08:03, both pass`. The
# gates are not named, so `VERDICT` cannot see it -- six of ten rows in
# `archive-run-f180e3-merged.md` and two of five in `399-403` read `unread`
# until the review of 2026-09-06 found them. `both` must be followed by the
# verdict, with only `gates` and emphasis between, which keeps out `both gates
# concurrent`, `Both agree the fact is real` and `both halves are wanted`.
PAIR = re.compile(
    r"\bboth\b(?:\s+gates?)?\s*\**\s*"
    r"\b(pass(?:es|ed)?|accept(?:s|ed)?|reject(?:s|ed)?)\b",
    re.IGNORECASE)

REJECTED = ("reject", "rejects", "rejected")

# The row denying a strike this reader counted. Two shapes cover every
# denial in the corpus: a negated `strike` -- `NOT a strike`, `charging no
# strike` -- and the annulment verb, `annulled from any strike`, `the strikes
# are annulled`. A third alternative for `charg\w* no strikes?` stood here
# until mutation testing on 2026-09-06 proved it could never be the reason for
# a match, because the negation alternative already reads that string.
DENIAL = re.compile(
    r"\b(?:not|no|never)\s+(?:a\s+)?strikes?\b"
    r"|\bannull?(?:ed|s)\b",
    re.IGNORECASE)

# What the first attempt's gates did. `unread` is its own answer: a row stating
# no verdict is a gap in the record, and reporting it as a pass would put a
# figure in the briefing that nothing measured.
PASS = "pass"
REJECT = "reject"
UNREAD = "unread"


@dataclass
class Issue:
    """One issue's inside-run quality, ruling 15's three figures."""

    issue: str = ""
    attempts: int = 0
    first_attempt: str = UNREAD
    corrections: int = 0
    strikes: int = 0
    flags: tuple = ()


def attempt_segments(row):
    """`((n, text), ...)` — one span per attempt, in order.

    An attempt's span runs from the first marker naming it to the next marker
    IN THE TEXT. Two facts from run `batch-b5e96d` force that rule rather than a
    plain split: issue 527 writes `attempt 2` twice, once as running and once
    with its verdicts, and issue 549's correction text cites `attempt 1's
    record` after the round closed. Splitting on occurrences reads three
    attempts on 527 and two on 549, and both are wrong.

    **The cut follows the text and not the numbers.** Slicing from a number's
    marker to the NEXT NUMBER's marker gives a backwards slice on any row that
    names a later attempt first, and Python returns a backwards slice as "" --
    so the span reads `unread` on a row that plainly states its verdicts. Cut in
    reading order and no span can be empty.
    """
    marks = [(int(m.group(1)), m.start()) for m in ATTEMPT.finditer(row or "")]
    if not marks:
        return ()
    starts = {}
    for number, where in marks:
        starts.setdefault(number, where)
    in_text = sorted(starts.items(), key=lambda pair: pair[1])
    found = []
    for index, (number, where) in enumerate(in_text):
        end = in_text[index + 1][1] if index + 1 < len(in_text) else len(row)
        found.append((number, row[where:end]))
    return tuple(sorted(found))


def gate_verdicts(text):
    """`((role, outcome), ...)` stated in this span, lowercased.

    A pair verdict is filed under the role `both`, because it is one statement
    about two gates and splitting it into two would invent a row.
    """
    named = [(role.lower(), word.lower())
             for role, word in VERDICT.findall(text or "")]
    paired = [("both", word.lower())
              for word in PAIR.findall(text or "")
              + BY_THE_GATES.findall(text or "")]
    return tuple(named + paired)


def _outcome(text):
    verdicts = gate_verdicts(text)
    if not verdicts:
        return UNREAD
    return REJECT if any(w in REJECTED for _, w in verdicts) else PASS


def issue_quality(ledger_text):
    """Ruling 15's three figures, one row per issue in the status table."""
    found = []
    for issue, row in status_rows(ledger_text or ""):
        segments = attempt_segments(row)
        # A row with no `attempt` marker is graded whole. The marker landed on
        # 2026-08-17 and older ledgers are still read.
        spans = segments or ((1, row),)

        strikes, flags = 0, []
        for number, text in spans:
            rejected = _outcome(text) == REJECT
            if rejected:
                strikes += 1
            if RESET.search(text):
                # `SKILL.md` step 8: the earlier attempts were graded against a
                # spec that no longer exists, so every strike to here goes, not
                # one of them. Run `batch-b5e96d`'s issue 531 says the same in
                # its own words -- "the strikes are annulled".
                strikes = 0
            elif rejected and DENIAL.search(text):
                # The row denies a strike this reader counted, and no reset
                # explains it. `SKILL.md` step 5's prose-deletion road ends a
                # rejected round with no strike and writes no marker, so the
                # count cannot see it. Neither answer is silently preferred.
                flags.append(
                    f"issue {issue}, attempt {number}: the round was rejected "
                    f"and the row denies the strike. Counted as one; read the "
                    f"row before quoting the figure.")

        found.append(Issue(
            issue=issue,
            # 0 means the row carries no `attempt N` marker, not that nothing
            # was attempted. `render_quality` prints that cell as `not
            # recorded`, because a row reading 0 on an issue that shipped is a
            # false figure in a briefing.
            attempts=len(spans) if segments else 0,
            first_attempt=_outcome(spans[0][1]),
            corrections=(len(ROUND.findall(row))
                         + sum(HOW_MANY[word.lower()]
                               for word in WORDED_ROUNDS.findall(row))),
            strikes=strikes,
            flags=tuple(flags),
        ))
    return tuple(found)


# Ruling 22 in full, because a reader who meets `VOID` with no explanation
# reads it as a failed run and questions a merge that is fine.
VOID_MEANS = (
    "The work is still good work and only the experiment is void. Nothing was\n"
    "halted, nothing is unmerged for this, and every issue stands on its own\n"
    "gates. What a void trial means is narrower: this run may not be compared\n"
    "against another run to read a model choice.")


def render_verdict(verdict):
    """The trial block for the merge briefing — ruling 22's whole output."""
    if verdict.state == UNMEASURED:
        if not verdict.spawns:
            return (
                "Trial: **not measured**. The run journal holds no `model "
                "landed:` line, so\nnothing looked at what the workers ran on. "
                "This is a missing measurement and\nnot a fault: a run from "
                "before the landed check, or one whose hook never fired.\nDo "
                "not read it as a pass.")
        return (
            f"Trial: **not measured**. The journal holds {verdict.spawns} "
            "landed line(s) and not one\nof them compared what ran against a "
            "map: the ledger had no map line, or its map\nline was damaged, or "
            "the subagent's transcript could not be read. The spawns\nhappened; "
            "nothing here says they landed. Do not read it as a pass.")
    if not verdict.void:
        text = (
            f"Trial: **holds**. {verdict.proved} of {verdict.spawns} mapped "
            "spawn(s) ran on the model and\nat the effort the ledger asked "
            "for, read from each subagent's own transcript.")
        short = verdict.spawns - verdict.proved
        if short:
            text += (
                f"\n\nThe other {short} compared against nothing -- no map "
                "line, a damaged map line, a\nmodel name the tier order does "
                "not know, an effort nothing read, or a\ntranscript that could "
                "not be read -- so they are neither evidence for the\ntrial nor "
                "against it.")
        return text
    lines = [
        f"Trial: **VOID**. {len(verdict.mismatches)} of {verdict.spawns} mapped "
        f"spawn(s) did not run on what\nthe ledger asked for.",
        "",
        VOID_MEANS,
        "",
        "The lines, as the landed check wrote them:",
        "",
    ]
    lines.extend("  " + line.strip() for line in verdict.mismatches)
    return "\n".join(lines)


def render_quality(rows):
    """Ruling 15's three figures, one line per issue, with the run's totals."""
    if not rows:
        return ("No status table was read, so there are no per-issue quality "
                "figures. This is a\nmissing measurement, not a clean run.")
    head = (f"{'issue':<8} {'attempts':>12} {'first attempt':>14} "
            f"{'corrections':>12} {'strikes':>8}")
    lines = [head, "-" * len(head)]
    for row in rows:
        mark = " *" if row.flags else ""
        # A row from before the `attempt N` marker landed (2026-08-17) still
        # ran at least one attempt, so 0 is a number nothing measured.
        attempts = str(row.attempts) if row.attempts else "not recorded"
        lines.append(f"{row.issue:<8} {attempts:>12} "
                     f"{row.first_attempt:>14} {row.corrections:>12} "
                     f"{str(row.strikes) + mark:>8}")
    passes = sum(1 for r in rows if r.first_attempt == PASS)
    rejects = sum(1 for r in rows if r.first_attempt == REJECT)
    unread = sum(1 for r in rows if r.first_attempt == UNREAD)
    lines.append("")
    lines.append(
        f"{len(rows)} issue(s): {passes} passed both gates first time, "
        f"{rejects} were rejected, {unread} unread.")
    lines.append(
        f"{sum(r.corrections for r in rows)} correction round(s), "
        f"{sum(r.strikes for r in rows)} strike(s).")
    flagged = [flag for row in rows for flag in row.flags]
    if flagged:
        lines.append("")
        lines.append(
            "* The strike column is DERIVED, from rounds rejected since the "
            "last criteria\n  reset. `SKILL.md` permits two annulments that "
            "write no marker -- a runner\n  error, and step 5's prose-deletion "
            "road -- so where the row's own words\n  disagree with the count, "
            "both are shown and neither is preferred:")
        lines.extend("  - " + flag for flag in flagged)
    return "\n".join(lines)


HEADING = "## What each role ran on, and whether the trial holds"

WHERE_THE_TABLE_COMES_FROM = (
    "Read from the TRANSCRIPTS, never from the ledger (ticket 39, ruling 21.3).\n"
    "The ledger is the thing under test here, so a table built from it could\n"
    "not fail. No figure below is added across models: a weighted fable token\n"
    "and a weighted opus token are not the same quantity. To read a model\n"
    "trial, compare the SAME ROLE across runs.")


# Ruling 15's three figures are PER ISSUE, and a hunt has none: it resolves
# register rows, and it never runs an attempt, a gate round or a correction
# round. Printing the run's "missing measurement" sentence there would report a
# hole where there is nothing to fill.
NO_ISSUES = ("This is a hunt, so there are no per-issue quality figures: a hunt "
             "has no issues,\nno attempts and no correction rounds. The trial "
             "verdict and the per-role table\nabove are the whole of ruling "
             "15's reading for a round.")

# The third kind: no ledger was found, so nothing says whether this was a run
# or a hunt. Both sentences above would be a claim. Found by the review of
# 2026-09-06 on a hunt whose `round-brief.md` had already been deleted, which
# took the run road and was told to go and find a status table it never had.
NO_LEDGER = ("No ledger was found for this batch, so nothing says whether it "
             "was a run or a\nhunt and there is no status table to read. See "
             "what could not be read, below.")


def render_block(spawns, rows, verdict, kind="run"):
    """The whole section the finale or the round end pastes, heading and all."""
    session = _load("run_session", "run_session.py")
    hunt = kind == "hunt"
    if kind == "unknown":
        quality = NO_LEDGER
    else:
        quality = NO_ISSUES if hunt else render_quality(rows)
    return "\n".join([
        HEADING,
        "",
        render_verdict(verdict),
        "",
        WHERE_THE_TABLE_COMES_FROM,
        "",
        "```",
        session.render_roles(spawns),
        "```",
        "",
        {"hunt": "### Inside-round quality",
         "unknown": "### Inside-run quality"}.get(
             kind, "### Inside-run quality, per issue"),
        "",
        "```",
        quality,
        "```",
    ])


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def main(argv=None):
    """Print the block. Exit 0 on every road, including every failure.

    `finale.md` step 4 already carries the rule for the cost readings and this
    obeys the same one: a measurement that could halt a finale would cost a run
    the thing the measurement is about. Whatever cannot be read is printed as
    text and the block is still written.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", help="batch id, e.g. batch-b5e96d")
    parser.add_argument("--repo", help="repository to walk; default the cwd's")
    parser.add_argument("--ledger", help="a ledger path, instead of --batch")
    parser.add_argument("--journal", help="a journal path; default beside the ledger")
    args = parser.parse_args(argv)

    session = _load("run_session", "run_session.py")
    ledgers = _load("find_live_ledger", "find_live_ledger.py")

    # Walked ONCE and passed to both readers. Each finds a ledger on its own,
    # and two `git worktree list` calls per invocation is the same class of
    # waste the 2026-09-06 review found in the launch reading.
    # Wrapped, because `git -C <not a repository> worktree list` exits 128 and
    # `list_worktrees` lets that out. `finale.md` promises this can never halt
    # the finale, and an uncaught raise is exactly a halt.
    trees, walk_failed = None, ""
    if args.batch:
        try:
            trees = ledgers.list_worktrees(args.repo)
        except Exception as error:
            trees = []
            walk_failed = (
                f"The worktrees of `{args.repo or os.getcwd()}` could not be "
                f"read ({error}),\nso nothing was searched for batch "
                f"`{args.batch}` -- no ledger, no transcript, no journal.")

    # The basename decides a ledger's kind, which is the rule
    # `find_live_ledger.journal_for` already uses to pick the journal beside it.
    # `--batch` overwrites this from the candidate below; `--ledger` has nothing
    # else to go on.
    notes = [walk_failed] if walk_failed else []
    path, spawns = args.ledger, []
    kind = "hunt" if os.path.basename(path or "") == "round-brief.md" else "run"
    if not path:
        if not args.batch:
            print("Pass --batch or --ledger. Nothing was read.")
            return 0
        found = None if walk_failed else session.ledger_for_batch(
            args.batch, worktrees=trees)
        if found is None:
            # `sessions_for_batch` below says the same thing at more length, so
            # this road leaves the sentence to it rather than printing two.
            kind = "unknown"
        else:
            path, kind = found.path, found.kind

    if args.batch and not walk_failed:
        transcripts, refusal = session.sessions_for_batch(
            args.batch, worktrees=trees)
        if refusal:
            notes.append(refusal)
        else:
            spawns = session.spawn_rows(transcripts)

    text = _read(path) if path else None
    rows = issue_quality(text) if text is not None else ()
    if path and text is None:
        kind = "unknown"
        notes.append(f"The ledger at {path} could not be read.")

    journal = args.journal or (ledgers.journal_for(path) if path else None)
    journal_text = _read(journal) if journal else None
    if journal and journal_text is None:
        # A journal that could not be OPENED is not a journal holding no
        # lines. Saying "holds no `model landed:` line" would state a fact
        # about contents nobody read.
        notes.append(f"The journal at {journal} could not be read, so the "
                     "trial verdict above\nrests on nothing.")
    verdict = trial_verdict(journal_text or "")

    print(render_block(spawns, rows, verdict, kind=kind))
    if notes:
        print()
        print("What could not be read:")
        for note in notes:
            print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
