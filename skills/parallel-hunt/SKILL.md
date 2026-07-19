---
name: parallel-hunt
description: Run a parallel bug-hunt round — Opus finder + Opus fixer as background subagents over a shared register, with ephemeral Fable gates reviewing claims and fixes. Use whenever the user wants a bug hunt, verification round, hardening pass, or any run with two or more concurrent agents on one repo (finder/fixer, find-and-fix, "parallel run"). Also invoke to RESUME an interrupted hunt ("/parallel-hunt resume").
---

# Parallel hunt

One thin orchestrator session runs the whole round. Workers are **background subagents**
(fresh context each), never extra chat sessions. Nobody waits on the user after launch.

Settled design — do not relitigate these in-session (agreed with Abdul 2026-07-19):
Fable gates + Opus workers; shared-file register; strict ownership; batch-of-3
succession; cron auto-resume.

## Roles and models

| Role         | Runs as                              | Model  | Lives for            |
|--------------|--------------------------------------|--------|----------------------|
| Orchestrator | the session that invoked this skill  | (any)  | the whole round      |
| Finder       | background subagent                  | opus   | one sweep group      |
| Fixer        | background subagent                  | opus   | one batch of 3 fixes |
| Claim gate   | subagent, spawned after each sweep   | fable  | one review, then dies|
| Fix gate     | subagent, spawned per fix batch      | fable  | one review, then dies|

Workers send bulk mechanical work (log trawls, wide greps, repeated probes) to
Sonnet subagents — never do it in their own context.

Effort floors (may be raised — by severity or a user `--effort=` flag — never
lowered; spawners may not weaken any canned brief): finder, fixer, claim gate and
fix gate all run at **high**; the claim gate and fix gate rise to **max** for
`severity: critical` entries or diffs touching money/auth/security.

## The register — all state lives in files, not in contexts

Location: **the main checkout**, not any worktree, so every agent reads and writes
the same absolute path with no git sync:

```
<main-repo-root>/.scratch/<feature>/register.md      # live index table
<main-repo-root>/.scratch/<feature>/bugs/<ID>.md     # evidence, reproducer, verdicts
```

`register.md` is a table: `ID | one-line summary | severity | status | owner-notes`.
Per-bug files hold evidence, reproducer, pinning-test path, gate verdicts. Agents
append to their own section of a bug file; only the transition owner touches `status`.

Status machine, single writer per transition:

- `open` — written by **finder** only (after claim gate passes). Finder may move its
  own entries to `retracted`.
- `open → in-fix → fix-ready` — **fixer** only.
- `fix-ready → verified`, or back to `in-fix` with written reasons — **fix gate** only.
- `deferred` — orchestrator, at round end. A deferred entry already IS the issue file
  a future /implement session picks up; no conversion step.

Commit `.scratch/<feature>/` to main when the round ends.

## Code ownership — the merge-tax rule

- **Finder** writes only: the register, and NEW test files at
  `tests/regressions/<bug-id>.test.ts` (one file per bug, never edits existing
  suites, never touches shipped code — not even to "help").
- **Fixer** owns shipped code, unit fakes, and fixtures. It may flip an `expect` in
  `tests/regressions/` only when the fix intentionally changes behaviour, and must
  say so in the register entry — the fix gate rejects unexplained touches.
- Deferred bugs keep their failing test as `test.skip` with the bug ID.

## Work units and succession (the anti-smart-zone rule)

Sessions degrade quietly past ~120k tokens, so no worker outlives one work unit:

- Finder unit: one sweep group (one subsystem, or ~8–10 new register entries,
  whichever first). Then it returns and the orchestrator spawns a fresh finder.
- Fixer unit: 3 fixes reaching `fix-ready`. Then the orchestrator spawns the fix
  gate, and a fresh fixer for the next batch.
- Backstop: any worker past ~60% context finishes its current bug only, then returns.

Succession needs no handoff doc: a successor's brief is the register plus the role
brief below. The register IS the handoff.

## Orchestrator rules

Stay thin — the orchestrator's context is the only one that lasts all round:

1. Never read bug-file contents or diffs; read only `register.md` status lines and
   worker return summaries. Judgment belongs to the gates.
2. **Pre-flight** before spawning anything: confirm the permission allowlist covers
   the run (test commands, git, the repo paths) — a worker blocked on a permission
   prompt stalls silently; fix the allowlist first (see /fewer-permission-prompts).
   And link env: every worktree's `.env.local` must be a SYMLINK to the repo's
   canonical env file (see the repo CLAUDE.md for its path), never a copy. Replace any copy found.
   Env files never get committed or pushed. **Vercel-CLI trap:** `vercel link` /
   `vercel pull` write through the symlink into the CANONICAL env file — remove
   the symlink first, run the command, delete its `.env.local`, restore the link.
3. Create `.scratch/<feature>/register.md` with the target scope, then spawn finder
   and fixer concurrently (fixer idles politely until entries reach `open`).
4. On each worker return: spawn the right gate and/or successor. Loop until the
   finder returns dry twice and no entries remain `open`/`in-fix`/`fix-ready`.
5. Round end: mark leftovers `deferred`, delete the heartbeat cron, commit the
   register, report: verified fixes, rejected fixes, retracted claims, deferred.

## Auto-resume across usage limits

At launch, create a repeating scheduled wakeup (CronCreate, every 30 min):
"If `<register path>` shows an active round with no worker progress since the last
firing, resume the round from register state; otherwise do nothing." Firings that
land while rate-limited simply fail — the first one after the reset revives the run.
Delete the cron at round end. Remind the user once at launch: machine must stay
awake (`caffeinate -dimsu` or equivalent).

Idempotency rule that makes resume safe — every worker brief begins:
"Read the register first. If your assigned work is already `fix-ready` or
`verified`, stop and return immediately."

## Canned role briefs

Use these verbatim (fill the <>). The spawner may not weaken them.

### Finder brief (opus, background)

> Read the register at <path> first; if your assigned sweep group is already
> covered, stop and return. You are the FINDER for <scope>. Investigate the live
> system for defects in <sweep group>. For each defect: create bugs/<ID>.md with
> evidence and a reproducer, write a failing pinning test at
> tests/regressions/<ID>.test.ts, and add a register row with status `candidate`.
> You may NOT edit shipped code or existing test suites — register and new
> regression test files only. Send bulk log/grep work to Sonnet subagents. Stop
> after <N> entries or when the group is swept, whichever first; if you pass ~60%
> context, finish the current bug and return. Your final message: register IDs
> added, plus anything learned that is NOT yet written into the bug files.

### Fixer brief (opus, background)

> Read the register at <path> first; if no entries are `open`, or your assigned
> entries are already `fix-ready`/`verified`, stop and return. You are the FIXER.
> Take the next `open` entries in order, up to 3. Per entry: set status `in-fix`,
> read the bug file and its pinning test, fix test-first (/tdd), run typecheck and
> the relevant test files, set `fix-ready` with a diff summary in the bug file. You
> own shipped code and fixtures; you may flip an expect in tests/regressions/ only
> with a written justification in the register entry. Commit per fix to the
> working branch. After 3 fixes (or ~60% context), return.

### Claim gate brief (fable, after each finder sweep)

> You are an adversarial CLAIM GATE. Read register entries <IDs> at <path> and
> their bug files. For each: try to REFUTE the claim — is the evidence real, does
> the reproducer reproduce, does the pinning test pin the claimed behaviour and
> not something else? Run the reproducer yourself where cheap. Verdict per entry,
> written into the bug file: promote `candidate → open`, or `retracted` with one
> line of why. When uncertain, retract — a phantom bug costs the whole pipeline.
> Touch nothing except status and your verdict section.

### Fix gate brief (fable, per batch of 3)

> You are an adversarial FIX GATE. For register entries <IDs> at <path>: read the
> bug file, the pinning test, and the fixer's diff (git). Try to refute the fix —
> does it fix the diagnosed cause or mask a symptom? Does the pinning test now
> pass for the right reason? Any touch of tests/regressions/ without a written
> justification in the register entry is an automatic reject. Check the diff
> against the repo's coderules (no bypassed controls, no new deps, parameterised
> queries). Verdict per entry in the bug file: `verified`, or back to `in-fix`
> with concrete reasons. Touch nothing except status and your verdict section.

## Also fits (promote when a real need lands, not before)

Pre-launch security gate (coderules' 10 points as register entries), test-coverage
campaigns, migration/deprecation sweeps, docs-drift rounds. NOT for building one
feature — that is a dependency chain, use /to-issues → /implement.
