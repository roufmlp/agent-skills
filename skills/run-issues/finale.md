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
   had run since 02:27, every route answered HTTP 500 afterwards, `preview_stop` is
   refused by the permission classifier in an unattended run, and starting a server
   by hand is forbidden by the round header. **So `finale-judgment` drove no
   cross-issue seam live in that run**, and fell back to reading composed source at
   branch head plus five seam test files. The failure is silent: the briefing still
   appears, and nothing in it announces the gap unless the finale volunteers it.)

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

   `check_paste_file.py` refuses a pilot paste file whose confirmation query is
   commented out. Pasted as written, such a query returns no rows, no error and
   no output, which reads exactly like a clean result — and on `0095` the
   dangerous outcome is the one only the row COUNT catches. Nine agents touched
   that run's two paste files and nobody ran the query. **A refusal here is
   repaired by deleting the comment marker AND running the query against QA
   before the briefing ships it.** The script cannot tell whether anybody ran it;
   it can only tell that the reader was handed something runnable.
2. **Judgment.** Spawn `run-issues-finale`. Its verdicts plus `merge-briefing.md`
   become the merge briefing.

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
   `promotion` agent over every register row this run wrote, **plus every row anywhere in
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
4. **Regenerate the action board** — `.scratch/<feature>/board.html`, the one-page
   human view of `merge-briefing.md`. Live actions only, grouped by when, one line of
   what and one of why each, ticks persisted in localStorage. Keep the existing
   styling; send it with SendUserFile. **A fresh subagent renders it, spawned with
   `model: "haiku"` named explicitly on the Agent call** — from `merge-briefing.md`
   plus the old board, never the runner itself, whose context is at its most
   expensive by run end, and the old board's bytes never enter the runner.
   Naming the model is not optional and "cheap" is not a model: an unnamed spawn
   inherits the session model, so this step was paying the top tier to convert one
   markdown file into HTML on the largest input in the pipeline (283 KB, measured
   2026-08-06). There is no judgement in the render — the briefing already decided
   what the board says. `merge-briefing.md` stays the source of truth,
   and `/daily-brief` reads that file, never the board.

   **This is the one spawn `SKILL.md`'s "never pass a `model:` value" rule does not
   cover, and the two do not conflict.** That rule is scoped to roles that HAVE an
   agent file, because there a spawn-time value silently defeats the file's
   `model: inherit`. The board renderer has no agent file, so there is nothing to
   defeat and nothing to inherit from but the session. (Scoped by the human on
   2026-08-22, answering C7 of the skills audit.)
5. **Recommend follow-ups; start none.** One exception is mandatory:
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

6. **Measure this run, and append its row.** Run

   ```
   python3 ~/.claude/skills/run-issues/run_costs.py --run <run-name> --issues <count> \
       --version <cc-version> --note "<what changed since the last run>"
   ```

   Paste its whole output into `merge-briefing.md` under `## What this run cost`. It
   appends one row to `.scratch/workflow-audit/run-costs.md`, which is the table the human
   reads to compare one run against the one before it.

   **`--run` is this run's own name, `batch-88624c` and the like — the part of the
   branch after `claude/run-issues-`.** Pass it. Without it the script takes the name
   from the branch checked out where it is running, which is right only when that is
   the run's own worktree, and refuses otherwise. Run `batch-88624c` ran this from the
   MAIN checkout on 2026-08-31; the old rule then took the newest transcript in that
   directory's slug, which holds 64 sessions of unrelated work, and reported 1.01 hours
   for an 8.48-hour run with a longest step the run never ran. The row it appended was
   wrong in both timing columns. It now checks that the transcript it picked names the
   run, and appends NO row when it cannot identify one.

   **Then run these two and paste them too**, in the same section:

   ```
   python3 ~/.claude/skills/run-issues/harness_cost.py
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
   The human asked for this measurement on 2026-08-30 because until then the only
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
