# run-issues — settled decisions and the incidents behind them

Read this before changing how the run works. Do not read it to run one — the
skill and the agent files are self-contained. Nothing here is loaded into a
subagent's context.

Newest section last.

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
to the human, a `Hardened:` stamp on resolved issues — and issues arrive with a
rubric-shaped template (`Status:`, acceptance criteria, `## Must still be true`)
already in place. This skill's only coupling is the pre-flight stamp check:
launch-time information, never a gate. Grilled and settled 2026-07-27 from two
runs' evidence (112, 114, 110, 117, 122, 124, 125, 126 all shipped criteria
faults through green gates); the design brief lives in a memory file, not
published here.

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
runs `/grilling` only where a real reporter exists. Against a local `.scratch/`
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
