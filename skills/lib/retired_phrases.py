#!/usr/bin/env python3
"""The retired-wording denylist, and the one place it lives.

Two things read this module: `test_retired_phrases.py` beside it, which reports,
and `~/.claude/hooks/retired-phrases-gate.py`, which refuses at the moment of the
write. Neither carries its own copy of the list. That is not tidiness — a rule
with two homes is exactly the defect the list exists to catch, and shipping this
guard as two divergent copies would have been the joke writing itself.

**The whole maintenance contract is one sentence: when a ruling retires wording,
its phrase joins RETIRED below.** Nothing else is asked of anybody.

**The five seeds below are one author's own retired wording, kept as worked
examples of the shape.** They will not match anything in your tree. Replace them
with sentences your own rulings have retired — until you do, this guard is a
green that polices nothing. By the
three-class test a proposal must refuse something or state a fact nobody wrote
down, and "remember to sweep the citing files" is the class that has already
failed repeatedly here.

**Why each entry carries its replacement.** A guard is graded by whether its
message names the act that would prevent a repeat, not by whether it refuses.
`check_verdict.py` refused a lone gate spawn and named the missing VERDICT, the
symptom, and the same slip happened again on the next attempt because nothing
named the missing SPAWN. So a refusal here says what superseded the sentence, on
what date, and where the ruling is recorded.

**`decisions.md` is not a steering file and never will be.** Provenance files
quote retired wording on purpose: as history, and as the supersession notes that
stop somebody re-deriving a dead rule from an old entry. `is_steering_file` lists
what it guards rather than excluding what it does not, so a decisions file can
never drift into scope.
"""

from pathlib import Path

CLAUDE_HOME = Path.home() / ".claude"

# The rules-only scan set: the files that TELL AN AGENT WHAT TO DO.
STEERING_FILES = [
    CLAUDE_HOME / "CLAUDE.md",
    CLAUDE_HOME / "questionrules.md",
]
SKILLS_DIR = CLAUDE_HOME / "skills"
AGENTS_DIR = CLAUDE_HOME / "agents"
SKILL_PATTERN = "*/SKILL.md"
AGENT_PATTERN = "*.md"


# Each entry: the retired phrase, what superseded it, and where that ruling is
# recorded. All five seeds come from the 2026-08-29 sweep that repaired eighteen
# instances of this defect by hand, and every one was confirmed absent from the
# scan set on 2026-09-01, the day the guard was built.
RETIRED = [
    (
        "splitting is his call",
        "A split the session can cut, harden and stamp itself is the session's "
        "to make; only a split it cannot complete that way goes to the human. "
        "Ruled 2026-08-29; routing table in ~/.claude/questionrules.md.",
    ),
    (
        "Splitting is the human's call",
        "Same ruling as above, 2026-08-29. The session settles a split it can "
        "complete; ~/.claude/questionrules.md's routing table decides.",
    ),
    (
        "a split, which stays the human's alone",
        "Same ruling as above, 2026-08-29. Global CLAUDE.md's chain paragraph "
        "now qualifies this to a split the session cannot cut, harden and "
        "stamp itself.",
    ),
    (
        "Only a seam that commits a public contract",
        "The seven-item irreversible list was replaced by the four routing-table "
        "classes on 2026-08-29 — major architectural change, deleting production "
        "rows, money, and authentication. Narrowing seam questions to public "
        "contracts alone meant a money seam never waited.",
    ),
    (
        "a write to `.out-of-scope/`, a transition on an issue a run holds",
        "The distinctive span of the retired seven-item irreversible list "
        "(2026-07-27), superseded 2026-08-29 by the four routing-table classes "
        "in ~/.claude/questionrules.md.",
    ),
]


def squash(text):
    """Collapse every run of whitespace to one space.

    These are hard-wrapped markdown documents. A retired sentence reintroduced
    across a line break is the same regression as one reintroduced on a single
    line, and a guard that only catches the second has a hole nobody can see.
    """
    return " ".join(text.split())


def contains(text, phrase):
    """True when `text` carries `phrase`, ignoring wrapping and case."""
    return squash(phrase).lower() in squash(text).lower()


def hits(text):
    """Every retired entry `text` carries, as (phrase, superseded_by)."""
    return [(p, s) for p, s in RETIRED if contains(text, p)]


def is_steering_file(path):
    """True for a file whose job is to tell an agent what to do.

    An allowlist, never an exclusion list. A path this does not recognise is
    simply not guarded, which is the safe direction for a hook: the reporting
    test still reads the whole scan set.
    """
    if not path:
        return False
    try:
        p = Path(path).expanduser().resolve()
    except (OSError, ValueError, RuntimeError):
        return False

    if p in [f.resolve() for f in STEERING_FILES if f.exists()]:
        return True
    if p.name == "CLAUDE.md" and p.parent == CLAUDE_HOME:
        return True
    if p.name == "questionrules.md" and p.parent == CLAUDE_HOME:
        return True
    if p.name == "SKILL.md" and p.parent.parent == SKILLS_DIR:
        return True
    if p.suffix == ".md" and p.parent == AGENTS_DIR:
        return True
    return False


def scan_set():
    """Every file the reporting test reads, or why it cannot read them.

    Returns (files, problems). A caller that ignores `problems` gets a green
    from an empty scan, which is the failure the citation checker was caught in:
    silence reading as a clean pass.
    """
    files, problems = [], []

    for path in STEERING_FILES:
        if path.is_file():
            files.append(path)
        else:
            problems.append(f"named steering file is missing: {path}")

    for root, pattern in ((SKILLS_DIR, SKILL_PATTERN), (AGENTS_DIR, AGENT_PATTERN)):
        if not root.is_dir():
            problems.append(f"steering directory is missing: {root}")
            continue
        found = sorted(root.glob(pattern))
        if not found:
            problems.append(f"no files matched {pattern} under {root}")
        files.extend(found)

    return files, problems
