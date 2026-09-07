# run-issues — settled decisions and the incidents behind them

Read this before changing how the run works. Do not read it to run one — the
skill and the agent files are self-contained. Nothing here is loaded into a
subagent's context.

Newest section last.

---

## Original design (2026-07-19, grilled and agreed)

Fresh subagent per unit of work; adversarial gates; two-strike escalation; runner
owns the branch and the human owns main; all state in files so any session can resume.
These have not changed.

## Post-run-1 revisions (2026-07-19, after the 13c–14 run)

Thin ledger and journal split; shared-quota ownership; routing verification;
one-writer worktrees with explicit-path commits; HTML-over-HTTP verification as
the default; preview-deploy skip where the classifier blocks it.

**Incidents behind them.** A verify gate and a live-claims agent were spawned
concurrently against one rate-limited org; the second got nothing and found out
late — hence quota ownership. A gate declared findings routed and never appended
them; another gate caught it by luck — hence "a declared routing is not a routing".
A side agent's probe files landed in the run tree and only explicit-path staging
kept them out of a gate-passed commit — hence one-writer worktrees.

## Finale go-ahead removed (2026-07-21)

The judgment half used to wait for a human go-ahead, to time the spend. Skipping
it on the 27–32 run cost a 64-finding acceptance walk. The spend is cheaper than
the walk. Do not re-litigate.

## Post-run-5 revisions (2026-07-22, after the 19-issue batch)

Ledger thinness enforced at each `done`; mid-run directives are this-run-only; the
finale builds cold; the halt block, not the cron, is what resumes a run.

**Why the cron cannot resume a run.** CronCreate jobs are session-only and fire
only while the session is idle, so they reach no further than a five-hour window
the same session sits through. Anything longer — a weekly limit resetting days
out — needs a human re-invoking `/run-issues resume` against the halt block.

**Incidents.** The ledger regrew to 39.8k characters, 23k of it Log — 25 entries
averaging ~900 characters against a "~2 lines" rule — re-read by ~57 spawns. The
branch built green on a warm cache and the first production deploy failed cold:
Tailwind scanned `.scratch`, found a `bg-[url(…)]` quoted inside an issue write-up,
and emitted CSS Turbopack could not resolve. "Use fable for UI/UX" was written to a
memory file mid-run, then rescinded at close, leaving seven issues' model
assignment needing a historical footnote. The run halted on a weekly limit
resetting three days later, and the cron could not survive it.

## Post-walk revisions (2026-07-23, after the 30-finding deployed walk)

Verify gates pick hostile fixtures and drive production-shaped data; the
post-deploy smoke walk is mandatory and owned by the merging session.

The gates themselves were re-examined and kept — the run's seven rejections were
all real money or auth defects. What leaked was deployed-behaviour-on-real-data,
which these rules aim at. Real leak: an acceptance of "never Telegram" was proven
on a supplier that had no Telegram connection; the connected one broke it live.

---

## Opus 5 rework (2026-07-25)

Prompted by Claude Opus 5 shipping on 24 July and by Anthropic's published
context-engineering guidance for Claude 5 models, which reports ~80% of Claude
Code's own system prompt removed with no measurable eval loss.

### What was measured, not assumed

The effort floors this skill carried since 19 July were **decorative**. The `Agent`
tool exposes `model` but no effort parameter, and there were no agent definition
files, so every subagent inherited the session-wide `effortLevel` from
`settings.json`. "Fable @ max" ran at high. `--effort=max` did nothing at all.

Agent definition frontmatter *does* carry effort, which the docs claimed and three
other signals contradicted (no tool parameter, the community validator does not
know the key, and `effort: banana` loads without complaint). Measured on identical
agents differing only in that one line, same task, interleaved runs:

| rung | mean wall-clock | vs default | mean output words |
|---|---|---|---|
| `low` | 40.7s | — | 371 |
| `high` (session default) | 39.7s | baseline | 382 |
| `xhigh` | 48.7s | +23% | 506 |
| `max` | 73.3s | +85% | 476 |

So the usable dial is `high → xhigh → max`. `low` showed no separation from `high`
on this task — probably because enumeration is recall rather than chained
reasoning, but it was not assumed either way.

Model pinning by family works (`model: haiku` reports Haiku). **Version** could not
be established: three runs gave "Opus 4.8", "Opus", and "Claude Opus 4.5", so model
self-report is unusable as evidence. Hence `model: inherit` everywhere plus a
pre-flight assertion that the session is Opus 5 — inheriting a known session beats
trusting an alias whose resolution is unverified.

### Decisions

1. **Fable leaves the runner path.** It was the review gate, both hunt gates, the
   finale and the escalation. Opus 5 now leads Fable on agentic terminal coding,
   agentic search and knowledge work at half the price, which is what those roles
   do. The escalation was then found to be **unrunnable**: Fable is credit-gated
   and the account was exhausted, so a two-strike escalation would have died on an
   API error at the worst possible moment — the third attempt at the hardest issue,
   unattended. A break-glass model that is not there when you break the glass turns
   a hard issue into a dead run. Escalation is now Opus at `max`, a measured +85%.
   Fable stays a deliberate manual choice, not a dependency.
2. **Both gates survive.** Anthropic's guidance to delete verification scaffolding
   targets an agent double-checking *its own* work in *its own* context. These are
   adversarial reviewers of another agent's work in a fresh context, which
   Anthropic's own harness guidance still endorses. The seven money/auth rejections
   are the evidence.
3. **Briefs moved into agent files.** Six agent types, each carrying its own brief,
   model and effort. The runner no longer pastes briefs, so a spawn's prompt is
   only what varies — which also makes the stable part cacheable, at Opus 5's
   512-token minimum prefix.
4. **The Log left the ledger.** The 22 July fix was a rule to prune, and it failed
   25 times out of 25, because the Log lived in the file every spawn reads. The
   ledger is now the status table and Carry-forward only; all log lines go to the
   journal, which subagents never read. The "~2 lines per event" rule and the 15k
   cap are deleted — there is nothing left in the hot path to bloat. Make the bad
   state unrepresentable rather than forbidden.
5. **Gates derive a rubric and grade it.** Each gate turns the acceptance criteria
   into numbered independently checkable statements, writes them into the verdict,
   and marks each pass or fail with cited evidence. **A criterion with no evidence
   is a FAIL** — "I did not see a problem" is not verification, and that is how
   half-finished issues used to pass.
6. **The finale drives seams only.** Its full end-to-end drive duplicated
   per-issue gates locally and was superseded by the mandatory smoke walk on real
   data. Its unique value is the whole-branch diff review plus the surfaces more
   than one issue touched.
7. **Delegation narrowed to reads.** The old "send bulk work to Sonnet subagents"
   was tuned for Opus 4.8, which under-delegated. Opus 5 over-delegates, so the
   instruction became an accelerant pointed at the one-writer worktree rule. Bulk
   reading may be delegated; anything that writes goes to the scratchpad.
8. **Completeness gaps closed.** The runner now reads the implementer's final
   message before spawning gates (it already reported partial work; nobody acted on
   it). Agent files carry an end-of-turn check against ending on a promise, and a
   requirement to ground progress claims against tool results.
9. **A wrong-criteria escape hatch.** A worker concluding the criteria are
   *incorrect* rather than merely unmet stops and says so with evidence; a gate
   confirms; the runner sets `needs-info`. Previously an implementer built to a bad
   spec and both gates graded against the same bad spec, so the run went green and
   the defect surfaced on the human walk.

## Throughput pass (2026-07-25)

Measured the 27-issue settlement batch from its commit timestamps: 01:29 → 23:45
on 23 July, so 22 hours. Median gap between issue commits 20-40 min, giving ~30
min per issue and ~13.5h of steady-state work. Two unexplained stalls around
issue 72 (05:06→09:03, then 09:03→11:14) accounted for ~6h, 27% of the run. The
ledger holds **no halt block** — the run was never usage-limit bound, so the
slowness is the pipeline, not the quota. Of the 15 issues whose journal entries
record an attempt count, 12 passed both gates first time.

**Gates now run concurrently.** They were serialised for no reason: the review
gate reads `primer.md`, the issue and the diff, never the verify verdict, and
verify drives the app. Wall clock per issue becomes the slower gate rather than
the sum. At an 80% first-pass rate, occasionally paying for a review that a verify
rejection discards is the right side of the trade. Both gates therefore write
under their own heading, append-only, and neither may treat the other's verdict as
an input. A double rejection is ONE retry carrying both verdicts and ONE strike.

**Every ledger transition is timestamped.** The 6h of stalls are unexplained only
because nothing recorded when a stage began. Without this, any further throughput
change is guesswork.

**Considered and rejected.** Dropping the review gate to save 15-20%: in that same
batch its routings minted issues 89, 99 and 100, so it buys speed with bugs.
Lowering implementer effort below `xhigh`: at an 80% first-pass rate it purchases
retries, and a retry costs a full implement plus both gates.

**Parked, needs its own grilling.** Two parallel tracks on separate worktrees is
the only remaining change big enough to matter (22h → ~13h). It is unresolved on
three counts: two implementers can edit the same core file, somebody must declare
which issues are genuinely independent, and the finale's one-branch coherence read
gets weaker across two branches.

## Post-run revisions (2026-07-26, after the 112-116 run)

First run on the reworked skill. Both throughput changes held: timestamps landed
at every transition, and on issue 114 the two gates rejected **independently and
from different angles** — the review gate via a differential harness against the
prior commit, the verify gate by reproducing it in the running app on QA data.
Double rejection correctly counted as ONE strike, so escalation fired on attempt
3 rather than attempt 2. Whether concurrency saved wall clock is not established:
five issues of unequal size, no controlled comparison.

**Issue 114 took 3h52m of a 7h run.** Attempts 1 and 2 wasted 2h25m; the
escalated attempt 3 that passed took 1h27m. Three causes, and the fixes for two
of them are in this revision:

1. *The criteria said what to change, never what must not change.* Attempt 1 met
   all four acceptance criteria while dropping the supplier page cap —
   `SUPPLIER_PAGE_SIZE` 24 became the page sequence `[1, 31, 24, 24, 24, 24, 4]`.
   Implementers now name the behaviours their diff sits beside (paging, limits,
   ordering, counts, permissions) and check none was spent to buy a criterion.
   The real fix is invariants at authoring time — still deferred, now priced.
2. *No triage decision settled the road, so the implementer invented one.* 113
   arrived with its road settled: 17 minutes, one attempt. 114 did not: three
   attempts. The runner now settles multi-road issues before spawning.
3. *A false impossibility claim steered two attempts.* Attempt 1 rejected
   ordering the fetch by the normalised key because "PostgREST cannot order by an
   expression" — untrue, unverified, and the same class of error recurred on 116.
   Both implementer briefs now require an impossibility claim to be verified
   against the real thing before it closes a road.

**Considered, not adopted.** A per-issue wall-clock budget that halts and reports
rather than grinding to attempt 3. It would have surfaced 114 at ~1h with both
verdicts in hand, but it trades away unattended completion on genuinely hard
issues. The human's call, not a default.

**Runner error recorded by the run itself:** a scope narrowing sent to a live gate
was read as a cancellation and the gate stood down without a verdict, costing an
independent read. Say "narrowing, not cancelling" explicitly.

## A blocked issue stops its dependents, not the run (2026-07-26)

The skill said "Issues are a dependency chain. Always run in order; never skip
past a blocked one", and halted the whole run on a blocked issue. **That rule had
no entry here** — no incident, no grilling, no measurement. It was asserted early
and inherited ever since, and it was repeated to the human as though settled. They
questioned it; it did not survive the question.

The premise is false for most batches. The 16-issue set queued on 2026-07-26 is
almost entirely independent: a name-length guard on the vouch road (111) has no
relationship to empty labels on the deal page (124). Halting fourteen issues
because a migration hit an unexpected row would have cost most of an unattended
overnight window for nothing.

**Now:** a blocked issue blocks the issues that declare a dependency on it and
nothing else. Dependencies are read from the invocation and from the issue files'
own cross-references, which in practice state them ("run 119 first", "this
assumes the chip fix has landed"). The run halts entirely only when nothing
independent remains.

**It fails safe by construction:** where the runner cannot tell whether a queued
issue depends on the blocked one, it treats it as dependent and skips it. The
original rule's protection — never build on a wrong slice — is kept; what goes is
the assumption that everything is a slice of everything else. Skipped issues are
named in the merge briefing so the next run collects them.

**Not yet exercised.** Changed the evening before a 16-issue unattended run, so
the first real test is that run. If the dependency reading proves unreliable, the
safe direction is to widen what counts as dependent, not to restore the blanket
halt.

### Known residual risk — addressed 2026-07-27

An issue whose acceptance criteria were wrong **when written** is caught late by
decision 9 and not at all by the gates, since every gate grades against the issue.
The early fix now exists: `/harden-issues` (its own skill) attacks criteria at
authoring time — evidence-backed sharpenings applied directly, open forks routed
to the human, a `Hardened:` stamp on resolved issues — and `/to-issues` carries a
rubric-shaped template. This skill's only coupling is the pre-flight stamp check:
launch-time information, never a gate. Grilled and settled 2026-07-27 from two
runs' evidence (112, 114, 110, 117, 122, 124, 125, 126 all shipped criteria
faults through green gates); the design brief lives in the
`acceptance-criteria-hardening` memory file.

## Cost grill (2026-07-27, after the 111-136 batch)

The 14-issue batch of 2026-07-26 cost roughly double its floor (three clean
issues at 28-38 min; everything else 60-300). Grilled and settled with the human.
The evidence lives on `main`: `run.md`, the 1177-line journal, and the merge
briefing under `.scratch/<feature>/`.

**The Opus 5 rework was not one thing.** Thin ledger, cached agent-file briefs
and concurrent gates are keepers. The two cost suspects it introduced were the
effort dial becoming real for the first time, and rubric gates whose
pass-with-findings verdicts spilled into unmodelled correction rounds.

1. **The correction round is a ledger stage, not a reject.** Five issues passed
   both gates and then got more work with no status, no timestamp, no price —
   and the statusless stage caused the two-writer incident (121's round sent
   while 129's correction was still writing). Rejected the alternative of
   all-or-nothing gates: it converts small follow-ups into full retry cycles
   (implement + two fresh gates), inflates strikes toward the max-effort
   escalation, and — the disqualifier — teaches gates that honesty is
   expensive, which corrodes exactly what makes them worth running. The stage
   is capped: one round, verdict-enumerated items only, no new spawn while any
   row shows `correction`, runner verifies the named evidence rather than
   grepping file paths, not a strike. Anything bigger is minted.

2. **Implementer effort drops to `high`; the next batch is the A/B.** xhigh
   never had evidence: the 80% first-pass rate cited for it was measured on the
   23 July batch, which ran at `high` under the decorative floors. xhigh's
   first real outing went 9/14 first-pass while paying a measured +23% on
   every attempt — the only cost in the run that multiplies every issue.
   Confounded in both directions (the gates got stricter in the same commit),
   so the next run buys the evidence. **The judge is the shape of its
   rejections, not the rate:** effort-shaped rejects (sloppiness, missed
   adjacent behaviour, half-done work) argue xhigh back in; criteria-shaped
   rejects (wrong road, wrong spec) indict the issue, not the rung. Escalated
   implementer, finale and critical review stay `max` — rare, and the
   break-glass and once-per-run roles justify it.

3. **No whale circuit breaker; whales run last.** 129's 4h58m decomposed as
   attempt 1 (59m), a 529 killing both gates, a review reject, attempt 2, a
   second gate pair and doc corrections — attempts self-bound at ~1-1.5h, so
   the whale is stages compounding on a genuinely big issue, not a runaway,
   and the three-attempt cap already bounds the worst case. A wall-clock kill
   would have thrown away 129's passing attempt 2. Runner-side splitting
   rejected: untriaged specs, the decision-9 failure mode. Adopted instead:
   size the issue at road-settling and write the estimate in the ledger row;
   schedule big ones last where order and dependencies permit (runs halt on
   usage limits — cheap issues land first); an issue too big to be one issue
   goes back through `/harden-issues`, which owns the split rule.

4. **The verify gate sweeps every route the diff touches.** On 121 a server
   component importing from a `"use client"` module passed both gates — verify
   drove its acceptance path, review read the diff, and opening the other
   pages was nobody's job. Three of five production deal pages rendered a
   21,935-byte error shell until the finale caught it. The sweep is seconds of
   HTTP against a server already running: fetch each touched route, and a 200
   wrapping an error shell is a FAIL. The finale's whole-branch sweep stays as
   backstop.

5. **Mid-run minting stays free, and write-only.** 15 issues minted in a
   14-issue run were real work cheaply captured — 154 alone named a defect
   (62 of 63 fake query builders don't project selected columns) that eight
   consecutive issues had been rediscovering. A cap throws away findings;
   clock accounting changes no behaviour. The rule that keeps it cheap: a mint
   records evidence already in hand, licenses no further investigation
   mid-run, and the merge briefing lists what was minted.

## Max tier cut everywhere but the finale (2026-07-27)

Reverses the last clause of decision 2 above ("Escalated implementer, finale and
critical review stay `max` — rare, and the break-glass and once-per-run roles
justify it"). Settled with the human after a panel review of the whole chain.

**The reason it fell: "rare" was wrong, and the evidence for the tier was earned
at `high`.** Modelled over a 10-issue run through to a hunt, using this file's own
measured multipliers, max ran 15 spawns — 19% of them, taking 30% of the bill, a
premium of ~14% on its own. Against that, neither decisions file records a single
defect max caught that `high` would have missed. The seven money/auth rejections
cited to justify the critical review gate were produced on the 23 July batch, when
the effort floors were decorative and everything ran at session-default `high`.
A tier whose whole case rests on results produced one rung below it is not
evidenced, it is assumed.

`run-issues-implementer-escalated`, `run-issues-review-gate-critical` and
`parallel-hunt-fix-gate-critical` drop to `high`. The `-critical` variants keep
their extra rubric — the money/auth/secrets trace was always the substance; the
tier was the wrapper. `run-issues-finale` stays `max`: once per run, and it is the
one stage with a recorded catch (121's three broken production pages, after both
gates passed).

**The judge, next run:** the shape of what the critical gates miss. A money or
auth defect reaching the merge read argues the tier back in. Slower or shallower
verdicts that still catch the defect do not.

Not adopted here, and still open: routing strike 2 to a criteria re-check instead
of the escalated implementer. Every documented cause of an expensive failure in
this file is upstream of the implementer — a missing invariant, an unsettled road,
an unverified premise — so the escalation path is better attacked at its cause
than at its price. That is a behaviour change, not a frontmatter edit.

## Strike 2 re-checks the spec before buying a third implementer (2026-07-27)

Escalation assumed the implementer was the weak link. The record does not support
that. 114 failed on criteria that omitted the invariant, an unsettled road and a
false impossibility claim; 122 spent two attempts down a road falsified by an
unverified premise. In both, a cleverer implementer was being asked to satisfy
criteria that were themselves wrong — and both gates grade against those same
criteria, so the good outcome (rejection) and the bad one (a correctly-built
defect shipping) are equally available.

The escalated implementer's own brief already carries the check: "if you conclude
the issue itself is wrong … say so with concrete evidence instead of forcing a
third bad implementation." That check now runs *before* the attempt, for 1.0 unit,
instead of after it for 3.0.

**Honest accounting: this costs more, not less.** One attacker spawn is +1.0 unit
on every second strike, because the escalation may still be needed. What it buys
is that the 3.0 stops being spent on an attempt that could not have worked.
Break-even is one spec-caused failure in three; the two multi-attempt disasters on
record were both spec-caused.

**Strike-2 mode is narrower than a normal hardening pass:** classes 1, 5 and 9
only, evidence or silence, and it never waits. A fork it cannot settle returns
`criteria-open`, the issue goes `blocked (criteria)`, and the run carries on. A
question mid-run is a blocked issue, never a stall — no run stops for a human
between launch and the merge read.

**Named exception to the hardening guard.** `/harden-issues` otherwise refuses to
touch an issue a run holds, because a second writer rewriting criteria under a
live implementer causes a rejection on correct work. Strike-2 is the one carve-out
and is safe for a stated reason, not by luck: the run has stopped, the implementer
is dead, and the runner spawns nothing else until the attacker returns. Written
into both files so the next reader does not find two rules contradicting.

**The judge, next run:** how the three verdicts split. Mostly `criteria-sound`
means the re-check is a tax and escalation was right; `criteria-fault` at any real
rate pays for the whole change.

## Provisional stamping: a pending question never removes an issue (2026-07-27)

Amends the same-day decision that `all` takes only stamped issues. That rule, plus
`/harden-issues`' "no stamp while a question is open", had a failure nobody would
see: one deferred question drops an issue out of every future `all` run,
permanently, while the file looks healthy. It also meant that today — with no
issue yet stamped, because the pass had no agent files until this session — `all`
resolved to an empty list.

**Default-and-decay.** Every question the pass raises now ships with its
recommended answer, marked `[reversible]` or `[irreversible]`. Unanswered
reversible questions take the default, the default is written into the file as a
default rather than a decision, and the issue is stamped
`Hardened (provisional): <date> — <n> sharpened, <m> defaults pending`. Provisional
counts as stamped for `all`. The merge briefing names every issue that shipped
provisional, with its pending question, so the answer lands after the run.

Two things never default: an `[irreversible]` question — a migration's direction,
a money or auth rule, anything that ships data — and a split, which stays the human's
alone. Both leave the issue unstamped and out of `all`.

*Superseded 2026-08-29: `~/.claude/questionrules.md`'s routing table now governs.
A split the hardening session can cut, harden and stamp itself no longer waits,
and the `[irreversible]` mark is confined to that table's four classes.*

The standing constraint this serves, stated by the human on 2026-07-27: **no run stops
mid-flight for their input.** Anything needing them is a blocked issue, a default
taken, or a line in the merge briefing — never a wait.

**`needs-info` becomes `needs-harden`.** The old status was terminal here: triage's
return path is "returns to `needs-triage` once the reporter replies", and a
`.scratch/` issue file has no reporter. Both places a run sets it — a superseded
issue at scope resolution, and criteria a worker proved wrong — now set
`needs-harden`, which `/harden-issues` takes as in-scope. The status now names the
thing that clears it.

**An empty `all` scope halts and says so**, rather than reporting a completed run
over no work.

## Default-and-decay across the whole chain (2026-07-27)

Extends the same-day provisional-stamping decision to `/to-prd`, `/to-issues` and
`/triage`, so the standing constraint holds everywhere and not just in one skill.

**The audit that prompted it.** A chain day on a ~14-issue batch demanded roughly
3h38m of the human's time. Of that, 45-55 min was irreversible judgement — the merge
read, merge and deploy, run scope, pending secrets. The rest was blocking loops:
`/to-issues` "iterate until the user approves", `/triage` step 2 "wait for
direction" and its one-question-at-a-time grilling, `/to-prd` "check with the user
that these seams match". None of those decisions needed them; they needed a written
rule and a default.

**The rule, now in all four skills.** Every question carries the pass's
recommended answer and a `[reversible]` / `[irreversible]` mark. Reversible
questions apply their default, record it in the file as a default rather than a
decision, and queue to `.scratch/decisions-queue.md`. Only irreversible ones wait.
Irreversible means: a split, a `wontfix` close, a write to `.out-of-scope/`, a
transition on an issue a run holds, a migration's direction, a money or auth rule,
anything that ships data or commits a public contract.

*Superseded 2026-08-25/29: the list is now `~/.claude/questionrules.md`'s four
rows — architectural change; deleting production rows or a migration's direction;
money or authentication; shipping data or a public contract. Splits route by its
table; triage's three waiting outcomes stand on their own rule, without the mark.*

**Write before you ask, everywhere.** `/to-prd` writes the PRD to disk before
publishing; `/to-issues` writes slice files before the harden pass and the quiz;
`/triage` writes its recommendation and its grilling findings into the issue as
they land. Every one of those previously lived only in a session context, so an
abandoned or rate-limited session lost the whole artefact with no record it had
been attempted.

**Grilling is now conditional on there being someone to grill.** `/triage` runs
`/grilling` only where a real reporter exists. Against a local `.scratch/` issue
file the loop cannot terminate — nobody answers — so it routes to `needs-harden`
instead. This is the same root cause as the `needs-info` dead end: triage is an
upstream skill written for a public tracker with reporters, used here on files
that have none.

**`Status:` is now the first line of the issue template.** Without it the stamp
had nowhere to land and `/run-issues` could not resolve scope — the contract was
asserted by three skills and provided by none.

Still open: whether `/triage` belongs in this chain at all, and which tracker is
canonical (`/to-issues` publishes to a real tracker; everything downstream appends
`##` headings to files). Both in `panel-review-2026-07-27.md`, section E.

## /daily-brief owns the human loop (2026-07-27)

The last piece of the 30-minute design. Every skill in the chain now defaults and
queues instead of asking; `/daily-brief` is where those queues become one file
The human reads once a day, and where their answers become writes.

**It closes three resting states this file already recorded as dead ends.**
`awaiting-merge` had no owner, no expiry and no reminder — an unmerged branch had
no clock on it anywhere. The pending-actions file was written to and never read
back. Queued defaults surfaced only in a merge briefing, so answers scattered
across runs. All three now have one reader on a schedule.

**The brief is a view, not a store.** Regenerated from source every firing,
authoritative only between being written and being applied. The chain's own rule
against second copies applies to it more than to anything else, because it is the
one artefact whose whole job is to duplicate state.

**The merge hazard, and the fix.** `merge` written into a file is an approval made
hours before the machine acts. The branch can move in between, and the human would be
merging a diff they never read. So every merge block carries the branch head SHA it
was written against; at apply time a differing SHA means no merge, rebuild the
block against the new diff, mark it `changed since you read it`. **A stale
approval is not an approval.** This is what makes "main belongs to the human" survive
an asynchronous decision.

**Apply runs before rebuild**, so a collation never overwrites an answer. And the
apply half re-reads `run.md` before touching any issue, skipping anything a run
holds — the same guard `/harden-issues` carries, whose only carve-out is strike-2
mode.

Not adopted: having the brief decide anything. Every item in it already has a
default that has already taken effect. The brief exists so the human can overturn a
default, never so the machine can ask them a question.

## /daily-brief runs by hand, not on a schedule (2026-07-27)

Reverses the same-day intention to schedule it. `/schedule` creates **cloud**
routines, and a cloud routine cannot do this job: it runs in a sandboxed checkout,
cannot read `~/.claude/`, cannot write `brief.md` back to the machine, and cannot
see an unpushed feature branch. Since a run commits per issue and never pushes, and
mid-run ledger state lives on the unmerged branch, a 6pm cloud firing would collate
yesterday's `main` and present it as today. **A brief that looks current and is not
is worse than no brief.**

A local wakeup would see everything, but the argument for it collapsed once stated
plainly: the only thing a timer buys is that the brief is already built when they
open it — about a minute. Every other benefit assumed they were absent, and the whole
design has them present for thirty minutes a day. The one real argument, that a
stale-dated brief signals a broken machine, does not apply when they are the one
invoking it.

So: bare `/daily-brief`, once a day. Apply then rebuild, in that order, from one
command. If the collation wait ever becomes annoying, a local wakeup is a small
addition — built then, on evidence, not now on a guess.

`.scratch/` is tracked in the repo this was measured on (255 files; only
`.scratch/documents/` is ignored), so the content a cloud agent would need does
exist in git. Freshness and write-back are what fail, not availability. Worth
knowing if the brief is ever moved into the repo to make a cloud routine viable.

## The five forks from the 2026-07-27 panel, taken by the human (2026-07-27)

All five put to the human in one sitting and answered; none is a default.

**The chain ships publicly minus the Pocock forks.** `harden-issues` and
`daily-brief` join the published pack; `to-prd` and `to-issues` stay private
because they are modified copies of Matt Pocock's skills and republishing them is
an attribution question nobody has answered. Every published reference to them
becomes a conditional. The pack's story is now: issues arrive however you make
them; the pack takes over at hardening.

**`/triage` leaves the chain but the skill survives.** It was built for a public
tracker with reporters. Against `.scratch/` files there is no reporter, so its
wait-for-direction and grilling loops were dead ends dressed as diligence. Bug
reports now enter at `/harden-issues` or as a direct issue file. The skill keeps
existing for any repo that grows a real tracker with outside reporters — deleted
from the chain, not from disk.

**`.scratch/` files are the canonical tracker.** Every downstream skill appends
`##` headings to issue files — harden stamps, status lines, deferred entries — and
a GitHub issue body cannot carry that. `/to-issues` now writes files as the
record; a tracker mirror, if ever wanted, is a read-only view added later. This
settles C12 the way the chain already behaves.

**The reuse rule is approved verbatim** and lives in coderules under "Reuse
approved patterns, not unreviewed precedent". The lint half shipped with it:
`jsx-a11y/anchor-is-valid` and `no-static-element-interactions` at `error`, plus
`docs/patterns.md` seeded with the button/anchor entry. One correction to the
redesign doc's claim: the repo measured does **not** have `eslint-config-next`
— its lint config is deliberately standalone — so the rules needed
`eslint-plugin-jsx-a11y` as a new dev dependency, on the same
never-runs-in-production ground the ESLint dependency was agreed on.

**`/harden-issues` gets its own `decisions.md`**, same pattern as this file and
parallel-hunt's. Provenance moves out of the hot SKILL.md, which is billed on
every invocation.

Judge for the sync decision: if the published pack draws a question about where
issues come from, that is the signal to either write the attribution and ship the
Pocock forks, or add a small "authoring issues" note — not to quietly re-add the
references.

## Ledger discovery, pruning and the owner line (2026-07-27, after the 155-157 run)

Four findings from the first run to exercise the reworked chain. All four are
ledger-shaped, and none was caught by the panel: the panel read the skill, and
these only appear when you read a real run's artefacts against it.

**The ledger's own rule had no teeth, and the ledger broke it.** `run.md` reached
15,443 bytes. The status table was 13% of it. Halt blocks were 27% (1,788 bytes of
which the file itself labelled *superseded* and kept anyway) and finale narrative
was 20%. Every implementer and gate reads this file, so the ~7 KB that the skill's
own "nothing else belongs in it" excludes was billed roughly a dozen times in one
run. Fix: name what gets moved out and when, and give it a checkable threshold
(status table plus Carry-forward under half the file → prune). Cost is modest,
maybe 20k tokens a run; it is in because it is free to fix and it compounds.

**"Which ledger" is the expensive one — 25 measured minutes.** The journal
diagnosed it and wrote the fix; nothing implemented it, so it was still live. The
sharper version, found by running the enumeration: the ambiguity is not many runs,
it is **one run with many copies**. Run state is committed, so every worktree
branched from that commit carries a frozen snapshot. Twelve `run.md` copies existed
on 2026-07-27 and six carried an identical live-looking owner line. The
discriminator was already in the format and unused: the `Worktree:` line written at
launch. The real copy is the one whose `Worktree:` names the tree it sits in; every
other is a snapshot to read never, write never.

**The owner line is never cleared.** All six live-looking copies belonged to a run
that was finished, PR open, `awaiting-merge` — with `Owner: session e43e10be,
heartbeat 14:55` still at the top hours later. That is indistinguishable from a run
that died mid-flight, which is exactly the state the heartbeat exists to detect,
and it is what the cron keys off. Reaching `awaiting-merge` or halting now rewrites
the line to `Owner: none — …`.

**Every command handed to a human runs once first.** The briefing's step one was a
reconciliation query naming the column migration 0075 adds, presented as a
*pre*-migration check. It cannot run pre-migration. Written by a gate, copied to
the board by the runner, executed by neither, and it failed in the human's hands with
`42703` under a heading saying the order was not negotiable. This is the run's own
central finding one level up: a criterion naming a test as a tripwire has not
proved it is one; an instruction naming a check as a safety step has not proved it
runs. A check that errors is worse than none — it reads as diligence and fails at
the moment someone is about to touch production.

**Judge for the next run:** does the ledger stay under the half threshold without
the runner being reminded, and does a `resume` with no range land on the right
ledger first try. If the enumeration command is run and the answer is still wrong,
the discriminator is wrong, not the discipline.

**Not changed, deliberately.** Gates were 43% of the modelled bill and 104 of the
run's 181 working minutes, against 77 for implementation. They are not the waste:
this run had zero strikes, three first-pass gates, and the verify gates caught the
wedged QA state, a fil-exact money reproduction, and two surviving mutations in
157. The cost grill already ruled the concurrent gates are not the driver. Left
alone.

## Second panel: cost, autonomy, enforcement (2026-07-27, run on Fable)

Five personas over this skill plus the agent briefs, with the 155-157 artefacts
as evidence. Full map in `panel-review-2026-07-27-cost.md`. What changed and why,
compressed:

**Enforcement over prose.** The ledger rules were right and the live ledger broke
three of them. Pruning now fires at the two existing transitions (halt write, row
to done) on two mechanical triggers (>1 HALT BLOCK heading; table+Carry-forward
under half the file). Carry-forward entries name their consumer and die with it.
Correction rounds get open/close stamps.

**Authors enforce the run-commands-first rule.** The 42703 rule lived only in the
runner's file; the gates who write the commands never saw it. Now: gates run any
human-bound command once (read-only) or mark it UNRUN; the finale re-runs all of
them and ships nothing UNRUN.

**Pre-flight grew three checks, all launch-time:** dry-run the allowlist (the old
text asserted coverage; settings.json refuted it), probe QA fixture health
read-only (156's verify paid 55 min for that discovery at gate prices), and echo
the launch line on every invocation (the 11.5-hour halt was a misread request).
Model check gained its remedy: non-Opus runner passes model: opus explicitly.

**Recurring token cuts:** board.html rendered by a fresh cheap subagent, never
the runner at end-of-run context; worker finals capped (implementer 15 lines,
gates 3); cron predicate is one grep, not a ledger read; primer appends one line
per fact; routing verified by exact quoted line, not heading.

**Autonomy:** classifier refusal = closed road (unprivileged path or report
blocked, never retry) — was invented mid-run and buried in the 155-157 ledger,
now standing in the worker briefs; ambiguous resume prefers the invocation's
range then stops at launch, never mid-run; run-close standing-directive question
goes to the Decisions inbox, not chat.

**Rejected, with reasons:** resume.md split (400 tokens once vs re-creating the
25-min wrong-file class through indirection); moving the attacker's nine
per-class anchors (they are rule+number, the settled hot-file format, not
stories); watchdog kill-and-respawn on suspected prompt stalls (heuristic kill
risks the two-writer incident).

**Net: SKILL.md +1.5 KB** (stories out, rules in) — paid once per session,
against per-run recurring savings (board ~10k tokens, finals ~5k+, Carry-forward
expiry O(n²)-shaped, ~15-25 min prep-during-gates, ~20-30 min QA probe when it
fires). Judge next run: runner glue under ~30 min, no gate paying for
environmental discovery, no human-bound command failing in the human's hands.

---

## 2026-07-28 — prose rejections are fixed by deletion, not refinement (run 154-181)

**The incident.** Issue 181 passed both gates on every acceptance criterion, and
its implementer had VOLUNTEERED an extra meta-test beyond the criteria. The test
was sound; a comment describing it over-claimed. Three sequential narrow review
gates, ~300k subagent tokens, went on that comment. Each gate was RIGHT and each
found a real, driven error — round 1 named `String.prototype.replace`/`split` as
regex compilers (they match literally), round 2's replacement umbrella sentence
was false of its own first route.

**The mechanism, which is the general lesson.** Round 1 correctly deleted the
false universal ("unrepresentable") and, in the SAME edit, added a list of routes
around the check. That addition is a new positive claim with its own falsifiable
surface — so the fix for an over-claim was itself an over-claim, twice. On this
class, *more precise* and *more likely wrong* move together.

**The rule.** A gate rejection on NON-EXECUTABLE prose is fixed by deleting the
claim, not restating it. One round. If a second rejection lands, the edit is
deletion down to the minimal sentence the gate cannot falsify, and the detail
becomes an issue with tests. Re-assertion is permitted only when the claim
becomes executable — a test cannot over-claim.

**The predictor nobody read.** The same over-claim class had already rejected
FOUR earlier attempts on that issue. The base rate for "a new prose claim about
this mechanism survives the gate" was 0 for 5 when the runner priced the fix as
a four-line edit. Corollary rule: **any fix in a class with two or more prior
rejections is delete-only.** Check the strike record before pricing a fix.

**Two cheaper defects underneath it.** (a) The same claim had been copied into
the code comment, the primer and the issue file — four surfaces, so four edits
per correction and a 4x gate cost. One canonical statement; everywhere else
cites `file:line` and asserts nothing. (b) Claims about LANGUAGE SEMANTICS were
argued across three rounds when a node REPL settles them in thirty seconds. Drive
a language claim before writing it down.

**Not the lesson: that the hold was wrong.** Panel-reviewed 2026-07-28, six
personas, unanimous "right call, wrong execution". Holding cost nothing — no
migration in flight, no second writer in the branch, and merging is the human's
manual step anyway. The rounds cost; the hold did not.

## Panel over run 154-181: cap the resets, mtime staleness, runner errors refund (2026-07-28)

Five personas over the run and the uncommitted skill diff — run economist, skill
maintainer, gate designer, implementer's advocate, auditor of the human's minute.
Full map in `panel-review-2026-07-28-run-154-181.md`, next to this file. Votes:
commit the diff with trims (3-2 over as-is; nobody voted revert), and the
prose-deletion rule stays — trimmed, and mirrored into the agent briefs that
actually type and grade prose, which never read SKILL.md step 5.

The run's shape, for the record: six issues 49% under estimate (~351 min against
690), three at zero strikes; 181 alone ~339 min — 7 attempts (61 min of
implementation), 14 gate runs (~160 min), 3 re-checks, plus a ~105-min evening
resolution. Every rejection individually correct; the loss was structural.

What changed, compressed:

- **Two criteria-fault resets maximum per issue.** Each reset was lawful and
  together they were unbounded — the skill promises three attempts and 181 got
  seven. The runner invented the cap mid-loop ("stated in advance so it cannot
  drift"); now it is written into step 8. Rejection classes are counted across
  resets — strikes reset, the class ledger does not.
- **Staleness keyed on the ledger file's mtime.** The handwritten
  `heartbeat <HH:MM>` failed twice in the very run cited as its evidence (10:31,
  15:47), on a runner who had already diagnosed the failure mode — knowing about
  a memory-enforced rule does not enforce it. Every transition updates mtime and
  nobody can forget to write it. The dangerous direction was a cron resuming
  into a live tree: the two-writer incident by another door.
- **Runner errors refund strikes.** Attempt 5's strike stood on the ledger's own
  "RUNNER ERROR" — a claimed shape mis-sorted onto the not-yours list, so the
  implementer was told to skip work that was in scope. A rejection ground
  attributable to the runner's brief is annulled from the strike and journalled;
  the symmetry criteria-fault already grants for spec fault. Not-yours items now
  cite the line that excludes them — a gate's summary sentence is not a warrant.
- **Gate-side prose rubric.** The delete-only rule was runner-only; the gates
  that priced three restatement rounds never saw it, and the final round split
  on severity, not fact. Both gate briefs now grade beyond-criteria prose
  non-blocking (unless a criterion names it or the artefact's purpose IS the
  claim — a guard's contract still blocks), enumerate every contradiction per
  round, name the defect class so repeats can be counted, and recommend
  deletion, never restatement.
- **Tenancy-empirical and prove-on-disk moved from run lore to the briefs.**
  Both bit twice: a review gate cleared a live cross-tenant leak by generalising
  a composite-FK trace onto a read no pin covered (180), and six distinct
  false-green mechanisms in one run (stale vitest cache, no-op patches, silent
  reverts) burned both 200 gates. A tenancy claim is settled by deleting the
  predicate and running the suite; a mutation is trusted only after the cache is
  cleared and the mutated line echoed.
- **Blocked handoffs stop sizing prose fixes in lines.** "Fix is two prose
  lines" — against a class with a 0-for-5 survival record — became four sites in
  three files and an evening. The finale corrected the count; the panel added
  the rule: state the strike-class record, present merge-now-fix-later beside
  fix-first with costs, and resolution is a procedure (one word from the human, one
  implementer, one narrow gate, unattended), not a supervised evening.
- **Prose-graded criteria flagged at authoring time** (step 1 + the attacker's
  class 8): a bar the gates grade by reading prose regenerates on every fix,
  because each edit mints a new falsifiable claim. This, more than difficulty,
  separated 181 from its six clean siblings, whose bars were mutations, query
  counts and byte-identical captures.

Confirmed by the run, unchanged: the strike-2 re-check (three firings, two real
criteria-faults, one disciplined criteria-sound — best ROI in the file); the
max→high tier cut (nothing money- or auth-shaped reached the merge read; what
saved 180 was gate redundancy plus the runner driving the dispute, not a tier);
concurrent gates; ledger discovery by `Worktree:` line (right ledger among 17
copies, first try).

**Judges, next run:** no issue exceeds two criteria-fault resets; zero
false-stale or missed-stale wakeups on the mtime predicate; a prose rejection,
if one recurs, closes in one delete-only round; no strike stands on a ground the
runner's own brief mis-sorted; the merge briefing opens with this run's header
only and reads in under thirty minutes.

## Inherit means inherit: the non-Opus override removed (2026-08-01)

Reverses "Model check gained its remedy: non-Opus runner passes model: opus
explicitly" (`:658`, from the 2026-07-27 second panel). Found by three personas
independently in the 2026-08-01 cost panel, confirmed by its gate, and reversed
at the human's instruction.

**What the rule said.** "The session model is Opus 5. Agent files use
`model: inherit`, so every worker inherits it. If the runner session is not
Opus, pass `model: opus` explicitly on every spawn — never ask, never proceed on
inherit from a non-Opus runner."

**Three defects, in order of size.**

1. **It made the model dial unreachable.** The Agent tool's `model` parameter
   "takes precedence over the agent definition's model frontmatter". So on any
   non-Opus session the rule overrode every per-stage `model:` value in every
   agent file. Nobody could test Sonnet on one stage, or on all of them, without
   first finding this line. The human assumed for months that launching on Sonnet
   gave them Sonnet workers. It would have given them a Sonnet runner driving Opus
   workers, at a higher bill than either.
2. **Its premise was already false.** "The session model is Opus 5" —
   `harden-issues-attacker.md:4` has read `model: fable` since it was written,
   and `SKILL.md`'s own who-runs-what table says each role carries "its own
   brief, model and effort".
3. **It overrode a deliberate pin.** "Every spawn" includes the Fable one. The
   author did not contemplate that case, and the rule as written breaks a stage
   whose tier was chosen on purpose.

**Never fired.** Every recorded run launched on Opus, so the branch was never
taken. Untested text that would have taken effect the first time the human tried the
experiment they were already planning.

**What replaced it.** Workers inherit; a spawn never carries a `model:`
override. The anti-silent-degradation intent survives, moved from force to
visibility: the launch line now prints the resolved session model inside the
existing interrupt window, and the ledger owner line plus the merge briefing
carry it so verdicts are read against the tier that produced them. The autonomy
intent survives untouched — still never ask, still never stall.

**Why visibility beats forcing.** Forcing bought protection against an accident
nobody has had, and paid for it by making a deliberate change impossible. One
printed word costs nothing and blocks the accident just as well, because the
launch line already exists and is already an interrupt window.

**The judge, next run:** whether the launch line's model word is actually
printed. If a runner omits it, the guard has become prose and the rule needs a
mechanical trigger, the way ledger pruning did.

## Post-run revisions (2026-08-02, after the 208/174/184/186/202 run)

Three rules promoted from that run's decisions inbox, plus one pre-flight check.
Gates drill mutations on scratchpad copies, with one tree writer at most while
gates run and checksums re-checked at staging. A published checksum is
re-stamped whenever a later round moves its file, and diff commands anchor to
`main...HEAD`. A figure or refutation passed onward is re-derived from a source
that cannot drift, with the source named. Pre-flight confirms `node_modules`
exists before trusting any green.

**The two-writer incident.** During 186's gates, `widget.js` on disk silently
reverted to its pre-fix form — guard absent, 478 lines — for over two minutes,
then restored itself. Both gates saw it independently. The verify gate's own
mutation drill was the writer; the review gate's backup, taken inside that
window, captured the mutant, so "restore from my backup" would have shipped the
defect the issue existed to fix. A checksum re-checked at staging time caught
it. The 202 gates then ran the new way — verify drilling on scratchpad copies,
review never writing — and the tree file held one checksum from gate open to
gate close. The old text said gates "touch no code" while requiring mutation
drills; the drills were the code-touching. Both statements could not stand, so
the drills moved off the tree.

**The expired-checksum incident.** Both 202 gates published staging checksums
for `client-boundary.test.ts`. A correction round at 08:44 then added a fixture
table to the same file. A merge reader running either command got FAILED — the
precise alarm the gates wrote them to raise, with nothing wrong. The finale
caught it and re-stamped, but only because the analysis pass looked; the rule
makes the re-stamp part of the correction round itself. Same class: a
`git diff --numstat` handed to the human printed nothing after commit, and
empty was also what a reverted-and-committed fix would print.

**The drifting-number incidents, three in one run.** A figure transcribed into
a retry brief unchecked (4,687,680 for 4,688,640 — the implementer caught it);
a causal refutation asserted from a grep scoped to `src/app` when the call sat
one import away in `src/lib` (the conclusion survived on the gate's reasoning,
not the runner's); hand-written journal timestamps that ran an hour ahead and
were corrected against `git log`. None was charged to an implementer; all
three were the runner deriving from its own earlier statements.

**The false-green launch.** The worktree shipped without `node_modules` and
`npm run typecheck` exited 0 anyway — `tsc` resolved off a global install with
no repo types loaded. Caught at launch because the runner ran `npm ci` on
principle. Now a named pre-flight check rather than a habit.

**The judge, next run:** whether the gates' recorded open/close checksums
actually appear in their verdicts, and whether the runner re-checks them at
staging. If either half goes missing, the rule has become prose and wants a
mechanical trigger, the way ledger pruning did.

## Post-run revisions (2026-08-03, after the 207/182/183/185 run)

The human took two of the three candidates the finale left in the decisions inbox.
Both are now in SKILL.md step 5, beside the prose-deletion rule they extend: a
claim may not say something is the only copy, and a recorded cause is tested
against a control rather than merely observed. They declined the third in its
prose form.

**The run's shape, which is why these two exist.** Four issues, ten gate runs,
one rejection (annulled as a criteria fault), zero strikes standing, 52% under
the estimate. And **ten stale-prose defects against zero code defects that
reached a gate uncaught.** Every one was a sentence true when written and false
once something else moved. That ratio, not the schedule, is what the run
measured.

**The only-copy incident.** The primer carried an inverted jsonb claim. The
runner deleted it and wrote, in its place, that issue 201's file was now the
sole home of the measured record. Three other copies existed. The repair for a
stale-prose defect was itself a stale-prose defect of the same class, written
by an agent that was following the deletion rule correctly. That is the whole
argument for the new rule: deletion tells an agent what to remove and says
nothing about what the replacement may assert.

**The observed-cause incident.** A scratchpad `.mjs` could not `import pg`. It
worked when run from the worktree root, so the primer recorded the cwd as the
cause. The real cause was a `node_modules` symlink; the import succeeds from
any directory holding one. The line also existed to correct a previous primer's
wrong cause, which is where a wrong cause costs the most.

**The third candidate, declined in this form.** "A correction round re-stamps or
expires every checksum it invalidates before it closes" is ALREADY promoted —
2026-08-02, from the 202 run — and 183's correction round broke it anyway.
The human's ruling is that a rule which has now failed after promotion does not want
restating. The finale's mechanical form goes to the architecture session
instead: publish every checksum as a command a human can run (`shasum -a 256
-c` against a stamped file), not a digest a human must trust. It fails loudly
the moment a correction round moves anything, and it would have caught all ten
of this run's defects rather than one.

**A placement finding, not yet acted on.** The existing checksum-expiry rule
sits in the Finale section (SKILL.md step 2 of the finale), not in step 5 where
a correction round is actually closed. A runner reading step 5 to close a round
never meets it. Whether the mechanical form supersedes the placement question,
or the rule should also move, is for the architecture session.

**The judge, next run:** whether stale-prose defects fall below ten with two
more prose rules in place. If they do not, prose rules are not the instrument
and the mechanical form should be bought without further evidence.

---

## Run 209-215 (2026-08-03) — seven rules, adopted by the human on 2026-08-04

Thirteen issues, one strike and it was annulled on a criteria fault, twelve
issues minted. Every rule below was written by something that went wrong in that
run, and each is now in `SKILL.md` or an agent file rather than only here.

**1. Gates drill in a private whole-tree copy, at a path naming the issue and
the role.** Two collisions in one day. Issue 210's gates both chose the
scratchpad name `drill`, and one gate's `rm -rf` destroyed the other's copy
mid-run. Issue 211's gates then collided inside the run's own tree, where one
briefly read the other's live mutant. The second case is the reason a naming
rule beats a detection rule: checksums at gate open and close cannot see it,
because the file is restored before either stamp is taken. In
`run-issues-verify-gate.md` and `run-issues-review-gate.md`.

**2. Never `git checkout -- <path>` on a branch with uncommitted work.** It
restores from `HEAD`, where the implementer's work is not. Issue 219's
implementer used it to undo a drill and deleted its own uncommitted work
instead. The repair is a scratchpad copy taken before the mutation. In the
implementer and both gate files.

**3. Implementers never self-commit; the runner commits after both gates pass.**
Two of the first three implementers on this run committed before the gates
opened. Neither caused harm, which is exactly the trap — a self-commit silently
changes what "the diff" means to a gate already reading one, and the runner then
has to hand out explicit commit ranges. Where it has already happened, record it
and give the gates the range rather than reverting. In `SKILL.md` step 4 and the
implementer file.

**4. A ruling that creates work gets its issue number in the same sitting.**
The human ruled question 3 of issue 213 by splitting a road out of scope. Nine hours
later no issue existed and the only trace was one phrase inside 213's own file.
A verify gate happened to notice; it became 234. Nothing was watching for it. A
ruling with no artefact cannot be told apart from a ruling nobody made. In
`SKILL.md`, "Nothing finishes vaguely".

**5. Facts carried into spawns are re-derived from source at pre-flight, with a
citation.** The batch plan said `current_workspace()` "answers null when the
count is not one". It orders memberships by `created_at` and returns the OLDEST,
answering null only at zero. The runner repeated the false version for nine
hours before a gate refuted it from `0011_workspaces_rls.sql:115-126`. The two
versions fail in opposite directions — the false one predicts a loud break, the
true one a silent misfile — so the error stayed invisible while it did damage.
In `SKILL.md`, Pre-flight.

**6. Every citation carries its repo-relative path in full, every time.** A
cross-session sweep found nine ambiguous citations across six issues. The worst
used a bare `review.ts` eleven times where the tree holds two files by that
name; the wrong one resolves to plausible code, so the reader finds a defect
that is not there and an implementer can lose a strike to it. Now the third of
the claim rules in `SKILL.md` step 5.

**7. The briefing's narrative sections are filled as each issue closes.** Four
sections were still empty placeholders when the finale opened the file,
including the one that should have carried the WhatsApp deploy step — the single
action in the batch that changed what a customer reads. A reader starting at the
top met a stale test count before reaching its correction 100 lines down. An
empty section reads as "nothing to report". In `SKILL.md`, run state.

**What this run also proves about the strike-2 re-check.** Issue 210 was
rejected twice by both gates. The criteria re-check found the bar it failed on
had never been written — both attempts met every criterion as written — and
annulled both strikes. It also refuted the runner's own hypothesis about the
fix. The re-check earns its cost.

## From the 310, 309, 308a, 308b run — 2026-08-11

**A correction round searches the branch for a twin of every claim it deletes.**
Four over-claiming sentences were deleted across the four issues of this run, and
a fifth reached main. The one that escaped was the same sentence as one that had
just been deleted, sitting one directory away in the route the test guarded. No
gate reads two files for one claim, and no gate reads two issues at all, so the
second copy had nobody looking at it. Every one of the five was found by a person
or a gate reading prose against code; no test caught any of them.

The human adopted this narrowly on 2026-08-11 and adopted nothing wider. They rejected
an authoring-time rule on the ground that the four caught instances cost about two
minutes each and no strike, so a rule charging attention on every comment in every
issue would be the more expensive mistake. In `SKILL.md`, step 5, under the
delete-only prose rule.

## Small-issue coalescing is retired — 2026-08-15

**The permission is gone from `SKILL.md`. Do not bring it back without new
evidence, and the evidence would have to be a batch, not an argument.**

What it was: up to two adjacent trivial issues (copy, config, no logic) could
share one implementer spawn and one combined gate spawn. It was in the skill from
the day it was written and it never once fired in the repo it was built for.

On 2026-08-12, ticket 29 of the pilot-delivery map asked for two runs to record
the decision, then a ruling. **Four runs recorded it and the count never reached
two.** 322-324, 328-332 and 327a-327b on 2026-08-13, and 325b on 2026-08-14. Two
of them independently call themselves "run one of the two"
(`merge-briefing-prev-run-322-324.md:155`, `merge-briefing-prev-run-327a-327b.md:201`
and `:625`); none calls itself run two. Nothing durable held the count, so each
run re-derived "run one" from the ticket text. That is the human's own three-class
test failing in the wild: the instruction asked an agent to remember a total
across sessions, and remembering does not work.

What the four runs did show, which is why they answered the substance instead of
building the counter: **a qualifying pair existed twice and qualified zero
times**, always because at least one issue in the batch carried logic. The
347/263 run of 2026-08-15 had the cleanest pair yet — issue 347 is one `if`, some
cases and an `.env.example` block — and it failed on issue 263, a thirteen-file
whale.

The mechanism that starves it is structural and postdates it: **the direct road**,
adopted 2026-08-12, takes exactly that class of work, so trivial issues no longer
queue for a run at all. The permission was neither useless nor unread. It was
unreachable.

The fact that would reopen it: a real batch of pure copy or configuration fixes
reaching `/run-issues`. Some still can, because the direct road needs an issue
naming a test that fails today and a pure copy change often has none. If such a
batch appears, the cheap answer is Road B — make the count durable — not a fresh
permission written from memory.

## The class-(a) slim — evidence moved out of SKILL.md (2026-08-23)

The panel review of 2026-08-22 walked `SKILL.md` for passages that are pure
history and mapped them. Eighteen of them moved here on 2026-08-23. Every rule
they illustrated stayed in the skill, and `test_skill_structure.py` asserts both
halves: the anchor still loaded, the story no longer loaded.

Read this section when you want to know why a rule is worded the way it is. Do
not read it to run anything.

**The full suite runs without the canonical env file.** Sourcing it cost the
328-332 run three red suites in one night, each investigated as a regression and
each caused by nothing. It had never been written down anywhere in this repo or
these skills, which is why three agents in one run each discovered it the hard
way.

**The round header, and why it is a block rather than a rule.** The rule that a
brief names the place and not only the act failed a third time in the `dc132b`
run of 2026-08-16. Three faults, one shape, and none of them a prohibition: a
brief said to drive a production build in a browser and named no harness, so the
implementer picked the blind one and drove a whole acceptance walk in it — one
round, on the largest issue in the batch. A settlement went to the implementer
and the verify gate and not to the review gate, which then rejected on clauses
the settlement had already answered — one annulled ground, one gate round. A gate
brief named the register and the issue file, and not the merge briefing, so the
gate found a file of that name in the main checkout and appended five lines to a
stale artefact of a merged run.

**A prohibition names the system, not the verb: the other two faults.** The
2026-08-09 run's three faults shared one shape. The one kept in the skill is the
writable-database example. The other two: "a probe script needs a directory
holding `node_modules`" named no home, so three files landed at the shared
worktree root; and a brief naming no register path sent two gates to the worktree
copy instead of the main checkout's.

**Why the verdict check is a check and not a reminder.** Two adversarial gates
died at the weekly usage limit during the 2026-08-15 workflow audit and wrote
nothing at all. Both times a person recovered the work by reading a transcript by
hand, and nothing mechanical noticed they had returned empty. Separately, one
gate's 175-line verdict was left in the wrong tree on the 328-332 run and
survived only because the finale diffed two checkouts for an unrelated reason.
The place-not-only-the-act rule was adopted on 2026-08-09, one of its own worked
examples is a brief that sent two gates to the wrong register copy, and the same
fault recurred four days later. A second telling would not have worked either.

**R2, and what the citation pass is worth.** Adopted from the `cab74e` finale.
The fourteen issue files that run built went from 1 broken citation to 251, and
twelve open backlog issues nobody opened went from 0 to 28, four of them
`ready-for-agent` and takeable in the next batch. The mechanism is not
carelessness: issue 353's citations were verified correct at 08:50 and issue 346
moved the same file at 13:11. Nothing re-read them, because the only stage that
looked was the finale, by which time thirteen commits had landed.

**A self-commit does no visible harm.** Two of the first three implementers on
the 209-215 run committed before either gate had opened. Neither did harm, which
is what makes the class hard to see.

**The scopeless negative that shipped.** The rule was advice in the skill from
2026-08-09 and was broken the same night: a wrong `updated_at` ruling shipped and
survived only because an implementer refused it on evidence.

**Searching the branch for a twin.** On the 310/309/308 run of 2026-08-11 four
deleted claims had twins and a fifth reached main, because its twin sat one
directory away in a file the correction never opened. The human adopted the search
narrowly: no authoring-time rule came with it, because the four caught instances
cost two minutes each rather than a strike.

**The three claim rules, illustrated.** The 207-185 primer asserted issue 201's
file was the only copy of a measured record while three others existed — and that
sentence was written as the REPAIR for a stale-prose defect, by an agent
following the deletion rule. The same primer recorded that `import pg` succeeds
"when node is launched from the worktree root", having watched it succeed there;
the cause was a `node_modules` symlink, so the import succeeds from any cwd that
has one and fails from every cwd that does not. And a cross-session sweep of the
209-215 batch found nine ambiguous citations across six issues, the worst a bare
`review.ts` used eleven times where the tree holds two files by that name.

**The three runner errors of the 208-202 run.** A transcribed figure off by 960;
a refutation from a grep that missed the call one directory over; and
hand-written timestamps an hour ahead of the clock.

**What uncapped criteria resets cost.** 7 attempts and 14 gate runs where the
skill promises three.

**The ruling that had no issue number.** the human ruled question 3 of issue 213 on
2026-08-02 by splitting a road out of scope; nine hours later no issue existed,
and the only trace of the split was one phrase inside 213's own file. A verify
gate happened to notice, and it was minted as 234. Nothing was watching for it,
so nothing would have caught it a day later.

**Why staleness is the file's mtime.** The handwritten `heartbeat <HH:MM>` field
failed twice in one run, on a runner who had already diagnosed the failure mode.

**The launch line that printed too late.** On the 247-170 run the line printed at
22:22, after the first implementer had already finished, so there was no window
left to interrupt.

**The carried fact that was never re-derived.** On the 209-215 run the plan file
said `current_workspace()` "answers null when the count is not one"; it actually
orders memberships by `created_at` and returns the OLDEST, answering null only at
zero. The runner repeated it for nine hours across many spawns before a gate
refuted it from `0011_workspaces_rls.sql:115-126`.

**No agent file pins a model.** `harden-issues-attacker` was the last, and it
moved to `inherit` on 2026-08-02, so the tier is chosen at launch.

**What worktree readiness costs, and the green it closes.** the human adopted it on
2026-08-07 and asked what it costs in tokens: it saves them. The failure it
closes was measured — a fresh worktree of this repo ran `npm run typecheck` to
exit 0 with `node_modules` absent, because `tsc` resolved off a global install
and never loaded the repo's types.

**The six hours the allowlist bullet cost.** On 2026-08-14 a verify gate sat on
"Allow Claude to start spine-dev-qa-auto?" with its own task counter reading
6h 00m 05s. The human found it by looking at the screen. The bullet was already there
and ran correctly: the runner enumerated the six classes the old text named and
dry-ran all six. It read an illustrative list as a complete one.

## Three experiments, pre-registered 2026-08-23 (arms and thresholds, before any run)

Written before any of them ran. The effort trial that closed on 2026-08-23 worked
because its threshold was fixed in advance and the human took the rule as written when
the reading went against the hypothesis. These three get the same treatment. A
threshold argued after the number arrives is not a threshold.

Order: the medium-rung validation first, because it costs a scratch session rather
than a run. Then slim-then-measure on the next real batch. Compaction last, because
its arms need a run each.

### 1. Medium-rung validation

**The question.** Is `medium` a distinct effort rung at all, or does it resolve to
something else? Nothing has established this. The trial that just closed ran a whole
batch at `medium` and read 1.22M weighted tokens per issue, and that number is
consistent with `medium` being a real rung, with it resolving silently to `high`,
and with it resolving to nothing. Agent frontmatter accepts `effort: banana` without
complaint, so an unrecognised value is known to load quietly.

**Design.** The interleaved experiment recorded above, repeated. Identical agents on
one enumeration task, differing only in the effort line, runs interleaved so drift in
the service hits every arm equally. Five runs per arm.

**Arms.** `low`, `medium`, `high`, `xhigh`, plus two that exist to grade the
measurement rather than the dial:

- A second `high`, under a different agent name. This is the noise floor. Two arms
  that are the same thing must land together, or the threshold below is meaningless.
- `effort: banana`. Where nonsense lands tells us what happens to a value the loader
  does not recognise, which is the failure mode `medium` might already be in.

**Measured.** Mean wall-clock and mean output words per arm, as in the table above.

**The threshold, fixed now.** `medium` is a distinct rung if its mean wall-clock
differs from `high` by 10 per cent or more, and the two `high` arms differ from each
other by less than 10 per cent. Both conditions, or the answer is "not established",
which is not the same as "identical" and must not be written up as one. If the two
`high` arms differ by 10 per cent or more, the task is too noisy to grade effort and
the experiment reports that instead of a rung.

**What a result buys.** A confirmed rung makes the B6 implementer-seat trial worth
running. An unconfirmed one retires `medium` from every future proposal, which is
the cheaper outcome and the more likely one.

### 2. Slim-then-measure

**The question.** Did the class-(a) slim of 2026-08-23 change what a run costs?

**Design.** Per-issue weighted tokens from `orchestrator_cost.py --days 7`, on
comparable batches before and after the slim, inside one seven-day window. Same
session effort on both sides, `high`. Comparable means a similar issue count; the
readings already on file are four issues and five issues.

**The honest answer is written before the run, because it will be tempting to claim
otherwise.** The slim took `SKILL.md` from 902 lines to 858. That is 5 per cent of
one file. Against it, the two batches already measured at `high` read 0.96M and 1.51M
weighted tokens per issue, a spread of 57 per cent driven by issue mix alone. One
batch after the slim cannot separate a 5 per cent input change from that. So:

**The threshold, fixed now.** The slim is recorded as having no measurable effect
unless the post-slim reading falls outside the 0.96M to 1.51M band already observed
at `high`. Inside the band, the entry reads "no measurable effect at this sample
size" and nobody writes that the slim saved tokens. Outside it, the reading is
interesting and still not attributable to the slim without a second batch.

**Why measure at all, then.** To catch the opposite result. A slim that moved a rule
somewhere the orchestrator no longer reads it costs correction rounds, and those show
up as a higher number, not a lower one.

### 3. Compaction

**The question.** Does compacting at an issue boundary cost less than carrying the
context, and does it cost less than halting and resuming?

**Arms.** Three, one run each:

- Boundary compact by hand. The human types `/compact` at each issue boundary. It is
  manual because it has to be: no skill, hook or tool in this harness can trigger
  compaction, which p3-4 established by walking the tool inventory. Adopting this arm
  means adopting a standing manual step, and that cost belongs in the decision.
- Deliberate halt-and-resume at each issue boundary, through the existing halt block.
- Control. Neither, as runs work today.

**Measured.** `orchestrator_cost.py --days 7`, per-issue weighted tokens, plus the
runner-error count at finale for each arm. A cheaper run that makes more mistakes is
not cheaper.

**Preconditions, both before arm one starts.** The citation baseline written to a
file under `.scratch/<feature>/`, and the road choice written into the issue's ledger
row so a later reader can tell which arm produced which number. The effort trial
nearly died on exactly this: its first launch printed `high` when the picker said
`medium`, and only the stamp rule caught it.

**The standing rule this experiment may not contradict.** Post-compact equals resume:
a compacted context is treated as a fresh session that must re-read the ledger, and
the compaction summary is not evidence of anything. An arm that reads its own summary
instead of the ledger has measured a different thing.

**The threshold, fixed now.** An arm is adopted if it cuts per-issue weighted tokens
by 15 per cent or more against the control, with no increase in runner errors at the
finale. Under 15 per cent, the manual step is not worth the human's attention and the
answer is no.

## Six changes after run `bridge-cse` — approved by the human 2026-08-24

The run built issues 408, 407, 409 and 338. It took 7h49m against an estimate of
3h15m to 4h45m, took eight implementer attempts for four issues, and spawned 43
agents where the last four-issue run spawned 35. `orchestrator_cost.py --days 7`
puts it at 1.78M weighted tokens per issue against 0.96M for the four-issue run of
2026-08-19, with the orchestrator at 23 per cent — the highest share of the seven
runs in that window.

The human asked where the time went. The answer is in the run's own journal and ledger,
both on main, and it is not batch size: four issues is already the small end and the
control at the same size cost half as much.

**The root cause is that the issue files were not ready.** All four carried
`Status: needs-harden`. Pre-flight found 408 and 407 carrying no criteria section at
all — promoted register rows with a fault and a remedy direction — so the runner
authored the graded criteria into the spawn prompts and the run then graded its own
invention. Two citations in that authored brief were wrong, reached a shipped code
comment, and cost a correction round. 409's file miscounted its own subject (36
`"use server"` files; there are 21, the rest being the string inside comments) and
its stated rule would have reddened 15 shipping type exports. 338's premise was
false — its guard is green on QA, not red — and its two requirements contradicted
each other on an empty exercise set. The runner's own settlement for 409 was then
wrong, two attempts were graded against a spec that stopped existing, and the
criteria were reset at 18:10. 409 alone took 165 minutes, 35 per cent of the run.

**And the hardening already existed.** A peer `/harden-issues` session had hardened
all four issues on `claude/harden-issues-407-408-ce713b`, unmerged, and messaged the
run mid-issue with five findings, all of which held. That branch merged at 23:12,
about ten hours after the run finished the same four files without it.

Sorted under the human's three-class test. Two refuse, three state a fact, one changes a
rule. Nothing here asks an agent to remember.

1. **`check_issue_ready.py` — refuse an issue whose file gives a gate nothing to
   grade.** Passes on `## Acceptance criteria`; passes and says so on
   `## Must still be true` alone; refuses on neither. Override per issue by id, and
   the override prints its cost. Measured before building: of the 32 files reading
   `Status: ready-for-agent` on 2026-08-24, exactly ONE carries neither section, so
   this does not stand between the runner and a hardened backlog. It stands between
   the runner and a freshly promoted register row. It does not touch the 2026-08-21
   ruling that an explicitly named issue always runs — the stamp asks whether
   hardening read the file, this asks whether the file has criteria at all.

2. **`check_harden_branch.py` — refuse to start while an unmerged
   `claude/harden-issues-*` branch holds an issue in the batch.** Reads the branch
   list, skips branches already in main, and intersects each branch's changed
   tracker paths with the batch. The remedy is a fast-forward: those branches touch
   `.scratch/` only.

3. **`cp -al` makes hard links, so a write inside that copy lands in the run's own
   worktree.** At 17:05 the runner appended three lines to a file inside such a copy
   and contaminated the tree it was orchestrating. It is a copy for reading and
   building. A drill that writes uses the rsync recipe.

4. **The rsync copy's `node_modules` symlink is a two-way door.** 338's verify gate
   ran `rm -rf node_modules/.vite` inside its private copy and deleted the run
   worktree's vitest transform cache.

5. **The `.git` exclusion is deliberate and now costs nothing.** `.git` is 87 MB
   against a 66 MB copy, so carrying it would more than double the copy to serve one
   script. Fixed at the source instead of warned about: the two cases in
   `tests/scripts/check-issue-citations.test.ts` that drive git now skip when the
   tree has no `.git`, and `scripts/check-issue-citations.mjs` exits 3 with
   `REFUSED no-git-repository` naming the copy as the likely cause. Both 408's gates
   and 409's gates had diagnosed that red independently; 409's filed `vg409-01`.

6. **Prose-only owed work no longer buys an implementer.** Where every gate grades
   the behaviour correct, every owed item is non-executable prose, the delete-only
   rule already governs the class, and the runner can verify each deletion by grep,
   the runner deletes and commits. No spawn, no correction round, straight to
   `done`, recorded in the row as `prose: deleted HH:MM`. 409's attempt-3 rejection
   was four comment deletions and 338's attempt-2 rejection was two prose sites;
   both bought a fresh implementer, and in both the journal records the runner
   verifying the result by grep afterwards. About 30 to 40 minutes across the two.

   **The human approved this as "the gate files a register row and the commit lands".
   It is built as a deletion instead, and the reason is a hole in the row road.** A
   false sentence in a code comment is `audience: agent`, and
   `~/.claude/agents/promotion.md:34-36` refuses `audience: agent` at any severity.
   Filed as a row, the false sentence would ship, be refused at promotion, and stay.
   The deletion road takes the same spawn out of the run and leaves nothing false
   behind. Where the four conditions do not hold, the correction round runs as
   before.

**Two things were deliberately NOT changed, and both were checked rather than
assumed.** Batch size, because the four-issue control cost half as much and the
difference is retries, not size. Gate concurrency, which the human refused to downgrade
on 2026-08-15 and which two audit passes upheld.

Every item above is under a test. The two guards carry `test_check_issue_ready.py`
and `test_check_harden_branch.py`; items 3 to 6 are prose and are pinned by
`TestTheBridgeCseChangesSurvive` in `test_skill_structure.py`, whose assertions were
mutated and confirmed red before this was written.

## Five measurement defects in the finale — repaired 2026-08-31

Run `batch-88624c` was the first run to take all four measurements the human commissioned on
2026-08-30. Two of the four were wrong, and neither said so.

1. **`run_costs.py` read a foreign transcript.** Its rule was "the newest `.jsonl` under
   this working directory's project slug", on the reasoning that a run holds its worktree.
   The finale ran it from the main checkout rather than the run's worktree, whose slug
   directory holds 64 transcripts from months of unrelated sessions. It reported a wall
   clock of 1.01 h for an 8.48 h run, with a longest step of "Gather week git activity"
   that this run never ran, and appended those figures to
   `.scratch/workflow-audit/run-costs.md`. The row is corrected and the table says why.

   It now takes the run's name — from `--run`, or from the `claude/run-issues-<name>`
   branch checked out where it runs — refuses when the branch is not a run branch and
   lists the run worktrees it can see, and **checks that the transcript it picked names
   the run** before reading a figure out of it. `batch-88624c`'s own transcript names it
   1231 times and no other transcript in that repository's slug names it at all, so a
   foreign session cannot pass. When it cannot identify a transcript it appends no row:
   a row from an unidentified transcript is worse than no row, because its wrong cells
   look exactly like its right ones. `finale.md` now passes `--run`.
   Tests: `test_run_costs.py`.

2. **`estimate_accuracy.py` booked 18 of 30 agent steps to the wrong issue.** It read the
   issue id with `\*\*(\d{2,4}[a-z]?)\*\*|\bissue\s+(\d{2,4}[a-z]?)\b`. Every brief in the
   run opens `issue **201 — pin the remaining workspace-crossing FKs**`, and neither half
   matches it: the bold span carries the title as well as the id, and `issue\s+` cannot
   cross the two asterisks. `re.search` walked past the heading and matched a later number
   in the brief's body. Issue 201's implementer went to 207, issue 224's two gates to 156,
   issue 339's review gate to 224. Issue 224c was named by no prompt at all, which is why
   it went ungraded. Issue 201 collected eight steps from four issues and read 7.34x; 339,
   225 and 269 kept only their correction round, which is the `steps 1` rows.

   It now reads `\bissue\s+\**(\d{2,4}[a-z]?)\b` **from the heading line only**. Falling
   through to the body always finds a number and reports it with the confidence of a right
   one. A brief whose heading names no issue is printed by its own text and the run exits
   2. Every run now ends with an `attribution:` line giving spawns found against spawns
   attributed. Re-measured, the run reads median 1.43x, spread 0.45x to 3.03x, 8 of 8
   graded, 30 of 30 attributed — estimates running SHORT where the original said long.
   Tests: `test_estimate_accuracy.py`.

3. **The 17% with nobody running was not a regression, and the share was the wrong
   number to read.** Measured across four runs, idle sits between 1.48 and 1.64 hours —
   a ten-minute spread — and between 9.4 and 11.1 minutes per issue. `batch-88624c` has
   the LOWEST absolute idle of the four. Agent time is what moved: 16.24 h over ten issues
   on 26 August against 7.00 h over eight. A constant numerator over a halved denominator
   is the whole of 9% to 17%.

   Of the 89 minutes, 49 are the issue seam (close the last issue, commit, spawn the
   next), 13 the finale stages, 12 the correction rounds and 12 the gate-pair spawns.
   Only 18 of the 89 are inside a tool call; the rest is the runner reading verdicts and
   writing the ledger, journal and next brief. Most is serial by construction — the next
   implementer cannot start before the previous commit lands. Two small ones are real: the
   lint and cold build at the seam could run in the background, and the 1.5-minute ledger
   stamp before each gate pair could happen after the spawn instead of before. About
   fifteen minutes, three per cent.

   `run_timings.py` now prints minutes per issue on the line under the share. The share
   has no meaning without its denominator, and reading one without it is what made a flat
   figure look like a regression.

4. **The briefing's navigation is ticket 34 of the pilot-delivery map, already open.**
   The human routed it there rather than to a new issue. `batch-88624c`'s briefing has a
   contents block as a sample to judge; nothing in `finale.md` or `SKILL.md` changed,
   because ticket 34 says not to choose between a table and a diagram before its
   deliverable 1 reports. That deliverable's evidence is recorded on the ticket.

5. **The human's ruling of 2026-08-31: the ledger's per-step clocks go.** `run_timings.py`
   is the single source for durations. The correction-round close stamp stays and comes
   from `date`, never from the runner's count of the clock. Applied to `SKILL.md`: the
   "stamp every transition" rule is replaced, a gate writes `verify: pass|reject` with no
   time, and the prose-delete row reads `prose: deleted`. **This supersedes
   `prose: deleted HH:MM` in the `bridge-cse` section above.** The owner line keeps its
   stamp: it is a run-level state, not a per-step clock, and the ruling was not that wide.

   **The sweep behind the ruling understated it by one stamp, found on re-running it.**
   It said `check_commit_order.py` parses one ledger clock. It parses two: `COMMITTED`
   required an `HH:MM` after the commit sha, and `rows_from` needs both patterns, so the
   first ledger written without it would have graded zero rows and printed `ok` — the
   silence its own empty-table refusal exists to prevent. That time is now optional. Git
   supplies the time this check actually compares; the ledger stamp was only quoted back
   in the refusal. Tests: `TheCommitClockIsOptional` in `test_check_commit_order.py`.

## The permission floor: an allow rule the run worktree could not see (2026-08-30)

Moved out of SKILL.md on 2026-09-01, in a pass that took the incident stories out
of both hot skills. The rule and the mechanism stay loaded there; this is what the
rule cost.

Run `414a-483-286335`, 2026-08-30, is the instance, and it cost 2 h 34 m — the
single largest step of a 14.76 hour run, spent on a 25-line test while the human
slept. That run's pre-flight DID dry-run `npx vitest` successfully at 04:00 and
the classifier still refused the same class at 07:22. Replayed against that
run's real launch state, `check_permission_floor.py` refuses all eight classes
and names `npx vitest` first.

Built 2026-08-30 on the human's instruction, closing `rn99f-03`.

## The hardening pass folds into the launch (2026-09-07, ticket 33 sitting 2)

Deliverable 3 of ticket 33 of the pilot-delivery map. The human's goal in their own
words: "from issues i can directly go afk and if any decisions pending i can take
later". Twenty-two rulings on 2026-09-07 settled the shape; sitting 1 landed the
machinery around the phase and this is the phase itself. `launch-harden.md`
carries the instructions and this section carries why they are those and not
others.

**Why a file beside `SKILL.md` and not a section inside it (ruling 16).** The
phase is a full load. Measured on the attended pass of 2026-09-06 that hardened
seven issues: 1.40 h wall clock, nine attacker spawns at 6.49M weighted tokens,
one seam at 1.32M, 4.95M on the main thread — about 1.8M weighted per issue,
against about 10M per issue for a run. A hundred-line file is about 1,560 tokens,
and `SKILL.md` is re-read on every runner turn: run `batch-b5e96d` took 624 of
them, so a section would add about 0.97M cache-read tokens to every run including
the ones with nothing to harden. Off the common path it costs those runs nothing.
It is the shape `finale.md` and `resume.md` already use, and removing the fold
later is deleting one file and two lines. A new combined skill was refused for the
same reason: two skills that must be launched together is a third thing to keep in
step.

**Why the launch line prints before the phase runs (ruling 9).** The line is the
interrupt window, and an attacker wave costs about twenty-five minutes. A line
printed after the phase would name the hardening after it had been paid for.

**Why the citation check split into two roads (ruling 9).** One instrument, two
jobs, and the difference is write authority rather than usefulness. A run may not
write an issue file it did not harden — that rule is what keeps a run from grading
itself against criteria it rewrote — so a stamped file's broken citations are
reported. An unstamped file is inside the phase's own scope, and the phase IS a
hardening pass, so the repair costs nothing there and costs an attacker a whole
round anywhere else. The bullet read `Report, never repair` while there was only
one road.

**Why five attackers and not all of them (ruling 21).** Five concurrent spawns is
what a usage window sees at once; fifteen is a batch that meets a limit mid-wave
and resumes into a half-hardened set. Nothing is dropped to fit the cap, because a
cap that drops work is a cap that quietly narrows a batch the human typed. It is a
recipe read at spawn time and nothing refuses it: a hook gets built the first time
a run is measured over the cap, which is his own rule that a reminder failing once
is not answered with a second reminder.

**Why exactly three drop classes (rulings 4 and 11).** Every reversible fork
already has a default road — take the default, write it as a default, queue it —
and two of the five rulings on the 2026-09-07 attended walk overturned a
recommended default, both on issue 443, both reversible in under an hour by the
pass's own estimate. So the cost of defaulting wrongly is an hour and the cost of
waiting is the whole point of the fold. The three that cannot default are the ones
where the default is not reversible in an hour: an `[irreversible]` question, a
split the phase cannot complete, and a premise check. The premise class is four
days old: on issue 465 an attacker, the seam pass and the orchestrating session
all read the code correctly and still got the issue wrong, because the datum that
settled it was on the human's phone.

**Why a split is cut at launch rather than dropped (ruling 3).** `questionrules.md`
already says the session settles a split it can complete, and the pass of
2026-09-07 cut 572b and 388b that way and the live run took both. The overlap
guard in `machine-preflight.py` covers both halves once they are in the ledger, so
no second run can take one of them. A split that changes a migration's direction
stays a drop, because a migration's direction is not reversible in an hour.

**Why one commit before spawn 1 (ruling 10).** The phase is the most expensive
part of a launch to lose and an uncommitted worktree loses it on any halt. Taking
it first also keeps every issue commit single-purpose, which is what
`check_diff_coverage.py` reads.

**Why the defaults go under `## Ruled` (ruling 12).** `run_measures.py` reads that
section and counts an issue as cut on a default when an item names it. There is no
marker for it and there does not need to be one: the section already exists, the
finale already writes it, and a default written anywhere else in the briefing is a
default nothing counts.

**Why all at launch rather than one before each implementer (ruling 15).** A
per-issue road pays the same tokens and spends them serially, about ten minutes
per issue instead of one wave. The case against it is a criterion that goes stale
mid-run — issue 523 falsified 522's count one commit earlier on the live run —
and that is one in fifteen, already covered by strike-2 mode. Three or four in one
run reopens this.

**Why no off switch (ruling 18).** The scope grammar has three override words and
a fourth is a road nobody would test. An unstamped issue can still be run raw:
stamp it in a standalone pass first. The criteria gate refuses a file with no
criteria in any case.

### The role count in the prose was twelve for a day (2026-09-07)

Ruling 2 widened `model_map.ROLES` to fourteen at sitting 1 and `SKILL.md` stated
twelve in five places and enumerated the old twelve keys in a sixth. None of them
changed what a run wrote: the runner pastes what `model_map.py` prints rather than
typing a role list, so every ledger header carried fourteen throughout. What the
stale prose cost is a reader who counts roles off it and concludes the two
hardening roles are outside the map — the opposite of the ruling. The correction
is five words; the guard is `TheProseRoleCountIsTheRealOne` in
`test_skill_structure.py`, which reads the live `ROLES`, `WORKERS` and `GATES` and
sends the next widening red on the day it lands. Written as a refusal rather than
a correction because prose beside a list in code goes stale on every widening, and
this one went stale within a day.

### The fold put the hardening phase above the concurrency gate (2026-09-07)

Found by mock drive D of ticket 33 sitting 3, and fixed in the same sitting.

`check_harden_branch.py` sat four bullets below the hardening-stamp bullet, which
is the bullet that opens `launch-harden.md`. So the pre-flight read in this order:
mint the batch id, write the ledger, seed the QA workspace, run the citation
check, print the launch line, **run the whole hardening phase**, run the criteria
gate — and only then ask whether a peer `/harden-issues` branch already held these
issues. The refusal arrived after five attacker spawns, a citation repair, a
stamp and a commit.

That is worse than the fault the gate was built for. Run `bridge-cse` built four
issues from unhardened files while a peer session held hardened copies; the fold
made the run WRITE those same files, concurrently with the peer session, and then
refuse the launch. Two hardening passes on one issue file with no merge between
them is the second-writer collision the never-attack guard exists to prevent, and
ruling 5's guard does not reach it: that guard reads live LEDGERS, and a peer
hardening branch has none.

The drive also measured a second cost of the same ordering. The batch id was
minted before the refusal, so a launch that never started left
`.scratch/example-feature/runs/batch-29e9c1/run.md` reading live and holding issue 909.
`machine-preflight.py` counts that as one of the two live runs and refuses any
later `/run-issues 909` as an overlapping range — a refused launch fencing off its
own issues for the life of a batch that does not exist.

The fix is order alone, and it costs nothing: `check_harden_branch.py` needs no
batch id, no ledger and no worktree, so it runs first. Two assertions in
`ThePeerHardenBranchIsRefusedBeforeThePhaseSpends` pin the two orderings against
the text of `SKILL.md`, because both faults are positions in a bullet list and a
position is exactly what a later edit moves without noticing.

`launch-harden.md` states the same fact at the head of its own order section, and
its `What this phase never does` list names the peer branch beside the live
ledger. That is ticket 33's own gap 1 class — a rule ruled in one file and not
written into the file that enforces it — and the phase file is what a launch
caller actually reads.

### The citation check's exit code is not a verdict about the batch (2026-09-07)

Found by mock drives A and B of ticket 33 sitting 3, and fixed in the same sitting.

Ruling 9 gave the pre-flight citation bullet two jobs by file — repair an
unstamped one, report on a stamped one — and both need to know which scoped
files are broken. The obvious instrument cannot answer.
`scripts/check-issue-citations.mjs --quiet <one issue file>` runs the DECISION
pass over the whole repository beside the citation pass over the named file, and
there is no flag to turn it off. On 2026-09-07, on the mock feature, a file
reading `0 citations in 1 file(s): 0 hold, 0 moved` exited 1 and a file carrying
two genuinely moved citations exited 1. The 1 was eight `Touches:` faults in
`docs/adr/` and other features' issue files, none of them in either batch.

Before the fold that misreading cost a wrong sentence in the launch line. Since
ruling 9 the phase WRITES on it, so it would open and repair every unstamped file
in scope including the clean ones — and a repair that quotes text into a file
nobody had a reason to touch is the class of edit no gate reads.

The remedy is a reading rule in both places that run the instrument, not a change
to the script: the verdict is the file's own summary line and the `MOVED`, `GONE`
and `AMBIGUOUS` rows that name it. Fixing the script would mean a seventh exit
code on a checker whose docstring already explains why six is the number it has,
and the decision pass is genuinely useful where the finale reads it.

### The phase works in the run's worktree, and the seam finds gaps it may not fix (2026-09-07)

Two more from ticket 33 sitting 3's mock drives, both fixed in the same sitting.

**Which tree.** `launch-harden.md` said the phase commits "on the run's own
branch" and never said which tree its attackers read and write. Every other path
it names is run-scoped, so the issue file was the one path a runner had to guess,
and the tracker lives in the main checkout, so that is what a path completes to.
Drive A guessed it and both halves of the failure landed at once: the run
worktree's copy of issue 901 still held the unhardened text, so the implementer
would have been graded against criteria the phase had already replaced, and the
MAIN checkout carried a run's uncommitted edits to two issue files. `main`
belongs to the human. Nothing mechanical would have caught either: the commit step
would have found nothing to commit on the run's branch and reported success on an
empty diff.

**The seam's stamped siblings.** The seam agent reads every issue in the batch,
because a gap between two issues does not care which of them was hardened today.
The phase may write only the unstamped ones. Drive A hit the case on its first
seam: it found that issue 901's criterion 1 carried an export-style ambiguity its
own attacker had missed, applied the fix to 901, then found the identical gap in
903 — already stamped — and correctly declined to edit it. It recorded the fact
in `seam.md`, and the phase reads counts and `## Checks for the human` out of that
file and nothing else, so the finding would have died there while 903's
implementer built to a criterion the seam had just shown to be short.

The fix needs no new authority. The runner already writes a spawn prompt per
issue and a merge briefing, and neither is an issue file, so the finding travels
in `Settlements:` and under `## Ruled`. Ruling 4's drop list is untouched: a seam
finding against a stamped issue drops nothing.

Both are the same shape as the concurrency-gate fault above — the phase was
specified against the pass it folds in, and the pass has no worktree, no ledger
and no stamped siblings it must not touch. Each gap only appears when the phase
is actually driven, which is what the mock drive was for.

### The review's own five, and the tree question the fold reopened (2026-09-07)

`/code-review` at high effort over sitting 3's diff. Five findings, all confirmed,
all fixed in the sitting. Three of the five are one fault seen from three sides.

**Naming the tree in ONE file was not enough.** The phase file now pins every
issue file it touches to the run's worktree, and two bullets in `SKILL.md` that
feed it still named no tree: the citation check, whose rows the phase repairs
from, and the hardening stamp, whose reading decides which issues enter the phase
at all. Both now name it, and both carry the reason, because a worktree freezes
the tracker at the moment it was cut. Drive `batch-800f60` was cut at `3d5fe7bf`
while issue 914 landed on main at `b81bf6a4`: the worktree did not hold that file,
the attacker was handed a path that did not exist, and it edited the main checkout
and reported doing so — which is the only reason it was caught rather than merged.
The same freeze makes an issue stamped on main after the cut read unstamped in the
worktree, so the stamp bullet could put one into the phase twice or skip it once
on nothing but which copy the runner opened.

**A false absolute, in a sentence written to close a gap.** The new
`What this phase never does` bullet said `check_harden_branch.py` refuses a peer
branch "so the phase never meets the case". That check lists
`refs/heads/claude/harden-issues-*` and diffs `main...<branch>`, so it sees
committed work on one branch name and nothing else — a peer pass whose hardening
is still uncommitted, or which branched under another name, walks past it. The
bullet now says what the gate sees and what it does not, and names the remedy for
the rest. It is the scopeless-negative class this skill's own step 5 forbids, and
it appeared in the paragraph written to fix a different scoping fault.

**A route that stopped at the drop.** The seam finding rule sent findings against
a stamped issue into that issue's implementer spawn prompt. An issue step 5 drops
has no implementer, and the seam reads dropped issues on purpose. Those findings
now go to the briefing under `## Decide`, beside the drop, where whoever
re-hardens the issue will read them.

**A test anchored on a name instead of on the thing it pins.** The ordering check
found the concurrency gate by the first occurrence of `check_harden_branch.py` in
`SKILL.md`. The script is named in cross-references too, so an earlier mention
would have satisfied the search while the bullet itself sat back below the phase
trigger — green on exactly the regression the class exists to catch. It anchors on
the bullet's opening words now, the way its sibling already anchored on
`Then mint the batch id`.
