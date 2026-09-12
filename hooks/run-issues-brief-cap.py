#!/usr/bin/env python3
"""Refuse a first-attempt implementer brief longer than the part that varies.

BLAST RADIUS, first:

- Registers on PreToolUse for Agent and Task. Nothing else.
- Matches one `subagent_type`, `run-issues-implementer`. Every other spawn on
  this machine passes untouched, at any length.
- REFUSES one shape: a first-attempt brief over CAP_WORDS words.
- DELIBERATELY LETS PAST: every retry, read off the FIRST `attempt N` marker in
  the prompt with N above 1; every brief whose opening carries the correction
  marker; every brief at or under the cap; a prompt it cannot read; and the
  escalated third implementer, which is a different type name.
- It writes ONE JSON line per implementer spawn it SEES, exempt ones included,
  to a file in the machine's temporary directory. Nothing else, nowhere else.
  See RULING 16.

WHAT A BRIEF CARRIES, which is what the refusal names: the issue path, the
attempt number, the road where the issue file leaves it open, and the rejection
grounds or owed items. Nothing else. The run facts every brief used to restate
-- register path, run directory, QA workspace, sign-in user, dev server,
private-copy recipe, the no-env-file suite rule -- are written once into the run
ledger's header at setup, and the implementer's own agent file already tells it
to read the ledger first.

WHY IT EXISTS. Ticket 40 of the pilot-delivery map, the runner's turn growth
ticket, ruling Q9 as revised in round 3, 2026-09-08. Measured on one fifteen-issue
run: fifteen genuine first-attempt briefs averaged 1,243 words, median 1,270,
and the part ruling Q9 permits -- the issue line plus the road settlements --
averaged 310 words. The rest was the runner restating the issue file's own
criteria and the run's own facts to an agent that reads both. Every restated word
is written once and then re-read on every later turn of the run.

WHY A CAP AND NOT A JUDGEMENT. A gate that grades what a brief SAYS was refused
by ticket 36 ruling 3, and rightly: nothing mechanical can tell a necessary
paragraph from a redundant one. A length cap judges nothing. It is the one
instrument available that cannot be wrong about content, and the human agreed on that
reading.

**THE CAP IS A CEILING, NOT A CUT, and 400 is the number.** The human revised it from
300 to 400 on 2026-09-08, in session, after the gain was measured rather than
estimated. Read the measurement before moving it again, because it says something
the ruling did not expect.

**What the cap actually saves, measured on one fifteen-issue run of 15.19 hours.**
Writing time: 3.0 minutes, which is 0.3 per cent of the run. Tokens: 7.88 million
cache-read tokens out of the 409 million the runner read, which is 0.6 per cent of
the run's weighted cost. Neither is worth a refusal on its own.

**What it does earn.** A brief grew from 606 words to about 1,500 across that one
run and nothing stopped it. At 400 every one of the fifteen first-attempt briefs
passes on the part ruling Q9 permits -- the issue line plus the road settlements,
which ran 208 to 381 words. So the cap refuses nothing that run wrote, and refuses
the next doubling. At 300 it would have refused six of the fifteen.

**The quality argument is NOT measured, and an earlier reading of it was wrong.**
Two issues on that run took a strike whose ground was annulled over something the
runner's brief carried. Both faults started in the ISSUE FILE, which the
implementer reads anyway. The brief relayed them; it did not invent them. So no
measured case exists yet of a paraphrase inventing a fault.

THE CORRECTION MARKER IS READ IN THE OPENING, not anywhere. Ticket 36 ruling 11,
2026-09-07: an override word the runner may type anywhere covers one fault and
then nothing. One run put a sentinel at the front of every gate prompt after the
first refusal and silenced its guard for the rest of the run. All four measured
correction briefs carry the marker in their first sixty characters, so the read
is anchored to the opening and the refusal says where.

RULING 16, AND WHY THE HOOK KEEPS A DIARY. Ticket 40 of the pilot-delivery map,
the runner's turn growth ticket, ruling 16, 2026-09-08. Nothing recorded when
this hook fired, so a run left no evidence of how often the runner was refused
or what it then cut the brief to, and any later move of the number would have
been an opinion. One line per implementer spawn now says which of four things
happened -- `refused`, `passed`, `exempt-retry`, `exempt-correction` -- with the
word count beside it. `report_brief_cap.py` in the run-issues skill reads it at
the finale.

TWO ROADS WERE OPEN AND THIS IS THE FIRST. Scrub rule H6 in
`~/code/agent-skills/MANIFEST.md` says a published hook writes nothing outside a
temporary directory, so the diary goes there and a script reads it at the finale.
The other road, appending to the run journal, writes inside a repository and
could not ship in the published copy. The price of this road is that the file can
vanish between a refusal and the finale -- a reboot, a temp sweep -- so a MISSING
FILE READS AS "NO DATA" AND NEVER AS "NO REFUSALS", and the reader says so in
those words.

A PASS IS RECORDED AS WELL AS A REFUSAL, and that is a default, not a ruling.
Ruling 16 asks two things of the record: how often the runner was refused, and
what it then removed. The second cannot be read off refusals alone, because what
the runner removed is visible only in the shorter brief it re-issues, which is
another first attempt. An exemption used is recorded by name for the same reason:
stamping `attempt 2` is the one road past the cap, and a record that hid it could
not tell a cut brief from a relabelled one.

IT NEVER HALTS A RUN. Nobody is at the keyboard during a run. A refusal answers ONE tool call
and names two roads out; the runner re-issues a shorter brief, or stamps the
marker the brief was missing, and the run carries on. That wording is shared by
every gate in this pack, so a refused agent meets one shape and not two.

It fails OPEN on anything it cannot read, and a prompt it cannot read passes. A
guard that blocks a spawn when the guard itself breaks is worse than no guard.
That covers the diary too: a record that cannot be written is swallowed, because
evidence for a later decision must never cost the run a spawn.

Drill: `test_run_issues_brief_cap.py` beside this file.

Exit codes: 0 pass, 2 refuse (stderr is fed back to the model).
"""

import json
import os
import re
import sys
import tempfile
import time

IMPLEMENTER = "run-issues-implementer"

# Ruling Q9, round 3, revised by the human on 2026-09-08 from 300 to 400. It is a
# CEILING: the widest permitted part measured on a real run was 381 words, so this
# refuses nothing that run wrote and refuses the next doubling.
CAP_WORDS = 400

# The correction marker is read in this many opening characters. All four
# measured correction briefs carry it inside sixty.
OPENING_CHARS = 400

# `attempt 1`, `**attempt 2**`, `attempt **3**`. The FIRST match only: a retry
# brief goes on to say "a previous gate rejected attempt 1", and reading that one
# would cap a lawful retry. The pattern is copied from
# `run-issues-parallel-gates.py:ATTEMPT`, which reads the first match for the
# same reason.
ATTEMPT = re.compile(r"\battempt\s*\**\s*(\d{1,2})\b", re.IGNORECASE)

# `**CORRECTION ROUND**`, `Correction round`, `a CORRECTION ROUND for issue 571`.
# Two adjacent words, so a brief that merely says "correction" does not exempt.
CORRECTION = re.compile(r"\bcorrection\s+round\b", re.IGNORECASE)

AFK = (
    "\n\nTHIS NEVER WAITS FOR THE HUMAN AND IT IS NOT A HALT. Nobody is at the "
    "keyboard during a run. Take one of the two roads above now and carry on."
    "\n(Gate: ~/.claude/hooks/run-issues-brief-cap.py)"
)


def count_words(prompt):
    """Whitespace-separated words, which is what the cap counts."""
    if not isinstance(prompt, str):
        return 0
    return len(prompt.split())


def attempt_of(prompt):
    """Which attempt this brief is, from the FIRST marker. 1 when it names none.

    A brief naming no attempt is read as a first attempt, so the cap is the
    default and an exemption is earned by a marker the runner writes. Every
    implementer spawn of the run this was measured on named its attempt.
    """
    if not isinstance(prompt, str):
        return 1
    found = ATTEMPT.search(prompt)
    return int(found.group(1)) if found else 1


def is_correction(prompt):
    """True when the brief's OPENING names a correction round."""
    if not isinstance(prompt, str):
        return False
    return CORRECTION.search(prompt[:OPENING_CHARS]) is not None


def exemption(prompt):
    """Which exemption this brief earns -- "retry", "correction" -- or None.

    `decide` and `observation` BOTH read this, and that is the point of it. The
    record exists to say what the cap did; a second copy of these two rules
    could drift from the one that refuses, and then the evidence would report an
    exemption the hook never granted. One rule, two readers.
    """
    if attempt_of(prompt) > 1:
        return "retry"
    if is_correction(prompt):
        return "correction"
    return None


def record_path():
    """One file, in the machine's temporary directory. Nothing else is written.

    The same directory `run-issues-typecheck-gate.py` keeps its cache in, for
    the same reason: scrub rule H6 permits it and a published copy needs no edit.
    """
    return os.path.join(tempfile.gettempdir(), "run-issues-brief-cap.jsonl")


def append_record(path, entry):
    """Append one JSON line. A failure here never reaches the caller.

    Two runs may write the same file. One short line written in append mode
    lands whole, and the reader counts anything it cannot parse rather than
    reporting a smaller number in silence.
    """
    try:
        with open(path, "a") as handle:
            handle.write(json.dumps(entry) + "\n")
    except (OSError, TypeError, ValueError):
        pass  # A guard that cannot keep its diary must still answer the spawn.


def observation(payload, code):
    """What to record for this spawn, or None for one the cap never looked at.

    It takes the exit code `decide` already reached and reads the same payload,
    so the two cannot disagree about the outcome. Its one impurity is the clock.
    Ruling 16, 2026-09-08.
    """
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    if str(tool_input.get("subagent_type") or "") != IMPLEMENTER:
        return None
    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return None

    let_past = exemption(prompt)
    if let_past:
        outcome = f"exempt-{let_past}"
    else:
        outcome = "refused" if code else "passed"
    return {
        "at": time.time(),
        "outcome": outcome,
        "words": count_words(prompt),
        "cap": CAP_WORDS,
        "attempt": attempt_of(prompt),
        "cwd": str(payload.get("cwd") or ""),
    }


def decide(payload):
    """Return (exit code, message). Pure: no disk, no clock, no state."""
    if not isinstance(payload, dict):
        return 0, ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0, ""
    if str(tool_input.get("subagent_type") or "") != IMPLEMENTER:
        return 0, ""

    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return 0, ""

    if exemption(prompt):
        return 0, ""

    counted = count_words(prompt)
    if counted <= CAP_WORDS:
        return 0, ""

    return 2, (
        f"REFUSED. This first-attempt implementer brief is {counted} words and "
        f"the cap is {CAP_WORDS}.\n\n"
        "A brief carries FOUR things and nothing else:\n"
        "1. The issue file's absolute path.\n"
        "2. The attempt number.\n"
        "3. The road, where the issue file leaves it open, and the roads "
        "rejected.\n"
        "4. The rejection grounds or the owed items, on a retry or a "
        "correction.\n\n"
        "Everything else the implementer already has. The run's facts -- "
        "register path, run directory, QA workspace, sign-in user, dev server "
        "and its link command, the private-copy recipe, the no-env-file suite "
        "rule -- are in the run ledger's header, and the implementer's agent "
        "file tells it to read that header first. The issue's criteria and "
        "invariants are in the issue file, which it reads next. Restating "
        "either is words written once and re-read on every later turn of this "
        "run.\n\n"
        "Two roads out:\n"
        f"1. Cut the brief to the four things above and re-issue it. Measured "
        "on a fifteen-issue run, the issue line plus the road settlements came "
        "to 310 words on average.\n"
        "2. If this is NOT a first attempt, stamp it: `attempt 2` or higher "
        "anywhere in the prompt, or `CORRECTION ROUND` inside the first "
        f"{OPENING_CHARS} characters. A retry and a correction round are exempt "
        "at any length, because their owed lists are the varying part." + AFK)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        print(f"run-issues-brief-cap: unreadable payload ({err}), so the spawn "
              "passed unchecked.", file=sys.stderr)
        return 0

    code, message = decide(payload)

    # Resolved HERE and not as a signature default, so a drill can replace the
    # module's own copy and reach it through `main`. Sitting 1's typecheck gate
    # bound its callables in the signature and silently ran the real compiler.
    seen = observation(payload, code)
    if seen is not None:
        append_record(record_path(), seen)

    if code and message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
