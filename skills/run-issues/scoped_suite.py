#!/usr/bin/env python3
"""Run the scoped suite: every test whose imports reach a changed file, every
test that lists a directory, and the repo-wide checks, with coverage, logged and
recorded as `run_suite.py` records.

    python3 ~/.claude/skills/run-issues/scoped_suite.py [--since <ref>]

The perf audit of 2026-09-28 (one project, `.scratch/workflow-audit/
perf-audit-2026-09-28/`), fixes 3 and 4, and the human's ruling
`q-fin-44052e-01` of 2026-09-30.

## Who runs it

- A `Level: light` issue's implementer, as its one suite (rule 5 of
  tracker-tooling issue 40 still refuses it the whole suite).
- The runner, after a correction round that changed test files only.
  `run_suite.py --stage correction` refuses the whole suite there and names
  this script.

## Why the set is wider than the touched files

A light issue's scoped run used to read the tests of the files it touched,
and three reds escaped to the finale: issue 181 broke
`tests/documents/brief-route.test.ts`, whose imports reach a file 181 changed;
254 broke `tests/build-checks/design-values.test.ts` and 234c broke
`tests/sessions/standing-rules.test.ts`, repo-wide checks that read source as
text and import nothing either changed.

So the set is three parts:

1. **The import closure.** `vitest list --filesOnly --changed=<since>` names
   every test file that transitively imports a changed file, changed test
   files included. vitest walks its own module graph, so aliases resolve as
   the suite resolves them. Changed means the uncommitted work, since the
   runner commits each issue after its gates; `--since <ref>` widens it. A
   change to a file vitest's `forceRerunTriggers` names, `package.json` or the
   vitest config by default, lists every file: a whole suite by that road,
   and correctly so.
2. **The repo-wide checks.** vitest filters, `tests/build-checks/` and
   `standing-rules.test.` by default. A repo replaces them with a
   `sweepTests` list in `.claude/run-isolation.json`. A filter matches a test
   file whose path holds it, and the config's own `exclude` still applies, so
   a harness file named by a filter stays out.
3. **The tree readers.** The human's ruling `q-fin-44052e-01`, road A: every
   test that lists a directory to find what it checks. Two runs in a row
   shipped a finale red of this class: issue 299 with
   `tests/controls/layout/skeleton.test.tsx`, and issue 304 (run
   `batch-44052e`) with `tests/controls/popup-sheet-changed.test.ts`. Both
   list the tree through a helper in `tests/build-checks/` and import nothing
   the issue changed. `tree_readers` reads every test `vitest list` names and
   follows what it uses, name by name, through the repository.

## How a tree reader is found

The walk runs over names, not files. A walk by file joined 102 of one
project's tests outside the checks against the finale's 46: 61 tests reach
`tests/scaffold/database-modules.ts`, and at least 22 of them import only its
`REPO`, never the `sourceFiles` beside it. A test joins when its own text lists a directory, or when a
name it imports is declared by text that does, through the names that text
uses in turn: `modulesUnder` calls `sourceFiles`, which calls `readdirSync`.
Imports resolve as a bundler does: relative paths, `tsconfig.json`'s
`paths` (that project imports through `@/` 2,308 times), `index` files, and a
`.js` specifier standing for its `.ts` source. Re-exports, `export *` and
namespace imports are followed; a namespace or side-effect import takes the
whole file.

`LISTING` names the directory-listing forms. That project's tests, helpers
and scripts held two on 2026-10-01, `readdirSync` and `readdir`, measured by
`grep -rhoE 'readdir|opendir|glob|ls-files|fdir|walkSync' tests src scripts`.
The rest are the other ways Node and its common packages list a tree.

What the walk cannot place, it runs. A test joins, and the output names why,
when it reaches an import that is neither a repository file, a package in
`node_modules` nor a Node built-in, or a file that ends inside a comment or a
template string. Comments are not read for imports, and template string
bodies and quote string bodies are not read as imports or uses, so the
fixture code tests carry in strings is never followed; a listing written
inside a string, such as a `git ls-files` command, still counts.

Measured on that project on 2026-10-01, at main `e7703fd4`: 597 test files,
62 tree readers outside the checks, the walk about 4 s. The 62 are the
finale's 46 and 16 more, 14 of them tests that call `migrate()` in
`scripts/migrate.mjs`, which lists `supabase/migrations/`. Their run time
was not measured.

The harness suite runs after it where the diff touches a path the harness
contract names (`run_suite.harness_wanted`).

## What it refuses, exit 3

A `sweepTests` value that is not a list of non-empty strings, a harness
contract it cannot place, either `vitest list` failing (an empty set read as
"nothing to test" would be a false green), a `node` that cannot name its
built-in modules, a directory outside git, and a second green run on an
unchanged tree.

The command's exit passes through, and 127 is a command that could not start.
The record goes to the same store as `run_suite.py`'s, at stage `scoped`, with
the files, tree readers and filters it ran, why each unplaced reader joined,
and the coverage report it kept.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_suite  # noqa: E402

STAGE = "scoped"
DEFAULT_SWEEP = ("tests/build-checks/", "standing-rules.test.")
LISTING = re.compile(
    r"\b(?:readdirSync|readdir|opendirSync|opendir|globSync)\b|\bglob\s*\(|"
    r"import\.meta\.glob|\bls-files\b|"
    r"[\"'](?:fast-glob|globby|tinyglobby|fdir|readdirp|glob)[\"']")
# A module is read as top-level chunks. A chunk opens on a line whose first
# character can start a statement; comments, closing braces and indented lines
# stay in the chunk above. Import lines inside a test's fixture strings are
# indented or open on a quote, so they are never read as imports.
CHUNK = re.compile(r"^(?=[A-Za-z_$@])", re.MULTILINE)
QUOTED = r"""["']([^"'\s]+)["']"""
IMPORT = re.compile(r"import\s+(?:type\s+)?(.*?)\s*\bfrom\s*" + QUOTED, re.DOTALL)
BARE_IMPORT = re.compile(r"import\s*" + QUOTED)
STAR_FROM = re.compile(r"export\s+(?:type\s+)?\*\s*(?:as\s+([\w$]+)\s*)?from\s*" + QUOTED)
LIST_FROM = re.compile(r"export\s+(?:type\s+)?\{([^}]*)\}\s*from\s*" + QUOTED)
LIST = re.compile(r"export\s+(?:type\s+)?\{([^}]*)\}")
DECLARED = re.compile(
    r"(?:export\s+)?(default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(?:(?:function\s*\*?|const|let|var|class|enum|interface|type)\s+([A-Za-z_$][\w$]*))?")
DYNAMIC = re.compile(r"\b(?:import|require|importActual)\s*(?:<[^>\n]*>)?\(\s*[\"']")
CODE_STOP = re.compile(r"[/'\"`{}]")
TEMPLATE_STOP = re.compile(r"[\\`]|\$\{")
BEFORE_REGEX = set("(,=:[!&|?{};+-*%<>~^")
KEYWORDS_BEFORE_REGEX = {"return", "typeof", "case", "do", "else", "in", "of", "new",
                         "delete", "void", "throw", "yield", "await"}
CODE = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
JS_FOR_TS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}
REFUSED = run_suite.REFUSED
SCOPED = run_suite.SCOPED


def refuse(why: str) -> int:
    print(f"REFUSED: {why}\nThe scoped suite did not start.")
    return REFUSED


def sweep_filters(tree: pathlib.Path) -> list[str]:
    """The repo-wide checks: the repo's `sweepTests`, or the default. Raises
    `run_suite.ContractError` on a value it cannot use."""
    path = tree / run_suite.CONTRACT
    if not path.exists():
        return list(DEFAULT_SWEEP)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        declared = data.get("sweepTests")
    except (ValueError, AttributeError, OSError) as error:
        raise run_suite.ContractError(f"{path} does not read as a JSON object ({error})")
    if declared is None:
        return list(DEFAULT_SWEEP)
    if not isinstance(declared, list) or not declared or not all(
            isinstance(item, str) and item for item in declared):
        raise run_suite.ContractError(
            f"{path}: sweepTests is {declared!r}. It must be a list of vitest "
            f"filters, each a non-empty string.")
    return declared


def related(vitest: list[str], tree: pathlib.Path, since: str) -> list[str]:
    """Every test file whose imports reach a change since `since`, as vitest's
    module graph names them, relative to the tree. Raises on a failed list."""
    return list_files(vitest, tree, f"--changed={since}")


def list_files(vitest: list[str], tree: pathlib.Path, *flags: str) -> list[str]:
    """The test files `vitest list --filesOnly` names under `flags`, relative
    to the tree. Raises on a failed list."""
    with tempfile.TemporaryDirectory() as scratch:
        out = pathlib.Path(scratch) / "list.json"
        done = subprocess.run(
            [*vitest, "list", "--filesOnly", *flags, f"--json={out}"],
            cwd=tree, capture_output=True, text=True)
        if done.returncode != 0 or not out.exists():
            raise RuntimeError(f"`vitest list` exited {done.returncode}: "
                               f"{(done.stdout + done.stderr).strip()[-2000:]}")
        entries = json.loads(out.read_text(encoding="utf-8"))
    found = []
    for entry in entries:
        path = pathlib.Path(entry["file"])
        name = str(path.relative_to(tree)) if path.is_relative_to(tree) else str(path)
        if name not in found:
            found.append(name)
    return found


def node_builtins() -> frozenset[str]:
    """Node's built-in module names, as the installed node lists them."""
    done = subprocess.run(
        ["node", "-e", "console.log(JSON.stringify(require('module').builtinModules))"],
        capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"node could not list its built-in modules: "
                           f"{(done.stdout + done.stderr).strip()[-500:]}")
    return frozenset(json.loads(done.stdout))


def aliases(tree: pathlib.Path) -> list[tuple[str, list[pathlib.Path]]]:
    """`tsconfig.json`'s `paths`, as (prefix, target directories) for each
    `name/*` pattern. Empty when the file does not read as JSON: an aliased
    import then goes unplaced, and its test joins."""
    try:
        options = json.loads((tree / "tsconfig.json").read_text(encoding="utf-8")) \
            .get("compilerOptions") or {}
        base = tree / options.get("baseUrl", ".")
        return [(pattern[:-1], [base / target[:-1] for target in targets
                                if target.endswith("*")])
                for pattern, targets in (options.get("paths") or {}).items()
                if pattern.endswith("*")]
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def resolve(base: pathlib.Path) -> pathlib.Path | None:
    """The file an import of `base` loads, as a bundler resolves it."""
    if base.is_file():
        return base
    for js, sources in JS_FOR_TS.items():
        if base.suffix == js:
            for source in sources:
                if base.with_suffix(source).is_file():
                    return base.with_suffix(source)
    for ext in CODE:
        for candidate in (base.parent / (base.name + ext), base / ("index" + ext)):
            if candidate.is_file():
                return candidate
    return None


def blanked(text: str) -> tuple[str, str, str, bool]:
    """Three views of the text, each the same length with every newline kept,
    so one offset names the same place in all of them, and whether the scan
    ended inside a comment or a template string.

    `code` blanks the comments; a listing is read there, so `git ls-files`
    in a template string or `"fast-glob"` in a quote still counts. `bare`
    blanks template string bodies too; a top-level chunk and an import
    statement are read there, so fixture code in a template is never an
    import. `shell` blanks quote string bodies as well; the names a chunk
    uses and its `import(...)` calls are read there, so a quoted
    `'import("./x")'` is neither.

    A regular expression literal is stepped over whole, since one project's
    hold backticks; a `/` opens one where an operand is due, as
    `BEFORE_REGEX` says. A quote string ends at its line, so a misread costs
    one line at most."""
    code, bare, shell = list(text), list(text), list(text)
    spaces = re.sub(r"[^\n]", " ", text)
    state, braces = "", []
    i, n = 0, len(text)

    def blank(start: int, end: int, *views: list[str]) -> None:
        for view in views:
            view[start:end] = spaces[start:end]

    while i < n:
        if state == "`":
            stop = TEMPLATE_STOP.search(text, i)
            end = stop.start() if stop else n
            blank(i, end, bare, shell)
            if not stop:
                break
            i = end
            if text[i] == "\\":
                blank(i, i + 2, bare, shell)
                i += 2
            elif text[i] == "`":
                state = ""
                i += 1
            else:
                braces.append(0)
                state = ""
                i += 2
            continue
        if state:
            stop = re.compile(r"[\\\n" + state + "]").search(text, i)
            end = stop.start() if stop else n
            blank(i, end, shell)
            if not stop:
                break
            i = end
            if text[i] == "\\":
                blank(i, i + 2, shell)
                i += 2
            else:
                state = ""
                i += 1
            continue
        stop = CODE_STOP.search(text, i)
        if not stop:
            break
        i = stop.start()
        c = text[i]
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank(i, end, code, bare, shell)
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                blank(i, n, code, bare, shell)
                return "".join(code), "".join(bare), "".join(shell), True
            blank(i, end + 2, code, bare, shell)
            i = end + 2
        elif c == "/":
            end = regex_end(text, i, "".join(bare[max(0, i - 40):i]))
            if end:
                blank(i, end, shell)
            i = end or i + 1
        elif c in "'\"`":
            state = c
            i += 1
        elif c == "{":
            if braces:
                braces[-1] += 1
            i += 1
        else:
            if braces and braces[-1] == 0:
                braces.pop()
                state = "`"
            elif braces:
                braces[-1] -= 1
            i += 1
    return "".join(code), "".join(bare), "".join(shell), state == "`" or bool(braces)


def regex_end(text: str, i: int, before: str) -> int | None:
    """Where the regular expression literal opening at `text[i]` ends, or
    None when the `/` there divides. `before` is the code ahead of it."""
    ahead = before.rstrip()
    word = re.search(r"[\w$]+$", ahead)
    if ahead and ahead[-1] not in BEFORE_REGEX and not (
            word and word.group(0) in KEYWORDS_BEFORE_REGEX):
        return None
    in_class, j = False, i + 1
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return None
        if in_class:
            in_class = c != "]"
        elif c == "[":
            in_class = True
        elif c == "/":
            j += 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            return j
        j += 1
    return None


def names_in(clause: str) -> list[tuple[str, str]]:
    """(name, local) for each entry of an `{ a, b as c, type d }` list."""
    pairs = []
    for item in clause.split(","):
        words = item.split()
        if words and words[0] == "type":
            words = words[1:]
        if len(words) == 3 and words[1] == "as":
            pairs.append((words[0], words[2]))
        elif len(words) == 1:
            pairs.append((words[0], words[0]))
    return pairs


Span = tuple[int, int]


class Module:
    """One file's top level: what it imports, what it declares and what it
    exports from elsewhere, each declaration kept as the span of text that
    makes it. Every import is a specifier, not yet placed."""

    def __init__(self, text: str):
        self.code, self.bare, self.shell, self.unsure = blanked(text)
        self.whole: Span = (0, len(text))
        self.bindings: dict[str, tuple[str, str]] = {}          # local -> (spec, name)
        self.side: list[str] = []                               # `import "x"`
        self.stars: list[str] = []                              # `export * from "x"`
        self.reexports: dict[str, tuple[str, str, Span]] = {}   # name -> (spec, name, span)
        self.local: dict[str, str] = {}                         # exported -> local
        self.segments: dict[str, Span] = {}                     # declared name -> span
        self.loose: list[Span] = []                             # every other statement
        cuts = [m.start() for m in CHUNK.finditer(self.bare)] + [len(text)]
        for span in zip(cuts, cuts[1:]):
            chunk = self.bare[slice(*span)]
            if chunk.startswith("import") and not chunk.startswith("import("):
                if found := IMPORT.match(chunk):
                    clause, spec = found.groups()
                    if default := re.match(r"([A-Za-z_$][\w$]*)\s*(?:,|$)", clause):
                        self.bindings[default.group(1)] = (spec, "default")
                    if space := re.search(r"\*\s*as\s+([\w$]+)", clause):
                        self.bindings[space.group(1)] = (spec, "*")
                    if named := re.search(r"\{([^}]*)\}", clause):
                        for name, local in names_in(named.group(1)):
                            self.bindings[local] = (spec, name)
                elif found := BARE_IMPORT.match(chunk):
                    self.side.append(found.group(1))
                else:
                    self.loose.append(span)
            elif found := STAR_FROM.match(chunk):
                if found.group(1):
                    self.reexports[found.group(1)] = (found.group(2), "*", span)
                else:
                    self.stars.append(found.group(2))
            elif found := LIST_FROM.match(chunk):
                for name, exported in names_in(found.group(1)):
                    self.reexports[exported] = (found.group(2), name, span)
            elif found := LIST.match(chunk):
                for name, exported in names_in(found.group(1)):
                    self.local[exported] = name
            else:
                found = DECLARED.match(chunk)
                if found.group(2):
                    self.segments[found.group(2)] = span
                if found.group(1):
                    self.segments["default"] = span
                if not (found.group(1) or found.group(2)):
                    self.loose.append(span)
        known = [*self.segments, *self.bindings]
        self.refers = re.compile(
            r"(?<![\w$.])(" + "|".join(map(re.escape, known)) + r")(?![\w$])"
        ) if known else None
        self.scans: dict[tuple[Span, ...], tuple[bool, set[str], list[str]]] = {}

    def scan(self, spans: tuple[Span, ...]) -> tuple[bool, set[str], list[str]]:
        """Whether these spans list a directory, the names they use and the
        files they import by call, read once per set of spans."""
        if spans not in self.scans:
            code, bare, shell = ("".join(view[a:b] for a, b in spans)
                                 for view in (self.code, self.bare, self.shell))
            called = [re.match(r"""([^"'\s]+)["']""", bare[m.end():])
                      for m in DYNAMIC.finditer(shell)]
            self.scans[spans] = (
                bool(LISTING.search(code)),
                set(self.refers.findall(shell)) if self.refers else set(),
                [m.group(1) for m in called if m])
        return self.scans[spans]


def tree_readers(tree: pathlib.Path, tests: list[str], builtins: frozenset[str]
                 ) -> tuple[list[str], dict[str, str]]:
    """The tests that list a directory, and why each unplaced one joined.

    The walk runs over names, not files: a test reads the tree when its own
    text matches `LISTING`, or when a name it imports is declared by text that
    does, through the names that text uses in turn. Importing `REPO` from a
    module whose `sourceFiles` lists is not listing. A test also joins when a
    name it reaches comes through an import the walk cannot place."""
    alias = aliases(tree)
    modules: dict[pathlib.Path, Module] = {}

    places: dict[tuple[str, pathlib.Path], pathlib.Path | str | None] = {}

    def place(spec: str, importer: pathlib.Path) -> pathlib.Path | str | None:
        if (spec, importer) not in places:
            places[spec, importer] = find(spec, importer)
        return places[spec, importer]

    def find(spec: str, importer: pathlib.Path) -> pathlib.Path | str | None:
        """The repository file `spec` loads, None for a package or built-in,
        or a string saying why it cannot be placed."""
        spec = spec.split("?", 1)[0]
        if spec.startswith((".", "/")):
            found = resolve((importer.parent / spec) if spec.startswith(".")
                            else pathlib.Path(spec))
            return found.resolve() if found else \
                f"{spec} in {importer.relative_to(tree)} is not a file"
        for prefix, targets in alias:
            if spec.startswith(prefix):
                for target in targets:
                    found = resolve(target / spec[len(prefix):])
                    if found:
                        return found.resolve()
                return f"{spec} in {importer.relative_to(tree)} matches no file its alias names"
        if spec.startswith("node:"):
            return None
        parts = spec.split("/")
        package = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
        if package in builtins or (tree / "node_modules" / package).exists():
            return None
        return f"{spec} in {importer.relative_to(tree)} is neither a package nor a file"

    def module(path: pathlib.Path) -> Module:
        if path not in modules:
            readable = path.suffix in CODE and path.is_relative_to(tree) \
                and "node_modules" not in path.parts
            modules[path] = Module(path.read_text(encoding="utf-8", errors="replace")
                                   if readable else "")
        return modules[path]

    # Every name the tests reach, as (file, name); "*" is the whole file, as a
    # test, a side-effect import or a namespace import uses it. Each node has
    # the text that declares it, the nodes that text uses, and a mark when it
    # lists ("") or reaches an import it cannot place (the reason).
    edges: dict[tuple[pathlib.Path, str], list[tuple[pathlib.Path, str]]] = {}
    marks: dict[tuple[pathlib.Path, str], str] = {}
    starts = [((tree / name).resolve(), "*") for name in tests]
    pending = list(starts)
    while pending:
        node = pending.pop()
        if node in edges:
            continue
        path, name = node
        mod = module(path)
        name = mod.local.get(name, name)
        uses: list[tuple[str, str]] = []
        if name in mod.segments:
            scans = [mod.scan((mod.segments[name],)), mod.scan(tuple(mod.loose))]
            uses += [(spec, "*") for spec in mod.side]
        elif name in mod.reexports:
            spec, target, span = mod.reexports[name]
            scans = [mod.scan((span,))]
            uses.append((spec, target))
        elif name in mod.bindings:
            scans = []
            uses.append(mod.bindings[name])
        elif name != "*" and mod.stars:
            scans = []
            uses += [(spec, name) for spec in mod.stars]
        else:
            # The whole file: a test, a side-effect or namespace import, or a
            # name the walk cannot find, which is read as the whole file.
            scans = [mod.scan((mod.whole,))]
            uses += list(mod.bindings.values())
            uses += [(spec, "*") for spec in (*mod.side, *mod.stars)]
            uses += [(spec, target) for spec, target, _ in mod.reexports.values()]
        for _, names, dynamic in scans:
            for used in names:
                if used in mod.bindings:
                    uses.append(mod.bindings[used])
                elif used != name:
                    uses.append((".", used))
            uses += [(spec, "*") for spec in dynamic]
        edges[node] = []
        if any(lists for lists, _, _ in scans):
            marks[node] = ""
        elif mod.unsure:
            marks[node] = (f"{path.relative_to(tree)} ends inside a comment or a "
                           f"template string, so the walk cannot read it")
        for spec, target in uses:
            placed = path if spec == "." else place(spec, path)
            if isinstance(placed, str):
                marks.setdefault(node, placed)
            elif placed is not None:
                edges[node].append((placed, target))
                pending.append((placed, target))

    # A node reads the tree when a marked node is reachable from it: walk the
    # uses backwards from every mark, carrying its reason. Listing marks go
    # first, so a test that reaches one is not reported as joining on an
    # unplaced import.
    users: dict[tuple[pathlib.Path, str], list[tuple[pathlib.Path, str]]] = {}
    for node, targets in edges.items():
        for target in targets:
            users.setdefault(target, []).append(node)
    reached: dict[tuple[pathlib.Path, str], str] = {}
    for group in ([n for n, why in marks.items() if not why],
                  [n for n, why in marks.items() if why]):
        pending = [node for node in group if node not in reached]
        reached.update((node, marks[node]) for node in pending)
        while pending:
            node = pending.pop()
            for user in users.get(node, []):
                if user not in reached:
                    reached[user] = reached[node]
                    pending.append(user)

    joined, unplaced = [], {}
    for name, node in zip(tests, starts):
        if node in reached:
            joined.append(name)
            if reached[node]:
                unplaced[name] = reached[node]
    return joined, unplaced


def light_commit_refusal(tree: pathlib.Path, level: str) -> str | None:
    """Why the runner may not commit a light issue's tree yet, or None.

    The perf audit of 2026-09-28, fix 4: three light-issue reds reached the
    finale because nothing read more than the touched files before the
    commit. The newest `scoped` record for the tree being committed decides:
    green passes, red or none refuses. A full issue is not judged here; its
    implementer's whole suite and the verify gate read its tree. Nor is a
    tree with no vitest installed: the scoped road is vitest's, and the skills
    repository runs light issues on Python suites."""
    if level != "light" or not (tree / "node_modules" / ".bin" / "vitest").exists():
        return None
    tree_id = run_suite.tree_hash(tree)
    for record in reversed(run_suite.read_records(run_suite.store_of(tree))):
        if record.get("stage") != STAGE or tree_id not in (
                record.get("tree"), record.get("tree_after")):
            continue
        if record.get("exit") == 0:
            return None
        return (f"the newest scoped reading of tree {tree_id}, at "
                f"{record.get('started')}, exited {record.get('exit')}. Failing "
                f"files: {', '.join(record.get('failing') or []) or 'none named'}. "
                f"Whole output: {record.get('log')}. Fix the red, then run "
                f"`{SCOPED}` again.")
    return (f"no scoped reading exists for tree {tree_id}, the tree this commit "
            f"stages. A light issue commits only on a green one, which runs every "
            f"test whose imports reach the change, every test that lists a "
            f"directory, and the repo-wide checks:\n"
            f"  {SCOPED}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="HEAD",
                        help="The ref the change is measured from. HEAD: the uncommitted work.")
    parser.add_argument("--vitest", default="npx vitest",
                        help="How vitest is launched in this tree.")
    args = parser.parse_args(argv)
    vitest = shlex.split(args.vitest)

    _, queue = run_suite.take_lock()
    try:
        tree, tree_id, store = run_suite.locate(os.getcwd())
    except (subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        return refuse(f"git could not read {os.getcwd()} ({detail.strip()}).")
    tree = tree.resolve()
    (store / "logs").mkdir(parents=True, exist_ok=True)
    try:
        contract = run_suite.harness_contract(tree)
        sweep = sweep_filters(tree)
    except run_suite.ContractError as error:
        return refuse(str(error))

    earlier = run_suite.green_before(run_suite.read_records(store), tree_id, STAGE)
    if earlier:
        return refuse(f"tree {tree_id} already ran green at stage {STAGE}, at "
                      f"{earlier.get('started')}. Read that log: {earlier.get('log')}")
    try:
        files = related(vitest, tree, args.since)
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        return refuse(f"vitest could not name the tests the change reaches. {error}")
    try:
        every = list_files(vitest, tree)
        readers, unplaced = tree_readers(tree, every, node_builtins())
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        return refuse(f"the tests that list a directory could not be named. {error}")
    readers = [name for name in readers if name not in files
               and not any(check in name for check in sweep)]

    started = run_suite.now()
    stem = f"{started:%Y%m%dT%H%M%S.%fZ}-{STAGE}-{tree_id[:12]}"
    log = store / "logs" / f"{stem}.log"
    kept = store / "coverage" / stem
    command, reports = run_suite.with_coverage(
        [*vitest, "run", *(str(tree / name) for name in files + readers), *sweep,
         "--passWithNoTests"], kept)
    suite_exit, text = run_suite.run_logged(command, log)
    report = run_suite.keep_report(reports, started, kept)
    harness = run_suite.run_harness(STAGE, tree, contract,
                                    store / "logs" / f"{stem}-harness.log")
    ended = run_suite.now()
    tree_after = run_suite.after_hash(tree)
    failing = run_suite.failing_files(text)
    failing += [name for name in harness.get("failing", []) if name not in failing]
    exit_code = suite_exit or harness.get("exit", 0)

    record = {"tree": tree_id, "tree_after": tree_after, "stage": STAGE,
              "exit": exit_code,
              "suite_exit": suite_exit, "harness": harness, "command": command,
              "files": files, "tree_readers": readers, "unplaced": unplaced,
              "sweep": sweep, "since": args.since,
              "asked": queue.asked.isoformat(), "waited": queue.waited,
              "lock": queue.lock, "lock_holder": queue.holder,
              "started": started.isoformat(),
              "seconds": round((ended - started).total_seconds(), 1),
              "log": str(log), "failing": failing,
              "coverage": str(report) if report else None,
              "report_root": str(tree) if report else None}
    with open(store / run_suite.RECORDS, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    print(f"scoped suite exit {suite_exit}, tree {tree_id}: {len(files)} files "
          f"whose imports reach the change since {args.since}, {len(readers)} "
          f"more that list a directory, and the checks {', '.join(sweep)}")
    for name, why in unplaced.items():
        if name in readers:
            print(f"  joined, an import it cannot place: {name}: {why}")
    print(run_suite.queue_line(queue))
    for line in run_suite.summary_lines(text):
        print(f"  {line}")
    if failing:
        print("failing files:")
        for name in failing:
            print(f"  {name}")
    print(f"whole output: {log}")
    print(run_suite.harness_line(harness))
    if report:
        print(f"Coverage report: {report}\nReport root:     {tree}")
    else:
        print("no coverage report: the run wrote none.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
