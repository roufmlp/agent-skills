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
