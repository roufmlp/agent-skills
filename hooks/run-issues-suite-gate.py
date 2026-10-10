#!/usr/bin/env python3
"""Refuse a whole suite in a run unless it goes through the wrapper, at a stage
the caller owns.

Blast radius, before anything else. This is a `PreToolUse` hook on the `Bash`
matcher. It reads `tool_input.command`, `agent_type` and `cwd`, and acts only on
a command that launches a whole test suite: `npm test` and its cousins, or
`vitest` with no file or directory argument. The two implementer roles and
`run-issues-verify-gate` are refused a whole suite outside
`run-issues/run_suite.py`, and that wrapper at any stage but their own. A light
issue's implementer is refused every whole suite. The main session is refused
the same only inside the tree of a live `/run-issues` run, where it is the
runner. Everything else passes: a run that names a file or a directory, the
review gates, every other agent, the main session outside a live run's tree,
and every tool but Bash. It writes nothing. On a payload it cannot parse it
exits 0. Where it cannot read the live ledgers the main session's suite passes,
and where it cannot read an issue's level the issue is judged full. Each of the
three says so on stderr.

Issue 18 of the tracker-tooling set, `the runner runs only its own three
suites`, fix F5 of an audit of 2026-09-23.

WHY. Four runs on one project spent 665 minutes on 206 whole suites. The runner
ran 20 of them, 77 minutes, after an earlier ruling had moved the
per-issue coverage suite to the verify gate; nothing refused a runner suite, so
the move held as long as the runner remembered it. Implementers ran 128, and 62
of those re-read an unchanged tree. `run-issues/run_suite.py` refuses the
repeat; this hook makes the wrapper the only road to a whole suite in a run.

WHAT IS REFUSED, and nothing else:

1. `run-issues-implementer` and `run-issues-implementer-escalated`: a whole
   suite outside the wrapper, anywhere, and the wrapper at any stage but
   `issue`.
2. The MAIN SESSION inside a tree a live RUN owns, which is the runner: a whole
   suite outside the wrapper, and the wrapper at any stage but its three.
   `baseline` and `correction` pass while the run's ledger names no finale
   stage; `finale` passes only once its `State:` line names one.

3. `run-issues-verify-gate`: a whole suite outside the wrapper, and the wrapper
   at any stage but `verify`. The perf audit of 2026-09-28 (fix 2): at `verify` the
   wrapper reuses the implementer's record for the same tree, and a bare
   `npx vitest run --coverage` in the gate's copy read that tree a second time
   and kept nothing.

A LIGHT ISSUE'S IMPLEMENTER, tracker-tooling issue 40 (rule 5): any whole
suite, the wrapper at `issue` included. Its road is `scoped_suite.py` beside
the wrapper: every test whose imports reach its change, and the repo-wide
checks (the perf audit's fix 4). The finale runs the one whole suite. The level is read on every such
call by `issue_level.py` (see SKILL_DIR below), from the issue file of the one
row in progress in the live run owning the call's directory, in the run's own
tree, and never cached. Anything it cannot read runs as full, said on stderr.

THREE RUNNER READINGS, NOT TWO. The audit's F5 names the baseline and the
finale. Issue 06 of the set, `three suites per issue`, rules a third: the
coverage re-run after a correction round, which `check_diff_coverage.py`'s
docstring explains. Refusing it would break that re-run. Issue 18 records this
as a default.

WHAT A WHOLE SUITE IS. `npm test`, `npm run test`, `npm t`, the same under
`pnpm`, `yarn` or `bun`, or `vitest` by any path, with no argument that names a
file or a directory. An argument names one when it holds a `/`, ends in a script
suffix, or holds `.test` or `.spec`. The value of an option that takes one is
skipped, so `--config vitest.conformance.config.ts` and `--coverage.include
src/**` do not read as filters, and a `-t` name filter or a bare word does not
narrow the run: vitest still loads every file and builds every database. A
wrong refusal here costs one reissue with a path; a wrong pass costs a suite.

ONLY A LAUNCH IS JUDGED. The word a shell runs, past assignments and launchers
(`timeout 600`, `npx --yes`, `env`, `node`, `pnpm exec`), is the one read. A
launcher option that takes a value skips it too, so `env -u DATABASE_URL npm
test` reads `npm` and not `DATABASE_URL` (issue 31 of the set). The string after
`env -S` is split and read as the command it is.
`npm ls vitest` and `grep vitest package.json` name the suite and run none. A
string handed to `sh -c`, `bash -c` or `eval` is read as a command of its own,
and so is the command after `run_step.py`'s `--`.

WHERE. The session's working directory, moved by any `cd` or `pushd` earlier in
the same command and put back where a subshell closes. Of the live runs whose
tree holds it, the deepest owns it.

LET PAST: the review gates, which run no whole suite by their briefs; every
other agent type; and the main session
outside a live run's tree, which is the human's own. A hunt is not a run here.

LIMITS, as facts. A command that reaches the suite through a script of its own
(`bash run-all.sh`) is not read, and neither is `npm --prefix <tree> test` from
outside the tree. The runner's own suites in the audit all used `cd`.

IT NEVER HALTS A RUN. A refusal answers one tool call and prints the command to
reissue. It fails OPEN on anything it cannot read, and says so on stderr.

Drill: `test_run_issues_suite_gate.py` beside this file.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import importlib.util
import json
import os
import re
import shlex
import sys

# The ledger selector and the finale's stage reader live beside the skill.
# Imported by path, never copied: one definition of "live", and one of "the
# State line names".
#
# `RUN_ISSUES_SKILL_DIR` points it at another copy, which is how
# `lib/run_python_suites.py` drills this hook against the skills tree it was
# handed. Unset, the `skills/run-issues` directory beside this hook's own
# directory: `~/.claude/skills/run-issues` once installed.
SKILL_DIR = os.environ.get("RUN_ISSUES_SKILL_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "skills", "run-issues")

WRAPPER = "run_suite.py"
WRAPPER_COMMAND = "python3 ~/.claude/skills/run-issues/run_suite.py"

IMPLEMENTERS = ("run-issues-implementer", "run-issues-implementer-escalated")
VERIFY_GATE = "run-issues-verify-gate"
JUDGED = (*IMPLEMENTERS, VERIFY_GATE)

# `check_finale_stage.py`'s CHAIN. A State line naming any of them means the
# finale has started.
FINALE_STAGES = ("finale-mechanical", "finale-judgment", "finale-promotion",
                 "finale-board", "awaiting-merge")

AFK = (
    "\n\nTHIS IS NOT A HALT AND IT NEVER WAITS FOR THE HUMAN. The human is AFK "
    "for every run. Reissue the call as above and carry on.\n"
    "(Gate: ~/.claude/hooks/run-issues-suite-gate.py)"
)

# Tokens that end one command and start the next. A redirect is not one: its
# next token is a file the command writes, never an argument it reads.
SEPARATORS = {"&&", "||", ";", ";;", "|", "|&", "&", "(", ")"}
REDIRECTS = {">", ">>", "<", ">&", "&>", "&>>", "<<", "<<<", ">|"}
# The characters shlex's `punctuation_chars` groups into one word.
PUNCTUATION = set("();<>|&")

PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
TEST_SCRIPTS = {"test", "t"}

# Words that run the word after them. Their own options are skipped, and
# `timeout` also takes a duration.
LAUNCHERS = {"time", "nohup", "command", "exec", "env", "timeout", "npx",
             "pnpx", "bunx", "node", "caffeinate"}
# Launcher options that take their value in the next word. The env and
# timeout rows are `run-issues/run_costs.py`'s, from issue 29 of the set, plus
# `-P altpath`, which the BSD `env` on macOS takes. The caffeinate, npx and
# node rows are the other launchers above whose manuals name a value option.
# `env -S` is read by `split_string`.
LAUNCHER_VALUE_OPTIONS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-P"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "caffeinate": {"-t", "-w"},
    "npx": {"-p", "--package"},
    "node": {"-r", "--require", "--import", "--loader", "-C", "--conditions"},
}
# Shell words that open a command without being one: `for ...; do npm test`.
KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{"}
SHELLS = {"sh", "bash", "zsh", "dash"}
PYTHONS = {"python", "python3"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# The finale's step clock. It runs the command after its own `--`, so that
# command is read in its place.
STEP_CLOCK = "run_step.py"

# vitest options that take a value in the next token. A value is never a file
# filter, and `--config vitest.conformance.config.ts` would otherwise read as
# one. `--coverage.*` is judged by prefix below.
VALUE_OPTIONS = {
    "-c", "--config", "-r", "--root", "--dir", "--project", "--reporter",
    "--outputFile", "--maxWorkers", "--minWorkers", "--pool", "--environment",
    "-t", "--testNamePattern", "--shard", "--mode", "--workspace", "--exclude",
    "--bail", "--retry", "--testTimeout", "--hookTimeout", "--sequence.seed",
}

FILE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")


def tokens_of(command):
    """The command as shell words, with operators as words of their own."""
    text = command.replace("\n", " ; ")
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        # An unclosed quote. The shell would not run it either, but the
        # operators are still split out, so no suite hides behind the quote.
        return re.sub(r"(&&|\|\||[;|&()])", r" \1 ", text).split()
    split = []
    for word in words:
        split.extend(operators_in(word) if word and set(word) <= PUNCTUATION
                     else [word])
    return split


def operators_in(run):
    """shlex keeps a run of operator characters as one word: `);` and `)&&`.
    Split it into the operators a shell reads, longest first."""
    found, at = [], 0
    while at < len(run):
        for size in (3, 2, 1):
            piece = run[at:at + size]
            if len(piece) == size and piece in SEPARATORS | REDIRECTS:
                found.append(piece)
                at += size
                break
        else:
            found.append(run[at])
            at += 1
    return found


def segments_of(command):
    """Each simple command, as a list of words, with redirect targets dropped.

    A subshell's brackets come through as the strings "(" and ")" between the
    lists, so a `cd` inside one can be ended where the subshell ends."""
    segments, current, skip = [], [], False
    for word in tokens_of(command):
        if skip:
            skip = False
            continue
        if word in SEPARATORS:
            segments.append(current)
            current = []
            if word in ("(", ")"):
                segments.append(word)
        elif word in REDIRECTS:
            skip = True
        else:
            current.append(word)
    segments.append(current)
    return [s for s in segments if s]


def is_file_filter(word):
    """True when an argument narrows vitest to files or a directory."""
    return ("/" in word or word.endswith(FILE_SUFFIXES)
            or ".test" in word or ".spec" in word)


def narrows(arguments):
    """True when any argument to the suite names a file or a directory."""
    skip = False
    for word in arguments:
        if skip:
            skip = False
            continue
        if word == "--":
            continue
        if word.startswith("-"):
            if "=" not in word and (word in VALUE_OPTIONS
                                    or word.startswith("--coverage.")):
                skip = True
            continue
        if is_file_filter(word):
            return True
    return False


def split_string(words, at):
    """`env -S STRING`, in any of its four spellings, as (the words STRING
    splits into, the index after it), or None when words[at] is not one."""
    word = words[at]
    if word in ("-S", "--split-string"):
        if at + 1 >= len(words):
            return None
        text, after = words[at + 1], at + 2
    elif word.startswith("--split-string="):
        text, after = word.split("=", 1)[1], at + 1
    elif word.startswith("-") and not word.startswith("--"):
        # A cluster such as `-iS'npm test'` or `-iS 'npm test'`. A value
        # letter before the S takes the rest of the word as its value.
        for index, letter in enumerate(word[1:], 1):
            if letter == "S":
                break
            if "-" + letter in LAUNCHER_VALUE_OPTIONS["env"]:
                return None
        else:
            return None
        if index + 1 < len(word):
            text, after = word[index + 1:], at + 1
        elif at + 1 < len(words):
            text, after = words[at + 1], at + 2
        else:
            return None
    else:
        return None
    try:
        return shlex.split(text), after
    except ValueError:
        return text.split(), after


def takes_next(word, takes_value):
    """True when this option word leaves its value to the next word: `-u`, or
    a cluster that ends in a value letter, `-iu`. `-uNAME` holds its own."""
    if word in takes_value:
        return True
    if word.startswith("--") or len(word) < 3:
        return False
    for index, letter in enumerate(word[1:], 1):
        if "-" + letter in takes_value:
            return index == len(word) - 1
    return False


def launched(words):
    """The words a shell RUNS, past assignments, keywords and launchers.

    Only their first word is judged. `npm ls vitest` and `grep vitest
    package.json` name the suite without running it; review finding 1 of
    2026-09-23 caught a reader that judged every word.
    """
    at = 0
    while at < len(words):
        word = words[at]
        if ASSIGNMENT.match(word) or word in KEYWORDS:
            at += 1
            continue
        name = os.path.basename(word)
        if name not in LAUNCHERS:
            break
        at += 1
        takes_value = LAUNCHER_VALUE_OPTIONS.get(name, set())
        while at < len(words) and (words[at].startswith("-")
                                   or ASSIGNMENT.match(words[at])):
            split = split_string(words, at) if name == "env" else None
            if split:
                return launched(split[0] + words[split[1]:])
            at += 2 if takes_next(words[at], takes_value) else 1
        if name == "timeout" and at < len(words):
            at += 1                     # the duration
    return words[at:]


def stage_of(arguments):
    """The wrapper's `--stage`, read up to its own `--`, or None."""
    for index, arg in enumerate(arguments):
        if arg == "--":
            break
        if arg.startswith("--stage="):
            return arg.split("=", 1)[1]
        if arg == "--stage" and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


def after_dashes(arguments):
    """The command after a step clock's own `--`, or []."""
    return arguments[arguments.index("--") + 1:] if "--" in arguments else []


def classify(words):
    """What this simple command launches, as a list of (kind, stage) and
    scripts to read in its place: `wrapper`, `suite`, or a string handed to
    `sh -c` or `eval`, which is returned as ("script", text)."""
    words = launched(words)
    if not words:
        return []
    name, rest = os.path.basename(words[0]), words[1:]

    if name in SHELLS:
        if "-c" in rest and rest.index("-c") + 1 < len(rest):
            return [("script", rest[rest.index("-c") + 1])]
        return []
    if name == "eval":
        return [("script", " ".join(rest))]
    if name in PYTHONS:
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        if not rest:
            return []
        name, rest = os.path.basename(rest[0]), rest[1:]
    if name == WRAPPER:
        return [("wrapper", stage_of(rest))]
    if name == STEP_CLOCK:
        return classify(after_dashes(rest))
    if name in PACKAGE_MANAGERS:
        if rest[:1] and rest[0] in TEST_SCRIPTS:
            return [] if narrows(rest[1:]) else [("suite", None)]
        if rest[:2] == ["run", "test"]:
            return [] if narrows(rest[2:]) else [("suite", None)]
        if rest[:1] == ["exec"]:
            return classify(rest[1:])
        if rest[:1] and os.path.basename(rest[0]) == "vitest":
            return classify(rest)
        return []
    if name == "vitest":
        if rest[:1] and rest[0] in ("--help", "-h", "--version", "-v"):
            return []
        return [] if narrows(rest) else [("suite", None)]
    return []


def calls_of(command, cwd, depth=0):
    """Every suite this command launches: (kind, stage, directory).

    kind is `wrapper` or `suite`. The directory is the session's, moved by any
    `cd` earlier in the same command and restored where a subshell closes.
    """
    found, here, saved = [], cwd, []
    for words in segments_of(command):
        if words == "(":
            saved.append(here)
            continue
        if words == ")":
            here = saved.pop() if saved else here
            continue
        if words[0] in ("cd", "pushd"):
            target = os.path.expanduser(words[1] if len(words) > 1 else "~")
            here = os.path.normpath(os.path.join(here, target))
            continue
        for kind, detail in classify(words):
            if kind == "script":
                if depth < 3:
                    found.extend(calls_of(detail, here, depth + 1))
            else:
                found.append((kind, detail, here))
    return found


def _inside(child, parent):
    child, parent = os.path.normpath(child), os.path.normpath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def owning_run(directory, runs):
    """The live run whose tree holds this directory. The DEEPEST such tree:
    a project's run trees may nest under its main checkout."""
    holding = [(tree, state) for tree, state in runs if _inside(directory, tree)]
    if not holding:
        return None
    return max(holding, key=lambda run: len(os.path.normpath(run[0])))


def implementer_reason(agent_type, kind, stage):
    if kind == "suite":
        return (
            f"Refused: `{agent_type}` ran a whole suite outside the wrapper. "
            f"Run it once, at the end, through the wrapper:\n"
            f"  {WRAPPER_COMMAND} --stage issue --spawn final -- <the ledger "
            f"header's Full suite: command>\n"
            f"The logic spawn of a screen issue runs no whole suite, and the "
            f"final spawn runs it after a green or WIDE reading of the same "
            f"tree from `scoped_suite.py --whole-if-wide`. The wrapper refuses both otherwise.\n"
            f"It keeps the whole output in a log and prints the log's path, "
            f"vitest's summary and the failing files, so the suite never needs "
            f"a second run to be read. Scoped runs, a file or a directory, pass "
            f"this gate untouched." + AFK)
    if stage == "issue":
        return None
    return (
        f"Refused: `{agent_type}` called the wrapper at stage `{stage}`. An "
        f"implementer's stage is `issue`; baseline, correction and finale are "
        f"the runner's readings. Reissue with --stage issue --spawn final." + AFK)


def verify_reason(kind, stage):
    if kind == "wrapper" and stage == "verify":
        return None
    shown = "a whole suite outside the wrapper" if kind == "suite" else (
        f"the wrapper at stage `{stage}`" if stage else "the wrapper with no --stage")
    return (
        f"Refused: `{VERIFY_GATE}` ran {shown}. The verify gate's one whole "
        f"suite is the wrapper at its own stage, from inside the copy "
        f"make_copy.py made:\n"
        f"  {WRAPPER_COMMAND} --stage verify -- <the ledger header's Full suite: "
        f"command>\n"
        f"Where the implementer's suite already read this tree, the wrapper "
        f"reuses that record and prints its report, and no suite starts. A "
        f"named test file, run alone, passes this gate." + AFK)


def light_reason(agent_type):
    return (
        f"Refused: `{agent_type}` is working a `Level: light` issue, and a light "
        f"issue runs no whole suite of its own. Its one suite is the scoped "
        f"one, which runs every test whose "
        f"imports reach your change and the repo-wide checks, with coverage:\n"
        f"  python3 ~/.claude/skills/run-issues/scoped_suite.py\n"
        f"The finale runs the one whole suite for the whole run, once." + AFK)


def runner_reason(tree, state, kind, stage):
    in_finale = state in FINALE_STAGES
    if kind == "wrapper":
        if stage == "finale" and in_finale:
            return None
        if stage in ("baseline", "correction") and not in_finale:
            return None
    shown = "a whole suite outside the wrapper" if kind == "suite" else (
        f"the wrapper at stage `{stage}`" if stage else
        "the wrapper with no --stage")
    where = (f"its ledger's State line names `{state}`" if state else
             "its ledger's State line names no finale stage yet")
    return (
        f"Refused: the runner ran {shown} inside the run tree {tree}, and "
        f"{where}.\n"
        f"The runner takes three whole-suite readings, each through the "
        f"wrapper, and no other:\n"
        f"  {WRAPPER_COMMAND} --stage baseline -- <suite>    before the first "
        f"spawn, once per run\n"
        f"  {WRAPPER_COMMAND} --stage correction -- <suite>  SKILL.md step 5's "
        f"coverage re-run after a correction round\n"
        f"  {WRAPPER_COMMAND} --stage finale -- <suite>      finale.md step 1, "
        f"once the State line names a finale stage\n"
        f"Every other reading of an issue's tree is the verify gate's, in its "
        f"own copy. Read its "
        f"report, or the wrapper's log of the last run, instead of running "
        f"the suite again." + AFK)


def decide(agent_type, command, cwd, runs, level_of=None):
    """The refusal to print, or None to let the call through. Pure.

    `runs` is every live run as (the tree it owns, the finale stage its
    ledger's State line names, or None). `level_of` answers `light` or `full`
    for a directory an implementer's suite runs in; None reads full."""
    if agent_type and agent_type not in JUDGED:
        return None
    for kind, stage, directory in calls_of(command, cwd):
        if agent_type == VERIFY_GATE:
            reason = verify_reason(kind, stage)
        elif agent_type:
            if level_of is not None and level_of(directory) == "light":
                return light_reason(agent_type)
            reason = implementer_reason(agent_type, kind, stage)
        else:
            run = owning_run(directory, runs)
            if run is None:
                continue
            reason = runner_reason(run[0], run[1], kind, stage)
        if reason:
            return reason
    return None


def _load(name):
    path = os.path.join(SKILL_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def live_runs(cwd):
    """Every live RUN as (the tree it owns, the finale stage its State line
    names, or None).

    The tree is the one the ledger's `Worktree:` line names, never the tree its
    copy sits in: a live copy sits in the main checkout, and a project's run
    trees may nest under it. A hunt is not a run
    and is not judged: the audit's runner suites are a run's.
    """
    ledger = _load("find_live_ledger")
    stage = _load("check_finale_stage")
    candidates = ledger.collect_candidates(worktrees=ledger.list_worktrees(cwd))
    return tuple(
        (ledger.parse_worktree_value(item.worktree_line) or item.tree,
         stage.read_state(item.scope_text or ""))
        for item in ledger.runs(candidates))


def issue_level_of(directory):
    """`light` or `full`: the level of the issue in progress in the live run
    owning `directory`, read now through `issue_level.py`. Fails to full."""
    try:
        ledger = _load("find_live_ledger")
        levels = _load("issue_level")
        candidates = ledger.collect_candidates(
            worktrees=ledger.list_worktrees(directory))
        owner = owning_run(directory, [
            (ledger.parse_worktree_value(item.worktree_line) or item.tree, item)
            for item in ledger.runs(candidates)])
        if owner is None:
            return "full"
        item = owner[1]
        reading = levels.read_live_level(item.path, item.scope_text or None)
    except Exception as err:  # not a git repo, the reader missing, git hung
        print(f"run-issues-suite-gate: cannot read the issue's level ({err}), "
              "so it runs as full.", file=sys.stderr)
        return "full"
    if reading.note:
        print(f"run-issues-suite-gate: {reading.note}.", file=sys.stderr)
    return reading.level


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        print(f"run-issues-suite-gate: unreadable payload ({err}), so the call "
              "passed unchecked.", file=sys.stderr)
        return 0
    tool_input = payload.get("tool_input")
    command = str((tool_input or {}).get("command") or "") \
        if isinstance(tool_input, dict) else ""
    agent_type = str(payload.get("agent_type") or "")
    cwd = str(payload.get("cwd") or os.getcwd())

    # Every Bash call on this machine reaches this hook. The parse is cheap and
    # pure; the ledger read is a `git worktree list` and a walk, so only a call
    # that launches a suite pays for it, and only the main session needs it.
    if agent_type and agent_type not in JUDGED:
        return 0
    if not calls_of(command, cwd):
        return 0
    runs = ()
    if not agent_type:
        try:
            runs = live_runs(cwd)
        except Exception as err:  # not a git repo, git hung, selector missing
            print(f"run-issues-suite-gate: cannot read the live ledgers "
                  f"({err}), so the suite passed unchecked.", file=sys.stderr)
            return 0

    levels = {}

    def level_of(directory):
        if directory not in levels:
            levels[directory] = issue_level_of(directory)
        return levels[directory]

    reason = decide(agent_type, command, cwd, runs,
                    level_of if agent_type in IMPLEMENTERS else None)
    if reason is None:
        return 0
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
