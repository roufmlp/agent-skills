#!/usr/bin/env python3
"""What the `build-feature-run` workflow cannot read for itself.

A workflow script has no filesystem: it sees only its `args`. So the session
that starts the run computes the run's inputs here, once, and passes the JSON
this prints as `args`. After the run the same session fills the two report
cells the script cannot know, the tokens and the cost per role, from the
workflow's own transcripts.

    python3 feature_run.py args <feature> --tree <feature worktree> \\
        [--role implementer=opus:medium ...] [--batch <id>] [--started <text>]
    python3 feature_run.py roles <workflow transcript dir> --report <report.md>

`args` prints one JSON object:

  feature, tree (the feature worktree), repo (the main checkout), main (its
  branch name), reports (the folder reject reports go to, inside the git
  common dir so no report can ever be read as a note), batch (the database
  claim's batch id), started, staging (the `Staging:` line of the product's
  CLAUDE.md, or null), risk (true when any note's `Risk:` names a class),
  notes (one row per note file: number, path, waits_for, screens, risk,
  state, strikes, attempts, fresh, rearmed, branch, worktree `<repo>/.claude/worktrees/note-<feature>-<nn>`), roles (model and
  effort per role, from the agent files, with `--role` overrides applied and
  marked `override: true`), earlier (the lines an earlier run left under the
  report's `## Defaults taken`, `## Done-check edits`, `## Final check` and
  `## Tooling stops`, as `defaults`, `edits`, `final` and `tooling`, and each
  role's strikes from `## Roles` as `strikes`, so a restart's report keeps
  them; the merger's own `Door:` and `Blast radius:` lines are left out, since
  it writes them again at main-in), and what away mode needs from the plan's
  `## Rulings` part (`rulings.py`): ruling_wait_seconds (how long the session
  waits for Abdul's answer), gate_open (the notes whose ruling by `default` or
  `panel` he has not confirmed; the script holds the merge while it is not
  empty), away (the report's "Ruled while you were away" lines, a panel
  ruling's in its full form from the panel's files) and held (true
  when an earlier run's final check passed and only the plan and the report
  changed since, so the run goes straight to the merge).

`started` is the clock when `--started` is not given, `YYYY-MM-DD HH:MM` local.

A note's starting state comes from the report on the feature branch, which is
the run's ledger: `merged <commit>` and `cut <date>` rows are left alone (a cut
note's file is under `cut/`, so its row alone puts it in the list, and the
report keeps showing it);
`running` rows come from a run that stopped mid-note and start again in a
fresh worktree; so do `stopped: API errors`, `stopped: <role> returned no result`,
`stopped: worktree:` and `stopped: tooling:` rows (`plan_check.RESTART_STATES`);
a `waiting:` row is left alone, since it waits for Abdul; any other
`stopped:` row and every `failed` row never reach here, because the plan check
sends the session to rule on them first. A note whose file or tests changed
after its note branch's base commit is `fresh` too: a ruling changed it, and
the old tree holds the build of the old note. `rearmed` is true when the plan
carries a `[re-arm]` ruling for the note; the script sends such a note's
second failure to `waiting:`. `args` refuses while a `fresh` note's old
worktree or branch exists, and prints the commands that remove them. The
session runs those: the merger's spawn cannot, because the auto-mode
classifier refuses `git worktree remove --force` as irreversible (measured in
the rehearsal on 2026-11-04), and the script cannot see a folder.

`args` also refuses a product whose `.githooks/reference-transaction` is
missing, not executable or not on `core.hooksPath`, and the fourth start in a
row that merged no new note (`count_start`), the final check's starts included.

`roles` reads every `agent-*.jsonl` under the transcript dir, groups the
assistant messages by the `agentType` in each `.meta.json`, and rewrites the
Tokens and Cost cells of the report's `## Roles` table in place, at list
price from `audit_transcripts.PRICES`. It changes nothing else in the file.
A panel's four agents are the session's own, so no row here counts them:
`rulings.py panel` keeps the paths of their transcripts in the panel's
`agents.json`, to be priced from `audit_transcripts.PRICES` once the first
risk questions have run.

Exit 0 on success, 3 with `REFUSED: <why>` on a bad role override, a missing
file or a feature name outside lower-case letters, digits and hyphens.
"""

import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_transcripts  # noqa: E402
import check_build_agents  # noqa: E402
import plan_check  # noqa: E402
import rulings  # noqa: E402

AGENTS_DIR = os.environ.get("BUILD_FEATURE_AGENTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
NAME = re.compile(r"^[a-z0-9-]+$")
RESTART_STATES = plan_check.RESTART_STATES
EARLIER = {"defaults": "Defaults taken", "edits": "Done-check edits", "final": "Final check",
           "tooling": "Tooling stops", "decide": "Decide"}
# The automatic restarts in a row that merge no new note: after a tool fault, a
# worktree the merger could not remove, or a run that hung. The next start is
# refused, and each such row waits for Abdul. A start whose only restart rows
# are API errors is an outage or a usage limit: it does not count toward the
# three, and only MAX_OUTAGE_SECONDS ends it.
MAX_STARTS_WITHOUT_MERGE = 3
MAX_OUTAGE_SECONDS = 3 * 24 * 3600
STARTS = "starts.json"
REF_HOOK = "reference-transaction"  # the hook that holds the gate on a fast-forward, a reset and update-ref
OUTAGE = re.compile(r"^stopped: (API errors|[a-z-]+ returned no result)")
NOTE_LABEL = re.compile(r"^note (\d+):")
ROLES_TABLE = "Roles"
MERGER_OWNED = ("Door:", "Blast radius:")
PLACEHOLDER = ("not run", "not assessed", "not yet")  # the script's and the merger's own filler
STAGING = re.compile(r"^Staging:\s*(\S+)", re.M)


class Refusal(Exception):
    pass


# ── args ─────────────────────────────────────────────────────────────────────

def read_roles(overrides: list[str]) -> dict:
    """Model and effort per role from the agent files, then the overrides."""
    roles = {}
    for role in check_build_agents.ROLES:
        path = os.path.join(AGENTS_DIR, f"build-feature-{role}.md")
        if not os.path.isfile(path):
            raise Refusal(f"agent file {path} does not exist.")
        with open(path, encoding="utf-8") as fh:
            fields, _ = check_build_agents.frontmatter(fh.read())
        fields = fields or {}
        roles[role] = {"model": fields.get("model", "inherit"), "effort": fields.get("effort", ""),
                       "override": False}
    for item in overrides:
        match = re.match(r"^([a-z-]+)=([a-z]+):([a-z]+)$", item)
        if not match:
            raise Refusal(f"role override `{item}` is not `<role>=<model>:<effort>`.")
        role, model, effort = match.groups()
        if role not in roles:
            raise Refusal(f"role override names `{role}`; the roles are "
                          + ", ".join(check_build_agents.ROLES) + ".")
        if model not in check_build_agents.MODELS - {"inherit"}:
            raise Refusal(f"role override model `{model}` is not one of "
                          + ", ".join(sorted(check_build_agents.MODELS - {"inherit"})) + ".")
        if effort not in check_build_agents.EFFORTS:
            raise Refusal(f"role override effort `{effort}` is not one of "
                          + ", ".join(sorted(check_build_agents.EFFORTS)) + ".")
        roles[role] = {"model": model, "effort": effort, "override": True}
    return roles


def starting_state(row: str | None) -> tuple[str, bool]:
    """The state a note starts the run in, and whether its worktree is remade."""
    row = (row or "").strip()
    if row.startswith("merged ") or row.startswith("cut"):
        return row, False
    if row == "running":
        return "not started", True
    if RESTART_STATES.match(row):
        return "not started", True
    if row.startswith("stopped:") or row.startswith(plan_check.WAITING):
        return row, False
    return "not started", False


def changed_since_base(tree: pathlib.Path, feature: str, branch: str, paths: list[str]) -> bool:
    """Whether a note's file or tests changed after its worktree's base commit:
    the feature tree holds a note the old note branch never saw. The run then
    makes the tree again. On 2026-11-11 note 02 of customer-tracking kept its
    old tree after a note change and merged the old build."""
    found = plan_check.git(tree, "rev-parse", "-q", "--verify", f"refs/heads/{branch}", check=False)
    if not found:
        return False
    base = plan_check.git(tree, "merge-base", f"feature/{feature}", branch, check=False)
    if not base:
        return True
    return bool(plan_check.git(tree, "diff", "--name-only", base, "--", *paths, check=False))


def held(tree: pathlib.Path, folder: str) -> bool:
    """Whether the final check of an earlier run still stands: the report says
    `State: held`, and since the commit that wrote that state nothing changed
    but the plan (his answers) and the report (the roles cells)."""
    report, plan = f"{folder}/{plan_check.REPORT}", f"{folder}/{plan_check.PLAN}"
    if not (tree / report).is_file():
        return False
    if plan_check.read_report((tree / report).read_text(encoding="utf-8"))["state"] != plan_check.HELD:
        return False
    first = None
    for commit in plan_check.git(tree, "log", "--format=%H", "--", report).splitlines():
        text = plan_check.git(tree, "show", f"{commit}:{report}", check=False)
        if plan_check.read_report(text)["state"] != plan_check.HELD:
            break
        first = commit
    if not first:
        return False
    changed = plan_check.git(tree, "diff", "--name-only", first).splitlines()
    states = [row.get("State", "") for row in report_rows(tree, folder).values()]
    return all(path in (report, plan) for path in changed) and all(s.startswith(("merged", "cut")) for s in states)


def count_start(reports: pathlib.Path, rows: dict, clock: float, state: str = "") -> None:
    """Count this start, and refuse it past the bound on automatic restarts.

    A start is automatic when a row reads `running` or a state the run starts
    again by itself, and when every note is merged and the report still reads
    `stopped` or `running`: the final check of an earlier run did not finish,
    and no row says so. The streak ends when a new note merged, when no such
    start is left, or when the row `final` changed: his ruling on the final
    check writes `ruled <date>` there. That row is compared, never exempt: an
    exemption for a `ruled` row passed six daily starts that finished no final
    check (review 3, note 7). Nothing else bounds these restarts: the plan
    check passes each one."""
    states = [row.get("State", "") for row in rows.values()]
    merged = sum(1 for s in states if s.startswith("merged"))
    again = [s for s in states if s == "running" or RESTART_STATES.match(s)]
    final = rows.get(rulings.FINAL, {}).get("State", "")
    notes = [row.get("State", "") for number, row in rows.items() if number != rulings.FINAL]
    if (not again and notes and all(s.startswith(("merged", "cut")) for s in notes)
            and state in ("stopped", "running")
            and not final.startswith(("stopped:", plan_check.WAITING))):
        again = ["the final check, which an earlier run did not finish"]
    path = reports / STARTS
    try:
        past = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        past = {}
    if not again or not isinstance(past, dict) or merged > past.get("merged", -1) or final != past.get("final", ""):
        past = {"merged": merged, "starts": 0, "since": clock, "final": final}
    refusal = None
    if again:
        if any(not OUTAGE.match(s) for s in again):
            past["starts"] += 1
        if past["starts"] > MAX_STARTS_WITHOUT_MERGE:
            refusal = (f"{MAX_STARTS_WITHOUT_MERGE} automatic restarts in a row merged no new note, and the rows "
                       f"still read: {'; '.join(sorted(set(again)))}. No further restart: set each such note to "
                       f"wait for Abdul (`rulings.py wait <feature> --tree <tree> --note <nn> --why \"tooling: "
                       f"<its line>\"`, with `--note final` for the final check), and the other notes run on.")
        elif clock - float(past["since"] if isinstance(past.get("since"), (int, float)) else clock) > MAX_OUTAGE_SECONDS:
            refusal = (f"the run has started again for {MAX_OUTAGE_SECONDS // 86400} days with no newly merged "
                       f"note. No further restart: tell Abdul.")
    reports.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(past) + "\n", encoding="utf-8")
    if refusal:
        raise Refusal(refusal)


def report_rows(tree: pathlib.Path, folder: str) -> dict:
    """Each note's cells from the report's notes table, by number."""
    path = tree / folder / plan_check.REPORT
    if not path.is_file():
        return {}
    rows = {}
    columns = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = plan_check.TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:2] == ["Note", "State"] else []
            continue
        if columns and len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: "):
            rows[cells[0]] = dict(zip(columns, cells))
    return rows


def earlier_lines(tree: pathlib.Path, folder: str) -> dict:
    """The lines an earlier run left in the three report parts a restart must keep."""
    path = tree / folder / plan_check.REPORT
    found = {key: [] for key in EARLIER}
    found["strikes"] = {}
    if not path.is_file():
        return found
    parts = plan_check.sections(path.read_text(encoding="utf-8"))
    columns = None
    for line in parts.get(ROLES_TABLE, []):
        match = plan_check.TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:1] == ["Role"] else []
            continue
        if columns and "Strikes" in columns and not set(cells[0]) <= set("-: ") and as_int(cells[columns.index("Strikes")]):
            found["strikes"][cells[0]] = as_int(cells[columns.index("Strikes")])
    for key, heading in EARLIER.items():
        for line in parts.get(heading, []):
            line = line.strip()
            if not line or line.lower() == "none" or line.startswith(MERGER_OWNED) \
                    or line.lower().startswith(PLACEHOLDER):
                continue
            found[key].append(line)
    return found


def as_int(value: str | None) -> int:
    try:
        return int((value or "").strip() or 0)
    except ValueError:
        return 0


def build_args(feature: str, tree: pathlib.Path, overrides: list[str], batch: str | None,
               started: str) -> dict:
    if not NAME.match(feature):
        raise Refusal(f"feature name `{feature}` is not lower-case letters, digits and hyphens.")
    if not tree.is_dir():
        raise Refusal(f"tree {tree} does not exist.")
    folder = f"{plan_check.CHANGES}/{feature}"
    files = plan_check.note_files(tree, folder)
    if not files:
        raise Refusal(f"{folder}/ in {tree} holds no note.")
    common = pathlib.Path(plan_check.git(tree, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    repo = common.parent
    main = plan_check.main_branch(tree)
    if not main:
        raise Refusal(f"{tree} has no main or master branch.")
    # A product that installed its hooks before the gate has no hook on a
    # fast-forward, so a ruling nobody answered could reach its main branch.
    hooks = repo / ".githooks"
    if hooks.is_dir():
        hook = hooks / REF_HOOK
        if not hook.is_file():
            raise Refusal(f"{hooks} has no `{REF_HOOK}` hook, so a fast-forward into {main} skips the gate before "
                          f"local main. On {main}: copy `{REF_HOOK}` and `prepare` from "
                          f"~/.claude/skills/workflow/templates/githooks/ into .githooks/, run `sh .githooks/prepare`, "
                          f"and commit the two files by name.")
        # git passes over a hook it may not execute, and over every hook when
        # `core.hooksPath` names another folder (review 2, N9).
        if not os.access(hook, os.X_OK):
            raise Refusal(f"{hook} is not executable, so git does not run it and a fast-forward into {main} skips "
                          f"the gate before local main. In {repo}: `chmod +x .githooks/{REF_HOOK}`, and commit it.")
        wrong = plan_check.suite.hooks_refusal(repo)
        if wrong:
            raise Refusal(f"the hooks of {repo} do not run, so nothing holds the gate before local main. "
                          f"In {repo}: `sh .githooks/prepare`. {wrong}")
    reports = common / "build-feature" / feature
    reports.mkdir(parents=True, exist_ok=True)
    rows = report_rows(tree, folder)
    plan = tree / folder / plan_check.PLAN
    report = tree / folder / plan_check.REPORT
    report_text = report.read_text(encoding="utf-8") if report.is_file() else ""
    # The same strict reading as the plan check: a ruling that does not hold,
    # or a correction nobody recorded, starts no run.
    cut = {n for n, row in rows.items() if row.get("State", "").startswith("cut")}
    entries, found = plan_check.ruling_faults(
        tree, folder, plan.read_text(encoding="utf-8"),
        {n for n, row in rows.items() if row.get("State", "").startswith("merged")},
        cut) if plan.is_file() else ([], [])
    found += [f"note {n}: the note checker corrected it and the plan has no `[correction]` entry"
              for n in rulings.uncorrected(entries, report_text)]
    if found:
        raise Refusal(f"the rulings in {folder}/{plan_check.PLAN} do not hold:\n  " + "\n  ".join(found))
    person = rulings.person(tree)
    rearmed = rulings.rearmed(entries)
    # A question of the final check lives in the row `final`. While it is not
    # ruled, no final check runs.
    final = rows.get(rulings.FINAL, {}).get("State", "").strip()
    if not (final.startswith(plan_check.WAITING) or (final.startswith("stopped:") and not RESTART_STATES.match(final))):
        final = ""
    notes, risk = [], False
    for number, path in files:
        text = (tree / path).read_text(encoding="utf-8")
        note = plan_check.read_note(text)
        head = text.split("\n## ", 1)[0].splitlines()
        screens = plan_check.line_value(head, "Screens") or "none"
        risk_line = plan_check.line_value(head, "Risk") or "none"
        if risk_line.strip().lower() != "none":
            risk = True
        row = rows.get(number, {})
        state, fresh = starting_state(row.get("State"))
        branch = f"note/{feature}/{number}"
        if state == "not started" and not fresh:
            fresh = changed_since_base(tree, feature, branch, [path, *note["tests"]])
        notes.append({
            "number": number, "path": path, "waits_for": note["waits_for"],
            "screens": screens, "risk": risk_line, "state": state,
            "strikes": as_int(row.get("Strikes")), "attempts": as_int(row.get("Attempts")),
            "last_report": (row.get("Last report") or "").strip(), "fresh": fresh,
            "rearmed": number in rearmed, "branch": branch,
            "worktree": str(repo / ".claude" / "worktrees" / f"note-{feature}-{number}"),
        })
    for number, row in sorted(rows.items()):
        # A cut note's file moved to cut/, and its row stays in the report.
        if number in {n["number"] for n in notes} or not row.get("State", "").startswith("cut") \
                or not number.isdigit():
            continue
        notes.append({
            "number": number, "path": f"{folder}/cut/{number}", "waits_for": [], "screens": "none",
            "risk": "none", "state": row["State"].strip(), "strikes": as_int(row.get("Strikes")),
            "attempts": as_int(row.get("Attempts")), "last_report": (row.get("Last report") or "").strip(),
            "fresh": False, "rearmed": False, "branch": f"note/{feature}/{number}",
            "worktree": str(repo / ".claude" / "worktrees" / f"note-{feature}-{number}"),
        })
    notes.sort(key=lambda n: n["number"])
    # A fresh note is built in a new tree. The old tree holds the build of the
    # old note, and nothing but this refusal keeps a run from using it again:
    # the script cannot see a folder, and an agent may not remove one.
    stale = []
    for n in notes:
        tree_left = pathlib.Path(n["worktree"]).exists()
        branch_left = bool(plan_check.git(tree, "rev-parse", "-q", "--verify", f"refs/heads/{n['branch']}", check=False))
        if n["fresh"] and (tree_left or branch_left):
            stale.append(f"note {n['number']}: "
                         + (f"`git -C {repo} worktree remove --force {n['worktree']}`; " if tree_left else "")
                         + (f"`git -C {repo} branch -D {n['branch']}`; " if branch_left else "")
                         + f"`git -C {repo} worktree prune`")
    if stale:
        raise Refusal("a note that starts again needs a new tree, and its old tree or branch is still there. "
                      "Remove them from this session, then run this command again:\n  " + "\n  ".join(stale))
    claude_md = tree / "CLAUDE.md"
    staging = None
    if claude_md.is_file():
        found = STAGING.search(claude_md.read_text(encoding="utf-8"))
        staging = found.group(1) if found else None
    return {
        "feature": feature, "tree": str(tree), "repo": str(repo), "main": main,
        "reports": str(reports), "batch": batch or f"batch-{secrets.token_hex(3)}",
        "started": started, "staging": staging, "risk": risk, "notes": notes,
        "roles": read_roles(overrides), "earlier": earlier_lines(tree, folder),
        "ruling_wait_seconds": rulings.RULING_WAIT_SECONDS,
        "gate_open": [e["number"] for e in rulings.open_entries(entries, person, cut)],
        "away": rulings.away_lines(entries, person, records=plan_check.records_of(tree, feature), cut=cut),
        "held": held(tree, folder), "final": final,
    }


# ── stops ────────────────────────────────────────────────────────────────────

def typed_stops(transcripts: pathlib.Path) -> list[dict]:
    """Each question a role stopped on, as the role typed it: the `stop` of
    its last StructuredOutput call. The label of the spawn names the note; a
    fix round's question belongs to `final`. A class outside the form's own
    is `unclassified`, so nobody reads it as outside the risk classes."""
    found = []
    for meta_path in sorted(glob.glob(str(transcripts / "**" / "agent-*.meta.json"), recursive=True)):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            continue
        role = str(meta.get("agentType") or "").removeprefix("workflow:")
        label = str(meta.get("description") or "")
        note = NOTE_LABEL.match(label)
        number = note.group(1) if note else rulings.FINAL if label.startswith("fix round") else None
        if not role.startswith("build-feature-") or number is None:
            continue
        answer = None
        for rec in audit_transcripts._iter_records(meta_path[:-len(".meta.json")] + ".jsonl"):
            content = (rec.get("message") or {}).get("content") if rec.get("type") == "assistant" else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "StructuredOutput":
                    answer = block.get("input")
        if not isinstance(answer, dict):
            continue
        stop = answer.get("stop") if isinstance(answer.get("stop"), dict) else {}
        if stop.get("kind") == "question":
            cls, question, default = stop.get("class"), stop.get("question"), stop.get("default")
        elif answer.get("outcome") == "stopped" and stop.get("kind") != "tooling":
            cls, question, default = None, answer.get("line"), ""
        else:
            continue
        found.append({"note": number, "role": role[len("build-feature-"):], "kind": "question",
                      "class": cls if cls in ("none", *rulings.RISK_CLASSES) else "unclassified",
                      "question": rulings.plain(question), "default": rulings.plain(default),
                      "agent": os.path.basename(meta_path)[:-len(".meta.json")]})
    return found


def record_stops(report: pathlib.Path, stops: list[dict]) -> tuple[pathlib.Path | None, int]:
    """Append the stops the run's record lacks; `rulings.py` reads the class
    there. A report outside `<tree>/changes/<feature>/` has no record."""
    if report.parent.parent.name != plan_check.CHANGES:
        return None, 0
    try:
        path = rulings.records_dir(report.parents[2], report.parent.name) / rulings.STOPS
    except rulings.Refusal:
        return None, 0
    have = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    seen = set()
    for raw in have:
        try:
            seen.add(json.loads(raw).get("agent"))
        except (ValueError, AttributeError):
            continue
    new = [json.dumps(stop) for stop in stops if stop["agent"] not in seen]
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(have + new) + "\n", encoding="utf-8")
    return path, len(new)


# ── roles ────────────────────────────────────────────────────────────────────

def role_totals(transcripts: pathlib.Path) -> dict:
    """Tokens and list-price cost per build-feature role, from the run's transcripts."""
    totals = {}
    for meta_path in sorted(glob.glob(str(transcripts / "**" / "agent-*.meta.json"), recursive=True)):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            continue
        role = str(meta.get("agentType") or "").removeprefix("workflow:")
        if not role.startswith("build-feature-"):
            continue
        role = role[len("build-feature-"):]
        entry = totals.setdefault(role, {"tokens": 0, "cost": 0.0, "model": "", "unpriced": False})
        seen = {}
        for rec in audit_transcripts._iter_records(meta_path[:-len(".meta.json")] + ".jsonl"):
            if rec.get("type") != "assistant":
                continue
            message = rec.get("message") or {}
            usage = message.get("usage") or {}
            if not usage:
                continue
            cache = usage.get("cache_creation") or {}
            tokens = {
                "input": usage.get("input_tokens") or 0,
                "cache_write_5m": cache.get("ephemeral_5m_input_tokens",
                                            usage.get("cache_creation_input_tokens") or 0) or 0,
                "cache_write_1h": cache.get("ephemeral_1h_input_tokens") or 0,
                "cache_read": usage.get("cache_read_input_tokens") or 0,
                "output": usage.get("output_tokens") or 0,
            }
            key = message.get("id") or rec.get("uuid")
            if key in seen and seen[key] >= sum(tokens.values()):
                continue
            seen[key] = sum(tokens.values())
            model = str(message.get("model") or "")
            entry["model"] = entry["model"] or model
            context = tokens["input"] + tokens["cache_read"] + tokens["cache_write_5m"] + tokens["cache_write_1h"]
            cost = audit_transcripts.message_cost(model, tokens, context)
            entry["tokens"] += sum(tokens.values())
            if cost is None:
                entry["unpriced"] = True
            else:
                entry["cost"] += cost
    return totals


def fill_roles(report: pathlib.Path, totals: dict) -> int:
    """Rewrite the Tokens and Cost cells of the `## Roles` table; return rows changed."""
    lines = report.read_text(encoding="utf-8").splitlines()
    columns, changed = None, 0
    for i, line in enumerate(lines):
        match = plan_check.TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:1] == ["Role"] else []
            continue
        if not columns or set(cells[0]) <= set("-: "):
            continue
        role = cells[0]
        if role not in totals or "Tokens" not in columns or "Cost" not in columns:
            continue
        cells[columns.index("Tokens")] = f"{totals[role]['tokens']:,}"
        cost = totals[role]["cost"]
        cells[columns.index("Cost")] = f"${cost:.2f}" + (" plus unpriced" if totals[role]["unpriced"] else "")
        lines[i] = "| " + " | ".join(cells) + " |"
        changed += 1
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


# ── main ─────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="kind", required=True)
    a = sub.add_parser("args")
    a.add_argument("feature")
    a.add_argument("--tree", required=True)
    a.add_argument("--role", action="append", default=[], help="<role>=<model>:<effort>")
    a.add_argument("--batch")
    a.add_argument("--started", default="", help="defaults to the clock, `date '+%%Y-%%m-%%d %%H:%%M'`")
    r = sub.add_parser("roles")
    r.add_argument("transcripts")
    r.add_argument("--report", required=True)
    opts = parser.parse_args(argv)
    try:
        if opts.kind == "args":
            started = opts.started or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            built = build_args(opts.feature, pathlib.Path(opts.tree).resolve(), opts.role, opts.batch, started)
            folder = f"{plan_check.CHANGES}/{opts.feature}"
            report = pathlib.Path(built["tree"]) / folder / plan_check.REPORT
            count_start(pathlib.Path(built["reports"]), report_rows(pathlib.Path(built["tree"]), folder),
                        datetime.datetime.now().timestamp(),
                        plan_check.read_report(report.read_text(encoding="utf-8"))["state"] if report.is_file() else "")
            print(json.dumps(built, indent=1))
            return 0
        transcripts, report = pathlib.Path(opts.transcripts), pathlib.Path(opts.report)
        if not transcripts.is_dir():
            raise Refusal(f"transcript dir {transcripts} does not exist.")
        if not report.is_file():
            raise Refusal(f"report {report} does not exist.")
        totals = role_totals(transcripts)
        changed = fill_roles(report, totals)
        for role in sorted(totals):
            print(f"{role}: {totals[role]['tokens']:,} tokens, ${totals[role]['cost']:.2f}")
        print(f"roles: {changed} row(s) filled in {report}")
        path, added = record_stops(report.resolve(), typed_stops(transcripts))
        print(f"stops: {added} typed stop(s) added to {path}" if path else
              "stops: none recorded, the report is not in a feature tree")
        return 0
    except Refusal as err:
        print(f"REFUSED: {err}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
