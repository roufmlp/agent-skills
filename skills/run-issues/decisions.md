# run-issues — settled decisions and the incidents behind them

Read this before changing how the run works. Do not read it to run one — the
skill and the agent files are self-contained. Nothing here is loaded into a
subagent's context.

Newest section last, each dated. It is a running log, not a document — entries
were written the day the incident happened and are left as written, including
the ones later overturned. That is the point of keeping it.

**Passing through and curious?** Three entries carry the argument on their own:

- [What was measured, not assumed](#what-was-measured-not-assumed) — where a
  four-month-old assumption met a stopwatch and lost.
- [A blocked issue stops its dependents, not the
  run](#a-blocked-issue-stops-its-dependents-not-the-run-2026-07-26) — the
  cheapest correctness rule here, and it took a bad run to see it.
- [Prose rejections are fixed by deletion, not
  refinement](#prose-rejections-are-fixed-by-deletion-not-refinement-2026-07-28)
  — what gate feedback taught about writing.

---

## Original design (2026-07-19, grilled and agreed)

Fresh subagent per unit of work; adversarial gates; two-strike escalation; runner
owns the branch and the human owns main; all state in files so any session can
resume.
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
which these rules aim at. Real leak: an acceptance of "never notify" was proven
on a record with no messaging connection; the connected one broke it live.

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
   and the credits were gone, so a two-strike escalation would have died on an
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
   all four acceptance criteria while dropping the page cap —
   `PAGE_SIZE` 24 became the page sequence `[1, 31, 24, 24, 24, 24, 4]`.
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
issues. A human's call, not a default.

**Runner error recorded by the run itself:** a scope narrowing sent to a live gate
was read as a cancellation and the gate stood down without a verdict, costing an
independent read. Say "narrowing, not cancelling" explicitly.

## A blocked issue stops its dependents, not the run (2026-07-26)

The skill said "Issues are a dependency chain. Always run in order; never skip
past a blocked one", and halted the whole run on a blocked issue. **That rule had
no entry here** — no incident, no grilling, no measurement. It was asserted early
and inherited ever since, and it was restated as though settled. It was questioned;
it did not survive the question.

The premise is false for most batches. A 16-issue set queued on 2026-07-26 was
almost entirely independent: a name-length guard on one form (111) has no
relationship to empty labels on an unrelated detail page (124). Halting
fourteen issues because a migration hit an unexpected row would have cost most
of an unattended overnight window for nothing.

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
to the human, a `Hardened:` stamp on resolved issues — and issues arrive with a
rubric-shaped template (`Status:`, acceptance criteria, `## Must still be true`)
already in place. This skill's only coupling is the pre-flight stamp check:
launch-time information, never a gate. Grilled and settled 2026-07-27 from two
runs' evidence (112, 114, 110, 117, 122, 124, 125, 126 all shipped criteria
faults through green gates).

## Cost grill (2026-07-27, after the 111-136 batch)

The 14-issue batch of 2026-07-26 cost roughly double its floor (three clean
issues at 28-38 min; everything else 60-300). Grilled and settled with the
human. The evidence lives on `main` in the project's repo: `run.md`, the
1177-line journal, and the merge briefing under `.scratch/<feature>/`.

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
   pages was nobody's job. Three of the five production pages in that section
   rendered a 21,935-byte error shell until the finale caught it. The sweep is
   seconds of HTTP against a server already running: fetch each touched route,
   and a 200 wrapping an error shell is a FAIL. The finale's whole-branch sweep
   stays as backstop.

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
a money or auth rule, anything that ships data — and a split, which stays the
human's alone. Both leave the issue unstamped and out of `all`.

The standing constraint this serves, stated by the human on 2026-07-27: **no run
stops mid-flight for their input.** Anything needing them is a blocked issue, a
default taken, or a line in the merge briefing — never a wait.

**`needs-info` becomes `needs-harden`.** The old status had no return path here —
nothing re-reads a `.scratch/` issue file the way an upstream tracker re-reads a
reporter's reply. Both places a run sets it — a superseded issue at scope
resolution, and criteria a worker proved wrong — now set `needs-harden`, which
`/harden-issues` takes as in-scope. The status now names the thing that clears it.

**An empty `all` scope halts and says so**, rather than reporting a completed run
over no work.

## Default-and-decay across the chain (2026-07-27)

Extends the same-day provisional-stamping decision to the rest of the chain that
feeds this skill its issues, so the standing constraint holds everywhere and not
just in one skill.

**The audit that prompted it.** A chain day on a ~14-issue batch demanded roughly
3h38m of the human's time. Of that, 45-55 min was irreversible judgement — the
merge read, merge and deploy, run scope, pending secrets. The rest was blocking
loops: the issue-drafting tool's "iterate until the user approves", the triage
tool's step 2 "wait for direction" and its one-question-at-a-time grilling, the
PRD-drafting tool's "check with the user that these seams match". None of those
decisions needed the human; they needed a written rule and a default.

**The rule, now in all four tools upstream of this one.** Every question carries
the pass's recommended answer and a `[reversible]` / `[irreversible]` mark.
Reversible questions apply their default, record it in the file as a default
rather than a decision, and queue to a decisions-queue file. Only irreversible
ones wait. Irreversible means: a split, a `wontfix` close, a write to an
out-of-scope area, a transition on an issue a run holds, a migration's direction,
a money or auth rule, anything that ships data or commits a public contract.

**Write before you ask, everywhere.** The PRD-drafting tool writes its output to
disk before publishing; the issue-drafting tool writes slice files before the
harden pass and the quiz; the triage tool writes its recommendation and its
grilling findings into the issue as they land. Every one of those previously
lived only in a session context, so an abandoned or rate-limited session lost the
whole artefact with no record it had been attempted.

**Grilling is now conditional on there being someone to grill.** The triage tool
runs a grilling pass only where a real reporter exists. Against a local `.scratch/`
issue file the loop cannot terminate — nobody answers — so it routes to
`needs-harden` instead. This is the same root cause as the old `needs-info` dead
end: triage is built for a public tracker with reporters, used here on files that
have none.

**`Status:` is now the first line of the issue template.** Without it the stamp
had nowhere to land and `/run-issues` could not resolve scope — the contract was
assumed upstream and provided by nothing.

Still open: whether the triage step belongs in this chain at all, and which
tracker is canonical. Both recorded in a separate panel-review write-up.

## /daily-brief owns the human loop (2026-07-27)

The last piece of the 30-minute design. Every skill in the chain now defaults and
queues instead of asking; `/daily-brief` is where those queues become one file the
human reads once a day, and where their answers become writes.

**It closes three resting states this file already recorded as dead ends.**
`awaiting-merge` had no owner, no expiry and no reminder — an unmerged branch had
no clock on it anywhere. The project's pending-actions file was written to and
never read back. Queued defaults surfaced only in a merge briefing, so answers
scattered across runs. All three now have one reader on a schedule.

**The brief is a view, not a store.** Regenerated from source every firing,
authoritative only between being written and being applied. The chain's own rule
against second copies applies to it more than to anything else, because it is the
one artefact whose whole job is to duplicate state.

**The merge hazard, and the fix.** `merge` written into a file is an approval made
hours before the machine acts. The branch can move in between, and the human would
be merging a diff they never read. So every merge block carries the branch head
SHA it was written against; at apply time a differing SHA means no merge, rebuild
the block against the new diff, mark it `changed since you read it`. **A stale
approval is not an approval.** This is what makes "main belongs to the human"
survive an asynchronous decision.

**Apply runs before rebuild**, so a collation never overwrites an answer. And the
apply half re-reads `run.md` before touching any issue, skipping anything a run
holds — the same guard the hardening pass carries, whose only carve-out is
strike-2 mode.

Not adopted: having the brief decide anything. Every item in it already has a
default that has already taken effect. The brief exists so the human can overturn
a default, never so the machine can ask them a question.

## /daily-brief runs by hand, not on a schedule (2026-07-27)

Reverses the same-day intention to schedule it. `/schedule` creates **cloud**
routines, and a cloud routine cannot do this job: it runs in a sandboxed checkout,
cannot read `~/.claude/`, cannot write `brief.md` back to the machine, and cannot
see an unpushed feature branch. Since a run commits per issue and never pushes, and
mid-run ledger state lives on the unmerged branch, a 6pm cloud firing would collate
yesterday's `main` and present it as today. **A brief that looks current and is not
is worse than no brief.**

A local wakeup would see everything, but the argument for it collapsed once stated
plainly: the only thing a timer buys is that the brief is already built when the
human opens it — about a minute. Every other benefit assumed the human was absent,
and the whole design has them present for thirty minutes a day. The one real
argument, that a stale-dated brief signals a broken machine, does not apply when
the human is the one invoking it.

So: bare `/daily-brief`, once a day. Apply then rebuild, in that order, from one
command. If the collation wait ever becomes annoying, a local wakeup is a small
addition — built then, on evidence, not now on a guess.

Committed run state (the ledger, journal, and issue files under `.scratch/`) is
already tracked in git in projects that don't gitignore it, so the content a cloud
agent would need can already exist there. Freshness and write-back are what fail,
not availability. Worth knowing if the brief is ever moved into the repo to make a
cloud routine viable.

## The five forks from the 2026-07-27 panel, taken by the human (2026-07-27)

All five put to the human in one sitting and answered; none is a default.

**The chain ships publicly minus the upstream forks.** `harden-issues` and
`daily-brief` joined this pack; `to-prd` and `to-issues` stay private because
they are modified copies of Matt Pocock's skills and republishing a fork is an
attribution question, not a scrub question (see MANIFEST.md, "What ships"). The
pack's story: issues arrive however you make them; the pack takes over at
hardening.

**`triage` leaves the chain but the skill survives.** It was built for a public
tracker with reporters. Against issue files there is no reporter, so its
wait-for-direction and grilling loops were dead ends dressed as diligence. Bug
reports now enter at `/harden-issues` or as a direct issue file. The skill keeps
existing for any repo that grows a real tracker with outside reporters — deleted
from the chain, not from disk.

**Issue files are the canonical tracker.** Every downstream skill appends `##`
headings to issue files — harden stamps, status lines, deferred entries — and a
tracker issue body cannot carry that. Upstream authoring now writes files as the
record; a tracker mirror, if ever wanted, is a read-only view added later.

**The reuse rule is approved verbatim** and lives in
[`steering/coderules.md`](../../steering/coderules.md) as rule 6 under "The
working rule: AI types, I decide" — "Reuse approved patterns, not unreviewed
precedent" — closing the drift class where a wrong shape written once becomes
the house style through the primer. The lint half shipped with it in the app
repo it was decided on: anchor-without-href, placeholder-href and
static-element-handler checks at `error`, plus a seeded
`docs/patterns.md`. One correction to the working doc's claim: that repo did not
have `eslint-config-next`, and `eslint-plugin-jsx-a11y` caps its peer range below
the repo's ESLint major — so the checks are hand-rolled `no-restricted-syntax`
selectors with fixture tests, zero new dependencies.

**`harden-issues` gets its own `decisions.md`**, same pattern as this file and
parallel-hunt's. Provenance moves out of the hot SKILL.md, which is billed on
every invocation.

Judge for the sync decision: if the published pack draws a question about where
issues come from, that is the signal to either write the attribution and ship the
upstream forks, or add a small "authoring issues" note — not to quietly re-add
the references.

## Ledger discovery, pruning and the owner line (2026-07-27, after the first run on the reworked chain)

Four findings from a real three-issue run. All four are ledger-shaped, and none
was caught by panel review: the panel read the skill, and these only appear when
you read a run's artefacts against it.

**The ledger's own rule had no teeth, and the ledger broke it.** `run.md` reached
15,443 bytes. The status table was 13% of it. Halt blocks were 27% (1,788 bytes of
which the file itself labelled *superseded* and kept anyway) and finale narrative
was 20%. Every implementer and gate reads this file, so the ~7 KB the skill's own
"nothing else belongs in it" excludes was billed roughly a dozen times in one run.
Fix: name what gets moved out and when, and give it a checkable threshold.

**"Which ledger" is the expensive one — 25 measured minutes.** The journal
diagnosed it and wrote the fix; nothing implemented it, so it was still live. The
sharper version, found by running the enumeration: the ambiguity is not many runs,
it is **one run with many copies**. Run state is committed, so every worktree
branched from that commit carries a frozen snapshot — twelve copies, six with an
identical live-looking owner line. The discriminator was already in the format and
unused: the `Worktree:` line written at launch. The real copy is the one whose
`Worktree:` names the tree it sits in; every other is a snapshot to read never,
write never.

**The owner line was never cleared.** All six live-looking copies belonged to a
run that was finished, PR open, `awaiting-merge` — still naming a live session
hours later. Indistinguishable from a run that died mid-flight, which is exactly
the state the heartbeat exists to detect and what the cron keys off. Reaching
`awaiting-merge` or halting now rewrites the line to `Owner: none — …`.

**Every command handed to a human runs once first.** The briefing's step one was a
reconciliation query naming the column its own migration adds, presented as a
*pre*-migration check. It cannot run pre-migration. Written by a gate, copied to
the board by the runner, executed by neither, and it failed in the human's hands
with `column does not exist` under a heading saying the order was not negotiable.
The run's own central finding one level up: a criterion naming a test as a
tripwire has not proved it is one; an instruction naming a check as a safety step
has not proved it runs. A check that errors is worse than none — it reads as
diligence and fails at the moment someone is about to touch production.

**Judge for the next run:** does the ledger stay under the half threshold without
the runner being reminded, and does a `resume` with no range land on the right
ledger first try.

**Not changed, deliberately.** Gates were 43% of the modelled bill and 104 of the
run's 181 working minutes, against 77 for implementation. They are not the waste:
this run had zero strikes, three first-pass gates, and the verify gates caught a
wedged test-database state, an exact money reproduction, and two surviving
mutations. The cost grill already ruled the concurrent gates are not the driver.
Left alone.

## Second panel: cost, autonomy, enforcement (2026-07-27)

Five personas over this skill plus the agent briefs, with the same run's artefacts
as evidence. What changed and why, compressed:

**Enforcement over prose.** The ledger rules were right and the live ledger broke
three of them. Pruning now fires at the two existing transitions (halt write, row
to done) on two mechanical triggers (>1 HALT BLOCK heading; table+Carry-forward
under half the file). Carry-forward entries name their consumer and die with it.
Correction rounds get open/close stamps.

**Authors enforce the run-commands-first rule.** The failed-query rule lived only
in the runner's file; the gates who write the commands never saw it. Now: gates
run any human-bound command once (read-only) or mark it UNRUN; the finale re-runs
all of them and ships nothing UNRUN.

**Pre-flight grew three checks, all launch-time:** dry-run the allowlist (the old
text asserted coverage; the actual settings refuted it), probe fixture health
read-only (one verify gate paid a 55-minute stage for that discovery at gate
prices), and echo the launch line on every invocation (the 11.5-hour halt was a
misread request). Model check gained its remedy: a wrong-model session passes the
intended model explicitly on every spawn.

**Recurring token cuts:** the action board rendered by a fresh cheap subagent,
never the runner at end-of-run context; worker finals capped (implementer 15
lines, gates 3); cron predicate is one grep, not a ledger read; primer appends
one line per fact; routing verified by exact quoted line, not heading.

**Autonomy:** classifier refusal = closed road (unprivileged path or report
blocked, never retry) — was invented mid-run and buried in a ledger, now standing
in the worker briefs; ambiguous resume prefers the invocation's range then stops
at launch, never mid-run; run-close standing-directive question goes to the
Decisions inbox, not chat.

**Rejected, with reasons:** splitting the resume section into its own file (a few
hundred tokens once, against re-creating the 25-minute wrong-file class through
indirection); moving the attacker's nine per-class anchors out of its brief (they
are rule+number, the settled hot-file format, not stories); a watchdog that kills
suspected prompt-stalled workers (a heuristic kill risks the two-writer incident).

**Net: the skill grew ~1.5 KB** (stories out, rules in) — paid once per session,
against per-run recurring savings. Judge next run: runner glue under ~30 min, no
gate paying for environmental discovery, no human-bound command failing in the
human's hands.

## Prose rejections are fixed by deletion, not refinement (2026-07-28)

**The incident, in shape.** An issue passed both gates on every acceptance
criterion, and its implementer had volunteered an extra meta-test beyond them.
The test was sound; a comment describing it over-claimed, and several
sequential review rounds went on that one comment. Every rejection was correct.

**The mechanism, which is the general lesson.** Each fix correctly deleted a
false claim and, in the SAME edit, added a replacement claim with its own
falsifiable surface — so the fix for an over-claim was itself an over-claim,
repeatedly. On this class, *more precise* and *more likely wrong* move
together.

**The rule.** A gate rejection on NON-EXECUTABLE prose is fixed by deleting the
claim, not restating it. One round. If a second rejection lands, the edit is
deletion down to the minimal sentence the gate cannot falsify, and the detail
becomes an issue with tests. Re-assertion is permitted only when the claim
becomes executable — a test cannot over-claim.

**The predictor nobody read.** The same over-claim class had already rejected
every earlier attempt on the issue when the runner priced the fix as a few
lines. Corollary rule: **any fix in a class with two or more prior rejections
is delete-only.** Check the strike record before pricing a fix.

**Two cheaper defects underneath it.** (a) The same claim had been copied into
the code comment, the primer and the issue file, multiplying every correction
and its gate cost. One canonical statement; everywhere else cites `file:line`
and asserts nothing. (b) Claims about LANGUAGE SEMANTICS were argued across
rounds when a REPL settles them in seconds. Drive a language claim before
writing it down.

**Not the lesson: that the hold was wrong.** Panel-reviewed, unanimous "right
call, wrong execution". Holding cost nothing — no migration in flight, no
second writer in the branch, and merging is the human's manual step anyway. The
rounds cost; the hold did not.

## Panel after the first run on the reworked chain (2026-07-28)

Five personas over the run and the skill — run economist, skill maintainer,
gate designer, implementer's advocate, auditor of the human's minute. Verdict:
the amendments stay (nobody voted revert), and the prose-deletion rule stays —
trimmed, and mirrored into the agent briefs that actually type and grade prose,
which never read the runner's step 5. The run itself: most issues came in under
estimate with few strikes; one whale, failing on prose-graded criteria,
consumed as much as the rest combined. Every rejection was individually
correct; the loss was structural.

What changed, compressed:

- **Two criteria-fault resets maximum per issue.** Each reset was lawful and
  together they were unbounded — the whale ran more than twice the promised
  attempts. The runner invented the cap mid-loop ("stated in advance so it
  cannot drift"); now it is written into step 8. Rejection classes are counted
  across resets — strikes reset, the class ledger does not.
- **Staleness keyed on the ledger file's mtime.** The handwritten
  `heartbeat <HH:MM>` failed twice in the very run cited as its evidence, on a
  runner who had already diagnosed the failure mode — knowing about a
  memory-enforced rule does not enforce it. Every transition updates mtime and
  nobody can forget to write it. The dangerous direction was a cron resuming
  into a live tree: the two-writer incident by another door.
- **Runner errors refund strikes.** One attempt's strike stood on the ledger's
  own "RUNNER ERROR" — a claimed shape mis-sorted onto the not-yours list, so
  the implementer was told to skip work that was in scope. A rejection ground
  attributable to the runner's brief is annulled from the strike and journalled;
  the symmetry criteria-fault already grants for spec fault. Not-yours items now
  cite the line that excludes them — a gate's summary sentence is not a warrant.
- **Gate-side prose rubric.** The delete-only rule was runner-only; the gates
  that priced the restatement rounds never saw it, and the final round split
  on severity, not fact. Both gate briefs now grade beyond-criteria prose
  non-blocking (unless a criterion names it or the artefact's purpose IS the
  claim — a guard's contract still blocks), enumerate every contradiction per
  round, name the defect class so repeats can be counted, and recommend
  deletion, never restatement.
- **Tenancy-empirical and prove-on-disk moved from run lore to the briefs.**
  Both bit twice: a review gate cleared a live cross-tenant leak by generalising
  a composite-FK trace onto a read no pin covered, and several distinct
  false-green mechanisms (a stale test-runner cache, no-op patches, silent
  reverts) burned both of one issue's gates. A tenancy claim is settled by
  deleting the predicate and running the suite; a mutation is trusted only
  after the cache is cleared and the mutated line echoed.
- **Blocked handoffs stop sizing prose fixes in lines.** A "two prose lines"
  fix — in a class where no prior attempt had survived the gate — became four
  sites in three files and an evening. The rule: state the strike-class record,
  present merge-now-fix-later beside fix-first with costs, and resolution is a
  procedure (one word from the human, one implementer, one narrow gate,
  unattended), not a supervised evening.
- **Prose-graded criteria flagged at authoring time** (step 1 + the attacker's
  class 8): a bar the gates grade by reading prose regenerates on every fix,
  because each edit mints a new falsifiable claim. This, more than difficulty,
  is what separated the whale from its clean siblings, whose bars were
  mutations, query counts and byte-identical captures.

Confirmed by the run, unchanged: the strike-2 re-check (multiple firings, real
criteria-faults found, and the discipline to return criteria-sound on weak
warrant); the max→high tier cut (nothing money- or auth-shaped reached the
merge read — what saved the leak was gate redundancy plus the runner driving
the dispute, not a tier); concurrent gates; ledger discovery by the
`Worktree:` line (right ledger first try among many committed copies).

**Judges, next run:** no issue exceeds two criteria-fault resets; zero
false-stale or missed-stale wakeups on the mtime predicate; a prose rejection,
if one recurs, closes in one delete-only round; no strike stands on a ground the
runner's own brief mis-sorted; the merge briefing opens with this run's header
only and reads in under thirty minutes.

## Inherit means inherit: the model override removed (2026-08-01)

Reverses "Model check gained its remedy: a non-Opus runner passes `model: opus`
explicitly", from the 2026-07-27 second panel. Found by three personas
independently in the 2026-08-01 cost panel, confirmed by its gate, and reversed.

**What the rule said.** "The session model is Opus 5. Agent files use
`model: inherit`, so every worker inherits it. If the runner session is not
Opus, pass `model: opus` explicitly on every spawn — never ask, never proceed on
inherit from a non-Opus runner."

**Three defects, in order of size.**

1. **It made the model dial unreachable.** The spawn tool's `model` parameter
   takes precedence over the agent definition's frontmatter. So on any non-Opus
   session the rule overrode every per-stage `model:` value in every agent file.
   Nobody could test Sonnet on one stage, or on all of them, without first
   finding this line. Launching on Sonnet looked like it bought Sonnet workers;
   it would have bought a Sonnet runner driving Opus workers, at a higher bill
   than either.
2. **Its premise was already false.** "The session model is Opus 5" —
   `harden-issues-attacker.md` had pinned a different model since it was
   written, and `SKILL.md`'s own who-runs-what table says each role carries "its
   own brief, model and effort".
3. **It overrode a deliberate pin.** "Every spawn" includes the pinned one. The
   author did not contemplate that case, and the rule as written breaks a stage
   whose tier was chosen on purpose.

**Never fired.** Every recorded run launched on Opus, so the branch was never
taken. Untested text that would have taken effect the first time anyone ran the
model experiment.

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

## Post-run revisions (2026-08-02)

Three rules promoted from that run's decisions inbox, plus one pre-flight check.
Gates drill mutations on scratchpad copies, with one tree writer at most while
gates run and checksums re-checked at staging. A published checksum is
re-stamped whenever a later round moves its file, and diff commands anchor to
`main...HEAD`. A figure or refutation passed onward is re-derived from a source
that cannot drift, with the source named. Pre-flight confirms the dependency
directory exists before trusting any green.

**The two-writer incident.** During one issue's gates, a source file on disk
silently reverted to its pre-fix form — guard absent, 478 lines — for over two
minutes, then restored itself. Both gates saw it independently. The verify
gate's own mutation drill was the writer; the review gate's backup, taken inside
that window, captured the mutant, so "restore from my backup" would have shipped
the defect the issue existed to fix. A checksum re-checked at staging time
caught it. The next issue's gates ran the new way — verify drilling on
scratchpad copies, review never writing — and the tree file held one checksum
from gate open to gate close. The old text said gates "touch no code" while
requiring mutation drills; the drills were the code-touching. Both statements
could not stand, so the drills moved off the tree.

**The expired-checksum incident.** Both gates on one issue published staging
checksums for the same test file. A correction round then added a fixture table
to it. A merge reader running either command got FAILED — the precise alarm the
gates wrote them to raise, with nothing wrong. The finale caught it and
re-stamped, but only because the analysis pass looked; the rule makes the
re-stamp part of the correction round itself. Same class: a `git diff --numstat`
handed to a human printed nothing after commit, and empty was also what a
reverted-and-committed fix would print.

**The drifting-number incidents, three in one run.** A figure transcribed into
a retry brief unchecked (4,687,680 for 4,688,640 — the implementer caught it);
a causal refutation asserted from a grep scoped to one directory when the call
sat one import away in another (the conclusion survived on the gate's reasoning,
not the runner's); hand-written journal timestamps that ran an hour ahead and
were corrected against `git log`. None was charged to an implementer; all three
were the runner deriving from its own earlier statements.

**The false-green launch.** The worktree shipped without its dependency
directory and the typecheck exited 0 anyway — the compiler resolved off a global
install with no repo types loaded. Caught at launch because the runner installed
dependencies on principle. Now a named pre-flight check rather than a habit.

**The judge, next run:** whether the gates' recorded open/close checksums
actually appear in their verdicts, and whether the runner re-checks them at
staging. If either half goes missing, the rule has become prose and wants a
mechanical trigger, the way ledger pruning did.

## Post-run revisions (2026-08-03)

Two of the three candidates the finale left in the decisions inbox were taken.
Both are now in SKILL.md step 5, beside the prose-deletion rule they extend: a
claim may not say something is the only copy, and a recorded cause is tested
against a control rather than merely observed. The third was declined in its
prose form.

**The run's shape, which is why these two exist.** Four issues, ten gate runs,
one rejection (annulled as a criteria fault), zero strikes standing, 52% under
the estimate. And **ten stale-prose defects against zero code defects that
reached a gate uncaught.** Every one was a sentence true when written and false
once something else moved. That ratio, not the schedule, is what the run
measured.

**The only-copy incident.** The primer carried an inverted jsonb claim. The
runner deleted it and wrote, in its place, that one issue's file was now the
sole home of the measured record. Three other copies existed. The repair for a
stale-prose defect was itself a stale-prose defect of the same class, written
by an agent that was following the deletion rule correctly. That is the whole
argument for the new rule: deletion tells an agent what to remove and says
nothing about what the replacement may assert.

**The observed-cause incident.** A scratchpad script could not import a package.
It worked when run from the worktree root, so the primer recorded the cwd as the
cause. The real cause was a `node_modules` symlink; the import succeeds from
any directory holding one. The line also existed to correct a previous primer's
wrong cause, which is where a wrong cause costs the most.

**The third candidate, declined in this form.** "A correction round re-stamps or
expires every checksum it invalidates before it closes" is ALREADY promoted —
2026-08-02 — and a correction round broke it anyway. The ruling is that a rule
which has now failed after promotion does not want restating. The finale's
mechanical form goes to the architecture session instead: publish every checksum
as a command a human can run (`shasum -a 256 -c` against a stamped file), not a
digest a human must trust. It fails loudly the moment a correction round moves
anything, and it would have caught all ten of this run's defects rather than one.

**A placement finding, not yet acted on.** The existing checksum-expiry rule
sits in the Finale section (SKILL.md step 2 of the finale), not in step 5 where
a correction round is actually closed. A runner reading step 5 to close a round
never meets it. Whether the mechanical form supersedes the placement question,
or the rule should also move, is for the architecture session.

**The judge, next run:** whether stale-prose defects fall below ten with two
more prose rules in place. If they do not, prose rules are not the instrument
and the mechanical form should be bought without further evidence.

---

## The seven rules from the 2026-08-03 batch (adopted 2026-08-04)

Thirteen issues, one strike and it was annulled on a criteria fault, twelve
issues minted. Every rule below was written by something that went wrong in that
run, and each is now in `SKILL.md` or an agent file rather than only here.

**1. Gates drill in a private whole-tree copy, at a path naming the issue and
the role.** Two collisions in one day. One issue's gates both chose the
scratchpad name `drill`, and one gate's `rm -rf` destroyed the other's copy
mid-run. The next issue's gates then collided inside the run's own tree, where
one briefly read the other's live mutant. The second case is the reason a naming
rule beats a detection rule: checksums at gate open and close cannot see it,
because the file is restored before either stamp is taken. In
`run-issues-verify-gate.md` and `run-issues-review-gate.md`.

**2. Never `git checkout -- <path>` on a branch with uncommitted work.** It
restores from `HEAD`, where the implementer's work is not. One implementer used
it to undo a drill and deleted its own uncommitted work instead. The repair is a
scratchpad copy taken before the mutation. In the implementer and both gate
files.

**3. Implementers never self-commit; the runner commits after both gates pass.**
Two of the first three implementers on this run committed before the gates
opened. Neither caused harm, which is exactly the trap — a self-commit silently
changes what "the diff" means to a gate already reading one, and the runner then
has to hand out explicit commit ranges. Where it has already happened, record it
and give the gates the range rather than reverting. In `SKILL.md` step 4 and the
implementer file.

**4. A ruling that creates work gets its issue number in the same sitting.** A
ruling settled an open question by splitting a road out of scope. Nine hours
later no issue existed and the only trace was one phrase inside the original
issue's own file. A verify gate happened to notice, and it was minted then.
Nothing was watching for it. A ruling with no artefact cannot be told apart from
a ruling nobody made. In `SKILL.md`, "Nothing finishes vaguely".

**5. Facts carried into spawns are re-derived from source at pre-flight, with a
citation.** The batch plan said a workspace helper "answers null when the count
is not one". It orders its rows by creation time and returns the OLDEST,
answering null only at zero. The runner repeated the false version for nine
hours before a gate refuted it from the migration file. The two versions fail in
opposite directions — the false one predicts a loud break, the true one a silent
misfile — so the error stayed invisible while it did damage. In `SKILL.md`,
Pre-flight.

**6. Every citation carries its repo-relative path in full, every time.** A
cross-session sweep found nine ambiguous citations across six issues. The worst
used a bare filename eleven times where the tree holds two files by that
name; the wrong one resolves to plausible code, so the reader finds a defect
that is not there and an implementer can lose a strike to it. Now the third of
the claim rules in `SKILL.md` step 5.

**7. The briefing's narrative sections are filled as each issue closes.** Four
sections were still empty placeholders when the finale opened the file,
including the one that should have carried a deploy step — the single action in
the batch that changed what a customer reads. A reader starting at the top met a
stale test count before reaching its correction 100 lines down. An empty section
reads as "nothing to report". In `SKILL.md`, run state.

**What this run also proves about the strike-2 re-check.** One issue was
rejected twice by both gates. The criteria re-check found the bar it failed on
had never been written — both attempts met every criterion as written — and
annulled both strikes. It also refuted the runner's own hypothesis about the
fix. The re-check earns its cost.

## The twin of a deleted claim (2026-08-11)

**A correction round searches the branch for a twin of every claim it deletes.**
Four over-claiming sentences were deleted across the four issues of one run, and
a fifth reached main. The one that escaped was the same sentence as one that had
just been deleted, sitting one directory away in the route the test guarded. No
gate reads two files for one claim, and no gate reads two issues at all, so the
second copy had nobody looking at it. Every one of the five was found by a person
or a gate reading prose against code; no test caught any of them.

Adopted narrowly, and nothing wider: an authoring-time rule was rejected on the
ground that the four caught instances cost about two minutes each and no strike,
so a rule charging attention on every comment in every issue would be the more
expensive mistake. In `SKILL.md`, step 5, under the delete-only prose rule.

## Small-issue coalescing is retired (2026-08-15)

**The permission is gone from `SKILL.md`. Do not bring it back without new
evidence, and the evidence would have to be a batch, not an argument.**

What it was: up to two adjacent trivial issues (copy, config, no logic) could
share one implementer spawn and one combined gate spawn. It was in the skill from
the day it was written and it never once fired.

On 2026-08-12 a ruling asked for two runs to record the decision, then a verdict.
**Four runs recorded it and the count never reached two.** Two of them
independently call themselves "run one of the two" in their merge briefings;
none calls itself run two. Nothing durable held the count, so each run re-derived
"run one" from the ruling's text. That is the ask-an-agent-to-remember failure
mode in the wild: the instruction asked an agent to remember a total across
sessions, and remembering does not work.

What the four runs did show, which is why the substance was answered instead of
building the counter: **a qualifying pair existed twice and qualified zero
times**, always because at least one issue in the batch carried logic. One run
had the cleanest pair yet — one issue was a single `if`, some cases and an
`.env.example` block — and it failed on its sibling, a thirteen-file whale.

The mechanism that starves it is structural and postdates it: a lighter
single-session road for trivial pre-specified fixes, adopted outside this skill
on 2026-08-12, takes exactly that class of work, so trivial issues no longer
queue for a run at all. The permission was neither useless nor unread. It was
unreachable.

The fact that would reopen it: a real batch of pure copy or configuration fixes
reaching `/run-issues`. Some still can, because the lighter road needs an issue
naming a test that fails today and a pure copy change often has none. If such a
batch appears, the cheap answer is to make the count durable, not a fresh
permission written from memory.

## The class-(a) slim — evidence moved out of SKILL.md (2026-08-23)

A review walked `SKILL.md` for passages that are pure history and mapped them.
Eighteen of them moved here. Every rule they illustrated stayed in the skill, and
`test_skill_structure.py` asserts both halves: the anchor still loaded, the story
no longer loaded.

Read this section when you want to know why a rule is worded the way it is. Do
not read it to run anything.

**The full suite runs without the canonical env file.** Sourcing it cost one run
three red suites in one night, each investigated as a regression and each caused
by nothing. It had never been written down anywhere, which is why three agents in
one run each discovered it the hard way.

**The round header, and why it is a block rather than a rule.** The rule that a
brief names the place and not only the act failed a third time on 2026-08-16.
Three faults, one shape, and none of them a prohibition: a brief said to drive a
production build in a browser and named no harness, so the implementer picked the
blind one and drove a whole acceptance walk in it — one round, on the largest
issue in the batch. A settlement went to the implementer and the verify gate and
not to the review gate, which then rejected on clauses the settlement had already
answered — one annulled ground, one gate round. A gate brief named the register
and the issue file, and not the merge briefing, so the gate found a file of that
name in the main checkout and appended five lines to a stale artefact of a merged
run.

**A prohibition names the system, not the verb: the other two faults.** One run's
three faults shared one shape. The one kept in the skill is the writable-database
example. The other two: "a probe script needs a directory holding `node_modules`"
named no home, so three files landed at the shared worktree root; and a brief
naming no register path sent two gates to the worktree copy instead of the main
checkout's.

**Why the verdict check is a check and not a reminder.** Two adversarial gates
died at the weekly usage limit during one workflow audit and wrote nothing at all.
Both times a person recovered the work by reading a transcript by hand, and
nothing mechanical noticed they had returned empty. Separately, one gate's
175-line verdict was left in the wrong tree and survived only because the finale
diffed two checkouts for an unrelated reason. The place-not-only-the-act rule was
adopted on 2026-08-09, one of its own worked examples is a brief that sent two
gates to the wrong register copy, and the same fault recurred four days later. A
second telling would not have worked either.

**The citation pass, and what it is worth.** The fourteen issue files one run
built went from 1 broken citation to 251, and twelve open backlog issues nobody
opened went from 0 to 28, four of them takeable in the next batch. The mechanism
is not carelessness: one issue's citations were verified correct at 08:50 and
another issue moved the same file at 13:11. Nothing re-read them, because the only
stage that looked was the finale, by which time thirteen commits had landed.

**A self-commit does no visible harm.** Two of the first three implementers on
one batch committed before either gate had opened. Neither did harm, which is what
makes the class hard to see.

**The scopeless negative that shipped.** The rule was advice in the skill from
2026-08-09 and was broken the same night: a wrong ruling shipped and survived only
because an implementer refused it on evidence.

**Searching the branch for a twin.** On one run four deleted claims had twins and
a fifth reached main, because its twin sat one directory away in a file the
correction never opened. The search was adopted narrowly: no authoring-time rule
came with it, because the four caught instances cost two minutes each rather than
a strike.

**The three claim rules, illustrated.** One primer asserted an issue file was the
only copy of a measured record while three others existed — and that sentence was
written as the REPAIR for a stale-prose defect, by an agent following the deletion
rule. The same primer recorded that a package import succeeds "when node is
launched from the worktree root", having watched it succeed there; the cause was a
`node_modules` symlink, so the import succeeds from any cwd that has one and fails
from every cwd that does not. And a cross-session sweep of one batch found nine
ambiguous citations across six issues, the worst a bare filename used eleven times
where the tree holds two files by that name.

**The three runner errors of one run.** A transcribed figure off by 960; a
refutation from a grep that missed the call one directory over; and hand-written
timestamps an hour ahead of the clock.

**What uncapped criteria resets cost.** 7 attempts and 14 gate runs where the
skill promises three.

**The ruling that had no issue number.** A ruling settled an open question by
splitting a road out of scope; nine hours later no issue existed, and the only
trace of the split was one phrase inside the original issue's own file. A verify
gate happened to notice, and it was minted then. Nothing was watching for it, so
nothing would have caught it a day later.

**Why staleness is the file's mtime.** The handwritten `heartbeat <HH:MM>` field
failed twice in one run, on a runner who had already diagnosed the failure mode.

**The launch line that printed too late.** On one run the line printed at 22:22,
after the first implementer had already finished, so there was no window left to
interrupt.

**The carried fact that was never re-derived.** One run's plan file said a helper
"answers null when the count is not one"; it actually ordered its rows by creation
time and returned the OLDEST, answering null only at zero. The runner repeated it
for nine hours across many spawns before a gate refuted it from the migration
file.

**No agent file pins a model.** `harden-issues-attacker` was the last, and it
moved to `inherit` on 2026-08-02, so the tier is chosen at launch.

**What worktree readiness costs, and the green it closes.** Adopted on 2026-08-07
on the question of what it costs in tokens: it saves them. The failure it closes
was measured — a fresh worktree ran its typecheck to exit 0 with `node_modules`
absent, because the compiler resolved off a global install and never loaded the
repo's own types.

**The six hours the allowlist bullet cost.** On 2026-08-14 a verify gate sat on a
dialog asking to start the dev server, with its own task counter reading
6h 00m 05s. A person found it by looking at the screen. The bullet was already
there and ran correctly: the runner enumerated the classes the old text named and
dry-ran all of them. It read an illustrative list as a complete one.

## Three experiments, pre-registered 2026-08-23 (arms and thresholds, before any run)

Written before any of them ran. The effort trial that closed on 2026-08-23 worked
because its threshold was fixed in advance and the rule was taken as written when
the reading went against the hypothesis. These three get the same treatment. A
threshold argued after the number arrives is not a threshold.

Order: the medium-rung validation first, because it costs a scratch session rather
than a run. Then slim-then-measure on the next real batch. Compaction last,
because its arms need a run each.

### 1. Medium-rung validation

**The question.** Is `medium` a distinct effort rung at all, or does it resolve to
something else? Nothing has established this. The trial that just closed ran a
whole batch at `medium` and read 1.22M weighted tokens per issue, and that number
is consistent with `medium` being a real rung, with it resolving silently to
`high`, and with it resolving to nothing. Agent frontmatter accepts `effort:
banana` without complaint, so an unrecognised value is known to load quietly.

**Design.** The interleaved experiment recorded above, repeated. Identical agents
on one enumeration task, differing only in the effort line, runs interleaved so
drift in the service hits every arm equally. Five runs per arm.

**Arms.** `low`, `medium`, `high`, `xhigh`, plus two that exist to grade the
measurement rather than the dial:

- A second `high`, under a different agent name. This is the noise floor. Two arms
  that are the same thing must land together, or the threshold below is
  meaningless.
- `effort: banana`. Where nonsense lands tells us what happens to a value the
  loader does not recognise, which is the failure mode `medium` might already be
  in.

**Measured.** Mean wall-clock and mean output words per arm, as in the table
above.

**The threshold, fixed now.** `medium` is a distinct rung if its mean wall-clock
differs from `high` by 10 per cent or more, and the two `high` arms differ from
each other by less than 10 per cent. Both conditions, or the answer is "not
established", which is not the same as "identical" and must not be written up as
one. If the two `high` arms differ by 10 per cent or more, the task is too noisy
to grade effort and the experiment reports that instead of a rung.

**What a result buys.** A confirmed rung makes a per-seat effort trial worth
running. An unconfirmed one retires `medium` from every future proposal, which is
the cheaper outcome and the more likely one.

### 2. Slim-then-measure

**The question.** Did the class-(a) slim change what a run costs?

**Design.** Per-issue weighted tokens from `orchestrator_cost.py --days 7`, on
comparable batches before and after the slim, inside one seven-day window. Same
session effort on both sides, `high`. Comparable means a similar issue count; the
readings already on file are four issues and five issues.

**The honest answer is written before the run, because it will be tempting to
claim otherwise.** The slim took `SKILL.md` from 902 lines to 858. That is 5 per
cent of one file. Against it, the two batches already measured at `high` read
0.96M and 1.51M weighted tokens per issue, a spread of 57 per cent driven by issue
mix alone. One batch after the slim cannot separate a 5 per cent input change from
that. So:

**The threshold, fixed now.** The slim is recorded as having no measurable effect
unless the post-slim reading falls outside the 0.96M to 1.51M band already
observed at `high`. Inside the band, the entry reads "no measurable effect at this
sample size" and nobody writes that the slim saved tokens. Outside it, the reading
is interesting and still not attributable to the slim without a second batch.

**Why measure at all, then.** To catch the opposite result. A slim that moved a
rule somewhere the orchestrator no longer reads it costs correction rounds, and
those show up as a higher number, not a lower one.

### 3. Compaction

**The question.** Does compacting at an issue boundary cost less than carrying the
context, and does it cost less than halting and resuming?

**Arms.** Three, one run each:

- Boundary compact by hand, typed by the human at each issue boundary. It is
  manual because it has to be: no skill, hook or tool in this harness can trigger
  compaction, established by walking the tool inventory. Adopting this arm means
  adopting a standing manual step, and that cost belongs in the decision.
- Deliberate halt-and-resume at each issue boundary, through the existing halt
  block.
- Control. Neither, as runs work today.

**Measured.** `orchestrator_cost.py --days 7`, per-issue weighted tokens, plus the
runner-error count at finale for each arm. A cheaper run that makes more mistakes
is not cheaper.

**Preconditions, both before arm one starts.** The citation baseline written to a
file under `.scratch/<feature>/`, and the road choice written into the issue's
ledger row so a later reader can tell which arm produced which number. The effort
trial nearly died on exactly this: its first launch printed `high` when the picker
said `medium`, and only the stamp rule caught it.

**The standing rule this experiment may not contradict.** Post-compact equals
resume: a compacted context is treated as a fresh session that must re-read the
ledger, and the compaction summary is not evidence of anything. An arm that reads
its own summary instead of the ledger has measured a different thing.

**The threshold, fixed now.** An arm is adopted if it cuts per-issue weighted
tokens by 15 per cent or more against the control, with no increase in runner
errors at the finale. Under 15 per cent, the manual step is not worth a person's
attention and the answer is no.
