#!/usr/bin/env python3
"""The note check: the one script behind a graduated product's three git hooks.

    python3 ~/.claude/skills/workflow/lib/note_check.py commit                 # pre-commit
    python3 ~/.claude/skills/workflow/lib/note_check.py merge                  # pre-merge-commit
    python3 ~/.claude/skills/workflow/lib/note_check.py push <remote> <url>    # pre-push, refs on stdin
    python3 ~/.claude/skills/workflow/lib/note_check.py migrations             # the duplicate-number check alone

"Where the note check lives, and baselines for changed screens" (workflow v2
ticket 33) put every check that must fire on every commit, whoever makes it,
into git hooks committed in the product's `.githooks/`, each a few lines that
call this script. `templates/githooks/` holds the hooks and the `prepare`
script that installs them. `--tree` names the checkout; the default is the
current directory's, which is where git runs a hook.

## Which note a commit belongs to

The branch names the note (spec, "Open at build time", point 1):

    note/<feature>/<nn>   note <nn> of changes/<feature>/, the file <nn>-*.md
    note/<nn>             a one-note change, changes/<nn>-*.md
    feature/<feature>     every note in changes/<feature>/: the merger's commits
                          and the final verifier's baselines land here
    anything else         no note. The commit may not touch a guarded path.

A branch that names a note whose file is not in the index is refused. The
note and `docs/design.md` are read from the index, so a commit that adds the
screen's row and the page together passes.

## What `commit` refuses

The diff is the staged one, against HEAD. Guarded paths are a baseline (a
`.png` in a `*-snapshots/` folder), `docs/design.md`, a listed screen's route
folder and a group's shared files.

- A path in a screen's route folder, or a shared file of a group, when no
  mapped note names that screen on its `Screens:` line ("What the verifier
  checks in the browser", ticket 24). `Screens: all <group>` names every
  screen of the group. The route folder is the folder of the `page.*` file
  whose route, with `(group)` and `@slot` segments dropped, is the screen's
  route; a file belongs to the deepest such folder above it.
- A new `page.*` file at a route the screens table does not list. The note
  that adds a screen adds its row.
- A baseline whose screen no mapped note names, or whose name matches no
  screen (ticket 15, case 1; ticket 33, changed screens).
- A change to `docs/design.md` when no mapped note has a `Core design:` line
  (ticket 15, case 2).
- A rewrite of the screens table, meaning an existing row changed or removed,
  when no mapped note has a `Prototype:` line (ticket 15, case 3). Adding a
  row is not a rewrite.
- Two `.sql` files with one leading number in a `migrations/` folder, or one
  with no number ("What a run does when notes collide or fail", ticket 32,
  C8).
- A `Screens:` line naming a screen the table does not list, or a mapped note
  with no `Screens:` line. A missing line is a refusal, not a default.
- On `feature/<feature>` only: a new test-side file (`suite.TEST_SIDE`: a
  `.test`/`.spec` file or anything under `tests/`, `__tests__/` or `e2e/`,
  baselines aside) that no note in the folder names in its `## Tests` part,
  and a deleted test-side file that a note still names. The interview
  commits a note with its tests, so both pass together; a cut moves the
  note to `cut/` and deletes its tests in one commit, so that passes too.
  What this refuses is the final fix round: twice in the rehearsal it added
  a test no note names (a budget test, a tables guard) and the final
  reviewer refused the feature on it. A note branch is not held to this:
  the implementer's new tests there answer to the red check.

A commit that concludes a merge by hand, with `MERGE_HEAD` present, runs the
`merge` checks instead: the merged commits passed the note check already.

## What `merge` does

The duplicate-number check on the merged index, and on a merge into main the
red check for the whole feature: `suite.py red --base HEAD`, main's code from
before the merge ("Whether the build agents work test-first", ticket 22).

## What `push` does

For each ref pushed to main it lists the migrations in the pushed commit and
reads `<git common dir>/last-production-migration`, the one line
`migrate:production` writes. A migration numbered after that file's, a tree
that lacks the named file, or no file at all while the tree has migrations,
refuses the push ("How a change goes live", ticket 29). It never opens a
database. Inside `.git`, the file needs no ignore rule and cannot be committed.

Every refusal prints `REFUSED: ...` and exits 3, like `suite.py`.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suite  # noqa: E402

REFUSED = 3
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MAIN_BRANCHES = ("main", "master")
DESIGN = "docs/design.md"
CHANGES = "changes"
LAST_APPLIED = "last-production-migration"
NOTE_FILE = re.compile(r"^(\d+)(?:[-_].*)?\.md$")
PAGE = re.compile(r"(^|/)app/(.*/)?page\.(tsx|jsx|ts|js|mdx)$")
BASELINE = re.compile(r"(^|/)[^/]+-snapshots/([^/]+)\.png$")
BASELINE_STEM = re.compile(r"^(?P<slug>.+?)-(?P<width>\d{3,4})(?:-[A-Za-z0-9]+)*$")
MIGRATION = re.compile(r"(^|/)migrations/[^/]+\.sql$")
NUMBER = re.compile(r"^(\d+)")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
SHARED = re.compile(r"^Shared files for ([^:]+):\s*(.*)$")
ROUTE_GROUP = re.compile(r"^\(.*\)$")
SUITE = pathlib.Path(__file__).resolve().with_name("suite.py")
TOKEN = re.compile(r"[`'\"]?([^\s`'\"()]+)[`'\"]?")


class Refusal(Exception):
    """Printed as `REFUSED: ...`; exit 3."""


def git(tree, *args, check=True, stdin=None) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True,
                          text=True, input=stdin)
    if check and done.returncode:
        raise subprocess.CalledProcessError(done.returncode, done.args, done.stdout, done.stderr)
    return done.stdout


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ── What the index holds ─────────────────────────────────────────────────────

def index_paths(tree) -> list[str]:
    return git(tree, "ls-files", "--cached").splitlines()


def index_text(tree, path: str) -> str | None:
    """The staged content of `path`, or None when the index lacks it."""
    done = subprocess.run(["git", "-C", str(tree), "show", f":{path}"],
                          capture_output=True, text=True, errors="replace")
    return done.stdout if done.returncode == 0 else None


def head_text(tree, path: str) -> str | None:
    done = subprocess.run(["git", "-C", str(tree), "show", f"HEAD:{path}"],
                          capture_output=True, text=True, errors="replace")
    return done.stdout if done.returncode == 0 else None


def has_head(tree) -> bool:
    return subprocess.run(["git", "-C", str(tree), "rev-parse", "-q", "--verify", "HEAD"],
                          capture_output=True).returncode == 0


def staged_changes(tree) -> list[tuple[str, str]]:
    """(status, path) for every staged change: A, M or D, renames split."""
    base = "HEAD" if has_head(tree) else EMPTY_TREE
    out = git(tree, "diff", "--cached", "--name-status", "--no-renames", base)
    changes = []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        changes.append((status[:1], path))
    return changes


def branch_name(tree) -> str:
    return git(tree, "symbolic-ref", "--short", "-q", "HEAD", check=False).strip()


def merge_in_progress(tree) -> bool:
    git_dir = pathlib.Path(git(tree, "rev-parse", "--path-format=absolute", "--git-dir").strip())
    return (git_dir / "MERGE_HEAD").exists()


# ── The commit-to-note map ───────────────────────────────────────────────────

def notes_in(folder: str, paths: list[str]) -> list[tuple[str, str]]:
    """(number, path) for every note file directly in `folder`."""
    found = []
    for path in paths:
        head, _, name = path.rpartition("/")
        match = NOTE_FILE.match(name)
        if head == folder and match:
            found.append((match.group(1), path))
    return found


def note_paths(branch: str, paths: list[str]) -> list[str] | None:
    """The index paths of the notes a commit on `branch` belongs to, or None
    when the branch names no note."""
    parts = branch.split("/")
    if parts[0] == "note" and len(parts) >= 2:
        number = parts[-1]
        folder = "/".join([CHANGES, *parts[1:-1]])
        found = [path for n, path in notes_in(folder, paths) if n == number]
        if not found:
            raise Refusal(f"branch `{branch}` names note {number}, and {folder}/ in the index "
                          f"has no `{number}-*.md`. Commit the note first, or use a branch "
                          f"that names no note.")
        return found
    if parts[0] == "feature" and len(parts) >= 2:
        return [path for _, path in notes_in("/".join([CHANGES, *parts[1:]]), paths)]
    return None


def test_paths(lines: list[str]) -> list[str]:
    """Every token in the `## Tests` part that reads as a test-side path."""
    found = []
    for line in lines:
        for match in TOKEN.finditer(line):
            token = match.group(1).rstrip(".,;:")
            if suite.TEST_SIDE.search(token) and token not in found:
                found.append(token)
    return found


def read_note(text: str) -> dict:
    """The lines the check reads: `Screens:`, `Core design:`, `Prototype:`,
    and the test files the `## Tests` part names."""
    note = {"screens": None, "core_design": None, "prototype": None, "tests": []}
    part = ""
    for line in text.splitlines():
        if line.startswith("## "):
            part = line[3:].strip()
            continue
        if part == "Tests":
            note["tests"].extend(t for t in test_paths([line]) if t not in note["tests"])
        elif line.startswith("Screens:"):
            note["screens"] = line[len("Screens:"):].strip()
        elif line.startswith("Core design:"):
            note["core_design"] = line[len("Core design:"):].strip()
        elif line.startswith("Prototype:"):
            note["prototype"] = line[len("Prototype:"):].strip()
    return note


# ── The screens part of the core design ──────────────────────────────────────

def read_screens(text: str | None) -> tuple[list[dict], dict[str, list[str]]]:
    """The rows of the Screen | Route | Group table and the shared files per
    group. No design, or a design with no such table, gives no screens."""
    rows, shared = [], {}
    if text is None:
        return rows, shared
    columns = None
    for line in text.splitlines():
        match = SHARED.match(line.strip())
        if match:
            files = [f.strip().strip("`") for f in match.group(2).split(",") if f.strip()]
            shared.setdefault(match.group(1).strip(), []).extend(files)
            continue
        match = TABLE_ROW.match(line.strip())
        if not match:
            columns = None
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if columns is None:
            columns = cells if cells[:3] == ["Screen", "Route", "Group"] else []
            continue
        if not columns or all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) < 3 or not cells[0]:
            continue
        rows.append({"screen": cells[0], "route": cells[1].rstrip("/") or "/",
                     "group": cells[2]})
    return rows, shared


def route_of_page(path: str) -> str | None:
    """`src/app/(signed-in)/orders/[id]/page.tsx` is `/orders/[id]`."""
    match = PAGE.search(path)
    if not match:
        return None
    inner = match.group(2) or ""
    segments = [s for s in inner.split("/") if s and not ROUTE_GROUP.match(s) and not s.startswith("@")]
    return "/" + "/".join(segments)


def page_folders(paths: list[str]) -> dict[str, str]:
    """Each page folder in the index and its route."""
    folders = {}
    for path in paths:
        route = route_of_page(path)
        if route is not None:
            folders[path.rsplit("/", 1)[0]] = route
    return folders


def folder_of(path: str, folders: dict[str, str]) -> str | None:
    """The deepest page folder above `path`, or None."""
    above = [f for f in folders if path.startswith(f + "/")]
    return max(above, key=len) if above else None


def named_screens(notes: list[dict], rows: list[dict]) -> set[str]:
    """Every screen the mapped notes name, groups expanded."""
    known = {r["screen"] for r in rows}
    groups = {r["group"] for r in rows}
    named = set()
    for note in notes:
        line = note["screens"]
        if line is None:
            raise Refusal(f"note {note['path']} has no `Screens:` line. Name the screens it "
                          f"touches, `all <group>`, or `none`.")
        for item in (i.strip() for i in line.split(",")):
            if not item or item.lower() == "none":
                continue
            if item.lower().startswith("all "):
                group = item[4:].strip()
                if group not in groups:
                    raise Refusal(f"note {note['path']} names `all {group}`, and the screens "
                                  f"table in {DESIGN} has no group `{group}`.")
                named |= {r["screen"] for r in rows if r["group"] == group}
            elif item in known:
                named.add(item)
            else:
                raise Refusal(f"note {note['path']} names screen `{item}`, which the screens "
                              f"table in {DESIGN} does not list.")
    return named


def screens_rewritten(old: str | None, new: str | None) -> list[str]:
    """The existing rows a change to the screens table changed or removed."""
    before = {r["screen"]: r for r in read_screens(old)[0]}
    after = {r["screen"]: r for r in read_screens(new)[0]}
    return [name for name, row in before.items() if after.get(name) != row]


# ── The checks ───────────────────────────────────────────────────────────────

def migrations_refusal(paths: list[str]) -> list[str]:
    """Two `.sql` files with one number in a migrations folder, or one with
    no number, by folder."""
    by_number: dict[tuple[str, str], list[str]] = {}
    reasons = []
    for path in paths:
        if not MIGRATION.search(path):
            continue
        folder, name = path.rsplit("/", 1)
        match = NUMBER.match(name)
        if not match:
            reasons.append(f"{path} has no leading number, so its order is unknown.")
            continue
        by_number.setdefault((folder, match.group(1)), []).append(path)
    for (folder, number), files in sorted(by_number.items()):
        if len(files) > 1:
            reasons.append(f"migrations {' and '.join(sorted(files))} share the number {number}. "
                           f"Give one the next free number in {folder}/.")
    return reasons


def note_refusals(tree, branch: str, paths: list[str], changes: list[tuple[str, str]]) -> list[str]:
    """Every reason the staged diff goes past its note."""
    mapped = note_paths(branch, paths)
    notes = []
    for path in mapped or []:
        notes.append({"path": path, **read_note(index_text(tree, path) or "")})
    rows, shared = read_screens(index_text(tree, DESIGN))
    by_slug = {slug(r["screen"]): r["screen"] for r in rows}
    by_route: dict[str, list[str]] = {}
    for row in rows:
        by_route.setdefault(row["route"], []).append(row["screen"])
    folders = page_folders(paths + [p for s, p in changes if s == "D"])
    shared_of = {f: g for g, files in shared.items() for f in files}
    named = named_screens(notes, rows) if mapped is not None else set()
    who = (f"branch `{branch}` names no note" if mapped is None
           else "no note on this branch names" if len(notes) != 1
           else f"note {notes[0]['path']} does not name")
    reasons = []
    design_changed = False
    on_feature = mapped is not None and branch.startswith("feature/")
    named_tests = {t: n["path"] for n in notes for t in n["tests"]}
    for status, path in changes:
        if path == DESIGN:
            design_changed = True
            continue
        baseline = BASELINE.search(path)
        if on_feature and not baseline and suite.TEST_SIDE.search(path):
            if status == "A" and path not in named_tests:
                reasons.append(f"{path} is a new test file, and no note in the feature names it "
                               f"in its `## Tests` part. A test belongs to a note: a fix round "
                               f"changes the files the findings name, and a finding that needs "
                               f"a new test is a new note for Abdul, not a fix.")
            elif status == "D" and path in named_tests:
                reasons.append(f"{path} is deleted, and {named_tests[path]} still names it in "
                               f"`## Tests`. A note's tests leave with the note: cut the note "
                               f"to changes/<feature>/cut/ in the same commit.")
            continue
        if baseline:
            stem = BASELINE_STEM.match(baseline.group(2))
            screen = by_slug.get(stem.group("slug")) if stem else None
            if screen is None:
                reasons.append(f"{path} is a baseline, and no screen in {DESIGN} has that name.")
            elif screen not in named:
                reasons.append(f"{path} is the baseline of screen `{screen}`, and {who} it.")
            continue
        if path in shared_of:
            group = shared_of[path]
            missing = sorted(r["screen"] for r in rows if r["group"] == group and r["screen"] not in named)
            if missing:
                reasons.append(f"{path} is a shared file of group `{group}`, which touches "
                               f"{', '.join('`' + m + '`' for m in missing)}, and {who} "
                               f"{'them' if len(missing) > 1 else 'it'}. `Screens: all {group}` names them all.")
            continue
        folder = path.rsplit("/", 1)[0] if route_of_page(path) else folder_of(path, folders)
        if folder is None:
            continue
        route = folders[folder]
        screens = by_route.get(route, [])
        if not screens:
            if status == "A" and route_of_page(path):
                reasons.append(f"{path} is a new page at route `{route}`, which the screens "
                               f"table in {DESIGN} does not list. Add its row in the same "
                               f"commit, with a `Core design:` line in the note.")
            continue
        for screen in screens:
            if screen not in named:
                reasons.append(f"{path} is in the route folder of screen `{screen}` "
                               f"({route}), and {who} it.")
    if design_changed:
        if mapped is None:
            reasons.append(f"{DESIGN} changed, and {who}. The core design changes only "
                           f"through a note with a `Core design:` line.")
        elif not any(n["core_design"] for n in notes):
            reasons.append(f"{DESIGN} changed, and no mapped note has a `Core design:` line "
                           f"saying what it adds or rewrites.")
        rewritten = screens_rewritten(head_text(tree, DESIGN) if has_head(tree) else None,
                                      index_text(tree, DESIGN))
        if rewritten and mapped is not None and not any(n["prototype"] for n in notes):
            reasons.append(f"the screens table changed for {', '.join('`' + r + '`' for r in rewritten)}, "
                           f"and no mapped note has a `Prototype:` line. A rewrite of the "
                           f"screens starts from a prototype Abdul approved (ticket 15).")
    return reasons


# ── The kinds ────────────────────────────────────────────────────────────────

def check_commit(tree) -> int:
    if merge_in_progress(tree):
        return check_merge(tree)
    paths = index_paths(tree)
    reasons = migrations_refusal(paths)
    reasons += note_refusals(tree, branch_name(tree), paths, staged_changes(tree))
    if reasons:
        raise Refusal("\n".join(reasons))
    print("note check: passed")
    return 0


def check_merge(tree) -> int:
    reasons = migrations_refusal(index_paths(tree))
    if reasons:
        raise Refusal("\n".join(reasons))
    branch = branch_name(tree)
    if branch not in MAIN_BRANCHES:
        print("note check: migrations numbered once; not a merge into main, so no red check")
        return 0
    print(f"note check: merge into {branch}; running the red check against {branch} before "
          f"the merge", flush=True)
    # git runs a hook with GIT_INDEX_FILE=.git/index and friends in its
    # environment, under which the red check's `git worktree add` fails
    # ("index file open failed: Not a directory", measured 2026-11-03). The
    # red check reads the working tree, not the index, so they go.
    env = {k: v for k, v in os.environ.items()
           if k not in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX")}
    done = subprocess.run([sys.executable, str(SUITE), "red", "--base", "HEAD",
                           "--tree", str(tree)], env=env)
    return done.returncode


def check_push(tree, lines: list[str]) -> int:
    common = pathlib.Path(git(tree, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    record = common / LAST_APPLIED
    last = record.read_text(encoding="utf-8").strip() if record.exists() else None
    reasons = []
    for line in lines:
        fields = line.split()
        if len(fields) != 4:
            continue
        _, local_sha, remote_ref, _ = fields
        if remote_ref.rsplit("/", 1)[-1] not in MAIN_BRANCHES or set(local_sha) == {"0"}:
            continue
        tree_paths = git(tree, "ls-tree", "-r", "--name-only", local_sha).splitlines()
        migrations = [p for p in tree_paths if MIGRATION.search(p)]
        if not migrations:
            continue
        if last is None:
            reasons.append(f"{remote_ref} carries {len(migrations)} migrations and {record} does "
                           f"not exist, so none is known to be applied. Run migrate:production first.")
            continue
        names = {p.rsplit("/", 1)[1]: p for p in migrations}
        if last not in names:
            reasons.append(f"{record} names `{last}`, which {remote_ref} does not carry.")
            continue
        last_number = NUMBER.match(last)
        unnumbered = [p for n, p in sorted(names.items()) if not NUMBER.match(n)]
        if unnumbered or not last_number:
            reasons.append(f"a migration without a leading number cannot be ordered: "
                           f"{', '.join(unnumbered) or last}.")
            continue
        later = [p for n, p in sorted(names.items())
                 if int(NUMBER.match(n).group(1)) > int(last_number.group(1))]
        if later:
            reasons.append(f"{remote_ref} carries {len(later)} migration(s) after `{last}`, the last "
                           f"migrate:production applied: {', '.join(later)}. Migrations go first: "
                           f"run migrate:production, then push.")
    if reasons:
        raise Refusal("\n".join(reasons))
    print("note check: every pushed migration is applied")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=("commit", "merge", "push", "migrations"))
    parser.add_argument("--tree", default=os.getcwd())
    parser.add_argument("rest", nargs="*", help="push: the remote name and url git passes")
    args = parser.parse_args(argv)
    try:
        try:
            tree = pathlib.Path(git(args.tree, "rev-parse", "--show-toplevel").strip())
        except (subprocess.CalledProcessError, OSError) as error:
            raise Refusal(f"git could not read {args.tree}: {getattr(error, 'stderr', error)}")
        if args.kind == "commit":
            return check_commit(tree)
        if args.kind == "merge":
            return check_merge(tree)
        if args.kind == "push":
            return check_push(tree, sys.stdin.read().splitlines())
        reasons = migrations_refusal(index_paths(tree))
        if reasons:
            raise Refusal("\n".join(reasons))
        print("note check: migrations numbered once")
        return 0
    except Refusal as error:
        print(f"REFUSED: {error}")
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
