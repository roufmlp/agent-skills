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

## This file exists (2026-07-27)

One of the five forks from the 2026-07-27 panel review, taken by the human: three
personas wanted the provenance out of the hot file, which is billed on every
invocation. The incident anecdotes above moved here from SKILL.md the same day;
the checklist itself stays in SKILL.md because it is the working instruction, not
provenance.
