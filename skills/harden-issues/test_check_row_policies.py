#!/usr/bin/env python3
"""Tests for check_row_policies.py. Run: python3 test_check_row_policies.py

The human's ruling `q-fin4d16a5-06` of 2026-10-12. One tracker's issue 485 took a strike
because the `pending_uploads` delete policy (migration 0058) admits admin and nobody
knew. The fixtures are cut down from that table and its migrations, built in `tmp`.
"""

import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_row_policies as check  # noqa: E402

SCRIPT = pathlib.Path(__file__).parent / "check_row_policies.py"

CREATE = """
create table public.pending_uploads (id uuid primary key, owner uuid, job_id uuid);
alter table public.pending_uploads enable row level security;
create table public.jobs (id uuid primary key);
alter table public.jobs enable row level security;
create table public.audit (id uuid primary key);
alter table public.audit enable row level security;
-- create policy commented_out on public.jobs for select using (true);
create policy pending_uploads_delete_own on public.pending_uploads
  for delete to authenticated using (owner = auth.uid());
create policy jobs_select_staff on public.jobs
  for select to authenticated using (public.is_enabled_staff());
"""

ADMIN = """
drop policy if exists pending_uploads_delete_own on public.pending_uploads;
create policy pending_uploads_delete_owner_or_admin on public.pending_uploads
  for delete to authenticated
  using (public.is_enabled_staff() and (owner = auth.uid() or public.has_role('admin')));
"""

MODEL = 'const q = "delete from public.pending_uploads where id = $1";\n'


def make(root: pathlib.Path, migrations: dict[str, str], files: dict[str, str]) -> pathlib.Path:
    for name, sql in migrations.items():
        target = root / "supabase" / "migrations" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sql)
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return root


def issue(touches: str, section: str = "") -> str:
    return f"Status: needs-harden\nTouches: {touches}\n\n# Issue\n\n## Acceptance criteria\n\n1. A thing.\n\n{section}"


def fill(block: str, reads: str = "enabled staff", writes: str = "owner and admin") -> str:
    return block.replace(check.BLANK + ". Writes", reads + ". Writes").replace(check.BLANK, writes)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        make(self.root, {"0001_create.sql": CREATE, "0002_admin.sql": ADMIN},
             {"src/model/pending-uploads.ts": MODEL, "src/model/notes.ts": "// jobs and users, in English\n"})

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return check.Migrations(self.root / "supabase" / "migrations")

    def printed(self, touches="`src/model/pending-uploads.ts`"):
        state = self.state()
        tables, _, _ = check.touched(self.root, state, check.touches(issue(touches)))
        return check.block(state, tables)

    def faults(self, text):
        return check.faults(text, self.root, self.state())[0]


class WhatTheMigrationsLeaveStanding(Fixture):
    def test_the_policy_that_replaced_the_old_one_is_the_one_standing(self):
        """485's fact: 0058 dropped the owner-only policy and the admin one stands."""
        names = set(self.state().policies["pending_uploads"])
        self.assertEqual(names, {"pending_uploads_delete_owner_or_admin"})

    def test_the_printed_block_carries_the_expression_that_admits_admin(self):
        self.assertIn("public.has_role('admin')", self.printed())

    def test_a_policy_in_a_comment_is_not_standing(self):
        self.assertNotIn("commented_out", self.state().policies["jobs"])

    def test_alter_policy_changes_what_stands_and_its_signature(self):
        before = self.state().policies["jobs"]["jobs_select_staff"].signature()
        make(self.root, {"0003_alter.sql":
                         "alter policy jobs_select_staff on public.jobs using (public.has_role('admin'));"}, {})
        after = self.state().policies["jobs"]["jobs_select_staff"]
        self.assertNotEqual(before, after.signature())
        self.assertEqual(after.using, "public.has_role('admin')")

    def test_a_dropped_table_takes_its_policies_with_it(self):
        make(self.root, {"0003_drop.sql": "drop table public.jobs;"}, {})
        self.assertNotIn("jobs", self.state().tables)

    def test_a_renamed_table_keeps_its_policies(self):
        make(self.root, {"0003_rename.sql": "alter table public.jobs rename to orders;"}, {})
        self.assertIn("jobs_select_staff", self.state().policies["orders"])

    def test_a_policy_built_inside_execute_format_is_read_with_the_migration_role(self):
        make(self.root, {"0003_dynamic.sql": (
            "do $$ begin execute format(\n"
            "  'create policy jobs_select_owner on public.jobs '\n"
            "  'for select to %I using (true)', current_user); end $$;")}, {})
        policy = self.state().policies["jobs"]["jobs_select_owner"]
        self.assertEqual((policy.command, policy.roles, policy.using), ("select", "current_user", "true"))

    def test_a_policy_whose_name_is_built_in_a_loop_is_listed_as_not_itemised(self):
        make(self.root, {"0003_loop.sql": (
            "do $$ begin execute format('create policy %I on public.%I for select to %I using (true)',\n"
            "  target || '_select_own', target, current_user); end $$;")}, {})
        self.assertIn("0003_loop.sql", self.state().unplaced)


class WhichTablesAnIssueTouches(Fixture):
    def reached(self, touches):
        return set(check.touched(self.root, self.state(), check.touches(issue(touches)))[0])

    def test_a_file_that_names_the_table_schema_qualified_reaches_it(self):
        self.assertEqual(self.reached("`src/model/pending-uploads.ts`"), {"pending_uploads"})

    def test_the_client_from_call_reaches_it(self):
        make(self.root, {}, {"src/db.ts": 'await client.from("jobs").select();\n'})
        self.assertEqual(self.reached("`src/db.ts`"), {"jobs"})

    def test_a_one_word_table_as_a_plain_word_is_not_reached(self):
        self.assertEqual(self.reached("`src/model/notes.ts`"), set())

    def test_an_underscore_table_as_a_plain_word_is_reached(self):
        make(self.root, {}, {"src/names.ts": "const key = 'pending_uploads';\n"})
        self.assertEqual(self.reached("`src/names.ts`"), {"pending_uploads"})

    def test_a_folder_and_a_glob_are_read(self):
        self.assertEqual(self.reached("`src/model/`"), {"pending_uploads"})
        self.assertEqual(self.reached("`src/model/pending-*.ts`"), {"pending_uploads"})

    def test_a_folder_with_brackets_in_its_name_is_read(self):
        make(self.root, {}, {"src/app/jobs/[number]/page.tsx": 'select * from public.jobs'})
        self.assertEqual(self.reached("`src/app/jobs/[number]/page.tsx`"), {"jobs"})

    def test_an_entry_that_is_the_table_itself_counts(self):
        self.assertEqual(self.reached("`public.jobs`, `pending_uploads`"), {"jobs", "pending_uploads"})

    def test_a_file_the_issue_will_create_is_unread_and_not_a_fault(self):
        _, unread, _ = check.touched(self.root, self.state(), ["src/new-file.ts"])
        self.assertEqual(unread, ["src/new-file.ts"])


class TheSectionIsOwed(Fixture):
    def test_a_touched_table_and_no_section_is_refused(self):
        found = self.faults(issue("`src/model/pending-uploads.ts`"))
        self.assertEqual(len(found), 1)
        self.assertIn("`pending_uploads`", found[0])
        self.assertIn("no `## Row policies` section", found[0])

    def test_issue_485_as_it_was_stamped_is_refused(self):
        """485 named the file, not the table, and carried no policy fact."""
        self.assertTrue(self.faults(issue("`src/model/pending-uploads.ts`, `tests/alerts/*.test.ts`")))

    def test_no_table_reached_and_no_migration_owes_nothing(self):
        self.assertEqual(self.faults(issue("`src/model/notes.ts`")), [])

    def test_an_issue_with_no_touches_line_owes_nothing(self):
        self.assertEqual(self.faults("Status: needs-harden\n\n# Issue\n"), [])

    def test_the_printed_block_filled_in_passes(self):
        block = fill(self.printed())
        self.assertEqual(self.faults(issue("`src/model/pending-uploads.ts`", block)), [])

    def test_the_printed_block_left_blank_is_refused_on_both_labels(self):
        found = self.faults(issue("`src/model/pending-uploads.ts`", self.printed()))
        self.assertEqual(sorted(re.findall(r"no `(\w+):`", " ".join(found))), ["Reads", "Writes"])

    def test_a_block_with_one_label_blank_is_refused(self):
        block = fill(self.printed(), reads="enabled staff", writes="").replace("Writes: .", "Writes: <fill>.")
        self.assertTrue(any("Writes" in f for f in self.faults(issue("`src/model/pending-uploads.ts`", block))))

    def test_a_table_left_out_of_the_section_is_refused(self):
        make(self.root, {}, {"src/two.ts": "from public.pending_uploads; from public.jobs"})
        state = self.state()
        tables, _, _ = check.touched(self.root, state, ["src/two.ts"])
        only_one = check.block(state, {"pending_uploads": tables["pending_uploads"]})
        found = self.faults(issue("`src/two.ts`", fill(only_one)))
        self.assertEqual(len(found), 1)
        self.assertIn("table `jobs` has no block", found[0])

    def test_a_policy_changed_after_the_section_was_written_is_refused(self):
        block = fill(self.printed())
        make(self.root, {"0003_loosen.sql": (
            "alter policy pending_uploads_delete_owner_or_admin on public.pending_uploads using (true);")}, {})
        found = self.faults(issue("`src/model/pending-uploads.ts`", block))
        self.assertTrue(any("has changed since" in f for f in found))

    def test_a_policy_dropped_after_the_section_was_written_is_refused(self):
        block = fill(self.printed())
        make(self.root, {"0003_drop.sql": "drop policy pending_uploads_delete_owner_or_admin on public.pending_uploads;"}, {})
        found = self.faults(issue("`src/model/pending-uploads.ts`", block))
        self.assertTrue(any("no migration leaves standing" in f for f in found))

    def test_a_standing_policy_the_section_does_not_name_is_refused(self):
        make(self.root, {"0003_more.sql": (
            "create policy pending_uploads_select_all on public.pending_uploads for select to authenticated using (true);")}, {})
        found = self.faults(issue("`src/model/pending-uploads.ts`", fill(self.printed()).replace(
            "pending_uploads_select_all", "x")))
        self.assertTrue(any("`pending_uploads_select_all` stands" in f for f in found))

    def test_a_section_cannot_be_satisfied_by_a_heading_alone(self):
        found = self.faults(issue("`src/model/pending-uploads.ts`", "## Row policies\n\nThey are fine.\n"))
        self.assertTrue(any("has no block" in f for f in found))


class ATableWithNoPolicy(Fixture):
    def setUp(self):
        super().setUp()
        make(self.root, {}, {"src/audit.ts": "select * from public.audit"})

    def test_it_needs_a_no_policies_line_with_words(self):
        printed = self.printed("`src/audit.ts`")
        self.assertIn("No policies:", printed)
        self.assertTrue(self.faults(issue("`src/audit.ts`", printed)))
        said = printed.replace(check.BLANK, "every API role is denied; only the owner role reads it")
        self.assertEqual(self.faults(issue("`src/audit.ts`", said)), [])

    def test_no_policies_on_a_table_that_has_policies_is_refused(self):
        wrong = fill(self.printed()).replace(
            "- Table `pending_uploads`", "- Table `pending_uploads`\n  - No policies: everything is denied here\n", 1)
        self.assertTrue(any("says `No policies:`" in f for f in self.faults(issue("`src/model/pending-uploads.ts`", wrong))))


class NotItemised(Fixture):
    def setUp(self):
        super().setUp()
        make(self.root, {"0003_loop.sql": (
            "do $$ begin execute format('create policy %I on public.%I for select to %I using (true)',\n"
            "  target || '_select_own', target, current_user); end $$;")}, {})

    def test_the_printed_block_carries_the_note_and_passes(self):
        block = fill(self.printed())
        self.assertIn("Not itemised: `0003_loop.sql`", block)
        self.assertEqual(self.faults(issue("`src/model/pending-uploads.ts`", block)), [])

    def test_a_section_without_the_note_is_refused(self):
        block = re.sub(r"- Not itemised:.*\n?", "", fill(self.printed()))
        found = self.faults(issue("`src/model/pending-uploads.ts`", block))
        self.assertTrue(any("Not itemised" in f and "0003_loop.sql" in f for f in found))


class AMigrationIssue(Fixture):
    def test_naming_the_migrations_folder_owes_the_section(self):
        found = self.faults(issue("`supabase/migrations/`"))
        self.assertEqual(len(found), 1)
        self.assertIn("`supabase/migrations`", found[0])

    def test_none_with_a_reason_passes(self):
        section = "## Row policies\n\n- None: the migration adds a column and no policy.\n"
        self.assertEqual(self.faults(issue("`supabase/migrations/`", section)), [])

    def test_none_without_a_reason_is_refused(self):
        self.assertTrue(self.faults(issue("`supabase/migrations/`", "## Row policies\n\n- None: no.\n")))

    def test_a_new_table_s_policy_needs_its_roles_too(self):
        section = ("## Row policies\n\n- Table `invoices`\n"
                   "  - `invoices_select_staff` #00000000 — select to authenticated. Reads: <fill>. Writes: none.\n")
        found = self.faults(issue("`supabase/migrations/`", section))
        self.assertTrue(any("`Reads:`" in f for f in found))


class TheCommandLine(Fixture):
    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def write(self, name, text):
        path = self.root / ".scratch" / "issues" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return str(path)

    def test_a_refused_issue_exits_one_and_names_the_table(self):
        done = self.run_script("--issue", self.write("485-upload-alerts.md", issue("`src/model/pending-uploads.ts`")))
        self.assertEqual(done.returncode, 1)
        self.assertIn("REFUSED   485", done.stderr)
        self.assertIn("`pending_uploads`", done.stderr)

    def test_print_then_fill_then_check_exits_zero(self):
        path = self.write("485-upload-alerts.md", issue("`src/model/pending-uploads.ts`"))
        printed = self.run_script("--print", "--issue", path)
        self.assertEqual(printed.returncode, 0)
        self.assertIn("public.has_role('admin')", printed.stdout)
        text = pathlib.Path(path).read_text() + "\n" + fill(printed.stdout)
        pathlib.Path(path).write_text(text)
        done = self.run_script("--issue", path)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ok        485", done.stdout)

    def test_one_clean_and_one_refused_issue_exit_one(self):
        clean = self.write("1-clean.md", issue("`src/model/notes.ts`"))
        bad = self.write("2-bad.md", issue("`src/model/pending-uploads.ts`"))
        self.assertEqual(self.run_script("--issue", clean, "--issue", bad).returncode, 1)

    def test_a_repo_with_no_migrations_folder_says_so_and_passes(self):
        with tempfile.TemporaryDirectory() as bare:
            path = pathlib.Path(bare) / "1-x.md"
            path.write_text(issue("`src/a.ts`"))
            done = self.run_script("--issue", str(path))
        self.assertEqual(done.returncode, 0)
        self.assertIn("no supabase/migrations above this file", done.stdout)

    def test_an_unreadable_issue_is_refused(self):
        self.assertEqual(self.run_script("--issue", str(self.root / "gone.md")).returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
