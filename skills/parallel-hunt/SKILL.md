---
name: parallel-hunt
description: Run a parallel bug-hunt round — a finder and a fixer working concurrently over a shared register, with ephemeral adversarial gates reviewing every claim and every fix. EXPLICIT INVOCATION ONLY. Use this skill only when the user types the command /parallel-hunt (including /parallel-hunt resume). Never infer it from a request for a bug hunt, a verification round, a hardening pass or a find-and-fix run — say the command exists and let the user choose it.
---

# Parallel hunt

One thin orchestrator session runs the whole round. Workers are background
subagents with fresh contexts, never extra chat sessions. Nobody waits on the user
after launch.

Settled design decisions and the incidents behind them live in `decisions.md`,
next to this file. Read it if you are tempted to change how the round works —
not to run one. The terms below — orchestrator, sweep group, claim gate, lead and
the rest — are defined in `glossary.md`, also next to this file.

## Who runs what

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the orchestrator never pastes a brief.

| Role | Agent type | Effort | Lives for |
|---|---|---|---|
| Finder | `parallel-hunt-finder` | xhigh | one sweep group |
| Fixer | `parallel-hunt-fixer` | high | one batch of fixes |
| Claim gate | `parallel-hunt-claim-gate` | high | one review, then dies |
| Fix gate | `parallel-hunt-fix-gate` | high | one batch, then dies |
| Fix gate, critical | `parallel-hunt-fix-gate-critical` | high | one batch, then dies |
| Promotion | `promotion` | medium | one round end, then dies |

Use the critical fix gate for `severity: critical` entries, or any fix whose diff
touches money, auth or security.

Spawn prompts carry **only** what varies — the sweep group, the register IDs, the
batch size. Everything stable already lives in the agent file, where it caches.

## The register — all state in files

In **the main checkout**, not any worktree, so every agent reads and writes the
same absolute path with no git sync. Four files, split on one test: a thing belongs
in the register only if another agent must read it to do its own job.

```
<main-repo-root>/.scratch/<feature>/register.md      # the index table, live findings only
<main-repo-root>/.scratch/<feature>/round-brief.md   # this round's brief, scope, sweep groups
<main-repo-root>/.scratch/<feature>/leads.md         # standing leads and rulings
<main-repo-root>/.scratch/<feature>/bugs/<ID>.md     # evidence, reproducer, verdicts
```

`register.md` is a table:
`ID | one-line summary | audience | severity | status | owner-notes`.

- **`audience`** is `operator`, `tester` or `agent` — who can see the fault at all.
  The finder writes it with the row, and promotion reads it.
- **`owner-notes` holds a status word and a link to `bugs/<ID>.md`. Nothing else,
  and 200 characters hard.** Both gates refuse a row that breaks it. One round of
  one project reached 5,212 bytes a row because this cell held whole gate verdicts;
  the same sixteen rows under the cap cost about 2.4 KB. The structural rule tells a
  finder what to write and the character count gives a gate something to count.

Per-bug files hold the evidence, the reproducer, the pinning-test path and gate
verdicts. Agents append to their own section; only the owner of a transition
touches `status`.

`round-brief.md` holds what this round is about and dies at round close.
`leads.md` holds what outlives it — leads already examined, and the orchestrator's
rulings. It never rotates; see "Harvesting the leads file".

Status machine, single writer per transition:

- `candidate` — finder only.
- `candidate → open` or `retracted` — claim gate only.
- `open → in-fix → fix-ready` — fixer only.
- `fix-ready → verified`, or back to `in-fix` with written reasons — fix gate only.
- `deferred` — orchestrator, at round end, and only from `open`, `in-fix` or
  `fix-ready`. A `candidate` is gated or deleted, never deferred; `retracted` is
  terminal. **`deferred` means the row is waiting for promotion, and nothing else.**
  It writes no issue file. Nothing in this loop writes an issue file except
  promotion.

**Nothing rotates and nothing is archived.** Three exits bound the register instead.
Promotion takes a row out and into `issues/`; a refusal takes a row out and leaves it
out; `fixed` takes out a row the round already verified, writes nothing, and owes no
reason, because the fix is in the commit and the record is in the bug file. What stays
is live findings only, so the file's length is the promotion backlog — a number worth
being able to read. A register that rotates on size or on the round boundary needs a
guard against firing mid-run; with no rotation there is nothing to guard.

**`fixed` is an exit in its own right and never a kind of refusal.** Split out on
the human's ruling, 2026-08-06. Before it, a round that fixed thirteen faults
reported thirteen refusals into the daily brief, where one word would have
overturned them and minted thirteen issue files for work that had already shipped.

**Retractions clean up after themselves.** The claim gate may touch nothing but
status and its verdict, and the finder is dead, so the orchestrator deletes the
finder's regression test file for that bug ID when it records a retraction. A
deliberately failing test left in the suite poisons every later green judgement.

At round end commit `register.md`, `leads.md`, `bugs/` and the finder's regression
test directory — those paths only — and delete `round-brief.md`. Never commit the
whole `.scratch/<feature>/` directory: a run's ledger, journal and issue files live
there too, and committing them mid-run puts half-written run state on main.

## Promotion — the only door into `issues/`

**No role in this loop writes an issue file.** Finders, fixers, gates and the
orchestrator all write register rows. Promotion is the last phase of the round that
resolves findings, after the round-end commit above, and the only step that creates
an issue. `/run-issues` carries the same phase, on the
same rule and the same register.

A finding is out by default. Promotion is the work that gets it in.

**A fresh `promotion` subagent does the work, never the orchestrator.** Writing issue
files is repetitive file work arriving at the moment the orchestrator's context is
most expensive, and the orchestrator would be reading rows it has no other reason to
hold. It spawns the agent, gets two lists and a count back, and puts them in the
round report.
The rule below lives in the agent file too, where it caches.

Promotion runs on that rule and applies its own answer. It never waits. Every row is
resolved one of three ways:

- **Fixed** — the row is already at `verified`. **Take this exit first, before you
  look at audience or severity.** Delete the row, write nothing, and report it as a
  bare count. A fault the round fixed needs no issue: the fix is in the commit and
  the record is in `bugs/<ID>.md`.
- **Promoted** — the row clears the audience-and-severity thresholds. Write the issue
  file, then delete the row.
- **Refused** — everything else. Delete the row and give the reason in the round report.

**The thresholds live in [`agents/promotion.md`](../../agents/promotion.md) and
nowhere else.** This file and `run-issues/SKILL.md` both carried "operator at any
severity" for a day after the human set a `medium` floor on `operator` (2026-08-09),
and a run brief repeated the stale figure. Name the exits here; read the numbers
there.

**`fixed` is never reported as a refusal**, and the ordering above is what enforces
it. The human overturns a refusal with one word, so a round's thirteen successful
fixes listed as thirteen refusals put a trap on their only control: one word would
mint thirteen issue files for work that had already shipped. Ruled 2026-08-06. This
section still said "two ways" a day after that ruling landed forty lines above it;
corrected 2026-08-07.

A promoted row becomes an issue file carrying:

- `Status: needs-harden`. A local file has no reporter, so there is nobody to ask
  for more, and `needs-info` is a dead end there. `/harden-issues` sharpens it from
  evidence instead.
- One category role, from the project's own triage set.
- A link to `bugs/<ID>.md`. Promotion copies no evidence into the issue file.

**The human holds the veto, through `/daily-brief`.** The round report lists every
promotion and every refusal, and the brief carries both to them. Overturning either
is one word in the brief. **`fixed` is a count only, and carries no control** — it
is not a decision and the human is offered none over it. A step they have to invoke
by hand is a step somebody forgets, and then the register grows in place of the
issue directory.

**Anything needing the human's hands, rather than their judgement, goes somewhere
else.** A secret, an env var, an OAuth client, a DNS record at a registrar, a console
setting — anything the repo cannot do to itself — is written as a numbered action,
one action per number, with one line of what is blocked on it, to the project's
pending-actions file, if it keeps one. The round report is history the moment the
branch merges; that file is the list the human actually reads.

## Harvesting the leads file

`leads.md` never rotates, so it gets emptied by hand. The human runs this every few
months, or when the file gets long. For each entry, choose one of three actions:

1. **A rule true of a tool in any repository** — of the database, the framework or
   the test runner the entry names. Move it into your own copy of this skill file
   as a rule, and delete the entry. Once the skill carries it, no finder needs the
   list.
2. **A rule true only of this product** — it names a table, a route or a term this
   codebase owns. It stays in the leads file. It is not general, whatever it looks
   like, and promoting it into a published skill would carry the product's
   internals out with it.
3. **An entry about one file at one version** — it carries the commit it was judged
   at. Delete it once that file has moved on, which one `git log` answers.

A skill that tells you to create a file owes you the way to empty it. Without this,
the pack ships the same fault the split removes: nothing here ever told anybody to
archive a register, and archived registers piled up on disk anyway.

## Code ownership — the merge-tax rule

- **Finder** writes the register and NEW test files, one per bug, named by bug id,
  in a regressions directory of the project's own test layout. It never edits
  existing suites and never touches shipped code, not even to help.
  **Where the project has no test layout of its own, that directory is
  `tests/regressions/`** — the pack's default, and the path the agent files name.
- **Fixer** owns shipped code, unit fakes and fixtures. It may flip an expectation
  in one of those regression files only when the fix intentionally changes the
  pinned behaviour, and must say so in `bugs/<ID>.md`. Unexplained touches are an
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

**A prohibition in a brief names the SYSTEM, not the verb.** Every "do not" carries
the forbidden thing AND the permitted one, with an absolute path wherever a path
exists. Three faults in one `/run-issues` batch shared one shape: "QA is the only
WRITABLE database" constrained the operation and left production reachable, so a
verify gate read production with a service-role key; "a probe script needs a
directory holding `node_modules`" named no home, so three files landed at the shared
worktree root; and a brief naming no register path sent two gates to the worktree
copy instead of the main checkout's. A brief that constrains the ACT while leaving
the PLACE unnamed gets a different answer from every agent. (Adopted 2026-08-09.)

Stay thin — the orchestrator's context is the only one that lasts all round.

1. **Never read bug-file contents or diffs.** Read `register.md` status lines and
   worker return summaries. Judgement belongs to the gates; the moment the
   orchestrator starts forming opinions about bugs, it stops being thin.
2. Write `round-brief.md` with the brief, the target scope and the sweep groups,
   create an empty `register.md` if the feature has none, then spawn finder and
   fixer concurrently. The fixer idles politely until entries reach `open`.
3. On each worker return, spawn the right gate and/or successor.
4. **On each gate return, check it wrote a verdict, before you act on the
   status.** One command against the bug file in the main checkout:

   ```bash
   python3 ~/.claude/skills/lib/check_verdict.py --file <bugs/ID.md> --section "## Claim gate"
   python3 ~/.claude/skills/lib/check_verdict.py --file <bugs/ID.md> --section "## Fix gate"
   ```

   It exits non-zero when the heading is absent, when nothing sits under it, or
   when a row still reads `pending`. A non-zero exit means the gate died or wrote
   somewhere else, so the entry keeps its old status and the gate is re-spawned.
   **A gate that returned empty has not retracted anything and has not verified
   anything** — two adversarial gates died at the weekly usage limit during one
   workflow audit and wrote nothing, and nothing mechanical noticed.

   This does not break rule 1. The check reads the file; you read an exit code
   and one line.
5. Loop until the finder returns dry twice **and** no entries remain `open`,
   `in-fix` or `fix-ready`.
6. Round end, in this order: mark leftovers `deferred`; spawn one `promotion` agent
   over every row, giving it the project's issue directory path and its numbering
   rule; delete the heartbeat cron; delete `round-brief.md`; commit. Then
   report — verified fixes, rejected fixes, retracted claims, and the two lists
   promotion returned. Say plainly what was left undone; a round that reports only
   its wins is not a report.

   Do not promote rows yourself. Rule 1 holds all the way to the end of the round,
   and spawning is what keeps it holding: the agent reads the rows, and you read two
   lists.

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

- **One skill per checkout.** Refuse to start if `git status` is dirty, or if
  `.scratch/<feature>/run.md` shows a run that is not at `awaiting-merge` with its
  branch merged. A hunt beside a live run puts two writers in one tree and lands
  deliberately failing tests in the run's finale.
- **One tree, one branch.** Finder and fixer both work in the main checkout on
  `hunt/<scope>`, cut at launch. A second worktree hides the finder's pinning
  tests from the fixer. Exactly one finder and one fixer live at a time. The
  branch goes to the human at round end; the orchestrator never merges to main.
- **The session is on the model the whole round should use.** Agent files use
  `model: inherit`, so every worker inherits it. Check before spawning anything.
- The permission allowlist covers the run — test commands, git, the repo paths. A
  worker blocked on a permission prompt stalls silently; fix the allowlist first.
- **Creating a worktree includes installing dependencies and making the
  `.env.local` symlink. If either fails, the round refuses to start.** Not a
  checklist item to remember afterwards — part of what "the tree is ready" means.
  One shell command, 30 to 60 seconds per worktree, and it saves more than it
  costs the first time it stops a finder diagnosing a false green that was really
  a missing environment file. (Adopted 2026-08-07.)
- If the project keeps its env in a canonical file outside the worktrees, every
  worktree's `.env.local` is a **symlink** to it, never a copy. Replace any copy
  found. Env files are never committed or pushed.
- **If that symlink exists, CLI tools can write through it.** Vercel's `vercel
  link` / `vercel pull` are the known case: they write *through* the link into the
  canonical file. Remove the symlink, run the command, delete the `.env.local` it
  wrote, restore the link.

## Also fits

Pre-launch security gates (the ten points under "The pre-launch gate" in
[`steering/coderules.md`](../../steering/coderules.md) as register entries),
test-coverage campaigns, migration and deprecation sweeps, docs-drift rounds.

**Not** for building one feature — that is a dependency chain. Take an issue file
(with a `Status:` line, acceptance criteria, and a `## Must still be true`
section) through `/run-issues` instead.
