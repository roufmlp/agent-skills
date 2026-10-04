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
   114 ran 3h52m, 55% of its run. **Both figures are UNVERIFIED and neither may be
   cited as a comparable.** Checked 2026-09-14 against every measurement record on
   this machine: no line of any `issues.jsonl` names issue 129 or 114, so nothing
   says whether these were measured or estimated. They stay here as the anecdote
   that bought the class and nothing more. The measured record lives in
   `~/.claude/rulings.md`, "Class 9 counts and refuses".

## Class 9 stopped being a judgement (2026-09-14)

The human ruled it. The class asked an attacker whether an issue fits "one implementer"
against a sentence — "A clean issue runs ~30-90 min" — and no script computed anything.
Each attacker listed what the file held, found some past durations, and reasoned by
analogy. One attacker in the pass of 2026-09-14 wrote in its own findings file,
unprompted: "the estimate above is mine and is a judgement, not a measurement." The
human's three-class test in `~/.claude/CLAUDE.md` sorts that into the class that does not work,
so the rule refuses now instead: `~/.claude/skills/lib/check_issue_size.py`.

**The analogy step had nothing under it.** The durations attackers were quoting to each
other were ESTIMATES. `batch-be624c`'s ledger heads that column *Estimate*;
`batch-d67136`'s carries the runner's launch sizes and says so; `02e`'s WHALE stamp
quotes the issue file's own `## Size`, which is a previous attacker. The pipeline was
calibrating estimates against estimates, and the errors were large and one-directional:
`05b` estimated 150 minutes took 68.6, `06` estimated 120 took 40.5, `05d` estimated 120
took 28.0.

**The unit is the acceptance criterion**, chosen by measurement and not by taste. Over
the 25 issues that have run, criteria count correlates at spearman +0.62 and nothing else
comes close; invariant count and blocker count predict nothing at all (+0.05 and +0.03),
and both were things attackers had cited. The script counts and refuses; it does not
estimate minutes, because the analogy step is exactly where the judgement hid.

**It is scored.** `run_costs.py` writes the count onto the issue's line in `issues.jsonl`
beside the span that issue then occupied, and `run_compare.py sizing` reads the two
together. Nothing compared a prediction to an outcome before this, which is why the bound
went four passes without anyone noticing it named a ceiling only 4% of issues reached.

**The human set the limit at 14 the same day**, from the distribution: no issue may be bigger
than the biggest one this pipeline has finished, which is issue 06 at 14 criteria and 40.5
minutes. They were shown 12 and 17 and took neither — 12 would have refused issue 06 itself,
and 17 would have left the passes judging size by hand.

The whole measurement — the distribution, every predictor tested, the two faults found on
the way — is in `~/.claude/rulings.md`, under "Class 9 counts and refuses", because
the human's rule is that the rule belongs in the hot file and the evidence behind it does not.


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

The default road is untouched. If they are away or wave the list off, the check
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
citations across 49 open issue files and they named the repair cost as time they
were losing personally. Issue 406, the guard that makes the rule stick, read
`needs-harden` on the day the rule was written.

### The pass that ran ahead of the no-minting rule

The rule was already written and the practice ran ahead of it anyway: one pass
cleared two issues out of `needs-harden` and minted two more into it, leaving
the queue exactly where it started.

### The blanket never-attack rule, and why the fold could not keep it

Until 2026-09-07 the never-attack guard had a second half: skip EVERYTHING if
any ledger's owner line named a live session, not only the issues that ledger
holds. The reason it was written that way is real — a live run's promotion mints
issue files no ledger title carries, so a pass reading titles alone could pick
one up mid-mint.

Ticket 33 of the pilot-delivery map, ruling 5, removed it. Deliverable 3 folds
the hardening pass into a run's launch, and read literally the blanket half
refuses the run's own launch attackers: the ledger exists, its owner line names
a live session, so the pass skips everything including the issues it was spawned
to harden. It also refused run A's launch phase for as long as run B was live,
which is a second measured cost on a machine that carries two runs by design
(ticket 38, the one-run-per-feature layout ticket).

What replaces it is the row test alone, which is the half that names the actual
danger: a second writer on a file an implementer is reading. A row still at
`queued` has no implementer. The freshly minted file the blanket half protected
is now covered by promotion itself, which mints with `Status: needs-harden` and
re-derives its citations before it writes (`promotion.md`).

## The third entry point: a run's launch calls this pass (2026-09-07)

Ticket 33 of the pilot-delivery map, ruling 16, sitting 2. The phase itself is
specified in `run-issues/launch-harden.md`, and `run-issues/decisions.md` holds
why it is shaped that way. Two things belong here, because they are facts about
THIS skill rather than about the run.

**The pass gained a caller and lost nothing.** Ruling 6 kept the standalone,
pre-batch door. The human wanted the attended walk available for an issue they mean to
rule on before any code is written, and the fold does not serve that: a launch
phase defaults every reversible fork by design, which is the whole point of going
AFK. So the fold ADDS a door. The count word in the lead-in sentence is the part
that goes stale silently -- a reader who counts two doors concludes a run cannot
call this pass at all -- so `TheThirdEntryPointIsNamed` in
`test_skill_structure.py` counts the bullets and grades the word against them.

**The checklist has exactly one home, and the fold is where a second copy would
have appeared.** `launch-harden.md` says which pass to run and never how to
attack. Two copies of eleven classes drift, and the drift is invisible, because
both files read as authoritative while they disagree. The structure test refuses
a class name appearing in the phase file.

## The citation-repair step is gone, and class 5 carries it (2026-09-15)

SKILL.md told the pass to run a project's citation checker over every issue in
scope before the attackers spawned, and to correct each `moved` row. That step was
the human's own ruling of 2026-08-15. They deleted it on 2026-09-15, in the `h0915`
pass over one tracker, on a measurement taken during that pass.

What was measured. That tracker carries no such script, so the pass repaired by hand
and the corpus was counted instead: `src/` comments held ZERO line-number citations
(the human's own sweep, merged as `ffb5022`), `tests/` and `scripts/` held nine, and the
ISSUE FILES held 1,535 across 77 of 149 files. So the corpus the step served is the
issue files, and the guard being built -- issue 112 -- covers source comments only.
The step was buying a check over the corpus nobody was guarding.

Why it goes rather than widens. **Class 5 already does this work.** Class 5 makes
every attacker verify each factual claim against the real code, and a citation is a
factual claim. The one drifted citation the `h0915` pass found -- issue 103's
pointer into `src/model/delivery-date.ts`, whose line 225 had moved to a comment
fragment -- was found by an attacker reading the code under class 5, not by any
script. Four more citations in issue 111 were hand-checked the same round and all
four held. The step duplicated work the attackers cannot skip, and it charged a
round per issue in every run to do it.

The convention did NOT go with the step. A citation written from 2026-08-26 onward
still quotes text, and the legacy corpus still drains rather than being converted.
What changed is who notices a stale one: class 5, in the same pass that was going to
read the file anyway.

The structure test caught the first draft of this edit. `TestTheSlimLeftEveryRuleBehind`
refused it twice, on the anchors `Every citation you WRITE from 2026-08-26 onward
quotes text, never a line` and `is the guard that makes it stick` -- both had been
paraphrased out while the story was rewritten. That is the test doing its stated job,
and both sentences went back verbatim.

## A guard names its forms, and a reset criterion is rewritten (2026-09-23)

The audit of 2026-09-23 (`.scratch/tracker-tooling/evidence/audit-2026-09-23-run-time-and-strikes/`,
section 2) measured six runs on one tracker. 62 per cent of rejected agent-minutes, about 1,665
of 2,687, came from 12 guard-over-source issues. Two causes were this pass's.

**Root cause 1: guard criteria no attempt can meet.** `~/.claude/coderules.md` said a guard
"reads the WHOLE artefact and refuses what it cannot place", and nothing said what the
whole artefact was. Issue 53 passed criteria 2 to 7 and every invariant in all seven
attempts; each rejection named a new bypass. Issue 139 was rejected on a `.jsx` road and
139b on `@apply`, and `src/` held zero of either. The human ruled `q-s4-1`: the whole artefact
is the forms the repository holds today, measured by a stated command. Class 4 now asks for
the `Forms:` block and `check_issue_ready.py --all-guards` refuses the stamp without it
(tracker-tooling issue 22).

**Root cause 2: hardening wrote the faulty criterion, then churned it.** Issue 139c gained a
broad rule beside the narrow one and kept both; issue 139 was given "twenty-two" colour
families with no command, and Tailwind ships 26. Class 5 now asks for the command beside a
count and a rewrite rather than an addition on a reset criterion, and
`check_criteria_edit.py` refuses both (tracker-tooling issue 23). Graded over whole files the
count rule flagged 123 of 269 ready criteria, mostly fixture sizes, so it reads only the
sentences the pass wrote.

## An accepted default is recorded, and the walk closes on a check (2026-10-02)

Pass `h1001pk` in one project, 1 October 2026. The human walked the 33 queued defaults of the
picker run at the keyboard, flipped two (`q-h1001pk-seam-3`, the cut of 335 and 338, and
`q-h1001pk-315-2`, the Used-before rule) and accepted 31: "All other default is ok", then
"Ok thats fine" for the laptop count's "0+". The session wrote the two flips into
`.scratch/rulings.md` (commit `ec682f60`) and nothing for the 31. SKILL.md said "a ruling
the human gives at the keyboard goes into the rulings file", and an acceptance read as no
ruling. The 31 stayed open on the queue, all ten issues kept `Hardened (provisional)`, and
`/run-issues`' criteria gate refused issue 334 (level full) on `q-h1001pk-334-2` and
`q-h1001pk-334-4`. Run `batch-f32961` launched under `--override 334`. The 31 entries were
written a day later from the session transcript (that project's commit `c523bc11`).

A second sentence in SKILL.md would have asked the next session to remember what the first
one failed to make it remember. `check_walk_closed.py` refuses instead. The `Walk:` line is
the fact it needs: without it the check cannot tell a pass nobody walked from a walk that
recorded nothing, which is the h1001pk state. Driven on that project's own trees: the tree at
`ec682f60` with `Walk: 2026-10-01` added is refused on exactly the 31 items; the tree at
`c523bc11` passes. This pack does not ship `check_walk_closed.py`, so `SKILL.md` states the
rule the check holds, and the pass holds it by hand.

## This file exists (2026-07-27)

One of the five forks from the 2026-07-27 panel, taken by the human: three personas
wanted the provenance out of the hot file, which is billed on every invocation.
The incident anecdotes above moved here from SKILL.md the same day; the checklist
itself stays in SKILL.md because it is the working instruction, not provenance.
