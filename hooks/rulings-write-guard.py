#!/usr/bin/env python3
"""Refuse a write that would leave an unreadable entry in a `rulings.md`.

PreToolUse hook on Edit|Write, registered in `~/.claude/settings.json`.

Ruled by the human on 2026-09-20, at the close of a hardening pass.

WHAT HAPPENED. At the start of that pass `rulings.py --list` exited 1 over one
project's `.scratch/rulings.md` and dropped NINE of 106 entries. Every one
failed the same way: its `Carried by:` line named several paths, and the
reader's `CARRIED` pattern takes one and forbids a second backtick. Four of the
nine had been written the DAY BEFORE, so this was a live rate and not old
damage. Three of the dropped entries governed a guard road, a storage-budget
fault and an attempt ceiling.

WHY IT MATTERS MORE THAN A SHORT LISTING. `check_queue_shard.py` grades a
queued question against these entries. A ruling that does not parse cannot
refuse a question the human has already answered, so the next pass asks them
again -- which is the one failure the rulings file exists to prevent. It is also
silent: `parse` steps over a bad entry and the caller reports a confident
count of what survived.

WHY A HOOK AND NOT A REMINDER. `rulings.py` has refused this shape since
2026-09-17 and says so in its own docstring. The refusal was never wired to
anything that runs at write time, so nine bad entries were written anyway by
sessions that had the checker available. That is the test `~/.claude/CLAUDE.md`
sets: a rule an agent is asked to remember is not a rule. This one can refuse,
so it refuses.

WHAT IS REFUSED

1. An `Edit` or a `Write` whose target basename is `rulings.md` and whose
   RESULT would carry MORE unreadable entries than the file carries now.
2. A write that empties a rulings file which currently holds entries. That is
   the house rule of `run-issues/empty_input.py` -- a reader that parsed
   nothing may not report a pass -- applied to the write side, because a
   truncating write would otherwise sail past check 1 with zero bad entries.

The hook applies the edit in memory and parses the result. It never writes.

WHY IT DELEGATES THE PARSE. `entries_and_skips` in `~/.claude/skills/lib/
rulings.py` is the one reader, and it already walks the whole file and reports
every entry it cannot place rather than enumerating forbidden spellings. A
second parser here would be a guard built as a list of banned shapes, which
`~/.claude/coderules.md` refuses in terms, and two readers disagreeing about
what an entry is would be the same silence one layer down.

WHAT IS DELIBERATELY LET PAST

- A file that is not named `rulings.md`. The shape is this file's, not a
  general markdown rule.
- A write that leaves the SAME number of bad entries or fewer. A pass repairing
  an inherited mess must be able to land a partial repair, and refusing that
  would make the file harder to fix than to break. Only a write that ADDS a bad
  entry is refused.
- Every read, every `Bash` command, and a `rulings.md` outside a `.scratch`
  tree, which is somebody else's file with the same name.
- A payload this hook cannot parse, a missing reader, and an `Edit` whose
  `old_string` does not appear exactly once -- that last one fails on the
  Edit tool's own terms and is not this hook's call. Each returns 0 rather
  than break a session or guess.

The block mechanism: read the payload from stdin, write the reason to stderr,
exit 2. Exit 0 lets the tool run.
"""

from __future__ import annotations

import io
import json
import os
import sys

LIB = os.path.expanduser("~/.claude/skills/lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)


def load_reader():
    """`entries_and_skips` from the one reader, or None where it is absent."""
    try:
        from rulings import entries_and_skips  # type: ignore
        return entries_and_skips
    except Exception:
        return None


def is_rulings(path: str) -> bool:
    """Whether this path is a project's rulings file."""
    if os.path.basename(path) != "rulings.md":
        return False
    # A `rulings.md` belonging to some other tool, outside a scratch tree, is
    # not this file and does not carry this shape.
    parts = path.replace("\\", "/").split("/")
    return ".scratch" in parts


def current(path: str) -> str:
    try:
        return io.open(path, encoding="utf-8").read()
    except Exception:
        return ""


def resulting_text(tool: str, tool_input: dict, path: str):
    """The file's content after this tool call, or None when unknowable."""
    if tool == "Write":
        return str(tool_input.get("content") or "")
    if tool == "Edit":
        old = tool_input.get("old_string")
        new = tool_input.get("new_string")
        if old is None or new is None:
            return None
        text = current(path)
        if not text:
            return None
        if tool_input.get("replace_all"):
            return text.replace(str(old), str(new))
        if text.count(str(old)) != 1:
            return None  # Edit fails on its own terms; not this hook's call.
        return text.replace(str(old), str(new), 1)
    return None


SHAPE = (
    "The shape each entry takes:\n"
    "  ## <YYYY-MM-DD> `<id>` - <subject>\n"
    "  Ruled: <the ruling, on one line>\n"
    "  Carried by: `<ONE path>`\n\n"
    "`Carried by:` takes exactly ONE backticked path. Where a ruling lives in\n"
    "several places, put the first in `Carried by:` and the rest on an\n"
    "`Also carried by:` line underneath, which the reader ignores and a human\n"
    "still reads. That is how the nine entries of 2026-09-20 were repaired.\n\n"
    "Ruled 2026-09-20. See ~/.claude/hooks/rulings-write-guard.py.\n"
)

WHY = (
    "A ruling this reader cannot parse is DROPPED IN SILENCE, and a dropped\n"
    "ruling cannot refuse the question it answered -- `check_queue_shard.py`\n"
    "grades queued questions against these entries, so the next pass asks\n"
    "again about something already ruled on.\n\n"
)


def refuse_added(added, before: int, after: int) -> int:
    lines = "\n".join("  " + s for s in added[:4])
    more = "" if len(added) <= 4 else f"\n  ... and {len(added) - 4} more"
    sys.stderr.write(
        "REFUSED - this write adds an entry `rulings.py` cannot read.\n"
        f"Unreadable entries before this write: {before}. After it: {after}.\n\n"
        f"{lines}{more}\n\n" + WHY + SHAPE
    )
    return 2


def refuse_emptied(before: int) -> int:
    sys.stderr.write(
        "REFUSED - this write would leave a rulings file with no readable entry.\n"
        f"It holds {before} today.\n\n"
        "A reader that parsed nothing may not report a pass -- the house rule in\n"
        "`~/.claude/skills/run-issues/empty_input.py`, applied here to the write\n"
        "side. A truncating write would otherwise pass the bad-entry count with a\n"
        "clean zero while destroying every ruling given on this project.\n\n"
        "If you genuinely mean to empty it, move the file aside in a `Bash` call,\n"
        "which this hook does not judge, and say why in the same turn.\n"
    )
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.

    tool = str(payload.get("tool_name") or "")
    if tool not in ("Edit", "Write"):
        return 0

    tool_input = payload.get("tool_input") or {}
    path = str(tool_input.get("file_path") or "")
    if not is_rulings(path):
        return 0

    reader = load_reader()
    if reader is None:
        return 0  # No reader, no opinion. Say nothing rather than guess.

    after_text = resulting_text(tool, tool_input, path)
    if after_text is None:
        return 0

    try:
        entries_after, skips_after = reader(after_text)
        entries_before, skips_before = reader(current(path))
    except Exception:
        return 0

    if entries_before and not entries_after:
        return refuse_emptied(len(entries_before))

    if len(skips_after) <= len(skips_before):
        return 0  # Same or fewer. A partial repair must be able to land.

    before_set = set(skips_before)
    added = [s for s in skips_after if s not in before_set] or list(skips_after)
    return refuse_added(added, len(skips_before), len(skips_after))


if __name__ == "__main__":
    sys.exit(main())
