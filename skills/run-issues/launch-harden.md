# Harden at launch — the phase between the launch line and spawn 1

**One trigger, and nothing else opens this file.** `SKILL.md`'s hardening-stamp
bullet listed the scoped issues whose files carry no `Hardened:` line. That list
is not empty, so this phase runs. A run whose scope is entirely stamped never
reads a word of this, and costs exactly what every run before the fold cost.

**This file holds the phase. It does not hold the pass.** How an issue is
attacked — the eleven classes, the write-authority bar, the stamp, the question
form — lives in `harden-issues/SKILL.md` and in that skill's `decisions.md`,
which is where the agents you spawn read it from. Never restate a class here:
two copies of a checklist drift, and both read as authoritative while they
disagree. Why the phase is shaped this way is in `decisions.md` beside this
file, under the 2026-09-07 heading.

## Scope — what the phase takes, and what it refuses to take

**The phase hardens every unstamped issue in scope, at launch, in one pass** —
never one issue at a time before each implementer. Strike-2 mode already covers
the narrower case of a criterion that goes stale mid-run, and it stays where it
is, in `harden-issues/SKILL.md`.

**Only an issue that was typed on the command line enters this phase.** A run
still does not pick its own batch. `all` is unchanged: it resolves from each
file's `Status:` line, it skips every `needs-*`, and an unstamped issue it
resolves is listed in the launch message as before and hardened by nobody. The
backlog's `needs-harden` issues enter a run by being typed, and by no other
road. (Ruling 1.)

**There is no off switch on the command line.** The scope grammar gains no
fourth override word beside `models:`. To build an unstamped issue raw, stamp it
in a standalone `/harden-issues` pass first — and note that `check_issue_ready.py`
refuses a file with no criteria whatever the stamp says. (Ruling 18.)

## Which tree the phase works in, and it is not the one the tracker lives in

**Every issue file this phase reads and writes is the copy in the run's own
worktree, never the main checkout.** The commit in step 6 lands on the run's own
branch, so a file hardened anywhere else is not in it: the implementer then reads
the unhardened copy the worktree still holds and is graded against criteria the
phase already replaced, while the main checkout carries a run's uncommitted edits
to an issue file. Both halves are wrong and neither is loud. The commit step
finds nothing to commit and says so cheerfully.

So the attacker and seam spawns carry the **worktree path** of each issue file —
`<run worktree>/.scratch/<feature>/issues/<file>` — the same way they carry the
run-scoped findings path. The findings themselves stay where ruling 7 put them,
under the run directory in the main checkout, because that is where the ledger
and the journal already are and nothing grades against them.

`main` belongs to the human, and a run touching it is the rule the phase is likeliest
to break by accident: the tracker lives in the main checkout, so the main copy is
the one a path completes to.

## The order, and it is fixed

**`check_harden_branch.py` has already refused, or this phase does not run.**
It is the pre-flight's first bullet, above the batch id and above the trigger
that opens this file, so by the time you are reading this no unmerged
`claude/harden-issues-*` branch holds an issue in scope. That order is what
makes the phase safe to spend on: a peer hardening session and this phase
rewriting one issue file at the same moment is the collision
`check_harden_branch.py` exists to prevent, and the fold nearly reintroduced it.

Inside the pre-flight, in this order and no other (ruling 9):

1. The launch line prints, naming what this phase will harden.
2. The citation check repairs the unstamped files and reports on the stamped ones.
3. The attacker waves.
4. The seam pass, where two or more issues are unstamped.
5. Drops, defaults and stamps.
6. One commit.
7. `check_issue_ready.py`, over the scope that survived step 5.
8. Spawn 1.

The launch line is first for the reason it is first everywhere: it is the
interrupt window, and it has to open before the first attacker token is spent.

## Step 1 — the launch line names the phase

The line `SKILL.md` already requires gains one clause: which issues this phase
will harden, and how many attackers are about to spawn. It is not a wait. It
prints and the phase starts.

## Step 2 — the citation repair, and it is not the report

`node scripts/check-issue-citations.mjs --quiet <file>` is already run over every
scoped file at pre-flight. Its two jobs are now different by file:

- **An unstamped file in this phase's scope is REPAIRED.** Correct every `moved`
  row to the line it reports; read every `gone` row rather than deleting it. The
  phase holds the write authority a hardening pass holds, so the repair costs
  nothing extra here and costs an attacker a whole round everywhere else.
- **A stamped file is REPORTED and left alone.** A run may not write an issue
  file it did not harden. Name the broken ones in the launch line and carry on.

**Read the rows, never the exit code.** That command grades every landed
decision in the repository beside the file you named, and it has no flag to stop
it, so it exits 1 on a stale `Touches:` line in a feature this batch never
touches. Take the verdict from the file's own summary line and from the `MOVED`,
`GONE` and `AMBIGUOUS` rows that name it. Repairing on the exit code rewrites
every unstamped file in scope, including the clean ones.

Every citation this phase WRITES quotes text, never a line number. That rule and
the corpus it does not convert are in `harden-issues/SKILL.md`.

## Step 3 — the attacker waves

**Five attackers at a time, and no more.** Spawn five, wait for all five to
return, spawn the next five. **Nothing is dropped to fit the cap** and no issue
is deferred to a later run: a batch of thirteen unstamped issues is three waves,
not eight issues and a promise. A wave is about twenty-five minutes of wall
clock whatever its size, because the five run concurrently. (Ruling 21.)

The cap is a recipe read at spawn time, not a refusal. Nothing hooks it. A
refusing hook gets built the first time a run is measured over the cap, and not
before.

Every spawn is `harden-issues-attacker`, one issue each, with `run_in_background`
named on the call. **Give each one the worktree path of its issue file**, per the
section above: the run's own worktree, never the main checkout.

**Carry this run's model on every spawn.** Read
`Model map at launch:` in `run.md`, take the `attacker` value, and pass it in the
Agent call's `model` field. **This pack ships no refusal for that**, so the map
is a rule the runner holds: `run-issues/SKILL.md` says the same, and
`hooks/README.md` says what a reader gains by writing one.

**Findings go to this run's own directory**: `.scratch/<feature>/runs/<batch-id>/harden/<issue>.md`,
never the shared `harden/` directory an attended pass writes. Pass the batch id
in the brief. On each return, before the next wave and before anything is
stamped:

```bash
python3 ~/.claude/skills/lib/check_verdict.py \
    --file .scratch/<feature>/runs/<batch-id>/harden/<issue>.md
```

A non-zero exit means that attacker produced nothing whatever its final message
said. Re-spawn it once. **If the second spawn also writes nothing the phase has
FAILED on that issue**: leave it unstamped, take it out of scope by step 5's
last paragraph, and name it in the launch line as unattacked, because an issue
nobody attacked is never stamped. That is a phase failure and not a fourth drop
class — ruling 4 closes the list of FORKS that drop an issue, and an attacker
that wrote nothing settled no fork.

## Step 4 — the seam pass

Spawn one `harden-issues-seam` after the last wave returns, **where two or more
issues in this batch are unstamped**. One unstamped issue in a batch of fifteen
buys a seam agent that reads fifteen files to find gaps around one, so it is
skipped and the launch line says it was skipped. The `seam` key in the model map
carries its model, the same way the attacker's does.

**Give the seam agent every issue in the batch, stamped ones included**, and be
ready for what comes back. A gap between two issues does not care which of them
was hardened today, so the seam will find some against files this phase may not
write.

**A seam finding against a stamped issue is carried, never applied.** The phase
holds write authority over the unstamped files only, and editing a criterion
under an existing stamp leaves that stamp describing a file it no longer
matches. So the finding goes two places: into that issue's implementer **spawn
prompt**, under `Settlements:` in the round header, and into the **merge
briefing** as a line under `## Ruled`, naming the issue. The runner is allowed
both — neither is an issue file. It drops nothing; ruling 4's list stays closed.

**An issue step 5 drops has no implementer, so its seam findings go to the
briefing alone**, under `## Decide` beside the drop itself rather than under
`## Ruled` — the issue comes back to be re-hardened, and whoever hardens it
should read what the seam saw before it left.

A finding left in `seam.md` alone is a finding nobody reads. This phase takes
counts and `## Checks for the human` out of that file and never the working, which is
the rule `harden-issues/SKILL.md` sets for every caller.

## Step 5 — what the phase settles, and what it drops

**Only three things drop an issue from this run:**

- An `[irreversible]` question. It takes no default by rule, so the issue leaves
  the scope and waits for the human.
- **A split this phase can complete is cut here**, so a split is a drop only
  where the phase cannot complete it. Cut it, write criteria for both halves,
  stamp both, and put both in the ledger — where the reader's setup carries an
  overlap guard it then covers both halves, so no second run can take them.
  **A split that changes a migration's direction is a drop** whatever else is
  true of it.
- A premise check whose answer only the human can fetch. It is not defaultable at
  any tier, so the issue leaves the scope unstamped.

**Every other fork takes its recommended default**, is written into the file as
a default rather than a decision, and is queued to this run's own decisions
shard. The issue is stamped `Hardened (provisional):` and stays in the run.
(Rulings 3, 4 and 11.)

A dropped issue comes out of the ledger's status table AND out of its title line
and any `Scope` line, before spawn 1. **All three, because
`find_live_ledger.parse_scope_ids` reads all three**, and an id left in any one
of them is an issue this ledger still holds: an overlap guard reading that
ledger would then refuse another run that typed it, for the whole remaining life
of this batch, which is the opposite of dropping it. Name it in the launch line with the class
that dropped it, and again in the merge briefing. It is not `blocked` — nothing
in this run is waiting on it.

## Step 6 — one commit, before spawn 1

Commit every file this phase wrote, on the run's own branch, in one commit:

```
Harden at launch: NN, NN
```

Nothing else goes in it. **A halt between the phase and spawn 1 then keeps the
hardened files**, which is the whole reason it exists — the phase is the most
expensive part of a launch to lose, and an uncommitted worktree loses it. Issue
commits stay single-purpose because this one is taken first. (Ruling 10.)

## After the phase — what the run owes the merge briefing

**Every default this phase took is an item under `## Ruled — <n>, overturn any
of these`**, one line each, **naming its issue**. `run_measures.py` reads that
section and counts the issue as cut on a default, so a default written anywhere
else in the briefing is a default nothing counts. Put the facts in Carry-forward
as the phase closes, with the issues they serve named, so the finale writes them
from a record rather than from memory. (Ruling 12.)

A dropped issue goes under `## Decide` with the class that dropped it, because
its answer is genuinely owed.

**A `## Checks for the human` item that survives the phase goes to the pending file,
and it does not drop the issue.** `harden-issues/SKILL.md` settles these at the
end of the attended pass, in the same session as the questions — and this caller
has no attended session and never waits. An attacker files one when it has
exhausted the instruments this machine holds and the value is behind a console,
a credential or a live production read. That is a fact somebody has to fetch, not
a fork somebody has to settle, so ruling 4's drop list does not reach it and
ruling 12's `## Ruled` items are the wrong home: nobody ruled anything.

Write it as a numbered action in the project's pending-actions file, where the
project keeps one — the home `SKILL.md` already names for anything a run needs
from the human's hands, and the file `/daily-brief` reads every morning. **Where
that file lives outside the repo, cite its path in full whenever you refer to
it** — a bare filename does not resolve from inside a repo tree, and one merge
briefing sent its reader searching the tree for a file that was never in it. Name
it under `## Decide` in the merge briefing as well, so the merge read sees it
beside the drops.

Kill the ones the phase's own defaults made pointless before you write either: a
check that exists only to decide a question this phase has already defaulted dies
with that question, and survives only where it decides something else. That rule
and the rest are in `harden-issues/SKILL.md`.

## What this phase never does

- It never widens the batch. Ruling 1 again, and it is the rule the fold is
  likeliest to erode.
- It never attacks an issue another live run holds past `queued`. That guard is
  one rule for every caller and it lives in `harden-issues/SKILL.md`. This run's
  own rows sit at `queued` while the phase runs, which is what lets the phase
  run at all.
- It never waits for an answer. Nothing in a run halts for the human; a fork that
  cannot default drops its issue and the run carries on with the rest.
- It never runs after spawn 1. An issue whose criteria go stale mid-run is
  strike-2 mode's, not this phase's.
- It never attacks an issue an unmerged `claude/harden-issues-*` branch holds
  **that the gate can see**. `check_harden_branch.py` refuses that launch
  outright, before this file is opened. **What it sees is committed work on that
  one branch name**: it lists `refs/heads/claude/harden-issues-*` and diffs
  `main...<branch>`. A peer pass whose hardening is still uncommitted in its own
  worktree, or which branched under another name, passes the gate unseen — so
  the phase can still meet a second writer, and the remedy there is the same one
  the never-attack guard uses: if `find_live_ledger.py --list` or a `git
  worktree list` shows a hardening session on these issues, stop and merge it
  first. A live LEDGER and a peer BRANCH are the two second writers ruling 5 and
  this gate cover between them, and neither covers uncommitted work.
