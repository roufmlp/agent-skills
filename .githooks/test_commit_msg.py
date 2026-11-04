"""Drills for the commit-msg hook: a throwaway repo, a fake home and a fake list.

Run from the repo root: `python3 .githooks/test_commit_msg.py`.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
HOOK = HERE / "commit-msg"


class ACommit(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.home = self.root / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".claude" / "private-names.txt").write_text("# comment\nacmeclub\nacme.example\n")
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "Pat Example", "GIT_COMMITTER_NAME": "Pat Example",
                    "GIT_AUTHOR_EMAIL": "p@example.com", "GIT_COMMITTER_EMAIL": "p@example.com"}
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Pat Example")
        self.git("config", "user.email", "p@example.com")
        self.git("config", "core.hooksPath", str(HERE))
        self.write("README.md", "# hello\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "first")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message, *paths):
        self.git("add", *paths)
        done = subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", message, "--", *paths],
                              env=self.env, capture_output=True, text=True)
        return done.returncode, done.stderr

    def test_a_clean_commit_passes(self):
        self.write("docs/a.md", "A plain line.\n")
        code, err = self.commit("plain", "docs/a.md")
        self.assertEqual(code, 0, err)

    def test_a_private_name_in_a_file_is_refused_anywhere(self):
        self.write("docs/a.md", "Built for AcmeClub.\n")
        code, err = self.commit("plain", "docs/a.md")
        self.assertEqual(code, 1)
        self.assertIn("docs/a.md:1: carries the private text `acmeclub`", err)

    def test_the_home_path_is_refused_anywhere(self):
        self.write("docs/a.md", f"See {self.home}/notes.md\n")
        code, err = self.commit("plain", "docs/a.md")
        self.assertEqual(code, 1)
        self.assertIn("carries the private text", err)

    def test_a_private_name_in_the_message_is_refused(self):
        self.write("docs/a.md", "fine\n")
        code, err = self.commit("for acme.example", "docs/a.md")
        self.assertEqual(code, 1)
        self.assertIn("the commit message", err)

    def test_the_owner_name_is_refused_in_a_skill_file_only(self):
        self.write("docs/a.md", "Pat approves it.\n")
        code, err = self.commit("docs", "docs/a.md")
        self.assertEqual(code, 0, err)
        self.write("skills/x/SKILL.md", "Pat approves it.\n")
        code, err = self.commit("skill", "skills/x/SKILL.md")
        self.assertEqual(code, 1)
        self.assertIn("names a person, `Pat`", err)

    def test_a_private_name_in_a_file_name_is_refused(self):
        self.write("docs/acmeclub-notes.md", "fine\n")
        code, err = self.commit("docs", "docs/acmeclub-notes.md")
        self.assertEqual(code, 1)
        self.assertIn("file name docs/acmeclub-notes.md", err)

    def test_tree_mode_walks_every_tracked_file(self):
        self.write("docs/a.md", "fine\n")
        self.commit("docs", "docs/a.md")
        # Slip a name past the hook, then catch it in the tree walk.
        self.write("docs/b.md", "AcmeClub again\n")
        self.git("add", "docs/b.md")
        subprocess.run(["git", "-C", str(self.repo), "-c", "core.hooksPath=/nonexistent", "commit", "-qm", "slip",
                        "--", "docs/b.md"], env=self.env, check=True, capture_output=True)
        done = subprocess.run(["python3", str(HOOK), "--tree"], cwd=self.repo, env=self.env,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("docs/b.md:1", done.stderr)

    def test_without_a_list_the_hook_still_checks_the_path_and_says_so(self):
        (self.home / ".claude" / "private-names.txt").unlink()
        self.write("docs/a.md", f"{self.home}\n")
        code, err = self.commit("docs", "docs/a.md")
        self.assertEqual(code, 1)
        self.assertIn("No private names list", err)


if __name__ == "__main__":
    unittest.main()
