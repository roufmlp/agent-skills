#!/usr/bin/env python3
"""The rulings file: what the human has already ruled, and the guard that reads it.

A queue item is a question nobody has answered. A ruling is an answer the
human gave. Nothing compared the two, so a pass could queue a question that
was already ruled, and it did: the drafting pass of 12 September queued 170 questions and
the two attended harden passes 45 more, against 13 from three run batches. In
the last two attended passes the attackers asked for hardening on issues the
human had already cut and ruled, and the queue held at least one item answered
elsewhere.

`~/.claude/CLAUDE.md` sorts that into the first class. An attacker cannot comply
with a ruling it never read, and asking it to remember will not work, so the
comparison is built and it refuses.

## The file

One per project, `.scratch/rulings.md`, one entry per ruling:

    ## <date> `<question id>` — <subject in ten words>
    Ruled: <the ruling in one line>
    Carried by: `<the file that now carries it>`

Written by `daily-brief` when it applies answers, and by an attended session
when the human rules in it. Both halves of the heading matter: the question id
ties the entry back to the item it retired, and the subject is what the guard reads.

Usage:
    rulings.py --list <rulings.md>
    rulings.py --answered <answered.md> --queue <queue.md> --rulings <rulings.md>
    rulings.py --commit <path> [--commit <path> ...]
    rulings.py --fold <decisions-log.md>

Exit 0 is a clean walk. Exit 1 is "something was read and it is wrong".
Exit 2 is "nothing was read", which a call selecting no work also returns:
an invocation that asserted nothing never reads as a pass.

**A path given on the command line must open, or the walk refuses at exit 2
naming it.** A rulings file that exists and holds no entry is the other case
and still exits 0 with `no ruling on record`. The two used to print the same
sentence at the same code, because `read` answered the empty string for a file
it could not open; see `read` for what that cost.

**An entry the reader cannot parse is named at exit 1, never stepped over.**
The file was read and one of its entries is wrong, which is a third answer
again: see `entries_and_skips`.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collect_shards import ANSWER_TOKEN, RULED, split_items  # noqa: E402

# `run-issues/empty_input.py` owns this refusal for the whole tree: one sentence
# for a reader handed nothing, so an empty input never reads as a clean result.
# It is imported rather than restated, for the reason its own docstring gives --
# a clause copied into each checker drifts, and that class is already four
# incidents of the clause being absent rather than wrong. The reach across
# directories is the one `run-issues/check_origin.py` makes in the other
# direction; the path is this file's own tree, so a worktree grades against the
# copy it is changing. A failed import raises here and nothing prints a pass,
# which is the outcome `check_origin.py` buys with a try block -- left out
# because a CLI that cannot load its guard already exits non-zero saying so.
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "run-issues"))
from empty_input import EXIT_EMPTY, empty_refusal  # noqa: E402

# The exit codes the rest of this directory uses. `EMPTY` is "nothing could be
# read", and it is also what a call that selected no work returns: an
# invocation that asserted nothing must never read as a clean walk. It is the
# guard's own constant rather than a second 2 written beside it.
CLEAN = 0
WRONG = 1
EMPTY = EXIT_EMPTY

# One rulings file per project, beside the queue it guards.
SCRATCH = ".scratch"
NAME = "rulings.md"
# An attended session's own retirement shard. The prefix comes from the
# collector, so the shard this refuses is the shard that session actually
# writes, however the collector later names it.
RULED_SHARD = RULED + ".md"

# The day a ruling was given, or `undated` where the record folded in carried
# none. An undated entry is a worse record than a dated one and a far better
# one than a ruling the reader drops on the floor.
UNDATED = "undated"
# `## 2026-09-13 `01-Q1` — local Postgres for tests`. The dash is an em dash
# because that is what the rest of this tree writes; a hyphen is accepted too,
# so an entry typed by hand on a keyboard without one still parses.
HEADING = re.compile(
    rf"^##\s+(\d{{4}}-\d{{2}}-\d{{2}}|{UNDATED})\s+`([^`]+)`\s*[—-]\s*(.+?)\s*$",
    re.MULTILINE)
# Horizontal space only, on both sides of both captures. `\s` matches a newline
# and `$` under `MULTILINE` sits before one, so `\s*` used to let a `Ruled:`
# line with nothing after it reach across the break and capture the NEXT line:
# an entry reading `Ruled:` then `Carried by: \`x.md\`` parsed clean, with
# `Carried by: \`x.md\`` recorded as the ruling. That is the same silence one
# step further on -- a bad entry reported as a good one rather than dropped --
# and it also put the `Ruled:` half of `entries_and_skips` out of reach.
RULED_LINE = re.compile(r"^Ruled:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
CARRIED = re.compile(r"^Carried by:[ \t]*`?([^`\n]+?)`?[ \t]*$", re.MULTILINE)
# The same two lines, matched on their opening words alone. A line that OPENS
# as one of them and does not parse is a malformed entry; a line absent
# altogether is a different repair, and a reader that cannot tell the two apart
# can only say "no entry here" -- which is what this file used to say, in
# silence, about both. See `entries_and_skips`.
LOOSE_RULED = re.compile(r"^Ruled:.*$", re.MULTILINE)
LOOSE_CARRIED = re.compile(r"^Carried by:.*$", re.MULTILINE)


@dataclass(frozen=True)
class Ruling:
    """One answer the human gave, and where it now lives."""

    date: str
    question: str
    subject: str
    ruling: str
    home: str


def line_fault(body, strict, loose, label):
    """Why one line of an entry did not parse, or empty where it did.

    Absent and malformed are separated because they want different repairs,
    and because the reader needs the text of the line it must fix.
    """
    if strict.search(body):
        return ""
    found = loose.search(body)
    if found:
        return f"its `{label}` line does not parse: {found.group(0).strip()}"
    return f"it carries no `{label}` line"


def entries_and_skips(text):
    """A rulings file sorted into the entries this reads and the ones it cannot.

    The skips are refusal lines, `<line>: ...`, for a caller to prefix with the
    file's own path. **An entry this reader cannot parse is never dropped in
    silence**, and the silence is what was measured on 2026-09-17: a
    `Carried by:` line carrying two backticked paths failed a capture that
    forbids a backtick, `parse` stepped over it on a `continue`, and two
    well-formed-looking entries went in while one came out. `--list` printed
    the shorter file and exited 0.

    The cost is not the short listing. It is `check_queue_shard.py`, which
    grades a queued question against these entries: a ruling that does not
    parse cannot refuse a question the human has already answered, so the pass
    asks it again -- the exact failure this file was built to prevent -- and
    nothing tells anyone the entry was bad. `run-issues/empty_input.py` holds
    the house rule this follows: a reader that parsed nothing may not report a
    pass. This is that rule at the granularity of one entry, because a file of
    seventeen entries of which one is unreadable parses to a perfectly
    confident sixteen.

    One walk, not two. `parse` and `skipped` disagreeing about what an entry is
    would be the same silence one layer down.
    """
    out, skips = [], []
    found = list(HEADING.finditer(text))
    starts = [match.start() for match in found]
    for index, match in enumerate(found):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        body = text[match.end():end]
        ruled = RULED_LINE.search(body)
        carried = CARRIED.search(body)
        if ruled and carried:
            out.append(Ruling(date=match.group(1), question=match.group(2),
                              subject=match.group(3), ruling=ruled.group(1),
                              home=carried.group(1)))
            continue
        faults = [fault for fault in (
            line_fault(body, RULED_LINE, LOOSE_RULED, "Ruled:"),
            line_fault(body, CARRIED, LOOSE_CARRIED, "Carried by:")) if fault]
        line = text.count("\n", 0, match.start()) + 1
        skips.append(
            f"{line}: `{match.group(2)}` — {match.group(3)}: "
            f"{' and '.join(faults)}. The entry is dropped, and a ruling this "
            f"reader cannot parse cannot refuse the question it answered, so "
            f"the next pass asks it again.")
    return out, skips


def parse(text):
    """Every well-formed entry in a rulings file, in the order it holds them.

    A plain list, because both importers -- `check_queue_shard.py` and this
    module's own roads -- want one, and because a second return value is a
    thing every caller must remember to look at. `skipped` is the companion,
    and the refusal is wired into the two readers that actually consume a
    rulings file rather than left for a future caller to recall.
    """
    return entries_and_skips(text)[0]


def skipped(text):
    """Every entry of a rulings file this reader could not parse, as reasons."""
    return entries_and_skips(text)[1]


# Words that carry no subject. Kept short on purpose: a long list is a second
# thing to maintain and every word dropped from it lowers the bar for a match.
# Question words are here because every queued item opens with one.
STOP = frozenset("""
a an and any are as at be been but by can could did do does for from had has have
how if in into is it its may might must no nor not of on or shall should so than
that the their them then there these they this to under up upon was we were what
when where whether which while who whom why will with would you your
""".split())

# Three shared content words is a match. Two is enough where the item and the
# entry name the same issue: the issue number is evidence in its own right, so
# it lowers the bar rather than gating the match.
#
# Ruled by the human on 2026-09-13. The issue's own sentence read "same issue
# number AND three or more shared words", and its first criterion then
# contradicted that by matching a question on issue 05 against a ruling on
# 01-Q1. The ruling settled it on the cause: a gate on the issue number can
# never catch a question already answered ELSEWHERE, and the queue held such an
# item. Nobody has measured the false-refusal rate at three words against a real
# tracker; `test_rulings.py` beside this file pins both directions.
FAR = 3
NEAR = 2

WORD = re.compile(r"[A-Za-z][A-Za-z0-9']*")
# `05-Q2` -> `05`; `641-Q11` -> `641`. A retirement id (`q-h0912-1`) opens with
# a letter and yields nothing, which is correct: it names a pass, not an issue.
ISSUE = re.compile(r"^(\d+)-")
# `05-Q2`: the issue and question a heading or an entry names. Held here rather
# than restated in every caller, for the same reason `ITEM_ID` lives in the
# collector: two copies of a matching rule drift.
QUESTION_REF = re.compile(r"(?<![\w-])(\d+-Q\d+)(?![\w-])")


def content_words(text):
    """The words of a subject that carry it, lowercased, each counted once."""
    return {word.lower() for word in WORD.findall(text)
            if word.lower() not in STOP}


def issue_of(question):
    """The issue number a question reference names, or empty where it names none."""
    found = ISSUE.match(question.strip())
    return found.group(1) if found else ""


def matches(subject, entries, issue=""):
    """Every ruling whose subject is close enough to `subject` to answer it.

    `issue` is the issue number the asking item sits on. Where it equals the
    entry's own, the threshold drops from `FAR` to `NEAR`.

    This is the HEURISTIC half of the comparison, and it answers one question:
    is this the same question in different words. `ruled_by_id` is the
    certainty that sits beside it and answers the other one: does this item
    carry the entry's own name. Neither replaces the other, and only this half
    can be passed by a writer's declaration -- see `ruled_by_id` for why.
    """
    words = content_words(subject)
    out = []
    for entry in entries:
        shared = words & content_words(entry.subject)
        near = bool(issue) and issue == issue_of(entry.question)
        if len(shared) >= (NEAR if near else FAR):
            out.append(entry)
    return out


# The one line that lets a question through a matching ruling. The writer has
# read the entries and says they do not answer it. `none match` is the wording
# the issue fixed; anything after the colon is the writer's own note, so a
# contradiction of a named entry reads here exactly as a clean check does.
DECLARATION = re.compile(r"^Rulings checked:", re.MULTILINE)
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def body_of(item):
    """What an item ASSERTS: its heading dropped and its fenced blocks removed.

    Both removals close a hole the review of 2026-09-13 found in this guard.

    The heading, because an item re-asking a ruled question carries that
    entry's own id on it — `## 05-Q2: ...` against an entry for `05-Q2` — so
    reading the whole item let an exact duplicate satisfy the quote
    requirement with nothing read at all. An item does not quote itself.

    The fences, because a block showing the escape line as an example is an
    example. `headings` already treats a `## ` inside a fence that way, by way
    of the collector's own splitter, and one file should read a fence one way.
    """
    lines = item.split("\n")
    if lines and lines[0].startswith("## "):
        lines = lines[1:]
    return FENCE.sub(" ", "\n".join(lines))


def declared(item):
    """Whether an item says it read the rulings file."""
    return bool(DECLARATION.search(body_of(item)))


def quoted_ids(item, entries):
    """The question ids of entries this item quotes.

    An id the rulings file does not hold is not a quote. The writer has to have
    read something that exists, or the declaration asserts nothing.
    """
    held = {entry.question for entry in entries}
    body = body_of(item)
    return {question for question in held
            if re.search(rf"(?<![\w-]){re.escape(question)}(?![\w-])", body)}


def nearest(subject, entries, count=2):
    """The entries closest to `subject`, most shared words first.

    Ties keep the file's own order, so the same item always quotes the same
    two entries and a second run of the guard prints what the first one did.
    """
    words = content_words(subject)
    ranked = sorted(enumerate(entries),
                    key=lambda pair: (-len(words & content_words(pair[1].subject)),
                                      pair[0]))
    return [entry for _, entry in ranked[:count]]


def path_for(start):
    """The rulings file governing a path, or empty where its tree holds none.

    A queue shard sits at `<tree>/.scratch/decisions-queue.d/<owner>/<x>.md`, so
    the walk upwards finds `.scratch` two directories above it. The walk rather
    than a fixed depth, because the same guard is run by hand on a shard copied
    anywhere, and by a hook on a path it was handed.

    **The walk stops at the tree that owns the shard**, marked by its `.git`.
    A worktree lives INSIDE the checkout it was cut from -- these live at
    `<repo>/.claude/worktrees/<name>` -- so an unbounded walk out of a tree
    with no `.scratch` of its own lands in the parent's, and grades one tree's
    questions against another tree's record. `collect_shards.py` is built on
    the opposite rule: a shard under `<tree>/` belongs to that tree. Found by
    the review of 2026-09-13.
    """
    here = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.basename(here) == SCRATCH:
            return os.path.join(here, NAME)
        if os.path.isdir(os.path.join(here, SCRATCH)):
            return os.path.join(here, SCRATCH, NAME)
        parent = os.path.dirname(here)
        if parent == here or os.path.exists(os.path.join(here, ".git")):
            return ""
        here = parent


def entries_for(start):
    """(rulings, skips) governing a path, in one read, the skips path-named.

    No file and no `.scratch` both read as two empty lists. Empty is the honest
    answer for a project that has never recorded a ruling, and every caller
    treats it as a clean walk. A rulings file that cannot be READ is the same:
    this guard refuses questions, never the absence of a file.

    The pair, and no single-value road beside it. `read_for` stood here and
    answered entries alone; it was left in place when this was written, with
    one caller and a docstring, which is the shape a future caller reaches for
    without ever learning that entries can go missing. The skips come back
    whether or not the caller wants them.
    """
    path = path_for(start)
    if not path:
        return [], []
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return [], []
    entries, skips = entries_and_skips(text)
    return entries, [f"{path}:{skip}" for skip in skips]


def heading_ids(head):
    """Every id a queue heading carries: the retirement id and the question ref.

    Both name the same item. The shard retires by the `q-` id, and the brief
    and the attackers speak in the `05-Q2` reference, so an entry written under
    either one is an entry for this item.
    """
    return set(ANSWER_TOKEN.findall(head)) | set(QUESTION_REF.findall(head))


def ruled_by_id(head, entries):
    """Every ruling entry recorded under an id this heading itself carries.

    The word overlap in `matches` is the right tool for "is this the same
    question in different words", and the wrong tool when the two carry the
    same NAME. MEASURED 2026-09-22: a queue item headed
    ``## `q-h0922b-124-1` [irreversible] — a failed push cleanup fails the
    sign-in`` was graded against an entry headed ``## 2026-09-22
    `q-h0922b-124-1` — which road stops a refused subscription clear from
    refusing the sign-in``. The ids are identical. The subjects name one thing
    in different words -- "cleanup" against "clear", "fails" against
    "refusing" -- so they share ONE content word against a threshold of three,
    nothing fired, and `check_queue_shard.py` exited 0 over a question the human
    had already ruled.

    So this is a second road, not a looser threshold on the first. It ignores
    `NEAR` and `FAR` entirely, because an id in common is not evidence of a
    match -- it is the match.

    **A hit here is not escapable by the item's `Rulings checked:` line, and
    that is the whole reason the two roads are separate functions.** The
    declaration exists for a writer who read a near-miss entry and judged it a
    different question; that is a judgement, and a judgement can be right.
    Carrying the entry's own id is not a judgement about anything. A writer
    with a genuine follow-up takes a NEW id, which is the road
    `check_queue_shard.py` names in its refusal.

    Both halves of an item's name count, by way of `heading_ids`: the `q-` id
    the shard retires on, and the `05-Q2` reference the brief and the
    attackers speak in. An entry written under either one is an entry for this
    item. The comparison is case-folded, so an id retyped in another case is
    still the same id rather than a free escape.
    """
    wanted = {one.strip().casefold() for one in heading_ids(head) if one.strip()}
    return [entry for entry in entries
            if entry.question.strip().casefold() in wanted]


def check_answered(answered, queue, entries):
    """Every answered item that the rulings file does not carry, as reasons.

    The daily brief retires an item by writing its id into its own
    `answered.md`. Retiring it is what makes it invisible; recording the ruling
    is what makes the next pass able to read it. Those are two writes, and
    before this check the second one was a thing the brief was asked to
    remember. An empty list is a brief that wrote both.
    """
    held = {entry.question for entry in entries}
    by_id = {}
    for part in split_items(queue):
        head = part.split("\n", 1)[0]
        if head.startswith("## "):
            ids = heading_ids(head)
            for one in ids:
                by_id[one] = (head, ids)
    out = []
    for ident in ANSWER_TOKEN.findall(answered):
        if ident not in by_id:
            out.append(f"`{ident}` is answered and no item in the queue carries "
                       f"that id, so no ruling can be recorded for it")
            continue
        head, ids = by_id[ident]
        if ids & held:
            continue
        names = ", ".join(f"`{one}`" for one in sorted(ids))
        out.append(f"`{ident}` is answered and the rulings file holds no entry "
                   f"under {names}. Write one, or the next pass asks it again: "
                   f"{head.strip()}")
    return out


def check_commit(paths):
    """Every ruling in a commit's file list that the rulings file does not join.

    The human ruled on 2026-08-08 that an attended session sweeps its own queue
    at close, and such a session records the retirement in its own `ruled.md`.
    That file hides the item from the board immediately. The rulings file is
    what the next pass reads, and it is a SECOND write — so a commit that
    carries the first and not the second takes a question off the board and
    leaves nothing behind that anyone can apply.

    The brief's own `answered.md` is not this shape. Its entries are checked
    against the queue by `check_answered`, which can name the item; a file list
    cannot, because an id is not a path.
    """
    seen = [path.replace("\\", "/") for path in paths]
    roots = {scratch_root(path) for path in seen
             if os.path.basename(path) == NAME}
    return [f"{path} records a ruling and the commit carries no {NAME} in its "
            f"own {SCRATCH}; the question leaves the board with nothing on record"
            for path in seen
            if os.path.basename(path) == RULED_SHARD
            and scratch_root(path) not in roots]


def scratch_root(path):
    """The `.scratch` directory a path sits under, as written, or empty.

    Two paths share a root when the same `.scratch` holds them. A `rulings.md`
    somewhere else in the tree -- another feature's copy, a doc of the same
    name -- leaves this project's own record untouched, so it is not the entry
    a retirement needs beside it.
    """
    parts = path.split("/")
    if SCRATCH not in parts:
        return ""
    return "/".join(parts[:parts.index(SCRATCH) + 1])


# A date anywhere in an answered log item. Used rather than today's, because
# folding is bookkeeping over answers already given and stamping them with the
# day of the fold would say they were all ruled at once.
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def strip_ids(head):
    """A heading's own words, with its backticked ids and refs taken off."""
    text = re.sub(r"`[^`]*`", " ", head[len("## "):])
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = QUESTION_REF.sub(" ", text)
    return " ".join(text.split()).strip(" :-")


def entry(date, question, subject, ruling, home):
    """One rulings entry, in the shape `parse` reads back."""
    return (f"## {date} `{question}` — {subject}\n"
            f"Ruled: {ruling}\n"
            f"Carried by: `{home}`\n")


def fold(log, home):
    """A project's `decisions-log.md` as rulings entries.

    The log is described by `daily-brief` as the answered half of the queue
    (`daily-brief/SKILL.md`), so it holds queue items and is split by the
    collector's own splitter. An item's first prose line is its ruling; an item
    with no prose was never answered and is not folded, because an entry with
    no ruling would refuse a later question and offer nothing to apply instead.

    Ruled by the human on 2026-09-13. No repository this was written against
    holds a `decisions-log.md`, so the shape is read off that one sentence and
    has never met a real file. Run the fold against one before
    trusting its output.

    `home` is the log itself. That is where the reasoning still lives, and the
    entry points at what a reader can actually open.
    """
    out = []
    for part in split_items(log):
        head = part.split("\n", 1)[0]
        if not head.startswith("## "):
            continue
        ids = heading_ids(head)
        body = [line.strip() for line in part.split("\n")[1:] if line.strip()]
        if not ids or not body:
            continue
        found = DATE.search(part)
        refs = sorted(one for one in ids if issue_of(one))
        out.append(entry(found.group(1) if found else UNDATED,
                         refs[0] if refs else sorted(ids)[0],
                         strip_ids(head), body[0], home))
    return "\n".join(out)


class Unreadable(Exception):
    """A path the operator named on the command line that would not open.

    It carries the finished refusal rather than the cause, because the sentence
    is built where the shape is known -- `main` knows a `--fold` path holds a
    decisions log and a `--list` path holds rulings, and the reader needs that
    word to know which file to go and look at.
    """

    def __init__(self, refusal):
        super().__init__(refusal)
        self.refusal = refusal


def read(path):
    """A file's text. An unreadable path raises `OSError`, it does not read empty.

    It used to answer the empty string for a path that is not there, and that
    swallow IS the defect measured on 2026-09-17: every caller turns empty text
    into zero entries, and zero entries is what a rulings file holding none
    yields, so `--list ti06` -- a search term where a path belongs -- printed
    `ti06: no ruling on record.` and exited 0 while `.scratch/rulings.md` held
    sixteen entries. The same blindness reached `--fold`, which printed one
    blank line, and `--answered`, which printed its own pass sentence over
    three files of which one did not exist. `--commit` is not affected: it
    grades path STRINGS from a commit's file list and opens none of them.

    `entries_for` keeps its own swallow and is deliberately not changed. Its
    path is one this module DERIVES by walking upwards, not one an operator typed,
    and a project that has never recorded a ruling legitimately has no file
    there. That is the guard's second rule -- where zero is legitimate and the
    reader already says so, leave it -- and `check_queue_shard.py` is built on
    it: it refuses questions, never the absence of a record.
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read_named(path, shape, remedy):
    """The text of a path the OPERATOR named, or `Unreadable` saying why not.

    The distinction this draws is readability, never how much was parsed, and
    it has to be: a file that is not there and a rulings file holding no entry
    BOTH parse to zero entries, and telling those two apart is the whole of the
    repair. So this takes the shared sentence from `empty_input` and its exit
    code, and leaves behind `refuse_empty`, which triggers on a count of zero
    rows and cannot separate them.

    `read=0` is passed because it is true -- nothing was read at all -- and it
    selects the guard's own "very likely the wrong file rather than a pattern
    fault" line, which is exactly the diagnosis a typed search term earns.
    """
    try:
        return read(path)
    except OSError as failure:
        reason = failure.strerror or failure.__class__.__name__
        raise Unreadable(empty_refusal(
            path, shape, read=0,
            remedy=f"The path could not be opened: {reason}. {remedy}")) from failure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rulings", default="", help="the project's rulings file")
    parser.add_argument("--list", dest="show", default="",
                        help="print one line per entry of a rulings file")
    parser.add_argument("--answered", default="",
                        help="a brief's `answered.md`; refuses an answered item "
                             "the rulings file does not carry")
    parser.add_argument("--queue", default="",
                        help="the collected `decisions-queue.md` the ids name")
    parser.add_argument("--commit", action="append", default=[],
                        metavar="PATH",
                        help="one file of a commit's file list; refuses a "
                             "`ruled.md` with no rulings file beside it")
    parser.add_argument("--fold", default="",
                        help="print a `decisions-log.md` as rulings entries")
    args = parser.parse_args(argv)
    try:
        return walk(args, parser)
    except Unreadable as refused:
        # One refusal point for every road. A clause per flag is what the
        # shared guard exists to stop, and one swallow in `read` was already
        # enough to blind three of them at once.
        print(refused.refusal, file=sys.stderr)
        return EMPTY


def walk(args, parser):
    """Every road `main` offers, with an unreadable named path free to raise."""
    if args.show:
        entries, skips = entries_and_skips(read_named(
            args.show, "ruling entry",
            "`--list` takes the PATH of a rulings file, not a search term and "
            "not a question id. A rulings file that exists and holds no entry "
            "is a different answer, and it still exits clean."))
        for item in entries:
            print(f"{item.date} {item.question} — {item.subject} — {item.ruling}")
        if skips:
            # What parsed is printed first and the refusal follows it, because
            # the operator needs both: the entries this listing is short by,
            # and the lines to repair. Exit 1, not 2 -- the file was read and
            # it is wrong.
            for skip in skips:
                print(f"REFUSED — {args.show}:{skip}", file=sys.stderr)
            return WRONG
        if not entries:
            print(f"{args.show}: no ruling on record.")
        return CLEAN

    if args.fold:
        log = read_named(
            args.fold, "decisions log",
            "`--fold` takes the PATH of a project's `decisions-log.md`. "
            "Printing nothing over a path that is not there reads exactly like "
            "a log in which nothing was ever answered.")
        print(fold(log, home=args.fold))
        return CLEAN

    refusals = []
    if args.commit:
        refusals += check_commit(args.commit)
    if args.answered:
        if not args.queue:
            parser.error("--answered needs --queue: an id is not an item")
        if not args.rulings:
            parser.error("--answered needs --rulings: without it every "
                         "retired id reads as unrecorded")
        # All three paths are ones the operator typed, so the absence of any
        # one of them is a typo rather than a state. Before this, a missing
        # `answered.md` yielded no ids to grade and the walk printed its own
        # pass sentence; a missing `--queue` or `--rulings` blamed the brief for
        # every id it had correctly retired.
        entries, skips = entries_and_skips(read_named(
            args.rulings, "ruling entry",
            "`--rulings` takes the PATH of the project's rulings file."))
        # An entry that did not parse is named before any id is graded. This
        # road reads the rulings file to decide whether a retired question was
        # recorded, so a dropped entry blames the brief for a ruling it wrote.
        refusals += [f"{args.rulings}:{skip}" for skip in skips]
        refusals += check_answered(
            read_named(args.answered, "retired id",
                       "`--answered` takes the PATH of a brief's "
                       "`answered.md`."),
            read_named(args.queue, "queue item",
                       "`--queue` takes the PATH of the collected "
                       "`decisions-queue.md` the ids name."),
            entries)
    if not args.commit and not args.answered:
        print("REFUSED — no --list, --fold, --commit or --answered: nothing "
              "was checked, so nothing passes", file=sys.stderr)
        return EMPTY
    for line in refusals:
        print(f"REFUSED — {line}", file=sys.stderr)
    if refusals:
        return WRONG
    print("rulings checked: every answer on record, every ruling committed with it.")
    return CLEAN


if __name__ == "__main__":
    sys.exit(main())
