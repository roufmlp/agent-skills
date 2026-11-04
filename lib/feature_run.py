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
  state, strikes, attempts, fresh, branch, worktree `<repo>/.claude/worktrees/note-<feature>-<nn>`), roles (model and
  effort per role, from the agent files, with `--role` overrides applied and
  marked `override: true`) and earlier (the lines an earlier run left under the
  report's `## Defaults taken`, `## Done-check edits` and `## Final check`, as
  `defaults`, `edits` and `final`, and each role's strikes from `## Roles` as
  `strikes`, so a restart's report keeps them; the
  merger's own `Door:` and `Blast radius:` lines are left out, since it writes
  them again at main-in).

`started` is the clock when `--started` is not given, `YYYY-MM-DD HH:MM` local.

A note's starting state comes from the report on the feature branch, which is
the run's ledger: `merged <commit>` and `cut <date>` rows are left alone (a cut
note's file is under `cut/`, so its row alone puts it in the list, and the
report keeps showing it);
`running` rows come from a run that stopped mid-note and start again in a
fresh worktree; so do `stopped: API errors`, `stopped: <role> returned no result`
and `stopped: worktree:` rows (`plan_check.RESTART_STATES`); any other
`stopped:` row and every `failed` row never reach here, because the plan check
opens the short interview on them. A `fresh` note's old worktree and branch are
removed by the session before the run, as the skill says: the merger's spawn
cannot, because the auto-mode classifier refuses `git worktree remove --force`
as irreversible (measured in the rehearsal on 2026-11-04).

`roles` reads every `agent-*.jsonl` under the transcript dir, groups the
assistant messages by the `agentType` in each `.meta.json`, and rewrites the
Tokens and Cost cells of the report's `## Roles` table in place, at list
price from `audit_transcripts.PRICES`. It changes nothing else in the file.

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

AGENTS_DIR = os.environ.get("BUILD_FEATURE_AGENTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
NAME = re.compile(r"^[a-z0-9-]+$")
RESTART_STATES = plan_check.RESTART_STATES
EARLIER = {"defaults": "Defaults taken", "edits": "Done-check edits", "final": "Final check"}
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
    if row.startswith("stopped:"):
        return row, False
    return "not started", False


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
    reports = common / "build-feature" / feature
    reports.mkdir(parents=True, exist_ok=True)
    rows = report_rows(tree, folder)
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
        notes.append({
            "number": number, "path": path, "waits_for": note["waits_for"],
            "screens": screens, "risk": risk_line, "state": state,
            "strikes": as_int(row.get("Strikes")), "attempts": as_int(row.get("Attempts")),
            "last_report": (row.get("Last report") or "").strip(), "fresh": fresh,
            "branch": f"note/{feature}/{number}",
            "worktree": str(repo / ".claude" / "worktrees" / f"note-{feature}-{number}"),
        })
    for number, row in sorted(rows.items()):
        # A cut note's file moved to cut/, and its row stays in the report.
        if number in {n["number"] for n in notes} or not row.get("State", "").startswith("cut"):
            continue
        notes.append({
            "number": number, "path": f"{folder}/cut/{number}", "waits_for": [], "screens": "none",
            "risk": "none", "state": row["State"].strip(), "strikes": as_int(row.get("Strikes")),
            "attempts": as_int(row.get("Attempts")), "last_report": (row.get("Last report") or "").strip(),
            "fresh": False, "branch": f"note/{feature}/{number}",
            "worktree": str(repo / ".claude" / "worktrees" / f"note-{feature}-{number}"),
        })
    notes.sort(key=lambda n: n["number"])
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
    }


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
        role = str(meta.get("agentType") or "")
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
            print(json.dumps(build_args(opts.feature, pathlib.Path(opts.tree).resolve(), opts.role,
                                        opts.batch, started), indent=1))
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
        return 0
    except Refusal as err:
        print(f"REFUSED: {err}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
