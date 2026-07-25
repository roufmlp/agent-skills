---
name: parallel-hunt
description: Run a parallel bug-hunt round — a finder and a fixer working concurrently over a shared register, with ephemeral adversarial gates reviewing every claim and every fix. Use whenever the user wants a bug hunt, verification round, hardening pass, or any run with two or more concurrent agents on one repo (finder/fixer, find-and-fix, "parallel run"). Also invoke to RESUME an interrupted hunt ("/parallel-hunt resume").
---

# Parallel hunt

One thin orchestrator session runs the whole round. Workers are background
subagents with fresh contexts, never extra chat sessions. Nobody waits on the user
after launch.

Settled design decisions and the incidents behind them live in `decisions.md`,
next to this file. Read it if you are tempted to change how the round works —
not to run one.

## Who runs what

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the orchestrator never pastes a brief.

| Role | Agent type | Effort | Lives for |
|---|---|---|---|
| Finder | `parallel-hunt-finder` | xhigh | one sweep group |
| Fixer | `parallel-hunt-fixer` | high | one batch of fixes |
| Claim gate | `parallel-hunt-claim-gate` | high | one review, then dies |
| Fix gate | `parallel-hunt-fix-gate` | high | one batch, then dies |
| Fix gate, critical | `parallel-hunt-fix-gate-critical` | max | one batch, then dies |

Use the critical fix gate for `severity: critical` entries, or any fix whose diff
touches money, auth or security.

Spawn prompts carry **only** what varies — the sweep group, the register IDs, the
batch size. Everything stable already lives in the agent file, where it caches.

## The register — all state in files

In **the main checkout**, not any worktree, so every agent reads and writes the
same absolute path with no git sync:

```
<main-repo-root>/.scratch/<feature>/register.md   # the index table
<main-repo-root>/.scratch/<feature>/bugs/<ID>.md  # evidence, reproducer, verdicts
```

`register.md` is a table: `ID | one-line summary | severity | status | owner-notes`.
Per-bug files hold the evidence, the reproducer, the pinning-test path and gate
verdicts. Agents append to their own section; only the owner of a transition
touches `status`.

Status machine, single writer per transition:

- `candidate` — finder only.
- `candidate → open` or `retracted` — claim gate only.
- `open → in-fix → fix-ready` — fixer only.
- `fix-ready → verified`, or back to `in-fix` with written reasons — fix gate only.
- `deferred` — orchestrator, at round end. A deferred entry already **is** the
  issue file a future run picks up; there is no conversion step.

Commit `.scratch/<feature>/` to main when the round ends.

## Code ownership — the merge-tax rule

- **Finder** writes the register and NEW test files, one per bug, named by bug id,
  in a regressions directory of the project's own test layout. It never edits
  existing suites and never touches shipped code, not even to help.
- **Fixer** owns shipped code, unit fakes and fixtures. It may flip an expectation
  in one of those regression files only when the fix intentionally changes the
  pinned behaviour, and must say so in the register entry. Unexplained touches are an
  automatic reject.
- Deferred bugs keep their failing test as `test.skip` with the bug ID.

## Work units and succession

Sessions degrade quietly past ~120k tokens, so no worker outlives one work unit:

- **Finder unit:** one sweep group — one subsystem, or ~6–8 new register entries,
  whichever comes first. It runs at xhigh and burns context faster than the other
  roles, which is why its unit is the smallest.
- **Fixer unit:** 3 fixes reaching `fix-ready`.
- **Backstop:** any worker past ~60% context finishes its current bug and returns.

Succession needs no handoff document. A successor's brief is the register plus its
own agent file. **The register is the handoff.**

## Orchestrator rules

Stay thin — the orchestrator's context is the only one that lasts all round.

1. **Never read bug-file contents or diffs.** Read `register.md` status lines and
   worker return summaries. Judgement belongs to the gates; the moment the
   orchestrator starts forming opinions about bugs, it stops being thin.
2. Create the register with the target scope, then spawn finder and fixer
   concurrently. The fixer idles politely until entries reach `open`.
3. On each worker return, spawn the right gate and/or successor.
4. Loop until the finder returns dry twice **and** no entries remain `open`,
   `in-fix` or `fix-ready`.
5. Round end: mark leftovers `deferred`, delete the heartbeat cron, commit the
   register, and report — verified fixes, rejected fixes, retracted claims,
   deferred entries. Say plainly what was left undone; a round that reports only
   its wins is not a report.

## Auto-resume across usage limits

At launch create a repeating wakeup (CronCreate, every ~30 min): "If
`<register path>` shows an active round with no worker progress since the last
firing, resume from register state; otherwise do nothing." Firings that land while
rate-limited simply fail; the first after the reset revives the round. Delete it at
round end. Remind the user once that the machine must stay awake
(on macOS, `caffeinate -dimsu`).

Every agent file opens with its own idempotency check — read the register first,
stop if the assigned work is already past this stage — which is what makes resume
safe.

## Pre-flight

- **The session is on the model the whole round should use.** Agent files use
  `model: inherit`, so every worker inherits it. Check before spawning anything.
- The permission allowlist covers the run — test commands, git, the repo paths. A
  worker blocked on a permission prompt stalls silently; fix the allowlist first
  (see `/fewer-permission-prompts`).
- If the project keeps its env in a canonical file outside the worktrees, every
  worktree's `.env.local` is a **symlink** to it, never a copy. Replace any copy
  found. Env files are never committed or pushed.
- **If that symlink exists, CLI tools can write through it.** Vercel's `vercel
  link` / `vercel pull` are the known case: they write *through* the link into the
  canonical file. Remove the symlink, run the command, delete the `.env.local` it
  wrote, restore the link.

## Also fits

Pre-launch security gates (coderules' ten points as register entries),
test-coverage campaigns, migration and deprecation sweeps, docs-drift rounds.

**Not** for building one feature — that is a dependency chain. Use
`/to-issues` then `/run-issues`.
