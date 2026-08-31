# harden-issues — decisions record

Why the skill is shaped the way it is. Same pattern as `run-issues/decisions.md`:
the SKILL.md carries the rules, this file carries the evidence and the reversals,
so the provenance is not billed on every invocation. Read it when changing the
skill, not when running it.

## The pass exists because gates grade against the issue (2026-07-27)

Settled after two runs' evidence (the July 2026 batches; the fuller brief lives
in the `acceptance-criteria-hardening` memory file). An issue whose acceptance
criteria are wrong when written passes every gate, because the implementer builds
to the bad spec and both gates grade against that same bad spec. The only place
to catch it is before anyone builds — at authoring time, with write authority
capped at what can be cited.

## What each checklist class cost before it was a class (2026-07-27)

Earned, not invented — each shipped a real defect through green gates:

1. **Unstated invariants** — issue 114 met all four criteria while dropping the
   page cap.
2. **Invariant scope** — 126's request-count invariant was graded against four
   callers while two more arrived from 120.
3. **Vague words** — 122's "internally consistent" was satisfied by the bug it
   described.
4. **Guards that cannot fail** — eleven guards that could not fail in fourteen
   issues.
5. **Unverified premises** — 114's headline premise was false of the actual
   database; 116 said two channels, the code had three.
6. **Empty or missing hostile data** — 118: five tables, zero rows.
7. **Deploy and boundary reality** — three migrations in one run, each with an
   unstated ordering hazard; the run's worst defect was a server page importing
   a client module.
8. **Observability** — 112's known fault is structurally invisible to a UI walk.
9. **Size against the one-implementer bound** — 129 ran 4h58m, 19% of its batch;
   114 ran 3h52m, 55% of its run.

## Hypotheses are not facts: the 122 lesson (2026-07-27)

A manual pre-batch pass settled "latest outcome wins" as fact, and the run spent
two attempts down the falsified road. Hence the rule: any road-shaped statement
whose premise was not tested is written as a hypothesis with an explicit
premise-check clause for the implementer — testing the premise itself, not a
narrow question near it.

## The stamp and `Status:` were two sources of truth (found 2026-08-02, fixed 2026-08-04)

Found after the model-comparison pass on issues 167, 174,
182-187 and 201-206. All three arms hit it, so it is the skill's fault rather than
one model's.

**What happened.** Five issues (167, 182, 183, 185, 186) came out of the pass with
`Hardened (provisional): 2026-08-02 — n sharpened, m defaults pending.` and with
their `Status:` line still reading `needs-harden`. By this skill a provisional stamp
puts an issue in scope. By `/run-issues`, `all` "resolve[s] the scope from each issue
file's `Status:` line and take[s] only clean `ready-for-agent` issues", and skips
`needs-*`. So all five would have been silently dropped from the next batch, while
this skill's own output said they were ready. Nothing errors. The run just comes back
smaller than it should, and nobody is told which issues went missing.

**Why the skill causes it.** SKILL.md says "Then stamp the issue, one line under
`Status:`". It says where to put the stamp and never says to update `Status:` itself.
The only place it touches `Status:` is the failure road — "set `needs-harden`
instead" when an answer needs input nobody has. So a pass that succeeds has no
instruction to clear the `needs-harden` it started from, and an issue that entered
through the standalone door keeps the status that sent it here.

**A second, related contradiction, same cause.** The fan-out guard says "Skip
anything whose `Status:` is not `ready-for-agent`", but the standalone entry point
says the pass runs over "any set of `ready-for-agent` or `needs-harden` issue files"
and that `needs-harden` "is what a run sets when it finds criteria that are wrong or
stale, so those issues return here". Read literally, the guard tells the pass to skip
exactly the issues the entry point exists to serve. In practice every arm ignored the
guard and attacked the `needs-harden` issues, which was the right call and is not what
the text says.

**Cost if it had been left.** Silent under-scoping of every batch after a standalone
pass, in the direction that looks like success. This is the same shape as the defects
the checklist exists to catch: a green that means nothing, with no observer.

**The fix, applied 2026-08-04 in one edit across four files.**

1. In "Output and the stamp", the status change is now part of stamping: a full or
   provisional stamp sets `Status: ready-for-agent`, and any minting note goes on
   its own `Provenance:` line rather than as a suffix on `Status:`. The text says
   plainly that the two must agree and that `/run-issues` reads the status, not the
   stamp.
2. In "Fan-out", the never-attack guard now keys on what it was always protecting
   against — an issue a run currently holds. It reads the run ledger's row and owner
   line, not the issue's `Status:`, and says outright that `needs-harden` is in
   scope. The same guard was duplicated in `harden-issues-attacker.md` and
   `harden-issues-seam.md`; both were corrected the same way, since an agent obeying
   its own brief would have re-introduced the skip the skill had just dropped.

**The judge, next standalone pass:** whether any issue leaves the pass with a
`Hardened` stamp and a `needs-*` status. One is a regression, not a slip.

## The Fable pin is gone; both agents inherit (2026-08-02)

The human's call. `harden-issues-attacker.md` and `harden-issues-seam.md` had read
`model: fable` since they were written, on the theory that blind-spot hunting was
the one job Fable still led. Both now read `model: inherit`, so the pass runs on
whatever tier the session was launched on. Effort is unchanged at `high`.

Two reasons. The pin put the model in a file nobody reads at launch, so a session
started on Opus quietly bought Fable for the hardest, most parallel stage of the
pass. And Fable is credit-gated, which is why SKILL.md carried a respawn-on-Opus
fallback — a branch that only exists because of the pin. Wanting Fable is now one
action: launch the session on Fable.

This also removes the last exception to `/run-issues`'s "workers inherit the
session model" rule, so that rule's parenthetical about a deliberate pin went with
it. The rule against passing `model:` on a spawn stands: the Agent tool's
parameter still beats frontmatter, and `inherit` is exactly what it would defeat.

**The launch line came with it, same day.** `inherit` makes the tier a launch-time
choice, and this pass had nowhere that choice was visible: `/run-issues` prints
its resolved model before spawn #1 and records it in the ledger and the merge
briefing, while a harden stamp carries a date and two counts and no tier. So a
spawn-time `model:` value, or a session launched on the wrong tier, would have run
the whole pass unobserved. SKILL.md now requires the same launch line, and repeats
the never-pass-`model:` rule where the spawning happens rather than only in
`/run-issues`. The human asked for it after asking what the odds of a stray Fable
spawn actually were — low, but nothing would have caught one.

## Checks only the human can run belong to the pass, not to the run (2026-08-09)

The human's call, from the pass that hardened the batch before it. That pass left two
issues carrying work for a person: one told the run to execute a script and report
what it saw, another asked for a value mid-flight. Both were checks against
production — the database the agents may not write and the settings they cannot
reach — and both were answerable in ten minutes by the man sitting at the keyboard.
They ran them themselves at the end of the session and handed the results back, and the
issues were corrected before the run started.

That is now the rule rather than the exception. The pass is attended by definition;
`/run-issues` is not, and a run that meets a human-only check either stalls or
guesses. So an attacker or the seam agent records an out-of-reach premise as a
**check**, distinct
from a question: a question needs the human's judgement, a check needs only their hands
and their credentials. The orchestrating session runs everything it can run itself,
puts the remainder to them as a numbered list beside the questions, and writes the
answers into the issue files cited `checked by the human <date>`. A criterion that asks
the run to pause for a person is treated as a defect in the issue, the same as a
guard that cannot fail.

The default road is untouched. If they are away or waves the list off, the check
defaults, is written as a default and is queued — the batch never waits on it.

## No issue named the database its rows land in (2026-08-12)

Class 10. An issue loaded a supplier catalogue: 4058 rows across four tables. Both
gates graded it row by row. It passed nine criteria and ten invariants, and merged.

Every row landed on the QA project. The customer's project held none of them, and
the release conditions that count those rows count them there.

Nothing failed. The issue's own text opened "the import that fills the four tables
from the snapshot" and named no database. Its parent ticket named none either. Its
last criterion read "counting rows on the target database answers release conditions
1 and 3", and the target database was bound to nothing anywhere in the file. Every
agent in a run may write one non-production database, correctly, so the implementer
built the only importer it could build and the gates read the only database they
could reach. Both gates raised the gap independently, and both were right to stop
there: a gate reports rather than widens scope, so the sentence arrived in the merge
briefing after the branch was finished.

The instance closed on a follow-up issue. The shape repeats on anything that writes
rows rather than code, which is why it became a class instead.

## The 481/482 gaps: the split rule aligned, checks carry their attempt, defaults kill their checks (2026-08-29)

Routed through pilot-delivery ticket 33, "Four gaps the 481/482 hardening pass
hit". The human changed the split rule in `~/.claude/questionrules.md`'s routing
table at 12:42 and the afternoon's pass still put a split to them, because this
skill's class 9 and its stamp section carried the 2026-07-27 rule — a local
refusal beats a table it does not cite. Both sentences now defer to the table:
the session settles a split it can complete (cut, harden both halves, stamp
both); one it cannot goes to them. `to-issues/SKILL.md` carried the same stale
sentence and lost it the same day. The deeper repair is in `questionrules.md`
itself, "When a skill disagrees with this file": that file wins, and the finder
repairs the skill rather than asking which wins.

Two refusals joined the checks section the same day, both from the same pass.
Gap 2: a `## Checks for the human` item carries its failed attempt — the command run
and what it returned, or the credential/console wall — or the pass runs it or
deletes it; the incident was an allow-list read they were asked for that twenty
lines of `scripts/dev-signin-link.mjs` answered. Gap 3: a defaulted question
kills every check that only serves it; the incident was a 307-replay check that
went to them after the seam agent had already defaulted the 303 answer that
removed the replay. Both agent briefs now state the item shape, so the refusals
grade arrivals rather than manufacture rewrites. Gap 4 of the same section
records the `[irreversible]` blast-radius refusal working as written; the
attacker brief's looser "expensive to undo" wording was tightened to the routing
table's four classes so the wrong marks stop arriving.

## The incident anecdotes moved out of SKILL.md (2026-09-01)

The human asked for both skills to be as slim as possible on 2026-08-29, and
the reason is measured rather than aesthetic: the 2026-08-26 timing reading puts a gate at
78% of its wall clock reading and writing rather than in tool calls, so every
line in a loaded brief is paid on every spawn that reads it, for the life of the
skill.

The rules, their dates and their adoption stamps stayed in SKILL.md. What
follows is the evidence each one was adopted on. `test_skill_structure.py`
beside this file is what refuses a move that carries a rule out with its story,
and what refuses a paste-back.

Two stories are not repeated here because they already had a home:
`run-issues/decisions.md` holds the 2026-08-09 prohibition's three faults and
the two adversarial gates that died at the 2026-08-15 weekly usage limit. This
skill had been carrying a second full copy of both, which is the duplication the
ticket is named for. The Fable pin's history is the same case, and its home is
the 2026-08-02 section above.

### Class 3, R1: the sanitiser that passed 69 tests and broke the confirm route

Adopted by the human 2026-08-18, from the `cab74e` run. Issue 262b moved the auth
failure sanitiser into a shared module so `/auth/confirm` could use it. Its
criterion graded the move by the surviving tests. The implementer replaced a
literal sanitiser with a pattern built per character, and all 69 tests passed.
The critical review gate then drove two live defects on the unauthenticated
confirm route: a needle of about 1000 characters built a regex V8 refuses to
compile, so the route returned HTTP 500 **and logged nothing**, because its own
`catch` called the throwing function again; and the separator tolerance let a
crafted `token_hash` delete the real message out of the log line. Strike 1, one
retry, 89 minutes against an estimate of 30 to 45. The 21-item verify pass
missed both, and the gate said why: a permissive-regex swap satisfies "the
existing tests keep passing" while changing behaviour.

### Class 4, D4: ten guards green while proving nothing, and why not mutation testing

Adopted by the human 2026-08-19, from the `e047ba` finale, queue item D4. **Ten
guards in that batch were green while proving nothing**, and `docs/patterns.md`
entry 6 already forbade exactly that, written four days earlier after the
328-332 run lost four correction rounds to it. Every implementer followed it and
every drill passed. Issue 333a drilled its leak guard against a fixture built
from the same wrong idea of Sentry's payload that the guard held, so 54 tests
could not see it. In all ten the catch came from an adversarial gate designing
its own drill.

**Mutation testing was weighed as the mechanical alternative and refused the
same day**, and the refusal is recorded so nobody re-proposes it: it runs the
suite per mutant, and against 6,385 tests it would have been the most expensive
rule in the system, per run, for ever.

### Class 4: evidence addressed to a party that cannot write it

Adopted by the human 2026-08-10 for the issue file, from the 301-307 finale. Issue
305's criteria 3 and 8 asked for mutation drives "recorded in the issue's
notes", the spawn brief forbade it, the drives went into test doc comments, and
the review gate filed the contradiction as `rg305-06`.

**Widened by the human 2026-08-16 to any closed home, after the `dc132b` run.** Five
of its nine issues — 345, 355, 288, 292 and 293 — carried a clause aimed at the
implementer, and the commit-message half fell outside the 2026-08-10 wording.
Issue 288's review gate rejected the work partly because those clauses were
unmet, and the runner had to annul the ground. One annulled rejection and one
wasted gate round, in one batch.

### Class 11: the five criteria resets that shared one shape

Adopted by the human 2026-08-29, from the ticket 33 audit. Five criteria resets
shared this shape — 296, 327, 332, 335, 419b — every one on a stamped file, each
costing two rejected attempts before the strike-2 check found the spec at fault.
It was the one criteria-fault shape no class covered.

### The unmeasured `[irreversible]` mark that held a stamp

Adopted by the human 2026-08-29, on the ticket 33 audit. Issue 419b's question 6 was
marked on the premise that it "decides the shape of rows a person types on the
pilot project"; the pilot holds 151 supplier rows with 151 distinct dedupe keys,
so no typed row was at risk, and one query would have killed the question that
instead held the stamp and cost three agents and four exchanges.

### The measurement behind the graded-home refusal

Adopted by the human 2026-08-28, after run `99b-99e-6e11ba`. Issue 99b's rule for
how much of a supplier's message may advance a purchase order was written once,
in `## Questions for the human, round two`, a section no gate grades. The file an
implementer read at spawn was 1417 lines, of which 368 were graded, and the rule
was in none of them. Two implementers filled the silence with something wider.
Both were rejected by both gates, and both rejections were annulled when the
strike-2 pass found the criteria at fault rather than the code. **Two implementer
spawns and four gate spawns, bought by a section-heading choice.**

### The citation repair cost that produced the quoted-phrase rule

Ruled by the human on 2026-08-26 in the daily brief, after one run broke 228
citations across 49 open issue files and he named the repair cost as time he was
losing personally. Issue 406, the guard that makes the rule stick, read
`needs-harden` on the day the rule was written.

### The pass that ran ahead of the no-minting rule

The rule was already written and the practice ran ahead of it anyway: one pass
cleared two issues out of `needs-harden` and minted two more into it, leaving
the queue exactly where it started.

## This file exists (2026-07-27)

One of the five forks from the 2026-07-27 panel, taken by the human: three personas
wanted the provenance out of the hot file, which is billed on every invocation.
The incident anecdotes above moved here from SKILL.md the same day; the checklist
itself stays in SKILL.md because it is the working instruction, not provenance.
