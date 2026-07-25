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

### Known residual risk

An issue whose acceptance criteria were wrong **when written** is caught late by
decision 9 and not at all by the gates, since every gate grades against the issue.
The early fix — a blind-spot pass and rubric-shaped criteria at authoring time —
was deliberately deferred to its own session.
