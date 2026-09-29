#!/usr/bin/env python3
"""The class-only decider, ruled by the human on 2026-09-25 (queue item
q-971a22-03).

A change to a risk file that only edits styling class names must not lift a
light issue to the full level. An agent may not judge that; this script does,
and it refuses a class edit that can hide, show, block or cover something.
These tests pin the masking comparison, the allowlist of safe class tokens
(road B, ruled 2026-09-25), and the fail-closed answers for everything the
script cannot read.

Run: python3 test_class_only_edit.py
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "class_only_edit.py"
sys.path.insert(0, str(HERE))

import class_only_edit  # noqa: E402

# The email input of one project's `src/app/login/page.tsx`, before and after
# commit 7ae2d84 (issue 230, run batch-971a22). The only change is the removed
# `focus:border-primary`, and the whole issue ran FULL for 105 minutes on it.
LOGIN_BEFORE = '''\
          <input
            id="sign-in-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            className="mt-1 w-full rounded-card border border-line p-3 text-sm text-ink placeholder:text-ink-3 focus:border-primary"
          />
          <button
            type="submit"
            className="mt-4 w-full rounded-card bg-primary p-3 text-sm font-semibold text-card"
          >
            Send me a sign-in link
          </button>
'''
LOGIN_AFTER = LOGIN_BEFORE.replace(" focus:border-primary", "")


def classify(before, after):
    return class_only_edit.classify(before, after)


class ClassOnly(unittest.TestCase):
    def test_issue_230_email_input_is_class_only(self):
        self.assertNotEqual(LOGIN_BEFORE, LOGIN_AFTER)
        self.assertEqual(classify(LOGIN_BEFORE, LOGIN_AFTER), (True, ""))


class Behaviour(unittest.TestCase):
    def assertBehaviour(self, after, *fragments):
        ok, reason = classify(LOGIN_BEFORE, after)
        self.assertFalse(ok, reason)
        for fragment in fragments:
            self.assertIn(fragment, reason)

    def test_a_changed_attribute_is_behaviour_and_names_its_line(self):
        after = LOGIN_BEFORE.replace('type="email"', 'type="text"')
        self.assertBehaviour(after, "line 4", 'type="text"')

    def test_an_added_handler_is_behaviour(self):
        after = LOGIN_BEFORE.replace('            required\n',
                                     '            required\n'
                                     '            onSubmit={send}\n')
        self.assertBehaviour(after, "line 7", "onSubmit={send}")

    def test_changed_text_is_behaviour(self):
        after = LOGIN_BEFORE.replace("Send me a sign-in link", "Sign in")
        self.assertBehaviour(after, "line 14")

    def test_a_class_edit_beside_a_behaviour_edit_is_behaviour(self):
        after = LOGIN_AFTER.replace("required\n", "")
        self.assertBehaviour(after, "line 6")


class UnsafeClasses(unittest.TestCase):
    """A class edit can hide, show, block or cover a control. Each of these is
    a pure class edit that the masking comparison alone would pass."""

    def verdict(self, before_classes, after_classes):
        return verdict(before_classes, after_classes)

    def test_adding_hidden_is_behaviour_and_names_it(self):
        ok, reason = self.verdict("mt-4 p-3", "mt-4 p-3 hidden")
        self.assertFalse(ok)
        self.assertIn("`hidden` added", reason)
        self.assertIn("line 12", reason)

    def test_removing_sr_only_is_behaviour(self):
        ok, reason = self.verdict("sr-only mt-4", "mt-4")
        self.assertFalse(ok)
        self.assertIn("`sr-only` removed", reason)

    def test_a_variant_prefix_does_not_hide_the_token(self):
        ok, reason = self.verdict("mt-4", "mt-4 md:hidden")
        self.assertFalse(ok)
        self.assertIn("`md:hidden` added", reason)

    def test_an_important_mark_does_not_hide_the_token(self):
        for token in ("!hidden", "hidden!", "sm:!hidden"):
            ok, reason = self.verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)
            self.assertIn(f"`{token}` added", reason)

    def test_a_negative_stacking_prefix_is_caught(self):
        ok, reason = self.verdict("mt-4", "mt-4 -z-10")
        self.assertFalse(ok)
        self.assertIn("`-z-10` added", reason)

    def test_prefix_groups_are_caught(self):
        for token in ("z-50", "inset-0", "inset-x-4", "focus:z-10"):
            ok, _reason = self.verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)

    def test_a_safe_class_edit_stays_class_only(self):
        self.assertEqual(self.verdict("mt-4 p-3", "mt-2 p-4 bg-card"),
                         (True, ""))

    def test_an_unchanged_dangerous_class_is_not_a_change(self):
        """`hidden` present on both sides was there before this change."""
        self.assertEqual(self.verdict("hidden mt-4", "hidden mt-2"),
                         (True, ""))

    def test_a_token_the_allowlist_does_not_name_is_behaviour(self):
        """The denylist passed these as lookalikes. The allowlist names none
        of them, so each one is refused and named."""
        for token in ("overflow-hidden", "flex-1", "grid-cols-2", "z", "blocked"):
            ok, reason = self.verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)
            self.assertIn(f"`{token}` added", reason)


class Forms(unittest.TestCase):
    """Every class-string shape the rule names, and the ones it refuses."""

    def test_every_named_form_is_masked(self):
        forms = [
            'className="{}"',
            "className='{}'",
            'className={{"{}"}}',
            "className={{'{}'}}",
            'className={{`{}`}}',
            'className={{ "{}" }}',
            'class="{}"',
        ]
        for form in forms:
            before = "<div " + form.format("mt-4 p-3") + " />\n"
            after = "<div " + form.format("mt-2 p-4") + " />\n"
            self.assertEqual(classify(before, after), (True, ""), form)

    def test_a_dangerous_token_is_caught_in_every_form(self):
        for form in ('className={{`{}`}}', "className='{}'", 'class="{}"'):
            before = "<div " + form.format("mt-4") + " />\n"
            after = "<div " + form.format("mt-4 hidden") + " />\n"
            ok, reason = classify(before, after)
            self.assertFalse(ok, form)
            self.assertIn("`hidden` added", reason)

    def test_a_template_with_an_expression_is_behaviour(self):
        before = "<div className={`mt-4 ${open ? 'a' : 'b'}`} />\n"
        after = "<div className={`mt-2 ${open ? 'a' : 'b'}`} />\n"
        ok, reason = classify(before, after)
        self.assertFalse(ok)
        self.assertIn("class template holding ${}", reason)

    def test_an_unchanged_template_with_an_expression_is_left_alone(self):
        """A file may hold one; only a change to it is unreadable."""
        text = "<div className={`mt-4 ${x}`} />\n"
        before = text + '<p className="mt-1" />\n'
        after = text + '<p className="mt-2" />\n'
        self.assertEqual(classify(before, after), (True, ""))

    def test_a_class_edit_spanning_lines_keeps_true_line_numbers(self):
        before = '<div className={`a\n  b`} />\n<p>one</p>\n'
        after = '<div className={`a\n  c\n  d`} />\n<p>two</p>\n'
        ok, reason = classify(before, after)
        self.assertFalse(ok)
        self.assertIn("line 4", reason)


    def test_a_stray_quote_cannot_mask_code_on_later_lines(self):
        """A quoted class string ends on its own line. Were it allowed to run
        on, the quote in this comment would mask the handler below it."""
        before = '// set className="x\nsubmit(form);\nconst y = "z";\n'
        after = '// set className="x\ndeleteAll(form);\nconst y = "z";\n'
        ok, reason = classify(before, after)
        self.assertFalse(ok)
        self.assertIn("line 2", reason)


IMPORTS = ('import { cn } from "@/lib/utils";\n'
           'import clsx from "clsx";\n'
           'import { twMerge } from "tailwind-merge";\n')


def classify_with_imports(before, after):
    return class_only_edit.classify(IMPORTS + before, IMPORTS + after)


class HelperCalls(unittest.TestCase):
    """The helper is recognised only where the file imports it."""
    def test_a_cn_argument_change_is_class_only(self):
        before = 'const c = cn("mt-4", "p-2");\n'
        after = 'const c = cn("mt-4", "p-3");\n'
        self.assertEqual(classify_with_imports(before, after), (True, ""))

    def test_clsx_and_twmerge_and_single_quotes(self):
        for call in ("clsx", "twMerge"):
            before = f"const c = {call}('mt-4', 'p-3');\n"
            after = f"const c = {call}('mt-2', 'p-3');\n"
            self.assertEqual(classify_with_imports(before, after), (True, ""), call)

    def test_a_literal_after_a_condition_is_not_plain(self):
        before = 'const c = cn("a", open && "b", "c");\n'
        after = 'const c = cn("a", open && "x", "d");\n'
        ok, reason = classify_with_imports(before, after)
        self.assertFalse(ok)
        self.assertIn("line 4", reason)

    def test_plain_arguments_after_a_condition_are_still_masked(self):
        before = 'const c = cn("mt-1", open && "b", "p-1");\n'
        after = 'const c = cn("mt-2", open && "b", "p-2");\n'
        self.assertEqual(classify_with_imports(before, after), (True, ""))

    def test_a_changed_condition_is_behaviour(self):
        before = 'const c = cn("a", open && "b");\n'
        after = 'const c = cn("a", !open && "b");\n'
        self.assertFalse(classify_with_imports(before, after)[0])

    def test_hidden_added_through_cn_is_caught(self):
        before = 'const c = cn("mt-4", "p-3");\n'
        after = 'const c = cn("mt-4 hidden", "p-3");\n'
        ok, reason = classify_with_imports(before, after)
        self.assertFalse(ok)
        self.assertIn("`hidden` added", reason)

    def test_a_similarly_named_function_is_not_a_helper(self):
        before = 'const c = scn("a");\n'
        after = 'const c = scn("b");\n'
        self.assertFalse(classify_with_imports(before, after)[0])

    def test_an_unclosed_call_is_behaviour(self):
        before = 'const c = cn("a", \n'
        after = 'const c = cn("b", \n'
        self.assertFalse(classify_with_imports(before, after)[0])


class ReviewHoles(unittest.TestCase):
    """Fail-open shapes the code review of 2026-09-25 found. Each one was
    judged class-only before the fix while it changed behaviour."""

    def assertNotClassOnly(self, before, after):
        ok, reason = classify(before, after)
        self.assertFalse(ok, (before, after))
        return reason

    def test_html_built_in_a_string_does_not_mask_code(self):
        self.assertNotClassOnly(
            """row = '<td class="' + fmt(total) + '">';\n""",
            """row = '<td class="' + fmt(total * 0) + '">';\n""")
        self.assertNotClassOnly(
            """html += "<td class='" + cls + "'>";\n""",
            """html += "<td class='" + leak(token) + "'>";\n""")

    def test_an_expression_inside_a_quoted_class_string_is_not_masked(self):
        reason = self.assertNotClassOnly(
            'const r = `<td class="${cls}">`;\n',
            'const r = `<td class="${chargeCard(amount)}">`;\n')
        self.assertIn("cannot read", reason)

    def test_bound_class_attributes_are_not_class_strings(self):
        for name in (":class", "v-bind:class", "x-bind:class", "data-class",
                     "@class"):
            self.assertNotClassOnly(f'<b {name}="cls()" />\n',
                                    f'<b {name}="cls(refund())" />\n')

    def test_a_class_pattern_in_a_comment_does_not_mask_code(self):
        self.assertNotClassOnly(
            '/* className="x */ total = a /* " */\n',
            '/* className="x */ total = a * 2 /* " */\n')

    def test_a_class_pattern_in_jsx_text_does_not_mask_text(self):
        self.assertNotClassOnly('<p>class="{price}"</p>\n',
                                '<p>class="{price * 2}"</p>\n')

    def test_an_html_entity_in_a_class_string_is_not_masked(self):
        self.assertNotClassOnly('<b className="mt-4" />\n',
                                '<b className="mt-4 hid&#100;en" />\n')

    def test_arbitrary_properties_and_values_of_listed_classes_are_caught(self):
        for token in ("[display:none]", "md:[visibility:hidden]",
                      "opacity-[0]", "h-[0px]", "max-h-[0]", "scale-y-0",
                      "z-[60]", "inset-[0]"):
            reason = self.assertNotClassOnly(
                '<b className="mt-4" />\n', f'<b className="mt-4 {token}" />\n')
            self.assertIn(f"`{token}` added", reason)

    def test_a_tailwind_data_variant_is_read_and_refused(self):
        """shadcn writes these. The `=` and brackets must not make the string
        unreadable, but the bracketed variant is refused by the allowlist
        ruling of 2026-09-25, and the reason says why."""
        ok, reason = classify(
            '<b className="data-[state=open]:bg-card mt-4" />\n',
            '<b className="data-[state=open]:bg-line mt-4" />\n')
        self.assertFalse(ok)
        self.assertIn("`data-[state=open]:bg-line` added", reason)
        self.assertIn("arbitrary variant", reason)

    def test_a_local_function_named_cn_is_not_the_class_helper(self):
        self.assertNotClassOnly(
            'function cn(code) { return fmt(code); }\nconst p = cn("USD");\n',
            'function cn(code) { return fmt(code); }\nconst p = cn("EUR");\n')

    def test_an_unimported_cn_is_not_the_class_helper(self):
        self.assertNotClassOnly('const p = cn("USD");\n',
                                'const p = cn("EUR");\n')

    def test_an_imported_cn_is_the_class_helper(self):
        head = 'import { cn } from "@/lib/utils";\n'
        self.assertEqual(classify(head + 'const c = cn("mt-4", "p-2");\n',
                                  head + 'const c = cn("mt-4", "p-3");\n'),
                         (True, ""))


class ReviewHolesSecondPass(unittest.TestCase):
    """Fail-open shapes the second review pass of 2026-09-25 found."""

    def assertNotClassOnly(self, before, after):
        ok, reason = classify(before, after)
        self.assertFalse(ok, (before, after))
        return reason

    def test_an_attribute_selector_is_not_a_class_string(self):
        self.assertNotClassOnly(
            '<style>[class="btn"]{display:none}</style>\n',
            '<style>[class="pay-now"]{display:none}</style>\n')

    def test_reordering_around_a_dangerous_class_is_behaviour(self):
        reason = self.assertNotClassOnly('<b className="hidden flex" />\n',
                                         '<b className="flex hidden" />\n')
        self.assertIn("order", reason)

    def test_a_safe_reorder_stays_class_only(self):
        self.assertEqual(classify('<b className="mt-4 p-3" />\n',
                                  '<b className="p-3 mt-4" />\n'), (True, ""))

    def test_overriding_a_dangerous_class_is_behaviour(self):
        """The denylist caught these as overrides. The allowlist names none of
        the overriding tokens, so each is refused as an unknown token."""
        for before, after, token in (
                ("opacity-0 transition", "opacity-0 opacity-100", "opacity-100"),
                ("h-0 overflow-hidden", "h-0 h-auto overflow-hidden", "h-auto"),
                ("opacity-0 opacity-100", "opacity-0", "opacity-100"),
                ("absolute top-0", "absolute relative top-0", "relative")):
            reason = self.assertNotClassOnly(
                f'<b className="{before}" />\n', f'<b className="{after}" />\n')
            self.assertIn(f"`{token}`", reason)
            self.assertIn("not on the allowlist", reason)

    def test_a_same_family_edit_beside_a_safe_class_stays_class_only(self):
        self.assertEqual(classify('<b className="mt-4 p-4" />\n',
                                  '<b className="mt-5 p-4" />\n'), (True, ""))

    def test_a_sizing_edit_is_not_on_the_allowlist(self):
        """Sizing can shrink a control to nothing; the allowlist leaves it out."""
        reason = self.assertNotClassOnly('<b className="h-4 w-4" />\n',
                                         '<b className="h-5 w-4" />\n')
        self.assertIn("`h-5` added", reason)

    def test_a_css_variable_value_of_a_listed_class_is_caught(self):
        for token in ("opacity-(--zero)", "h-(--x)", "w-(--x)", "scale-(--x)"):
            reason = self.assertNotClassOnly(
                '<b className="mt-4" />\n', f'<b className="mt-4 {token}" />\n')
            self.assertIn(f"`{token}` added", reason)

    def test_an_aliased_import_is_not_the_class_helper(self):
        head = 'import { formatCents as cn } from "./money";\n'
        self.assertNotClassOnly(head + 'const p = cn("100");\n',
                                head + 'const p = cn("999");\n')

    def test_a_parameter_shadowing_the_helper_is_not_the_class_helper(self):
        head = 'import { cn } from "@/lib/utils";\n'
        self.assertNotClassOnly(head + 'const f = (cn) => cn("USD");\n',
                                head + 'const f = (cn) => cn("EUR");\n')

    def test_a_declared_variable_named_classname_is_not_a_class_string(self):
        for keyword in ("let", "const", "var"):
            self.assertNotClassOnly(f'{keyword} className="user";\n',
                                    f'{keyword} className="admin";\n')


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def commit_all(repo, message):
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
        "-m", message)
    done = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True)
    return done.stdout.strip()


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


LOGIN = "src/app/login/page.tsx"


class Cli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q")
        (self.repo / "src/app/login").mkdir(parents=True)
        (self.repo / LOGIN).write_text(LOGIN_BEFORE, encoding="utf-8")
        (self.repo / "src/session.ts").write_text("export const ttl = 60;\n")
        self.base = commit_all(self.repo, "base")

    def tearDown(self):
        self._tmp.cleanup()

    def test_issue_230_against_the_working_tree_exits_0(self):
        (self.repo / LOGIN).write_text(LOGIN_AFTER, encoding="utf-8")
        code, out, err = run("--repo", str(self.repo), "--base", self.base,
                             "--", LOGIN)
        self.assertEqual((code, out, err), (0, f"{LOGIN}: class-only\n", ""))

    def test_issue_230_against_a_head_commit_exits_0(self):
        (self.repo / LOGIN).write_text(LOGIN_AFTER, encoding="utf-8")
        head = commit_all(self.repo, "issue 230")
        (self.repo / LOGIN).write_text("dirty working tree\n")
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--head", head, "--", LOGIN)
        self.assertEqual((code, out), (0, f"{LOGIN}: class-only\n"))

    def test_one_class_only_file_and_one_behaviour_file_exits_1(self):
        (self.repo / LOGIN).write_text(LOGIN_AFTER, encoding="utf-8")
        (self.repo / "src/session.ts").write_text("export const ttl = 6000;\n")
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", LOGIN, "src/session.ts")
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"{LOGIN}: class-only")
        self.assertTrue(lines[1].startswith("src/session.ts: behaviour — "),
                        lines[1])
        self.assertEqual(len(lines), 2)

    def test_a_deleted_file_is_behaviour(self):
        (self.repo / "src/session.ts").unlink()
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", "src/session.ts")
        self.assertEqual(code, 1)
        self.assertIn("src/session.ts: behaviour — ", out)
        self.assertIn("deleted", out)

    def test_an_added_file_is_behaviour(self):
        (self.repo / "src/new.ts").write_text('<p className="a" />\n')
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", "src/new.ts")
        self.assertEqual(code, 1)
        self.assertIn("added", out)

    def test_a_binary_file_is_behaviour(self):
        (self.repo / "logo.png").write_bytes(b"\x89PNG\x00\x01")
        base = commit_all(self.repo, "logo")
        (self.repo / "logo.png").write_bytes(b"\x89PNG\x00\x02")
        code, out, _ = run("--repo", str(self.repo), "--base", base,
                           "--", "logo.png")
        self.assertEqual(code, 1)
        self.assertIn("logo.png: behaviour — ", out)
        self.assertIn("not text", out)

    def test_a_path_outside_the_repo_is_behaviour(self):
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", "../elsewhere.ts")
        self.assertEqual(code, 1)
        self.assertIn("outside the repository", out)

    def test_a_dangerous_class_through_the_cli_exits_1(self):
        (self.repo / LOGIN).write_text(
            LOGIN_BEFORE.replace("mt-4 w-full", "mt-4 hidden w-full"))
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", LOGIN)
        self.assertEqual(code, 1)
        self.assertIn("class `hidden` added at line 12, which is not on the "
                      "allowlist", out)

    def test_only_markup_files_can_be_class_only(self):
        """`UPDATE plans SET class='free'` reads as a class attribute. A
        migration or a plain script file is never judged class-only."""
        for name, text in (("m.sql", "UPDATE plans SET class='{}';\n"),
                           ("pay.ts", "const c = '<b class=\"{}\">';\n")):
            (self.repo / name).write_text(text.format("free"))
            base = commit_all(self.repo, name)
            (self.repo / name).write_text(text.format("admin"))
            code, out, _ = run("--repo", str(self.repo), "--base", base,
                               "--", name)
            self.assertEqual(code, 1, name)
            self.assertIn(f"{name}: behaviour — only .tsx, .jsx and .html", out)

    def test_an_unchanged_file_of_any_kind_is_class_only(self):
        code, out, _ = run("--repo", str(self.repo), "--base", self.base,
                           "--", "src/session.ts")
        self.assertEqual((code, out), (0, "src/session.ts: class-only\n"))

    def test_usage_errors_exit_2(self):
        cases = [
            ("--repo", str(self.repo), "--base", self.base),
            ("--repo", str(self.repo), "--base", "no-such-commit", "--", LOGIN),
            ("--repo", str(self.repo), "--base", self.base, "--head",
             "no-such-commit", "--", LOGIN),
            ("--repo", str(self.repo / "src"), "--base", self.base, "--", LOGIN),
            ("--repo", str(self.repo / "missing"), "--base", self.base, "--",
             LOGIN),
            ("--base", self.base, "--", LOGIN),
            ("--repo", str(self.repo), "--base=--all", "--", LOGIN),
        ]
        for args in cases:
            code, out, err = run(*args)
            self.assertEqual(code, 2, (args, out, err))
            self.assertEqual(out, "", args)


SUBMIT_FULL = ('className="mt-4 w-full rounded-card bg-primary p-3 text-sm '
               'font-semibold text-card"')


def verdict(before_classes, after_classes):
    """classify() over the submit button, with only its classes changed."""
    before = LOGIN_BEFORE.replace(SUBMIT_FULL, f'className="{before_classes}"')
    after = LOGIN_BEFORE.replace(SUBMIT_FULL, f'className="{after_classes}"')
    return classify(before, after)


class Allowlist(unittest.TestCase):
    """The human's ruling of 2026-09-25, road B: a token passes only if the
    allowlist names it. Anything else is behaviour, and the reason names it."""

    def test_an_unknown_token_added_is_behaviour_and_named(self):
        ok, reason = verdict("mt-4 p-3", "mt-4 p-3 foo-bar")
        self.assertFalse(ok)
        self.assertIn("`foo-bar` added at line 12", reason)
        self.assertIn("not on the allowlist", reason)

    def test_an_unknown_token_removed_is_behaviour_and_named(self):
        ok, reason = verdict("mt-4 foo-bar", "mt-4")
        self.assertFalse(ok)
        self.assertIn("`foo-bar` removed at line 12 of the base", reason)

    def test_the_ruling_s_unsafe_tokens_are_behaviour_and_named(self):
        for token, why in (
                ("text-transparent", "not on the allowlist"),
                ("-left-[9999px]", "arbitrary value"),
                ("translate-x-full", "not on the allowlist"),
                ("order-first", "not on the allowlist"),
                ("hidden", "not on the allowlist"),
                ("peer", "not on the allowlist"),
                ("group", "not on the allowlist"),
                ("!text-red-500", "important mark"),
                ("bg-red-500/0", "not on the allowlist"),
                ("-mt-4", "not on the allowlist")):
            for before, after, direction in (("mt-4", f"mt-4 {token}", "added"),
                                             (f"mt-4 {token}", "mt-4",
                                              "removed")):
                ok, reason = verdict(before, after)
                self.assertFalse(ok, (token, direction))
                self.assertIn(f"`{token}` {direction} at line 12", reason)
                self.assertIn(why, reason)

    def test_a_variant_keeps_an_unsafe_token_unsafe(self):
        for token in ("hover:text-transparent", "md:hidden", "dark:-mt-4",
                      "focus:peer"):
            self.assertFalse(verdict("mt-4", f"mt-4 {token}")[0], token)

    def test_a_bracketed_variant_is_behaviour(self):
        for token in ("data-[state=open]:bg-card", "aria-[busy=true]:mt-2",
                      "supports-(--x):mt-2"):
            ok, reason = verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)
            self.assertIn("arbitrary variant", reason)

    def test_an_important_mark_at_either_end_or_after_a_variant(self):
        for token in ("!mt-2", "mt-2!", "sm:!mt-2"):
            ok, reason = verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)
            self.assertIn("important mark", reason)

    def test_a_safe_token_overriding_a_held_unsafe_one_is_behaviour(self):
        """`text-transparent` was there before; the new colour shows the text."""
        for before, after in (("text-transparent mt-4", "text-transparent text-ink mt-4"),
                              ("-mt-4 p-2", "-mt-4 mt-2 p-2"),
                              ("[color:transparent] p-2", "[color:transparent] p-3")):
            ok, reason = verdict(before, after)
            self.assertFalse(ok, before)
            self.assertIn("overrides", reason)

    def test_a_side_margin_overriding_a_held_negative_margin_is_behaviour(self):
        """Code review, 2026-09-25: `mt-4` held the top of `-m-96` in place;
        removing it moves the element up 24rem. `m` and `mt` set one property."""
        for before, after in (("-m-96 mt-4", "-m-96"),
                              ("-mt-4 p-2", "-mt-4 m-2 p-2"),
                              ("-px-4 mt-2", "-px-4 pl-2 mt-2")):
            ok, reason = verdict(before, after)
            self.assertFalse(ok, before)
            self.assertIn("overrides", reason)

    def test_a_reorder_beside_a_safe_swap_is_behaviour(self):
        """Code review, 2026-09-25: twMerge keeps the last class, so this
        shows the element; the colour swap must not hide the reorder."""
        ok, reason = verdict("block hidden text-sm", "hidden block text-red-500")
        self.assertFalse(ok)
        self.assertIn("order", reason)

    def test_a_safe_swap_beside_an_unmoved_unsafe_token_stays_class_only(self):
        self.assertEqual(verdict("w-full mt-4 text-sm", "w-full mt-2 text-lg"),
                         (True, ""))

    def test_a_background_in_the_text_colour_is_behaviour(self):
        """`bg-current` paints the background the colour of the text."""
        for token in ("bg-current", "from-current", "via-current",
                      "to-current"):
            ok, reason = verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(ok, token)
            self.assertIn("not on the allowlist", reason)

    def test_a_duration_or_delay_off_the_tailwind_scale_is_behaviour(self):
        """`delay-999999` keeps a fading element invisible for 17 minutes."""
        for token in ("delay-999999", "duration-99999", "delay-1001"):
            self.assertFalse(verdict("mt-4", f"mt-4 {token}")[0], token)
        for token in ("delay-0", "duration-75", "duration-1000"):
            self.assertEqual(verdict("mt-4", f"mt-4 {token}"), (True, ""),
                             token)

    def test_the_ruling_s_safe_tokens_are_class_only(self):
        for token in ("hover:bg-red-600", "md:text-lg", "rounded-lg",
                      "ring-2", "text-muted-foreground"):
            self.assertEqual(verdict("mt-4", f"mt-4 {token}"), (True, ""),
                             token)

    def test_a_near_invisible_colour_and_truncate_are_behaviour(self):
        """The human's ruling of 2026-09-25, taken on the allowlist review: an opacity
        suffix from /1 to /9 leaves a colour almost invisible, and `truncate` sets
        `overflow: hidden`, which can clip a child. Both leave the safe list; a
        wrong refusal costs one full-level run, a wrong pass skips the critical
        gates on a sign-in or money file."""
        for token in ("text-ink/5", "bg-black/1", "border-line/9", "truncate",
                      "md:truncate"):
            safe, reason = verdict("mt-4", f"mt-4 {token}")
            self.assertFalse(safe, token)
            self.assertIn(token.split(":")[-1], reason, token)

    def test_one_token_of_every_family_is_class_only(self):
        for token in (
                # colour, with one project's tokens and an opacity suffix
                "text-ink-3", "bg-primary-soft", "border-line", "ring-red-500",
                "outline-primary", "decoration-sky-300", "fill-current",
                "stroke-black", "placeholder-ink-2", "caret-white",
                "accent-primary", "divide-slate-200", "from-amber-50",
                "via-inherit", "to-green", "bg-black/50", "text-red-500/100",
                "text-ink/10",
                # spacing
                "p-0", "px-2.5", "mb-px", "gap-x-6", "space-y-96", "me-3",
                # typography
                "text-xs", "text-9xl", "font-thin", "font-black", "font-mono",
                "leading-6", "leading-relaxed", "tracking-widest", "italic",
                "not-italic", "underline", "no-underline", "line-through",
                "uppercase", "normal-case", "text-end",
                "whitespace-nowrap", "break-words",
                # borders and corners
                "border", "border-2", "border-t", "border-x-4", "rounded",
                "rounded-t-lg", "rounded-full", "rounded-card", "border-dashed",
                # focus and rings
                "ring", "ring-inset", "ring-offset-2", "outline",
                "outline-none", "outline-4", "outline-offset-1",
                "outline-dotted",
                # effects
                "shadow", "shadow-lg", "transition", "transition-colors",
                "duration-150", "ease-in-out", "delay-75",
                # variants
                "focus-visible:ring-2", "sm:p-4", "dark:bg-slate-900",
                "disabled:text-ink-3", "aria-invalid:border-red",
                "data-open:bg-card", "group-hover:underline"):
            self.assertEqual(verdict("mt-4", f"mt-4 {token}"), (True, ""),
                             token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
