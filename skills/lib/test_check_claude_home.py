#!/usr/bin/env python3
"""Drill for check_claude_home.py, and the walk of this repo it performs.

    python3 test_check_claude_home.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_claude_home as mod


class Rooted(unittest.TestCase):
    """Which names carry a climb from `__file__`."""

    def test_a_direct_climb_is_rooted(self):
        self.assertIn("HERE", mod.rooted_names(
            "HERE = Path(__file__).resolve().parent\n"))

    def test_the_os_path_spelling_is_rooted_too(self):
        self.assertIn("HERE", mod.rooted_names(
            "HERE = os.path.dirname(os.path.abspath(__file__))\n"))

    def test_a_name_derived_from_a_rooted_name_is_rooted(self):
        names = mod.rooted_names(
            "HERE = Path(__file__).resolve().parent\nSKILLS = HERE.parent\n")
        self.assertIn("SKILLS", names)

    def test_the_derivation_carries_as_far_as_it_goes(self):
        names = mod.rooted_names("A = Path(__file__).parent\nB = A.parent\n"
                                 "C = B.parent\n")
        self.assertIn("C", names)

    def test_a_home_anchor_is_not_rooted(self):
        names = mod.rooted_names('CLAUDE = Path.home() / ".claude"\n')
        self.assertNotIn("CLAUDE", names)

    def test_an_expanduser_anchor_is_not_rooted(self):
        names = mod.rooted_names('ROOT = os.path.expanduser("~/.claude")\n')
        self.assertNotIn("ROOT", names)

    def test_a_name_bound_inside_a_class_body_is_rooted(self):
        # `test_claim_number.py` held its climb as a class attribute, so a
        # reader that only looked at the module body would have missed it.
        names = mod.rooted_names("HERE = Path(__file__).parent\n\n"
                                 "class T:\n    CLAUDE = HERE.parent.parent\n")
        self.assertIn("CLAUDE", names)


class Refusals(unittest.TestCase):
    """What the checker will not let through."""

    def refuse(self, source):
        return mod.refusals(source, "a/test_x.py")

    def test_a_climb_to_agents_is_refused(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'AGENTS = HERE.parent.parent / "agents"\n')
        self.assertEqual(1, len(found))
        self.assertIn("agents", found[0])

    def test_a_climb_to_hooks_is_refused(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'HOOKS = HERE.parent / "hooks"\n')
        self.assertEqual(1, len(found))

    def test_a_climb_to_settings_json_is_refused(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'CFG = HERE.parent.parent / "settings.json"\n')
        self.assertEqual(1, len(found))

    def test_a_rooted_name_read_back_off_self_is_refused(self):
        # `test_claim_number.py` held its climb as a class attribute and read
        # it back as `self.CLAUDE / "settings.json"`. A reader looking only for
        # bare names passes that.
        found = self.refuse(
            "HERE = Path(__file__).parent\n\n"
            "class T:\n"
            "    CLAUDE = HERE.parent.parent\n\n"
            "    def t(self):\n"
            '        return self.CLAUDE / "settings.json"\n')
        self.assertEqual(1, len(found))

    def test_a_home_anchored_class_attribute_read_off_self_passes(self):
        self.assertEqual([], self.refuse(
            "class T:\n"
            '    CLAUDE = Path.home() / ".claude"\n\n'
            "    def t(self):\n"
            '        return self.CLAUDE / "agents"\n'))

    def test_an_inline_climb_binding_no_name_is_refused(self):
        # `parents[2] / "hooks"` written straight into the expression, which is
        # the shape `correction_brief.py` carried.
        found = self.refuse(
            'HOOK = Path(__file__).resolve().parents[2] / "hooks" / "cap.py"\n')
        self.assertEqual(1, len(found))

    def test_the_refusal_names_the_file_and_the_line(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'AGENTS = HERE.parent / "agents"\n')
        self.assertIn("a/test_x.py", found[0])
        self.assertIn(":2", found[0])

    def test_the_refusal_names_the_repair(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'AGENTS = HERE.parent / "agents"\n')
        self.assertIn("Path.home()", found[0])

    def test_every_refusal_opens_with_the_refused_word(self):
        found = self.refuse("HERE = Path(__file__).parent\n"
                            'AGENTS = HERE.parent / "agents"\n')
        self.assertTrue(found[0].startswith("REFUSED"), found[0])

    def test_a_home_anchored_reach_to_agents_passes(self):
        self.assertEqual([], self.refuse(
            'CLAUDE = Path.home() / ".claude"\nAGENTS = CLAUDE / "agents"\n'))

    def test_a_climb_to_a_directory_inside_this_repo_passes(self):
        self.assertEqual([], self.refuse(
            "HERE = Path(__file__).parent\nSKILLS = HERE.parent\n"
            'LIB = SKILLS / "lib"\n'))

    def test_a_bare_string_naming_the_outside_tree_passes(self):
        # `run_python_suites.py` names `~/.claude/hooks` as a default root.
        # That is an absolute anchor, not a climb, and it is correct.
        self.assertEqual([], self.refuse(
            'ROOTS = (os.path.expanduser("~/.claude/hooks"),)\n'))

    def test_a_file_that_will_not_parse_is_refused_and_not_read_as_clean(self):
        found = self.refuse("def f(:\n")
        self.assertEqual(1, len(found))
        self.assertIn("parse", found[0])


class ThisRepo(unittest.TestCase):
    """The rule, over the checkout this file lives in.

    The point of the whole script. Four files carried this fault and every one
    of them was written beside a comment stating the fact it broke, so the
    comment is not what holds it.
    """

    def test_no_python_file_in_this_checkout_climbs_to_the_outside_tree(self):
        found = mod.walk(mod.REPO)
        self.assertEqual([], found, "\n\n".join(found))

    def test_the_walk_read_something(self):
        # A walk of a mistyped root refuses nothing and looks identical to a
        # clean repo.
        self.assertGreater(mod.count_files(mod.REPO), 20)


if __name__ == "__main__":
    unittest.main()
