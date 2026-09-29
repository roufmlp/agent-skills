#!/usr/bin/env python3
"""Claim the next issue or migration number, atomically, across every worktree.

    python3 ~/.claude/skills/lib/claim_number.py issue <issues dir> [--for <who>] [--slug <slug>]
    python3 ~/.claude/skills/lib/claim_number.py migration <migrations dir> [--for <who>]
    python3 ~/.claude/skills/lib/claim_number.py --check <path-about-to-be-written>
    python3 ~/.claude/skills/lib/claim_number.py --rename <old path> <new path>
    python3 ~/.claude/skills/lib/claim_number.py --list <dir>

Ticket 38 of the pilot-delivery map, the one-run-per-feature layout ticket, sitting 5
(2026-09-04). Ruling 7: issue numbers come off one counter file with an atomic claim,
one sequence, no prefix per minter and no renumbering at merge. Ruling 16: every minter
calls the claim script and a hook refuses a write to `issues/NN-*.md` when NN was not
claimed. Ruling 19: the same script and hook cover `supabase/migrations/NNNN_*.sql`.
Two minters used to pick "the next free number" by listing one directory in one tree.
A live run's promotion and a hand-minted ticket in another session could both write
`512`, and two runs once both wrote migration `0078` (`docs/agents/issue-tracker.md`
in the main repo records the day).

HOW A CLAIM WORKS. The next number is one past the highest number anything holds: the
directory in every worktree of the repository, plus every claim already in the store,
which covers a number claimed in a session that has not written its file yet. The
claim itself is a file created with an exclusive create (`O_CREAT | O_EXCL`), so two
processes racing for one number cannot both win; the loser steps to the next number
and tries again. The store lives OUTSIDE every repository, in
`$XDG_STATE_HOME/claims/<main checkout path>/<kind>/<dir>/<number>` (default
`~/.local/state/...`), the same home sitting 2 gave the Zoho lock, because a file
inside a worktree is invisible to every other worktree until it merges. The main
checkout is read off `git rev-parse --git-common-dir`, so every worktree of one clone
shares one store and a second clone at another path gets its own. Path segments are
percent-encoded, so two directories cannot share a key. `CLAIM_STORE` overrides the
root, for tests.

WHAT A CLAIM RECORDS. The worktree it was made in, who asked, the slug they meant and
the time, one `key=value` per line; a newline in a value is replaced, so a value can
never masquerade as a later line. `--check` reads the tree back: a number claimed in
one tree and written in another is the collision this exists to refuse, so the hook
that calls `--check` refuses it and names the tree that holds the claim. The name must
be spelled as the claim printed it: a claim of `03` does not cover `3-slug.md`.

WHAT NEEDS NO CLAIM. A file that already exists (an edit), and a split, which takes a
letter suffix on its parent's number (`216b`) and draws from a name exactly one issue
owns (`docs/agents/issue-tracker.md`, settled 2026-08-03). `--check` passes both.

RENAMING A FILE THAT ALREADY HOLDS ITS NUMBER. The human's ruling `q-h0920-37` of
2026-09-20: a tracker file whose title has gone false is RENAMED — keep the number,
rewrite the title, rename the file with it. Hardening pass `h0922b` was refused that
on 2026-09-22. One tracker's issue 105 was claimed by `promotion batch-d41839` in the
worktree `run-issues-batch-d41839`; the file had since merged into another tree, so
`--check` read the new name as a number claimed elsewhere, which is the collision it
exists to stop. `--rename <old> <new>` is the road that tells the two apart, and what
tells them apart is the OLD FILE ON DISK: a file this tree already holds is a file
this tree already owns, and re-spelling its title mints nothing. Five refusals, each
one a check and not a convention:

  1. the number and any split suffix are identical in both names — changing either is
     a mint, and a mint claims a number;
  2. both names are the same kind and sit in the same directory;
  3. the old file exists, in the tree the rename is run from — a rename with no source
     file is a mint wearing a disguise;
  4. the new name is free — nothing is ever renamed over;
  5. both names parse as numbered files at all.

It UPDATES the one claim record rather than writing a second: `slug` becomes the new
slug and `tree` becomes the tree the rename happened in, while `who` and `at` keep the
original claimant and the original claim time, and `claimed_tree` records where the
claim was first made. A later reader still sees that 105 was claimed by
`promotion batch-d41839` on 2026-09-15 and renamed after. A second rename overwrites
none of that history. A number older than the store gains a record here, which is not
a mint because its file is already on disk.

`--rename` moves no file. It makes the claim true and the caller then runs `git mv`,
which `--check` now passes because the claim names this tree — so the rule keeps one
home in `check()` and the rename road adds no second case to it. A CROSS-TREE MINT IS
UNTOUCHED and stays refused; `test_claim_number.py` drives both halves of that.

TWO FACTS, NOT RULES. A file written through a road no hook sees exists afterwards,
and every later edit to it passes as an edit; the guard catches the minting write,
not its history. And a number that predates this script has no claim, so if its file
were deleted from every worktree the number could be issued again; closed issues stay
on disk, so nothing does that today.

Exit codes: 0 claimed, check passed or rename recorded; 1 check or rename refused
(reason on stderr); 2 bad usage or a directory outside any git repository.
"""

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collect_shards import list_worktrees as _list_worktrees  # noqa: E402  (same directory)

GIT_TIMEOUT = 20
MAX_STEPS = 10000

KINDS = {
    # kind: (file-name pattern with the number first, minimum width)
    "issue": (re.compile(r"^(?P<number>\d+)(?P<suffix>[a-z]?)-[^/]*\.md$"), 2),
    "migration": (re.compile(r"^(?P<number>\d{4})(?P<suffix>)_[^/]*\.sql$"), 4),
}

# What `--check` and the hook recognise: `<anything>/issues/NN-slug.md` and
# `<anything>/supabase/migrations/NNNN_slug.sql`, and nothing deeper. One definition,
# imported by `number-claim-guard.py`, so the hook and the check cannot drift apart.
CHECK_SHAPES = (
    ("issue", re.compile(r"^(?P<dir>.*/issues)/(?P<name>\d+[a-z]?-[^/]*\.md)$")),
    ("migration", re.compile(r"^(?P<dir>.*/supabase/migrations)/(?P<name>\d{4}_[^/]*\.sql)$")),
)

SCRIPT = os.path.abspath(__file__)


class NotARepository(Exception):
    pass


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=True, timeout=GIT_TIMEOUT).stdout


def looks_numbered(path: str) -> bool:
    """Whether `path` has one of the two shapes the claim covers."""
    normalised = os.path.normpath(path)
    return any(shape.match(normalised) for _, shape in CHECK_SHAPES)


def tree_root(path: str) -> str:
    """The worktree root holding `path`, or raise NotARepository."""
    probe = path if os.path.isdir(path) else os.path.dirname(path)
    while not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            raise NotARepository(path)
        probe = parent
    try:
        return os.path.realpath(_git(["rev-parse", "--show-toplevel"], probe).strip())
    except subprocess.CalledProcessError:
        raise NotARepository(path)


def main_checkout(tree: str) -> str:
    """The main checkout of the clone `tree` belongs to: the parent of the common git dir."""
    common = _git(["rev-parse", "--git-common-dir"], tree).strip()
    if not os.path.isabs(common):
        common = os.path.join(tree, common)
    return os.path.realpath(os.path.dirname(common))


def list_worktrees(tree: str) -> list:
    """Every worktree of the repository, main checkout first, resolved through symlinks."""
    return [os.path.realpath(path) for path in _list_worktrees(tree)] or [tree]


def store_dir(kind: str, main_tree: str, relative_dir: str, env=None) -> str:
    env = os.environ if env is None else env
    root = env.get("CLAIM_STORE") or os.path.join(
        env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"),
        "claims")
    return os.path.join(root, quote(main_tree, safe=""), kind, quote(relative_dir, safe=""))


def numbers_in(directory: str, kind: str) -> list:
    """(number, width) for every file in one directory that carries a number."""
    pattern = KINDS[kind][0]
    found = []
    try:
        names = os.listdir(directory)
    except OSError:
        return found
    for name in names:
        match = pattern.match(name)
        if match:
            found.append((int(match.group("number")), len(match.group("number"))))
    return found


def claimed_numbers(store: str) -> list:
    found = []
    try:
        names = os.listdir(store)
    except OSError:
        return found
    for name in names:
        if name.isdigit():
            found.append((int(name), len(name)))
    return found


def locate(directory: str):
    """The tree holding `directory`, the clone's main checkout, and the directory's
    path inside the tree."""
    absolute = os.path.realpath(os.path.abspath(directory))
    tree = tree_root(absolute)
    relative = os.path.relpath(absolute, tree)
    if relative.startswith(".."):
        raise NotARepository(directory)
    return tree, main_checkout(tree), relative


def next_number(kind: str, trees: list, relative: str, store: str):
    """(highest + 1, width) across every worktree's copy and every claim."""
    seen = []
    for tree in trees:
        seen.extend(numbers_in(os.path.join(tree, relative), kind))
    seen.extend(claimed_numbers(store))
    minimum = KINDS[kind][1]
    if not seen:
        return 1, minimum
    highest = max(n for n, _ in seen)
    width = max([minimum] + [w for _, w in seen])
    return highest + 1, width


def _one_line(value: str) -> str:
    """A record value on one line, so it cannot pose as a later `key=` line."""
    return " ".join(str(value).splitlines())


def claim(kind: str, directory: str, who: str = "", slug: str = "", env=None) -> str:
    tree, main, relative = locate(directory)
    store = store_dir(kind, main, relative, env)
    os.makedirs(store, exist_ok=True)
    number, width = next_number(kind, list_worktrees(tree), relative, store)
    record = "\n".join([
        f"tree={tree}",
        f"who={_one_line(who)}",
        f"slug={_one_line(slug)}",
        f"at={_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}",
        "",
    ])
    for _ in range(MAX_STEPS):
        name = str(number).zfill(width)
        path = os.path.join(store, name)
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            number += 1
            continue
        with os.fdopen(handle, "w") as fh:
            fh.write(record)
        return name
    raise RuntimeError(f"no free number within {MAX_STEPS} steps")


def read_claim(path: str) -> dict:
    fields = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.rstrip("\n").partition("=")
                fields[key] = value
    except OSError:
        pass
    return fields


def kind_of_dir(relative: str) -> str:
    """`--list` takes a directory alone; the migrations directory is the one name the
    check shape knows, and every other directory holds issues."""
    return "migration" if relative.replace(os.sep, "/").endswith("supabase/migrations") else "issue"


def list_claims(directory: str, env=None) -> list:
    """Every claim for a directory, lowest number first, as (name, fields)."""
    tree, main, relative = locate(directory)
    store = store_dir(kind_of_dir(relative), main, relative, env)
    names = sorted((name for name in os.listdir(store) if name.isdigit()), key=int) \
        if os.path.isdir(store) else []
    return [(name, read_claim(os.path.join(store, name))) for name in names]


def parent_exists(parent: int, kind: str, trees: list, relative: str) -> bool:
    """Whether any worktree holds a file numbered `parent`, with or without a suffix."""
    return any(number == parent
               for tree in trees
               for number, _ in numbers_in(os.path.join(tree, relative), kind))


def _claim_command(kind: str, directory: str) -> str:
    return f"  python3 {SCRIPT} {kind} {directory} --for <who> --slug <slug>"


def parse_numbered(path: str):
    """(kind, directory, name, spelled number, suffix) for a numbered path, else None.

    One reading of a path, shared by `--check` and `--rename`, so the two cannot
    disagree about what a numbered file is.
    """
    normalised = os.path.normpath(os.path.abspath(path))
    for kind, shape in CHECK_SHAPES:
        match = shape.match(normalised)
        if not match:
            continue
        parsed = KINDS[kind][0].match(match.group("name"))
        if not parsed:
            return None
        return (kind, match.group("dir"), match.group("name"),
                parsed.group("number"), parsed.group("suffix"))
    return None


def slug_of(name: str, spelled: str, suffix: str) -> str:
    """The part of a file name after the number and its separator, without the suffix
    extension: `105-line-page-...md` gives `line-page-...`."""
    body = name[len(spelled) + len(suffix) + 1:]
    return body[: body.rindex(".")] if "." in body else body


def _record_lines(fields: dict) -> str:
    """A claim record, the fixed keys first and in their original order, so a record
    written before the rename road reads the same afterwards."""
    order = ["tree", "who", "slug", "at", "claimed_tree", "renamed_from", "renamed_at"]
    keys = order + sorted(key for key in fields if key and key not in order)
    return "\n".join(f"{key}={_one_line(fields[key])}" for key in keys if key in fields) + "\n"


def _write_record(holder: str, fields: dict) -> None:
    """Replace a claim record in one step, so no reader sees a half-written one."""
    temporary = f"{holder}.writing-{os.getpid()}"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(_record_lines(fields))
    os.replace(temporary, holder)


def _rename_refusal(reason: list) -> str:
    return "\n".join(reason)


def rename(old: str, new: str, env=None) -> str:
    """The refusal for re-slugging `old` to `new`, or "" once the claim carries the
    new name. Moves no file: the caller runs `git mv` and `--check` then passes it.

    The human's ruling `q-h0920-37`. The whole docstring above states the five refusals;
    each one is here and none of them is a convention.
    """
    old_abs = os.path.normpath(os.path.abspath(old))
    new_abs = os.path.normpath(os.path.abspath(new))
    old_parts, new_parts = parse_numbered(old_abs), parse_numbered(new_abs)
    if not old_parts or not new_parts:
        unreadable = old_abs if not old_parts else new_abs
        return _rename_refusal([
            "REFUSED. Give two numbered tracker paths and reissue:",
            f"  python3 {SCRIPT} --rename <old path> <new path>",
            "",
            f"  cannot read as a numbered file: {unreadable}",
            "",
            "A rename road covers `<anything>/issues/NN-<slug>.md` and",
            "`<anything>/supabase/migrations/NNNN_<slug>.sql`, and nothing else.",
        ])
    kind, directory, old_name, spelled, suffix = old_parts
    new_kind, new_directory, new_name, new_spelled, new_suffix = new_parts
    if new_kind != kind or new_directory != directory:
        return _rename_refusal([
            "REFUSED. Rename inside one directory, and reissue:",
            f"  from: {directory}",
            f"    to: {new_directory}",
            "",
            "A rename rewrites a title. Moving a numbered file to another directory or",
            "another kind is a new file there, and a new file there claims a number.",
        ])
    if new_spelled != spelled or new_suffix != suffix:
        return _rename_refusal([
            f"REFUSED. Keep the number `{spelled}{suffix}`, or claim a fresh one and reissue:",
            _claim_command(kind, directory),
            "",
            f"  you asked: {old_name} -> {new_name}",
            "",
            "Ruling `q-h0920-37` of 2026-09-20 renames a file whose TITLE has gone false and",
            "keeps its number. A rename that changes the number is a mint, and a mint claims.",
        ])
    if new_name == old_name:
        return _rename_refusal([
            "REFUSED. Give a new name that differs from the old one, and reissue.",
            "",
            f"  both names are: {old_name}",
        ])
    if not os.path.isfile(old_abs):
        return _rename_refusal([
            "REFUSED. Claim the number and write the file, or correct the old path, and reissue:",
            _claim_command(kind, directory),
            "",
            f"  no such file: {old_name} in {directory}",
            "",
            "A rename re-spells a file this tree already holds. With no file to rename this is",
            "a mint wearing a disguise, and the claim exists to stop exactly that.",
        ])
    if os.path.exists(new_abs):
        return _rename_refusal([
            "REFUSED. Pick a name nothing holds, and reissue.",
            "",
            f"  already on disk: {new_name} in {directory}",
            "",
            "Nothing is renamed over. Two tracker files are two files, whatever they are called.",
        ])
    try:
        tree, main, relative = locate(directory)
    except (NotARepository, subprocess.SubprocessError, OSError):
        raise NotARepository(directory)
    if suffix:
        return ""  # A split carries no claim; its file on disk is its own proof.
    store = store_dir(kind, main, relative, env)
    holder = os.path.join(store, spelled)
    fields = read_claim(holder) if os.path.isfile(holder) else {}
    if fields:
        # Written once, by the FIRST rename. A later rename overwrites no history.
        fields.setdefault("claimed_tree", fields.get("tree", ""))
    else:
        # A number older than the store. Its file is on disk, so recording it is not a mint.
        fields = {"who": "", "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    fields["tree"] = tree
    fields["slug"] = slug_of(new_name, new_spelled, new_suffix)
    fields["renamed_from"] = old_name
    fields["renamed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    os.makedirs(store, exist_ok=True)
    _write_record(holder, fields)
    return ""


def check(path: str, env=None) -> str:
    """The refusal for writing `path`, or "" when the write may go ahead.

    Passes: a path that is not a numbered issue or migration file; a file that
    already exists (an edit); a split whose parent exists in any worktree; a
    number claimed in this tree, spelled as the claim printed it. Refuses: a new
    number nobody claimed, a split with no parent anywhere, a number claimed in
    another worktree, and a claimed number written at another width. Every refusal
    leads with what to do, because a run reissues one call and never halts.

    A RENAME NEEDS NO CASE HERE, and deliberately. `--rename` moves the claim to the
    tree holding the file, so the last clause below then passes the new name on the
    rule it already holds. One home for the rule; the road makes the claim true.
    """
    normalised = os.path.normpath(os.path.abspath(path))
    for kind, shape in CHECK_SHAPES:
        match = shape.match(normalised)
        if match:
            break
    else:
        return ""
    if os.path.exists(normalised):
        return ""
    directory, name = match.group("dir"), match.group("name")
    parsed = KINDS[kind][0].match(name)
    spelled, suffix = parsed.group("number"), parsed.group("suffix")
    number = int(spelled)
    try:
        tree, main, relative = locate(directory)
    except (NotARepository, subprocess.SubprocessError, OSError):
        return ""  # Outside any repository nothing can count, and the hook fails open.
    if suffix:
        if parent_exists(number, kind, list_worktrees(tree), relative):
            return ""
        return "\n".join([
            f"REFUSED. Write the parent issue {number} first, or claim a fresh number and reissue:",
            _claim_command(kind, directory),
            "",
            f"`{name}` is a split, and no worktree holds an issue {number}. A split takes a",
            "letter suffix on its PARENT's number (docs/agents/issue-tracker.md, settled 2026-08-03).",
        ])
    store = store_dir(kind, main, relative, env)
    holder = os.path.join(store, spelled)
    if not os.path.isfile(holder):
        at_other_width = [claimed for claimed in (os.listdir(store) if os.path.isdir(store) else [])
                          if claimed.isdigit() and int(claimed) == number]
        if at_other_width:
            return "\n".join([
                f"REFUSED. Name the file `{at_other_width[0]}-<slug>` as the claim printed it, and reissue.",
                "",
                f"  you wrote: {name}",
                "",
                "The claim spells the number at the directory's width; one directory holding",
                "`03-` and `3-` names is what ruling 7 (one sequence) exists to prevent.",
            ])
        return "\n".join([
            "REFUSED. Claim the number first, write the file under the number it prints, and reissue:",
            _claim_command(kind, directory),
            "",
            f"  you wrote: {name}, and nobody claimed {kind} number {spelled} for {directory}.",
            "",
            "Since 2026-09-05 (ticket 38, the one-run-per-feature layout ticket: ruling 7 makes",
            "the number an atomic claim, ruling 16 makes the hook refuse an unclaimed issue,",
            "ruling 19 extends both to migrations) every number comes off one claim across",
            "every worktree, so two sessions cannot both mint it. Nothing else stops: claim,",
            "write the file under the claimed number, and carry on.",
        ])
    fields = read_claim(holder)
    if fields.get("tree", "") != tree:
        return "\n".join([
            "REFUSED. Claim your own number and reissue:",
            _claim_command(kind, directory),
            "",
            f"  {kind} number {spelled} was claimed in another worktree:",
            f"  {fields.get('tree', '?')}",
            f"  by {fields.get('who') or '(unnamed)'} at {fields.get('at', '?')}, slug {fields.get('slug') or '(none)'}",
            "",
            "Writing it here would be the collision the claim exists to stop.",
        ])
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", nargs="?", choices=sorted(KINDS))
    parser.add_argument("directory", nargs="?")
    parser.add_argument("--for", dest="who", default="", help="who is minting: a skill, a batch id, a name")
    parser.add_argument("--slug", default="", help="the slug the file will carry, for the record")
    parser.add_argument("--list", metavar="DIR", help="print every claim for a directory")
    parser.add_argument("--check", metavar="PATH", help="exit 0 when PATH may be written, 1 with a reason when not")
    parser.add_argument("--rename", nargs=2, metavar=("OLD", "NEW"),
                        help="re-slug a numbered file that exists, keeping its number (ruling q-h0920-37)")
    args = parser.parse_args(argv)

    try:
        if args.rename:
            reason = rename(args.rename[0], args.rename[1])
            if reason:
                print(reason, file=sys.stderr)
                return 1
            return 0
        if args.list:
            for name, fields in list_claims(args.list):
                print(f"{name}  " + "  ".join(f"{k}={v}" for k, v in fields.items()))
            return 0
        if args.check:
            reason = check(args.check)
            if reason:
                print(reason, file=sys.stderr)
                return 1
            return 0
        if not args.kind or not args.directory:
            parser.error("give a kind and a directory, or --check, or --list")
        print(claim(args.kind, args.directory, args.who, args.slug))
        return 0
    except NotARepository as exc:
        print(f"REFUSED: {exc} is not inside a git repository, so there is no worktree list to count across.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
