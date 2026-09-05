#!/usr/bin/env python3
"""The per-run model map: parse it, resolve it, refuse an inverted one.

Ticket 39 of the pilot-delivery map, every-worker-inherits-the-session-model,
sitting 1 (rulings 1, 3, 4, 5, 6, 7, 14, 20).

Before this, every one of the twelve loop agent files read `model: inherit` and
nothing passed a `model` on a spawn, so a whole run or hunt ran on whatever the
session was started with. The map names a model per role for one run:

    /run-issues 512 513 models: implementer=opus gates=fable
    /parallel-hunt <scope> models: finder=fable fixer=opus

One grammar for both (ruling 20). The twelve agent files stay `model: inherit`
(ruling 6), so a spawn by hand behaves as it always did; the map reaches a run
only through the ledger the launch line writes.
"""

import importlib.util
import os
import re
import subprocess


def _grammar():
    """`find_live_ledger.py` owns the `models:` word, because it owns the scope
    grammar that has to stop at it (ruling 20: one grammar, one parser).

    Loaded by path, the way `machine-preflight.py` loads the same file: these two
    always ship in one directory, and the hook already dies without that file, so
    this adds no failure mode the launch did not already have.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "find_live_ledger.py")
    spec = importlib.util.spec_from_file_location("find_live_ledger", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GRAMMAR = _grammar()
MODELS_WORD = _GRAMMAR.MODELS_WORD
split_models = _GRAMMAR.split_models

# `force-machine`, `force-version`, `force-model`. The scope grammar has skipped
# these since they existed, and this one did not, so
# `models: implementer=opus force-model` was refused as a typo -- found by the
# 2026-09-05 review of sitting 2. They are addressed to `machine-preflight.py`,
# not to the map, and a person types them where the sentence ends.
OVERRIDE_WORDS = _GRAMMAR.OVERRIDE_WORDS

# The four the Agent tool accepts. No other model is reachable per role: the
# 2026-08 harden-issues DeepSeek arm pointed a whole session at another API.
MODELS = ("haiku", "sonnet", "opus", "fable")

# Ruling 14's tier order, cheapest first. The index is the tier.
TIER = {name: index for index, name in enumerate(MODELS)}

INHERIT = "inherit"

# Ruling 5: one key per agent type, without its prefix.
ROLES = {
    "implementer": "run-issues-implementer",
    "escalated": "run-issues-implementer-escalated",
    "verify": "run-issues-verify-gate",
    "review": "run-issues-review-gate",
    "review-critical": "run-issues-review-gate-critical",
    "finale": "run-issues-finale",
    "finder": "parallel-hunt-finder",
    "fixer": "parallel-hunt-fixer",
    "claim-gate": "parallel-hunt-claim-gate",
    "fix-gate": "parallel-hunt-fix-gate",
    "fix-gate-critical": "parallel-hunt-fix-gate-critical",
    "promotion": "promotion",
}

# The roles that build. A gate checks one of these, and ruling 14 refuses a gate
# below the worker it checks.
WORKERS = ("implementer", "escalated", "finder", "fixer")

# The adversarial gates.
GATES = ("verify", "review", "review-critical",
         "claim-gate", "fix-gate", "fix-gate-critical")

GROUPS = {"all": tuple(ROLES), "workers": WORKERS, "gates": GATES}

# Which roles each command can actually spawn. `all` names twelve and the ledger
# header records twelve, because one grammar serves both (ruling 20). But a run
# never spawns a finder and a hunt never spawns a verify gate, so a guard asking
# "what still inherits the session tier" must count only what can run --
# otherwise it refuses a hunt whose every spawn is named and lists six roles that
# cannot start. Found by the 2026-09-05 review of sitting 2.
SPAWNED_BY = {
    "/run-issues": ("implementer", "escalated", "verify", "review",
                    "review-critical", "finale", "promotion"),
    "/parallel-hunt": ("finder", "fixer", "claim-gate", "fix-gate",
                       "fix-gate-critical", "promotion"),
}

# Least specific first. A later entry overrides an earlier one, which is
# ruling 5's "more specific wins".
SPECIFICITY = ("all", "workers", "gates")

TOKEN = re.compile(r"^([A-Za-z][A-Za-z-]*)=([A-Za-z0-9.-]+)$")


def parse_map(text):
    """`(assignments, bad)` for the map half of a launch line.

    `assignments` is `[(key, model), ...]` in the order typed, where `key` is a
    group name or a role name and `model` is one of `MODELS` or `inherit`.
    A token the grammar cannot read goes into `bad` rather than being dropped,
    for the same reason the scope grammar reports its own: a dropped token is a
    run that silently ran on a model nobody chose.
    """
    assignments, bad = [], []
    for word in (text or "").replace(",", " ").split():
        if word.lower() in OVERRIDE_WORDS:
            continue
        match = TOKEN.match(word)
        if not match:
            bad.append(word)
            continue
        key, model = match.group(1).lower(), match.group(2).lower()
        if key not in GROUPS and key not in ROLES:
            bad.append(word)
        elif model != INHERIT and model not in MODELS:
            bad.append(word)
        else:
            assignments.append((key, model))
    return assignments, bad


def tier_name(model):
    """The bare tier in a model name, or None.

    The ledger records what the process command line carries (`claude-opus-5`,
    `claude-haiku-4-5-20251001`); the Agent tool's `model` field takes the bare
    tier. Longest name first, so nothing matches a substring of another.
    """
    if not model:
        return None
    text = model.strip().lower()
    for name in sorted(MODELS, key=len, reverse=True):
        if name in text:
            return name
    return None


def apply_map(assignments):
    """`{role: model}` for all twelve roles, `inherit` where the map is silent.

    Ruling 5's "more specific wins, whatever the order typed": the assignments
    are ranked by how specific their key is, and only ties are broken by the
    order they were typed in.
    """
    applied = {role: INHERIT for role in ROLES}
    ranked = sorted(
        enumerate(assignments),
        key=lambda pair: (SPECIFICITY.index(pair[1][0])
                          if pair[1][0] in SPECIFICITY else len(SPECIFICITY),
                          pair[0]),
    )
    for _, (key, model) in ranked:
        for role in GROUPS.get(key, (key,)):
            applied[role] = model
    return applied


def inheriting(applied):
    """The roles a map leaves taking the session's model, in `ROLES` order.

    Empty means the session tier reaches no spawn in the run, which is what
    `machine-preflight.py` row 14 needs to know: the fault that guard exists to
    refuse is a tier chosen by SILENCE, and a map that names every role has
    chosen one out loud.
    """
    return tuple(role for role in ROLES if applied.get(role) == INHERIT)


def substitute_inherit(applied, session_model):
    """`applied` with every `inherit` replaced by the session's own tier.

    `session_model` is what the launch line measured off the process command
    line. It is read only where something still says `inherit`; a map that
    names every role does not need it, which is why an unreadable session model
    is not refused until it is actually wanted. Where it is wanted and cannot be
    read, this raises rather than guessing: a guessed stamp is worse than a
    missing one, because the next reader treats it as evidence.
    """
    if INHERIT not in applied.values():
        return dict(applied)
    inherited = tier_name(session_model)
    if inherited is None:
        raise ValueError(
            f"the session model reads {session_model!r}, which names none of "
            f"{', '.join(MODELS)}. `inherit` cannot be resolved, and a guessed "
            "stamp is worse than a missing one. Name every role in the map, or "
            "measure the session model before the launch line runs."
        )
    return {role: (inherited if model == INHERIT else model)
            for role, model in applied.items()}


def resolve(assignments, session_model):
    """`{role: model}` for all twelve roles, every value one of `MODELS`.

    Ruling 4: resolved fully at launch, so `inherit` never reaches a ledger and
    a resume on a different session model changes the orchestrator only.
    """
    return substitute_inherit(apply_map(assignments), session_model)


# Ruling 14, stated as the pairs it names: `(gate, worker)`. A gate checks
# exactly the workers listed against it and no others, which is why a cheap
# hunt finder beside an expensive run implementer is not an inversion.
CHECKS = (
    ("verify", "implementer"),
    ("verify", "escalated"),
    ("review", "implementer"),
    ("review", "escalated"),
    ("review-critical", "implementer"),
    ("review-critical", "escalated"),
    ("claim-gate", "finder"),
    ("fix-gate", "fixer"),
    ("fix-gate-critical", "fixer"),
)


def inversions(resolved):
    """The refusals a resolved map earns, one line each, empty when it is legal.

    Ruling 1 keeps the 2026-08-15 gate-tier ruling standing and asks this
    predicate to refuse at launch, which is where it was always meant to be:
    that ruling asked for it and it was never built. Equal is legal (ruling 14).
    """
    return [
        f"`{gate}={resolved[gate]}` sits below `{worker}={resolved[worker]}` — "
        f"raise {gate} to {resolved[worker]} or above, or lower {worker}"
        for gate, worker in CHECKS
        if TIER[resolved[gate]] < TIER[resolved[worker]]
    ]


SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MAP_FILE = os.path.join(SKILL_DIR, "model-map.default")
AGENTS_DIR = os.path.expanduser("~/.claude/agents")

COMMENT = re.compile(r"#.*$", re.MULTILINE)
# The frontmatter block only. A brief's body is long prose ABOUT how hard to
# work, so an unbounded search would read a sentence as a measurement the first
# time a file lost its frontmatter key.
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
EFFORT_LINE = re.compile(r"^effort:\s*(\S+)\s*$", re.MULTILINE)

UNMEASURED = "unmeasured"


def read_default_map(path=None):
    """The default map's text, comments stripped (ruling 3).

    A missing file reads as `all=inherit`, which is what every run did before
    the map existed. The file is a default, not a control: losing it must not
    stop a launch.
    """
    try:
        with open(path or DEFAULT_MAP_FILE, encoding="utf-8") as handle:
            text = COMMENT.sub("", handle.read())
    except OSError:
        return "all=inherit"
    return " ".join(text.split()) or "all=inherit"


def role_efforts(agents_dir=AGENTS_DIR):
    """`{role: effort}` read off the twelve agent files (ruling 7).

    Effort cannot ride on a spawn -- the Agent tool takes `model` and no effort
    field -- so it lives in the agent file frontmatter and the ledger only
    records it. A file that cannot be read records `unmeasured`, never a guess,
    for the reason SKILL.md gives about the session model: a guessed stamp is
    treated as evidence by the next reader.
    """
    efforts = {}
    for role, agent_type in ROLES.items():
        try:
            with open(os.path.join(agents_dir, agent_type + ".md"),
                      encoding="utf-8") as handle:
                head = handle.read(4096)
        except OSError:
            efforts[role] = UNMEASURED
            continue
        block = FRONTMATTER.search(head)
        match = EFFORT_LINE.search(block.group(1)) if block else None
        efforts[role] = match.group(1) if match else UNMEASURED
    return efforts


MAP_LABEL = "Model map at launch:"
EFFORT_LABEL = "Role effort at launch:"
MAP_LINE = re.compile(r"^" + re.escape(MAP_LABEL) + r"\s*`([^`]*)`", re.MULTILINE)


def header_lines(resolved, efforts, session_model, typed):
    """The two ledger header lines the launch writes (rulings 4 and 7).

    One line each, both a single `role=value` list in the order of `ROLES`, both
    read back by `ledger_map`. Two lines rather than a twelve-row table because
    every line in `run.md` is billed on every spawn, and a dozen spawns a run is
    the low end.
    """
    models = " ".join(f"{role}={resolved[role]}" for role in ROLES)
    stated = " ".join(f"{role}={efforts[role]}" for role in ROLES)
    return (
        f"{MAP_LABEL} `{models}`\n"
        f"  (resolved from `{typed}`, against session model `{session_model}`; "
        f"ticket 39, rulings 4 and 5. Every spawn carries its role's value.)\n"
        f"{EFFORT_LABEL} `{stated}`\n"
        f"  (read from the agent files; the Agent tool has no effort field, so "
        f"this is recorded and never set — ticket 39, ruling 7.)"
    )


def ledger_map(text):
    """The ledger's resolved map. Three answers, because the hook owes three.

      None  no map line at all. The spawn passes on the session's model, as it
            always did (ruling 9).
      {}    a map line that does not name all twelve roles with reachable
            models. That is a fault, and ruling 16 says a fault passes the
            spawn AND writes one line to the run journal -- which the caller
            cannot do if a damaged line is indistinguishable from no line.
      dict  all twelve. This is the only answer the hook may refuse against.
    """
    match = MAP_LINE.search(text or "")
    if not match:
        return None
    found = {}
    for word in match.group(1).split():
        key, _, model = word.partition("=")
        if key in ROLES and model in MODELS:
            found[key] = model
    return found if set(found) == set(ROLES) else {}


def inversion_refusal(found):
    """The words an inverted map earns. One text, because two callers print it.

    `machine-preflight.py` row 14 refuses the same map at prompt-submit time
    and the launch line refuses it again before spawn 1. Two wordings of one
    rule drift apart, and the reader cannot tell which one is the rule.
    """
    return (
        "REFUSED. No adversarial gate runs below the tier of the worker it "
        "checks (ruled 2026-08-15, `~/.claude/rulings.md:99-121`): a wrong "
        "reject costs one retry round, and a wrong pass has no catcher until "
        f"the merge. Tier order `{' < '.join(MODELS)}`; equal is legal.\n\n"
        + "\n".join("  " + line for line in found)
    )


def read_map(command_text):
    """`(typed, applied, refusals)` for one launch line, grammar only.

    No session model is read here, so `applied` still carries `inherit` for
    every role the map does not name. That split is what lets
    `machine-preflight.py` row 14 refuse a bad map at PROMPT-SUBMIT time:
    the human ruled on 2026-09-05 that a map refusal must arrive in the first two
    minutes, before a batch id is minted and before a QA workspace is seeded,
    and that hook must never refuse merely because it could not measure the
    session model.

    `command_text` is everything after `/run-issues` or `/parallel-hunt`: the
    scope, then the `models:` word and the map. One grammar for both (ruling 20).
    """
    _, map_text = split_models(command_text)
    if map_text is None:
        typed = read_default_map()
    elif not map_text.strip():
        return "", {}, [
            f"REFUSED. `{MODELS_WORD}` was typed with no map after it. Name at "
            f"least one role or group, or drop the word to take the default "
            f"(`{read_default_map()}`). A launch that silently fell back would "
            f"run a trial nobody chose."
        ]
    else:
        typed = map_text.strip()

    assignments, bad = parse_map(typed)
    if bad:
        return typed, {}, [
            "REFUSED. The map carries a token the grammar cannot read: "
            f"{', '.join(bad)}. Keys: all, workers, gates, or one of "
            f"{', '.join(ROLES)}. Values: {', '.join(MODELS)}, {INHERIT}."
        ]

    return typed, apply_map(assignments), []


def resolve_launch(command_text, session_model):
    """`(header, refusals)` for one launch line. A refusal writes no header.

    Every refusal here is a LAUNCH-time stop, before anything is spawned, which
    is the only place this ticket stops anything: ruling 10 and ruling 22 keep a
    live run moving whatever it finds.
    """
    typed, applied, refusals = read_map(command_text)
    if refusals:
        return "", refusals

    try:
        resolved = substitute_inherit(applied, session_model)
    except ValueError as error:
        return "", [f"REFUSED. {error}"]

    found = inversions(resolved)
    if found:
        return "", [inversion_refusal(found)]

    return header_lines(resolved, role_efforts(), session_model, typed), []


MODEL_ARG = re.compile(r"--model[=\s]+(\S+)")


def session_model_from_process(pid=None):
    """The session's model, off its own command line.

    The same road `machine-preflight.py` and SKILL.md already take, so the hook,
    the ledger and this script agree by construction. A session cannot read its
    own settings from its context, so this is measured or it is refused; it is
    never assumed.
    """
    pid = pid or os.environ.get("CLAUDE_PID", "")
    if not pid:
        return ""
    try:
        args = subprocess.run(["ps", "-o", "args=", "-p", str(pid)],
                              capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    found = [t for t in MODEL_ARG.findall(args) if tier_name(t)]
    return found[-1] if found else ""


def main(argv=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Resolve a run or hunt's model map and print the ledger header.")
    parser.add_argument(
        "command_text",
        help="everything after /run-issues or /parallel-hunt: the scope, then "
             "the `models:` word and the map")
    parser.add_argument(
        "--session-model", default=None,
        help="the model this session runs; measured off the process command "
             "line when not given")
    args = parser.parse_args(argv)

    session = args.session_model
    if session is None:
        session = session_model_from_process()

    header, refusals = resolve_launch(args.command_text, session)
    if refusals:
        for line in refusals:
            print(line, file=sys.stderr)
        print(
            "\nNothing is spawned and no ledger is written. This is a launch-time "
            "stop, before spawn 1; a live run is never stopped by this ticket "
            "(rulings 10 and 22).", file=sys.stderr)
        return 1
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
