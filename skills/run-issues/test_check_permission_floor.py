#!/usr/bin/env python3
"""Cases for check_permission_floor.py, driven on throwaway settings files.

The anchor case is run `414a-483-286335`'s real launch state: nineteen tracked
rules, and `Bash(npx vitest *)` present only in the untracked local file. That
run then lost 2 h 34 m to a classifier refusal on `npx vitest run`.

    python3 -m unittest test_check_permission_floor
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import check_permission_floor as guard


def settings(root: pathlib.Path, name: str, rules: list[str]) -> None:
    target = root / ".claude" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"permissions": {"allow": rules}}))


def declare(root: pathlib.Path, body: str) -> None:
    """Write `.claude/run-classes.json` verbatim, malformed bodies included."""
    target = root / ".claude" / "run-classes.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)


def tree(
    tracked: list[str] | None = None,
    local: list[str] | None = None,
    classes: list[str] | None = None,
) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="permfloor-"))
    if tracked is not None:
        settings(root, "settings.json", tracked)
    if local is not None:
        settings(root, "settings.local.json", local)
    if classes is not None:
        declare(root, json.dumps({"classes": classes}))
    return root


TIER_A = [
    "Bash(cd:*)",
    "Bash(export PATH=*)",
    "Bash(sed:*)",
    "Bash(grep:*)",
    "Bash(head:*)",
    "Bash(tail:*)",
    "Bash(cat:*)",
    "Bash(ls:*)",
    "Bash(wc:*)",
    "Bash(shasum:*)",
    "Bash(diff:*)",
    "Bash(find:*)",
    "Bash(sort:*)",
    "Bash(cut:*)",
    "Bash(tr:*)",
    "Bash(awk:*)",
    "Bash(md5:*)",
    "Bash(stat:*)",
    "Bash(date:*)",
    "Bash(echo:*)",
    "Bash(printf:*)",
    "Bash(true)",
    "Bash(env:*)",
    "Bash(lsof:*)",
    "Bash(pgrep:*)",
    "Bash(tee:*)",
    "Bash(node scripts/http-probe.mjs:*)",
    "Bash(python3 ~/.claude/skills/*)",
]

# Every rule here is repo-independent: it names no repository's own files. That
# is the whole point of the 2026-09-13 change -- a repo must be able to pass this
# check on rules like these alone, with no rule naming another repo's env file.
EVERYTHING = [
    "Bash(npx vitest*)",
    "Bash(npx tsc*)",
    "Bash(npx eslint*)",
    "Bash(npm test*)",
    "Bash(npm run test*)",
    "Bash(npm run lint*)",
    "Bash(npm run typecheck*)",
    "Bash(npm run build*)",
]

# One repository's own four `node --env-file=<its env> scripts/*.mjs` commands,
# and the one rule that covers them. They were built into the runner's list until
# 2026-09-13 and are now a repo declaration, which is what the cases below drive.
# The env path is a fixture shape: what matters is that the verdict turns on it.
REPO_OWN_CLASSES = [
    "node --env-file=/home/user/project/.project-spine.env"
    " scripts/seed-run-workspace.mjs --batch batch-000000 --ledger run.md",
    "node --env-file=/home/user/project/.project-spine.env"
    " scripts/dev-signin-link.mjs --batch batch-000000 --site http://batch-000000.localhost:3000",
    "node --env-file=/home/user/project/.project-spine.env"
    " scripts/zoho-live-lock.mjs --batch batch-000000 -- npx vitest run src/lib/zoho/live",
    "node --env-file=/home/user/project/.project-spine.env"
    " scripts/delete-run-workspace.mjs --batch batch-000000 --ledger run.md",
]
REPO_OWN_RULE = "Bash(node --env-file=/home/user/project/.project-spine.env *)"


class Covers(unittest.TestCase):
    def test_a_star_rule_matches_by_prefix(self):
        self.assertTrue(guard.covers("Bash(npx vitest*)", "npx vitest run a.test.ts"))

    def test_a_rule_with_no_star_matches_exactly(self):
        self.assertTrue(guard.covers("Bash(npm test)", "npm test"))
        self.assertFalse(guard.covers("Bash(npm test)", "npm test -- --watch"))

    def test_the_trailing_space_is_the_trap(self):
        """`Bash(npx vitest *)` does NOT cover a bare `npx vitest`.

        That spaced form is what the local file carried, and it is why the
        tracked rule this session added has no space.
        """
        self.assertFalse(guard.covers("Bash(npx vitest *)", "npx vitest"))
        self.assertTrue(guard.covers("Bash(npx vitest*)", "npx vitest"))

    def test_a_broad_rule_covers_a_narrow_command(self):
        self.assertTrue(guard.covers("Bash(npm run *)", "npm run lint"))

    def test_an_unrelated_rule_covers_nothing(self):
        self.assertFalse(guard.covers("Bash(vercel deploy*)", "npx vitest run"))


class Judge(unittest.TestCase):
    def test_a_tracked_rule_passes(self):
        verdict, rule = guard.judge("npx vitest run", ["Bash(npx vitest*)"], [])
        self.assertEqual(verdict, "ok")
        self.assertEqual(rule, "Bash(npx vitest*)")

    def test_a_local_only_rule_is_untracked_not_ok(self):
        """The whole fault. The command WORKS today and stops working in the
        next worktree, which is worse than never having worked."""
        verdict, rule = guard.judge("npx vitest run", [], ["Bash(npx vitest *)"])
        self.assertEqual(verdict, "untracked")
        self.assertEqual(rule, "Bash(npx vitest *)")

    def test_no_rule_anywhere_is_uncovered(self):
        self.assertEqual(guard.judge("npx vitest run", [], [])[0], "uncovered")

    def test_tracked_wins_when_both_files_carry_it(self):
        verdict, _ = guard.judge("npm run lint", ["Bash(npm run lint*)"], ["Bash(npm run *)"])
        self.assertEqual(verdict, "ok")


class TheRunsOwnLaunchState(unittest.TestCase):
    """Run `414a-483-286335`, 2026-08-30, 04:00."""

    def test_the_launch_state_is_refused(self):
        root = tree(tracked=["Bash(vercel deploy*)"], local=["Bash(npx vitest *)"])
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_the_state_after_this_sessions_fix_passes(self):
        """`EVERYTHING` was enough while the floor graded the runner alone. From
        2026-09-12 it grades the gates too, so the pass needs `TIER_A` beside it
        -- which is the whole finding of run batch-200d42."""
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 0)

    def test_a_worktree_that_never_saw_the_local_rule_is_also_refused(self):
        """The run worktree's own copy did not carry `Bash(npx vitest *)` at
        all, so its verdict is `uncovered` rather than `untracked`. Both
        refuse, which is the point."""
        root = tree(tracked=["Bash(vercel deploy*)"], local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 1)


class Main(unittest.TestCase):
    def test_an_extra_class_is_graded_too(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        self.assertEqual(guard.main(["--repo", str(root), "--class", "npx playwright test"]), 1)

    def test_an_extra_class_that_is_tracked_passes(self):
        root = tree(tracked=EVERYTHING + TIER_A + ["Bash(npx playwright*)"], local=[])
        self.assertEqual(guard.main(["--repo", str(root), "--class", "npx playwright test"]), 0)

    def test_a_missing_tracked_file_is_a_refusal_not_a_crash(self):
        root = tree(tracked=None, local=EVERYTHING)
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_an_unparseable_settings_file_exits_two(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        (root / ".claude" / "settings.json").write_text("{not json")
        self.assertEqual(guard.main(["--repo", str(root)]), 2)

    def test_a_repo_with_no_claude_directory_is_refused(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="permfloor-bare-"))
        self.assertEqual(guard.main(["--repo", str(root)]), 1)


class Suggest(unittest.TestCase):
    def test_an_npm_run_class_keeps_its_script_name(self):
        self.assertEqual(guard.suggest("npm run lint"), '"Bash(npm run lint*)"')

    def test_an_npx_class_keeps_two_words(self):
        self.assertEqual(guard.suggest("npx vitest run a.test.ts"), '"Bash(npx vitest*)"')

    def test_the_suggestion_actually_covers_the_class(self):
        """A remedy that does not fix the refusal is worse than no remedy."""
        for command in guard.REQUIRED:
            rule = guard.suggest(command).strip('"')
            with self.subTest(command=command):
                self.assertTrue(guard.covers(rule, command), f"{rule} misses {command}")



# --------------------------------------------------------------------------
# Run `batch-200d42`, 2026-09-11. The floor printed `ok: 12 command class(es)`
# and the run then lost 3 h 37 m to a classifier modal on issue 441's verify
# gate. The twelve classes were the RUNNER's; the command that halted was a
# GATE's, and it is compound:
#
#     cd <copy> && export PATH=... && sed -n '806p' <file> \
#       && npx vitest run <two files> 2>&1 | tail -20
#
# `npx vitest*` was tracked. `cd`, `export`, `sed` and `tail` were not, and a
# rule covering one segment of a compound command covers none of the others.
# --------------------------------------------------------------------------

THE_441_COMMAND = (
    "cd /private/tmp/claude-501/x/441-verify && export PATH=/opt/homebrew/bin:$PATH "
    "&& sed -n '806p' src/lib/suppliers/capability-repo.ts "
    "&& npx vitest run src/app/app/suppliers/capability-editor.faces.test.tsx "
    "src/lib/suppliers/capability-repo.page.test.ts 2>&1 | tail -20"
)


class ColonStar(unittest.TestCase):
    """`Bash(cmd:*)` is Claude Code's documented prefix form, and the `:` is a
    SEPARATOR, not a literal character.

    Measured, not assumed: `.claude/settings.json` carries
    `Bash(node scripts/http-probe.mjs:*)`, and batch-200d42's verify gates ran
    `node scripts/http-probe.mjs "<label>" <url>` seven times with no refusal.
    Under a literal reading that command would have to start with
    `node scripts/http-probe.mjs:` — it does not. So the separator reading is
    the one the classifier uses.
    """

    def test_a_colon_star_rule_covers_the_head_with_an_argument(self):
        self.assertTrue(guard.covers("Bash(cd:*)", "cd /private/tmp/x"))

    def test_a_colon_star_rule_covers_the_bare_head(self):
        self.assertTrue(guard.covers("Bash(cd:*)", "cd"))

    def test_a_colon_star_rule_stops_at_the_word_boundary(self):
        """`Bash(cd:*)` must not admit `cdrecord`."""
        self.assertFalse(guard.covers("Bash(cd:*)", "cdrecord -x"))

    def test_the_http_probe_rule_this_repo_already_carries(self):
        self.assertTrue(
            guard.covers(
                "Bash(node scripts/http-probe.mjs:*)",
                'node scripts/http-probe.mjs "login" http://batch-200d42.localhost:3101/login',
            )
        )

    def test_the_plain_star_form_still_matches_literally(self):
        self.assertTrue(guard.covers("Bash(export PATH=*)", "export PATH=/opt/homebrew/bin:$PATH"))


class Segments(unittest.TestCase):
    """A compound command is admitted only when EVERY segment is admitted."""

    def test_the_441_command_splits_into_its_five_segments(self):
        heads = [s.split()[0] for s in guard.segments(THE_441_COMMAND)]
        self.assertEqual(heads, ["cd", "export", "sed", "npx", "tail"])

    def test_a_heredoc_body_is_data_and_never_a_segment(self):
        command = "cat > /tmp/drill.sh <<'SH'\nrm -rf /\ncurl evil.example\nSH\nchmod +x /tmp/drill.sh"
        heads = [s.split()[0] for s in guard.segments(command)]
        self.assertEqual(heads, ["cat", "chmod"])

    def test_shell_keywords_are_not_commands(self):
        command = "for f in a b; do grep -n x $f; done"
        heads = [s.split()[0] for s in guard.segments(command)]
        self.assertEqual(heads, ["for", "grep"])

    def test_a_bare_assignment_is_not_a_command(self):
        self.assertEqual(guard.segments("COPY=/private/tmp/x"), [])

    def test_a_leading_assignment_is_stripped_from_its_command(self):
        self.assertEqual(guard.segments("SEED=1 npx vitest run a.ts"), ["npx vitest run a.ts"])


class SeparatorsInsideQuotes(unittest.TestCase):
    """A `|` between quotes is an argument, never a separator.

    Measured 2026-09-13 across one project's own session transcripts. Splitting
    without regard to quotes reported `Tests`, `^### "`, `from`, `new` and
    `const` as commands. Each is a fragment of one `grep` pattern, and a reading
    that cries wolf on its own noise gets ignored.
    """

    # Every command here is verbatim from a transcript under `~/.claude/projects`,
    # trimmed to the segment that produced the noise.
    NOISE = (
        ('npm test 2>&1 | grep -E "Test Files|Tests "', "Tests"),
        ('awk \'NR>=494\' $B | grep -n "^## \\|^### " | head -30', '^### "'),
        ("grep -rEn '\\b(bg|text|from|to|via)-(slate|red)-[0-9]{2,3}\\b' src/", "from"),
        ('grep -nE "KINDS|kind|new|fix|deepen" check_run_rail.py | head -10', "new"),
        ("grep -nE '^\\s*(function|const|let) [A-Za-z_]+' flow.html | sed -n '1,200p'", "const"),
    )

    def test_no_fragment_of_a_quoted_pattern_is_reported_as_a_command(self):
        for command, noise in self.NOISE:
            with self.subTest(noise=noise):
                self.assertNotIn(noise, guard.segments(command))

    def test_the_quoted_pattern_stays_whole_inside_its_own_segment(self):
        found = guard.segments('npm test 2>&1 | grep -E "Test Files|Tests "')
        self.assertEqual([s.split()[0] for s in found], ["npm", "grep"])
        self.assertIn('"Test Files|Tests "', found[1])

    def test_a_single_quoted_separator_is_not_a_separator(self):
        self.assertEqual(guard.segments("grep -n 'a;b' f"), ["grep -n 'a;b' f"])

    def test_a_backslash_escaped_separator_is_not_a_separator(self):
        self.assertEqual(guard.segments("echo a\\;b"), ["echo a\\;b"])

    def test_an_unbalanced_quote_never_raises_and_never_splits_inside_it(self):
        """A transcript holds whatever was typed. A reading that dies on one
        malformed command reads nothing after it."""
        self.assertEqual(guard.segments("echo 'unbalanced | still one piece"),
                         ["echo 'unbalanced | still one piece"])

    def test_a_separator_outside_the_quotes_still_splits(self):
        found = guard.segments('echo "a && b" && ls')
        self.assertEqual(found, ['echo "a && b"', "ls"])

    def test_an_apostrophe_in_a_comment_does_not_open_a_quote(self):
        """The one that survived the first fix. A run-issues review gate wrote
        `# ... only the shipped tree's own files matter` on its own line, and
        that apostrophe inverted the quote state for the rest of the command --
        so `grep -E 'Test Files|Tests |FAIL'` split and reported `Tests`."""
        command = (
            "cd $COPY\n"
            "# remove the fixtures so only the shipped tree's own files matter\n"
            "npm test 2>&1 | grep -E 'Test Files|Tests |FAIL'"
        )
        found = guard.segments(command)
        self.assertNotIn("Tests", found)
        self.assertEqual([s.split()[0] for s in found], ["cd", "npm", "grep"])

    def test_a_hash_inside_a_url_is_not_a_comment(self):
        self.assertEqual(guard.segments("curl http://x/y#frag"), ["curl http://x/y#frag"])

    def test_a_hash_line_inside_a_quoted_string_takes_no_command_with_it(self):
        """The comment rule has to run where the quote state is known. A pass
        over raw lines drops `# b" && rm -rf /tmp/x`, the second line of a
        quoted commit message, and the `rm` on it goes ungraded."""
        found = guard.segments('git commit -m "a\n# b" && rm -rf /tmp/x')
        self.assertEqual([s.split()[0] for s in found], ["git", "rm"])

    def test_an_indented_comment_line_is_still_a_comment(self):
        self.assertEqual(guard.segments("  # indented\nls"), ["ls"])

    def test_a_line_continuation_joins_its_two_halves(self):
        """A backslash before a newline is whitespace, so the command carries
        on. Splitting there left 70 segments headed by a bare backslash in
        that project's transcripts, and the real command in each was hidden
        behind it."""
        found = guard.segments("DATABASE_URL=postgresql://localhost/x \\\n  npx vitest run a.ts")
        self.assertEqual(found, ["npx vitest run a.ts"])


class JudgeCommand(unittest.TestCase):
    """The regression. `npx vitest*` tracked is not the 441 command covered."""

    def test_the_441_command_is_uncovered_although_vitest_is_tracked(self):
        verdict, _, segment = guard.judge_command(THE_441_COMMAND, ["Bash(npx vitest*)"], [])
        self.assertEqual(verdict, "uncovered")
        self.assertEqual(segment.split()[0], "cd")

    def test_the_441_command_passes_once_every_segment_is_tracked(self):
        tracked = [
            "Bash(npx vitest*)",
            "Bash(cd:*)",
            "Bash(export PATH=*)",
            "Bash(sed:*)",
            "Bash(tail:*)",
        ]
        self.assertEqual(guard.judge_command(THE_441_COMMAND, tracked, [])[0], "ok")

    def test_one_local_only_segment_makes_the_whole_command_untracked(self):
        verdict, rule, segment = guard.judge_command(
            "cd /tmp && npx vitest run a.ts", ["Bash(cd:*)"], ["Bash(npx vitest*)"]
        )
        self.assertEqual(verdict, "untracked")
        self.assertEqual(rule, "Bash(npx vitest*)")
        self.assertEqual(segment, "npx vitest run a.ts")

    def test_uncovered_outranks_untracked(self):
        """Report the worse fault when a command carries both."""
        verdict, _, _ = guard.judge_command(
            "cd /tmp && npx vitest run a.ts && perl -e 1", ["Bash(cd:*)"], ["Bash(npx vitest*)"]
        )
        self.assertEqual(verdict, "uncovered")


class Roles(unittest.TestCase):
    """A floor that grades one role's list and says `ok` is reporting on its
    own list. It must name the roles it graded and the roles it did not."""

    def test_every_gate_role_is_graded(self):
        for role in ("runner", "verify-gate", "review-gate", "review-gate-critical"):
            with self.subTest(role=role):
                self.assertIn(role, guard.ROLE_CLASSES)
                self.assertTrue(guard.ROLE_CLASSES[role])

    def test_the_441_command_is_one_of_the_verify_gate_classes(self):
        """The anchor: the exact shape that halted batch-200d42."""
        shapes = guard.ROLE_CLASSES["verify-gate"]
        self.assertTrue(
            any(s.startswith("cd ") and "npx vitest run" in s and "| tail" in s for s in shapes),
            "no verify-gate class carries the cd/sed/vitest/tail shape that halted 441",
        )

    def test_the_ungraded_roles_are_named(self):
        self.assertIn("implementer", guard.UNGRADED_ROLES)
        self.assertIn("finale", guard.UNGRADED_ROLES)

    def test_no_role_is_both_graded_and_ungraded(self):
        self.assertFalse(set(guard.ROLE_CLASSES) & set(guard.UNGRADED_ROLES))

    def test_the_ruled_uncovered_classes_are_named_and_reasoned(self):
        """the human ruled on 2026-09-12 that these stay classifier-judged. They
        are measured gate shapes, so the floor must name them — and must NOT
        refuse over them, or no run would ever launch."""
        self.assertTrue(guard.RULED_UNCOVERED)
        for command, reason in guard.RULED_UNCOVERED:
            with self.subTest(command=command):
                self.assertTrue(reason.strip(), f"{command} is listed with no reason")

    def test_a_ruled_uncovered_class_does_not_refuse_the_launch(self):
        root = tree(tracked=TIER_A + EVERYTHING, local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 0)




class TheOutputSaysWhatItGraded(unittest.TestCase):
    def test_the_pass_line_names_the_roles(self):
        root = tree(tracked=TIER_A + EVERYTHING, local=[])
        import contextlib, io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(guard.main(["--repo", str(root)]), 0)
        printed = out.getvalue()
        for role in guard.ROLE_CLASSES:
            self.assertIn(role, printed, f"the pass line never names {role}")

    def test_the_pass_line_names_what_it_did_not_grade(self):
        root = tree(tracked=TIER_A + EVERYTHING, local=[])
        import contextlib, io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            guard.main(["--repo", str(root)])
        printed = out.getvalue()
        for role in guard.UNGRADED_ROLES:
            self.assertIn(role, printed, f"the pass line hides that {role} is ungraded")

    def test_a_refusal_names_the_role_and_the_offending_segment(self):
        root = tree(tracked=EVERYTHING, local=[])
        import contextlib, io

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(guard.main(["--repo", str(root)]), 1)
        printed = err.getvalue()
        self.assertIn("verify-gate", printed)
        self.assertIn("cd ", printed)


class SuggestForGateShapes(unittest.TestCase):
    def test_a_bare_unix_tool_gets_the_colon_star_form(self):
        self.assertEqual(guard.suggest("sed -n '806p' a.ts"), '"Bash(sed:*)"')

    def test_an_export_keeps_its_variable_name(self):
        """`Bash(export:*)` would admit every environment variable. The measured
        shape is `export PATH=...` and the rule says so."""
        self.assertEqual(guard.suggest("export PATH=/opt/homebrew/bin:$PATH"), '"Bash(export PATH=*)"')

    def test_every_class_in_every_role_has_a_working_suggestion(self):
        for role, shapes in guard.ROLE_CLASSES.items():
            for command in shapes:
                for segment in guard.segments(command):
                    rule = guard.suggest(segment).strip('"')
                    with self.subTest(role=role, segment=segment):
                        self.assertTrue(
                            guard.covers(rule, segment), f"{rule} misses {segment}"
                        )

# --------------------------------------------------------------------------
# 2026-09-13. This machinery is one copy serving more than one repository. Four
# commands naming ONE repository's live-secrets env file sat in the runner's list
# and a fifth in the verify gate's, so the floor graded every repo against
# them -- and the second repository's `.claude/settings.json` carried a rule
# allowing that path only to get past this check. Repo-specific shapes are now a
# declaration the repo under test owns.
# --------------------------------------------------------------------------


class NoBuiltInClassBelongsToOneRepo(unittest.TestCase):
    def test_no_built_in_class_names_an_env_file(self):
        """`--env-file=<path>` is the shape whose verdict turns on the path, so
        it can only ever be covered by a rule naming that one repository's
        file. It belongs in a declaration, never in a shared list."""
        for role, shapes in guard.ROLE_CLASSES.items():
            for command in shapes:
                with self.subTest(role=role, command=command):
                    self.assertNotIn("--env-file=", command)

    def test_no_built_in_class_names_one_repositorys_env_file(self):
        for role, shapes in guard.ROLE_CLASSES.items():
            for command in shapes:
                with self.subTest(role=role, command=command):
                    self.assertNotIn(".project-spine.env", command)

    def test_a_repo_holding_no_other_repos_rule_passes(self):
        """The second repository after the fix: tier A and the universal npm
        and npx rules, and not one rule naming another repository. This refused
        before 2026-09-13, which is why that rule was in its allow list."""
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        self.assertEqual(guard.main(["--repo", str(root)]), 0)
        self.assertNotIn(REPO_OWN_RULE, EVERYTHING + TIER_A)


class TheRepoDeclaresItsOwn(unittest.TestCase):
    def test_a_repo_with_no_declaration_declares_nothing(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        self.assertEqual(guard.repo_classes(root / guard.REPO_CLASSES), [])

    def test_the_declared_commands_are_read_back(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[], classes=REPO_OWN_CLASSES)
        self.assertEqual(guard.repo_classes(root / guard.REPO_CLASSES), REPO_OWN_CLASSES)

    def test_a_declared_class_with_no_rule_refuses_the_launch(self):
        """The four, declared, in a repo that lost the rule covering them. The
        2026-09-13 change must not cost that repo this refusal."""
        root = tree(tracked=EVERYTHING + TIER_A, local=[], classes=REPO_OWN_CLASSES)
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_a_declared_class_with_its_rule_passes(self):
        root = tree(
            tracked=EVERYTHING + TIER_A + [REPO_OWN_RULE],
            local=[],
            classes=REPO_OWN_CLASSES,
        )
        self.assertEqual(guard.main(["--repo", str(root)]), 0)

    def test_a_declared_class_covered_only_locally_is_untracked(self):
        root = tree(
            tracked=EVERYTHING + TIER_A,
            local=[REPO_OWN_RULE],
            classes=REPO_OWN_CLASSES,
        )
        self.assertEqual(guard.main(["--repo", str(root)]), 1)

    def test_an_unparseable_declaration_exits_two(self):
        """A declaration nobody can read must not be read as a declaration of
        nothing. Exit 2 is the same answer an unreadable settings file gets."""
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        declare(root, "{not json")
        self.assertEqual(guard.main(["--repo", str(root)]), 2)

    def test_a_declaration_that_is_not_a_list_exits_two(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        declare(root, json.dumps({"classes": "npx vitest run"}))
        self.assertEqual(guard.main(["--repo", str(root)]), 2)

    def test_a_declaration_holding_a_blank_command_exits_two(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        declare(root, json.dumps({"classes": ["npx vitest run", "   "]}))
        self.assertEqual(guard.main(["--repo", str(root)]), 2)

    def test_a_declaration_with_no_classes_key_declares_nothing(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        declare(root, json.dumps({"note": "nothing repo-specific yet"}))
        self.assertEqual(guard.main(["--repo", str(root)]), 0)


class TheOutputSaysWhoDeclaredWhat(unittest.TestCase):
    def test_a_repo_declaring_nothing_is_told_so(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[])
        import contextlib, io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(guard.main(["--repo", str(root)]), 0)
        self.assertIn("REPO-DECLARED CLASSES: none", out.getvalue())

    def test_a_repo_declaring_four_is_told_how_many_and_from_where(self):
        root = tree(
            tracked=EVERYTHING + TIER_A + [REPO_OWN_RULE],
            local=[],
            classes=REPO_OWN_CLASSES,
        )
        import contextlib, io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(guard.main(["--repo", str(root)]), 0)
        printed = out.getvalue()
        self.assertIn("REPO-DECLARED CLASSES: 4", printed)
        self.assertIn(guard.REPO_CLASSES, printed)

    def test_a_refusal_on_a_declared_class_names_it_as_the_repos_own(self):
        root = tree(tracked=EVERYTHING + TIER_A, local=[], classes=REPO_OWN_CLASSES)
        import contextlib, io

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(guard.main(["--repo", str(root)]), 1)
        self.assertIn(guard.REPO_ROLE, err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
