#!/usr/bin/env python3
"""The rulings of a feature: what was decided while a run was stopped, by whom,
and whether Abdul has confirmed it.

    python3 ~/.claude/skills/workflow/lib/rulings.py ruler <class>
    python3 ~/.claude/skills/workflow/lib/rulings.py record <feature> --tree <feature worktree> --note <nn> \\
        --kind <kind> --who <who> --question <text> --words <text> --touches <none|nn,nn> --undo <text>
    python3 ~/.claude/skills/workflow/lib/rulings.py wait <feature> --tree <feature worktree> --note <nn> [--why <text>]
    python3 ~/.claude/skills/workflow/lib/rulings.py panel <feature> --tree <feature worktree> --note <nn>
    python3 ~/.claude/skills/workflow/lib/rulings.py list <feature> --tree <feature worktree>
    python3 ~/.claude/skills/workflow/lib/rulings.py answer <feature> --tree <feature worktree> --words <text> \\
        (--all | --note <nn> (--confirmed | --overturned --fix <nn>))

A run that stops on a question no longer waits for an interview. The session
that started it sends the question to Abdul's phone (`wait` records when) and
waits RULING_WAIT_SECONDS. His answer rules when it comes in time; otherwise
`ruler_when_unanswered` says who does: the agent's written default, a panel
for a risk class, or nobody. The session then changes the note inside the
ruling, records it here and starts the run again. Every ruling he did not
make himself is shown to him once, before the merge into local main.

## The part of the plan this reads

`changes/<feature>/plan.md` carries the rulings under `## Rulings`, above the
`Approved:` lines. One entry per ruled note, one line of each name per entry:

    - [<kind>] <nn>: <the question, in plain words>
      Ruled: <date>, <who>, "<the words of the ruling>"
      Panel: <the count>, files <the folder of the panel's files>
      Condition: <a named test of a reader who chose the road>
      Touches: <none, or the numbers of the other notes the ruling changes>
      Undo: <what reversing it costs>
      Confirmed: <date>[, "<his words>"]
      Overturned: <date>, "<his words>"
      Fix: <the number of the fix note that undoes an overturned ruling>

`<nn>` is a note's number, or `final` for a question of the final check, whose
row in the report is `final`. `<kind>` is `none`, a risk class (`money`,
`access`, `migration`, `data leaving`), `re-arm` (the one automatic second try
of a note that failed three strikes), `correction` (the note checker corrected
the note at strike two), `screen` (the commit hook refused a file in the route
folder of a screen the note did not name, and the session added that screen to
the note's `Screens:` line) or `follows <nn>` (a note the ruling on `<nn>`
touched, or the fix note written for it). `<who>` is `default`, `panel`, or
the first word of `git config user.name`, which is how the page names Abdul.
Only an entry by `panel` has a `Panel:` line, and it may have several
`Condition:` lines; `record` writes both from the panel's files.

## The panel

A question in a risk class that he did not answer goes to a panel. `panel`
prints one step per call and refuses before the wait is over:

1. one road finder (`agents/build-feature-road-finder.md`) writes
   `finder.json`: the roads the question's words offer, and at most MAX_FOUND
   roads it does not offer, each with `file:line` evidence, where it fails,
   what it costs to undo, and `needs_owner_fact`;
2. three readers, one per seat of SEATS, each a `panel-review-persona` agent
   on PANEL_MODEL, judge every road and write `<seat>.md`: line 1 is
   `Rule: <road id>` or `Hold: <the one fact to measure first>`. The brief
   `panel` writes gives the whole form of that file, and says in words that
   it replaces the section "What you return" of the agent file, which is
   what that section asks for before it gives way;
3. `count` decides. No agent is the judge.

The files of one stop are in `<git dir>/build-feature/<feature>/panel/<nn>-<key>/`,
where the key is made from the feature and the question, so a note's next
question never reads them. Each agent's label carries that folder's name.
Road `A` is the written default, `B` onwards the other offered roads, `F1`
and `F2` the found ones.

Two or three readers on one road: it rules. A vote for a road that needs a
fact only Abdul can get is a hold on that fact. No two on one road and fewer
than two holds: the written default rules, and only when a reader chose it.
Every other count makes the row `waiting:`; so do a stop with no written
default and a note that took MAX_DEFAULT_RULINGS rulings without him.

A reader's file with no vote, an agent with no transcript under its label or
not on PANEL_MODEL, and a reader's transcript that names another seat's
answer file each send the readers back once: `panel` removes the three
answers (and the finder's, when the fault is the finder's), leaves the empty
file `second-round` and prints the spawns again. A second fault makes the row
`waiting:`. A call while one or two readers' files are missing is no fault:
`panel` prints "readers still run" and changes nothing.

## What a command refuses

`record` reads the note's row in the report and the run's own record of the
stop, `<git dir>/build-feature/<feature>/stops.jsonl`, which `feature_run.py
roles` writes from the agents' transcripts:

- the class is the one the agent typed. `--kind` must equal it; a stop with
  no class on record waits for Abdul, and he names its class;
- a `stopped:` question takes no ruling before `wait` recorded that it went
  out, and none by `default` or `panel` before that time plus
  RULING_WAIT_SECONDS; each of the two rules only the classes
  `ruler_when_unanswered` gives it;
- a note that stopped on a question takes an entry with that question,
  word for word: `--question` is compared with the row;
- `--who panel` needs the panel's files for that stop (the finder's answer
  and the three readers' files, each with a vote), words equal to the road
  `count` gives, and, among this session's subagent transcripts, the finder
  and one reader per seat under the labels `panel` printed, all four on
  PANEL_MODEL, and no reader's naming another seat's answer file;
- a `failed` row takes `re-arm` from a default, a `waiting:` row and a cut
  take a ruling from Abdul alone, and a row that did not stop takes none;
- a `merged` row takes a ruling from Abdul alone, of kind `none` or a risk
  class, with words that start with the note's number and a colon, after
  `wait --note <nn>` showed it to him. `--touches` must name a new fix note:
  a note the approved plan did not hold, not merged or cut, whose `Waits
  for:` line names the merged note. The row stays `merged`, and the fix note
  takes its `follows <nn>` entry with his words. A merged note is never
  edited: the plan check refuses a change to its file;
- `--kind correction` is by `default`, for a correction the report's Decide
  part lists and the plan does not yet carry;
- `--kind screen` is by `default`, for a row `stopped: tooling:` whose line
  holds the commit hook's refusal "is in the route folder of screen `<s>`",
  with that line as `--question`, and only once the note's `Screens:` line
  names each such screen and the note passes the plan check's static reading
  (a note that names a screen has an end-to-end done check). The hook still
  refuses, and the final check still retakes the screen's baselines: the
  repair adds the screen to what the note must answer for, and loosens
  nothing (Abdul, 2026-11-13);
- a ruling or an answer in Abdul's name carries words he typed, read from
  this session's transcript (`CLAUDE_CODE_SESSION_ID` names it). With no
  such session nobody rules in his name. The rule:
  1. only a message a person typed counts, and only one typed after the
     note was put in front of him: after `wait` for a ruling (`wait --note
     <nn>` with no `--why` records the time for a failed row, a waiting row
     or a cut), after `list` for an answer at the gate;
  2. what the app adds to a message is taken out first: a
     `<system-reminder>` block, the `<command-...>` parts of a slash
     command, and a line that is a slash command;
  3. `--words` must equal the whole message, or one whole sentence of it;
     case, quotes, white space and the closing `.`, `!` or `?` aside;
  4. one sentence answers once (`sent.json` keeps what it answered).
     `answer --all` is the one call that takes several entries;
  5. a risk-class entry, in `record` and in `answer`, takes only a sentence
     that starts with the note's number and a colon, as in `02: A` or `03:
     confirm`. `wait` prints the notice with that form, and `list` states it.
  A follow-on in his name carries the words of the ruling it follows.

The check stops a session that writes an answer itself. It does not stop one
that forges a transcript, names another session's id, writes a reader's
file after the reader ran, or lets a reader open another's file by a path
its transcript does not spell out: the limit is stated in
`skills/build-feature/when-a-run-stops.md`.

## What the page refuses

`read` places every line of the part or reports it; `faults` then refuses:

- an entry with no `Ruled:` line, or with no `Touches:` line;
- a kind or a who it does not know;
- a ruling by `default` on a risk class, one by `panel` outside the risk
  classes or with no `Panel:` line, a `Panel:` line on any other entry, and a
  follow-on whose who is not the who of the ruling it follows;
- `Touches:` naming a note that is not in the feature (a note he cut since
  is passed over), or a touched note with no `follows` entry of its own; each touched note that is merged needs a
  fix note of its own, with a `follows` entry;
- `follows <nn>` when `<nn>` has no ruling above it;
- a second `re-arm` for one note, and more than MAX_DEFAULT_RULINGS rulings
  by default or panel on one note: the next question on it waits for Abdul;
- both answers on one entry, or `Overturned:` whose `Fix:` names no fix note
  with an entry `[follows <nn>]`.

`open_entries` is the gate before local main: each ruling Abdul did not make
that has no answer, and each follow-on, whoever made the ruling it follows:
a follow-on changes a note no question was asked about, so he sees it once.
A follow-on on a note he cut since does not wait.
A risk-class line counts as confirmed only when the line carries his words. An overturned line closes on a fix note that was not merged when
he answered. A panel ruling's line has the full form (`panel_part`): the
count, each reader's vote and reason, the conditions, each found road with
its evidence and undo cost, and each candidate road with the fact it needs. `plan_check.py`, `feature_run.py args` and the hooks
(`note_check.py merge` and `note_check.py ref`) all call `faults` and
`open_entries`, with the same person.

Exit 0 on success, 3 with `REFUSED: <why>`.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time

# How long the starting session waits for Abdul's answer before the default
# rules. The one place this number lives: `ruler` prints it and
# `feature_run.py args` passes it on.
RULING_WAIT_SECONDS = 900
RISK_CLASSES = ("money", "access", "migration", "data leaving")
SCREEN = "screen"  # the listed repair of a hook's refusal on a screen the note did not name
KINDS = ("none", *RISK_CLASSES, "re-arm", "correction", SCREEN)
# The kinds a default rules. Every other class waits, one nobody named included.
DEFAULT_RULED = ("none", "re-arm", "correction", SCREEN)
# The commit hook's line for a file in the route folder of a screen no mapped
# note names (`note_check.py commit`). The screen's name is the one group.
UNNAMED_SCREEN = re.compile(r"is in the route folder of screen `([^`]+)`")
PANEL = "panel"  # who rules a risk-class question he did not answer, and the folder its files are in
RULERS = ("default", PANEL)
# The rulings one note's questions get without Abdul, by default or by panel,
# the final check's included (its number is `final`). The next question waits
# for him, so a note that stops, takes a ruling and stops again has an end, and
# so has the cycle of fix notes a final check asks for.
MAX_DEFAULT_RULINGS = 2
FINAL = "final"
# A stop no agent typed, so no transcript holds it. The row itself fixes its
# class as `none`, and this table its written default: the session's pre-run
# stop has none, so it waits for Abdul; the script gives a final-check finding
# that needs a fix note the default below (`build-feature-run.js`).
PLAIN_STOPS = {"done check passes before the work": "",
               "fix note needed:": "write a fix note with the test each finding names"}
# Rows a run starts again by itself; none is a question (`plan_check.RESTART_STATES`).
NOT_A_QUESTION = re.compile(r"^stopped: (API errors|[a-z-]+ returned no result|worktree:|tooling:)")
STOPS = "stops.jsonl"  # the run's own record of each typed stop, written from the agents' transcripts
SENT = "sent.json"     # when each question went to Abdul, when the gate list was shown, and what each typed sentence answered
GATE = "gate"          # its key for the time `list` last printed the gate list
USED = "used"          # its key for the sentences of his that answered something already
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
SESSION = "CLAUDE_CODE_SESSION_ID"
FINDER = "finder.json"  # the road finder's typed answer, in the panel's folder for one stop
SECOND = "second-round"  # an empty file in a panel's folder once its readers were sent back. They run no third time
MAX_OFFERED = 4         # the roads a question's own words offer besides the default: ids B to E
MAX_FOUND = 2           # the roads a finder may add: ids F1 and F2
MAX_CONDITIONS = 2      # the named tests one reader may attach to its vote
# The sentence each reader's brief carries. `agents/panel-review-persona.md` gives
# way only to a brief that says this in words (review 4, note F).
REPLACES = "This form replaces the section \"What you return\" of your agent file, whole"
PANEL_MODEL = "opus"    # the model the finder and each reader run on; a reader by an override at its spawn
DISAGREED = "the readers disagreed"
# The three seats of a panel. They are fixed here, and nobody derives a seat at
# run time: each is the party that pays when a road is wrong in one way. `{who}`
# is how the plan page names Abdul.
SEATS = {
    "exposed": ("the exposed party",
                "You are the exposed party: the staff member or customer the rule or the data protects. You pay "
                "when a road lets through a read, a write or a wrong result that a narrower road refuses."),
    "operator": ("the operator at release and rollback",
                 "You are the operator at release and rollback: {who} on release day, who runs the production "
                 "migration by hand, then pushes, and rolls back a bad deploy. No agent reads production for you. "
                 "You pay when a road cannot be undone after the production migration, when live code misbehaves "
                 "between the migration and the push, when a rollback leaves a shape the old code cannot read, or "
                 "when a road needs a guard loosened."),
    "builder": ("the next builder, who is also the stranger",
                "You are the next builder, who is also the stranger: the next agent that builds on this code from "
                "the notes, the plan page and `docs/design.md`. You pay when a road adds a second way to do a "
                "named pattern, a rule the plan does not name, a check that can no longer go red, or more code "
                "than the question needs."),
}
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
# The folder name is a path part read from the page, so it is a note number and a key, never a path.
PANEL_LINE = re.compile(rf"^Panel:\s*(\S.*), files ({NUMBER}-[0-9a-f]{{10}})$")
CONDITION = "Condition:"
SUB_LINES = ("Ruled:", "Touches:", "Undo:", "Confirmed:", "Overturned:", "Fix:", "Panel:", CONDITION)
RULE = re.compile(r"^Rule: (\S+)$")
HOLD = re.compile(r"^Hold: (\S.*)$")
EVIDENCE = re.compile(r"^\S+:\d+")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


class Refusal(Exception):
    pass


def ruler_when_unanswered(kind: str) -> str:
    """Who rules a question Abdul did not answer inside RULING_WAIT_SECONDS.

    `default`: the agent's written default rules. `panel`: a road finder and
    three readers judge the roads, and `count` decides from their files.
    `wait`: nobody does; the note waits for him and the other notes continue.
    This is the one place that answers it. Every class this function does not
    know waits: a new one, and a stop nobody typed a class for."""
    if kind in DEFAULT_RULED:
        return "default"
    if kind in RISK_CLASSES:
        return PANEL
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
                     "confirmed": None, "overturned": None, "fix": None, "panel": None, "conditions": []}
            entries.append(entry)
            seen = set()
            continue
        name = line.split(":", 1)[0]
        if entry is not None and name in seen and not line.startswith(CONDITION):
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
    if line.startswith("Panel:"):
        match = PANEL_LINE.match(line)
        if match:
            entry["panel"] = {"count": match.group(1).strip(), "files": match.group(2)}
        return bool(match)
    if line.startswith(CONDITION):
        value = line[len(CONDITION):].strip()
        if value:
            entry["conditions"].append(value)
        return bool(value)
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


def faults(entries: list[dict], numbers: set[str], who: str | None, merged=frozenset(), cut=frozenset()) -> list[str]:
    """Every reason the rulings do not hold together. `numbers` are the notes
    of the feature, `who` is `person()`, `merged` the notes already merged and
    `cut` the notes cut since: a ruling that touched one asks nothing more of it."""
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
        if not e["follows"] and (e["who"] == PANEL) != bool(e["panel"]):
            found.append(f"{name}: a ruling by `{PANEL}` has no `Panel:` line. `record --who {PANEL}` writes it from "
                         f"the count of the readers' files." if e["who"] == PANEL else
                         f"{name}: a `Panel:` line belongs to a ruling by `{PANEL}`, and this one is by `{e['who']}`.")
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
            if number in cut and number != e["number"]:
                continue
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
        if e["kind"] in ("none", *RISK_CLASSES) and e["who"] in RULERS:
            defaults[e["number"]] += 1
            if defaults[e["number"]] == MAX_DEFAULT_RULINGS + 1:
                found.append(f"{name}: {MAX_DEFAULT_RULINGS} questions of {e['number']} took a ruling without "
                             f"{who} already. The next one waits for him.")
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


def needs_answer(entry: dict, entries: list[dict], who: str | None, cut=frozenset()) -> bool:
    """Abdul answers everything he did not rule himself. A follow-on is an
    edit a reader and a session wrote, on a note the question was not about,
    so it waits for him, whoever made the ruling it follows. A follow-on on a
    note he cut since asks nothing: no line of that note reaches main (review
    3, note 8: he confirmed a line about a note that was gone)."""
    if entry["follows"]:
        return entry["number"] not in cut
    return not by_person(entry, who)


def answered(entry: dict, entries: list[dict]) -> bool:
    if entry["overturned"]:
        return bool(entry["fix"]) and any(f["number"] == entry["fix"] and f["follows"] == entry["number"]
                                          for f in entries)
    if not entry["confirmed"]:
        return False
    return bool(entry["confirmed"]["words"]) or not is_risk(entry, entries)


def open_entries(entries: list[dict], who: str | None = None, cut=frozenset()) -> list[dict]:
    """The gate before local main: each ruling that still waits for his answer.
    With no `who`, nobody is the person and every ruling waits. `cut` are the
    notes the report shows as cut."""
    return [e for e in entries if needs_answer(e, entries, who, cut) and not answered(e, entries)]


def rearmed(entries: list[dict]) -> set[str]:
    return {e["number"] for e in entries if e["kind"] == "re-arm"}


def new_since(now: list[dict], then: list[dict]) -> set[str]:
    """The notes with a ruling the older page does not carry."""
    old = {(e["number"], e["kind"], e["date"], e["who"], e["words"]) for e in then}
    return {e["number"] for e in now
            if (e["number"], e["kind"], e["date"], e["who"], e["words"]) not in old}


def closed(text: str) -> str:
    """A sentence with its closing mark."""
    text = str(text).strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def brief(text: str, most: int = 2) -> str:
    """The first sentences of a reader's reason: what a gate line has room for."""
    return " ".join([part.strip() for part in SENTENCE_END.split(text) if part.strip()][:most])


def panel_part(entry: dict, who: str | None, records: pathlib.Path | None) -> str:
    """What only a panel ruling's gate line carries: the count, each reader's
    vote and reason, the conditions, each found road with its evidence and
    undo cost, and each candidate road with the fact it needs from Abdul. The
    count and the conditions are on the page; the rest is in the panel's files."""
    mark, name = entry["panel"]["count"], entry["panel"]["files"]
    parts = [f"The count: {mark}."]
    folder = records / PANEL / name if records else None
    roads = votes = None
    if folder is not None and (folder / FINDER).is_file():
        try:
            roads = read_roads("", json.loads((folder / FINDER).read_text(encoding="utf-8")))
            votes = {seat: read_vote((folder / f"{seat}.md").read_text(encoding="utf-8"), roads)
                     for seat in SEATS if (folder / f"{seat}.md").is_file()}
        except (ValueError, Refusal):
            roads = None
    if roads is None and records is not None:
        parts.append(f"The readers' reasons and the roads are not on this machine (panel files {name}).")
    for seat, vote in (votes or {}).items():
        parts.append(closed(f"{seat}: {vote['first']}") + (f" {closed(brief(vote['reason']))}" if vote["reason"] else ""))
    parts.append(closed("Conditions: " + ("; ".join(entry["conditions"]) or "none")))
    taken = re.match(r"^road (\S+),", mark)
    for road in roads or []:
        if road["kind"] != "found":
            continue
        if road["needs_owner_fact"]:
            parts.append(f"A candidate road that needs a fact from {who or 'the human'}: {road['id']}, {road['road']}; "
                         + closed(f"the fact: {road['needs_owner_fact']}"))
        else:
            parts.append(f"A road the question did not offer: {road['id']}"
                         + (" (the road taken)" if taken and taken.group(1) == road["id"] else "")
                         + f", {road['road']}; evidence: {', '.join(road['evidence'])}; "
                         + closed(f"undo: {road['undo']}"))
    return " ".join(parts)


def away_line(entry: dict, entries: list[dict], records: pathlib.Path | None = None, who: str | None = None) -> str:
    cls = class_of(entry, entries)
    head = f"**{cls.upper()}** " if cls in RISK_CLASSES else ""
    panel = f" {panel_part(entry, who, records)}" if entry.get("panel") else ""
    return (f"{head}{entry['number']}: {entry['question']} Road taken: \"{entry['words']}\". "
            f"Ruled by {entry['who']} on {entry['date']}.{panel} "
            f"Touched: {', '.join(entry['touches'] or []) or 'none'}. "
            f"Undo: {entry['undo'] or 'not stated'}.")


def away_lines(entries: list[dict], who: str | None, open_only=False, records: pathlib.Path | None = None,
               cut=frozenset()) -> list[str]:
    """The report's "Ruled while you were away" lines, risk classes first.
    With `records`, the run's folder in the git common dir, a panel ruling's
    line takes its full form from the panel's files."""
    shown = [e for e in entries if needs_answer(e, entries, who, cut) and not (open_only and answered(e, entries))]
    return [away_line(e, entries, records, who)
            for e in sorted(shown, key=lambda e: (not is_risk(e, entries), e["line"]))]


# ── The panel ────────────────────────────────────────────────────────────────

def one_line(value) -> str:
    return plain(value) if isinstance(value, str) else ""


def read_roads(default: str, finder) -> list[dict]:
    """Every road of one question, with the id a reader names it by: `A` is the
    written default, `B` onwards the other roads the question's own words
    offer, `F1` and `F2` the roads the finder found. Refuses a finder's answer
    outside its typed form; an empty `found` list is a full answer."""
    if not isinstance(finder, dict):
        raise Refusal("the answer is not one JSON object.")
    if not one_line(finder.get("need")):
        raise Refusal("it has no `need`: the real need behind the question, in one line.")
    offered, found = finder.get("offered"), finder.get("found")
    if not isinstance(offered, list) or not isinstance(found, list):
        raise Refusal("`offered` and `found` are each a list; an empty list is a full answer.")
    if len(offered) > MAX_OFFERED or len(found) > MAX_FOUND:
        raise Refusal(f"it holds {len(offered)} offered and {len(found)} found roads; at most {MAX_OFFERED} "
                      f"offered and at most {MAX_FOUND} found.")
    roads = [{"id": "A", "kind": "default", "road": plain(default), "cost": one_line(finder.get("default_cost"))}]
    for at, item in enumerate(offered):
        if not isinstance(item, dict) or not one_line(item.get("road")):
            raise Refusal(f"offered road {at + 1} has no `road` line.")
        roads.append({"id": chr(ord("B") + at), "kind": "offered", "road": one_line(item["road"]),
                      "cost": one_line(item.get("cost"))})
    for at, item in enumerate(found, 1):
        if not isinstance(item, dict):
            raise Refusal(f"found road {at} is not an object.")
        lists = {name: [one_line(v) for v in item[name]] if isinstance(item.get(name), list) else []
                 for name in ("files", "evidence")}
        lines = {name: one_line(item.get(name)) for name in ("road", "beats", "fails", "undo")}
        lacking = [name for name, value in {**lines, **lists}.items() if not value or not all(value)]
        if lacking:
            raise Refusal(f"found road {at} lacks {', '.join(f'`{name}`' for name in lacking)}: `road`, `beats`, "
                          f"`fails` and `undo` are one line each, `files` and `evidence` a list each.")
        loose = [line for line in lists["evidence"] if not EVIDENCE.match(line)]
        if loose:
            raise Refusal(f"found road {at}: evidence `{loose[0]}` is not `file:line`. A road rests on lines somebody read.")
        if not isinstance(item.get("needs_owner_fact"), str):
            raise Refusal(f"found road {at} has no `needs_owner_fact`: an empty line, or the one fact only he can get.")
        roads.append({"id": f"F{at}", "kind": "found", **lines, **lists,
                      "needs_owner_fact": one_line(item["needs_owner_fact"])})
    return roads


def read_vote(text: str, roads: list[dict]) -> dict:
    """One reader's file. Line 1 is the vote, exactly `Rule: <road id>` for a
    road on the list or `Hold: <the one fact to measure first>`; a file with
    any other first line is refused, and its reader runs again. A vote for a
    road that needs a fact only Abdul can get is a hold on that fact. Then
    the reason, and at most MAX_CONDITIONS `Condition:` lines."""
    rows = text.splitlines()
    first = rows[0].rstrip() if rows else ""
    rule, hold = RULE.match(first), HOLD.match(first)
    if not rule and not hold:
        raise Refusal(f"line 1 is `{first[:80]}`, which is not `Rule: <road id>` or `Hold: <fact>`")
    road = next((r for r in roads if rule and r["id"] == rule.group(1)), None)
    if rule and road is None:
        raise Refusal(f"line 1 names `{rule.group(1)}`, which is no road of this question")
    body = [row.strip() for row in rows[1:] if row.strip()]
    conditions = [plain(row[len(CONDITION):]) for row in body if row.startswith(CONDITION)]
    vote = {"first": first, "kind": "hold", "road": None, "fact": None,
            "reason": plain(" ".join(row for row in body if not row.startswith(CONDITION))),
            "conditions": [c for c in conditions if c][:MAX_CONDITIONS]}
    if hold:
        vote["fact"] = plain(hold.group(1))
    elif road.get("needs_owner_fact"):
        vote["fact"] = road["needs_owner_fact"]
    else:
        vote["kind"], vote["road"] = "rule", road["id"]
    return vote


def count(votes: dict[str, dict]) -> dict:
    """The counting rule, on the three readers' votes. No agent is the judge.

    Two or three readers on one road, and that road rules, a found road like
    any other. No two on one road and fewer than two holds, and the written
    default rules with the entry marked, but only when a reader chose it.
    Every other count rules nothing: the note waits for Abdul. So the default
    never rules on a count in which no reader named it (review 3, fault 2).
    `seats` are the readers behind the outcome; their conditions go with the
    ruling, and their facts with a hold."""
    named = collections.Counter(vote["road"] for vote in votes.values() if vote["kind"] == "rule")
    holds = [seat for seat, vote in votes.items() if vote["kind"] == "hold"]
    road, most = named.most_common(1)[0] if named else (None, 0)
    if most >= 2:
        outcome, mark = "road", f"road {road}, {most} of {len(SEATS)}"
    elif len(holds) >= 2:
        return {"outcome": "hold", "road": None, "seats": holds, "mark": f"hold, {len(holds)} of {len(SEATS)}"}
    elif named["A"]:
        outcome, road, mark = "default", "A", f"{DISAGREED}, so the written default rules"
    else:
        return {"outcome": "hold", "road": None, "seats": holds,
                "mark": f"{DISAGREED}, and none chose the written default"}
    return {"outcome": outcome, "road": road, "mark": mark,
            "seats": [seat for seat, vote in votes.items() if vote["kind"] == "rule" and vote["road"] == road]}


# ── Writing ──────────────────────────────────────────────────────────────────

def entry_text(number, kind, date, who, question, words, touches, undo, more=()) -> list[str]:
    """One entry. `more` are the lines only a panel ruling has: `Panel:` and each `Condition:`."""
    return [f"- [{kind}] {number}: {question}",
            f'  Ruled: {date}, {who}, "{words}"',
            *[f"  {line}" for line in more],
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


def with_row(text: str, number: str, state: str, strikes: int | None = None, add: bool = False) -> tuple[str, bool]:
    """The report with one note row's state set, and its strikes when given.
    With `add`, a table that has no such row gets one at its end."""
    rows, columns, changed, last = text.splitlines(), None, False, None
    for i, line in enumerate(rows):
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
            continue
        if columns:
            last = (i, len(columns))
        if not columns or cells[0] != number:
            continue
        cells[1] = state
        if strikes is not None and "Strikes" in columns and columns.index("Strikes") < len(cells):
            cells[columns.index("Strikes")] = str(strikes)
        rows[i] = "| " + " | ".join(cells) + " |"
        changed = True
    if add and not changed and last:
        rows.insert(last[0] + 1, f"| {number} | {state} |" + " |" * (last[1] - 2))
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


def cut_notes(report_text: str) -> set[str]:
    return {number for number, state in report_rows(report_text).items() if state.startswith("cut")}


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


HARNESS_BLOCK = re.compile(r"<([a-z]+(?:-[a-z]+)+)>.*?</\1>", re.S)  # <system-reminder>, <command-args> and the like
SLASH_LINE = re.compile(r"^\s*/[A-Za-z][\w:-]*(\s|$)")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def typed_text(content) -> str:
    """What a person typed in one record. The blocks the app adds to it
    (`<system-reminder>`, the three `<command-*>` parts of a slash command)
    and a line that is a slash command are not his words."""
    if isinstance(content, list):
        content = "\n".join(str(block.get("text", "")) for block in content
                            if isinstance(block, dict) and block.get("type") == "text")
    if not isinstance(content, str):
        return ""
    lines = HARNESS_BLOCK.sub("\n", content).splitlines()
    return "\n".join(line for line in lines if not SLASH_LINE.match(line)).strip()


def human_messages(since: float) -> list[tuple[str, str]]:
    """What Abdul typed in this session after `since`, from its transcript:
    (timestamp, text) of each `user` record whose origin is `human`. A tool
    result, a task notice, another agent's message and a compaction summary
    carry another origin or none."""
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
                if stamp(rec.get("timestamp")) <= since:
                    continue
                text = typed_text((rec.get("message") or {}).get("content"))
                if text:
                    found.append((str(rec.get("timestamp")), text))
    return found


def spoken(text: str) -> str:
    """Words as they are compared: case, quotes, white space and the closing mark of a sentence aside."""
    return " ".join(str(text).replace('"', "'").casefold().split()).rstrip(".!?").rstrip()


def sentences(message: str) -> list[str]:
    found = []
    for part in SENTENCE_END.split(message):
        if spoken(part) and spoken(part) not in found:
            found.append(spoken(part))
    return found


def names_line(sentence: str, number: str) -> bool:
    """Whether a sentence answers one line by name: it starts with the line's
    number and a colon and says something after them, as in `02: A` or `03:
    confirm`. A number further inside a sentence names nothing: "Give me 2
    minutes" closed a [money] question on note 02 (review 3, fault 5). A digit
    straight after the colon makes it a clock time: "2:30 is when I am back"
    closed one too (review 4, fault A)."""
    token = re.escape(number.lstrip("0") or "0") if number.isdigit() else re.escape(number)
    return bool(re.match(rf"0*{token}\s*:(?!\d)\s*\S", sentence.strip()))


def said(words: str, since: float, who: str | None, used: dict, names: str | None = None) -> tuple[str, list[str]]:
    """The message of his that carries `words`, as (timestamp, sentences).

    `words` are his answer only when they are one whole message he typed after
    `since`, or one whole sentence of it. A sentence answers once: `used` holds
    what earlier calls took. With `names`, the sentence must also start with
    that line's number and a colon (`names_line`): a risk-class line takes no
    answer meant for another, and no sentence about something else."""
    want = spoken(words)
    if not want:
        raise Refusal("his words are empty.")
    messages = human_messages(since)
    taken = None
    for when, text in messages:
        parts = sentences(text)
        if want == spoken(text):
            mine = parts
        elif want in parts:
            mine = [want]
        else:
            continue
        if names and not names_line(want, names):
            raise Refusal(f"\"{words.strip()}\" does not start with `{names}:`. A risk-class line takes only a "
                          f"sentence of his that starts with its number and a colon, such as \"{names}: A\" or "
                          f"\"{names}: confirm\".")
        before = [answered for part in mine for answered in [used.get(when, {}).get(part)] if answered]
        if before:
            taken = before[0]
            continue
        return when, mine
    if taken:
        raise Refusal(f"he typed \"{words.strip()}\" once, and it answered {taken} already. One sentence answers one "
                      f"question; a second answer is a second message.")
    raise Refusal(f"no message {who} typed in this session after {clock(since)} is \"{words.strip()}\", as a whole "
                  f"message or a whole sentence of one ({len(messages)} message(s) typed since). A ruling or an answer "
                  f"in his name quotes him exactly; without his words the default rules, or the note waits.")


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

    def checked(self, text: str) -> list[dict]:
        """The entries of `text`, refused when they do not hold together."""
        entries, found = read(text)
        found += faults(entries, note_numbers(self.folder), self.who, merged_notes(self.report_text()),
                        cut_notes(self.report_text()))
        if found:
            raise Refusal("\n  ".join(found))
        return entries

    def set_row(self, number: str, state: str, strikes: int | None = None, add: bool = False) -> bool:
        if not self.report.is_file():
            return False
        text, changed = with_row(self.report.read_text(encoding="utf-8"), number, state, strikes, add)
        if changed:
            self.report.write_text(text, encoding="utf-8")
        return changed

    def records(self) -> pathlib.Path:
        return records_dir(self.tree, self.name)

    def stop(self, number: str, question: str) -> dict:
        """The stop a row shows, as the agent typed it: its class and its
        written default. The run's record holds it (`feature_run.py roles`
        writes it from the transcripts); a stop with no record, or with a
        class nobody knows, is `unclassified`."""
        for start, default in PLAIN_STOPS.items():
            if question.startswith(start):
                return {"class": "none", "default": default}
        found = {"class": "unclassified", "default": ""}
        path = self.records() / STOPS
        if path.is_file():
            for raw in path.read_text(encoding="utf-8").splitlines():
                try:
                    stop = json.loads(raw)
                except ValueError:
                    continue
                if (isinstance(stop, dict) and stop.get("note") == number and stop.get("kind") == "question"
                        and plain(stop.get("question")) == plain(question)):
                    found = {"class": stop.get("class") if stop.get("class") in ("none", *RISK_CLASSES) else "unclassified",
                             "default": plain(stop.get("default"))}
        return found

    def stop_class(self, number: str, question: str) -> str:
        return self.stop(number, question)["class"]

    def sent_times(self) -> dict:
        path = self.records() / SENT
        try:
            found = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return found if isinstance(found, dict) else {}

    def keep(self, times: dict) -> None:
        folder = self.records()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / SENT).write_text(json.dumps(times, indent=1) + "\n", encoding="utf-8")

    def sent(self, number: str, question: str) -> float | None:
        value = self.sent_times().get(f"{number}: {plain(question)}")
        return float(value) if isinstance(value, (int, float)) else None

    def shown(self, number: str) -> float | None:
        """The last time `wait` put this note in front of him, whatever the question."""
        times = [t for key, t in self.sent_times().items()
                 if key.startswith(f"{number}: ") and isinstance(t, (int, float))]
        return float(max(times)) if times else None

    def mark_sent(self, number: str, question: str, again: bool = False) -> float:
        """When the question went to him. The first time stands, so the wait
        for a default cannot be started over; `again` is for a row he is shown
        once more."""
        times, key = self.sent_times(), f"{number}: {plain(question)}"
        if again or not isinstance(times.get(key), (int, float)):
            times[key] = now()
            self.keep(times)
        return float(times[key])

    def used(self) -> dict:
        found = self.sent_times().get(USED)
        return found if isinstance(found, dict) else {}

    def mark_used(self, claim: tuple[str, list[str]], what: str) -> None:
        """One sentence of his answers one question: keep what this one answered."""
        times = self.sent_times()
        when, parts = claim
        times.setdefault(USED, {}).setdefault(when, {}).update({part: what for part in parts})
        self.keep(times)

    def ruled_paths(self, number: str) -> list[str]:
        """Every path a ruling may change: the feature's folder, and the tests
        of the ruled note and of each note that follows the same ruling, as the
        note names them now, named them at the last commit, or names them from
        `cut/`. One commit applies a ruling, so the line `record` prints takes
        them all (review 2, N7: the tests stayed out and the ruling was stranded).
        A merged note's tests are not the ruling's: what it changes is a fix note."""
        import plan_check  # here, because plan_check imports this module
        folder = f"{CHANGES}/{self.name}"
        paths = [folder]
        entries = read(self.plan.read_text(encoding="utf-8"))[0]
        root = next((e["follows"] or number for e in reversed(entries) if e["number"] == number), number)
        merged = merged_notes(self.report_text())
        numbers = {n for n in {number, root, *(e["number"] for e in entries if e["follows"] == root)}
                   if n.isdigit() and n not in merged}
        texts = [path.read_text(encoding="utf-8") for where in (self.folder, self.folder / "cut")
                 for n in sorted(numbers) for path in sorted(where.glob(f"{n}-*.md"))]
        listed = subprocess.run(["git", "-C", str(self.tree), "ls-tree", "-r", "--name-only", "HEAD", "--", folder],
                                capture_output=True, text=True).stdout.splitlines()
        for path in listed:
            if path.rsplit("/", 1)[-1].split("-")[0] in numbers and path.endswith(".md"):
                texts.append(subprocess.run(["git", "-C", str(self.tree), "show", f"HEAD:{path}"],
                                            capture_output=True, text=True).stdout)
        for text in texts:
            for test in plan_check.read_note(text)["tests"]:
                tracked = subprocess.run(["git", "-C", str(self.tree), "ls-files", "--error-unmatch", "--", test],
                                         capture_output=True).returncode == 0
                if test not in paths and ((self.tree / test).exists() or tracked):
                    paths.append(test)
        return paths

    def commit_line(self, what: str, number: str = "") -> str:
        paths = " ".join(shlex.quote(path) for path in self.ruled_paths(number))
        return (f"commit it: git -C {self.tree} add -- {paths} && "
                f"git -C {self.tree} commit -m \"{what}\"")


def clock(seconds: float) -> str:
    return datetime.datetime.fromtimestamp(seconds).strftime("%H:%M:%S")


def shown_since(feature: Feature, number: str, name: str) -> float:
    """Since when a message of his answers this row: the last time `wait` put it in front of him."""
    since = feature.shown(number)
    if since is None:
        raise Refusal(f"{name} was not put in front of {feature.who} yet: `rulings.py wait {feature.name} --tree "
                      f"{feature.tree} --note {number}` records when. His answer is a message he types after that.")
    return since


def fix_note_faults(feature: Feature, number: str, touches: list[str]) -> list[str]:
    """Why no note `touches` names is a new fix note for merged note `number`;
    empty when one is. A fix note was not in the approved plan, is not merged
    or cut, and its `Waits for:` line names `number`: the merged note stays as
    it merged, and the change he ruled is built on top of it."""
    import plan_check  # here, because plan_check imports this module
    if not touches:
        return ["--touches names no note."]
    plan = f"{CHANGES}/{feature.name}/plan.md"
    approval = plan_check.approval_commit(feature.tree, plan, plan_check.approved_lines(
        feature.plan.read_text(encoding="utf-8")))
    if not approval:
        return [f"The `Approved:` line of {plan} is not committed, so no note is new since the approval."]
    rows, why = report_rows(feature.report_text()), []
    for touched in touches:
        found = sorted(feature.folder.glob(f"{touched}-*.md"))
        state = rows.get(touched, "")
        if len(found) != 1:
            why.append(f"Note {touched}: no file {CHANGES}/{feature.name}/{touched}-*.md, or more than one.")
            continue
        path = found[0].relative_to(feature.tree).as_posix()
        if state.startswith(("merged", "cut")):
            why.append(f"Note {touched} reads `{state}`.")
        elif subprocess.run(["git", "-C", str(feature.tree), "cat-file", "-e", f"{approval}:{path}"],
                            capture_output=True).returncode == 0:
            why.append(f"Note {touched} was in the approved plan.")
        elif number not in plan_check.read_note(found[0].read_text(encoding="utf-8"))["waits_for"]:
            why.append(f"Note {touched}: its `Waits for:` line does not name {number}.")
        else:
            return []
    return why


def standing(feature: Feature, number: str, kind: str, who: str, touches=()) -> tuple[bool, float | None]:
    """Refuse a ruling the note's row does not ask for. Returns whether the
    row goes back to `not started`, and since when a message of his answers
    it (None when the ruling is not in his name, or follows another).

    The class is the stop's, never the session's: `--kind` must be the class
    the agent typed. A default or a panel rules one question at a time, after
    the wait, each the classes `ruler_when_unanswered` gives it, and a default
    gives one re-arm per note; a waiting row, a cut and a stop with no class
    are his. So is a ruling on a merged note, which names its new fix note in
    `touches` and leaves the row `merged`."""
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
    if kind == SCREEN:
        screen_repair(feature, number, state, who)
        return True, None
    if state.startswith("merged"):
        merged = (f"{name} is merged, and a merged note is never edited or built again. Write a fix note with "
                  f"its own entry `[follows <nn>]`")
        if not his or kind not in ("none", *RISK_CLASSES):
            raise Refusal(f"{merged}. A ruling on a merged note is {feature.who}'s alone, of kind `none` or a "
                          f"risk class.")
        why = fix_note_faults(feature, number, touches)
        if why:
            raise Refusal(f"{merged}, and name it in --touches: a note that was not in the approved plan, is not "
                          f"merged or cut, and whose `Waits for:` line names {number}. {' '.join(why)}")
        return False, shown_since(feature, number, name)
    if FOLLOWS.match(kind):
        if state.startswith(("cut", "stopped:", "waiting:", "failed")):
            raise Refusal(f"{name} reads `{state}`: it takes a ruling of its own, not a follow-on.")
        return True, None
    if state.startswith("cut"):
        if not his:
            raise Refusal(f"only {feature.who} cuts a note.")
        return False, shown_since(feature, number, name)
    if state == "failed":
        if not his and kind != "re-arm":
            raise Refusal(f"{name} failed three strikes. A default gives it one re-arm, `--kind re-arm`; "
                          f"any other ruling on it is {feature.who}'s.")
        return True, shown_since(feature, number, name) if his else None
    if state.startswith("waiting:"):
        if not his:
            raise Refusal(f"{name} waits for {feature.who}: `{state}`. No default and no panel rules it.")
        why = state[len("waiting:"):].strip()
        cls = next((c for c in RISK_CLASSES if why.startswith(c + ":")), None)
        if kind not in ("none", *RISK_CLASSES) or (cls and kind != cls):
            raise Refusal(f"{name} waits on a [{cls or 'none or a risk class'}] question; `--kind {kind}` is not it.")
        return True, shown_since(feature, number, name)
    if state.startswith("stopped:") and not NOT_A_QUESTION.match(state):
        question = state[len("stopped:"):].strip()
        cls = feature.stop_class(number, question)
        if cls == "unclassified":
            if kind not in RISK_CLASSES or not his:
                raise Refusal(f"the stop of {name} has no class on record ({feature.records() / STOPS}), so it is "
                              f"a risk class and waits for {feature.who}. He names the class: one of "
                              f"{', '.join(RISK_CLASSES)}.")
        elif kind != cls:
            raise Refusal(f"the agent typed this stop of {name} as [{cls}]; `--kind {kind}` is not that class.")
        sent = feature.sent(number, question)
        if sent is None:
            raise Refusal(f"the question of {name} was not sent yet: `rulings.py wait {feature.name} --tree "
                          f"{feature.tree} --note {number}` first.")
        road = ruler_when_unanswered(cls)
        if not his and now() < sent + RULING_WAIT_SECONDS:
            raise Refusal(f"the question of {name} went out at {clock(sent)}. His answer rules until "
                          f"{clock(sent + RULING_WAIT_SECONDS)}; the {road} rules after that.")
        if not his and who in RULERS and who != road:
            raise Refusal(f"the `{road}` rules a [{cls}] question he did not answer, never the `{who}`"
                          + (f": `rulings.py panel {feature.name} --tree {feature.tree} --note {number}` prints "
                             f"its steps." if road == PANEL else "."))
        return True, sent if his else None
    raise Refusal(f"{name} did not stop on a question: its row reads `{state or 'no row'}`. A ruling settles a "
                  f"failed, stopped or waiting note; any other change after the approval is {feature.who}'s "
                  f"new `Approved:` line.")


def screen_repair(feature: Feature, number: str, state: str, who: str) -> None:
    """Refuse a `screen` ruling the row and the note do not bear out. The row
    is a tooling stop whose line holds the hook's refusal of a file in the
    route folder of a screen; the note's `Screens:` line now names each such
    screen, read as the hook reads it; and the note still passes the plan
    check's static reading, which asks a note that names a screen for an
    end-to-end done check. A note that lacks one waits for Abdul."""
    import note_check  # here, because both import this module
    import plan_check
    if who != "default":
        raise Refusal("a screen the commit hook named is a listed repair, recorded by `default`; he confirms it "
                      "at the gate.")
    screens = UNNAMED_SCREEN.findall(state) if state.startswith("stopped: tooling:") else []
    if not screens:
        raise Refusal(f"note {number} reads `{state or 'no row'}`. `--kind {SCREEN}` repairs only a tooling stop "
                      f"whose line holds the commit hook's refusal \"is in the route folder of screen `<s>`\".")
    found = sorted(feature.folder.glob(f"{number}-*.md"))
    if len(found) != 1:
        raise Refusal(f"changes/{feature.name}/{number}-*.md matches {len(found)} file(s), not one.")
    path = found[0].relative_to(feature.tree).as_posix()
    text = found[0].read_text(encoding="utf-8")
    design = feature.tree / note_check.DESIGN
    rows, _ = note_check.read_screens(design.read_text(encoding="utf-8") if design.is_file() else None)
    try:
        named = note_check.named_screens([{"path": path, "screens": note_check.read_note(text)["screens"]}], rows)
    except note_check.Refusal as error:
        raise Refusal(str(error))
    missing = [screen for screen in dict.fromkeys(screens) if screen not in named]
    if missing:
        raise Refusal(f"the `Screens:` line of {path} does not name {', '.join('`' + s + '`' for s in missing)}. "
                      f"Add each screen the hook named to that line first, then record the ruling.")
    static = plan_check.static_refusals(feature.tree, path, plan_check.read_note(text), None)
    if static:
        raise Refusal(f"{path} does not pass with the screen added: {' '.join(static)} This stop has no listed "
                      f"repair, so it waits for {feature.who}: `rulings.py wait {feature.name} --tree "
                      f"{feature.tree} --note {number} --why \"tooling: <its line>\"`.")


def record(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    named = opts.touches.strip()
    if named.startswith("Touches:"):  # the reader's last line, as it wrote it
        named = named[len("Touches:"):].strip()
    touches = [] if named.lower() == "none" else [t.strip() for t in named.split(",") if t.strip()]
    for value in (opts.question, opts.words, opts.undo):
        if "\n" in value or not value.strip():
            raise Refusal("a question, the words and the undo cost are one line each, and none is empty.")
    kind = opts.kind.strip()
    reset, since = standing(feature, opts.note, kind, opts.who, touches)
    state = report_rows(feature.report_text()).get(opts.note, "")
    # A ruling on a merged note answers no typed question, so the sentence
    # names the note, as a risk-class answer does.
    names = opts.note if kind in RISK_CLASSES or state.startswith("merged") else None
    if kind == SCREEN or (kind != "correction" and state.startswith("stopped:") and not NOT_A_QUESTION.match(state)):
        # The class, the wait and a panel's count are all read from the row's
        # question, so the page carries that question and no other (review 3,
        # fault 4: a panel's ruling went on the page under another question).
        asked = state[len("stopped:"):].strip()
        if plain(opts.question) != plain(asked):
            raise Refusal(f"note {opts.note} stopped on the question \"{asked}\", and `--question` is another "
                          f"text. The page carries the question that was asked, word for word.")
    claim = None
    if opts.who == feature.who and FOLLOWS.match(kind):
        # A follow-on in his name carries the words of the ruling it follows,
        # which were checked when that ruling was recorded, and no others.
        first = [e for e in read(feature.plan.read_text(encoding="utf-8"))[0]
                 if e["number"] == FOLLOWS.match(kind).group(1) and not e["follows"]]
        if not first or spoken(first[-1]["words"] or "") != spoken(opts.words):
            raise Refusal(f"a follow-on in {feature.who}'s name carries the words of the ruling it follows"
                          + (f", \"{first[-1]['words']}\"" if first else "") + ", and no others. What changed in "
                          f"this note goes in --question.")
    elif opts.who == feature.who:
        claim = said(opts.words, since, feature.who, feature.used(), names)
    more = panel_ruling(feature, opts.note, opts.words) if opts.who == PANEL and kind in RISK_CLASSES else ()
    lines = entry_text(opts.note, opts.kind, opts.date, opts.who, opts.question.strip(),
                       opts.words.strip().replace('"', "'"), touches, opts.undo.strip(), more)
    text = with_entry(feature.plan.read_text(encoding="utf-8"), lines)
    # A ruling that touches other notes is recorded before their follow-on
    # entries exist, so that one fault waits for the plan check at the restart.
    entries, found = read(text)
    found += [f for f in faults(entries, note_numbers(feature.folder), feature.who,
                                merged_notes(feature.report_text()), cut_notes(feature.report_text()))
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
    if claim:
        feature.mark_used(claim, f"note {opts.note}: {opts.question.strip()}")
    if more:
        conditions = [line[len(CONDITION):].strip() for line in more if line.startswith(CONDITION)]
        print(f"panel: {more[0][len('Panel:'):].strip()}. " + (
            f"Each of its {len(conditions)} condition(s) is a done check of note {opts.note}, word for word; the "
            f"plan check refuses the restart without them." if conditions else "The readers gave it no condition."))
    print(feature.commit_line(f"ruling: note {opts.note}", opts.note))
    return 0


def notice(feature: str, number: str, cls: str, question: str, default: str) -> str:
    """The question as it goes to his phone, with its written default. A
    risk-class question shows the form its answer must have (`names_line`),
    with the note's own number."""
    if cls not in RISK_CLASSES:
        return f"{feature} {number}: {closed(question)} Default: {closed(default)}"
    return (f"{feature} {number}: [{cls}] {closed(question)} Default (A): {closed(default)} To answer, start your "
            f"message with \"{number}:\", for example \"{number}: A\" or \"{number}: <your own road>\".")


def wait(opts) -> int:
    """The question goes to Abdul now. A class a default or a panel rules
    keeps its row, and that one rules after the wait; any other row waits for
    him, and so does a stop with no written default: a default that nobody
    wrote rules nothing, and the session writes no answer of its own."""
    feature = Feature(opts.tree, opts.feature)
    state = report_rows(feature.report_text()).get(opts.note)
    why = (opts.why or "").strip()
    if "\n" in why or "|" in why:
        raise Refusal("--why is one line with no `|`.")
    # The final check has a row only once it stopped or waited. A final check
    # that no run finishes has none, and it waits for him all the same.
    adds = state is None and opts.note == FINAL and bool(why) and feature.report.is_file()
    if state is None and not adds:
        raise Refusal(f"{feature.report} has no row for note {opts.note}.")
    state = state or ""
    if state.startswith("stopped:") and not NOT_A_QUESTION.match(state):
        question = state[len("stopped:"):].strip()
        stop = feature.stop(opts.note, question)
        cls = stop["class"]
        sent = feature.mark_sent(opts.note, question)
        road = ruler_when_unanswered(cls)
        if road in RULERS and not stop["default"]:
            return to_him(feature, opts.note, cls, question, f"The stop carries no written default, so neither a "
                          f"default nor a panel rules it: it waits for {feature.who}.")
        if road in RULERS:
            print(f"note {opts.note}: [{cls}] sent at {clock(sent)}. His answer rules until "
                  f"{clock(sent + RULING_WAIT_SECONDS)}; after that the {road} rules ("
                  + (f"`rulings.py record --kind {cls} --who default`" if road == "default" else
                     f"`rulings.py panel {feature.name} --tree {feature.tree} --note {opts.note}`") + ").")
            print(f"notice: {notice(feature.name, opts.note, cls, question, stop['default'])}")
            return 0
        why = f"{cls}: {question}"
    elif not why:
        if NOT_A_QUESTION.match(state):
            raise Refusal(f"note {opts.note} reads `{state}`, which asks him nothing. To make it wait for him, "
                          f"say why with --why.")
        # A failed row, a waiting row, a note he may cut, or a merged note he
        # rules on: he is shown it now, and only a message he types after this
        # answers it. The row stays as it is.
        at = feature.mark_sent(opts.note, "shown", again=True)
        if state.startswith("merged"):
            print(f"note {opts.note}: `{state}` shown at {clock(at)}. His ruling on it is a message he types after "
                  f"this that starts with \"{opts.note}:\", and it is built as a new fix note that waits for "
                  f"{opts.note}: `record --note {opts.note} --touches <the fix note>`.")
            return 0
        print(f"note {opts.note}: `{state}` shown at {clock(at)}. His answer is a message he types after this, and "
              f"his answer to a risk-class question starts with \"{opts.note}:\"; to make the row wait for him, say "
              f"why with --why.")
        return 0
    else:
        feature.mark_sent(opts.note, why)
    if not feature.set_row(opts.note, f"waiting: {why}", add=adds):
        raise Refusal(f"{feature.report} has no notes table to hold the row `{opts.note}`.")
    print(f"note {opts.note}: waiting: {why}")
    print(feature.commit_line(f"report: note {opts.note} waits"))
    return 0


# ── The panel's files and its command ───────────────────────────────────────

def panel_dir(feature: Feature, number: str, question: str) -> pathlib.Path:
    """The folder of one stop's panel. The feature and the question name it,
    so the files of one question are never read as the files of the note's
    next one, and its name is the key each agent's label carries."""
    if not re.fullmatch(NUMBER, number):
        raise Refusal(f"`{number}` is not a note number or `final`.")
    key = hashlib.sha1(f"{feature.name}\n{plain(question)}".encode("utf-8")).hexdigest()[:10]
    return feature.records() / PANEL / f"{number}-{key}"


def panel_files(folder: pathlib.Path, default: str) -> tuple[list[dict] | None, dict[str, dict], dict[str, str]]:
    """What a panel's folder holds so far: the roads (none before the finder
    wrote its answer), one vote per reader's file, and for each reader's file
    that holds no vote the reason."""
    path = folder / FINDER
    if not path.is_file():
        return None, {}, {}
    try:
        roads = read_roads(default, json.loads(path.read_text(encoding="utf-8")))
    except ValueError as error:
        raise Refusal(f"{path} is not JSON ({error}). The road finder writes it again.")
    except Refusal as error:
        raise Refusal(f"{path} is not the finder's typed answer: {error} The road finder writes it again.")
    votes, slips = {}, {}
    for seat in SEATS:
        if not (folder / f"{seat}.md").is_file():
            continue
        try:
            votes[seat] = read_vote((folder / f"{seat}.md").read_text(encoding="utf-8"), roads)
        except Refusal as error:
            slips[seat] = f"the file of the reader {seat} holds no vote: {error}"
    return roads, votes, slips


def label(key: str, seat: str | None = None) -> str:
    """The description an agent of the panel is spawned with; `panel_agents`
    finds its transcript by it. `key` is the name of the panel's folder."""
    return f"panel {key}: reader {seat}" if seat else f"panel {key}: finder"


def panel_agents(folder: pathlib.Path) -> dict[str, str]:
    """What is wrong with the run of each of one panel's four agents, read
    from their transcripts among this session's subagents.

    An agent is found by its agent type and its label. The label carries the
    name of the panel's folder, so the agents of another question, another
    note or another feature are never this panel's (review 3, fault 3). The
    newest wins when a label ran twice. Wrong are: no transcript; a model
    that is not PANEL_MODEL, for the finder and for each reader, since the
    override is one word at the spawn and nothing else shows that it was left
    out; and a reader's transcript that names another seat's answer file by
    its path, since a reader judges alone (review 3, fault 6)."""
    session = os.environ.get(SESSION, "")
    if not re.fullmatch(r"[0-9A-Za-z-]{8,}", session):
        raise Refusal(f"${SESSION} is not set, so the transcripts of the panel's agents cannot be found. Run the "
                      f"command from the session that spawned them.")
    key = folder.name
    wanted = {"finder": ("build-feature-road-finder", label(key)),
              **{seat: ("panel-review-persona", label(key, seat)) for seat in SEATS}}
    found, wrong = {}, {}
    metas = sorted(PROJECTS.glob(f"*/{session}/subagents/agent-*.meta.json"), key=lambda path: path.stat().st_mtime)
    for path in metas:
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        kind = str(meta.get("agentType") or "").removeprefix("workflow:")
        for name, (agent, text) in wanted.items():
            if kind == agent and plain(meta.get("description")) == text:
                found[name] = str(path)[:-len(".meta.json")] + ".jsonl"
    for name, (agent, text) in wanted.items():
        who = "road finder" if name == "finder" else f"reader {name}"
        if name not in found:
            wrong[name] = f"this session spawned no agent `workflow:{agent}` with the description \"{text}\""
            continue
        try:
            raw = pathlib.Path(found[name]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw = ""
        model = ""
        for line in raw.splitlines():
            if '"assistant"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("type") == "assistant":
                model = str((rec.get("message") or {}).get("model") or "")
                if model:
                    break
        others = [seat for seat in SEATS if name in SEATS and seat != name and f"{key}/{seat}.md" in raw]
        if PANEL_MODEL not in model:
            wrong[name] = (f"the {who} ran on `{model or 'no model on record'}`, and a panel's agents run on "
                           f"{PANEL_MODEL}")
        elif others:
            wrong[name] = f"the transcript of the {who} names the answer file of the reader {', '.join(others)}"
    return wrong


def panel_ruling(feature: Feature, number: str, words: str) -> list[str]:
    """What `record --who panel` adds to the entry. Refused unless the panel's
    files for this stop are all there, each reader's file holds a vote, the
    four agents ran in this session as `panel_agents` asks, the count gives a
    road, and `words` are that road.
    `standing` checked the row, the class and the wait before this."""
    name = f"note {number}" if number != FINAL else "the final check"
    question = report_rows(feature.report_text()).get(number, "")[len("stopped:"):].strip()
    folder = panel_dir(feature, number, question)
    again = f"`rulings.py panel {feature.name} --tree {feature.tree} --note {number}` prints the step that is next."
    roads, votes, slips = panel_files(folder, feature.stop(number, question)["default"])
    if roads is None:
        raise Refusal(f"the panel of {name} has no files for this question: {folder / FINDER} is missing. {again}")
    missing = [seat for seat in SEATS if seat not in votes and seat not in slips]
    if missing:
        raise Refusal(f"the panel of {name} is not complete: {folder} holds no file of the reader "
                      f"{', '.join(missing)}. {again}")
    wrong = {**panel_agents(folder), **slips}
    if wrong:
        raise Refusal(f"the panel of {name} is not sound: {'; '.join(wrong.values())}. {again}")
    result = count(votes)
    if result["outcome"] == "hold":
        raise Refusal(f"no road rules ({result['mark']}), and {name} waits for {feature.who}. {again}")
    road = next(r for r in roads if r["id"] == result["road"])
    if plain(words).replace('"', "'") != road["road"].replace('"', "'"):
        raise Refusal(f"the count gives road {road['id']}: \"{road['road']}\" ({result['mark']}). `--words` is "
                      f"that road, word for word; a panel rules nothing else.")
    conditions = []
    for seat in result["seats"]:
        conditions += [c for c in votes[seat]["conditions"] if c not in conditions]
    return [f"Panel: {result['mark']}, files {folder.name}", *[f"{CONDITION} {c}" for c in conditions]]


def road_lines(roads: list[dict], who: str | None) -> list[str]:
    """Each road as a reader sees it, with its id."""
    lines = []
    for road in roads:
        if road["kind"] != "found":
            what = "the written default" if road["kind"] == "default" else "offered by the question"
            lines.append(f"{road['id']} ({what}): {closed(road['road'])}"
                         + (f" Its cost, as the road finder states it: {closed(road['cost'])}" if road["cost"] else ""))
            continue
        lines.append(f"{road['id']} (a road the question did not offer): {closed(road['road'])} "
                     f"Files: {', '.join(road['files'])}. Evidence: {', '.join(road['evidence'])}. "
                     f"Why it beats the offered roads: {closed(road['beats'])} Where it fails: {closed(road['fails'])} "
                     f"What it costs to undo: {closed(road['undo'])}"
                     + (f" It needs a fact only {who or 'the human'} can get: {closed(road['needs_owner_fact'])} "
                        f"No reader rules this road: a vote for it counts as a hold on that fact."
                        if road["needs_owner_fact"] else ""))
    return lines


def stop_lines(feature: Feature, number: str, cls: str, question: str, default: str) -> list[str]:
    """The typed stop and where to read, for the finder and for each reader."""
    folder = feature.folder
    note = (f"The note: {folder}/{number}-*.md" if number != FINAL else
            f"The final check asked it: read `## Final check` in the report.")
    return [f"Class: {cls}", f"Question: {question}", f"Written default: {default}", "",
            f"Feature worktree: {feature.tree}", note, f"The plan page: {feature.plan}",
            f"The report: {feature.report}", f"The reject reports: {feature.records()}",
            f"The core design: {feature.tree / 'docs' / 'design.md'}"]


def to_him(feature: Feature, number: str, cls: str, question: str, why: str) -> int:
    """A question nobody rules for him: its row waits for Abdul."""
    feature.set_row(number, f"waiting: {cls}: {question}")
    print(f"note {number}: waiting: {cls}: {question}")
    print(f"  {why}")
    print(feature.commit_line(f"report: note {number} waits"))
    return 0


def panel(opts) -> int:
    """The next step of the panel on one stopped risk question: the finder,
    then the three readers, then the count. It writes each agent's brief into
    the panel's folder and prints the spawn; the agents write their own files.
    A panel that is not sound runs once more, from clean answers; a second
    fault makes the question wait for Abdul."""
    feature = Feature(opts.tree, opts.feature)
    number = opts.note
    state = report_rows(feature.report_text()).get(number, "")
    if not state.startswith("stopped:") or NOT_A_QUESTION.match(state):
        raise Refusal(f"note {number} reads `{state or 'no row'}`. A panel rules a note that stopped on a question "
                      f"in a risk class, after the wait for {feature.who}.")
    question = state[len("stopped:"):].strip()
    stop = feature.stop(number, question)
    cls, default = stop["class"], stop["default"]
    standing(feature, number, cls, PANEL)
    entries = read(feature.plan.read_text(encoding="utf-8"))[0]
    without = sum(1 for e in entries if e["number"] == number and e["who"] in RULERS
                  and e["kind"] in ("none", *RISK_CLASSES))
    if without >= MAX_DEFAULT_RULINGS:
        return to_him(feature, number, cls, question, f"{MAX_DEFAULT_RULINGS} questions of {number} took a ruling "
                      f"without {feature.who} already, so no panel runs: this one waits for him.")
    folder = panel_dir(feature, number, question)
    folder.mkdir(parents=True, exist_ok=True)
    roads, votes, slips = panel_files(folder, default)
    head = f"panel: note {number} [{cls}]"
    again = "Then run this command again."
    written = [seat for seat in SEATS if seat in votes or seat in slips]
    if 0 < len(written) < len(SEATS):
        # Each agent reports back on its own, so a call can come while a
        # reader still writes. That is no fault, and it changes no state: two
        # early calls sent a sound panel's question to him (review 4, note C).
        print(f"{head}: readers still run: call again when all three have returned. No file yet of the reader "
              f"{', '.join(seat for seat in SEATS if seat not in written)}.")
        return 0
    # The agents are checked before the count is shown, so no note changes on
    # a panel whose agents did not run as asked.
    wrong = slips or (panel_agents(folder) if written else {})
    if wrong:
        # No reader runs again beside the answers of the first round: all
        # three go, and all three run again, once (review 3, faults 2 and 6).
        why = "; ".join(wrong.values())
        if (folder / SECOND).exists():
            return to_him(feature, number, cls, question, f"The panel ran twice and is not sound: {why}. It runs "
                          f"no third time: the question waits for {feature.who}.")
        (folder / SECOND).touch()
        for seat in SEATS:
            (folder / f"{seat}.md").unlink(missing_ok=True)
        if "finder" in wrong:
            (folder / FINDER).unlink(missing_ok=True)
            roads = None
        written = []
        print(f"{head} is not sound: {why}. The three readers' answers are removed"
              + (", and the finder's answer" if roads is None else "") + f", and the panel runs once more. After a "
              f"second fault the question waits for {feature.who}.")
    if roads is None:
        (folder / "finder.brief.md").write_text("\n".join([
            f"# Road finder: {feature.name}, {number}", "",
            f"A run stopped on this question, and {feature.who} did not answer in time.", "",
            *stop_lines(feature, number, cls, question, default), "",
            f"Write your answer to {folder / FINDER}, in the form your brief gives, and write nothing else."]) + "\n",
            encoding="utf-8")
        print(f"{head}, step 1 of 3: the road finder")
        print(f"  one agent: subagent_type workflow:build-feature-road-finder, description \"{label(folder.name)}\"")
        print(f"  prompt: Read {folder / 'finder.brief.md'} and do what it says.")
        print(f"  It writes {folder / FINDER}. {again}")
        return 0
    if not written:
        who = feature.who or "the human"
        for seat, (title, lens) in SEATS.items():
            (folder / f"{seat}.brief.md").write_text("\n".join([
                f"# Reader, {title}: {feature.name}, {number}", "", lens.format(who=who), "",
                f"A run stopped on one question, and {who} did not answer in time. You and two other "
                f"readers judge every road below on equal terms: the written default, the roads the question "
                f"offers and the roads a finder found. You judge alone. You do not see the other readers' answers "
                f"and you do not look for them: a reader whose transcript names another reader's file is refused, "
                f"and all three run again.", "",
                *stop_lines(feature, number, cls, question, default), "", "## The roads", "",
                *road_lines(roads, feature.who), "",
                "Read the note, the plan page and the code before you judge. Each claim of yours cites "
                "`file:line`. State no number you did not read.", "", "## Your answer", "",
                f"Write one file, {folder / f'{seat}.md'}, and write nothing else. The form below is the whole "
                f"form of that file and of what you return. {REPLACES}: no verdict lines, no list of issues, no "
                f"cuts, no invariant marks and no scenario walk.", "",
                "Line 1 is your vote. It is exactly one of these two forms, with no bold, no quotation marks and "
                "nothing after it:", "",
                "Rule: <one road id from the list above, such as A or F1>",
                "Hold: <the one fact that must be measured before any road is safe>", "",
                "A file whose line 1 is anything else is refused, and all three readers run again. `Rule:` for a "
                f"road that needs a fact only {who} can get counts as `Hold:` on that fact.", "",
                "From line 2: your reason, a few sentences in one paragraph.", "",
                f"After the reason: at most {MAX_CONDITIONS} lines `Condition: <test file>: <test title, and what "
                "it proves>`. Each is a named test that fails on today's code; the note takes it as a done check "
                "when your road rules. A file with no condition is complete.", "",
                "Return line 1 of your file as your answer, and nothing else."]) + "\n", encoding="utf-8")
        print(f"{head}, step 2 of 3: the three readers. Spawn the three below in one message, so they run at the "
              f"same time, and show no reader another reader's answer.")
        print(f"  each: subagent_type workflow:panel-review-persona, model {PANEL_MODEL}")
        for seat in SEATS:
            print(f"  description \"{label(folder.name, seat)}\"; prompt: Read {folder / f'{seat}.brief.md'} and do "
                  f"what it says.")
        print(f"  Each writes its own file in {folder}. Run this command again when all three have returned.")
        return 0
    result = count(votes)
    print(f"{head}, step 3 of 3: the count")
    for seat, vote in votes.items():
        print(f"  {seat}: {vote['first']}" + (" (a hold: that road needs a fact only he can get)"
                                               if vote["kind"] == "hold" and RULE.match(vote["first"]) else ""))
    for road in roads:
        if road.get("needs_owner_fact"):
            print(f"  candidate road {road['id']}, \"{road['road']}\", needs a fact from {feature.who}: "
                  f"{road['needs_owner_fact']}")
    if result["outcome"] == "hold":
        facts = "; ".join(votes[seat]["fact"] for seat in result["seats"])
        return to_him(feature, number, cls, question, f"No road rules ({result['mark']})."
                      + (f" To measure first: {facts}." if facts else "") + " Write the question"
                      + (" and these facts" if facts else "") + " under Decide in the pending file.")
    road = next(r for r in roads if r["id"] == result["road"])
    conditions = []
    for seat in result["seats"]:
        conditions += [c for c in votes[seat]["conditions"] if c not in conditions]
    print(f"  count: {result['mark']}: \"{road['road']}\"")
    for condition in conditions:
        print(f"  condition, a done check of the note: {condition}")
    print(f"  Change the note inside that road, run the ruling reader, then record it: python3 {__file__} record "
          f"{feature.name} --tree {feature.tree} --note {number} --kind {shlex.quote(cls)} --who {PANEL} --question "
          f"{shlex.quote(question)} --words {shlex.quote(road['road'])} --touches <the reader's line> --undo "
          + (shlex.quote(road["undo"]) if road["kind"] == "found" else "\"<what reversing it costs>\""))
    return 0


def show(opts) -> int:
    """The gate list. Printing it records the time: his answers are the
    messages he types after he was shown it."""
    feature = Feature(opts.tree, opts.feature)
    entries = feature.checked(feature.plan.read_text(encoding="utf-8"))
    cut = cut_notes(feature.report_text())
    waiting = open_entries(entries, feature.who, cut)
    print(f"{len(waiting)} ruling(s) to confirm, of "
          f"{sum(1 for e in entries if needs_answer(e, entries, feature.who, cut))} he did not make himself")
    for line in away_lines(entries, feature.who, open_only=True, records=feature.records(), cut=cut):
        print(f"- {line}")
    if waiting:
        times = feature.sent_times()
        times[GATE] = now()
        feature.keep(times)
        risk = [e["number"] for e in waiting if is_risk(e, entries)]
        print(f"shown at {clock(times[GATE])}. An answer is a message he types after this: one sentence such as "
              f"\"confirm all\" for the lines outside the risk classes"
              + (f", and for each line in bold one sentence that starts with its number and a colon, as in "
                 f"\"{risk[0]}: confirm\"" if risk else "") + ".")
    return 0


def answer(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    text = feature.plan.read_text(encoding="utf-8")
    entries = feature.checked(text)
    cut = cut_notes(feature.report_text())
    waiting = open_entries(entries, feature.who, cut)
    words = (opts.words or "").strip()
    if not words:
        raise Refusal(f"an answer carries {feature.who}'s own words: --words \"<what he typed>\".")
    since = feature.sent_times().get(GATE)
    if not isinstance(since, (int, float)):
        raise Refusal(f"the list was not shown to {feature.who} yet: `rulings.py list {feature.name} --tree "
                      f"{feature.tree}` prints it and records when. An answer is a message he types after that.")
    if opts.all:
        chosen = [e for e in waiting if not is_risk(e, entries) and not e["confirmed"]]
        if not chosen:
            raise Refusal("no line outside the risk classes waits for an answer.")
        claim = said(words, since, feature.who, feature.used())
        what = "the lines outside the risk classes"
    else:
        chosen = [e for e in waiting if e["number"] == opts.note][:1]
        if not chosen:
            raise Refusal(f"note {opts.note} has no ruling that waits for an answer.")
        if opts.overturned:
            if not opts.fix:
                raise Refusal("an overturned ruling needs --fix, the number of the fix note that undoes it.")
            state = report_rows(feature.report_text()).get(opts.fix, "")
            if state.startswith(("merged", "cut")):
                raise Refusal(f"note {opts.fix} reads `{state}`. An overturned ruling closes on a new fix "
                              f"note that the run still builds.")
        claim = said(words, since, feature.who, feature.used(), opts.note if is_risk(chosen[0], entries) else None)
        what = f"line {opts.note} of the gate list"
    words = words.replace('"', "'")
    lines = ([f'Overturned: {opts.date}, "{words}"', f"Fix: {opts.fix}"] if opts.overturned and not opts.all
             else [f'Confirmed: {opts.date}, "{words}"'])
    for entry in sorted(chosen, key=lambda e: -e["line"]):
        text = with_sub_lines(text, entry, lines)
    left = open_entries(feature.checked(text), feature.who, cut)
    feature.plan.write_text(text, encoding="utf-8")
    feature.mark_used(claim, what)
    print(f"answered: {', '.join(e['number'] for e in chosen) or 'none'}; {len(left)} ruling(s) still wait"
          + (f": {', '.join(e['number'] for e in left)}" if left else ""))
    print(feature.commit_line("rulings: answered"))
    return 0


def main(argv=None) -> int:
    today = datetime.date.today().isoformat()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ruler").add_argument("kind")
    for name in ("record", "wait", "panel", "list", "answer"):
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
            print(f"{road} after {RULING_WAIT_SECONDS} s" if road in RULERS else road)
            return 0
        if opts.command == "answer" and not opts.all and not (opts.note and (opts.confirmed or opts.overturned)):
            raise Refusal("answer takes --all, or --note with --confirmed or --overturned.")
        return {"record": record, "wait": wait, "panel": panel, "list": show, "answer": answer}[opts.command](opts)
    except Refusal as error:
        print(f"REFUSED: {error}")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
