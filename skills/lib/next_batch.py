#!/usr/bin/env python3
"""Pick the next batch of issues for a run, in an order that honours every blocker.

    python3 ~/.claude/skills/lib/next_batch.py <issues dir> --count N
        [--theme <name>] [--by number]
        [--queued released|held|fresh] [--queued-fresh-days D]

Asked for on 2026-09-13. The human scheduled runs by hand, and on that day nearly put
issue 05 ahead of issue 37, which builds the connection every one of 05's criteria
needs, because 05's `## Blocked by` named only a merged issue and the real dependency
sat in prose. This tool reads every issue file, works out what is reachable, and
prints a table of the batch plus up to three commands:

    /harden-issues 64 66 67          harden these BEFORE the run; see HOW IT RANKS
    /harden-issues 34 35 45          members that have to be hardened first
    /run-issues 37 05 05d 38 ...     members ready to be built, in order

A command with nothing to list is not printed at all, and NO NUMBER SITS ON TWO of
them: both are lines a reader pastes, and a number carried by two teaches the
reader to skip one.

THE QUESTION IT ANSWERS IS "WHAT CAN I START TODAY", and the answer has three
shapes. Which one fired is the first thing it prints.

    1  NOTHING CAN START          every candidate depends on work that exists only
                                  on an unmerged run's branch. The run that must
                                  merge is named, the batch that merge releases is
                                  printed, and NO `/run-issues` line is printed
                                  with it. Exit 1.
    2  SOME CAN START IN PARALLEL a run is live, and these issues have every
                                  blocker done or closed IN MAIN. They are printed
                                  with their `/run-issues` line; everything else is
                                  printed under the run or the harden it waits on.
                                  Exit 0.
    3  (no heading)               no run is live, so there is one reading of the
                                  tracker and this is the batch. Exit 0, and the
                                  count still REFUSES when it cannot be honoured.

Shape 2 is a claim about DEPENDENCIES and nothing else. Whether two sessions would
edit the same file is in no issue file, so this tool does not assert it.

WHAT IT READS. An issue number is any run of digits with an optional letter suffix:
`07`, `05b`, `641`, `149e`. It was capped at two digits until 2026-09-13, which
dropped every issue from 100 up: the file did not match, `load_issues` never held it,
and the tool neither offered it nor counted it. That broke this file's own promise
that it never silently drops work. One tracker in use carries 641 issues, measured
that day for issue 03 of the set that widened this, so the case is live. A leading
ISO date is not an issue number: a bullet opening `- 2026-09-13 ruling ...` is
prose, and a dated note beside the issue files is a note.

`Status:` is the first token after the colon; `done` and `closed` are
satisfied and never batch members, `ready-for-agent` and `needs-harden` are candidates,
`parked` is neither (see WHAT PARKED MEANS), anything else is a refusal. The `## Blocked by` section, when present, is read bullet by
bullet (a heading such as `## Blocked by, and the order` counts too): a bullet
counts as a blocker only when its first token, after any `**` and
backticks, is an issue number (`02c`, `02-sign-in-users-sessions`). Bullets like
`None`, `Not blocked by ...`, `Nothing waits on the human` and prose paragraphs are not
blockers. A file with no section has no blockers; measured on 2026-09-13, the nine such
files genuinely had none.

`- Unknown until hardened` is not a blocker either, and it is the one non-blocker
bullet a script writes. Promotion mints an issue off a register row and cannot know
what that issue blocks, because it never reads the code; the harden pass does read the
code and writes the real edges. So a minted file carries that bullet as the explicit
null, which is what tells a reader a minted issue from a hardened one with no blockers,
and this tool places such an issue exactly as it places one reading `- None`. Issue 02
of that same set, ruled by the human on 2026-09-13.

HOW IT ORDERS. A candidate joins the batch once every blocker is satisfied: `done`,
`closed`, or a `ready-for-agent` member already placed. Among the candidates free at
each step the one with the largest FAN-OUT goes first, and the lowest number breaks
that tie (`05` before `05b` before `09` before `10`). An issue's fan-out is the count
of open issues downstream of it through `## Blocked by`, transitively and counted
once each, so a diamond gives the top issue three and not four. Open means neither
`done` nor `closed` nor held by a run ledger nor parked (see WHAT PARKED MEANS:
an issue this tool will not offer carries no leverage). `--by number` restores the
old order, which is number alone, so a reader can compare the two on one tracker.
A `needs-harden` member does not satisfy anything, because hardening writes criteria
and ships no code: an issue behind one is out of reach until the hardening lands and
this tool is run again.

Ruled by the human on 2026-09-13. Until that day the tie-break was the number alone.
Measured the same day on one tracker: issue 37 sat upstream of 56 open issues and the
05 family upstream of 48 to 55 each, and the script still listed them by number.

HOW IT RANKS THE HARDEN LINE, the same ruling. A needs-harden issue never appeared in
a `/harden-issues` line unless the count exhausted every ready issue, because its
number is higher, so no agent ever told the human to harden an upstream issue before
a run. The first command line names two kinds of needs-harden issue:

    BLOCKING   it stands in the way of a candidate the placement wanted. That
               candidate is listed under the count line as `35 waits on harden of
               34`, and only where EVERY blocker still in its way is a harden: a
               promise with a second condition hidden in it is worse than no line.
               An issue that also waits on a run stays out of that list, and the
               count line's refusal names the run instead. Ruled by the human on
               2026-09-13, walking the three defaults this line was built on.
    MINTED     its `Origin:` issue has a fan-out above zero. `Origin: 05/batch-<id>`
               means the issue changes what 05 built, and everything downstream of 05
               calls that code, so it inherits 05's fan-out as its rank. Severity from
               its `Rows:` line breaks the tie inside one rank, high before medium, and
               the number breaks that. An origin of `unknown`, an origin no file
               carries, and an origin with fan-out zero all stay out of the line.

The blocking kind is listed before the minted kind, because a blocker holds up work
the count asked for today; fan-out orders each kind inside itself. A batch member is
named by the members line below and never by this one: both are commands a reader
pastes, and a number carried by both teaches the reader to skip one. Both ruled by
the human on 2026-09-13.

This answers "which of the run's new issues do I harden before the next run" without
anyone reading the briefing. The human read it by hand for one run on 2026-09-13, and
the answer was the five issues minted from 05, 05b and 05d. A run-held issue is never
offered in either kind.

WHAT THE LEDGERS ADD. `Status:` in an issue file does not change until a run MERGES,
so an issue that a run has built, or is building now, still reads `ready-for-agent`.
Measured 2026-09-13: one run had all eight of its issues at `done` and this
tool still offered five of them as a fresh batch, and it missed that issue 05 had just
become unblocked by two of them. So the tool also reads every run ledger,
`<feature>/runs/<batch>/run.md`, where `runs/` is the sibling of the issues directory
(a missing `runs/` is harmless). Each ledger's issue table (`| Issue | ... | Status |`)
answers two separate questions per issue:

    SATISFIED (may stand as a blocker)   a row reads `done` AND the run has merged;
                                         see WHAT AN UNMERGED BRANCH MEANS
    HELD      (never offered)            a row reads `done`, `in-progress`, `gates`
                                         or `correction`
    RELEASED  (offered again)            `queued`, `blocked (criteria)`, or plain
                                         `blocked` — the run gave up without
                                         building it; not satisfied

Any other row status is a REFUSAL naming the status, the run and the issue. The
vocabulary is the run-issues skill's and it grows; a tool that guessed an unknown
status meant "available" would hand out an issue another session is building, and a
second writer on one issue is how a run rejects correct work. Issues a run holds are
listed under the table with the run id and the row status, so a missing issue explains
itself. A row naming an issue no file carries is also a refusal.

THE TWO BLOCKED STATUSES, AND WHY BOTH RELEASE. `blocked (criteria)` is a run that
never started an issue. Plain `blocked` is the SPENT ATTEMPT CAP: three implementers
tried, three gates rejected, and the issue left the run. The two differ in how much
was spent and in nothing this tool reads, because both end the same way — the run
built nothing into main, so a new batch may offer the issue again.

Measured on one tracker on 2026-09-17. One run wrote `blocked` for issue 08d, the
draft store and the first browser flow, after three attempts and three rejections.
Plain `blocked` was not in `LEDGER_KNOWN`, so this tool REFUSED THE WHOLE TRACKER over
one row: no batch at all, for 178 issue files, because one cell of one merged run's
ledger used a word from the same family. That is the fault this entry closes.

WHAT A RELEASE DOES NOT SAY, and where the reader gets it. A `blocked` row often
leaves a diff on a side branch — issue 08d's three attempts sit on that run's own
`...-08d-blocked` branch, which is merged nowhere. This tool does not
carry that, and it should not: the issue FILE's own `Status:` line carries the history,
the ruling and the branch name, and the harden pass and the run both read that file.
One source of truth. A second copy here would drift the first time somebody merged the
branch.

WHAT AN UNMERGED BRANCH MEANS, and the fault that paid for this. Until 2026-09-14
`LEDGER_SATISFIES = ("done",)` let an issue finished on an UNMERGED run branch stand
as a satisfied blocker. IT IS NOT ONE. A new run branches from main, so work that
exists only on another run's branch cannot be built behind.

Measured on one tracker on 2026-09-14, with one run live — 25 issues, 13 committed,
1 in gates, 11 queued. The tool offered five issues as free, and every
one of them was blocked by work that existed only on that branch:

    07b   needs 07   done in that run, NOT in main
    30    needs 07   same
    30b   needs 67, 08, and 30
    27    needs 70 (same) and 17 (still queued in that run)
    32    needs 17, 70 (same) and 07b

So the tool printed a confident table of a batch main could not build.

THE RULE NOW. A blocker is satisfied for a NEW batch only when the issue FILE says
`done` or `closed`, or when a MERGED run's ledger says `done`. A ledger `done` on an
unmerged run means "finished on that run's branch": it orders work INSIDE that run
and satisfies nothing outside it. Both readings are kept and neither is collapsed
into the other — see `satisfied_by`, `IN_MAIN` and `ON_A_BRANCH`.

The merged half of that rule is not decoration. A merge does not always rewrite the
issue file: issue 37 was `done` in the ledger of a run that merged to main on
2026-09-13, and its file still read `ready-for-agent` a day
later. Without the ledger half, everything behind 37 would have been reported as
blocked on a run that finished.

WHICH RUNS ARE LIVE. A ledger's `State:` line, read by `run_is_merged`: the state is
the FIRST word on the line once `*` and backticks are stripped, because
`State: merged - reached awaiting-merge 12:40, merged to main 12:49` carries the
word `merged` three times and a search for it anywhere answers the wrong question.
A LEDGER WITH NO `State:` LINE IS NOT MERGED. The live ledger measured on 2026-09-14
carried none, and a tool that read a missing line as merged would hand out exactly
the batch that could not be built.

THE QUEUED QUESTION, WHICH IS THE HUMAN'S. `LEDGER_RELEASES` offers a live run's own
queued issues to a new batch. On 2026-09-14 that meant eight of the thirteen offered
issues belonged to the live run's scope. Against that: an abandoned run must not lock
its queue for ever. NOTHING HERE DECIDES IT. `--queued` builds all three roads and
defaults to today's behaviour:

    released   today, and the default. The issue is offered.
    held       the run keeps it while the run is unmerged.
    fresh      held only while the ledger FILE is younger than
               `--queued-fresh-days`. The window is a GUESS nobody measured, kept on
               a flag so it is never buried.

A `queued` row on a MERGED run always releases, whatever the policy: that run will
never build it, and holding it would strand the issue for ever. The question is
queued for the human as `q-nb01-1`.

HARDENING THE BATCH IT OFFERS, and only that batch. A sweep over one tracker's 116
files names 28 unstamped issues and refuses 3 on size, and a reader looking for
today's batch would never find it in that. So the guidance is read on the OFFERED
issues:

    SIZE       `check_issue_size.py --issues <dir> --grade <each offered file>`,
               and its refusal is carried word for word. THE LIMIT IS NOT WRITTEN
               HERE. It is the human's ruling of 2026-09-14 and it lives in that
               script's `--limit` default with the distribution it was read off; a
               second copy of the number is a second copy that goes stale.
    THE MARKS  no `Hardened:` stamp, where a `Light:` line stands in for one on a
               `Level: light` issue only (issue 43); an open `## Questions`
               section. Either says
               the file is not specification-complete, so the issue moves off the
               `/run-issues` line and onto the `/harden-issues` line.
    A NOTE     no `## Blocked by` section. Named, and it moves nothing. This file
               reads a missing section as no blockers, measured on 2026-09-13:
               nine files on one tracker had none and all nine genuinely had none.

A `## Questions` section is read as DEFAULTED, and so not a mark, when its heading
or first paragraph says the questions are defaults. Measured on the three files of
one tracker that carry one: `## Questions, defaulted so the run never waits` is
defaulted; `## Questions open on this file` and `## Questions for the human` are open. The judgement
is coarse on purpose — it advises and never refuses, so a wrong call costs a line.

WHAT PARKED MEANS. Issue 03 of that same set, ruled by the human on 2026-09-13 on a
measurement of one tracker: 641 issues, 149 of them needs-harden, and not one of those
149 named as a blocker by any other issue. A needs-harden issue with fan-out zero sits
last for ever under the order above, so the backlog grows and nothing ever leaves it.
Promotion now mints a medium or low row that names no blocker as `Status: parked`
instead. A parked issue is NEVER offered by this tool: not as a member, not on either
`/harden-issues` line, and not as an ancestor pulled in ahead of a candidate. An issue
blocked by a parked one is therefore out of reach, and the refusal names the status.
`python3 ~/.claude/skills/lib/sweep_parked.py <issues dir>` is the one door back,
where this pack ships that script: it lists the parked issues past thirty days and the
ones some open issue now names, and the human hardens what they want back.

WHAT THE COUNT LINE SAYS. Under the table: `10 of 14 reachable, 4 not shown`, and
`12 parked, not offered` beneath it where the tracker holds any. The tool
never silently drops work.

WHY IT REFUSES. An order the human cannot trust is worse than none. It exits 1 and says
why
when the count exceeds what is reachable (naming what stands in the way), when a
blocker names an issue no file carries, when the graph has a cycle (printing it), or
when a file has no `Status:` or one it does not know. It never drops an issue to make
the batch fit. Before printing, the finished order is checked once more, independently
of how it was built, and a stranded issue is a refusal.

THEMES. `--theme <name>` keeps only candidates whose `Themes:` header line (comma
separated) carries the name; their unsatisfied blockers are pulled in ahead of them and
shown in the table. It refuses when no file carries `Themes:` at all, because there is
no theme data to filter on. No file carries one today; the door is left open only.

Exit codes: 0 batch printed (shapes 2 and 3); 1 refusal, or shape 1's "nothing can
start" — the reason is on stderr and the report is still on stdout, because a reader
who cannot start needs to know what the merge releases; 2 bad usage.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "run-issues"))
from check_issue_ready import headers, pending_defaults  # noqa: E402  Issue 33's one reader of `Level:`; issue 43b's rule 7.

SATISFIED = ("done", "closed")
CANDIDATES = ("ready-for-agent", "needs-harden")
# The fifth status. It is neither satisfied nor a candidate: a parked issue is
# open work this tool will not offer, and `sweep_parked.py` is the one door back.
PARKED = "parked"
# The sixth. A run writes it when an issue spends its strike cap and leaves the
# run, and the code sits unmerged on its own branch. Like `parked` it is open
# work that this tool will not offer, and unlike `parked` nobody set it aside:
# it is a run's own record of a stop. Added 2026-09-18 on the human's ruling, after
# issue 08d on 17 September and issue 139 on 18 September had each written the
# word and blinded four instruments with it.
#
# It is NOT excluded from `open_ids` the way `parked` is. A blocked issue is
# coming back, so what waits on it is waiting on real work, and `sweep_parked`
# reads that as a blocker rather than as backlog.
BLOCKED = "blocked"
KNOWN_STATUSES = SATISFIED + CANDIDATES + (PARKED, BLOCKED)

# Ledger row statuses, from the run-issues skill: `queued -> in-progress -> gates ->
# done`, plus `correction`, `blocked (criteria)` and plain `blocked`. Anything else is
# a refusal. The membership tests below are EXACT, so `blocked` and `blocked (criteria)`
# stay two entries and neither shadows the other; see THE TWO BLOCKED STATUSES above.
LEDGER_SATISFIES = ("done",)
LEDGER_HOLDS = ("done", "in-progress", "gates", "correction")
LEDGER_RELEASES = ("queued", "blocked (criteria)", "blocked")
LEDGER_KNOWN = LEDGER_HOLDS + LEDGER_RELEASES

# THE TWO READINGS OF A LEDGER `done`, separated on 2026-09-14. See the module
# docstring, WHAT AN UNMERGED BRANCH MEANS.
#
#   in main      the issue FILE says `done`/`closed`, OR a MERGED run's ledger
#                says `done`. This is the only reading a NEW batch may use,
#                because a new run branches from main.
#   on a branch  an UNMERGED run's ledger says `done`. The code exists, but it
#                exists on that run's branch. It orders work INSIDE that run and
#                satisfies nothing outside it.
IN_MAIN = "in-main"
ON_A_BRANCH = "on-a-branch"

# A run's `State:` line. The grammar is `run-issues/check_finale_stage.py`'s,
# which owns it: the line is written by hand and its decoration is not stable,
# so the ledgers carry `State: merged 2026-09-13 21:59, into main at ...`,
# `State: **awaiting-merge, reached 15:45.**` and plain `State: finale-board`.
# It is not always at the start of its line.
STATE_LINE = re.compile(r"State:\s*(.+)$", re.M)
# The state is the FIRST word on that line, once `*` and backticks are stripped.
# Anchoring matters: `State: merged - reached awaiting-merge 12:40, merged to
# main 12:49` carries the word `merged` three times and the word
# `awaiting-merge` once, and only the first word says where the run got to.
STATE_WORD = re.compile(r"^([a-z][a-z-]*)")
MERGED = "merged"

# What a `queued` row on an UNMERGED run does to a new batch. The human's question,
# not this tool's: see THE QUEUED QUESTION in the module docstring and the queue
# item `q-nb01-1`. `released` is today's behaviour and the default.
QUEUED_RELEASED = "released"
QUEUED_HELD = "held"
QUEUED_FRESH = "fresh"
QUEUED_POLICIES = (QUEUED_RELEASED, QUEUED_HELD, QUEUED_FRESH)
# The freshness window for `--queued fresh`, in days. NOBODY MEASURED THIS. It
# is a guess offered so the middle road can be driven, and it is a flag so the
# guess is never buried. The run ledger itself says staleness is the file's
# mtime and never a written clock.
QUEUED_FRESH_DAYS = 2.0

# The two tie-breaks among the candidates free at one step. Fan-out first is the
# ruling of 2026-09-13; `--by number` restores the old order so a reader can
# compare the two on one tracker.
FAN_OUT = "fan-out"
BY_NUMBER = "number"

# An issue number, the identifier `run-issues/check_origin.py` also reads: any run of
# digits with an optional letter suffix. `07`, `05b`, `641`, and the `149e` of an
# `Origin: 149e/batch-170a59` field.
ISSUE_ID = r"\d+[a-z]?"
# A leading ISO date is not an issue number. A `## Blocked by` bullet may open with a
# ruling date (`- 2026-09-13 ruling ...`), and a dated note may sit beside the issue
# files. The old two-digit cap rejected both by accident; `\d+` would read the first as
# issue 2026 and refuse "blocked by 2026, and no file carries that number", and would
# read the second as an issue file with no Status: line. So the guard is written against
# the date shape itself, at each place a leading number is read.
NOT_A_DATE = r"(?!\d{4}-\d{2}-\d{2})"
FILE_RE = re.compile(rf"^{NOT_A_DATE}({ISSUE_ID})-.*\.md$")
HEADER_RE = re.compile(r"^([A-Z][A-Za-z-]*):\s*(.*)$")
BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
BLOCKER_RE = re.compile(rf"^(?:\*\*)?`?{NOT_A_DATE}({ISSUE_ID})(?:[-`\s]|$)")

# A run ledger's Issue cell. Same grammar as a `## Blocked by` bullet: the
# first token is the issue number and anything after it is the title.
#
# **This read used `re.fullmatch(ISSUE_ID, ...)` until 2026-09-14, and that was
# a SILENT hold failure.** A ledger writing `| 70 — permit write narrowing is
# private |` matched nothing, so every row of that ledger was dropped and the
# run holding those issues held nothing. Measured that day on one tracker: one run
# was live, 25 issues, 13 committed; this tool offered fifteen of
# them as the NEXT batch, and the "Held by a run" block named one issue from a
# run that had already merged. Two of the four ledgers on that tracker write the
# title in the cell, so the guard was failing on half of them and had never
# said so.
#
# `NOT_A_DATE` is carried across for the same reason it exists above: a row
# opening `2026-09-13 ...` is a note, not issue 2026.
LEDGER_CELL = re.compile(rf"^(?:\*\*)?`?{NOT_A_DATE}({ISSUE_ID})(?:[-—`\s]|$)")
SECTION_RE = re.compile(r"^## Blocked by\b")

# THE THREE MARKS OF A FILE A RUN SHOULD NOT BE HANDED, read only on the issues
# this tool OFFERS. Nothing here refuses; each one names a file for
# `/harden-issues` BEFORE the run.
#
# The stamp. Every hardened file on one tracker opens with one, in two spellings:
# 80 files write `Hardened (provisional):` and 8 write `Hardened:`. The 28 files
# carrying neither are the un-hardened backlog, measured 2026-09-14.
HARDENED_RE = re.compile(r"^Hardened\b[^:\n]*:", re.M)
# Rule 5 of issue 32, built by issue 43: `/to-issues` writes this line in place of
# the stamp on a `Level: light` draft it does not send to `/harden-issues`. It
# counts as the stamp on that level only. Issue 42's lift rewrites a light issue
# to `Level: full` and leaves the line, and that issue needs hardening (default
# `q-h0925b-43-2`), so there the line is named and not counted.
LIGHT_RE = re.compile(r"^Light:", re.M)
# The questions section, in any of the three spellings this tracker writes:
# `## Questions open on this file`, `## Questions, defaulted so the run never
# waits`, `## Questions for the human, from the hardening pass of 2026-09-14`.
QUESTIONS_RE = re.compile(r"^## Questions\b.*$", re.M)
# A questions section is DEFAULTED, and so not a mark, when its heading or its
# first paragraph says the questions are defaults. That is the difference
# between "the run never waits" and "three must be ruled before this issue is
# stamped". Measured on the three files of one tracker that carry the section: 42 is
# defaulted by its heading, 02d and 66 are open. The judgement is COARSE and it
# advises rather than refuses, which is why a wrong call here costs a line of
# output and nothing else.
DEFAULTED_RE = re.compile(r"default", re.I)
# A mark opening with this is NAMED and does not move the issue off the
# `/run-issues` line. See `harden_marks`.
NOTE_ONLY = "note: "
HEADING_RE = re.compile(r"^## ")
TITLE_RE = re.compile(r"^# ")

# `Origin: <issue>/<run>` and `Rows: <row id> <audience>/<severity>; ...`, the two
# header fields promotion writes on a minted issue. The grammar is
# `run-issues/check_origin.py`'s, which owns it; only the halves this tool ranks by
# are read here. The refusals are deliberately left there and not copied: grading a
# malformed line belongs to the check promotion runs on the file it has just
# written, and a scheduler that refused on one could print no order at all for a
# tracker holding issues minted before those fields existed.
ORIGIN_RE = re.compile(rf"^({ISSUE_ID}|unknown)/", re.IGNORECASE)
ROWS_ENTRY_RE = re.compile(r"^\S+\s+[A-Za-z]+\s*/\s*([A-Za-z]+)$")

# Highest first, and an unranked word sits below `low` rather than refusing: the
# severity only breaks a tie inside one origin's rank.
SEVERITIES = ("critical", "high", "medium", "low")


class Refusal(Exception):
    """A reason the tool will not print an order."""


@dataclass
class Issue:
    id: str
    file: str
    status: str
    blockers: list
    themes: list = field(default_factory=list)
    origin: str = ""       # the issue half of `Origin:`, where it names a real one
    severity: str = ""     # the worst severity on the `Rows:` line
    marks: list = field(default_factory=list)   # see `harden_marks`
    # Why no tool here can place this file: a missing `Status:` line, or a word
    # the vocabulary above does not hold. Empty on every file that reads. See
    # `parse_issue` for why an unreadable file is loaded rather than refused.
    unreadable: str = ""


@dataclass
class Plan:
    """What one placement learned: the batch, how much was reachable, and the
    candidates that only a hardening pass can release."""
    order: list
    reachable: int
    waiting: list = field(default_factory=list)
    # `(issue id, [(blocker id, why it still stands)])` for every candidate the
    # placement could not reach. `waiting` is the subset a hardening pass alone
    # would release; this is all of them, with the reason per blocker.
    stuck: list = field(default_factory=list)


@dataclass
class Standing:
    """One blocker that still stands in a stuck candidate's way, and why."""
    blocker: str
    why: str
    run: str = ""     # the run holding it, where a run holds it; "" otherwise
    status: str = ""  # the LEDGER row status, where a run holds it; "" otherwise


@dataclass
class LedgerRow:
    issue: str
    run: str
    status: str
    # False until the ledger's `State:` line says the run reached `merged`. A row
    # on an unmerged run describes work on that run's BRANCH, and main does not
    # carry it. A ledger with no `State:` line at all is unmerged: the live
    # ledger measured on 2026-09-14 carried none, and a tool that
    # read a missing line as "merged" would hand out exactly the batch that could
    # not be built.
    merged: bool = False
    # The ledger FILE's mtime, epoch seconds. Read only by `--queued fresh`.
    # The run ledger states the rule itself: "staleness is THIS FILE'S mtime,
    # never a written clock".
    mtime: float = 0.0


def sort_key(issue_id: str):
    match = re.fullmatch(r"(\d+)([a-z]?)", issue_id)
    return (int(match.group(1)), match.group(2))


def parse_issue(path: Path) -> Issue:
    lines = path.read_text(encoding="utf-8").splitlines()
    issue_id = FILE_RE.match(path.name).group(1)
    status = None
    themes = []
    origin = severity = ""
    in_header = True
    for line in lines:
        if TITLE_RE.match(line):
            in_header = False
        header = HEADER_RE.match(line)
        if not header:
            if line.startswith("## "):
                break
            continue
        key, value = header.groups()
        if key == "Status" and status is None:
            status = value.split()[0] if value.split() else ""
        elif key == "Themes":
            themes = [t.strip() for t in value.split(",") if t.strip()]
        elif key == "Origin" and in_header and not origin:
            origin = origin_issue(value)
        elif key == "Rows" and in_header and not severity:
            severity = worst_severity(value)
    # ONE FILE'S FAULT COSTS THAT FILE, NOT THE TRACKER. The human's ruling of
    # 2026-09-18: a status word nobody's tools knew refused two whole trackers
    # in four instruments on one day, and 42 parked issues on one of them went
    # unchecked behind it. So the file is loaded, carrying the reason it could
    # not be placed, and every caller names it.
    #
    # Nothing is loosened by that. The word is kept exactly as it was read, so
    # it is in neither `SATISFIED` nor `CANDIDATES`: the issue can never be
    # offered as work, and anything naming it as a blocker stays unreachable
    # until a human repairs the file.
    reason = ""
    if status is None:
        status, reason = "", "no Status: line in the header"
    elif status not in KNOWN_STATUSES:
        reason = (f"Status: {status!r} is not one this tool knows "
                  f"({', '.join(KNOWN_STATUSES)})")
    return Issue(issue_id, path.name, status, blockers_of(lines), themes,
                 origin, severity, harden_marks("\n".join(lines), path), reason)


def harden_marks(text: str, path: Path | None = None) -> list:
    """What says this file is not ready to be handed to an implementer.

    Four marks, all of them advice and none of them a refusal, and all of them
    read ONLY on the issues this tool offers. A tracker's backlog carries these
    by the dozen and naming them all would bury the batch. The fourth is issue
    43b's rule 7, read through `check_issue_ready.pending_defaults`, the function
    the criteria gate refuses on, so the `/run-issues` line never names an issue
    that gate refuses. It needs the file's path to find the rulings file.
    """
    marks = []
    if path is not None:
        faults, binds = pending_defaults(path, text)
        if binds:
            marks += [f"rule 7: {fault}" for fault in faults]
    if not HARDENED_RE.search(text):
        if not LIGHT_RE.search(text):
            marks.append("no Hardened: stamp")
        else:
            level = headers(text).level
            if level != "light":
                marks.append("no Hardened: stamp, and its Light: line counts only on "
                             f"Level: light, not Level: {level or 'missing'}")
    found = QUESTIONS_RE.search(text)
    if found:
        heading = found.group(0)
        rest = text[found.end():].lstrip("\n")
        first = rest.split("\n\n", 1)[0]
        if not DEFAULTED_RE.search(heading + "\n" + first):
            marks.append("an open " + heading.strip())
    if not any(SECTION_RE.match(line) for line in text.splitlines()):
        # A NOTE, NOT A BLOCKING MARK, and the difference decides whether the
        # issue keeps its place on the `/run-issues` line. This file's own
        # reading of a missing section is "no blockers", measured on 2026-09-13:
        # nine files on one tracker had no section and all nine genuinely had none.
        # So it is worth saying that nobody wrote the edges down, and it is not
        # worth pulling a stamped, sized, ready issue out of a batch for.
        marks.append(NOTE_ONLY + "no ## Blocked by section (nobody recorded "
                     "whether it has any; it keeps its place in the batch)")
    return marks


def blocking_marks(marks) -> list:
    """The marks that say the file is not specification-complete."""
    return [m for m in marks if not m.startswith(NOTE_ONLY)]


def origin_issue(value: str) -> str:
    """The issue half of an `Origin:` line, or "" where it names no single issue.

    `unknown` is legal in that grammar and is exactly the case with no issue to
    rank by, so it reads the same here as a line nobody wrote.
    """
    text = value.replace("*", "").strip().strip("`").strip().lower()
    found = ORIGIN_RE.match(text)
    if not found or found.group(1).lower() == "unknown":
        return ""
    return found.group(1)


def worst_severity(value: str) -> str:
    """The worst severity on a `Rows:` line, or "" where it is not that grammar."""
    worst = ""
    for part in value.replace("*", "").replace("`", "").split(";"):
        found = ROWS_ENTRY_RE.match(part.strip())
        if not found:
            continue
        word = found.group(1).lower()
        if word in SEVERITIES and (not worst
                                   or SEVERITIES.index(word) < SEVERITIES.index(worst)):
            worst = word
    return worst


def severity_rank(issue: Issue) -> int:
    """Higher sorts first. An unranked or absent severity sits below `low`."""
    if issue.severity in SEVERITIES:
        return len(SEVERITIES) - SEVERITIES.index(issue.severity)
    return 0


def blockers_of(lines) -> list:
    blockers = []
    inside = False
    for line in lines:
        if SECTION_RE.match(line):
            inside = True
            continue
        if inside and HEADING_RE.match(line):
            break
        if not inside:
            continue
        bullet = BULLET_RE.match(line)
        if not bullet:
            continue
        found = BLOCKER_RE.match(bullet.group(1))
        if found and found.group(1) not in blockers:
            blockers.append(found.group(1))
    return blockers


def load_issues(issues_dir: Path) -> dict:
    paths = sorted(p for p in issues_dir.iterdir() if FILE_RE.match(p.name))
    if not paths:
        raise Refusal(f"{issues_dir}: no issue files (NN-slug.md) found")
    issues = {}
    for path in paths:
        issue = parse_issue(path)
        if issue.id in issues:
            raise Refusal(f"{path.name} and {issues[issue.id].file} share number {issue.id}")
        issues[issue.id] = issue
    for issue in issues.values():
        for blocker in issue.blockers:
            if blocker not in issues:
                raise Refusal(
                    f"{issue.file}: blocked by {blocker}, and no file carries that number")
    return issues


def unreadable(issues: dict) -> list:
    """`(file, reason)` for every issue file no tool here can place, in tracker
    order. Empty on a tracker that reads.

    Every command that loads a tracker prints this. A file nobody names is a
    file nobody repairs, and the whole point of loading it rather than refusing
    on it is that the reader is told which one it is.
    """
    return [(i.file, i.unreadable)
            for i in sorted(issues.values(), key=lambda i: sort_key(i.id))
            if i.unreadable]


def unreadable_note(issues: dict) -> str:
    """The lines naming every unreadable file, or "" when they all read."""
    found = unreadable(issues)
    if not found:
        return ""
    head = (f"{len(found)} issue file(s) could not be placed and are NOT in the "
            "reading below. Repair the header of each:")
    return "\n".join([head] + [f"  {file}: {reason}" for file, reason in found])


def runs_dir_for(issues_dir: Path) -> Path:
    """`runs/` sits beside the issues directory under the feature directory."""
    return issues_dir.resolve().parent / "runs"


def run_is_merged(text: str) -> bool:
    """True when a ledger's `State:` line says the run reached `merged`.

    The state is the FIRST word on the line once `*` and backticks are stripped.
    Anchoring is the whole point: `State: merged - reached awaiting-merge
    2026-09-13 12:40, merged to main 12:49` carries `merged` three times and
    `awaiting-merge` once, and a search for either word anywhere on the line
    answers the wrong question. A ledger with no `State:` line is NOT merged, and
    that is the case this tool was fixed for.
    """
    for found in STATE_LINE.finditer(text):
        line = found.group(1).replace("*", "").replace("`", "").strip().lower()
        word = STATE_WORD.match(line)
        if word and word.group(1) == MERGED:
            return True
    return False


def load_ledgers(runs_dir: Path, issues: dict) -> list:
    """Read every `<runs_dir>/<batch>/run.md` issue table. Missing dir: no rows."""
    rows = []
    if not runs_dir.is_dir():
        return rows
    for ledger in sorted(runs_dir.glob("*/run.md")):
        run_id = ledger.parent.name
        text = ledger.read_text(encoding="utf-8")
        merged = run_is_merged(text)
        mtime = ledger.stat().st_mtime
        for issue_id, status in ledger_rows(text):
            if issue_id not in issues:
                raise Refusal(
                    f"run {run_id}: ledger row for issue {issue_id}, and no file carries "
                    "that number")
            if status not in LEDGER_KNOWN:
                raise Refusal(
                    f"run {run_id}: issue {issue_id} has ledger status {status!r}, which "
                    f"this tool does not know ({', '.join(LEDGER_KNOWN)}); it will not "
                    "guess whether the run holds the issue")
            rows.append(LedgerRow(issue_id, run_id, status, merged, mtime))
    return rows


def live_runs(rows) -> list:
    """The batch ids of the runs that have NOT merged, lowest id first.

    These are the runs whose branches main does not carry. A new batch that
    depends on one of them cannot be built today, however green that run's
    ledger looks.
    """
    return sorted({r.run for r in rows if not r.merged})


def ledger_rows(text: str):
    """Yield (issue id, status) from every table whose header has Issue and Status.

    THE STATUS COMES BACK WITHOUT ITS EMPHASIS. `*` and backticks are stripped the
    way `run_is_merged` strips them from a `State:` line, and nothing else is: the
    word under them still meets `LEDGER_KNOWN` by exact membership, so an unknown
    status refuses as it always did. One run wrote `**blocked**` for issues 151,
    152 and 53, and on 2026-09-23 this tool refused the whole tracker
    over the asterisks. A holding status is stripped the same way, so a formatted
    `in-progress` still hides the issue rather than refusing or releasing it.
    """
    issue_col = status_col = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            issue_col = status_col = None
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if issue_col is None:
            if "Issue" in cells and "Status" in cells:
                issue_col, status_col = cells.index("Issue"), cells.index("Status")
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) <= max(issue_col, status_col):
            continue
        found = LEDGER_CELL.match(cells[issue_col])
        if found:
            yield found.group(1), cells[status_col].replace("*", "").replace("`", "").strip()


@dataclass(frozen=True)
class QueuedPolicy:
    """What a `queued` row on an UNMERGED run does to a new batch."""
    mode: str = QUEUED_RELEASED
    fresh_days: float = QUEUED_FRESH_DAYS


def as_policy(queued) -> QueuedPolicy:
    """Every `queued=` parameter in this file takes the mode name or the policy."""
    return queued if isinstance(queued, QueuedPolicy) else QueuedPolicy(queued)


def held_by(rows: list, queued=QUEUED_RELEASED, now=None) -> dict:
    """issue id -> the LedgerRow that keeps it out of a new batch.

    `queued` decides what a `queued` row on an UNMERGED run does, and it is
    THE HUMAN'S QUESTION, not this tool's: see THE QUEUED QUESTION in the module
    docstring. `released` is today's behaviour and the default. A `queued` row
    on a MERGED run always releases, because that run will never build it.
    """
    policy = as_policy(queued)
    held = {r.issue: r for r in rows if r.status in LEDGER_HOLDS}
    if policy.mode == QUEUED_RELEASED:
        return held
    if now is None:
        now = time.time()
    window = policy.fresh_days * 86400
    for row in rows:
        if row.status != "queued" or row.merged or row.issue in held:
            continue
        if policy.mode == QUEUED_HELD or now - row.mtime <= window:
            held[row.issue] = row
    return held


def satisfied_by(rows: list, reading=IN_MAIN) -> dict:
    """issue id -> the LedgerRow whose `done` lets it stand as a blocker.

    **THE READING IS THE WHOLE FIX OF 2026-09-14.** `IN_MAIN` counts only a
    MERGED run's `done`, which is the only reading a NEW batch may use.
    `ON_A_BRANCH` counts every `done`, which is what orders work INSIDE a run
    and what says which batch a merge would release.
    """
    return {r.issue: r for r in rows
            if r.status in LEDGER_SATISFIES
            and (reading == ON_A_BRANCH or r.merged)}


def done_on_a_branch(rows: list) -> dict:
    """issue id -> the LedgerRow saying it is done on an UNMERGED run's branch.

    This is exactly the set that satisfies `ON_A_BRANCH` and not `IN_MAIN`: the
    work that must merge before anything behind it can be built.
    """
    return {r.issue: r for r in rows
            if r.status in LEDGER_SATISFIES and not r.merged}


def satisfied_ids(issues: dict, rows=(), reading=IN_MAIN) -> set:
    """Every issue a new batch may treat as already built, under `reading`.

    The issue FILE is the first source and it needs no ledger: `done` or
    `closed` in the header is in main by definition. A MERGED run's `done` row
    is the second, and it is needed because a merge does not always rewrite the
    file. Measured on one tracker on 2026-09-14: issue 37 was `done` in the
    ledger of a run that merged to main on 2026-09-13, and its file still read
    `ready-for-agent`.
    """
    satisfied = {i.id for i in issues.values() if i.status in SATISFIED}
    return satisfied | set(satisfied_by(rows, reading))


def open_ids(issues: dict, rows=(), queued=QUEUED_RELEASED) -> set:
    """The issues that still have to be built: neither `done`/`closed` in the file
    nor held by a run ledger nor parked. Fan-out counts these and nothing else.

    Parked is out because fan-out is leverage, and an issue this tool will not
    offer carries none. A sweep that brings a parked issue back to
    `needs-harden` puts its weight behind its blockers again, on the next run of
    this tool."""
    held = held_by(rows, queued)
    return {i.id for i in issues.values()
            if i.status not in SATISFIED and i.status != PARKED
            and i.id not in held}


def fan_out(issues: dict, rows=(), queued=QUEUED_RELEASED) -> dict:
    """issue id -> how many OPEN issues sit downstream of it through `## Blocked by`.

    An edge runs blocker -> blocked: `05` blocked by `37` puts 05 downstream of 37.
    Counted transitively and as a set, so a diamond (A blocks B and C, both block D)
    gives A three and not four. The subject may be any issue, open or not: a `done`
    issue's fan-out is what its code carries, which is the rank criterion 4 of the
    ruling asks a minted issue to inherit.

    Breadth-first from each node rather than a memo over a topological order,
    because `find_cycle` has not necessarily run yet and a cycle must not hang the
    walk.
    """
    downstream = {i: [] for i in issues}
    for issue in issues.values():
        for blocker in issue.blockers:
            if blocker in downstream:
                downstream[blocker].append(issue.id)
    still_open = open_ids(issues, rows, queued)
    counts = {}
    for start in issues:
        seen, todo = set(), list(downstream[start])
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(downstream[node])
        seen.discard(start)
        counts[start] = len(seen & still_open)
    return counts


SIZE_CHECK = Path(__file__).resolve().parent / "check_issue_size.py"


def size_check(issues_dir: Path, files, script=SIZE_CHECK, timeout=120):
    """Grade the OFFERED issues with `check_issue_size.py` and carry its verdict.

    **The limit is NOT written here.** It is the human's ruling of 2026-09-14 and it
    lives in that script's `--limit` default, with the distribution it was read
    off. A second copy of the number in this file is a second copy that goes
    stale, so no `--limit` is passed and the script's own refusal is carried
    word for word.

    `--grade` is what makes this a stamp rather than a tracker sweep: every file
    under `--issues` is still read and counted, and only the files this tool is
    about to offer are graded. A backlog minted before the rule is not this
    tool's to refuse.

    Returns `(ok, refusals, notes)`, the shape every caller unpacks. `ok` is
    False only when the script REFUSED (exit 1): a missing script, a crash or a
    timeout is a note saying nothing was measured, because a check that did not
    run may never be reported as a pass.

    A MISSING SCRIPT IS THE ORDINARY CASE HERE, not an accident. This pack may
    ship without `check_issue_size.py`, and then the batch is printed with a note
    saying it was not sized. Nothing else changes.
    """
    if not files:
        return True, [], []
    if not Path(script).is_file():
        return True, [], [f"note: {script} was not found, so no issue was graded "
                          "for size. Nothing here says the batch is the right "
                          "size."]
    cmd = [sys.executable, str(script), "--issues", str(issues_dir)]
    for path in files:
        cmd += ["--grade", os.path.abspath(str(path))]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as problem:
        return True, [], [f"note: {Path(script).name} could not be run "
                          f"({problem}), so no issue was graded for size. Nothing "
                          "here says the batch is the right size."]
    if done.returncode == 0:
        return True, [], []
    body = (done.stderr or done.stdout).splitlines()
    refusals, rest = split_size_refusal(body, issues_dir, files)
    if done.returncode == 1:
        return False, refusals, rest
    # Exit 2 is that script's "nothing could be read, so nothing is asserted".
    return True, [], [f"note: {Path(script).name} measured nothing (exit "
                      f"{done.returncode})"] + [line.strip() for line in body]


# The trailing clause that introduces the per-criterion evidence, which this
# tool drops. `check_issue_size.py --grade <file>` prints it in full, and that
# command is named wherever this block is rendered.
COUNTED_TAIL = re.compile(r"\s*The \d+ counted:\s*$")


def split_size_refusal(body, issues_dir, files):
    """`([(file, one sentence)], [line])` off `check_issue_size.py`'s output.

    That script refuses BY ABSOLUTE PATH and repeats its sentence once per
    file, so a batch of twenty printed fourteen copies of one paragraph with a
    long path in front of each. The human asked for issue numbers and less text on
    2026-09-15. The sentence is still the script's own words, printed once for
    every file that shares it; the per-criterion evidence is dropped, because
    cutting an issue is the harden pass's job and that pass runs the script
    itself.

    **Nothing is dropped silently.** A line this reader does not recognise
    comes back in the second list and is printed as it stands.
    """
    wanted = {os.path.abspath(str(f)) for f in files}
    refusals, rest = [], []
    for line in body:
        if line != line.lstrip():
            continue                      # indented: the per-criterion evidence
        stripped = line.strip()
        if not stripped or stripped.startswith("Refused:"):
            continue                      # the summary, recomputed by the caller
        head, sep, tail = stripped.partition(": ")
        if sep and os.path.abspath(head) in wanted:
            refusals.append((head, COUNTED_TAIL.sub("", tail).strip()))
        else:
            rest.append(stripped)
    return refusals, rest


def by_reason(pairs, key_of):
    """`[(shared value, [key, ...])]`, first appearance first.

    One line per reason instead of one line per issue. It is used for the size
    refusals and for the harden marks, both of which say the same sentence
    about a dozen issues at a time.
    """
    grouped = {}
    for key, value in pairs:
        grouped.setdefault(value, []).append(key)
    return [(value, [key_of(k) for k in keys]) for value, keys in grouped.items()]


def id_of(path, order: list, issues: dict, issues_dir=None) -> str:
    """The issue number for a file `check_issue_size.py` named, or the path.

    The match is on the ABSOLUTE path that script prints, never on the bare
    file name: `23-the-home.md` is a substring of `123-the-home.md`, and on a
    tracker carrying issue numbers above 99 the bare name would name the wrong
    issue. One tracker in use carries 641.
    """
    target = os.path.abspath(str(path))
    for i in order:
        name = (os.path.abspath(os.path.join(str(issues_dir), issues[i].file))
                if issues_dir is not None else issues[i].file)
        if name == target:
            return i
    return str(path)


def find_cycle(issues: dict):
    """Return one cycle as a list of ids (first repeated at the end), or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {i: WHITE for i in issues}
    stack = []

    def visit(node):
        colour[node] = GREY
        stack.append(node)
        for nxt in issues[node].blockers:
            if colour[nxt] == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if colour[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    for start in sorted(issues, key=sort_key):
        if colour[start] == WHITE:
            found = visit(start)
            if found:
                return found
    return None


def schedule(issues: dict, count: int, theme=None, rows=(), by=FAN_OUT,
             counts=None, reading=IN_MAIN, refuse_short=True,
             queued=QUEUED_RELEASED) -> Plan:
    """Return the Plan: the batch in order, how much was reachable, and what only a
    hardening pass can release. Raise Refusal when the count cannot be honoured.
    `by` picks the tie-break among the candidates free at each step: fan-out
    descending then number ascending, or number alone.

    `reading` picks which `done` counts as a satisfied blocker. It DEFAULTS to
    `IN_MAIN`, which is what a NEW batch must use; `ON_A_BRANCH` says which batch
    a merge would release, and a caller has to ask for it by name. The dangerous
    reading is the one you have to type, because a caller that forgets the
    argument must not get the batch main cannot build. See `satisfied_by`.

    `refuse_short=False` returns whatever the placement reached instead of
    refusing, down to an empty order. The caller that turns it off is the one
    that has something better to print than a refusal: a live run is standing in
    the way, and naming the run beats naming the arithmetic.
    """
    cycle = find_cycle(issues)
    if cycle:
        raise Refusal("the dependency graph has a cycle: " + " -> ".join(cycle))

    if theme is not None:
        if not any(i.themes for i in issues.values()):
            raise Refusal(
                "--theme asked for, but no issue file carries a Themes: header line; "
                "there is no theme data to filter on")
        wanted = {i.id for i in issues.values()
                  if i.status in CANDIDATES and theme in i.themes}
        if not wanted:
            raise Refusal(f"no candidate issue carries theme {theme!r}")
    else:
        wanted = {i.id for i in issues.values() if i.status in CANDIDATES}

    if counts is None:
        counts = fan_out(issues, rows, queued)
    pick_key = (sort_key if by == BY_NUMBER
                else lambda i: (-counts[i], sort_key(i)))

    held = held_by(rows, queued)
    wanted -= set(held)
    satisfied = satisfied_ids(issues, rows, reading)
    placed = []
    placed_ready = set()

    def is_free(issue):
        return all(b in satisfied or b in placed_ready for b in issue.blockers)

    def needed_for(ids):
        """The candidates in `ids` plus every unsatisfied ancestor."""
        needed, todo = set(), list(ids)
        while todo:
            node = todo.pop()
            if node in needed or node in satisfied:
                continue
            needed.add(node)
            todo.extend(issues[node].blockers)
        return needed

    # A held issue can be a wanted issue's unsatisfied ancestor (a run is building
    # it now). It is never a member, and nothing can be placed behind it. A parked
    # ancestor is out for the same reason and a stronger one: it is not offered at
    # all, so an issue behind it is out of reach until a sweep releases it, and the
    # refusal below names the status.
    #
    # `blocked` and an unreadable file join parked there, added 2026-09-18. A run
    # left the blocked one behind after its strike cap, and nobody can place the
    # unreadable one at all; placing an issue behind either would offer work whose
    # ancestor no batch can build.
    withheld = {i.id for i in issues.values()
                if i.status in (PARKED, BLOCKED) or i.unreadable}
    pool = needed_for(wanted) - set(held) - withheld
    # Place until nothing is free. The greedy pick is deterministic, so the
    # count-limited batch is a prefix of this full placement.
    while True:
        free = [issues[i] for i in sorted(pool - set(placed), key=pick_key)
                if is_free(issues[i])]
        if not free:
            break
        pick = free[0]
        placed.append(pick.id)
        if pick.status == "ready-for-agent":
            placed_ready.add(pick.id)

    reached = [p for p in placed if p in wanted]
    stuck = sorted(pool - set(placed), key=sort_key)
    if len(reached) < count and refuse_short:
        lines = [f"asked for {count}, only {len(reached)} reachable"]
        if not stuck:
            lines.append("  every candidate (ready-for-agent or needs-harden) is already in the batch")
        for sid in stuck:
            lines.append(f"  {sid} waits on " + ", ".join(
                f"{s.blocker} ({s.why})" for s in
                standing_blockers(sid, issues, satisfied, placed_ready, rows, held)))
        raise Refusal("\n".join(lines))

    cut = placed.index(reached[count - 1]) + 1 if len(reached) >= count else len(placed)
    batch = placed[:cut]
    verify_order(batch, issues, satisfied)
    return Plan(batch, len(reached),
                waiting_on_harden(stuck, issues, satisfied, placed_ready, held),
                [(sid, standing_blockers(sid, issues, satisfied, placed_ready,
                                         rows, held)) for sid in stuck])


def standing_blockers(issue_id, issues: dict, satisfied, placed_ready, rows=(),
                      held=None):
    """`Standing` per blocker of one candidate the placement missed.

    The reason is the whole value of this function, because the four reasons ask
    for four different actions. An issue done on an UNMERGED branch waits on a
    merge; a held issue waits on the run finishing; a `needs-harden` blocker
    waits on `/harden-issues`; anything else waits on an earlier batch.
    """
    if held is None:
        held = held_by(rows)
    on_branch = done_on_a_branch(rows)
    standing = []
    for b in issues[issue_id].blockers:
        if b in satisfied or b in placed_ready:
            continue
        if b in on_branch:
            standing.append(Standing(
                b, f"done on the branch of run {on_branch[b].run}, not in main",
                on_branch[b].run, on_branch[b].status))
        elif b in held:
            standing.append(Standing(
                b, f"{held[b].status} in run {held[b].run}", held[b].run,
                held[b].status))
        else:
            standing.append(Standing(b, standing_status(issues[b])))
    return standing


def standing_status(issue) -> str:
    """How one blocker's state reads in a refusal line.

    An unreadable file has no status worth printing on its own -- it may have
    no `Status:` line at all -- so the line says that rather than printing an
    empty cell a reader would have to go and look up.
    """
    if issue.unreadable:
        return f"{issue.status or 'no status'}, which no tool here can place"
    return issue.status


def waiting_on_a_run(plan: "Plan") -> dict:
    """run id -> `[(issue id, standing)]` for every stuck candidate a run holds up.

    A candidate is filed under the FIRST unmerged run standing in its way, so it
    is named once. Its full standing list travels with it, so a second condition
    — a harden, an earlier batch — is never hidden by the heading.
    """
    groups = {}
    for issue_id, standing in plan.stuck:
        run = next((s.run for s in standing if s.run), None)
        if run:
            groups.setdefault(run, []).append((issue_id, standing))
    return groups


def waiting_on_harden(stuck, issues: dict, satisfied, placed_ready, held=()) -> list:
    """`(issue id, the needs-harden issues it waits on)` for every stuck candidate
    that a hardening pass would release, in order.

    An issue is listed only when EVERY blocker still standing in its way is
    `needs-harden`. One that also waits on a run, or on a ready issue the placement
    could not reach, is left out: the line is a promise that hardening these frees
    that issue, and a promise with a second condition hidden in it is worse than
    no line.
    """
    waiting = []
    for issue_id in stuck:
        standing = [b for b in issues[issue_id].blockers
                    if b not in satisfied and b not in placed_ready]
        if standing and all(issues[b].status == "needs-harden" and b not in held
                           for b in standing):
            waiting.append((issue_id, standing))
    return waiting


def verify_order(order: list, issues: dict, satisfied=frozenset()) -> None:
    """Independent check: every blocker of every member is satisfied before it.
    `satisfied` carries the ids the ledgers mark `done`; file status is read here."""
    seen_ready = set()
    for issue_id in order:
        issue = issues[issue_id]
        for blocker in issue.blockers:
            other = issues.get(blocker)
            if other is None:
                raise Refusal(f"{issue.file}: blocked by {blocker}, which no file carries")
            if other.status in SATISFIED or blocker in satisfied or blocker in seen_ready:
                continue
            raise Refusal(
                f"{issue.file}: blocked by {blocker} ({other.status}), which the order "
                "does not satisfy before it")
        if issue.status == "ready-for-agent":
            seen_ready.add(issue_id)


def harden_before_the_run(plan: Plan, issues: dict, counts: dict, held=()) -> list:
    """The issues to harden BEFORE the next run, highest leverage first. Two kinds.

    FIRST, every issue that stands between the placement and work it wanted: the
    `needs-harden` blockers of the issues `waiting_on_harden` found, ordered by their
    own fan-out and then by number.

    SECOND, every minted issue whose `Origin:` issue has a fan-out above zero. An
    issue carrying `Origin: 05/batch-<id4>` changes what issue 05 built, and
    everything downstream of 05 calls that code, so it inherits 05's fan-out as its
    rank; severity from its `Rows:` line breaks the tie inside one rank, and the
    number breaks that. A minted issue whose origin has fan-out zero is left out.
    This answers "which of the run's new issues do I harden before the next run"
    without anyone reading the briefing. The human read it by hand for one run on
    2026-09-13, and the answer was the five issues minted from 05, 05b and 05d.

    A run-held issue is never offered, in either kind.
    """
    blockers = {b for _, standing in plan.waiting for b in standing}
    first = sorted(blockers, key=lambda i: (-counts[i], sort_key(i)))
    minted = [i for i in issues.values()
              if i.status == "needs-harden" and i.id not in held
              and i.id not in blockers and counts.get(i.origin, 0) > 0]
    second = sorted(minted, key=lambda i: (-counts[i.origin], -severity_rank(i),
                                           sort_key(i.id)))
    return first + [i.id for i in second]


def render_table(order: list, issues: dict, counts: dict, ledger_rows=()) -> list:
    """The batch table. `Waited on` names the run for a blocker a ledger closed,
    and says out loud when that run has not merged."""
    on_branch = done_on_a_branch(ledger_rows)
    merged_done = satisfied_by(ledger_rows, IN_MAIN)
    rows = []
    for issue_id in order:
        issue = issues[issue_id]
        waited = []
        for b in issue.blockers:
            other = issues[b]
            if other.status in SATISFIED:
                waited.append(f"{b} ({other.status})")
            elif b in on_branch:
                waited.append(f"{b} (on branch {on_branch[b].run})")
            elif b in merged_done:
                waited.append(f"{b} (done, {merged_done[b].run})")
            else:
                waited.append(b)
        rows.append((issue_id, issue.status, str(counts[issue_id]),
                     ", ".join(waited) or "-"))
    width_id = max(len("Issue"), *(len(r[0]) for r in rows))
    width_st = max(len("Status"), *(len(r[1]) for r in rows))
    width_fo = max(len("Fan-out"), *(len(r[2]) for r in rows))
    out = [f"{'Issue':<{width_id}}  {'Status':<{width_st}}  "
           f"{'Fan-out':<{width_fo}}  Waited on"]
    out += [f"{r[0]:<{width_id}}  {r[1]:<{width_st}}  {r[2]:<{width_fo}}  {r[3]}"
            for r in rows]
    return out


def id_width(order: list) -> int:
    return max([len("Issue")] + [len(i) for i in order])


def render_parked(issues: dict) -> list:
    """Printed only where a tracker holds a parked issue. A `0 parked` line on
    every tracker is noise, and the count exists to tell a reader that work
    they cannot see was deliberately left out."""
    parked = [i for i in issues.values() if i.status == PARKED]
    return [f"{len(parked)} parked, not offered"] if parked else []


def render_held(issues: dict, ledger_rows, width: int, queued=QUEUED_RELEASED) -> list:
    """The issues a run owns, one line per run and row status.

    Fifteen issues held by one run printed fifteen copies of
    `done in run batch-<id5> (NOT merged)`. The human asked for less text on
    2026-09-15, and the run and its state are the only things that vary.
    """
    held = [r for r in held_by(ledger_rows, queued).values()
            if issues[r.issue].status in CANDIDATES]
    if not held:
        return []
    groups = {}
    for r in held:
        state = "merged" if r.merged else "NOT merged"
        groups.setdefault((r.run, state, r.status), []).append(r.issue)
    out = ["", "Held by a run (the issue file still reads as a candidate):"]
    for (run, state, status) in sorted(groups):
        ids = " ".join(sorted(groups[(run, state, status)], key=sort_key))
        out.append(f"  {run}  {state}  {status}: {ids}")
    return out


def render_waiting_harden(plan: Plan, width: int) -> list:
    if not plan.waiting:
        return []
    out = ["", "Waiting on a harden (not offered, and not counted as reachable):"]
    for issue_id, standing in plan.waiting:
        out.append(f"  {issue_id:<{width}}  waits on harden of "
                   + ", ".join(standing))
    return out


def render_waiting_runs(plan: Plan, width: int) -> list:
    """Every stuck candidate, grouped under the run standing in its way.

    This is the half of the answer the tool could not express before
    2026-09-14. A reader asking "what can I start today" needs it as much as
    the batch: these are the issues a merge releases, and nothing they do today
    moves them.

    THE HEADING CARRIES THE LEGEND AND THE ROWS CARRY NUMBERS. Every blocker
    used to repeat `(done on the branch of run batch-<id5>, not in main)`,
    which is the same 52 characters on every line under a heading that already
    names the run. The human asked for it on 2026-09-15. A blocker the run has NOT
    finished keeps its bracket, because that one is not released by the merge
    alone.
    """
    groups = waiting_on_a_run(plan)
    if not groups:
        return []
    out = []
    for run in sorted(groups):
        out.append("")
        out.append(f"Waiting on run {run} to merge (not offered). Each number "
                   "below is done on that branch")
        out.append("and not in main, unless a bracket says otherwise. "
                   "(+N) counts blockers this batch has not placed.")
        for issue_id, standing in sorted(groups[run],
                                         key=lambda pair: sort_key(pair[0])):
            mine = [s for s in standing if s.run == run]
            others = len(standing) - len(mine)
            named = " ".join(
                s.blocker if s.status in LEDGER_SATISFIES
                else f"{s.blocker} ({s.status})" for s in mine)
            out.append(f"  {issue_id:<{width}}  {named}"
                       + (f"  (+{others})" if others else ""))
    return out


def harden_first(order: list, issues: dict, issues_dir: Path):
    """The offered issues that must be hardened BEFORE the run, and why each.

    Two kinds, both read on the batch and never on the tracker. A tracker sweep
    over one tracker's 116 files names 28 unstamped issues and refuses 3 on size,
    and a reader looking for today's batch would never find it in that.

        SIZE       `check_issue_size.py --grade`. THE LIMIT IS NOT WRITTEN
                   HERE. It is the human's ruling of 2026-09-14 and it lives in
                   that script's `--limit` default with the distribution it was
                   read off; a second copy of the number goes stale.
        THE MARKS  `harden_marks`: no `Hardened:` stamp, an open `## Questions`
                   section, and a note for a missing `## Blocked by` section.

    ONE LINE PER REASON, not one line per issue, and issue numbers rather than
    paths. The human asked for both on 2026-09-15: a batch of twenty printed
    fourteen copies of one paragraph, each behind an absolute path.

    Returns `(ids, lines)`.
    """
    if issues_dir is None or not order:
        return [], []
    ok, refusals, rest = size_check(issues_dir, [issues_dir / issues[i].file
                                                 for i in order])
    marked = [(i, m) for i in order for m in issues[i].marks]
    if ok and not refusals and not rest and not marked:
        return [], []
    lines = ["", "BEFORE the run, harden these offered issues:"]
    if refusals:
        lines.append(f"  {SIZE_CHECK.name} refuses {len({f for f, _ in refusals})} "
                     f"of the {len(order)} offered:")
        for sentence, ids in by_reason(
                refusals, lambda f: id_of(f, order, issues, issues_dir)):
            lines.append(f"    {' '.join(ids)} — {sentence}")
        lines.append(f"    For the criterion-by-criterion list, run "
                     f"{SIZE_CHECK.name} --grade <file>.")
    lines += [f"  {line}" for line in rest]
    for mark, ids in by_reason(marked, lambda i: i):
        lines.append(f"  {mark}: {' '.join(sorted(ids, key=sort_key))}")
    ids = sorted({i for i, m in marked if not m.startswith(NOTE_ONLY)}
                 | ({id_of(f, order, issues, issues_dir) for f, _ in refusals}
                    if not ok else set()),
                 key=sort_key)
    return ids, lines


def render_commands(order: list, plan: Plan, issues: dict, counts: dict,
                    ledger_rows=(), issues_dir=None, with_run=True,
                    queued=QUEUED_RELEASED) -> list:
    """The pasteable lines, and the block that explains the harden ones.

    **NO NUMBER APPEARS ON TWO PASTEABLE LINES.** Both are commands a reader
    pastes, and a number carried by both teaches the reader to skip one. So a
    member that must be hardened first LEAVES the `/run-issues` line and joins the
    members' `/harden-issues` line. It is never dropped: it is in the table
    above, and the block says which mark moved it.
    """
    first, first_lines = harden_first(order, issues, issues_dir)
    out = list(first_lines)
    out.append("")
    members = sorted({i for i in order if issues[i].status == "needs-harden"}
                     | set(first), key=sort_key)
    ready = [i for i in order
             if issues[i].status == "ready-for-agent" and i not in members]
    # Upstream work the placement wanted and could not have. Never a member,
    # so it never collides with the two lines below.
    before = [i for i in harden_before_the_run(plan, issues, counts,
                                               held_by(ledger_rows, queued))
              if i not in members]
    if before:
        out.append("/harden-issues " + " ".join(before))
    if members:
        out.append("/harden-issues " + " ".join(members))
    if ready and with_run:
        out.append("/run-issues " + " ".join(ready))
    elif with_run and not ready:
        out.append("No /run-issues line: every offered issue has to be hardened "
                   "first. The lines above are the work that can start today.")
    return out


def render(plan: Plan, issues: dict, ledger_rows=(), counts=None,
           issues_dir=None, queued=QUEUED_RELEASED) -> str:
    """OUTPUT 3, and the only output when no run is live: here is the batch."""
    if counts is None:
        counts = fan_out(issues, ledger_rows, queued)
    order, reachable = plan.order, plan.reachable
    width = id_width(order)
    out = render_table(order, issues, counts, ledger_rows)
    out.append("")
    out.append(f"{len(order)} of {reachable} reachable, {reachable - len(order)} not shown")
    out += render_parked(issues)
    out += render_held(issues, ledger_rows, width, queued)
    out += render_waiting_harden(plan, width)
    out += render_commands(order, plan, issues, counts, ledger_rows, issues_dir,
                           True, queued)
    return "\n".join(out) + "\n"


def render_nothing_can_start(plan_b: Plan, issues: dict, runs: list, count: int,
                             ledger_rows=(), counts=None, issues_dir=None,
                             queued=QUEUED_RELEASED) -> str:
    """OUTPUT 1: nothing can start, and here is what the merge releases.

    Measured on one tracker on 2026-09-14 with one run live: every
    candidate the tool could reach was blocked by work that existed only on that
    run's branch, and the tool printed five of them as a batch. This is what it
    should have printed.

    NO `/run-issues` LINE IS PRINTED, deliberately. A new run branches from main,
    and pasting a command whose issues main cannot build is the fault this output
    exists to end. The `/harden-issues` lines ARE printed: hardening writes
    criteria and ships no code, so it is the one thing that can be started today.
    """
    if counts is None:
        counts = fan_out(issues, ledger_rows, queued)
    named = ", ".join(runs)
    plural = "runs" if len(runs) > 1 else "run"
    out = [f"NOTHING CAN START. Every issue this tracker can reach waits on work "
           f"that exists only on the branch of {plural} {named}, which "
           f"{'have' if len(runs) > 1 else 'has'} not merged."]
    out.append("")
    if not plan_b.order:
        out.append(f"No batch becomes available on that merge either: nothing "
                   f"outside {named} is reachable at all.")
    else:
        out.append(f"Available the moment {named} "
                   f"{'merge' if len(runs) > 1 else 'merges'} "
                   f"(asked for {count}, {plan_b.reachable} reachable then):")
        out.append("")
        out += render_table(plan_b.order, issues, counts, ledger_rows)
    width = id_width(plan_b.order or ["Issue"])
    out.append("")
    out.append(f"{len(plan_b.order)} of {plan_b.reachable} reachable after the "
               f"merge, {plan_b.reachable - len(plan_b.order)} not shown")
    out += render_parked(issues)
    out += render_held(issues, ledger_rows, width, queued)
    out += render_waiting_harden(plan_b, width)
    out += render_commands(plan_b.order, plan_b, issues, counts, ledger_rows,
                           issues_dir, False, queued)
    out.append("")
    out.append("No /run-issues command is printed. A new run branches from main, "
               "and main cannot build this batch yet.")
    out.append("Hardening is the work that CAN be started today: it writes "
               "criteria and ships no code, so it does not wait on the merge.")
    return "\n".join(out) + "\n"


def render_some_in_parallel(plan_a: Plan, plan_b: Plan, issues: dict, runs: list,
                            count: int, ledger_rows=(), counts=None,
                            issues_dir=None, queued=QUEUED_RELEASED) -> str:
    """OUTPUT 2: these can run beside the live run, and the rest cannot.

    "Safe to run beside" is a claim about DEPENDENCIES and nothing else. These
    issues need no code that only the live branch carries. Whether two sessions
    would edit the same file is not in any issue file, so this tool does not
    assert it.
    """
    if counts is None:
        counts = fan_out(issues, ledger_rows, queued)
    named = ", ".join(runs)
    plural = "runs" if len(runs) > 1 else "run"
    order = plan_a.order
    out = [f"SOME CAN START IN PARALLEL. {len(order)} issue(s) have every "
           f"blocker done or closed IN MAIN, so they do not wait on the live "
           f"{plural} {named}. Safe beside it on dependencies; this tool cannot "
           f"see whether two sessions would edit the same file."]
    out.append("")
    out += render_table(order, issues, counts, ledger_rows)
    out.append("")
    out.append(f"{len(order)} of {plan_a.reachable} reachable in main today, "
               f"{plan_a.reachable - len(order)} not shown (asked for {count})")
    if plan_b.reachable > plan_a.reachable:
        out.append(f"{plan_b.reachable - plan_a.reachable} more become reachable "
                   f"when {named} "
                   f"{'merge' if len(runs) > 1 else 'merges'}.")
    out += render_parked(issues)
    out += render_held(issues, ledger_rows, id_width(order), queued)
    out += render_waiting_runs(plan_a, id_width(order))
    out += render_waiting_harden(plan_a, id_width(order))
    out += render_commands(order, plan_a, issues, counts, ledger_rows, issues_dir,
                           True, queued)
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues_dir", type=Path)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--theme", default=None)
    parser.add_argument("--by", choices=(FAN_OUT, BY_NUMBER), default=FAN_OUT,
                        help="tie-break among free candidates (default: fan-out)")
    parser.add_argument("--queued", choices=QUEUED_POLICIES,
                        default=QUEUED_RELEASED,
                        help="what a `queued` row on an UNMERGED run does. "
                             "`released` is today's behaviour and the default: "
                             "the issue is offered to a new batch, so an "
                             "abandoned run never locks its queue. `held` keeps "
                             "it for that run. `fresh` holds it only while the "
                             "ledger FILE is younger than --queued-fresh-days. "
                             "WHICH ONE IS RIGHT IS THE HUMAN'S QUESTION, "
                             "queued as "
                             "q-nb01-1; nothing here decides it")
    parser.add_argument("--queued-fresh-days", type=float,
                        default=QUEUED_FRESH_DAYS,
                        help="the window `--queued fresh` calls fresh, in days. "
                             "NOBODY MEASURED THIS NUMBER; it is a guess kept on "
                             "a flag so it is never buried")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.queued_fresh_days <= 0:
        parser.error("--queued-fresh-days must be above zero")
    if not args.issues_dir.is_dir():
        parser.error(f"{args.issues_dir} is not a directory")
    queued = QueuedPolicy(args.queued, args.queued_fresh_days)
    try:
        issues = load_issues(args.issues_dir)
        # Named on stderr, so it reaches a reader watching the terminal without
        # disturbing a caller that parses the report on stdout.
        note = unreadable_note(issues)
        if note:
            print(note, file=sys.stderr)
        rows = load_ledgers(runs_dir_for(args.issues_dir), issues)
        counts = fan_out(issues, rows, queued)
        runs = live_runs(rows)

        # OUTPUT 3, and the shape this tool had until 2026-09-14: no run is
        # live, so main carries everything every ledger carries and there is
        # only one reading of `done`. The count still REFUSES when it cannot be
        # honoured, because nothing but the tracker is standing in the way.
        if not runs:
            plan = schedule(issues, args.count, args.theme, rows, args.by,
                            counts, IN_MAIN, True, queued)
            sys.stdout.write(render(plan, issues, rows, counts,
                                    args.issues_dir, queued))
            return 0

        # A run is live. Two placements, and the pair is the answer:
        #   plan_a  what main can build TODAY
        #   plan_b  what the live branches release when they merge
        # Neither refuses on a short count. The count is still reported, but a
        # live run standing in the way is a better sentence than the arithmetic,
        # and this tool used to print the arithmetic and a batch that could not
        # be built.
        plan_a = schedule(issues, args.count, args.theme, rows, args.by, counts,
                          IN_MAIN, False, queued)
        plan_b = schedule(issues, args.count, args.theme, rows, args.by, counts,
                          ON_A_BRANCH, False, queued)
    except Refusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1

    if plan_a.order:
        sys.stdout.write(render_some_in_parallel(
            plan_a, plan_b, issues, runs, args.count, rows, counts,
            args.issues_dir, queued))
        return 0

    sys.stdout.write(render_nothing_can_start(
        plan_b, issues, runs, args.count, rows, counts, args.issues_dir, queued))
    print(f"REFUSED: nothing can start today. Every reachable issue waits on "
          f"work that exists only on the branch of "
          f"{'runs' if len(runs) > 1 else 'run'} {', '.join(runs)}. "
          f"The batch above is what that merge releases, not a batch to start.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
