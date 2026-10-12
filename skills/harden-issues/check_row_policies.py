#!/usr/bin/env python3
"""Print, and refuse the absence of, the row policies of every table an issue touches.

The human's ruling `q-fin4d16a5-06` of 2026-10-12, in the walk of run `batch-4d16a5`:
the hardening pass writes into the issue, as a fact, the row policies of each table
in its `Touches:` and which roles each lets read and write. "Agree."

    python3 ~/.claude/skills/harden-issues/check_row_policies.py --print --issue <file>
    python3 ~/.claude/skills/harden-issues/check_row_policies.py --issue <each file this pass hardened>

**What it was built on.** One tracker's issue 485 took a strike because the
`pending_uploads` delete policy (migration 0058) admits admin, and nobody who wrote or
attacked the criteria knew. The policy sat in a migration the issue never listed:
`Touches:` names files, and the table is reached through `src/model/pending-uploads.ts`.

**Two jobs, one reader of the migrations.**

`--print` replays `supabase/migrations/` in file order (create, drop and alter of
policies, table drops and renames, row level security) and prints the
`## Row policies` section for the issue's tables, each policy with its command, its
roles, its `using` and `with check` text verbatim, and a signature. The attacker
pastes that block into the issue and fills the two blanks on each policy line,
`Reads:` and `Writes:`: the roles it lets through. The expression is the fact; which
roles it admits is the judgement, and the judgement is the attacker's.

With no `--print` the script refuses the stamp when the issue:

- touches a table and carries no `## Row policies` section;
- carries the section and leaves one of those tables out of it;
- names a policy with a signature other than the one the migrations give now (a
  migration changed it since), or names a policy no migration leaves standing;
- leaves a standing policy unnamed, or a policy's `Reads:` or `Writes:` empty or
  still the printed blank;
- says `No policies:` for a table that has policies, or names none for one that has
  none.

**Which tables an issue touches.** The tables are read from the migrations (every
`create table`), never listed here. A table is touched when a `Touches:` entry is the
table or `public.<table>`, or a file the entry names, a folder it holds, or a glob it
matches, carries the table as `public.<table>`, as `.from("<table>")`, or, for a name
with an underscore, as a bare word. A one-word table (`jobs`, `users`) as a bare word
is English as often as SQL, so it does not count. Measured 2026-10-12 on one tracker's
`src/`: of its 31 tables, every one code reaches is reached as `public.<table>` or
`.from("<table>")`, and the bare one-word spellings run to 164 files for `jobs`.
A second tracker reaches its tables as `.from("<table>")`.

An entry the script cannot read (a file the issue will create) is listed as unread
and checks nothing. A `Touches:` that names `supabase/migrations` owes the section
too, because the issue adds or changes a policy: it prints blocks for the tables it
does name, or `None:` with a reason of four words or more.

**What it does not judge.** Whether `Reads:` and `Writes:` are right. That is the
attacker's, from the printed expression, and the gates read it.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import pathlib
import re
import sys

NAME = r'(?:"[^"]+"|[A-Za-z_][A-Za-z_0-9]*)'
TABLE = rf'(?:public\.)?({NAME})'
STATEMENT = re.compile(
    rf"\b(create\s+policy|drop\s+policy(?:\s+if\s+exists)?|alter\s+policy)\s+({NAME})\s+on\s+{TABLE}",
    re.IGNORECASE,
)
CREATE_TABLE = re.compile(rf"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?{TABLE}\s*\(", re.IGNORECASE)
DROP_TABLE = re.compile(rf"\bdrop\s+table\s+(?:if\s+exists\s+)?{TABLE}", re.IGNORECASE)
RENAME_TABLE = re.compile(rf"\balter\s+table\s+(?:if\s+exists\s+)?{TABLE}\s+rename\s+to\s+{TABLE}", re.IGNORECASE)
RLS = re.compile(
    rf"\balter\s+table\s+(?:if\s+exists\s+)?{TABLE}\s+(enable|disable)\s+row\s+level\s+security", re.IGNORECASE
)
MENTION = re.compile(r"\b(?:create|alter)\s+policy\b", re.IGNORECASE)
CLAUSE = re.compile(r"(as|for|to|using|with\s+check|rename\s+to)\b", re.IGNORECASE)

SECTION = re.compile(r"^#{2,6}[ \t]+Row policies[ \t]*$", re.MULTILINE | re.IGNORECASE)
NEXT_HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)
TABLE_BULLET = re.compile(r"^[-*][ \t]+Table[ \t]+`([^`]+)`", re.IGNORECASE)
POLICY_LINE = re.compile(r"^[ \t]+[-*][ \t]+`([^`]+)`[ \t]+#([0-9a-f]{8})\b(.*)$", re.IGNORECASE)
NONE_LINE = re.compile(r"^[ \t]*[-*]?[ \t]*None:[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE)
NO_POLICIES = re.compile(r"No policies:[ \t]*(.*)", re.IGNORECASE)
LABELS = ("Reads", "Writes")
REASON_WORDS = 4
BLANK = "<fill>"


def unquote(name: str) -> str:
    return name[1:-1] if name.startswith('"') else name.lower()


def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def statement_tail(sql: str, start: int) -> str:
    """The text from `start` to the next `;` outside brackets and single quotes."""
    depth, quoted = 0, False
    for n in range(start, len(sql)):
        char = sql[n]
        if char == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ";" and depth <= 0:
            return sql[start:n]
    return sql[start:]


def dynamic_text(sql: str, start: int) -> str:
    """A statement built inside `execute format(...)`: the rest of the string literal
    `start` sits in, and the adjacent literals that follow it, joined."""
    out, quoted, n = [], True, start
    while n < len(sql):
        char = sql[n]
        if quoted and char == "'":
            if sql[n + 1:n + 2] == "'":
                out.append("'")
                n += 1
            else:
                quoted = False
        elif quoted:
            out.append(char)
        elif char == "'":
            quoted = True
        elif not char.isspace():
            break
        n += 1
    return "".join(out)


def clauses(tail: str) -> dict[str, str]:
    """`as`, `for`, `to`, `using`, `with check`, `rename to` of a policy statement,
    each found at bracket depth 0 so a word inside an expression is never a clause."""
    spots, depth, quoted = [], 0, False
    for n, char in enumerate(tail):
        if char == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and (n == 0 or not (tail[n - 1].isalnum() or tail[n - 1] == "_")):
            found = CLAUSE.match(tail, n)
            if found:
                spots.append((n, found.end(), re.sub(r"\s+", " ", found.group(1).lower())))
    values = {}
    for i, (_, end, key) in enumerate(spots):
        stop = spots[i + 1][0] if i + 1 < len(spots) else len(tail)
        values[key] = " ".join(tail[end:stop].split())
    return values


def expression(text: str) -> str:
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return text


class Policy:
    def __init__(self, name: str, parts: dict[str, str], source: str):
        self.name, self.source = name, source
        self.command = parts.get("for", "all").lower()
        self.mode = parts.get("as", "permissive").lower()
        self.roles = parts.get("to", "public")
        self.using = expression(parts.get("using", ""))
        self.check = expression(parts.get("with check", ""))

    def merge(self, parts: dict[str, str], source: str) -> None:
        if "to" in parts:
            self.roles = parts["to"]
        if "using" in parts:
            self.using = expression(parts["using"])
        if "with check" in parts:
            self.check = expression(parts["with check"])
        self.source = source

    def signature(self) -> str:
        basis = "|".join((self.mode, self.command, self.roles, self.using, self.check)).lower()
        return hashlib.sha1(basis.encode()).hexdigest()[:8]


class Migrations:
    """The policies standing after every migration has run, in file order."""

    def __init__(self, folder: pathlib.Path):
        self.tables: set[str] = set()
        self.unplaced: dict[str, str] = {}
        self.policies: dict[str, dict[str, Policy]] = {}
        self.rls: dict[str, bool] = {}
        files = sorted(folder.glob("*.sql"))
        self.latest = files[-1].name if files else ""
        for path in files:
            self.replay(path.name, strip_comments(path.read_text(errors="replace")))

    def replay(self, source: str, sql: str) -> None:
        events = [(f.start(), "table", f) for f in CREATE_TABLE.finditer(sql)]
        for kind, pattern in (("drop table", DROP_TABLE), ("rename", RENAME_TABLE),
                              ("rls", RLS), ("policy", STATEMENT)):
            events += [(f.start(), kind, f) for f in pattern.finditer(sql)]
        placed = {f.start() for f in STATEMENT.finditer(sql)}
        for mention in MENTION.finditer(sql):
            if mention.start() not in placed:
                self.unplaced.setdefault(source, re.sub(r"\s+", " ", sql[mention.start():mention.start() + 80]))
        for _, kind, found in sorted(events, key=lambda event: event[0]):
            if kind == "table":
                table = unquote(found.group(1))
                self.tables.add(table)
                self.policies.setdefault(table, {})
            elif kind == "drop table":
                table = unquote(found.group(1))
                self.tables.discard(table)
                self.policies.pop(table, None)
                self.rls.pop(table, None)
            elif kind == "rename":
                old, new = unquote(found.group(1)), unquote(found.group(2))
                if old in self.tables:
                    self.tables.discard(old)
                    self.tables.add(new)
                    self.policies[new] = self.policies.pop(old, {})
                    self.rls[new] = self.rls.pop(old, False)
            elif kind == "rls":
                self.rls[unquote(found.group(1))] = found.group(2).lower() == "enable"
            else:
                self.apply_policy(source, sql, found)

    def apply_policy(self, source: str, sql: str, found: re.Match) -> None:
        verb = re.sub(r"\s+", " ", found.group(1).lower())
        name, table = unquote(found.group(2)), unquote(found.group(3))
        stock = self.policies.setdefault(table, {})
        if verb.startswith("drop"):
            stock.pop(name, None)
            return
        if sql.count("'", 0, found.start()) % 2:
            text = dynamic_text(sql, found.start())
            again = STATEMENT.match(text)
            if not again:
                self.unplaced.setdefault(source, text[:80])
                return
            tail = text[again.end():].replace("%I", "current_user")
        else:
            tail = statement_tail(sql, found.end())
        parts = clauses(tail)
        if verb.startswith("create"):
            stock[name] = Policy(name, parts, source)
        elif name in stock:
            policy = stock[name]
            if "rename to" in parts:
                new = unquote(parts["rename to"])
                stock[new] = stock.pop(name)
                policy.name = new
            policy.merge(parts, source)


def repo_root(issue: pathlib.Path, given: str | None) -> pathlib.Path | None:
    if given:
        return pathlib.Path(given).resolve()
    for folder in [issue.resolve().parent, *issue.resolve().parents]:
        if (folder / "supabase" / "migrations").is_dir():
            return folder
    return None


def touches(text: str) -> list[str]:
    """Every entry on every `Touches:` line, backticks off."""
    entries = []
    for line in re.findall(r"^Touches:[ \t]*(.*)$", text, re.MULTILINE):
        entries += [item.strip(" `") for item in line.split(",") if item.strip(" `")]
    return entries


def readable(root: pathlib.Path, entry: str) -> list[pathlib.Path] | None:
    """The files an entry stands for, or None where nothing on disk answers to it."""
    path = root / entry
    if path.is_file():
        return [path]
    if path.is_dir():
        return [p for p in path.rglob("*") if p.is_file() and "node_modules" not in p.parts]
    pattern = "".join(c if c in "*?" else glob.escape(c) for c in entry)
    found = [pathlib.Path(p) for p in glob.glob(str(root / pattern), recursive=True)]
    files = [p for p in found if p.is_file()] + [q for p in found if p.is_dir() for q in p.rglob("*") if q.is_file()]
    return files or None


def reaching(known: frozenset[str]) -> re.Pattern:
    """One pattern for every spelling measured in the docstring; group 1 or 2 is the table."""
    every = "|".join(re.escape(t) for t in sorted(known, key=len, reverse=True))
    underscored = "|".join(re.escape(t) for t in sorted(known, key=len, reverse=True) if "_" in t)
    parts = [rf"\bpublic\.({every})\b", rf"\.from\(\s*[\"'`]({every})[\"'`]"]
    if underscored:
        parts.append(rf"\b({underscored})\b")
    return re.compile("|".join(parts))


def reached(known: set[str], source: str, pattern: re.Pattern | None = None) -> set[str]:
    """The tables a file's text reaches."""
    if not known:
        return set()
    pattern = pattern or reaching(frozenset(known))
    return {next(g for g in found.groups() if g) for found in pattern.finditer(source)}


def touched(root: pathlib.Path, state: Migrations, entries: list[str]) -> tuple[dict[str, str], list[str], bool]:
    """(table -> the entry that reaches it, entries unread, whether the migrations folder is named)."""
    tables, unread, migrating = {}, [], False
    pattern = reaching(frozenset(state.tables)) if state.tables else None
    for entry in entries:
        bare = entry.removeprefix("public.")
        if bare in state.tables:
            tables.setdefault(bare, entry)
            continue
        if "supabase/migrations" in entry:
            migrating = True
            continue
        files = readable(root, entry)
        if files is None:
            unread.append(entry)
            continue
        for path in files:
            try:
                source = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for table in reached(state.tables, source, pattern):
                tables.setdefault(table, entry)
    return tables, unread, migrating


def policy_line(policy: Policy) -> str:
    using = f"; using: {policy.using}" if policy.using else ""
    check = f"; with check: {policy.check}" if policy.check else ""
    return (f"  - `{policy.name}` #{policy.signature()} — {policy.command} to {policy.roles}"
            f"{using}{check}. Reads: {BLANK}. Writes: {BLANK}.")


def block(state: Migrations, tables: dict[str, str]) -> str:
    out = ["## Row policies", "",
           f"Read from `supabase/migrations/` up to `{state.latest}` by `check_row_policies.py` "
           f"on {datetime.date.today().isoformat()}. `Reads:` and `Writes:` name the roles the "
           "expression lets through; the rest is the migrations' own text.", ""]
    for table in sorted(tables):
        rls = "row level security on" if state.rls.get(table) else "ROW LEVEL SECURITY NOT ENABLED"
        out.append(f"- Table `{table}` ({rls}; reached through `{tables[table]}`)")
        policies = state.policies.get(table, {})
        if not policies:
            out.append(f"  - No policies: {BLANK}")
        for policy in sorted(policies.values(), key=lambda p: p.name):
            out.append(policy_line(policy))
    for source in sorted(state.unplaced):
        out.append(f"- Not itemised: `{source}` builds policy names in a loop; this reader cannot name them.")
    return "\n".join(out) + "\n"


def section(text: str) -> str | None:
    found = SECTION.search(text)
    if not found:
        return None
    following = NEXT_HEADING.search(text, found.end())
    return text[found.end():following.start() if following else len(text)]


def read_blocks(body: str) -> dict[str, dict]:
    """table -> {"policies": {name: [signature, text]}, "none": text or None}."""
    blocks, current, last = {}, None, None
    for line in body.splitlines():
        table = TABLE_BULLET.match(line)
        policy = POLICY_LINE.match(line)
        none = NO_POLICIES.search(line)
        if table:
            current = blocks.setdefault(table.group(1), {"policies": {}, "none": None})
            last = None
        elif policy and current is not None:
            last = [policy.group(2).lower(), policy.group(3)]
            current["policies"][policy.group(1)] = last
        elif none and current is not None:
            current["none"] = none.group(1).strip()
            last = None
        elif line.strip() and last is not None and not line.lstrip().startswith(("-", "*")):
            last[1] += " " + line.strip()
        elif not line.strip():
            last = None
    return blocks


def labelled(text: str) -> dict[str, str]:
    marks = list(re.finditer(r"\b(Reads|Writes):", text))
    values = {}
    for n, mark in enumerate(marks):
        end = marks[n + 1].start() if n + 1 < len(marks) else len(text)
        values[mark.group(1)] = text[mark.end():end].strip(" .")
    return values


def empty(value: str | None) -> bool:
    return not value or BLANK in value or "<" in value or not re.search(r"[A-Za-z]", value)


def role_faults(table: str, name: str, text: str) -> list[str]:
    values = labelled(text)
    return [f"table `{table}`: policy `{name}` has no `{label}:` roles filled in"
            for label in LABELS if empty(values.get(label))]


def table_faults(state: Migrations, table: str, held: dict | None) -> list[str]:
    if held is None:
        return [f"table `{table}` has no block in `## Row policies`: run `--print` and paste it"]
    found, policies = [], state.policies.get(table, {})
    if not policies:
        if held["policies"]:
            found.append(f"table `{table}` has no standing policy; the section names "
                         + ", ".join(f"`{n}`" for n in held["policies"])
                         + ", which no migration leaves standing")
        if empty(held["none"]):
            found.append(f"table `{table}` has no policy: say `No policies:` and what that means "
                         "for every role (row level security on and no policy denies them all)")
        return found
    if held["none"] is not None:
        found.append(f"table `{table}` has policies and the section says `No policies:`")
    for name, policy in sorted(policies.items()):
        if name not in held["policies"]:
            found.append(f"table `{table}`: policy `{name}` stands ({policy.source}) "
                         "and the section does not name it")
            continue
        signature, text = held["policies"][name]
        if signature != policy.signature():
            found.append(f"table `{table}`: policy `{name}` has changed since the section was written "
                         f"({policy.source}); run `--print` again")
        found += role_faults(table, name, text)
    for name in held["policies"]:
        if name not in policies:
            found.append(f"table `{table}`: the section names policy `{name}`, "
                         "which no migration leaves standing")
    return found


def faults(text: str, root: pathlib.Path, state: Migrations) -> tuple[list[str], list[str]]:
    """(reasons this issue is refused, entries that were not readable)."""
    tables, unread, migrating = touched(root, state, touches(text))
    if not tables and not migrating:
        return [], unread
    body = section(text)
    if body is None:
        names = ", ".join(f"`{t}`" for t in sorted(tables)) or "`supabase/migrations`"
        return [f"touches {names} and has no `## Row policies` section: run "
                "`check_row_policies.py --print --issue <file>` and paste what it prints"], unread
    held = read_blocks(body)
    found = [f"the section does not carry the `Not itemised:` line for `{source}`, "
             "which builds policy names in a loop (run `--print`)"
             for source in sorted(state.unplaced) if f"Not itemised: `{source}`" not in body]
    for table in sorted(tables):
        found += table_faults(state, table, held.get(table))
    if not tables:
        none = NONE_LINE.search(body)
        reasoned = none and len(re.findall(r"[A-Za-z]+", none.group(1))) >= REASON_WORDS
        if not held and not reasoned:
            found.append("names `supabase/migrations` and no table: say `None:` with a reason, "
                         "or print the blocks for the tables the migration changes")
    for table, one in held.items():
        if table not in state.tables:
            for name, (_, rest) in one["policies"].items():
                found += role_faults(table, name, rest)
    return found, unread


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print, or check, the row policies of every table an issue's Touches: reaches.")
    parser.add_argument("--issue", required=True, action="append", dest="issues",
                        help="an issue file; repeat for each when checking")
    parser.add_argument("--print", action="store_true", dest="show",
                        help="print the `## Row policies` block for the issue's tables")
    parser.add_argument("--repo", help="the repository root; found above the issue file when omitted")
    args = parser.parse_args()
    if args.show and len(args.issues) != 1:
        parser.error("--print takes one --issue")

    refused, states = False, {}
    for one in args.issues:
        path = pathlib.Path(one)
        identifier = re.match(r"^(\d+[a-z]?)-", path.name)
        identifier = identifier.group(1) if identifier else path.name
        try:
            text = path.read_text()
        except OSError as error:
            print(f"REFUSED   {identifier}: unreadable, {error}", file=sys.stderr)
            refused = True
            continue
        root = repo_root(path, args.repo)
        if root is None or not (root / "supabase" / "migrations").is_dir():
            print(f"ok        {identifier}: no supabase/migrations above this file; no tables to place "
                  "(pass --repo if the issue belongs to a repository that has them)")
            continue
        if root not in states:
            states[root] = Migrations(root / "supabase" / "migrations")
        state = states[root]
        if args.show:
            tables, unread, _ = touched(root, state, touches(text))
            print(block(state, tables) if tables else "No table in this issue's `Touches:`.\n")
            if unread:
                print(f"unread (not on disk): {', '.join(unread)}", file=sys.stderr)
            continue
        found, unread = faults(text, root, state)
        if found:
            refused = True
            for fault in found:
                print(f"REFUSED   {identifier}: {fault}", file=sys.stderr)
        else:
            note = f" ({len(unread)} Touches: entries unread, not on disk)" if unread else ""
            print(f"ok        {identifier}{note}")

    if not args.show:
        print(f"read {len(args.issues)} issue file(s)")
    if refused:
        print("\nREFUSED: no stamp until each issue above carries the row policies of its tables. "
              "Run `--print` for the block; fill `Reads:` and `Writes:` on each policy.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
