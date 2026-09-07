#!/usr/bin/env python3
"""Tests for git-shared-state-guard.

The guard for "one git index serves every session in the main checkout".
Ruling 12 of its own grilling made the build one sitting rather
than a set of issues, on the grounds that the guard's whole behaviour is a test
file. This is that file.

Every case runs the hook as a subprocess against a REAL git fixture — a main
checkout and a linked worktree on disk — because the one thing the guard must
get right is which of the two it is standing in, and that is a question only git
answers. A mocked `rev-parse` would test the rules and skip the fault.

Run: python3 test_git_shared_state_guard.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
GUARD = HOOKS / "git-shared-state-guard.py"

_TMP = tempfile.TemporaryDirectory()
ROOT = os.path.realpath(_TMP.name)
MAIN = os.path.join(ROOT, "checkout")
TREE = os.path.join(MAIN, ".claude", "worktrees", "side")


def git(*args, cwd=MAIN):
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True)


os.makedirs(MAIN)
git("init", "-q", "-b", "main")
Path(MAIN, "a.txt").write_text("a\n")
Path(MAIN, "paths.txt").write_text("a.txt\n")
os.makedirs(os.path.join(MAIN, "sub"))
Path(MAIN, "sub", "b.txt").write_text("b\n")
git("add", "a.txt", "paths.txt", "sub/b.txt")
git("commit", "-q", "-m", "first")
git("worktree", "add", "-q", "-b", "side", TREE)


def run_hook(command, cwd=MAIN, tool="Bash"):
    payload = {"tool_name": tool, "cwd": cwd, "tool_input": {"command": command}}
    done = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload), capture_output=True, text=True)
    return done.returncode, done.stderr


class TestRuling5WideStagingInTheMainCheckout(unittest.TestCase):
    """Six forms count as wide. Only `git add <file path>` passes."""

    def test_add_all_is_refused(self):
        code, _ = run_hook("git add -A")
        self.assertEqual(code, 2)

    def test_add_dot_is_refused(self):
        code, _ = run_hook("git add .")
        self.assertEqual(code, 2)

    def test_add_update_is_refused(self):
        code, _ = run_hook("git add -u")
        self.assertEqual(code, 2)

    def test_commit_all_is_refused(self):
        code, _ = run_hook("git commit -a -m 'x'")
        self.assertEqual(code, 2)

    def test_a_bundled_short_flag_hides_nothing(self):
        """`git commit -am msg` is `-a` wearing two letters."""
        code, _ = run_hook("git commit -am 'x'")
        self.assertEqual(code, 2)

    def test_add_of_a_directory_is_refused(self):
        """The class instance one committed: `.scratch/example-feature/`
        holds the register and every run."""
        code, _ = run_hook("git add sub")
        self.assertEqual(code, 2)

    def test_add_of_a_glob_is_refused(self):
        code, _ = run_hook("git add '*.txt'")
        self.assertEqual(code, 2)

    def test_add_of_a_named_file_passes(self):
        code, _ = run_hook("git add a.txt")
        self.assertEqual(code, 0)

    def test_add_of_two_named_files_passes(self):
        code, _ = run_hook("git add a.txt sub/b.txt")
        self.assertEqual(code, 0)

    def test_a_redirect_does_not_hide_a_wide_add(self):
        code, _ = run_hook("git add -A > /dev/null")
        self.assertEqual(code, 2)


class TestRuling7EveryCommitNamesItsPaths(unittest.TestCase):
    """The residual shape instance two suffered: both sessions staged explicit
    paths and one committed first, taking the other's files with it."""

    def test_a_bare_commit_is_refused(self):
        code, _ = run_hook("git commit -m 'a message naming one change'")
        self.assertEqual(code, 2)

    def test_a_commit_naming_its_paths_passes(self):
        code, _ = run_hook("git commit -m 'x' -- a.txt")
        self.assertEqual(code, 0)

    def test_a_commit_naming_a_dot_pathspec_is_refused(self):
        code, _ = run_hook("git commit -m 'x' -- .")
        self.assertEqual(code, 2)

    def test_a_commit_naming_a_directory_is_refused(self):
        code, _ = run_hook("git commit -m 'x' -- sub")
        self.assertEqual(code, 2)

    def test_a_double_dash_with_nothing_after_it_is_refused(self):
        code, _ = run_hook("git commit -m 'x' --")
        self.assertEqual(code, 2)


class TestRuling10AWideButHonestCommit(unittest.TestCase):
    """No exception list. One rule holds for every commit: the commit names
    what it carries. Six commits a week keep this road."""

    def test_a_pathspec_file_passes(self):
        code, _ = run_hook("git commit -m 'run records' --pathspec-from-file=paths.txt")
        self.assertEqual(code, 0)

    def test_a_pathspec_file_read_from_stdin_passes(self):
        code, _ = run_hook("git commit -m 'x' --pathspec-from-file=-")
        self.assertEqual(code, 0)


class TestRuling9AmendAndSoftReset(unittest.TestCase):
    def test_amend_is_refused(self):
        code, _ = run_hook("git commit --amend --no-edit")
        self.assertEqual(code, 2)

    def test_a_soft_reset_passes_because_it_is_instance_one_s_remedy(self):
        code, _ = run_hook("git reset --soft HEAD~1")
        self.assertEqual(code, 0)

    def test_the_amend_refusal_sends_the_session_to_read_head_first(self):
        """The guard never detects whose commit HEAD is (ruling 6). The message
        does, so the refusal puts `git log -1` in front of the reset."""
        _, err = run_hook("git commit --amend")
        self.assertIn("git log -1", err)
        self.assertIn("git reset --soft", err)


class TestRuling8TheDestructiveCommands(unittest.TestCase):
    """Refused in their wide form only. An explicit path passes, because that
    is how a session undoes its own edit."""

    def test_a_hard_reset_is_refused(self):
        code, _ = run_hook("git reset --hard HEAD~1")
        self.assertEqual(code, 2)

    def test_checkout_of_a_dot_is_refused(self):
        code, _ = run_hook("git checkout -- .")
        self.assertEqual(code, 2)

    def test_restore_of_a_dot_is_refused(self):
        code, _ = run_hook("git restore .")
        self.assertEqual(code, 2)

    def test_clean_with_no_path_is_refused(self):
        code, _ = run_hook("git clean -fd")
        self.assertEqual(code, 2)

    def test_restore_of_a_named_file_passes(self):
        code, _ = run_hook("git restore a.txt")
        self.assertEqual(code, 0)

    def test_checkout_of_a_named_file_passes(self):
        code, _ = run_hook("git checkout -- a.txt")
        self.assertEqual(code, 0)

    def test_clean_of_a_named_path_passes(self):
        code, _ = run_hook("git clean -fd sub")
        self.assertEqual(code, 0)

    def test_a_dry_run_clean_passes_because_it_deletes_nothing(self):
        code, _ = run_hook("git clean -nd")
        self.assertEqual(code, 0)


class TestRuling14ABranchSwitch(unittest.TestCase):
    """It changes the working tree under every other session in the directory,
    which is a larger loss than anything else on the list."""

    def test_checkout_of_a_branch_is_refused(self):
        code, _ = run_hook("git checkout side")
        self.assertEqual(code, 2)

    def test_switch_is_refused(self):
        code, _ = run_hook("git switch side")
        self.assertEqual(code, 2)

    def test_creating_a_branch_is_refused(self):
        code, _ = run_hook("git checkout -b feature")
        self.assertEqual(code, 2)

    def test_the_refusal_names_a_worktree_as_the_road(self):
        _, err = run_hook("git switch side")
        self.assertIn("git worktree add", err)


class TestRuling13TheStashRuleInEveryCheckout(unittest.TestCase):
    """The stack is shared by every worktree of the repository, so this rule
    ignores which checkout the command runs in. It was text in CLAUDE.md and
    depended on memory; here it refuses."""

    def test_a_bare_stash_is_refused_in_the_main_checkout(self):
        code, _ = run_hook("git stash")
        self.assertEqual(code, 2)

    def test_a_bare_stash_is_refused_in_a_worktree_too(self):
        code, _ = run_hook("git stash", cwd=TREE)
        self.assertEqual(code, 2)

    def test_a_bare_stash_with_a_flag_is_still_bare(self):
        code, _ = run_hook("git stash -u", cwd=TREE)
        self.assertEqual(code, 2)

    def test_stash_pop_is_refused_in_the_main_checkout(self):
        code, _ = run_hook("git stash pop")
        self.assertEqual(code, 2)

    def test_stash_pop_is_refused_in_a_worktree_too(self):
        code, _ = run_hook("git stash pop", cwd=TREE)
        self.assertEqual(code, 2)

    def test_the_tagged_push_passes(self):
        code, _ = run_hook("git stash push -u -m 'ticket-41-wip'", cwd=TREE)
        self.assertEqual(code, 0)

    def test_listing_and_applying_pass(self):
        for command in ("git stash list --format='%H %gs'",
                        "git stash apply 3d5fe7bf",
                        "git stash drop 'stash@{0}'"):
            with self.subTest(command=command):
                code, _ = run_hook(command, cwd=TREE)
                self.assertEqual(code, 0)

    def test_the_refusal_names_the_tagged_form(self):
        _, err = run_hook("git stash")
        self.assertIn("git stash push -u -m", err)
        self.assertIn("git stash apply", err)

    def test_the_stash_refusal_does_not_claim_a_worktree_shares_an_index(self):
        """A worktree's index IS its own. Only the stack is shared, and the
        refusal a reader trusts most is the one they read first."""
        _, err = run_hook("git stash", cwd=TREE)
        self.assertIn("stash stack", err)
        self.assertNotIn("shares one git index", err)


class TestTheScopeIsTheSharedCheckoutOnly(unittest.TestCase):
    """A linked worktree has a private index, so nothing there is touched."""

    def test_a_wide_add_in_a_worktree_passes(self):
        code, _ = run_hook("git add -A", cwd=TREE)
        self.assertEqual(code, 0)

    def test_a_bare_commit_in_a_worktree_passes(self):
        code, _ = run_hook("git commit -m 'ordinary work'", cwd=TREE)
        self.assertEqual(code, 0)

    def test_a_hard_reset_in_a_worktree_passes(self):
        code, _ = run_hook("git reset --hard HEAD~1", cwd=TREE)
        self.assertEqual(code, 0)

    def test_a_branch_switch_in_a_worktree_passes(self):
        code, _ = run_hook("git switch main", cwd=TREE)
        self.assertEqual(code, 0)

    def test_an_amend_in_a_worktree_passes(self):
        code, _ = run_hook("git commit --amend --no-edit", cwd=TREE)
        self.assertEqual(code, 0)

    def test_a_directory_that_is_not_a_repository_passes(self):
        code, _ = run_hook("git add -A", cwd=ROOT)
        self.assertEqual(code, 0)


class TestItCannotBeReachedAround(unittest.TestCase):
    """A command run FROM a worktree can otherwise reach the main checkout
    around a working-directory test. All three roads are followed."""

    def test_a_cd_into_the_main_checkout_is_followed(self):
        """Instance one, byte for byte: the `cd` was meant to reach a file."""
        code, _ = run_hook(f"cd {MAIN} && git add -A && git commit -m 'a message naming one change'",
                           cwd=TREE)
        self.assertEqual(code, 2)

    def test_dash_c_into_the_main_checkout_is_followed(self):
        code, _ = run_hook(f"git -C {MAIN} add -A", cwd=TREE)
        self.assertEqual(code, 2)

    def test_git_dir_into_the_main_checkout_is_followed(self):
        code, _ = run_hook(f"git --git-dir={MAIN}/.git add -A", cwd=TREE)
        self.assertEqual(code, 2)

    def test_a_relative_cd_is_resolved_against_the_session_directory(self):
        code, _ = run_hook("cd ../../.. && git add -A", cwd=TREE)
        self.assertEqual(code, 2)

    def test_a_cd_the_other_way_does_not_make_a_worktree_refuse(self):
        code, _ = run_hook(f"cd {TREE} && git add -A", cwd=MAIN)
        self.assertEqual(code, 0)

    def test_an_environment_prefix_does_not_hide_the_command(self):
        code, _ = run_hook("GIT_PAGER=cat git add -A")
        self.assertEqual(code, 2)

    def test_a_wide_add_later_in_the_line_is_still_found(self):
        code, _ = run_hook("git status --short && git add -A")
        self.assertEqual(code, 2)


class TestRuling4TheRefusalNamesTheRoad(unittest.TestCase):
    """Four conventions in this repository failed because they asked a session
    to remember. Every refusal carries the command that works."""

    def test_the_add_refusal_names_staging_by_file(self):
        _, err = run_hook("git add -A")
        self.assertIn("git add <file>", err)

    def test_the_commit_refusal_names_the_pathspec_form(self):
        _, err = run_hook("git commit -m 'x'")
        self.assertIn("-- <file>", err)

    def test_the_commit_refusal_names_the_pathspec_file_for_a_wide_commit(self):
        _, err = run_hook("git commit -m 'x'")
        self.assertIn("--pathspec-from-file", err)

    def test_the_destructive_refusal_names_the_single_file_road(self):
        _, err = run_hook("git restore .")
        self.assertIn("git restore <file>", err)

    def test_every_refusal_names_the_directory_it_refused_in(self):
        _, err = run_hook("git add -A")
        self.assertIn(MAIN, err)

    def test_every_refusal_says_why_naming_paths_is_not_enough(self):
        """H2 keeps a tracker id out of the message, so the evidence has to
        travel as the fact itself: the second instance staged its two paths by
        name and lost them to another session's wide add regardless."""
        _, err = run_hook("git add -A")
        self.assertIn("does not protect it", err)


class TestItRefusesNothingElse(unittest.TestCase):
    def test_reading_commands_pass(self):
        for command in ("git status --short", "git log -1 --format=%s",
                        "git diff --stat", "git worktree list",
                        "git rev-parse --git-dir", "git show HEAD"):
            with self.subTest(command=command):
                code, _ = run_hook(command)
                self.assertEqual(code, 0)

    def test_a_quoted_git_command_inside_another_command_passes(self):
        """`echo "git add -A"` is data, not a git call."""
        code, _ = run_hook('echo "git add -A"')
        self.assertEqual(code, 0)

    def test_a_heredoc_body_naming_a_wide_add_passes(self):
        """A ticket file or a hook docstring quotes these commands to forbid
        them. Written through a heredoc, the body is data. The shell operator
        in it is what makes the case bite: unstripped, it starts a new simple
        command and the words after it read as a real git call."""
        code, _ = run_hook(
            "cat > notes.md <<'EOF'\nNever run this here: ; git add -A\nEOF")
        self.assertEqual(code, 0)

    def test_a_command_with_no_git_in_it_passes(self):
        code, _ = run_hook("npm ci && npx vitest run")
        self.assertEqual(code, 0)

    def test_a_non_bash_tool_is_not_this_hook_s_business(self):
        code, _ = run_hook("git add -A", tool="Write")
        self.assertEqual(code, 0)

    def test_a_malformed_payload_never_breaks_the_session(self):
        done = subprocess.run([sys.executable, str(GUARD)], input="not json",
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)

    def test_a_missing_directory_never_breaks_the_session(self):
        code, _ = run_hook("git add -A", cwd=os.path.join(ROOT, "gone"))
        self.assertEqual(code, 0)

    def test_a_push_is_not_refused_because_it_touches_no_shared_state(self):
        code, _ = run_hook("git push origin main")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
