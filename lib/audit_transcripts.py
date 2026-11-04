#!/usr/bin/env python3
"""Read one Claude Code session transcript and summarise it for the audit.

The weekly audit (`audit_week.py`) and the one-off version 1 measurement
(`measure_v1.py`) both need the same facts about a session, and both read the
same files: `~/.claude/projects/<folder>/<session-id>.jsonl` for the main
thread and `<folder>/<session-id>/subagents/agent-*.jsonl` for its subagents.
This module is the one reader. It streams a transcript line by line and keeps
a few hundred bytes per session, so a 10 GB store fits in minutes and in a few
MB of memory.

What a summary holds, and the rule behind each field:

  hours          first timestamp to last, main thread only. This is what
                 `run_timings.py` measured for a version 1 run, so version 2
                 reads the same instrument (research 17, "How to measure
                 version 2 the same way").
  tokens         per model: input, cache writes at the 5-minute and the 1-hour
                 rate, cache reads, output. Main thread plus subagents. One
                 assistant message can appear on several rows with the same
                 message id; the rows carry the same counts, so the reader
                 keeps the largest value per id, which is right whether rows
                 repeat or run up.
  cost_usd       list price from PRICES, per message, so Haiku's two rates by
                 prompt length apply per message. Models not in PRICES are
                 counted under `unpriced`, never silently priced at zero. The
                 rows' output count is a floor: one hunt's rows summed to 2.8
                 million output tokens where the app's own `cost-state` record
                 said 11.7 million. `cost_state_usd` and `app_tokens` carry
                 that record where the session wrote one.
  context        the first assistant message's context size (start), the
                 largest, and the count of compactions (`compact_boundary`).
  questions      AskUserQuestion tool calls and the ❓ marker in assistant text.
  interruptions  a gap of INTERRUPTION_MINUTES or more during which nothing
                 wrote: not the main thread, not any subagent. The cause is
                 read from the last main-thread record before the gap. A
                 version change across the gap marks a restart.
  skills, agents Skill and Agent tool calls by name, and the `attributionSkill`
                 field a record carries when a skill shaped it.
  drift          `DRIFT:` lines in tool results, for the Drift row.
  kind           run, hunt, direct-road or other, from the first prompt.

Lines whose type is `api-request`, `api-request-blob`, `api-request-shape` or
`file-history-snapshot` are skipped before parsing: they carry whole prompts,
are most of the bytes, and hold nothing the summary needs.
"""

import bisect
import json
import os
import re
import statistics
from datetime import datetime, timezone

INTERRUPTION_MINUTES = 30

# Dollars per million tokens: input, 5-minute cache write, 1-hour cache write,
# cache read, output. platform.claude.com/docs/en/about-claude/pricing, read
# 2026-11-02. Haiku 5.5 has one row per prompt length; see price_of().
PRICES = {
    "claude-fable-5-1": (10, 12.5, 20, 0.25, 50),
    "claude-fable-5": (10, 12.5, 20, 1, 50),
    "claude-opus-5-5": (4, 5, 8, 0.20, 20),
    "claude-opus-5": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-8": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-7": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-6": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-5": (5, 6.25, 10, 0.50, 25),
    "claude-sonnet-5-5": (2, 2.5, 4, 0.10, 10),
    "claude-sonnet-5": (2, 2.5, 4, 0.20, 10),
    "claude-sonnet-4-6": (3, 3.75, 6, 0.30, 15),
    "claude-sonnet-4-5": (3, 3.75, 6, 0.30, 15),
    "claude-haiku-5-5": (0.5, 0.625, 1, 0.05, 2.5),
    "claude-haiku-5-5-short": (0.1, 0.125, 0.2, 0.01, 0.5),
    "claude-haiku-4-5": (1, 1.25, 2, 0.10, 5),
}
PRICES_SOURCE = "platform.claude.com/docs/en/about-claude/pricing, read 2026-11-02"

SKIP_PREFIXES = (
    '{"type":"api-request',
    '{"type":"file-history-snapshot',
)

LIMIT_WORDS = ("usage limit", "hit your limit", "limit reached", "you've reached your", "resets at", "resets in")

TOKEN_FIELDS = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")


def price_of(model, context_tokens):
    """Return the price tuple for a model, or None when the model is not priced.

    A dated id (`claude-haiku-4-5-20251001`) and the long-context suffix
    (`claude-opus-5-5[1m]`) price as the plain model.
    """
    model = re.sub(r"(\[1m\]|-\d{8})$", "", model)
    if model == "claude-haiku-5-5" and context_tokens <= 100_000:
        return PRICES["claude-haiku-5-5-short"]
    return PRICES.get(model)


def message_cost(model, tokens, context_tokens):
    """List-price dollars for one message's tokens, or None when unpriced."""
    rates = price_of(model, context_tokens)
    if rates is None:
        return None
    parts = (tokens["input"], tokens["cache_write_5m"], tokens["cache_write_1h"], tokens["cache_read"], tokens["output"])
    return sum(n * r for n, r in zip(parts, rates)) / 1_000_000


def parse_ts(value):
    """ISO timestamp with a Z or an offset to an aware datetime; None if unreadable."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def project_of(folder):
    """The short project name a transcript folder belongs to.

    `-Users-roufmlp-code-orderflow--claude-worktrees-run-12ab` is orderflow, so is
    `-private-tmp-claude-501--Users-roufmlp-code-orderflow-...` (a scratchpad
    folder); `-Users-roufmlp--claude-skills` is skills. Anything else keeps its
    last path part.
    """
    if "-scratch-workspaces-" in folder:
        return "cowork-scratch"
    if "-Claude-CoWork-" in folder:
        return "cowork"
    name = folder
    for prefix in ("-private-tmp-claude-501-", "-private-tmp-"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    name = name.split("--claude-worktrees-")[0]
    m = re.match(r"^-Users-[^-]+-code-(.+)$", name)
    if m:
        return m.group(1)
    m = re.match(r"^-Users-[^-]+--claude-(.+)$", name)
    if m:
        return m.group(1)
    if "run-harness" in folder:
        return "run-harness"
    return name.strip("-").split("-")[-1] or folder


def kind_of(first_prompt):
    text = (first_prompt or "").strip().lower()
    if text.startswith("/run-issues"):
        return "run"
    if text.startswith("/parallel-hunt"):
        return "hunt"
    if "direct road" in text:
        return "direct-road"
    return "other"


def _text_of(content):
    """The plain text in a message content, string or block list; tool results left out."""
    if isinstance(content, str):
        return content
    out = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                out.append(block.get("text") or "")
    return "\n".join(out)


def _iter_records(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(SKIP_PREFIXES):
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _empty_tokens():
    return {k: 0 for k in TOKEN_FIELDS}


class _Reader:
    """Accumulates one transcript file (main or subagent) into shared totals."""

    def __init__(self, summary):
        self.s = summary
        self.seen = {}  # message id -> (model, tokens, context)
        self.timestamps = []
        self.events = []  # main thread only: (ts, descriptor)

    def read(self, path, main):
        for rec in _iter_records(path):
            ts = parse_ts(rec.get("timestamp"))
            if ts is not None:
                self.timestamps.append(ts)
            kind = rec.get("type")
            if main:
                self._main_fields(rec)
            if kind == "assistant":
                self._assistant(rec, ts, main)
            elif kind == "user":
                self._user(rec, ts, main)
            elif kind == "system":
                self._system(rec, ts, main)
            skill = rec.get("attributionSkill")
            if skill:
                self.s["skills_attributed"][skill] = self.s["skills_attributed"].get(skill, 0) + 1
        for model, tokens, ctx in self.seen.values():
            per_model = self.s["tokens"].setdefault(model, _empty_tokens())
            for k in TOKEN_FIELDS:
                per_model[k] += tokens[k]
            cost = message_cost(model, tokens, ctx)
            if cost is None:
                self.s["unpriced"][model] = self.s["unpriced"].get(model, 0) + sum(tokens.values())
            else:
                self.s["cost_usd"] += cost
        self.seen = {}

    def _main_fields(self, rec):
        s = self.s
        if not s["cwd"] and rec.get("cwd"):
            s["cwd"] = rec["cwd"]
            s["branch"] = rec.get("gitBranch")
        if rec.get("version"):
            s["versions"].add(rec["version"])
        if rec.get("type") == "last-prompt" and not s["first_prompt"]:
            s["first_prompt"] = (rec.get("lastPrompt") or "")[:120]
        if rec.get("type") == "cost-state":
            # The app's own running total for the whole session, subagents
            # included. Its output count is several times the rows' sum (the
            # rows lost output tokens in some versions; research 17 saw the
            # hole), so the audit shows this figure where a session has one
            # and the rows' figure as the floor.
            s["cost_state_usd"] = rec.get("totalCostUSD")
            s["app_tokens"] = {
                model: {
                    "input": m.get("inputTokens", 0),
                    "output": m.get("outputTokens", 0),
                    "thinking": m.get("thinkingTokens", 0),
                    "cache_read": m.get("cacheReadInputTokens", 0),
                    "cache_write": m.get("cacheCreationInputTokens", 0),
                }
                for model, m in (rec.get("modelUsage") or {}).items()
                if isinstance(m, dict)
            }

    def _assistant(self, rec, ts, main):
        msg = rec.get("message") or {}
        model = msg.get("model") or "unknown"
        usage = msg.get("usage") or {}
        cache = usage.get("cache_creation") or {}
        tokens = {
            "input": usage.get("input_tokens") or 0,
            "cache_write_5m": cache.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens") or 0) or 0,
            "cache_write_1h": cache.get("ephemeral_1h_input_tokens") or 0,
            "cache_read": usage.get("cache_read_input_tokens") or 0,
            "output": usage.get("output_tokens") or 0,
        }
        context = tokens["input"] + tokens["cache_read"] + tokens["cache_write_5m"] + tokens["cache_write_1h"]
        mid = msg.get("id") or rec.get("uuid")
        if model != "<synthetic>" and usage:
            prev = self.seen.get(mid)
            if prev is None:
                self.seen[mid] = (model, tokens, context)
                if main:
                    self.s["messages"] += 1
                    if self.s["context"]["start"] is None:
                        self.s["context"]["start"] = context
                    self.s["context"]["largest"] = max(self.s["context"]["largest"], context)
            else:
                merged = {k: max(prev[1][k], tokens[k]) for k in TOKEN_FIELDS}
                self.seen[mid] = (model, merged, max(prev[2], context))
        tools = []
        text = ""
        for block in msg.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name") or ""
                tools.append(name)
                inp = block.get("input") or {}
                if name == "Skill" and main:
                    skill = inp.get("skill") or "?"
                    self.s["skills"][skill] = self.s["skills"].get(skill, 0) + 1
                elif name == "Agent" and main:
                    agent = inp.get("subagent_type") or "general-purpose"
                    self.s["agents"][agent] = self.s["agents"].get(agent, 0) + 1
                elif name == "AskUserQuestion":
                    self.s["questions"]["tool"] += 1
            elif block.get("type") == "text":
                text += block.get("text") or ""
        if "❓" in text:
            self.s["questions"]["marker"] += text.count("❓")
        if main and ts is not None:
            self.events.append((ts, ("assistant", tuple(tools), text.rstrip().endswith("?"))))

    def _user(self, rec, ts, main):
        msg = rec.get("message") or {}
        content = msg.get("content")
        text = _text_of(content)
        has_result = isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )
        if has_result:
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    body = b.get("content")
                    body = body if isinstance(body, str) else json.dumps(body) if body else ""
                    if "DRIFT:" in body:
                        self.s["drift"] += body.count("DRIFT:")
        if main and not self.s["first_prompt"] and text.strip() and not rec.get("isMeta") and not has_result:
            if not text.lstrip().startswith("<"):
                self.s["first_prompt"] = text.strip()[:120]
        limit = (not has_result) and any(w in text.lower() for w in LIMIT_WORDS)
        if limit:
            self.s["limit_waits"] += 1
        if main and ts is not None:
            self.events.append((ts, ("tool_result" if has_result else "user", limit)))

    def _system(self, rec, ts, main):
        sub = rec.get("subtype")
        if sub == "compact_boundary":
            self.s["context"]["compactions"] += 1
        elif sub == "api_error":
            self.s["api_errors"] += 1
        content = rec.get("content") or ""
        limit = isinstance(content, str) and any(w in content.lower() for w in LIMIT_WORDS)
        if limit:
            self.s["limit_waits"] += 1
        if main and ts is not None:
            self.events.append((ts, ("system", sub, limit)))


def _cause(descriptor):
    kind = descriptor[0]
    if kind == "system":
        _, sub, limit = descriptor
        if limit:
            return "usage limit"
        if sub == "api_error":
            return "error"
        return "unknown: sleep, crash or left open"
    if kind == "user":
        _, limit = descriptor
        if limit:
            return "usage limit"
        return "no answer after a prompt: crash, restart or sleep"
    if kind == "tool_result":
        return "no turn after a tool result: crash, restart or sleep"
    _, tools, asks = descriptor
    if "AskUserQuestion" in tools:
        return "question to Abdul"
    if tools:
        return "tool call open: permission prompt or long command"
    if asks:
        return "question to Abdul"
    return "turn ended: waiting for Abdul"


def _interruptions(reader, versions_by_ts):
    stamps = sorted(reader.timestamps)
    events = sorted(reader.events, key=lambda e: e[0])
    event_ts = [e[0] for e in events]
    out = []
    limit = INTERRUPTION_MINUTES * 60
    for a, b in zip(stamps, stamps[1:]):
        gap = (b - a).total_seconds()
        if gap < limit:
            continue
        i = bisect.bisect_right(event_ts, a) - 1
        # A stop-hook summary or another plain system record follows every
        # turn; it says nothing about why the session then waited, so read
        # back to the last record that does.
        while i >= 0 and events[i][1][0] == "system" and events[i][1][1] != "api_error" and not events[i][1][2]:
            i -= 1
        cause = _cause(events[i][1]) if i >= 0 else "unknown: sleep, crash or left open"
        before = versions_by_ts.get(a)
        after = versions_by_ts.get(b)
        if before and after and before != after:
            cause += " (version changed: restart)"
        out.append({"at": a.isoformat(), "minutes": round(gap / 60, 1), "cause": cause})
    return out


def summarise(main_path):
    """Summarise one main transcript and its subagents. Returns None for a file with no timestamps."""
    folder = os.path.basename(os.path.dirname(main_path))
    session_id = os.path.splitext(os.path.basename(main_path))[0]
    s = {
        "id": session_id,
        "folder": folder,
        "project": project_of(folder),
        "cwd": None,
        "branch": None,
        "kind": None,
        "first_prompt": None,
        "start": None,
        "end": None,
        "hours": 0.0,
        "messages": 0,
        "subagents": 0,
        "subagent_hours": 0.0,
        "tokens": {},
        "cost_usd": 0.0,
        "cost_state_usd": None,
        "app_tokens": {},
        "unpriced": {},
        "context": {"start": None, "largest": 0, "compactions": 0},
        "questions": {"tool": 0, "marker": 0},
        "interruptions": [],
        "limit_waits": 0,
        "api_errors": 0,
        "skills": {},
        "skills_attributed": {},
        "agents": {},
        "drift": 0,
        "versions": set(),
        "mtime": int(os.path.getmtime(main_path)),
    }
    reader = _Reader(s)
    versions_by_ts = {}
    for rec in _iter_records(main_path):
        ts = parse_ts(rec.get("timestamp"))
        if ts is not None and rec.get("version"):
            versions_by_ts[ts] = rec["version"]
    reader.read(main_path, main=True)
    if not reader.timestamps:
        return None
    main_stamps = sorted(reader.timestamps)
    s["start"], s["end"] = main_stamps[0].isoformat(), main_stamps[-1].isoformat()
    s["hours"] = round((main_stamps[-1] - main_stamps[0]).total_seconds() / 3600, 3)

    sub_dir = os.path.join(os.path.dirname(main_path), session_id, "subagents")
    if os.path.isdir(sub_dir):
        for name in sorted(os.listdir(sub_dir)):
            if not name.endswith(".jsonl"):
                continue
            before = len(reader.timestamps)
            reader.read(os.path.join(sub_dir, name), main=False)
            own = sorted(reader.timestamps[before:])
            if own:
                s["subagents"] += 1
                s["subagent_hours"] += (own[-1] - own[0]).total_seconds() / 3600
    s["subagent_hours"] = round(s["subagent_hours"], 3)
    s["interruptions"] = _interruptions(reader, versions_by_ts)
    s["kind"] = kind_of(s["first_prompt"])
    s["cost_usd"] = round(s["cost_usd"], 6)
    s["versions"] = sorted(s["versions"])
    return s


def main_transcripts(projects_dir):
    """Every main transcript path under a projects store, sorted."""
    out = []
    if not os.path.isdir(projects_dir):
        return out
    for folder in sorted(os.listdir(projects_dir)):
        full = os.path.join(projects_dir, folder)
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if name.endswith(".jsonl"):
                out.append(os.path.join(full, name))
    return out


def max_concurrent(intervals):
    """The most intervals (start, end) open at one moment."""
    points = []
    for a, b in intervals:
        points.append((a, 1))
        points.append((b, -1))
    points.sort(key=lambda p: (p[0], p[1]))
    best = cur = 0
    for _, d in points:
        cur += d
        best = max(best, cur)
    return best


def median_or_none(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values)) if values else None


def month_of(iso):
    return (iso or "")[:7]


def utc_now():
    return datetime.now(timezone.utc)
