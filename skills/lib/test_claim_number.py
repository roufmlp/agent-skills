#!/usr/bin/env python3
"""Ticket 38 of the pilot-delivery map, sitting 5: one claim script for issue and
migration numbers (rulings 7, 16 and 19).

Two minters used to pick "the next free number" by listing one directory in one
tree, so a live run's promotion and a hand-minted ticket in another session
could both write `512`, and two runs both wrote migration `0078`. The counter is
now a claim: a file created with an exclusive create in a store outside every
repository, so two claims can never answer the same number. The next number is
one past the highest anything holds, counting every worktree AND every claim
not yet written to disk.

Run: python3 test_claim_number.py
"""

import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "claim_number.py"


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(root: Path) -> Path:
    main = root / "project"
    main.mkdir()
    git("init", "-q", "-b", "main", cwd=main)
    git("config", "user.email", "t@example.test", cwd=main)
    git("config", "user.name", "t", cwd=main)
    (main / "README.md").write_text("x\n")
    git("add", ".", cwd=main)
    git("commit", "-q", "-m", "init", cwd=main)
    return main


def run(args, cwd, store, env_extra=None):
    env = dict(os.environ, CLAIM_STORE=str(store))
    if env_extra:
        env.update(env_extra)
    done = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                          capture_output=True, text=True, env=env)
    return done.returncode, done.stdout.strip(), done.stderr


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.main = make_repo(root)
        self.store = root / "state"
        self.issues = self.main / ".scratch" / "pilot" / "issues"
        self.issues.mkdir(parents=True)
        self.migrations = self.main / "supabase" / "migrations"
        self.migrations.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def claim(self, kind, directory, *extra, cwd=None):
        return run([kind, str(directory), *extra], cwd or self.main, self.store)


class TestTheNextNumberIsOnePastTheHighestAnythingHolds(Fixture):
    def test_the_first_claim_follows_the_files_on_disk(self):
        (self.issues / "01-a.md").write_text("Status: open\n")
        (self.issues / "02-b.md").write_text("Status: open\n")
        code, out, err = self.claim("issue", self.issues, "--for", "to-issues")
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "03")

    def test_the_second_claim_counts_the_first_even_though_no_file_exists_yet(self):
        (self.issues / "01-a.md").write_text("x\n")
        self.claim("issue", self.issues, "--for", "a")
        _, out, _ = self.claim("issue", self.issues, "--for", "b")
        self.assertEqual(out, "03")

    def test_a_number_that_exists_only_in_an_unmerged_worktree_is_counted(self):
        (self.issues / "02-b.md").write_text("x\n")
        tree = self.main / ".claude" / "worktrees" / "run-a"
        git("worktree", "add", "-q", "-b", "claude/run-a", str(tree), cwd=self.main)
        other = tree / ".scratch" / "pilot" / "issues"
        other.mkdir(parents=True)
        (other / "05-in-a-run.md").write_text("x\n")
        _, out, _ = self.claim("issue", self.issues, "--for", "hand")
        self.assertEqual(out, "06")

    def test_the_width_follows_the_widest_name_and_a_split_suffix_counts_as_its_parent(self):
        (self.issues / "573-x.md").write_text("x\n")
        (self.issues / "216b-split.md").write_text("x\n")
        _, out, _ = self.claim("issue", self.issues)
        self.assertEqual(out, "574")

    def test_a_migration_number_is_four_digits_wide(self):
        (self.migrations / "0121_alias.sql").write_text("select 1;\n")
        _, out, _ = self.claim("migration", self.migrations, "--for", "implementer 512")
        self.assertEqual(out, "0122")

    def test_an_empty_directory_starts_at_one(self):
        _, out, _ = self.claim("issue", self.issues)
        self.assertEqual(out, "01")
        _, out, _ = self.claim("migration", self.migrations)
        self.assertEqual(out, "0001")


class TestTwoClaimsNeverAnswerTheSameNumber(Fixture):
    def test_parallel_claims_are_all_distinct(self):
        (self.issues / "10-a.md").write_text("x\n")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: self.claim("issue", self.issues, "--for", f"p{i}"), range(8)))
        numbers = [out for code, out, _ in results if code == 0]
        self.assertEqual(len(numbers), 8, results)
        self.assertEqual(len(set(numbers)), 8, numbers)
        self.assertEqual(sorted(numbers), [str(n) for n in range(11, 19)])

    def test_a_claim_file_planted_by_hand_is_stepped_over(self):
        (self.issues / "01-a.md").write_text("x\n")
        first = self.claim("issue", self.issues)[1]
        self.assertEqual(first, "02")
        _, out, _ = self.claim("issue", self.issues)
        self.assertEqual(out, "03")


class TestTheClaimRecordsWhoAndWhere(Fixture):
    def test_the_claim_file_names_the_tree_the_claimant_and_the_time(self):
        _, out, _ = self.claim("issue", self.issues, "--for", "promotion batch-abc123", "--slug", "a-thing")
        store_files = list(self.store.rglob("01"))
        self.assertEqual(len(store_files), 1, list(self.store.rglob("*")))
        text = store_files[0].read_text()
        self.assertIn(f"tree={os.path.realpath(self.main)}", text)
        self.assertIn("who=promotion batch-abc123", text)
        self.assertIn("slug=a-thing", text)
        self.assertIn("at=", text)

    def test_the_store_is_keyed_by_the_main_checkout_path_and_the_directory(self):
        self.claim("issue", self.issues)
        self.claim("migration", self.migrations)
        from urllib.parse import quote
        repo = quote(os.path.realpath(self.main), safe="")
        rel = sorted(str(p.relative_to(self.store)) for p in self.store.rglob("*") if p.is_file())
        self.assertEqual(rel, [
            f"{repo}/issue/.scratch%2Fpilot%2Fissues/01",
            f"{repo}/migration/supabase%2Fmigrations/0001",
        ])

    def test_a_second_clone_with_the_same_name_gets_its_own_store(self):
        (self.issues / "05-a.md").write_text("x\n")
        other_root = Path(self.tmp.name) / "elsewhere"
        other_root.mkdir()
        other = make_repo(other_root)
        other_issues = other / ".scratch" / "pilot" / "issues"
        other_issues.mkdir(parents=True)
        self.assertEqual(self.claim("issue", self.issues)[1], "06")
        self.assertEqual(run(["issue", str(other_issues)], other, self.store)[1], "01")

    def test_a_worktree_shares_its_clone_s_store(self):
        tree = self.main / ".claude" / "worktrees" / "run-a"
        git("worktree", "add", "-q", "-b", "claude/run-a", str(tree), cwd=self.main)
        other = tree / ".scratch" / "pilot" / "issues"
        other.mkdir(parents=True)
        self.assertEqual(self.claim("issue", self.issues)[1], "01")
        self.assertEqual(run(["issue", str(other)], tree, self.store)[1], "02")

    def test_a_newline_in_who_or_slug_cannot_forge_a_record_line(self):
        self.claim("issue", self.issues, "--for", "x\ntree=/spoofed", "--slug", "a\nb")
        text = next(self.store.rglob("01")).read_text()
        self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("tree=")), 1)
        self.assertIn("who=x tree=/spoofed", text)
        code, _, _ = run(["--check", str(self.issues / "01-new.md")], self.main, self.store)
        self.assertEqual(code, 0)

    def test_a_directory_outside_any_repository_is_refused(self):
        loose = Path(self.tmp.name) / "loose"
        loose.mkdir()
        code, out, err = run(["issue", str(loose)], loose, self.store)
        self.assertEqual(code, 2)
        self.assertIn("not inside a git repository", err)

    def test_list_prints_every_claim_for_a_directory(self):
        self.claim("issue", self.issues, "--for", "a")
        self.claim("issue", self.issues, "--for", "b")
        code, out, _ = run(["--list", str(self.issues)], self.main, self.store)
        self.assertEqual(code, 0)
        self.assertIn("01", out)
        self.assertIn("02", out)
        self.assertIn("who=b", out)


class TestCheckDecidesWhetherAPathMayBeWritten(Fixture):
    """`--check` is what the hook calls. Exit 0 lets the write through; exit 1
    refuses it with the reason and the claim command on stderr."""

    def check(self, path, cwd=None):
        return run(["--check", str(path)], cwd or self.main, self.store)

    def test_an_unclaimed_new_issue_file_is_refused_and_told_how_to_claim(self):
        code, _, err = self.check(self.issues / "07-new.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertIn("claim_number.py issue", err)
        self.assertIn(str(self.issues), err)

    def test_an_unclaimed_new_migration_is_refused_the_same_way(self):
        code, _, err = self.check(self.migrations / "0122_x.sql")
        self.assertEqual(code, 1)
        self.assertIn("claim_number.py migration", err)

    def test_a_number_claimed_in_this_tree_passes(self):
        number = self.claim("issue", self.issues, "--for", "a")[1]
        code, _, err = self.check(self.issues / f"{number}-new.md")
        self.assertEqual(code, 0, err)

    def test_a_number_claimed_in_another_tree_is_refused_and_the_tree_is_named(self):
        tree = self.main / ".claude" / "worktrees" / "run-a"
        git("worktree", "add", "-q", "-b", "claude/run-a", str(tree), cwd=self.main)
        other = tree / ".scratch" / "pilot" / "issues"
        other.mkdir(parents=True)
        number = run(["issue", str(other), "--for", "promotion"], tree, self.store)[1]
        code, _, err = self.check(self.issues / f"{number}-mine.md")
        self.assertEqual(code, 1)
        self.assertIn(os.path.realpath(tree), err)
        self.assertIn("promotion", err)

    def test_a_file_that_already_exists_is_an_edit_and_passes(self):
        (self.issues / "03-old.md").write_text("x\n")
        code, _, _ = self.check(self.issues / "03-old.md")
        self.assertEqual(code, 0)

    def test_a_split_with_a_letter_suffix_needs_no_claim(self):
        (self.issues / "216-parent.md").write_text("x\n")
        code, _, _ = self.check(self.issues / "216b-half.md")
        self.assertEqual(code, 0)

    def test_a_split_whose_parent_exists_nowhere_is_refused(self):
        code, _, err = self.check(self.issues / "999b-orphan.md")
        self.assertEqual(code, 1)
        self.assertIn("999", err)

    def test_a_split_whose_parent_lives_in_another_worktree_passes(self):
        tree = self.main / ".claude" / "worktrees" / "run-a"
        git("worktree", "add", "-q", "-b", "claude/run-a", str(tree), cwd=self.main)
        other = tree / ".scratch" / "pilot" / "issues"
        other.mkdir(parents=True)
        (other / "300-parent.md").write_text("x\n")
        code, _, _ = self.check(self.issues / "300b-half.md")
        self.assertEqual(code, 0)

    def test_paths_that_are_not_numbered_issue_or_migration_files_pass(self):
        for path in (self.main / "README.md", self.issues / "notes.md",
                     self.main / ".scratch" / "pilot" / "PRD.md",
                     self.main / "supabase" / "seed.sql", self.issues / "sub" / "01-x.md"):
            with self.subTest(path=str(path)):
                code, _, _ = self.check(path)
                self.assertEqual(code, 0)

    def test_a_path_outside_any_repository_passes_because_the_hook_fails_open(self):
        loose = Path(self.tmp.name) / "loose" / "issues"
        loose.mkdir(parents=True)
        code, _, _ = run(["--check", str(loose / "01-x.md")], self.tmp.name, self.store)
        self.assertEqual(code, 0)

    def test_the_number_written_must_be_spelled_as_the_claim_printed_it(self):
        number = self.claim("issue", self.issues)[1]
        self.assertEqual(number, "01")
        code, _, err = self.check(self.issues / "1-x.md")
        self.assertEqual(code, 1)
        self.assertIn("01-<slug>", err)

    def test_every_refusal_leads_with_what_to_do(self):
        for path in (self.issues / "07-new.md", self.issues / "999b-orphan.md", self.issues / "1-x.md"):
            with self.subTest(path=path.name):
                if path.name == "1-x.md":
                    self.claim("issue", self.issues)
                _, _, err = self.check(path)
                first = err.strip().splitlines()[0]
                self.assertTrue(first.startswith("REFUSED. "), first)
                self.assertRegex(first, r"REFUSED\. (Claim|Write|Name) ")


class TestTheRenameRoad(Fixture):
    """The human's ruling `q-h0920-37` of 2026-09-20: a tracker file whose title has gone
    false is RENAMED — keep the number, rewrite the title, rename the file with it.

    Hardening pass `h0922b` was refused that rename on 2026-09-22. Issue 105 of one
    tracker was claimed by `promotion batch-d41839` in the worktree
    `run-issues-batch-d41839`; the file had since merged into another tree, and
    `--check` reads a claim held by another tree as the collision it exists to stop.
    The claim could not say "this number moved house", so `--rename` says it.

    The sharp edge these cases hold: a cross-tree RENAME passes and a cross-tree MINT
    is still refused, and the thing that tells them apart is the old file on disk.
    """

    def rename(self, old, new, cwd=None):
        return run(["--rename", str(old), str(new)], cwd or self.main, self.store)

    def check(self, path, cwd=None):
        return run(["--check", str(path)], cwd or self.main, self.store)

    def worktree(self, name="run-a"):
        tree = self.main / ".claude" / "worktrees" / name
        git("worktree", "add", "-q", "-b", f"claude/{name}", str(tree), cwd=self.main)
        other = tree / ".scratch" / "pilot" / "issues"
        other.mkdir(parents=True)
        return tree, other

    def store_record(self, number):
        files = list(self.store.rglob(number))
        self.assertEqual(len(files), 1, [str(p) for p in self.store.rglob("*")])
        return dict(line.split("=", 1) for line in files[0].read_text().splitlines() if "=" in line)

    def test_a_rename_in_the_claiming_tree_passes_and_the_check_passes_the_new_name(self):
        number = self.claim("issue", self.issues, "--for", "to-issues", "--slug", "old-title")[1]
        (self.issues / f"{number}-old-title.md").write_text("x\n")
        code, _, err = self.rename(self.issues / f"{number}-old-title.md",
                                   self.issues / f"{number}-new-title.md")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.check(self.issues / f"{number}-new-title.md")[0], 0)

    def test_the_number_never_changes_and_a_new_number_is_refused_as_a_mint(self):
        self.claim("issue", self.issues, "--for", "a", "--slug", "old")
        (self.issues / "01-old.md").write_text("x\n")
        code, _, err = self.rename(self.issues / "01-old.md", self.issues / "02-old.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertIn("number", err)
        self.assertEqual(self.check(self.issues / "02-old.md")[0], 1)

    def test_a_rename_out_of_the_directory_or_across_kinds_is_refused(self):
        self.claim("issue", self.issues, "--for", "a")
        (self.issues / "01-old.md").write_text("x\n")
        elsewhere = self.main / "docs" / "issues"
        elsewhere.mkdir(parents=True)
        for target in (elsewhere / "01-old.md", self.migrations / "0001_old.sql"):
            with self.subTest(target=str(target)):
                code, _, err = self.rename(self.issues / "01-old.md", target)
                self.assertEqual(code, 1)
                self.assertIn("REFUSED", err)

    def test_a_rename_with_no_source_file_is_a_mint_wearing_a_disguise(self):
        number = self.claim("issue", self.issues, "--for", "a", "--slug", "old")[1]
        code, _, err = self.rename(self.issues / f"{number}-old.md",
                                   self.issues / f"{number}-new.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertIn(f"{number}-old.md", err)

    def test_a_new_name_something_already_holds_is_refused(self):
        number = self.claim("issue", self.issues, "--for", "a", "--slug", "old")[1]
        (self.issues / f"{number}-old.md").write_text("x\n")
        (self.issues / f"{number}-new.md").write_text("y\n")
        code, _, err = self.rename(self.issues / f"{number}-old.md",
                                   self.issues / f"{number}-new.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertEqual((self.issues / f"{number}-new.md").read_text(), "y\n")

    def test_renaming_a_file_to_its_own_name_is_refused(self):
        self.claim("issue", self.issues, "--for", "a", "--slug", "old")
        (self.issues / "01-old.md").write_text("x\n")
        code, _, err = self.rename(self.issues / "01-old.md", self.issues / "01-old.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)

    def test_a_path_that_is_not_a_numbered_file_is_refused(self):
        (self.issues / "notes.md").write_text("x\n")
        code, _, err = self.rename(self.issues / "notes.md", self.issues / "01-new.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)

    def test_the_claim_record_is_updated_and_the_original_claimant_survives(self):
        number = self.claim("issue", self.issues, "--for", "promotion batch-d41839",
                            "--slug", "clash-shown-on-no-delivery-date-road")[1]
        claimed_at = self.store_record(number)["at"]
        (self.issues / f"{number}-clash-shown-on-no-delivery-date-road.md").write_text("x\n")
        code, _, err = self.rename(
            self.issues / f"{number}-clash-shown-on-no-delivery-date-road.md",
            self.issues / f"{number}-line-page-shows-no-clash-on-a-cold-read.md")
        self.assertEqual(code, 0, err)
        record = self.store_record(number)  # exactly ONE store file: updated, not duplicated
        self.assertEqual(record["slug"], "line-page-shows-no-clash-on-a-cold-read")
        self.assertEqual(record["who"], "promotion batch-d41839")
        self.assertEqual(record["at"], claimed_at)
        self.assertEqual(record["renamed_from"],
                         f"{number}-clash-shown-on-no-delivery-date-road.md")
        self.assertIn("renamed_at", record)

    def test_a_cross_tree_rename_is_allowed_and_names_both_trees(self):
        tree, other = self.worktree()
        number = run(["issue", str(other), "--for", "promotion batch-d41839", "--slug", "old"],
                     tree, self.store)[1]
        self.assertEqual(self.check(self.issues / f"{number}-old.md")[0], 1)  # a mint, today
        (self.issues / f"{number}-old.md").write_text("x\n")  # the file merged into this tree
        code, _, err = self.rename(self.issues / f"{number}-old.md",
                                   self.issues / f"{number}-new.md")
        self.assertEqual(code, 0, err)
        record = self.store_record(number)
        self.assertEqual(record["tree"], os.path.realpath(self.main))
        self.assertEqual(record["claimed_tree"], os.path.realpath(tree))
        self.assertEqual(record["who"], "promotion batch-d41839")
        self.assertEqual(self.check(self.issues / f"{number}-new.md")[0], 0)

    def test_a_cross_tree_mint_is_still_refused_after_a_rename_has_moved_another_number(self):
        tree, other = self.worktree()
        renamed = run(["issue", str(other), "--for", "promotion", "--slug", "old"], tree, self.store)[1]
        minted = run(["issue", str(other), "--for", "promotion", "--slug", "fresh"], tree, self.store)[1]
        (self.issues / f"{renamed}-old.md").write_text("x\n")
        self.assertEqual(self.rename(self.issues / f"{renamed}-old.md",
                                     self.issues / f"{renamed}-new.md")[0], 0)
        code, _, err = self.check(self.issues / f"{minted}-mine.md")
        self.assertEqual(code, 1)
        self.assertIn(os.path.realpath(tree), err)
        self.assertIn("Writing it here would be the collision", err)

    def test_a_rename_cannot_borrow_another_trees_number_without_the_file(self):
        tree, other = self.worktree()
        number = run(["issue", str(other), "--for", "promotion", "--slug", "old"], tree, self.store)[1]
        (other / f"{number}-old.md").write_text("x\n")  # the file is in the OTHER tree only
        code, _, err = self.rename(self.issues / f"{number}-old.md",
                                   self.issues / f"{number}-new.md")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", err)
        self.assertEqual(self.store_record(number)["tree"], os.path.realpath(tree))
        self.assertEqual(self.check(self.issues / f"{number}-new.md")[0], 1)

    def test_a_second_rename_keeps_the_first_claimants_history(self):
        tree, other = self.worktree()
        number = run(["issue", str(other), "--for", "promotion", "--slug", "one"], tree, self.store)[1]
        (self.issues / f"{number}-one.md").write_text("x\n")
        self.rename(self.issues / f"{number}-one.md", self.issues / f"{number}-two.md")
        os.rename(self.issues / f"{number}-one.md", self.issues / f"{number}-two.md")
        self.rename(self.issues / f"{number}-two.md", self.issues / f"{number}-three.md")
        record = self.store_record(number)
        self.assertEqual(record["slug"], "three")
        self.assertEqual(record["who"], "promotion")
        self.assertEqual(record["claimed_tree"], os.path.realpath(tree))
        self.assertEqual(record["renamed_from"], f"{number}-two.md")

    def test_a_number_older_than_the_store_gains_a_record_because_its_file_exists(self):
        (self.issues / "41-old.md").write_text("x\n")
        code, _, err = self.rename(self.issues / "41-old.md", self.issues / "41-new.md")
        self.assertEqual(code, 0, err)
        record = self.store_record("41")
        self.assertEqual(record["slug"], "new")
        self.assertEqual(record["tree"], os.path.realpath(self.main))
        self.assertEqual(self.check(self.issues / "41-new.md")[0], 0)

    def test_a_split_renames_on_its_parent_and_needs_no_claim(self):
        (self.issues / "216-parent.md").write_text("x\n")
        (self.issues / "216b-old.md").write_text("x\n")
        code, _, err = self.rename(self.issues / "216b-old.md", self.issues / "216b-new.md")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.check(self.issues / "216b-new.md")[0], 0)
        code, _, err = self.rename(self.issues / "216b-old.md", self.issues / "216c-new.md")
        self.assertEqual(code, 1)

    def test_a_migration_renames_the_same_way(self):
        number = self.claim("migration", self.migrations, "--for", "implementer", "--slug", "old")[1]
        (self.migrations / f"{number}_old.sql").write_text("select 1;\n")
        code, _, err = self.rename(self.migrations / f"{number}_old.sql",
                                   self.migrations / f"{number}_new.sql")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.store_record(number)["slug"], "new")

    def test_the_rename_moves_no_file_itself(self):
        self.claim("issue", self.issues, "--for", "a", "--slug", "old")
        (self.issues / "01-old.md").write_text("x\n")
        self.rename(self.issues / "01-old.md", self.issues / "01-new.md")
        self.assertTrue((self.issues / "01-old.md").is_file())
        self.assertFalse((self.issues / "01-new.md").exists())

    def test_every_rename_refusal_leads_with_what_to_do(self):
        self.claim("issue", self.issues, "--for", "a", "--slug", "old")
        (self.issues / "01-old.md").write_text("x\n")
        for old, new in ((self.issues / "01-old.md", self.issues / "02-old.md"),
                         (self.issues / "09-gone.md", self.issues / "09-new.md"),
                         (self.issues / "01-old.md", self.issues / "01-old.md")):
            with self.subTest(new=new.name):
                _, _, err = self.rename(old, new)
                first = err.strip().splitlines()[0]
                self.assertTrue(first.startswith("REFUSED. "), first)

    def test_a_rename_outside_any_repository_is_refused_rather_than_silently_passed(self):
        loose = Path(self.tmp.name) / "loose" / "issues"
        loose.mkdir(parents=True)
        (loose / "01-old.md").write_text("x\n")
        code, _, _ = run(["--rename", str(loose / "01-old.md"), str(loose / "01-new.md")],
                         self.tmp.name, self.store)
        self.assertNotEqual(code, 0)


class TestEveryMinterNamesTheClaimScript(unittest.TestCase):
    """Ruling 16: every minter calls the claim script. A minter is a skill or brief
    that writes a new issue file or a new migration, and the text is where the
    rule reaches an agent, so the text is what these read."""

    SKILLS = HERE.parent
    # `agents/`, `hooks/` and `settings.json` are NOT in this git repo. They live
    # under `~/.claude` and nowhere else, so a climb from `__file__` finds them
    # only from the main checkout and lands on nothing from a worktree. The two
    # trees are separate facts and are resolved separately.
    CLAUDE = Path.home() / ".claude"
    MINTERS = {
        "to-issues": SKILLS / "to-issues" / "SKILL.md",
        "promotion brief": CLAUDE / "agents" / "promotion.md",
        # `parallel-hunt` left this list with issue 36 of the tracker-tooling
        # set, and the `run-issues` finale with issue 39: neither spawns
        # promotion any more, so neither mints anything.
        "daily-brief": SKILLS / "daily-brief" / "SKILL.md",
        "implementer": CLAUDE / "agents" / "run-issues-implementer.md",
        "escalated implementer": CLAUDE / "agents" / "run-issues-implementer-escalated.md",
        "harden-issues": SKILLS / "harden-issues" / "SKILL.md",
    }

    # A minter whose file this pack does not carry is skipped, never failed.
    # `to-issues` is deliberately unpublished, and a reader may not have installed
    # every skill named above.
    def minters(self):
        found = {n: p for n, p in self.MINTERS.items() if p.is_file()}
        if not found:
            self.skipTest("no minter file is installed beside this pack")
        return found

    def test_each_minter_names_the_claim_script(self):
        for name, path in self.minters().items():
            with self.subTest(minter=name):
                self.assertIn("claim_number.py", path.read_text())

    def test_the_two_implementer_briefs_claim_a_migration_number(self):
        for name in ("implementer", "escalated implementer"):
            path = self.MINTERS[name]
            if not path.is_file():
                continue
            with self.subTest(brief=name):
                self.assertIn("claim_number.py migration", path.read_text())

    def test_the_hook_is_registered_on_every_writing_tool(self):
        """The refusal that makes the claim a rule rather than a reminder.

        This pack ships the check, not the hook that calls it, so this grades a
        `settings.json` beside the installed tool directory when there is one and
        skips otherwise. A reader who writes the hook gets the registration graded;
        a reader who does not is told nothing false.
        """
        import json
        settings = self.CLAUDE / "settings.json"
        if not settings.is_file():
            self.skipTest(f"{settings} is not on this machine")
        cfg = json.loads(settings.read_text())
        entries = [e for e in cfg.get("hooks", {}).get("PreToolUse", [])
                   if any("number-claim-guard.py" in h["command"] for h in e["hooks"])]
        if not entries:
            self.skipTest("no number-claim-guard.py hook is registered")
        self.assertEqual(len(entries), 1)
        for tool in ("Edit", "Write", "NotebookEdit", "Bash"):
            self.assertIn(tool, entries[0]["matcher"])

    def test_no_minter_still_reads_the_number_off_a_listing(self):
        for name, path in self.minters().items():
            with self.subTest(minter=name):
                text = path.read_text().lower()
                for phrase in ("next free number", "highest number in the directory", "the numbering rule"):
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
