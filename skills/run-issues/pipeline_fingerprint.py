#!/usr/bin/env python3
"""What the pipeline WAS when a run ran. Ticket 37, ruling 23.

The three repositories that hold this pipeline -- the skills, the agents and
the hooks -- are separate git repositories, and on 2026-09-05 they sat at
`5215fb5`, `24f37ef` and `19b097f` with NO ledger and NO cost row naming any of
them. So a row saying run twelve was faster than run four could not say what
the pipeline was when either ran, which is the question ticket 37 exists to
answer. The launch writes these three HEADs into the ledger header and the
per-run line copies them.

**A dirty tree still runs.** Ruling 23 says the mark is a fact, not a refusal,
and the measurement behind that is on this machine: the hooks repository held
seven uncommitted files on 2026-09-06, six of them the daily brief's own
records and one a `__pycache__` file. A launch that refused there would stop a
run for a byte-compiled file. What the mark buys is narrower and worth having:
a row whose fingerprint is dirty may not be compared cleanly against another,
because the commit it names is not what actually ran.

The `hooks` repository is rooted at `~/.claude`, not `~/.claude/hooks` --
measured, not assumed, with `git rev-parse --show-toplevel`. It carries the
daily brief and the memory directory as well, which is why its tree is so often
dirty.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
from dataclasses import dataclass

UNKNOWN = "unknown"
LABEL = "Pipeline fingerprint at launch:"

# Twelve characters, the same width `git log --oneline` is configured to here
# and long enough that a collision is not a practical concern.
WIDTH = 12

REPOS = {
    "skills": pathlib.Path.home() / ".claude" / "skills",
    "agents": pathlib.Path.home() / ".claude" / "agents",
    # Rooted at ~/.claude, measured with `git rev-parse --show-toplevel`.
    "hooks": pathlib.Path.home() / ".claude",
}

LINE = re.compile(
    r"^\s*-\s*(?P<name>skills|agents|hooks)\s*:\s*`(?P<head>[^`]+)`"
    r"(?P<dirty>\s+dirty)?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Mark:
    head: str
    dirty: bool


def _git(root, *args) -> str:
    try:
        done = subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def measure(repos=None):
    """`{name: Mark}` for each repository. Never raises, never refuses."""
    found = {}
    for name, root in (repos or REPOS).items():
        head = _git(root, "rev-parse", f"--short={WIDTH}", "HEAD").strip()
        if not head:
            found[name] = Mark(UNKNOWN, False)
            continue
        found[name] = Mark(head, bool(_git(root, "status", "--porcelain").strip()))
    return found


def header_lines(marks) -> str:
    """The ledger header block the launch writes. Additive to ticket 39's."""
    lines = [LABEL]
    for name in ("skills", "agents", "hooks"):
        if name not in marks:
            continue
        mark = marks[name]
        lines.append(f"  - {name}: `{mark.head}`" + (" dirty" if mark.dirty else ""))
    lines.append(
        "  (the three repositories this pipeline runs from; ticket 37, ruling "
        "23. `dirty` means that tree held uncommitted files at launch, so the "
        "commit named is not exactly what ran. It is a fact, never a refusal.)")
    return "\n".join(lines)


def from_ledger(text):
    """`{name: Mark}` read back out of a ledger header, or `{}`.

    An empty answer is every ledger written before this sitting, and ruling 3
    keeps all of them, so it is a normal reading and never an error.
    """
    found = {}
    for match in LINE.finditer(text or ""):
        found[match.group("name")] = Mark(match.group("head"),
                                          bool(match.group("dirty")))
    return found


def as_record(marks):
    """The `fingerprint` field of a per-run line."""
    return {name: {"head": mark.head, "dirty": mark.dirty}
            for name, mark in sorted(marks.items())}


if __name__ == "__main__":
    print(header_lines(measure()))
