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

Use the critical fix gate for `severity: critical` entries, or any fix whose diff
touches money, auth or security.

Spawn prompts carry **only** what varies — the sweep group, the register IDs, the
batch size. Everything stable already lives in the agent file, where it caches.

## The register — all state in files

**`register.md` is GENERATED.** Its content lives in shards — one per WRITER,
under a directory named for the worktree that owns it — and every writer appends
to its own shard inside its own tree and commits it on that tree's branch.
`collect_shards.py` concatenates them. This is ticket 38 of the pilot-delivery
map, the one-run-per-feature layout ticket, rulings 5, 14 and 15, 2026-09-05: one
file with many writers loses a row silently whenever two of them write at once,
and nothing reports the loss.

**One writer is one shard, not one tree.** A run's two gates run at once in one
tree, and two agents editing one file rebuild the fault. Your shard is named
after the row prefix you stamp.

**A hunt is the exception, on purpose: the whole round shares ONE shard, named
after the round, inside the hunt's own worktree.** The finder writes a row and
the fixer and both gates then change its `status` and `owner-notes` in place,
so the row has to sit in a file they all hold. That is the status machine this
skill has always had, and sitting 3 neither widened nor narrowed it — two of
them writing at the same moment can still lose an edit, as they could when the
register was one file. What sitting 4 changed is where the file sits: the
hunt's worktree, so no run and no other session holds it. Named as a fact.

Ask for it rather than working the path out:

```bash
python3 ~/.claude/skills/workflow/lib/collect_shards.py --kind register \
    --feature <feature> --my-shard --prefix <your row prefix>
```

Read the whole register by printing it from the shards into your session
scratchpad, then read that file. The print writes nothing, so a hunt's worker
never touches the main checkout. The collector refuses to write main's board
from a worktree (ruling `q-fin-44052e-02`, 2026-09-30), and a write from here
would change main's tracked `register.md` under whatever run is live there. The
register runs to thousands of lines, so read the file rather than the output:

```bash
python3 ~/.claude/skills/workflow/lib/collect_shards.py --kind register --feature <feature> --print > <session scratchpad>/register.md
```

**Writers append to a shard. Readers print, then read.** A write to
`register.md` itself is refused by `generated-file-guard.py` in the hooks, which
names your shard in the refusal.

Five paths, split on one test: a thing belongs in the register only if another
agent must read it to do its own job.

```
<hunt-worktree>/.scratch/<feature>/register.d/<hunt-id>/<prefix>.md  # this round's rows, one shard
<main-repo-root>/.scratch/<feature>/register.md           # generated: every shard, in order; a worker prints it instead
<hunt-worktree>/.scratch/<feature>/round-brief.md         # this round's ledger: header, round block, brief, scope, sweep groups
<hunt-worktree>/.scratch/<feature>/round-journal.md       # lock waits and breaks, halts, anything the brief must not carry
<hunt-worktree>/.scratch/<feature>/leads.md               # standing leads and rulings; reaches main at merge
<hunt-worktree>/.scratch/<feature>/bugs/<ID>.md           # evidence, reproducer, verdicts
```

The shard directory is `<hunt-id>` because `collect_shards.py` names a shard
directory after the worktree's own directory name, and the worktree is cut at
`.claude/worktrees/<hunt-id>`. Move the worktree and the shard directory moves
with it.

Everything a round writes lives in the hunt's own worktree and lands in main when
The human merges the hunt branch (ticket 38, the one-run-per-feature layout ticket,
ruling 6, sitting 4). The one exception is the generated register, which sits in
the main checkout; a worker reads it with `--print` and never writes it. A hunt
cut from main before a run merges hunts the code as main holds it, without that
run's fixes; that is a fact about the cut, not a wait. Name any run at
`awaiting-merge` in the brief text at launch, so a finder that reproduces one of
its fixes on the old code is read against it.

`register.md` is a table:
`ID | one-line summary | audience | severity | status | origin | owner-notes`.

- **`origin`** names where the fault came from: the issue and the run that shipped
  the code it is in, written `<issue>/<run>`, with `unknown` legal for either half
  or for both. It is what makes an escaped fault countable, and nothing else in the
  record carries it. `origin-row-guard.py` in the hooks refuses a row without it and
  a table that declares no such column; `check_origin.py` grades a file that already
  exists. A table declaring no `origin` column is history and is never graded, which
  is how the count starts the day the key landed and backfills nothing. (Ticket 37 of
  the pilot-delivery map, ruling 7, ruled by the human 2026-09-05.)
- **`audience`** is `operator`, `tester` or `agent` — who can see the fault at all.
  The finder writes it with the row, and the human reads it when he turns a row into
  an issue.
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
  (Outside this loop, a `/run-issues` commit step also closes rows to `verified`
  where its commit fixed them — rule F6, 2026-08-27.)
- A hardening-pass or seam-agent row enters at `open` — or at `deferred` where
  it only waits for the human. No claim gate runs over it: the pass's evidence
  bar is the gates' own. (Ruled by the human 2026-08-29.)
- `deferred` — orchestrator, at round end, and only from `open`, `in-fix` or
  `fix-ready`. A `candidate` is gated or deleted, never deferred; `retracted` is
  terminal. **`deferred` means the row is waiting for the human, and nothing else.**
  It writes no issue file. Nothing in this loop writes an issue file.

**Nothing rotates and nothing is archived.** A row leaves the register by the human's
hand, when he turns it into an issue file or refuses it. A done row, at `verified` or
`fixed`, leaves by `~/.claude/skills/workflow/lib/retire_done_rows.py`, which a run's finale and
`/daily-brief` both run: it appends the row's id to a `closed` shard, and the bug file
keeps the record (issue 44 of the tracker-tooling set, ruling `q-h0925-36-1`). A register that rotates on size or on the round boundary
needs a guard against firing mid-run; with no rotation there is nothing to guard.

**Retractions clean up after themselves.** The claim gate may touch nothing but
status and its verdict, and the finder is dead, so the orchestrator deletes
`tests/regressions/<ID>.test.ts` when it records a retraction. A deliberately
failing test left in the suite poisons every later green judgement.

**A fix rejection on non-executable PROSE is fixed by deleting the claim, never by
restating it.** A fix for an over-claim is itself a new claim with its own
falsifiable surface, so on this class more precise and more likely wrong move
together. Second rejection → delete down to the minimal sentence the gate cannot
falsify; re-assert only by making the claim executable. **The claim is part of the
deliverable**, so a bug file's diff summary and its recommended-fix prose are
graded like the diff. One canonical statement per claim — everywhere else cites
`file:line` and asserts nothing. `/run-issues` carries the same rule, at its
"One canonical statement per claim" paragraph in `run-issues/SKILL.md`.

Round 9 is the measurement: four fix rejections across sixteen entries and four
assigned tasks, and **not one was a wrong diff**. All four were prose, and three of
them were caught only because a gate re-measured a sentence nobody had asked it to
check (`decisions.md:91-108`).

At round end, in the hunt's worktree on the hunt branch, commit
`register.d/<hunt-id>/`, `round-journal.md`, `leads.md`, `bugs/` and
`tests/regressions/`, those paths only, and delete `round-brief.md`. **Never commit the generated `register.md`**: it falls out of
the shards, and committing it puts one tree's snapshot of every other tree's
rows on the branch. Never commit the whole
`.scratch/<feature>/` directory: a run's ledger, journal and issue files live there
too, and committing them mid-run puts half-written run state on main.

## The round block — built at launch, pasted into every spawn

A hunt is a run for isolation (ticket 38, the one-run-per-feature layout
ticket, ruling 22): it takes a hunt id, a worktree, a QA workspace and user, the
dev server by name, and the Zoho lock, exactly as `/run-issues` does, and its
round end deletes the workspace. So `round-brief.md` is a ledger with the same
header a run's `run.md` carries, and the places a role needs travel in one
block below that header, pasted verbatim into every spawn prompt.

**The header is the first thing in the file, and the block follows it.** Every
script that reads a ledger stops at line 60, and the seed refuses a brief whose
title line and `Worktree:` line are not there (`ledgerHeaderFault` in
`scripts/lib/run-workspace.mjs`). The brief text, the scope and the sweep groups
come after.

```
# Round brief — <scope> (hunt `<hunt-id>`)

Owner: session <session id> (orchestrator)
Worktree: `<absolute path of the hunt's worktree>`
Branch: `hunt/<hunt-id>`
```

**`model_map.py` writes two more header lines at launch, under `Worktree:`:**
`Model map at launch:` and `Role effort at launch:`, all twelve loop roles named
in each (ticket 39 of the pilot-delivery map,
every-worker-inherits-the-session-model, rulings 4, 7 and 8). Ruling 8 asks a
hunt for a ledger carrying the same header a run's `run.md` carries; ticket 38
already made `round-brief.md` that ledger, so the lines go here and no second
hunt state file is minted. Run this before the first spawn and paste what it
prints:

```
python3 ~/.claude/skills/run-issues/model_map.py "<everything after /parallel-hunt>"
```

**A hunt takes its map with the same word and the same parser** (ruling 20):

```
/parallel-hunt <scope> models: finder=fable claim-gate=fable fixer=opus
```

The grammar, the default file, the resolution and the refusals are all the run's,
documented in `~/.claude/skills/run-issues/SKILL.md` under "Run state". Two of
the twelve keys matter most here — `finder` and `fixer` — and the gates that
check them are `claim-gate` and `fix-gate`/`fix-gate-critical`. **No gate may sit
below the worker it checks** (ruled 2026-08-15,
`~/.claude/rulings.md:99-121`), so `finder=fable` needs `claim-gate=fable` beside
it: the bare `finder=fable fixer=opus` line is refused on any session below
`fable`. Exit 1 is a launch-time stop — spawn nothing and hand the human the refusal.

The seed then writes `QA workspace:` and `Sign-in user:` under `Worktree:`
itself, so no uuid passes through a keyboard. The fenced id on the title line is
what `find_live_ledger.py`, `sweep-run-workspaces.mjs` and `dev-signin-link.mjs`
read; the `Owner:` line is what makes the round live to all three, under the
one rule a run's ledger already follows. Then the block:

```
Hunt:             <hunt-id>
Worktree:         <absolute path of the hunt's worktree; every role works here, and reads the register with collect_shards.py --print>
Branch:           hunt/<hunt-id>
QA workspace:     <the id on round-brief.md's QA workspace: line, seeded for this round alone; every fixture script run in this worktree reads it off round-brief.md itself>
Sign-in user:     <the email on round-brief.md's Sign-in user: line>
Sign-in link:     <the dev-signin-link.mjs command from the pre-flight, with this hunt id filled in; the port comes from the preview_start result>
Dev server:       <the launch.json entry by name; it carries autoPort, so the port exists only in the preview_start result of the spawn that started it>
Zoho lock:        <the zoho-live-lock.mjs command from the pre-flight, with this hunt id and the journal path filled in>
Register shard:   <absolute path from collect_shards.py --my-shard, run inside the worktree>
Bugs:             <absolute path of <hunt-worktree>/.scratch/<feature>/bugs/>
Journal:          <absolute path of <hunt-worktree>/.scratch/<feature>/round-journal.md>
Leads:            <absolute path of <hunt-worktree>/.scratch/<feature>/leads.md>
```

A field you cannot fill stops the spawn. Two of them are refused rather than
remembered: the seed will not write into a brief with no header, and the
sign-in script will not mint on any host but this hunt's.

## The register is the inbox

**No role in this loop writes an issue file**, and the orchestrator writes none
either. Finders, fixers, gates and the orchestrator all write register rows. The round
ends with its leftover rows at `deferred`, and they wait in the register for the human,
who turns a row into an issue file by his own hand. `gate-issue-write-guard.py`
refuses any subagent a write that creates a file under `.scratch/<feature>/issues/`
(issue 36 of the tracker-tooling set); an edit to an issue file that exists still
passes.

**Anything needing his hands, rather than his judgement, goes somewhere else.** A
secret, an env var, an OAuth client, a DNS record at a registrar, a console setting —
anything the repo cannot do to itself — is written as a numbered action, one action per
number, with one line of what is blocked on it, under `Do` in `~/.claude/pending.md`.
Never make a repo-local copy. The round report is history the moment the branch merges;
that file is the list the human actually reads.

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

- **Finder** writes the register and NEW files at
  `tests/regressions/<bug-id>.test.ts` — one per bug. It never edits existing
  suites and never touches shipped code, not even to help.
- **Fixer** owns shipped code, unit fakes and fixtures. It may flip an expectation
  in `tests/regressions/` only when the fix intentionally changes the pinned
  behaviour, and must say so in `bugs/<ID>.md`. Unexplained touches are an
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

**A prohibition in a brief names the SYSTEM, not the verb.** Every "do not" carries the
forbidden thing AND the permitted one, with an absolute path wherever a path exists. Three
faults in the 2026-08-09 `/run-issues` batch shared one shape: "QA is the only WRITABLE
database" constrained the operation and left production reachable, so a verify gate read
production with a service-role key; "a probe script needs a directory holding `node_modules`"
named no home, so three files landed at the shared worktree root; and a brief naming no
register path sent two gates to the worktree copy instead of the main checkout's. A brief
that constrains the ACT while leaving the PLACE unnamed gets a different answer from every
agent. Adopted by the human, 2026-08-09.

Stay thin — the orchestrator's context is the only one that lasts all round.

1. **Never read bug-file contents or diffs.** Read `register.md` status lines and
   worker return summaries. Judgement belongs to the gates; the moment the
   orchestrator starts forming opinions about bugs, it stops being thin.
2. Write `round-brief.md` in the hunt's worktree with the round block, the
   brief, the target scope and the sweep groups, then spawn finder and fixer
   concurrently, each prompt carrying the block. Nothing has to create a
   register: the shards make it, and a feature with no shard has no register to
   make. The fixer idles politely until entries reach `open`.
3. On each worker return, spawn the right gate and/or successor.
4. **On each gate return, check it wrote a verdict, before you act on the
   status.** One command against the bug file in the hunt's worktree, at the
   `Bugs:` path in the round block:

   ```bash
   python3 ~/.claude/skills/workflow/lib/check_verdict.py --file <bugs/ID.md> --section "## Claim gate"
   python3 ~/.claude/skills/workflow/lib/check_verdict.py --file <bugs/ID.md> --section "## Fix gate"
   ```

   **It has four refusals, not three.** It exits non-zero when the heading is
   absent, when nothing sits under it, when a row still reads `pending`, and when
   the section sits above the newest `Implementation record, attempt N` heading —
   `stale`, meaning the section grades an earlier diff. `stale` closes the
   2026-08-19 fault: issue 390a's attempt-2 gates died before writing, the file
   still held attempt 1's rejections under the same headings, and the check passed
   both (`check_verdict.py:28-34`). A non-zero exit means the gate died, wrote
   somewhere else, or judged an older attempt, so the entry keeps its old status
   and the gate is re-spawned.
   **A gate that returned empty has not retracted anything and has not verified
   anything** — two adversarial gates died at the weekly usage limit during the
   2026-08-15 workflow audit and wrote nothing, and nothing mechanical noticed.

   This does not break rule 1. The check reads the file; you read an exit code
   and one line.
5. Loop until the finder returns dry twice **and** no entries remain `open`,
   `in-fix` or `fix-ready`.
6. Round end, in this order: mark leftovers `deferred`;
   **take the five readings below, which must happen before the brief is
   deleted**; delete this round's QA workspace; delete the heartbeat
   cron; delete `round-brief.md`; commit. Then report — verified fixes, rejected
   fixes, retracted claims, the rows left `deferred` and the count of rows at
   `verified`, and the branch and
   worktree the human merges. Say plainly what was left undone; a round that reports
   only its wins is not a report.

   **What a round cost, and what each role ran on.** Until ticket 39 of the
   pilot-delivery map, every-worker-inherits-the-session-model, a hunt had no cost
   script at all, so a hunt's cost was not measured whatever the model. Its sitting 3
   gave the run's four scripts a `--batch` and one set now serves both (ruling 12).
   Run all five with this round's hunt id and paste the output into the round report:

   ```
   python3 ~/.claude/skills/run-issues/run_costs.py --batch <hunt-id> --kind hunt
   python3 ~/.claude/skills/run-issues/harness_cost.py --batch <hunt-id>
   python3 ~/.claude/skills/run-issues/orchestrator_cost.py --batch <hunt-id>
   python3 ~/.claude/skills/run-issues/run_timings.py --batch <hunt-id>
   python3 ~/.claude/skills/run-issues/run_quality.py --batch <hunt-id>
   ```

   **The fifth is sitting 4's, and it answers a different question from the other
   four** (ticket 39, deliverable 4, rulings 21.3 and 22). They say what the round
   cost. It says whether the round's model trial may be READ: the per-role table
   built from the transcripts, and the verdict `holds`, `VOID` or `not measured`.
   `VOID` means at least one mapped spawn ran on something other than what
   `round-brief.md` asked for, and `~/.claude/hooks/model-landed-check.py` wrote the
   `**MISMATCH**` line naming it. **A void trial stops nothing and reverses nothing**
   — the fixes are still good fixes, the branch still goes to the human, and the only
   thing void is the comparison against another round. Paste it into the round report
   whole. It prints no per-issue figures, because a hunt has no issues.

   **`--kind hunt` on the first one**, so it reads
   `run_costs.py --batch <hunt-id> --kind hunt`. The line goes into
   `.scratch/workflow-audit/runs.jsonl` beside the runs, and `run-costs.md` draws it
   with `hunt` in its own column.

   **This REVERSES the old `--no-append` rule, and the reason is worth keeping.**
   That rule existed because a hunt row in a table of run rows is read as a run for
   as long as the table lives, and the columns are a run's — issues shipped, per
   issue, correction rounds — none of which a hunt has. Ticket 37 of the
   pilot-delivery map, ruling 11 (2026-09-05), removes the reason rather than the
   rule: the record carries a `kind` field, and ruling 12 compares a line against the
   previous line OF THE SAME KIND, never the line above it. So a hunt can never be
   read as a run. The columns a hunt cannot fill read `not measured`, which is a
   different statement from zero.

   What this buys: until now a hunt's cost was never recorded at all, whatever model
   it ran on, which is exactly what ticket 39 ruling 12 set out to end.

   **The order above is not a preference. Every one of them finds the session by
   reading `round-brief.md`**, so all five must run while it still exists. Once it is
   deleted no ledger names this hunt and the round can never be measured — unlike a
   run, whose `run.md` is committed and readable for ever. **`run_quality.py` loses
   more than the others do**: it also reads `round-journal.md`, which sits beside the
   brief, so a round that deletes first can never say whether its own trial held.
   **A reading that refuses is never a halt**: it prints what it could not read, exits
   0, and the round end carries on.

   **No figure any of them prints is added across models** (ruling 11, and the human's
   ruling of 2026-09-06). Every token cell names its own model. To read a model trial,
   compare the SAME ROLE across rounds; for spend, read `/usage` by hand.

   The workspace goes before the brief, because the brief is where its id is. Run
   the repo's own delete command, spelt as that repo's `.claude/run-classes.json`
   spells it. In TenderFlow it reads

   ```
   node --env-file=<the repo's canonical env file> scripts/delete-run-workspace.mjs --batch <hunt-id> --ledger <round-brief.md>
   ```

   **A repo with no `scripts/delete-run-workspace.mjs` has no workspace to delete.**
   Say so in the round report and go on. OrderFlow is such a repo today.

   It audits every foreign key from `workspaces` off `pg_constraint` and refuses
   unless all cascade and the row's name carries this hunt id. **A refusal is
   exit 1 with the cause printed, and the round end continues**: put the printed
   migration road in the round report as an action on the human, with the workspace
   id, and go on. Once the brief is deleted no ledger names that workspace, so
   the daily brief's sweeper reports it as an orphan every day and never deletes
   it; the human deletes it by id once the migration is in.

   Leave every row in the register for the human. The round report names the rows left
   `deferred`; it resolves none of them.

## Auto-resume across usage limits

**The register resumes a round. The cron only saves short waits** — it reaches no
further than a five-hour window the same session sits through. A weekly limit
resetting days out is resumed by a human re-invoking `/parallel-hunt resume`.

**Staleness is a FILE's mtime, never worker progress.** Every status transition
writes a register shard, so a shard's mtime moves whenever the round moves and
nobody can forget to write it. Read the shards, never the generated
`register.md`: that file's mtime moves when the collector last ran, which is not
when the round last moved. `collect_shards.py --mtime` answers with the newest
shard's, in epoch seconds. A long finder sweep, or a long fix, moves no status line for an
hour — so "no worker progress" cannot mean "dead", and only a stale mtime can.
`/run-issues` refuted the handwritten alternative twice in one run, on a runner who
had already diagnosed the failure mode (`run-issues/SKILL.md`, the paragraph
beginning "The ledger carries an owner line").

Create the wakeup anyway at launch (CronCreate, every ~30 min): "Check that
`<hunt-worktree>/.scratch/<feature>/round-brief.md` exists, and read
`python3 ~/.claude/skills/workflow/lib/collect_shards.py --kind register --feature <feature> --mtime`
— do not read the rest of either file. If the brief is there and the register's mtime is over 60 minutes
old, resume from register state; otherwise do nothing." `round-brief.md` is the
marker because it is written at launch and deleted at round end, so its presence is
what "a round is open" means. Firings that land while rate-limited simply fail; the
first after the reset revives the round. Delete the cron at round end. Remind the
user once that the machine must stay awake (`caffeinate -dimsu`).

**`/parallel-hunt resume` is typed inside the hunt's worktree, and
`machine-preflight.py` refuses it anywhere else**, naming the open hunts. The
listing is `python3 ~/.claude/skills/run-issues/find_live_ledger.py --list`,
which prints every live ledger with its kind in the last column, `hunt` for a
round brief. Nothing picks a round by freshness, and a resume from the wrong
tree would spawn workers into a tree that holds no round.

Every agent file opens with its own idempotency check — read the register first,
stop if the assigned work is already past this stage — which is what makes resume
safe.

## Pre-flight

- **The ceiling is refused at the prompt, not checked here.**
  `~/.claude/hooks/machine-preflight.py` refuses a second `/parallel-hunt` while
  a `round-brief.md` is live in any worktree (ticket 38, the one-run-per-feature
  layout ticket, ruling 20: the ceiling is refused, not advised), and it has no
  override word. A hunt beside a live run is allowed: the old refusal existed
  because both shared the main checkout, and sitting 4 removed the cause with
  the rule (ruling 6: a hunt in its own worktree). Refuse to start only if the
  main checkout's `git status` is dirty, because the worktree is cut from it.
- **Mint the hunt id and cut the hunt's own worktree.** The id is `hunt-` plus
  six hex characters (`openssl rand -hex 3`), and it is the same id the branch
  carries, the workspace name carries and the shard directory carries. Then, from
  the main checkout:

  ```
  git worktree add <main-repo-root>/.claude/worktrees/<hunt-id> -b hunt/<hunt-id> main
  ```

  Finder and fixer both work in that one tree, on that one branch. They stay
  together on purpose: a second tree would hide the finder's pinning tests from
  the fixer, and a failing pinning test lives on the hunt branch until merge and
  never enters a run's finale. Exactly one finder and one fixer live at a time.
  The branch goes to the human at round end; the orchestrator never merges to main.
- **Seed this round's QA workspace; the script writes its two lines into the
  brief.** Inside the hunt's worktree, once `round-brief.md` exists with the
  header above, run the repo's own seed command, spelt as that repo's
  `.claude/run-classes.json` spells it. In TenderFlow it reads

  ```
  node --env-file=<the repo's canonical env file> scripts/seed-run-workspace.mjs --batch <hunt-id> --ledger <round-brief.md>
  ```

  **A repo with no `scripts/seed-run-workspace.mjs` seeds no workspace**: write one
  line in the brief saying so, leave `QA workspace:` and `Sign-in user:` out, and
  carry on. OrderFlow is such a repo today, and the paragraph below describes the
  script where it exists rather than asking for one here.

  It creates one auth user, one `workspaces` row named `run-workspace <hunt-id>`
  and one `admin` membership, idempotently, behind `scripts/lib/db-target.mjs`,
  and writes `QA workspace:` and `Sign-in user:` into the brief (ruling 22: a hunt
  is a run for isolation; ruling 3: one workspace row per run). **Every fixture
  script in `scripts/` run inside the hunt's worktree reads that `QA workspace:`
  id off the brief itself**, through `seedWorkspaceId` in
  `scripts/lib/run-workspace.mjs`, and refuses a `SEED_WORKSPACE_ID` naming any
  other workspace (ticket 38, the one-run-per-feature layout ticket, sitting 5), so a
  finder or fixer sets nothing. The round end
  deletes the workspace by that id. While the brief's
  `Owner:` line reads live the daily brief's sweeper keeps the workspace
  whatever its age, exactly as it keeps a live run's; a round whose session died
  past the cron's reach is resumed from its worktree or its brief is deleted by
  hand, and there is no clock that decides for you.
- **The finder signs in as this round's user, on this round's host.** The dev
  server entry carries `autoPort`, so the port exists only in the `preview_start`
  result of the spawn that started it, and the finder drives it at
  `<hunt-id>.localhost:<port>`, never bare `localhost`: a browser cookie is scoped
  to the host and not the port, so two servers on `localhost` share one session
  (measured in the sitting 2 rehearsal). The link comes from the repo's own
  sign-in-link command, spelt as its `.claude/run-classes.json` spells it. In
  TenderFlow that reads

  ```
  node --env-file=<the repo's canonical env file> scripts/dev-signin-link.mjs --batch <hunt-id> --site http://<hunt-id>.localhost:<port from the preview_start result>
  ```

  **Where the repo has no `scripts/dev-signin-link.mjs`, sign in the way that repo
  documents** and record which road you took; never invent a link minter.

  `dev-signin-link.mjs --batch` refuses any other host, and a bare email typed
  inside the hunt's worktree is refused when the brief names another user.
- **The live Zoho suites run only through the lock wrapper.** One organisation,
  one lock file outside every repo, and the second holder waits (ruling 4:
  serialise the suites; ruling 13: the lock is a file outside every repo, keyed
  by organisation id). Pass the whole directory to one wrapper, and the journal,
  so a wait or a thirty-minute break is written where the round end reads it;
  the harness refuses a live context the wrapper did not start:

  ```
  node --env-file=<the repo's canonical env file> scripts/zoho-live-lock.mjs --batch <hunt-id> --journal <round-journal.md> -- npx vitest run src/lib/zoho/live
  ```

  **That wrapper is TenderFlow's.** A repo with no live Zoho suites and no
  `scripts/zoho-live-lock.mjs` holds no quota here and skips this bullet whole.
  OrderFlow's CLAUDE.md rules out a Zoho integration outright.
- **Every spawn carries its own role's model, read off `round-brief.md`.** The
  five hunt roles — `finder`, `fixer`, `claim-gate`, `fix-gate`,
  `fix-gate-critical` — are named on the brief's `Model map at launch:` line,
  which the launch line writes (ticket 39 of the pilot-delivery map, rulings 4,
  10 and 20). Take this role's value and pass it in the Agent call's `model`
  field. `~/.claude/hooks/model-map-gate.py` refuses any other value and a
  missing one, and its refusal names the exact value to reissue; it is never a
  halt. The line may still carry a promotion model; nothing in the round spawns
  that role.

  This bullet said the opposite until 2026-09-05: agent files use
  `model: inherit`, so every worker inherits the session's tier. The twelve agent
  files still say `inherit`, so a spawn by hand outside a round is unchanged
  (ruling 9), but a round with a brief takes its models from the brief.

- **Record the session model in the register, and qualify a null result by it.**
  A round on any tier is a valid round, and it is also the first evidence at that
  tier. **A null result -- "no bugs found" -- from a tier with no track record is
  not evidence of absence, and may not be reported as one.** This loop has no
  downstream check on a finder's miss: a weak finder and a clean codebase produce
  the same empty register, which is why the tier is recorded and the null result
  qualified. (Generalised by the human, 2026-08-23, answering C8 of the skills audit.
  This bullet read "The session model is Opus 5" -- a pinned model name goes stale
  the day a new model ships, and a stale pin gets edited away with the caution
  inside it. `run-issues/SKILL.md` carries the same rule for a run.)
- **Verify the allowlist, never assert it.** Dry-run every command class this
  round will use, in no-op form, before spawn #1. A miss is a launch-time blocker;
  mid-round it is a worker blocked on a prompt, stalling silently. (The text this
  replaces asserted coverage — "the permission allowlist covers the run" followed
  by an illustrative list. Both halves are the fault. `/fewer-permission-prompts`
  writes the rules; this bullet proves they hold.)

  **Refuse to spawn while any class is refused or unverified.** Never start a
  round intending to approve a prompt later. The whole value of this check is that
  it fails while the human is still at the keyboard.

  **Derive the list from the roles THIS round spawns, not from this bullet.** What
  follows is what today's roles need. It is a floor, not a definition. Walk each
  role the round will spawn and ask what it shells out to.

  - **Finder** — the test runner on single files, wide greps, and **starting the
    dev server** by name from the repo's `.claude/launch.json`, because it hunts
    the live system rather than the code's intentions. On this repo that is
    `spine-dev-qa-auto`; its entry carries `autoPort: true`, so **the port exists
    only in the `preview_start` result of the spawn that started it** (ticket 38, the one-run-per-feature layout ticket,
    sitting 2). **It probes that server through the repo's
    probe script, never with a bare `curl`** — on this repo,
    `node scripts/http-probe.mjs "<label>" <url>`, allowed by one prefix rule.
    It also mints its sign-in link and runs any live Zoho suite through the lock
    wrapper, both `node --env-file=<canonical env> scripts/...` forms, allowed
    by one prefix rule on that spelling.
  - **Fixer** — typecheck, lint, the relevant test files, git stage and commit,
    and the same lock wrapper for a live Zoho suite.
  - **Claim gate** — whatever the reproducers it runs need, plus
    `python3 ~/.claude/skills/run-issues/make_copy.py --own-node-modules` into
    the session scratchpad.
  - **Fix gate, and fix gate critical** — the same `make_copy.py` into the
    scratchpad, the test runner inside that copy, and `/code-review`.
  - **The orchestrator itself** — `CronCreate`, for the resume wakeup.

  **Two measurements, both paid by `/run-issues`, and both would repeat here.** On
  2026-08-14 a verify gate sat on "Allow Claude to start spine-dev-qa-auto?" with
  its own task counter reading 6h 00m 05s, and the human found it by looking at the
  screen. A bullet was already present and the runner ran it correctly: it
  enumerated the classes the old text named and dry-ran every one. It read an
  illustrative list as a complete one. Separately, run `cab74e` stopped for a
  permission dialog at the end, unattended, because a raw `curl` is allowed as an
  exact string and the next probe used a different port. The list is derived from
  roles for those two reasons, and each role names its own tools.
- **Creating a worktree includes installing dependencies and making the
  `.env.local` symlink. If either fails, the round refuses to start.** Not a
  checklist item to remember afterwards — part of what "the tree is ready" means.
  One shell command, 30 to 60 seconds per worktree, and it saves more than it
  costs the first time it stops a finder diagnosing a false green that was really
  a missing environment file. (Adopted by the human 2026-08-07.)
- Every worktree's `.env.local` is a **symlink** to the canonical env file (path in
  the repo CLAUDE.md), never a copy. Replace any copy found. Env files are never
  committed or pushed.
- **Vercel-CLI trap:** `vercel link` / `vercel pull` write *through* the symlink
  into the canonical env file. Remove the symlink, run the command, delete the
  `.env.local` it wrote, restore the link.

## Also fits

Pre-launch security gates (coderules' ten points as register entries),
test-coverage campaigns, migration and deprecation sweeps, docs-drift rounds.

**Not** for building one feature — that is a dependency chain. Use
`/to-issues` then `/run-issues`.
