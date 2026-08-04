# harden-issues — decisions record

Why the skill is shaped the way it is. Same pattern as `run-issues/decisions.md`:
the SKILL.md carries the rules, this file carries the evidence and the reversals,
so the provenance is not billed on every invocation. Read it when changing the
skill, not when running it.

## The pass exists because gates grade against the issue (2026-07-27)

Settled after two runs' evidence (the July 2026 batches). An issue whose
acceptance criteria are wrong when written passes every gate, because the
implementer builds to the bad spec and both gates grade against that same bad
spec. The only place to catch it is before anyone builds — at authoring time,
with write authority capped at what can be cited.

## What each checklist class cost before it was a class (2026-07-27)

Earned, not invented — each shipped a real defect through green gates:

1. **Unstated invariants** — issue 114 met all four criteria while dropping the
   page cap.
2. **Invariant scope** — 126's request-count invariant was graded against four
   callers while two more arrived from 120.
3. **Vague words** — 122's "internally consistent" was satisfied by the bug it
   described.
4. **Guards that cannot fail** — eleven guards that could not fail in fourteen
   issues.
5. **Unverified premises** — 114's headline premise was false of the actual
   database; 116 said two channels, the code had three.
6. **Empty or missing hostile data** — 118: five tables, zero rows.
7. **Deploy and boundary reality** — three migrations in one run, each with an
   unstated ordering hazard; the run's worst defect was a server page importing
   a client module.
8. **Observability** — 112's known fault is structurally invisible to a UI walk.
9. **Size against the one-implementer bound** — 129 ran 4h58m, 19% of its batch;
   114 ran 3h52m, 55% of its run.

## Hypotheses are not facts: the 122 lesson (2026-07-27)

A manual pre-batch pass settled "latest outcome wins" as fact, and the run spent
two attempts down the falsified road. Hence the rule: any road-shaped statement
whose premise was not tested is written as a hypothesis with an explicit
premise-check clause for the implementer — testing the premise itself, not a
narrow question near it.

## The stamp and `Status:` were two sources of truth (found 2026-08-02, fixed 2026-08-04)

Found after a model-comparison pass over eight issues. All three arms hit it, so it
is the skill's fault rather than one model's.

**What happened.** Five issues came out of the pass with
`Hardened (provisional): <date> — n sharpened, m defaults pending.` and with their
`Status:` line still reading `needs-harden`. By this skill a provisional stamp puts
an issue in scope. By `/run-issues`, `all` resolves scope from each issue file's
`Status:` line and takes only clean `ready-for-agent` issues, skipping `needs-*`. So
all five would have been silently dropped from the next batch, while this skill's own
output said they were ready. Nothing errors. The run just comes back smaller than it
should, and nobody is told which issues went missing.

**Why the skill causes it.** SKILL.md says "Then stamp the issue, one line under
`Status:`". It says where to put the stamp and never says to update `Status:` itself.
The only place it touches `Status:` is the failure road — "set `needs-harden`
instead" when an answer needs input nobody has. So a pass that succeeds has no
instruction to clear the `needs-harden` it started from, and an issue that entered
through the standalone door keeps the status that sent it here.

**A second, related contradiction, same cause.** The fan-out guard says "Skip
anything whose `Status:` is not `ready-for-agent`", but the standalone entry point
says the pass runs over "any set of `ready-for-agent` or `needs-harden` issue files"
and that `needs-harden` "is what a run sets when it finds criteria that are wrong or
stale, so those issues return here". Read literally, the guard tells the pass to skip
exactly the issues the entry point exists to serve. In practice every arm ignored the
guard and attacked the `needs-harden` issues, which was the right call and is not what
the text says.

**Cost if it had been left.** Silent under-scoping of every batch after a standalone
pass, in the direction that looks like success. This is the same shape as the defects
the checklist exists to catch: a green that means nothing, with no observer.

**The fix, applied 2026-08-04 in one edit across four files.**

1. In "Output and the stamp", the status change is now part of stamping: a full or
   provisional stamp sets `Status: ready-for-agent`, and any minting note goes on
   its own `Provenance:` line rather than as a suffix on `Status:`. The text says
   plainly that the two must agree and that `/run-issues` reads the status, not the
   stamp.
2. In "Fan-out", the never-attack guard now keys on what it was always protecting
   against — an issue a run currently holds. It reads the run ledger's row and owner
   line, not the issue's `Status:`, and says outright that `needs-harden` is in
   scope. The same guard was duplicated in `harden-issues-attacker.md` and
   `harden-issues-seam.md`; both were corrected the same way, since an agent obeying
   its own brief would have re-introduced the skip the skill had just dropped.

**The judge, next standalone pass:** whether any issue leaves the pass with a
`Hardened` stamp and a `needs-*` status. One is a regression, not a slip.

## The model pin is gone; both agents inherit (2026-08-02)

The human's call. `harden-issues-attacker.md` and `harden-issues-seam.md` had
pinned a specific model since they were written, on the theory that blind-spot
hunting was the one job that model still led. Both now read `model: inherit`, so
the pass runs on whatever tier the session was launched on. Effort is unchanged at
`high`.

Two reasons. The pin put the model in a file nobody reads at launch, so a session
started on one tier quietly bought another for the hardest, most parallel stage of
the pass. And the pinned model was credit-gated, which is why SKILL.md carried a
respawn fallback — a branch that only exists because of the pin. Wanting a
different model is now one action: launch the session on it.

This also removes the last exception to `/run-issues`'s "workers inherit the
session model" rule, so that rule's parenthetical about a deliberate pin went with
it. The rule against passing `model:` on a spawn stands: the spawn tool's
parameter still beats frontmatter, and `inherit` is exactly what it would defeat.

**The launch line came with it, same day.** `inherit` makes the tier a launch-time
choice, and this pass had nowhere that choice was visible: `/run-issues` prints
its resolved model before spawn #1 and records it in the ledger and the merge
briefing, while a harden stamp carries a date and two counts and no tier. So a
spawn-time `model:` value, or a session launched on the wrong tier, would have run
the whole pass unobserved. SKILL.md now requires the same launch line, and repeats
the never-pass-`model:` rule where the spawning happens rather than only in
`/run-issues`. Asked for after the question of how likely a stray wrong-tier spawn
actually was — low, but nothing would have caught one.

## This file exists (2026-07-27)

One of the five forks from the 2026-07-27 panel review, taken by the human: three
personas wanted the provenance out of the hot file, which is billed on every
invocation. The incident anecdotes above moved here from SKILL.md the same day;
the checklist itself stays in SKILL.md because it is the working instruction, not
provenance.
