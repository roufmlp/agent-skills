#!/usr/bin/env python3
"""Refuse the git commands that reach across sessions in one checkout.

Blast radius, before anything else. This is a `PreToolUse` hook on the `Bash`
matcher. It reads one field, `tool_input.command`, and acts only when a word in
it is `git`. In a LINKED WORKTREE it refuses one thing: a bare `git stash` and a
`git stash pop`, because the stash stack is the one piece of git state a
worktree does not get its own copy of. In the MAIN checkout it also refuses a
wide `git add`, a `git commit` that names no paths, and the destructive
whole-tree commands. Every other git command passes, every non-Bash tool call
passes, and it writes nothing anywhere. On a payload it cannot parse, or on any
error of its own, it exits 0.

## The fault

A git worktree gets its own index. The MAIN checkout has exactly one, at
`.git/index`, and every session working there shares it. So a wide `git add` in
the main checkout stages whatever every other session has touched, and the
commit that follows carries work its message does not describe.

Two measured instances, about two hours apart:

    one   a session ran `cd <main> && git add -A && git commit`, meaning the
          `cd` only to reach a file. It committed 1,472 lines of another
          session's in-flight state under a message describing none of it.

    two   a session staged exactly two files BY NAME, having learnt from the
          first. Between its `git add` and its `git commit`, another session
          committed on main with a wide add and took both files with it. The
          victim's own commit then answered "no changes added to commit".

Instance two is why this is a guard and not a habit: staging explicit paths does
not protect you. Ruling 7 closes it — every commit in the main checkout names
its paths, so a commit can only carry what its author chose, whatever else sits
in the shared index.

## Scope

Every repository, with no worktree-count test (ruling 3). The reason: a reader
may cut worktrees in any of their repositories, and a day with none present does
not mean the session is alone. A guard that goes quiet on that evidence is worse
than no guard.

The main checkout is where git reports the same path for `--git-dir` and
`--git-common-dir`. A linked worktree has a private index and is never touched —
`git add -A` there is correct and common. The probe reads `git -C <dir>` and
`--git-dir` as the command gives them, because a command run FROM a worktree can
otherwise reach the main checkout around a working-directory test, and because
instance one reached it with a `cd`. Both are followed here.

One rule is wider than the checkout: the stash stack is shared by every worktree
of a repository, so ruling 13 refuses a bare `git stash` and a `git stash pop`
anywhere.

## What it does not do

It never tries to detect a second session (ruling 6). Detection adds a failure
mode that reports nothing when it is wrong, and the road costs one command. It
refuses always in the main checkout instead.

It holds no exception list (ruling 10). A wide but honest commit uses
`--pathspec-from-file`, so one rule holds for every commit: the commit names what
it carries.

The block mechanism — read the payload from stdin, write the reason to stderr,
exit 2 — is the documented PreToolUse contract, and every published hook beside
this one carries the same shape.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# Shell operators that end one simple command and start the next. `shlex.split`
# hands these back as their own tokens when they are unquoted, which is exactly
# the split wanted: a quoted `echo "git add -A"` stays one token and is never
# read as a git call.
OPERATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}"}

REDIRECT = re.compile(r"^\d*(>>?|<)$")

WORKTREE_ROAD = (
    "The road is a worktree: each one has a private index and working tree, "
    "so nothing you do there reaches another session."
)


# ---------------------------------------------------------------- parsing


def strip_heredocs(command):
    """Drop heredoc bodies before tokenising.

    `cat <<'EOF' ... git add -A ... EOF` carries the words of a git command
    inside data. Tokenised whole, the body reads as a git call and the guard
    refuses a write that was never a git call at all.
    """
    if "<<" not in command:
        return command
    lines = command.split("\n")
    kept = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        found = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        index += 1
        if not found:
            continue
        terminator = found.group(2)
        while index < len(lines) and lines[index].strip() != terminator:
            index += 1
        if index < len(lines):
            index += 1  # the terminator line itself
    return "\n".join(kept)


def simple_commands(command):
    """Every simple command in a bash line, as a list of words.

    Redirect tokens and their targets are dropped: `git log > /tmp/x` is a git
    call whose operands are `>` and `/tmp/x`, and neither is a pathspec.
    """
    try:
        words = shlex.split(strip_heredocs(command), posix=True)
    except ValueError:
        return []
    out = []
    current = []
    skip_next = False
    for word in words:
        if skip_next:
            skip_next = False
            continue
        if word in OPERATORS:
            if current:
                out.append(current)
            current = []
            continue
        if REDIRECT.match(word):
            skip_next = True
            continue
        current.append(word)
    if current:
        out.append(current)
    return out


def resolve(base, path):
    return os.path.normpath(os.path.join(base, os.path.expanduser(path)))


VALUE_OPTIONS = {"-c", "--work-tree", "--namespace", "--exec-path",
                 "--super-prefix", "--config-env", "--attr-source"}


def parse_git(words, cwd):
    """Split a git invocation into (directory, git-dir, subcommand argv).

    Global options come before the subcommand. `-C` is applied in order and
    cumulatively, the way git applies it, so `git -C a -C b` lands in `a/b`.
    """
    git_dir = None
    index = 1
    while index < len(words):
        word = words[index]
        if word == "-C" and index + 1 < len(words):
            cwd = resolve(cwd, words[index + 1])
            index += 2
        elif word.startswith("-C") and len(word) > 2:
            cwd = resolve(cwd, word[2:])
            index += 1
        elif word.startswith("--git-dir="):
            git_dir = word.split("=", 1)[1]
            index += 1
        elif word == "--git-dir" and index + 1 < len(words):
            git_dir = words[index + 1]
            index += 2
        elif word in VALUE_OPTIONS:
            index += 2
        elif word.startswith("-"):
            index += 1
        else:
            break
    return cwd, git_dir, words[index:]


# ---------------------------------------------------- where the command lands


_CHECKOUT_CACHE = {}


def is_main_checkout(cwd, git_dir):
    """True where this git call lands in a checkout whose index is shared.

    git reports the same path for `--git-dir` and `--git-common-dir` in the main
    checkout, and two different paths in a linked worktree. Nothing else is
    asked: no repository test, no worktree count (rulings 3 and 6).

    Anything unreadable — git missing, the directory gone, not a repository —
    answers False. A guard that cannot measure may not refuse.
    """
    key = (cwd, git_dir)
    if key in _CHECKOUT_CACHE:
        return _CHECKOUT_CACHE[key]
    answer = False
    argv = ["git", "-C", cwd]
    if git_dir:
        argv += ["--git-dir", git_dir]
    argv += ["rev-parse", "--git-dir", "--git-common-dir"]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        if done.returncode == 0:
            lines = done.stdout.strip().split("\n")
            if len(lines) == 2:
                paths = [os.path.realpath(resolve(cwd, line.strip())) for line in lines]
                answer = paths[0] == paths[1]
    except Exception:
        answer = False
    _CHECKOUT_CACHE[key] = answer
    return answer


# ------------------------------------------------------------- the rulings


def short_flags(word):
    """The letters of a bundled short option: `-am` is `a` and `m`."""
    if re.fullmatch(r"-[A-Za-z]+", word):
        return set(word[1:])
    return set()


def split_pathspec(argv):
    """(options-and-operands, paths-after-a-double-dash).

    `None` for the second where no `--` was written, which is different from an
    empty list: `git commit -- ` names no path, and `git commit` names none
    either, but only one of them tried.
    """
    if "--" in argv:
        cut = argv.index("--")
        return argv[:cut], argv[cut + 1:]
    return argv, None


def operands(argv):
    """Non-option words, ignoring anything after a `--` marker is handled by
    the caller. Option ARGUMENTS are not separated here, because none of the
    subcommands read below takes a value that could be mistaken for a path."""
    return [word for word in argv if not word.startswith("-")]


def names_everything(path):
    """Ruling 8's trigger for the destructive commands: a path that names the
    whole checkout rather than a file.

    Narrower than `is_wide_path`, and deliberately so. Ruling 8 refuses these
    four "where they name no path or name `.`", because an explicit path is how
    a session undoes its own edit; ruling 5's wider net covers staging only.
    """
    return path in (".", "./", "", "*", ":/")


def is_wide_path(path, cwd):
    """A pathspec that names more than one file the author chose.

    `.`, a glob, a magic pathspec, or a directory on disk. Ruling 5 names the
    directory case: `.scratch/example-feature/` holds the register and every
    run, and that is the class instance one committed.
    """
    if path in (".", "./", "", "*"):
        return True
    if path.startswith(":"):
        return True
    if any(character in path for character in "*?["):
        return True
    return os.path.isdir(os.path.join(cwd, os.path.expanduser(path)))


def refuse_add(argv, cwd):
    """Ruling 5: six forms count as wide. Only `git add <file path>` passes."""
    rest, after = split_pathspec(argv[1:])
    flags = set()
    for word in rest:
        flags |= short_flags(word)
        if word.startswith("--"):
            flags.add(word)
    if "A" in flags or "--all" in flags or "--no-ignore-removal" in flags:
        return "`git add -A` stages every change in the checkout, including every other session's."
    if "u" in flags or "--update" in flags:
        return "`git add -u` stages every tracked change in the checkout, including every other session's."
    paths = operands(rest) + (after or [])
    for path in paths:
        if is_wide_path(path, cwd):
            return f"`git add {path}` stages a whole directory or pattern, which reaches files other sessions are editing."
    return None


def refuse_commit(argv, cwd):
    """Rulings 5, 7, 9 and 10."""
    rest, after = split_pathspec(argv[1:])
    flags = set()
    pathspec_file = False
    for word in rest:
        flags |= short_flags(word)
        if word.startswith("--"):
            flags.add(word.split("=", 1)[0])
        if word.startswith("--pathspec-from-file"):
            pathspec_file = True
    if "--amend" in flags:
        return ("`git commit --amend` rewrites a commit that may not be yours: the "
                "index and HEAD in this checkout are shared by every session in it.")
    if "a" in flags or "--all" in flags:
        return "`git commit -a` commits every tracked change in the checkout, including every other session's."
    if pathspec_file:
        return None
    if after is None or not after:
        return ("a commit here carries whatever the shared index holds, which is "
                "every session's staged work and not only yours.")
    for path in after:
        if is_wide_path(path, cwd):
            return f"`-- {path}` names a whole directory or pattern, which is not naming what the commit carries."
    return None


def refuse_reset(argv):
    """Ruling 8 for `--hard`, ruling 9 for `--soft`."""
    flags = {word for word in argv[1:] if word.startswith("-")}
    for destructive in ("--hard", "--merge", "--keep"):
        if destructive in flags:
            return (f"`git reset {destructive}` throws away the working tree of every "
                    "session in this checkout, and there is nothing left to undo.")
    return None


def refuse_checkout(argv, cwd):
    """Ruling 8 for the wide restore, ruling 14 for the branch switch."""
    rest, after = split_pathspec(argv[1:])
    flags = {word for word in rest if word.startswith("-")}
    if flags & {"-b", "-B", "--orphan", "-t", "--track", "--detach"}:
        return ("`git checkout` here moves the branch under every other session "
                "working in this directory.")
    if after is not None:
        if not after or any(names_everything(path) for path in after):
            return ("`git checkout -- .` discards uncommitted edits across the "
                    "checkout, including edits other sessions have not committed yet.")
        return None
    names = operands(rest)
    if not names:
        return None
    first = names[0]
    if names_everything(first):
        return ("`git checkout .` discards uncommitted edits across the checkout, "
                "including edits other sessions have not committed yet.")
    if os.path.exists(os.path.join(cwd, os.path.expanduser(first))):
        return None  # an explicit path: a session undoing its own edit.
    return ("`git checkout` here moves the branch under every other session "
            "working in this directory.")


def refuse_switch(argv):
    """Ruling 14. Every form of `git switch` changes the branch."""
    return ("`git switch` here moves the branch under every other session "
            "working in this directory.")


def refuse_restore(argv, cwd):
    """Ruling 8."""
    rest, after = split_pathspec(argv[1:])
    paths = (after if after is not None else []) + operands(rest)
    if not paths:
        return ("`git restore` with no path discards uncommitted edits across the "
                "checkout, including edits other sessions have not committed yet.")
    for path in paths:
        if names_everything(path):
            return ("`git restore .` discards uncommitted edits across the checkout, "
                    "including edits other sessions have not committed yet.")
    return None


def refuse_clean(argv, cwd):
    """Ruling 8. A dry run reads and deletes nothing, so it passes."""
    rest, after = split_pathspec(argv[1:])
    flags = set()
    for word in rest:
        flags |= short_flags(word)
        if word.startswith("--"):
            flags.add(word)
    if "n" in flags or "--dry-run" in flags:
        return None
    paths = (after if after is not None else []) + operands(rest)
    if not paths:
        return ("`git clean` with no path deletes untracked files across the whole "
                "checkout, including files other sessions have just written.")
    for path in paths:
        if names_everything(path):
            return ("`git clean .` deletes untracked files across the whole checkout, "
                    "including files other sessions have just written.")
    return None


def refuse_stash(argv):
    """Ruling 13. Any checkout: the stash stack is shared by all of them."""
    rest = [word for word in argv[1:] if not word.startswith("-")]
    subcommand = rest[0] if rest else ""
    if not subcommand:
        return ("a bare `git stash` pushes an untagged entry onto a stack every "
                "worktree of this repository shares.")
    if subcommand == "pop":
        return ("`git stash pop` takes the TOP entry, which may be another "
                "session's, and removes it whether or not it applied cleanly.")
    return None


def road_for(subcommand):
    """Ruling 4: the refusal names the road. Four conventions in this repository
    failed because they asked a session to remember."""
    roads = {
        "add": ("Stage the files you changed, one path each:\n"
                "  git add <file> <file>\n"
                "Then commit them by name (see below). To find your own edits:\n"
                "  git status --short"),
        "commit": ("Name what the commit carries:\n"
                   "  git commit -m \"<message>\" -- <file> <file>\n"
                   "It commits those paths whatever else is staged, so another "
                   "session's work cannot ride along. For a wide but honest commit, "
                   "list the paths in a file:\n"
                   "  git commit -m \"<message>\" --pathspec-from-file=<file>\n"
                   "A commit still refuses a file git does not know yet, so a new "
                   "file needs its own `git add <path>` first."),
        "amend": ("Undo your own last commit instead, which loses no work:\n"
                  "  git log -1            # read the message first: is it yours?\n"
                  "  git reset --soft HEAD~1\n"
                  "Then re-commit by name:\n"
                  "  git commit -m \"<message>\" -- <file>"),
        "reset": ("To undo a wrong COMMIT, losing nothing:\n"
                  "  git log -1            # read the message first: is it yours?\n"
                  "  git reset --soft HEAD~1\n"
                  "To undo your own EDIT to one file:\n"
                  "  git restore <file>"),
        "restore": ("Name the file you want back:\n"
                    "  git restore <file>\n"
                    "  git checkout -- <file>"),
        "clean": ("Name what you want deleted:\n"
                  "  git clean -f <path>\n"
                  "Or read it first:\n"
                  "  git clean -nd"),
        "branch": ("Cut a worktree and switch there:\n"
                   "  git worktree add .claude/worktrees/<name> -b <branch>\n"
                   f"{WORKTREE_ROAD}"),
        "stash": ("Tag your entry, and never pop:\n"
                  "  git stash push -u -m \"<unique-tag>\"\n"
                  "  git stash list --format='%H %gs'        # find YOUR sha by tag\n"
                  "  git stash apply <sha>\n"
                  "  git stash drop stash@{n}                # re-find n by tag first\n"
                  "Better still, set work aside with a temporary WIP commit."),
    }
    return roads.get(subcommand, "")


# `git checkout` and `git switch` refuse for two different reasons and need two
# different roads, so the road is keyed on the reason rather than the subcommand.
def road_key(subcommand, reason):
    if "moves the branch" in reason:
        return "branch"
    if "--amend" in reason:
        return "amend"
    if subcommand in ("checkout", "switch"):
        return "restore"
    return subcommand


CHECKOUT_RULES = {
    "add": lambda argv, cwd: refuse_add(argv, cwd),
    "stage": lambda argv, cwd: refuse_add(argv, cwd),
    "commit": lambda argv, cwd: refuse_commit(argv, cwd),
    "reset": lambda argv, cwd: refuse_reset(argv),
    "checkout": lambda argv, cwd: refuse_checkout(argv, cwd),
    "switch": lambda argv, cwd: refuse_switch(argv),
    "restore": lambda argv, cwd: refuse_restore(argv, cwd),
    "clean": lambda argv, cwd: refuse_clean(argv, cwd),
}


def verdict(argv, cwd, main):
    """The reason this git call is refused, or None.

    `main` says whether the call lands in a checkout whose index is shared. The
    stash rule ignores it: the stack is shared by every worktree too.
    """
    if not argv:
        return None, ""
    subcommand = argv[0]
    if subcommand == "stash":
        return refuse_stash(argv), "stash"
    if not main:
        return None, ""
    rule = CHECKOUT_RULES.get(subcommand)
    if not rule:
        return None, ""
    return rule(argv, cwd), subcommand


# The stash rule holds in every checkout, so its refusal may not open with the
# shared-index sentence: a worktree's index is its own, and only the stack is
# shared. Saying otherwise would be a false statement in the one place a reader
# is most likely to believe the guard.
SHARED_INDEX = ("Every session working in this directory shares one git index, "
                "one HEAD and one working tree. There is no second copy: ")
SHARED_STACK = ("Every worktree of this repository shares one stash stack, this "
                "one included: ")


def refuse(command, cwd, reason, subcommand):
    preamble = SHARED_STACK if subcommand == "stash" else SHARED_INDEX
    where = "any checkout" if subcommand == "stash" else "a shared checkout"
    print(
        f"REFUSED — {command} in {where}.\n"
        f"  {cwd}\n"
        f"{preamble}{reason}\n\n"
        f"{road_for(road_key(subcommand, reason))}\n\n"
        "This closes two measured instances. In the second, the paths were "
        "staged explicitly by name and another session committed them anyway: "
        "naming what you stage does not protect it while the index is shared.",
        file=sys.stderr,
    )
    return 2


# ------------------------------------------------------------------- driver


def decide(payload):
    tool = str(payload.get("tool_name") or "")
    if tool != "Bash":
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if "git" not in command:
        return 0
    cwd = str(payload.get("cwd") or os.getcwd())

    for words in simple_commands(command):
        if not words:
            continue
        # `FOO=bar git ...`: an environment prefix is not the command name.
        index = 0
        while index < len(words) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[index]):
            index += 1
        words = words[index:]
        if not words:
            continue
        head = words[0]
        if head == "cd":
            # Instance one's `cd` was meant to reach a file, not to change where
            # git ran. It is followed here for exactly that reason.
            target = words[1] if len(words) > 1 else "~"
            if not target.startswith("-"):
                cwd = resolve(cwd, target)
            continue
        if os.path.basename(head) != "git":
            continue
        where, git_dir, argv = parse_git(words, cwd)
        reason, subcommand = verdict(argv, where, is_main_checkout(where, git_dir))
        if reason:
            return refuse("git " + " ".join(argv[:1]), where, reason, subcommand)
    return 0


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.
    try:
        return decide(payload)
    except Exception:
        return 0  # A guard that cannot measure may not refuse.


if __name__ == "__main__":
    sys.exit(main())
