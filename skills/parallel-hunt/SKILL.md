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
python3 ~/.claude/skills/lib/collect_shards.py --kind register \
    --feature <feature> --my-shard --prefix <your row prefix>
```

Read the whole register by regenerating it first. Run this from anywhere; it
writes the generated file into the main checkout, and reading that one file
there is the only thing a hunt's worker does in the main checkout:

```bash
python3 ~/.claude/skills/lib/collect_shards.py --kind register --feature <feature>
```

**Writers append to a shard. Readers regenerate, then read.** A write to
`register.md` itself is refused by `generated-file-guard.py` in the hooks, which
names your shard in the refusal.

Five paths, split on one test: a thing belongs in the register only if another
agent must read it to do its own job.

```
<hunt-worktree>/.scratch/<feature>/register.d/<hunt-id>/<prefix>.md  # this round's rows, one shard
<main-repo-root>/.scratch/<feature>/register.md           # generated: every shard, in order
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
ruling 6, sitting 4). The one exception is the generated register, which the
collector always writes into the main checkout and which nobody commits. A hunt
cut from main before a run merges hunts the code as main holds it, without that
run's fixes; that is a fact about the cut, not a wait. Name any run at
`awaiting-merge` in the brief text at launch, so a finder that reproduces one of
its fixes on the old code is read against it.

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
  (Outside this loop, a `/run-issues` commit step also closes rows to `verified`
  where its commit fixed them — rule F6, 2026-08-27.)
- A hardening-pass or seam-agent row enters at `open` — or at `deferred` where
  it only waits for promotion. No claim gate runs over it: the pass's evidence
  bar is the gates' own. (Ruled by the human 2026-08-29.)
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
the human's ruling, 2026-08-06 (queue item T15-3). Before it, a round that fixed thirteen
faults reported thirteen refusals into their daily brief, where one word would have
overturned them and minted thirteen issue files for work that had already shipped.

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
script that reads a ledger stops at line 60, so a project's own seed script should
refuse a brief whose title line and `Worktree:` line are not inside it. The brief
text, the scope and the sweep groups come after.

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
Worktree:         <absolute path of the hunt's worktree; every role works here, and reads the regenerated register in the main checkout>
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
round report. The spawn names the issue directory; the agent takes each number from
`python3 ~/.claude/skills/lib/claim_number.py issue <dir> --for "promotion <hunt id>"`, which is
atomic across every worktree, and the hook `number-claim-guard.py` refuses a file under
an unclaimed number (ticket 38, rulings 7 and 16).
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

**The thresholds live in `~/.claude/agents/promotion.md` and nowhere else.** This file
and `run-issues/SKILL.md` both carried "operator at any severity" for a day after the human
set a `medium` floor on `operator` (T15-2, 2026-08-09), and a run brief repeated the
stale figure. Name the exits here; read the numbers there.

**`fixed` is never reported as a refusal**, and the ordering above is what enforces
it. The human overturns a refusal with one word, so a round's thirteen successful fixes
listed as thirteen refusals put a trap on their only control: one word would mint
thirteen issue files for work that had already shipped. Ruled 2026-08-06, queue item
T15-3. This section still said "two ways" a day after that ruling landed forty lines
above it; corrected 2026-08-07.

A promoted row becomes an issue file carrying:

- `Status: needs-harden`. A local file has no reporter, so there is nobody to ask
  for more, and `needs-info` is a dead end there. `/harden-issues` sharpens it from
  evidence instead. This is `triage`'s rule for a local file, inherited unchanged.
- One category role, from the same set `triage` uses.
- A link to `bugs/<ID>.md`. Promotion copies no evidence into the issue file.

**The human holds the veto, through `/daily-brief`.** The round report lists every
promotion and every refusal, and the brief carries both to them. Overturning either
is one word in the brief. **`fixed` is a count only, and carries no control** — it
is not a decision and they are offered none over it. A step they have to invoke by hand is a
step somebody forgets, and then the register grows in place of the issue directory.

**Anything needing their hands, rather than their judgement, goes somewhere else.** A
secret, an env var, an OAuth client, a DNS record at a registrar, a console setting —
anything the repo cannot do to itself — is written as a numbered action, one action per
number, with one line of what is blocked on it, to the project's pending-actions file,
if it has one. Where that file lives outside the repo, cite its path in full every time
and never make a repo-local copy. The round report is history the moment the branch
merges; the pending-actions file is the list a human actually reads.

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
   python3 ~/.claude/skills/lib/check_verdict.py --file <bugs/ID.md> --section "## Claim gate"
   python3 ~/.claude/skills/lib/check_verdict.py --file <bugs/ID.md> --section "## Fix gate"
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
6. Round end, in this order: mark leftovers `deferred`; spawn one `promotion`
   agent over every row, **carrying `model:` set to the `promotion=` value on
   `round-brief.md`'s `Model map at launch:` line** — it is a mapped role, so
   `model-map-gate.py` refuses a spawn that omits it (ticket 39, ruling 10);
   **take the five readings below, which must happen before the brief is
   deleted**; delete this round's QA workspace; delete the heartbeat
   cron; delete `round-brief.md`; commit. Then report — verified fixes, rejected
   fixes, retracted claims, the two lists promotion returned, and the branch and
   worktree the human merges. Say plainly what was left undone; a round that reports
   only its wins is not a report.

   **What a round cost, and what each role ran on.** Until ticket 39 of the
   pilot-delivery map, every-worker-inherits-the-session-model, a hunt had no cost
   script at all, so a hunt's cost was not measured whatever the model. Its sitting 3
   gave the run's four scripts a `--batch` and one set now serves both (ruling 12).
   Run all five with this round's hunt id and paste the output into the round report:

   ```
   python3 ~/.claude/skills/run-issues/run_costs.py --batch <hunt-id> --no-append
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

   **`--no-append` on the first one.** `.scratch/workflow-audit/run-costs.md` is one
   row per RUN and its columns are a run's — issues shipped, per issue, correction
   rounds. A hunt has none of those, and a hunt row in that table would be read as a
   run for as long as the table lives.

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

   Whatever the round seeded outside git goes BEFORE the brief is deleted, because
   the brief is where its id is. Where the project has a teardown script, run it
   here and let it read the id off the brief rather than taking one by hand: it
   should delete only a row whose name carries this hunt id, and it should refuse
   rather than orphan child rows. **A refusal is not a stop**: put its printed
   remedy in the round report as an action on the human, with the id, and go on.
   Once the brief is deleted no ledger names that row, so nothing can sweep it
   later and the human clears it by id.

   Do not promote rows yourself. Rule 1 holds all the way to the end of the round,
   and spawning is what keeps it holding: the agent reads the rows, and you read two
   lists.

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
`python3 ~/.claude/skills/lib/collect_shards.py --kind register --feature <feature> --mtime`
— do not read the rest of either file. If the brief is there and the register's
mtime is over 60 minutes old, resume from register state; otherwise do nothing." `round-brief.md` is the
marker because it is written at launch and deleted at round end, so its presence is
what "a round is open" means. Firings that land while rate-limited simply fail; the
first after the reset revives the round. Delete the cron at round end. Remind the
user once that the machine must stay awake (`caffeinate -dimsu`).

**`/parallel-hunt resume` is typed inside the hunt's own worktree.** The listing
is `python3 ~/.claude/skills/run-issues/find_live_ledger.py --list`, which prints
every live ledger with its kind in the last column, `hunt` for a round brief.
Nothing picks a round by freshness, and a resume from the wrong tree would spawn
workers into a tree that holds no round.

Every agent file opens with its own idempotency check — read the register first,
stop if the assigned work is already past this stage — which is what makes resume
safe.

## Pre-flight

- **One hunt at a time, and a hunt beside a live run is allowed.** Refuse to
  start while a `round-brief.md` is live in any worktree. The old refusal — no
  hunt beside a run — existed because both worked in the main checkout, and the
  next bullet removes that cause. Refuse to start only if the MAIN checkout's
  `git status` is dirty, because the hunt's worktree is cut from it.
- **Mint the hunt id and cut the hunt's own worktree.** The id is `hunt-` plus
  six hex characters (`openssl rand -hex 3`), and it is the same id the branch
  carries and the shard directory carries. Then, from the main checkout:

  ```
  git worktree add <main-repo-root>/.claude/worktrees/<hunt-id> -b hunt/<hunt-id> main
  ```

  Finder and fixer both work in that one tree, on that one branch. They stay
  together on purpose: a second tree would hide the finder's pinning tests from
  the fixer, and a failing pinning test lives on the hunt branch until merge and
  never enters a run's finale. Exactly one finder and one fixer live at a time.
  The branch goes to the human at round end; the orchestrator never merges to main.
- **Isolate whatever the round writes outside the repo, under the hunt id.** A
  round that seeds a database, drives a dev server or takes a third-party
  sandbox needs its own row, its own host and its own lock, all named by the
  hunt id, or two rounds — or a round beside a run — collide in a place git
  cannot separate. What that takes is the project's to say, so it belongs in
  the project's own scripts and its `CLAUDE.md`, not here. Three shapes worth
  copying: one workspace row per round, named `run-workspace <hunt-id>` and
  deleted at round end; a dev server driven at `<hunt-id>.localhost:<port>`
  rather than bare `localhost`, because a browser cookie is scoped to the host
  and not the port, so two servers on `localhost` share one session; and any
  live third-party suite serialised behind one lock file outside every repo,
  keyed by the account it writes to.
- **Every spawn carries its own role's model, read off `round-brief.md`.** The
  five hunt roles — `finder`, `fixer`, `claim-gate`, `fix-gate`,
  `fix-gate-critical` — plus `promotion` are named on the brief's
  `Model map at launch:` line, which the launch line writes. Take this role's
  value and pass it in the Agent call's `model` field.

  This bullet said the opposite until 2026-09-05: agent files use
  `model: inherit`, so every worker inherits the session's tier. The agent files
  still say `inherit`, so a spawn by hand outside a round is unchanged, but a
  round with a brief takes its models from the brief.
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
    `git clone --shared` into the session scratchpad.
  - **Fix gate, and fix gate critical** — `git clone --shared` into the
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
