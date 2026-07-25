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

Issues are a dependency chain. Always run in order; never skip past a blocked one.

For `all`, resolve the scope from each issue file's `Status:` line and take only
clean `ready-for-agent` issues. Print the resolved list in the launch message.
Skip `ready-for-human`, `in-progress`, `needs-*` and anything `done`. If a
`ready-for-agent` issue looks superseded by merged work, set it `needs-info` with
one line of why and skip it — never build a stale issue blind.

## Who runs what

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the runner never pastes a brief.

| Stage | Agent type | Effort |
|---|---|---|
| Implement | `run-issues-implementer` | xhigh |
| Third attempt after two rejections | `run-issues-implementer-escalated` | max |
| Verify | `run-issues-verify-gate` | high |
| Review | `run-issues-review-gate` | high |
| Review, diff changes money/auth/secrets | `run-issues-review-gate-critical` | max |
| Coherence finale, once per run | `run-issues-finale` | max |

Spawn prompts carry **only** what varies — issue ID, paths, rejection reasons.
Everything stable already lives in the agent file, where it caches.

## Run state — files, not contexts

In the main checkout, under `.scratch/<feature>/`:

- **`run.md`** — the ledger. Status table plus a **Carry-forward** section, and
  nothing else. Every spawn reads it, so nothing else belongs in it.
- **`run-journal.md`** — the narrative, append-only. Every log line goes here:
  what each attempt did, verdict stories, dead ends. Subagents never read it. It
  is read exactly twice — by a resuming runner, and by the finale.
- **`primer.md`** — the codebase primer. Fresh subagents read this instead of
  exploring. The first implementer creates it; every implementer appends what it
  learns. Exploration is paid once per run.
- **`merge-briefing.md`** — the merge-read briefing, built up as the run goes.

Ledger statuses: `queued → in-progress → gates → done`, plus `blocked`. Both gates
run under the one `gates` status. Only the runner writes the ledger. Gates write
verdicts into issue files. Everyone appends; nobody rewrites another's section.

**Stamp every transition with the local time** (`HH:MM`, dated on the day's first
entry). A stage that quietly took four hours is invisible without it, and the
run's own timings are the only evidence for whether the pipeline is worth
changing. Cheap to write, impossible to reconstruct later.

**Carry-forward** is what the runner curates for future spawns: shared-quota state,
traps discovered, conventions later issues must follow, do-not-tidy lists. A
learning that lives only in the journal survives only if the runner remembers to
re-brief it.

## Shared external quotas

Any per-window cap on an external system is run state, owned by the runner.
Carry-forward holds the last observed status, its timestamp, and who holds the
window. **Two agents never hold the same quota at once.** Schedule live halves
first, while the window exists.

## Per-issue loop

1. Spawn `run-issues-implementer` for the issue.
2. **Read its final message before doing anything else.** If it reports unfinished
   work, the issue is not gate-ready — re-spawn to finish it, or mark `blocked`.
   If it reports the acceptance criteria are *wrong* rather than unmet, spawn a
   review gate to confirm that claim only; if confirmed, set the issue
   `needs-info` with the evidence and move on. Never build to criteria a worker
   has shown to be wrong.
3. Spawn **both gates in one message, concurrently.** Neither reads the other's
   verdict — verify drives the app, review reads the diff — so serialising them
   buys nothing and the wall clock is the slower of the two rather than their sum.
   Use the review `-critical` variant when the diff **changes** money computation,
   auth or secret handling (touching a file that has a price field does not
   count). If verify rejects, read the review anyway: its findings still route,
   and its work is already spent.
4. Both pass → **verify the routings**: grep each target file a gate said it
   appended to. A declared routing is not a routing. Then commit, staging
   **explicit paths only** — never `git add -A` or `.`. Glance at `git status` and
   investigate anything unexplained *before* committing.
5. Ledger `done`; set the issue's `Status:` to `done — on branch <branch>,
   unmerged` (gate history goes in the body — `all` runs parse that line).
6. A gate rejects → same implementer retries with the written reasons. If **both**
   reject, that is still ONE retry carrying both verdicts, and one strike, not two.
7. **Two strikes** → kill it and spawn `run-issues-implementer-escalated` with the
   issue and both verdicts, but none of the failed reasoning.
8. If that also fails a gate → ledger `blocked`, and the run **halts**. It is a
   dependency chain; do not build on a wrong slice.

Small-issue coalescing: up to two adjacent trivial issues (copy, config, no logic)
may share one implementer spawn and one combined gate spawn. Anything with logic
is one issue per spawn.

## Nothing finishes vaguely

An issue leaves the ledger as `done` or `blocked`. Never "done, mostly". Anything
unfinished goes into its one named home before the ledger moves, and the merge
briefing lists every such entry:

- Acceptance unmet → stays `blocked`.
- Waiting on the user (secret, env var, OAuth client) → wherever the project keeps
  its standing list of actions owed by a human, as a numbered action. Code may
  still complete around it.
- Follow-up found mid-issue → a new issue file, or a fold-in section in the next.
- Gaps tests cannot reach → noted for the post-deploy `/parallel-hunt`.
- Bugs found **outside** the issue's scope → routed to one of the homes above.

Handoff documents are never the home for any of this.

## Branch and human gate

The runner owns the feature branch; **main belongs to the human.** The worktree
has **one writer** — the current implementer, plus the runner committing. Anything
spawned beside the per-issue loop works in the scratchpad, never the run's tree.

Commit per issue after gates pass. **No merge between issues.** Merge to main
happens once, at run end, by the human. A single-issue run therefore runs the full
finale and stops at the merge read — that stop is the design, not a stall.
Extending a finished run to a new issue is a NEW run: merge first, then invoke
again from main.

**A worktree dies when its branch merges.** The merging session runs, for that
branch: `git status --porcelain` clean → `git worktree remove <path>` →
`git branch -d <branch>`. Report a dirty tree instead of removing it.

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
   become the merge briefing. If it fails on a usage limit, leave the ledger at
   `finale-judgment`, write the halt block, and revive after reset — never
   downgrade it to save the wait, and never declare the run complete with the
   judgment half unrun.
3. **Regenerate the action board** — `.scratch/<feature>/board.html`, the one-page
   human view of `merge-briefing.md`. Live actions only, grouped by when, one line of
   of what and one of why each, ticks persisted in localStorage. Match the styling
   of the previous run's board if there is one, then send the file to the user.
   `merge-briefing.md` stays the source of truth.
4. **Recommend follow-ups; start none.** One exception is mandatory:
   - **The post-deploy smoke walk.** The session that merges and deploys
     immediately drives a READ-ONLY walk of the **deployed** site on real data,
     before the human walk: every list page and its filters and search, every
     detail page, the send and receive surfaces as far as read-only allows.
     Read-only means no permission risk, so there is no reason to skip it.
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

Create the wakeup anyway at launch (every ~29 min): "If `<run.md>` shows an active
run with no ledger progress since last firing, resume from ledger state; otherwise
do nothing. The finale is a resumable stage — revive it, never re-run completed
halves." Delete it at run end. Remind once that the machine must stay awake
(on macOS, `caffeinate -dimsu`).

**Every halt writes a HALT BLOCK into the ledger before the session stops.** It is
the only resume document — a second copy goes stale. In order: why it halted and
when the block lifts; what is on disk **checked, not assumed** (was a worker killed
mid-edit, `git status`, typecheck, the tests touching affected modules — say which
you verified); what is owed, in order, naming the agent type for each, and what
must NOT be re-spawned because its work is already on disk and green; the
remaining queue in the order given.

A resuming runner reads the ledger, then `run-journal.md` once, then re-runs
pre-flight before spawning anything, and recreates the cron.

## Pre-flight

- **The session is on the model the whole run should use.** Agent files use
  `model: inherit`, so every worker inherits it. Check before spawning anything —
  launch on the wrong model and the entire run silently changes tier.
- The permission allowlist covers the run — tests, git, migrations. A worker
  blocked on a prompt stalls silently.
- If the project keeps its env in a canonical file outside the worktree, the
  worktree's `.env.local` is a **symlink** to it, never a copy. Replace any copy.
  Env files are never committed.
- **If that symlink exists, CLI tools can write through it.** Vercel's `vercel
  link` / `vercel pull` are the known case: they write *through* the link into the
  canonical file. Remove the symlink, run the command, delete the `.env.local` it
  wrote, restore the link. Never edit the canonical file to clean up afterwards.

Every agent file already opens with its own idempotency check, so a re-spawn after
a resume stops on its own if its stage is already past.

## Mid-run directives

A directive arriving mid-run is **this run only** unless the user says it is
standing. Record it in Carry-forward with its scope written on it and re-brief it
from there. Do not write it to a memory file in-session — the test is whether it
would still be true if this run had never happened. Ask at run close whether it
should become standing.
