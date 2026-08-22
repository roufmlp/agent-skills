#!/usr/bin/env python3
"""Refuse a MANIFEST that has stopped describing the live tree.

This repo is a publication. The files Claude Code actually reads live in
`~/.claude/`, and MANIFEST.md is the map between the two. The map goes stale in
one direction far more often than the other: somebody writes a NEW live file,
and nothing anywhere notices it was never published.

**Measured twice in one week.** `check_finale_stage.py` was written live on
2026-08-21 and `orchestrator_cost.py` on the same day; both were still
unpublished on 2026-08-22, when a panel review found them by hand. The reminder
that was supposed to catch this fires "after editing any file listed in its
MANIFEST.md" — and a new file is listed nowhere, so it never fires. A reminder
with a hole exactly the shape of the fault is not a reminder.

So this refuses instead. Three refusals:

    unlisted           a file sits in a published live directory and no row and
                       no withheld entry names it
    dead-source        a row's live source matches nothing on disk
    dead-publication   a row's published path matches nothing in this repo

**It is keyed on the PRESENCE of a file, never on its content.** The published
copy differs from the live copy by design — the scrub rules rewrite names, paths
and run ids on every sync — so a content diff would alarm on every file for ever
and be switched off within a day. Presence is the one thing the two copies must
agree on.

It cannot tell a session record from an instruction file, and does not try. A
file that should never ship goes in MANIFEST.md's ```withheld block, where the
decision to withhold it is written down rather than remembered. That is the
point: the only way to silence this check is to record what you decided.

Exit 0 means the map is accurate. Exit 1 prints every disagreement and refuses.

    python3 check_manifest_coverage.py
"""

from __future__ import annotations

import argparse
import glob
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field

# Not decisions anybody records: a compiler dropping and the dot-directories
# every tool leaves behind. `~/.claude/agents` is itself a git checkout, so
# walking hidden directories would enumerate its whole object store.
SKIP_DIRS = {"__pycache__"}

BACKTICKED = re.compile(r"`([^`]+)`")
WITHHELD_BLOCK = re.compile(r"^```withheld\n(.*?)^```", re.MULTILINE | re.DOTALL)


@dataclass
class Manifest:
    published: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)


def parse_manifest(text: str) -> Manifest:
    """The two path columns of the source table, plus the withheld block.

    A row is read only for what is inside backticks, which is how the prose in
    either cell — "(16 role definitions...)", "written for this repo; no live
    source" — stays out of the way. The header row and the `|---|` rule carry no
    backticks at all, so neither needs a special case.
    """
    parsed = Manifest()
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        published = BACKTICKED.search(cells[0])
        if not published:
            continue
        parsed.published.append(published.group(1))
        source = BACKTICKED.search(cells[1])
        if source:
            parsed.sources.append(source.group(1))

    for block in WITHHELD_BLOCK.findall(text):
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parsed.withheld.append(line)
    return parsed


def expand(pattern: str, live_root: pathlib.Path) -> str:
    """`~/x` against the given root, so the tests can build a whole fake home."""
    if pattern.startswith("~/"):
        return str(pathlib.Path(live_root) / pattern[2:])
    return pattern


def is_live(pattern: str) -> bool:
    return pattern.startswith("~/")


def watched_directories(sources, live_root: pathlib.Path) -> list[pathlib.Path]:
    """The directories that exist to hold published files.

    Start from the parent of each live-source PATTERN, not of its matches, so
    `agents/*.md` watches `agents/` whether or not anything matches today.

    Then drop the containers. A directory holding another watched directory more
    than one level down is somewhere the pack merely passes through, not a
    publication directory: `~/.claude` is the whole tool installation — uploads,
    projects, history, every unpublished skill — and sweeping it would raise
    hundreds of files no row could ever describe. The steering docs that sit
    loose in it are named one row at a time and checked by `dead-source`
    instead, which is the trade: a NEW loose file there is not caught. Every
    directory the pack owns outright is still swept, `panel-review/` included,
    because its `references/` child is one level down and does not shadow it.
    """
    seen = {pathlib.Path(expand(s, live_root)).parent
            for s in sources if is_live(s)}
    return sorted(
        directory for directory in seen
        if not any(other != directory
                   and other.parent != directory
                   and directory in other.parents
                   for other in seen)
    )


def files_under(directory: pathlib.Path) -> list[pathlib.Path]:
    if not directory.is_dir():
        return []
    found = []
    for root, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in SKIP_DIRS]
        found.extend(pathlib.Path(root) / name for name in filenames)
    return found


def covered(path: pathlib.Path, patterns, live_root: pathlib.Path) -> bool:
    """Does any pattern name this exact file?

    `PurePath.match` is deliberate: `fnmatch` lets `*` cross a directory
    separator, so `agents/*.md` would silently swallow a whole new
    `agents/drafts/` folder — the case a coverage check exists to catch.
    """
    for pattern in patterns:
        if not is_live(pattern):
            continue
        if pathlib.PurePath(path).match(expand(pattern, live_root)):
            return True
    return False


def audit(manifest_path, live_root, repo_root) -> list[tuple[str, str]]:
    """Every disagreement between the map and the two trees, in reading order."""
    manifest_path = pathlib.Path(manifest_path)
    live_root = pathlib.Path(live_root)
    repo_root = pathlib.Path(repo_root)
    parsed = parse_manifest(manifest_path.read_text())
    problems: list[tuple[str, str]] = []

    for source in parsed.sources:
        if is_live(source) and not glob.glob(expand(source, live_root)):
            problems.append(("dead-source", source))

    for published in parsed.published:
        if not glob.glob(str(repo_root / published)):
            problems.append(("dead-publication", published))

    for directory in watched_directories(parsed.sources, live_root):
        for path in sorted(files_under(directory)):
            if covered(path, parsed.sources, live_root):
                continue
            if covered(path, parsed.withheld, live_root):
                continue
            problems.append(("unlisted", str(path)))
    return problems


REMEDY = {
    "unlisted": (
        "Publish it with a MANIFEST row, or record it in the ```withheld block. "
        "Deciding not to publish is fine; leaving it undecided is what this refuses."
    ),
    "dead-source": "The live file moved or went. Fix the row or drop it.",
    "dead-publication": "The published file moved or went. Fix the row or drop it.",
}


def render(problems) -> str:
    if not problems:
        return "MANIFEST describes the live tree."
    lines = [f"REFUSED: {len(problems)} disagreement(s) between MANIFEST and the trees.", ""]
    for kind in ("unlisted", "dead-source", "dead-publication"):
        hits = [subject for found, subject in problems if found == kind]
        if not hits:
            continue
        lines.append(f"{kind} ({len(hits)}):")
        lines.extend(f"    {subject}" for subject in hits)
        lines.append(f"  {REMEDY[kind]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Refuse a stale MANIFEST.")
    parser.add_argument("--manifest", default=str(here / "MANIFEST.md"))
    parser.add_argument("--live-root", default=str(pathlib.Path.home()))
    parser.add_argument("--repo-root", default=str(here))
    args = parser.parse_args(argv)

    try:
        problems = audit(args.manifest, args.live_root, args.repo_root)
    except OSError as error:
        print(f"REFUSED unreadable-manifest: {error}", file=sys.stderr)
        return 2

    if problems:
        print(render(problems), file=sys.stderr)
        return 1
    print(render(problems))
    return 0


if __name__ == "__main__":
    sys.exit(main())
