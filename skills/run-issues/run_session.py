#!/usr/bin/env python3
"""A batch id, the session it ran in, and what every spawn in it cost.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 3 (rulings 11, 12, 15). The four cost scripts read this and nothing
else, so they agree on what a run IS by construction.

## Why a batch id, and not the run's name

`run_costs.py` used to find a session by looking for the run's name inside the
PROJECT DIRECTORY name, which is the worktree path with the slashes replaced.
That works only while a worktree is named after the run it holds. Two rows in
`.scratch/workflow-audit/run-costs.md` say it did not — 2026-09-02 and
2026-09-05 both carry "the worktree was reused and its name does not match the
branch, so --transcript had to be passed by hand". Run `batch-b5e96d` ran in
`run-issues-414a-99f-286335`.

The road here has no such step. The batch id names a LEDGER, the ledger's
`Worktree:` line names a path, and the path IS the project slug. Whatever the
worktree is called is never read.

## Why liveness is not asked about

`find_live_ledger.py` returns only live ledgers, because it picks a run to
RESUME. A cost script measures a run that has just finished, whose owner line
by then reads `awaiting-merge` or `merged`. Same files, opposite question. This
module answers the second one and reuses that file for everything else: the
layout, the candidate reader, and the worktree walk all stay owned there.
"""

from __future__ import annotations

import importlib.util
import os
import sys


def _load(name, filename):
    """Load a sibling script by path, as `model_map.py` and the hooks do.

    Registered in `sys.modules` before it runs: a `@dataclass` in the loaded
    file resolves its annotations through `sys.modules[cls.__module__]`, and
    on Python 3.14 that lookup raises when the module is absent.
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


# `find_live_ledger.py` owns the ledger layout, so it owns finding one. These
# ship in one directory and each already dies without the other.
_LEDGERS = _load("find_live_ledger", "find_live_ledger.py")

collect_candidates = _LEDGERS.collect_candidates
list_worktrees = _LEDGERS.list_worktrees
parse_worktree_value = _LEDGERS.parse_worktree_value


def ledger_for_batch(batch, repo=None, worktrees=None):
    """The ledger a batch id names, live or finished, or None.

    None where no ledger carries the id. Nothing is picked by count: a single
    candidate that names another batch is still the wrong answer, and the
    155-157 chase cost 25 minutes to a selector that guessed.
    """
    wanted = (batch or "").strip()
    if not wanted:
        return None
    trees = worktrees if worktrees is not None else list_worktrees(repo)
    for candidate in collect_candidates(worktrees=trees):
        if candidate.batch == wanted or candidate.title_batch == wanted:
            return candidate
    return None


PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")

# Every character outside this set becomes a dash in a project directory name.
# Measured 2026-09-06 over all 355 directories under `~/.claude/projects`: not
# one holds any other character, and `/home/user/My Project 01` is
# filed as `-home-user-My-Project-01`, so a space is punctuation too.
KEPT = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def slug_for(worktree_path):
    """The `~/.claude/projects` directory name a worktree's transcripts sit in."""
    path = (worktree_path or "").rstrip("/")
    return "".join(c if c in KEPT else "-" for c in path)


import glob
import re

TIMESTAMP = re.compile(r'"timestamp"\s*:\s*"([^"]+)"')


def last_stamp(path):
    """The newest timestamp inside a transcript, or "" if it holds none.

    Modification time is NOT a proxy for this and the drill of 2026-08-30
    proved it: the newest file by mtime in the busiest project held records
    from 2026-07-27, because a file can be rewritten long after its last turn.
    """
    newest = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                found = TIMESTAMP.search(line)
                if found and found.group(1) > newest:
                    newest = found.group(1)
    except OSError:
        return ""
    return newest


def names_the_batch(path, batch):
    """Does this transcript name the batch it is claimed for?

    The check a foreign session cannot pass, and the reason `run_costs.py`
    stopped appending a row it could not stand behind. A substring scan of a
    file already on disk, costing milliseconds.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return any(batch in line for line in handle)
    except OSError:
        return False


def sessions_for_batch(batch, repo=None, worktrees=None, projects=None):
    """`([main transcript, ...], "")` for a batch id, oldest first, or `([], why)`.

    More than one is a RESUME: a run halted on a usage limit comes back in a
    second session, and both halves spawned real work for this batch. Callers
    that want one session take the last.

    Every refusal names what it looked for. A cost script that cannot identify
    a session prints the reason and records nothing, because a figure from a
    session it could not identify looks exactly like a figure from one it could.
    """
    found = ledger_for_batch(batch, repo=repo, worktrees=worktrees)
    if found is None:
        return [], (
            f"no ledger names batch `{batch}`. Looked in every worktree of this "
            "repository, under `.scratch/*/runs/*/run.md` and "
            "`.scratch/*/round-brief.md`.")

    tree = parse_worktree_value(found.worktree_line)
    if not tree:
        return [], (
            f"{found.path} carries no `Worktree:` line, so nothing says which "
            "directory's transcripts belong to batch "
            f"`{batch}`.")

    slug = slug_for(tree)
    directory = os.path.join(projects or PROJECTS, slug)
    if not os.path.isdir(directory):
        return [], (
            f"batch `{batch}` ran in `{tree}`, whose transcripts would sit in "
            f"`{slug}`, and no such directory exists under "
            f"{projects or PROJECTS}.")

    files = sorted(glob.glob(os.path.join(directory, "*.jsonl")))
    named = [f for f in files if names_the_batch(f, batch)]
    if not named:
        return [], (
            f"none of the {len(files)} transcript(s) in `{slug}` names batch "
            f"`{batch}`, so every one of them is a different session that "
            "happened to sit in the same directory. Nothing was read.")
    return sorted(named, key=last_stamp), ""


import datetime as dt
import json
from dataclasses import dataclass, field

# A row the harness wrote, not a model that answered. MEASURED 2026-09-05 over
# 20000 assistant rows in this machine's subagent transcripts: `<synthetic>`
# really does appear as `message.model`. Counted as a model it makes a
# correctly-mapped spawn report a mismatch and voids a run's trial row on no
# fault at all.
SYNTHETIC = "<synthetic>"


def read_transcript(path):
    """`(models, efforts)` seen on the assistant rows, distinct, in order.

    Lived in `~/.claude/hooks/model-landed-check.py` until sitting 3 of this
    ticket, when the cost scripts needed the same reading. It moved here rather
    than being copied, for the reason the 2026-09-05 review gave when
    `journal_for` had grown a copy in each hook: two readers of one file drift.
    The hook loads it from here and its contract is unchanged.

    Both are reported as SETS rather than one value, because a reader that
    printed one value could print a value the spawn did not have.
    """
    models, efforts = [], []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"assistant"' not in line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("type") != "assistant":
                    continue
                model = ((row.get("message") or {}).get("model") or "").strip()
                if model == SYNTHETIC:
                    continue
                if model and model not in models:
                    models.append(model)
                effort = str(row.get("effort") or "").strip()
                if effort and effort not in efforts:
                    efforts.append(effort)
    except OSError:
        return (), ()
    return tuple(models), tuple(efforts)


@dataclass
class Spawn:
    """One subagent, reduced to what ruling 15 asks a row to carry."""

    agent_id: str = ""
    agent_type: str = ""
    role: str | None = None
    description: str = ""
    models: tuple = ()
    efforts: tuple = ()
    input: int = 0
    cache_creation: int = 0
    cache_read: int = 0
    output: int = 0
    rows: int = 0
    seconds: float = 0.0
    by_model: dict = field(default_factory=dict)


def _moment(stamp):
    try:
        return dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


KINDS = ("input", "cache_creation", "cache_read", "output")

USAGE_KEYS = {
    "input": "input_tokens",
    "cache_creation": "cache_creation_input_tokens",
    "cache_read": "cache_read_input_tokens",
    "output": "output_tokens",
}


def _roles():
    """`{agent type: role key}`. `model_map.py` owns the twelve names."""
    return {name: role
            for role, name in _load("model_map", "model_map.py").ROLES.items()}


def subagents_dir(main_transcript):
    """The `subagents/` directory beside a session's own transcript."""
    stem = os.path.basename(main_transcript)
    if stem.endswith(".jsonl"):
        stem = stem[: -len(".jsonl")]
    return os.path.join(os.path.dirname(main_transcript), stem, "subagents")


def _meta(path):
    try:
        with open(path, encoding="utf-8") as handle:
            blob = json.load(handle)
    except (OSError, ValueError):
        return {}
    return blob if isinstance(blob, dict) else {}


def read_spawn(body_path, roles):
    """One `Spawn` from one subagent transcript, tokens by kind, never merged."""
    agent_id = os.path.basename(body_path)[: -len(".jsonl")]
    meta = _meta(body_path[: -len(".jsonl")] + ".meta.json")
    agent_type = str(meta.get("agentType") or "")
    spawn = Spawn(
        agent_id=agent_id,
        agent_type=agent_type,
        role=roles.get(agent_type),
        description=str(meta.get("description") or ""),
    )
    first = last = None
    seen = set()
    models, efforts = [], []
    try:
        handle = open(body_path, encoding="utf-8", errors="replace")
    except OSError:
        return spawn
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            moment = _moment(row.get("timestamp"))
            if moment:
                first = moment if first is None or moment < first else first
                last = moment if last is None or moment > last else last
            if row.get("type") != "assistant":
                continue
            message = row.get("message") or {}
            named = (message.get("model") or "").strip()
            # `<synthetic>` is a row the harness wrote, not a model that
            # answered, and it is skipped HERE only -- its tokens are still
            # counted below, under its own name.
            if named and named != SYNTHETIC and named not in models:
                models.append(named)
            effort = str(row.get("effort") or "").strip()
            if effort and effort not in efforts:
                efforts.append(effort)
            usage = message.get("usage")
            if not usage:
                continue
            # A retried turn is written twice under one `message.id`. Counting
            # both would report tokens the bill never saw.
            key = message.get("id") or row.get("uuid")
            if key:
                if key in seen:
                    continue
                seen.add(key)
            spawn.rows += 1
            model = (message.get("model") or "").strip()
            counted = spawn.by_model.setdefault(
                model or SYNTHETIC, dict.fromkeys(KINDS, 0))
            for kind, source in USAGE_KEYS.items():
                value = int(usage.get(source, 0) or 0)
                setattr(spawn, kind, getattr(spawn, kind) + value)
                counted[kind] += value
    # One pass, not two. `read_transcript` answers the same question and
    # `orchestrator_cost.py` calls this for every session in its week window
    # AT LAUNCH: a second walk of every subagent transcript took that reading
    # from 1.79s to 4.05s, measured on this machine 2026-09-06.
    spawn.models, spawn.efforts = tuple(models), tuple(efforts)
    if first and last:
        spawn.seconds = (last - first).total_seconds()
    return spawn


def spawn_rows(main_transcripts):
    """One `Spawn` per subagent, over every session of a batch.

    A resumed run has two sessions and both spawned real work for the batch,
    so both directories are walked.
    """
    roles = _roles()
    rows = []
    for main in main_transcripts:
        folder = subagents_dir(main)
        if not os.path.isdir(folder):
            continue
        for body in sorted(glob.glob(os.path.join(folder, "*.jsonl"))):
            rows.append(read_spawn(body, roles))
    return rows


# A row that carried usage and no `message.model`. Not the same gap as
# `<synthetic>`, which names itself, so it does not borrow that word.
UNMEASURED = "unmeasured"

# Not models. Tokens filed under these are recorded, because ruling 11 asks for
# every detail the transcripts hold, and they never make a run look mixed.
NOT_A_MODEL = (SYNTHETIC, UNMEASURED)


def weigh(counts):
    """Weighted tokens WITHIN one model: the four kinds against each other.

    `orchestrator_cost.py` has weighted this way since 2026-08-21 and the share
    it feeds held at 15% under every weighting tried -- 0.1, 0.25, 0.5 and 1.0
    on cache reads, 1 and 5 on output.

    **It weights kinds, never models.** A weighted fable token and a weighted
    opus token are not the same quantity of anything, so nothing here adds two
    models together, and no function in this file returns one figure that spans
    them. The human ruled that on 2026-09-06: record everything, display everything
    per model, and refuse only the merged total, because that total is the one
    number needing a cross-model multiplier and a multiplier is a price with
    the currency taken off (ruling 11; `~/.claude/rulings.md:64-67`).
    """
    return (counts.get("input", 0)
            + counts.get("cache_creation", 0)
            + counts.get("cache_read", 0) / 10
            + counts.get("output", 0) * 5)


def _blank():
    counts = dict.fromkeys(KINDS, 0)
    counts.update(spawns=0, rows=0, seconds=0.0, weighted=0.0, efforts=())
    return counts


def by_model(spawns):
    """`{model: {kind totals, spawns, rows, seconds, weighted}}`.

    Seconds are attributed to every model a spawn ran on, so they are wall
    clock per model and NOT additive across a mixed spawn. A spawn that changed
    model mid-life is rare and the honest reading is that both models occupied
    that clock.
    """
    found = {}
    for spawn in spawns:
        for model, counts in spawn.by_model.items():
            slot = found.setdefault(model, _blank())
            for kind in KINDS:
                slot[kind] += counts.get(kind, 0)
            slot["spawns"] += 1
            slot["rows"] += spawn.rows
            slot["seconds"] += spawn.seconds
            slot["weighted"] += weigh(counts)
    return found


def models_that_answered(spawns):
    """Every real model seen, in the order first seen. Never `<synthetic>`."""
    seen = []
    for spawn in spawns:
        for model in spawn.models:
            if model not in seen and model not in NOT_A_MODEL:
                seen.append(model)
    return tuple(seen)


def mixed(spawns):
    """True when more than one real model answered, so no figure may be merged."""
    return len(models_that_answered(spawns)) > 1


def by_role(spawns):
    """`{role: {models, efforts, spawns, seconds, by_model}}` — ruling 15.

    A spawn outside the twelve loop roles is filed under its agent type, so the
    board render and any by-hand spawn still appear. `role` is the map's word;
    `agent_type` is the harness's, and the key is whichever exists.
    """
    found = {}
    for spawn in spawns:
        key = spawn.role or spawn.agent_type or "(no agent type)"
        slot = found.setdefault(key, {
            "models": (), "efforts": (), "spawns": 0, "rows": 0,
            "seconds": 0.0, "by_model": {},
        })
        slot["models"] = tuple(dict.fromkeys(slot["models"] + spawn.models))
        slot["efforts"] = tuple(dict.fromkeys(slot["efforts"] + spawn.efforts))
        slot["spawns"] += 1
        slot["rows"] += spawn.rows
        slot["seconds"] += spawn.seconds
        for model, counts in spawn.by_model.items():
            into = slot["by_model"].setdefault(model, _blank())
            for kind in KINDS:
                into[kind] += counts.get(kind, 0)
            into["spawns"] += 1
            into["rows"] += spawn.rows
            into["seconds"] += spawn.seconds
            into["weighted"] += weigh(counts)
            # The effort belongs to the spawn, and a spawn is one model far
            # more often than not. Held per model rather than per role, a row
            # can no longer state an effort that model never ran at.
            into["efforts"] = tuple(dict.fromkeys(into["efforts"] + spawn.efforts))
    return found


NOTHING = ("No subagent transcript was read, so there is no per-role or "
           "per-spawn reading. This is a missing measurement, not a failed run.")

# Printed whenever two real models answered inside one run. It is the whole of
# ruling 11's refusal, said where the reader would otherwise add the columns up.
MIXED_NOTE = (
    "This run used mixed models, so no figure above spans them. A weighted\n"
    "fable token and a weighted opus token are not the same quantity, and any\n"
    "single total across the two needs a cross-model multiplier -- which is a\n"
    "price with the currency taken off (ruling 11 refuses a dollar figure).\n"
    "Compare the SAME ROLE across runs: that is like against like and needs no\n"
    "multiplier. For spend, read the `/usage` screen by hand.")


def _thousands(value):
    return f"{int(round(value)):,}"


def render_roles(spawns):
    """The per-role table: role, model, effort, tokens by kind, clock, spawns.

    This is ruling 15's "a model column per role", and it is the table sitting
    4 puts in the merge briefing. One line per role and model pair, because a
    role that ran on two models has two honest rows and no single one.
    """
    if not spawns:
        return NOTHING
    roles = by_role(spawns)
    head = (f"{'role':<24} {'model':<26} {'effort':<8} {'spawns':>6} "
            f"{'input':>10} {'cache_cr':>11} {'cache_rd':>12} {'output':>9} "
            f"{'weighted':>11} {'hours':>7}")
    lines = [head, "-" * len(head)]
    for role in sorted(roles):
        slot = roles[role]
        for model in sorted(slot["by_model"]):
            counts = slot["by_model"][model]
            effort = "/".join(counts["efforts"]) or UNMEASURED
            lines.append(
                f"{role:<24} {model:<26} {effort:<8} {counts['spawns']:>6} "
                f"{_thousands(counts['input']):>10} "
                f"{_thousands(counts['cache_creation']):>11} "
                f"{_thousands(counts['cache_read']):>12} "
                f"{_thousands(counts['output']):>9} "
                f"{counts['weighted'] / 1e6:>10.2f}M "
                f"{counts['seconds'] / 3600:>7.2f}")
    lines.append("")
    lines.append("weighted tokens by model, never added together")
    totals = by_model(spawns)
    for model in sorted(totals):
        slot = totals[model]
        mark = "   (not a model; harness rows)" if model in NOT_A_MODEL else ""
        lines.append(f"  {model:<26} {slot['weighted'] / 1e6:>8.2f}M   "
                     f"{slot['spawns']:>4} spawn(s)   "
                     f"{slot['seconds'] / 3600:>6.2f} h{mark}")
    if mixed(spawns):
        lines.append("")
        lines.append(MIXED_NOTE)
    return "\n".join(lines)


def render_spawns(spawns):
    """One row per subagent — ruling 15, and the human's "record everything"."""
    if not spawns:
        return NOTHING
    head = (f"{'role':<24} {'model':<26} {'effort':<8} {'input':>9} "
            f"{'cache_cr':>10} {'cache_rd':>12} {'output':>8} {'rows':>6} "
            f"{'minutes':>8}  step")
    lines = [head, "-" * len(head)]
    for spawn in sorted(spawns, key=lambda s: -s.seconds):
        lines.append(
            f"{(spawn.role or spawn.agent_type or '?'):<24} "
            f"{('/'.join(spawn.models) or UNMEASURED):<26} "
            f"{('/'.join(spawn.efforts) or UNMEASURED):<8} "
            f"{_thousands(spawn.input):>9} "
            f"{_thousands(spawn.cache_creation):>10} "
            f"{_thousands(spawn.cache_read):>12} "
            f"{_thousands(spawn.output):>8} "
            f"{spawn.rows:>6} {spawn.seconds / 60:>8.1f}  "
            f"{spawn.description[:60]}")
    return "\n".join(lines)


def tier_of(model):
    """The bare tier in a model name (`opus` in `claude-opus-5`), or None.

    `model_map.py` owns the tier order and this is its reader, re-exported so
    the cost scripts do not each load that module for one function.
    """
    return _load("model_map", "model_map.py").tier_name(model)


def main_thread_by_model(path):
    """`{model: weighted}` for one session's OWN transcript, retries counted once.

    The orchestrator's share is main-thread tokens over main plus fleet, which
    is a RATIO ACROSS MODELS the moment a run is mixed. It is therefore
    reported per model and never merged, like every other figure here.
    """
    found = {}
    seen = set()
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return found
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            message = row.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            key = message.get("id") or row.get("uuid")
            if key:
                if key in seen:
                    continue
                seen.add(key)
            model = (message.get("model") or "").strip() or UNMEASURED
            counts = {kind: int(usage.get(source, 0) or 0)
                      for kind, source in USAGE_KEYS.items()}
            found[model] = found.get(model, 0.0) + weigh(counts)
    return found


# `Implement issue 545`, `Verify gate for issue **557b — `. Matched loosely on
# purpose and for the reason `orchestrator_cost.count_issues` gives: the prompt
# format is not stable, and a matcher written against one shape silently
# returned zero on the other when runs `cab74e` and `fd4fa2` opened their gates
# differently.
ISSUE_IN_DESCRIPTION = re.compile(r"\bissue\s+\**([0-9]{1,4}[a-z]?)\b",
                                  re.IGNORECASE)


def issue_count(spawns):
    """How many distinct issues these spawns worked on, off their descriptions.

    Spawns are counted nowhere here: a retry is a second spawn on one issue,
    and the batch size the human picks is a count of issues.
    """
    found = set()
    for spawn in spawns:
        match = ISSUE_IN_DESCRIPTION.search(spawn.description or "")
        if match:
            found.add(match.group(1).lower())
    return len(found)


def share_by_model(orchestrator, spawns):
    """`{model: share}` — the orchestrator's own slice, one model at a time."""
    fleet = by_model(spawns)
    shares = {}
    for model in set(orchestrator) | set(fleet):
        total = orchestrator.get(model, 0.0) + fleet.get(model, {}).get("weighted", 0.0)
        if total:
            shares[model] = orchestrator.get(model, 0.0) / total
    return shares
