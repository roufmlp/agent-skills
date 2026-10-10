#!/usr/bin/env python3
"""After a run merges, write each part it carved out into an issue file.

    python3 ~/.claude/skills/run-issues/mint_carved.py \\
        --ledger <feature>/runs/<batch-id>/run.md --issues <feature>/issues

Run it in the main checkout, after the merge, every time. It is safe to run
again: a carve it has minted is skipped.

WHY. The human ruled on 2026-10-06 that a run never blocks on one feature.
When an issue reaches its attempt cap, or its second criteria reset, the runner
carves the failing criteria out, ships the rest, and the dependents run. One
run on one project is the measurement: one issue's Undo criterion blocked, the
ten issues behind it were skipped, and 1 of 12 shipped. The human then carved
the Undo by hand into a new issue. This is that hand step, made a command,
and `next_batch.py` refuses to plan a new batch while a merged run's carve is
still unminted (`unminted_carves`).

WHAT IT WRITES. For each ledger row at `done (carved)`:

  - a NEW issue at `Status: needs-harden`, its number from `claim_number.py`,
    with `Origin:` and `Carved from:` in its header. It carries the carved
    criteria word for word, the source's invariants, its register rows, the
    paths of its verdicts, its ledger row as the strike history, and the side
    branch where the carved code sits when that branch exists;
  - in the source issue, each carved criterion becomes one box,
    `- [ ] MOVED to issue NN ...`, so the place numbers of the criteria after
    it do not move. This is the shape the hand-carved issue took on 2026-10-06.

For each row at `carved (whole)`, nothing is minted: the issue's own `Status:`
goes back to `needs-harden`, and the same record is appended under
`## Carved whole by run <batch>`. A second number for the same work would be
two files for one thing.

WHAT IT REFUSES. A run that has not merged: its ledger's `State:` reads
`merged`, or its `Branch:` is an ancestor of the checkout's `HEAD`. A carved
row whose carve stamps `check_attempt_cap.py` cannot read. A source issue
file that is missing or doubled. Exit 0 done or nothing to do, 1 refused, 2 a
file could not be read.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "lib"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(LIB))
cap = _load("mint_cap", HERE / "check_attempt_cap.py")
ids = _load("mint_criteria_ids", HERE / "criteria_ids.py")
levels = _load("mint_issue_level", HERE / "issue_level.py")
next_batch = _load("mint_next_batch", LIB / "next_batch.py")
claim_number = _load("mint_claim_number", LIB / "claim_number.py")

BRANCH_LINE = re.compile(r"^Branch:\s*`([^`]+)`", re.MULTILINE)
PREFIX_LINE = re.compile(r"Register prefix:\s*`([\w-]+?)-NN`")
HEADER = re.compile(r"^(?P<key>[A-Z][\w ]*):\s*(?P<value>.*)$")


class Refused(Exception):
    pass


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True)


def repo_root(path):
    found = git(["rev-parse", "--show-toplevel"], path)
    return found.stdout.strip() if found.returncode == 0 else None


def has_merged(ledger_text, repo):
    """True when the ledger says `merged`, or its branch is in `HEAD`."""
    if next_batch.run_is_merged(ledger_text):
        return True
    branch = BRANCH_LINE.search(ledger_text)
    if not branch or not repo:
        return False
    if git(["rev-parse", "--verify", "--quiet", branch.group(1)],
           repo).returncode != 0:
        return False
    return git(["merge-base", "--is-ancestor", branch.group(1), "HEAD"],
               repo).returncode == 0


def source_file(issues_dir, issue):
    found = [path for path in sorted(issues_dir.glob("*.md"))
             if re.match(rf"{re.escape(issue)}-", path.name, re.IGNORECASE)]
    if len(found) != 1:
        raise Refused(f"issue {issue}: {len(found)} files in {issues_dir} "
                      f"carry that number, and the carve needs exactly one.")
    return found[0]


def headers(body):
    """The `Key: value` lines above the first heading."""
    found = {}
    for line in body.splitlines():
        if line.startswith("#"):
            break
        match = HEADER.match(line)
        if match:
            found.setdefault(match.group("key").lower(), match.group("value"))
    return found


def title(body):
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled"


def own_lines(text):
    """A criterion's own lines: its first line and the indented lines under
    it. A note or a paragraph after the last criterion is not part of it."""
    lines = text.splitlines(keepends=True)
    kept = lines[:1]
    for line in lines[1:]:
        if not line.strip() or not line[:1].isspace():
            break
        kept.append(line)
    return "".join(kept)


def carved_criteria(body, carved):
    """`[(name, its text)]` for each carved criterion, in the issue's order."""
    wanted = set(carved)
    return [(f"C{number}", own_lines(text))
            for number, text in ids.criteria(body) if f"C{number}" in wanted]


def register_rows(row, ledger_text):
    prefix = PREFIX_LINE.search(ledger_text)
    patterns = [r"\brn-[0-9a-f]{6}-[\w]+(?:-[\w]+)*"]
    if prefix:
        patterns.insert(0, re.escape(prefix.group(1)) + r"-[\w]+(?:-[\w]+)*")
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, row):
            name = match.group(0).rstrip("-")
            if name not in found:
                found.append(name)
    return found


def verdict_paths(ledger, issue, repo):
    folder = ledger.parent / "verdicts"
    if not folder.is_dir():
        return []
    pattern = re.compile(rf"^{re.escape(issue)}-attempt-\d+(?:-\w+)?\.md$",
                         re.IGNORECASE)
    paths = sorted(path for path in folder.iterdir() if pattern.match(path.name))
    return [os.path.relpath(path, repo) if repo else str(path) for path in paths]


def side_branch(ledger_text, issue, repo):
    branch = BRANCH_LINE.search(ledger_text)
    if not branch or not repo:
        return None
    name = f"{branch.group(1)}-{issue}-carved"
    if git(["rev-parse", "--verify", "--quiet", name], repo).returncode == 0:
        return name
    return None


def record(row, ledger, ledger_text, issue, repo, heading="###"):
    rows = register_rows(row, ledger_text)
    verdicts = verdict_paths(ledger, issue, repo)
    branch = side_branch(ledger_text, issue, repo)
    lines = [f"{heading} Strike history", "",
             "The issue's ledger row, as the run left it:", "", "```text",
             row.strip(), "```", "", f"{heading} Register rows", ""]
    lines += [f"- `{name}`" for name in rows] or ["- none named in the row"]
    lines += ["", f"{heading} Verdicts", ""]
    lines += [f"- `{path}`" for path in verdicts] or ["- none beside the ledger"]
    lines += ["", f"{heading} Where the code is", ""]
    lines.append(f"Branch `{branch}`, which no merge carries." if branch else
                 "No side branch named `<run branch>-<issue>-carved` exists, so "
                 "the carved code is in the branch history of the run, if "
                 "anywhere.")
    return "\n".join(lines) + "\n"


def carve_of(row, body):
    names = {f"C{number}" for number, _ in ids.criteria(body)}
    carve, faults = cap.read_carve(row, names)
    if faults:
        raise Refused("the carve stamps cannot be read: " + " ".join(faults))
    return carve, names


def after_text(row):
    found = list(cap.MARKER["carve"].finditer(row))
    return f"after gates {found[0].group('round')}" if found else "at launch"


def mint_part(issue, run_id, row, ledger, ledger_text, issues_dir, repo):
    path = source_file(issues_dir, issue)
    body = path.read_text(encoding="utf-8")
    carve, _ = carve_of(row, body)
    if not carve.ids or carve.whole:
        raise Refused(f"issue {issue} is ledgered `done (carved)`, and its row "
                      + ("carves it whole." if carve.whole
                         else "names no carved criterion."))
    parts = carved_criteria(body, carve.ids)
    when = after_text(row)
    head = headers(body)
    slug = re.sub(r"[^a-z0-9]+", "-", title(body).lower()).strip("-")[:40]
    number = claim_number.claim("issue", str(issues_dir), who=run_id,
                                slug=f"{slug}-carved")
    name = f"{number}-{slug}-carved.md"
    names = ", ".join(carve.ids)
    invariants = ids.section(body, "must still be true").strip()
    text = "\n".join([
        "Status: needs-harden",
        f"Origin: {issue}/{run_id}",
        f"Carved from: issue {issue} in run {run_id}, criteria {names}, {when}",
        "",
        f"Sentence: {head.get('sentence', title(body))}, the part run "
        f"{run_id} carved out",
        "",
        f"Touches: {head.get('touches', 'unknown')}",
        f"Kind: {head.get('kind', 'product')}",
        "Level: full",
        f"Run: {head.get('run', 'unknown')}",
        "",
        f"# {title(body)}: the carved part",
        "",
        "## Parent",
        "",
        f"Carved out of issue {issue}, `{path.name}`, by run `{run_id}` "
        f"{when}, on the standing rule of 2026-10-06: a run never blocks on "
        f"one feature. The rest of "
        f"{issue} shipped in that run.",
        "",
        "## Why this needs hardening before anyone builds it",
        "",
        f"Criteria {names} failed their gates in run `{run_id}`. The record "
        f"below is what that run learned; read it before sharpening.",
        "",
        record(row, ledger, ledger_text, issue, repo).rstrip("\n"),
        "",
        "## Acceptance criteria",
        "",
        f"Carried word for word from issue {issue}.",
        "",
        "".join(text for _, text in parts).rstrip("\n"),
        "",
    ] + (["## Must still be true", "",
          f"Carried from issue {issue}.", "", invariants, ""]
         if invariants else []) + [
        "## Blocked by",
        "",
        f"- {path.stem}",
        "",
    ])
    (issues_dir / name).write_text(text, encoding="utf-8")
    # Each criterion is replaced inside its own section, never earlier in the
    # file, where the same words may stand in a note.
    start = body.find(ids.section(body, "acceptance criteria"))
    for criterion, chunk in parts:
        moved = (f"- [ ] MOVED to issue {number}, `{name}`: carved by run "
                 f"`{run_id}` {when}.\n")
        at = body.find(chunk, max(start, 0))
        body = body[:at] + moved + body[at + len(chunk):]
    path.write_text(body, encoding="utf-8")
    return f"issue {issue}: {names} minted as {name}"


def send_back(issue, run_id, row, ledger, ledger_text, issues_dir, repo):
    path = source_file(issues_dir, issue)
    body = path.read_text(encoding="utf-8")
    carve_of(row, body)
    status = (f"Status: needs-harden — carved whole by run {run_id}; its "
              f"record is the last section of this file.")
    body, count = re.subn(r"^Status:.*$", status, body, count=1,
                          flags=re.MULTILINE)
    if not count:
        body = status + "\n" + body
    body = (body.rstrip("\n") + f"\n\n## Carved whole by run {run_id}\n\n"
            f"Nothing of this issue shipped in run `{run_id}`. It goes back "
            f"through hardening with this record, on the standing rule of "
            f"2026-10-06: a run never blocks on one feature.\n\n"
            + record(row, ledger, ledger_text, issue, repo))
    path.write_text(body, encoding="utf-8")
    return f"issue {issue}: carved whole, sent back to needs-harden"


def mint(ledger, issues_dir):
    ledger_text = ledger.read_text(encoding="utf-8")
    run_id = ledger.parent.name
    repo = repo_root(issues_dir)
    if not has_merged(ledger_text, repo):
        raise Refused(
            f"run {run_id} has not merged: its `State:` does not read "
            f"`merged`, and its `Branch:` is not in the checkout's HEAD. A "
            f"carve is minted after the merge.")
    texts = [path.read_text(encoding="utf-8", errors="replace")
             for path in sorted(issues_dir.glob("*.md"))]
    done = []
    for issue, status in levels.status_rows(ledger_text):
        status = status.replace("*", "").replace("`", "").strip()
        if status not in next_batch.CARVED_STATUSES:
            continue
        row = cap.find_row(ledger_text, issue)
        if status == "done (carved)":
            if any(found.group("issue").lower() == issue.lower()
                   and found.group("run").lower() == run_id.lower()
                   for text in texts
                   for found in next_batch.CARVED_FROM.finditer(text)):
                done.append(f"issue {issue}: already minted")
                continue
            done.append(mint_part(issue, run_id, row, ledger, ledger_text,
                                  issues_dir, repo))
        else:
            body = source_file(issues_dir, issue).read_text(encoding="utf-8")
            if any(found.group("run").lower() == run_id.lower()
                   for found in next_batch.CARVED_WHOLE.finditer(body)):
                done.append(f"issue {issue}: already sent back")
                continue
            done.append(send_back(issue, run_id, row, ledger, ledger_text,
                                  issues_dir, repo))
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--issues", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.ledger.is_file() or not args.issues.is_dir():
        print(f"mint_carved: cannot read {args.ledger} or {args.issues}.",
              file=sys.stderr)
        return 2
    try:
        done = mint(args.ledger.resolve(), args.issues.resolve())
    except Refused as refusal:
        print(f"Refused: {refusal}", file=sys.stderr)
        return 1
    print("\n".join(done) if done else "no carved issue in this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
