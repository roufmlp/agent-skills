#!/usr/bin/env python3
"""The rulings of a feature: what was decided while a run was stopped, by whom,
and whether Abdul has confirmed it.

    python3 ~/.claude/skills/workflow/lib/rulings.py ruler <class>
    python3 ~/.claude/skills/workflow/lib/rulings.py record <feature> --tree <feature worktree> --note <nn> \\
        --kind <kind> --who <who> --question <text> --words <text> --touches <none|nn,nn> --undo <text>
    python3 ~/.claude/skills/workflow/lib/rulings.py wait <feature> --tree <feature worktree> --note <nn> --why <text>
    python3 ~/.claude/skills/workflow/lib/rulings.py list <feature> --tree <feature worktree>
    python3 ~/.claude/skills/workflow/lib/rulings.py answer <feature> --tree <feature worktree> \\
        (--all | --note <nn> (--confirmed | --overturned --fix <nn>) [--words <text>])

A run that stops on a question no longer waits for an interview. The session
that started it sends the question to Abdul's phone and waits
RULING_WAIT_SECONDS. His answer rules when it comes in time; otherwise
`ruler_when_unanswered` says who does. The session then changes the note
inside the ruling, records it here and starts the run again. Every ruling he
did not make himself is shown to him once, before the merge into local main.

## The part of the plan this reads

`changes/<feature>/plan.md` carries the rulings under `## Rulings`, above the
`Approved:` lines. One entry per ruled note:

    - [<kind>] <nn>: <the question, in plain words>
      Ruled: <date>, <who>, "<the words of the ruling>"
      Touches: <none, or the numbers of the other notes the ruling changes>
      Undo: <what reversing it costs>
      Confirmed: <date>[, "<his words>"]
      Overturned: <date>, "<his words>"
      Fix: <the number of the fix note that undoes an overturned ruling>

`<kind>` is `none`, a risk class (`money`, `access`, `migration`, `data
leaving`), `re-arm` (the one automatic second try of a note that failed three
strikes) or `follows <nn>` (a note the ruling on `<nn>` touched, or the fix
note written for it). `<who>` is `default`, `panel`, or the first word of
`git config user.name`, which is how the page names Abdul.

## What refuses

`read` places every line of the part or reports it; `faults` then refuses:

- an entry with no `Ruled:` line, or with no `Touches:` line;
- a kind or a who it does not know;
- a ruling Abdul did not make whose who is not the one `ruler_when_unanswered`
  names for its class, so a `default` never rules a risk class;
- `Touches:` naming a note that is not in the feature, or a touched note with
  no `follows` entry of its own; a touched note that is merged is never
  edited, so it needs a `follows` entry on a fix note instead;
- `follows <nn>` when `<nn>` has no ruling;
- a second `re-arm` for one note;
- both answers on one entry, or `Overturned:` with no `Fix:` naming a note.

`open_entries` is the gate before local main: each ruling by `default` or
`panel` with no `Confirmed:` or `Overturned:` line. A risk-class line counts
as confirmed only when the line carries his words, so one "confirm all" cannot
close it. `plan_check.py` and the `pre-merge-commit` hook (`note_check.py
merge`) both call it.

Exit 0 on success, 3 with `REFUSED: <why>`.
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import subprocess
import sys

# How long the starting session waits for Abdul's answer before the default
# rules. The one place this number lives: `ruler` prints it and
# `feature_run.py args` passes it on.
RULING_WAIT_SECONDS = 900
RISK_CLASSES = ("money", "access", "migration", "data leaving")
KINDS = ("none", *RISK_CLASSES, "re-arm")
RULERS = ("default", "panel")
HEADING = "## Rulings"
REFUSED = 3
CHANGES = "changes"

ENTRY = re.compile(r"^- \[([^\]]+)\]\s*(\d+):\s*(\S.*)$")
FOLLOWS = re.compile(r"^follows (\d+)$")
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
    if kind in ("none", "re-arm"):
        return "default"
    return "wait"


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
    entries, faults, entry = [], [], None
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
            continue
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

def class_of(entry: dict, entries: list[dict]) -> str:
    """An entry's class; a follow-on takes the class of the ruling it follows."""
    seen = set()
    while entry["follows"] and entry["number"] not in seen:
        seen.add(entry["number"])
        first = next((e for e in entries if e["number"] == entry["follows"] and not e["follows"]), None)
        if first is None:
            break
        entry = first
    return entry["kind"]


def is_risk(entry: dict, entries: list[dict]) -> bool:
    return class_of(entry, entries) in RISK_CLASSES


def faults(entries: list[dict], numbers: set[str], who: str | None, merged=frozenset()) -> list[str]:
    """Every reason the rulings do not hold together. `numbers` are the notes
    of the feature, `who` is `person()`, `merged` the notes already merged."""
    found = []
    ruled = {e["number"] for e in entries if not e["follows"]}
    rearmed = set()
    for e in entries:
        name = f"ruling [{e['kind']}] {e['number']}"
        if e["kind"] not in KINDS and not e["follows"]:
            found.append(f"{name}: [{e['kind']}] is not a kind. The kinds are "
                         f"{', '.join(KINDS)} and `follows <nn>`.")
        if e["follows"] and e["follows"] not in ruled:
            found.append(f"{name}: `follows {e['follows']}` names a note with no ruling of its own.")
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
        if e["touches"] is None:
            found.append(f"{name} has no `Touches:` line. One reader names the notes each ruling "
                         f"touches: `Touches: none` or `Touches: 06, 09`.")
        for number in e["touches"] or []:
            if number not in numbers or number == e["number"]:
                found.append(f"{name}: `Touches: {number}` names no other note of the feature.")
            elif number in merged:
                if not any(f["follows"] == e["number"] and f["number"] not in merged for f in entries):
                    found.append(f"{name}: note {number} is merged, and a merged note is never edited. "
                                 f"Write a fix note with its own entry `[follows {e['number']}]`.")
            elif not any(f["number"] == number and f["follows"] == e["number"] for f in entries):
                found.append(f"{name}: note {number} is touched and has no entry "
                             f"`[follows {e['number']}] {number}` of its own.")
        if e["kind"] == "re-arm":
            if e["number"] in rearmed:
                found.append(f"{name}: a note gets one re-arm. Its second failure waits for {who}.")
            rearmed.add(e["number"])
        if e["confirmed"] and e["overturned"]:
            found.append(f"{name} carries both `Confirmed:` and `Overturned:`.")
        if e["overturned"]:
            if not e["fix"]:
                found.append(f"{name} is overturned and has no `Fix:` line naming its fix note.")
            elif e["fix"] not in numbers:
                found.append(f"{name}: `Fix: {e['fix']}` names no note of the feature.")
    return found


def needs_answer(entry: dict) -> bool:
    """Abdul confirms what he did not rule himself; a follow-on is answered
    with the ruling it follows."""
    return entry["who"] in RULERS and not entry["follows"]


def answered(entry: dict, entries: list[dict]) -> bool:
    if entry["overturned"]:
        return bool(entry["fix"])
    if not entry["confirmed"]:
        return False
    return bool(entry["confirmed"]["words"]) or not is_risk(entry, entries)


def open_entries(entries: list[dict], who: str | None = None) -> list[dict]:
    """The gate before local main: each ruling that still waits for his answer."""
    return [e for e in entries if needs_answer(e) and not answered(e, entries)]


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


def away_lines(entries: list[dict], who: str | None = None) -> list[str]:
    """The report's "Ruled while you were away" lines, risk classes first."""
    shown = [e for e in entries if needs_answer(e)]
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


def merged_notes(report_text: str) -> set[str]:
    found, columns = set(), None
    for line in report_text.splitlines():
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
        elif columns and len(cells) >= 2 and cells[1].startswith("merged"):
            found.add(cells[0])
    return found


class Feature:
    """The plan and the report of one feature in one tree."""

    def __init__(self, tree: str, feature: str):
        self.tree = pathlib.Path(tree)
        self.folder = self.tree / CHANGES / feature
        self.plan = self.folder / "plan.md"
        self.report = self.folder / "report.md"
        if not self.plan.is_file():
            raise Refusal(f"{self.plan} does not exist.")
        self.who = person(self.tree)

    def checked(self, text: str) -> list[dict]:
        """The entries of `text`, refused when they do not hold together."""
        entries, found = read(text)
        report = self.report.read_text(encoding="utf-8") if self.report.is_file() else ""
        found += faults(entries, note_numbers(self.folder), self.who, merged_notes(report))
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

    def commit_line(self, what: str) -> str:
        return (f"commit it: git -C {self.tree} add {CHANGES}/{self.folder.name} && "
                f"git -C {self.tree} commit -m \"{what}\"")


def record(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    named = opts.touches.strip()
    if named.startswith("Touches:"):  # the reader's last line, as it wrote it
        named = named[len("Touches:"):].strip()
    touches = [] if named.lower() == "none" else [t.strip() for t in named.split(",") if t.strip()]
    for value in (opts.question, opts.words, opts.undo):
        if "\n" in value or not value.strip():
            raise Refusal("a question, the words and the undo cost are one line each, and none is empty.")
    lines = entry_text(opts.note, opts.kind, opts.date, opts.who, opts.question.strip(),
                       opts.words.strip().replace('"', "'"), touches, opts.undo.strip())
    text = with_entry(feature.plan.read_text(encoding="utf-8"), lines)
    # A ruling that touches other notes is recorded before their follow-on
    # entries exist, so that one fault waits for the plan check at the restart.
    entries, found = read(text)
    report = feature.report.read_text(encoding="utf-8") if feature.report.is_file() else ""
    found += [f for f in faults(entries, note_numbers(feature.folder), feature.who, merged_notes(report))
              if "is touched and has no entry" not in f and "is merged, and a merged note" not in f]
    if found:
        raise Refusal("\n  ".join(found))
    feature.plan.write_text(text, encoding="utf-8")
    reset = feature.set_row(opts.note, "not started", 0)
    print(f"ruling: [{opts.kind}] {opts.note} by {opts.who} written to {feature.plan}"
          + ("; its report row reads `not started` with no strike" if reset else "; the report has no row for it"))
    if touches:
        print(f"touched: {', '.join(touches)}. Each needs its own `[follows {opts.note}]` entry "
              f"(a merged one: a fix note) before the restart.")
    print(feature.commit_line(f"ruling: note {opts.note}"))
    return 0


def wait(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    if "\n" in opts.why or "|" in opts.why or not opts.why.strip():
        raise Refusal("--why is one line with no `|`.")
    if not feature.set_row(opts.note, f"waiting: {opts.why.strip()}"):
        raise Refusal(f"{feature.report} has no row for note {opts.note}.")
    print(f"note {opts.note}: waiting: {opts.why.strip()}")
    print(feature.commit_line(f"report: note {opts.note} waits"))
    return 0


def show(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    entries = feature.checked(feature.plan.read_text(encoding="utf-8"))
    waiting = open_entries(entries)
    print(f"{len(waiting)} ruling(s) to confirm, of {sum(1 for e in entries if needs_answer(e))} "
          f"made by default or panel")
    for line in away_lines(waiting):
        print(f"- {line}")
    return 0


def answer(opts) -> int:
    feature = Feature(opts.tree, opts.feature)
    text = feature.plan.read_text(encoding="utf-8")
    entries = feature.checked(text)
    waiting = open_entries(entries)
    if opts.all:
        chosen = [e for e in waiting if not is_risk(e, entries) and not e["confirmed"]]
        lines = [f"Confirmed: {opts.date}"]
    else:
        chosen = [e for e in waiting if e["number"] == opts.note]
        if not chosen:
            raise Refusal(f"note {opts.note} has no ruling that waits for an answer.")
        chosen = chosen[:1]
        words = (opts.words or "").strip().replace('"', "'")
        if opts.overturned:
            if not words or not opts.fix:
                raise Refusal("an overturned ruling needs --words, his words, and --fix, the number "
                              "of the fix note that undoes it.")
            lines = [f'Overturned: {opts.date}, "{words}"', f"Fix: {opts.fix}"]
        elif is_risk(chosen[0], entries) and not words:
            raise Refusal(f"ruling {opts.note} is in a risk class: it needs --words, his own answer.")
        else:
            lines = [f"Confirmed: {opts.date}" + (f', "{words}"' if words else "")]
    for entry in sorted(chosen, key=lambda e: -e["line"]):
        text = with_sub_lines(text, entry, lines)
    left = open_entries(feature.checked(text))
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
            one.add_argument("--why", required=True)
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
