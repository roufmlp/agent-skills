#!/usr/bin/env python3
"""Cases for scoped_suite.py, the light road's one suite.

Each case drives the script as a command in a throwaway repository, against a
fake vitest that answers `list` from FAKE_LIST and records every `run`.

    python3 -m unittest test_scoped_suite
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "scoped_suite.py"
sys.path.insert(0, str(HERE))
import run_suite  # noqa: E402  (for `LOCK_ENV` only)

# `list --filesOnly --changed=<since> --json=<path>` writes FAKE_LIST, a comma
# list of repo-relative files, as vitest's JSON, and exits FAKE_LIST_EXIT.
# `list` without `--changed` names every test file the same way, from FAKE_ALL,
# and exits FAKE_ALL_EXIT.
# `run` appends its argv to `argv.jsonl`, writes a report where
# `--coverage.reportsDirectory=` points, prints a FAIL line per FAKE_FAILING
# and exits FAKE_EXIT.
FAKE_VITEST = textwrap.dedent("""\
    import json, os, pathlib, sys
    here = pathlib.Path(__file__).resolve().parent
    args = sys.argv[1:]
    with open(here / "argv.jsonl", "a") as handle:
        handle.write(json.dumps(args) + "\\n")
    if args[0] == "list":
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--json="))
        base = next((a.split("=", 1)[1] for a in args if a.startswith("--changed=")), None)
        key = ("FAKE_ALL" if base is None else "FAKE_LIST"
               if base == os.environ.get("FAKE_SINCE", "HEAD") else "FAKE_RECHECK")
        files = [f for f in os.environ.get(key, "").split(",") if f]
        pathlib.Path(out).write_text(json.dumps(
            [{"file": str(pathlib.Path.cwd() / f)} for f in files]))
        sys.exit(int(os.environ.get(key + "_EXIT", "0")))
    where = next((a.split("=", 1)[1] for a in args
                  if a.startswith("--coverage.reportsDirectory=")), None)
    if where:
        pathlib.Path(where).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(where) / "coverage-final.json").write_text(
            os.environ.get("FAKE_COVERAGE", "{}").replace("<ROOT>", str(pathlib.Path.cwd())))
    for name in filter(None, os.environ.get("FAKE_FAILING", "").split(",")):
        print(f" FAIL  {name} > a suite > a case")
    # FAKE_FLAKY: files that fail in the scoped run and pass in the recheck.
    flaky = [f for f in os.environ.get("FAKE_FLAKY", "").split(",") if f]
    if flaky and "--no-file-parallelism" not in args:
        for name in flaky:
            print(f" FAIL  {name} > a suite > a case")
        sys.exit(1)
    print(" Test Files  2 passed (2)")
    sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
""")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class Repo(unittest.TestCase):

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.scratch.name)
        self.repo = root / "tree"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.ts").write_text("export const a = 1;\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "one")
        self.bin = root / "bin"
        self.bin.mkdir()
        self.vitest = self.bin / "vitest"
        self.vitest.write_text(f"#!{sys.executable}\n{FAKE_VITEST}")
        self.vitest.chmod(0o755)
        self.env = {**os.environ, run_suite.LOCK_ENV: str(root / "suite.lock")}

    def tearDown(self):
        self.scratch.cleanup()

    def scoped(self, *extra, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--vitest", str(self.vitest), *extra],
            cwd=str(self.repo), capture_output=True, text=True,
            env={**self.env, **(env or {})}, timeout=60)

    def argvs(self):
        path = self.bin / "argv.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def runs(self):
        """The scoped runs, not the flake rechecks after a red one."""
        return [argv for argv in self.argvs() if argv[0] == "run"
                and "--no-file-parallelism" not in argv]

    def rechecks(self):
        return [argv for argv in self.argvs() if "--no-file-parallelism" in argv]

    def records(self):
        path = pathlib.Path(git(self.repo, "rev-parse", "--absolute-git-dir")) \
            / "run-suite" / "records.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]


class TheSet(Repo):
    """The perf audit of 2026-09-28, fix 4. Three light-issue reds escaped
    because the scoped run read only the touched files: 181's brief-route,
    which imports a file 181 changed, and 254's design-values and 234c's
    standing-rules, repo-wide checks that import nothing it changed."""

    def test_vitest_names_the_tests_whose_imports_reach_a_change(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.scoped(env={"FAKE_LIST": "tests/documents/brief-route.test.ts"})
        listed = self.argvs()[0]
        self.assertEqual(listed[:2], ["list", "--filesOnly"])
        self.assertIn("--changed=HEAD", listed)
        [run] = self.runs()
        self.assertIn(str(self.repo.resolve() / "tests/documents/brief-route.test.ts"), run)

    def test_the_repo_wide_checks_run_whatever_the_change(self):
        self.scoped()
        [run] = self.runs()
        self.assertIn("tests/build-checks/", run)
        self.assertIn("standing-rules.test.", run)
        self.assertIn("--passWithNoTests", run)

    def test_the_repo_declares_its_own_checks(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "run-isolation.json").write_text(json.dumps(
            {"sweepTests": ["tests/sweeps/", "rules.test."]}))
        self.scoped()
        [run] = self.runs()
        self.assertIn("tests/sweeps/", run)
        self.assertNotIn("tests/build-checks/", run)

    def test_a_declaration_it_cannot_read_is_refused(self):
        (self.repo / ".claude").mkdir()
        for bad in ([], ["tests/", 3], "tests/", [""]):
            with self.subTest(bad=bad):
                (self.repo / ".claude" / "run-isolation.json").write_text(
                    json.dumps({"sweepTests": bad}))
                done = self.scoped()
                self.assertEqual(done.returncode, 3, done.stdout)
                self.assertEqual(self.runs(), [])

    def test_since_widens_the_diff(self):
        self.scoped("--since", "main")
        self.assertIn("--changed=main", self.argvs()[0])

    def test_a_list_that_fails_is_refused_and_nothing_runs(self):
        done = self.scoped(env={"FAKE_LIST_EXIT": "1"})
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.runs(), [])


class TheTreeReaders(Repo):
    """The human's ruling, road A, 2026-09-30. One issue moved two
    sheets that `tests/controls/popup-sheet-changed.test.ts` names by line, and
    another broke `tests/controls/layout/skeleton.test.tsx`, which scans the
    tree. Both list the source tree through a helper and import nothing the
    issue changed, so the import closure missed them and both reached the
    finale red. Every test that lists a directory now joins the scoped run."""

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_files(self):
        [run] = self.runs()
        root = self.repo.resolve()
        return {str(pathlib.Path(arg).relative_to(root)) for arg in run
                if arg.startswith(str(root))}

    def test_a_test_that_lists_the_tree_through_a_helper_joins(self):
        self.write("tests/build-checks/walk.ts",
                   'import { readdirSync } from "node:fs";\n'
                   "export const sourceFiles = (d: string) => readdirSync(d);\n")
        self.write("tests/controls/sheet.test.ts",
                   'import { sourceFiles } from "../build-checks/walk";\n')
        self.write("tests/plain.test.ts", 'import { a } from "../a";\n')
        done = self.scoped(env={"FAKE_ALL": "tests/controls/sheet.test.ts,tests/plain.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.run_files(), {"tests/controls/sheet.test.ts"})
        self.assertEqual(self.records()[-1]["tree_readers"], ["tests/controls/sheet.test.ts"])

    def test_a_test_that_lists_a_directory_itself_joins(self):
        self.write("tests/tree.test.ts",
                   'import fs from "node:fs";\nconst names = fs.readdir(".", () => {});\n')
        self.scoped(env={"FAKE_ALL": "tests/tree.test.ts"})
        self.assertEqual(self.run_files(), {"tests/tree.test.ts"})

    def test_the_walk_follows_the_repo_alias_and_a_js_specifier(self):
        self.write("tsconfig.json", json.dumps(
            {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}))
        self.write("src/lib/scan.ts", 'export { globSync } from "node:fs";\n')
        self.write("src/lib/index.ts", 'export * from "./scan.js";\n')
        self.write("tests/alias.test.ts", 'import { globSync } from "@/lib";\n')
        self.scoped(env={"FAKE_ALL": "tests/alias.test.ts"})
        self.assertEqual(self.run_files(), {"tests/alias.test.ts"})

    def test_a_name_that_lists_nothing_does_not_join(self):
        """22 of one project's tests import only `REPO` from
        `tests/scaffold/database-modules.ts`, beside a `sourceFiles` they
        never call. Importing a module that can list is not listing."""
        self.write("tests/scaffold/modules.ts", textwrap.dedent("""\
            import { readdirSync } from "node:fs";
            export const REPO = "/repo/";
            export function sourceFiles(dir: string): string[] {
              return readdirSync(dir);
            }
            export function modulesUnder(dir: string) {
              return sourceFiles(dir).map((file) => ({ file }));
            }
            """))
        self.write("tests/db.test.ts", 'import { REPO } from "./scaffold/modules";\n')
        self.write("tests/walks.test.ts", textwrap.dedent("""\
            import {
              REPO,
              modulesUnder,
            } from "./scaffold/modules";
            """))
        self.scoped(env={"FAKE_ALL": "tests/db.test.ts,tests/walks.test.ts"})
        self.assertEqual(self.run_files(), {"tests/walks.test.ts"})

    def test_a_name_reaches_a_listing_through_another_module(self):
        self.write("tests/checks/walk.ts",
                   'import { readdirSync } from "node:fs";\n'
                   "export const sourceFiles = (d: string) => readdirSync(d);\n")
        self.write("tests/checks/scan.ts",
                   'import { sourceFiles as files } from "./walk";\n'
                   "export const RULE = 1;\n"
                   "export function literalsIn(root: string) {\n"
                   "  return files(root);\n}\n")
        self.write("tests/checks/index.ts",
                   'export * from "./scan";\nexport { sourceFiles as walk } from "./walk";\n')
        self.write("tests/uses-scan.test.ts", 'import { literalsIn } from "./checks/scan";\n')
        self.write("tests/uses-rule.test.ts", 'import { RULE } from "./checks/scan";\n')
        self.write("tests/via-star.test.ts", 'import { literalsIn } from "./checks";\n')
        self.write("tests/via-rename.test.ts", 'import { walk } from "./checks";\n')
        self.write("tests/via-namespace.test.ts", 'import * as scan from "./checks/scan";\n')
        names = ["uses-scan", "uses-rule", "via-star", "via-rename", "via-namespace"]
        self.scoped(env={"FAKE_ALL": ",".join(f"tests/{n}.test.ts" for n in names)})
        self.assertEqual(self.run_files(), {f"tests/{n}.test.ts" for n in names
                                            if n != "uses-rule"})

    def test_a_name_spread_into_a_value_is_a_use(self):
        """The human's ruling, road A2, 2026-10-07. One issue committed green
        on the scoped suite with `tests/documents/route-tracing.test.ts` red. It imports `MODULES` from
        `tests/scaffold/module-imports.ts`, declared as
        `[...sourceFiles("src"), ...sourceFiles("scripts")]`, and the walk
        read the spread `...sourceFiles` as the property `.sourceFiles`. A
        property of another object stays no use."""
        self.write("tests/scaffold/module-imports.ts", textwrap.dedent("""\
            import { readdirSync } from "node:fs";
            export function sourceFiles(dir: string): string[] {
              return readdirSync(dir);
            }
            export function paperFiles(dir: string): string[] {
              return readdirSync(dir);
            }
            export const MODULES = [...sourceFiles("src"), ...sourceFiles("scripts")].map(
              (file) => ({ file }),
            );
            const other = globalThis as never;
            export const NAMES = [other.paperFiles, other?.paperFiles];
            """))
        self.write("tests/documents/route-tracing.test.ts",
                   'import { MODULES } from "../scaffold/module-imports";\n')
        self.write("tests/names.test.ts",
                   'import { NAMES } from "./scaffold/module-imports";\n')
        self.scoped(env={"FAKE_ALL": "tests/documents/route-tracing.test.ts,"
                                     "tests/names.test.ts"})
        self.assertEqual(self.run_files(), {"tests/documents/route-tracing.test.ts"})

    def test_comments_template_bodies_and_types_are_not_imports_or_uses(self):
        """`tests/scaffold/module-imports.ts` quotes `import("./rights")` in
        its comments, and a helper can hold fixture code in a template
        string at column 0. Neither is an import. A type has no runtime."""
        self.write("tests/helpers/walk.ts", textwrap.dedent("""\
            import { readdirSync } from "node:fs";
            // `import("./gone").then((r) => r.permit)` never produces a name.
            /* require("./gone") */
            export interface Walked { file: string }
            export const FIXTURE = `
            import { gone } from "./gone";
            `;
            const cell = /^`([^`\\s/]+)`$/.exec("x"), half = 4 / 2 / 1;
            export const quoted = ['await import("./gone")', "sourceFiles"];
            export function sourceFiles(dir: string): Walked[] {
              return readdirSync(dir).map((file) => ({ file }));
            }
            """))
        self.write("tests/fixture.test.ts", 'import { FIXTURE } from "./helpers/walk";\n')
        self.write("tests/quoted.test.ts",
                   'import { quoted } from "./helpers/walk";\n'
                   "const text = 'await import(\"./gone\")';\n")
        self.write("tests/typed.test.ts", 'import type { Walked } from "./helpers/walk";\n')
        self.scoped(env={"FAKE_ALL": "tests/fixture.test.ts,tests/typed.test.ts,"
                                     "tests/quoted.test.ts"})
        self.assertEqual(self.run_files(), set())

    def test_a_file_the_walk_cannot_read_to_its_end_joins(self):
        self.write("tests/helpers/open.ts", "export const A = 1;\nexport const B = `\n")
        self.write("tests/open.test.ts", 'import { A } from "./helpers/open";\n')
        done = self.scoped(env={"FAKE_ALL": "tests/open.test.ts"})
        self.assertEqual(self.run_files(), {"tests/open.test.ts"})
        self.assertIn("tests/helpers/open.ts", done.stdout)

    def test_a_cycle_of_imports_hides_no_reader(self):
        self.write("tests/lib/a.ts", 'import "./b";\nimport "./c";\n')
        self.write("tests/lib/b.ts", 'import "./a";\n')
        self.write("tests/lib/c.ts", 'import { opendirSync } from "node:fs";\n')
        self.write("tests/one.test.ts", 'import "./lib/a";\n')
        self.write("tests/two.test.ts", 'import "./lib/b";\n')
        self.scoped(env={"FAKE_ALL": "tests/one.test.ts,tests/two.test.ts"})
        self.assertEqual(self.run_files(), {"tests/one.test.ts", "tests/two.test.ts"})

    def test_a_test_with_an_import_it_cannot_place_joins(self):
        """A walk that cannot follow an import cannot say the test lists
        nothing, so the test runs."""
        self.write("tests/lost.test.ts", 'import { x } from "./gone";\n')
        self.write("tests/unknown.test.ts", 'import { y } from "~lib/y";\n')
        done = self.scoped(env={"FAKE_ALL": "tests/lost.test.ts,tests/unknown.test.ts"})
        self.assertEqual(self.run_files(), {"tests/lost.test.ts", "tests/unknown.test.ts"})
        self.assertIn("tests/lost.test.ts", done.stdout)

    def test_a_reader_the_checks_already_run_is_not_named_twice(self):
        self.write("tests/build-checks/nul.test.ts",
                   'import { readdirSync } from "node:fs";\n')
        self.scoped(env={"FAKE_ALL": "tests/build-checks/nul.test.ts"})
        self.assertEqual(self.run_files(), set())
        self.assertEqual(self.records()[-1]["tree_readers"], [])

    def test_a_list_of_every_test_that_fails_is_refused_and_nothing_runs(self):
        done = self.scoped(env={"FAKE_ALL_EXIT": "1"})
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(self.runs(), [])


class TheNamingTests(TheTreeReaders):
    """The human's ruling, 2026-10-01. One issue changed
    `src/controls/picker/picker.tsx`, and `tests/bills/bill-form-invariants.test.ts`
    reads that file as text by its path. Neither the import closure nor the
    tree-reader walk named it, so it rode red through the next two issues to
    the finale. Every test whose text holds a changed file's path now joins."""

    PICKER = "src/controls/picker/picker.tsx"
    INVARIANTS = "tests/bills/bill-form-invariants.test.ts"

    def setUp(self):
        super().setUp()
        self.write(self.PICKER, "export const Picker = 1;\n")
        self.write(self.INVARIANTS,
                   'import { readFileSync } from "node:fs";\n'
                   "const codeOf = (p: string) => readFileSync(p, 'utf8');\n"
                   f'codeOf("{self.PICKER}");\n')
        self.write("tests/other.test.ts", 'codeOf("src/controls/picker/compact.tsx");\n')
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "picker")

    def every(self, *more):
        return {"FAKE_ALL": ",".join([self.INVARIANTS, "tests/other.test.ts", *more])}

    def test_issue_310s_missed_test_joins_on_the_picker_change(self):
        self.write(self.PICKER, "export const Picker = 2;\n")
        done = self.scoped(env=self.every())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.run_files(), {self.INVARIANTS})
        self.assertEqual(self.records()[-1]["named"], [self.INVARIANTS])
        self.assertIn(self.INVARIANTS, done.stdout)

    def test_a_test_naming_an_unchanged_file_does_not_join(self):
        self.write("a.ts", "export const a = 3;\n")
        self.scoped(env=self.every())
        self.assertEqual(self.run_files(), set())
        self.assertEqual(self.records()[-1]["named"], [])

    def test_run_state_and_changed_tests_are_not_sources(self):
        self.write(".scratch/run.md", "x\n")
        self.write("tests/helper.ts", "export const h = 1;\n")
        self.write("tests/names-them.test.ts",
                   'const a = ".scratch/run.md", b = "tests/helper.ts";\n')
        self.scoped(env=self.every("tests/names-them.test.ts"))
        self.assertEqual(self.records()[-1]["named"], [])

    def test_since_takes_committed_changes_too(self):
        self.write(self.PICKER, "export const Picker = 2;\n")
        git(self.repo, "commit", "-qam", "change the picker")
        self.scoped("--since", "HEAD~1", env=self.every())
        self.assertEqual(self.records()[-1]["named"], [self.INVARIANTS])

    def test_a_test_the_closure_already_runs_is_not_named_twice(self):
        self.write(self.PICKER, "export const Picker = 2;\n")
        self.scoped(env={**self.every(), "FAKE_LIST": self.INVARIANTS})
        [run] = self.runs()
        self.assertEqual(run.count(str(self.repo.resolve() / self.INVARIANTS)), 1)
        self.assertEqual(self.records()[-1]["named"], [])

    def test_an_e2e_spec_naming_the_change_is_reported_not_run(self):
        """vitest does not run a Playwright spec, so the scoped run names it
        for the browser harness and records it."""
        self.write("e2e/picker.spec.ts", f'const source = "{self.PICKER}";\n')
        self.write(self.PICKER, "export const Picker = 2;\n")
        done = self.scoped(env=self.every())
        self.assertEqual(self.run_files(), {self.INVARIANTS})
        self.assertEqual(self.records()[-1]["named_e2e"], ["e2e/picker.spec.ts"])
        self.assertIn("e2e/picker.spec.ts", done.stdout)


class TheReading(Repo):

    def test_it_runs_with_coverage_and_records_a_scoped_reading(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        done = self.scoped(env={"FAKE_LIST": "a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        [run] = self.runs()
        self.assertIn("--coverage.enabled", run)
        record = self.records()[-1]
        self.assertEqual(record["stage"], "scoped")
        self.assertEqual(record["files"], ["a.test.ts"])
        self.assertTrue(pathlib.Path(record["coverage"]).exists())
        self.assertEqual(record["tree"], run_suite.tree_hash(self.repo))
        self.assertIn(f"Coverage report: {record['coverage']}", done.stdout)

    def test_a_red_run_passes_its_exit_and_names_its_files(self):
        done = self.scoped(env={"FAKE_EXIT": "1",
                                "FAKE_FAILING": "tests/build-checks/design-values.test.ts"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("tests/build-checks/design-values.test.ts", done.stdout)
        self.assertEqual(self.records()[-1]["failing"],
                         ["tests/build-checks/design-values.test.ts"])

    def test_a_second_run_on_a_green_tree_is_refused(self):
        self.scoped()
        done = self.scoped()
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertEqual(len(self.runs()), 1)

    def test_a_second_run_after_a_red_one_runs(self):
        self.scoped(env={"FAKE_EXIT": "1"})
        self.scoped()
        self.assertEqual(len(self.runs()), 2)

    def test_the_harness_runs_when_the_diff_touches_its_paths(self):
        counter = pathlib.Path(self.scratch.name) / "harness"
        harness = pathlib.Path(self.scratch.name) / "harness.py"
        harness.write_text("import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('ran')\n")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "run-isolation.json").write_text(json.dumps(
            {"harnessSuite": {"command": f"{sys.executable} {harness} {counter}",
                              "requiredWhen": ["scripts/**"]}}))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "contract")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "seed.mjs").write_text("x\n")
        done = self.scoped()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertTrue(counter.exists())
        self.assertTrue(self.records()[-1]["harness"]["run"])


def entry(path, hits):
    """An istanbul file entry with one statement per hit count."""
    return {"path": path,
            "statementMap": {str(i): {"start": {"line": i + 1, "column": 0},
                                      "end": {"line": i + 1, "column": 1}}
                             for i in range(len(hits))},
            "fnMap": {}, "branchMap": {}, "s": {str(i): h for i, h in enumerate(hits)},
            "f": {}, "b": {}}


class TheRecheck(Repo):
    """The human, 2026-10-05: make the implementers fast. On two runs
    a light implementer's first scoped reading found one to
    six failing files, and the whole 260-to-470-file set ran again, about four
    minutes, to confirm the fix. After a red reading the next run reads only
    what the fix can move: the failing files, every test whose imports reach a
    file changed since the red tree, the tree readers and the checks."""

    FIRST = "tests/one.test.ts,tests/two.test.ts,tests/three.test.ts"

    def setUp(self):
        super().setUp()
        (self.repo / "tests").mkdir()
        for name in ("one", "two", "three", "four"):
            (self.repo / "tests" / f"{name}.test.ts").write_text("test('x', () => {});\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "tests")

    def red_then_fix(self, fix="fix.ts", **second):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.scoped(env={"FAKE_LIST": self.FIRST, "FAKE_EXIT": "1",
                         "FAKE_FAILING": "tests/two.test.ts",
                         "FAKE_COVERAGE": second.pop("first_coverage", "{}")})
        (self.repo / fix).write_text("export const fixed = true;\n")
        return self.scoped(env={"FAKE_LIST": self.FIRST + ",tests/four.test.ts",
                                "FAKE_ALL": self.FIRST + ",tests/four.test.ts",
                                "FAKE_RECHECK": "tests/four.test.ts", **second})

    def ran(self, argv):
        return [pathlib.Path(word).resolve().relative_to(self.repo.resolve()).as_posix()
                for word in argv
                if word.endswith(".test.ts") and pathlib.Path(word).is_absolute()]

    def test_a_run_after_a_red_one_reads_only_what_the_fix_can_move(self):
        done = self.red_then_fix()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(sorted(self.ran(self.runs()[-1])),
                         ["tests/four.test.ts", "tests/two.test.ts"])
        self.assertIn("recheck", done.stdout)

    def test_the_recheck_records_the_whole_set_and_its_base(self):
        self.red_then_fix()
        first, second = self.records()[-2:]
        self.assertEqual(second["recheck_of"], first["tree"])
        self.assertIn("fix.ts", second["delta"])
        self.assertEqual(second["files"], self.FIRST.split(",") + ["tests/four.test.ts"])
        self.assertEqual(sorted(second["ran"]), ["tests/four.test.ts", "tests/two.test.ts"])

    def test_a_green_recheck_lets_a_light_issue_commit(self):
        import scoped_suite
        bin_dir = self.repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "vitest").write_text("")
        (self.repo / ".gitignore").write_text("node_modules/\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-q", "-m", "ignore node_modules")
        self.red_then_fix()
        self.assertIsNone(scoped_suite.light_commit_refusal(self.repo, "light"))

    def test_a_red_recheck_stays_red(self):
        done = self.red_then_fix(FAKE_EXIT="1", FAKE_FAILING="tests/two.test.ts")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.records()[-1]["exit"], 1)

    def test_coverage_keeps_the_unchanged_files_and_takes_the_changed_ones_fresh(self):
        old = {"<ROOT>/kept.ts": entry("<ROOT>/kept.ts", [1, 0]),
               "<ROOT>/fix.ts": entry("<ROOT>/fix.ts", [5])}
        new = {"<ROOT>/kept.ts": entry("<ROOT>/kept.ts", [0, 2]),
               "<ROOT>/fix.ts": entry("<ROOT>/fix.ts", [0, 3])}
        self.red_then_fix(first_coverage=json.dumps(old), FAKE_COVERAGE=json.dumps(new))
        report = json.loads(pathlib.Path(self.records()[-1]["coverage"]).read_text())
        root = str(self.repo.resolve())
        self.assertEqual(report[f"{root}/kept.ts"]["s"], {"0": 1, "1": 2})
        self.assertEqual(report[f"{root}/fix.ts"]["s"], {"0": 0, "1": 3})

    def test_the_change_is_measured_from_the_red_tree_not_from_head(self):
        """vitest adds the work not yet committed to any `--changed` base, so
        against the real HEAD it would name the whole closure again. Driven on
        one project: 165 of 168 files ran before this, 1 after."""
        import scoped_suite
        git_vitest = pathlib.Path(self.scratch.name) / "git-vitest"
        git_vitest.write_text(f"#!{sys.executable}\n" + textwrap.dedent("""\
            import json, pathlib, subprocess, sys
            out = next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--json="))
            seen = subprocess.run(["git", "ls-files", "--other", "--modified",
                                   "--exclude-standard"], capture_output=True,
                                  text=True, check=True).stdout.split()
            pathlib.Path(out).write_text(json.dumps(
                [{"file": str(pathlib.Path.cwd() / f)} for f in seen
                 if f.endswith(".test.ts")]))
            """))
        git_vitest.chmod(0o755)
        (self.repo / "tests" / "one.test.ts").write_text("changed before the red reading\n")
        red = run_suite.tree_hash(self.repo)
        (self.repo / "tests" / "two.test.ts").write_text("changed by the fix\n")
        self.assertEqual(scoped_suite.reached_since([str(git_vitest)], self.repo.resolve(), red),
                         ["tests/two.test.ts"])
        self.assertEqual(git(self.repo, "status", "--short"),
                         "M tests/one.test.ts\n M tests/two.test.ts")

    def test_a_change_to_a_rerun_trigger_reads_the_whole_set(self):
        done = self.red_then_fix(fix="package.json")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.ran(self.runs()[-1])), 4)
        self.assertNotIn("recheck_of", self.records()[-1])

    def test_a_red_reading_that_names_no_failing_file_reads_the_whole_set(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.scoped(env={"FAKE_LIST": self.FIRST, "FAKE_EXIT": "1"})
        (self.repo / "fix.ts").write_text("x\n")
        self.scoped(env={"FAKE_LIST": self.FIRST, "FAKE_RECHECK": ""})
        self.assertEqual(len(self.ran(self.runs()[-1])), 3)

    def test_a_failing_file_vitest_no_longer_lists_reads_the_whole_set(self):
        """A harness file, or a test the fix deleted: nothing proves the rest."""
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        self.scoped(env={"FAKE_LIST": self.FIRST, "FAKE_EXIT": "1",
                         "FAKE_FAILING": "tests/harness/lease.test.ts"})
        (self.repo / "fix.ts").write_text("x\n")
        self.scoped(env={"FAKE_LIST": self.FIRST, "FAKE_ALL": self.FIRST,
                         "FAKE_RECHECK": ""})
        self.assertEqual(len(self.ran(self.runs()[-1])), 3)


class TheFlakeRecheck(Repo):
    """A red scoped run rechecks its failing files alone, as `run_suite.py`
    does. One issue re-ran a 462-file scoped suite, 4.7
    minutes, after `regenerate-route` flaked in it on 2026-10-06."""

    def ledger(self):
        path = self.repo / ".git" / run_suite.FLAKES
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_a_file_that_passes_alone_makes_the_scoped_reading_green(self):
        done = self.scoped(env={"FAKE_FLAKY": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("FLAKY: tests/a.test.ts", done.stdout)
        [again] = self.rechecks()
        self.assertIn("tests/a.test.ts", again)
        self.assertFalse(any(a.startswith("--coverage") for a in again))
        record = self.records()[-1]
        self.assertEqual((record["exit"], record["suite_exit"], record["failing"],
                          record["flaky"]), (0, 1, [], ["tests/a.test.ts"]))
        self.assertEqual([e["stage"] for e in self.ledger()], ["scoped"])

    def test_a_file_that_fails_alone_too_stays_red(self):
        done = self.scoped(env={"FAKE_EXIT": "1", "FAKE_FAILING": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(len(self.rechecks()), 1)
        self.assertEqual(self.records()[-1]["failing"], ["tests/a.test.ts"])
        self.assertEqual(self.ledger(), [])


class TheWideChange(Repo):
    """One issue reached 462 of about 716 test files: its
    scoped suites took 4.1 to 4.7 minutes, as long as a whole suite. A final
    spawn asks `--whole-if-wide` and goes straight to the whole suite."""

    ALL = "tests/a.test.ts,tests/b.test.ts,tests/c.test.ts,tests/d.test.ts"

    def setUp(self):
        super().setUp()
        (self.repo / "tests").mkdir()
        for name in self.ALL.split(","):
            (self.repo / name).write_text("export {};\n")

    def test_a_change_reaching_more_than_half_runs_nothing_and_says_wide(self):
        done = self.scoped("--whole-if-wide", env={
            "FAKE_ALL": self.ALL, "FAKE_LIST": "tests/a.test.ts,tests/b.test.ts,tests/c.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("WIDE", done.stdout)
        self.assertIn("run_suite.py", done.stdout)
        self.assertEqual(self.runs(), [])
        record = self.records()[-1]
        self.assertEqual((record["stage"], record["exit"], record["wide"]),
                         ("scoped", None, True))
        self.assertEqual(record["tree"], run_suite.tree_hash(self.repo))

    def test_without_the_flag_a_wide_change_still_runs(self):
        done = self.scoped(env={
            "FAKE_ALL": self.ALL, "FAKE_LIST": "tests/a.test.ts,tests/b.test.ts,tests/c.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.runs()), 1)

    def test_a_narrow_change_runs_even_with_the_flag(self):
        done = self.scoped("--whole-if-wide", env={
            "FAKE_ALL": self.ALL, "FAKE_LIST": "tests/a.test.ts"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(self.runs()), 1)
        self.assertNotIn("wide", self.records()[-1])

    def test_a_wide_record_is_no_green_for_a_light_commit(self):
        self.scoped("--whole-if-wide", env={
            "FAKE_ALL": self.ALL, "FAKE_LIST": "tests/a.test.ts,tests/b.test.ts,tests/c.test.ts"})
        (self.repo / "node_modules" / ".bin").mkdir(parents=True)
        (self.repo / "node_modules" / ".bin" / "vitest").write_text("")
        sys.path.insert(0, str(HERE))
        import scoped_suite
        self.assertIsNotNone(scoped_suite.light_commit_refusal(self.repo, "light"))


class TheLightCommit(Repo):
    """The perf audit of 2026-09-28, fix 4. The runner's commit of a light
    issue waits for a green scoped reading of the tree it commits. A commit
    hook, where the reader has one, calls this at every issue's commit; this
    pack does not ship that hook."""

    def setUp(self):
        super().setUp()
        bin_dir = self.repo / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "vitest").write_text("")
        (self.repo / ".gitignore").write_text("node_modules/\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "ignore node_modules")

    def refusal(self, level="light"):
        import scoped_suite
        return scoped_suite.light_commit_refusal(self.repo, level)

    def test_a_tree_with_no_vitest_is_not_judged(self):
        """The skills repository runs light issues on Python suites. The
        scoped road is vitest's, so a tree without it keeps its old road."""
        (self.repo / "node_modules" / ".bin" / "vitest").unlink()
        self.assertIsNone(self.refusal())

    def test_with_no_scoped_reading_it_refuses_and_names_the_road(self):
        why = self.refusal()
        self.assertIn("scoped_suite.py", why)

    def test_a_green_reading_of_this_tree_passes(self):
        self.scoped()
        self.assertIsNone(self.refusal())

    def test_a_red_reading_refuses_and_names_its_files(self):
        self.scoped(env={"FAKE_EXIT": "1", "FAKE_FAILING": "tests/x.test.ts"})
        self.assertIn("tests/x.test.ts", self.refusal())

    def test_a_reading_of_an_older_tree_refuses(self):
        self.scoped()
        (self.repo / "a.ts").write_text("export const a = 9;\n")
        self.assertIn("scoped_suite.py", self.refusal())

    def test_run_state_written_after_the_reading_does_not_matter(self):
        self.scoped()
        (self.repo / ".scratch" / "feat").mkdir(parents=True)
        (self.repo / ".scratch" / "feat" / "run.md").write_text("committed\n")
        self.assertIsNone(self.refusal())

    def test_a_full_issue_is_not_judged_here(self):
        self.assertIsNone(self.refusal("full"))


if __name__ == "__main__":
    unittest.main()
