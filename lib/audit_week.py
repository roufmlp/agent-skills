#!/usr/bin/env python3
"""The weekly audit: summarise new sessions, snapshot the workflow's size, write the month's table.

"How a regular audit keeps the workflow small" puts the measuring on the
laptop, because the brainstorm routine runs in the cloud and cannot read the
transcripts. A desktop scheduled task runs this script every Sunday. It
writes three things into the ideas repo and pushes them, which that repo's
rule allows without asking:

  audit/sessions.jsonl   one line per main session, from `audit_transcripts`.
                         A session is read again only when its transcript has
                         changed since (its mtime), so a session open across
                         two Sundays is read twice and stored once. A line
                         stays after Claude Code deletes the transcript, which
                         is what lets the keep go back to 30 days.
  audit/growth.jsonl     one line per run: the skills, agents, hooks and
                         workflows by name, and the line counts of the private
                         CLAUDE.md and memory. The Growth and Not used rows
                         diff two of these.
  pages/<1st>-audit.md   the table for the next 1st of the month: one row per
                         measure, columns this month, last month and version 1
                         (from audit/v1-baseline.json, written once by
                         `measure_v1.py`), then the proposals. The brainstorm
                         page on the 1st links this file by that name. Every
                         Sunday rewrites it, so the 1st reads the newest.

The audit measures and proposes. It removes nothing, and a proposal is a
line ending "yes or no?" that the session with Abdul puts to him.

    python3 audit_week.py [--projects ~/.claude/projects] [--ideas ~/code/ideas]
                          [--home ~/.claude] [--today YYYY-MM-DD] [--no-push]
"""

import argparse
import collections
import datetime as dt
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audit_transcripts as at  # noqa: E402

ROWS = ("Cost", "Tokens", "Speed", "Decisions", "Interruptions", "Bugs", "Parallel", "Drift", "Not used", "Growth")


def load_jsonl(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def refresh_sessions(projects_dir, stored, today):
    """Return (sessions, read): stored lines kept, changed or new transcripts read again."""
    by_id = {s["id"]: s for s in stored}
    read = set()
    for path in at.main_transcripts(projects_dir):
        session_id = os.path.splitext(os.path.basename(path))[0]
        known = by_id.get(session_id)
        if known and known.get("mtime") == int(os.path.getmtime(path)) and session_id not in read:
            continue
        summary = at.summarise(path)
        if summary is None:
            continue
        summary["summarised"] = today
        by_id[session_id] = summary
        read.add(session_id)
    sessions = sorted(by_id.values(), key=lambda s: s.get("start") or "")
    return sessions, len(read)


def line_count(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def growth_snapshot(home, today):
    skills = sorted(
        os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(home, "skills", "*", "SKILL.md"))
    )
    agents = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(home, "agents", "*.md")))
    workflows = sorted(os.path.basename(p) for p in glob.glob(os.path.join(home, "workflows", "*")))
    hooks = []
    settings = os.path.join(home, "settings.json")
    if os.path.isfile(settings):
        try:
            with open(settings, encoding="utf-8") as fh:
                data = json.load(fh)
        except ValueError:
            data = {}
        for event, entries in (data.get("hooks") or {}).items():
            for entry in entries or []:
                for hook in entry.get("hooks") or []:
                    cmd = hook.get("command") or ""
                    name = os.path.basename(cmd.split()[1]) if cmd.startswith("python3 ") and len(cmd.split()) > 1 else cmd
                    hooks.append(f"{event}:{name}")
    claude_md = os.path.join(home, "CLAUDE.md")
    claude_lines = line_count(claude_md) if os.path.isfile(claude_md) else 0
    memory_lines = sum(line_count(p) for p in glob.glob(os.path.join(home, "projects", "*", "memory", "*.md")))
    return {
        "date": today,
        "skills": skills,
        "agents": agents,
        "hooks": sorted(hooks),
        "workflows": workflows,
        "claude_md_lines": claude_lines,
        "memory_lines": memory_lines,
    }


def month_window(day):
    """(this_month, last_month, next_first) as strings for a date."""
    first = day.replace(day=1)
    last_month_end = first - dt.timedelta(days=1)
    next_first = (first + dt.timedelta(days=32)).replace(day=1)
    return first.strftime("%Y-%m"), last_month_end.strftime("%Y-%m"), next_first.isoformat()


def mvp_speeds(ideas_dir):
    """Days from start to live for each MVP line in mvps.md that has a live date."""
    path = os.path.join(ideas_dir, "mvps.md")
    if not os.path.isfile(path):
        return []
    header = None
    out = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if cells and set(cells[0]) <= {"-", " "}:
            continue
        row = dict(zip(header, cells))
        start, live = row.get("start"), row.get("live")
        if start and live:
            try:
                days = (dt.date.fromisoformat(live) - dt.date.fromisoformat(start)).days
            except ValueError:
                continue
            out.append((row.get("name") or "?", days, live))
    return out


def used_names(sessions):
    skills = collections.Counter()
    agents = collections.Counter()
    for s in sessions:
        skills.update(s.get("skills") or {})
        skills.update(s.get("skills_attributed") or {})
        agents.update(s.get("agents") or {})
    return skills, agents


def fmt_k(n):
    return f"{round((n or 0) / 1000)}k"


def month_cells(sessions, month, snapshot, previous, speeds):
    """One dict row -> text for the sessions that started in `month`."""
    group = [s for s in sessions if at.month_of(s.get("start")) == month]
    if not group:
        return {row: "no sessions" for row in ROWS}, group
    hours = sum(s["hours"] for s in group)
    kinds = collections.Counter(s["kind"] for s in group)
    kind_text = ""
    if kinds.get("run") or kinds.get("hunt"):
        parts = {k: round(sum(s["hours"] for s in group if s["kind"] == k), 1) for k in kinds}
        kind_text = " (" + ", ".join(f"{v} h {k}" for k, v in parts.items()) + ")"
    tokens = {}
    for s in group:
        for model, t in s["tokens"].items():
            tokens.setdefault(model, collections.Counter()).update(t)
    tok = "; ".join(
        f"{m.replace('claude-', '')} {at_fmt(t['cache_read'])} cache reads, {at_fmt(t['output'])} output"
        for m, t in sorted(tokens.items(), key=lambda kv: -sum(kv[1].values()))
        if sum(t.values()) >= 100_000
    )
    cost_rows = sum(s["cost_usd"] for s in group)
    app = [s["cost_state_usd"] for s in group if s.get("cost_state_usd") is not None]
    compactions = sum(s["context"]["compactions"] for s in group)
    compacted = sum(1 for s in group if s["context"]["compactions"])
    starts = at.median_or_none([s["context"]["start"] for s in group])
    largest = max(s["context"]["largest"] for s in group)
    questions = sum(s["questions"]["tool"] for s in group)
    markers = sum(s["questions"]["marker"] for s in group)
    interruptions = [i for s in group for i in s["interruptions"]]
    causes = collections.Counter(i["cause"] for i in interruptions)
    lost = sum(i["minutes"] for i in interruptions) / 60
    drift = sum(s["drift"] for s in group)
    intervals = [(at.parse_ts(s["start"]), at.parse_ts(s["end"])) for s in group]
    skills_used, agents_used = used_names(group)
    not_used = [n for n in snapshot["skills"] if n not in skills_used] + [n for n in snapshot["agents"] if n not in agents_used]
    growth = []
    if previous:
        for key in ("skills", "agents", "hooks", "workflows"):
            added = sorted(set(snapshot[key]) - set(previous.get(key) or []))
            removed = sorted(set(previous.get(key) or []) - set(snapshot[key]))
            if added:
                growth.append(f"added {key}: {', '.join(added)}")
            if removed:
                growth.append(f"removed {key}: {', '.join(removed)}")
    counts = (
        f"{len(snapshot['skills'])} skills, {len(snapshot['agents'])} agents, {len(snapshot['hooks'])} hooks, "
        f"{len(snapshot['workflows'])} workflows; CLAUDE.md {snapshot['claude_md_lines']} lines, memory {snapshot['memory_lines']} lines"
    )
    month_speeds = [f"{name} {days} days" for name, days, live in speeds if live.startswith(month)]
    cells = {
        "Cost": f"{len(group)} sessions, {hours:.1f} h{kind_text}; per change note: not measured until stage two",
        "Tokens": (
            f"rows: {tok or 'under 100k'}; list ${cost_rows:,.0f}, a floor; app's own ${sum(app):,.0f} on {len(app)} sessions. "
            f"Median start {fmt_k(starts)}, largest {fmt_k(largest)}, {compactions} compactions in {compacted} of {len(group)} sessions"
        ),
        "Speed": ", ".join(month_speeds) if month_speeds else "no MVP went live",
        "Decisions": f"{questions} by the question tool, {markers} ❓ markers; per change note or brief: not measured until stage two",
        "Interruptions": (
            f"{len(interruptions)} in {sum(1 for s in group if s['interruptions'])} sessions, {lost:.1f} h: "
            + (", ".join(f"{v} {k}" for k, v in causes.most_common(4)) or "none")
        ),
        "Bugs": "not measured until stage two (fix commits per note, hunt rows)",
        "Parallel": f"most sessions at once {at.max_concurrent(intervals)}",
        "Drift": f"{drift} DRIFT lines",
        "Not used": ", ".join(not_used) if not_used else "every skill and agent was used",
        "Growth": "; ".join(growth + [counts]) if growth else counts,
    }
    return cells, group


def at_fmt(n):
    if n >= 1_000_000_000:
        return f"{n / 1e9:.1f} G"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f} M"
    return f"{round(n / 1e3)}k"


def proposals(sessions, this_month, last_month, snapshot, previous_snapshot):
    out = []
    this_group = [s for s in sessions if at.month_of(s.get("start")) == this_month]
    last_group = [s for s in sessions if at.month_of(s.get("start")) == last_month]
    # "Not used in two audits" needs two audits: the name was already there at
    # the previous snapshot, and no session in either month used it. A skill
    # built this month is never proposed for retirement on its first table.
    if this_group and last_group and previous_snapshot:
        skills_now, agents_now = used_names(this_group)
        skills_then, agents_then = used_names(last_group)
        for name in snapshot["skills"]:
            if name in previous_snapshot.get("skills", []) and name not in skills_now and name not in skills_then:
                out.append(f"retire the skill {name}: not used in two audits, yes or no?")
        for name in snapshot["agents"]:
            if name in previous_snapshot.get("agents", []) and name not in agents_now and name not in agents_then:
                out.append(f"retire the agent {name}: not used in two audits, yes or no?")
    if this_group:
        compacted = sum(1 for s in this_group if s["context"]["compactions"])
        if compacted * 10 > len(this_group):
            out.append(
                f"a fix for compaction, such as smaller notes: {compacted} of {len(this_group)} sessions compacted this month, yes or no?"
            )
        now = at.median_or_none([s["context"]["start"] for s in this_group])
        then = at.median_or_none([s["context"]["start"] for s in last_group]) if last_group else None
        if now and then and now <= then * 0.9:  # a fall of a tenth or more; less is noise
            out.append(
                f"lower the compaction window from 400k to 300k: the median start size fell from {fmt_k(then)} to {fmt_k(now)}, yes or no?"
            )
    return out


def render_page(today, this_month, last_month, this_cells, last_cells, v1_column, props, n_sessions, n_read):
    lines = [
        f"# Audit table, written {today}",
        "",
        f"One row per measure. Columns: {this_month} (this month), {last_month} (last month), version 1. "
        f"{n_sessions} sessions in audit/sessions.jsonl, {n_read} read this run. The audit removes nothing.",
        "",
        f"| Row | {this_month} | {last_month} | Version 1 |",
        "| --- | --- | --- | --- |",
    ]
    for row in ROWS:
        lines.append(f"| {row} | {this_cells[row]} | {last_cells[row]} | {v1_column.get(row, 'not measured')} |")
    lines += ["", "## Proposals", ""]
    lines += [f"- {p}" for p in props] or ["- none this month"]
    return "\n".join(lines) + "\n"


def git(ideas_dir, *args):
    return subprocess.run(["git", "-C", ideas_dir, *args], capture_output=True, text=True)


def commit_and_push(ideas_dir, today, push):
    git(ideas_dir, "add", "audit", "pages")
    status = git(ideas_dir, "status", "--porcelain", "audit", "pages").stdout.strip()
    if not status:
        return "nothing to commit"
    commit = git(ideas_dir, "commit", "-q", "-m", f"Weekly audit for {today}")
    if commit.returncode != 0:
        return f"commit failed: {commit.stderr.strip()}"
    if not push:
        return "committed, not pushed"
    for attempt in (1, 2):
        pull = git(ideas_dir, "pull", "--rebase", "origin", "main")
        pushed = git(ideas_dir, "push", "origin", "main")
        if pull.returncode == 0 and pushed.returncode == 0:
            return "committed and pushed"
    return f"committed, push failed twice: {pushed.stderr.strip()[:200]}"


def run(projects_dir, ideas_dir, home, today, push=True):
    day = dt.date.fromisoformat(today)
    this_month, last_month, next_first = month_window(day)
    sessions_path = os.path.join(ideas_dir, "audit", "sessions.jsonl")
    sessions, read = refresh_sessions(projects_dir, load_jsonl(sessions_path), today)
    write_jsonl(sessions_path, sessions)

    growth_path = os.path.join(ideas_dir, "audit", "growth.jsonl")
    snapshots = [g for g in load_jsonl(growth_path) if g.get("date") != today]
    previous = snapshots[-1] if snapshots else None
    snapshot = growth_snapshot(home, today)
    write_jsonl(growth_path, snapshots + [snapshot])
    last_month_snapshot = next((g for g in reversed(snapshots) if g["date"][:7] <= last_month), None)

    baseline_path = os.path.join(ideas_dir, "audit", "v1-baseline.json")
    v1_column = {}
    if os.path.isfile(baseline_path):
        with open(baseline_path, encoding="utf-8") as fh:
            v1_column = json.load(fh).get("column") or {}
    speeds = mvp_speeds(ideas_dir)
    this_cells, _ = month_cells(sessions, this_month, snapshot, previous, speeds)
    last_cells, _ = month_cells(sessions, last_month, last_month_snapshot or snapshot, None, speeds)
    props = proposals(sessions, this_month, last_month, snapshot, previous)
    page_path = os.path.join(ideas_dir, "pages", f"{next_first}-audit.md")
    os.makedirs(os.path.dirname(page_path), exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as fh:
        fh.write(render_page(today, this_month, last_month, this_cells, last_cells, v1_column, props, len(sessions), read))
    result = commit_and_push(ideas_dir, today, push) if os.path.isdir(os.path.join(ideas_dir, ".git")) else "no git repo"
    return {"sessions": len(sessions), "read": read, "page": page_path, "git": result, "proposals": props}


def main(argv=None):
    home = os.path.expanduser("~/.claude")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", default=os.path.join(home, "projects"))
    ap.add_argument("--ideas", default=os.path.expanduser("~/code/ideas"))
    ap.add_argument("--home", default=home)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.ideas):
        print(f"Refused: no ideas repo at {args.ideas}", file=sys.stderr)
        return 2
    out = run(args.projects, args.ideas, args.home, args.today, push=not args.no_push)
    print(f"{out['read']} sessions read, {out['sessions']} stored. Page {out['page']}. Git: {out['git']}.")
    for p in out["proposals"]:
        print(f"- {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
