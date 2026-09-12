#!/usr/bin/env python3
"""Refuse a python file that reaches `~/.claude/agents`, `~/.claude/hooks` or
`~/.claude/settings.json` by climbing parents from `__file__`.

## The class

Two different things were resolved by one climb:

    the skills tree   the checkout this file lives in. It has copies: a git
                      worktree sits at `.claude/worktrees/<name>/` INSIDE the
                      main checkout, so this is a moving target and a climb
                      from `__file__` is the right way to find it.

    ~/.claude         `agents/`, `hooks/` and `settings.json`. These are NOT in
                      this git repository. They have exactly one home on the
                      machine, no worktree copy, and never will have one.

`CLAUDE = HERE.parent.parent` is right only while the checkout sits at
`~/.claude/skills`. From `~/.claude/skills/.claude/worktrees/<name>/lib` the
same climb lands on `.claude/worktrees`, and `CLAUDE / "agents"` becomes a path
that has never existed.

## What it cost, measured 2026-09-11

Five suites refused from a worktree and passed in the main checkout:
`lib/test_claim_number.py`, `parallel-hunt/test_hunt_isolation.py`,
`run-issues/test_correction_brief.py`, `run-issues/test_run_isolation.py` and
`run-issues/test_skill_structure.py`. The green-light ritual reported five
faults that were not there.

One was not a test fault at all. `run-issues/correction_brief.py` loads the
brief-cap hook from `parents[2] / "hooks"` and treats an unreadable hook as "no
hook installed", which fails open on purpose. Run from a worktree the hook was
installed and armed, the climb could not see it, and the correction-round
exemption guard silently stopped guarding.

## Why prose did not close it

`run-issues/test_skill_structure.py` carried this comment DIRECTLY ABOVE its
broken climb:

    Issue 551. The promotion and attacker briefs live in a DIFFERENT repository
    (`claude-agents`), so `SKILLS` does not reach them.

The author knew the fact, wrote it down, and wrote the climb anyway. The human's
three-class test in `~/.claude/CLAUDE.md` sorts that outcome into the class that
does not work, and answering a failed reminder with a second reminder is named
there as the thing not to do. So the rule refuses here instead.

## The refusal

    climbed       a `/` join onto `"agents"`, `"hooks"` or `"settings.json"`
                  whose left side carries a climb from `__file__`, either
                  written inline or through a name bound to one earlier in the
                  file. The repair is `pathlib.Path.home() / ".claude"`.

An absolute anchor reaching the same three names is correct and passes:
`os.path.expanduser("~/.claude/hooks")` is how this directory's own walker
names its default roots.

A file that will not parse is refused rather than read as clean, for the same
reason `run_python_suites.py` refuses one: a file this reader cannot parse is
not a file with no fault in it.

Exit codes follow the rest of this directory. 0 is a clean walk, 1 is "a file
was read and it is wrong", and 2 is "nothing could be read, so nothing is
asserted".
"""

import argparse
import ast
import os
import sys
from pathlib import Path

# The three names that live outside this repository. Listed rather than
# inferred: a directory that grows inside the repo must not silently join them.
OUTSIDE = ("agents", "hooks", "settings.json")

# The checkout this file lives in. Resolved by a climb ON PURPOSE -- the skills
# tree is the thing that has worktree copies, and this is how a copy finds
# itself. It is the same two lines the rule above forbids pointing at
# `~/.claude`, which is the whole distinction.
REPO = Path(__file__).resolve().parent.parent


def _mentions_file(node):
    """Whether `__file__` appears anywhere in this expression."""
    return any(isinstance(n, ast.Name) and n.id == "__file__"
               for n in ast.walk(node))


def _mentions_any(node, names):
    """Whether any of `names` is read anywhere in this expression.

    A bare `CLAUDE`, and also `self.CLAUDE` or `cls.CLAUDE`. The class-attribute
    spelling is counted because `test_claim_number.py` bound its climb in a
    class body and read it back off `self`, and a reader that only saw bare
    names passed that line.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in names:
            return True
        if isinstance(n, ast.Attribute) and n.attr in names:
            if isinstance(n.value, ast.Name) and n.value.id in ("self", "cls"):
                return True
    return False


def _assignments(tree):
    """Every `NAME = <expr>` in the module body and in any class body it holds.

    Class bodies are included because `test_claim_number.py` held its climb as
    a class attribute, and a reader of the module body alone would have passed
    it.
    """
    bodies = [tree.body]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bodies.append(node.body)
    for body in bodies:
        for node in body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        yield target.id, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                if isinstance(node.target, ast.Name):
                    yield node.target.id, node.value


def rooted_names(source, filename="<unknown>"):
    """The names in `source` bound to a climb from `__file__`.

    Directly -- `HERE = Path(__file__).resolve().parent` -- or through another
    such name, however many steps along: `SKILLS = HERE.parent`. The pass
    repeats until nothing new is found, so order of definition in the file does
    not decide the answer.

    `filename` travels into the parse so any compiler warning the file provokes
    names the file rather than `<unknown>`.
    """
    pairs = list(_assignments(ast.parse(source, filename=filename)))
    rooted = set()
    while True:
        grown = False
        for name, value in pairs:
            if name in rooted:
                continue
            if _mentions_file(value) or _mentions_any(value, rooted):
                rooted.add(name)
                grown = True
        if not grown:
            return rooted


def refusals(source, path):
    """Every refusal this file earns, as finished sentences."""
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as err:
        return [f"REFUSED claude-home: {path} will not parse: {err}.\n"
                f"  A file this reader cannot parse is not a file with no "
                f"climb in it."]

    rooted = rooted_names(source, filename=path)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        right = node.right
        if not (isinstance(right, ast.Constant) and right.value in OUTSIDE):
            continue
        if not (_mentions_file(node.left) or _mentions_any(node.left, rooted)):
            continue
        found.append(
            f"REFUSED claude-home: {path}:{node.lineno} reaches "
            f"`{right.value}` by climbing parents from `__file__`.\n"
            f"  `{right.value}` is not in this repository. It lives under "
            f"`~/.claude` and has no worktree copy, so this climb finds it "
            f"only from the main checkout and lands on nothing from a "
            f"worktree.\n"
            f"  Resolve it against `Path.home() / \".claude\"` instead. Keep "
            f"the climb for paths INSIDE this checkout, which is the tree that "
            f"moves.")
    return found


def count_files(root):
    """How many python files a walk of `root` would read."""
    return len(list(_python_files(root)))


def _python_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs
                         if d != "__pycache__" and not os.path.exists(
                             os.path.join(base, d, ".git")))
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(base, name)


def walk(root):
    """Every refusal earned anywhere under `root`.

    A nested checkout is skipped for the reason `run_python_suites.py` skips
    one: it is another branch's tree and its faults are not this tree's.
    """
    found = []
    for path in _python_files(root):
        try:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
        except OSError as err:
            found.append(f"REFUSED claude-home: cannot read {path}: {err}.\n"
                         f"  A file this walker could not open is not a file "
                         f"that passed.")
            continue
        found.extend(refusals(source, os.path.relpath(path, root)))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=str(REPO),
                        help="the checkout to walk (default: this one)")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        print(f"check_claude_home: no such directory to walk: {args.root}",
              file=sys.stderr)
        return 2

    total = count_files(args.root)
    if not total:
        print(f"REFUSED empty-input: {args.root} holds no `.py` file this "
              f"walker could find.\n"
              f"  This is NOT a pass. A walk that read nothing and a walk that "
              f"found no fault look alike.", file=sys.stderr)
        return 2

    found = walk(args.root)
    if found:
        for refusal in found:
            print(refusal, file=sys.stderr)
        print(f"\nRefused: {len(found)} climb(s) to `~/.claude` across "
              f"{total} python file(s).", file=sys.stderr)
        return 1

    print(f"{total} python file(s) in {args.root}: none reaches "
          f"{', '.join(OUTSIDE)} by climbing from `__file__`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
