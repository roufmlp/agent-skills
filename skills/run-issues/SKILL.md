---
name: run-issues
description: Autonomously implement a range of tracker issues one by one — a fresh implementer per issue working test-first, adversarial verify and review gates, two-strike escalation, ledger-driven resume across usage limits, and a human merge gate at the end. EXPLICIT INVOCATION ONLY. Use this skill only when the user types the command /run-issues (including /run-issues resume). Never infer it from wording such as "run issue 05", "implement the remaining issues" or "keep going until they are done" — treat those as ordinary requests and handle them in the session.
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
| Promotion, once per run | `promotion` | medium |

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
  file (decisions.md). A third trigger while an issue is still fighting: before
  re-spawning gates on the same issue, a row over ~10 lines loses its verdict
  story to the journal, keeping stamps only — a growing row is re-billed to
  every one of its own gate spawns, and the existing triggers fire exactly when
  it has stopped growing (decisions.md).
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
  **A new run archives the old briefing at launch** — same rule as the primer.
  Gate verdicts get one summary line each; the full verdict text lives in the
  issue files, which already carry it. It is a thirty-minute read or it has
  failed.

  **The narrative sections are filled as each issue closes, not at the finale.**
  What shipped, what was minted, what was skipped, what waits on the human —
  each gets its lines when the issue that produced them goes `done`, while the
  runner still holds the facts. On one run four sections were still empty
  placeholders when the finale opened the file, and one of them was the section
  that should have carried a deploy step — the single action in that batch that
  changed what a customer reads. A reader starting at the top met a stale test
  count before reaching the correction 100 lines down. An empty section is not
  neutral: it reads as "nothing to report" (decisions.md).

Ledger statuses: `queued → in-progress → gates → done`, plus `correction`
(between `gates` and `done`, when taken) and `blocked`. Both gates run under the
one `gates` status. Only the runner writes the ledger. Gates write
verdicts into issue files. Everyone appends; nobody rewrites another's section.

**Stamp every transition with the local time** (`HH:MM`, dated on the day's first
entry) — the run's own timings are the only evidence for whether the pipeline is
worth changing. A correction round is a transition too: its row gains
`correction: open HH:MM → closed HH:MM` (decisions.md).

**Carry-forward** is what the runner curates for future spawns: shared-quota state,
traps discovered, conventions later issues must follow, do-not-tidy lists. A
learning that lives only in the journal survives only if the runner remembers to
re-brief it. **Every entry names the issue(s) it serves**, and the runner deletes
it when its last consumer goes `done` — an unexpired entry is billed to every
remaining spawn. A human action taken mid-run (a SQL fix, a console change) is
recorded here with its **observed** effect, not its intended one: one has
already silently failed to land.

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

   **Flag a prose-graded criterion while settling the road** — one whose
   pass/fail is decided by reading prose rather than driving behaviour. Its bar
   regenerates on every fix (each edit mints a new falsifiable claim), so make
   it executable or bounded before spawn, or send the issue back through
   `/harden-issues`. This, more than difficulty, is what separates a whale from
   a clean issue (decisions.md).
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

   **Concurrent gates share a tree but not a pen.** Both gate briefs require
   mutation drills on scratchpad copies; a gate that genuinely must write the
   tree declares it in its verdict, and then it is the only writer — a "touch no
   code" gate that mutates source to prove a test can fail is a writer, whatever
   its banner says. Before committing, re-check each graded file's checksum
   against the ones the gates recorded at gate close. On one run the tree sat
   reverted to the pre-fix file for two minutes mid-gate, one gate's backup
   captured the mutant, and only a staging-time checksum stood between the run
   and committing the defect it had just fixed (decisions.md).

   **Each gate drills in its OWN private whole-tree copy, at a path carrying its
   issue id and its role.** Never a shared scratch directory, and never a name
   two gates could both choose. One batch lost work twice to this in a single
   day: both gates on one issue picked the scratchpad name `drill`, and one
   gate's `rm -rf` destroyed the other's copy mid-run; the next issue's gates
   then collided in the run's own tree, where one gate briefly read the other's
   live mutant. Checksums at gate open and close cannot see the second case —
   the file is back before either stamp is taken. A private copy makes both
   unrepresentable rather than detectable (decisions.md).

   **While the gates run, the runner preps issue N+1, read-only:** settle its
   road, size it, pre-write the spawn prompt, prune the ledger, run the fixture
   pre-check (below). None of it touches the tree, so single-writer holds; on
   gate-pass only routing-verify, lint and commit remain serial (decisions.md).
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

   **The runner commits. An implementer never commits its own work**, and the
   runner says so in every spawn. Two of the first three implementers on one
   batch committed before either gate had opened. Neither did harm, and that is
   the trap: a self-commit silently changes what "the diff" means to a gate
   already reading it, so the runner must hand those gates an explicit commit
   range instead of the working tree. Where an implementer has committed anyway,
   do not revert it — record it and give the gates the range (decisions.md).
5. **Both pass but a verdict enumerates follow-up items** (a gap on the issue's
   own invariant, a test the evidence says should exist) → ledger `correction`,
   not `done`. Re-spawn `run-issues-implementer` with the enumerated items, the
   correction marker, and nothing else — a fresh context, never a message to a
   live agent. On resume, a `correction` row is re-spawned the same way; it is
   still the one round. One round maximum; the scope is the verdicts' list —
   anything bigger, or anything a second round would need, becomes a register row
   instead.
   **While any row shows `correction`, no new implementer spawns** — that status
   is what makes a second writer in the tree unrepresentable. The round closes
   when the runner verifies each item's *named evidence* (the test now exists and
   is green, the mutation now reds), not just that files were touched. Then
   commit and `done`. A correction round is not a strike.

   **A standards-shaped split is a correction, not a retry, on one condition:
   every gate grades the behaviour correct AND the owed work is enumerated.** The
   shape is a verdict that splits on how the work is written down rather than on
   what it does — a missing pin, an unrun mutation, a claim that outruns its
   evidence. Where the behaviour is agreed and the list is closed, buying a fresh
   implementer to re-do correct work is waste, and the strike it charges is a
   strike against a spec fault. If either half fails — any gate doubts the
   behaviour, or the owed work cannot be enumerated — it is a retry and a strike,
   as before. (Adopted 2026-08-07 with that condition attached, from a run
   finale.)

   **A rejection on non-executable PROSE is fixed by deleting the claim, never
   restating it.** A fix for an over-claim is itself a new claim with its own
   falsifiable surface, so on this class more precise and more likely wrong
   move together. Second rejection → delete down to the minimal sentence the
   gate cannot falsify; re-assert only by making the claim executable. Before
   pricing any fix, read the strike record: two or more prior rejections in the
   class makes it delete-only and forbids sizing the fix in lines. One
   canonical statement per claim — everywhere else cites `file:line` and
   asserts nothing. The same rule governs post-block resolution rounds.
   (decisions.md.)

   **Three rules on what a claim may SAY. They bind every artefact an agent
   writes — issue files, the primer, migration headers, the briefing — not
   only a rejection fix.** (decisions.md.)

   *Never write that something is the only copy.* Uniqueness across a corpus is
   not a fact one agent can establish, so "this is now the sole home of X" is a
   guess wearing a fact's clothes. Cite the canonical location; do not claim it
   is the only one. One primer asserted an issue file was the only copy of a
   measured record while three others existed — and that sentence was written as
   the REPAIR for a stale-prose defect, by an agent following the deletion rule
   above. The class survives its own cure.

   *A recorded cause is tested against a control, never merely observed.* One
   run that works does not name the reason it works. The same primer recorded
   that a package import succeeds "when node is launched from the worktree
   root", having watched it succeed there. The cause was a `node_modules`
   symlink: the import succeeds from any cwd that has one and fails from every
   cwd that does not. One control run settles it. A wrong cause does the most
   damage exactly where that one sat — in a line written to correct a previous
   agent's wrong cause.

   *Every citation carries its repo-relative path in full, every time.* Not the
   first mention only, and never a bare filename afterwards. A cross-session
   sweep of one batch found nine ambiguous citations across six issues; the
   worst was a bare `review.ts` used eleven times where the tree holds two files
   by that name. The wrong one resolves to plausible code, so the reader does
   not discover the mistake — they find a defect that is not there, and an
   implementer can lose a strike to it. Repetition is cheaper than ambiguity.
6. Ledger `done`; set the issue's `Status:` to `done — on branch <branch>,
   unmerged` (gate history goes in the body — `all` runs parse that line).
7. A gate rejects → re-spawn the implementer with the written reasons. If **both**
   reject, that is still ONE retry carrying both verdicts, and one strike, not two.
   Then re-run step 3 in full: both gates, on the new diff. A gate that passed the
   previous attempt has not seen this one.

   **The retry brief's not-yours list is checked, not asserted:** every item the
   runner excludes cites the criterion or executable-record line that excludes
   it — a gate's summary sentence is not a warrant. A rejection ground
   attributable to the runner's own brief is **annulled from the strike** and
   journalled as a runner error — the same refund criteria-fault grants for
   spec fault. After a criteria correction, the re-spawn prompt carries the
   CURRENT surviving contract — corrected criteria plus the latest verdicts
   only; verdicts graded against a superseded spec are journal, never prompt.

   **Any figure or refutation the runner passes onward is re-derived first,
   from a source that cannot drift, and the brief names that source.** Commit
   times, a re-run command, the file itself — never the runner's own earlier
   statement. A grep-backed refutation states its scope beside its conclusion.
   Three runner errors in one run shared this shape: a transcribed figure off
   by 960, a refutation from a grep that missed the call one directory over,
   and hand-written timestamps an hour ahead of the clock (decisions.md).
   Ledger actuals derive from commit times, full stop.

   **When the gates split:** a factual split is settled by the runner driving
   it — a tenancy claim by deleting the predicate (or planting the cross-tenant
   row) and running the suite, cache-cleared, never by reading the code
   (twice on one measured run: decisions.md). A severity or standards split
   takes the stricter verdict.
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

   **Two criteria-fault resets maximum per issue.** After the second, the
   criteria are frozen for the run; the next strike-2 buys one escalated
   attempt, then `blocked`. Rejection CLASSES are counted across resets —
   strikes reset, the class ledger does not. Without the cap, lawful resets
   compound: one measured issue ran more than twice the promised three attempts
   (decisions.md).

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

   **A blocked row's handoff never sizes a fix in lines** — in a class with
   prior rejections a line count is fiction (a "two prose lines" fix became
   four sites in three files and an evening — decisions.md). It states the
   strike-class record beside any size claim, and the briefing presents both
   roads side by side — merge-now-fix-later and fix-first — each with what it
   costs and what it risks. The judgement is the human's; the sizing is not.

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
- Follow-up found mid-issue → a register row, or a fold-in section in the next
  issue. Writing a row is **write-only**: it records evidence already in hand, and
  nobody investigates further mid-run. The merge briefing lists every row written.
- Gaps tests cannot reach → noted for the post-deploy `/parallel-hunt`.
- Bugs found **outside** the issue's scope → routed to one of the homes above.

Handoff documents are never the home for any of this.

**Nothing in a run writes an issue file.** Not the runner, not an implementer, not
a gate. Findings go to the register, and they leave it through promotion, which the
finale runs once at the end of the run. A finding is out by default; promotion is
the work that gets it in. The register, the row format and the promotion rule are
specified once, in `parallel-hunt/SKILL.md`, and a run uses them unchanged — the
same file for the same feature, in the main checkout, whichever worktree the writer
is standing in. Two registers for one product rebuilds the problem this closes.

**A ruling that creates work gets its issue number in the same sitting as the
ruling.** A ruling is a decision, not a finding, so this stays a direct issue file
and does not go through the register. Not "that becomes its own issue" — the
number, or the file and line where the work now lives. On one batch a ruling
settled an open question by
splitting a road out of scope; nine hours later no issue existed, and the only
trace of the split was one phrase inside the original issue's own file. A verify
gate happened to notice, and it was minted then. Nothing was watching for it, so
nothing would have caught it a day later. A ruling with no artefact cannot be
told apart from a ruling nobody made (decisions.md).

## Resolving a blocked issue

Resolution happens after the run closes, and it is a procedure, not an evening
of improvisation. The human's answer is one word — `merge`, `fix` or `drop`.
`fix` spawns ONE implementer, under the delete-only prose rule where it applies,
then ONE narrow gate round maximum, unattended; anything more becomes a register
row. The human supervises nothing — they answer, and the machine reports back
in the next brief.

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

   **A published checksum expires the moment the file moves.** A correction
   round re-stamps every checksum a gate published for a file it touched, and
   the finale re-runs any that remain before the briefing closes. Anchor diff
   commands to `main...HEAD`, never the working tree — a worktree diff prints
   nothing once the work is committed, and an empty print cannot distinguish
   "fine" from "the fix was reverted and committed". Both checksums on one issue
   were correct at gate close and false three hours later, and running them read
   as the exact alarm the gate wrote them to raise (decisions.md).

   If the finale fails on a usage limit, leave the ledger at
   `finale-judgment`, write the halt block, and revive after reset — never
   downgrade it to save the wait, and never declare the run complete with the
   judgment half unrun.
3. **Promotion — the last phase, and the only door into `issues/`.** Spawn one
   `promotion` agent over every register row this run wrote. A row already at
   `verified` exits as `fixed`, before audience is even read, because the run fixed it
   and the fix is in the commit. Of the rest it promotes a row whose `audience` is
   `operator` at any severity, or `tester` at `critical` or `high`, and refuses the
   others. A promoted row becomes an issue file at `Status: needs-harden` with one
   category role and a link to its bug file. All three exits delete the row, so the
   register's length stays the promotion backlog and nothing else. The rule lives in
   the agent file and in `parallel-hunt/SKILL.md`; both skills use the one agent.

   **`fixed` is reported as a count and never as a refusal** (ruled 2026-08-06). A
   run that fixes work must not report that work under a word the daily brief
   offers to overturn.

   **The runner never promotes rows itself.** This is the same call as the board in
   step 4, for the same reason: by run end the runner's context is the most expensive
   in the pipeline, and writing issue files is repetitive work that has no business
   in it. The runner spawns, gets two lists back, and appends them to
   `merge-briefing.md`, one line each. `/daily-brief` carries both to the human, who
   holds the veto over either direction.
4. **Regenerate the action board** — `.scratch/<feature>/board.html`, the one-page
   human view of `merge-briefing.md`. Live actions only, grouped by when, one line of
   what and one of why each, ticks persisted in localStorage. Keep the existing
   styling; send it with SendUserFile. **A fresh subagent renders it, spawned with
   the cheapest model named explicitly on the spawn call** — from `merge-briefing.md`
   plus the old board, never the runner itself, whose context is at its most
   expensive by run end, and the old board's bytes never enter the runner.
   Naming the model is not optional and "cheap" is not a model: an unnamed spawn
   inherits the session model, so this step was paying the top tier to convert one
   markdown file into HTML on the largest input in the pipeline (283 KB, measured
   2026-08-06). There is no judgement in the render — the briefing already decided
   what the board says. `merge-briefing.md` stays the source of truth,
   and `/daily-brief` reads that file, never the board.
5. **Recommend follow-ups; start none.** One exception is mandatory:
   - **The post-deploy smoke walk**, owned by `/daily-brief`. The run ends at
     `awaiting-merge` and the brief carries it to the human with the branch head
     SHA they are approving. When they write `merge`, that session merges,
     rewrites the `unmerged` statuses, deploys, and drives a READ-ONLY walk of the
     **deployed** site on real data before the human walk: every list page and its
     filters and search, every detail page, the send and receive surfaces as far
     as read-only allows. Read-only means no permission risk, so there is no
     reason to skip it.
     **The walk fires on ANY merge of a run branch, whoever merged** — a merge
     outside the `/daily-brief` path does not skip it; the next brief session
     runs it and reports what it found.
   - Recommended after it: a `/parallel-hunt` round on the live system. It hunts
     the seams between issues and against live external systems — the class of bug
     per-issue gates cannot see. Its own promotion phase decides which of its
     findings become the next run's issues.
   - Only if the finale's findings are structural: an architecture-improvement
     session on a clean tree.

## Resume across usage limits

**The ledger resumes a run. The cron only saves short waits** — it reaches no
further than a five-hour window the same session sits through. A weekly limit
resetting days out is resumed by a human re-invoking `/run-issues resume`.

**The ledger carries an owner line; staleness is the FILE's mtime, never a
handwritten timestamp.** One line at the top: `Owner: <session>`. Every
transition already updates the file's mtime and nobody can forget to write it —
a handwritten `heartbeat <HH:MM>` field failed twice in one run, on a runner who
had already diagnosed the failure mode (decisions.md). A long implement attempt
moves no status line for an hour, so "no progress" cannot mean "dead" — only a
stale mtime can.

**The owner line is cleared the moment the run stops owning the tree.** Reaching
`awaiting-merge`, or halting, rewrites it to `Owner: none — <awaiting-merge|HALTED>
<date> <HH:MM>`.

Create the wakeup anyway at launch (every ~29 min): "Check `grep -m1 '^Owner:'
<run.md>` and the file's mtime (`stat -f %m` on macOS, `stat -c %Y` on Linux) —
do not read the rest of the file. If the owner line names a session and the
mtime is over 60 minutes old, resume from ledger state; otherwise do nothing.
The finale is a resumable stage — revive it, never re-run completed halves." Delete it at run end. Remind once that the machine must stay awake
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

- **The launch line is a gate, not an announcement. Nothing spawns before it
  prints.** One line on every invocation — issues in order, branch, the resolved
  session model, and what will NOT happen (no merge, no prod). It is still not a
  wait: it prints and the run carries on at once, so the gate costs nothing. What
  it buys is that the interrupt window exists at all. On one run the line
  printed after the first implementer had already finished, so there was no
  window left to interrupt. (Adopted 2026-08-07. The older hazard is the
  11.5-hour halt from a misread request: decisions.md.)
- **Re-derive every fact the run will carry into its spawns, from source, and
  name the source beside it.** Carry-forward entries, batch-plan sentences,
  anything a previous session wrote down — none of it is evidence. Read the
  function, run the query, open the migration. On one run the plan file said a
  helper "answers null when the count is not one"; it actually ordered its rows
  by creation time and returned the OLDEST, answering null only at zero. The
  runner repeated it for nine hours across many spawns before a gate refuted it
  from the migration file. The two versions fail in opposite directions — the
  false one predicts a loud break, the true one a silent misfile — so the error
  was invisible while it did damage. One read of the source at pre-flight would
  have caught it (decisions.md).
- **Workers inherit the session model. Let them.** Agent files use
  `model: inherit`, so the run takes the tier it was launched on. Never pass a
  `model:` value on a spawn to override that: the spawn tool's `model` parameter
  beats agent-file frontmatter, so a spawn-time value silently defeats both
  `inherit` and any model an agent file might pin on purpose. No agent file in
  this pack pins one. Never ask, and never stall — the launch line above is
  where a wrong tier gets caught, one keystroke before spawn #1.
- **Record the session model in the ledger's owner line and in the merge
  briefing.** A run on a tier this pipeline has no evidence for is still a valid
  run, and it is also the first evidence at that tier — so whoever reads its
  verdicts later has to know which tier produced them. Say it once, where the
  verdicts live.
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
- **Creating the worktree includes installing dependencies and making the
  env-file symlink, where the project uses one. If either fails, the runner
  refuses to start.** Not a check to remember at pre-flight — part of what "the
  worktree is ready" means. It costs one shell command, a few lines of output and
  30 to 60 seconds per worktree, and it saves more than that the first time it
  stops an agent diagnosing a false green caused by a missing environment file.
  (Adopted 2026-08-07, on the question of what it costs in tokens: it saves them.)

  The failure it closes: a fresh worktree of one repo ran its typecheck to exit 0
  with `node_modules` absent — the compiler resolved off a global install and
  never loaded the repo's own types. A green produced without dependencies on
  disk is a false green (decisions.md).
- **Verify the allowlist, never assert it.** Enumerate the command classes this
  run will use — typecheck, lint, test, the cold-build delete, git stage and
  commit, any migration script — and dry-run each in no-op form before
  spawn #1. A miss is a launch-time blocker; mid-run it is a worker blocked on a
  prompt, stalling silently. (Coverage has been asserted and wrong before.)
- **An unattended run may delete only rows it marked as its own, and the scope of
  the delete is that marker.** Where a run needs to clean up after itself, it
  stamps a run-owned marker column on every row it writes and deletes on that
  marker alone. It never widens its database permission to cover deletes in
  general, and it never deletes a row on an argument that it must have written it.
  A permission granted once is held for every later run, including the one that
  reasons badly at 3am; a marker column is scoped to the rows and expires with
  them. (Adopted 2026-08-07, from a run finale.)
- **Probe fixture health, read-only** — whatever writable test database or
  seeded state the batch will drive: row counts on the tables the issues touch,
  any counters or sequences, a can-create sanity check. Results go into
  Carry-forward as the known-good path. Fixture viability is run state like any
  quota; discovering it mid-drive is paid at gate prices (decisions.md).
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
this become standing?" to the finale's `## Decide` heading, and from there into
`.scratch/decisions-queue.md`, where `/daily-brief` collects it — a chat question
at session end dies with the session. It goes under `## Decide` rather than
`## Ruled` because nobody has answered it. Write it with the run's recommended
answer, marked `[reversible]` or `[irreversible]`.
