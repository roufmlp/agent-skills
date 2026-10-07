#!/usr/bin/env python3
"""Refuse a hardening edit that adds beside a reset criterion, or writes a count
nobody measured.

Fix F9 of the audit of 2026-09-23, tracker-tooling issue 23 (the audit's
section 2, root cause 2: hardening wrote the faulty criterion, then churned it).

    python3 ~/.claude/skills/harden-issues/check_criteria_edit.py \
        --issue <each file this pass hardened> [--base HEAD]

Three refusals, all on text the pass wrote:

**Replace, not add.** One tracker's issue 139c: pass `h0919` added a broad rule
beside the narrow one and deleted nothing. "Both implementers built the first. Both
gates graded the second." Where a run has reset an issue's criteria, a criterion
this pass changed must lose at least one sentence it held at `--base`. Struck
text, `~~like this~~`, counts as lost, because the pass strikes a false claim
where it stands. A criterion absent at `--base` is new and is not an edit.

A reset is on record when a strike-2 findings file, `runs/<batch>/harden/<id>.md`
beside the issues directory, carries `criteria-fault` in its first
`VERDICT_LINES` lines. Measured 2026-09-23: all ten such files on one
tracker carry it between lines 3 and 7, by
`grep -n -m1 -E 'criteria-(fault|sound|open)'`. Every worktree of the
repository is read, because a worktree holds `runs/` frozen at
its branch point; pass `h0913` missed a live run that way on 2026-09-13.

**A count carries its command.** Issue 139 of the same tracker: pass `h0917c`
wrote "twenty-two" colour families, and the installed Tailwind ships 26. A sentence
the pass wrote that states a count (a number of two or more, then a plural
within two words) needs a backticked command in the same criterion whose first
word is in `COMMANDS`, or a `Not measured:` line quoting that count. The command
list is closed: an unknown first word is not a command.

Only the pass's own sentences are read. Graded whole, the rule flagged 123 of the
269 criteria in the 55 `ready-for-agent` files of two trackers on
2026-09-23, mostly fixture sizes such as "two rows". One command anywhere in a
criterion covers every count in it; that is the limit of this check, and the
attacker's class 5 is the judgement behind it.

**An example carries its command in its clause.** Issue 381 of one tracker: the launch
pass of run batch-ce5d7b wrote "`4` finds no bill", and both gates measured it
false. Ruling `q-fin-ce5d7b-03`; `unmeasured_examples` holds the measurement.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "run-issues"))

from check_issue_ready import criteria  # noqa: E402  One reader of criteria for both skills.

# A sentence ends at a full stop, before or after closing emphasis or a quote.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[.!?]\*\*)\s+|(?<=[.!?][*_\"')])\s+")
# Struck text is removed text: the pass strikes a false claim where it stands.
STRUCK = re.compile(r"~~.*?~~", re.DOTALL)


# A strike-2 findings file opens with its verdict. Measured 2026-09-23: all ten
# such files on one tracker carry it between lines 3 and 7.
VERDICT_LINES = 20
RESET = re.compile(r"criteria-fault")


def worktrees(anywhere: pathlib.Path) -> list[pathlib.Path]:
    """Every worktree root of the repository holding `anywhere`, or none."""
    listed = subprocess.run(
        ["git", "-C", str(anywhere), "worktree", "list", "--porcelain"],
        capture_output=True, text=True,
    )
    if listed.returncode != 0:
        return []
    return [pathlib.Path(line[len("worktree "):]) for line in listed.stdout.splitlines()
            if line.startswith("worktree ")]


def reset_record(issue: pathlib.Path) -> list[pathlib.Path]:
    """The strike-2 findings files that record a criteria reset of this issue.

    They sit at `<feature>/runs/<batch>/harden/<id>.md`, and a worktree holds
    only the copy of `runs/` frozen at its branch point, so every worktree of
    the repository is read, as `find_live_ledger.py` reads every ledger.
    """
    issue = issue.resolve()
    feature = issue.parent.parent
    identifier = re.match(r"^(\d+[a-z]?)-", issue.name)
    if not identifier:
        return []
    features = [feature]
    toplevel = subprocess.run(
        ["git", "-C", str(feature), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if toplevel.returncode == 0:
        relative = feature.relative_to(pathlib.Path(toplevel.stdout.strip()).resolve())
        features += [root.resolve() / relative for root in worktrees(feature)]
    found = []
    for directory in dict.fromkeys(features):
        for path in sorted(directory.glob(f"runs/*/harden/{identifier.group(1)}.md")):
            head = path.read_text(errors="replace").splitlines()[:VERDICT_LINES]
            if any(RESET.search(line) for line in head):
                found.append(path)
    return found


# A count is a number of two or more followed, within two words, by a plural.
UNITS = {
    "ms", "kb", "mb", "gb", "bytes", "bps", "seconds", "minutes", "hours", "days", "weeks",
    "months", "years", "px", "pixels", "percent",
}
NUMBER_WORD = (
    r"(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:-(?:one|two|three|four|"
    r"five|six|seven|eight|nine))?|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|hundred|dozen"
)
COUNT = re.compile(
    rf"(?<![\w.:/-])(?P<number>[2-9]|\d{{2,}}|{NUMBER_WORD})(?![\w.:/-]\w)"
    r"(?P<rest>(?:\s+[A-Za-z][\w'-]*){0,2}?\s+[A-Za-z][\w-]*s)\b",
    re.IGNORECASE,
)
# A number after one of these names a thing ("criterion 9", "issue 139").
NAMING = {
    "criterion", "criteria", "issue", "issues", "attempt", "round", "default", "invariant",
    "line", "lines", "step", "class", "ruling", "gate", "gates", "strike", "version", "pass",
    "run", "section", "part", "item", "option", "road", "row", "case", "figure", "table",
    "question", "ticket", "fix", "wave", "session", "stage", "form", "level", "port", "exit",
    "code", "page", "measurement", "wave", "commit", "migration", "phase", "sitting",
}
# The first word of a command a person can run. Closed: anything else is not one.
COMMANDS = {
    "git", "grep", "rg", "find", "ls", "wc", "node", "npx", "npm", "pnpm", "python",
    "python3", "psql", "jq", "sed", "awk", "sort", "uniq", "head", "tail", "cat", "curl",
    "shasum", "diff", "du", "tsc", "vitest", "supabase", "sqlite3", "cd", "select", "with",
}
BACKTICK = re.compile(r"`([^`\n]+)`")
# The author's own word that a count was set, not measured. It clears only the
# counts it quotes, so a line cannot wave a criterion through wholesale.
NOT_MEASURED = re.compile(r"^[ \t]*(?:[-*][ \t]+)?Not measured:(?P<why>.*?)(?:\n[ \t]*\n|\Z)",
                          re.MULTILINE | re.IGNORECASE | re.DOTALL)


def plain(body: str) -> str:
    """A criterion's prose, without code spans, struck text or its waiver."""
    return BACKTICK.sub(" ", STRUCK.sub(" ", NOT_MEASURED.sub(" ", body)))


def unmeasured_counts(text: str, base: str | None = None) -> list[str]:
    """Each criterion whose new text states a count and carries no command.

    Only the sentences absent from the same criterion at `base` are read: graded
    whole, the rule flagged 123 of 269 ready criteria on 2026-09-23, mostly
    fixture sizes nobody measures. The pass owns what it writes.
    """
    before = dict(criteria(base)) if base is not None else {}
    faults = []
    for number, body in criteria(text):
        commands = [span for span in BACKTICK.findall(body)
                    if span.split() and span.split()[0].lower() in COMMANDS]
        if commands:
            continue
        waived = " ".join(match.group("why") for match in NOT_MEASURED.finditer(body)).lower()
        prose = plain(body)
        old = " ".join(plain(before.get(number, "")).split())
        written = " ".join(one for one in sentences(prose) if one not in old)
        counts = []
        for found in COUNT.finditer(written):
            preceding = written[:found.start()].split()
            if preceding and preceding[-1].lower().strip("*(") in NAMING:
                continue
            words = found.group("rest").split()
            if words[-1].lower() in UNITS or len(words[-1]) < 3 or words[-1].endswith("ss"):
                continue
            count = " ".join([found.group("number")] + words)
            if count.lower() not in waived:
                counts.append(count)
        if counts:
            faults.append(
                f"criterion {number} states {', '.join(repr(one) for one in counts)} "
                "and carries no command that measured it"
            )
    return faults


# An example is a literal input, backticked or double-quoted, then an outcome verb.
EXAMPLE = re.compile(
    r"(?:`(?P<code>[^`\n]+)`|\"(?P<quoted>[^\"\n]{1,40})\")(?:\s+\([^)]*\))?\s+"
    r"(?:returns?|finds?|match(?:es)?|folds?\s+to|prints?|yields?|outputs?|"
    r"evaluates?\s+to|resolves?\s+to)\b",
    re.IGNORECASE,
)
# A backticked span that names code is not an input: a function, a file, a path or a flag.
NAMES_CODE = re.compile(
    r"[A-Za-z_$][\w$.]*(?:\(\))?|[\w.-]+\.(?:ts|tsx|js|mjs|py|md|sql|json|sh)|-.*|.*/.*"
)
CLAUSE_END = re.compile(r";|(?<=[.!?])\s+|(?<=[.!?]\*\*)\s+|(?<=[.!?][*_\"')])\s+")


def is_command(span: str) -> bool:
    return bool(span.split()) and span.split()[0].lower() in COMMANDS


def clauses(body: str) -> list[str]:
    """A criterion's clauses, split at `;` and at a sentence end, without struck
    text or its `Not measured:` line. Backticks are kept: they mark the input."""
    kept = STRUCK.sub(" ", NOT_MEASURED.sub(" ", body))
    return [one.strip() for one in CLAUSE_END.split(" ".join(kept.split())) if one.strip()]


def unmeasured_examples(text: str, base: str | None = None) -> list[str]:
    """Each criterion whose new text gives an example input and outcome with no
    command in the same clause.

    Ruling `q-fin-ce5d7b-03`, 2026-10-07, road A2. Issue 381's criterion 3, as
    the launch pass of run batch-ce5d7b wrote it, said "`04 39` returns nothing
    by phone" and "`4` finds no bill"; both gates measured both false, which
    cost a strike-2 attacker and a second attempt. The refusal sits here, where
    the pass writes, and not in `check_issue_ready.py`, which also runs at
    `/run-issues` launch, where its exit 1 blocks the run.

    Beside means the same clause, because 381's criterion held one `grep` that
    a one-command-per-criterion rule would have let cover every example in it.
    There is no `Not measured:` waiver: the ruling is measure it or remove it.

    Measured 2026-10-07 over the 391 criteria of one project's `ready-for-agent`
    issues: any backticked span before an outcome verb hit 24 criteria, 23 of
    them naming a function, file or flag (`saveLinePrice` returns), so a span
    that names code is not an input. With that cut one live criterion hits, and
    the 381 text does. Whether the command measures the claim is the attacker's
    judgement; this checks only that one stands beside it.
    """
    before = dict(criteria(base)) if base is not None else {}
    faults = []
    for number, body in criteria(text):
        old = " ".join(clauses(before.get(number, "")))
        examples = []
        for clause in clauses(body):
            if clause in old or any(is_command(span) for span in BACKTICK.findall(clause)):
                continue
            for found in EXAMPLE.finditer(clause):
                code = found.group("code")
                if code is not None and (is_command(code) or NAMES_CODE.fullmatch(code.strip())):
                    continue
                examples.append(" ".join(found.group(0).split()))
        if examples:
            faults.append(
                f"criterion {number} gives {', '.join(repr(one) for one in examples)} "
                "with no command beside it that measured the outcome"
            )
    return faults


def sentences(text: str) -> list[str]:
    return [one for one in SENTENCE_END.split(" ".join(text.split())) if one]


def added_only(base: str, now: str) -> list[str]:
    """Each criterion that changed and kept every sentence it had at base."""
    before = dict(criteria(base))
    faults = []
    for number, body in criteria(now):
        old = before.get(number)
        if old is None or " ".join(old.split()) == " ".join(body.split()):
            continue
        kept = " ".join(STRUCK.sub(" ", body).split())
        if all(sentence in kept for sentence in sentences(STRUCK.sub(" ", old))):
            faults.append(f"criterion {number} only gained text")
    return faults


def at_base(issue: pathlib.Path, base: str) -> str | None:
    """The file as `base` holds it, or None where it is new or outside git."""
    issue = issue.resolve()
    toplevel = subprocess.run(
        ["git", "-C", str(issue.parent), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if toplevel.returncode != 0:
        return None
    relative = issue.relative_to(pathlib.Path(toplevel.stdout.strip()).resolve())
    shown = subprocess.run(
        ["git", "-C", toplevel.stdout.strip(), "show", f"{base}:{relative.as_posix()}"],
        capture_output=True, text=True,
    )
    return shown.stdout if shown.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a hardening edit that only adds to a reset criterion, "
        "or writes a count with no command.",
    )
    parser.add_argument("--issue", required=True, action="append", dest="issues",
                        help="an issue file this pass hardened; repeat for each")
    parser.add_argument("--base", default="HEAD",
                        help="the commit holding the file before this pass (default HEAD)")
    args = parser.parse_args()

    refused = False
    read = 0
    for one in args.issues:
        path = pathlib.Path(one)
        identifier = re.match(r"^(\d+[a-z]?)-", path.name)
        identifier = identifier.group(1) if identifier else path.name
        try:
            now = path.read_text()
        except OSError as error:
            print(f"REFUSED   {identifier}: unreadable, {error}", file=sys.stderr)
            refused = True
            continue
        read += len(criteria(now))
        base = at_base(path, args.base)
        record = reset_record(path)
        faults = []
        if record and base is not None:
            faults += [f"{fault}, and a run reset this issue's criteria "
                       f"({', '.join(str(one) for one in record)}): replace the text the "
                       "run found at fault, or strike it with ~~ ~~" for fault in added_only(base, now)]
        faults += unmeasured_counts(now, base)
        faults += unmeasured_examples(now, base)
        if faults:
            refused = True
            for fault in faults:
                print(f"REFUSED   {identifier}: {fault}", file=sys.stderr)
        else:
            print(f"ok        {identifier}" + (f": reset on record, {len(record)} file(s)" if record else ""))

    print(f"read {len(args.issues)} issue file(s), {read} criteria")
    if refused:
        print(
            "\nREFUSED: repair the criteria above before the stamp. A count takes the "
            "command that measured it in backticks, or a `Not measured:` line quoting it. "
            "An example input and outcome takes its command in the same clause: measure it "
            "or remove it.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
