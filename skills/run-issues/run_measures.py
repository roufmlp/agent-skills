#!/usr/bin/env python3
"""The per-issue line, the five "faster" figures, and the longest step per kind.

Ticket 37 of the pilot-delivery map, "is the pipeline getting cheaper, faster
or better", sitting 3, deliverable 3 and rulings 5, 17, 18, 20 and 21.

## What this is for, in the human's words

Ruling 5: "one look tells them where to optimise, with no mental arithmetic".
Two uses they named. **Time against issue size**, so they can learn whether a 3x
issue costs 2x time and resize issues in `harden-issues` -- which is why the
estimate midpoint (ruling 18) rides on every per-issue line and why the figure
must include escalations and correction rounds. And **the longest step by
kind**, so a two-hour citation pass is visible on its own (ruling 21).

## It builds records; it reads no disk and writes none

Every input arrives as text, as a mapping, or as a callable. That is not
tidiness: it is what let this be measured against run `batch-170a59` on disk
AND against fixtures, and sitting 4 of ticket 39 is the reason to insist. Its
first per-issue reading was measured against ONE real ledger, looked sound, and
was blind to seven dialects in the other fifteen.

`run_costs.py` is the caller that opens the files.

## Where each field comes from, and why it is that source

| field | source | why |
|---|---|---|
| attempts, strikes, corrections, verdicts | the ledger's status table | the only place they exist |
| span, agent minutes, roles | the run's transcript | ticket 39 ruling 21.3: the ledger records what was ASKED for |
| estimate midpoint | the ledger's `Est` column | ruling 18 |
| stage | `merge-briefing.md`'s rail block | ruling 20; `check_run_rail.read_rail` owns that parse |
| migration | git, keyed by the row's own `committed <sha>` | two sources that cannot drift into agreement |
| cut on a default | `merge-briefing.md`'s `## Ruled` section | CLAUDE.md: a skill records each default AS a default |

Not one of these readers is written here. `run_quality`, `estimate_accuracy`
and `check_run_rail` already own them, and a second reader of one table drifts
in silence -- the lesson `journal_for` taught ticket 39 in sitting 2,
`read_transcript` in sitting 3, and `graded_rows` taught this ticket in
sitting 1.

## Null, never zero and never false

Sitting 2 settled it in the human's words: a run with no strikes is a fact, and a
run whose strikes were never read is not. So an issue the transcript never
named carries `null` for its times and `null` -- not `false` -- for whether it
escalated, and a repository git cannot read leaves `migration` null rather than
saying the commit held none.

## The limit on "cut on a default", stated rather than hidden

There is no marker for it. `## Ruled — N, overturn any of these` is the record
CLAUDE.md's rule produces, and an item there naming an issue is that issue's
default. **It is prose, and it depends on the finale naming the issue in the
item.** A default cut and never written down is not counted, and cannot be.
That is a fact about the record, not about the reader, and it is the same class
of limit sitting 4 stated for the verdicts before ruling 28 minted a marker for
them.
"""

from __future__ import annotations

import importlib.util
import os
import re
import statistics
import sys


def _load(name, filename):
    """Load a sibling script by path, registered before it runs.

    A `@dataclass` in the loaded file resolves its annotations through
    `sys.modules[cls.__module__]`, and on Python 3.14 that lookup raises when
    the module is absent. `run_session.py` and `run_quality.py` carry the same
    loader for the same reason.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    existing = sys.modules.get(name)
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_QUALITY = _load("run_quality", "run_quality.py")
_ESTIMATES = _load("estimate_accuracy", "estimate_accuracy.py")
_ORDER = _load("check_commit_order", "check_commit_order.py")
_RAIL = _load("check_run_rail", "check_run_rail.py")

# Read by role name off the transcript (ticket 39, ruling 21.3). Both were
# readable this way all along and neither was read anywhere until sitting 3.
ESCALATED = "run-issues-implementer-escalated"
CRITICAL = "run-issues-review-gate-critical"

# Anything under this path is a migration. One directory, named once.
MIGRATIONS = "supabase/migrations/"

# `## Ruled — 9, overturn any of these`. The em dash and the count vary; the
# word does not.
RULED = re.compile(r"^#{1,4}\s*Ruled\b.*$", re.IGNORECASE | re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,4}\s+", re.MULTILINE)

ISSUE_FIELDS = (
    "batch", "issue",
    # Ruling 17
    "estimate_minutes", "span_minutes", "agent_minutes", "attempts",
    "correction_rounds", "strikes", "escalated", "verify", "review",
    # Ruling 20's five kind facts. `estimate_minutes` above is the second.
    "stage", "critical_gate", "migration", "cut_on_a_default",
    # Ruling 28's marker, counted rather than assumed.
    "marked_rounds", "derived_strike_disputed",
)


def ruled_section(briefing_text):
    """The body of EVERY `## Ruled` section on the page, joined, or "".

    Each section ends at the next heading of any level. Reading to the end of
    the file instead would sweep in every later section's prose, and the
    sections after it name issues constantly.

    **Every section, not the first, and the corpus is why.** A merge briefing
    is written in passes, so several carry an empty `## Ruled` placeholder
    early and the real `## Ruled — N, overturn any of these` much later:
    `archive-merge-briefing-batch-375cbf.md` holds one at line 529 reading
    "Nothing yet." and the real one at 1785, and `batch-45c8b1` holds the same
    pair at 156 and 2044. Taking the first match read the placeholder, found
    nothing, and reported `cut_on_a_default: false` for every issue in the run.

    That is a false `false`, and it is the shape of the fault ruling 28 sent
    this sitting to repair -- take the first thing that matches rather than the
    right thing, and report an answer with no sign that nothing was read.
    Joining them costs nothing: a placeholder contributes no items, and a
    briefing that genuinely rules twice keeps both.
    """
    text = briefing_text or ""
    parts = []
    for found in RULED.finditer(text):
        rest = text[found.end():]
        stop = NEXT_HEADING.search(rest)
        parts.append(rest[:stop.start()] if stop else rest)
    return "\n".join(parts)


def cut_on_a_default(issue, ruled_text):
    """Does a `## Ruled` item name this issue?

    **The word boundary is the whole of it.** `rg149c-02` is a REGISTER ROW
    prefix that carries `149c`, and a run names its own register rows in this
    very section -- item 9 of `batch-170a59`'s briefing does. Without the
    boundary every such run would mark that issue defaulted.
    """
    if not ruled_text:
        return False
    return bool(re.search(rf"(?<![0-9a-z]){re.escape(issue)}(?![0-9a-z])",
                          ruled_text, re.IGNORECASE))


def stages_from(briefing_text):
    """`{issue: stage}` from the briefing's rail block, or `{}`.

    `check_run_rail.read_rail` owns that parse and `check_run_picture.py`
    already reuses it for exactly this reason: a second reader of the block
    drifts, and the two then disagree about what the briefing says while both
    report a pass.
    """
    if not briefing_text:
        return {}
    rail = _RAIL.read_rail(briefing_text)
    if rail is None:
        return {}
    found = {}
    for cells in rail.rows:
        if len(cells) >= 2 and cells[0].strip():
            found[cells[0].strip()] = cells[1].strip() or None
    return found


def commit_of(row_text):
    """The sha the row records, or None. `check_commit_order` owns the shape."""
    found = _ORDER.COMMITTED.search(row_text or "")
    return found.group("sha") if found else None


def _migration(sha, touched):
    """True, False or None. None means nothing read it (see the docstring)."""
    if not sha or touched is None:
        return None
    try:
        paths = touched(sha)
    except Exception:
        # git absent, a bad repository, a sha this checkout does not hold. All
        # three are "nobody looked", and none of them is "no migration".
        return None
    if paths is None:
        return None
    return any(MIGRATIONS in str(one) for one in paths)


def issue_records(batch, ledger_text, briefing_text="", spans=None,
                  touched=None):
    """One record per row of the ledger's status table (ruling 17).

    `spans` is `estimate_accuracy.actuals(...)[0]`; `touched` answers "what
    paths did this sha change", and both are passed in so that this is pure.
    """
    spans = spans or {}
    estimates = _ESTIMATES.estimates(ledger_text or "")
    stages = stages_from(briefing_text)
    ruled = ruled_section(briefing_text)
    rows = {issue: text for issue, text in _ORDER.status_rows(ledger_text or "")}

    found = []
    for one in _QUALITY.issue_quality(ledger_text or ""):
        seen = spans.get(one.issue)
        roles = (seen or {}).get("roles")
        span = None
        if seen and seen.get("first") and seen.get("last"):
            span = (seen["last"] - seen["first"]).total_seconds() / 60
        found.append({
            "batch": batch,
            "issue": one.issue,
            "estimate_minutes": estimates.get(one.issue),
            "span_minutes": round(span, 2) if span is not None else None,
            "agent_minutes": (round(seen["agent"], 2)
                              if seen and seen.get("agent") is not None
                              else None),
            "attempts": one.attempts or None,
            "correction_rounds": one.corrections,
            "strikes": one.strikes,
            # `null`, not `false`, where no transcript named this issue. The
            # two are a different fact about the pipeline.
            "escalated": (ESCALATED in roles) if roles is not None else None,
            "critical_gate": (CRITICAL in roles) if roles is not None else None,
            "verify": one.verify,
            "review": one.review,
            "stage": stages.get(one.issue),
            "migration": _migration(commit_of(rows.get(one.issue, "")), touched),
            "cut_on_a_default": cut_on_a_default(one.issue, ruled),
            "marked_rounds": one.marked,
            # Sitting 4's `*`, carried onto the line rather than left in the
            # printed block. Ruling 28 keeps it: a row whose own words disagree
            # with the derived strike count.
            "derived_strike_disputed": bool(one.flags),
        })
    return found


def _per_issue(total, count):
    return round(total / count, 2) if total is not None and count else None


def faster(issues, wall_hours=None, idle_hours=None, agent_hours=None):
    """Ruling 5's five figures, all RECORDED and none left to be divided.

    The human's aim is one look with no mental arithmetic, so a reader that had to
    divide `Hours` by `Issues` to get the first of these would not have it.
    Each is null on its own where its input is missing; a missing clock costs
    one figure, never the other four.
    """
    count = len(issues)
    ratios = [one["span_minutes"] / one["estimate_minutes"]
              for one in issues
              if one.get("estimate_minutes") and one.get("span_minutes")]
    return {
        "wall_minutes_per_issue": _per_issue(
            wall_hours * 60 if wall_hours is not None else None, count),
        "idle_minutes_per_issue": _per_issue(
            idle_hours * 60 if idle_hours is not None else None, count),
        "agent_hours_per_issue": _per_issue(agent_hours, count),
        # The MEDIAN, which is what `estimate_accuracy.py:284` prints and what
        # stops one runaway issue deciding the figure on its own.
        "estimate_median_ratio": (round(statistics.median(ratios), 2)
                                  if ratios else None),
        "issues_rated": len(ratios),
    }


def longest_steps(stamped, agent_steps):
    """`{kind: {...}}` — the longest step of every kind (ruling 21).

    **Both halves, because neither alone can answer the question.** A finale's
    mechanical steps leave no duration in a transcript at all
    (`run_timings.py:40-46` records that a backgrounded Bash call reads as
    instant), and an agent step leaves none in `steps.jsonl`. Ruling 19 built
    the wrapper so that this join could exist.

    Every entry says which instrument measured it. A stamped step is a wall
    clock held by `run_step.py` around a call it did not make; an agent step is
    a tool call's own span out of the transcript. A reader comparing two
    numbers has to be able to see that they were taken differently.
    """
    found = {}
    for lines, measured in ((stamped or (), "stamped"),
                            (agent_steps or (), "agent")):
        for line in lines:
            kind, seconds = line.get("kind"), line.get("seconds")
            if not kind or not isinstance(seconds, (int, float)):
                continue
            if kind in found and found[kind]["minutes"] >= seconds / 60:
                continue
            found[kind] = {"minutes": round(seconds / 60, 2),
                           "label": line.get("label") or "",
                           "measured": measured}
    return found
