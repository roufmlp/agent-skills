# The finale, in full

The runner reads this file once a run, when it writes `finale-mechanical` into
the ledger after the last issue. That write is the trigger, and `SKILL.md` holds
it. Nothing here is resident in `SKILL.md`, because a run pays for that file on
every turn and pays for this one once.

The text below stood in `SKILL.md` until 2026-08-16 and moved here.

## Finale — fully automatic

After the last issue, in order, tracked in the ledger as
`finale-mechanical → finale-judgment → finale-promotion → finale-board →
awaiting-merge` so an interrupted finale resumes rather than re-running. Write each
state before the step it names begins, so a kill inside a step resumes at that step
rather than past it. Promotion is safe to re-enter — it deletes each row as it
resolves it — and the board render is safe to repeat:

1. **Mechanical.** Full typecheck, full test suite, and a build from a **cold
   cache** (delete whatever the project's build cache is — `.next`, `dist`, `target`
   — because a warm cache agrees with whatever it already compiled). Committed run state is build input: the ledger, journal and
   issue files sit inside the repo, so whatever scans the project scans them too.
   Confirm the toolchain excludes them, and treat a code fence in a write-up as
   something the build may try to compile. Failures reopen the offending issue
   through the per-issue loop.

   **The cold-cache build destroys the dev server's build directory, so this step
   hands the next one a working server.** After the build finishes, `preview_start`
   the dev server and confirm one route answers 200. Record that confirmation in
   the ledger beside `finale-mechanical`, so the judgment step reads whether it has
   a live harness rather than assuming one. `preview_start` on a stopped server is
   already permitted, so this needs no new permission. (Adopted 2026-08-18, from
   one run's finale: the step deleted `.next` under a server that
   had run since 02:27, every route answered HTTP 500 afterwards, `preview_stop` is
   refused by the permission classifier in an unattended run, and starting a server
   by hand is forbidden by the round header. **So `finale-judgment` drove no
   cross-issue seam live in that run**, and fell back to reading composed source at
   branch head plus five seam test files. The failure is silent: the briefing still
   appears, and nothing in it announces the gap unless the finale volunteers it.)

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

   **A migration says when a constraint came from measured data rather than from
   a business rule.** A number read off today's input is a fact about one import,
   not a rule about the business, so the header names it as measured and the
   issue lists it in `## Must still be true` as an assumption a later issue may
   lift. (Adopted 2026-08-10, from a run finale: one issue wrote a check
   constraint capping a rank at 3 because no group in the source workbook held
   more than three entries; a sibling issue in the same run let a user add a
   fourth, so an unplanned migration had to lift the ceiling, and the runner's
   spawn brief had told that implementer "this issue adds no migration" for the
   same reason. Both gates passed the constraint correctly, because its own
   criteria never mentioned the case. Cost: one unplanned migration and one
   wrong brief. The lifting migration's header is the model — it names which
   sentence in the original was evidence and which was inference.)

   **A published checksum expires the moment the file moves.** A correction
   round re-stamps every checksum a gate published for a file it touched, and
   the finale re-runs any that remain before the briefing closes. Anchor diff
   commands to `main...HEAD`, never the working tree — a worktree diff prints
   nothing once the work is committed, and an empty print cannot distinguish
   "fine" from "the fix was reverted and committed". Both checksums on one issue
   were correct at gate close and false three hours later, and running them read
   as the exact alarm the gate wrote them to raise (decisions.md).

   **Main moved while you worked. Read it before you write a question.** The run
   branches from a worktree cut hours or days earlier, so the human's rulings
   since the cut are invisible to every agent in the pipeline. The finale diffs
   the merge base against main's current tip and reads every commit touching an
   issue in scope. Anything already answered leaves the briefing, and the
   briefing says it was answered. (Adopted 2026-08-10: the human ruled twice on
   an issue while its run was in flight, and the run came within one `Decide`
   item of handing back a question closed three hours earlier.)

   **Sweep the register for rows their own issue already fixed.** A review gate
   files a row, the issue's correction round fixes it inside the commit the gate
   was reading, and nothing re-reads the row afterwards — so promotion, which
   reads neither the bug file nor the diff, mints an issue for work that has
   shipped. The finale already holds the commits, so it does the re-reading: any
   row whose issue committed after the row was filed is checked against that
   commit and marked `verified` where the fix landed, which routes it to
   promotion's `fixed` exit. Three of seventeen issues minted on one run were
   stale this way, each costing a run slot and a hardening pass. (Remedy chosen
   2026-08-10.)

   If the finale fails on a usage limit, leave the ledger at
   `finale-judgment`, write the halt block, and revive after reset — never
   downgrade it to save the wait, and never declare the run complete with the
   judgment half unrun.
3. **Promotion — the last phase that resolves findings, and the only door into
   `issues/`.** Spawn one
   `promotion` agent over every register row this run wrote, **plus every row
   anywhere in the register that already reads `verified`**, giving it the
   project's issue directory path and its numbering rule. A row already at
   `verified` exits as `fixed`, before audience is even read, because the run fixed it
   and the fix is in the commit. That exit takes no judgement, so widening the
   scope cannot promote anything wrongly, and it is what sweeps up a `verified`
   row left by a fix made outside any run — without the sweep those rows belong
   to no run and accumulate for ever (ruled 2026-08-12). Of the rest it promotes
   on the audience-and-severity thresholds, and refuses the others. A promoted
   row becomes an issue file at `Status: needs-harden` with one
   category role and a link to its bug file. All three exits delete the row, so the
   register's length stays the promotion backlog and nothing else.

   **The thresholds live in the `promotion` agent file and nowhere else.** Both
   skills spawn the one agent, so a run brief that restates a threshold restates
   a figure it cannot keep current. This file and `parallel-hunt/SKILL.md` both
   carried "operator at any severity" for a day after the human set a `medium`
   floor on `operator` (2026-08-09); one run's brief repeated the stale figure
   and promotion had to overrule its own brief. Name the exits here; read the
   numbers there.

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
