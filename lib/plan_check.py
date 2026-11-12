#!/usr/bin/env python3
"""The plan check: what `/build-feature` reads before it interviews, before
Abdul sees the page, and before a run starts.

    python3 ~/.claude/skills/workflow/lib/plan_check.py plan <feature>                   # which road: run, interview, or refused
    python3 ~/.claude/skills/workflow/lib/plan_check.py notes <feature> [--only 03 05]   # each note's shape, files and done checks
    python3 ~/.claude/skills/workflow/lib/plan_check.py notes changes/<nn>-*.md          # a one-note change, before its session builds

"What the interview settles before a run" (workflow v2 ticket 31) made
`/build-feature <name>` one command with two halves: with no approved plan it
interviews, with one it runs. This script is the check between the two, and
the pre-run check that runs inside the interview before Abdul sees the page.
`--tree` names the checkout; the default is the current directory's. Exit 0
means the road is clear, 2 means a road with Abdul or a ruling on it
(`INTERVIEW: ...`, `RULING: ...`, `GATE: ...`), 3 means refused
(`REFUSED: ...`), like `suite.py` and `note_check.py`.

## What `plan` decides

The plan is `changes/<feature>/plan.md`, from `templates/plan.md`; the report is
`changes/<feature>/report.md`, from `templates/report.md`. In this order:

- The session's folder is a worktree of the repo other than the main checkout
  and the feature tree: refused. The desktop app refuses
  such a session's writes into the feature tree, the note trees and the reports
  folder, and the build agents inherit that (`session_folder_refusal`).
- `report.md` on local main (`main` or `master`) carries a `Merged:` line:
  refused, with the merge commit. A change to a merged feature is a new
  feature or a one-note change (ticket 31, "Work that is already done").
- No `plan.md`: `INTERVIEW: no plan`, exit 2. The skill interviews.
- No `Approved: <date>` line: refused. The interview did not end.
- A question in `## Questions` with no `Answer:` line, or an answer left as the
  template's `<...>`: refused. Abdul answers every question that could stop
  the run before it starts (ticket 19).
- The last full run in `<git common dir>/suite/runs.jsonl` is over budget and
  the plan has no answered `[pruning]` question: refused ("How the careful lane
  keeps the test suite fast and trusted", ticket 21).
- The `Approved:` line is not committed: refused. The approval is the commit.
- The `## Rulings` part of the plan does not hold together: refused, with every
  fault `rulings.py` names. A `Ruled:` line with no `Touches:` line is one, and
  so is a note that follows a ruling and does not wait for the ruled note.
- A note, a test file a note's `## Tests` part names, or the plan changed
  after the approval commit, or a note was added, and no ruling written since
  covers it: refused. The approval commit is the one that wrote the plan's
  `Approved:` lines as they are now, the oldest of the newest run of commits
  whose lines equal them; the diff runs from it to the working tree, untracked
  notes included. A ruling covers the change it names, once: the note and its
  tests as they stood at the commit that added the entry to the page. A later
  change to either is refused, and a test file two notes name needs an entry
  for each. The plan may change in its rulings part, and its `## Cut` part may
  gain the line of a note Abdul's own ruling cut. A merged note's file that
  changed since its merge commit is refused whatever the rulings say: what
  touches it becomes a fix note. The test files of a merged note are not
  watched: its implementer and the final fix rounds edit them, the reviewers
  read those edits, and any change after a held final check runs the final
  check again. Approving again appends a new `Approved:` line, which starts a
  new run.
- The report's `## Decide` part shows a correction by the note checker and
  the plan has no `[correction]` entry for it: `RULING:`, exit 2.
- The report on the feature branch shows a note `failed`, or `stopped:` on a
  question (a `stopped:` the run starts again by itself, such as `API errors`,
  `worktree:` or `tooling:`, is not one): `RULING: notes 03 (failed)`, exit 2.
  The session rules each one, by Abdul's answer or by the written default, sets
  its row to `not started` and starts the run again in the same session. A
  `waiting:` row waits for Abdul with no timeout and holds nothing else.
- The report's `State:` is `held` and a ruling by `default` or `panel` has no
  `Confirmed:` or `Overturned:` line: `GATE: <n> ruling(s) ...`, exit 2, with
  the lines. The final check passed and the merge into local main waits for
  his answers; `note_check.py merge` refuses that merge on the same lines.
- Else `plan: approved <date> at <commit>`, exit 0.

## What `notes` refuses

For every note in `changes/<feature>/` (files whose name starts with digits,
the same map as `note_check.py`), or the ones `--only` names, or the one note
file given:

- A `Merged:` line: the one-note change already merged.
- No `Screens:` or `Risk:` line. A missing line is a refusal, not a default.
- `Waits for:` naming a note that is not in the folder.
- No `## Done` list, or a line in it that is not `` - `<command>`: <what a pass
  proves> ``. A done check is a command (ticket 19).
- No file in `## Tests`, or one that does not exist in the tree, or a test-side
  path a done check names that does not exist. A missing file fails for the
  wrong reason (ticket 31, "Done-check tests").
- A `Screens:` line other than `none` and no done check that names an
  end-to-end file, a `.spec.*` file or one under `e2e/` ("What the verifier
  checks in the browser", ticket 24).
- A done check that passes on today's code, exit 0, unless `--static`. Each
  command runs through the shell in the tree, output to `<git common
  dir>/suite/logs/<stamp>-plan-<nn>.log`, up to TIMEOUT seconds. A check that
  passes before the work proves nothing; the implementer's red check later
  covers the vitest tests the same way.

It prints `note <nn>: ok` or `note <nn>: REFUSED ...` per note, then the
pruning notice when the last full run is over budget, and exits 3 when any
note was refused.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulings  # noqa: E402
import suite  # noqa: E402
from note_check import CHANGES, MAIN_BRANCHES, NOTE_FILE, TOKEN, notes_in, test_paths  # noqa: E402

REFUSED = 3
INTERVIEW = 2
# Report rows a run starts again by itself: the run's own faults and a tool's, never a question for Abdul.
RESTART_STATES = re.compile(r"^stopped: (API errors|[a-z-]+ returned no result|worktree:|tooling:)")
# A row that waits for Abdul with no timeout. The other notes run on.
WAITING = "waiting:"
HELD = "held"
TIMEOUT = 1800
PLAN = "plan.md"
REPORT = "report.md"
FEATURE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
DONE_LINE = re.compile(r"^- `([^`]+)`:\s*(\S.*)$")
QUESTION = re.compile(r"^- \[([a-z ]+)\]\s*(.*)$")
ANSWER = re.compile(r"^\s*Answer:\s*(.*)$")
PLACEHOLDER = re.compile(r"^<.*>$")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
END_TO_END = re.compile(r"\.spec\.[cm]?[jt]sx?$|(^|/)e2e/")
KINDS = ("core design", "migration", "money or access rules", "data leaving", "pruning")


class Refusal(Exception):
    pass


class Interview(Exception):
    pass


class Ruling(Exception):
    pass


class Gate(Exception):
    pass


def git(tree, *args, check=True) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True)
    if check and done.returncode:
        raise subprocess.CalledProcessError(done.returncode, done.args, done.stdout, done.stderr)
    return done.stdout.strip()


def main_branch(tree) -> str | None:
    for name in MAIN_BRANCHES:
        found = subprocess.run(["git", "-C", str(tree), "show-ref", "--verify", "--quiet",
                                f"refs/heads/{name}"], capture_output=True)
        if found.returncode == 0:
            return name
    return None


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# ── Reading a note ───────────────────────────────────────────────────────────

def sections(text: str) -> dict[str, list[str]]:
    """The lines under each `## ` heading; the head of the file under ``."""
    found, current = {"": []}, ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            found.setdefault(current, [])
        else:
            found[current].append(line)
    return found


def line_value(lines: list[str], key: str) -> str | None:
    for line in lines:
        if line.startswith(f"{key}:"):
            return line[len(key) + 1:].strip()
    return None


def read_note(text: str) -> dict:
    parts = sections(text)
    head = parts[""]
    done, bad = [], []
    for line in parts.get("Done", []):
        if not line.startswith("- "):
            continue
        match = DONE_LINE.match(line)
        (done if match else bad).append(match.groups() if match else line)
    waits = line_value(head, "Waits for") or ""
    return {"title": next((l[2:].strip() for l in head if l.startswith("# ")), ""),
            "screens": line_value(head, "Screens"),
            "risk": line_value(head, "Risk"),
            "merged": line_value(head, "Merged"),
            "waits_for": [w.strip() for w in waits.split(",") if w.strip() and w.strip().lower() != "none"],
            "done": done, "bad_done": bad, "has_done": "Done" in parts,
            "tests": test_paths(parts.get("Tests", []))}


def note_files(tree: pathlib.Path, folder: str) -> list[tuple[str, str]]:
    """(number, path) of every note directly in `folder`, sorted."""
    full = tree / folder
    paths = [f"{folder}/{name}" for name in os.listdir(full)] if full.is_dir() else []
    return sorted(notes_in(folder, paths))


# ── Reading the plan and the report ──────────────────────────────────────────

def read_plan(text: str) -> dict:
    """The `Approved:` date and every question with its answer."""
    parts = sections(text)
    approved = None
    for line in text.splitlines():
        if line.startswith("Approved:"):
            approved = line[len("Approved:"):].strip()
    questions = []
    lines = parts.get("Questions", [])
    for i, line in enumerate(lines):
        match = QUESTION.match(line)
        if not match:
            continue
        answer = None
        for after in lines[i + 1:]:
            if QUESTION.match(after) or after.startswith("## "):
                break
            found = ANSWER.match(after)
            if found:
                answer = found.group(1).strip()
                break
        questions.append({"kind": match.group(1).strip(), "text": match.group(2).strip(),
                          "answer": answer})
    return {"approved": approved, "questions": questions}


def unanswered(questions: list[dict]) -> list[dict]:
    return [q for q in questions if not q["answer"] or PLACEHOLDER.match(q["answer"])]


def read_report(text: str | None) -> dict:
    """The `Merged:` line, the `State:` line and each note row's state."""
    merged, state, rows, columns = None, None, {}, None
    if text is None:
        return {"merged": None, "state": None, "states": rows}
    for line in text.splitlines():
        if line.startswith("Merged:"):
            merged = line[len("Merged:"):].strip()
        if line.startswith("State:") and state is None:
            state = line[len("State:"):].strip()
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
            continue
        if columns and len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: "):
            rows[cells[0]] = cells[1]
    return {"merged": merged, "state": state, "states": rows}


def pruning_notice(tree: pathlib.Path) -> str | None:
    row = suite.last_full_run(tree)
    if row and row.get("over_budget"):
        return (f"the last full run took {row.get('seconds')} s against a budget of "
                f"{row.get('budget_seconds')} s")
    return None


# ── plan ─────────────────────────────────────────────────────────────────────

def approved_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("Approved:")]


def approval_commit(tree: pathlib.Path, plan: str, current: list[str], rev: str = "HEAD") -> str | None:
    """The commit that wrote the plan's `Approved:` lines as they are now: the
    oldest of the newest run of commits whose lines equal them. None when the
    newest commit differs, so the approval is not committed."""
    found = None
    for commit in git(tree, "log", "--format=%H", rev, "--", plan).splitlines():
        if approved_lines(git(tree, "show", f"{commit}:{plan}", check=False)) != current:
            break
        found = commit
    return found


def changed_since(tree: pathlib.Path, commit: str, folder: str, watched: set[str]) -> list[str]:
    """The watched paths that differ between `commit` and the working tree,
    and the notes added since."""
    diff = git(tree, "diff", "--name-only", commit, "--", folder, *sorted(watched)).splitlines()
    untracked = git(tree, "ls-files", "--others", "--exclude-standard", "--", folder).splitlines()
    changed = []
    for path in diff + untracked:
        head, _, name = path.rpartition("/")
        if path in watched or (head == folder and NOTE_FILE.match(name)):
            if path not in changed:
                changed.append(path)
    return changed


def session_folder_refusal(tree: pathlib.Path) -> None:
    """Refuse a session whose folder is a worktree of this repo other than
    the main checkout and the feature tree. The desktop app guards such a
    session: it refuses every Write and Edit, the build agents' too, into the
    base checkout (the reports under `.git/build-feature/` included) and into a
    sibling worktree, which is where the feature tree and every note tree are.
    Five runs stopped on that between 2026-11-08 and 2026-11-11; from a session
    whose folder is the main checkout, 73 agent writes passed and none was
    refused."""
    here = os.getcwd()
    try:
        top = pathlib.Path(git(here, "rev-parse", "--show-toplevel")).resolve()
        common_here = git(here, "rev-parse", "--path-format=absolute", "--git-common-dir")
        common = git(tree, "rev-parse", "--path-format=absolute", "--git-common-dir")
    except (subprocess.CalledProcessError, OSError):
        return
    checkout = pathlib.Path(common).resolve().parent
    if common_here != common or top in (checkout, tree.resolve()):
        return
    raise Refusal(f"this session's folder is the worktree {top}. The desktop app refuses a Write "
                  f"or an Edit from it into the feature tree, a note tree and the reports folder, "
                  f"for the build agents too. Start `/build-feature` from a session whose folder "
                  f"is the main checkout, {checkout}.")


def waits_closure(waits: dict[str, list[str]], number: str) -> set[str]:
    """Every note `number` waits for, through other notes too."""
    seen, todo = set(), list(waits.get(number, []))
    while todo:
        one = todo.pop()
        if one not in seen:
            seen.add(one)
            todo.extend(waits.get(one, []))
    return seen


def ruling_faults(tree: pathlib.Path, folder: str, text: str, merged: set[str]) -> tuple[list[dict], list[str]]:
    """The plan's rulings and every reason they do not hold, the `Waits for:`
    line of a touched note included: a note that follows a ruling waits for the
    ruled note, unless that note is merged or already waits for this one."""
    entries, found = rulings.read(text)
    notes = {number: read_note((tree / path).read_text(encoding="utf-8"))
             for number, path in note_files(tree, folder)}
    found += rulings.faults(entries, set(notes), rulings.person(tree), merged)
    waits = {number: note["waits_for"] for number, note in notes.items()}
    for entry in entries:
        first, number = entry["follows"], entry["number"]
        if not first or first == number or number not in notes or first not in notes:
            continue
        if number in merged or first in merged or number in waits_closure(waits, first):
            continue
        if first not in waits[number]:
            found.append(f"note {number} follows the ruling on {first} and its `Waits for:` line "
                         f"does not name {first}. A touched note builds after the ruled note.")
    return entries, found


def entry_commits(tree: pathlib.Path, plan: str, commit: str) -> dict[str, str]:
    """For each note, the newest commit since the approval that added a ruling
    entry for it to the plan. An entry nobody committed covers nothing."""
    found = {}
    before = rulings.read(git(tree, "show", f"{commit}:{plan}", check=False))[0]
    for sha in git(tree, "log", "--reverse", "--format=%H", f"{commit}..HEAD", "--", plan).splitlines():
        now = rulings.read(git(tree, "show", f"{sha}:{plan}", check=False))[0]
        for number in rulings.new_since(now, before):
            found[number] = sha
        before = now
    return found


def cut_part(text: str) -> tuple[list[str], list[str]]:
    """What Abdul approved outside the rulings, and the lines of `## Cut`."""
    rest, cut, inside = [], [], False
    for line in rulings.outside(text).splitlines():
        if line.startswith("## ") or line.startswith("Approved:"):
            inside = line.strip() == "## Cut"
            if inside:
                continue
        (cut if inside else rest).append(line.strip())
    return rest, cut


def plan_changed(text: str, then: str, entries: list[dict], who: str | None) -> bool:
    """Whether the plan changed outside its rulings. The `## Cut` part may
    gain the line of a note that a ruling of his own names; nothing else moves."""
    rest, cut = cut_part(text)
    rest_then, cut_then = cut_part(then)
    if rest != rest_then or any(line not in cut for line in cut_then):
        return True
    his = {e["number"] for e in entries if not e["follows"] and rulings.by_person(e, who)}
    for line in cut:
        number = re.match(r"^(\d+)\b", line)
        if line not in cut_then and (not number or number.group(1) not in his):
            return True
    return False


def weakened_follow_ons(tree: pathlib.Path, folder: str, entries: list[dict], rev: str | None = None) -> set[str]:
    """The follow-on entries whose note had a test it named at the approval
    changed or deleted since. Such an entry is never free of his answer.
    The feature is read from the working tree, or from the commit `rev` when
    a hook asks about a branch on its way to main."""
    plan = f"{folder}/{PLAN}"

    def text_of(path: str) -> str:
        if rev:
            return git(tree, "show", f"{rev}:{path}", check=False)
        return (tree / path).read_text(encoding="utf-8") if (tree / path).is_file() else ""

    if not any(e["follows"] for e in entries) or not text_of(plan):
        return set()
    try:
        commit = approval_commit(tree, plan, approved_lines(text_of(plan)), rev or "HEAD")
    except subprocess.CalledProcessError:
        commit = None  # no commit yet
    if not commit:
        return {e["number"] for e in entries if e["follows"]}
    notes = note_files(tree, folder) if not rev else sorted(notes_in(
        folder, git(tree, "ls-tree", "--name-only", rev, f"{folder}/", check=False).splitlines()))
    found = set()
    for number, path in notes:
        if not any(e["follows"] and e["number"] == number for e in entries):
            continue
        tests = set(read_note(text_of(path))["tests"])
        then = git(tree, "show", f"{commit}:{path}", check=False)
        tests |= set(read_note(then)["tests"]) if then else set()
        span = [commit, rev] if rev else [commit]
        if tests and git(tree, "diff", "--name-only", "--diff-filter=MD", *span, "--", *sorted(tests), check=False):
            found.add(number)
    return found


def uncovered(tree: pathlib.Path, folder: str, plan: str, commit: str, text: str, entries: list[dict],
              changed: list[str], report: dict) -> list[str]:
    """The changes since the approval that no ruling covers. A ruling covers
    exactly the change it names, once: each owner of a changed path needs an
    entry a commit since the approval added, and the path must read today as
    it read at that commit. The plan may change in its rulings part, and in
    `## Cut` under his own ruling. A merged note is never edited: what touches
    it becomes a fix note."""
    then = git(tree, "show", f"{commit}:{plan}", check=False)
    covers = entry_commits(tree, plan, commit)
    owners: dict[str, set[str]] = {}
    for number, path in note_files(tree, folder):
        owners.setdefault(path, set()).add(number)
        for test in read_note((tree / path).read_text(encoding="utf-8"))["tests"]:
            owners.setdefault(test, set()).add(number)
    left = []
    for path in changed:
        if path == plan:
            if plan_changed(text, then, entries, rulings.person(tree)):
                left.append(path)
            continue
        numbers = set(owners.get(path, set()))
        head, _, name = path.rpartition("/")
        gone = NOTE_FILE.match(name) if head == folder and not numbers else None
        if gone:
            numbers = {gone.group(1)}  # a note that left the folder: a cut
        state = next((report["states"].get(n, "") for n in numbers if path.startswith(folder + "/")), "")
        if state.startswith("merged"):
            merge = state.split()[1] if len(state.split()) > 1 else ""
            since = subprocess.run(["git", "-C", str(tree), "diff", "--quiet", merge, "--", path],
                                   capture_output=True)
            if since.returncode:
                left.append(f"{path} (a merged note is never edited: write a fix note)")
                continue
        lacking = sorted(n for n in numbers if n not in covers)
        if not numbers or lacking:
            left.append(path + (f" (also named by note {', '.join(lacking)}, which no ruling covers)"
                                if lacking and len(numbers) > 1 else ""))
            continue
        later = [n for n in sorted(numbers) if subprocess.run(
            ["git", "-C", str(tree), "diff", "--quiet", covers[n], "--", path], capture_output=True).returncode
            or git(tree, "status", "--porcelain", "--", path, check=False).startswith("??")]
        if later:
            left.append(f"{path} (changed after the commit that applied the ruling on note {later[0]}: "
                        f"one commit applies a ruling, and it covers that change alone)")
    return left


def check_plan(tree: pathlib.Path, feature: str) -> int:
    session_folder_refusal(tree)
    folder = f"{CHANGES}/{feature}"
    plan = f"{folder}/{PLAN}"
    main = main_branch(tree)
    if main:
        on_main = read_report(git(tree, "show", f"{main}:{folder}/{REPORT}", check=False) or None)
        if on_main["merged"]:
            raise Refusal(f"{folder}/{REPORT} on {main} says `Merged: {on_main['merged']}`. A "
                          f"change to a merged feature is a new feature with a new name, or "
                          f"a one-note change.")
    if not (tree / plan).is_file():
        raise Interview(f"no plan: {plan} does not exist.")
    text = (tree / plan).read_text(encoding="utf-8")
    read = read_plan(text)
    if not read["approved"] or not DATE.match(read["approved"]):
        raise Refusal(f"{plan} has no `Approved: <date>` line. The run starts only from an "
                      f"approved plan; finish the interview.")
    open_ = unanswered(read["questions"])
    if open_:
        raise Refusal(f"{plan} has {len(open_)} question(s) with no answer:\n  " +
                      "\n  ".join(f"[{q['kind']}] {q['text']}" for q in open_) +
                      "\nAbdul answers every question that could stop the run before it starts.")
    notice = pruning_notice(tree)
    if notice and not any(q["kind"] == "pruning" for q in read["questions"]):
        raise Refusal(f"{notice}, and {plan} has no `[pruning]` question. Ask it: raise the "
                      f"budget, or add a pruning note first.")
    commit = approval_commit(tree, plan, approved_lines(text))
    if not commit:
        raise Refusal(f"the `Approved:` line of {plan} is not committed. The approval is the "
                      f"commit of the plan and the notes together.")
    here = tree / folder / REPORT
    report = read_report(here.read_text(encoding="utf-8") if here.is_file() else None)
    merged = {n for n, state in report["states"].items() if state.startswith("merged")}
    entries, found = ruling_faults(tree, folder, text, merged)
    if found:
        raise Refusal(f"the rulings in {plan} do not hold:\n  " + "\n  ".join(found))
    watched = {plan}
    for number, path in note_files(tree, folder):
        watched.add(path)
        # A merged note's implementer may edit a done-check test (a name that
        # changed as the screen was built); its reviewer read the edit against
        # the note, and the report lists it. That edit is the run's, not a
        # change to what Abdul approved, so a restart does not refuse on it.
        if number in merged:
            continue
        watched |= set(read_note((tree / path).read_text(encoding="utf-8"))["tests"])
    changed = uncovered(tree, folder, plan, commit, text, entries,
                        changed_since(tree, commit, folder, watched), report)
    if changed:
        raise Refusal(f"changed after the approval at {commit[:9]} ({read['approved']}), and no "
                      f"ruling written since covers it:\n  " + "\n  ".join(changed) +
                      "\nA ruling covers a note it names (`rulings.py record`), or Abdul approves "
                      "the plan again, which writes a new `Approved:` line.")
    person = rulings.person(tree)
    who = person or "the human"
    to_rule = [f"{n} ({state})" for n, state in report["states"].items() if state.startswith("failed")
               or (state.startswith("stopped:") and not RESTART_STATES.match(state))]
    to_rule += [f"{n} (corrected by the note checker; record it with `--kind correction`)"
                for n in rulings.uncorrected(entries, here.read_text(encoding="utf-8") if here.is_file() else "")]
    if to_rule:
        again = sorted(n for n, state in report["states"].items()
                       if state.startswith("failed") and n in rulings.rearmed(entries))
        raise Ruling(f"notes {', '.join(to_rule)} in {folder}/{REPORT}. Each takes a ruling: "
                     f"{who}'s answer, or the written default once the wait is over; then the run "
                     f"starts again." + (f" Note {', '.join(again)} failed again after its one "
                                         f"re-arm: it waits for {who} (`rulings.py wait`)." if again else ""))
    forced = weakened_follow_ons(tree, folder, entries)
    waiting = rulings.open_entries(entries, person, forced)
    if report["state"] == HELD and waiting:
        raise Gate(f"{len(waiting)} ruling(s) {who} did not make wait for him before the merge "
                   f"into local main:\n  " + "\n  ".join(rulings.away_lines(entries, person, forced, open_only=True)) +
                   "\nHe confirms or overturns each one (`rulings.py answer`).")
    count = len(note_files(tree, folder))
    waits = sorted(n for n, state in report["states"].items() if state.startswith(WAITING))
    print(f"plan: approved {read['approved']} at {commit[:9]}; {count} note(s); "
          f"{len(read['questions'])} question(s) answered; {len(entries)} ruling(s)"
          + (f", {len(waiting)} to confirm before the merge" if waiting else "")
          + (f"; waiting for {who}: {', '.join(waits)}" if waits else ""))
    return 0


# ── notes ────────────────────────────────────────────────────────────────────

def static_refusals(tree: pathlib.Path, path: str, note: dict, numbers: set[str] | None) -> list[str]:
    why = []
    if note["merged"]:
        why.append(f"`Merged: {note['merged']}`: this change is already in main.")
    if note["screens"] is None:
        why.append("no `Screens:` line.")
    if note["risk"] is None:
        why.append("no `Risk:` line.")
    if numbers is not None:
        for number in note["waits_for"]:
            if number not in numbers:
                why.append(f"`Waits for: {number}` names a note that is not in the folder.")
    if not note["has_done"] or not note["done"] and not note["bad_done"]:
        why.append("no `## Done` list. A done check is a command.")
    for line in note["bad_done"]:
        why.append(f"not a command with what a pass proves: `{line}`.")
    if not note["tests"]:
        why.append("no test file in `## Tests`. The interview writes one per done check.")
    for test in note["tests"]:
        if not (tree / test).exists():
            why.append(f"test file {test} does not exist.")
    for command, _ in note["done"]:
        for match in TOKEN.finditer(command):
            token = match.group(1)
            if suite.TEST_SIDE.search(token) and not (tree / token).exists():
                why.append(f"`{command}` names {token}, which does not exist.")
    if note["screens"] is not None and note["screens"].lower() != "none":
        if not any(END_TO_END.search(m.group(1)) for c, _ in note["done"] for m in TOKEN.finditer(c)):
            why.append(f"`Screens: {note['screens']}` and no end-to-end done check (a `.spec.*` "
                       f"file or one under e2e/).")
    return why


def run_done(tree: pathlib.Path, number: str, note: dict, stamp: str) -> list[str]:
    logs = suite.common_dir(tree) / "suite" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{stamp}-plan-{number}.log"
    why = []
    with log.open("w", encoding="utf-8") as handle:
        for command, proves in note["done"]:
            handle.write(f"$ {command}\n")
            handle.flush()
            try:
                done = subprocess.run(command, shell=True, cwd=tree, stdout=handle,
                                      stderr=subprocess.STDOUT, timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                why.append(f"`{command}` did not finish in {TIMEOUT} s.")
                continue
            handle.write(f"exit {done.returncode}\n")
            if done.returncode == 0:
                why.append(f"`{command}` passes on today's code, so it proves nothing about "
                           f"the work ({proves}).")
    print(f"  log: {log}")
    return why


def check_notes(tree: pathlib.Path, target: str, only: list[str], static: bool) -> int:
    if target.endswith(".md"):
        head, _, name = target.rpartition("/")
        match = NOTE_FILE.match(name)
        if not match or not (tree / target).is_file():
            raise Refusal(f"{target} is not a note file: `<nn>-*.md` under {CHANGES}/.")
        notes, numbers = [(match.group(1), target)], None
    else:
        if not FEATURE.match(target):
            raise Refusal(f"`{target}` is not a feature name: lower-case letters, digits and hyphens.")
        notes = note_files(tree, f"{CHANGES}/{target}")
        if not notes:
            raise Refusal(f"{CHANGES}/{target}/ has no note. A note is `<nn>-*.md`.")
        numbers = {n for n, _ in notes}
        if only:
            missing = [n for n in only if n not in numbers]
            if missing:
                raise Refusal(f"--only names {', '.join(missing)}, not in {CHANGES}/{target}/.")
            notes = [(n, p) for n, p in notes if n in only]
    stamp = f"{now():%Y%m%dT%H%M%S.%fZ}"
    refused = 0
    for number, path in notes:
        note = read_note((tree / path).read_text(encoding="utf-8"))
        why = static_refusals(tree, path, note, numbers)
        if not why and not static:
            why = run_done(tree, number, note, stamp)
        if why:
            refused += 1
            print(f"note {number}: REFUSED {path}\n  " + "\n  ".join(why))
        else:
            print(f"note {number}: ok ({len(note['done'])} done check(s), "
                  f"{len(note['tests'])} test file(s){', static' if static else ''})")
    notice = pruning_notice(tree)
    if notice:
        print(f"PRUNING: {notice}. The plan needs a `[pruning]` question.")
    if refused:
        print(f"REFUSED: {refused} of {len(notes)} note(s). Fix each before Abdul sees the page.")
        return REFUSED
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=("plan", "notes"))
    parser.add_argument("target", help="the feature name, or for notes a one-note file")
    parser.add_argument("--tree", default=os.getcwd())
    parser.add_argument("--only", nargs="*", default=[], help="notes: the numbers to check")
    parser.add_argument("--static", action="store_true", help="notes: do not run the done checks")
    args = parser.parse_args(argv)
    try:
        try:
            tree = pathlib.Path(git(args.tree, "rev-parse", "--show-toplevel"))
        except (subprocess.CalledProcessError, OSError) as error:
            raise Refusal(f"git could not read {args.tree}: {getattr(error, 'stderr', error)}")
        if args.kind == "plan":
            if not FEATURE.match(args.target):
                raise Refusal(f"`{args.target}` is not a feature name: lower-case letters, "
                              f"digits and hyphens.")
            return check_plan(tree, args.target)
        return check_notes(tree, args.target, args.only, args.static)
    except Interview as error:
        print(f"INTERVIEW: {error}")
        return INTERVIEW
    except Ruling as error:
        print(f"RULING: {error}")
        return INTERVIEW
    except Gate as error:
        print(f"GATE: {error}")
        return INTERVIEW
    except Refusal as error:
        print(f"REFUSED: {error}")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
