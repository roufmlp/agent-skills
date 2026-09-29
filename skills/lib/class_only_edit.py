#!/usr/bin/env python3
"""Decide whether a change to a file only edits styling class names.

## The rule

The light level lifts an issue to the full level when its diff touches a risk
file: sign-in, sessions, secrets, money, `src/model/`, migrations. The human
ruled on 2026-09-25 (queue item q-971a22-03, run batch-971a22) that the lift
must NOT fire when the change to such a file only edits styling
class names -- and that an agent may not judge "class-only and safe". A
script decides, and it refuses a class edit that can hide, show, block or
cover something. This is that script.

## The fault that paid for this

Issue 230 removed one class, `focus:border-primary`, from the email input of
one project's `src/app/login/page.tsx` (commit 7ae2d84). The sign-in page is a
risk file, so the whole issue ran at the full level: 105 minutes, with the
critical review gate, for a focus-ring colour.

## How it decides

A masking comparison, not a parser. In both versions of a file the CONTENTS
of every class string are cut out. If the two masked texts are byte-identical,
the change touched nothing but class strings. Anything else that differs --
an attribute, a handler, text, whitespace, a comment -- is behaviour.

Class strings are:

    className="..."   className='...'
    className={"..."} className={'...'} className={`...`}  (no `${` inside)
    class="..."       class='...'
    a plain string-literal argument of cn(...), clsx(...), twMerge(...)

Only .tsx, .jsx and .html files are judged; a changed file of any other
kind is behaviour. A quoted attribute string ends on its own line. A bound
attribute (`:class`, `v-bind:class`, `data-class`), a CSS attribute selector
(`[class="btn"]`) and a declared variable (`let className="x"`) are not class
strings. A helper is read as one only where the file imports it under its
own name and uses it only as a call: an alias, a local definition or a
parameter of the same name makes it code.
A helper argument that is not one plain literal (`open && "b"`, `"a" + b`) is
not masked.

A class string is masked only when it is written in the characters a class
list uses (letters, digits, `_ - : / . [ ] % # ! , @ ( ) =`, whitespace). A
`${}` template, a quote, `+`, `{`, `;`, `&` or `*` means the pattern caught
code, JSX text holding an expression, a comment or an HTML entity, so that string is compared byte
for byte, and a change inside it is behaviour and says so.

Then every class string that changed is split into tokens, and each token
added or removed must be on the ALLOWLIST below (road B, ruled by the human on
2026-09-25): colour, spacing, typography, borders and corners, focus and
rings, and effects, as Tailwind utility names. The variant (everything up to
the last `:` outside square brackets, `hover:` or `md:`) is stripped first,
and the token keeps its judgement under it. Every other token is behaviour,
and the reason names it and says whether it was added or removed: a class the
list does not name (`hidden`, `peer`, `order-first`, `text-transparent`), a
negative value (`-mt-4`), an arbitrary value in square brackets or
parentheses (`-left-[9999px]`, `opacity-(--x)`), a bracketed variant
(`data-[state=open]:`) and the important mark `!`. The list is the human's to
widen. A safe class it does not name costs one full-level run, never a wrong
pass.

A changed class string that holds a token off the list is behaviour too when
the change adds or removes a token of the same utility (`text-ink` beside
`text-transparent`, `mt-2` beside `-mt-4`; an arbitrary property such as
`[color:transparent]` shares a utility with every token), or when the
tokens both versions hold change order, whatever else changed beside them:
the later class can win a conflict. An unsafe token that the change does
not touch was there before, and is not judged.

## It fails toward the full level, on purpose

The hooks in `~/.claude/hooks` fail OPEN: a hook that cannot read its input
lets the work through. This script is the opposite. A wrong "class-only"
skips the critical gates on a sign-in or money file, and a wrong "behaviour"
costs one full-level run. So everything it cannot place is behaviour, with
the reason stated: a file added or deleted, a binary or non-UTF-8 file, a
symbolic link, a path outside the repository, a changed file that is not
.tsx, .jsx or .html, a class string it cannot read that changed, a helper
call it cannot scan to its end (a comment or a `/` between its arguments
included), and any shape it does not name above.

What it still cannot see, said plainly: an allowlisted colour can match
the colour behind it (`text-card` on a card, `text-white` on white) and hide
text, and nothing here knows the background. An opacity suffix below `/10`
and `truncate` (which sets `overflow: hidden`) are NOT on the list, on
the human's ruling of 2026-09-25. JSX text that looks like a class
attribute and holds no braces (`<p>class="12"</p>`) still masks, because the
masking reads no JSX structure.

An unchanged file is class-only: it changed nothing, classes included. The
caller names the files; this script judges only those.

## Usage and exit codes

    python3 lib/class_only_edit.py --repo <path> --base <commit> \\
        [--head <commit>] -- <path> [<path> ...]

Each named file is compared at --base against --head, or against the
working tree when --head is absent. One line is printed per file:

    <path>: class-only
    <path>: behaviour — <reason>

    0  every named file is class-only and safe
    1  at least one file is behaviour
    2  usage error: bad arguments, --repo not the top of a git repository,
       or --base/--head not a commit. Nothing was read, so nothing is
       asserted.
"""

import argparse
import os
import re
import subprocess
import sys

# The attribute forms. Each alternative captures the CONTENTS of one literal.
# A quoted literal ends on its own line: were it allowed to run on, one stray
# quote in a comment would mask every line of code up to the next quote. A
# backslash in a braced literal leaves it unmatched too. Either way the text
# is compared byte for byte instead of masked, which fails toward the full
# level.
# The name must not follow a word character, `:`, `.`, `@`, `$`, `-` or `[`,
# so a bound attribute (`:class`, `v-bind:class`, `data-class`) or a CSS
# attribute selector (`[class="btn"]`) is not read as one. Nor may it follow
# `let `, `const ` or `var `: `let className="user"` is a variable.
NOT_BOUND = r"(?<![\w:.@$\[-])(?<!let )(?<!const )(?<!var )"
CLASS_ATTRIBUTE = re.compile(
    NOT_BOUND + r"""className=(?:"([^"\n]*)"|'([^'\n]*)'"""
    r"""|\{\s*(?:"([^"\\\n]*)"|'([^'\\\n]*)'|`([^`\\]*)`)\s*\})"""
    r"""|""" + NOT_BOUND + r"""class=(?:"([^"\n]*)"|'([^'\n]*)')""")
TEMPLATE_GROUP = 5
# The characters a class list is written in, Tailwind arbitrary values and
# `data-[state=open]:` variants included. A class string holding anything
# else -- a quote, `+`, `$`, `{`, `;`, `&`, `*`, `<` -- is code, JSX text, a
# comment or an HTML entity caught by the pattern, and is compared byte for
# byte instead of masked. `&` refuses `[&>svg]:` variants too; that costs a
# full-level run, never a skipped gate.
CLASS_TEXT = re.compile(r"[A-Za-z0-9_\-:/.\[\]%#!,@()=\s]*")
# The class helpers. A name is read as one only where the file imports it and
# does not define it, so a local `cn` that formats a currency is code. A name
# ending in one of these (`scn(`) or reached through a member (`utils.cn(`) is
# never matched, so its edits count as behaviour.
HELPERS = ("cn", "clsx", "twMerge")
QUOTES = "\"'`"
OPENERS, CLOSERS = "([{", ")]}"


class Unreadable(Exception):
    """A shape this script cannot place. The caller reports it as behaviour."""


# THE ALLOWLIST: the class tokens known to be safe, as Tailwind utility
# names. A token is judged after its variant (`hover:`, `md:`, `dark:`,
# `aria-invalid:`) is stripped, and the whole base must match one family
# below. Everything else is behaviour. The list is the human's to widen: a safe
# class missing from it costs one full-level run, never a wrong pass.

# The Tailwind palette, one project's own colour tokens (its `@theme` in
# `src/styles/tokens.css`, read 2026-09-25), and the shadcn token names
# (`muted-foreground`), which the human named in the ruling. A reader's
# project puts its own `@theme` names in place of that project's.
# `transparent` is NOT here: `text-transparent` hides text. Nor is `current` for a background or
# gradient: `bg-current` paints the background the colour of the text.
PALETTE_NAMES = ("slate", "gray", "zinc", "neutral", "stone", "red", "orange",
                 "amber", "yellow", "lime", "green", "emerald", "teal",
                 "cyan", "sky", "blue", "indigo", "violet", "purple",
                 "fuchsia", "pink", "rose")
SHADES = ("50", "100", "200", "300", "400", "500", "600", "700", "800",
          "900", "950")
PROJECT_COLOURS = (
    # one project's `@theme` tokens
    "primary", "primary-soft", "ground", "card", "ink", "ink-2", "ink-3",
    "line", "amber-soft", "green-soft", "red-soft",
    # shadcn
    "background", "foreground", "muted", "muted-foreground",
    "primary-foreground", "secondary", "secondary-foreground", "accent",
    "accent-foreground", "destructive", "destructive-foreground",
    "card-foreground", "popover", "popover-foreground", "border", "input",
    "ring")


def alternatives(words):
    return "(?:" + "|".join(re.escape(w) for w in words) + ")"


COLOUR_VALUE = ("(?:" + alternatives(PALETTE_NAMES) + "(?:-" + alternatives(SHADES)
                + ")?|" + alternatives(("white", "black", "inherit")
                                       + PROJECT_COLOURS) + ")")
# An opacity suffix from /10 to /100. `/0` makes the colour invisible and
# `/1` to `/9` almost so; the human ruled both out on 2026-09-25.
OPACITY = r"(?:/(?:100|[1-9][0-9]))?"
FOREGROUNDS = ("text", "border", "ring", "outline", "decoration", "fill",
               "stroke", "placeholder", "caret", "accent", "divide")
BACKGROUNDS = ("bg", "from", "via", "to")
COLOUR = ("(?:" + alternatives(FOREGROUNDS) + "-(?:" + COLOUR_VALUE
          + "|current)|" + alternatives(BACKGROUNDS) + "-" + COLOUR_VALUE + ")"
          + OPACITY)

# Spacing: padding, margin, gap and space-between on the default Tailwind 3
# scale. No negative values (`-mt-4` can move a control off screen), and no
# value past 96, since Tailwind 4 accepts any number and `ml-9999` would.
SPACING_SCALE = alternatives(("0", "px", "0.5", "1", "1.5", "2", "2.5", "3",
                              "3.5", "4", "5", "6", "7", "8", "9", "10", "11",
                              "12", "14", "16", "20", "24", "28", "32", "36",
                              "40", "44", "48", "52", "56", "60", "64", "72",
                              "80", "96"))
SPACING = (alternatives(("p", "px", "py", "pt", "pr", "pb", "pl", "ps", "pe",
                         "m", "mx", "my", "mt", "mr", "mb", "ml", "ms", "me",
                         "gap", "gap-x", "gap-y", "space-x", "space-y"))
           + "-" + SPACING_SCALE)

# Typography: size, weight, family, line height, letter spacing, style,
# decoration, case, alignment, truncation, wrapping.
TYPOGRAPHY = "|".join((
    r"text-(?:xs|sm|base|lg|xl|[2-9]xl)",
    r"font-(?:thin|extralight|light|normal|medium|semibold|bold|extrabold"
    r"|black|sans|serif|mono)",
    r"leading-(?:none|tight|snug|normal|relaxed|loose|[3-9]|10)",
    r"tracking-(?:tighter|tight|normal|wide|wider|widest)",
    r"italic|not-italic|underline|no-underline|line-through",
    r"uppercase|lowercase|capitalize|normal-case",
    r"text-(?:left|center|right|start|end)",
    r"whitespace-(?:normal|nowrap|pre|pre-line|pre-wrap|break-spaces)",
    r"break-(?:normal|words|all|keep)"))

# Borders and corners: width on every side, style, and every radius.
BORDERS = "|".join((
    r"border(?:-[trblxyse])?(?:-(?:0|2|4|8))?",
    r"border-(?:solid|dashed|dotted|none)",
    r"rounded(?:-[a-z0-9]+){0,2}"))

# Focus and rings: ring width, ring offset, outline width, style and offset.
FOCUS = "|".join((
    r"ring(?:-(?:0|1|2|4|8))?",
    r"ring-inset",
    r"ring-offset-(?:0|1|2|4|8)",
    r"outline(?:-(?:none|0|1|2|4|8|dashed|dotted))?",
    r"outline-offset-(?:0|1|2|4|8)"))

# Effects: shadow, transition, duration, easing, delay. Duration and delay
# on the default Tailwind scale only: Tailwind 4 accepts any number, and
# `delay-999999` keeps a fading control invisible for 17 minutes.
TIMING = alternatives(("0", "75", "100", "150", "200", "300", "500", "700",
                       "1000"))
EFFECTS = "|".join((
    r"shadow(?:-[a-z0-9]+)*" + OPACITY,
    r"transition(?:-[a-z]+)?",
    r"duration-" + TIMING,
    r"ease-(?:linear|in|out|in-out)",
    r"delay-" + TIMING))

SAFE = re.compile("|".join((COLOUR, SPACING, TYPOGRAPHY, BORDERS, FOCUS,
                            EFFECTS)))


TEMPLATE_WHY = "a class template holding ${}, whose classes cannot be read"
TEXT_WHY = ("a class string holding characters a class list does not use, "
            "so this script cannot read it")


def opaque_reason(body, is_template):
    """Why a class string is compared byte for byte, or "" when it is masked."""
    if is_template and "${" in body:
        return TEMPLATE_WHY
    if not CLASS_TEXT.fullmatch(body):
        return TEXT_WHY
    return ""


def attribute_strings(text):
    """Masked spans, and opaque (start, end, why) spans, of the attributes."""
    spans, opaque = [], []
    for match in CLASS_ATTRIBUTE.finditer(text):
        group = next(g for g in range(1, 8) if match.group(g) is not None)
        why = opaque_reason(match.group(group), group == TEMPLATE_GROUP)
        if why:
            opaque.append((*match.span(group), why))
        else:
            spans.append(match.span(group))
    return spans, opaque


IMPORT_STATEMENT = re.compile(r"^\s*import\b[^;]*?\bfrom\s*[\"'][^\"']*[\"']",
                              re.MULTILINE)


def helper_names(text):
    """The helper names this file imports under their own name and uses only
    as calls.

    Every other use refuses the name: an alias (`formatCents as cn`), a local
    definition, a parameter (`(cn) => cn("USD")`), a bare reference. The name
    is then code, and a change to its arguments is behaviour.
    """
    imports = IMPORT_STATEMENT.findall(text)
    rest = IMPORT_STATEMENT.sub("", text)
    names = []
    for name in HELPERS:
        bare = rf"(?<![\w$.]){name}\b"
        imported = any(re.search(bare + r"(?!\s+as\b)", statement)
                       and not re.search(rf"\bas\s+{name}\b", statement)
                       for statement in imports)
        defined = re.search(
            rf"\b(?:function|const|let|var|class)\s+{name}\b", rest)
        other_use = re.search(bare + r"(?!\s*\()", rest)
        if imported and not defined and not other_use:
            names.append(name)
    return names


def read_literal(text, index):
    """The end offset (after the closing quote) of the literal at INDEX."""
    quote = text[index]
    cursor = index + 1
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == quote:
            return cursor + 1
        if char == "\n" and quote != "`":
            break
        cursor += 1
    raise Unreadable(f"an unclosed string at line {line_of(text, index)}")


def helper_arguments(text, open_paren, opaque):
    """The spans of the plain string-literal arguments of one helper call.

    A small scanner, not a parser: it tracks brackets and skips strings to
    find the top-level commas. A comment or a slash between the arguments
    is refused rather than guessed at, because a scanner that loses its place
    could mask code as if it were a class string.
    """
    line = line_of(text, open_paren)
    depth, cursor, start = 0, open_paren + 1, open_paren + 1
    spans = []

    def close_argument(end):
        argument = text[start:end]
        stripped = argument.strip()
        if (len(stripped) >= 2 and stripped[0] in QUOTES
                and stripped[-1] == stripped[0]):
            offset = start + argument.index(stripped[0])
            try:
                closes = read_literal(text, offset)
            except Unreadable:
                return
            if closes != offset + len(stripped):
                return
            body = stripped[1:-1]
            span = (offset + 1, offset + len(stripped) - 1)
            why = opaque_reason(body, stripped[0] == "`")
            if "\\" in body:
                why = TEXT_WHY
            if why:
                opaque.append((*span, why))
            else:
                spans.append(span)

    while cursor < len(text):
        char = text[cursor]
        if char in QUOTES:
            cursor = read_literal(text, cursor)
            continue
        if char == "/":
            raise Unreadable(f"a comment or slash inside the class helper "
                             f"call at line {line}")
        if char in OPENERS:
            depth += 1
        elif char in CLOSERS:
            if depth == 0:
                if char != ")":
                    break
                close_argument(cursor)
                return spans
            depth -= 1
        elif char == "," and depth == 0:
            close_argument(cursor)
            start = cursor + 1
        cursor += 1
    raise Unreadable(f"the class helper call at line {line} has no end this "
                     f"script can find")


def class_strings(text):
    """The contents spans of every class string, and the opaque ones.

    Raises Unreadable for a helper call it cannot scan.
    """
    spans, opaque = attribute_strings(text)
    names = helper_names(text)
    if names:
        call = re.compile(r"(?<![\w$.])(?:" + "|".join(names) + r")\(")
        for match in call.finditer(text):
            spans.extend(helper_arguments(text, match.end() - 1, opaque))
    kept, reach = [], -1
    for start, end in sorted(spans):
        if start >= reach:
            kept.append((start, end))
            reach = end
    return kept, opaque


def mask(text, spans):
    parts, cursor = [], 0
    for start, end in spans:
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def split_token(token):
    """(variant, base) of a class token.

    Everything up to the last colon OUTSIDE square brackets is the variant,
    so `md:[display:none]` splits as (`md:`, `[display:none]`).
    """
    depth, cut = 0, 0
    for index, char in enumerate(token):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == ":" and depth == 0:
            cut = index + 1
    return token[:cut], token[cut:]


def unsafe_reason(token):
    """Why a class token is not known to be safe, or "" when it is.

    The variant is stripped and the base judged against SAFE. A token the
    allowlist does not name is refused: this is a guard that refuses what it
    cannot place, not a list of what it forbids.
    """
    variant, base = split_token(token)
    if base.startswith("!") or base.endswith("!"):
        return "which carries the important mark `!`"
    if "[" in variant or "(" in variant:
        return "which has an arbitrary variant in brackets"
    if "[" in base or "(" in base:
        return "which holds an arbitrary value in brackets or parentheses"
    if not SAFE.fullmatch(base):
        return "which is not on the allowlist"
    return ""


def family(token):
    """The utility a token sets, its first word: `text` for `hover:text-sm`
    and for `text-transparent`. A side of a margin or padding joins its whole
    (`mt` and `mx` are `m`), since `m-2` overrides `-mt-4`. None for an
    arbitrary property, which can set any CSS and so shares a family with
    every token."""
    base = split_token(token)[1].strip("!").lstrip("-")
    if base.startswith("["):
        return None
    word = base.split("-")[0].split("/")[0]
    if re.fullmatch(r"[mp][xytrblse]", word):
        return word[0]
    return word


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def first_difference(before, after, before_spans, after_spans):
    """The 1-based line in AFTER where the masked texts part, its text, and
    the offset in AFTER."""
    masked_before = mask(before, before_spans)
    masked_after = mask(after, after_spans)
    index = next((i for i, (a, b) in enumerate(zip(masked_before, masked_after))
                  if a != b), min(len(masked_before), len(masked_after)))
    # Map the masked offset back onto the unmasked text.
    shift = 0
    for start, end in after_spans:
        if start - shift > index:
            break
        shift += end - start
    offset = min(index + shift, len(after))
    line = line_of(after, offset)
    lines = after.splitlines()
    shown = lines[line - 1].strip()[:100] if line - 1 < len(lines) else ""
    return line, shown, offset


def unsafe_change(before, after, before_spans, after_spans):
    """The first reason a changed class string is unsafe, or "".

    In order: a token added that the allowlist does not name, one removed,
    an allowlisted token added or removed in the family of an unsafe token
    still held (`text-red-500` beside `text-transparent`), and a change in the
    order of the tokens both versions hold, in a string holding an unsafe
    token, whatever else changed beside it.
    """
    for (b_start, b_end), (a_start, a_end) in zip(before_spans, after_spans):
        old = before[b_start:b_end].split()
        new = after[a_start:a_end].split()
        if old == new:
            continue
        added = [t for t in new if t not in old]
        removed = [t for t in old if t not in new]
        for token in added:
            why = unsafe_reason(token)
            if why:
                return (f"class `{token}` added at line "
                        f"{line_of(after, a_start)}, {why}")
        for token in removed:
            why = unsafe_reason(token)
            if why:
                return (f"class `{token}` removed at line "
                        f"{line_of(before, b_start)} of the base, {why}")
        held = [t for t in old + new if unsafe_reason(t)]
        changed = added + removed
        for token in held:
            held_family = family(token)
            clash = [c for c in changed
                     if held_family is None or family(c) == held_family]
            if clash:
                return (f"a class string holding `{token}` changes "
                        f"`{clash[0]}`, which overrides it, at line "
                        f"{line_of(after, a_start)}")
        kept_old = [t for t in old if t in new]
        kept_new = [t for t in new if t in old]
        if kept_old != kept_new and held:
            return (f"the order of a class string holding `{held[0]}` "
                    f"changed at line {line_of(after, a_start)}; the last "
                    f"class can win a conflict")
    return ""


def classify(before, after):
    try:
        before_spans, _ = class_strings(before)
        after_spans, opaque = class_strings(after)
    except Unreadable as refusal:
        return False, f"cannot read {refusal}"
    if mask(before, before_spans) != mask(after, after_spans):
        line, text, offset = first_difference(before, after, before_spans,
                                              after_spans)
        for start, end, why in opaque:
            if start <= offset <= end:
                return False, f"line {line} changes {why}: {text}"
        return False, f"line {line} differs outside a class string: {text}"
    if len(before_spans) != len(after_spans):
        return False, "the class strings of the two versions do not pair up"
    reason = unsafe_change(before, after, before_spans, after_spans)
    if reason:
        return False, reason
    return True, ""


# ---------------------------------------------------------------- reading

REGULAR_FILE_MODES = ("100644", "100755")
# Only markup is judged. In a migration or a plain script, `class='free'` is
# data, and a class-shaped string is far likelier to be code.
MARKUP_EXTENSIONS = (".tsx", ".jsx", ".html")


class Usage(Exception):
    """A bad invocation. Nothing was read, so nothing is asserted."""


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True)


def resolve_commit(repo, rev, flag):
    # The `^{commit}` suffix keeps an option-shaped value (`--all`,
    # `--git-dir`) a revision that fails to resolve, never an option.
    done = git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if done.returncode != 0:
        raise Usage(f"{flag} {rev} is not a commit in {repo}")
    return done.stdout.decode().strip()


def check_repo(repo):
    done = git(repo, "rev-parse", "--show-toplevel")
    if done.returncode != 0:
        raise Usage(f"--repo {repo} is not a git repository")
    top = done.stdout.decode().strip()
    if os.path.realpath(top) != os.path.realpath(repo):
        raise Usage(f"--repo {repo} is inside a repository whose top is "
                    f"{top}; name the top, so the paths mean one thing")


def relative_path(repo, path):
    """The path relative to the repository top, or None when it leaves it."""
    full = path if os.path.isabs(path) else os.path.join(repo, path)
    rel = os.path.relpath(os.path.realpath(os.path.dirname(full)),
                          os.path.realpath(repo))
    rel = os.path.normpath(os.path.join(rel, os.path.basename(full)))
    if rel == ".." or rel.startswith(".." + os.sep) or os.path.isabs(rel):
        return None
    return rel


def decode(data, where):
    if b"\0" in data:
        raise Unreadable(f"the file at {where} is not text")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Unreadable(f"the file at {where} is not text (not UTF-8)")


def read_at_commit(repo, commit, rel, where):
    """The file's text at COMMIT, or None when the commit does not hold it."""
    done = git(repo, "ls-tree", "-z", commit, "--", rel)
    if done.returncode != 0:
        raise Unreadable(f"git could not list it at {where}")
    entry = done.stdout.split(b"\0")[0]
    if not entry:
        return None
    mode, kind, sha = entry.split(b"\t")[0].decode().split()
    if kind != "blob" or mode not in REGULAR_FILE_MODES:
        raise Unreadable(f"it is not a regular file at {where} (mode {mode})")
    blob = git(repo, "cat-file", "blob", sha)
    if blob.returncode != 0:
        raise Unreadable(f"git could not read it at {where}")
    return decode(blob.stdout, where)


def read_working_tree(repo, rel):
    full = os.path.join(repo, rel)
    if os.path.islink(full):
        raise Unreadable("it is a symbolic link in the working tree")
    if not os.path.lexists(full):
        return None
    if not os.path.isfile(full):
        raise Unreadable("it is not a regular file in the working tree")
    try:
        with open(full, "rb") as handle:
            data = handle.read()
    except OSError as error:
        raise Unreadable(f"it cannot be read in the working tree "
                         f"({error.strerror})")
    return decode(data, "the working tree")


def judge(repo, base, head, path):
    """(class_only, reason) for one named path."""
    rel = relative_path(repo, path)
    if rel is None:
        return False, "the path is outside the repository"
    try:
        before = read_at_commit(repo, base, rel, "the base")
        if head is None:
            after = read_working_tree(repo, rel)
        else:
            after = read_at_commit(repo, head, rel, "the head")
    except Unreadable as refusal:
        return False, f"cannot read: {refusal}"
    if before is None:
        return False, "the file is added (the base does not hold it)"
    if after is None:
        return False, "the file is deleted (the head does not hold it)"
    if before == after:
        return True, ""
    if not rel.endswith(MARKUP_EXTENSIONS):
        return False, ("only .tsx, .jsx and .html files can be judged "
                       "class-only, and this one changed")
    return classify(before, after)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True,
                        help="the top of the git repository the paths are in")
    parser.add_argument("--base", required=True,
                        help="the commit the change is measured from")
    parser.add_argument("--head",
                        help="the commit the change is measured to; without "
                             "it, the working tree")
    parser.add_argument("paths", nargs="+", metavar="path",
                        help="a file to judge, relative to --repo")
    args = parser.parse_args(argv)

    try:
        check_repo(args.repo)
        base = resolve_commit(args.repo, args.base, "--base")
        head = (resolve_commit(args.repo, args.head, "--head")
                if args.head is not None else None)
    except Usage as refusal:
        print(f"Refused: {refusal}. Nothing was read, so nothing here is "
              f"asserted.", file=sys.stderr)
        return 2

    all_class_only = True
    for path in args.paths:
        class_only, reason = judge(args.repo, base, head, path)
        if class_only:
            print(f"{path}: class-only")
        else:
            all_class_only = False
            print(f"{path}: behaviour — {reason}")
    return 0 if all_class_only else 1


if __name__ == "__main__":
    sys.exit(main())
