#!/usr/bin/env python3
"""Print where a run's wall clock went, per step, from its own transcript.

The human asked for this on 2026-08-26, in the daily brief, after a nine-to-ten issue run
took more than fourteen hours and nothing could say which step ate it. In their words: "is
there any measurement we have that says what took how much time and where".

There was not. The run ledger's Status table carries per-attempt stamps, but they are
the runner's estimates of elapsed time, written turn by turn, and on run
`416-419-421-d167e0` they drifted 68 minutes by the last issue. `check_commit_order.py`
caught it by refusing two rows. Only the commit stamps in that table are measured, and a
commit time cannot tell an implementer from a gate.

So this reads the transcript instead, for the same reason `orchestrator_cost.py` does:
a table needs someone to write a row after every run, and a transcript is written
whether anyone remembers or not.

    python3 run_timings.py <transcript.jsonl>
    python3 run_timings.py <transcript.jsonl> --deep

`--deep` opens the `subagents/` directory beside the transcript and reads every step's own
transcript, so it can say what a gate or an implementer spent its time ON. The human asked on
2026-08-26 whether instrumenting the gates would cost them time. It costs nothing: no gate
brief changes, because every subagent already writes one of these whether anyone reads it
or not.

WHAT IT COSTS THE RUN: nothing. It runs after the run, over a file the harness already
wrote. It spawns no agent, reads no database and touches no repository.

WHAT IT MEASURES, and the one thing it deliberately does not:

  * Per tool call, wall clock from the `tool_use` block to its `tool_result`. For an
    `Agent` call that is the subagent's whole life, which is what a step costs.
  * The union of every Agent span, against the run's own first and last timestamp. The
    difference is time with NO subagent running: the main thread reading, writing
    `run.md`, `run-journal.md`, `merge-briefing.md`, register rows and the primer.
  * Sidechain lines are skipped, so a subagent's own tool calls are not double-counted
    against the step that spawned it.

  * A BACKGROUNDED Bash call is NOT its real duration and this script cannot fix that.
    Backgrounding returns immediately, so the tool call reads as instant while the work
    runs on. On `416-419-421-d167e0` the citation passes showed 50m 47s, 31m 32s and
    30m 39s on the background-task panel while every Bash call in the run summed to 26
    minutes. The cost of a backgrounded command appears as the wall clock of whatever
    later waited for it. Read the "nobody running" figure and the Agent spans with that
    in mind, and do not report a Bash total as though it were the whole story.
"""

import argparse
import collections
import datetime
import importlib.util
import json
import os
import re
import sys


def _run_session():
    """`run_session.py` owns the road from a batch id to a transcript."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "run_session.py")
    existing = sys.modules.get("run_session")
    if existing is not None and os.path.realpath(
            getattr(existing, "__file__", "") or "") == os.path.realpath(path):
        return existing  # One instance per file; two would diverge on any state.
    spec = importlib.util.spec_from_file_location("run_session", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_session"] = module
    spec.loader.exec_module(module)
    return module


def parse(stamp):
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def label(block):
    payload = block.get("input") or {}
    for key in ("description", "subagent_type", "command"):
        value = payload.get(key)
        if value:
            return str(value).splitlines()[0][:70]
    return ""


def read(path):
    pending, calls, spans, labelled = {}, [], [], []
    first = last = None
    for line in open(path):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        stamp = entry.get("timestamp")
        if stamp:
            moment = parse(stamp)
            first = moment if first is None or moment < first else first
            last = moment if last is None or moment > last else last
        if entry.get("isSidechain"):
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                pending[block["id"]] = (block.get("name"), label(block), stamp)
            elif block.get("type") == "tool_result":
                found = pending.pop(block.get("tool_use_id"), None)
                if not found or not stamp:
                    continue
                name, text, started = found
                if not started:
                    continue
                seconds = (parse(stamp) - parse(started)).total_seconds()
                calls.append((seconds, name, text))
                if name == "Agent":
                    spans.append([parse(started), parse(stamp)])
                    labelled.append((parse(started), parse(stamp), text))
    return calls, spans, first, last, labelled


def deep(path):
    """Break each step's own transcript into tool time against thinking time.

    The split is the finding this mode exists for. On run `416-419-421-d167e0` the gates
    spent 22% of their wall clock inside tool calls and 78% reading and writing, and the
    implementers split 25/75. A step that is 78% model time is not slow because a command
    is slow, so tuning commands will not move it. Read that number before proposing a fix.
    """
    import glob
    import os

    folder = os.path.join(os.path.dirname(path),
                          os.path.basename(path).rsplit(".jsonl", 1)[0], "subagents")
    if not os.path.isdir(folder):
        print(f"\nno subagents directory beside {os.path.basename(path)} — skipping --deep")
        return
    groups = {}
    for meta_path in sorted(glob.glob(os.path.join(folder, "*.meta.json"))):
        try:
            blob = json.dumps(json.load(open(meta_path))).lower()
        except (ValueError, OSError):
            continue
        kind = next((w for w in ("gate", "implement", "correction", "coherence", "promotion")
                     if w in blob), "other")
        body = meta_path.replace(".meta.json", ".jsonl")
        if not os.path.exists(body):
            continue
        pending, tools = {}, collections.Counter()
        first = last = None
        for line in open(body):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            stamp = entry.get("timestamp")
            if stamp:
                moment = parse(stamp)
                first = moment if first is None else first
                last = moment
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    pending[block["id"]] = (block.get("name"), stamp)
                elif block.get("type") == "tool_result":
                    found = pending.pop(block.get("tool_use_id"), None)
                    if found and found[1] and stamp:
                        tools[found[0]] += (parse(stamp) - parse(found[1])).total_seconds()
        wall = (last - first).total_seconds() if first and last else 0.0
        slot = groups.setdefault(kind, {"n": 0, "wall": 0.0, "tools": collections.Counter()})
        slot["n"] += 1
        slot["wall"] += wall
        slot["tools"].update(tools)

    print("\ninside each step  (tool time against model time)")
    for kind, slot in sorted(groups.items(), key=lambda kv: -kv[1]["wall"]):
        tool = sum(slot["tools"].values())
        if not slot["wall"]:
            continue
        share = tool / slot["wall"] * 100
        print(f"\n  {kind}: {slot['n']} step(s), {slot['wall'] / 3600:.2f} h wall clock")
        print(f"    {tool / 3600:.2f} h in tool calls ({share:.0f}%), "
              f"{(slot['wall'] - tool) / 3600:.2f} h reading and writing ({100 - share:.0f}%)")
        for name, seconds in slot["tools"].most_common(4):
            print(f"      {seconds / 60:7.1f}m  {name}")


# `901`, `99b`, `413a` — the run's own issue-id shape. Same pattern as
# ~/.claude/hooks/run-issues-parallel-gates.py, deliberately, because that guard
# and this report must agree on what a pair is.
ISSUE_ID = re.compile(r"\b(\d{2,4}[a-z]?)\b")

# `attempt 1`, `**attempt 2**`. FIRST match only, for the reason the hook gives:
# an attempt-2 label may go on to mention attempt 1.
ATTEMPT = re.compile(r"\battempt\s*\**\s*(\d{1,2})\b", re.IGNORECASE)


def gate_half(text):
    """Which half of a round this gate is: "verify", "review", or "" if neither.

    A round is one verify and one review. Two verify steps under one key are two
    ATTEMPTS whose labels lost their attempt marker, not a serialised pair —
    comparing them reported issue 349 as following itself on run `batch-44d0a8`.
    """
    low = (text or "").lower()
    if "verify" in low:
        return "verify"
    if "review" in low:
        return "review"
    return ""


def pair_key(text):
    """The pair a gate belongs to: `<issue>@<attempt>`, or "" when unreadable.

    A label naming no issue returns "" and is not reported. That is the safe
    direction — this function can only lose a true report, never manufacture a
    false one, which is the whole reason it exists.
    """
    issue = ISSUE_ID.search(text or "")
    if not issue:
        return ""
    attempt = ATTEMPT.search(text or "")
    return f"{issue.group(1)}@{attempt.group(1) if attempt else '?'}"


def serial_gates(labelled):
    """Flag gate pairs that ran one after the other instead of together.

    `run-issues/SKILL.md` says to spawn both gates in one message, and two foreground Agent
    calls in one message run concurrently. Two messages do not. Nothing refuses a second
    message, so this reports it — the class below a guard, and better than nobody noticing.

    The human caught it themselves on 2026-08-27 by reading the background-task panel: run
    `99b-99e-6e11ba` spawned each review gate one to two minutes AFTER its verify gate
    returned, while run `416-419-421-d167e0` the day before spawned all thirteen pairs within
    30 seconds of each other. The cost is the shorter gate's whole runtime, every round —
    roughly three to four hours on a ten-issue run.

    **Corrected 2026-09-04, and the old shape reported a fault that did not exist.**
    It sorted every gate by time and compared each to the PREVIOUS gate in that order,
    calling them a pair whenever the second started within 20 minutes of the first ending.
    Proximity in time was its only test. Measured on run `batch-44d0a8` it printed
    "3 ran one after the other / ROUGHLY 39 MINUTES", and all three were false:

        11.9m  Verify gate issue 312d     after  Review gate 312b attempt 2
        12.6m  Verify gate 250 attempt 2  after  Review gate issue 250
        14.7m  Verify gate 392 attempt 2  after  Review gate issue 392

    The first pairs two DIFFERENT ISSUES. The other two pair attempt 2 against attempt 1,
    which can never overlap, because attempt 2 does not exist until attempt 1's gates have
    returned a rejection. True cost that run: zero. The runner had obeyed on every real pair.

    That false reading reached the merge briefing, became a `[rule, nothing live]` proposal
    to build a new refusal, and reached the human in the daily brief of 2026-09-03.

    `~/.claude/hooks/run-issues-parallel-gates.py` had this identical defect and was fixed on
    2026-08-30 by filing state per `<issue>@<attempt>`. This is the same correction, one tool
    later. Gates are now grouped by that key, so only two halves of the same round are ever
    compared, and a label naming no issue is dropped rather than guessed at.
    """
    gates = sorted((s, e, text) for s, e, text in labelled if "gate" in text.lower())
    if not gates:
        return

    rounds = {}
    unreadable = 0
    for start, end, text in gates:
        key, half = pair_key(text), gate_half(text)
        if not key or not half:
            unreadable += 1
            continue
        rounds.setdefault(key, {}).setdefault(half, []).append((start, end, text))

    serial, parallel = [], 0
    for key in sorted(rounds):
        halves = rounds[key]
        # A round is one verify and one review. A key holding only one half, or two
        # of the same half, is not a pair: the second case is two attempts whose
        # labels lost their marker, and comparing them makes an issue follow itself.
        if "verify" not in halves or "review" not in halves:
            continue
        first, second = sorted([min(halves["verify"]), min(halves["review"])])
        (first_start, first_end, first_text), (start, end, text) = first, second
        if start >= first_end:
            serial.append((first_text, text, min(end - start, first_end - first_start).total_seconds()))
        else:
            parallel += 1

    print(f"\ngate concurrency: {parallel} pair(s) overlapped, {len(serial)} ran one after the other")
    if unreadable:
        print(f"  {unreadable} gate step(s) named no issue and were not graded.")
    if serial:
        wasted = sum(row[2] for row in serial)
        print(f"  SERIAL GATES COST THIS RUN ROUGHLY {wasted / 60:.0f} MINUTES.")
        print("  SKILL.md says spawn both gates in ONE message; two messages do not run in parallel.")
        for first_text, second_text, cost in serial:
            print(f"    {cost / 60:5.1f}m  {second_text[:40]}  followed  {first_text[:40]}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", nargs="?", default=None,
                        help="a transcript path; the finale passes one")
    parser.add_argument("--batch", default=None,
                        help="a run or hunt batch id; the transcript is found "
                             "from that batch's ledger (ticket 39, ruling 12)")
    parser.add_argument("--repo", default=None,
                        help="checkout whose worktrees hold the ledger")
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args(argv)

    if bool(args.transcript) == bool(args.batch):
        parser.error("give exactly one of <transcript> or --batch")

    path = args.transcript
    if args.batch:
        session = _run_session()
        found, why = session.sessions_for_batch(args.batch, repo=args.repo)
        if not found:
            sys.exit(f"no transcript for batch `{args.batch}`: {why}")
        # The newest session. A resumed run has two, and the clock this reports
        # is one session's own span; adding two spans would count the gap
        # between them as run time.
        path = found[-1]
        print(f"batch `{args.batch}`, transcript `{path}`"
              + (f"  (resumed: {len(found)} sessions, newest read)"
                 if len(found) > 1 else ""))

    calls, spans, first, last, spans_by_label = read(path)
    if not calls or first is None:
        sys.exit("no completed tool calls with timestamps in that transcript")

    wall = (last - first).total_seconds()
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    busy = sum((end - start).total_seconds() for start, end in merged)

    print(f"wall clock          {wall / 3600:6.2f} h   "
          f"{first.strftime('%Y-%m-%d %H:%M')} to {last.strftime('%H:%M')} UTC")
    print(f"a subagent running  {busy / 3600:6.2f} h   {busy / wall * 100:3.0f}%")
    idle = wall - busy
    print(f"nobody running      {idle / 3600:6.2f} h   "
          f"{idle / wall * 100:3.0f}%   (the main thread's own turns)")

    # **The share has no meaning without its denominator, and reading one without
    # it produced a false regression on 2026-08-31.** Run `batch-88624c` read 17%
    # against 9% on 2026-08-26 and looked like the runner had got slower. Nothing
    # had: idle sat between 1.48 and 1.64 hours on all four runs measured, a
    # ten-minute spread, while agent time halved. Per issue is the figure that
    # holds still, so this prints it beside the share.
    issues = {found.group(1).lower()
              for _, _, text in spans_by_label
              for found in [re.search(r"\bissue\s+(\S+)", text or "")] if found}
    if issues:
        print(f"                             {idle / 60 / len(issues):5.1f} min per issue, "
              f"over {len(issues)} issue(s). Compare THIS across runs, not the share.")

    print("\nlongest steps")
    for seconds, name, text in sorted(calls, reverse=True)[:20]:
        print(f"  {seconds / 60:7.1f}m  {name:<9} {text}")

    totals = collections.Counter()
    for seconds, name, _ in calls:
        totals[name] += seconds
    print("\nby tool  (a backgrounded Bash call reads as instant; see the header)")
    for name, seconds in totals.most_common(8):
        print(f"  {seconds / 3600:6.2f} h  {name}")

    serial_gates(spans_by_label)

    agents = [c for c in calls if c[1] == "Agent"]
    if agents:
        kinds = collections.Counter()
        for seconds, _, text in agents:
            word = text.split()[0].lower() if text else "other"
            kinds[word] += seconds
        print("\nagent time by first word of the step label")
        for word, seconds in kinds.most_common(10):
            print(f"  {seconds / 3600:6.2f} h  {word}")

    if args.batch:
        session = _run_session()
        rows = session.spawn_rows([path])
        print("\n\nper role, with the model column ticket 39 ruling 15 asks for\n")
        print(session.render_roles(rows))
        print("\n\none row per subagent\n")
        print(session.render_spawns(rows))

    if args.deep:
        deep(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
