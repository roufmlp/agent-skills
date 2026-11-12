#!/usr/bin/env python3
"""The rulings of a feature: what was decided while a run was stopped, by whom,
and whether Abdul has confirmed it.

    python3 ~/.claude/skills/workflow/lib/rulings.py ruler <class>
    python3 ~/.claude/skills/workflow/lib/rulings.py record <feature> --tree <feature worktree> --note <nn> \\
        --kind <kind> --who <who> --question <text> --words <text> --touches <none|nn,nn> --undo <text>
    python3 ~/.claude/skills/workflow/lib/rulings.py wait <feature> --tree <feature worktree> --note <nn> [--why <text>]
    python3 ~/.claude/skills/workflow/lib/rulings.py list <feature> --tree <feature worktree>
    python3 ~/.claude/skills/workflow/lib/rulings.py answer <feature> --tree <feature worktree> --words <text> \\
        (--all | --note <nn> (--confirmed | --overturned --fix <nn>))

A run that stops on a question no longer waits for an interview. The session
that started it sends the question to Abdul's phone (`wait` records when) and
waits RULING_WAIT_SECONDS. His answer rules when it comes in time; otherwise
`ruler_when_unanswered` says who does. The session then changes the note
inside the ruling, records it here and starts the run again. Every ruling he
did not make himself is shown to him once, before the merge into local main.

## The part of the plan this reads

`changes/<feature>/plan.md` carries the rulings under `## Rulings`, above the
`Approved:` lines. One entry per ruled note, one line of each name per entry:

    - [<kind>] <nn>: <the question, in plain words>
      Ruled: <date>, <who>, "<the words of the ruling>"
      Touches: <none, or the numbers of the other notes the ruling changes>
      Undo: <what reversing it costs>
      Confirmed: <date>[, "<his words>"]
      Overturned: <date>, "<his words>"
      Fix: <the number of the fix note that undoes an overturned ruling>

`<nn>` is a note's number, or `final` for a question of the final check, whose
row in the report is `final`. `<kind>` is `none`, a risk class (`money`,
`access`, `migration`, `data leaving`), `re-arm` (the one automatic second try
of a note that failed three strikes), `correction` (the note checker corrected
the note at strike two) or `follows <nn>` (a note the ruling on `<nn>`
touched, or the fix note written for it). `<who>` is `default`, `panel`, or
the first word of `git config user.name`, which is how the page names Abdul.

## What a command refuses

`record` reads the note's row in the report and the run's own record of the
stop, `<git dir>/build-feature/<feature>/stops.jsonl`, which `feature_run.py
roles` writes from the agents' transcripts:

- the class is the one the agent typed. `--kind` must equal it; a stop with
  no class on record is a risk class, and Abdul names it;
- a `stopped:` question takes no ruling before `wait` recorded that it went
  out, and none by `default` before that time plus RULING_WAIT_SECONDS;
- a `failed` row takes `re-arm` from a default, a `waiting:` row and a cut
  take a ruling from Abdul alone, a `merged` row takes none (a merged note
  takes a fix note), and a row that did not stop takes none;
- `--kind correction` is by `default`, for a correction the report's Decide
  part lists and the plan does not yet carry;
- a ruling or an answer in Abdul's name carries words he typed: `--words`
  must occur in a message a person typed in this session's transcript
  (`CLAUDE_CODE_SESSION_ID` names it), after the question went out. With no
  such session nobody rules in his name.

## What the page refuses

`read` places every line of the part or reports it; `faults` then refuses:

- an entry with no `Ruled:` line, or with no `Touches:` line;
- a kind or a who it does not know;
- a ruling Abdul did not make on a risk class, and a follow-on whose who is
  not the who of the ruling it follows;
- `Touches:` naming a note that is not in the feature, or a touched note with
  no `follows` entry of its own; each touched note that is merged needs a
  fix note of its own, with a `follows` entry;
- `follows <nn>` when `<nn>` has no ruling above it;
- a second `re-arm` for one note, and more than MAX_DEFAULT_RULINGS rulings
  by default on one note: the next question on it waits for Abdul;
- both answers on one entry, or `Overturned:` whose `Fix:` names no fix note
  with an entry `[follows <nn>]`.

`open_entries` is the gate before local main: each ruling Abdul did not make
that has no answer. A follow-on is free only when he made the ruling it
follows, that ruling's `Touches:` line names it, and it changed no test he
approved. A risk-class line counts as confirmed only when the line carries
his words. An overturned line closes on a fix note that was not merged when
he answered. `plan_check.py`, `feature_run.py args` and the hooks
(`note_check.py merge` and `note_check.py ref`) all call `faults` and
`open_entries`, with the same person.

Exit 0 on success, 3 with `REFUSED: <why>`.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

# How long the starting session waits for Abdul's answer before the default
# rules. The one place this number lives: `ruler` prints it and
# `feature_run.py args` passes it on.
RULING_WAIT_SECONDS = 900
RISK_CLASSES = ("money", "access", "migration", "data leaving")
KINDS = ("none", *RISK_CLASSES, "re-arm", "correction")
# The kinds a default rules. Every other class waits, one nobody named included.
DEFAULT_RULED = ("none", "re-arm", "correction")
RULERS = ("default", "panel")
# The rulings by default one note's questions get, the final check's included
# (its number is `final`). The next question waits for Abdul, so a note that
# stops, takes a default and stops again has an end, and so has the cycle of
# fix notes a final check asks for.
MAX_DEFAULT_RULINGS = 2
FINAL = "final"
# A stop whose class the row itself fixes as `none`: the session's pre-run
# stop, and a final-check finding that needs a fix note.
PLAIN_STOPS = ("done check passes before the work", "fix note needed:")
# Rows a run starts again by itself; none is a question (`plan_check.RESTART_STATES`).
NOT_A_QUESTION = re.compile(r"^stopped: (API errors|[a-z-]+ returned no result|worktree:|tooling:)")
STOPS = "stops.jsonl"  # the run's own record of each typed stop, written from the agents' transcripts
SENT = "sent.json"     # when each question went to Abdul
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
SESSION = "CLAUDE_CODE_SESSION_ID"
HEADING = "## Rulings"
REFUSED = 3
CHANGES = "changes"

NUMBER = r"(?:\d+|final)"
ENTRY = re.compile(rf"^- \[([^\]]+)\]\s*({NUMBER}):\s*(\S.*)$")
FOLLOWS = re.compile(rf"^follows ({NUMBER})$")
DECIDED = re.compile(rf"^(?:[-*]\s*)?({NUMBER}):\s*\[([^\]]*)\]\s*(.*)$")
DATE = r"\d{4}-\d{2}-\d{2}"
RULED = re.compile(rf'^Ruled:\s*({DATE}),\s*([^,"]+?),\s*"(.+)"$')
CONFIRMED = re.compile(rf'^Confirmed:\s*({DATE})(?:,\s*"(.+)")?$')
OVERTURNED = re.compile(rf'^Overturned:\s*({DATE}),\s*"(.+)"$')
SUB_LINES = ("Ruled:", "Touches:", "Undo:", "Confirmed:", "Overturned:", "Fix:")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


class Refusal(Exception):
    pass


def ruler_when_unanswered(kind: str) -> str:
    """Who rules a question Abdul did not answer inside RULING_WAIT_SECONDS.

    `default`: the agent's written default rules. `wait`: nobody does; the
    note waits for him and the other notes continue. This is the one place
    that answers it. A panel will rule a risk-class question here once its
    cost is measured; until then every class this function does not know
    waits, a new one included."""
    if kind in DEFAULT_RULED:
        return "default"
    return "wait"


def now() -> float:
    return time.time()


def plain(text: str) -> str:
    """One line, as the run script's `oneLine` makes it: what two copies of a
    question are compared by."""
    return " ".join(re.sub(r"[\r\n|]+", " ", str(text or "")).split())


def person(tree) -> str | None:
    """How the plan page names Abdul: the first word of `git config user.name`."""
    done = subprocess.run(["git", "-C", str(tree), "config", "user.name"], capture_output=True, text=True)
    words = done.stdout.split()
    return words[0] if words else None


# ── Reading the part ─────────────────────────────────────────────────────────

def split(text: str) -> tuple[list[str], list[tuple[int, str]]]:
    """The plan's lines outside `## Rulings`, and the part's own lines with
    their line numbers. The part ends at the next heading or `Approved:` line."""
    outside, part, inside = [], [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip() == HEADING:
            inside = True
            continue
        if inside and (line.startswith("## ") or line.startswith("Approved:")):
            inside = False
        (part if inside else outside).append((number, line))
    return [line for _, line in outside], part


def outside(text: str) -> str:
    """The plan without its rulings and without blank lines: what Abdul
    approved. A ruling written after the approval leaves this text as it was."""
    return "\n".join(line for line in split(text)[0] if line.strip())


def read(text: str) -> tuple[list[dict], list[str]]:
    """Every entry of the part, and a fault for each line it cannot place."""
    lines, part = split(text)
    entries, faults, entry, seen = [], [], None, set()
    for line in lines:
        if line.strip().startswith(SUB_LINES[:2]):
            faults.append(f"`{line.strip()}` is outside `{HEADING}`. A ruling is an entry of that part.")
    for number, raw in part:
        line = raw.strip()
        if not line:
            continue
        match = ENTRY.match(raw)
        if match:
            kind = match.group(1).strip()
            follows = FOLLOWS.match(kind)
            entry = {"kind": kind, "follows": follows.group(1) if follows else None,
                     "number": match.group(2), "question": match.group(3).strip(), "line": number,
                     "date": None, "who": None, "words": None, "touches": None, "undo": None,
                     "confirmed": None, "overturned": None, "fix": None}
            entries.append(entry)
            seen = set()
            continue
        name = line.split(":", 1)[0]
        if entry is not None and name in seen:
            # A second `Ruled:` line would put another name on the ruling.
            faults.append(f"line {number} of `{HEADING}`: the entry has a `{name}:` line already. One of each.")
            continue
        seen.add(name)
        placed = entry is not None and raw.startswith(" ") and place(entry, line)
        if not placed:
            faults.append(f"line {number} of `{HEADING}` is not a ruling line: `{line}`.")
    return entries, faults


def place(entry: dict, line: str) -> bool:
    """Put one sub-line into its entry; False when it is none of them."""
    if line.startswith("Ruled:"):
        match = RULED.match(line)
        if match:
            entry["date"], entry["who"], entry["words"] = (g.strip() for g in match.groups())
        return bool(match)
    if line.startswith("Touches:"):
        value = line[len("Touches:"):].strip()
        entry["touches"] = [] if value.lower() == "none" else [t.strip() for t in value.split(",") if t.strip()]
        return bool(value)
    if line.startswith("Undo:"):
        entry["undo"] = line[len("Undo:"):].strip()
        return True
    if line.startswith("Confirmed:"):
        match = CONFIRMED.match(line)
        if match:
            entry["confirmed"] = {"date": match.group(1), "words": match.group(2)}
        return bool(match)
    if line.startswith("Overturned:"):
        match = OVERTURNED.match(line)
        if match:
            entry["overturned"] = {"date": match.group(1), "words": match.group(2)}
        return bool(match)
    if line.startswith("Fix:"):
        entry["fix"] = line[len("Fix:"):].strip()
        return bool(entry["fix"])
    return False


# ── What refuses ─────────────────────────────────────────────────────────────

def parent(entry: dict, entries: list[dict]) -> dict | None:
    """The ruling a follow-on follows: the last one on that note written above it."""
    above = [e for e in entries if e["number"] == entry["follows"] and not e["follows"] and e["line"] < entry["line"]]
    return above[-1] if above else None


def class_of(entry: dict, entries: list[dict]) -> str:
    """An entry's class; a follow-on takes the class of the ruling it follows."""
    seen = set()
    while entry["follows"] and entry["number"] not in seen:
        seen.add(entry["number"])
        first = parent(entry, entries) or next(
            (e for e in entries if e["number"] == entry["follows"] and not e["follows"]), None)
        if first is None:
            break
        entry = first
    return entry["kind"]


def is_risk(entry: dict, entries: list[dict]) -> bool:
    """A class nobody knows is a risk class: only the kinds a default rules are not."""
    return class_of(entry, entries) not in DEFAULT_RULED


def by_person(entry: dict, who: str | None) -> bool:
    return who is not None and entry["who"] == who


def faults(entries: list[dict], numbers: set[str], who: str | None, merged=frozenset()) -> list[str]:
    """Every reason the rulings do not hold together. `numbers` are the notes
    of the feature, `who` is `person()`, `merged` the notes already merged."""
    found = []
    ruled = {e["number"] for e in entries if not e["follows"]}
    rearmed, defaults = set(), collections.Counter()
    for e in entries:
        name = f"ruling [{e['kind']}] {e['number']}"
        if e["kind"] not in KINDS and not e["follows"]:
            found.append(f"{name}: [{e['kind']}] is not a kind. The kinds are "
                         f"{', '.join(KINDS)} and `follows <nn>`.")
        if e["follows"] and e["follows"] not in ruled:
            found.append(f"{name}: `follows {e['follows']}` names a note with no ruling of its own.")
        first = parent(e, entries) if e["follows"] else None
        if e["who"] is None:
            found.append(f"{name} has no `Ruled:` line: `Ruled: <date>, <who>, \"<the words>\"`.")
        elif e["who"] not in RULERS and e["who"] != who:
            found.append(f"{name}: `{e['who']}` is not `default`, `panel` or `{who}`.")
        elif e["who"] in RULERS:
            cls = class_of(e, entries)
            road = ruler_when_unanswered(cls)
            if road != e["who"]:
                found.append(f"{name}: `{e['who']}` may not rule a [{cls}] question. "
                             + (f"It waits for {who}." if road == "wait" else f"The `{road}` rules it."))
        if first is not None and None not in (e["who"], first["who"]) and e["who"] != first["who"]:
            found.append(f"{name}: a follow-on carries the who of the ruling it follows, `{first['who']}`.")
        if e["touches"] is None:
            found.append(f"{name} has no `Touches:` line. One reader names the notes each ruling "
                         f"touches: `Touches: none` or `Touches: 06, 09`.")
        touched = e["touches"] or []
        own = {f["number"] for f in entries if f["follows"] == e["number"]}
        fix_notes = [f for f in entries if f["follows"] == e["number"] and f["number"] not in touched]
        need_fix = []
        for number in touched:
            if number not in numbers or number == e["number"]:
                found.append(f"{name}: `Touches: {number}` names no other note of the feature.")
            elif number in own:
                continue
            elif number in merged:
                need_fix.append(number)
            else:
                found.append(f"{name}: note {number} is touched and has no entry "
                             f"`[follows {e['number']}] {number}` of its own.")
        if len(need_fix) > len(fix_notes):
            found.append(f"{name}: note(s) {', '.join(need_fix)} are merged, and a merged note is never edited. "
                         f"Each needs a fix note of its own with an entry `[follows {e['number']}]`; "
                         f"the plan has {len(fix_notes)}.")
        if e["kind"] == "re-arm":
            if e["number"] in rearmed:
                found.append(f"{name}: a note gets one re-arm. Its second failure waits for {who}.")
            rearmed.add(e["number"])
        if e["kind"] == "none" and e["who"] in RULERS:
            defaults[e["number"]] += 1
            if defaults[e["number"]] == MAX_DEFAULT_RULINGS + 1:
                found.append(f"{name}: {MAX_DEFAULT_RULINGS} questions of {e['number']} took a default already. "
                             f"The next one waits for {who}.")
        if e["confirmed"] and e["overturned"]:
            found.append(f"{name} carries both `Confirmed:` and `Overturned:`.")
        if e["overturned"]:
            if not e["fix"]:
                found.append(f"{name} is overturned and has no `Fix:` line naming its fix note.")
            elif e["fix"] not in numbers:
                found.append(f"{name}: `Fix: {e['fix']}` names no note of the feature.")
            elif not any(f["number"] == e["fix"] and f["follows"] == e["number"] for f in entries):
                found.append(f"{name}: `Fix: {e['fix']}` names a note with no entry `[follows {e['number']}] "
                             f"{e['fix']}`. An overturned ruling closes on a new fix note, never on an old note.")
    return found


def needs_answer(entry: dict, entries: list[dict], who: str | None, forced=frozenset()) -> bool:
    """Abdul answers everything he did not rule himself. A follow-on is free
    only when he made the ruling it follows and that ruling's `Touches:` line
    names it; `forced` holds the follow-ons that changed a test he approved,
    and those are never free."""
    if not entry["follows"]:
        return not by_person(entry, who)
    first = parent(entry, entries)
    return not (first is not None and by_person(first, who) and entry["number"] in (first["touches"] or [])
                and entry["number"] not in forced)


def answered(entry: dict, entries: list[dict]) -> bool:
    if entry["overturned"]:
        return bool(entry["fix"]) and any(f["number"] == entry["fix"] and f["follows"] == entry["number"]
                                          for f in entries)
    if not entry["confirmed"]:
        return False
    return bool(entry["confirmed"]["words"]) or not is_risk(entry, entries)


def open_entries(entries: list[dict], who: str | None = None, forced=frozenset()) -> list[dict]:
    """The gate before local main: each ruling that still waits for his answer.
    With no `who`, nobody is the person and every ruling waits."""
    return [e for e in entries if needs_answer(e, entries, who, forced) and not answered(e, entries)]


def rearmed(entries: list[dict]) -> set[str]:
    return {e["number"] for e in entries if e["kind"] == "re-arm"}


def new_since(now: list[dict], then: list[dict]) -> set[str]:
    """The notes with a ruling the older page does not carry."""
    old = {(e["number"], e["kind"], e["date"], e["who"], e["words"]) for e in then}
    return {e["number"] for e in now
            if (e["number"], e["kind"], e["date"], e["who"], e["words"]) not in old}


def away_line(entry: dict, entries: list[dict]) -> str:
    cls = class_of(entry, entries)
    head = f"**{cls.upper()}** " if cls in RISK_CLASSES else ""
    return (f"{head}{entry['number']}: {entry['question']} Road taken: \"{entry['words']}\". "
            f"Ruled by {entry['who']} on {entry['date']}. "
            f"Touched: {', '.join(entry['touches'] or []) or 'none'}. "
            f"Undo: {entry['undo'] or 'not stated'}.")


def away_lines(entries: list[dict], who: str | None, forced=frozenset(), open_only=False) -> list[str]:
    """The report's "Ruled while you were away" lines, risk classes first."""
    shown = [e for e in entries if needs_answer(e, entries, who, forced)
             and not (open_only and answered(e, entries))]
    shown.sort(key=lambda e: (not is_risk(e, entries), e["line"]))
    return [away_line(e, entries) for e in shown]


# ── Writing ──────────────────────────────────────────────────────────────────

def entry_text(number, kind, date, who, question, words, touches, undo) -> list[str]:
    return [f"- [{kind}] {number}: {question}",
            f'  Ruled: {date}, {who}, "{words}"',
            f"  Touches: {', '.join(touches) if touches else 'none'}",
            f"  Undo: {undo}"]


def with_entry(text: str, lines: list[str]) -> str:
    """The plan with one more entry at the end of its rulings part, which is
    made above the first `Approved:` line when the page has none."""
    rows = text.splitlines()
    start = next((i for i, r in enumerate(rows) if r.strip() == HEADING), None)
    if start is None:
        start = end = next((i for i, r in enumerate(rows) if r.startswith("Approved:")), len(rows))
    else:
        end = next((i for i in range(start + 1, len(rows))
                    if rows[i].startswith("## ") or rows[i].startswith("Approved:")), len(rows))
    before = rows[:start]
    while before and not before[-1].strip():
        before.pop()
    body = [r for r in rows[start + 1:end] if r.strip()]
    return "\n".join(before + ["", HEADING, ""] + body + lines + [""] + rows[end:]) + "\n"


def with_sub_lines(text: str, entry: dict, lines: list[str]) -> str:
    """The plan with `lines` added at the end of one entry."""
    rows = text.splitlines()
    at = entry["line"]  # the index after the entry's first line
    while at < len(rows) and rows[at].startswith(" ") and rows[at].strip():
        at += 1
    rows[at:at] = [f"  {line}" for line in lines]
    return "\n".join(rows) + "\n"


def with_row(text: str, number: str, state: str, strikes: int | None = None) -> tuple[str, bool]:
    """The report with one note row's state set, and its strikes when given."""
    rows, columns, changed = text.splitlines(), None, False
    for i, line in enumerate(rows):
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
            continue
        if not columns or cells[0] != number:
            continue
        cells[1] = state
        if strikes is not None and "Strikes" in columns and columns.index("Strikes") < len(cells):
            cells[columns.index("Strikes")] = str(strikes)
        rows[i] = "| " + " | ".join(cells) + " |"
        changed = True
    return "\n".join(rows) + "\n", changed


def note_numbers(folder: pathlib.Path) -> set[str]:
    found = set()
    for path in folder.glob("*.md"):
        match = re.match(r"^(\d+)(?:[-_].*)?\.md$", path.name)
        if match:
            found.add(match.group(1))
    return found


def report_rows(report_text: str) -> dict[str, str]:
    """Each row of the report's notes table: number to state."""
    found, columns = {}, None
    for line in report_text.splitlines():
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
        elif columns and len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: "):
            found[cells[0]] = cells[1]
    return found


def merged_notes(report_text: str) -> set[str]:
    return {number for number, state in report_rows(report_text).items() if state.startswith("merged")}


def decided(report_text: str) -> list[tuple[str, str, str]]:
    """The lines of the report's `## Decide` part: (number, class, the rest)."""
    found, inside = [], False
    for line in report_text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Decide"
            continue
        match = DECIDED.match(line.strip()) if inside else None
        if match:
            found.append((match.group(1), match.group(2).strip(), match.group(3).strip()))
    return found


def corrections(report_text: str) -> collections.Counter:
    """How many times the note checker corrected each note, from the report."""
    return collections.Counter(number for number, cls, _ in decided(report_text) if cls == "correction")


def uncorrected(entries: list[dict], report_text: str) -> list[str]:
    """The notes with a correction the plan carries no `[correction]` entry for."""
    have = collections.Counter(e["number"] for e in entries if e["kind"] == "correction")
    return sorted(number for number, count in corrections(report_text).items() if count > have[number])


# ── His words ────────────────────────────────────────────────────────────────

def stamp(value) -> float:
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def human_messages(since: float = 0.0) -> list[str]:
    """What Abdul typed in this session, from its transcript: the `user`
    records whose origin is `human`. A tool result, a task notice, another
    agent's message and a compaction summary carry another origin or none."""
    session = os.environ.get(SESSION, "")
    if not re.fullmatch(r"[0-9A-Za-z-]{8,}", session):
        raise Refusal(f"${SESSION} is not set, so this session's transcript cannot be found and his "
                      f"words cannot be checked. Run the command from the session he typed in.")
    paths = sorted(PROJECTS.glob(f"*/{session}.jsonl"))
    if not paths:
        raise Refusal(f"no transcript {session}.jsonl under {PROJECTS}, so his words cannot be checked.")
    found = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(rec, dict) or rec.get("type") != "user" or rec.get("isMeta") or rec.get("isSidechain"):
                    continue
                origin = rec.get("origin")
                if not isinstance(origin, dict) or origin.get("kind") != "human":
                    continue
                if stamp(rec.get("timestamp")) < since:
                    continue
                content = (rec.get("message") or {}).get("content")
                if isinstance(content, list):
                    content = " ".join(str(block.get("text", "")) for block in content
                                       if isinstance(block, dict) and block.get("type") == "text")
                if isinstance(content, str):
                    found.append(content)
    return found


def spoken(text: str) -> str:
    return " ".join(str(text).replace('"', "'").casefold().split())


def said(words: str, since: float, who: str | None) -> None:
    """Refuse words that no message he typed in this session carries."""
    want = spoken(words)
    if len(want) < 2:
        raise Refusal("his words are two characters or more.")
    if not any(want in spoken(message) for message in human_messages(since)):
        raise Refusal(f"no message {who} typed in this session"
                      + (" since the question was sent" if since else "")
                      + f" contains \"{words.strip()}\". A ruling or an answer in his name carries his own "
                        f"words; without them the default rules, or the note waits.")


def records_dir(tree, feature: str) -> pathlib.Path:
    """The run's own folder, in the git common dir: no branch carries it."""
    done = subprocess.run(["git", "-C", str(tree), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                          capture_output=True, text=True)
    if done.returncode:
        raise Refusal(f"{tree} is not a git tree.")
    return pathlib.Path(done.stdout.strip()) / "build-feature" / feature


class Feature:
    """The plan and the report of one feature in one tree."""

    def __init__(self, tree: str, feature: str):
        self.tree = pathlib.Path(tree)
        self.name = feature
        self.folder = self.tree / CHANGES / feature
        self.plan = self.folder / "plan.md"
        self.report = self.folder / "report.md"
        if not self.plan.is_file():
            raise Refusal(f"{self.plan} does not exist.")
        self.who = person(self.tree)

    def report_text(self) -> str:
        return self.report.read_text(encoding="utf-8") if self.report.is_file() else ""

    def forced(self, entries: list[dict]) -> set[str]:
        import plan_check  # here, because plan_check imports this module
        return plan_check.weakened_follow_ons(self.tree, f"{CHANGES}/{self.name}", entries)

    def checked(self, text: str) -> list[dict]:
        """The entries of `text`, refused when they do not hold together."""
        entries, found = read(text)
        found += faults(entries, note_numbers(self.folder), self.who, merged_notes(self.report_text()))
        if found:
            raise Refusal("\n  ".join(found))
        return entries

    def set_row(self, number: str, state: str, strikes: int | None = None) -> bool:
        if not self.report.is_file():
            return False
        text, changed = with_row(self.report.read_text(encoding="utf-8"), number, state, strikes)
        if changed:
            self.report.write_text(text, encoding="utf-8")
        return changed

    def records(self) -> pathlib.Path:
        return records_dir(self.tree, self.name)

    def stop_class(self, number: str, question: str) -> str:
        """The class of the stop a row shows, as the agent typed it. The run's
        record holds it (`feature_run.py roles` writes it from the transcripts);
        a stop with no record, or with a class nobody knows, is `unclassified`."""
        if question.startswith(PLAIN_STOPS):
            return "none"
        found = "unclassified"
        path = self.records() / STOPS
        if path.is_file():
            for raw in path.read_text(encoding="utf-8").splitlines():
                try:
                    stop = json.loads(raw)
                except ValueError:
                    continue
                if (isinstance(stop, dict) and stop.get("note") == number and stop.get("kind") == "question"
                        and plain(stop.get("question")) == plain(question)):
                    found = stop.get("class") if stop.get("class") in ("none", *RISK_CLASSES) else "unclassified"
        return found

    def sent_times(self) -> dict:
        path = self.records() / SENT
        try:
            found = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return found if isinstance(found, dict) else {}

    def sent(self, number: str, question: str) -> float | None:
        value = self.sent_times().get(f"{number}: {plain(question)}")
        return float(value) if isinstance(value, (int, float)) else None

    def mark_sent(self, number: str, question: str) -> float:
        """When the question went to him. The first time stands."""
        times, key = self.sent_times(), f"{number}: {plain(question)}"
        if not isinstance(times.get(key), (int, float)):
            times[key] = now()
            folder = self.records()
            folder.mkdir(parents=True, exist_ok=True)
            (folder / SENT).write_text(json.dumps(times, indent=1) + "\n", encoding="utf-8")
        return float(times[key])

    def commit_line(self, what: str) -> str:
        return (f"commit it: git -C {self.tree} add {CHANGES}/{self.folder.name} && "
                f"git -C {self.tree} commit -m \"{what}\"")


def clock(seconds: float) -> str:
    return datetime.datetime.fromtimestamp(seconds).strftime("%H:%M:%S")


def standing(feature: Feature, number: str, kind: str, who: str) -> tuple[bool, float | None]:
    """Refuse a ruling the note's row does not ask for. Returns whether the
    row goes back to `not started`, and since when his words count.

    The class is the stop's, never the session's: `--kind` must be the class
    the agent typed. A default rules one question at a time, after the wait,
    and one re-arm per note; a waiting row, a cut and a risk class are his."""
    state = report_rows(feature.report_text()).get(number, "")
    his = who == feature.who
    name = f"note {number}" if number != FINAL else "the final check"
    if kind == "correction":
        if who != "default":
            raise Refusal("a correction by the note checker is recorded by `default`; he confirms it at the gate.")
        entries = read(feature.plan.read_text(encoding="utf-8"))[0]
        if number not in uncorrected(entries, feature.report_text()):
            raise Refusal(f"the report's `## Decide` part holds no correction of note {number} that the plan lacks.")
        return False, None
    if state.startswith("merged"):
        raise Refusal(f"{name} is merged, and a merged note is never edited or built again. "
                      f"Write a fix note with its own entry `[follows <nn>]`.")
    if FOLLOWS.match(kind):
        if state.startswith(("cut", "stopped:", "waiting:", "failed")):
            raise Refusal(f"{name} reads `{state}`: it takes a ruling of its own, not a follow-on.")
        return True, None
    if state.startswith("cut"):
        if not his:
            raise Refusal(f"only {feature.who} cuts a note.")
        return False, 0.0
    if state == "failed":
        if not his and kind != "re-arm":
            raise Refusal(f"{name} failed three strikes. A default gives it one re-arm, `--kind re-arm`; "
                          f"any other ruling on it is {feature.who}'s.")
        return True, 0.0
    if state.startswith("waiting:"):
        if not his:
            raise Refusal(f"{name} waits for {feature.who}: `{state}`. No default rules it.")
        why = state[len("waiting:"):].strip()
        cls = next((c for c in RISK_CLASSES if why.startswith(c + ":")), None)
        if kind not in ("none", *RISK_CLASSES) or (cls and kind != cls):
            raise Refusal(f"{name} waits on a [{cls or 'none or a risk class'}] question; `--kind {kind}` is not it.")
        sent = max((t for key, t in feature.sent_times().items()
                    if key.startswith(f"{number}: ") and isinstance(t, (int, float))), default=0.0)
        return True, sent
    if state.startswith("stopped:") and not NOT_A_QUESTION.match(state):
        question = state[len("stopped:"):].strip()
        cls = feature.stop_class(number, question)
        if cls == "unclassified":
            if kind not in RISK_CLASSES:
                raise Refusal(f"the stop of {name} has no class on record ({feature.records() / STOPS}), so it is "
                              f"a risk class and waits for {feature.who}. He names the class: one of "
                              f"{', '.join(RISK_CLASSES)}.")
        elif kind != cls:
            raise Refusal(f"the agent typed this stop of {name} as [{cls}]; `--kind {kind}` is not that class.")
        sent = feature.sent(number, question)
        if sent is None:
            raise Refusal(f"the question of {name} was not sent yet: `rulings.py wait {feature.name} --tree "
                          f"{feature.tree} --note {number}` first.")
        if not his and now() < sent + RULING_WAIT_SECONDS:
            raise Refusal(f"the question of {name} went out at {clock(sent)}. His answer rules until "
                          f"{clock(sent + RULING_WAIT_SECONDS)}; the default rules after that.")
        return True, sent
    raise Refusal(f"{name} did not stop on a question: its row reads `{state or 'no row'}`. A ruling settles a "
                  f"failed, stopped or waiting note; any other change after the approval is {feature.who}'s "
                  f"new `Approved:` line.")


def record(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    named = opts.touches.strip()
    if named.startswith("Touches:"):  # the reader's last line, as it wrote it
        named = named[len("Touches:"):].strip()
    touches = [] if named.lower() == "none" else [t.strip() for t in named.split(",") if t.strip()]
    for value in (opts.question, opts.words, opts.undo):
        if "\n" in value or not value.strip():
            raise Refusal("a question, the words and the undo cost are one line each, and none is empty.")
    reset, since = standing(feature, opts.note, opts.kind.strip(), opts.who)
    if opts.who == feature.who and since is not None:
        said(opts.words, since, feature.who)
    lines = entry_text(opts.note, opts.kind, opts.date, opts.who, opts.question.strip(),
                       opts.words.strip().replace('"', "'"), touches, opts.undo.strip())
    text = with_entry(feature.plan.read_text(encoding="utf-8"), lines)
    # A ruling that touches other notes is recorded before their follow-on
    # entries exist, so that one fault waits for the plan check at the restart.
    entries, found = read(text)
    found += [f for f in faults(entries, note_numbers(feature.folder), feature.who,
                                merged_notes(feature.report_text()))
              if "is touched and has no entry" not in f and "a merged note is never edited" not in f]
    if found:
        raise Refusal("\n  ".join(found))
    feature.plan.write_text(text, encoding="utf-8")
    reset = reset and feature.set_row(opts.note, "not started" if opts.note != FINAL else f"ruled {opts.date}", 0)
    print(f"ruling: [{opts.kind}] {opts.note} by {opts.who} written to {feature.plan}"
          + ("; its report row reads `not started` with no strike" if reset else "; its report row stays as it is"))
    if touches:
        print(f"touched: {', '.join(touches)}. Each needs its own `[follows {opts.note}]` entry "
              f"(a merged one: a fix note) before the restart.")
    print(feature.commit_line(f"ruling: note {opts.note}"))
    return 0


def wait(opts) -> int:
    """The question goes to Abdul now. A class a default rules keeps its row,
    and the default rules after the wait; any other row waits for him."""
    feature = Feature(opts.tree, opts.feature)
    state = report_rows(feature.report_text()).get(opts.note)
    if state is None:
        raise Refusal(f"{feature.report} has no row for note {opts.note}.")
    why = (opts.why or "").strip()
    if "\n" in why or "|" in why:
        raise Refusal("--why is one line with no `|`.")
    if state.startswith("stopped:") and not NOT_A_QUESTION.match(state):
        question = state[len("stopped:"):].strip()
        cls = feature.stop_class(opts.note, question)
        sent = feature.mark_sent(opts.note, question)
        if ruler_when_unanswered(cls) == "default":
            print(f"note {opts.note}: [{cls}] sent at {clock(sent)}. His answer rules until "
                  f"{clock(sent + RULING_WAIT_SECONDS)}; after that the default rules "
                  f"(`rulings.py record --kind {cls} --who default`).")
            return 0
        why = f"{cls}: {question}"
    elif not why:
        raise Refusal(f"note {opts.note} reads `{state}`, which holds no question: say why it waits with --why.")
    else:
        feature.mark_sent(opts.note, why)
    feature.set_row(opts.note, f"waiting: {why}")
    print(f"note {opts.note}: waiting: {why}")
    print(feature.commit_line(f"report: note {opts.note} waits"))
    return 0


def show(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    entries = feature.checked(feature.plan.read_text(encoding="utf-8"))
    forced = feature.forced(entries)
    waiting = open_entries(entries, feature.who, forced)
    print(f"{len(waiting)} ruling(s) to confirm, of "
          f"{sum(1 for e in entries if needs_answer(e, entries, feature.who, forced))} he did not make himself")
    for line in away_lines(entries, feature.who, forced, open_only=True):
        print(f"- {line}")
    return 0


def answer(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    text = feature.plan.read_text(encoding="utf-8")
    entries = feature.checked(text)
    forced = feature.forced(entries)
    waiting = open_entries(entries, feature.who, forced)
    words = (opts.words or "").strip()
    if not words:
        raise Refusal(f"an answer carries {feature.who}'s own words: --words \"<what he typed>\".")
    said(words, 0.0, feature.who)
    words = words.replace('"', "'")
    if opts.all:
        chosen = [e for e in waiting if not is_risk(e, entries) and not e["confirmed"]]
        lines = [f'Confirmed: {opts.date}, "{words}"']
    else:
        chosen = [e for e in waiting if e["number"] == opts.note]
        if not chosen:
            raise Refusal(f"note {opts.note} has no ruling that waits for an answer.")
        chosen = chosen[:1]
        if opts.overturned:
            if not opts.fix:
                raise Refusal("an overturned ruling needs --fix, the number of the fix note that undoes it.")
            state = report_rows(feature.report_text()).get(opts.fix, "")
            if state.startswith(("merged", "cut")):
                raise Refusal(f"note {opts.fix} reads `{state}`. An overturned ruling closes on a new fix "
                              f"note that the run still builds.")
            lines = [f'Overturned: {opts.date}, "{words}"', f"Fix: {opts.fix}"]
        else:
            lines = [f'Confirmed: {opts.date}, "{words}"']
    for entry in sorted(chosen, key=lambda e: -e["line"]):
        text = with_sub_lines(text, entry, lines)
    left = open_entries(feature.checked(text), feature.who, forced)
    feature.plan.write_text(text, encoding="utf-8")
    print(f"answered: {', '.join(e['number'] for e in chosen) or 'none'}; {len(left)} ruling(s) still wait"
          + (f": {', '.join(e['number'] for e in left)}" if left else ""))
    print(feature.commit_line("rulings: answered"))
    return 0


def main(argv=None) -> int:
    today = datetime.date.today().isoformat()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ruler").add_argument("kind")
    for name in ("record", "wait", "list", "answer"):
        one = sub.add_parser(name)
        one.add_argument("feature")
        one.add_argument("--tree", required=True)
        one.add_argument("--date", default=today)
        if name != "list":
            one.add_argument("--note", required=name != "answer")
        if name == "record":
            for flag in ("--kind", "--who", "--question", "--words", "--touches", "--undo"):
                one.add_argument(flag, required=True)
        if name == "wait":
            one.add_argument("--why")
        if name == "answer":
            one.add_argument("--all", action="store_true")
            one.add_argument("--confirmed", action="store_true")
            one.add_argument("--overturned", action="store_true")
            one.add_argument("--words")
            one.add_argument("--fix")
    opts = parser.parse_args(argv)
    try:
        if opts.command == "ruler":
            road = ruler_when_unanswered(opts.kind)
            print(f"default after {RULING_WAIT_SECONDS} s" if road == "default" else road)
            return 0
        if opts.command == "answer" and not opts.all and not (opts.note and (opts.confirmed or opts.overturned)):
            raise Refusal("answer takes --all, or --note with --confirmed or --overturned.")
        return {"record": record, "wait": wait, "list": show, "answer": answer}[opts.command](opts)
    except Refusal as error:
        print(f"REFUSED: {error}")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
