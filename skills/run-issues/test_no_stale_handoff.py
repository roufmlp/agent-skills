#!/usr/bin/env python3
"""No handoff file lives beside a skill.

The house rule is that handoffs are single-use — they serve the one session
resuming the interrupted work, and anything durable is promoted at write time
into an issue file, a primer, an ADR or a memory. A handoff that survives past
that session is a July task list a future session can read as current work.

`run-issues/HANDOFF-2026-07-27.md` was the file testing whether the rule was
real: 682 words of read-ordering pointers and a P1 list, twenty days past a
delete condition it wrote for itself in its own second sentence. It is deleted.
Git history keeps the bytes.

The glob is deliberate. Asserting only that one filename is gone leaves the next
handoff free to settle in beside a skill, and the rule is about the class, not
the instance.

Run: python3 test_no_stale_handoff.py
"""

import unittest
from pathlib import Path

RUN_ISSUES = Path(__file__).resolve().parent
SKILLS = RUN_ISSUES.parent

DELETED = RUN_ISSUES / "HANDOFF-2026-07-27.md"


class TestNoResidentHandoff(unittest.TestCase):
    def test_the_july_handoff_is_gone(self):
        self.assertFalse(
            DELETED.exists(),
            f"{DELETED} is back. It is a July task list, not current work.",
        )

    def test_no_skill_directory_holds_a_handoff_file(self):
        found = sorted(str(p.relative_to(SKILLS)) for p in SKILLS.glob("*/HANDOFF*"))
        self.assertEqual(
            [],
            found,
            "handoffs are single-use; promote what matters and delete the file",
        )

    def test_no_skill_still_points_at_the_deleted_file(self):
        """A pointer that outlives its target sends a session looking for a file
        that is not there, which costs more than the file did."""
        pointing = []
        for path in sorted(SKILLS.glob("*/*.md")):
            if DELETED.name in path.read_text(encoding="utf-8"):
                pointing.append(str(path.relative_to(SKILLS)))
        self.assertEqual([], pointing, f"still cite the deleted handoff: {pointing}")


if __name__ == "__main__":
    unittest.main()
