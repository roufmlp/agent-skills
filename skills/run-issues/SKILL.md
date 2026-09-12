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
not to run one. **This file holds rules. The reason and the measurement behind a
rule live in `decisions.md` or in the docstring of the script that enforces it,
and a line ceiling in `test_skill_structure.py` refuses a commit that grows this
file back** (ticket 36 of the pilot-delivery map, rulings 9 and 14).

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
runs, so pass `false` when the next action depends on the result. The verify gate
is the one exception, because the review gate CAN run while it does: spawn verify
in the background, then review in the foreground on the next turn, and the two
overlap by construction.

**The field is enforced, not remembered.** A `PreToolUse` hook,
`~/.claude/hooks/run-issues-foreground-gate.py`, refuses a `run-issues-verify-gate`
spawn whose `run_in_background` is not exactly `true` and any other `run-issues-*`
spawn whose value is not exactly `false`, and its message says how to reissue. Its
docstring holds the two measurements behind the shape: the stall claim against
background spawns, refuted the day after it was made, and the run that never once
spawned both gates in one message.

**The cron stays, at its usage-limit interval.** It rescued one run exactly once,
from a spawn the runner announced and never made; `run_in_background: false`
cannot prevent a call that was never made, so shortening the interval buys nothing.

**This is also what row 23 guards.** A runner that does not block can mark an
issue done before the work lands. `skills/lib/check_verdict.py` refuses on a gate
that returned no verdict, and that refusal is load-bearing today.

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
because the model looks strong enough.** Promotion is the only role in this table
that passes that test. `xhigh` in place of `max` on the finale stays refused: it
runs once per run, so the saving is one spawn and what it buys is a cheaper last
look before a merge.

No value in the effort column was measured against a lower one. What the last
column states is what a wrong answer costs, because that is the evidence a
downgrade has to beat.

Spawn prompts carry **only** what varies — issue ID, paths, rejection reasons.
Everything stable already lives in the agent file, where it caches.

## Run state — files, not contexts

In the main checkout, under `.scratch/<feature>/runs/<batch-id>/`. **One directory
per run, keyed by the batch id**, so two runs on one feature never share a file
(ticket 38 of the pilot-delivery map, the one-run-per-feature layout ticket, ruling
10). The batch id is minted at launch: `batch-` plus six hex characters
(`openssl rand -hex 3`), and it is the same id the branch carries after
`claude/run-issues-`, the register prefix `rn-<id>-NN`, and every journal line.
Create the directory before spawn 1. The fixed names `.scratch/<feature>/run.md`,
`primer.md`, `merge-briefing.md` and `run-journal.md` are retired:
`find_live_ledger.py` does not read them, and
`~/.claude/hooks/run-state-path-guard.py` refuses a write to them with the right
path in its message, so a slip costs one reissued call and never a halt.

- **`run.md`** — the ledger. Status table plus a **Carry-forward** section, plus
  the one live halt block if the run is halted. Nothing else. Every spawn reads
  it, so every line in it is billed a dozen times a run.

  **Its header carries the two settings a later measurement cannot recover:**
  `Session model at launch:` and `Session effort at launch:`, one line each,
  written before spawn 1. Both are required rather than remembered. **The reason
  is a void experiment**: the first trial of `medium` effort could not be read,
  because no file in the run said which tier produced it (`decisions.md`). A run
  that does not stamp its own settings cannot be used as evidence about them.

  **Measure both, never guess them.** A guessed stamp is worse than a missing
  one: the next reader treats it as evidence. Both values are in the process's
  own command line. Run this before spawn 1 and copy what it prints:

  ```
  ps -o args= -p "$CLAUDE_PID" | tr ' ' '\n' | grep -A1 -E '^--(model|effort)$'
  ```

  It returns the flags as pairs, for example `--effort` then `high`, by the road
  `machine-preflight.py` takes, so the hook and the ledger agree by construction.
  If `$CLAUDE_PID` is empty or a flag is absent, write `unmeasured` on that line
  and say so in the journal. Never write a value you did not read.

  **Two more header lines, written at launch BY `model_map.py`:** `Model map at
  launch:` and `Role effort at launch:`, a `role=value` list each, all fourteen
  loop roles named in both (ticket 39 of the pilot-delivery map,
  every-worker-inherits-the-session-model, rulings 4 and 7). Run this before spawn
  1 and paste what it prints:

  ```
  python3 ~/.claude/skills/run-issues/model_map.py "<everything after /run-issues>"
  ```

  Pass the command text exactly as it was typed, scope and all. **Exit 1 is a
  launch-time stop: spawn nothing, write no ledger, and hand the human the refusal.**
  It is the only stop this ticket has; once a run is live nothing in it ever
  halts. You should never see it, because `machine-preflight.py` refuses the same
  faults at prompt-submit time, before the batch id is minted.

  The map is typed after the issue list, behind the word `models:`, as in
  `/run-issues 512 513 models: implementer=opus gates=fable`. Its grammar — the
  keys, the values, the default file, the inverted-map refusal and why the
  effort line is recorded and never set — is in `model_map.py`'s docstring. All
  fourteen loop roles are named there; `workers` is the four roles that build
  and `gates` the eight that check. `inherit` never reaches a ledger: every role
  is resolved to a concrete name at launch, and the fourteen agent files stay
  `model: inherit`, so a spawn by hand is untouched. **Effort is recorded, never
  set**: the Agent tool has no effort field, so never pass one and never edit an
  agent file mid-run. **No adversarial gate runs below the tier of the worker it
  checks**, `haiku < sonnet < opus < fable`, and `model_map.py` refuses a map
  that inverts it.

  **Two more header lines, written at launch BY the seed script:** `QA workspace:`
  with the workspace id and `Sign-in user:` with the run user's email,
  `run-<batch-id>@example.test`. `scripts/seed-run-workspace.mjs --ledger <run.md>`
  writes them itself, so no uuid passes through a keyboard. Every verify gate signs
  in as that user, so `current_workspace()` scopes its reads to this run's rows;
  every fixture script run inside the worktree reads that id off `run.md`
  itself and refuses a `SEED_WORKSPACE_ID` naming any other; and the finale
  deletes by it (ticket 38, the layout ticket, sitting 2, rulings 3 and 12).

  **Eight more header lines, written before spawn 1. They are the RUN FACTS, and
  the ledger is the only place they are written** (ticket 40 of the pilot-delivery
  map, the runner's turn growth ticket, ruling Q9):

  ```
  Register:            <absolute path of this run's register shard directory>
  Run directory:       <absolute path of .scratch/<feature>/runs/<batch-id>/, and the synchronised copy at <worktree>/.scratch/<feature>/runs/<batch-id>/, which scripts/lib/run-workspace.mjs reads; an append to primer.md goes to BOTH>
  Merge briefing:      <absolute path>
  Browser harness:     <the tool name that PAINTS in this environment>
  Dev server:          <the launch.json entry by name, and the host every agent drives — never bare localhost>
  Sign-in link:        <the command that mints a link for the run user, with --batch and --site>
  Private copy recipe: <the rsync line, and the node_modules symlink that follows it>
  Full suite:          <the command, and that it runs WITHOUT the canonical env file sourced>
  ```

  With `QA workspace:` and `Sign-in user:` above, that is TEN header lines, and
  they are what a brief used to restate. **Every role a round spawns is sent to
  this header by its own agent file:** both implementers, the verify gate and
  both review gates. `~/.claude/hooks/run-issues-brief-cap.py` refuses a
  first-attempt implementer brief over 400 words, so a brief that restates them
  does not spawn. The number is a CEILING and not a cut; the hook's docstring
  holds the measurement.

  **It is pruned, not appended to.** Three things go in the journal instead, and
  the runner moves them the moment they appear: a **superseded halt block** (the
  new one replaces it — delete the old one, do not mark it), the **finale
  write-up** (the ledger carries the stage and the verdict, one line each; the
  reasoning is narrative), and any **verdict story** longer than its row.
  The prune runs at every halt-block write and every row moved to `done`. Two
  mechanical triggers, either one means prune before the next spawn: more than
  one `## HALT BLOCK` heading, or status table plus Carry-forward under half the
  file. A third while an issue is still fighting: before re-spawning gates on
  the same issue, a row over ~10 lines loses its verdict story to the journal,
  keeping stamps only — a growing row is re-billed to every one of its own gate
  spawns (decisions.md).
- **`run-journal.md`** — the narrative, append-only. Every log line goes here:
  what each attempt did, verdict stories, dead ends. Subagents never read it. It
  is read exactly twice — by a resuming runner, and by the finale.
- **`primer.md`** — the codebase primer. Fresh subagents read this instead of
  exploring. The first implementer creates it; every implementer appends what it
  learns. **A run reads only its own primer** — another run's directory is never
  read. It is written by implementers about implementer-written code, so it is
  orientation, never authority: what ought to be true lives in
  `docs/patterns.md`, on main, and outranks both the primer and the code.
- **`merge-briefing.md`** — the merge-read briefing, built as the run goes. It starts
  empty in the run's own directory. Gate verdicts get one summary line each; the
  full text lives in the issue files. Every command it hands a human carries `RAN`
  or `UNRUN` beside it, and `check_briefing_commands.py` refuses one that does not.
  A thirty-minute read or it has failed. **The narrative sections are filled as
  each issue closes, not at the finale**, while the runner still holds the facts.
  An empty section is not neutral: it reads as "nothing to report" (209-215:
  decisions.md).

Ledger statuses: `queued → in-progress → gates → done`, plus `correction`
(between `gates` and `done`, when taken) and `blocked`. Both gates run under the
one `gates` status. Only the runner writes the ledger. Gates write
verdicts into issue files. Everyone appends; nobody rewrites another's section.

**Do NOT stamp transitions with the time.** `run_timings.py` is the single source
for how long anything took, and it reads the transcript, which is written whether
anyone remembers or not. Hand-written clocks drifted by over an hour on past runs
(`decisions.md`; ruled by the human 2026-08-31).

**Two stamps survive, and they are the only two.** A correction round's row gains
`correction: open → closed HH:MM`, and the commit gains `committed <sha>`.
`check_commit_order.py` grades one against the other. **The close stamp comes
from `date`, never from your own count of the clock.** Run `date +%H:%M` and
paste what it prints.

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
runner.** Every live Zoho suite runs through the wrapper, which sets `ZOHO_LIVE=1`
itself, waits behind any other holder, and breaks a holder with no heartbeat for
thirty minutes with a journal line; the harness refuses a live context the wrapper
did not start. Pass the whole directory to ONE wrapper — a second wrapper of the
same batch waits behind the first, so never delete the lock file or export
`ZOHO_LIVE` by hand (ticket 38, the one-run-per-feature layout ticket, sitting 2,
rulings 4 and 13):

```
node --env-file=<env file> scripts/zoho-live-lock.mjs --batch <batch-id> --journal <run-journal.md> -- npx vitest run src/lib/zoho/live
```

## The round header — the four fields that vary, and nothing else

A **round** is the set of agents spawned for one issue: the implementer, then both
gates, then any retry. Before the first spawn of a round, fill this block. Paste it
verbatim into every brief in that round. A field you cannot fill stops the spawn —
you settle it, you do not leave it out.

```
Issue file:       <absolute path>
Verdict goes to:  <absolute path, and the heading the record goes under>
Private copy:     <absolute path carrying the issue id and the role>
Settlements:      <every settlement this round is working under, verbatim>
```

**The run facts are NOT here.** They are ten header lines of `run.md`, written
before spawn 1 (see Run state), and every role a round spawns is sent to that
header by its own agent file. A brief that restates them is refused by
`~/.claude/hooks/run-issues-brief-cap.py` at 400 words on a first attempt.

**Why a block and not a rule.** The rule that a brief names the place and not only
the act was adopted, restated as a check, and failed a third time anyway
(`decisions.md`). The block turns naming the place into a field you fill and
settlement parity into a structural fact: one text, one paste, every agent in the
round. Adopted by the human 2026-08-16.

## Per-issue loop

1. **Settle the road before spawning.** If the issue admits more than one
   plausible approach and no triage decision picks one, choose it now and put the
   choice — and the roads rejected — in the spawn prompt. Minutes here against
   hours later (112-116 run: decisions.md). Then spawn `run-issues-implementer`.

   **Every implementer spawn passes the cap first**, this one and the escalated
   third in step 8. It refuses the fourth attempt and the third criteria reset,
   and prints the counts it refused on:

   ```bash
   python3 ~/.claude/skills/run-issues/check_attempt_cap.py --ledger <run.md> --issue <id>
   ```

   A non-zero exit means the issue is `blocked`: ledger it and go to step 9.
   **Stamp `attempt <N>` into the issue's row before each spawn** — that marker
   is the only thing the cap counts, and a row still carrying the older
   `implement …` / `retry …` stamps is refused until it is restamped.

   **Stamp `gates <N>: verify=<pass|reject> review=<pass|reject>` into the row
   when both gates of a round have answered** — one token per gate ROUND, `N`
   being that round's number, read by `run_quality.py` (ticket 37, the run-record ticket, ruling 28).
   Write it beside whatever prose you were going to write. Two fixed verdict
   words only, `pass` and `reject`: a token that also took `accept`, `passed`
   and `rejects` would be an eighth dialect rather than an end to the seven
   (`run_quality.py`'s docstring holds the seven).

   **A strike is still DERIVED and the token does not state one.** It says what
   the gates answered. Step 5's prose-deletion road and a runner-error
   annulment both cancel a strike in prose and write no marker, so the count
   stays "rounds rejected since the last criteria reset", and a row whose own
   words disagree with the count is marked `*` with both shown and neither
   preferred. **Nothing refuses a row without it**, and that is deliberate: 143
   rows were written before it existed, and the prose reader stays.
   `run_quality.py` prints how many rounds carry the token.

   **Size the issue while settling the road**, and write the estimate in its
   ledger row — an overrun then reads as live signal instead of archaeology.
   Where the given order and dependencies permit, schedule the big ones last:
   runs halt on usage limits, and a whale mid-batch starves the cheap issues
   queued behind it. Never split an issue yourself — a runner-invented sub-issue
   is an untriaged spec. An issue too big to be one issue goes back through
   `/harden-issues`.

   **Flag a prose-graded criterion while settling the road** — one whose
   pass/fail is decided by reading prose rather than driving behaviour. Its bar
   regenerates on every fix, so make it executable or bounded before spawn, or
   send the issue back through `/harden-issues`. This, more than difficulty, is
   what separates a whale from a clean issue (181: decisions.md).

   **A prohibition in a brief names the SYSTEM, not the verb.** Every "do not"
   carries the forbidden thing AND the permitted one, with an absolute path
   wherever a path exists. The pattern, from the 2026-08-09 run: "QA is the only
   WRITABLE database" constrained the operation and left production reachable, so
   a verify gate read production with a service-role key. A brief that constrains
   the ACT while leaving the PLACE unnamed gets a different answer from every
   agent. Adopted by the human, 2026-08-09; `decisions.md` holds that run's other two
   faults. The round header above carries the paths and the harness for every
   brief; this rule governs the prohibitions the header has no field for.
2. **Read its final message before doing anything else.** If it reports unfinished
   work, the issue is not gate-ready — re-spawn to finish it, or mark `blocked`.
   If it reports the acceptance criteria are *wrong* rather than unmet, spawn a
   review gate to confirm that claim only; if confirmed, set the issue
   `needs-harden` with the evidence and move on. Never build to criteria a worker
   has shown to be wrong.
3. Spawn **the verify gate with `run_in_background: true`, then the review gate
   with `run_in_background: false` on the next turn, without waiting for the
   verify notification.** Neither reads the other's verdict — verify drives the
   app, review reads the diff — so the wall clock is the slower of the two rather
   than their sum. The round ends when both verdicts are in: the review gate's
   return and the verify gate's task notification, in either order. Read both
   before step 4. Use the review `-critical` variant when the diff **changes**
   money computation, auth or secret handling (touching a file that has a price
   field does not count). If verify rejects, read the review anyway: its findings
   still route, and its work is already spent.

   **A brief that names a path for a private copy also names the method**: `rsync`
   the tree excluding `node_modules`, `.next` and `.git`, then symlink the real
   `node_modules` into the copy. A gate given a path and no method invents its
   own; `decisions.md` holds the one that hung. (Adopted by the human 2026-08-14.)
   **This copy cannot run `npm run build`** — Turbopack panics on the symlink.
   Use `cp -al` for a build; tests and mutation drills keep the rsync recipe.

   **Three facts about those two copies, each one paid for before it was written
   down.** *`cp -al` makes HARD LINKS, so a write inside that copy lands in the
   run's own worktree.* It is a copy for READING and BUILDING, never for a drill
   that writes. **A drill that writes proves its copy is not hard-linked, before
   it writes.** The sentence above cannot refuse anything; this can:

   ```bash
   ls -li <file in the copy> <the same file in the run worktree>
   ```

   The same inode means the write will land in the run's own worktree: stop.
   (Adopted by the human 2026-08-27 as B5.)

   *The rsync copy's `node_modules` symlink is a TWO-WAY DOOR.* A path that
   resolves through it reaches the real directory, and nothing warns. Delete
   nothing under `node_modules` from inside a copy. Where the project's
   vitest cache lives at `./.vitest-cache` in each tree's own root, so clear a
   stale one with `rm -rf .vitest-cache` inside your own copy (ruled by the human
   2026-08-29; `decisions.md` holds the three deletions that earned it).

   *The rsync copy excludes `.git`, so anything reading history refuses there,
   and that refusal is not damage.* The two cases in
   `tests/scripts/check-issue-citations.test.ts` that drive git SKIP when the
   tree has no `.git`, and `scripts/check-issue-citations.mjs` exits 3 with
   `REFUSED no-git-repository` naming the copy as the likely cause.

   **Concurrent gates share a tree but not a pen.** Both gate briefs require
   mutation drills on scratchpad copies; a gate that genuinely must write the
   tree declares it in its verdict, and then it is the only writer — a "touch no
   code" gate that mutates source to prove a test can fail is a writer, whatever
   its banner says. Before committing, re-check each graded file's checksum
   against the ones the gates recorded at gate close (`decisions.md` holds the
   run where only that checksum stood between the run and committing a mutant).

   **Each gate drills in its OWN private whole-tree copy, at a path carrying its
   issue id and its role.** Never a shared scratch directory, and never a name
   two gates could both choose. Checksums at gate open and close cannot see a
   collision that undoes itself before the stamp; a private copy makes it
   unrepresentable rather than detectable (209-215: decisions.md).

   **While the gates run, the runner preps issue N+1, read-only:** settle its
   road, size it, pre-write the spawn prompt, prune the ledger, run the fixture
   pre-check (below). None of it touches the tree, so single-writer holds; on
   gate-pass only routing-verify, lint and commit remain serial.

   **The coverage check runs in that same window, never before the gates.** The
   VERIFY GATE writes the report inside its own private copy, as part of a whole
   suite run its brief requires; you run the check alone, at the commit step. So
   the proof is written by something that did not build the diff, and the run
   stops paying the suite's runtime in the foreground (ticket 40, ruling Q4):

   ```bash
   python3 ~/.claude/skills/run-issues/check_diff_coverage.py \
     --repo . --diff-range <fork-point>..HEAD \
     --coverage <verify gate's copy>/coverage/coverage-final.json \
     --report-root <verify gate's copy>
   ```

   **Both paths come off the gate's last line, verbatim, and you cannot guess
   them.** Without `--report-root` every changed file reads as absent and the
   check refuses a diff it never graded. Where a gate returned no such line, run
   the suite with coverage in your own tree and drop `--report-root`.

   It refuses a diff that changes source and changes no test, a diff whose
   changed lines the report shows unexecuted, and a diff it cannot grade — no
   report, an unreadable one, or one older than the code. **It does NOT grade a
   standalone script, and it names every one it skipped**: a file is excused
   only when it sits at the top level of a `scripts/` directory, nothing imports
   it, and the report does not mention it, so `scripts/lib/…` is graded. **Read the `NOT
   GRADED` block in its output before you quote its percentage.** The docstring
   holds the measurements.

   **At prep, if a recorded default seeds, deletes or renames a row in a shared
   database, read the test files this run has already committed on this branch.**
   One `git diff --name-only <fork-point>..HEAD -- '*.test.ts'`, then read the
   ones that touch the same tables. A default hardened days ago cannot know about
   a guard an earlier issue in the same run committed, and no hardening pass can
   catch it. A permanently red test invites a relaxation, and that relaxation
   disarms a tenancy guard (`decisions.md`; the human 2026-08-14, queue item
   T24R1-5).
4. **Before reading either verdict, run the check.** One command per gate,
   against the issue file in this run's own worktree:

   ```bash
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Verify gate"
   python3 ~/.claude/skills/lib/check_verdict.py --file <issue file> --section "## Review gate"
   ```

   **It has four refusals, not three.** It exits non-zero when the heading is
   absent, when nothing sits under it, when a row still reads `pending`, and when
   the section sits above the newest `Implementation record, attempt N` heading —
   `stale`, meaning the section grades an earlier diff. **A non-zero exit is
   neither a pass nor a rejection: the gate did not report.** Re-spawn it, or
   ledger the issue `blocked` with what the check printed. Never let one gate's
   verdict stand as the round's answer while the other is missing. A gate that
   drilled on a private copy can write its verdict beside the copy instead of
   beside the branch; passing the path in this worktree is what makes that a
   refusal instead of a silent pass. **This is a check and not a reminder on
   purpose:** the rule it enforces was told twice and failed a third time
   (the human 2026-08-14; `decisions.md` and the script's docstring hold the faults).

   Both pass → **verify the routings**: grep each target file for the exact
   line the gate quoted as appended — gates end each routed finding with that
   quote, and the runner greps the string, never a heading. A declared routing is
   not a routing. Check the verify gate's `Drove:` list against
   `git diff --name-only`; a route the diff touches and the gate never fetched is
   an incomplete verdict, not a pass. **Run lint** — it costs nothing and catches
   the shape defects no per-issue gate can see. Then commit, staging **explicit
   paths only** — never `git add -A` or `.`. Glance at `git status` and
   investigate anything unexplained *before* committing.

   **Run `npm run build` at every commit step, not only at the finale.** The suite,
   the type checker and the linter together do not run the Next compiler, so none
   of them sees a module the compiler will empty (`decisions.md`). It costs
   seconds a commit. (Adopted by the human 2026-08-24.)

   **A build result is never read from log text. Every build writes its exit code,
   and the exit code is the record.**

   ```bash
   npm run build; echo "BUILD EXIT=$?"
   ```

   A brief that reports a build without one is incomplete, and that is what makes
   this refusable rather than a reminder. A build can print a success line and
   then exit 1 (`decisions.md`; the human 2026-08-27, B4).

   **Build in a copy, never in the tree a dev server is serving.** `rm -rf .next &&
   npm run build` deletes the directory the dev server answers from, and every
   route then answers HTTP 500 on sound code. Copy with `cp -al` and build there;
   the rsync recipe is for tests and drills. (Adopted by the human 2026-08-24.)

   **Each pass is pinned to the commit it reports on, and runs in the background.**
   The checker takes `--at <sha>`, and at that sha no verdict it prints depends on
   anything outside the commit, so the pass never runs serial with the
   implementers. At every commit, fire the pass and move on:

   ```
   git diff --name-only <previous commit>..HEAD
   node scripts/check-issue-citations.mjs --at <the commit just made> --quiet \
     <each issue file citing one of those changed files> \
     > .scratch/<feature>/citation-deltas/<sha>.txt 2>&1
   ```

   **Pin to the commit just made, never to branch head.** R2 needs each row to
   name the commit that moved the citation, and a pass pinned to a later head
   cannot name one. **Name only issue files that commit carries**: the pass
   refuses with exit 5 and names the path when it is handed one the pinned tree
   does not hold. Filter the list against `git ls-tree -r --name-only <the
   commit just made> -- .scratch`, or run that file unpinned. A skipped file
   leaves no row, and a pass with no rows prints a clean summary.

   **`--all` stays banned here** (ruled 2026-08-26): a commit can only break a
   citation into a file that commit changed. **The baseline pass pins too**: the
   runner commits its pre-flight state and pins the baseline to that commit; it
   does not stash and it does not read the working tree. **Passes queue in commit
   order and run one at a time. None is ever dropped.**

   **One file per sha, in `.scratch/<feature>/citation-deltas/<sha>.txt`.** The
   last line of a finished pass reads `=== CITATION PASS COMPLETE === exit=<n>
   pinned=<sha>`. A file without that line is a killed pass, not a clean one.
   `citation_pass.py --deltas <dir>` is the one reader, and the finale runs it
   over the whole directory and names every sha it refuses on in the merge
   briefing; it re-runs the pass itself for nothing. **The catch-up pass at
   branch head is removed** (ruled by the human 2026-09-06): nothing in a run acts on
   the finding, because a run may not write an issue file. `citation_pass.py`'s
   docstring holds the measurements behind both rules.

   **File each new `moved` or `gone` as a register row naming the citation and the
   commit that moved it.** The row is the whole remedy, and the run repairs
   nothing: a run may not edit the specification it is graded against, so the
   repair belongs to the next `/harden-issues` pass over that issue, which
   already reads the file and is already allowed to write it (the human,
   2026-08-15). The checker holds the same rule in its own code.

   **The register is swept at every issue's commit too, and for the same reason.**
   Re-read every register row filed against the issue that just committed, and
   close what the commit closed. A row the commit closed reads `verified`. A row
   it did not stays `open` WITH THE REASON, never bare, and travels to promotion
   untouched. Without the sweep promotion mints issue files for work that has
   already shipped (`check_register_status.py`'s docstring holds the count;
   the human 2026-08-27, F6). **A hook refuses the commit until this is done**, so
   read the sweep back before you commit rather than being told (ticket 36,
   ruling 16):

   ```
   python3 ~/.claude/skills/run-issues/check_register_status.py <register or shard> --sweep <issue>
   ```

   The finale runs the same command with `--sweep <batch-id>` before promotion.

   The citation checker's exit codes, which a collector reads: 0 clean, 1 a fault,
   2 no issue file matched, 3 not a git repository, 4 the unchecked-majority
   refusal, 5 `--at` could not be honoured, 6 named paths went ungraded. Codes 4,
   5 and 6 are refusals to answer, not answers, and all three outrank 1
   (`decisions.md` holds why 6 is a sixth code). (Adopted by the human 2026-08-18 as
   R2: it trades run time for record accuracy, which is a price only the human may
   set, and they set it.)

   **The runner commits. An implementer never commits its own work**, and the
   runner says so in every spawn. A self-commit does no visible harm, and that is
   the trap: it silently changes what "the diff" means to a gate already reading
   it, so the runner must hand those gates an explicit commit range instead of
   the working tree. Where an implementer has committed anyway, do not revert
   it — record it and give the gates the range (209-215: decisions.md).
5. **Both pass but a verdict enumerates follow-up items** (a gap on the issue's
   own invariant, a test the evidence says should exist) → ledger `correction`,
   not `done`. Name the owed items yourself — a verdict is prose and no gate brief
   sets a list shape — then compose the spawn prompt with `correction_brief.py
   --issue <file> --item "..."`, which carries the items, the correction marker and
   nothing else, and refuses a prompt the brief cap would refuse. Spawn it in a
   fresh context, never as a message to a live agent. On resume, a `correction` row
   is re-spawned the same way; it is still the one round. One round maximum; the
   scope is the verdicts' list — anything bigger becomes a register row instead.
   **While any row shows `correction`, no new implementer spawns** — that status is
   what makes a second writer in the tree unrepresentable. The round closes on each
   item's *named evidence* (the test now exists and is green, the mutation now reds)
   AND on a citation re-run over the files it touched that reached its terminator —
   never on files having been touched. `correction_close.py --test "<cmd>"
   --pass-file <path>` refuses on either. Then commit and `done`. A correction round
   is not a strike. A round closing on its own say-so states a conclusion where it
   owes a measurement (`decisions.md` holds two that did). (R1, 2026-08-23; the
   terminator and both scripts, ticket 40 ruling Q7.)

   **A standards-shaped split is a correction, not a retry, on one condition:
   every gate grades the behaviour correct AND the owed work is enumerated.** The
   shape is a verdict that splits on how the work is written down rather than on
   what it does — a missing pin, an unrun mutation, a claim that outruns its
   evidence. Where the behaviour is agreed and the list is closed, buying a fresh
   implementer to re-do correct work is waste, and the strike it charges is a
   strike against a spec fault. If either half fails — any gate doubts the
   behaviour, or the owed work cannot be enumerated — it is a retry and a strike,
   as before. (Adopted by the human 2026-08-07 with that condition attached.)

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
   lines is the waste, not the deletion. Four conditions, all of them, and any
   miss puts it back to a correction round:
   every gate grades the behaviour correct; every owed item is non-executable
   prose; the delete-only rule above already governs the class; and the runner
   can verify each deletion by grep, from its own context, without reading the
   diff into a new one. The runner records the deletions in the ledger row as
   `prose: deleted` and names each site. It is not a strike, and it is not a
   correction round either — the row goes straight to `done`.

   the human approved this on 2026-08-24 as "the gate files a register row and the
   commit lands". It is built as a deletion instead because a false sentence in
   a code comment is `audience: agent`, and `~/.claude/agents/promotion.md:34-36`
   refuses `audience: agent` at any severity: filed as a row, the false sentence
   would ship, be refused at promotion, and stay. `decisions.md` holds the two
   rounds the saving was measured on.

   **A negative conclusion drawn from a grep does not travel without its scope,
   in the same sentence.** "There is no X" from a single-line grep is a statement
   about that pattern in those paths, not about the codebase, and it must say so
   where it is asserted. Adopted as admissibility by the human 2026-08-14 — a
   scopeless negative is not passed onward, by a gate, a finale or a runner, and
   a reader who receives one sends it back rather than acting on it
   (`decisions.md` holds the night the advice was broken).

   **When a round deletes a claim, search the branch for a twin before the round
   closes.** One grep for a distinctive phrase from the deleted sentence. A claim
   worth writing once tends to get written twice, and no gate reads two issues,
   so the second copy ships unread. (Adopted by the human 2026-08-11, narrowly;
   `decisions.md` holds the run that earned it.)

   **Three rules on what a claim may SAY. They bind every artefact an agent
   writes — issue files, the primer, migration headers, the briefing — not
   only a rejection fix.** (207-185 and 209-215: decisions.md.)

   *Never write that something is the only copy.* Uniqueness across a corpus is
   not a fact one agent can establish. Cite the canonical location; do not claim
   it is the only one. The class survives its own cure: `decisions.md` holds the
   instance written as the REPAIR for a stale-prose defect.

   *A recorded cause is tested against a control, never merely observed.* One
   run that works does not name the reason it works, and one control run settles
   it (`decisions.md`).

   *Every citation carries its repo-relative path in full, every time.* Not the
   first mention only, and never a bare filename afterwards. A bare filename the
   tree holds twice resolves to plausible code, so the reader finds a defect that
   is not there, and an implementer can lose a strike to it. Repetition is
   cheaper than ambiguity (209-215: decisions.md).
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
   statement. A grep-backed refutation states its scope beside its conclusion
   (208-202 run: decisions.md). Ledger actuals derive from commit times, full
   stop. **`check_commit_order.py` is what checks that, at every commit step and
   again at the finale.** Run `check_commit_order.py --ledger <run.md> --repo .`
   right after the row's `committed <sha>` stamp is written, so a drifted stamp
   fails while the runner still has the round in context. It compares the git
   author date against the round's close time, two sources that cannot drift
   into agreement; its docstring holds the runs that broke the sentence above.
   (Adopted by the human 2026-08-25 and 2026-08-29.)

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
     (Ruled by the human 2026-08-29.)

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
   prior rejections a line count is fiction (decisions.md). It states the
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
names it, and a write to `register.md` itself is refused.

**A ruling that creates work gets its issue number in the same sitting as the
ruling, from `python3 ~/.claude/skills/lib/claim_number.py issue <dir> --for <who>`.** A ruling is a decision, not a finding, so this stays a direct issue file
and does not go through the register. Not "that becomes its own issue" — the
number, or the file and line where the work now lives. A ruling with no artefact
cannot be told apart from a ruling nobody made (209-215: decisions.md).

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
The human's decision, taken once at run end: the run stops at `awaiting-merge`, and
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
(decisions.md). A long implement attempt moves no status line for an hour, so
"no progress" cannot mean "dead" — only a stale mtime can.

**The owner line is cleared the moment the run stops owning the tree.** Reaching
`awaiting-merge`, or halting, rewrites it to `Owner: none — <awaiting-merge|HALTED>
<date> <HH:MM>`.

**The stall watch is a separate PROCESS, and the cron cannot replace it.** A
`CronCreate` job fires only while the REPL is idle, and a session behind a modal
is mid-query, so it is never evaluated — measured 2026-09-12, a job due at
04:44:00 sat unfired at 04:45:32 under one tool call holding 04:42:02 to
04:45:32. That is why `batch-200d42` stalled 208.8 minutes with a wakeup
installed. Jobs die with the session too, so one can never report the death it
was made to catch. Start this at launch; it exits itself when the run ends:

  ```
  nohup python3 ~/.claude/skills/run-issues/stall_watch.py --ledger <run.md> \
      >> ~/.claude/logs/run-stall-watch.log 2>&1 &
  ```
It resumes nothing. On a frozen ledger it tests whether a `claude` process still
sits in the run's worktree: alive is STALLED and says do not resume, gone is DEAD
and prints the resume command. Keep the cron for the idle usage-limit wait it does
cover, and remind once that the machine must stay awake (`caffeinate -dimsu`).

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
(ticket 38, the layout ticket, ruling 11); `resume.md` says how.

## Pre-flight

- **The session that types `/run-issues` is launched with the three directories
  every worker reads outside the worktree**, or an unattended worker meets the
  CLI's one-time permission prompt for a read outside the working directory and
  the run halts where nobody is watching (ruled by the human 2026-09-06):

  ```
  claude --permission-mode bypassPermissions \
      --add-dir ~/.claude/skills ~/.claude/agents <the project's memory directory>
  ```
- **The mode is part of the launch line, not an option.** An unattended run cannot
  answer a modal: run `batch-200d42` lost 5.7 hours of 9.22 to two permission
  prompts nobody was there to press. `bypassPermissions` turns off the classifier,
  not the hooks — measured 2026-09-12, `coderules-gate.py` and an unconditional
  PreToolUse hook both still block in that mode, and the denial still reaches the
  agent. The human's guards keep their teeth; the modal goes.
- **The launch line is a gate, not an announcement. Nothing spawns before it
  prints.** One line on every invocation — issues in order, branch, the resolved
  session model, **the resolved session effort**, and what will NOT happen (no
  merge, no prod). This line is where a wrong setting gets caught, one keystroke
  before spawn 1; write both settings into `run.md`'s header in the same breath.
  It is not a wait: it prints and the run carries on. (Adopted by the human
  2026-08-07; `decisions.md` holds the run whose line printed too late.)
- **Concurrency gate — REFUSE to start while an unmerged hardening branch holds
  an issue in this batch. This is the FIRST thing the pre-flight runs, before
  the batch id is minted and before the hardening phase is triggered.**

  ```
  python3 ~/.claude/skills/run-issues/check_harden_branch.py \
      --issue <id> [--issue <id> ...] [--repo <path>] [--base main]
  ```

  Exit 1 blocks the launch. The remedy is to merge that branch and re-read the
  issue files, which costs a fast-forward: those branches touch `.scratch/` only.
  It needs no batch id, no ledger and no worktree, which is why it can run first.
  Run `bridge-cse` built four issues from unhardened files while a peer
  `/harden-issues` branch held hardened copies of all four (the script's
  docstring holds it), and `decisions.md` holds what mock drive D measured when
  the fold put the hardening phase above this gate.
- **The ceiling and the issue range are refused at the prompt, not checked
  here.** `~/.claude/hooks/machine-preflight.py` refuses a third `/run-issues`
  while two runs are live, any `/run-issues` whose typed issue range overlaps a
  live ledger, `all` beside any live run, and a scope token the grammar cannot
  read (ticket 38, the layout ticket, rulings 20 and 21). It has no override word.
  Then mint the batch id and create `.scratch/<feature>/runs/<batch-id>/`.
- **Seed this run's QA workspace; the script writes its two lines into the ledger
  header.** Inside the run's worktree, once the batch id and `run.md` exist:

  ```
  node --env-file=<env file> scripts/seed-run-workspace.mjs --batch <batch-id> --ledger <run.md>
  ```

  It creates one auth user, one `workspaces` row named `run-workspace <batch-id>`
  and one `admin` membership, idempotently, behind `scripts/lib/db-target.mjs`, and
  writes `QA workspace:` and `Sign-in user:` into that `run.md`. Two runs at once
  then write disjoint rows (ticket 38, the layout ticket, sitting 2, ruling 3). **Every fixture
  script in `scripts/` run inside the run's worktree reads that `QA workspace:`
  id off `run.md` itself**, through `seedWorkspaceId` in
  `scripts/lib/run-workspace.mjs`, and refuses a `SEED_WORKSPACE_ID` naming any
  other workspace, so an implementer sets nothing and its gate reads the run's
  rows. The finale deletes the workspace by that id; the daily brief sweeps what
  a merged or long-halted run left (ruling 12).
- **Run the citation check over the batch's own issue files, and name the broken
  ones in the launch line.** `node scripts/check-issue-citations.mjs --quiet
  <file>` per issue in scope, batch files only, never `--all`, over the copies in
  the run's own worktree.

  **It is report-only on a stamped file, and the phase repairs an unstamped
  one.** A run may not write an issue file it did not harden, so a stamped
  file's broken citations are named in the launch line and left where they are.
  An unstamped one is inside `launch-harden.md`'s scope, which is a hardening
  pass and carries the write authority to repair it. Either way a stale spec is
  visible in the interrupt window instead of met mid-run as a wrong premise.
  (Ruling 9 of ticket 33 split the two roads.)

  **Read the copies in the run's own worktree, not the main checkout's**, so
  that this reading and the phase's repair are about the same files. A worktree
  freezes the tracker at the moment it was cut: an issue file committed to main
  afterwards is not in it at all, and one stamped afterwards still reads
  unstamped there. **Where a scoped file is missing from the worktree, bring it
  onto the branch before the phase runs**; the criteria gate below refuses it
  either way (`decisions.md` holds the drive that met it).

  **The verdict is the file's own summary line and the `MOVED`, `GONE` and
  `AMBIGUOUS` rows that NAME it — never the exit code.** There is no flag that
  turns the decision pass off, so `--quiet <one issue file>` always grades every
  landed decision in the repository beside the citations in the file you named,
  and one stale `Touches:` line anywhere makes the process exit 1. A runner
  reading the exit code names every scoped file as broken — and since ruling 9
  the phase WRITES on that reading (`decisions.md` holds the measurement).

  **A zero from that check is a fact about the FILE, not about the instrument.**
  Report it as "this file carries no parsed citations at this moment" and never
  as "the checker does not recognise the form these files use": a claim about
  the tool tells every later pass the instrument is blind, so nobody runs it
  again (`decisions.md` holds the run that did; the human 2026-08-29 and 2026-08-30).
- **Re-derive every fact the run will carry into its spawns, from source, and
  name the source beside it.** Carry-forward entries, batch-plan sentences,
  anything a previous session wrote down — none of it is evidence. Read the
  function, run the query, open the migration. A carried misreading and the truth
  it replaced can fail in opposite directions, so the error stays invisible while
  it does damage; `decisions.md` holds the nine-hour instance (209-215).
- **Every spawn carries its own role's model, read off the ledger.** Read
  `Model map at launch:` in `run.md`, take this role's value, and pass it in
  the Agent call's `model` field. Every spawn, every role, every attempt.
  (Ticket 39 ruling 10 reversed the older rule of never passing one;
  `decisions.md` holds the era it was right in.)

  **`~/.claude/hooks/model-map-gate.py` refuses any other value, and a missing
  one.** The refusal names the exact value to reissue. **It is never a halt and
  never waits for the human**: reissue the same call with the value it names, in the
  same turn. **`~/.claude/hooks/model-landed-check.py` then reads what actually
  ran** and appends one line per spawn to `run-journal.md`; a mismatch never
  halts anything. **The finale READS those lines, and `run_quality.py` is what
  reads them** (sitting 4, ruling 22): one `**MISMATCH**` marks this run's trial
  VOID in the merge briefing, which halts nothing and unmerges nothing. **A
  journal with no landed line reads `not measured`, which is not a pass.**

  **The fourteen agent files still say `model: inherit`** (ruling 6), so a spawn
  by hand in an ordinary sitting behaves exactly as it always did. **One spawn
  falls outside all of this, and it is the one with no agent file.** The
  finale's board render is not one of the fourteen roles, so the map does not
  name it and the gate does not judge it. `finale.md` step 5 requires
  `model: "opus"` named explicitly on that Agent call, and carries the reasoning
  for the pin. This bullet governs the fourteen briefed roles; `finale.md`
  governs the one spawn that has no brief and no map row.
- **Record the session model in the ledger's owner line and in the merge
  briefing.** Every tier this pipeline has evidence for was earned at Opus 5
  (decisions.md). A run on any other tier is still a valid run, and it is also
  the first evidence at that tier. Say it once, where the verdicts live.
- **Orchestrator cost, stated at launch.** Run
  `python3 ~/.claude/skills/run-issues/orchestrator_cost.py --days 7 --issues <count>`
  and paste its table into the launch message. It reads the last week's run transcripts
  and prints what the orchestrator cost at each batch size already run.

  **This states a fact. It refuses nothing, and it recommends no size.** The human ruled on
  2026-08-21 that there is no ceiling on how many issues a run may take, and that the
  reading must come from inside the last week: they change the workflow daily, so an older
  figure describes a system that no longer exists. If the window is empty the script says
  so and prints nothing else. Do not go looking for an older number.

  **`--days` is the launch reading and `--batch <id>` is the finale's.** `--batch`
  measures ONE run or hunt, per model and per role, and the finale takes it through
  `run_costs.py` (ticket 39, the model-map ticket, ruling 12). Do not read the window as this run's cost.
  A run that mixed models has no single weighted figure: the table names the tiers
  that answered and refuses to add them (ruling 11).
- **Hardening stamp, and the phase it triggers.** List every scoped issue whose
  file lacks a `Hardened:` line in the launch message. **A typed issue in scope
  with no `Hardened:` line is the trigger to read `launch-harden.md`, beside this
  file, and the phase it holds runs here — after this line prints, before the
  criteria gate below it, and before spawn 1.** The phase reads the batch id and
  the model map off `run.md`, so it cannot run before the bullets that mint
  them. That file holds the whole phase. Where the list is empty the file is
  never opened and the run costs what every run before the fold cost. (Ticket
  33, ruling 16; `decisions.md` holds why the phase is a file rather than a
  section here.)

  **Read the `Hardened:` lines in the run's own worktree**, the same copies the
  phase repairs and commits, for the reason the citation bullet above gives: a
  worktree cut before an issue was stamped still reads it unstamped.

  An `all` run takes stamped issues, and `Hardened (provisional)` counts as
  stamped — a pending default is not a reason to drop an issue. An explicitly
  named issue always runs, stamped or not. The merge briefing names every issue
  that shipped unstamped or provisional, with its pending defaults.

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
  into the spawn prompt and the run then grades its own invention. It stands
  between the runner and a freshly promoted register row, not a hardened
  backlog: the script's docstring holds the base rate among `ready-for-agent`
  files and the run that hurt. (Approved by the human 2026-08-24.)
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

  The instance is a rule that sat in the MAIN checkout's untracked
  `.claude/settings.local.json` and not in the run worktree's copy. That file is
  gitignored, so a worktree freezes it on the day it was cut (`decisions.md`
  holds what it cost). **This does not dry-run anything, deliberately.** A class
  verified at launch is not a class verified for the run, because the dry run
  never consulted the thing that refuses. A tracked allow rule is checked BEFORE
  the classifier and git carries it into every worktree, so that is what this
  reads. (Built 2026-08-30 on the human's instruction, closing `rn99f-03`.)

  **It grades FOUR roles and says so, and it grades per SEGMENT.** Run
  `batch-200d42` read `ok: 12 command class(es)` and then lost 3 h 37 m of its
  9.22 hours to a permission modal on issue 441's verify gate. The twelve were
  the RUNNER's classes; the command that halted was a GATE's, and it was
  compound -- `cd ... && export PATH=... && sed ... && npx vitest ... | tail`.
  `npx vitest*` was tracked and the other four segments were in no allow list,
  and the classifier admits a compound command only when EVERY segment is
  admitted. The check now carries `runner`, `verify-gate`, `review-gate` and
  `review-gate-critical`, splits each shape into segments, and **names in its
  own output the roles it did NOT grade and the classes the human ruled must stay
  classifier-judged**. A floor that grades a list it wrote itself and prints
  `ok` is evidence about that list and nothing else. (Built 2026-09-12 on his
  instruction; the run's own audit file holds the measurement.)

  **A pass does not mean the run cannot halt.** Seven measured gate classes are
  deliberately uncovered -- `psql` writes, `bash -s`, `perl -0pi`, `python3 -`,
  `node -e`, git writes and the private-copy tools -- because each is either
  arbitrary execution or a road around a control. The check prints them at every
  launch. Expect a classifier refusal on each, and a gate takes the closed road
  its brief already names: unprivileged path or report blocked, never a retry.
- **Creating the worktree includes installing dependencies and making the
  `.env.local` symlink. If either fails, the runner refuses to start.** Not a
  check to remember at pre-flight — part of what "the worktree is ready" means.
  It costs one shell command and under a minute per worktree. (Adopted by the human
  2026-08-07.) A typecheck can exit 0 against a global install and never load
  the repo's types. **A green produced without dependencies on disk is a false
  green** (208-202 run: decisions.md).
- **Verify the allowlist, never assert it.** Dry-run every command class this run
  will use, in no-op form, before spawn #1. A miss is a launch-time blocker;
  mid-run it is a worker blocked on a prompt, stalling silently. **Refuse to
  spawn while any class is refused or unverified.** Never start a run intending
  to approve a prompt later. The whole value of this check is that it fails
  while the human is still at the keyboard.

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
    other run's server (ticket 38, the layout ticket, sitting 2). No refusal catches a wrong port
    yet; the header field `Dev server:` and this fact are what there is. **The
    gate drives that server at `<batch-id>.localhost:<port>`, never bare
    `localhost`**: a browser cookie is scoped to the host and not the port, so
    two runs on `localhost` share one session, and `dev-signin-link.mjs --batch`
    refuses any other host. **It probes that server through the repo's probe
    script, never with a bare `curl`.** On this repo that is
    `node scripts/http-probe.mjs "<label>" <url>`, allowed by one prefix rule; a
    raw `curl` gets allowed as an exact string, so the next probe with a
    different port, path or label prompts again, unattended. The script refuses
    any target that is not this machine.
  - **The runner itself** — `CronCreate`, for the resume wakeup, on any run that
    could meet a usage limit.

  **The dev server is named here because leaving it off cost a night.** The
  bullet it replaced ran correctly and still lost it: a runner read an
  illustrative list as a complete one. That is why the list above is a floor
  rather than a definition (`decisions.md`).
- **An unattended run may delete only rows it marked as its own, and the scope of
  the delete is that marker.** Where a run needs to clean up after itself, it
  stamps a run-owned marker column on every row it writes and deletes on that
  marker alone. It never widens its database permission to cover deletes in
  general, and it never deletes a row on an argument that it must have written it.
  A permission granted once is held for every later run, including the one that
  reasons badly at 3am; a marker column is scoped to the rows and expires with
  them. (Adopted by the human 2026-08-07.)
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
