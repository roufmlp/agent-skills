# parallel-hunt — settled decisions and the incidents behind them

Read this before changing how the round works. Do not read it to run one — the
skill and the agent files are self-contained. Nothing here is loaded into a
subagent's context.

Newest section last.

---

## Original design (2026-07-19, grilled and agreed)

Adversarial gates over both claims and fixes; a shared-file register as the only
state; strict single-writer ownership per status transition; batch succession so no
worker outlives its work unit; cron auto-resume.

The load-bearing idea is that **the register is the handoff**. No worker writes a
handover document, because a second copy of the state goes stale the moment it is
written.

## Why the claim gate biases toward retraction

A phantom bug is more expensive than a missed one. It consumes a fixer slot, a fix
gate review, and then sits in the register as a lie that later rounds trust. A real
bug that gets wrongly retracted will be found again by a later sweep. The asymmetry
is deliberate, and the gate is told not to talk itself into keeping a weak claim.

## Why the finder may not touch shipped code

Not tidiness — merge tax. A finder that fixes as it goes produces diffs nobody
gated, competing with the fixer's own edits in the same tree. Splitting find from
fix means every change to shipped code passes exactly one adversarial review.

---

## Opus 5 rework (2026-07-25)

Done alongside the same rework of `run-issues`; the measurements and the reasoning
behind model and effort choices are recorded once, in that skill's `decisions.md`.
Summary of what applies here:

1. **Fable left the gates.** Both gates were Fable on the theory that adversarial
   judgement was its strength. Opus 5 now leads Fable on agentic search and
   knowledge work — which is what a gate does — at half the price. Fable was also
   found to be credit-gated and exhausted, so it was not a dependency worth having.
2. **Effort is real now, and measured.** The old "effort floors" were decorative:
   the `Agent` tool has no effort parameter, so every worker inherited the
   session-wide setting. Agent definition frontmatter does carry effort. Measured:
   `xhigh` is +23% over the default and `max` is +85%; `low` showed no separation
   from the default and is not used.
3. **The finder runs at `xhigh`, alone among the roles.** Its failure is the only
   one invisible from inside the round — a missed bug is not caught downstream, it
   is found weeks later by a human on the deployed system. Every other role's
   failure surfaces immediately. Buy depth where the feedback loop is longest.
4. **The finder's sweep group dropped from 8–10 entries to 6–8.** Higher effort
   burns context faster, so the unit that runs at `xhigh` needs to be the smallest.
   The fixer stays at `high` and keeps its batch of 3.
5. **Delegation narrowed to reads.** The old instruction pushed bulk mechanical
   work to Sonnet subagents, tuned for a model that under-delegated. Opus 5
   over-delegates. Bulk *reading* may still go to a subagent for context hygiene;
   anything that writes stays with the worker, in its own tree.
6. **Briefs moved into agent files**, so the orchestrator no longer pastes them and
   a spawn's prompt carries only what varies.
7. **Grounding added to every role.** Claims are audited against tool results
   before they are reported: a gate that did not run the reproducer says so rather
   than implying it verified one, and a finder that could not reproduce a suspicion
   files a note rather than a register entry.

---

## Round 9 (2026-08-01/02) — three findings the round paid for

### 1. Gates need somewhere to drive a state that is not the shared tree

Two gates wrote into the hunt worktree in one round. One left an untracked throwaway
named `*.test.ts` in the repo **root**, where it would have joined the suite. The other
**overwrote four source files and restored them with `git checkout --` while a fixer was
mid-edit**. The work survived on timing alone: the clobber window closed before the
fixer's first edit, which the fixer verified rather than assumed.

Both gates were rigorous, and both self-reported. **The failure is the instruction, not
the judgement.** A gate that must drive a state to test a claim has nowhere to put it.

Mid-round the orchestrator began telling every gate to use a `git clone --shared` under
a scratch directory and delete it after. Every gate after that did, and it cost nothing.
**Put it in the gate agent files:** never write source in the hunt tree; clone to
scratch; never `git checkout --`. Some checks need no clone at all — ESLint accepts
`--suppressions-location` pointed at an empty file.

### 2. Every fix rejection was prose. None was code.

Four rejections across sixteen entries and four assigned tasks, and **not one was a
wrong diff**. Each was a sentence a fixer wrote that its own diff did not support:

- A claim about what a shipped acceptance criterion had decided. The criterion said
  something narrower, and the fix had quietly widened past it.
- A claim that the fix also repaired a second defect. Driven both sides of the commit:
  the repair did not exist.
- A claim that a test's isolation guarded a particular assertion. The component under
  test never emits the class that assertion looks for.
- A retracted entry whose bug file recommended a fix that would have left the record
  half-written with no remediation task at all — worse than the bug. Flagged, not built.

`run-issues` already carries the rule this produces: **delete a rejected prose claim,
never restate it.** It belongs here too, and the fixer agent file should say the claim is
part of the deliverable. Three of these were caught only because a gate re-measured a
sentence nobody had asked it to check.

### 3. A green pin proves the behaviour, not the wiring

Three pins in one round could pass while proving nothing: an any-throw `catch`, a
whole-object `not.toEqual`, and an early `return` on a null. All three were caught by a
claim gate reading the pin rather than running it.

Worse, three *fixes* were correct while nothing protected the path to them. Deleting the
line that carried a value from the read to the screen compiled clean and red nothing
across 3565 tests, three separate times. The remedy each time was one rendering case, or
one required prop that turns the deletion into a type error.

**Worth a line in the claim-gate and fix-gate files:** ask what a green pin would still
pass with the fix removed *and* the wiring cut, not only with the fix removed.

### A method worth keeping, and its limit

A lint-suppressions file is a map of where a repo has agreed to look away. Deleting one
file's entry and re-running the linter enumerated four real defects in a file three
finder units had already swept.

**But it cannot close a class.** The lint config named shapes its own rule could not see,
and said of one, "There is no count of how many remain." Use it to enumerate; never
report the result as closure.
