#!/usr/bin/env python3
"""Checks for check_build_agents.py: a fixture set of seven files that passes, and one edit per refusal.

    python3 test_check_build_agents.py
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_build_agents as mod  # noqa: E402

BODIES = {
    "implementer": "Invoke /tdd. Do not wait for a seam. A test starts with `keeps:`.",
    "verifier": "The hostile walk: a reload, a second road, two fast clicks, the 390-pixel width, the empty state and the error state. on_main.py decides a difference at the base.",
    "reviewer": "Invoke the code-review skill. Each keeps: test protects unchanged behaviour.",
    "note-checker": "Write `Corrected:`, `Sound:` or `Stopped:`; a stopped note goes under Decide.",
    "merger": "Renumber first. The header begins `| Note | State |`. On a refusal `git merge --abort`. A note merges with --no-ff. The merge into main is fast-forward only.",
    "final-verifier": (
        "The pre-launch gate; the baseline retake; on_main.py decides what holds on main.\n"
        "   1. RLS on every table.\n   2. grep for service_role.\n   3. user A and B.\n   4. webhooks.\n"
        "   5. npm audit.\n   6. error pages.\n   7. the last call answers 429.\n"
    ),
    "final-reviewer": "Invoke the code-review skill. Money. Access. Secrets.",
}


def write(directory, role, fields=None, body=None):
    f = {
        "name": f"build-feature-{role}",
        "description": "A role.",
        "model": "sonnet",
        "effort": "high",
        "autoCompactWindow": "400000",
        "tools": "Read, Bash",
    }
    f.update(fields or {})
    head = "\n".join(f"{k}: {v}" for k, v in f.items() if v is not None)
    with open(os.path.join(directory, f"build-feature-{role}.md"), "w") as out:
        out.write(f"---\n{head}\n---\n\n{body if body is not None else BODIES[role]}\n")


class Lint(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        for role in mod.ROLES:
            write(self.dir, role)

    def refusals(self):
        return mod.check_dir(self.dir)

    def test_fixture_passes(self):
        self.assertEqual(self.refusals(), [])
        self.assertEqual(mod.main(["--dir", self.dir]), 0)

    def test_missing_file(self):
        os.remove(os.path.join(self.dir, "build-feature-merger.md"))
        self.assertEqual(self.refusals(), ["build-feature-merger.md: missing"])
        self.assertEqual(mod.main(["--dir", self.dir]), 1)

    def test_no_frontmatter(self):
        with open(os.path.join(self.dir, "build-feature-merger.md"), "w") as f:
            f.write("just prose\n")
        self.assertEqual(self.refusals(), ["build-feature-merger.md: no frontmatter"])

    def test_name_must_match_stem(self):
        write(self.dir, "verifier", {"name": "verifier"})
        self.assertIn("build-feature-verifier.md: name must be `build-feature-verifier`, is `verifier`", self.refusals())

    def test_model_spelling(self):
        write(self.dir, "reviewer", {"model": "opus-4"})
        self.assertTrue(any("model `opus-4`" in r for r in self.refusals()))
        write(self.dir, "reviewer", {"model": "claude-opus-5-5"})
        self.assertEqual(self.refusals(), [])

    def test_effort_spelling(self):
        write(self.dir, "reviewer", {"effort": "very high"})
        self.assertTrue(any("effort `very high`" in r for r in self.refusals()))

    def test_window(self):
        write(self.dir, "merger", {"autoCompactWindow": "300000"})
        self.assertIn("build-feature-merger.md: autoCompactWindow must be 400000, is `300000`", self.refusals())
        write(self.dir, "merger", {"autoCompactWindow": None})
        self.assertIn("build-feature-merger.md: autoCompactWindow must be 400000, is `None`", self.refusals())

    def test_tools(self):
        write(self.dir, "merger", {"tools": None})
        self.assertIn("build-feature-merger.md: no tools list", self.refusals())
        write(self.dir, "merger", {"tools": "Read, Bash, Grep, Glob, Edit, Write, Skill, Agent, WebFetch"})
        self.assertTrue(any("tools list has 9 names" in r for r in self.refusals()))
        write(self.dir, "merger", {"tools": "Read, Hammer"})
        self.assertIn("build-feature-merger.md: tool `Hammer` is not a known tool name", self.refusals())
        write(self.dir, "merger", {"tools": "[Read, Bash]"})
        self.assertEqual(self.refusals(), [])

    def test_bypass_mode_refused(self):
        write(self.dir, "merger", {"permissionMode": "bypassPermissions"})
        self.assertTrue(any("bypassPermissions" in r for r in self.refusals()))

    def test_omit_claude_md_is_boolean(self):
        write(self.dir, "merger", {"omitClaudeMd": "yes"})
        self.assertTrue(any("omitClaudeMd must be true or false" in r for r in self.refusals()))
        write(self.dir, "merger", {"omitClaudeMd": "true"})
        self.assertEqual(self.refusals(), [])

    def test_each_role_phrase(self):
        for role, phrases in mod.PHRASES.items():
            for phrase in phrases:
                body = BODIES[role].lower().replace(phrase, "")
                write(self.dir, role, body=body)
                self.assertIn(f"build-feature-{role}.md: body lacks `{phrase}`", self.refusals(), (role, phrase))
                write(self.dir, role)

    def test_a_prose_final_message_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for role in mod.ROLES:
                write(d, role)
            write(d, "verifier", body=BODIES["verifier"] + "\nFinal message, 10 lines at most: the verdict word.")
            lines = mod.check_dir(d)
            self.assertEqual(len(lines), 1, lines)
            self.assertIn("final message", lines[0])

    def test_gate_steps_counted(self):
        body = BODIES["final-verifier"].replace("   7. the last call answers 429.\n", "   the last call answers 429.\n")
        write(self.dir, "final-verifier", body=body)
        self.assertIn("build-feature-final-verifier.md: body lacks gate step 7", self.refusals())

    def test_real_files(self):
        """The seven files on this machine pass, where they exist."""
        real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents")
        if not all(os.path.isfile(os.path.join(real, f"build-feature-{r}.md")) for r in mod.ROLES):
            self.skipTest("the real agent files are not all present")
        self.assertEqual(mod.check_dir(real), [])


if __name__ == "__main__":
    unittest.main()
