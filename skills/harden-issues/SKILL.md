---
name: harden-issues
description: Attack acceptance criteria at authoring time — a blind-spot pass over issue files that sharpens criteria with evidence, names invariants, and routes open forks to the human. Use before a /run-issues batch (pre-batch pass over ready-for-agent issues) or when an upstream issue-drafting pass invokes it on drafts. Also on "harden these issues", "pre-batch pass", "attack the criteria".
argument-hint: "issue numbers, a range, 'all ready-for-agent', or nothing when invoked on drafts by an upstream tool"
---

# Harden issues

Attack acceptance criteria before anyone builds to them. An issue whose criteria
are wrong when written passes every gate — the implementer builds to the bad spec
and both gates grade against that same bad spec. This pass is the early fix.
Settled 2026-07-27 after two runs' evidence; the brief lives in a memory file, not
published here.

Two entry points, same pass:

- **From an upstream issue-drafting pass, if the project has one** — runs on the
  drafted slices before the user quiz; the pass's questions join that quiz.
- **Standalone, pre-batch** — runs over any set of `ready-for-agent` or
  `needs-harden` issue files before a `/run-issues` batch; questions come back as
  one numbered list. `needs-harden` is what a run sets when it finds criteria that
  are wrong or stale, so those issues return here rather than resting.

## Write authority — the one rule that matters

The pass may edit an issue file **only where it can cite verification**: a
file:line in current code, a query against real data, or a measured value. The
same bar the run gates use. Everything else — and **every open fork** — becomes a
numbered question for the human. The pass never settles a fork by choice.

Any road-shaped statement it writes ("the rule is X", "the cause is Y") is a
hypothesis unless its premise was tested. Untested → write it as a hypothesis
with an explicit premise-check clause for the implementer, testing the premise
itself, not a narrow question near it. This is the 122 lesson: a manual pre-batch
pass settled "latest outcome wins" as fact, and the run spent two attempts down
the falsified road.

## Fan-out

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the pass never pastes a brief.

| Stage | Agent type | Effort |
|---|---|---|
| Attack one issue | `harden-issues-attacker` | high |
| Seam pass over the set, once | `harden-issues-seam` | high |

Attackers run concurrently, one per issue. The seam agent runs after them all,
reading every issue plus the attackers' findings files.

Findings go to files, not through this session's context: attackers write
`.scratch/<feature>/harden/<issue>.md`, the seam agent writes
`.scratch/<feature>/harden/seam.md`. The pass reads counts and questions, never
the working.

**Model: the agents ship on `model: inherit`.** Blind-spot hunting benefits from a
second, differently-tuned model rather than the session's default, so pin one in
the agent frontmatter if you have one available and trust it on this job. Either
way run it at `high`, not `max`: the checklist is enumeration against a file, and
enumeration is recall rather than chained reasoning.

**Never attack an issue a run holds.** Skip anything whose `Status:` is not
`ready-for-agent`, or whose row in the same directory's `run.md` is past `queued`.
Rewriting criteria under a working implementer causes a rejection on correct work,
then a strike, then an escalation chasing a criterion the implementer never saw.

**The one exception: strike-2 mode.** A `/run-issues` runner may spawn a single
attacker against an issue it holds, after two rejections, before it buys a third
implementer. The guard above protects against a second writer, and at that moment
there is none — the implementer is dead and the runner spawns nothing else until
the attacker returns. Strike-2 mode is narrower than a normal pass: classes 1, 5
and 9 only, evidence or silence, and **it never waits for an answer** — an
unsettled fork returns as a blocked issue, not a question the run sits on.

## The attack checklist

Earned, not invented — each class shipped a real defect through green gates in the
July 2026 runs. The attacker works the list against the issue AND the current
code/data, and reports per class: sharpened (with evidence), question (for the
human), or clean.

1. **Unstated invariants.** What must NOT change. Name the neighbouring behaviours
   the slice sits beside — paging, limits, ordering, counts, permissions — and
   write them into `## Must still be true`. (114 met all four criteria while
   dropping the page cap.)
2. **Invariant scope.** Every invariant states who it covers: all callers,
   including ones routed in by other issues later. (126's request-count invariant
   was graded against four callers while two more arrived from 120.)
3. **Vague words.** "Consistent", "bounded", "handled", "a recovery affordance" —
   each criterion must name a fixture and an answer. (122's "internally
   consistent" was satisfied by the bug it described.)
4. **Guards that cannot fail.** Each criterion states how a violation would be
   observed. Prefer mutation-shaped criteria — "reds when X is deliberately
   reintroduced" — where cheap. (Eleven guards that could not fail in fourteen
   issues.)
5. **Unverified premises.** Every factual claim in the issue — counts, "both
   bots", "the DB splits case variants", any impossibility claim — verified
   against the real code or data, or flagged. (114's headline premise was false
   of the actual database; 116 said two channels, the code had three.)
6. **Empty or missing hostile data.** Does QA/production hold data that can
   exercise each criterion? If not, say so and name the fixture to create —
   otherwise the gates validate over an empty set. (118: five tables, zero rows.)
7. **Deploy and boundary reality.** Migration ordering (one-way? code-first or
   db-first?), client/server module boundary, platform caps. (Three migrations in
   one run, each with an unstated ordering hazard; the run's worst defect was a
   server page importing a client module.)
8. **Observability.** How will each criterion be verified, and is the property
   observable to a gate or a walk at all? A criterion nobody can observe is not a
   criterion. (112's known fault is structurally invisible to a UI walk.)
9. **Size against the one-implementer bound.** A clean issue runs ~30-90 min;
   suspect anything whose criteria span several independent deliverables, or that
   packs migration + logic + UI into one slice. Propose the cut line — where one
   half ships and gates alone ("extract + harness", then "behavioural tests") —
   as a question for the human; splitting is their call, never the pass's or the
   runner's. (129 ran 4h58m, 19% of its batch; 114 ran 3h52m, 55% of its run.
   `/run-issues` deliberately never splits mid-run — an oversized issue that
   reaches a runner arrives back here.)

The seam agent adds: gaps that fall between two issues, invariants one issue
scopes that another widens, and accidental dependencies (a fix that holds only
because of something a sibling issue deletes).

## Output and the stamp

- Evidence-backed sharpenings are edited into `## Acceptance criteria` and
  `## Must still be true` directly, each carrying its citation.
- **Every question ships with the pass's recommended answer**, and is marked
  `[reversible]` or `[irreversible]`. A question with no default is a question the
  pass has not finished thinking about.
- Questions go to the human: into the upstream drafting tool's quiz, if there is
  one, or as the standalone numbered list. Apply their answers to the files.
- Then stamp the issue, one line under `Status:`:
  `Hardened: <date> — <n> sharpened, <m> questions resolved.`

**An open question never removes an issue from a run.** Where the human has not
answered, take the recommended default, write it into the file as a default rather
than a decision, and stamp:

`Hardened (provisional): <date> — <n> sharpened, <m> defaults pending.`

A provisionally stamped issue is in scope for `all`, and the merge briefing names
every one that shipped that way, so the answer arrives after the run instead of
holding it up. Two things are not defaultable: an `[irreversible]` question, and a
split — both leave the issue unstamped, and out of `all` until the human rules.

Every defaulted question is also appended to `.scratch/decisions-queue.md`, the
one place every tool upstream of this pass queues decisions, so they reach the
human in a single list rather than scattered across issue files.

Where an answer needs input nobody here has — a third party, a credential, a
product call with no defensible default — set `needs-harden` instead, so the issue
comes back to this pass rather than dying in a status nothing reads.

`/run-issues` lists unstamped scoped issues in its launch message — a launch-time
line for the human, never a gate, never mid-run.

## Scope notes

Issue trackers are per-project — this pack's convention is
`.scratch/<feature>/issues/`. The pass edits issue files only — never code, never
the tracker board, never another skill's state.
