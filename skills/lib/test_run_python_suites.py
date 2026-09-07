#!/usr/bin/env python3
"""Drill for run_python_suites.py, the refusal of the silent-suite class.

The corpus is a tree of small test files, each written to one of the shapes the
grader must tell apart: a suite that runs what it defines, a suite that defines
checks and has no way to reach them, a suite that reaches only some of them, and
a hand-rolled runner that defines no `test_` function at all.

    python3 test_run_python_suites.py
"""

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_python_suites", os.path.join(HERE, "run_python_suites.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DefinedTests(unittest.TestCase):
    """What counts as a check this file promises to run."""

    def test_a_module_level_function_counts(self):
        self.assertEqual(["test_a"], mod.defined_tests("def test_a():\n    pass\n"))

    def test_a_method_on_a_class_counts_under_its_class_name(self):
        src = "class T(unittest.TestCase):\n    def test_a(self):\n        pass\n"
        self.assertEqual(["T.test_a"], mod.defined_tests(src))

    def test_a_helper_that_is_not_a_test_does_not_count(self):
        src = "def write(x):\n    pass\n\n\ndef testify(x):\n    pass\n"
        self.assertEqual([], mod.defined_tests(src))

    def test_the_prefix_is_test_underscore_and_not_bare_test(self):
        # `testify` above shares the first four letters. The unittest loader
        # matches `test` bare, but every file in these two repositories writes
        # `def test_`, and the looser prefix would count helpers as checks.
        self.assertEqual([], mod.defined_tests("def tests_helper():\n    pass\n"))

    def test_a_closure_inside_another_function_does_not_count(self):
        # A check cannot be nested inside a helper and still be collected, so
        # counting one would make the defined total unreachable by design.
        src = "def helper():\n    def test_inner():\n        pass\n    return test_inner\n"
        self.assertEqual([], mod.defined_tests(src))

    def test_a_decorated_test_counts(self):
        src = ("import unittest\n\n\n@unittest.skip('x')\n"
               "def test_a():\n    pass\n")
        self.assertEqual(["test_a"], mod.defined_tests(src))

    def test_an_async_test_counts(self):
        self.assertEqual(["test_a"], mod.defined_tests("async def test_a():\n    pass\n"))

    def test_two_classes_may_carry_the_same_method_name(self):
        src = ("class A(unittest.TestCase):\n    def test_x(self):\n        pass\n\n\n"
               "class B(unittest.TestCase):\n    def test_x(self):\n        pass\n")
        self.assertEqual(["A.test_x", "B.test_x"], mod.defined_tests(src))

    def test_a_file_that_will_not_parse_is_not_read_as_empty(self):
        # A syntax error yields no names, and reading that as "defines nothing"
        # is the vacuous pass this whole script exists to refuse.
        with self.assertRaises(SyntaxError):
            mod.defined_tests("def test_a(:\n")

    def test_the_parse_names_the_file_it_was_reading(self):
        # Both trees hold files whose docstrings carry a `\\s`, and the compiler
        # warns on them. Named, the warning says which file to open; unnamed it
        # reads `<unknown>:124`, which sent a reader looking through 61 files.
        with self.assertRaises(SyntaxError) as caught:
            mod.defined_tests("def test_a(:\n", filename="a/test_a.py")
        self.assertEqual("a/test_a.py", caught.exception.filename)


class EntryPoint(unittest.TestCase):
    """Whether `python3 <file>` has anything to reach."""

    def test_the_standard_block_is_found(self):
        self.assertTrue(mod.has_entry_point(
            'if __name__ == "__main__":\n    unittest.main()\n'))

    def test_single_quotes_are_the_same_block(self):
        self.assertTrue(mod.has_entry_point(
            "if __name__ == '__main__':\n    unittest.main()\n"))

    def test_the_operands_may_be_written_either_way_round(self):
        self.assertTrue(mod.has_entry_point(
            'if "__main__" == __name__:\n    unittest.main()\n'))

    def test_a_file_with_no_block_has_no_entry_point(self):
        self.assertFalse(mod.has_entry_point("def test_a():\n    pass\n"))

    def test_a_block_nested_inside_a_function_is_not_an_entry_point(self):
        # Indented, it runs only when that function is called, and nothing
        # calls it. This is the dead-runner shape wearing the right words.
        src = ('def helper():\n    if __name__ == "__main__":\n'
               '        unittest.main()\n')
        self.assertFalse(mod.has_entry_point(src))

    def test_a_comparison_against_something_else_is_not_an_entry_point(self):
        self.assertFalse(mod.has_entry_point(
            'if __name__ == "__test__":\n    unittest.main()\n'))


class ExecutedCount(unittest.TestCase):
    """The number of checks a run says it executed, read off its own output."""

    def test_the_unittest_summary_is_read(self):
        self.assertEqual(135, mod.executed_count("", "Ran 135 tests in 0.075s\n\nOK\n"))

    def test_one_test_is_written_singular_by_unittest(self):
        self.assertEqual(1, mod.executed_count("", "Ran 1 test in 0.001s\n\nOK\n"))

    def test_the_pytest_summary_is_read(self):
        self.assertEqual(12, mod.executed_count("12 passed in 0.01s\n", ""))

    def test_pytest_skips_are_added_to_the_total(self):
        # A skipped check was collected and reached. It is not a silent check.
        self.assertEqual(12, mod.executed_count("10 passed, 2 skipped in 0.01s\n", ""))

    def test_pytest_failures_are_added_to_the_total(self):
        self.assertEqual(4, mod.executed_count("3 failed, 1 passed in 0.02s\n", ""))

    def test_pytest_errors_and_expected_failures_are_added_to_the_total(self):
        self.assertEqual(6, mod.executed_count(
            "2 passed, 1 xfailed, 1 xpassed, 2 errors in 0.02s\n", ""))

    def test_pytest_saying_no_tests_ran_is_a_readable_zero(self):
        self.assertEqual(0, mod.executed_count("no tests ran in 0.01s\n", ""))

    def test_unittest_saying_no_tests_ran_is_a_readable_zero(self):
        self.assertEqual(0, mod.executed_count("", "Ran 0 tests in 0.000s\n\nNO TESTS RAN\n"))

    def test_output_carrying_no_count_reads_as_unreadable_and_not_as_zero(self):
        # The hand-rolled runner in this directory prints a sentence and no
        # figure. `None` says "not measured"; zero would say "measured, empty".
        self.assertIsNone(mod.executed_count("check_x: all cases passed.\n", ""))

    def test_a_count_is_found_when_other_output_surrounds_it(self):
        self.assertEqual(47, mod.executed_count(
            "", "some chatter\nRan 47 tests in 0.1s\n\nOK\n"))

    def test_the_last_count_wins_when_a_run_prints_more_than_one(self):
        # A file that runs two suites in one process prints two summaries. The
        # grader must not stop at the first and under-read the total.
        self.assertEqual(9, mod.executed_count("", "Ran 4 tests in 0.1s\nRan 9 tests in 0.1s\n"))


class Grade(unittest.TestCase):
    """The verdict on one file, given what it defines and what it reported."""

    def grade(self, path="t/test_a.py", defined=0, entry=True, code=0,
              out="", err=""):
        return mod.grade(path, defined=defined, has_entry=entry,
                         returncode=code, stdout=out, stderr=err)

    def test_a_suite_that_ran_everything_it_defines_passes(self):
        verdict = self.grade(defined=12, out="12 passed in 0.01s\n")
        self.assertTrue(verdict.ok)
        self.assertEqual(12, verdict.executed)

    def test_a_suite_with_no_entry_point_is_refused_by_name(self):
        verdict = self.grade(defined=24, entry=False)
        self.assertFalse(verdict.ok)
        self.assertIn("t/test_a.py", verdict.reason)
        self.assertIn("24", verdict.reason)

    def test_the_no_entry_point_refusal_names_the_repair(self):
        reason = self.grade(defined=24, entry=False).reason
        self.assertIn("__main__", reason)

    def test_a_file_defining_nothing_needs_no_entry_point(self):
        # The hand-rolled runner beside this file is exactly this shape: it
        # defines no `test_` function, carries its checks inside `main()`, and
        # is graded on its exit code alone.
        self.assertTrue(self.grade(defined=0, entry=False).ok)

    def test_a_non_zero_exit_is_refused_whatever_it_ran(self):
        verdict = self.grade(defined=12, code=1, out="11 passed, 1 failed in 0.01s\n")
        self.assertFalse(verdict.ok)
        self.assertIn("exited 1", verdict.reason)

    def test_a_suite_that_reached_fewer_checks_than_it_defines_is_refused(self):
        # The dead-runner-block shape: 135 defined, 79 reached, exit zero.
        verdict = self.grade(defined=135, out="79 passed in 0.1s\n")
        self.assertFalse(verdict.ok)
        self.assertIn("135", verdict.reason)
        self.assertIn("79", verdict.reason)

    def test_a_suite_that_reached_more_than_it_defines_is_not_refused(self):
        # Parametrised cases and methods inherited from a base class both make
        # the executed total exceed the defined one. Neither is a silence.
        self.assertTrue(self.grade(defined=12, out="30 passed in 0.1s\n").ok)

    def test_a_suite_that_defines_checks_and_reports_no_count_is_refused(self):
        verdict = self.grade(defined=12, out="all fine\n")
        self.assertFalse(verdict.ok)
        self.assertIn("no count", verdict.reason.lower())

    def test_a_reported_zero_is_refused_when_checks_are_defined(self):
        verdict = self.grade(defined=12, out="no tests ran in 0.01s\n")
        self.assertFalse(verdict.ok)

    def test_a_file_defining_nothing_and_reporting_nothing_passes(self):
        verdict = self.grade(defined=0, out="check_x: all cases passed.\n")
        self.assertTrue(verdict.ok)
        self.assertIsNone(verdict.executed)

    def test_every_refusal_opens_with_the_refused_word(self):
        for verdict in (self.grade(defined=24, entry=False),
                        self.grade(defined=12, code=1),
                        self.grade(defined=135, out="79 passed in 0.1s\n"),
                        self.grade(defined=12, out="all fine\n")):
            self.assertTrue(verdict.reason.startswith("REFUSED silent-suite:"),
                            verdict.reason)


class OneBadFileDoesNotEndTheWalk(unittest.TestCase):
    """A file the walker cannot run is refused BY NAME, and the walk goes on.

    A traceback out of the middle of the walk exits non-zero, which reads like
    a refusal, and leaves every later file ungraded with nothing saying so.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as handle:
            handle.write(text)
        return os.path.join(self.root, name)

    def test_a_suite_that_hangs_is_refused_rather_than_raised(self):
        path = self.write("test_hang.py",
                          'import time, unittest\n\n\n'
                          'class T(unittest.TestCase):\n'
                          '    def test_a(self):\n        time.sleep(30)\n\n\n'
                          'if __name__ == "__main__":\n    unittest.main()\n')
        verdict = mod.check(path, timeout=1)
        self.assertFalse(verdict.ok)
        self.assertIn("timed out", verdict.reason.lower())
        self.assertIn("test_hang.py", verdict.reason)

    def test_the_hang_refusal_names_the_limit_it_hit(self):
        path = self.write("test_hang2.py",
                          'import time, unittest\n\n\n'
                          'class T(unittest.TestCase):\n'
                          '    def test_a(self):\n        time.sleep(30)\n\n\n'
                          'if __name__ == "__main__":\n    unittest.main()\n')
        self.assertIn("1", mod.check(path, timeout=1).reason)

    def test_a_file_that_cannot_be_read_is_refused_rather_than_raised(self):
        missing = os.path.join(self.root, "test_gone.py")
        verdict = mod.check(missing)
        self.assertFalse(verdict.ok)
        self.assertIn("cannot read", verdict.reason.lower())

    def test_the_walk_grades_the_files_after_a_hanging_one(self):
        self.write("test_a_hang.py",
                   'import time, unittest\n\n\n'
                   'class T(unittest.TestCase):\n'
                   '    def test_a(self):\n        time.sleep(30)\n\n\n'
                   'if __name__ == "__main__":\n    unittest.main()\n')
        self.write("test_b_silent.py", 'def test_a():\n    assert True\n')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mod.main([self.root, "--timeout", "1"])
        printed = out.getvalue() + err.getvalue()
        self.assertEqual(1, code)
        self.assertIn("test_a_hang.py", printed)
        self.assertIn("test_b_silent.py", printed)
        self.assertIn("2 of 2", printed)


class Discover(unittest.TestCase):
    """Which files the walk picks up."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text="pass\n"):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_a_test_file_is_found(self):
        self.write("a/test_one.py")
        self.assertEqual(["a/test_one.py"], self.found())

    def test_a_file_that_is_not_a_test_is_left_alone(self):
        self.write("a/helper.py")
        self.write("a/test_one.py")
        self.assertEqual(["a/test_one.py"], self.found())

    def test_a_cached_copy_is_never_run(self):
        self.write("a/__pycache__/test_one.cpython-314.pyc")
        self.write("a/__pycache__/test_one.py")
        self.assertEqual([], self.found())

    def test_the_walk_is_ordered_so_two_runs_report_alike(self):
        self.write("b/test_two.py")
        self.write("a/test_one.py")
        self.assertEqual(["a/test_one.py", "b/test_two.py"], self.found())

    def test_a_root_that_does_not_exist_is_refused_rather_than_walked_empty(self):
        with self.assertRaises(FileNotFoundError):
            mod.discover([os.path.join(self.root, "nowhere")])

    def found(self):
        return sorted(os.path.relpath(p, self.root)
                      for p in mod.discover([self.root]))


class EndToEnd(unittest.TestCase):
    """The walk, the runs and the exit code, over a real tree."""

    GOOD = ('import unittest\n\n\n'
            'class T(unittest.TestCase):\n'
            '    def test_a(self):\n        self.assertTrue(True)\n\n\n'
            'if __name__ == "__main__":\n    unittest.main()\n')
    SILENT = ('def test_a():\n    assert True\n\n\n'
              'def test_b():\n    assert True\n')
    HANDROLLED = ('def main():\n    print("check_x: all cases passed.")\n'
                  '    return 0\n\n\n'
                  'if __name__ == "__main__":\n    raise SystemExit(main())\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_main(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mod.main([self.root])
        return code, out.getvalue() + err.getvalue()

    def test_a_tree_of_honest_suites_passes(self):
        self.write("test_good.py", self.GOOD)
        self.write("test_hand.py", self.HANDROLLED)
        code, printed = self.run_main()
        self.assertEqual(0, code, printed)

    def test_a_silent_suite_fails_the_walk(self):
        self.write("test_good.py", self.GOOD)
        self.write("test_silent.py", self.SILENT)
        code, printed = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("test_silent.py", printed)
        self.assertNotIn("REFUSED silent-suite: " + os.path.join(self.root, "test_good.py"),
                         printed)

    def test_the_silent_suite_refusal_names_how_many_checks_were_never_run(self):
        self.write("test_silent.py", self.SILENT)
        _, printed = self.run_main()
        self.assertIn("2", printed)

    def test_a_red_suite_fails_the_walk_and_shows_its_own_output(self):
        self.write("test_red.py", self.GOOD.replace("assertTrue(True)",
                                                    "assertTrue(False)"))
        code, printed = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("test_red.py", printed)

    def test_a_tree_holding_no_suite_at_all_is_refused_and_not_called_clean(self):
        # An empty walk reporting a pass is the same vacuous silence in the
        # instrument that runs the suites.
        code, printed = self.run_main()
        self.assertEqual(2, code)
        self.assertIn("REFUSED", printed)

    def test_the_pass_line_carries_the_totals_it_measured(self):
        self.write("test_good.py", self.GOOD)
        _, printed = self.run_main()
        self.assertIn("1 file", printed)

    def test_each_file_runs_in_its_own_directory(self):
        # The suites import sibling modules by relative path, so a run started
        # anywhere else fails on the import rather than on a check.
        os.makedirs(os.path.join(self.root, "sub"))
        with open(os.path.join(self.root, "sub", "sibling.py"), "w") as handle:
            handle.write("VALUE = 7\n")
        self.write("sub/test_sib.py",
                   'import os, sys, unittest\n'
                   'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n'
                   'import sibling\n\n\n'
                   'class T(unittest.TestCase):\n'
                   '    def test_a(self):\n'
                   '        self.assertEqual(7, sibling.VALUE)\n'
                   '        self.assertEqual(os.path.dirname(os.path.abspath(__file__)),\n'
                   '                         os.getcwd())\n\n\n'
                   'if __name__ == "__main__":\n    unittest.main()\n')
        code, printed = self.run_main()
        self.assertEqual(0, code, printed)


if __name__ == "__main__":
    unittest.main()
