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

**Every spawn in this run names `run_in_background` on the call. Do not take the
tool's default. The verify gate carries `true`; every other spawn carries
`false`.** The runner has nothing to do while an implementer or a review gate
runs — it cannot open the gates until the implementer returns, and it cannot judge
until both gates answer — so the Agent tool's own rule applies: pass `false` when
the next action depends on the result and nothing else could usefully happen
meanwhile. The verify gate is the one exception, because something else CAN
happen while it runs: the review gate. Spawn the verify gate in the background,
then spawn the review gate in the foreground on the next turn, and the two overlap
by construction. Ruled 2026-09-04 after run `batch-b5e96d` spawned zero of fifteen
gate pairs together at a measured cost of 97 minutes.

**The measurement first recorded here was wrong, and the rule survives on the
paragraph above alone.** The 2026-08-17 audit of run `cab74e` blamed eight 17-to-23
minute stalls, 158 minutes, on background spawns: the runner asleep past finished
work until the resume cron woke it. The 2026-08-18 re-measure joined every spawn to
its subagent transcript and refuted that. A task notification woke the runner
within seconds of every completion, and the eight gaps were the workers' own
runtimes. Foreground spawning recovers none of them; expect it to save no clock.
What it buys is not betting the run on notification delivery holding across
harness versions.

**The cron stays, at its usage-limit interval, and it rescued that run exactly
once — not from a background spawn.** At 06:34Z the runner wrote "spawning 357",
ended its turn, and never made the Agent call; the cron caught the 24-minute gap.
`run_in_background: false` cannot prevent a call that was never made. Shortening
the interval buys nothing.

**The field is enforced, not remembered.** A `PreToolUse` hook,
`~/.claude/hooks/run-issues-foreground-gate.py`, refuses a `run-issues-verify-gate`
spawn whose `run_in_background` is not exactly `true` and any other `run-issues-*`
spawn whose value is not exactly `false`, and its message says how to reissue.
Before 2026-09-04 it required `false` everywhere and left "spawn both gates in
one message" as the only concurrent shape. Run `batch-b5e96d` on CLI 2.1.255
never once produced that shape across fifteen pairs, accepted a correction and
repeated the fault a turn later. A reminder failed twice, so the shape is now one
the hook can refuse.

**This is also what row 23 guards.** A runner that does not block can mark an
issue done before the work lands. `skills/lib/check_verdict.py` refuses on a gate
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

In the main checkout, under `.scratch/<feature>/runs/<batch-id>/`. **One directory
per run, keyed by the batch id**, so two runs on one feature never share a file
(ticket 38 of the pilot-delivery map, the one-run-per-feature layout ticket, ruling
10, landed 2026-09-05). The batch id
is minted at launch: `batch-` plus six hex characters (`openssl rand -hex 3`), and
it is the same id the branch carries after `claude/run-issues-`, the register
prefix `rn-<id>-NN`, and every journal line. Create the directory before spawn 1.
Nothing archives, renames or overwrites another run's state, because no two runs
have a path in common. The fixed names `.scratch/<feature>/run.md`, `primer.md`,
`merge-briefing.md` and `run-journal.md` are retired: `find_live_ledger.py` does
not read them, and `~/.claude/hooks/run-state-path-guard.py` refuses a write to
them with the right path in its message, so a slip costs one reissued call and
never a halt.

- **`run.md`** — the ledger. Status table plus a **Carry-forward** section, plus
  the one live halt block if the run is halted. Nothing else. Every spawn reads
  it, so every line in it is billed a dozen times a run.

  **Its header carries the two settings a later measurement cannot recover:**
  `Session model at launch:` and `Session effort at launch:`, one line each,
  written before spawn 1. The model line was already a habit; the effort line is
  new, and both are now required rather than remembered. **The reason is a void
  experiment.** The 2026-08-21 run of 395, 394, 396, 397 and 395b was the first
  trial of `medium` effort. `orchestrator_cost.py` read it at 1.51M weighted
  tokens per issue on 2026-08-23, above the threshold that would have ended the
  effort question — and the reading had to be thrown away, because neither
  `run.md` nor `run-journal.md` contained the word "effort" anywhere, so nobody
  could prove which tier produced it. A run that does not stamp its own settings
  cannot be used as evidence about them.

  **Measure both, never guess them.** A session cannot read its own settings from
  its context, so a runner told only to write the lines writes what it assumes,
  and a guessed stamp is worse than a missing one: the next reader treats it as
  evidence. Both values are in the process's own command line. Run this before
  spawn 1 and copy what it prints:

  ```
  ps -o args= -p "$CLAUDE_PID" | tr ' ' '\n' | grep -A1 -E '^--(model|effort)$'
  ```

  It returns the flags as pairs, for example `--effort` then `high`, and
  `--model` then `claude-opus-5`. This is the road `machine-preflight.py` already
  takes to read the model, so the hook and the ledger agree by construction. If
  `$CLAUDE_PID` is empty or a flag is absent, write `unmeasured` on that line and
  say so in the journal. Never write a value you did not read.

  Added 2026-08-30. The harness fixture's first pre-flight reported this field as
  unobservable and said it would be left blank or guessed. The value was readable
  all along; nothing had written down how.

  **Two more header lines, written at launch BY `model_map.py`:** `Model map at
  launch:` and `Role effort at launch:`, a `role=value` list each, all twelve loop
  roles named in both (ticket 39 of the pilot-delivery map,
  every-worker-inherits-the-session-model, rulings 4 and 7). Run this before spawn
  1 and paste what it prints:

  ```
  python3 ~/.claude/skills/run-issues/model_map.py "<everything after /run-issues>"
  ```

  Pass the command text exactly as it was typed, scope and all. It measures the
  session model off `$CLAUDE_PID` the same way the block above does, so the ledger
  and `machine-preflight.py` cannot disagree. **Exit 1 is a launch-time stop:
  spawn nothing, write no ledger, and hand the human the refusal.** That is the only
  stop this ticket has; once a run is live nothing in it ever halts (rulings 10
  and 22).

  **In practice you should never see that exit 1, and that is deliberate.**
  `machine-preflight.py` row 14 reads the same map at PROMPT-SUBMIT time, through
  the same parser, so a bad token, an empty `models:` word and an inverted map
  are all refused before this step is reached — before the batch id is minted and
  before the QA workspace is seeded. The human ruled on 2026-09-05 that a map refusal
  must arrive in the first two minutes, not after the ledger and the workspace
  exist. This step stays as the second gate and as the writer of the header.

  **The map names a model per role for this run.** It is typed after the issue
  list, behind the word `models:`:

  ```
  /run-issues 512 513 models: implementer=opus gates=fable
  ```

  Keys are `all`, `workers`, `gates`, or one agent type without its prefix —
  `implementer`, `escalated`, `verify`, `review`, `review-critical`, `finale`,
  `finder`, `fixer`, `claim-gate`, `fix-gate`, `fix-gate-critical`, `promotion`.
  More specific wins, whatever the order typed. Values are `haiku`, `sonnet`,
  `opus`, `fable` and `inherit`. `workers` is the four roles that build and
  `gates` the six that check; `finale` and `promotion` are reached by `all` or by
  their own key. With no `models:` word the default file
  `model-map.default` in this directory is read, and it ships at `all=inherit`, so
  a launch that types nothing behaves exactly as every run did before the map
  existed.

  **`inherit` never reaches a ledger.** Every role is resolved to a concrete name
  at launch, so a resume on a different session model changes the orchestrator
  only. The twelve agent files stay `model: inherit`, so a spawn by hand is
  untouched — the map reaches a run through the ledger and nowhere else.

  **An inverted map is refused before anything is spawned.** No adversarial gate
  runs below the tier of the worker it checks (ruled 2026-08-15,
  `~/.claude/rulings.md:99-121`); the tier order is `haiku < sonnet < opus <
  fable` and equal is legal. A wrong reject costs one retry round; a wrong pass
  has no catcher until the merge. `implementer=opus gates=sonnet` is refused, and
  so is the hunt line `finder=fable fixer=opus` on any session below `fable`,
  because it leaves the claim gate under the finder.

  **The effort line is recorded, never set.** The Agent tool takes `model` and has
  no effort field, so effort lives in each agent file's frontmatter and the launch
  only reads it. A file it cannot read records `unmeasured`, for the same reason
  the session model does: a guessed stamp is worse than a missing one, because the
  next reader treats it as evidence.

  **Two more header lines, written at launch BY the seed script:** `QA workspace:`
  with the workspace id and `Sign-in user:` with the run user's email,
  `run-<batch-id>@example.test`. `scripts/seed-run-workspace.mjs --ledger <run.md>`
  writes them itself, so no uuid passes through a keyboard. Every verify gate signs
  in as that user, so `current_workspace()` scopes its reads to this run's rows;
  every fixture script run inside the worktree reads that id off `run.md`
  itself and refuses a `SEED_WORKSPACE_ID` naming any other (sitting 5); and the finale
  deletes by it (ticket 38, the one-run-per-feature layout ticket, sitting 2, rulings 3 and 12).

  **It is pruned, not appended to.** Three things go in the journal instead, and
  the runner moves them the moment they appear: a **superseded halt block** (the
  new one replaces it — delete the old one, do not mark it), the **finale
  write-up** (the ledger carries the stage and the verdict, one line each; the
  reasoning is narrative), and any **verdict story** longer than its row.
  The prune runs at the two transitions that already exist — every halt-block
  write and every row moved to `done` — not as a separate chore. Two mechanical
  triggers, either one means prune before the next spawn: more than one
  `## HALT BLOCK` heading, or status table plus Carry-forward under half the
  file (155-157: decisions.md). A third trigger while an issue is still
  fighting: before re-spawning gates on the same issue, a row over ~10 lines
  loses its verdict story to the journal, keeping stamps only — a growing row
  is re-billed to every one of its own gate spawns, and the existing triggers
  fire exactly when it has stopped growing (181's row: decisions.md).
- **`run-journal.md`** — the narrative, append-only. Every log line goes here:
  what each attempt did, verdict stories, dead ends. Subagents never read it. It
  is read exactly twice — by a resuming runner, and by the finale.
- **`primer.md`** — the codebase primer. Fresh subagents read this instead of
  exploring. The first implementer creates it; every implementer appends what it
  learns. Exploration is paid once per run. **A run reads only its own primer** —
  another run's directory is never read. It is written by implementers about
  implementer-written code, so it is orientation, never authority: what ought to
  be true lives in `docs/patterns.md`, on main, and outranks both the primer and
  the code.
- **`merge-briefing.md`** — the merge-read briefing, built up as the run goes.
  It starts empty in the run's own directory; there is no old one to archive.
  Gate verdicts get one summary line each; the full verdict text lives in the
  issue files, which already carry it. It is a thirty-minute read or it has
  failed.

  **The narrative sections are filled as each issue closes, not at the finale.**
  What shipped, what was minted, what was skipped, what waits on the human — each
  gets its lines when the issue that produced them goes `done`, while the runner
  still holds the facts. On the 209-215 run four sections were still empty
  placeholders when the finale opened the file, and one of them was the section
  that should have carried the WhatsApp deploy step — the single action in that
  batch that changed what a customer reads. A reader starting at the top met a
  stale test count before reaching the correction 100 lines down. An empty
  section is not neutral: it reads as "nothing to report" (209-215: decisions.md).

Ledger statuses: `queued → in-progress → gates → done`, plus `correction`
(between `gates` and `done`, when taken) and `blocked`. Both gates run under the
one `gates` status. Only the runner writes the ledger. Gates write
verdicts into issue files. Everyone appends; nobody rewrites another's section.

**Do NOT stamp transitions with the time.** `run_timings.py` is the single source
for how long anything took, and it reads the transcript, which is written whether
anyone remembers or not. Hand-written clocks have drifted 68 and 95 minutes on
past runs, and run `batch-88624c` wrote three times it had not read — 02:33, 08:26
and 08:25 — and corrected each one on checking. (Ruled by the human 2026-08-31, after
a sweep found that no script read them.)

**Two stamps survive, and they are the only two.** A correction round's row gains
`correction: open → closed HH:MM`, and the commit gains `committed <sha>`.
`check_commit_order.py` grades one against the other: it refuses a commit stamped
before the round it is supposed to carry, which is a fault run `batch-34455f`
carried twice.

**The close stamp comes from `date`, never from your own count of the clock.** Run
`date +%H:%M` and paste what it prints. A time you worked out from how long a step
felt is the class of stamp this rule deletes, and writing one into the one row a
checker still reads is worse than writing none.

**Carry-forward** is what the runner curates for future spawns: shared-quota state,
traps discovered, conventions later issues must follow, do-not-tidy lists. A
learning that lives only in the journal survives only if the runner remembers to
re-brief it. **Every entry names the issue(s) it serves**, and the runner deletes
it when its last consumer goes `done` — an unexpired entry is billed to every
remaining spawn. A human action taken mid-run (a SQL fix, a console change) is
recorded here with its **observed** effect, not its intended one: one already
silently failed to land.

## The full suite runs WITHOUT the canonical env file sourced

A fact, not a duty. Sourcing the canonical env file before running the whole
suite turns tests red that no diff caused, because the live-database suites stop
skipping and run against whatever the variables point at.

Run the full suite clean. Export the `QA_*` variables only when you deliberately
want the live-database tests, and say so in the ledger when you do. Adopted by
The human 2026-08-14; `decisions.md` holds the night three agents each discovered it
the hard way.

## Shared external quotas

Any per-window cap on an external system is run state, owned by the runner.
Carry-forward holds the last observed status, its timestamp, and who holds the
window. **Two agents never hold the same quota at once.** Schedule live halves
first, while the window exists.

**The Zoho organisation is one such quota, and it is held by a lock file, not by the
runner.** Every live Zoho suite runs through the wrapper, which takes
`~/.local/state/run-issues/locks/zoho-<org id>.lock` with an exclusive create,
heartbeats it every minute, waits behind any other holder — a second wrapper of
this same batch included, so pass the whole directory to ONE wrapper — breaks a
holder with no heartbeat for thirty minutes with a journal line, and sets
`ZOHO_LIVE=1` itself. The harness reads that lock file for the organisation it is
about to write and refuses unless it names this batch:

```
node --env-file=<env file> scripts/zoho-live-lock.mjs --batch <batch-id> --journal <run-journal.md> -- npx vitest run src/lib/zoho/live
```

**The wrapper is the project's, not this pack's**, and so are the seed, the sign-in
link and the teardown named elsewhere here. This pack ships no `scripts/`. What it
fixes is the shape — one lock outside every repo, keyed by the account written to;
one command; the journal told. A project with no live third-party suite has nothing
to serialise and skips this whole section.

(ticket 38, the one-run-per-feature layout ticket, sitting 2, ruling 4: serialise the suites; ruling 13: the lock is a file
outside every repo, keyed by organisation id).

## The round header — one block, built once, pasted into every brief

A **round** is the set of agents spawned for one issue: the implementer, then both
gates, then any retry. Before the first spawn of a round, fill this block. Paste it
verbatim into every brief in that round. A field you cannot fill stops the spawn —
you settle it, you do not leave it out.

```
Browser harness:  <the tool name that PAINTS in this environment>
Register:         <absolute path>
Run directory:    <absolute path of .scratch/<feature>/runs/<batch-id>/; run.md, primer.md and the journal are in it>
QA workspace:     <the id on run.md's QA workspace: line, seeded for this run alone; every fixture script run in this worktree reads it off run.md itself>
Sign-in user:     <the email on run.md's Sign-in user: line; dev-signin-link.mjs --batch <batch-id> mints it>
Dev server:       <the launch.json entry by name; it carries autoPort, so the port exists only in the preview_start result of the spawn that started it>
Issue file:       <absolute path>
Merge briefing:   <absolute path>
Verdict goes to:  <absolute path>
Private copy:     <absolute path carrying the issue id and the role> + the rsync recipe
Settlements:      <every settlement this round is working under, verbatim>
```

**Why a block and not a rule.** The rule that a brief names the place and not only
the act was adopted on 2026-08-09, restated as a check on 2026-08-14, and failed a
third time in the `dc132b` run of 2026-08-16; `decisions.md` holds its three
faults, one shape, and none of them a prohibition.

A third telling would have failed the same way. The block turns naming the place
into a field you fill and settlement parity into a structural fact: one text, one
paste, every agent in the round. Adopted by the human 2026-08-16.

## Per-issue loop

1. **Settle the road before spawning.** If the issue admits more than one
   plausible approach and no triage decision picks one, choose it now and put the
   choice — and the roads rejected — in the spawn prompt. Minutes here against
   hours later: 17 minutes versus 3h52m on the 112-116 run (decisions.md). Then
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

   **Stamp `gates <N>: verify=<pass|reject> review=<pass|reject>` into the row
   when both gates of a round have answered** — one token per gate ROUND, `N`
   being that round's number. Minted by ticket 37 of the pilot-delivery map,
   ruling 28, 2026-09-06, and read by `run_quality.py`.

   Write it beside whatever prose you were going to write; the prose is not
   forbidden and nothing is deleted. Two fixed verdict words only, `pass` and
   `reject`: **a token that also took `accept`, `passed` and `rejects` would be
   an eighth dialect rather than an end to the seven.**

   **Why it exists is measured, and it is `attempt N`'s own story.** Ticket 39
   sitting 4 read the verdicts out of prose across sixteen ledgers and found
   SEVEN dialects, every one of them read as silence until two review passes
   caught them — bolded verdicts in 17 rows, `gates both pass`, `v: pass · r:
   reject`, `rejected by BOTH gates`, `one correction round`, `correction
   18:48->18:54`, `correction open 04:06`. Two ledgers reported `0 strike(s)`
   on runs that had charged them. A regex cannot be widened out of that; only
   the writer can end it, which is exactly why `attempt N` replaced
   `implement`/`retry`.

   **A strike is still DERIVED and the token does not state one.** It says what
   the gates answered. Step 5's prose-deletion road and a runner-error
   annulment both cancel a strike in prose and write no marker, so the count
   stays "rounds rejected since the last criteria reset", and a row whose own
   words disagree with the count is marked `*` with both shown and neither
   preferred.

   **Nothing refuses a row without it**, and that is deliberate: sixteen
   ledgers and 143 rows were written before it existed, ruling 3 loses no
   history, and the prose reader stays. `run_quality.py` counts how many rounds
   carry the token and prints the figure, so the rate at which it is actually
   written is visible rather than assumed — the same discipline as the
   `Origin:` check's pass line.

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
   a clean issue (181 against its six siblings: decisions.md).

   **A prohibition in a brief names the SYSTEM, not the verb.** Every "do not"
   carries the forbidden thing AND the permitted one, with an absolute path
   wherever a path exists. The pattern, from the 2026-08-09 run: "QA is the only
   WRITABLE database" constrained the operation and left production reachable, so
   a verify gate read production with a service-role key. A brief that constrains
   the ACT while leaving the PLACE unnamed gets a different answer from every
   agent. Adopted by the human, 2026-08-09; `decisions.md` holds that run's other two
   faults. The
   round header above carries the paths and the harness for every brief; this
   rule governs the prohibitions the header has no field for.
2. **Read its final message before doing anything else.** If it reports unfinished
   work, the issue is not gate-ready — re-spawn to finish it, or mark `blocked`.
   If it reports the acceptance criteria are *wrong* rather than unmet, spawn a
   review gate to confirm that claim only; if confirmed, set the issue
   `needs-harden` with the evidence and move on. Never build to criteria a worker
   has shown to be wrong.
3. Spawn **the verify gate with `run_in_background: true`, then the review gate
   with `run_in_background: false` on the next turn, without waiting for the
   verify notification.** Neither reads the other's verdict — verify drives the
   app, review reads the diff — so serialising them buys nothing and the wall
   clock is the slower of the two rather than their sum. The round ends when
   both verdicts are in: the review gate's return and the verify gate's task
   notification, in either order. Read both before step 4.
   Use the review `-critical` variant when the diff **changes** money computation,
   auth or secret handling (touching a file that has a price field does not
   count). If verify rejects, read the review anyway: its findings still route,
   and its work is already spent.

   **A brief that names a path for a private copy also names the method.** The
   recipe, measured on the 327 run: `rsync` the tree excluding `node_modules`,
   `.next` and `.git`, then symlink the real `node_modules` into the copy. 0.8
   seconds and 66 MB, and module resolution through the symlink was proved by
   running a test file inside the copy. A gate given a path and no method invented
   its own — `tar` over all 790 MB including `node_modules` — produced nothing for
   81 minutes and was killed with no verdict. Every later gate got the recipe and
   none has hung since. *Honest caveat: nobody re-ran `tar` against a control, so
   the slow-`tar` diagnosis is untested. What is established is that the
   replacement is fast.* Adopted by the human 2026-08-14; a recipe nobody writes down
   is a recipe every gate reinvents.

   **This copy cannot run `npm run build`** — Turbopack panics on the `node_modules`
   symlink. Use `cp -al` for a build, measured at 14 seconds on the `402-251d11`
   tree, which gives a real directory instead. Tests and mutation drills keep the
   rsync recipe. Found by that run's attempt-3 implementer.

   **Three facts about those two copies. None of them is guessable from the
   command, and each one cost a run something before it was written down here.**

   *`cp -al` makes HARD LINKS, so a write inside that copy lands in the run's own
   worktree.* It is a copy for READING and BUILDING, never for a drill that
   writes. On run `bridge-cse`, 2026-08-24 at 17:05, the runner appended three
   lines to a file inside a `cp -al` copy to settle a split between two gates.
   The write went straight into the run worktree, and the attempt-2 brief had to
   be rebuilt around it. Where a drill must write, use the rsync recipe, which
   copies.

   **A drill that writes proves its copy is not hard-linked, before it writes.**
   The sentence above says which recipe to use; it cannot refuse anything. This
   can:

   ```bash
   ls -li <file in the copy> <the same file in the run worktree>
   ```

   The same inode means the copy is hard-linked and the write will land in the
   run's own worktree. Stop. Different inodes mean it is safe. Adopted by the human
   2026-08-27 as B5, on the reasoning that turned a sentence into a check.

   *The rsync copy's `node_modules` symlink is a TWO-WAY DOOR.* A path that
   resolves through it reaches the real directory. Issue 338's verify gate ran
   `rm -rf node_modules/.vite` inside its private copy on the same run and
   deleted the RUN worktree's vitest transform cache. No tracked file moved, and
   nothing warned. Delete nothing under `node_modules` from inside a copy.

   **Where a repo moves that cache, the reason to type that command is gone.** `vitest.config.ts` sets `cacheDir: "./.vitest-cache"`, so
   each tree — main, a worktree, an rsync copy — caches into its own project root
   and `node_modules/.vite` holds nothing. Clear a stale cache with `rm -rf
   .vitest-cache` inside your own copy, which cannot reach anything else. Ruled by
   the human 2026-08-29 after three gates deleted the run's cache on 2026-08-27
   despite the warning above; they had already refused a stronger warning on cost,
   and a reminder that three briefed agents ignored is not a control. A repo that
   has not made this change keeps the older rule alone.

   *The rsync copy excludes `.git`, so anything reading history refuses there,
   and that refusal is not damage.* `.git` is 87 MB against a 66 MB copy, so
   carrying it would more than double the copy to serve one script. On run
   `bridge-cse` both issue 408's gates and issue 409's gates independently spent
   time diagnosing the same unexplained red, and 409's filed it as `vg409-01`.
   Fixed at the source on 2026-08-24 rather than left as a warning: the two cases
   in `tests/scripts/check-issue-citations.test.ts` that drive git now SKIP when
   the tree has no `.git`, and `scripts/check-issue-citations.mjs` exits 3 with
   `REFUSED no-git-repository` naming the copy as the likely cause. A gate that
   meets either one is reading a correct answer, not a fault.

   **Concurrent gates share a tree but not a pen.** Both gate briefs now require
   mutation drills on scratchpad copies; a gate that genuinely must write the
   tree declares it in its verdict, and then it is the only writer — a "touch no
   code" gate that mutates source to prove a test can fail is a writer, whatever
   its banner says. Before committing, re-check each graded file's checksum
   against the ones the gates recorded at gate close. On 186 the tree sat
   reverted to the pre-fix file for two minutes mid-gate, one gate's backup
   captured the mutant, and only a staging-time checksum stood between the run
   and committing the defect it had just fixed (decisions.md).

   **Each gate drills in its OWN private whole-tree copy, at a path carrying its
   issue id and its role.** Never a shared scratch directory, and never a name
   two gates could both choose. The 209-215 run lost work twice to this in one
   day: 210's gates both picked the scratchpad name `drill`, and one gate's
   `rm -rf` destroyed the other's copy mid-run; 211's gates then collided in the
   run's own tree, where one gate briefly read the other's live mutant.
   Checksums at gate open and close cannot see the second case — the file is
   back before either stamp is taken. A private copy makes both unrepresentable
   rather than detectable (209-215: decisions.md).

   **While the gates run, the runner preps issue N+1, read-only:** settle its
   road, size it, pre-write the spawn prompt, prune the ledger, run the fixture
   pre-check (below). None of it touches the tree, so single-writer holds; on
   gate-pass only routing-verify, lint and commit remain serial (155-157:
   decisions.md).

   **The coverage check runs in that same window, never before the gates.** Start
   it when the gate spawns go out and read it at the commit step, which is already
   serial:

   ```bash
   npx vitest run --coverage.enabled --coverage.provider=v8 \
     --coverage.reporter=json --coverage.reportsDirectory=coverage \
     --coverage.reportOnFailure=true
   python3 ~/.claude/skills/run-issues/check_diff_coverage.py \
     --repo . --diff-range <fork-point>..HEAD --coverage coverage/coverage-final.json
   ```

   **`--coverage.reportOnFailure=true` is not optional.** Vitest writes NO
   report at all when any test fails, and the check then refuses `no-report`
   over a suite that ran perfectly well. Measured 2026-08-30: a run without the
   flag produced an empty directory and cost 73 seconds to repeat.

   It refuses a diff that changes source and changes no test, and a diff whose
   changed lines the report shows unexecuted. It also refuses when it cannot
   grade — no report, an unreadable one, or one older than the code — because a
   check that cannot see its input must not pass.

   **It does NOT grade a standalone script, and it names every one it skipped.**
   Added 2026-08-30, closing `rn483-01`. A file is excused only when all three
   hold: it sits at the TOP LEVEL of a `scripts/` directory, nothing in the
   repository imports it, and the coverage report does not mention it. Any one
   failing puts it back under the full bar, and git failing to answer counts as
   a failure. So `scripts/lib/…` is graded, and so is a script the moment a test
   imports it. **Read the `NOT GRADED` block in its output before you quote its
   percentage** — the block is how a run records the exclusion, so no verdict
   needs to explain a script in prose any more. The `untested` half is
   unchanged: a diff adding a script and no test is still refused. **Ordering it before the verify
   spawn would add its whole runtime to every issue's critical path**, and the
   window above costs nothing. Measured on this repo 2026-08-23: the suite takes
   31s clean and 40s with coverage, so the check adds about 9 seconds of work to a
   window that already holds minutes of gate time.

   **At prep, if a recorded default seeds, deletes or renames a row in a shared
   database, read the test files this run has already committed on this branch.**
   One `git diff --name-only <fork-point>..HEAD -- '*.test.ts'`, then read the
   ones that touch the same tables. A default hardened days ago cannot know about
   a guard an earlier issue in the same run committed ninety minutes back, and no
   hardening pass can catch it because that guard did not exist when the issue was
   hardened. Issue 319's recorded default would have seeded a second
   profile-holding QA workspace while issue 317's fresh
   `tests/schema/grain-pin.live.test.ts` asserted exactly one existed; the runner
   caught it by chance. A permanently red test invites a relaxation, and that
   relaxation disarms a tenancy guard. Adopted by the human 2026-08-14, queue item
   T24R1-5, narrowed from "shared state" — which nobody could apply — to rows in a
   shared database, which is mechanical.
4. **Before reading either verdict, run the check.** One command per gate,
   against the issue file in this run's own worktree:

   ```bash
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Verify gate"
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Review gate"
   ```

   **It has four refusals, not three.** It exits non-zero when the heading is
   absent, when nothing sits under it, when a row still reads `pending`, and when
   the section sits above the newest `Implementation record, attempt N` heading —
   `stale`, meaning the section grades an earlier diff. `stale` closes the
   2026-08-19 fault: issue 390a's attempt-2 gates died with their session before
   writing, the file still held attempt 1's two rejections under the same two
   headings, and this check passed both (`check_verdict.py:28-34`). **A non-zero
   exit is neither a pass nor a rejection: the gate did not report.** Re-spawn it,
   or ledger the issue `blocked` with what the check printed. Never let one gate's verdict stand as
   the round's answer while the other is missing.

   A gate that drilled on a private copy can write its verdict beside the copy
   instead of beside the branch, and a verdict in the wrong checkout is one
   careless `rm` from gone. Passing the path in this worktree is what makes that
   a refusal instead of a silent pass. **This is a check and not a reminder on
   purpose:** the rule it enforces was told twice and failed a third time.
   Adopted by the human 2026-08-14; `decisions.md` holds the two gates that died
   writing nothing and the verdict left in the wrong tree.

   Both pass → **verify the routings**: grep each target file for the exact
   line the gate quoted as appended — gates end each routed finding with that
   quote, and the runner greps the string, never a heading (a heading-level
   check false-negatived two present routings on 155-157). A declared routing is
   not a routing. Check the verify gate's
   `Drove:` list against `git diff --name-only`; a route the diff touches and the
   gate never fetched is an incomplete verdict, not a pass. **Run lint** — it costs
   nothing and catches the shape defects no per-issue gate can see. Then commit,
   staging **explicit paths only** — never `git add -A` or `.`. Glance at
   `git status` and investigate anything unexplained *before* committing.

   **Run `npm run build` at every commit step, not only at the finale.** The suite,
   the type checker and the linter together do not run the Next compiler, so none
   of them sees a module the compiler will empty. On run `402-251d11` an
   implementer added `export const MATCH_LINE_CAP = 200;` to a `"use server"` file,
   where Next allows only async function exports. The module then exported nothing
   and every route answered HTTP 500, including `/login` — on a tree where `npm
   test` reported 649 files and 7219 tests green, with `tsc --noEmit` and `eslint`
   both clean. Two gates caught it by driving the app; nothing mechanical did. The
   finale's own build on that run compiled in 4.9 seconds, so this costs seconds a
   commit. Adopted by the human 2026-08-24, walking that run's forks.

   **A build result is never read from log text. Every build writes its exit code,
   and the exit code is the record.**

   ```bash
   npm run build; echo "BUILD EXIT=$?"
   ```

   A brief that reports a build without one is incomplete, and that is what makes
   this refusable rather than a reminder. On run `bridge-cse` a build printed
   "Compiled successfully" and then exited 1 at "Collecting page data". The runner
   grepped the log, concluded a gate was wrong, and overruled it. The gate was
   right, and it cost issue 409 an attempt built to a wrong spec plus a criteria
   reset. Adopted by the human 2026-08-27 as B4.

   **Build in a copy, never in the tree a dev server is serving.** `rm -rf .next &&
   npm run build` deletes the directory the dev server answers from. On the same
   run the runner did that minutes before spawning two gates: every route then
   answered HTTP 500 on sound code, and the browser console held a stale error
   naming a line that no longer existed. A gate that trusted the console would have
   rejected an issue for a bug already fixed. Copy with `cp -al`, measured at 14
   seconds on that tree, and build there. Do not reach for the rsync recipe above
   for a build — Turbopack panics on its `node_modules` symlink. That recipe stays
   correct for tests and for mutation drills. Adopted by the human 2026-08-24, the
   other half of the same walk.

   **Each pass is pinned to the commit it reports on, and runs in the background.** The
   checker takes `--at <sha>`, and at that sha no verdict it prints depends on anything
   outside the commit. So the pass does not have to run serial with the implementers any
   more, and R2's measured cost goes to nearly nothing: run `e047ba` paid about 5h50m on an
   8h30m estimate for ten serial passes.

   At every commit, fire the pass and move on:

   ```
   git diff --name-only <previous commit>..HEAD
   node scripts/check-issue-citations.mjs --at <the commit just made> --quiet \
     <each issue file citing one of those changed files> \
     > .scratch/<feature>/citation-deltas/<sha>.txt 2>&1
   ```

   **Pin to the commit just made, never to branch head.** R2 needs each row to name the commit
   that moved the citation, and a pass pinned to a later head cannot name one.

   **Name only issue files that commit carries.** The pass refuses with exit 5 and names the
   path when it is handed one the pinned tree does not hold — an issue file the run minted or
   renamed after the commit is the ordinary way that happens. Filter the list against
   `git ls-tree -r --name-only <the commit just made> -- .scratch`, or run that file unpinned.
   The refusal is deliberate: a skipped file leaves no row, and a pass with no rows prints a
   clean summary.

   **`--all` stays banned here**, for the reason ruled on 2026-08-26: a commit can only break a
   citation into a file that commit changed, so reading all 592 issue files buys nothing and
   costs the whole corpus. Pinning makes a wide pass cheap in wall clock, not free in machine
   time.

   **The baseline pass pins too.** The runner commits its pre-flight state and pins the
   baseline to that commit. It does not stash and it does not read the working tree, because
   issue files carry uncommitted edits at pre-flight and a working-tree baseline compares the
   run against something no commit holds.

   **Passes queue in commit order and run one at a time. None is ever dropped.** Dropping one
   loses the attribution R2 was bought for. A pass is roughly 40 minutes against an issue of 30
   to 90, so the queue mostly keeps up.

   **One file per sha, in `.scratch/<feature>/citation-deltas/<sha>.txt`.** The last line of a
   finished pass reads `=== CITATION PASS COMPLETE === exit=<n> pinned=<sha>`. A file without
   that line is a killed pass, not a clean one: a session host can exit and take every session
   with it, so the file on disk is the only record.

   **The finale collects every file, checks each one for that terminator line, and names in
   the merge briefing every sha whose file is missing or unterminated. It re-runs nothing.** A
   run that reports a clean sweep over a pass that never returned is reporting on nothing, and
   this listing is what stops that: a directory listing and a `tail -1` per file, seconds of
   work. On run `batch-170a59` four of six commits had no pass at all and the finale was the
   only thing that noticed.

   **The catch-up pass at branch head is removed, ruled by the human 2026-09-06.** It is the same
   argument that removed the differential on 2026-08-28: nothing in a run acts on the finding,
   because a run may not write an issue file and the repair goes through `/harden-issues` by
   hand. Measured at full scope on that same run: 268 files, about 17,200 citations, 70 minutes
   at 4 per cent CPU duty, and about three hours from finishing when it was stopped. The
   collection and the report stay; only the re-run goes.

   **File each new `moved` or `gone` as a register row naming the citation and the commit that
   moved it**, exactly as before. The row is the whole remedy, and the run repairs nothing: a
   run may not edit the specification it is graded against, so the repair belongs to the next
   `/harden-issues` pass over that issue, which already reads the file and is already allowed
   to write it (the human, 2026-08-15). The checker holds the same rule in its own code and never
   writes an issue file.

   **The register is swept at every issue's commit too, and for the same reason.**
   Re-read every register row filed against the issue that just committed, and close
   what the commit closed. Until now the sweep happened once, at the finale.

   **The measurement.** The finale of run `416-419-421-d167e0` swept 112 rows and
   moved 16 to `verified`. **Nine of those sixteen were flagged by nobody** and still
   read `open`, so promotion would have minted nine issue files for work that had
   already shipped inside the commit the gate was reading. Three of the seventeen
   issues minted on 2026-08-09 carried the same defect, so the finale sweep alone has
   not fixed it. Run `99b-99e-6e11ba` caught two more the same way.

   A row the commit closed reads `verified`. A row it did not stays `open` and travels
   to promotion untouched. Adopted by the human 2026-08-27 as F6, because it moves work
   earlier rather than adding it.

   The exit codes a collector reads: 0 clean, 1 a fault, 2 no issue file matched, 3 not a git
   repository, 4 the unchecked-majority refusal, 5 `--at` could not be honoured, 6 named paths
   went ungraded. Codes 4, 5 and 6 are refusals to answer, not answers, and all three outrank 1.

   **Exit 6 was added 2026-09-02 with issue 503.** Positional paths were given and the pass
   graded none of them, so there is no summary line to read. Two roads reach it: `--touches`
   passed together with paths, and a path the unpinned pass cannot read. Both answered exit 0
   on a run that had graded nothing until then, which is why it is a sixth code and not a
   second meaning on one of the five.

   (Adopted by the human 2026-08-18 as R2, from the `cab74e` finale; `decisions.md`
   holds that run's citation counts and the drift mechanism behind them. It trades
   run time for record accuracy, which is a price only the human may set, and they set
   it.)

   **The runner commits. An implementer never commits its own work**, and the
   runner says so in every spawn. A self-commit does no visible harm, and that is
   the trap: it silently changes what "the diff" means to a gate already reading
   it, so the runner must hand those gates an explicit commit range instead of
   the working tree. Where an implementer has committed anyway, do not revert
   it — record it and give the gates the range (209-215: decisions.md).
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
   say-so states a conclusion where it owes a measurement: the 395-397 run closed
   claiming every item was verified, and a third of `rg394-02` had not landed.
   Nothing shipped wrong; the closing claim did. (Adopted by the human 2026-08-23 as
   R1.)

   **A standards-shaped split is a correction, not a retry, on one condition:
   every gate grades the behaviour correct AND the owed work is enumerated.** The
   shape is a verdict that splits on how the work is written down rather than on
   what it does — a missing pin, an unrun mutation, a claim that outruns its
   evidence. Where the behaviour is agreed and the list is closed, buying a fresh
   implementer to re-do correct work is waste, and the strike it charges is a
   strike against a spec fault. If either half fails — any gate doubts the
   behaviour, or the owed work cannot be enumerated — it is a retry and a strike,
   as before. (Adopted by the human 2026-08-07 with that condition attached, from the
   238-245 finale.)

   **A rejection on non-executable PROSE is fixed by deleting the claim, never
   restating it.** A fix for an over-claim is itself a new claim with its own
   falsifiable surface, so on this class more precise and more likely wrong
   move together. Second rejection → delete down to the minimal sentence the
   gate cannot falsify; re-assert only by making the claim executable. Before
   pricing any fix, read the strike record: two or more prior rejections in the
   class makes it delete-only and forbids sizing the fix in lines. One
   canonical statement per claim — everywhere else cites `file:line` and
   asserts nothing. The same rule governs post-block resolution rounds.

   **Where EVERY owed item is prose and the remedy is deletion, the runner
   deletes and commits. No implementer spawns, and there is no correction
   round.** The round exists to buy a writer. Buying one to delete four comment
   lines is the waste, not the deletion.

   Four conditions, all of them, and any miss puts it back to a correction round:
   every gate grades the behaviour correct; every owed item is non-executable
   prose; the delete-only rule above already governs the class; and the runner
   can verify each deletion by grep, from its own context, without reading the
   diff into a new one. The runner records the deletions in the ledger row as
   `prose: deleted` and names each site. It is not a strike, and it is not
   a correction round either — the row goes straight to `done`.

   **The saving is measured. Run `bridge-cse`, 2026-08-24, paid for two of
   these.** Issue 409's attempt-3 rejection enumerated four comment deletions,
   and issue 338's attempt-2 rejection named two prose sites. Both gates passed
   the behaviour in both cases. Each bought a fresh implementer, and in both the
   journal records that the runner verified the result by grep rather than by
   reading it — so the spawn produced a deletion the runner then re-did the work
   of checking. About 30 to 40 minutes across the two.

   **The human approved this on 2026-08-24 as "the gate files a register row and the
   commit lands". It is built as a deletion instead, and the reason is a hole in
   the row road.** A false sentence in a code comment is `audience: agent`, and
   `~/.claude/agents/promotion.md:34-36` refuses `audience: agent` at any
   severity. Filed as a row, the false sentence would ship, be refused at
   promotion, and stay. The deletion road takes the same spawn out of the run and
   leaves nothing false behind. Where the four conditions do not hold, nothing
   changes and the correction round runs as before.

   **A negative conclusion drawn from a grep does not travel without its scope,
   in the same sentence.** "There is no X" from a single-line grep is a statement
   about that pattern in those paths, not about the codebase, and it must say so
   where it is asserted rather than in a paragraph nearby. It was advice here
   first, and `decisions.md` holds the night that advice was broken. Adopted as
   admissibility by the human 2026-08-14 — a scopeless negative is not
   passed onward, by a gate, a finale or a runner, and a reader who receives one
   sends it back rather than acting on it.

   **When a round deletes a claim, search the branch for a twin before the round
   closes.** One grep for a distinctive phrase from the deleted sentence. A claim
   worth writing once tends to get written twice, and no gate reads two issues,
   so the second copy ships unread. The search costs seconds and costs nothing
   when it finds nothing. (Adopted by the human 2026-08-11, narrowly; `decisions.md`
   holds the run that earned it and the reason no authoring-time rule came with
   it.)

   **Three rules on what a claim may SAY. They bind every artefact an agent
   writes — issue files, the primer, migration headers, the briefing — not
   only a rejection fix.** (207-185 and 209-215: decisions.md.)

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
   lose a strike to it. Repetition is cheaper than ambiguity
   (209-215: decisions.md).
6. Ledger `done`; set the issue's `Status:` to `done — on branch <branch>,
   unmerged` (gate history goes in the body — `all` runs parse that line).
7. A gate rejects → re-spawn the implementer with the written reasons. If **both**
   reject, that is still ONE retry carrying both verdicts, and one strike, not two.
   Then re-run step 3 in full: verify in the background, review in the foreground
   on the next turn, both on the new diff. A gate that passed the previous
   attempt has not seen this one.

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
   Three runner errors in one run shared this shape (208-202 run: decisions.md).
   Ledger actuals derive from commit times, full stop.

   **The finale checks that, rather than trusting it.** Read each issue's commit
   time with `git log -1 --format=%ad <commit>` and compare it against the stamp
   the ledger carries, and report every gap in the briefing.

   **That comparison is necessary and not sufficient, and `check_commit_order.py`
   is the sufficient one.** The ledger stamp and the git date agree whenever the
   runner is working normally, because the runner writes one from the other — so
   this check passes on a commit stamped BEFORE the correction round whose items
   it is supposed to contain. Run `batch-34455f` carried two such rows, 413b and
   413, and both read as healthy here. The finale runs
   `check_commit_order.py --ledger <run.md> --repo .` in step 1 of `finale.md`,
   which compares the git date against the round's close time instead. (Adopted
   by the human 2026-08-25, as candidate rule b of that run's briefing.)

   **Run it at every commit step too, not only at the finale.** Same command,
   seconds of Bash, right after the ledger row's `committed <sha>` stamp is
   written. A drifted stamp then fails while the runner still has the round in
   context and fixes the row on the spot, instead of a hand-repair 17 hours later
   at the finale — the same move F6 made for the register sweep. The finale run
   stays as the backstop. (Adopted by the human 2026-08-29, closing the F5 question
   on ticket 33: the "derive from commit times" sentence has been broken twice
   since it was written, by 68 and 95 minutes, and a sentence nothing checks at
   write time is the remember class.) This sentence has
   stood since the 208-202 run and the 399-403 run broke it anyway: the ledger
   stamps issue 399's commit at 09:38 against a git author date of 08:03, and the
   gap across that run reaches 95 minutes. Every per-issue duration in a run's
   records comes from the ledger, and `orchestrator_cost.py` readings inherit the
   error. (Adopted by the human 2026-08-23 as rule 9, after the rule alone had already
   failed once.)

   **When the gates split:** a factual split is settled by the runner driving
   it — a tenancy claim by deleting the predicate (or planting the cross-tenant
   row) and running the suite, cache-cleared, never by reading the code
   (154-181, twice: decisions.md). A severity or standards split takes the
   stricter verdict.
8. **Two strikes → re-check the criteria before buying a third implementer.**
   Spawn `harden-issues-attacker` in strike-2 mode with both verdicts: classes 1,
   5 and 9 only, evidence or silence, and no waiting. One of three outcomes:

   - **A fault in the criteria, with a citation** → it corrects the issue file and
     says what changed. Re-spawn `run-issues-implementer` with the corrected
     issue. **Not a strike** — the earlier attempts were graded against a spec
     that no longer exists.
   - **Criteria confirmed sound** → spawn `run-issues-implementer-escalated` with
     the issue and both verdicts, but none of the failed reasoning.
   - **A fork it cannot settle from evidence** → route it by
     `~/.claude/questionrules.md`'s table. A reversible fork — wording, fixture
     shape, reversible criteria scope or product behaviour — takes its
     recommended default: the runner writes it into the issue file as a default,
     queues it, and the corrected issue buys the next attempt, under the same
     two-reset cap. A fork in the table's four `[irreversible]` classes, or a
     split, → ledger `blocked (criteria)`, the question goes to the merge
     briefing, and the run moves to step 9. **It never waits for an answer.** A
     question mid-run is a default taken or a blocked issue, never a stall.
     (Ruled by the human 2026-08-29, the second ticket 33 walk.)

   **Two criteria-fault resets maximum per issue.** After the second, the
   criteria are frozen for the run; the next strike-2 buys one escalated
   attempt, then `blocked`. Rejection CLASSES are counted across resets —
   strikes reset, the class ledger does not. Without the cap, lawful resets
   compound past what this skill promises (154-181: decisions.md).
   **This paragraph states the intent; the pre-spawn
   check in step 1 is what enforces it.**

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
   prior rejections a line count is fiction ("two prose lines" became four
   sites in three files and an evening — decisions.md). It states the
   strike-class record beside any size claim, and the briefing presents both
   roads side by side — merge-now-fix-later and fix-first — each with what it
   costs and what it risks. The judgement is the human's; the sizing is not.

**One issue, one implementer spawn. Always.** Small-issue coalescing was retired
by the human on 2026-08-15; `decisions.md` holds the measurement. Do not reinvent it,
and do not report on it in the merge briefing.

## Nothing finishes vaguely

An issue leaves the ledger as `done` or `blocked`. Never "done, mostly". Anything
unfinished goes into its one named home before the ledger moves, and the merge
briefing lists every such entry:

- Acceptance unmet → stays `blocked`.
- Waiting on the user (secret, env var, OAuth client) → the project's
  pending-actions file, if it has one, as a numbered action, with one line of
  what is blocked on it. Code may
  still complete around it. `/daily-brief` surfaces it; the run never waits.
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
specified once, in `parallel-hunt/SKILL.md`, and a run uses them unchanged — one
register per feature, generated from a shard per writing worktree. Every writer
appends to its own shard inside its own tree; `collect_shards.py --my-shard`
names it, and a write to `register.md` itself is refused. Two registers for one
product rebuilds the problem this closes.

**A ruling that creates work gets its issue number in the same sitting as the
ruling, from `python3 ~/.claude/skills/lib/claim_number.py issue <dir> --for <who>`.** A ruling is a decision, not a finding, so this stays a direct issue file
and does not go through the register — the same reason `/to-issues` is untouched by
any of this. Not "that becomes its own issue" — the number, or the file and line
where the work now lives. A ruling with no artefact cannot be told apart from a
ruling nobody made, and nothing is watching for one: `decisions.md` holds the
split that survived nine hours as a phrase inside another issue's file
(209-215: decisions.md).

## Resolving a blocked issue

Resolution happens after the run closes, and it is a procedure, not an evening
of improvisation. The human's answer is one word — `merge`, `fix` or `drop`. `fix`
spawns ONE implementer, under the delete-only prose rule where it applies, then
ONE narrow gate round maximum, unattended; anything more becomes a register row.
The human supervises nothing — they answer, and the machine reports back in the next
brief.

## Branch and human gate

The runner owns the feature branch; **main belongs to the human.** The worktree has
**one writer** — the current implementer, plus the runner committing. Anything
spawned beside the per-issue loop works in the scratchpad, never the run's tree.

Commit per issue after gates pass. **No merge between issues.** Merge to main is
the human's decision, taken once at run end: the run stops at `awaiting-merge`, and
`/daily-brief` carries the merge read to them and executes their answer. A
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
the handwritten `heartbeat <HH:MM>` field it replaced could be, and was
(decisions.md). A long implement
attempt moves no status line for an hour, so "no progress" cannot mean "dead" —
only a stale mtime can.

**The owner line is cleared the moment the run stops owning the tree.** Reaching
`awaiting-merge`, or halting, rewrites it to `Owner: none — <awaiting-merge|HALTED>
<date> <HH:MM>`.

Create the wakeup anyway at launch (every ~29 min): "Check `grep -m1 '^Owner:'
<run.md>` and `stat -f %m <run.md>` — do not read the rest of the file. If the
owner line names a session and the file's mtime is over 60 minutes old, resume
from ledger state; otherwise do nothing. The finale is a resumable stage —
revive it, never re-run completed halves." Delete it at run end. Remind once that the machine must stay awake
(`caffeinate -dimsu`).

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
procedure is a script and not a judgement. Resume keys on the current directory
(ticket 38, the one-run-per-feature layout ticket, ruling 11); `resume.md` says how.

## Pre-flight

- **The session that types `/run-issues` is launched with the three directories
  every worker reads outside the worktree.** CLI 2.1.257 added a one-time
  permission prompt in auto mode before the first file read outside the working
  directory. Every worker in this run reads outside its worktree as a matter of
  course, so an unattended one meets that prompt and the run halts where nobody
  is watching. The launch command names all three:

  ```
  claude --add-dir ~/.claude/skills ~/.claude/agents <the project's memory directory, if it has one>
  ```

  The skills directory holds the guard scripts every role shells out to and the
  briefs it reads beside them; the agents directory holds the agent files; the
  memory directory holds this project's memory, including the pending list the
  daily brief writes. (Ruled by the human 2026-09-06, overturning the default of
  changing nothing.)
- **The launch line is a gate, not an announcement. Nothing spawns before it
  prints.** One line on every invocation — issues in order, branch, the resolved
  session model, **the resolved session effort**, and what will NOT happen (no
  merge, no prod). The effort belongs here for the reason the model does: this
  line is where a wrong setting gets caught, one keystroke before spawn 1, and it
  is the only place both are read aloud while they can still be changed. Write
  both into `run.md`'s header in the same breath. It is still not a
  wait: it prints and the run carries on at once, so the gate costs nothing. What
  it buys is that the interrupt window exists at all. (Adopted by the human
  2026-08-07; `decisions.md` holds the run whose line printed too late to
  interrupt, and the older 11.5-hour misread halt.)
- **The ceiling and the issue range are refused at the prompt, not checked
  here.** `~/.claude/hooks/machine-preflight.py` refuses a third `/run-issues`
  while two runs are live, any `/run-issues` whose typed issue range overlaps a
  live ledger, `all` beside any live run, and a scope token the grammar cannot
  read (ticket 38, the one-run-per-feature layout ticket, rulings 20 and 21). It
  counts live runs the way `find_live_ledger.py --list` does, and it has no
  override word. Then mint the batch id and create
  `.scratch/<feature>/runs/<batch-id>/`.
- **Seed this run's QA workspace; the script writes its two lines into the ledger
  header.** Inside the run's worktree, once the batch id and `run.md` exist:

  ```
  node --env-file=<env file> scripts/seed-run-workspace.mjs --batch <batch-id> --ledger <run.md>
  ```

  It creates one auth user, one `workspaces` row named `run-workspace <batch-id>`
  and one `admin` membership, idempotently, behind `scripts/lib/db-target.mjs`, and
  writes `QA workspace:` and `Sign-in user:` into that `run.md`. The round header
  copies those two lines. Two runs at once then write disjoint rows, which is the
  collision no diff shows (ticket 38, the one-run-per-feature layout ticket, sitting 2, ruling 3: one workspace row per
  run). **Every fixture script in `scripts/` run inside the run's worktree reads
  that `QA workspace:` id off `run.md` itself**, through `seedWorkspaceId` in
  `scripts/lib/run-workspace.mjs`, and refuses a `SEED_WORKSPACE_ID` naming any
  other workspace (sitting 5), so an implementer sets nothing and its gate reads
  the run's rows. The finale deletes the workspace by that id; the
  daily brief sweeps what a merged or long-halted run left (ruling 12: the finale
  deletes its own workspace, the brief sweeps abandoned ones).
- **Run the citation check over the batch's own issue files, and name the broken
  ones in the launch line.** `node scripts/check-issue-citations.mjs --quiet
  <file>` per issue in scope — about ten seconds a file, no `node_modules`
  needed, batch files only, never `--all`. Report, never repair: a run may not
  write an issue file, so the repair still belongs to a hardening pass; what this
  buys is that a stale spec is visible in the interrupt window instead of met
  mid-run by an implementer as a wrong premise.

  **A zero from that check is a fact about the FILE, not about the instrument.**
  Report it as "this file carries no parsed citations at this moment" and never
  as "the checker does not recognise the form these files use". The two readings
  are not equivalent: a claim about the tool tells every later pass the
  instrument is blind, so nobody runs it again. Measured on run
  `481-482-2d0f77`: the pre-flight got `0 citations in 1 file(s)` on both issue
  files at 18:16 and the journal concluded the checker was blind. The finale ran
  the same checker on the same two files and got **106 citations, 83 holding**.
  Nothing about the checker had changed; the implementers had appended their
  records in between, and the pre-flight had measured the files before those
  existed. (Adopted by the human 2026-08-30 in the daily brief. The defect class of
  the 347/263 run was citations, which is what a suppressed re-check costs.) (Adopted by the human 2026-08-29 on
  ticket 33's audit: 28 of the 49 `ready-for-agent` files carried 169 broken
  citations that day, and nothing re-checked any of them between the stamp and
  the spawn.)
- **Re-derive every fact the run will carry into its spawns, from source, and
  name the source beside it.** Carry-forward entries, batch-plan sentences,
  anything a previous session wrote down — none of it is evidence. Read the
  function, run the query, open the migration. A carried misreading and the truth
  it replaced can fail in opposite directions — one predicts a loud break, the
  other a silent misfile — so the error stays invisible while it does damage. One
  read of the source at pre-flight catches it; `decisions.md` holds the nine-hour
  instance (209-215).
- **Every spawn carries its own role's model, read off the ledger.** This bullet
  said the opposite until 2026-09-05: never pass a `model:` value on a spawn for
  any role that has an agent file. That was right while all twelve loop briefs
  said `model: inherit` and nothing could name a model per role — a spawn-time
  value could then only defeat the file by accident. The launch line now resolves
  a model map, so the rule reverses.

  Read `Model map at launch:` in `run.md`, take this role's value, and pass it in
  the Agent call's `model` field. Every spawn, every role, every attempt.

  **The twelve agent files still say `model: inherit`.** A spawn by hand in an
  ordinary sitting therefore behaves exactly as it always did: no live ledger, no
  map, no change.

  **A map that cannot be forgotten needs a refusal, and this pack does not ship
  one.** Two `PreToolUse` and `SubagentStop` hooks do that job in the author's
  own setup — one refuses a spawn whose `model` field does not match the ledger
  and names the value to reissue, the other opens each subagent's transcript
  after it concludes and journals what actually ran. Neither ships here, because
  neither can be made true of a reader's machine by scrubbing alone. Without
  them the map is a rule the runner has to hold, which is weaker; read
  `hooks/README.md` for what a reader gains by writing their own.

  **The finale reads those lines, and `run_quality.py` is what reads them.** One
  `**MISMATCH**` anywhere in the journal marks this run's trial VOID in the merge
  briefing, beside the per-role table and the three per-issue quality figures.
  `finale.md` step 4 carries the command. A void trial halts nothing and unmerges
  nothing: it says only that this run may not be compared against another to read
  a model choice.

  **A journal with no landed line reads `not measured`, which is not a pass.**

  **One spawn falls outside all of this, and it is the one with no agent file.**
  The finale's board render is not one of the twelve roles, so the map does not
  name it. `finale.md` step 5 requires `model: "opus"` named explicitly on that
  Agent call — an unnamed spawn there inherits whatever the session runs, to
  convert a 283 KB markdown file into HTML, measured 2026-08-06. **The pin is
  `opus`: the top reasoning tier below the most expensive one**, and it was
  `haiku`, then `fable`, before that. The render cost 0.30M weighted
  tokens against a run's 149.70M, so the saving is not what decides it, and the
  tier order in this pack ranks review authority and never price. `finale.md`
  step 5 carries the rest of that reasoning. Read the two together: this bullet
  governs the twelve briefed roles, which take their model from the ledger;
  `finale.md` governs the one spawn that has no brief and no map row. (Scoped by
  the human on 2026-08-22, answering C7 of the skills audit. The alternative —
  minting an agent file for the board renderer — was refused, because it adds a
  file to fix a wording problem.)
- **Record the session model in the ledger's owner line and in the merge
  briefing.** Every tier this pipeline has evidence for was earned at Opus 5
  (decisions.md). A run on any other tier is still a valid run, and it is also
  the first evidence at that tier — so whoever reads its verdicts later has to
  know which tier produced them. Say it once, where the verdicts live.
- **Orchestrator cost, stated at launch.** Run
  `python3 ~/.claude/skills/run-issues/orchestrator_cost.py --days 7 --issues <count>`
  and paste its table into the launch message. It reads the last week's run transcripts
  and prints what the orchestrator cost at each batch size already run.

  **This states a fact. It refuses nothing, and it recommends no size.** the human ruled on
  2026-08-21 that there is no ceiling on how many issues a run may take, and that the
  reading must come from inside the last week: they change the workflow daily, so an older
  figure describes a system that no longer exists. If the window is empty the script says
  so and prints nothing else. Do not go looking for an older number.

  **`--days` is the launch reading and `--batch <id>` is the finale's.** The window
  answers "what have other runs cost at this size", which is a question you ask before
  you pick a list. `--batch` measures ONE run or hunt, per model and per role, and the
  finale takes it through `run_costs.py` (ticket 39 of the pilot-delivery map,
  every-worker-inherits-the-session-model, ruling 12). Do not read the window as this
  run's cost: until 2026-09-06 `run_costs.py` did exactly that, and the row it appended
  borrowed another run's issue count, agent count and orchestrator share.

  **The weekly table now carries a `models` column.** A run that mixed models has no
  single weighted figure, so the table names the tiers that answered and refuses to add
  them (ruling 11).

  What the five runs to 2026-08-20 measured, and why the column matters: the orchestrator
  is the single session that holds the whole run, and every turn re-reads the conversation
  before it. Four issues cost it 0.96M weighted tokens per issue, nine cost 1.44M to
  1.67M, and thirteen cost 2.45M. Nothing else in the audit moved a number this far.

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
- **Criteria gate — REFUSE an issue whose file gives a gate nothing to grade.**

  ```
  python3 ~/.claude/skills/run-issues/check_issue_ready.py \
      --issue <path> [--issue <path> ...] [--override <id> ...]
  ```

  Exit 1 blocks the launch. An issue passes on a `## Acceptance criteria`
  section; a `## Must still be true` section alone passes and says so; neither
  refuses. The human clears one by naming its id in an `--override`, and the script
  then prints what the override costs. Never pass `--override` without their word,
  and never for a whole batch.

  **This is a different thing from the `Hardened:` stamp above, and it does not
  touch their 2026-08-21 ruling that an explicitly named issue always runs.** The
  stamp asks whether a hardening pass has read the file. This asks whether the
  file contains criteria at all — and where it does not, the runner writes them
  into the spawn prompt and the run then grades its own invention.

  **Measured before it was built, on 2026-08-24: of the 32 issue files reading
  `Status: ready-for-agent`, exactly ONE carries neither section.** This does not
  stand between the runner and a hardened backlog. It stands between the runner
  and a freshly promoted register row, which is the class that hurt on run
  `bridge-cse`: 408 and 407 were both that shape, the runner authored their
  criteria, two citations in that brief were wrong, and they reached a shipped
  code comment. (Approved by the human 2026-08-24, override per issue, cost printed.)
- **Concurrency gate — REFUSE to start while an unmerged hardening branch holds
  an issue in this batch.**

  ```
  python3 ~/.claude/skills/run-issues/check_harden_branch.py \
      --issue <id> [--issue <id> ...] [--repo <path>] [--base main]
  ```

  Exit 1 blocks the launch. The remedy is to merge that branch and re-read the
  issue files, which costs a fast-forward: those branches touch `.scratch/` only.

  **Run `bridge-cse`, 2026-08-24, is the instance.** It built 408, 407, 409 and
  338 from unhardened files while a peer `/harden-issues` session held hardened
  copies of all four on `claude/harden-issues-407-408-ce713b`. That session even
  messaged the run mid-issue with five findings, all of which held. Its branch
  merged at 23:12, about ten hours after the run finished the same four files
  without it. The hardening existed, on disk, before the run started. Nothing
  read it, because nothing looked. (Approved by the human 2026-08-24.)
- **Permission floor — REFUSE to start when the run's own commands are not in
  the TRACKED allow list.** Run it INSIDE the run's worktree, after the worktree
  exists and before the first issue spawns.

  ```
  python3 ~/.claude/skills/run-issues/check_permission_floor.py --repo . \
      [--class "<any extra command this batch needs>" ...]
  ```

  Exit 1 blocks the launch. The remedy is the human's hands: an agent cannot write
  `.claude/settings.json`, because the auto-mode classifier refuses every write
  to it. Give them the exact lines the check prints and wait.

  **Run `414a-483-286335`, 2026-08-30, is the instance; `decisions.md` holds what
  it cost.** `Bash(npx vitest *)` sat in the MAIN checkout's untracked
  `.claude/settings.local.json` and not in the run worktree's copy. That file is
  gitignored (`.gitignore:31`), so a worktree freezes it on the day it was cut.

  **This does not dry-run anything, deliberately.** A class verified at launch
  is not a class verified for the run, because the dry run never consulted the
  thing that refuses. A
  tracked allow rule is checked BEFORE the classifier and git carries it into
  every worktree, so that is what this reads. (Built 2026-08-30 on the human's
  instruction, closing `rn99f-03`; `decisions.md` holds the replay.)
- **Creating the worktree includes installing dependencies and making the
  `.env.local` symlink. If either fails, the runner refuses to start.** Not a
  check to remember at pre-flight — part of what "the worktree is ready" means.
  It costs one shell command, a few lines of output and 30 to 60 seconds per
  worktree, and it saves more than that the first time it stops an agent
  diagnosing a false green caused by a missing environment file. (Adopted by
  the human 2026-08-07; `decisions.md` holds what they asked and the answer.)

  The failure it closes: a typecheck can exit 0 against a global install and
  never load the repo's types. **A green produced without dependencies on disk
  is a false green** (208-202 run: decisions.md).
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
    and commit, the QA migration script.
  - **Verify gate** — **starting the dev server**, by name, from the repo's
    `.claude/launch.json`. On this repo that is `spine-dev-qa-auto`, whose entry
    carries `autoPort: true`: **the port exists only in the `preview_start` result
    of the spawn that started the server.** Two runs start the same entry at once
    and the second takes the next free port, so a number carried in a brief is the
    other run's server (ticket 38, the one-run-per-feature layout ticket, sitting 2). No refusal catches a wrong port yet;
    the header field `Dev server:` and this fact are what there is. **The gate
    drives that server at `<batch-id>.localhost:<port>`, never bare `localhost`**:
    a browser cookie is scoped to the host and not the port, so two runs on
    `localhost` share one session (measured in the sitting 2 rehearsal), and
    `dev-signin-link.mjs --batch` refuses any other host. A verify gate cannot
    drive an acceptance path without the server. **It probes that
    server through the repo's probe script, never with a bare `curl`.** On this
    repo that is `node scripts/http-probe.mjs "<label>" <url>`, allowed by one
    prefix rule. A raw `curl` gets allowed as an exact string, so the next probe
    with a different port, path or label prompts again — which is how run
    `cab74e` stopped for a permission dialog at the end, unattended. The script
    refuses any target that is not this machine, which is what makes one
    standing permission safe to grant.
  - **The runner itself** — `CronCreate`, for the resume wakeup, on any run that
    could meet a usage limit.

  **The dev server is named here because leaving it off cost six hours.** The
  bullet it replaced ran correctly and still lost them: a runner dry-ran every
  class the old text named, because it read an illustrative list as a complete
  one. That is the fault the derive-from-roles rule closes, and it is why the
  list above is a floor rather than a definition (`decisions.md`).
- **An unattended run may delete only rows it marked as its own, and the scope of
  the delete is that marker.** Where a run needs to clean up after itself, it
  stamps a run-owned marker column on every row it writes and deletes on that
  marker alone. It never widens its database permission to cover deletes in
  general, and it never deletes a row on an argument that it must have written it.
  A permission granted once is held for every later run, including the one that
  reasons badly at 3am; a marker column is scoped to the rows and expires with
  them. (Adopted by the human 2026-08-07, from the 238-245 finale.)
- **Probe QA health, read-only** — the fixture state the batch will drive:
  per-workspace counter rows, row counts on the tables the issues touch, a
  can-mint sanity check. Results go into Carry-forward as the known-good path.
  Fixture viability is run state like any quota; discovering it mid-drive is
  paid at gate prices (155-157: decisions.md).
- The worktree's `.env.local` is a **symlink** to the canonical env file (path in
  the repo CLAUDE.md), never a copy. Replace any copy. Env files are never
  committed.
- **Vercel-CLI trap:** `vercel link` / `vercel pull` write *through* the symlink
  into the canonical env file. Remove the symlink, run the command, delete the
  `.env.local` it wrote, restore the link. Never edit the canonical file to clean
  up after Vercel.

Every agent file opens with its own idempotency check, so a re-spawn after a
resume stops on its own if its stage is already past. A gate also writes
`verify: pass|reject` or `review: …` into its ledger row on return, so a
resume on a `gates` row re-spawns only the gate with no entry. The ENTRY is what
the resume reads; it carries no time, per the rule above.

## Mid-run directives

A directive arriving mid-run is **this run only** unless the user says it is
standing. Record it in Carry-forward with its scope written on it and re-brief it
from there. Do not write it to a memory file in-session — the test is whether it
would still be true if this run had never happened. At run close, route "should
this become standing?" to the finale's `## Decide` heading, and from there into
the run's own queue shard, where `/daily-brief` collects it — a chat question
at session end dies with the session. It goes under `## Decide` rather than
`## Ruled` because nobody has answered it. Write it in the form
`~/.claude/questionrules.md` sets.
