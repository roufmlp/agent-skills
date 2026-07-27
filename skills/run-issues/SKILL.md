---
name: run-issues
description: Autonomously implement a range of tracker issues one by one — a fresh implementer per issue working test-first, adversarial verify and review gates, two-strike escalation, ledger-driven resume across usage limits, and a human merge gate at the end. Use when the user wants issues implemented sequentially without supervision ("run issues 05-09", "implement all remaining issues", "continue until all issues are done"), or to RESUME an interrupted run ("/run-issues resume").
argument-hint: "one issue, a range (05-09), an explicit list, or 'all'"
---

# Run issues

One thin runner session implements a range of issues end to end. Every worker and
gate is a subagent with a fresh context. After launch the user is needed once: the
merge read.

Settled design decisions and the incidents behind them live in `decisions.md`,
next to this file. Read it if you are tempted to change how the run works —
not to run one.

## Scope argument

`/run-issues 05` · `05-09` · `13c 20 14 22` (explicit list, run in that order) ·
`all` (every remaining `ready-for-agent` issue in tracker order).

Run in the order given. Some issues depend on earlier ones and say so in their own
file ("run NN first", "this assumes NN has landed"); most do not. A blocked issue
stops its dependents, not the whole run — see the per-issue loop.

For `all`, resolve the scope from each issue file's `Status:` line and take only
clean `ready-for-agent` issues. Print the resolved list in the launch message.
Skip `ready-for-human`, `in-progress`, `needs-*` and anything `done`. If a
`ready-for-agent` issue looks superseded by merged work, set it `needs-harden`
with one line of why and skip it — never build a stale issue blind. `needs-harden`
is the return path: `/harden-issues` takes it as in-scope.

## Who runs what

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the runner never pastes a brief.

| Stage | Agent type | Effort |
|---|---|---|
| Implement | `run-issues-implementer` | high |
| Third attempt after two rejections | `run-issues-implementer-escalated` | high |
| Verify | `run-issues-verify-gate` | high |
| Review | `run-issues-review-gate` | high |
| Review, diff changes money/auth/secrets | `run-issues-review-gate-critical` | high |
| Coherence finale, once per run | `run-issues-finale` | max |

Spawn prompts carry **only** what varies — issue ID, paths, rejection reasons.
Everything stable already lives in the agent file, where it caches.

## Run state — files, not contexts

In the main checkout, under `.scratch/<feature>/`:

- **`run.md`** — the ledger. Status table plus a **Carry-forward** section, plus
  the one live halt block if the run is halted. Nothing else. Every spawn reads
  it, so every line in it is billed a dozen times a run.

  **It is pruned, not appended to.** Three things go in the journal instead, and
  the runner moves them the moment they appear: a **superseded halt block** (the
  new one replaces it — delete the old one, do not mark it), the **finale
  write-up** (the ledger carries the stage and the verdict, one line each; the
  reasoning is narrative), and any **verdict story** longer than its row.
  The prune runs at the two transitions that already exist — every halt-block
  write and every row moved to `done` — not as a separate chore. Two mechanical
  triggers, either one means prune before the next spawn: more than one
  `## HALT BLOCK` heading, or status table plus Carry-forward under half the
  file (a measured ledger once hit 15.4 KB with the status table at 13% —
  decisions.md).
- **`run-journal.md`** — the narrative, append-only. Every log line goes here:
  what each attempt did, verdict stories, dead ends. Subagents never read it. It
  is read exactly twice — by a resuming runner, and by the finale.
- **`primer.md`** — the codebase primer. Fresh subagents read this instead of
  exploring. The first implementer creates it; every implementer appends what it
  learns. Exploration is paid once per run. **A new run starts a new primer** —
  rename the old one and never read it. It is written by implementers about
  implementer-written code, so it is orientation, never authority: what ought to
  be true lives in `docs/patterns.md`, on main, and outranks both the primer and
  the code.
- **`merge-briefing.md`** — the merge-read briefing, built up as the run goes.

Ledger statuses: `queued → in-progress → gates → done`, plus `correction`
(between `gates` and `done`, when taken) and `blocked`. Both gates run under the
one `gates` status. Only the runner writes the ledger. Gates write
verdicts into issue files. Everyone appends; nobody rewrites another's section.

**Stamp every transition with the local time** (`HH:MM`, dated on the day's first
entry) — the run's own timings are the only evidence for whether the pipeline is
worth changing. A correction round is a transition too: its row gains
`correction: open HH:MM → closed HH:MM`. One run took correction rounds on two of
three issues and neither's cost could be reconstructed afterwards.

**Carry-forward** is what the runner curates for future spawns: shared-quota state,
traps discovered, conventions later issues must follow, do-not-tidy lists. A
learning that lives only in the journal survives only if the runner remembers to
re-brief it. **Every entry names the issue(s) it serves**, and the runner deletes
it when its last consumer goes `done` — an unexpired entry is billed to every
remaining spawn, and the waste grows with the square of the batch. A human action
taken mid-run (a SQL fix, a console change) is recorded here with its **observed**
effect, not its intended one: one has already silently failed to land.

## Shared external quotas

Any per-window cap on an external system is run state, owned by the runner.
Carry-forward holds the last observed status, its timestamp, and who holds the
window. **Two agents never hold the same quota at once.** Schedule live halves
first, while the window exists.

## Per-issue loop

1. **Settle the road before spawning.** If the issue admits more than one
   plausible approach and no triage decision picks one, choose it now and put the
   choice — and the roads rejected — in the spawn prompt. Minutes here against
   hours later: 17 minutes versus 3h52m on one measured pair (decisions.md). Then
   spawn `run-issues-implementer`.

   **Size the issue while settling the road**, and write the estimate in its
   ledger row — an overrun then reads as live signal instead of archaeology.
   Where the given order and dependencies permit, schedule the big ones last:
   runs halt on usage limits, and a whale mid-batch starves the cheap issues
   queued behind it. Never split an issue yourself — a runner-invented sub-issue
   is an untriaged spec. An issue too big to be one issue goes back through
   `/harden-issues`.
2. **Read its final message before doing anything else.** If it reports unfinished
   work, the issue is not gate-ready — re-spawn to finish it, or mark `blocked`.
   If it reports the acceptance criteria are *wrong* rather than unmet, spawn a
   review gate to confirm that claim only; if confirmed, set the issue
   `needs-harden` with the evidence and move on. Never build to criteria a worker
   has shown to be wrong.
3. Spawn **both gates in one message, concurrently.** Neither reads the other's
   verdict — verify drives the app, review reads the diff — so serialising them
   buys nothing and the wall clock is the slower of the two rather than their sum.
   Use the review `-critical` variant when the diff **changes** money computation,
   auth or secret handling (touching a file that has a price field does not
   count). If verify rejects, read the review anyway: its findings still route,
   and its work is already spent.

   **While the gates run, the runner preps issue N+1, read-only:** settle its
   road, size it, pre-write the spawn prompt, prune the ledger, run the fixture
   pre-check (below). None of it touches the tree, so single-writer holds; on
   gate-pass only routing-verify, lint and commit remain serial. On one measured
   run the runner's serial glue was ~49 minutes, all spent after stages returned.
4. Both pass → **verify the routings**: grep each target file for the exact
   line the gate quoted as appended — gates end each routed finding with that
   quote, and the runner greps the string, never a heading (a heading-level
   check has false-negatived routings that were present). A declared routing is
   not a routing. Check the verify gate's
   `Drove:` list against `git diff --name-only`; a route the diff touches and the
   gate never fetched is an incomplete verdict, not a pass. **Run lint** — it costs
   nothing and catches the shape defects no per-issue gate can see. Then commit,
   staging **explicit paths only** — never `git add -A` or `.`. Glance at
   `git status` and investigate anything unexplained *before* committing.
5. **Both pass but a verdict enumerates follow-up items** (a gap on the issue's
   own invariant, a test the evidence says should exist) → ledger `correction`,
   not `done`. Re-spawn `run-issues-implementer` with the enumerated items, the
   correction marker, and nothing else — a fresh context, never a message to a
   live agent. On resume, a `correction` row is re-spawned the same way; it is
   still the one round. One round maximum; the scope is the verdicts' list —
   anything bigger, or anything a second round would need, is minted as an issue
   instead.
   **While any row shows `correction`, no new implementer spawns** — that status
   is what makes a second writer in the tree unrepresentable. The round closes
   when the runner verifies each item's *named evidence* (the test now exists and
   is green, the mutation now reds), not just that files were touched. Then
   commit and `done`. A correction round is not a strike.
6. Ledger `done`; set the issue's `Status:` to `done — on branch <branch>,
   unmerged` (gate history goes in the body — `all` runs parse that line).
7. A gate rejects → re-spawn the implementer with the written reasons. If **both**
   reject, that is still ONE retry carrying both verdicts, and one strike, not two.
   Then re-run step 3 in full: both gates, on the new diff. A gate that passed the
   previous attempt has not seen this one.
8. **Two strikes → re-check the criteria before buying a third implementer.**
   Spawn `harden-issues-attacker` in strike-2 mode with both verdicts: classes 1,
   5 and 9 only, evidence or silence, and no waiting. One of three outcomes:

   - **A fault in the criteria, with a citation** → it corrects the issue file and
     says what changed. Re-spawn `run-issues-implementer` with the corrected
     issue. **Not a strike** — the earlier attempts were graded against a spec
     that no longer exists.
   - **Criteria confirmed sound** → spawn `run-issues-implementer-escalated` with
     the issue and both verdicts, but none of the failed reasoning.
   - **A fork it cannot settle from evidence** → ledger `blocked (criteria)`, the
     question goes to the merge briefing, and the run moves to step 9. **It never
     waits for an answer.** A question mid-run is a blocked issue, never a stall.

   This is the one case where a hardening pass may touch an issue a live run
   holds, and only because the run has stopped: no implementer is in the tree, and
   the runner spawns nothing else until the re-check returns.
9. If the third attempt also fails a gate → ledger `blocked`. **Then work out what
   depended on it.** Mark every queued issue that declares a dependency on the blocked one
   `blocked (depends on NN)` and skip it; carry on with the rest. The run halts
   entirely only when nothing independent is left.

   Dependencies come from the invocation where it declares them, and from the
   issue files' own cross-references. **Where you cannot tell whether a queued
   issue depends on the blocked one, treat it as dependent and skip it.**

   Say in the merge briefing which issues were skipped and for what, so the next
   run picks them up rather than rediscovering them.

Small-issue coalescing: up to two adjacent trivial issues (copy, config, no logic)
may share one implementer spawn and one combined gate spawn. Anything with logic
is one issue per spawn.

## Nothing finishes vaguely

An issue leaves the ledger as `done` or `blocked`. Never "done, mostly". Anything
unfinished goes into its one named home before the ledger moves, and the merge
briefing lists every such entry:

- Acceptance unmet → stays `blocked`.
- Waiting on the user (secret, env var, OAuth client) → the project's
  pending-actions file, if it has one, as a numbered action, with one line of what
  is blocked on it. Code may still complete around it. `/daily-brief` surfaces it;
  the run never waits.
- Follow-up found mid-issue → a new issue file, or a fold-in section in the next.
  Minting is **write-only**: the file records evidence already in hand, and
  nobody investigates further mid-run. The merge briefing lists what was minted.
- Gaps tests cannot reach → noted for the post-deploy `/parallel-hunt`.
- Bugs found **outside** the issue's scope → routed to one of the homes above.

Handoff documents are never the home for any of this.

## Branch and human gate

The runner owns the feature branch; **main belongs to the human.** The worktree
has **one writer** — the current implementer, plus the runner committing. Anything
spawned beside the per-issue loop works in the scratchpad, never the run's tree.

Commit per issue after gates pass. **No merge between issues.** Merge to main is
the human's decision, taken once at run end: the run stops at `awaiting-merge`,
and `/daily-brief` carries the merge read to them and executes their answer. A
single-issue run therefore runs the full finale and stops there too — that stop is
the design, not a stall.
Extending a finished run to a new issue is a NEW run: merge first, then invoke
again from main.

## Finale — fully automatic

After the last issue, in order, tracked in the ledger as
`finale-mechanical → finale-judgment → awaiting-merge` so an interrupted finale
resumes rather than re-running:

1. **Mechanical.** Full typecheck, full test suite, and a build from a **cold
   cache** (delete whatever the project's build cache is — `.next`, `dist`, `target`
   — because a warm cache agrees with whatever it already compiled). Committed run state is build input: the ledger, journal and
   issue files sit inside the repo, so whatever scans the project scans them too.
   Confirm the toolchain excludes them, and treat a code fence in a write-up as
   something the build may try to compile. Failures reopen the offending issue
   through the per-issue loop.
   Then a preview deploy, if the project has one. Where a standing decision says
   to skip it, say so in the briefing; never work around it; never re-litigate it
   per run.
2. **Judgment.** Spawn `run-issues-finale`. Its verdicts plus `merge-briefing.md`
   become the merge briefing.

   **Every command the briefing hands a human runs once first, against the state
   it will actually meet.** A pre-migration check runs before the migration, on
   the pre-migration schema. If it cannot run there, it is the wrong check. (On
   one run a gate wrote the check, the runner copied it, neither ran it — and the
   human's first instruction errored with `column does not exist`. decisions.md.)
   The gate briefs carry the same rule from the author's side; the runner
   re-checks when assembling.

   If the finale fails on a usage limit, leave the ledger at
   `finale-judgment`, write the halt block, and revive after reset — never
   downgrade it to save the wait, and never declare the run complete with the
   judgment half unrun.
3. **Regenerate the action board** — `.scratch/<feature>/board.html`, the one-page
   human view of `merge-briefing.md`. Live actions only, grouped by when, one line of
   what and one of why each, ticks persisted in localStorage. Keep the existing
   styling; send it with SendUserFile. **A fresh cheap subagent renders it** from
   `merge-briefing.md` plus the old board — never the runner itself, whose context
   is at its most expensive by run end, and the old board's bytes never enter the
   runner. `merge-briefing.md` stays the source of truth,
   and `/daily-brief` reads that file, never the board.
4. **Recommend follow-ups; start none.** One exception is mandatory:
   - **The post-deploy smoke walk**, owned by `/daily-brief`. The run ends at
     `awaiting-merge` and the brief carries it to the human with the branch head
     SHA they are approving. When they write `merge`, that session merges,
     rewrites the `unmerged` statuses, deploys, and drives a READ-ONLY walk of the
     **deployed** site on real data before the human walk: every list page and its
     filters and search, every detail page, the send and receive surfaces as far
     as read-only allows. Read-only means no permission risk, so there is no
     reason to skip it.
   - Recommended after it: a `/parallel-hunt` round on the live system. It hunts
     the seams between issues and against live external systems — the class of bug
     per-issue gates cannot see. Its `deferred` entries become the next run's
     issues.
   - Only if the finale's findings are structural: an architecture-improvement
     session on a clean tree.

## Resume across usage limits

**The ledger resumes a run. The cron only saves short waits** — it reaches no
further than a five-hour window the same session sits through. A weekly limit
resetting days out is resumed by a human re-invoking `/run-issues resume`.

**The ledger carries an owner heartbeat.** One line at the top: `Owner: <session>,
heartbeat <HH:MM>`, rewritten on every ledger touch. A long implement attempt moves
no status line for an hour, so "no progress" cannot mean "dead" — only a stale
heartbeat can.

**The owner line is cleared the moment the run stops owning the tree.** Reaching
`awaiting-merge`, or halting, rewrites it to `Owner: none — <awaiting-merge|HALTED>
<date> <HH:MM>`.

Create the wakeup anyway at launch (every ~29 min): "Check `grep -m1 '^Owner:'
<run.md>` — do not read the rest of the file. If it names a session and its
heartbeat is over 60 minutes old, resume from ledger state; otherwise do
nothing. The finale is a resumable stage — revive it, never re-run completed
halves." Delete it at run end. Remind once that the machine must stay awake
(on macOS, `caffeinate -dimsu`).

**Every halt writes a HALT BLOCK into the ledger before the session stops.** It is
the only resume document — a second copy goes stale. In order: why it halted and
when the block lifts; what is on disk **checked, not assumed** (was a worker killed
mid-edit, `git status`, typecheck, the tests touching affected modules — say which
you verified); what is owed, in order, naming the agent type for each, and what
must NOT be re-spawned because its work is already on disk and green; the
remaining queue in the order given.

**Find the right ledger before reading any of it.** `resume` with no issue range
is ambiguous: every worktree carries its own `.scratch/<feature>/run.md`, and the
most recently *touched* one is routinely the wrong one. Enumerate them all and
read two lines of each, `Owner:` and `Worktree:`, before opening any of them:

```bash
for w in $(git worktree list --porcelain | grep ^worktree | cut -d' ' -f2); do for l in "$w"/.scratch/*/run.md; do [ -f "$l" ] && printf '%s\n  %s\n  %s\n' "$l" "$(grep -m1 '^Owner:' "$l" || echo 'NO OWNER LINE')" "$(grep -m1 '^Worktree:' "$l" || echo 'no Worktree: line')"; done; done
```

**Most of what that prints is the same ledger, not different runs.** Run state is
committed, so every worktree branched from that commit carries a copy, frozen at
whatever the ledger said when it branched (one measured repo held twelve copies,
six claiming the same live owner — decisions.md). The discriminator is the
`Worktree:` line the ledger writes at launch: **the only real copy is the one
whose `Worktree:` line names the tree it is sitting in.** Every other copy is a
snapshot — never resume from one, and never write to one.

Then read that copy's owner line. No owner line, or `none — awaiting-merge`, is
finished paperwork and not the run. Never pick by timestamp: on the same run the
freshest ledger was an already-merged run's, and chasing it cost 25 minutes. If
the rules still leave two live candidates or none, prefer the ledger matching the
invocation's issue range; failing that, report what you found in the launch
message and stop — a launch-time stop, before anything is spawned, is not a
mid-run stall.

Only then: read that ledger, then `run-journal.md` once, then re-run pre-flight
before spawning anything, and recreate the cron.

## Pre-flight

- **Print one launch line before spawn #1, on every invocation** — issues in
  order, branch, and what will NOT happen (no merge, no prod). Not a wait, an
  interrupt window: the longest stall on record was an 11.5-hour halt from a run
  started on a misread request.
- **The session is on the model the whole run should use.** Agent files use
  `model: inherit`, so every worker inherits it. If the session is on a different
  model, pass the intended model explicitly on every spawn — never ask, never
  proceed on inherit from a wrong-model session; that silently changes the whole
  run's tier.
- **Hardening stamp.** List every scoped issue whose file lacks a `Hardened:`
  line in the launch message, naming `/harden-issues` as the fix **for the next
  run**. Never run it against issues this run holds. Launch-time information for
  the human only — not a gate, and nothing mid-run.

  An `all` run takes stamped issues, and `Hardened (provisional)` counts as
  stamped — a pending default is not a reason to drop an issue. An explicitly
  named issue always runs, stamped or not. The merge briefing names every issue
  that shipped unstamped or provisional, with its pending defaults, so those
  answers land after the run rather than gating it.

  **If `all` resolves to nothing, say so and stop.** An empty scope means the
  batch was never hardened, not that there is no work — never treat it as a
  completed run.
- **Verify the allowlist, never assert it.** Enumerate the command classes this
  run will use — typecheck, lint, test, the cold-build delete, git stage and
  commit, any migration script — and dry-run each in no-op form before
  spawn #1. A miss is a launch-time blocker; mid-run it is a worker blocked on a
  prompt, stalling silently. (Coverage has been asserted and wrong before.)
- **Probe fixture health, read-only** — whatever writable test database or
  seeded state the batch will drive: row counts on the tables the issues touch,
  any counters or sequences, a can-create sanity check. Results go into
  Carry-forward as the known-good path. Fixture viability is run state like any
  quota: on one measured run nobody owned it, and a verify gate paid a 55-minute
  stage (versus 19 for a strictly bigger issue) to discover mid-drive that the
  test database could not mint a document.
- If the project keeps its env in a canonical file outside the worktree, the
  worktree's `.env.local` is a **symlink** to it, never a copy. Replace any copy.
  Env files are never committed.
- **If that symlink exists, CLI tools can write through it.** Vercel's `vercel
  link` / `vercel pull` are the known case: they write *through* the link into the
  canonical file. Remove the symlink, run the command, delete the `.env.local` it
  wrote, restore the link. Never edit the canonical file to clean up afterwards.

Every agent file opens with its own idempotency check, so a re-spawn after a
resume stops on its own if its stage is already past. A gate also writes
`verify: pass|reject <HH:MM>` or `review: …` into its ledger row on return, so a
resume on a `gates` row re-spawns only the gate with no entry.

## Mid-run directives

A directive arriving mid-run is **this run only** unless the user says it is
standing. Record it in Carry-forward with its scope written on it and re-brief it
from there. Do not write it to a memory file in-session — the test is whether it
would still be true if this run had never happened. At run close, route "should
this become standing?" to the finale's `## Decisions inbox`, where `/daily-brief`
collects it — a chat question at session end dies with the session.
