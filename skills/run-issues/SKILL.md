---
name: run-issues
description: Autonomously implement a range of tracker issues one by one — fresh Opus implementer per issue (TDD), ephemeral Fable verify + review gates, two-strike Fable escalation, cron auto-resume across usage limits, human merge gate at the end. Use when the user wants to implement issues sequentially without supervision ("run issues 05-09", "implement all remaining issues", "continue until all issues are done"), or to RESUME an interrupted run ("/run-issues resume").
argument-hint: "issue range: one issue, a range (05-09), or 'all'; optionally --effort=max"
---

# Run issues

One thin runner session implements a range of issues end to end. Workers and gates
are subagents (fresh context each). After launch the user is needed only twice: the
finale go-ahead, and the merge read.

Settled design — do not relitigate in-session (agreed with Abdul 2026-07-19,
cost revision same day after the first real run): Opus implementers; Opus verify
gate + Fable review gate (Fable is the judgment choke point, verify is
observational); two-strike escalation; runner owns the branch, Abdul owns main;
finale judgment half waits for explicit confirmation; effort floors below.
Post-run-1 revisions (grilled and agreed 2026-07-19, after the 13c–14 run):
thin ledger + journal split, derived-money fable tag, shared-quota ownership,
routing verification, one-writer worktrees + explicit-path commits,
HTML-over-HTTP verification default, preview-deploy skip where blocked.
Review-gate effort floors were examined and deliberately left unchanged.

## Scope argument

`/run-issues 05` (one), `/run-issues 05-09` (range), `/run-issues 13c 20 14 22`
(explicit list, run in the order given), `/run-issues all` (every remaining
`ready-for-agent` issue, tracker order). Issues are a dependency chain:
always run in order, never skip forward past a blocked one.

**`all` hygiene:** resolve the scope from each issue file's `Status:` line and
take ONLY clean `ready-for-agent` issues. Print the resolved list in the launch
message so the user sees exactly what will run. Skip `ready-for-human`,
`in-progress`, `needs-*` and anything already `done`. If a `ready-for-agent`
issue looks superseded by later merged work (primer/git says so), set it
`needs-info` with one line of why and skip it — never build a stale issue blind.

## Roles, models, effort floors

| Role                  | Runs as              | Model | Effort | Raised to max when                     |
|-----------------------|----------------------|-------|--------|----------------------------------------|
| Runner                | invoking session     | (any) | —      | —                                      |
| Implementer           | subagent, per issue  | opus  | high   | — (escalated respawn is fable @ max)   |
| Verify gate           | subagent, per issue  | opus  | high   | becomes fable @ high if issue tagged `model: fable` |
| Review gate           | subagent, per issue  | fable | high   | tagged issue, or the diff CHANGES money computation, auth, or secret handling (merely touching a file with a price field does not count) |
| Coherence finale      | subagent, once       | fable | max    | always                                 |

Floors may be raised (issue tag, diff contents, user `--effort=`), never lowered.
Spawners may not weaken any canned brief. Workers send bulk mechanical work to
Sonnet subagents.

Issues that are engine-core (novel algorithms, concurrency) — or whose
acceptance includes a DERIVED money figure shown to the operator (a computed
margin, P&L, drift verdict; merely reading, recording or storing figures does
not count) — should carry `model: fable` in their frontmatter at /to-issues
time; the runner then spawns a Fable implementer at max effort for that issue
directly. Derivation is where enumeration-style fixes fail and design-property
thinking wins; the first real run paid two rejected Opus attempts on exactly
such an issue before the escalated Fable implementer solved it by making the
bad state unrepresentable. A runner that spots an untagged derived-money issue
at spawn time applies the tag itself and notes it in the ledger.

## Run state — files, not contexts

In the main checkout:

```
<main-repo-root>/.scratch/<feature>/run.md         # THIN ledger — the only run file subagents read
<main-repo-root>/.scratch/<feature>/run-journal.md # full narrative, append-only — subagents NEVER read it
<main-repo-root>/.scratch/<feature>/primer.md      # codebase primer (see below)
<main-repo-root>/.scratch/<feature>/for-abdul.md   # running merge-read briefing
```

Ledger statuses: `queued → in-progress → gate-verify → gate-review → done`,
plus `blocked`. The runner alone writes the ledger; gates write verdicts into the
issue file; everyone appends, nobody rewrites others' sections.

**The ledger stays thin — it is read by every spawn.** `run.md` holds: the
status table, pre-flight, a log capped at ~2 lines per event (spawn, verdict,
commit), and a **Carry-forward** section the runner curates — the distilled
facts every future brief must include (shared-quota state, traps discovered,
conventions later issues must follow, do-not-tidy lists). If a learning matters
to a future spawn it goes in carry-forward as a bullet, not in log prose —
a learning that lives only in narrative survives only if the runner remembers
to re-brief it.

**The narrative goes in `run-journal.md`** — what each attempt did and why,
verdict stories, dead ends. The runner appends as it goes. It is read exactly
twice: by a resuming runner on revival (so resume briefs stay as good as the
originals) and by the finale / post-run analysis. Verdict detail still lives in
the issue files; the journal is the run-level thread. The first real run kept
all of this in the ledger — ~40k tokens re-read by ~19 spawns whose briefs
needed only the table.

**Primer:** fresh subagents read `primer.md` INSTEAD of exploring the codebase —
key files, seams, decisions made so far. The first implementer creates it (one
exploration, once); every implementer appends anything structural it learned.
Exploration is paid once per run, not once per issue.

## Shared external quotas

Any per-day or per-window cap on an external system — API call caps, email or
messaging send limits, trial-org allowances — is RUN STATE, owned by the runner:

- The carry-forward section holds the last observed status, its timestamp, and
  who currently holds the spend window. An agent may spend against a quota only
  if its brief grants it; **two agents never hold the same quota at once**.
  (First real run: a verify gate and a live-claims agent spawned concurrently
  against one rate-limited org — the second got nothing and found out late.)
- **Live halves schedule first.** When an issue has live verification against a
  capped system and the window is open, drive it at the start of the session —
  one cheap read to confirm headroom, then the live work — not after a day of
  code with the cap long gone.
- Every brief that touches a rate-limited system carries: **two consecutive
  refusals → stop and report. Never poll.**

## Per-issue loop

1. Runner spawns a fresh implementer (brief below). Small-issue coalescing: up to
   two adjacent trivially-small issues (copy, config — no logic) may share one
   spawn; anything with logic is one issue per spawn.
2. Implementer done → runner spawns the verify gate, then the review gate.
   Coalesced trivial issues get ONE combined gate spawn (fable @ high, both
   briefs merged) instead of two separate gates.
3. Both pass → before anything else, **verify the routings**: every finding a
   gate declared routed must actually be present in its target file — grep the
   target; a declared routing is not a routing (a real gate declared findings
   routed and never appended them; another gate caught it by luck). Then commit
   to the feature branch — **staging explicit paths only, never `git add -A`
   or `.`**: list what the issue's diff owns, glance at `git status`, and
   investigate anything unexplained in the tree before committing, not after.
   Ledger `done`, and set the issue file's `Status:` line to the canonical label
   `done — on branch <branch>, unmerged` (gate history goes in the body, never
   in the Status line — `all` runs parse it). The merging session flips it to
   `done — merged <date>`. Then next issue.
4. A gate rejects → same implementer retries with the written reasons.
5. **Two strikes:** second rejection of the same issue kills the implementer. The
   runner spawns a FRESH implementer — **fable, max effort** — briefed with the
   issue and both rejection verdicts but none of the failed attempt's reasoning.
6. If the fable implementer also fails a gate: ledger `blocked` with a note, and
   the run HALTS (dependency chain — do not build on a wrong slice). Report to the
   user what's blocked and why.

## Nothing finishes vaguely

An issue may only leave the ledger as `done` or `blocked` — never "done, mostly".
Anything unfinished gets written into its ONE named home before the ledger moves,
and the merge briefing lists every such entry (no silent caps):

- Acceptance unmet → the issue stays `blocked`; gates must refuse `done`.
- Waiting on the user (secret, env var, OAuth client, external account) → the
  pending-on-abdul memory file, as a numbered action in his briefing style; the
  code side may still complete and the briefing says what is stubbed until then.
- Follow-up work discovered mid-issue → a new issue file in
  `.scratch/<feature>/issues/`, or a fold-in section in the next issue's file.
- Live-system gaps tests cannot reach → noted for the post-deploy /parallel-hunt.
- **Bugs the gates find OUTSIDE the issue's scope** (pre-existing, or belonging
  to another issue): route to one of the homes above and move on. A gate judges
  the issue against ITS acceptance only — an out-of-scope find never blocks the
  issue or the run.

**A declared routing is not a routing.** A gate appends to the target home
FIRST, then writes its verdict citing the appended location ("routed to issue
NN — appended"); a verdict may not claim a routing it cannot cite. The runner
verifies every target before the ledger moves (per-issue loop step 3).

Handoff documents are NEVER the home for any of this — a new issue's session
starts from its issue file + primer + CONTEXT.md and must find every loose end
already in the right place.

## Branch and human gate

The runner owns the feature branch; **main belongs to Abdul.** The run
worktree has **ONE writer** — the current issue's implementer, plus the runner
committing. Side agents (live probes, concurrent checks, anything spawned
beside the per-issue loop) work in the scratchpad or their own worktree, never
the run's tree; a side agent that needs to touch the run tree is a sign it
should have been a gate or the implementer. (First real run: a side agent's
probe files landed in the run tree and only explicit-path staging kept them out
of a gate-passed commit.) Commit per issue after gates pass. **There is NO merge between issues** — the next issue builds
directly on the branch; merge to main happens once, at run end, by Abdul. A
single-issue run therefore reaches the finale ask immediately after its only
issue — that stop is by design, not a stall. Extending a finished run to a new
issue is a NEW run: Abdul merges first, then invokes /run-issues again from
main. Nothing merges to main and nothing deploys beyond preview
without his read. The review gate appends anything a human should look at to
`for-abdul.md` as it goes, so his merge read is guided.

**Merge ritual — a worktree dies the moment its branch merges.** The session that
merges to main immediately runs, for that branch's worktree: check
`git status --porcelain` is clean → `git worktree remove <path>` →
`git branch -d <branch>` (committed work is already in main's history; only
uncommitted files can be lost, and the clean check catches those — report any
dirty tree to Abdul instead of removing). Standing worktree inventory must never
exceed the number of live runs.

## Finale — mechanical half automatic, judgment half on confirmation

After the last issue:

1. **Automatic:** full typecheck, full test suite, preview deploy — but only
   where the deploy needs no permission the classifier withholds. Where it is
   blocked (e.g. a repo whose deploy path touches a protected secrets file):
   skip it, say so in the briefing, NEVER work around the classifier, and never
   re-litigate per run — the repo's CLAUDE.md records the standing decision.
   Failures here reopen the offending issue via the per-issue loop.
2. **Then STOP and ask:** "Finale pending — one fable pass (whole-branch coherence
   review at max effort + full /verify) before your merge read. Say go."
   The resume cron must NEVER trigger this half; only the user does. This lets him
   time the fable spend (e.g. after a limit reset).
3. On go: one fable subagent reviews the ENTIRE branch diff as a single change —
   design coherence, duplication across issues, drifted seams, coderules — and a
   full end-to-end /verify runs. Verdicts + `for-abdul.md` become the merge
   briefing.
4. Close the report by recommending follow-ups — recommend, never start; Abdul
   picks the time:
   - Always: after merge + deploy, a `/parallel-hunt` round on the live system —
     it hunts the seams BETWEEN issues and against live external systems (Zoho,
     email, WhatsApp), the class of bug per-issue gates cannot see. Its `deferred`
     register entries become the issues for the next /run-issues round.
   - Only if the coherence findings are structural (duplication across issues,
     drifted seams): an `improve-codebase-architecture` session on a clean tree
     before the next phase's issues are written.

## Auto-resume across usage limits

At launch create a repeating scheduled wakeup (CronCreate, every 30 min): "If
`<run.md>` shows an active run with no ledger progress since last firing, resume
from ledger state; otherwise do nothing. Never trigger the finale judgment half."
Firings during a rate-limit window simply fail; the first one after reset revives
the run. A RESUMING runner reads `run-journal.md` once on revival — that is one
of the journal's two sanctioned reads — so its briefs carry the full story, not
just the table. Delete the cron at run end. Remind once at launch: machine stays awake
(`caffeinate -dimsu`).

Idempotency: every brief begins "Read the ledger first; if your assigned issue is
already past your stage, stop and return."

Pre-flight before spawning anything: confirm the permission allowlist covers the
run (tests, git, preview deploy) — a worker blocked on a prompt stalls silently.
And link env: the worktree's `.env.local` must be a SYMLINK to the repo's
canonical env file (see the repo CLAUDE.md for its path), never a copy. Replace
any copy found. Env files never get committed or pushed.

**Vercel-CLI trap (real incident, 2026-07-19):** `vercel link` / `vercel pull`
write through the `.env.local` symlink into the CANONICAL env file. Before any
such command: remove the symlink, run the command, delete whatever `.env.local`
it wrote, restore the symlink. Never edit the canonical file to clean up after
Vercel.

## Canned briefs (verbatim, fill the <>)

### Implementer (opus @ high; or fable @ max if tagged/escalated)

> Read the ledger's status table and Carry-forward section at <path> first —
> never run-journal.md; if issue <ID> is already past implementation, stop and
> return. Read primer.md INSTEAD of exploring the codebase; append anything
> structural you learn. You may spend against a shared external quota (API cap,
> send limit) ONLY if this brief grants it; two consecutive refusals from a
> rate-limited system → stop and report, never poll. If the issue has a live
> half against a capped system and this brief grants the window, drive that
> half FIRST while the window exists. Implement issue <ID> per its brief:
> invoke /tdd, work test-first at the pre-agreed seams, run typecheck and the
> relevant test files as you go (NOT the full suite — that is the finale's
> job). You own shipped code on the feature branch; do not merge, deploy, or
> touch main. Send bulk mechanical work to Sonnet subagents. If you pass ~60%
> context, write remaining state into the issue file and return. Final message:
> what changed, test status, anything NOT yet written down.
> [Escalation respawn only: attempts 1–2 were rejected for the reasons attached.
> Do not trust the previous diagnosis — re-derive from the issue and the code.]

### Verify gate (opus @ high; fable @ high if issue tagged `model: fable`)

> You are an adversarial VERIFY GATE for issue <ID>. Read primer.md and the
> issue file INSTEAD of exploring the codebase — your context is expensive, spend
> it on the acceptance path, not on orientation. Then invoke /verify and drive
> ONLY this issue's acceptance path in the
> running app. For server-rendered surfaces, drive over HTTP and read the served
> HTML — it is the whole truth and costs no browser; open a real browser only
> for what genuinely lives client-side (hydration handlers, client navigation,
> visual layout) — never use HTTP-only driving to dodge testing client-side
> behaviour. Spend against a shared external quota ONLY if this brief grants
> it; two consecutive refusals → stop and report, never poll. Your job is not
> to tick the checklist — it is to catch behaviour
> that technically passes while being subtly wrong: states, edge inputs, design
> floor. Verdict into the issue file: pass, or reject with concrete observed
> behaviour. Route findings at write time: append to the target home FIRST,
> then cite the appended location in the verdict — never declare a routing you
> cannot cite. Touch no code.

### Review gate (fable @ high; max if tagged, or the diff changes money/auth/secret logic)

> You are an adversarial REVIEW GATE for issue <ID>. Read primer.md, the issue,
> and the issue's diff — nothing else unless the diff itself points there. Then
> invoke /code-review on the issue's diff at high effort. Beyond it: try to REFUTE the
> implementation — does it solve the issue's actual requirement or a lookalike?
> Do the tests pin behaviour or mirror the code? Check against the repo coderules
> (no bypassed controls, no new deps, parameterised queries, no secrets
> client-side). Verdict into the issue file: pass, or reject with concrete
> reasons. Route findings at write time: append to the target home FIRST, then
> cite the appended location in the verdict — never declare a routing you
> cannot cite. Append anything a human should see at merge time to for-abdul.md.
> Touch no code.

### Coherence finale (fable @ max — only after the user says go)

> You are the COHERENCE FINALE. Read run-journal.md — this is one of its two
> sanctioned reads; you are the fresh eyes it exists for. Review the ENTIRE
> branch diff against main as one
> change: design coherence across issues, duplication, seams that drifted, missed
> simplifications, coderules. Then run the full end-to-end /verify (same
> HTML-over-HTTP default as the verify gate). You are the
> last fresh eyes before the human merge read — write your findings and finalise
> for-abdul.md into a merge briefing: per-issue summary, gate history, open
> concerns, what to look at first. Touch no code.
