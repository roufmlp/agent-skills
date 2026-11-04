#!/usr/bin/env python3
"""Drill for note_check.py and the three hook templates: a throwaway product
repo with the hooks installed by the prepare script, where every refusal and
every allowed case is a real git commit, merge or push.

    python3 test_note_check.py

`HOME` points at a temporary directory whose `.claude/skills/workflow/lib` links to this
directory, so the hooks' one path line resolves to the script under test.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import note_check as mod  # noqa: E402
from test_suite import BLOCK, FAKE_VITEST  # noqa: E402

SCRIPT = os.path.join(HERE, "note_check.py")
HOOKS = pathlib.Path(HERE).parent / "templates" / "githooks"

DESIGN = textwrap.dedent("""\
    # A product core design

    ## Screens

    | Screen | Route | Group |
    | --- | --- | --- |
    | Sign in | /login | public |
    | Home | / | signed-in |
    | Orders | /orders | signed-in |
    | Order | /orders/[id] | signed-in |

    Shared files for signed-in: src/app/(signed-in)/layout.tsx

    ## Patterns

    | Pattern | Check |
    | --- | --- |
    | one button | `npm run check:controls` |
""")

NOTE_01 = "# 01 Header bubble\n\nA bubble in the header.\n\nScreens: all signed-in\nRisk: none\n"
NOTE_02 = "# 02 Order page\n\nThe order page shows it.\n\nScreens: Order\nRisk: none\n"

FILES = {
    "docs/design.md": DESIGN,
    "src/app/login/page.tsx": "export default () => null;\n",
    "src/app/(signed-in)/layout.tsx": "export default ({children}) => children;\n",
    "src/app/(signed-in)/(home)/page.tsx": "export default () => null;\n",
    "src/app/(signed-in)/orders/page.tsx": "export default () => null;\n",
    "src/app/(signed-in)/orders/[id]/page.tsx": "export default () => null;\n",
    "src/app/(signed-in)/orders/[id]/parts/row.tsx": "export const Row = 1;\n",
    "src/app/(signed-in)/lines/helper.ts": "export const h = 1;\n",
    "src/lib/money.ts": "export const money = 1;\n",
    "README.md": "# A product\n",
    "e2e/screens.spec.ts": "// screens\n",
    "e2e/screens.spec.ts-snapshots/orders-390.png": "png\n",
    "e2e/screens.spec.ts-snapshots/order-390.png": "png\n",
    "supabase/migrations/0001_a.sql": "select 1;\n",
    "changes/bubble/01-header.md": NOTE_01,
    "changes/bubble/02-order.md": NOTE_02,
    "changes/07-csv.md": "# 07 CSV\n\nScreens: Orders\n",
    "tests/a.test.ts": 'it("adds", () => {});\n',
    "package.json": '{"name": "p", "scripts": {"prepare": "sh .githooks/prepare"}}\n',
}


class Product(unittest.TestCase):
    """A product repo on `main` with one commit, then the hooks installed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        home = root / "home"
        (home / ".claude" / "skills" / "workflow").mkdir(parents=True)
        os.symlink(HERE, home / ".claude" / "skills" / "workflow" / "lib")
        self.vitest = root / "vitest"
        self.vitest.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
        self.vitest.chmod(0o755)
        self.env = {**os.environ, "HOME": str(home), "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                    "RUN_SUITE_LOCK": str(root / "lock"), "FAKE_ARGV": str(root / "argv.jsonl")}
        for key in ("FAKE_FAILING", "FAKE_FLAKY", "FAKE_EXIT", "FAKE_RAN", "FAKE_STATUS",
                    "FAKE_NO_LOAD", "FAKE_HOLD"):
            self.env.pop(key, None)
        self.tree = root / "product"
        self.tree.mkdir()
        for path, text in FILES.items():
            self.write(path, text)
        self.write("CLAUDE.md", BLOCK.format(vitest=self.vitest))
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        shutil.copytree(HOOKS, self.tree / ".githooks")
        prepared = subprocess.run(["sh", ".githooks/prepare"], cwd=self.tree, env=self.env,
                                  capture_output=True, text=True)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.git("add", ".githooks")
        self.git("commit", "-qm", "hooks")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        full = self.tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text)

    def git(self, *args, check=True, env=None, stdin=None):
        done = subprocess.run(["git", *args], cwd=self.tree, env={**self.env, **(env or {})},
                              capture_output=True, text=True, input=stdin)
        if check and done.returncode:
            raise AssertionError(f"git {' '.join(args)} failed:\n{done.stdout}\n{done.stderr}")
        return done

    def commit(self, message, *paths, env=None):
        """Stage `paths` and commit through the hooks: (exit code, output)."""
        self.git("add", "-A", "--", *paths)
        done = self.git("commit", "-qm", message, check=False, env=env)
        return done.returncode, done.stdout + done.stderr

    def branch(self, name):
        self.git("checkout", "-q", "-b", name)

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()


# ── The commit-to-note map ───────────────────────────────────────────────────

class TheMap(unittest.TestCase):
    PATHS = ["changes/bubble/01-header.md", "changes/bubble/02-order.md", "changes/07-csv.md",
             "changes/bubble/plan.md", "changes/bubble/notes/02-old.md"]

    def test_a_note_branch_maps_to_its_note(self):
        self.assertEqual(mod.note_paths("note/bubble/02", self.PATHS), ["changes/bubble/02-order.md"])

    def test_a_one_note_branch_maps_to_the_top_level_note(self):
        self.assertEqual(mod.note_paths("note/07", self.PATHS), ["changes/07-csv.md"])

    def test_a_feature_branch_maps_to_every_note_of_the_feature(self):
        self.assertEqual(mod.note_paths("feature/bubble", self.PATHS),
                         ["changes/bubble/01-header.md", "changes/bubble/02-order.md"])

    def test_main_and_other_branches_map_to_no_note(self):
        for branch in ("main", "fix/typo", "", "notes/bubble/02"):
            with self.subTest(branch=branch):
                self.assertIsNone(mod.note_paths(branch, self.PATHS))

    def test_a_note_branch_without_its_file_is_refused(self):
        with self.assertRaises(mod.Refusal) as caught:
            mod.note_paths("note/bubble/03", self.PATHS)
        self.assertIn("has no `03-*.md`", str(caught.exception))


class TheScreensPart(unittest.TestCase):
    def test_the_table_and_the_shared_files_are_read(self):
        rows, shared = mod.read_screens(DESIGN)
        self.assertEqual([r["screen"] for r in rows], ["Sign in", "Home", "Orders", "Order"])
        self.assertEqual(rows[3], {"screen": "Order", "route": "/orders/[id]", "group": "signed-in"})
        self.assertEqual(shared, {"signed-in": ["src/app/(signed-in)/layout.tsx"]})

    def test_another_table_is_not_the_screens_table(self):
        rows, _ = mod.read_screens("| Pattern | Check |\n| --- | --- |\n| one | `x` |\n")
        self.assertEqual(rows, [])

    def test_no_design_gives_no_screens(self):
        self.assertEqual(mod.read_screens(None), ([], {}))

    def test_routes_drop_groups_and_slots(self):
        self.assertEqual(mod.route_of_page("src/app/(signed-in)/orders/[id]/page.tsx"), "/orders/[id]")
        self.assertEqual(mod.route_of_page("src/app/(signed-in)/(home)/page.tsx"), "/")
        self.assertEqual(mod.route_of_page("app/@modal/login/page.js"), "/login")
        self.assertIsNone(mod.route_of_page("src/app/(signed-in)/layout.tsx"))
        self.assertIsNone(mod.route_of_page("src/lib/page.tsx.bak"))

    def test_a_file_belongs_to_the_deepest_page_folder_above_it(self):
        folders = mod.page_folders(list(FILES))
        self.assertEqual(mod.folder_of("src/app/(signed-in)/orders/[id]/parts/row.tsx", folders),
                         "src/app/(signed-in)/orders/[id]")
        self.assertEqual(mod.folder_of("src/app/(signed-in)/orders/table.tsx", folders),
                         "src/app/(signed-in)/orders")
        self.assertIsNone(mod.folder_of("src/app/(signed-in)/layout.tsx", folders))
        self.assertIsNone(mod.folder_of("src/app/(signed-in)/lines/helper.ts", folders))

    def test_a_rewrite_is_a_changed_or_removed_row_not_an_added_one(self):
        added = DESIGN.replace("| Order | /orders/[id] | signed-in |",
                               "| Order | /orders/[id] | signed-in |\n| Bills | /bills | signed-in |")
        self.assertEqual(mod.screens_rewritten(DESIGN, added), [])
        moved = DESIGN.replace("| Orders | /orders |", "| Orders | /jobs |")
        self.assertEqual(mod.screens_rewritten(DESIGN, moved), ["Orders"])
        self.assertEqual(mod.screens_rewritten(DESIGN, DESIGN.replace("| Home | / | signed-in |\n", "")),
                         ["Home"])

    def test_slugs(self):
        self.assertEqual(mod.slug("Order line"), "order-line")
        self.assertEqual(mod.slug("Sign in"), "sign-in")


# ── pre-commit: the note check ───────────────────────────────────────────────

class ANoteBranch(Product):
    def test_touching_a_named_route_passes(self):
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/orders/[id]/page.tsx", "export default () => 2;\n")
        code, out = self.commit("order", "src")
        self.assertEqual(code, 0, out)
        self.assertIn("note check: passed", out)

    def test_touching_a_route_the_note_does_not_name_is_refused(self):
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/orders/page.tsx", "export default () => 2;\n")
        code, out = self.commit("orders list", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)
        self.assertIn("route folder of screen `Orders`", out)
        self.assertIn("changes/bubble/02-order.md does not name it", out)

    def test_a_file_below_the_route_folder_counts(self):
        self.branch("note/bubble/01")
        self.write("src/app/(signed-in)/orders/[id]/parts/row.tsx", "export const Row = 2;\n")
        code, out = self.commit("row", "src")
        self.assertEqual(code, 0, out)  # note 01 names all signed-in, Order among them
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/orders/parts/new.tsx", "export const N = 1;\n")
        code, out = self.commit("orders part", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("screen `Orders`", out)

    def test_a_file_under_app_outside_every_listed_route_passes(self):
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/lines/helper.ts", "export const h = 2;\n")
        self.write("src/lib/money.ts", "export const money = 2;\n")
        code, out = self.commit("helper", "src")
        self.assertEqual(code, 0, out)

    def test_a_shared_file_needs_the_whole_group(self):
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/layout.tsx", "export default ({children}) => [children];\n")
        code, out = self.commit("layout", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("shared file of group `signed-in`", out)
        self.assertIn("`Home`, `Orders`", out)
        self.assertIn("`Screens: all signed-in`", out)

    def test_all_group_names_the_shared_file(self):
        self.branch("note/bubble/01")
        self.write("src/app/(signed-in)/layout.tsx", "export default ({children}) => [children];\n")
        code, out = self.commit("layout", "src")
        self.assertEqual(code, 0, out)

    def test_a_new_page_at_an_unlisted_route_is_refused(self):
        self.branch("note/bubble/02")
        self.write("src/app/(signed-in)/bills/page.tsx", "export default () => null;\n")
        code, out = self.commit("bills", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("new page at route `/bills`", out)

    def test_a_new_page_listed_in_the_same_commit_passes(self):
        self.branch("note/bubble/02")
        self.write("changes/bubble/02-order.md", NOTE_02 + "Core design: adds screen Bills\n")
        self.commit("note names bills", "changes")
        self.write("changes/bubble/02-order.md",
                   "# 02\n\nScreens: Order, Bills\nCore design: adds screen Bills\n")
        self.write("docs/design.md", DESIGN.replace(
            "| Order | /orders/[id] | signed-in |",
            "| Order | /orders/[id] | signed-in |\n| Bills | /bills | signed-in |"))
        self.write("src/app/(signed-in)/bills/page.tsx", "export default () => null;\n")
        code, out = self.commit("bills", "src", "docs", "changes")
        self.assertEqual(code, 0, out)

    def test_a_screens_line_naming_an_unknown_screen_is_refused(self):
        self.branch("note/bubble/02")
        self.write("changes/bubble/02-order.md", "# 02\n\nScreens: Order, Invoices\n")
        code, out = self.commit("bad note", "changes")
        self.assertEqual(code, 1, out)
        self.assertIn("names screen `Invoices`", out)

    def test_a_note_without_a_screens_line_is_refused(self):
        self.branch("note/bubble/02")
        self.write("changes/bubble/02-order.md", "# 02\n\nNo screens line.\n")
        code, out = self.commit("bad note", "changes")
        self.assertEqual(code, 1, out)
        self.assertIn("has no `Screens:` line", out)

    def test_a_branch_whose_note_is_missing_is_refused(self):
        self.branch("note/bubble/03")
        self.write("README.md", "# A product, again\n")
        code, out = self.commit("readme", "README.md")
        self.assertEqual(code, 1, out)
        self.assertIn("has no `03-*.md`", out)

    def test_a_one_note_change_maps_by_number(self):
        self.branch("note/07")
        self.write("src/app/(signed-in)/orders/page.tsx", "export default () => 7;\n")
        code, out = self.commit("csv", "src")
        self.assertEqual(code, 0, out)


class Baselines(Product):
    def test_a_named_screens_baseline_passes(self):
        self.branch("note/bubble/02")
        self.write("e2e/screens.spec.ts-snapshots/order-390.png", "png2\n")
        self.write("e2e/screens.spec.ts-snapshots/order-1280-chromium-darwin.png", "png\n")
        code, out = self.commit("baseline", "e2e")
        self.assertEqual(code, 0, out)

    def test_an_unnamed_screens_baseline_is_refused(self):
        self.branch("note/bubble/02")
        self.write("e2e/screens.spec.ts-snapshots/orders-390.png", "png2\n")
        code, out = self.commit("baseline", "e2e")
        self.assertEqual(code, 1, out)
        self.assertIn("baseline of screen `Orders`", out)

    def test_a_baseline_matching_no_screen_is_refused(self):
        self.branch("note/bubble/01")
        self.write("e2e/screens.spec.ts-snapshots/invoices-390.png", "png\n")
        code, out = self.commit("baseline", "e2e")
        self.assertEqual(code, 1, out)
        self.assertIn("no screen in docs/design.md has that name", out)

    def test_on_the_feature_branch_any_note_may_name_the_screen(self):
        self.branch("feature/bubble")
        self.write("e2e/screens.spec.ts-snapshots/order-390.png", "retaken\n")
        self.write("e2e/screens.spec.ts-snapshots/home-390.png", "new\n")
        code, out = self.commit("retaken baselines", "e2e")
        self.assertEqual(code, 0, out)

    def test_on_the_feature_branch_a_screen_no_note_names_is_refused(self):
        self.branch("feature/bubble")
        self.write("e2e/screens.spec.ts-snapshots/sign-in-390.png", "new\n")
        code, out = self.commit("sign in baseline", "e2e")
        self.assertEqual(code, 1, out)
        self.assertIn("no note on this branch names it", out)


class TheFixRound(Product):
    """On the feature branch a test file belongs to a note, or it does not land."""

    NOTE_03 = "# 03 Totals\n\nThe totals line.\n\nScreens: none\nRisk: none\n\n## Tests\n\n- `tests/bubble/totals.test.ts`\n"

    def test_a_new_test_no_note_names_is_refused(self):
        self.branch("feature/bubble")
        self.write("tests/rehearsal/tables-exist.test.ts", 'it("tables", () => {});\n')
        code, out = self.commit("fix: guard the tables", "tests")
        self.assertEqual(code, 1, out)
        self.assertIn("tests/rehearsal/tables-exist.test.ts is a new test file, and no note in the feature names it", out)
        self.assertIn("a new note for Abdul", out)

    def test_a_note_and_its_tests_land_together(self):
        self.branch("feature/bubble")
        self.write("changes/bubble/03-totals.md", self.NOTE_03)
        self.write("tests/bubble/totals.test.ts", 'it("totals", () => {});\n')
        code, out = self.commit("note 03: totals", "changes", "tests")
        self.assertEqual(code, 0, out)

    def test_deleting_a_live_notes_test_is_refused(self):
        self.branch("feature/bubble")
        self.write("changes/bubble/03-totals.md", self.NOTE_03)
        self.write("tests/bubble/totals.test.ts", 'it("totals", () => {});\n')
        self.commit("note 03: totals", "changes", "tests")
        (self.tree / "tests/bubble/totals.test.ts").unlink()
        code, out = self.commit("fix: drop the totals test", "tests")
        self.assertEqual(code, 1, out)
        self.assertIn("tests/bubble/totals.test.ts is deleted, and changes/bubble/03-totals.md still names it", out)

    def test_a_cut_takes_its_tests_with_it(self):
        self.branch("feature/bubble")
        self.write("changes/bubble/03-totals.md", self.NOTE_03)
        self.write("tests/bubble/totals.test.ts", 'it("totals", () => {});\n')
        self.commit("note 03: totals", "changes", "tests")
        (self.tree / "changes/bubble/cut").mkdir()
        self.git("mv", "changes/bubble/03-totals.md", "changes/bubble/cut/03-totals.md")
        (self.tree / "tests/bubble/totals.test.ts").unlink()
        code, out = self.commit("cut 03", "changes", "tests")
        self.assertEqual(code, 0, out)

    def test_a_note_branch_may_add_a_test(self):
        self.branch("note/bubble/01")
        self.write("tests/bubble/header-more.test.ts", 'it("more", () => {});\n')
        code, out = self.commit("note 01: one more test", "tests")
        self.assertEqual(code, 0, out)

    def test_a_retaken_baseline_is_not_a_test_file(self):
        self.branch("feature/bubble")
        self.write("e2e/screens.spec.ts-snapshots/order-390.png", "retaken\n")
        code, out = self.commit("baselines: order", "e2e")
        self.assertEqual(code, 0, out)


class NoNote(Product):
    def test_a_plain_file_passes_on_main(self):
        self.write("README.md", "# A product, again\n")
        self.write("src/lib/money.ts", "export const money = 3;\n")
        code, out = self.commit("readme", "README.md", "src")
        self.assertEqual(code, 0, out)

    def test_a_route_folder_is_refused_on_main(self):
        self.write("src/app/(signed-in)/orders/page.tsx", "export default () => 3;\n")
        code, out = self.commit("orders", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("branch `main` names no note", out)

    def test_a_baseline_and_the_design_are_refused_on_main(self):
        self.write("e2e/screens.spec.ts-snapshots/order-390.png", "png3\n")
        self.write("docs/design.md", DESIGN + "\nMore.\n")
        code, out = self.commit("guarded", "e2e", "docs")
        self.assertEqual(code, 1, out)
        self.assertIn("baseline of screen `Order`", out)
        self.assertIn("docs/design.md changed, and branch `main` names no note", out)

    def test_a_branch_that_names_no_note_is_treated_like_main(self):
        self.branch("fix/typo")
        self.write("src/app/(signed-in)/orders/page.tsx", "export default () => 3;\n")
        code, out = self.commit("orders", "src")
        self.assertEqual(code, 1, out)
        self.assertIn("branch `fix/typo` names no note", out)


class TheCoreDesign(Product):
    def test_a_design_change_needs_a_core_design_line(self):
        self.branch("note/bubble/02")
        self.write("docs/design.md", DESIGN.replace("| one button |", "| one button, one menu |"))
        code, out = self.commit("pattern", "docs")
        self.assertEqual(code, 1, out)
        self.assertIn("no mapped note has a `Core design:` line", out)

    def test_a_design_change_with_the_line_passes(self):
        self.branch("note/bubble/02")
        self.write("changes/bubble/02-order.md", NOTE_02 + "Core design: adds pattern menu\n")
        self.write("docs/design.md", DESIGN.replace("| one button |", "| one button, one menu |"))
        code, out = self.commit("pattern", "docs", "changes")
        self.assertEqual(code, 0, out)

    def test_a_screens_rewrite_needs_a_prototype_line(self):
        self.branch("note/bubble/01")
        self.write("changes/bubble/01-header.md", NOTE_01 + "Core design: rewrites screens\n")
        self.write("docs/design.md", DESIGN.replace("| Orders | /orders |", "| Orders | /jobs |"))
        code, out = self.commit("redesign", "docs", "changes")
        self.assertEqual(code, 1, out)
        self.assertIn("screens table changed for `Orders`", out)
        self.assertIn("no mapped note has a `Prototype:` line", out)

    def test_a_screens_rewrite_with_a_prototype_passes(self):
        self.branch("note/bubble/01")
        self.write("changes/bubble/01-header.md",
                   NOTE_01 + "Core design: rewrites screens\nPrototype: prototype/jobs.html\n")
        self.write("docs/design.md", DESIGN.replace("| Orders | /orders |", "| Orders | /jobs |"))
        code, out = self.commit("redesign", "docs", "changes")
        self.assertEqual(code, 0, out)

    def test_adding_a_row_is_not_a_rewrite(self):
        self.branch("note/bubble/02")
        self.write("changes/bubble/02-order.md", NOTE_02 + "Core design: adds screen Bills\n")
        self.write("docs/design.md", DESIGN.replace(
            "| Order | /orders/[id] | signed-in |",
            "| Order | /orders/[id] | signed-in |\n| Bills | /bills | signed-in |"))
        code, out = self.commit("bills row", "docs", "changes")
        self.assertEqual(code, 0, out)


# ── Migrations: one number each ──────────────────────────────────────────────

class Migrations(Product):
    def test_two_migrations_with_one_number_are_refused(self):
        self.branch("note/bubble/02")
        self.write("supabase/migrations/0002_bubble.sql", "select 2;\n")
        self.write("supabase/migrations/0002_order.sql", "select 2;\n")
        code, out = self.commit("two", "supabase")
        self.assertEqual(code, 1, out)
        self.assertIn("share the number 0002", out)
        self.assertIn("0002_bubble.sql and supabase/migrations/0002_order.sql", out)

    def test_distinct_numbers_pass(self):
        self.branch("note/bubble/02")
        self.write("supabase/migrations/0002_bubble.sql", "select 2;\n")
        self.write("supabase/migrations/0003_order.sql", "select 3;\n")
        code, out = self.commit("two", "supabase")
        self.assertEqual(code, 0, out)

    def test_a_migration_without_a_number_is_refused(self):
        self.branch("note/bubble/02")
        self.write("supabase/migrations/bubble.sql", "select 2;\n")
        code, out = self.commit("one", "supabase")
        self.assertEqual(code, 1, out)
        self.assertIn("has no leading number", out)

    def test_the_migrations_kind_runs_alone(self):
        self.write("supabase/migrations/0001_b.sql", "select 1;\n")
        self.git("add", "supabase")
        done = subprocess.run([sys.executable, SCRIPT, "migrations", "--tree", str(self.tree)],
                              capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, mod.REFUSED, done.stdout)
        self.assertIn("share the number 0001", done.stdout)


# ── pre-merge-commit ─────────────────────────────────────────────────────────

class Merges(Product):
    def note_branch(self, number, path, text, note_text=None):
        self.git("checkout", "-q", "feature/bubble")
        self.branch(f"note/bubble/{number}")
        if note_text:
            self.write(f"changes/bubble/{number}-{'header' if number == '01' else 'order'}.md", note_text)
        self.write(path, text)
        code, out = self.commit(f"note {number}", "src", "supabase", "tests", "changes")
        self.assertEqual(code, 0, out)

    def setUp(self):
        super().setUp()
        self.branch("feature/bubble")
        self.feature = self.head()

    def test_a_note_merges_into_the_feature_with_no_ff_and_the_dup_check_only(self):
        self.note_branch("02", "src/app/(signed-in)/orders/[id]/page.tsx", "export default () => 2;\n")
        self.git("checkout", "-q", "feature/bubble")
        done = self.git("merge", "--no-ff", "-q", "note/bubble/02", check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("not a merge into main, so no red check", done.stdout + done.stderr)
        self.assertNotEqual(self.head(), self.feature)

    def test_a_merge_bringing_a_duplicate_number_is_refused(self):
        self.write("supabase/migrations/0002_feature.sql", "select 2;\n")
        self.commit("feature migration", "supabase")
        self.git("checkout", "-q", "-b", "note/bubble/02", self.feature)
        self.write("supabase/migrations/0002_note.sql", "select 2;\n")
        code, out = self.commit("note migration", "supabase")
        self.assertEqual(code, 0, out)
        self.git("checkout", "-q", "feature/bubble")
        before = self.head()
        done = self.git("merge", "--no-ff", "note/bubble/02", check=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("share the number 0002", done.stdout + done.stderr)
        self.assertEqual(self.head(), before)

    def test_a_no_ff_merge_into_main_runs_the_red_check_and_passes_when_the_tests_are_red(self):
        self.write("src/lib/money.ts", "export const money = 2;\n")
        self.write("changes/bubble/03-money.md", "# 03 Money\n\nScreens: none\nRisk: none\n\n## Tests\n\n- `tests/money.test.ts`\n")
        self.write("tests/money.test.ts", 'it("counts money", () => {});\n')
        code, out = self.commit("money", "src", "tests", "changes")
        self.assertEqual(code, 0, out)
        self.git("checkout", "-q", "main")
        main = self.head()
        done = self.git("merge", "feature/bubble", check=False)  # branch.main.mergeoptions=--no-ff
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = done.stdout + done.stderr
        self.assertIn("running the red check against main", text)
        self.assertIn("red check passed", text)
        self.assertNotEqual(self.head(), main)
        parents = self.git("log", "-1", "--format=%P").stdout.split()
        self.assertEqual(len(parents), 2, "a merge commit, not a fast-forward")

    def test_a_merge_into_main_whose_new_test_passes_on_main_is_refused(self):
        self.write("changes/bubble/03-money.md", "# 03 Money\n\nScreens: none\nRisk: none\n\n## Tests\n\n- `tests/money.test.ts`\n")
        self.write("tests/money.test.ts", 'it("counts money", () => {});\n')
        code, out = self.commit("money", "tests", "changes")
        self.assertEqual(code, 0, out)
        self.git("checkout", "-q", "main")
        main = self.head()
        done = self.git("merge", "feature/bubble", check=False, env={"FAKE_STATUS": "counts money=passed"})
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("did not fail on the code from before", done.stdout + done.stderr)
        self.assertEqual(self.head(), main)
        self.git("merge", "--abort", check=False)

    def test_a_conflicted_merge_concluded_by_commit_runs_the_merge_checks(self):
        self.write("README.md", "# feature\n")
        self.commit("feature readme", "README.md")
        self.git("checkout", "-q", "main")
        self.write("README.md", "# main\n")
        self.commit("main readme", "README.md")
        done = self.git("merge", "feature/bubble", check=False)
        self.assertNotEqual(done.returncode, 0)
        self.write("README.md", "# both\n")
        self.write("supabase/migrations/0001_dup.sql", "select 1;\n")
        self.git("add", "README.md", "supabase")
        done = self.git("commit", "-qm", "conclude", check=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("share the number 0001", done.stdout + done.stderr)
        self.assertNotIn("names no note", done.stdout + done.stderr)


# ── pre-push ─────────────────────────────────────────────────────────────────

class Pushes(Product):
    def setUp(self):
        super().setUp()
        self.remote = pathlib.Path(self.tmp.name) / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True, env=self.env)
        self.git("remote", "add", "origin", str(self.remote))
        self.record = pathlib.Path(self.git("rev-parse", "--path-format=absolute",
                                            "--git-common-dir").stdout.strip()) / mod.LAST_APPLIED

    def test_a_push_with_no_record_is_refused(self):
        done = self.git("push", "-q", "origin", "main", check=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("does not exist, so none is known to be applied", done.stderr + done.stdout)

    def test_a_push_whose_migrations_are_all_applied_passes(self):
        self.record.write_text("0001_a.sql\n")
        done = self.git("push", "-q", "origin", "main", check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("every pushed migration is applied", done.stderr + done.stdout)

    def test_a_push_carrying_an_unapplied_migration_is_refused(self):
        self.record.write_text("0001_a.sql\n")
        self.branch("note/bubble/02")
        self.write("supabase/migrations/0002_order.sql", "select 2;\n")
        self.write("tests/order.test.ts", 'it("holds the order", () => {});\n')
        self.commit("migration", "supabase", "tests")
        self.git("checkout", "-q", "main")
        self.git("merge", "note/bubble/02")  # --no-ff from config; the red check passes
        done = self.git("push", "-q", "origin", "main", check=False)
        self.assertNotEqual(done.returncode, 0)
        text = done.stderr + done.stdout
        self.assertIn("1 migration(s) after `0001_a.sql`", text)
        self.assertIn("0002_order.sql", text)
        self.assertIn("run migrate:production, then push", text)

    def test_a_record_naming_a_file_main_lacks_is_refused(self):
        self.record.write_text("0005_elsewhere.sql\n")
        done = self.git("push", "-q", "origin", "main", check=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("names `0005_elsewhere.sql`, which refs/heads/main does not carry",
                      done.stderr + done.stdout)

    def test_a_push_of_another_branch_passes_without_the_record(self):
        self.branch("feature/bubble")
        done = self.git("push", "-q", "origin", "feature/bubble", check=False)
        self.assertEqual(done.returncode, 0, done.stderr)


# ── The hooks' one path line ─────────────────────────────────────────────────

class TheHookFiles(Product):
    def test_each_hook_names_the_script_once_and_refuses_without_it(self):
        for name in ("pre-commit", "pre-merge-commit", "pre-push"):
            text = (HOOKS / name).read_text()
            self.assertEqual(text.count('CHECK="${WORKFLOW_LIB:-$HOME/.claude/skills/workflow/lib}/note_check.py"'), 1, name)
        (pathlib.Path(self.env["HOME"]) / ".claude" / "skills" / "workflow" / "lib").unlink()
        self.write("README.md", "# again\n")
        code, out = self.commit("readme", "README.md")
        self.assertEqual(code, 1, out)
        self.assertIn("is missing, so no commit passes", out)

    def test_prepare_sets_the_two_config_values_and_does_nothing_outside_git(self):
        self.assertEqual(self.git("config", "core.hooksPath").stdout.strip(), ".githooks")
        self.assertEqual(self.git("config", "branch.main.mergeoptions").stdout.strip(), "--no-ff")
        elsewhere = pathlib.Path(self.tmp.name) / "plain"
        shutil.copytree(self.tree / ".githooks", elsewhere / ".githooks")
        done = subprocess.run(["sh", ".githooks/prepare"], cwd=elsewhere, env=self.env,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, "")

    def test_suite_py_accepts_the_installed_hooks_path(self):
        sys.path.insert(0, HERE)
        import suite
        self.assertIsNone(suite.hooks_refusal(self.tree))


if __name__ == "__main__":
    unittest.main()
