# The finale, in full

The runner reads this file once a run, when it writes `finale-mechanical` into
the ledger after the last issue. That write is the trigger, and `SKILL.md` holds
it. Nothing here is resident in `SKILL.md`, because a run pays for that file on
every turn and pays for this one once.

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
jump, a reversal and a ledger with no state; its docstring holds the three runs that
earned it. Promotion is safe to re-enter — it deletes each row as it resolves it — and
the board render is safe to repeat:

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
   a live harness rather than assuming one. `preview_stop` is permitted in an
   unattended run (measured 2026-09-02 on `batch-45c8b1`): call it when the server
   needs restarting, and record what the call answered. Where the judgment step
   had no live harness, the briefing says so; the gap is silent otherwise. (R3,
   adopted by the human 2026-08-18; `decisions.md` holds the finale it happened to.)

   Preview deploy is **skipped in this repo** by standing decision — see the repo
   CLAUDE.md. Say so in the briefing; never work around it; never re-litigate it.

   **When you drive a server action live to prove it dispatches, pass an argument
   that CANNOT write.** Read the action's first validation branch and pass
   something that reaches it. The refusal sentence proves dispatch exactly as well
   as a success does, and it leaves no row behind. Never pass an argument that
   would succeed: the classifier refuses the service-role delete that would tidy
   up, correctly, so the row becomes a numbered action on the human. (Adopted by the human
   2026-08-30; `decisions.md` holds the probe that wrote.)

   **Two guards run here, and a refusal from either stops the finale** (the human,
   2026-08-25).

   ```
   python3 ~/.claude/skills/run-issues/check_commit_order.py --ledger <run.md> --repo .
   python3 ~/.claude/skills/run-issues/check_paste_file.py <every paste file this run wrote>
   ```

   **Run the suite, the build and the citation pass under the step wrapper** (ticket
   37 of the pilot-delivery map, ruling 19). It stamps start, end and exit code into
   `runs/<batch-id>/steps.jsonl` and passes the command's own exit code straight
   through, so a refusal still stops the finale exactly where it stopped before:

   ```
   python3 ~/.claude/skills/run-issues/run_step.py --batch <batch-id> --kind suite --label "full suite" -- <the suite command>
   python3 ~/.claude/skills/run-issues/run_step.py --batch <batch-id> --kind build --label "cold-cache build" -- <the build command>
   python3 ~/.claude/skills/run-issues/run_step.py --batch <batch-id> --kind citation --label "citation pass" -- <the citation command>
   ```

   The five kinds are `citation`, `suite`, `build`, `board` and `cost`, and a sixth
   spelling is REFUSED before the command runs, because a step stamped under a kind
   nothing reads is left out of the longest-step-per-kind figure in silence.

   **You never write a clock yourself** (ticket 36, ruling 3). That rule is the whole
   reason this is a wrapper: a runner asked to record when a step started and ended
   writes one time from the other, so the two agree by construction and the figure
   measures nothing. It is the same fault rule 9 had, which `check_commit_order.py`
   replaced for the same reason.

   **If the wrapper cannot stamp, it says `NOT stamped` and the command still
   runs**; it can never be the reason a step fails. Its docstring holds why.

   **`check_commit_order.py` prints two numbers and you read both**: how many
   status rows it READ, and how many of those carried a correction round. Its
   `ok` on nine rows and its `ok` on nothing are different sentences, and it
   exits 2 rather than passing when it can read no row at all. It REPLACES rule
   9's commit-time comparison in `SKILL.md`, which agreed by construction; this
   compares the git author date against the correction round the row says the
   commit carries. Its docstring holds the rows it refuses.

   **`check_paste_file.py` refuses a paste file git does not know, on exit 3.**
   An untracked paste file is not in the branch, so the merge cannot carry it and
   the deploy goes out with the migration unapplied. **Exit 3 is not exit 1 and
   wants a different repair**: `git add` and a commit, not a comment marker. It
   outranks a content refusal. **Exit 2 here means the question could not be
   asked** — no working tree, or no git — and is not a verdict on the file.
   Tracked means the index holds it: a file added but not yet committed passes,
   deliberately, because the finale writes and commits paste files in the same
   round.

   It also refuses a pilot paste file whose confirmation query is commented out:
   pasted as written, such a query returns no rows, no error and no output, which
   reads exactly like a clean result. **A refusal here is repaired by deleting the
   comment marker AND running the query against QA before the briefing ships
   it.** The script cannot tell whether anybody ran it; its docstring holds the
   two runs behind both refusals.
2. **Judgment.** Spawn `run-issues-finale`. Its verdicts plus `merge-briefing.md`
   become the merge briefing.

   **The one-screen block that opens the briefing is written at step 4, not here.**
   It carries the wall clock, which does not exist until the measurement runs.

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
   lift. (Adopted by the human 2026-08-10; `decisions.md` holds the migration that
   had to lift a measured ceiling and the model header that came of it.)

   **A published checksum expires the moment the file moves.** A correction
   round re-stamps every checksum a gate published for a file it touched, and
   the finale re-runs any that remain before the briefing closes. Anchor diff
   commands to `main...HEAD`, never the working tree — a worktree diff prints
   nothing once the work is committed, and an empty print cannot distinguish
   "fine" from "the fix was reverted and committed" (decisions.md).

   **Main moved while you worked. Read it before you write a question.** The run
   branches from a worktree cut hours or days earlier, so the human's rulings since the
   cut are invisible to every agent in the pipeline. The finale diffs the merge base
   against main's current tip and reads every commit touching an issue in scope.
   Anything he already answered leaves the briefing, and the briefing says he
   answered it. (Adopted 2026-08-10; `decisions.md` holds the near miss.)

   **Sweep the register for rows their own issue already fixed.** A review gate files
   a row, the issue's correction round fixes it inside the commit the gate was
   reading, and nothing re-reads the row afterwards — so promotion, which reads
   neither the bug file nor the diff, mints an issue for work that has shipped. The
   finale already holds the commits, so it does the re-reading: any row whose issue
   committed after the row was filed is checked against that commit and marked
   `verified` where the fix landed, which routes it to promotion's `fixed` exit
   (register row `seam-h04`; remedy chosen by the human, 2026-08-10).

   **Then read the sweep back over the whole run, and a non-zero exit stops the finale
   BEFORE promotion** (ticket 36, ruling 12). Every row this run owns must be one
   somebody decided: a status the machine knows, and a note saying why it stands where
   it does. A row left `open` WITH ITS REASON passes and that is deliberate; a row
   saying nothing does not, because promotion reads the status cell and would mint an
   issue file for work nobody has judged.

   ```
   python3 ~/.claude/skills/run-issues/check_register_status.py <register> --sweep <batch-id>
   ```

   Repair what it names and run it again. It is not a halt and it never waits for
   the human: exit 1 lists every offending row and the repair is the runner's, now.

   If the finale fails on a usage limit, leave the ledger at `finale-judgment`,
   write the halt block, and revive after reset — never downgrade it to save the
   wait, and never declare the run complete with the judgment half unrun.
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
   figure it cannot keep current; `decisions.md` holds the day both files carried a
   stale one. Name the exits here; read the numbers there.

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
   python3 ~/.claude/skills/run-issues/run_step.py --batch <batch-id> --kind cost --label "run_costs" -- \
       python3 ~/.claude/skills/run-issues/run_costs.py --batch <batch-id> \
       --note "<what changed since the last line, at most 160 characters>"
   ```

   Paste its whole output into `merge-briefing.md` under `## What this run cost`.

   **It appends one JSON line to `.scratch/workflow-audit/runs.jsonl` and regenerates
   `.scratch/workflow-audit/run-costs.md` from it** (ticket 37 of the pilot-delivery
   map, ruling 2). The view keeps its name, so every citation of it still reads, and
   it is the page the human opens. Never edit that page: a hook refuses the write and
   names this road, because a row typed there is gone at the next finale. To correct
   a figure, edit the one JSON line and say why in the commit message.

   **A second line for a batch id already present is REFUSED** (ruling 4, closing
   ticket 36's fault 9). The refusal is printed and the finale carries on; it never
   halts a run.

   **Compare a line against the previous line of the same KIND** (ruling 12), never
   the line above it. A hunt writes into the same file with `--kind hunt`.

   **It now writes ruling 6's four inside-run counts, and a second file beside the
   first** (ticket 37 sitting 3). **Do not type a figure into any of them**; every
   one is measured, and a typed count is the fault that put `claude-opus-5` in a
   version cell.

   **`.scratch/workflow-audit/issues.jsonl` gets one line per issue** (ruling 17):
   the estimate midpoint, span, agent minutes, attempts, correction rounds, strikes,
   escalation, both gate verdicts, and ruling 20's five kind facts. A second write
   for a batch already present is refused, for ruling 4's reason. A refusal there
   costs the per-issue population of ONE run and halts nothing.

   **A null is not a zero.** A run with no strikes is a fact; a run whose strikes were
   never read is not, and they must never read alike. Anything the script could not
   measure reads `not measured` on the page.

   **Do NOT pass `--version`.** The script measures it with `claude --version`
   (ticket 37, ruling 10); a value that is not a version is refused outright, so
   typing one costs the run its whole cost record rather than one wrong cell.

   **`--batch` is this run's batch id, `batch-88624c` and the like.** It is the only
   argument the reading needs: the id names the ledger, the ledger's `Worktree:` line
   names a path, and the path IS the transcript directory, so `--issues` is counted
   off the spawns rather than typed. **`--run` is no longer the road** (ticket 39,
   ruling 12): it matched the run's name against the PROJECT DIRECTORY name, which
   holds only while a worktree is named after the run inside it, and twice the
   worktree was reused and its name does not match the branch. `--run` still works
   for a run whose ledger is gone. Either way the transcript must NAME the run or
   nothing is read and no row is appended; where it read nothing, pass
   `--transcript <the run's main .jsonl>` by hand. The docstring holds the run
   that read a foreign transcript.

   **Every token figure it prints carries its own model, and none of them is added
   across models** (ruling 11, and the human's ruling of 2026-09-06). The `Weighted`,
   `Per issue` and `Orchestrator` cells read `opus 149.7M / fable 0.3M`, so the number
   cannot be read without the model it belongs to. One figure spanning two models would
   need a cross-model multiplier, and a multiplier is a price with the currency taken
   off. **To read a model trial, compare the SAME ROLE across runs** — that is like
   against like and needs no multiplier at all. For money, read `/usage` by hand.

   **Then the claim report** (the human, 2026-09-12). **It REFUSES NOTHING and exits 0 whatever it finds**, so it can never stop a finale:

   ```
   python3 ~/.claude/skills/run-issues/report_claim_commands.py --repo . --range $(git merge-base main HEAD)..HEAD --batch <batch-id> --ledger <run.md>
   ```

   It writes `claim-commands.md` beside the ledger, naming every added comment or test name claiming code outside its own file. **Paste its count into the briefing.**

   **Then run these four and paste them too**, in the same section:

   ```
   python3 ~/.claude/skills/run-issues/harness_cost.py --batch <batch-id>
   python3 ~/.claude/skills/run-issues/cache_probe.py --days 2
   python3 ~/.claude/skills/run-issues/estimate_accuracy.py \
       --ledger <run.md> --transcript <the run's main .jsonl>
   python3 ~/.claude/skills/run-issues/report_brief_cap.py --tree <the run's tree>
   ```

   **`report_brief_cap.py` says what the 400-word implementer brief cap did**: how
   often it refused the runner, and what the runner then cut each brief to. Ticket 40,
   ruling 16, 2026-09-08 — the cap's number moves on this evidence and on nothing else.
   **`NO DATA` is not `no refusals`.** Its record sits in a temporary directory, by the
   published-hook scrub rule, so it can be swept away mid-run; paste the words it prints
   and never translate them into a zero.

   **`estimate_accuracy.py` ends with an `attribution:` line. Read it.** It says how
   many per-issue spawns the transcript held and how many were booked to an issue,
   and the two must match; an unattributed spawn is named and exits 2. It joins the
   ledger's `Est` column to what each issue actually occupied. **Read the ratio
   beside `harness_cost.py` and never alone**: a permission prompt inside an issue
   reads as the issue running long.

   **`cache_probe.py`'s number is the read-to-write ratio, and it is a watchdog, not
   a score.** If it ever collapses toward 1, the run's input cost has gone up roughly
   tenfold and nothing else in this pipeline would say so.

   **`harness_cost.py` splits what the run lost to the HARNESS rather than to work,
   into three numbers that must never be added up.** PROMPTS is a Bash call left
   pending while a human was waited for, and it is the expensive one. POLLING is
   time spent sleeping for something the harness announces for free. DENIALS are
   classifier refusals, counted and not timed. **A PROMPT row is the finding.** It
   names a command class that has no rule in `.claude/settings.json`, and a rule
   there means it can never be asked again. The four docstrings hold the first
   readings.

   **The `--note` is the only part that needs a person.** Name what changed since
   the previous row — a skill edit, a new hook, a Claude Code version, a different
   effort tier. A row that says nothing changed is still a row; a row with no
   note is a number nobody can use.

   **It can never halt a run.** Every failure inside it is caught and printed as text,
   and it exits 0 even when it can read nothing at all. A cell reading `not read` is a
   missing figure, not a fault: record it and carry on. Do not retry it, do not
   investigate it, and never write a HALT BLOCK for it.

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
   Only `attempt N`, `gates N:` and `criteria reset` are markers; older ledgers hold
   a gate's verdict and a strike as sentences in the Notes cell. **A row it cannot
   read prints `unread` and never a pass**, so a hole is visible rather than silent;
   `test_run_quality.py` carries the whole corpus as a regression net.

   **The strike column is derived and says so.** `SKILL.md` step 5's prose-deletion
   road and a runner-error annulment both cancel a strike in prose and write no
   marker, so the reader counts rounds rejected since the last criteria reset, marks
   any row whose own words disagree with a `*`, and prints both rather than choosing.

   **It can never halt the finale.** Every road exits 0 and prints what it could not
   read, the same rule the cost readings above carry.

   **Then write `## The run in one screen` at the very top of the briefing, above
   every other section.** It is written this late because it is the first moment
   every figure in it exists. The rail block below it follows, and the board renders
   only after both are written and `check_run_rail.py` has passed.

   Six things are read after a run, and the block puts all six above line 40;
   `decisions.md` holds the briefing where three of them sat past line 1700.

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
   line number, because line numbers move daily. A finale that has to compute
   something to fill this block is the wrong build.

   **Every comparable figure is a table row, the two cost ones included.** The board
   panel copies this table and `check_run_picture.py` can only compare what it holds.

   **A run that shipped nothing writes an honest block, never a short one.** Zero is a
   row reading 0 and a sentence saying nothing shipped. A blank panel reads as a render
   that failed.

   **`/daily-brief` reads this block and never the board**, so the block must never be
   thinned on the grounds that the panel shows the same thing. The duplication is
   deliberate: the two are read at different moments, and a brief may not run before
   the human merges.

   **The `Shipped:` line is a required field of this block, and `check_run_rail.py`
   below exits 2 without it.** It is the only place the shipped list is read from,
   because `## What shipped` is not stable in name or in shape across real briefings.
   One line of comma-separated ids is what a reader can read. A run that shipped
   nothing writes `Shipped:      none`.

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
     is the normal case until issue 551's field has been on files for several runs.
     `59 characters or fewer`; the check refuses at 60.
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
     copied.** Real Decide headings run past the card's width and are seldom
     questions at all. Write the short question here, `59 characters or fewer`, and
     leave the fork's own item under `## Decide` exactly as it stands — that is the
     version `/daily-brief` reads, and the card adds no fact it does not carry.
   - **A fork key is unique across the whole briefing.** Number them `F1`, `F2` and
     onward in one sequence, in the order you write them, whatever section holds each
     fork. Every one of the five drawn runs carries TWO `## Decide` headings and each
     numbers its own items from 1, so an item number alone is not a key: two amber cards
     would collide and the board's guard could not tell which row a card came from.
   - **The register is drawn nowhere, and that is deliberate.** Every register row ends
     as one of four things — promoted, which is now a dashed row; fixed, which is already
     inside a shipped card; refused; or dropped below the operator floor, which is a
     refusal — and a fifth road never reaches promotion at all. None of the five
     gets a card: the only register fact on the board is the one-screen table's
     `Register rows left` row and its `Register:` line.
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
     inside the band, and never also as cards on their own stages: the card set and the
     chip set are disjoint and their union is the run's shipped count. That raises the
     cost of a wrong row, because an issue swallowed by a band that should not hold it
     vanishes from its own stage entirely.
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
   inherits whatever the session runs, which since ticket 39 can be Fable, and this
   step converts one markdown file into HTML on the largest input in the pipeline.
   `merge-briefing.md` stays the source of truth, and `/daily-brief` reads that file,
   never the board.

   **This is the one spawn the model map does not reach, and the two do not
   conflict.** Every loop role takes its model from the ledger's `Model map at
   launch:` line and `~/.claude/hooks/model-map-gate.py` refuses a spawn carrying
   anything else. The board renderer has no agent file and no map row, so the gate
   passes it untouched and this paragraph is what governs it. (Scoped by the human on
   2026-08-22; rewritten 2026-09-05 when ticket 39 ruling 10 reversed the older rule.)

   **The panel goes at the top, headed "The run in one screen".** It carries the counts
   as figures, one table of issues by state, one table of the register and cost
   numbers, and a drawn chain where the run has a blocked chain. Where it has none, no
   chain is drawn. Zero shipped reads as a red figure and a sentence saying nothing
   shipped, never as a blank panel.

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
   python3 ~/.claude/skills/run-issues/run_step.py --batch <batch-id> --kind board --label "draw the rail" -- \
       python3 ~/.claude/skills/run-issues/draw_run_rail.py \
       --briefing .scratch/<feature>/runs/<batch-id>/merge-briefing.md \
       --stages docs/agents/run-picture-stages.md
   ```

   (The wrapper is ticket 37 ruling 19 and stamps this step's clock into
   `steps.jsonl`; it passes the script's stdout and exit code straight through,
   so paste what it prints exactly. The board render's own SUBAGENT is not wrapped: it is an Agent spawn, so its
   clock is already in the transcript.)

   It prints four blocks, each with a comment saying where it goes: ten CSS tokens for
   `:root`, the same ten for the `@media (prefers-color-scheme: dark)` block, the
   rail's own CSS, and the `<svg>`. The rail goes inside `<div class="rail-bleed">`,
   directly above the `## The run in one screen` panel, and that div is a direct child of
   `<body>`.

   **The rail takes the WINDOW's width and the prose keeps its reading column**, and
   the CSS does it alone: `.rail-bleed` must be a child of `body`, never of a wrapper.

   **Why a script and not your own SVG**, ruled by the human on 2026-09-04: the shape is
   computed geometry carrying two assertions, and prose cannot assert.
   `check_run_picture.py` below refuses a board that came from anywhere else. Exit 1
   from the script means a sentence is too long: shorten it in the rail block, re-run
   step 4's guard, and draw again. The render is safe to repeat.

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

   **The pin is `opus`, ruled by the human on 2026-09-06.** It was `haiku`, then `fable`
   when the board grew a run panel. Three facts settle it. **Cost is not the
   constraint**: the render is two tenths of one per cent of a run, and one redo
   costs more than any model saving here, which is why the pin is not dropped below
   Opus. **Effort cannot be named on an Agent spawn**: the tool takes a model and no
   effort argument, and this spawn has no agent file to carry frontmatter, so effort
   inherits the session. **The tier order ranks review authority, not price**:
   ruling 14 of ticket 39 fixed `haiku < sonnet < opus < fable` so that no
   adversarial gate sits below the worker it checks, and read as a price list it
   made this pin name the most expensive model for the cheapest job, which
   `q-t39-s2-1` raised and this ruling closes. **Why not lower than Opus**: the
   evidence for a cheap tier on this class of work is
   `.scratch/workflow-audit/citation-recheck-fable.md`, and **state both limits
   wherever it is cited: it measured a checking task producing a report rather than
   an HTML render, and it is one reading rather than a trend.** Without the
   transcription rule and the guard the render is arithmetic, which no tier below
   Opus has been measured on here. `decisions.md` holds the measurements.

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
