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

**Every spawn in this run carries `run_in_background: false`. Name the field on
the call. Do not take the tool's default.** The runner has nothing to do while a
worker runs — it cannot open the gates until the implementer returns, and it
cannot judge until both gates answer — so the spawn tool's own rule applies: pass
`false` when the next action depends on the result and nothing else could usefully
happen meanwhile.

**The measurement first recorded here was wrong, and the rule survives on the
paragraph above alone.** The 2026-08-17 audit of one run blamed eight 17-to-23
minute stalls, 158 minutes, on background spawns: the runner asleep past finished
work until the resume cron woke it. The 2026-08-18 re-measure joined every spawn to
its subagent transcript and refuted that. A task notification woke the runner
within seconds of every completion, and the eight gaps were the workers' own
runtimes. Foreground spawning recovers none of them; expect it to save no clock.
What it buys is not betting the run on notification delivery holding across
harness versions.

**The cron stays, at its usage-limit interval, and it rescued that run exactly
once — not from a background spawn.** At 06:34Z the runner wrote that it was
spawning the next issue, ended its turn, and never made the spawn call; the cron
caught the 24-minute gap. `run_in_background: false` cannot prevent a call that
was never made. Shortening the interval buys nothing.

**The field is enforced, not remembered.** `hooks/run-issues-foreground-gate.py`
in this pack is a `PreToolUse` hook on `Agent|Task`. It refuses any `run-issues-*`
spawn whose `run_in_background` is not exactly `false`, and its message says how to
reissue. It refuses nothing else, so no other skill meets it. Register it before the
first run — a hook the harness has not been pointed at never runs, and
`hooks/README.md` carries the `settings.json` block. The two gates still run
concurrently: spawned in one message, two foreground calls run in parallel.

**This is also what the verdict check guards.** A runner that does not block can
mark an issue done before the work lands. `skills/lib/check_verdict.py` refuses on a gate
that returned no verdict, and that refusal is load-bearing today rather than
insurance against a future version.

| Stage | Agent type | Effort | What a wrong answer here costs |
|---|---|---|---|
| Implement | `run-issues-implementer` | high | A weak diff is paid for twice, by the gate round that rejects it and by the attempt it burns against the cap |
| Third attempt after two rejections | `run-issues-implementer-escalated` | high | Two attempts have already failed on this issue, so the next exit is `blocked`: the issue leaves the run and comes back as one of the human's answers |
| Verify | `run-issues-verify-gate` | high | A wrong pass ships behaviour nobody drove, and the finale is the first thing after it that looks |
| Review | `run-issues-review-gate` | high | Same: no catcher until the finale, and it is the only reader of the whole diff before then |
| Review, diff changes money/auth/secrets | `run-issues-review-gate-critical` | high | A wrong pass is money, auth or a secret, which is the class the variant exists for |
| Coherence finale, once per run | `run-issues-finale` | max | Once per run, and the last fresh eyes before the merge read |
| Promotion, once per run | `promotion` | medium | Every exit is recoverable: the row survives a wrong refusal, and the human vetoes either direction in the next brief |

**A role is safe to downgrade where its wrong verdict is recoverable, never
because the model looks strong enough.** That is the test, and promotion is the
only role in this table that passes it — it applies thresholds it may not argue
with, and both of its wrong exits are caught. It is also a measurement waiting to
be taken rather than a settled value. The two trials that keep getting proposed,
`xhigh` in place of `max` on the finale and on the panel gate, stay refused for
the same reason read the other way: each runs once per run, so the saving is one
spawn, and what it buys is a cheaper last look before a merge.

No value in the effort column was measured against a lower one. What the last
column states is what a wrong answer costs, because that is the evidence a
downgrade has to beat.

Spawn prompts carry **only** what varies — issue ID, paths, rejection reasons.
Everything stable already lives in the agent file, where it caches.

## Run state — files, not contexts

In the main checkout, under `.scratch/<feature>/`:

- **`run.md`** — the ledger. Status table plus a **Carry-forward** section, plus
  the one live halt block if the run is halted. Nothing else. Every spawn reads
  it, so every line in it is billed a dozen times a run.

  **Its header carries the two settings a later measurement cannot recover:**
  `Session model at launch:` and `Session effort at launch:`, one line each,
  written before spawn 1. The model line was already a habit; the effort line is
  new, and both are now required rather than remembered. **The reason is a void
  experiment.** One five-issue run was the first trial of `medium` effort.
  `orchestrator_cost.py` read it at 1.51M weighted tokens per issue, above the
  threshold that would have ended the effort question — and the reading had to be
  thrown away, because neither `run.md` nor `run-journal.md` contained the word
  "effort" anywhere, so nobody could prove which tier produced it. A run that does
  not stamp its own settings cannot be used as evidence about them.

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
  be true lives in the project's patterns record, if the project has one
  (`docs/patterns.md`, on main), and that record outranks both the primer and
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
recorded here with its **observed** effect, not its intended one: one already
silently failed to land.

## The full suite runs WITHOUT the canonical env file sourced

A fact, not a duty, in a project that keeps its env in a canonical file outside
the worktree. Sourcing that file before running the whole suite turns tests red
that no diff caused, because the live-database suites stop skipping and run
against whatever the variables point at.

Run the full suite clean. Export the live-database variables only when you
deliberately want the live-database tests, and say so in the ledger when you do.
(Adopted 2026-08-14; `decisions.md` holds the night three agents each discovered
it the hard way.)

## Shared external quotas

Any per-window cap on an external system is run state, owned by the runner.
Carry-forward holds the last observed status, its timestamp, and who holds the
window. **Two agents never hold the same quota at once.** Schedule live halves
first, while the window exists.

## The round header — one block, built once, pasted into every brief

A **round** is the set of agents spawned for one issue: the implementer, then both
gates, then any retry. Before the first spawn of a round, fill this block. Paste it
verbatim into every brief in that round. A field you cannot fill stops the spawn —
you settle it, you do not leave it out.

```
Browser harness:  <the tool name that PAINTS in this environment>
Register:         <absolute path>
Issue file:       <absolute path>
Merge briefing:   <absolute path>
Verdict goes to:  <absolute path>
Private copy:     <absolute path carrying the issue id and the role> + the rsync recipe
Settlements:      <every settlement this round is working under, verbatim>
```

**Why a block and not a rule.** The rule that a brief names the place and not only
the act was adopted on 2026-08-09, restated as a check on 2026-08-14, and failed a
third time in a run on 2026-08-16; `decisions.md` holds its three faults, one
shape, and none of them a prohibition.

A third telling would have failed the same way. The block turns naming the place
into a field you fill and settlement parity into a structural fact: one text, one
paste, every agent in the round. (Adopted 2026-08-16.)

## Per-issue loop

1. **Settle the road before spawning.** If the issue admits more than one
   plausible approach and no triage decision picks one, choose it now and put the
   choice — and the roads rejected — in the spawn prompt. Minutes here against
   hours later: 17 minutes versus 3h52m on one measured pair (decisions.md). Then
   spawn `run-issues-implementer`.

   **Every implementer spawn passes the cap first**, this one and the escalated
   third in step 8. It refuses the fourth attempt and the third criteria reset,
   and prints the counts it refused on:

   ```bash
   python3 ~/.claude/skills/run-issues/check_attempt_cap.py --ledger <run.md> --issue <id>
   ```

   A non-zero exit means the issue is `blocked`: ledger it and go to step 9.
   **Stamp `attempt <N>` into the issue's row before each spawn** — that marker
   is the only thing the cap counts. The older `implement …` / `retry 1 …`
   stamps cannot be counted, because `retry 00:18` is a clock and `retry 10.2`
   is a duration in minutes, so a row still carrying them is refused until it is
   restamped.

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

   **A prohibition in a brief names the SYSTEM, not the verb.** Every "do not"
   carries the forbidden thing AND the permitted one, with an absolute path
   wherever a path exists. The pattern: "the test database is the only WRITABLE
   database" constrained the operation and left production reachable, so a verify
   gate read production with a service-role key. A brief that constrains the ACT
   while leaving the PLACE unnamed gets a different answer from every agent.
   (Adopted 2026-08-09; `decisions.md` holds that run's other two faults.) The
   round header above carries the paths and the harness for every brief; this
   rule governs the prohibitions the header has no field for.
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

   **A brief that names a path for a private copy also names the method.** The
   recipe, measured on one run: `rsync` the tree excluding `node_modules`,
   `.next` and `.git`, then symlink the real `node_modules` into the copy. 0.8
   seconds and 66 MB, and module resolution through the symlink was proved by
   running a test file inside the copy. A gate given a path and no method invented
   its own — `tar` over all 790 MB including `node_modules` — produced nothing for
   81 minutes and was killed with no verdict. Every later gate got the recipe and
   none has hung since. *Honest caveat: nobody re-ran `tar` against a control, so
   the slow-`tar` diagnosis is untested. What is established is that the
   replacement is fast.* (Adopted 2026-08-14; a recipe nobody writes down
   is a recipe every gate reinvents.)

   **Concurrent gates share a tree but not a pen.** Both gate briefs now require
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

   **At prep, if a recorded default seeds, deletes or renames a row in a shared
   database, read the test files this run has already committed on this branch.**
   One `git diff --name-only <fork-point>..HEAD -- '*.test.ts'`, then read the
   ones that touch the same tables. A default hardened days ago cannot know about
   a guard an earlier issue in the same run committed ninety minutes back, and no
   hardening pass can catch it because that guard did not exist when the issue was
   hardened. One issue's recorded default would have seeded a second
   profile-holding workspace on the test database while a sibling issue's
   freshly committed schema test asserted exactly one existed; the runner
   caught it by chance. A permanently red test invites a relaxation, and that
   relaxation disarms a tenancy guard. (Adopted 2026-08-14, narrowed from
   "shared state" — which nobody could apply — to rows in a shared database,
   which is mechanical.)
4. **Before reading either verdict, run the check.** One command per gate,
   against the issue file in this run's own worktree:

   ```bash
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Verify gate"
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Review gate"
   ```

   **It has four refusals, not three.** It exits non-zero when the heading is
   absent, when nothing sits under it, when a row still reads `pending`, and when
   the section sits above the newest `Implementation record, attempt N` heading —
   `stale`, meaning the section grades an earlier diff. `stale` closes a measured
   fault: one issue's attempt-2 gates died with their session before writing, the
   file still held attempt 1's two rejections under the same two headings, and
   this check passed both. **A non-zero exit is neither a pass nor a rejection:
   the gate did not report.** Re-spawn it, or ledger the issue `blocked` with what
   the check printed. Never let one gate's verdict stand as the round's answer
   while the other is missing.

   A gate that drilled on a private copy can write its verdict beside the copy
   instead of beside the branch, and a verdict in the wrong checkout is one
   careless `rm` from gone. Passing the path in this worktree is what makes that
   a refusal instead of a silent pass. **This is a check and not a reminder on
   purpose:** the rule it enforces was told twice and failed a third time.
   (Adopted 2026-08-14; `decisions.md` holds the two gates that died writing
   nothing and the verdict left in the wrong tree.)

   **The spawn itself is gated too, where the hook is installed.**
   `hooks/run-issues-evidence-gate.py` in this pack refuses a verify- or
   review-gate spawn whose issue file holds no implementation record, or whose
   newest record sits above the last verdict of the kind being spawned. That is
   the fault upstream of this check: a gate with nothing to judge still writes a
   well-formed verdict, and a well-formed verdict passes here.

   Both pass → **verify the routings**: grep each target file for the exact
   line the gate quoted as appended — gates end each routed finding with that
   quote, and the runner greps the string, never a heading (a heading-level
   check has false-negatived routings that were present). A declared routing is
   not a routing. Check the verify gate's
   `Drove:` list against `git diff --name-only`; a route the diff touches and the
   gate never fetched is an incomplete verdict, not a pass. **Run lint** — it costs
   nothing and catches the shape defects no per-issue gate can see. Then commit,
   staging **explicit paths only** — never `git add -A` or `.`. Glance at
   `git status` and investigate anything unexplained *before* committing.

   **The citation checker runs at every issue's commit, and a citation this run
   moved becomes a register row before the next implementer spawns.** Where the
   repo carries the script: before the run's first commit, run
   `node scripts/check-issue-citations.mjs --all --quiet`
   once and keep the output as the run's baseline. After each commit, run it again;
   the delta against the baseline is what this run broke, in its own issue files
   and in open backlog issues nobody in the run opened. File each new `moved` or
   `gone` as a register row naming the citation and the commit that moved it, then
   replace the baseline with the current output. The loop advances to the next
   issue once every new one is filed.

   The row is the whole remedy, and the run repairs nothing: a run may not edit the
   specification it is graded against, so the repair belongs to the next
   `/harden-issues` pass over that issue, which already reads the file and is
   already allowed to write it (ruled 2026-08-15). The checker holds the same rule
   in its own code and never writes an issue file.

   (Adopted 2026-08-18, from one run's finale; `decisions.md` holds that run's
   citation counts and the drift mechanism behind them. It trades run time for
   record accuracy, which is a price only the human may set, and the human set
   it.)

   **The runner commits. An implementer never commits its own work**, and the
   runner says so in every spawn. A self-commit does no visible harm, and that is
   the trap: it silently changes what "the diff" means to a gate already reading
   it, so the runner must hand those gates an explicit commit range instead of
   the working tree. Where an implementer has committed anyway, do not revert
   it — record it and give the gates the range (decisions.md).
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

   **The round also re-runs the citation check over the files it touched, and
   quotes the summary line, before it may close.** A round that closes on its own
   say-so states a conclusion where it owes a measurement: one run closed claiming
   every item was verified, and a third of one register row had not landed.
   Nothing shipped wrong; the closing claim did. (Adopted 2026-08-23.)

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

   **A negative conclusion drawn from a grep does not travel without its scope,
   in the same sentence.** "There is no X" from a single-line grep is a statement
   about that pattern in those paths, not about the codebase, and it must say so
   where it is asserted rather than in a paragraph nearby. It was advice here
   first, and `decisions.md` holds the night that advice was broken. Adopted as
   admissibility 2026-08-14 — a scopeless negative is not
   passed onward, by a gate, a finale or a runner, and a reader who receives one
   sends it back rather than acting on it.

   **When a round deletes a claim, search the branch for a twin before the round
   closes.** One grep for a distinctive phrase from the deleted sentence. A claim
   worth writing once tends to get written twice, and no gate reads two issues,
   so the second copy ships unread. The search costs seconds and costs nothing
   when it finds nothing. (Adopted 2026-08-11, narrowly; `decisions.md` holds the
   run that earned it and the reason no authoring-time rule came with it.)

   **Three rules on what a claim may SAY. They bind every artefact an agent
   writes — issue files, the primer, migration headers, the briefing — not
   only a rejection fix.** (decisions.md.)

   *Never write that something is the only copy.* Uniqueness across a corpus is
   not a fact one agent can establish, so "this is now the sole home of X" is a
   guess wearing a fact's clothes. Cite the canonical location; do not claim it
   is the only one. The class survives its own cure: `decisions.md` holds the
   instance written as the REPAIR for a stale-prose defect, by an agent following
   the deletion rule above.

   *A recorded cause is tested against a control, never merely observed.* One
   run that works does not name the reason it works, and one control run settles
   it. A wrong cause does the most damage exactly where the recorded example sat
   — in a line written to correct a previous agent's wrong cause
   (`decisions.md`).

   *Every citation carries its repo-relative path in full, every time.* Not the
   first mention only, and never a bare filename afterwards. A bare filename the
   tree holds twice resolves to plausible code, so the reader does not discover
   the mistake — they find a defect that is not there, and an implementer can
   lose a strike to it. Repetition is cheaper than ambiguity (decisions.md).
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
   Three runner errors in one run shared this shape (decisions.md). Ledger
   actuals derive from commit times, full stop.

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
   compound past what this skill promises (decisions.md). **This paragraph
   states the intent; the pre-spawn check in step 1 is what enforces it.**

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

**One issue, one implementer spawn. Always.** Small-issue coalescing was retired
on 2026-08-15; `decisions.md` holds the measurement. Do not reinvent it,
and do not report on it in the merge briefing.

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
and does not go through the register — the same reason upstream issue authoring
is untouched by any of this. Not "that becomes its own issue" — the
number, or the file and line where the work now lives. A ruling with no artefact
cannot be told apart from a ruling nobody made, and nothing is watching for one:
`decisions.md` holds the split that survived nine hours as a phrase inside
another issue's file.

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

After the last issue the runner writes `finale-mechanical` into the ledger, and
**that write is the trigger to read `finale.md`, beside this file, before the
first finale step runs.** Nothing else starts the finale, and a runner that
writes the state without reading the file has skipped it.

The finale is one full load at the end of a run, so it is not resident here. Its
five steps, the ledger states after `finale-mechanical`, and what each step may
not skip are specified there and nowhere else. The run ends at `awaiting-merge`,
and the merge is the human's.

## Resume across usage limits

**The ledger resumes a run. The cron only saves short waits** — it reaches no
further than a five-hour window the same session sits through. A weekly limit
resetting days out is resumed by a human re-invoking `/run-issues resume`.

**The ledger carries an owner line; staleness is the FILE's mtime, never a
handwritten timestamp.** One line at the top: `Owner: <session>`. Every
transition already updates the file's mtime and nobody can forget to write it —
a handwritten `heartbeat <HH:MM>` field it replaced could be, and was
(decisions.md). A long implement attempt
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

**Pick the ledger before you read one, and `resume.md` beside this file says
how.** Read it on every `resume` invocation and on every revival from a halt,
before opening any `run.md`. It holds the script that chooses between the copies
every worktree carries, what a refusal from that script means, and the reading
order that follows. Guessing here cost 25 minutes once, which is why the
procedure is a script and not a judgement.

## Pre-flight

- **The launch line is a gate, not an announcement. Nothing spawns before it
  prints.** One line on every invocation — issues in order, branch, the resolved
  session model, and what will NOT happen (no merge, no prod). It is still not a
  wait: it prints and the run carries on at once, so the gate costs nothing. What
  it buys is that the interrupt window exists at all. (Adopted 2026-08-07;
  `decisions.md` holds the run whose line printed too late to interrupt, and the
  older 11.5-hour halt from a misread request.)
- **Re-derive every fact the run will carry into its spawns, from source, and
  name the source beside it.** Carry-forward entries, batch-plan sentences,
  anything a previous session wrote down — none of it is evidence. Read the
  function, run the query, open the migration. A carried misreading and the truth
  it replaced can fail in opposite directions — one predicts a loud break, the
  other a silent misfile — so the error stays invisible while it does damage. One
  read of the source at pre-flight catches it; `decisions.md` holds the nine-hour
  instance.
- **Workers inherit the session model. Let them.** Agent files use
  `model: inherit`, so the run takes the tier it was launched on. Never pass a
  `model:` value on a spawn to override that: the spawn tool's `model` parameter
  beats agent-file frontmatter, so a spawn-time value silently defeats both
  `inherit` and any model an agent file might pin on purpose. No agent file in
  this pack pins one today, so the tier is chosen at launch (`decisions.md`).
  Never ask, and never stall — the launch line above is where a wrong tier gets
  caught, one keystroke before spawn #1.

  **The scope of that prohibition is exactly "roles that HAVE an agent file", and
  one spawn falls outside it.** The finale's board render has no agent file, and
  `finale.md` requires a cheap model named explicitly on the spawn call — an
  unnamed spawn there inherits the session model and pays the top tier to convert
  a large markdown file into HTML. Read the two together: this bullet governs the
  briefed roles, where a spawn-time value silently defeats the file; `finale.md`
  governs the one spawn that has no brief to inherit from. (Scoped 2026-08-22.
  The alternative, minting an agent file for the board renderer, was refused:
  it adds a file to fix a wording problem.)
- **Record the session model in the ledger's owner line and in the merge
  briefing.** A run on a tier this pipeline has no evidence for is still a valid
  run, and it is also the first evidence at that tier — so whoever reads its
  verdicts later has to know which tier produced them. Say it once, where the
  verdicts live.
- **Orchestrator cost, stated at launch.** Run

  ```
  python3 ~/.claude/skills/run-issues/orchestrator_cost.py --days 7 --issues <count>
  ```

  and paste its table into the launch message. It reads the last week's run transcripts
  and prints what the orchestrator cost at each batch size already run.

  **This states a fact. It refuses nothing, and it recommends no size.** There is no
  ceiling on how many issues a run may take, and the reading must come from inside the
  last week: a workflow that changes weekly makes an older figure a description of a
  system that no longer exists. If the window is empty the script says so and prints
  nothing else. Do not go looking for an older number.

  What five runs measured, and why the column matters: the orchestrator is the single
  session that holds the whole run, and every turn re-reads the conversation before it.
  Four issues cost it 0.96M weighted tokens per issue, nine cost 1.44M to 1.67M, and
  thirteen cost 2.45M. Nothing else in the audit moved a number this far.
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
  (Adopted 2026-08-07; `decisions.md` holds the question of what it costs in
  tokens, and the answer.)

  The failure it closes: a typecheck can exit 0 against a global install and never
  load the repo's own types. **A green produced without dependencies on disk is a
  false green** (decisions.md).
- **Verify the allowlist, never assert it.** Dry-run every command class this run
  will use, in no-op form, before spawn #1. A miss is a launch-time blocker;
  mid-run it is a worker blocked on a prompt, stalling silently. (The old text
  asserted coverage; the actual settings.json refuted it.)

  **Refuse to spawn while any class is refused or unverified.** Never start a run
  intending to approve a prompt later. The whole value of this check is that it
  fails while the human is still at the keyboard.

  **Derive the list from the roles this run will spawn, not from this bullet.**
  What follows is what today's roles need. It is a floor, not a definition. Walk
  each role the run will spawn and ask what it shells out to.

  - **Implementer** — typecheck, lint, test, the cold-build `rm -rf`, git stage
    and commit, any migration script.
  - **Verify gate** — **starting the dev server**, by name, from the repo's
    `.claude/launch.json`, where the project has one. A verify gate cannot drive
    an acceptance path without it. **It probes that server through a repo probe
    script allowed by one prefix rule, if the project has one, never with a bare
    `curl`.** A raw `curl` gets allowed as an exact string, so the next probe
    with a different port, path or label prompts again — which is how one run
    stopped for a permission dialog at the end, unattended. A probe script that
    refuses any target that is not the local machine is what makes one standing
    permission safe to grant.
  - **The runner itself** — the cron-creation tool, for the resume wakeup, on
    any run that could meet a usage limit.

  **The dev server is named here because leaving it off cost six hours.** The
  bullet it replaced ran correctly and still lost them: a runner dry-ran every
  class the old text named, because it read an illustrative list as a complete
  one. That is the fault the derive-from-roles rule closes, and it is why the
  list above is a floor rather than a definition (decisions.md).
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
`## Ruled` because nobody has answered it. Write it in the form the project's
question standard sets, if it has one — with the run's recommended answer,
marked `[reversible]` or `[irreversible]`.
