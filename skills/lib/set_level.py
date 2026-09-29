#!/usr/bin/env python3
"""Set an issue's `Level:` from the paths it touches.

    python3 ~/.claude/skills/lib/set_level.py <issue file> [<issue file> ...]

Tracker-tooling issue 34, the level follows the risk file (issue 32, item 5; rule 4).
Each repository holds one risk file, `docs/agents/risk-paths.md`, a table mapping path
patterns to the five classes of the direct road. This script reads an issue's
`Touches:` line against it. Any item that meets a pattern makes the issue `full`,
and so does `Writes rows: yes` under `## Target database` (default `q-h0925-34-4`).
Otherwise it is `light`. The script writes the `Level:` line and no other line, and
prints the pattern and class that made an issue full. `/to-issues` runs it on every
drafted slice at step 3.5, after the files are on disk.

WHAT IT REFUSES, exit 1, the file left byte-identical:

  - a repository with no risk file. A missing file must not read as "nothing here
    is risky", so the refusal names the absolute path it looked for;
  - a risk file with no pattern row and no `No risk paths: <reason>` line, or a row
    whose class is not one of the five (default `q-h0925-34-3`);
  - an issue with no `Touches:` line, or one whose line is not backticked items:
    `none`, `none yet` and `none.` with prose, `unswept`, bare issue numbers, and a
    line wrapped onto the next (default `q-h0925-34-1`). Reading `588` as a path
    that meets no pattern would give `light`, the unsafe direction;
  - an issue whose `## Target database` gives no `Writes rows: yes` or `no`, for
    the same reason;
  - a `Level:` that is neither `light` nor `full`, or two `Level:` lines.

IT NEVER LOWERS A LEVEL. A `Level: full` stays `full` when the paths give `light`,
and the output says so. The script cannot tell its own `full` from a human's, so a
human lowers a level by hand.

THE MEET RULE (default `q-h0925-34-2`, as the seam pass h0925 restated it). Both
sides are normalised the same way: a leading `./` is removed, `~` is expanded, and a
relative path is read against the main checkout's root. A path inside a linked
worktree is rebased onto the main checkout, because `~/.claude/skills/` names the
main checkout while runs build under `.claude/worktrees/`. Then two items meet when
they are equal, when either matches the other as a glob, or when either ends in `/`
and the other begins with it. In a glob `*` stays inside one path segment and `**`
crosses `/`; every other character is literal, because Next.js paths such as
`src/app/[number]/page.tsx` carry brackets. `meet()` names which of the three made
the meet, so issue 35 can print a directory-only meet on its own line.

ONE DEFINITION. `read_risk_file()`, `normalise()` and `meet()` are imported by the
later callers (issues 35, 41 and 42's hook), the way `number-claim-guard.py`
imports `claim_number.CHECK_SHAPES`, so the callers cannot drift apart. The
`Touches:` line itself is read by `headers()` in `run-issues/check_issue_ready.py`,
issue 33's one reader.

Exit codes follow `claim_number.py`: 0 the level is written, 1 refused, 2 the issue
file is not inside a git repository.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "run-issues"))

from check_issue_ready import NO_LINE, PROSE, STRICT, headers  # noqa: E402  Issue 33's one reader.

RISK_FILE = pathlib.Path("docs") / "agents" / "risk-paths.md"
CLASSES = ("money", "sign-in", "secrets", "migrations", "writes-rows")
EQUAL, GLOB, DIRECTORY = "equal", "glob", "directory"

TABLE_ROW = re.compile(r"^\s*\|(.*)\|\s*$")
SEPARATOR_CELL = re.compile(r"^\s*:?-{3,}:?\s*$")
NO_RISK_PATHS = re.compile(r"^No risk paths:[ \t]*(.*)$", re.MULTILINE)
LEVEL_LINE = re.compile(r"^Level:[ \t]*(.*)$")
TARGET_DATABASE = re.compile(r"^##\s+Target database\s*$", re.MULTILINE | re.IGNORECASE)
NEXT_SECTION = re.compile(r"^#{1,2}\s", re.MULTILINE)
WRITES_ROWS = re.compile(r"Writes rows:[\s*]*([A-Za-z]*)")


class Refused(Exception):
    """The script cannot place something, so it writes nothing."""


class NotARepository(Exception):
    pass


@dataclass(frozen=True)
class Risk:
    pattern: str
    risk_class: str


@dataclass(frozen=True)
class RiskFile:
    rows: tuple[Risk, ...]
    no_risk_reason: str | None


def read_risk_file(path: pathlib.Path) -> RiskFile:
    """The `Pattern | Class` table of a risk file. Raises `Refused` on a missing file,
    a file that says nothing, and a row it cannot place."""
    if not path.is_file():
        raise Refused(f"no risk file at {path}. Write one before any level is set: "
                      "a missing file must not read as \"nothing here is risky\".")
    text = path.read_text(encoding="utf-8")
    rows: list[Risk] = []
    in_table = False
    for number, line in enumerate(text.splitlines(), 1):
        cells_found = TABLE_ROW.match(line)
        if not cells_found:
            in_table = False
            continue
        cells = [cell.strip() for cell in cells_found.group(1).split("|")]
        if [cell.strip("*` ").lower() for cell in cells] == ["pattern", "class"]:
            in_table = True
            continue
        if all(SEPARATOR_CELL.match(cell) for cell in cells):
            continue
        # A row outside a `Pattern | Class` table is refused, never skipped: a
        # skipped money row beside a `No risk paths:` line would read as all light.
        if not in_table or len(cells) != 2 or not cells[0].strip("`") or cells[1].strip("`") not in CLASSES:
            raise Refused(f"{path}, line {number}: `{line.strip()}` is not a pattern and one "
                          f"of the classes {', '.join(CLASSES)}.")
        rows.append(Risk(cells[0].strip("`"), cells[1].strip("`")))
    reason = NO_RISK_PATHS.search(text)
    reason_text = reason.group(1).strip() if reason else None
    if not rows and not reason_text:
        raise Refused(f"{path} holds no `Pattern | Class` row and no `No risk paths: <reason>` "
                      "line. An empty risk file reads as \"nothing here is risky\", exactly "
                      "as a missing one would.")
    return RiskFile(tuple(rows), reason_text)


def normalise(item: str, main_root: str, tree_root: str | None = None) -> str:
    """One spelling for a `Touches:` item or a risk pattern, before `meet()`."""
    item = item.strip()
    while item.startswith("./"):
        item = item[2:]
    item = os.path.expanduser(item)
    if not os.path.isabs(item):
        item = main_root.rstrip("/") + "/" + item
    if tree_root and tree_root != main_root:
        prefix = tree_root.rstrip("/") + "/"
        if item.startswith(prefix):
            item = main_root.rstrip("/") + "/" + item[len(prefix):]
    return item


def _glob(pattern: str) -> re.Pattern[str]:
    out = []
    at = 0
    while at < len(pattern):
        if pattern.startswith("**/", at):
            out.append("(?:.*/)?")
            at += 3
        elif pattern.startswith("**", at):
            out.append(".*")
            at += 2
        elif pattern[at] == "*":
            out.append("[^/]*")
            at += 1
        else:
            out.append(re.escape(pattern[at]))
            at += 1
    return re.compile("".join(out) + r"\Z")


def meet(one: str, other: str) -> str | None:
    """Whether two normalised items meet, and how: `equal`, `glob` or `directory`."""
    if one == other:
        return EQUAL
    if ("*" in one and _glob(one).match(other)) or ("*" in other and _glob(other).match(one)):
        return GLOB
    if (one.endswith("/") and other.startswith(one)) or (other.endswith("/") and one.startswith(other)):
        return DIRECTORY
    return None


def roots(directory: pathlib.Path) -> tuple[str, str]:
    """The worktree root holding `directory`, and the main checkout's root."""
    def rev_parse(flag: str) -> str:
        done = subprocess.run(["git", "rev-parse", flag], cwd=directory,
                              capture_output=True, text=True)
        if done.returncode:
            raise NotARepository(str(directory))
        return done.stdout.strip()
    tree = rev_parse("--show-toplevel")
    common = pathlib.Path(rev_parse("--git-common-dir"))
    if not common.is_absolute():
        common = directory / common
    return os.path.realpath(tree), os.path.realpath(common.parent)


def writes_rows(text: str) -> bool:
    section = TARGET_DATABASE.search(text)
    if not section:
        raise Refused("no `## Target database` section, so nothing says whether it writes rows.")
    body = text[section.end():]
    end = NEXT_SECTION.search(body)
    body = body[:end.start()] if end else body
    answer = WRITES_ROWS.search(body)
    word = answer.group(1).lower() if answer else ""
    if word not in ("yes", "no"):
        raise Refused("`## Target database` gives no `Writes rows: yes` or `Writes rows: no`.")
    return word == "yes"


def touched(text: str) -> tuple[str, ...]:
    found = headers(text)
    if found.touches_form == NO_LINE:
        raise Refused("no `Touches:` line, so there are no paths to read against the risk file.")
    line = found.touches_line or ""
    says_none = line.split(" ")[0].rstrip(".,") == "none"
    if found.touches_form not in (STRICT, PROSE) or says_none:
        form = "none" if says_none else found.touches_form
        raise Refused(f"`Touches: {line}` is {form}. The script reads backticked paths only; "
                      "a line that names none gives no level.")
    return found.touches


def verdict(text: str, risk: RiskFile, main_root: str, tree_root: str) -> tuple[str, list[str]]:
    """The level the paths give, and one reason line per meet."""
    reasons = []
    for item in touched(text):
        mine = normalise(item, main_root, tree_root)
        for row in risk.rows:
            how = meet(mine, normalise(row.pattern, main_root, tree_root))
            if how:
                reasons.append(f"`{item}` meets `{row.pattern}` ({row.risk_class}, {how})")
    if writes_rows(text):
        reasons.append("writes rows: `## Target database` says `Writes rows: yes`")
    return ("full" if reasons else "light"), reasons


def write_level(text: str, level: str) -> tuple[str, str | None]:
    """The text with its `Level:` set, and the level it already held."""
    lines = text.splitlines(keepends=True)
    heading = next((i for i, line in enumerate(lines) if line.startswith("# ")), len(lines))
    # Only the header holds the level; a `Level:` quoted in the body is prose.
    at = [i for i, line in enumerate(lines[:heading]) if LEVEL_LINE.match(line)]
    if len(at) > 1:
        raise Refused(f"{len(at)} `Level:` lines; an issue carries one.")
    if at:
        old = LEVEL_LINE.match(lines[at[0]]).group(1).strip()
        if old not in ("light", "full"):
            raise Refused(f"`Level: {old}` is neither `light` nor `full`.")
        if old == "full":
            level = "full"
        ending = lines[at[0]][len(lines[at[0]].rstrip("\r\n")):]
        lines[at[0]] = f"Level: {level}{ending}"
        return "".join(lines), old
    header = lines[:heading]
    anchor = next((i for label in ("Kind:", "Touches:")
                   for i in range(len(header) - 1, -1, -1) if header[i].startswith(label)), None)
    if anchor is None:
        anchor = max((i for i, line in enumerate(header) if line.strip()), default=-1)
    ending = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    if anchor >= 0 and not lines[anchor].endswith(("\n", "\r")):
        lines[anchor] += ending
    lines.insert(anchor + 1, f"Level: {level}{ending}")
    return "".join(lines), None


def set_level(path: pathlib.Path) -> str:
    """Write the level into one issue file and return what to print."""
    path = path.resolve()
    tree_root, main_root = roots(path.parent)
    risk = read_risk_file(pathlib.Path(tree_root) / RISK_FILE)
    text = path.read_bytes().decode("utf-8")
    level, reasons = verdict(text, risk, main_root, tree_root)
    new, old = write_level(text, level)
    if new != text:
        path.write_bytes(new.encode("utf-8"))
    lines = [f"{path.name}: Level: {'full' if old == 'full' else level}"]
    lines += [f"  {reason}" for reason in reasons]
    if old == "full" and level == "light":
        lines.append("  kept `Level: full`, stricter than the paths give (light); "
                     "the script never lowers a level")
    elif level == "light":
        lines.append("  no item meets a risk pattern" if risk.rows
                     else f"  the risk file says: No risk paths: {risk.no_risk_reason}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues", nargs="+", type=pathlib.Path, help="issue files to level")
    args = parser.parse_args(argv)
    worst = 0
    for path in args.issues:
        try:
            print(set_level(path))
        except Refused as exc:
            print(f"REFUSED {path}: {exc}", file=sys.stderr)
            worst = max(worst, 1)
        except NotARepository as exc:
            print(f"REFUSED: {exc} is not inside a git repository, so there is no risk file "
                  "to read.", file=sys.stderr)
            worst = 2
    return worst


if __name__ == "__main__":
    sys.exit(main())
