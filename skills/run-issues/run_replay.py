#!/usr/bin/env python3
"""Ruling 16's one-time replay. Ticket 37, sitting 5.

    python3 run_replay.py --repo <checkout> --dry-run
    python3 run_replay.py --repo <checkout>

Sittings 2, 3 and 4 built the record, the writers and the reader. Every figure
they built reads `not measured` on today's record, because the writers landed
after the last finale ran, so `run_compare.py` reports nothing and the whole
reader is unproven against real figures. Ruling 16 closes that with "a one-time
replay over the seven finale runs' transcripts to backfill the new fields, so
the first trend reads on the day the build lands".

## Why it rewrites rather than appends

`runs.jsonl` is append-only, and `run_records.append_run` refuses a second line
for a batch already present -- ruling 4, which is ticket 36's fault 9. So there
is no road that appends a filled line beside an empty one: the replay must
replace the line where it stands.

**What stops a half-finished replay leaving a line part-filled**, in two parts:

  1. **Per line.** A replacement record is built whole in memory, merged over
     the line it replaces, and validated through `run_records.validate_run` --
     the same rules a finale writes through. A batch the replay could not
     measure yields nothing at all, and its line is left byte for byte as it
     was.
  2. **Per file.** `rewrite` renders every line of the file, including the ones
     it did not touch and any line that is not JSON, writes them to a temporary
     file in the SAME directory, and moves it over the original with
     `os.replace`. That is atomic on one filesystem, so a reader sees the old
     file or the new one. If any single line is refused, nothing is written at
     all.

## The rule for what it writes

**The replay writes what today's `run_costs.py` would have written for that
run.** One rule, and it is why the replay calls `build_record` rather than
composing a record of its own: a second builder of one line drifts from the
first, which is the lesson `journal_for` taught in ticket 39 sitting 2 and
`read_transcript` in sitting 3.

The human ruled the reach on 2026-09-06, at the keyboard, after the delta was
measured: the replay ALSO repairs the five cells sitting 2 marked `borrowed`,
and drops the mark. The measurement that settled it is in `BORROWED_WAS_WRONG`
below.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_records


# --------------------------------------------------------------------------
# The seven lines, and where each one's ledger lives.
#
# This is a TYPED TABLE and not a search, and the reason is a fault this
# ticket met twice. `run_session.ledger_for_batch` looks under
# `.scratch/*/runs/*/run.md` and `.scratch/*/round-brief.md` in every worktree
# (ticket 38, ruling 9: no old path keeps working), and five of these seven
# ran before that layout, so it finds two of them. A looser search finds the
# wrong file: measured 2026-09-06, `archive-run-batch-44d0a8.md` names
# `batch-45c8b1` in its own text, and `runs/batch-170a59/run.md` names
# `batch-b5e96d`, so "the file that mentions this batch" picks a foreign
# ledger for two of the seven. Taking the first thing that matches is the
# shape of the fault ruling 28 sent sitting 3 to repair.
#
# So each row is named, and each is PROVED before it is used: the ledger must
# carry a `Worktree:` line, and that worktree's transcript directory must hold
# at least one transcript naming this batch id. That proof is
# `run_session.sessions_for_batch`'s own, and it is the check a foreign
# session cannot pass.
FEATURE = ".scratch/example-feature"

LEDGERS = {
    "batch-88624c": f"{FEATURE}/run-prev-run-batch-88624c.md",
    "review-375cbf": f"{FEATURE}/archive-run-batch-375cbf-merged.md",
    "batch-45c8b1": f"{FEATURE}/archive-run-batch-45c8b1.md",
    "batch-44d0a8": f"{FEATURE}/archive-run-batch-44d0a8.md",
    "batch-b5e96d": f"{FEATURE}/runs/batch-b5e96d/run.md",
    "batch-170a59": f"{FEATURE}/runs/batch-170a59/run.md",
}

BRIEFINGS = {
    "batch-88624c": f"{FEATURE}/merge-briefing-prev-run-batch-88624c.md",
    "review-375cbf": f"{FEATURE}/archive-merge-briefing-batch-375cbf.md",
    "batch-45c8b1": f"{FEATURE}/archive-merge-briefing-batch-45c8b1.md",
    "batch-44d0a8": f"{FEATURE}/archive-merge-briefing-batch-44d0a8.md",
    "batch-b5e96d": f"{FEATURE}/runs/batch-b5e96d/merge-briefing.md",
    "batch-170a59": f"{FEATURE}/runs/batch-170a59/merge-briefing.md",
}

# The seventh line, and it CANNOT be replayed. Its batch id is synthetic --
# the record carries `batch_synthetic: true` -- because the 2026-08-30 finale
# row named no batch id and sitting 2 minted one to key the line by. No run was
# ever called `backfilled-2026-08-30`, so no ledger names it and no transcript
# can be found for it. It is listed here rather than left out, so that the
# replay REFUSES it by name instead of reporting six of seven and saying
# nothing about the one it never looked at.
UNREPLAYABLE = {
    "backfilled-2026-08-30": (
        "its batch id is synthetic. The 2026-08-30 finale wrote a row naming "
        "no batch id, and sitting 2 minted `backfilled-2026-08-30` to key the "
        "line by (`batch_synthetic: true` on the line itself). No run ever "
        "carried that id, so no ledger names it and no transcript can be "
        "found. Its new fields stay `not measured`, which is the honest "
        "reading."),
}

# The seven ruling 16 names.
SEVEN = tuple(LEDGERS) + tuple(UNREPLAYABLE)

# The five cells sitting 2 marked `borrowed`, measured wrong on 2026-09-06 and
# repaired here on the human's ruling of the same day. `Per issue` is the figure
# that settled it: stored at 1.34M to 1.87M across the five marked lines and
# measured at 4.29M to 9.98M, wrong by a factor of three to six on every one.
# Ticket 39 sitting 3 measured `batch-b5e96d` by hand at its finale -- "88
# subagents", "opus 149.7M / fable 0.3M", "14% orchestrator share" -- and its
# own line in the record disagreed with all three.
#
# Ruling 3 says no existing history may be lost, and git holds it: the record
# file is committed, so every cell replaced here stays readable for ever.
BORROWED_WAS_WRONG = ("issues", "subagents", "weighted", "orchestrator",
                      "per_issue")

# What the replay may write onto a line. Everything else the line already
# carries is kept, and `taken` above all: it is the day the run finished and
# `build_record` would stamp it with today's date.
NEW_FIELDS = ("quality", "faster", "longest_steps", "cache", "trial",
              "orchestrator_model", "worker_models", "fingerprint")

# **`hours` and `idle` are re-read too, and the reason is a fault the first
# real replay exposed rather than a preference.** Sitting 4 measured that
# these two were the run's own on all eighteen lines, so they are not in
# `BORROWED_WAS_WRONG`. But `faster` is computed from the FRESH reading, and
# keeping the stored `hours` beside it put two figures on one line that
# disagree: `batch-170a59` read `hours 8.06` next to `82.6` wall minutes per
# issue, which is 8.26 h over its six issues.
#
# Both numbers are `run_timings.py` on the same transcript, taken at different
# moments -- the finale's reading was taken before the last rows were written.
# Measured across the six replayed lines the gap runs 0.00 to 2.48 per cent.
# The line now carries ONE reading taken at ONE moment, which is the rule the
# whole replay runs on.
REMEASURED = BORROWED_WAS_WRONG + ("hours", "idle")


def _module(name):
    """A sibling module, imported once. `HERE` is on `sys.path` at import."""
    import importlib
    return importlib.import_module(name)


# --------------------------------------------------------------------------
# The rewrite. This is the half that must never leave a line part-filled.
# --------------------------------------------------------------------------


def render(text, replacements):
    """`(lines, refusal)` — every line of the file, with the named ones
    replaced.

    Works on RAW LINES and never on `run_records.read_lines(...).records`,
    because that hands back only the lines that parsed. Rendering the file from
    those would delete every line that did not, and ruling 3 says no existing
    history may be lost.
    """
    seen, out = {}, []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        try:
            found = json.loads(stripped)
        except ValueError:
            out.append(line)
            continue
        if not isinstance(found, dict):
            out.append(line)
            continue
        batch = str(found.get("batch") or "")
        if batch not in replacements:
            out.append(line)
            continue
        if batch in seen:
            return [], (
                f"REFUSED: `{batch}` appears twice in this file, and nothing "
                "was written. Rewriting the first would leave the second "
                "reading the old figures under the same key -- which is "
                "ticket 36's fault 9, the duplicate `review-375cbf` row, "
                "arriving from the other side. Delete one by hand and say "
                "which in the commit message.")
        seen[batch] = True
        out.append(json.dumps(replacements[batch], sort_keys=True))

    missing = [one for one in replacements if one not in seen]
    if missing:
        return [], (
            "REFUSED: no line in this file names "
            + ", ".join(f"`{one}`" for one in sorted(missing))
            + ", and nothing was written. A replay that skipped a line it was "
              "asked to fill would report success over a line still reading "
              "`not measured`.")
    return out, ""


def rewrite(path, replacements):
    """`(ok, message)`. Whole file or nothing, moved into place.

    Every replacement passes `run_records.validate_run` first, so the replay
    writes through the same rules a finale writes through. A road that walked
    round them could put into the record exactly what `append_run` is there to
    keep out.
    """
    path = pathlib.Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return False, (
            f"REFUSED: `{path}` could not be read ({error}), and nothing was "
            "written. A replay pointed at the wrong repository would "
            "otherwise mint an empty record file there.")

    checked = {}
    for batch, record in replacements.items():
        valid, why = run_records.validate_run(record)
        if why:
            return False, (f"REFUSED on `{batch}`, and NOTHING was written to "
                           f"any line: {why}")
        checked[batch] = valid

    lines, why = render(text, checked)
    if why:
        return False, why

    body = "".join(one + "\n" for one in lines)
    # `splitlines` then a newline after every line ADDS one to a file whose
    # last line carried none, so comparing the two byte for byte said "not
    # yet" for ever and rewrote the file on every run. The comparison is
    # against the text as this would render it.
    if body == _rendered(text):
        return True, f"{path.name} is already what the replay would write."

    ok, why = move_into_place(path, body)
    if not ok:
        return False, why
    return True, f"rewrote {len(checked)} line(s) of {path.name}"


def _rendered(text):
    """`text` in the shape `render` writes, so idempotence is testable."""
    return "".join(one + "\n" for one in (text or "").splitlines())


def check_before_writing(runs_path, replacements, populations):
    """`(ok, refusal)` — every write validated before the first byte of any.

    **The replay is half applied ACROSS the two files without this, and the
    `/code-review` pass of 2026-09-06 found it.** `main` wrote `issues.jsonl`
    and then `runs.jsonl`; a refusal on the second left 80 per-issue lines on
    disk for six runs whose per-run lines still read `not measured`. The
    per-line and per-file guarantees each hold and neither says anything about
    the pair.
    """
    for batch, rows in populations.items():
        rows = list(rows or ())
        if not rows:
            continue
        named, why = run_records.validate_issues(rows)
        if why:
            return False, f"REFUSED on `{batch}`, nothing written: {why}"
        if named != batch:
            return False, (
                f"REFUSED: the rows filed under `{batch}` name batch "
                f"`{named}`, and nothing was written.")
    for batch, record in replacements.items():
        _, why = run_records.validate_run(record)
        if why:
            return False, f"REFUSED on `{batch}`, nothing written: {why}"
    try:
        text = pathlib.Path(runs_path).read_text(encoding="utf-8")
    except OSError as error:
        return False, f"REFUSED: `{runs_path}` could not be read ({error})."
    _, why = render(text, replacements)
    if why:
        return False, why
    return True, ""


def move_into_place(path, body):
    """`(ok, refusal)`. Write beside the file, then move over it.

    `open(path, "w")` empties the file before the first byte is written, so a
    reader between those two moments sees an empty record and a crash there
    leaves one. `os.replace` is atomic on one filesystem, which is why the
    temporary file must sit in the SAME directory and not in the system
    temporary directory -- across filesystems the move becomes a copy and the
    guarantee is gone.
    """
    path = pathlib.Path(path)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(path.parent),
        prefix=path.name + ".", suffix=".replay", delete=False)
    try:
        with handle:
            handle.write(body)
        os.replace(handle.name, str(path))
    except OSError as error:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        return False, f"REFUSED: nothing was written ({error})."
    return True, ""


def rewrite_issues(path, populations):
    """`(ok, message)` for `issues.jsonl`, rendered whole so it can be re-run.

    `run_records.append_issues` refuses a second write for a batch already
    present, for ruling 4's reason carried onto this file: a run written twice
    here doubles every per-issue population a trend reads. The replay writes
    six batches at one moment and has to survive a second hand running it, so
    it renders the file rather than appending to it -- every line of another
    run kept where it stands, every line of a replayed run replaced.
    """
    path = pathlib.Path(path)
    checked = {}
    for batch, rows in populations.items():
        rows = list(rows or ())
        if not rows:
            continue
        named, why = run_records.validate_issues(rows)
        if why:
            return False, f"REFUSED on `{batch}`, nothing written: {why}"
        if named != batch:
            return False, (
                f"REFUSED: the rows filed under `{batch}` name batch "
                f"`{named}`, and nothing was written. A caller holding rows "
                "for one run under another's key has lost track of which run "
                "it is measuring.")
        checked[batch] = rows

    kept = []
    for line in _existing(path).splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        try:
            found = json.loads(stripped)
        except ValueError:
            kept.append(line)          # ruling 3, on the second file
            continue
        if not isinstance(found, dict):
            kept.append(line)
            continue
        if str(found.get("batch") or "") not in checked:
            kept.append(line)

    written = [json.dumps(one, sort_keys=True)
               for batch in checked for one in checked[batch]]
    body = "".join(one + "\n" for one in kept + written)
    if path.is_file() and body == path.read_text(encoding="utf-8"):
        return True, f"{path.name} is already what the replay would write."
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, why = move_into_place(path, body)
    if not ok:
        return False, why
    return True, (f"wrote {len(written)} issue line(s) for "
                  f"{len(checked)} run(s) to {path.name}")


def _existing(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def is_a_reading(value):
    """Did anything actually measure this?

    **Null is not a zero, and empty is not a reading.** Two readers answer
    "nothing" with an object rather than with `None`:
    `pipeline_fingerprint.as_record` returns `{}` for a ledger carrying no
    header, and `run_costs.quality_counts` returns its five keys all reading
    `None` for a ledger carrying no status table. Both were written straight
    over whatever the line already held until the `/code-review` pass of
    2026-09-06.

    A measured `0` IS a reading and is taken: a run with no strikes is a fact,
    and refusing it here would invert the very rule this exists to keep.
    """
    if value is None:
        return False
    if isinstance(value, dict):
        return any(is_a_reading(one) for one in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value)
    return True


def merged(old, new):
    """The line to write: what it already carried, with what was measured.

    **Named field by field, never `old | new`.** `build_record` stamps `taken`
    with `date.today()`, and ruling 12 orders lines by `taken`, so taking that
    key would move all seven replayed lines to the day of the replay and
    collapse the trend to one point. The same goes for the note: six carried
    notes hold 1,293 characters over ruling 15's cap that nothing else holds,
    and sitting 2 settled ruling 3 against ruling 15 in ruling 3's favour for
    what already exists.

    A measured `None` is NOT written over a figure the line already had. Null
    means nothing read it, and writing that over a reading is a loss rather
    than a correction.
    """
    found = dict(old)
    for name in NEW_FIELDS + REMEASURED:
        if is_a_reading(new.get(name)):
            found[name] = new[name]
    # **The mark is NARROWED, not dropped wholesale.** It names WHICH cells
    # came from another run, and sitting 4's reader skips a marked line per
    # FIGURE rather than per line. A cell the replay could not re-measure is
    # still borrowed, so it stays named; when none is left the key goes.
    if old.get("borrowed"):
        left = [name for name in BORROWED_WAS_WRONG
                if new.get(name) is None]
        if left:
            found["borrowed"] = left
        else:
            found.pop("borrowed", None)
    return found


# --------------------------------------------------------------------------
# The measurement. Every reader here already existed; not one is written
# again. `build_record` builds the line, so the replay and a finale cannot
# answer differently -- the drift `journal_for` taught ticket 39 in sitting 2
# and `read_transcript` in sitting 3.
# --------------------------------------------------------------------------

WORKTREE = "Worktree:"


def sessions_named_by(ledger_text, batch):
    """`(mains, refusal)` — this run's transcripts, oldest first.

    `run_session.sessions_for_batch` cannot be called: it starts from
    `ledger_for_batch`, which searches only the live layout and finds two of
    these seven. The PROOF it applies is the part that matters and it is
    reused whole -- the ledger's own `Worktree:` line, that path's project
    slug, and a transcript in it that names this batch id. That last check is
    the one a foreign session cannot pass, and skipping it is what gave run
    `batch-88624c` a row reading 1.01 h for an 8.4 h run on 2026-08-31.
    """
    session = _module("run_session")
    line = next((one for one in (ledger_text or "").splitlines()
                 if one.startswith(WORKTREE)), "")
    tree = session.parse_worktree_value(line)
    if not tree:
        return [], (
            f"the ledger carries no `{WORKTREE}` line, so nothing says which "
            f"directory's transcripts belong to batch `{batch}`. That line is "
            "the only road from a batch id to its transcripts (ticket 39, "
            "ruling 12).")

    slug = session.slug_for(tree)
    directory = os.path.join(session.PROJECTS, slug)
    if not os.path.isdir(directory):
        return [], (
            f"batch `{batch}` ran in `{tree}`, whose transcripts would sit in "
            f"`{slug}`, and no such directory exists under {session.PROJECTS}.")

    files = sorted(glob.glob(os.path.join(directory, "*.jsonl")))
    named = [one for one in files if session.names_the_batch(one, batch)]
    if not named:
        return [], (
            f"none of the {len(files)} transcript(s) in `{slug}` names batch "
            f"`{batch}`, so every one of them is a different session that "
            "happened to sit in the same directory. Nothing was read.")
    return sorted(named, key=session.last_stamp), ""


def _text(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def measure(repo, batch, ledger, briefing=None):
    """`(record, refusal)` — what today's `run_costs.py` would have written.

    `record["issue_lines"]` rides along: ruling 17's per-issue lines are built
    ONCE and used by both halves, because `build_record` divides ruling 5's
    figures by that population. Two builds would be one run with two
    populations that agree only by accident, which is a fault the review of
    2026-09-06 found in `run_costs.report` itself.
    """
    costs = _module("run_costs")
    session = _module("run_session")
    measures = _module("run_measures")

    ledger = pathlib.Path(ledger)
    if not ledger.is_file():
        return None, f"no ledger at `{ledger}`, so nothing was read."
    ledger_text = _text(ledger)

    mains, why = sessions_named_by(ledger_text, batch)
    if why:
        return None, why

    path = pathlib.Path(mains[-1])
    spawns = session.spawn_rows(mains)

    # The per-issue spans and the role names, off the run's own transcript
    # (ticket 39, ruling 21.3). `orphans` is not optional: one unattributed
    # spawn nulls the escalation count, because the escalation may be the
    # spawn that was lost.
    spans, orphans = None, None
    try:
        spans, orphans = _module("estimate_accuracy").actuals(path)
    except Exception as error:  # noqa: BLE001 - a reading never raises
        # SAID, never swallowed. `run_costs.report` prints this reason, and a
        # reading that failed must not look like one that found nothing --
        # the `ok`-on-nothing shape sitting 1 met on the live register.
        print(f"  the per-issue spans could not be read from {path} "
              f"({error}), so every figure drawn from the transcript is null "
              f"on `{batch}`.")

    briefing_text = _text(briefing) if briefing else ""
    journal_text = _text(_module("find_live_ledger").journal_for(str(ledger)))
    stamped = _module("run_step").read_steps(
        _module("run_step").steps_beside(str(ledger)))

    issue_lines = measures.issue_records(
        batch=batch, ledger_text=ledger_text, briefing_text=briefing_text,
        spans=spans, touched=costs._touched(repo))

    timings = costs.run([sys.executable, str(HERE / "run_timings.py"),
                         str(path)])
    hours = costs.number(r"wall clock\s+([\d.,]+)\s*h", timings)
    idle_hours = costs.number(r"nobody running\s+([\d.,]+)\s*h", timings)
    agent_hours = costs.number(r"a subagent running\s+([\d.,]+)\s*h", timings)
    issues = costs.issues_for(0, session, spawns)

    record = costs.build_record(
        batch=batch,
        kind="run",
        version=run_records.NOT_STATED,
        ledger_text=ledger_text,
        journal_text=journal_text,
        spans=spans,
        orphans=orphans,
        issue_lines=issue_lines,
        stamped=stamped,
        agent_steps=costs._agent_steps(session, spawns),
        idle_hours=idle_hours,
        agent_hours=agent_hours,
        issues=issues,
        hours=hours,
        weighted=costs._by_model(session, spawns, "weighted"),
        per_issue=costs._per_issue_by_model(session, spawns, issues),
        subagents=len(spawns) if spawns else None,
        orchestrator=costs._share_by_model(session, mains, spawns),
        idle=(idle_hours / hours) if hours and idle_hours is not None else None,
        cache=costs.probe_cache(path),
    )
    record["issue_lines"] = issue_lines
    return record, ""


# --------------------------------------------------------------------------
# The command. It reports on all seven, whatever it could measure.
# --------------------------------------------------------------------------


def replay(repo, ledgers=None, briefings=None, unreplayable=None):
    """`(measured, refused)` for every batch the tables name.

    `measured` is `{batch: record}`, each record carrying its `issue_lines`.
    `refused` is `[(batch, why)]`, and every batch appears in exactly one of
    the two -- a line reported by neither would be a line nobody looked at,
    reported as done.
    """
    ledgers = LEDGERS if ledgers is None else ledgers
    briefings = BRIEFINGS if briefings is None else briefings
    unreplayable = UNREPLAYABLE if unreplayable is None else unreplayable

    root = pathlib.Path(repo)
    measured, refused = {}, []
    for batch, why in sorted(unreplayable.items()):
        refused.append((batch, why))
    for batch, named in sorted(ledgers.items()):
        briefing = briefings.get(batch)
        record, why = measure(root, batch, root / named,
                              root / briefing if briefing else None)
        if why:
            refused.append((batch, why))
            continue
        measured[batch] = record
    return measured, refused


def main(argv=None, ledgers=None, briefings=None):
    """Ruling 16's replay, once. Reports on all seven; writes six lines.

    Exit 0 where it wrote what it could measure, 1 where a write was refused.
    A batch it could not measure is REPORTED and costs that line alone: a
    measurement never halts the rest, which is this pipeline's oldest rule
    about readings (the human, 2026-08-30).
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default="",
                        help="the checkout holding .scratch/workflow-audit; "
                             "the working directory by default")
    parser.add_argument("--dry-run", action="store_true",
                        help="measure and report; write nothing")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.repo) if args.repo else pathlib.Path.cwd()

    print("# Ruling 16's one-time replay\n")
    measured, refused = replay(root, ledgers=ledgers, briefings=briefings)

    for batch, why in refused:
        print(f"- `{batch}`: NOT REPLAYED -- {why}")
    if refused:
        print()

    seen = run_records.read_runs(root)
    on_file = {str(one.get("batch") or ""): one for one in seen.records}
    replacements, populations = {}, {}
    for batch, record in sorted(measured.items()):
        old = on_file.get(batch)
        if old is None:
            print(f"- `{batch}`: measured, but no line on the record carries "
                  "that id, so nothing was written for it.")
            continue
        lines = record.pop("issue_lines", [])
        replacements[batch] = merged(old, record)
        populations[batch] = lines
        counts = record.get("quality") or {}
        print(f"- `{batch}`: {counts.get('issues_graded')} issue(s) graded, "
              f"{len(lines)} per-issue line(s), trial "
              f"{(record.get('trial') or {}).get('state')}.")

    if not replacements:
        print("\nNothing to write.")
        return 0

    if args.dry_run:
        print(f"\n(--dry-run: {len(replacements)} line(s) would be rewritten "
              f"and {sum(len(one) for one in populations.values())} per-issue "
              "line(s) written. Nothing was touched.)")
        return 0

    ok, said = check_before_writing(root / run_records.RUNS, replacements,
                                    populations)
    if not ok:
        print("\n" + said)
        print("NOTHING was written to either file.")
        return 1

    # **The per-issue file first, then the per-run line, then the page.**
    # `run_records.write_view` renders from disk, so publishing before the
    # rewrite would publish the old figures -- the stale-first-render fault
    # the review of 2026-09-06 found in `run_costs.report`.
    ok, said = rewrite_issues(root / run_records.ISSUES, populations)
    print("\n" + said)
    if not ok:
        return 1

    ok, said = rewrite(root / run_records.RUNS, replacements)
    print(said)
    if not ok:
        return 1

    ok, said = run_records.write_view(root)
    print(said)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
