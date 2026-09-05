# The finale, in full

The runner reads this file once a run, when it writes `finale-mechanical` into
the ledger after the last issue. That write is the trigger, and `SKILL.md` holds
it. Nothing here is resident in `SKILL.md`, because a run pays for that file on
every turn and pays for this one once.

The text below stood in `SKILL.md` until 2026-08-16 and moved here unchanged
(workflow-audit row 7).

## Finale — fully automatic

After the last issue, in order, tracked in the ledger as
`finale-mechanical → finale-judgment → finale-promotion → finale-board →
awaiting-merge` so an interrupted finale resumes rather than re-running. Write each
state before the step it names begins, so a kill inside a step resumes at that step
rather than past it.

**Run the guard before every one of those writes, and do not write if it refuses:**

```
python3 ~/.claude/skills/run-issues/check_finale_stage.py --ledger <run.md> --to <stage>
```

It permits the next stage in the chain and a repeat of the current one, and refuses a
jump, a reversal and a ledger with no state. **This exists because the finale wrote
`awaiting-merge` with promotion and the board still unrun in three consecutive runs** —
`dc132b`, `cab74e` and `fd4fa2`, the last at 15:10 on 2026-08-20, where the runner put the
state back by hand. Promotion is what turns register rows into issue files, so a resume
that skips it loses them. The human approved the refusal on 2026-08-21. Promotion is safe to re-enter — it deletes each row as it
resolves it — and the board render is safe to repeat:

1. **Mechanical.** Full typecheck, full test suite, and a build from a **cold
   cache** (delete `.next` / `dist` first — a warm cache agrees with whatever it
   already compiled). Committed run state is build input: the ledger, journal and
   issue files sit inside the repo, so whatever scans the project scans them too.
   Confirm the toolchain excludes them, and treat a code fence in a write-up as
   something the build may try to compile. Failures reopen the offending issue
   through the per-issue loop.

   **The cold-cache build destroys the dev server's build directory, so this step
   hands the next one a working server.** After the build finishes, `preview_start`
   the dev server and confirm one route answers 200. Record that confirmation in
   the ledger beside `finale-mechanical`, so the judgment step reads whether it has
   a live harness rather than assuming one. `preview_start` on a stopped server is
   already permitted, so this needs no new permission. (Adopted by the human 2026-08-18
   as R3, from the `cab74e` finale: the step deleted `.next` under a server that
   had run since 02:27, every route answered HTTP 500 afterwards, `preview_stop` was
   TAKEN TO BE refused by the permission classifier in an unattended run, and starting
   a server by hand is forbidden by the round header. **So `finale-judgment` drove no
   cross-issue seam live in that run**, and fell back to reading composed source at
   branch head plus five seam test files. The failure is silent: the briefing still
   appears, and nothing in it announces the gap unless the finale volunteers it.)

   **CORRECTED 2026-09-02: `preview_stop` is NOT refused.** The `batch-45c8b1` finale
   called it on Claude Code 2.1.255, unattended, and the classifier permitted it. That
   is the only reason that finale recovered its own dev server instead of handing the human
   a numbered action. R3 itself stands unchanged; only the claim about the classifier
   was wrong. Do not plan around a refusal that does not happen — call `preview_stop`
   when the server needs restarting, and record what the call actually answered.

   Preview deploy is **skipped in this repo** by standing decision — see the repo
   CLAUDE.md. Say so in the briefing; never work around it; never re-litigate it.

   **When you drive a server action live to prove it dispatches, pass an argument
   that CANNOT write.** Read the action's first validation branch and pass
   something that reaches it. The refusal sentence proves dispatch exactly as well
   as a success does, and it leaves no row behind. Never pass an argument that
   would succeed. (Adopted by the human 2026-08-30 in the daily brief, from run
   `481-482-2d0f77`: one probe passed `{name: "x"}` to `addSupplierAction` to see
   whether it dispatched, and created a supplier on QA. Every other probe in the
   same sweep used a failing argument and wrote nothing. The finale then tried to
   delete the row and **the permission classifier refused the service-role
   delete, correctly**, so an agent that makes this mistake cannot tidy up after
   itself — it becomes a numbered action on the human.)

   **Two guards run here, and a refusal from either stops the finale.** Both were
   adopted by the human on 2026-08-25, from candidate rules a and b of run
   `batch-34455f`'s merge briefing.

   ```
   python3 ~/.claude/skills/run-issues/check_commit_order.py --ledger <run.md> --repo .
   python3 ~/.claude/skills/run-issues/check_paste_file.py <every paste file this run wrote>
   ```

   **`check_commit_order.py` prints two numbers and you read both**: how many
   status rows it READ, and how many of those carried a correction round. Its
   `ok` on nine rows and its `ok` on nothing are different sentences, and it
   exits 2 rather than passing when it can read no row at all. Added 2026-08-30
   after `rn414a-01`: on run `414a-483-286335` it printed `ok` having matched
   zero rows, because its reader demanded an em-dash after the issue id and that
   ledger wrote the id in its own column. It now reads the id by column.

   `check_commit_order.py` REPLACES rule 9's commit-time comparison in `SKILL.md`.
   That one compared the ledger's stamp against git, and the runner writes one
   from the other, so it agreed by construction. This compares the git author
   date against the correction round the row says the commit carries, which are
   two sources that cannot drift into agreement. On `batch-34455f` it refuses
   413b (26 minutes early), 413 (115 minutes) and 422 (1 minute, which nobody
   noticed), and passes the other six.

   **`check_paste_file.py` refuses a paste file git does not know, on exit 3.**
   Added 2026-09-02 on the human's ruling, from this run's F1: `batch-45c8b1` wrote
   seven paste files, committed none of them, and seven gates ran this script
   over them and all seven exited 0, because until then it graded content alone.
   An untracked paste file is not in the branch, so the merge cannot carry it and
   the deploy goes out with the migration unapplied and nothing left to paste.
   **Exit 3 is not exit 1 and wants a different repair**: `git add` and a commit,
   not a comment marker. It outranks a content refusal, because repairing a
   comment in a file nobody can pull repairs nothing. **Exit 2 here means the
   question could not be asked** — no working tree, or no git — and is not a
   verdict on the file. Tracked means the index holds it: a file added but not
   yet committed passes, deliberately, because the finale writes and commits
   paste files in the same round.

   `check_paste_file.py` also refuses a pilot paste file whose confirmation query
   is commented out. Pasted as written, such a query returns no rows, no error and
   no output, which reads exactly like a clean result — and on `0095` the
   dangerous outcome is the one only the row COUNT catches. Nine agents touched
   that run's two paste files and nobody ran the query. **A refusal here is
   repaired by deleting the comment marker AND running the query against QA
   before the briefing ships it.** The script cannot tell whether anybody ran it;
   it can only tell that the reader was handed something runnable.
2. **Judgment.** Spawn `run-issues-finale`. Its verdicts plus `merge-briefing.md`
   become the merge briefing.

   **The one-screen block that opens the briefing is written at step 4, not here.**
   It carries the wall clock, and the wall clock does not exist until the measurement
   runs. Writing it early means writing it with a hole in it.

   **Every command the briefing hands a human runs once first, against the state
   it will actually meet.** A pre-migration check runs before the migration, on
   the pre-migration schema. If it cannot run there, it is the wrong check.
   (155-157: a gate wrote the check, the runner copied it, neither ran it —
   the human's first instruction errored `42703`. decisions.md.) The gate briefs
   carry the same rule from the author's side; the runner re-checks when
   assembling.

   **A migration says when a constraint came from measured data rather than from
   a business rule.** A number read off today's input is a fact about one import,
   not a rule about the business, so the header names it as measured and the
   issue lists it in `## Must still be true` as an assumption a later issue may
   lift. (Adopted by the human 2026-08-10, from the 301-307 finale: issue 304a wrote
   `check (rank between 1 and 3)` because no tier in the customer's workbook held more
   than three brands; issue 307 let a member add a fourth, so migration `0086`
   had to lift the ceiling, and the runner's spawn brief told 307's implementer
   "this issue adds no migration" for the same reason. Both of 304a's gates
   passed it correctly, because its own criteria never mentioned the case. Cost:
   one unplanned migration and one wrong brief. `0086`'s header is the model — it
   names which sentence in `0085` was evidence and which was inference.)

   **A published checksum expires the moment the file moves.** A correction
   round re-stamps every checksum a gate published for a file it touched, and
   the finale re-runs any that remain before the briefing closes. Anchor diff
   commands to `main...HEAD`, never the working tree — a worktree diff prints
   nothing once the work is committed, and an empty print cannot distinguish
   "fine" from "the fix was reverted and committed". Both 202 checksums were
   correct at gate close and false three hours later, and running them read as
   the exact alarm the gate wrote them to raise (decisions.md).

   **Main moved while you worked. Read it before you write a question.** The run
   branches from a worktree cut hours or days earlier, so the human's rulings since the
   cut are invisible to every agent in the pipeline. The finale diffs the merge base
   against main's current tip and reads every commit touching an issue in scope.
   Anything they already answered leaves the briefing, and the briefing says they
   answered it. Adopted 2026-08-10: they ruled twice on issue 276 while that run was in
   flight, and the run came within one `Decide` item of handing them back a question they
   had closed three hours earlier.

   **Sweep the register for rows their own issue already fixed.** A review gate files
   a row, the issue's correction round fixes it inside the commit the gate was
   reading, and nothing re-reads the row afterwards — so promotion, which reads
   neither the bug file nor the diff, mints an issue for work that has shipped. The
   finale already holds the commits, so it does the re-reading: any row whose issue
   committed after the row was filed is checked against that commit and marked
   `verified` where the fix landed, which routes it to promotion's `fixed` exit.
   Three of seventeen issues minted on 2026-08-09 were stale this way, each costing a
   run slot and a hardening pass (register row `seam-h04`; remedy chosen by the human,
   2026-08-10).

   If the finale fails on a usage limit, leave the ledger at
   `finale-judgment`, write the halt block, and revive after reset — never
   downgrade it to save the wait, and never declare the run complete with the
   judgment half unrun.
3. **Promotion — the last phase that resolves findings, and the only door into
   `issues/`.** Spawn one
   `promotion` agent **carrying `model:` set to the `promotion=` value on the
   ledger's `Model map at launch:` line** — it is one of the twelve mapped roles,
   so `model-map-gate.py` refuses a spawn that omits it (ticket 39, ruling 10).
   Its prompt names the issue directory and the claim command
   `python3 ~/.claude/skills/lib/claim_number.py issue <dir> --for "promotion <batch id>"`, one call per
   file: the number is claimed atomically across every worktree, never read off a
   listing, and `number-claim-guard.py` refuses a file under an unclaimed one (ticket
   38 of the pilot-delivery map, rulings 7 and 16). Run it over every register row this run wrote, **plus every row anywhere in
   the register that already reads `verified`**. A row already at
   `verified` exits as `fixed`, before audience is even read, because the run fixed it
   and the fix is in the commit. That exit takes no judgement, so widening the scope
   cannot promote anything wrongly, and it is what sweeps up a `df-NN` row left by a
   direct fix — see "The direct road" in `~/.claude/CLAUDE.md`. Without the sweep those
   rows belong to no run and accumulate for ever (ticket 29 of the pilot-delivery map,
   2026-08-12). Of the rest it promotes on the audience-and-severity
   thresholds, and refuses the others. A promoted row becomes an issue file at
   `Status: needs-harden` with one category role and a link to its bug file. All three
   exits delete the row, so the register's length stays the promotion backlog and
   nothing else.

   **The thresholds live in `~/.claude/agents/promotion.md` and nowhere else.** Both
   skills spawn the one agent, so a run brief that restates a threshold restates a
   figure it cannot keep current. This file and `parallel-hunt/SKILL.md` both carried
   "operator at any severity" for a day after the human set a `medium` floor on `operator`
   (T15-2, 2026-08-09); the 296-276-297 run's brief repeated the stale figure and
   promotion had to overrule its own brief. Name the exits here; read the numbers
   there.

   **`fixed` is reported as a count and never as a refusal** (T15-3, ruled
   2026-08-06). A run that fixes work must not report that work under a word the
   daily brief offers to overturn.

   **The runner never promotes rows itself.** This is the same call as the board in
   step 4, for the same reason: by run end the runner's context is the most expensive
   in the pipeline, and writing issue files is repetitive work that has no business
   in it. The runner spawns, gets two lists back, and appends them to
   `merge-briefing.md`, one line each. `/daily-brief` carries both to the human and they
   hold the veto over either direction.
4. **Tear down what this run seeded outside the repo, then measure the run and
   append its row.** The judgement step above is the last thing that drives the app,
   so anything the launch created outside git — a database workspace row, a sandbox
   tenant — goes first, by the id the ledger itself records. Where the project has a
   teardown script, run it here and let it read the id off the ledger rather than
   taking one by hand: deleting by the marker the run itself wrote is what the
   "delete only rows you marked" rule in `SKILL.md` requires. A teardown that
   refuses is not a stop — journal the refusal, put its printed remedy into the merge
   briefing as an action on the human, and go on to the measurement. Nothing else in
   the finale needs the teardown to have happened.

   Then run

   ```
   python3 ~/.claude/skills/run-issues/run_costs.py --batch <batch-id> \
       --version <cc-version> --note "<what changed since the last run>"
   ```

   Paste its whole output into `merge-briefing.md` under `## What this run cost`. It
   appends one row to `.scratch/workflow-audit/run-costs.md`, which is the table the human
   reads to compare one run against the one before it.

   **`--batch` is this run's batch id, `batch-88624c` and the like.** It is the only
   argument the reading needs. The id names the ledger, the ledger's `Worktree:` line
   names a path, and the path IS the transcript directory, so nothing depends on what
   the worktree is called and `--issues` is counted off the spawns rather than typed.

   **That is why `--run` is no longer the road** (ticket 39 of the pilot-delivery map,
   every-worker-inherits-the-session-model, ruling 12). `--run` matched the run's name
   against the PROJECT DIRECTORY name, which holds only while a worktree is named after
   the run inside it. Twice it was not: the 2026-09-02 and 2026-09-05 rows of
   `run-costs.md` each say the worktree was reused and its name does not match the
   branch, so `--transcript` had to be passed by hand. Run `batch-b5e96d` ran in a
   worktree called `run-issues-414a-99f-286335`. `--run` still works, for a run whose
   ledger is gone.

   Either way the transcript must NAME the run or nothing is read and no row is
   appended. Run `batch-88624c` ran this from the MAIN checkout on 2026-08-31, whose
   slug holds 64 sessions of unrelated work; the old rule took the newest and reported
   1.01 hours for an 8.48-hour run, with a longest step the run never ran, and appended
   it as though it were measured.

   **Every token figure it prints carries its own model, and none of them is added
   across models** (ruling 11, and the human's ruling of 2026-09-06). The `Weighted`,
   `Per issue` and `Orchestrator` cells read `opus 149.7M / fable 0.3M`, so the number
   cannot be read without the model it belongs to. One figure spanning two models would
   need a cross-model multiplier, and a multiplier is a price with the currency taken
   off. **To read a model trial, compare the SAME ROLE across runs** — that is like
   against like and needs no multiplier at all. For money, read `/usage` by hand.

   **Then run these three and paste them too**, in the same section:

   ```
   python3 ~/.claude/skills/run-issues/harness_cost.py --batch <batch-id>
   python3 ~/.claude/skills/run-issues/cache_probe.py --days 2
   python3 ~/.claude/skills/run-issues/estimate_accuracy.py \
       --ledger <run.md> --transcript <the run's main .jsonl>
   ```

   **`estimate_accuracy.py` ends with an `attribution:` line. Read it.** It says how
   many per-issue spawns the transcript held and how many were booked to an issue, and
   the two must match. On run `batch-88624c` the old reader lost 18 of 30 to a regex
   that could not read `issue **201 — title**`; it graded seven issues from a third of
   the run, reported estimates running long when they ran short, and printed no warning.
   An unattributed spawn is now named in the output and exits 2.

   `estimate_accuracy.py` joins the ledger's `Est` column to what each issue
   actually occupied. It exists because nothing did: `run_timings.py` says where
   the clock went per STEP and cannot say whether that was more or less than
   expected. On run `414a-483-286335` the median issue took **0.40** of its
   estimate, spread 0.31x to 1.04x, and a batch scoped at 26.5 hours of issue
   time occupied 13.8. **Read the ratio beside `harness_cost.py` and never
   alone** — 99f reads 1.04x on that run only because a permission prompt sat
   for 146 minutes inside it.

   `cache_probe.py` was the last measurement in this directory wired to nothing.
   The number to read is the **read-to-write ratio**: 61.7 to 1 on run
   `414a-483-286335`, 634M read against 10.28M written. A cache read costs about
   a tenth of a write, so that ratio IS the token bill. It has no target and it
   is not a score — it is a watchdog. **If it ever collapses toward 1, the run's
   input cost has gone up roughly tenfold and nothing else in this pipeline
   would say so.** Its original research question is settled and needs no
   re-asking: yes, a fresh subagent reads a cache it did not write, on 43 of 54
   agents, which is 0.2% of fleet reads.

   It splits what the run lost to the HARNESS rather than to work, into three
   numbers that must never be added up. PROMPTS is a Bash call left pending
   while a human was waited for, and it is the expensive one — 146 minutes on
   run `414a-483-286335`, 15.7 per cent of that run, one call. POLLING is time
   spent sleeping for something the harness announces for free. DENIALS are
   classifier refusals, counted and not timed, because the agent rewords and
   moves on in seconds; that run had five and they cost minutes between them.

   **A PROMPT row is the finding.** It names a command class that has no rule in
   `.claude/settings.json`, and a rule there means it can never be asked again.
   the human asked for this measurement on 2026-08-30 because until then the only
   way to see a lost night was for somebody to go and count afterwards.

   **The `--note` is the only part that needs a person, and it is the part that makes
   the table worth keeping.** Name what changed since the previous row — a skill edit, a
   new hook, a Claude Code version, a different effort tier. A row that says nothing
   changed is still a row; a row with no note is a number nobody can use.

   **What it costs the run: nothing measurable.** Two Python scripts read transcripts
   already on disk. No agent is spawned, no database is read, and the only write is one
   appended line.

   **It can never halt a run.** Every failure inside it is caught and printed as text,
   and it exits 0 even when it can read nothing at all. A cell reading `not read` is a
   missing figure, not a fault: record it and carry on. Do not retry it, do not
   investigate it, and never write a HALT BLOCK for it.

   Why this exists, measured on 2026-08-30: `orchestrator_cost.py` already ran at launch
   and read the LAST WEEK, so a run stated what other runs cost and never its own.
   `run_timings.py`, built on 2026-08-26 when a fourteen-hour run could not say which step
   ate the clock, was named in no skill file at all and had only ever been run by hand.
   Both readings existed and neither was wired to anything.

   **`run_costs.py` also prints two tables ticket 39 sitting 3 added, and they are the
   ones a model trial is read from** (ruling 15). `What each role ran on, per role and
   per model` gives one line per role and model pair — spawns, tokens by kind, weighted
   tokens and hours. `One row per subagent` gives every spawn: role, model, effort,
   tokens by kind, rows and minutes. Paste both here. **The per-role table also goes
   into the briefing as its own section**, by the command below, and the duplication is
   deliberate for the same reason the one-screen block duplicates the board: this
   section is a cost reading the human opens when they are asking about cost, and that section
   is the trial they open when they are asking which model to run next.

   **Then run this one, and paste its whole output as its own section of
   `merge-briefing.md`:**

   ```
   python3 ~/.claude/skills/run-issues/run_quality.py --batch <batch-id>
   ```

   It prints `## What each role ran on, and whether the trial holds` complete, heading
   and all — the trial verdict, the per-role table, and the three inside-run quality
   figures per issue. Paste it whole; write none of it yourself (ticket 39 of the
   pilot-delivery map, every-worker-inherits-the-session-model, sitting 4, deliverable 4
   and rulings 13, 15, 21.3 and 22).

   **The per-role table is read from the TRANSCRIPTS, never from the ledger** (ruling
   21.3). The ledger is the thing under test: it records the map the launch line
   resolved, so a table built from it would agree with the map by construction and
   could never fail. Every figure in it comes from each subagent's own transcript rows.

   **The verdict has three states and `holds` is only one of them.** `VOID` means at
   least one mapped spawn ran on something other than what the ledger asked for, and
   `~/.claude/hooks/model-landed-check.py` wrote a `**MISMATCH**` line saying which.
   **A void trial halts nothing, unmerges nothing and reopens no issue** (ruling 22):
   the work is still good work, and the only thing void is the comparison. `not
   measured` means the journal holds no landed line at all — a run from before that
   hook, or one whose hook never fired — and it must never be read as a pass. Run
   `batch-b5e96d` reads `not measured` for exactly that reason, measured 2026-09-06.

   **The per-issue figures PARSE PROSE, and the limit is stated rather than hidden.**
   Only `attempt N` and `criteria reset` are markers; a gate's verdict and a strike are
   sentences in the Notes cell. Measured 2026-09-06 over the sixteen ledgers in
   `.scratch/example-feature` that hold a status table, 143 rows: it grades 141 and
   prints `unread` on 2, both of which genuinely state no verdict. Reaching that took
   seven dialects two review passes found, in twelve ledgers the first reading had
   never opened. **A row it cannot read prints `unread` and
   never a pass**, so a hole is visible rather than silent. `test_run_quality.py`
   carries the whole corpus as a regression net.

   **The strike column is derived and says so.** `SKILL.md` step 5's prose-deletion
   road and a runner-error annulment both cancel a strike in prose and write no
   marker, so the reader counts rounds rejected since the last criteria reset, marks
   any row whose own words disagree with a `*`, and prints both rather than choosing.
   On run `batch-b5e96d` fourteen of fifteen rows agree with their own prose and issue
   530 is the one that does not.

   **It can never halt the finale.** Every road exits 0 and prints what it could not
   read, the same rule the cost readings above carry.

   **Then write `## The run in one screen` at the very top of the briefing, above
   every other section.** It is written this late because it is the first moment
   every figure in it exists. The rail block below it follows, and the board renders
   only after both are written and `check_run_rail.py` has passed.

   Six things are read after a run. On run `batch-88624c` three of them sat past line
   1700 of a 1963-line file and the human found none of them; the second time that happened
   it cost four cost measurements they had commissioned the day before. The block puts all
   six above line 40.

   ```
   ## The run in one screen

   Run `batch-88624c`, 10 issues, 8.48 h. Nothing is merged and nothing is deployed.

   | What                | Count | Detail lives at             |
   |---------------------|-------|-----------------------------|
   | Shipped, unmerged   |     8 | ## What shipped             |
   | Did NOT ship        |     2 | ## Skipped or blocked       |
   | Migrations minted   |     5 | ## Migrations minted        |
   | Issues minted       |     3 | ## Promotion                |
   | Register rows left  |     0 | ## Promotion                |
   | Waiting on you      |     6 | ## Actions waiting on the human |
   | Forks to decide     |     4 | ## Decide                   |
   | Wall clock, hours   |  8.48 | ## What this run cost       |
   | Idle, per cent      |    17 | ## What this run cost       |

   Shipped:      201, 224, 224b, 224c, 339, 153, 225, 269
   Did not ship: 160, 160b   - both wait on 161, which is unbuilt
   Minted:       500, 501, 502
   Register:     45 rows resolved - 3 promoted, 5 fixed, 37 refused. None left.
   ```

   **It adds no new measurement.** Every value comes from a section the briefing
   already writes, and each row names the HEADING that holds the detail rather than a
   line number, because that file grew from 1830 lines to 1963 in a single day. A
   finale that has to compute something to fill this block is the wrong build, and
   that cost would land on every run.

   **Every comparable figure is a table row, the two cost ones included.** The board
   panel copies this table and `check_run_picture.py` compares the two, and it can
   only compare what the table holds.

   **A run that shipped nothing writes an honest block, never a short one.** Zero is a
   row reading 0 and a sentence saying nothing shipped. A blank panel reads as a render
   that failed.

   **`/daily-brief` reads this block and never the board**, so the block must never be
   thinned on the grounds that the panel shows the same thing. The duplication is
   deliberate: the two are read at different moments, and a brief may not run before
   the human merges.

   **The `Shipped:` line is a required field of this block, and `check_run_rail.py`
   below exits 2 without it.** It is the only place the shipped list is read from.
   Measured across five real briefings on 2026-09-03, `## What shipped` is not stable in
   name or in shape: `batch-45c8b1` headed it `## What shipped, per issue` and listed
   sixteen inside one prose sentence, `batch-375cbf` used `### 161 —` sub-headings,
   `batch-88624c` bold lines. One line of comma-separated ids is what a reader can read.
   A run that shipped nothing writes `Shipped:      none`.

   **Then write `## The run on the rail` directly below the whole of that block**, after
   its last line and before every other `## ` heading. Never between the one-screen
   heading and its table: `check_run_picture.py` ends the one-screen block at the next
   `## `, so a rail heading above the table leaves it zero figures and it exits 2 on
   `no-block-figures` on every run. This is still step 4, while the ledger reads
   `finale-promotion`. No ledger stage is added for it.

   The block carries the run's headline, the lit stages, and one row per shipped issue:

   ```
   ## The run on the rail

   Headline: The database now refuses a viewer's direct write on every table this batch
   touched. The money road is still open.
   Lit: workspace, quotation, needs-you, zoho

   | Issue | Stage     | Kind  | Sentence                                      |
   |-------|-----------|-------|-----------------------------------------------|
   | 517   | workspace | new   | Admin adds a person and changes a seat        |
   | 517a  | workspace | guard | Database keeps the last admin in place        |
   | 516   | needs-you | new   | Admin is told a customer waits to be verified |
   | 503   | floor     | fix   | Citation checker refuses without a clean bill |
   ```

   **This is sixteen judgements a run, and it is not free.** Ticket 34 priced it: the
   finale decides a stage, a kind and a sentence for every shipped issue, plus one
   headline, and the sentence is the real cost. The judgement sits here because the
   board renderer may have none (step 5), and by this point the finale has read every
   issue file, every diff and every gate verdict.

   - **Headline** is required, and the story starts on the `Headline:` line or on
     the line under it. A run with no story writes the sentence saying so. A run that shipped nothing writes an honest rail: the headline
     says nothing shipped, `Lit: none`, and the table has its header row and no rows.
     Never a missing block, which reads as a finale that crashed.
   - **Issue** is every id on the `Shipped:` line, one row each, no more and no fewer.
   - **Stage** is one key from `docs/agents/run-picture-stages.md` in the repository the
     run is on, and the finale judges it from what the change is about. The verify gate's
     `Drove:` list and the issue's title are evidence, never the decision: the gate sweeps
     every route the diff touches, so on `batch-45c8b1` issue 488's list names nine
     routes across five stages and issue 486's names none. `floor` means an issue no user
     can see the effect of, such as agent tooling and guards on the build itself. It does
     not mean the gate drove no route: the four migrations 486 to 489 drove none and
     changed what a viewer can do on every screen, so they sit on the rail. A band member
     (issue 555's `### Bands` table) takes a stage inside its band's span, never `floor`.
   - **Kind** is one of `new`, `fix`, `guard`, `harness`, one per shipped issue. The
     `harness` kind and the `floor` stage are two judgements: on that run 485b read
     `catalogue | harness` and 503 read `floor | fix`. Never derive one from the other.
   - **Sentence** is the issue file's `Sentence:` line where it has one, copied. Where it
     has none, compress the title into a sentence with a subject and a verb. The fallback
     is the normal case until issue 551's field has been on files for several runs: on
     2026-09-04 the project it was written for held 585 issue files and none carried the
     line. `59 characters or fewer`; the check refuses at 60.
   - **Lit** is the stages the board draws with a bordered name: every stage holding at
     least one shipped card. A band chip lights nothing, so on `batch-45c8b1` `catalogue`
     was unlit while 485 shipped there. The finale states the set; the renderer never
     works it out.

   **Then two more tables, under the shipped one, inside the same block.** The rail drew
   what the run did. These draw what it left: an issue it named and did not close, and a
   question waiting on the human. Each is found by its own header row, so the three are
   read apart and a minted row never trips the shipped rule.

   ```
   ### Minted and left open

   | Issue | Stage     | Sentence                                |
   |-------|-----------|-----------------------------------------|
   | 522   | quotation | A failed price read shows as 'no price' |
   | 524   | floor     | A gate writes a row nothing later reads |

   ### Forks waiting on you

   | Fork | Stage     | Question                                          |
   |------|-----------|---------------------------------------------------|
   | F1   | workspace | Tell an admin the email belongs to another space? |
   | F4   | floor     | Refuse an untracked paste file?                   |
   ```

   - **A minted row is drawn as a dashed card, and it is a hole rather than a plan.** The
     rows are the `Minted:` line and the `Did not ship:` line together, every id on each,
     no more and no fewer. Both halves are wanted: promotion mints an issue from a
     register row, and a run also leaves an issue open on purpose — a run whose promotion
     minted nothing can still owe a dashed card. The `Sentence:` rule above is the same
     one, `59 characters or fewer`, and the wording says the work is not there rather
     than that somebody has started it.
   - **A fork row is drawn as an amber card carrying its question.** One row per fork,
     and the count must equal the one-screen table's `Forks to decide`. The stage is the
     question's own: a question about the product takes its stage, a question about the
     harness takes `floor`.
   - **The `Question` cell is a compression you write, never a `## Decide` heading
     copied.** Measured 2026-09-05 over the five runs the picture draws: only one writes
     its Decide items as questions at all, and five of those six headings run 61 to 89
     characters against a card that holds 60. The other four runs write statements, noun
     phrases, bold paragraphs or bare bullets. So write the short question here,
     `59 characters or fewer`, and leave the fork's own item under `## Decide` exactly as
     it stands — that is the version `/daily-brief` reads, and the card adds no fact it
     does not carry.
   - **A fork key is unique across the whole briefing.** Number them `F1`, `F2` and
     onward in one sequence, in the order you write them, whatever section holds each
     fork. Every one of the five drawn runs carries TWO `## Decide` headings and each
     numbers its own items from 1, so an item number alone is not a key: two amber cards
     would collide and the board's guard could not tell which row a card came from.
   - **The register is drawn nowhere, and that is deliberate.** Every register row ends
     as one of four things — promoted, which is now a dashed row; fixed, which is already
     inside a shipped card; refused; or dropped below the operator floor, which is a
     refusal — and a fifth road never reaches promotion at all. None of the five gets a
     card. The only register fact anywhere on the board is the one-screen table's
     `Register rows left` row and its `Register:` line, and drawing rows a second time
     would put one fact in two places.
   - **The one-screen counts do not move.** `Forks to decide`, `Issues minted` and
     `Register rows left` are what `/daily-brief` reads. These two tables sit below them
     and change none of them. `Forks to decide` still counts forks WRITTEN, never forks
     drawn.
   - **A run with neither omits both headings rather than printing an empty table**, and
     the rail is shipped cards only. Nothing forces this: an empty table with its header
     row reads the same to the guard, which grades rows and not headings.

   **Then the bands, where the run has one.** A band is one subject that changed
   across several stages, drawn as a strip crossing the columns it touches with its
   issues as chips inside it. On `batch-45c8b1` it is the viewer losing the pen across
   all eight columns, and it is that run's whole story in drawn form. Without it those
   runs draw as scattered cards that share a colour and nothing else.

   ```
   ### Bands

   | Band | Stages               | Kind  | Issues                           | Caption                                      | Seats                          |
   |------|----------------------|-------|----------------------------------|----------------------------------------------|--------------------------------|
   | B1   | workspace..catalogue | guard | 486 487 488 489 485 485b 519 509 | Viewer, on every screen, can no longer write | admin ok, member ok, viewer no |

   ### Band chips

   | Band | Issue | Text                  |
   |------|-------|-----------------------|
   | B1   | 486   | customers             |
   | B1   | 509   | money road still open |
   ```

   - **A run may state no bands, and that is the normal answer.** Two of the five runs
     the picture draws have none. State a band where the run has one subject that
     genuinely crossed several stages, and state none otherwise: a picture that must
     always find a subject will invent one, and an invented subject on a merge briefing
     is worse than no band at all. A run with no band omits both headings.
   - **The floor is two issues across two spanned columns, and it is provisional.** It
     rests on five measured runs and no counter-example, so the first run that draws a
     silly band is answered by changing that number here rather than by re-arguing the
     shape. Below either figure the thing is a card, not a band. **The floor is a shape
     rule and never an invention guard**: nothing derives a band, so a finale minded to
     invent one names three issues across three stages as easily as two across two. What
     refuses invention is the paragraph above, plus the membership rule below.
   - **A band REPLACES the cards for its members.** Its issues are drawn once, as chips
     inside the band, and never also as cards on their own stages. Measured over all five
     drawn runs: the card set and the chip set are disjoint every time and their union is
     the run's shipped count — nine cards plus seven chips for `batch-45c8b1`'s sixteen.
     That raises the cost of a wrong row rather than lowering it, because an issue
     swallowed by a band that should not hold it vanishes from its own stage entirely.
   - **Every issue a band names has a row elsewhere in the block**, in the shipped table
     or in `### Minted and left open`. Both halves are wanted: a band may carry an issue
     the run named in its headline and left open, drawn as a dashed chip. An issue in two
     band rows is refused, and so is a fork key: a fork waits on the human and is not a
     subject that changed.
   - **Stages** is `first..last` over the rail's columns, a contiguous range in the order
     the stage vocabulary sets. `floor` is never spannable, because the floor row is
     drawn beneath every band. Each member's own stage sits inside its band's span.
   - **Kind** is one of the same four a card takes and gives the band its colour.
     **Caption** is the band's story in one line or two, and it is judgement, exactly
     like a sentence.
   - **Seats** carries three marks in the fixed order `admin`, `member`, `viewer`, each
     one of `ok`, `no` or `dash`, and an empty cell draws no pills. That one line carries
     everything the old seat grid said. **Whether a band is about seats stays your
     judgement**, like the caption: the cell is what the drawing reads.
   - **Every member has a row under `### Band chips` holding its own few words.** A chip
     draws bare without one, and bare numbers are not the picture. **Write these short**:
     the space a chip has falls out of its band's span and its chip count, and across the
     five drawn bands that runs from 12.8 characters a line to 23.1. `draw_run_rail.py`
     computes each band's own budget and refuses a line over it.

   **Then run the guard from the repository root, and do not go on to the board while
   it refuses:**

   ```
   python3 ~/.claude/skills/run-issues/check_run_rail.py \
       --briefing .scratch/<feature>/runs/<batch-id>/merge-briefing.md \
       --stages docs/agents/run-picture-stages.md
   ```

   It refuses a stage or `Lit:` key outside the vocabulary, a kind outside the four, a
   row with fewer than four cells, a sentence or a question of 60 characters or more, a
   shipped issue with no row or a row for an issue that did not ship, an id on the
   `Minted:` or `Did not ship:` line with no dashed row or a dashed row neither line
   names, a fork row count that disagrees with `Forks to decide`, a repeated fork key, a
   band below the floor, a `Stages` cell that is not a contiguous range, a band naming an
   issue with no row anywhere in the block, an issue in two bands, a `Seats` cell that is
   not the three marks in order, a band member with no chip text, a missing headline, a
   missing `Lit:` line, and a rail placed anywhere but directly below the whole one-screen block,
   its `Shipped:` and sibling field lines included. Exit 2 means it could grade nothing:
   no one-screen block, no rail, no `Shipped:` line, or a vocabulary file that exists and
   holds no table. It prints every refusal, not the first. A relative `--stages` path is
   tried from the git top level too, so the command also works from the run's own directory. **It grades keys, counts and lengths and nothing else.** Whether a sentence is
   true or 516 belongs on `needs-you` passes unread, so never cite it as cover for the
   judgement. Where the repository has no `docs/agents/run-picture-stages.md` it says so,
   skips the stage rule and grades the rest, which is that file's own rule 4.

5. **Regenerate the action board** — `~/Documents/run-boards/<batch-id>.html`, the
   one-page human view of `merge-briefing.md`. **Every board lives in one folder
   outside every repository, named by batch id**: one place the human can walk later,
   and no run ever overwrites another run's board. Never write a board into
   `.scratch/`. Live actions only, grouped by when, one line of
   what and one of why each, ticks persisted in localStorage, **and the run panel
   described below**. Keep the existing styling; send it with SendUserFile. **A fresh
   subagent renders it, spawned with `model: "opus"` named explicitly on the Agent
   call** — from `merge-briefing.md` plus the old board, never the runner itself, whose
   context is at its most expensive by run end, and the old board's bytes never enter
   the runner.
   Naming the model is not optional and "cheap" is not a model: an unnamed spawn
   inherits whatever the session runs, and this step converts one markdown file into
   HTML on the largest input in the pipeline (283 KB, measured
   2026-08-06). `merge-briefing.md` stays the source of truth,
   and `/daily-brief` reads that file, never the board.

   **The pin is `opus`: the top reasoning tier below the most expensive one, and it
   does not go lower.** The saving is not what decides it: on one measured run the render cost 0.30M
   weighted tokens against the run's 149.70M. The tier order in this pack ranks review
   authority, never price, and this render is the last thing that touches the artefact
   the human opens first.

   **This is the one spawn the model map does not reach, and the two do not conflict.**
   `SKILL.md`'s rule was "never pass a `model:` value" until 2026-09-05, when the model
   map reversed it: every one of the twelve loop roles now takes its model from the
   ledger's `Model map at launch:` line. The board renderer is not one of the twelve.
   It has no agent file and no map row, so this paragraph is what governs it. (Scoped
   by the human on 2026-08-22, answering C7 of the skills audit; rewritten 2026-09-05
   when the rule it cited was reversed.)

   **The panel goes at the top, headed "The run in one screen".** the human named this
   surface themselves: the board is the only artefact a run produces that renders, and it
   is the one they open after every run. It carries the counts as figures, one table of
   issues by state, one table of the register and cost numbers, and a drawn chain where
   the run has a blocked chain. Where it has none, no chain is drawn. Zero shipped reads
   as a red figure and a sentence saying nothing shipped, never as a blank panel.

   **Above the panel goes the rail, drawn from `## The run on the rail` by a script.**
   It is the picture the human opens first: eight columns left to right, one card per
   shipped issue on the stage its rail row names, a dashed card under it for every issue
   the run left open and an amber card for every question waiting on the human, a band
   across the columns any one subject crossed, a floor row beneath them, and the run's
   headline across the top. **The renderer draws bands, it never finds them**: it reads
   the `### Bands` table and draws what it states, the same rule the cards obey.
   **The script is the only road to it.** Run it from the repository root and paste
   what it prints into the board:

   ```
   python3 ~/.claude/skills/run-issues/draw_run_rail.py \
       --briefing .scratch/<feature>/runs/<batch-id>/merge-briefing.md \
       --stages docs/agents/run-picture-stages.md
   ```

   It prints four blocks, each with a comment saying where it goes: ten CSS tokens for
   `:root`, the same ten for the `@media (prefers-color-scheme: dark)` block, the
   rail's own CSS, and the `<svg>`. The rail goes inside `<div class="rail-bleed">`,
   directly above the `## The run in one screen` panel, and that div is a direct child of
   `<body>`.

   **The rail takes the WINDOW's width and the prose keeps its reading column.** The CSS
   block does that by itself: it lifts the 720-pixel column off `body` and puts a
   680-pixel one on each of body's other children, which is the same width the prose had
   before. So `.rail-bleed` must be a child of `body` and never of a wrapper, or it
   inherits the column and the widening is lost. The rail draws at its natural 1040
   units, centred where the window has room and scrolling inside its own container where
   it does not; on a window 1080 pixels or wider nothing scrolls at all. The human ruled
   scroll rather than shrink on 2026-09-04, after being shown that scaling the rail to
   fit draws the card text at 6.5 CSS pixels, and widened it to the window on 2026-09-05.

   **Why a script and not your own SVG**, ruled by the human on 2026-09-04: the shape is
   computed geometry carrying two assertions, and a card whose sentence will not fit
   stops the finale here with the issue named, rather than reaching the human as clipped
   text. Prose cannot assert. `check_run_picture.py` below measures the drawn lines and
   refuses a board that came from anywhere else. Exit 1 from the script means a sentence
   is too long: shorten it in the rail block, re-run step 4's guard, and draw again. The
   render is safe to repeat.

   **The rail transcribes too. It never works out a stage, a kind or a lit column.**
   Every card's stage, kind and sentence is copied from the row step 4 wrote, and the
   bordered column heads are the block's own `Lit:` line. The script reads that block
   and nothing else: no diff, no issue file, no guess about which screen a change
   touched. That judgement was made one step earlier, where the whole run was in view.

   Every figure carries `data-figure` on the element whose own text is the number, and
   the key is the block's row label slugged — `Shipped, unmerged` becomes
   `shipped-unmerged`:

   ```
   <div class="stat good"><div class="n" data-figure="shipped-unmerged">8</div>
     <div class="l">Shipped</div></div>
   ```

   **The panel transcribes. It never counts, and neither does the rail.** Every figure is copied out of the
   briefing's `## The run in one screen` block, which is the single place a figure is
   derived. The renderer used to read all 1963 lines, count the bold issue headings
   under `## What shipped`, notice which of them also sat under `## Skipped or blocked`
   and subtract. That is arithmetic, and arithmetic in a render is judgement. The
   diagram draws the chain the block states in words, and draws nothing where the block
   states none.

   **Then run the guard, and do not ship a board it refuses:**

   ```
   python3 ~/.claude/skills/run-issues/check_run_picture.py \
       --briefing .scratch/<feature>/runs/<batch-id>/merge-briefing.md \
       --board ~/Documents/run-boards/<batch-id>.html \
       --stages docs/agents/run-picture-stages.md
   ```

   It reads the figures from both files and compares them, and it does the same for the
   rail's cards: every `data-card` must carry the stage and the kind its rail row holds,
   every shipped row must be drawn, and every drawn line must fit its box. A
   disagreement exits 1 and the finale stops; exit 2 means it could read neither the
   block nor a panel, which is also a stop. Each refusal names the issue, the attribute
   and the row it disagreed with, so the repair is one edit and one re-render.

   **The cards obey the OPPOSITE rule from the figures, and both are wanted.** The board
   may carry fewer figures than the block, because the panel is a summary and a figure
   it leaves out is a choice. The rail is not a summary: a row with no card is an issue
   that vanished from the picture, and it is refused.

   **This is the only part of the change that catches a false number at any model.** It
   catches numbers, keys and widths alone: a wrong sentence on a card, like a wrong
   sentence in a `why` line, passes, so never cite this guard as cover for the prose.
   Where the repository has no `docs/agents/run-picture-stages.md` it says so, skips the
   stage-key rule and grades the rest, which is that file's own rule 4.

   **Why Fable, and why the model line had to be settled here.** The old sentence
   justifying Haiku read "there is no judgement in the render". A panel carrying
   derived counts and a conditional diagram breaks that premise, so the licence would
   have expired the moment the panel shipped. The rule above restores it: with the
   transcription rule in force the render has no judgement in it again, and the guard
   refuses a board that finds some.

   **The pin is `opus`, ruled by the human on 2026-09-06.** It was `haiku`, then `fable`
   when the board grew a run panel. His words: Fable is not needed for that simple job.

   Three facts settle it, and only one of them is about price.

   **Cost is not the constraint.** The 2026-08-06 figure that chose Haiku cites a 283 KB
   input; measured 2026-09-01, the render reads `merge-briefing.md` at 125 KB plus the
   old board at 12.5 KB, roughly 35,000 tokens in and 3,000 out. Measured again on run
   `batch-b5e96d`, 2026-09-06, the render cost 0.30M weighted tokens in 0.08 h against
   that run's 149.70M — two tenths of one per cent. One redo costs more than any model
   saving here, which is why the pin is not dropped below Opus.

   **Effort cannot be named on an Agent spawn.** The tool takes a model and no effort
   argument, and this spawn has no agent file to carry frontmatter — the human refused
   minting one on 2026-08-22. So `opus medium` is unbuildable and effort inherits the
   session: the same run measured this render at effort `high`, which was the session's.
   Anyone asking for a model at an effort here is asking for half of what they said.

   **The tier order ranks review authority, not price.** Ruling 14 of ticket 39 fixed
   `haiku < sonnet < opus < fable` so that no adversarial gate sits below the worker it
   checks. Read as a price list it made this pin name the most expensive model for the
   cheapest job in the pipeline, which is the contradiction `q-t39-s2-1` raised on
   2026-09-05 and this ruling closes. The order is unchanged; the pin moved.

   **Why not lower than Opus.** The evidence for Fable on this class of work is
   `.scratch/workflow-audit/citation-recheck-fable.md`, taken 2026-08-16: read a source,
   report it faithfully, invent nothing. Of 107 citations it returned 95 correct, 2 off
   by a line number, and 6 mismatches of which 4 were drift that happened after the
   source was written. Two substantive errors in 107. **State both limits wherever this
   is cited: it measured a checking task producing a report rather than an HTML render,
   and it is one reading rather than a trend.** Without the transcription rule and the
   guard the render is arithmetic, which no tier below Opus has been measured on here.

6. **Recommend follow-ups; start none.** One exception is mandatory:
   - **The post-deploy smoke walk**, owned by `/daily-brief`. The run ends at
     `awaiting-merge` and the brief carries it to the human with the branch head SHA
     they are approving. When they write `merge`, that session merges, rewrites the
     `unmerged` statuses, deploys, and drives a READ-ONLY walk of the **deployed**
     site on real data before the human walk: every list page and its filters and
     search, every detail page, the send and receive surfaces as far as read-only
     allows. Read-only means no permission risk, so there is no reason to skip it.
     **The walk fires on ANY merge of a run branch, whoever merged** — a merge
     outside the `/daily-brief` path does not skip it; the next brief session
     runs it and reports what it found.
   - Recommended after it: a `/parallel-hunt` round on the live system. It hunts
     the seams between issues and against live external systems — the class of bug
     per-issue gates cannot see. Its own promotion phase decides which of its
     findings become the next run's issues.
   - Only if the finale's findings are structural: an architecture-improvement
     session on a clean tree.
